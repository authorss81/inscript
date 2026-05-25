#!/usr/bin/env python3
"""
inscript_dap.py — InScript Debug Adapter Protocol (DAP) server  v2.5.0
========================================================================
Implements a minimal DAP server over stdin/stdout.

Capabilities:
  • Launch (run a .ins file with debugging enabled)
  • Breakpoints (set/clear line breakpoints)
  • Step Over / Step Into / Step Out / Continue
  • Stack Frames (current call location)
  • Variables (local + global inspection)
  • Evaluate expression (hover eval in debugger)

Usage (VS Code launch.json):
  {
    "type": "inscript",
    "request": "launch",
    "program": "${file}"
  }

Or standalone:
  python inscript_dap.py --port 4711     # TCP mode
  python inscript_dap.py                  # stdio mode
"""

from __future__ import annotations
import sys, os, json, threading, time, socket
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# DAP Message framing  (Content-Length: N\r\n\r\n{json})
# ─────────────────────────────────────────────────────────────────────────────

def _read_msg(stream) -> Optional[dict]:
    """Read one DAP message from stream."""
    headers = {}
    while True:
        line = stream.readline()
        if not line:
            return None
        line = line.decode() if isinstance(line, bytes) else line
        line = line.rstrip("\r\n")
        if not line:
            break
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip()] = v.strip()
    length = int(headers.get("Content-Length", 0))
    if length == 0:
        return None
    body = stream.read(length)
    return json.loads(body.decode() if isinstance(body, bytes) else body)


def _write_msg(stream, msg: dict):
    """Write one DAP message to stream."""
    body = json.dumps(msg).encode()
    header = f"Content-Length: {len(body)}\r\n\r\n".encode()
    stream.write(header + body)
    stream.flush()


# ─────────────────────────────────────────────────────────────────────────────
# Debuggable Interpreter  (tree-walker with hooks)
# ─────────────────────────────────────────────────────────────────────────────

class DebugInterpreter:
    """
    Wraps the InScript tree-walker interpreter and adds debug hooks:
    - Breakpoints by line number
    - Step over / into / out
    - Variable inspection
    - Call-stack frames
    """

    def __init__(self, source: str, source_path: str):
        self.source      = source
        self.source_path = source_path
        self._breakpoints: set = set()   # set of line numbers (1-based)
        self._paused     = threading.Event()
        self._continue   = threading.Event()
        self._step_mode  = None          # None | 'over' | 'into' | 'out'
        self._stopped    = False
        self._stop_reason= "breakpoint"
        self._current_line = 0
        self._call_depth   = 0
        self._call_depth_at_step = 0
        self._frames: List[Dict] = []
        self._globals_snapshot: Dict = {}
        self._locals_snapshot:  Dict = {}
        self._thread: Optional[threading.Thread] = None
        self._done   = False
        self._output_lines: List[str] = []

    def set_breakpoints(self, lines: List[int]):
        self._breakpoints = set(lines)

    def _hook(self, line: int, interp):
        """Called before each statement execution."""
        self._current_line = line
        # Capture call stack
        self._frames = []
        for frame in reversed(interp._call_stack._frames
                              if hasattr(interp._call_stack, '_frames') else []):
            self._frames.append({
                "name":   getattr(frame, 'fn_name', '<script>'),
                "line":   getattr(frame, 'line', line),
                "source": self.source_path,
            })
        if not self._frames:
            self._frames = [{"name": "<script>", "line": line, "source": self.source_path}]

        # Capture variables
        try:
            self._locals_snapshot  = dict(interp._env._store) if hasattr(interp._env, '_store') else {}
            self._globals_snapshot = dict(interp._globals._store) if hasattr(interp, '_globals') else {}
        except Exception:
            pass

        should_pause = False
        if line in self._breakpoints:
            should_pause = True
            self._stop_reason = "breakpoint"
        elif self._step_mode == "over":
            if interp._call_depth <= self._call_depth_at_step:
                should_pause = True
                self._stop_reason = "step"
        elif self._step_mode == "into":
            should_pause = True
            self._stop_reason = "step"
        elif self._step_mode == "out":
            if interp._call_depth < self._call_depth_at_step:
                should_pause = True
                self._stop_reason = "step"

        if should_pause:
            self._step_mode = None
            self._stopped = True
            self._paused.set()
            self._continue.wait()
            self._continue.clear()
            self._stopped = False

    def _run_thread(self):
        """Execute the program in a background thread."""
        import io
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            from interpreter import Interpreter
            from parser      import parse

            program = parse(self.source)
            interp  = Interpreter(source_lines=self.source.splitlines())

            # Monkey-patch the visit method to inject our hook
            original_visit = interp.visit.__func__

            def hooked_visit(self_interp, node):
                line = getattr(node, 'line', 0)
                if line and line != self._current_line:
                    self._call_depth = self_interp._call_depth if hasattr(self_interp, '_call_depth') else 0
                    self._hook(line, self_interp)
                return original_visit(self_interp, node)

            import types
            interp.visit = types.MethodType(hooked_visit, interp)

            # Capture print output
            old_stdout = sys.stdout
            out_buf = io.StringIO()
            sys.stdout = out_buf
            interp.run(program)
            sys.stdout = old_stdout
            output = out_buf.getvalue()
            self._output_lines = output.splitlines()

        except Exception as e:
            sys.stdout = sys.__stdout__
            self._output_lines.append(f"[ERROR] {e}")
        finally:
            self._done = True
            self._paused.set()   # unblock any waiting pause

    def launch(self):
        """Start execution in background thread."""
        self._thread = threading.Thread(target=self._run_thread, daemon=True)
        self._thread.start()

    def wait_for_stop(self, timeout: float = 30.0) -> bool:
        """Block until paused at breakpoint/step or execution ends."""
        return self._paused.wait(timeout)

    def do_continue(self):
        self._step_mode = None
        self._paused.clear()
        self._continue.set()

    def do_step_over(self):
        self._step_mode = "over"
        self._call_depth_at_step = self._call_depth
        self._paused.clear()
        self._continue.set()

    def do_step_into(self):
        self._step_mode = "into"
        self._paused.clear()
        self._continue.set()

    def do_step_out(self):
        self._step_mode = "out"
        self._call_depth_at_step = self._call_depth
        self._paused.clear()
        self._continue.set()

    def get_stack_frames(self) -> List[Dict]:
        return self._frames or [{"name": "<script>", "line": self._current_line,
                                  "source": self.source_path}]

    def get_variables(self, scope: str = "locals") -> List[Dict]:
        store = self._locals_snapshot if scope == "locals" else self._globals_snapshot
        result = []
        for name, val in list(store.items())[:50]:  # cap at 50
            result.append({
                "name":  name,
                "value": _format_val(val),
                "type":  type(val).__name__,
            })
        return result


