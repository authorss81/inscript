# dap_server.py — Debug Adapter Protocol server for InScript (v3.9.6.13)
# Bridges VS Code DAP requests to the InScript Debugger.
# Usage: python inscript.py --dap game.ins
# Protocol: DAP over stdin/stdout with Content-Length headers.

from __future__ import annotations
import json
import sys
import traceback
from typing import Any, Dict, Optional
from debugger import StepMode


def _send_dap(msg: dict):
    payload = json.dumps(msg)
    header = f"Content-Length: {len(payload)}\r\n\r\n"
    sys.stdout.write(header + payload)
    sys.stdout.flush()


def _read_dap() -> Optional[dict]:
    try:
        headers = {}
        while True:
            line = sys.stdin.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                break
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        length = int(headers.get("content-length", 0))
        if length == 0:
            return None
        body = sys.stdin.read(length)
        return json.loads(body)
    except Exception:
        return None


_seq = 0

def _next_seq() -> int:
    global _seq
    _seq += 1
    return _seq


class DAPServer:
    def __init__(self, interpreter, debugger, source_path: str):
        self.interp = interpreter
        self.debugger = debugger
        self.source_path = source_path
        self._running = False
        self._pause_info: dict = {}
        debugger.set_dap_callback(self._on_pause)

    # ── Entry point ──────────────────────────────────────────────

    def run(self):
        self._running = True
        _send_dap({"type": "event", "event": "initialized", "seq": _next_seq()})
        while self._running:
            msg = _read_dap()
            if msg is None:
                break
            self._dispatch(msg)

    # ── Dispatch ─────────────────────────────────────────────────

    def _dispatch(self, msg: dict):
        if msg.get("type") != "request":
            return
        cmd = msg.get("command", "")
        args = msg.get("arguments", {})
        req_seq = msg.get("seq", 0)
        handler = getattr(self, f"_on_{cmd}", None)
        if handler:
            try:
                handler(req_seq, args)
            except Exception as e:
                self._error(req_seq, cmd, str(e))
        else:
            self._error(req_seq, cmd, f"Unsupported command: {cmd}")

    def _resp(self, req_seq: int, command: str, body: dict = None):
        msg = {"type": "response", "request_seq": req_seq, "success": True, "command": command, "seq": _next_seq()}
        if body:
            msg["body"] = body
        _send_dap(msg)

    def _error(self, req_seq: int, command: str, message: str):
        _send_dap({"type": "response", "request_seq": req_seq, "success": False,
                   "command": command, "message": message, "seq": _next_seq()})

    # ── DAP request handlers ─────────────────────────────────────

    def _on_initialize(self, seq: int, args: dict):
        self._resp(seq, "initialize", {
            "supportsConfigurationDoneRequest": True,
            "supportsFunctionBreakpoints": False,
            "supportsConditionalBreakpoints": True,
            "supportsHitConditionalBreakpoints": True,
            "supportsEvaluateForHovers": True,
            "supportsStepBack": False,
            "supportsSetVariable": True,
            "supportsRestartFrame": False,
            "supportsGotoTargetsRequest": False,
            "supportsCompletionsRequest": False,
            "supportsModulesRequest": False,
            "exceptionBreakpointFilters": [],
        })

    def _on_launch(self, seq: int, args: dict):
        self._resp(seq, "launch")

    def _on_configurationDone(self, seq: int, args: dict):
        self._resp(seq, "configurationDone")
        self._start_debugging()

    def _on_setBreakpoints(self, seq: int, args: dict):
        file_path = args.get("source", {}).get("path", self.source_path)
        bps = args.get("breakpoints", [])
        # Clear existing breakpoints for this file
        existing = self.debugger.bp_manager.list()
        for bp in existing:
            if bp.filename == file_path:
                self.debugger.bp_manager.remove(bp.filename, bp.line)
        result_bps = []
        for bp in bps:
            line = bp.get("line", 0)
            cond = bp.get("condition")
            hit_cond = bp.get("hitCondition")
            self.debugger.bp_manager.add(file_path, line, condition=cond, hit_condition=hit_cond)
            result_bps.append({"verified": True, "line": line})
        self._resp(seq, "setBreakpoints", {"breakpoints": result_bps})

    def _on_setExceptionBreakpoints(self, seq: int, args: dict):
        self._resp(seq, "setExceptionBreakpoints")

    def _on_continue(self, seq: int, args: dict):
        self.debugger.step_mode = StepMode.CONTINUE
        self._resp(seq, "continue", {"allThreadsContinued": True})

    def _on_next(self, seq: int, args: dict):
        self.debugger.set_step_mode(StepMode.STEP_OVER, self.interp._call_depth)
        self._resp(seq, "next")

    def _on_stepIn(self, seq: int, args: dict):
        self.debugger.set_step_mode(StepMode.STEP_INTO, self.interp._call_depth)
        self._resp(seq, "stepIn")

    def _on_stepOut(self, seq: int, args: dict):
        self.debugger.set_step_mode(StepMode.STEP_OUT, self.interp._call_depth)
        self._resp(seq, "stepOut")

    def _on_pause(self, seq: int, args: dict):
        self._resp(seq, "pause")

    def _on_stackTrace(self, seq: int, args: dict):
        stack_str = self.interp._call_stack.format()
        frames = []
        if stack_str:
            for i, line_text in enumerate(stack_str.strip().split("\n")):
                frames.append({
                    "id": i,
                    "name": line_text.split(",")[0].strip() if "," in line_text else f"frame_{i}",
                    "source": {"path": self.source_path},
                    "line": 1,
                    "column": 1,
                })
        self._resp(seq, "stackTrace", {"stackFrames": frames, "totalFrames": len(frames)})

    def _on_scopes(self, seq: int, args: dict):
        self._resp(seq, "scopes", {
            "scopes": [
                {"name": "Locals", "variablesReference": 1, "expensive": False},
                {"name": "Globals", "variablesReference": 2, "expensive": False},
            ]
        })

    def _on_variables(self, seq: int, args: dict):
        ref = args.get("variablesReference", 0)
        vars_list = []
        if ref == 1:
            env = self.interp._env
            items = {}
            while env:
                for k, v in env._store.items():
                    if k not in items and not k.startswith("_"):
                        items[k] = v
                env = env.parent if env is not self.interp._globals else None
            for k, v in sorted(items.items()):
                vars_list.append({"name": k, "value": str(v), "variablesReference": 0})
        elif ref == 2:
            env = self.interp._globals
            for k, v in sorted(env._store.items()):
                if not k.startswith("_"):
                    vars_list.append({"name": k, "value": str(v), "variablesReference": 0})
        self._resp(seq, "variables", {"variables": vars_list})

    def _on_evaluate(self, seq: int, args: dict):
        expr_str = args.get("expression", "")
        try:
            from parser import parse
            from ast_nodes import ExprStmt
            prog = parse(expr_str, "<dap-eval>")
            if prog.body and isinstance(prog.body[0], ExprStmt):
                val = self.interp.visit(prog.body[0].expr)
                from interpreter import _inscript_str
                self._resp(seq, "evaluate", {"result": _inscript_str(val), "variablesReference": 0})
                return
        except Exception as e:
            self._resp(seq, "evaluate", {"result": f"Error: {e}", "variablesReference": 0})
            return
        self._resp(seq, "evaluate", {"result": "", "variablesReference": 0})

    def _on_disconnect(self, seq: int, args: dict):
        self._running = False
        self.debugger.step_mode = StepMode.CONTINUE
        self._resp(seq, "disconnect")

    # ── Pause callback (called by debugger on breakpoint hit) ─

    def _on_pause(self, debugger):
        info = debugger._dap_pause_info
        _send_dap({
            "type": "event", "event": "stopped",
            "seq": _next_seq(),
            "body": {
                "reason": info.get("reason", "breakpoint"),
                "threadId": 1,
                "description": info.get("text", ""),
            }
        })
        # Enter DAP command loop — wait for continue/next/step/etc.
        while self._running:
            msg = _read_dap()
            if msg is None:
                break
            self._dispatch(msg)
            if self.debugger.step_mode != StepMode.CONTINUE or not self._running:
                break

    # ── Bootstrap ────────────────────────────────────────────────

    def _start_debugging(self):
        from parser import parse, tokenize

        source_text = open(self.source_path, "r", encoding="utf-8").read()
        tokens = tokenize(source_text, self.source_path)
        program = parse(source_text, self.source_path)
        self.interp.source_lines = source_text.splitlines()
        try:
            self.interp.run(program)
        except SystemExit:
            pass
        except Exception:
            _send_dap({
                "type": "event", "event": "output",
                "seq": _next_seq(),
                "body": {"category": "stderr", "output": f"{traceback.format_exc()}\n"}
            })
        _send_dap({
            "type": "event", "event": "terminated",
            "seq": _next_seq(),
            "body": {}
        })
        self._running = False
