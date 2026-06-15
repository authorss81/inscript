#!/usr/bin/env python3
import sys; sys.stdout.reconfigure(encoding='utf-8')
"""v3.9.6.12 — Debugger: variable inspection.

Tests:
  1. .locals lists local variables in current scope
  2. .globals lists global variables
  3. .stack prints call stack with line numbers
  4. .watch adds and lists watch expressions
  5. .set modifies variable in environment
  6. Expression evaluation in debug REPL context
  7. _eval_expr evaluates arbitrary expressions
  8. _cmd_set modifies live variables
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0

# ── Test 1: .locals lists local variables ────────────────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    from environment import Environment
    i = Interpreter(debug=True)
    d = Debugger(i, "test.ins")
    d.interp = i
    # Push some variables into environment
    i._env.define("my_var", 42)
    i._env.define("another", "hello")
    # Test _cmd_locals (prints to stdout)
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        d._cmd_locals()
    out = buf.getvalue()
    assert "my_var" in out
    assert "42" in out
    assert "another" in out
    assert "hello" in out
    print(f"  ✅ .locals shows local variables")
    PASS += 1
except Exception as e:
    print(f"  ❌ .locals: {e}")
    import traceback; traceback.print_exc()
    FAIL += 1

# ── Test 2: .globals lists global variables ─────────────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter(debug=True)
    d = Debugger(i, "test.ins")
    d.interp = i
    # Register some globals
    i._globals.define("global_x", 100)
    i._globals.define("global_y", 200)
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        d._cmd_globals()
    out = buf.getvalue()
    assert "global_x" in out
    assert "global_y" in out
    print(f"  ✅ .globals shows global variables")
    PASS += 1
except Exception as e:
    print(f"  ❌ .globals: {e}")
    import traceback; traceback.print_exc()
    FAIL += 1

# ── Test 3: .stack prints call stack ────────────────────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    from errors import InScriptCallStack
    i = Interpreter(debug=True, source_lines=["line1", "line2", "line3"])
    d = Debugger(i, "test.ins")
    d.interp = i
    # Simulate a call stack
    i._call_stack.push("outer_fn", 1)
    i._call_stack.push("inner_fn", 2)
    i._call_stack.update_top_line(3)
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        d._cmd_stack()
    out = buf.getvalue()
    assert "outer_fn" in out
    assert "inner_fn" in out
    assert "<script>" in out
    print(f"  ✅ .stack shows call stack with line numbers")
    PASS += 1
except Exception as e:
    print(f"  ❌ .stack: {e}")
    import traceback; traceback.print_exc()
    FAIL += 1

# ── Test 4: .watch adds watch expressions ───────────────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter(debug=True)
    d = Debugger(i, "test.ins")
    d.interp = i
    # Add watch expressions via _cmd_watch
    d._cmd_watch("x + 1")
    d._cmd_watch("y * 2")
    assert len(d._watch_exprs) == 2
    assert "x + 1" in d._watch_exprs
    assert "y * 2" in d._watch_exprs
    # List them
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        d._cmd_watch("")
    out = buf.getvalue()
    assert "x + 1" in out
    assert "y * 2" in out
    print(f"  ✅ .watch adds and lists watch expressions")
    PASS += 1
except Exception as e:
    print(f"  ❌ .watch: {e}")
    FAIL += 1

# ── Test 5: .set modifies variable in environment ────────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter(debug=True)
    d = Debugger(i, "test.ins")
    d.interp = i
    # Define a variable
    i._env.define("my_val", 10)
    assert i._env.get("my_val", 0) == 10
    # Modify via _cmd_set
    d._cmd_set("my_val = 99")
    assert i._env.get("my_val", 0) == 99
    print(f"  ✅ .set modifies variable in environment")
    PASS += 1
except Exception as e:
    print(f"  ❌ .set: {e}")
    import traceback; traceback.print_exc()
    FAIL += 1

# ── Test 6: Expression evaluation at breakpoint ─────────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter(debug=True)
    d = Debugger(i, "test.ins")
    d.interp = i
    i._env.define("a", 3)
    i._env.define("b", 4)
    # _eval_expr parses and evaluates expressions in current env
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        d._eval_expr("a + b")
    out = buf.getvalue()
    assert "7" in out, f"Expected 7, got {out!r}"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        d._eval_expr('"hello" + " world"')
    out = buf.getvalue()
    assert "hello world" in out
    print(f"  ✅ Expression evaluation at breakpoint")
    PASS += 1
except Exception as e:
    print(f"  ❌ Expression eval: {e}")
    import traceback; traceback.print_exc()
    FAIL += 1

# ── Test 7: Debug REPL help banner ─────────────────────────────────────
try:
    from debugger import DEBUG_BANNER, DEBUG_HELP
    assert "Debugger commands" in DEBUG_HELP
    assert "c, continue" in DEBUG_HELP
    assert "n, next" in DEBUG_HELP
    assert "s, step" in DEBUG_HELP
    assert ".locals" in DEBUG_HELP
    assert ".stack" in DEBUG_HELP
    assert ".watch" in DEBUG_HELP
    assert ".set" in DEBUG_HELP
    print(f"  ✅ Debugger help banner has all commands")
    PASS += 1
except Exception as e:
    print(f"  ❌ Debugger help: {e}")
    FAIL += 1

# ── Test 8: Breakpoint hit_count tracking ───────────────────────────────
try:
    from debugger import BreakpointManager
    bm = BreakpointManager()
    bp = bm.add("game.ins", 5)
    bm.should_break("game.ins", 5)
    bm.should_break("game.ins", 5)
    assert bp.hit_count == 2
    bp2 = bm.add("game.ins", 5)  # reusing key
    assert bp2 is bp  # same object
    print(f"  ✅ Breakpoint hit_count tracking")
    PASS += 1
except Exception as e:
    print(f"  ❌ hit_count: {e}")
    FAIL += 1

# ── Summary ──────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"v3.9.6.12: {PASS} passed, {FAIL} failed")
if FAIL:
    sys.exit(1)
