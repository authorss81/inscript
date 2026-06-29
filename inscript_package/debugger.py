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

from ast_nodes import Node, Program, FunctionDecl, LambdaExpr, BlockStmt, StructDecl
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
# Type display + pretty-print (v3.9.6.15)
# ─────────────────────────────────────────────────────────────────────────────

def _inscript_type_str(val) -> str:
    """Return InScript type name for a value."""
    if val is None:                      return "nil"
    if isinstance(val, bool):            return "bool"
    if isinstance(val, int):             return "int"
    if isinstance(val, float):           return "float"
    if isinstance(val, str):             return "string"
    if isinstance(val, list):            return "array"
    if isinstance(val, dict):
        if "_variant" in val:
            return f"enum({val.get('_enum', '?')}::{val.get('_variant', '?')})"
        if "_ok" in val or "_err" in val:
            return "result"
        return "dict"
    if hasattr(val, 'struct_name') and hasattr(val, 'fields'):
        return val.struct_name
    if callable(val):
        if hasattr(val, 'name') and val.name:
            return f"fn({val.name})"
        return "fn"
    if hasattr(val, 'start') and hasattr(val, 'end'):
        return "range"
    return type(val).__name__


def _pretty_format(val, indent: int = 0, max_depth: int = 3) -> str:
    """Pretty-print an InScript value with indentation."""
    prefix = "  " * indent
    next_prefix = "  " * (indent + 1)
    from interpreter import _inscript_str, _inscript_repr

    if val is None or isinstance(val, (bool, int, float)):
        return _inscript_str(val)
    if isinstance(val, str):
        return _inscript_str(val)

    if isinstance(val, list):
        if indent >= max_depth:
            return f"[...] ({len(val)} items)"
        if not val:
            return "[]"
        items = [f"{next_prefix}{_pretty_format(v, indent + 1, max_depth)}," for v in val]
        return "[\n" + "\n".join(items) + f"\n{prefix}]"

    if isinstance(val, dict):
        if indent >= max_depth:
            n = len([k for k in val if not str(k).startswith("_")])
            return f"{{...}} ({n} fields)"
        if not val:
            return "{}"
        items = []
        for k, v in val.items():
            if str(k).startswith("_"):
                continue
            k_str = f'"{k}"' if isinstance(k, str) else _inscript_str(k)
            items.append(f"{next_prefix}{k_str}: {_pretty_format(v, indent + 1, max_depth)},")
        if not items:
            return "{}"
        return "{\n" + "\n".join(items) + f"\n{prefix}}}"

    if hasattr(val, 'struct_name') and hasattr(val, 'fields'):
        if indent >= max_depth:
            return f"{val.struct_name}{{...}}"
        data = {k: v for k, v in val.fields.items()
                if not (callable(v) or (hasattr(v, 'is_native') or hasattr(v, 'params')))}
        if not data:
            return f"{val.struct_name}{{}}"
        items = [f"{next_prefix}{k}: {_pretty_format(v, indent + 1, max_depth)}," for k, v in data.items()]
        return f"{val.struct_name}{{\n" + "\n".join(items) + f"\n{prefix}}}"

    return _inscript_str(val)


