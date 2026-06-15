# -*- coding: utf-8 -*-
# debugger.py — InScript Step Debugger (v3.9.6.10–v3.9.6.12)
#
# Provides breakpoint infrastructure, step-over/into/out, variable inspection,
# call-stack display, and expression evaluation at breakpoints.
#
# Integrated into `Interpreter` via the `visit()` dispatch hook.

from __future__ import annotations
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum, auto

from ast_nodes import Node, Program, FunctionDecl, LambdaExpr, BlockStmt
from errors import InScriptRuntimeError


# ─────────────────────────────────────────────────────────────────────────────
# Breakpoint
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Breakpoint:
    filename: str
    line:   int
    condition: Optional[str] = None   # e.g. "x > 5"
    enabled: bool = True
    hit_count: int = 0
    hit_condition: Optional[str] = None  # e.g. ">= 5" (break every Nth hit)


# ─────────────────────────────────────────────────────────────────────────────
# BreakpointManager
# ─────────────────────────────────────────────────────────────────────────────

class BreakpointManager:
    def __init__(self):
        self._bps: Dict[Tuple[str, int], Breakpoint] = {}

    def add(self, filename: str, line: int, condition: str = None, hit_condition: str = None) -> Breakpoint:
        key = (filename, line)
        if key in self._bps:
            bp = self._bps[key]
            bp.condition = condition
            bp.hit_condition = hit_condition
            bp.enabled = True
            return bp
        bp = Breakpoint(filename=filename, line=line, condition=condition, hit_condition=hit_condition)
        self._bps[key] = bp
        return bp

    def remove(self, filename: str, line: int) -> bool:
        key = (filename, line)
        if key in self._bps:
            del self._bps[key]
            return True
        return False

    def list(self) -> List[Breakpoint]:
        return sorted(self._bps.values(), key=lambda bp: (bp.filename, bp.line))

    def clear(self):
        self._bps.clear()

    def get(self, filename: str, line: int) -> Optional[Breakpoint]:
        return self._bps.get((filename, line))

    def should_break(self, filename: str, line: int, env_get_fn=None) -> bool:
        bp = self._bps.get((filename, line))
        if bp is None or not bp.enabled:
            return False
        bp.hit_count += 1
        if bp.hit_condition:
            try:
                parts = bp.hit_condition.split(None, 1)
                if len(parts) == 2:
                    op, val_str = parts
                    val = int(val_str)
                    if op == "==": hit_ok = bp.hit_count == val
                    elif op == ">=": hit_ok = bp.hit_count >= val
                    elif op == "<=": hit_ok = bp.hit_count <= val
                    elif op == ">": hit_ok = bp.hit_count > val
                    elif op == "<": hit_ok = bp.hit_count < val
                    elif op == "%": hit_ok = bp.hit_count % val == 0
                    else: hit_ok = True
                else:
                    hit_ok = True
            except (ValueError, IndexError):
                hit_ok = True
            if not hit_ok:
                return False
        if bp.condition and env_get_fn:
            try:
                from parser import parse
                from ast_nodes import ExprStmt
                prog = parse(bp.condition, "<bp-condition>")
                if prog.body and isinstance(prog.body[0], ExprStmt):
                    val = env_get_fn(prog.body[0].expr)
                    return bool(val)
            except Exception:
                return True
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Step mode
# ─────────────────────────────────────────────────────────────────────────────

class StepMode(Enum):
    CONTINUE = auto()
    STEP_OVER = auto()
    STEP_INTO = auto()
    STEP_OUT = auto()


# ─────────────────────────────────────────────────────────────────────────────
# Debugger
# ─────────────────────────────────────────────────────────────────────────────

DEBUG_BANNER = """
[InScript Debugger] — Type ? for help
"""

DEBUG_HELP = """
Debugger commands:
  c, continue        — Resume execution until next breakpoint
  n, next            — Step over to next line (skip into calls)
  s, step            — Step into function call
  finish             — Step out of current function
  b <line>           — Set breakpoint at line N
  b <line> if <expr> — Conditional breakpoint (e.g. b 10 if x > 5)
  b <line> hit <op N>— Hit-count breakpoint (e.g. b 10 hit >= 5)
  b <file>:<line>    — Set breakpoint at specific file:line
  d <line>           — Delete breakpoint at current file, line N
  bl                 — List all breakpoints
  bc                 — Clear all breakpoints
  .locals            — List all local variables in current scope
  .stack             — Print call stack with line numbers
  .watch <expr>      — Evaluate an expression in current context
  .set <var>=<val>   — Modify a variable in current scope
  .globals           — List global variables
  q, quit            — Quit debugger and terminate execution
  ?                  — Print this help
"""