def _format_val(v) -> str:
    if v is None:       return "nil"
    if v is True:       return "true"
    if v is False:      return "false"
    if isinstance(v, list): return f"[{len(v)} items]"
    if isinstance(v, dict): return f"dict({len(v)} keys)"
    return str(v)[:80]


# ─────────────────────────────────────────────────────────────────────────────
# DAP Server
# ─────────────────────────────────────────────────────────────────────────────

class DAPServer:
    def __init__(self, reader, writer):
        self._r   = reader
        self._w   = writer
        self._seq = 0
        self._dbg: Optional[DebugInterpreter] = None
        self._source_path = ""

    def _send(self, msg: dict):
        self._seq += 1
        msg.setdefault("seq", self._seq)
        _write_msg(self._w, msg)

    def _respond(self, req: dict, body: dict = None, success: bool = True):
        self._send({
            "type":        "response",
            "request_seq": req["seq"],
            "command":     req["command"],
            "success":     success,
            "body":        body or {},
        })

    def _event(self, event: str, body: dict = None):
        self._send({
            "type":  "event",
            "event": event,
            "body":  body or {},
        })

    def run(self):
        """Main message loop."""
        while True:
            msg = _read_msg(self._r)
            if msg is None:
                break
            if msg.get("type") == "request":
                self._handle(msg)

    def _handle(self, req: dict):
        cmd = req.get("command", "")
        args = req.get("arguments", {}) or {}

        if cmd == "initialize":
            self._respond(req, {
                "supportsConfigurationDoneRequest": True,
                "supportsFunctionBreakpoints":      False,
                "supportsConditionalBreakpoints":   False,
                "supportsEvaluateForHovers":        True,
                "supportsStepBack":                 False,
                "supportsRestartRequest":           False,
            })
            self._event("initialized")

        elif cmd == "launch":
            self._source_path = args.get("program", "")
            try:
                with open(self._source_path, encoding="utf-8") as f:
                    source = f.read()
                self._dbg = DebugInterpreter(source, self._source_path)
            except Exception as e:
                self._respond(req, {"message": str(e)}, success=False)
                return
            self._respond(req)

        elif cmd == "configurationDone":
            self._respond(req)
            # Start execution now
            if self._dbg:
                self._dbg.launch()
                stopped = self._dbg.wait_for_stop(timeout=30)
                if stopped and self._dbg._stopped:
                    self._event("stopped", {
                        "reason": self._dbg._stop_reason,
                        "threadId": 1,
                    })
                elif self._dbg._done:
                    self._send_output()
                    self._event("terminated")
                    self._event("exited", {"exitCode": 0})

        elif cmd == "setBreakpoints":
            src   = args.get("source", {})
            bps   = args.get("breakpoints", [])
            lines = [b["line"] for b in bps]
            if self._dbg:
                self._dbg.set_breakpoints(lines)
            self._respond(req, {
                "breakpoints": [{"verified": True, "line": l} for l in lines]
            })

        elif cmd == "threads":
            self._respond(req, {"threads": [{"id": 1, "name": "main"}]})

        elif cmd == "stackTrace":
            frames = self._dbg.get_stack_frames() if self._dbg else []
            dap_frames = [
                {
                    "id": i,
                    "name": f["name"],
                    "line": f["line"],
                    "column": 0,
                    "source": {"name": os.path.basename(f["source"]),
                               "path": f["source"]},
                }
                for i, f in enumerate(frames)
            ]
            self._respond(req, {"stackFrames": dap_frames, "totalFrames": len(dap_frames)})

        elif cmd == "scopes":
            self._respond(req, {"scopes": [
                {"name": "Locals",  "variablesReference": 1, "expensive": False},
                {"name": "Globals", "variablesReference": 2, "expensive": False},
            ]})

        elif cmd == "variables":
            ref   = args.get("variablesReference", 1)
            scope = "locals" if ref == 1 else "globals"
            vars_ = self._dbg.get_variables(scope) if self._dbg else []
            self._respond(req, {"variables": [
                {"name": v["name"], "value": v["value"],
                 "type": v["type"], "variablesReference": 0}
                for v in vars_
            ]})

        elif cmd == "evaluate":
            expr   = args.get("expression", "")
            result = self._evaluate(expr)
            self._respond(req, {"result": result, "variablesReference": 0})

        elif cmd == "continue":
            if self._dbg:
                self._dbg.do_continue()
                self._respond(req, {"allThreadsContinued": True})
                stopped = self._dbg.wait_for_stop()
                if stopped and self._dbg._stopped:
                    self._event("stopped", {"reason": self._dbg._stop_reason, "threadId": 1})
                elif self._dbg._done:
                    self._send_output()
                    self._event("terminated")
                    self._event("exited", {"exitCode": 0})
            else:
                self._respond(req)

        elif cmd == "next":       # step over
            self._step_and_respond(req, "over")
        elif cmd == "stepIn":     # step into
            self._step_and_respond(req, "into")
        elif cmd == "stepOut":    # step out
            self._step_and_respond(req, "out")

        elif cmd == "disconnect":
            self._respond(req)
            sys.exit(0)

        else:
            self._respond(req)   # unknown command — respond with empty success

    def _step_and_respond(self, req: dict, mode: str):
        self._respond(req)
        if not self._dbg:
            return
        {"over": self._dbg.do_step_over,
         "into": self._dbg.do_step_into,
         "out":  self._dbg.do_step_out}[mode]()
        stopped = self._dbg.wait_for_stop()
        if stopped and self._dbg._stopped:
            self._event("stopped", {"reason": "step", "threadId": 1})
        elif self._dbg._done:
            self._send_output()
            self._event("terminated")
            self._event("exited", {"exitCode": 0})

    def _evaluate(self, expr: str) -> str:
        """Evaluate an expression in the current stopped context."""
        if not self._dbg:
            return "no active session"
        # Simple: look up in locals/globals
        for store in (self._dbg._locals_snapshot, self._dbg._globals_snapshot):
            if expr in store:
                return _format_val(store[expr])
        # Try evaluating as arithmetic via interpreter
        try:
            from interpreter import Interpreter
            from parser      import parse
            i = Interpreter()
            i.run(parse(f"let __eval__ = {expr}"))
            return _format_val(i._env.get("__eval__"))
        except Exception as e:
            return f"Error: {e}"

    def _send_output(self):
        if not self._dbg:
            return
        for line in self._dbg._output_lines:
            self._event("output", {"category": "stdout", "output": line + "\n"})


def main():
    import argparse
    parser = argparse.ArgumentParser(description="InScript DAP Server v2.5.0")
    parser.add_argument("--port", type=int, default=0,
                        help="TCP port (0 = stdio mode)")
    args = parser.parse_args()

    if args.port:
        # TCP mode
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", args.port))
        sock.listen(1)
        print(f"InScript DAP server listening on port {args.port}", file=sys.stderr)
        conn, _ = sock.accept()
        rfile = conn.makefile("rb")
        wfile = conn.makefile("wb")
        DAPServer(rfile, wfile).run()
        conn.close()
    else:
        # stdio mode (used by VS Code)
        sys.stdin  = sys.stdin.buffer  if hasattr(sys.stdin,  "buffer") else sys.stdin
        sys.stdout = sys.stdout.buffer if hasattr(sys.stdout, "buffer") else sys.stdout
        DAPServer(sys.stdin, sys.stdout).run()

if __name__ == "__main__":
    main()