def _format_value(val) -> str:
    """Return type: pretty_value string for display."""
    t = _inscript_type_str(val)
    p = _pretty_format(val)
    return f"({t}) {p}"


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
  d <file>:<line>    — Delete breakpoint at specific file
  bl                 — List all breakpoints (grouped by file)
  bc                 — Clear all breakpoints
  .locals            — List all local variables with types
  .globals           — List global variables with types
  .stack             — Print call stack with line numbers
  .watch [<expr>]    — Add/evaluate watch expression (auto-evaluated at breaks)
  .watch del <idx>   — Remove watch expression by index
  .type <expr>       — Show type and value of expression
  .set <var>=<val>   — Modify a variable in current scope
  .files             — List all loaded source files
  watchvar [<name>]  — List / watch variable for changes
  unwatch <name>     — Stop watching a variable
  catch [<type>]     — List / add exception breakpoint (catch * for all)
  uncatch <type>     — Remove exception breakpoint
  !!                 — Repeat last command
  .history           — Show command history
  q, quit            — Quit debugger and terminate execution
  ?, .help           — Print this help
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
        self._catch_types: List[str] = []   # v3.9.6.17: exception breakpoints
        self._watch_vars: Dict[str, Any] = {}  # v3.9.6.18: data breakpoints (name -> value)
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

    def _try_setup_readline(self):
        """v3.9.6.19: enable readline history and tab completion (Unix/macOS)."""
        import sys as _sys
        if _sys.platform == "win32":
            return  # readline not available on Windows
        try:
            import readline as _rl
            _rl.set_history_length(500)
            for h in self._cmd_history:
                _rl.add_history(h)
            def _completer(text, state):
                commands = ["c", "continue", "n", "next", "s", "step", "finish",
                            "b", "d", "bl", "breakpoints", ".files", "bc",
                            ".locals", ".globals", ".stack", ".watch",
                            ".set", ".history", "!!", ".help",
                            "watchvar", "unwatch", "catch", "uncatch",
                            ".type"]
                options = [cmd for cmd in commands if cmd.startswith(text)]
                return options[state] if state < len(options) else None
            _rl.set_completer(_completer)
            _rl.parse_and_bind("tab: complete")
        except (ImportError, AttributeError):
            pass

    def _known_filenames(self) -> list:
        """Return all filenames that have breakpoints or are known source files."""
        seen = {self.filename}
        if hasattr(self.interp, '_source_files'):
            seen.update(self.interp._source_files.keys())
        # Add all filenames from breakpoints
        for bp in self.bp_manager.list():
            seen.add(bp.filename)
        return list(seen)

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
            # Check breakpoints across all known files (v3.9.6.16 multi-file)
            for fname in self._known_filenames():
                if self.bp_manager.should_break(
                    fname, line,
                    env_get_fn=lambda expr: self.interp.visit(expr)
                ):
                    return True

        return False

    # ── debug REPL ────────────────────────────────────────────────────────

    def _find_src_line(self, line: int) -> str:
        """Look up source line from any loaded file."""
        src = self.interp._src_line(line, self.filename)
        if src:
            return src
        if hasattr(self.interp, '_source_files'):
            for fname, lines in self.interp._source_files.items():
                if 0 < line <= len(lines):
                    return lines[line - 1]
        return ""

    def enter_debug_repl(self, node: Node):
        line = getattr(node, 'line', 0)
        src = self._find_src_line(line)
        print(f"\n[debug] Break at {self.filename}:{line}")
        if src:
            print(f"  {src}")

        # Show auto-evaluated watches (v3.9.6.15)
        if self._watch_exprs:
            print("  Watches:")
            for expr in self._watch_exprs:
                try:
                    self._show_watch_value(expr)
                except Exception:
                    print(f"    {expr} = (error)")

        if self._dap_callback:
            self._dap_pause("breakpoint", line, src or "")
            return

        # v3.9.6.19: try readline for tab completion & history
        self._cmd_history: list = getattr(self, '_cmd_history', [])
        self._try_setup_readline()

        while True:
            try:
                prompt = f"(debug:{self.filename}:{line}) "
                raw = input(prompt)
                if raw:
                    self._cmd_history.append(raw)
                    if len(self._cmd_history) > 500:
                        self._cmd_history = self._cmd_history[-500:]
            except (EOFError, KeyboardInterrupt):
                print()
                self.step_mode = StepMode.CONTINUE
                return

            cmd = raw.strip()

            if not cmd:
                continue

            # v3.9.6.19: !! repeats last command
            if cmd == "!!":
                if len(self._cmd_history) >= 2:
                    cmd = self._cmd_history[-2].strip()
                    print(f"  {cmd}")
                else:
                    print("  No previous command.")
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

            elif verb == ".files":
                print("  Loaded files:")
                print(f"    {self.filename}  (main)")
                if hasattr(self.interp, '_source_files'):
                    for fname in sorted(self.interp._source_files.keys()):
                        if fname != self.filename:
                            print(f"    {fname}  ({len(self.interp._source_files[fname])} lines)")

            elif verb == "catch":
                if not arg:
                    if not self._catch_types:
                        print("  No catchpoints set.")
                    else:
                        print("  Catchpoints:")
                        for ct in self._catch_types:
                            print(f"    {ct}")
                else:
                    self._catch_types.append(arg.strip())
                    print(f"  Will catch: {arg.strip()}")

            elif verb == "uncatch":
                if not arg:
                    print("  Usage: uncatch <error-type>")
                else:
                    arg = arg.strip()
                    if arg in self._catch_types:
                        self._catch_types.remove(arg)
                        print(f"  No longer catching: {arg}")
                    else:
                        print(f"  No catchpoint for: {arg}")

            elif verb == "watchvar":
                if not arg:
                    if not self._watch_vars:
                        print("  No watched variables.")
                    else:
                        print("  Watched variables:")
                        for vn, vv in self._watch_vars.items():
                            print(f"    {vn} = {_format_value(vv)}")
                else:
                    vname = arg.strip()
                    # try to look up current value
                    try:
                        val = self.interp._env_get(vname, 0)
                    except Exception:
                        val = None
                    self._watch_vars[vname] = val
                    print(f"  Watching '{vname}' for changes (current: {_format_value(val)})")

            elif verb == "unwatch":
                if not arg:
                    print("  Usage: unwatch <var-name>")
                else:
                    vname = arg.strip()
                    if vname in self._watch_vars:
                        del self._watch_vars[vname]
                        print(f"  Stopped watching '{vname}'")
                    else:
                        print(f"  Not watching '{vname}'")

            elif verb == ".history":
                if not self._cmd_history:
                    print("  (empty)")
                else:
                    for i, h in enumerate(self._cmd_history, 1):
                        print(f"  {i:>4}: {h}")

            elif verb == ".help":
                print(DEBUG_HELP)

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
                    if not self._watch_exprs:
                        print("  (no watch expressions)")
                    else:
                        for i, expr in enumerate(self._watch_exprs):
                            try:
                                self._show_watch_value(expr)
                            except Exception as e:
                                print(f"  [{i}] {expr} = (error: {e})")

            elif verb == ".set":
                self._cmd_set(arg)

            elif verb in ("q", "quit"):
                print("[debug] Terminating execution.")
                sys.exit(0)

            elif verb in ("?", "help"):
                print(DEBUG_HELP)

            elif verb == ".type":
                if arg:
                    try:
                        from parser import parse
                        from ast_nodes import ExprStmt
                        prog = parse(arg, "<debug>")
                        if prog.body and isinstance(prog.body[0], ExprStmt):
                            val = self.interp.visit(prog.body[0].expr)
                            print(f"  type: {_inscript_type_str(val)}")
                            print(f"  value: {_pretty_format(val)}")
                    except Exception as e:
                        print(f"  Error: {e}")
                else:
                    print("  Usage: .type <expr>")

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
            print("  Usage: d <line>  or  d <file>:<line>")
            return
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
        if self.bp_manager.remove(fname, line):
            print(f"  Breakpoint removed at {fname}:{line}")
        else:
            print(f"  No breakpoint at {fname}:{line}")

    def _cmd_list_breakpoints(self):
        bps = self.bp_manager.list()
        if not bps:
            print("  No breakpoints set.")
            return
        print("  Breakpoints:")
        current_file = None
        for bp in bps:
            if bp.filename != current_file:
                print(f"    [{bp.filename}]")
                current_file = bp.filename
            cond = f" if {bp.condition}" if bp.condition else ""
            hit = f" hit {bp.hit_condition}" if bp.hit_condition else ""
            status = "enabled" if bp.enabled else "disabled"
            print(f"      line {bp.line}{cond}{hit}  [{status}, hit {bp.hit_count}]")

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
        for k in sorted(items.keys()):
            try:
                vs = _format_value(items[k])
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
        for k in sorted(items.keys()):
            try:
                vs = _format_value(items[k])
            except Exception:
                vs = repr(items[k])
            print(f"  {k} = {vs}")

    def _cmd_stack(self):
        stack = self.interp._call_stack.format()
        if stack:
            print(stack)
        else:
            print("  (call stack is empty)")

    def should_catch(self, error_msg: str) -> bool:
        """Check if an error matches any active catchpoint."""
        if not self._catch_types:
            return False
        for ctype in self._catch_types:
            if ctype == "*":
                return True
            if ctype in error_msg:
                return True
        return False

    def _check_watchvar(self, name: str, new_value: Any, node) -> bool:
        """Check if name is being watched; if so, pause and show change."""
        if name not in self._watch_vars:
            return False
        old_val = self._watch_vars[name]
        self._watch_vars[name] = new_value
        print(f"\n  ⚡ Data breakpoint: '{name}' changed")
        print(f"      old: {_format_value(old_val)}")
        print(f"      new: {_format_value(new_value)}")
        print(f"      at:  {self.filename}:{node.line}")
        self.enter_debug_repl(node)
        return True

    def _show_watch_value(self, expr: str):
        """Evaluate and display a single watch expression."""
        from parser import parse
        from ast_nodes import ExprStmt
        prog = parse(expr, "<watch>")
        if prog.body and isinstance(prog.body[0], ExprStmt):
            val = self.interp.visit(prog.body[0].expr)
            print(f"    {expr} = {_format_value(val)}")

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
                print(f"  → {_format_value(val)}")
                return
        except Exception as e:
            print(f"  Error: {e}")