class Debugger:
    def __init__(self, interp, filename: str = "<script>"):
        self.interp = interp
        self.filename = filename
        self.bp_manager = BreakpointManager()
        self.step_mode: StepMode = StepMode.CONTINUE
        self._step_depth: int = 0
        self._step_cmd_depth: int = 0
        self._paused: bool = False
        self._watch_exprs: List[str] = []
        self._dap_callback = None  # called instead of debug REPL on pause
        self._dap_pause_info: dict = {}

    def set_dap_callback(self, cb):
        self._dap_callback = cb

    def _dap_pause(self, reason: str, line: int, text: str = ""):
        self._dap_pause_info = {"reason": reason, "line": line, "text": text}
        if self._dap_callback:
            self._dap_callback(self)

    # ── stepping ──────────────────────────────────────────────────────────

    def set_step_mode(self, mode: StepMode, current_depth: int = 0):
        self.step_mode = mode
        self._step_cmd_depth = current_depth

    def should_pause_at(self, node: Node, current_depth: int) -> bool:
        line = getattr(node, 'line', 0)
        if not line:
            return False

        if self.step_mode == StepMode.STEP_INTO:
            self.step_mode = StepMode.CONTINUE
            return True

        if self.step_mode == StepMode.STEP_OVER:
            if current_depth <= self._step_cmd_depth:
                self.step_mode = StepMode.CONTINUE
                return True
            return False

        if self.step_mode == StepMode.STEP_OUT:
            if current_depth < self._step_cmd_depth:
                self.step_mode = StepMode.CONTINUE
                return True
            return False

        if self.step_mode == StepMode.CONTINUE:
            if self.bp_manager.should_break(
                self.filename, line,
                env_get_fn=lambda expr: self.interp.visit(expr)
            ):
                return True

        return False

    # ── debug REPL ────────────────────────────────────────────────────────

    def enter_debug_repl(self, node: Node):
        line = getattr(node, 'line', 0)
        src = self.interp._src_line(line)
        print(f"\n[debug] Break at {self.filename}:{line}")
        if src:
            print(f"  {src}")

        if self._dap_callback:
            self._dap_pause("breakpoint", line, src or "")
            return

        while True:
            try:
                cmd = input("(debug) ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                self.step_mode = StepMode.CONTINUE
                return

            if not cmd:
                continue

            parts = cmd.split(None, 1)
            verb = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if verb in ("c", "continue"):
                self.step_mode = StepMode.CONTINUE
                return

            elif verb in ("n", "next"):
                self.set_step_mode(StepMode.STEP_OVER, self.interp._call_depth)
                return

            elif verb in ("s", "step"):
                self.set_step_mode(StepMode.STEP_INTO, self.interp._call_depth)
                return

            elif verb == "finish":
                self.set_step_mode(StepMode.STEP_OUT, self.interp._call_depth)
                return

            elif verb == "b":
                self._cmd_break(arg)

            elif verb == "d":
                self._cmd_delete(arg)

            elif verb in ("bl", "breakpoints"):
                self._cmd_list_breakpoints()

            elif verb == "bc":
                self.bp_manager.clear()
                print("[debug] All breakpoints cleared.")

            elif verb == ".locals":
                self._cmd_locals()

            elif verb == ".globals":
                self._cmd_globals()

            elif verb == ".stack":
                self._cmd_stack()

            elif verb == ".watch":
                if arg:
                    self._cmd_watch(arg)
                else:
                    for i, expr in enumerate(self._watch_exprs):
                        print(f"  {i}: {expr}")

            elif verb == ".set":
                self._cmd_set(arg)

            elif verb in ("q", "quit"):
                print("[debug] Terminating execution.")
                sys.exit(0)

            elif verb in ("?", "help"):
                print(DEBUG_HELP)

            else:
                try:
                    self._eval_expr(cmd)
                except Exception as e:
                    print(f"  Error: {e}")

    def _cmd_break(self, arg: str):
        if not arg:
            print("  Usage: b <line> [if <cond>] [hit <op> <n>]")
            print("  Examples:")
            print("    b 10              — break at line 10")
            print("    b 10 if x > 5     — conditional break")
            print("    b 10 hit >= 5     — break every 5th hit")
            print("    b 10 hit % 3      — break every 3rd hit")
            return
        condition = None
        hit_condition = None
        if " if " in arg:
            arg, _, cond = arg.partition(" if ")
            condition = cond.strip()
        if " hit " in arg:
            parts = arg.split(" hit ", 1)
            arg = parts[0].strip()
            hit_condition = parts[1].strip()
        if ":" in arg:
            fname, line_str = arg.rsplit(":", 1)
            try:
                line = int(line_str)
            except ValueError:
                print(f"  Invalid line: {line_str}")
                return
        else:
            fname = self.filename
            try:
                line = int(arg)
            except ValueError:
                print(f"  Invalid line: {arg}")
                return
        bp = self.bp_manager.add(fname, line, condition=condition, hit_condition=hit_condition)
        extra = ""
        if condition:
            extra += f" if {condition}"
        if hit_condition:
            extra += f" (hit {hit_condition})"
        print(f"  Breakpoint set at {fname}:{line}{extra}")

    def _cmd_delete(self, arg: str):
        if not arg:
            print("  Usage: d <line>")
            return
        try:
            line = int(arg)
        except ValueError:
            print(f"  Invalid line: {arg}")
            return
        if self.bp_manager.remove(self.filename, line):
            print(f"  Breakpoint removed at {self.filename}:{line}")
        else:
            print(f"  No breakpoint at {self.filename}:{line}")

    def _cmd_list_breakpoints(self):
        bps = self.bp_manager.list()
        if not bps:
            print("  No breakpoints set.")
            return
        print("  Breakpoints:")
        for bp in bps:
            cond = f" if {bp.condition}" if bp.condition else ""
            hit = f" hit {bp.hit_condition}" if bp.hit_condition else ""
            status = "enabled" if bp.enabled else "disabled"
            print(f"    {bp.filename}:{bp.line}{cond}{hit}  [{status}, hit {bp.hit_count}]")

    def _cmd_locals(self):
        env = self.interp._env
        items = {}
        while env:
            for k, v in env._store.items():
                if k not in items and not k.startswith("_"):
                    items[k] = v
            env = env.parent if env is not self.interp._globals else None
        if not items:
            print("  (no local variables)")
            return
        from interpreter import _inscript_str
        for k in sorted(items.keys()):
            try:
                vs = _inscript_str(items[k])
            except Exception:
                vs = repr(items[k])
            print(f"  {k} = {vs}")

    def _cmd_globals(self):
        env = self.interp._globals
        items = {k: v for k, v in env._store.items()
                 if not k.startswith("_")}
        if not items:
            print("  (no global variables)")
            return
        from interpreter import _inscript_str
        for k in sorted(items.keys())[:80]:
            try:
                vs = _inscript_str(items[k])
            except Exception:
                vs = repr(items[k])
            print(f"  {k} = {vs}")

    def _cmd_stack(self):
        stack = self.interp._call_stack.format()
        if stack:
            print(stack)
        else:
            print("  (call stack is empty)")

    def _cmd_watch(self, arg: str):
        arg = arg.strip()
        if not arg:
            for i, expr in enumerate(self._watch_exprs):
                print(f"  [{i}] {expr}")
            return
        if arg.startswith("del"):
            parts = arg.split()
            if len(parts) == 2:
                try:
                    idx = int(parts[1])
                    if 0 <= idx < len(self._watch_exprs):
                        removed = self._watch_exprs.pop(idx)
                        print(f"  Removed watch: {removed}")
                    else:
                        print(f"  Invalid index: {idx}")
                except ValueError:
                    print(f"  Invalid index: {parts[1]}")
            return
        self._watch_exprs.append(arg)
        print(f"  Watch added: {arg}")

    def _cmd_set(self, arg: str):
        if "=" not in arg:
            print("  Usage: .set <var>=<value>")
            return
        name, _, raw_val = arg.partition("=")
        name = name.strip()
        raw_val = raw_val.strip()
        if not name:
            print("  Invalid variable name.")
            return
        try:
            from parser import parse
            from ast_nodes import ExprStmt
            prog = parse(raw_val, "<set-value>")
            if prog.body and isinstance(prog.body[0], ExprStmt):
                val = self.interp.visit(prog.body[0].expr)
                self.interp._env.set(name, val)
                print(f"  {name} = {val!r}")
        except Exception as e:
            print(f"  Error: {e}")

    def _eval_expr(self, expr_str: str):
        try:
            from parser import parse
            from ast_nodes import ExprStmt
            prog = parse(expr_str, "<debug>")
            if prog.body and isinstance(prog.body[0], ExprStmt):
                val = self.interp.visit(prog.body[0].expr)
                from interpreter import _inscript_str
                print(f"  → {_inscript_str(val)}")
                return
        except Exception as e:
            print(f"  Error: {e}")
