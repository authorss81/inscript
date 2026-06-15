#!/usr/bin/env python3
import sys; sys.stdout.reconfigure(encoding='utf-8')
"""v3.9.6.10 — Debugger: breakpoint infrastructure.

Tests:
  1. dbg() builtin prints value + location
  2. BreakpointManager add/remove/list/clear
  3. Breakpoint with condition (should_break)
  4. Debugger constructor + StepMode enum
  5. Interpreter --debug flag creates debugger
  6. Debugger integration pauses at breakpoints
  7. --debug CLI flag is recognized
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0

# ── Test 1: dbg() builtin ─────────────────────────────────────────────────
try:
    from interpreter import Interpreter
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        i = Interpreter()
        i.execute("dbg(42)")
        i.execute('fn test() { dbg("hello") }; test()')
    out = buf.getvalue()
    if "[dbg]" in out and "42" in out and "hello" in out:
        print(f"  ✅ dbg() prints value + location")
        PASS += 1
    else:
        print(f"  ❌ dbg() output unexpected: {out!r}")
        FAIL += 1
except Exception as e:
    print(f"  ❌ dbg() test raised: {e}")
    import traceback; traceback.print_exc()
    FAIL += 1

# ── Test 2: BreakpointManager add/remove/list/clear ───────────────────────
try:
    from debugger import BreakpointManager
    bm = BreakpointManager()
    bp1 = bm.add("test.ins", 10)
    bp2 = bm.add("test.ins", 20, condition="x > 5")
    assert bp1.line == 10
    assert bp2.condition == "x > 5"
    all_bps = bm.list()
    assert len(all_bps) == 2
    assert bm.remove("test.ins", 10) == True
    assert len(bm.list()) == 1
    assert bm.remove("test.ins", 10) == False
    bm.clear()
    assert len(bm.list()) == 0
    print(f"  ✅ BreakpointManager: add/remove/list/clear")
    PASS += 1
except Exception as e:
    print(f"  ❌ BreakpointManager test: {e}")
    FAIL += 1

# ── Test 3: Breakpoint should_break with condition ────────────────────────
try:
    from debugger import BreakpointManager
    bm = BreakpointManager()
    bm.add("test.ins", 15, condition="true")
    assert bm.should_break("test.ins", 15) == True
    bm.clear()
    bm.add("test.ins", 16)
    assert bm.should_break("test.ins", 16) == True
    assert bm.should_break("test.ins", 999) == False
    bp = bm.get("test.ins", 16)
    assert bp.hit_count == 1
    print(f"  ✅ should_break: basic + condition + hit_count")
    PASS += 1
except Exception as e:
    print(f"  ❌ should_break test: {e}")
    FAIL += 1

# ── Test 4: Debugger constructor and StepMode ────────────────────────────
try:
    from debugger import Debugger, StepMode
    from interpreter import Interpreter
    i = Interpreter()
    d = Debugger(i, "test.ins")
    assert d.filename == "test.ins"
    assert d.step_mode == StepMode.CONTINUE
    assert d.bp_manager is not None
    d.set_step_mode(StepMode.STEP_INTO)
    assert d.step_mode == StepMode.STEP_INTO
    print(f"  ✅ Debugger: constructor + StepMode")
    PASS += 1
except Exception as e:
    print(f"  ❌ Debugger constructor: {e}")
    FAIL += 1

# ── Test 5: Interpreter --debug flag ──────────────────────────────────────
try:
    i_debug = Interpreter(debug=True)
    assert i_debug._debug == True
    assert i_debug._debugger is not None
    i_nodebug = Interpreter(debug=False)
    assert i_nodebug._debug == False
    assert i_nodebug._debugger is None
    print(f"  ✅ Interpreter --debug flag creates debugger")
    PASS += 1
except Exception as e:
    print(f"  ❌ Interpreter --debug flag: {e}")
    FAIL += 1

# ── Test 6: Debugger integration pauses at breakpoints ──────────────────
try:
    from debugger import Debugger, BreakpointManager
    from interpreter import Interpreter
    from ast_nodes import Program, ExprStmt, IntLiteralExpr
    i = Interpreter(debug=True, filename="test.ins")
    d = i._debugger
    d.bp_manager.add("test.ins", 1)
    fake_stmt = type('_Fake', (), {'line': 1, 'col': 0})()
    # should_pause_at should return True for line 1
    assert d.should_pause_at(fake_stmt, 0) == True
    # should NOT pause at line 5 (no breakpoint)
    fake_stmt2 = type('_Fake', (), {'line': 5, 'col': 0})()
    assert d.should_pause_at(fake_stmt2, 0) == False
    print(f"  ✅ Debugger pauses at breakpoints")
    PASS += 1
except Exception as e:
    print(f"  ❌ Debugger pause test: {e}")
    import traceback; traceback.print_exc()
    FAIL += 1

# ── Test 7: Step mode transitions ──────────────────────────────────────
try:
    from debugger import StepMode
    from interpreter import Interpreter
    i = Interpreter(debug=True)
    d = i._debugger
    # StepOver: should pause if current_depth <= step_depth; resets to CONTINUE
    d.set_step_mode(StepMode.STEP_OVER, 5)
    assert d.should_pause_at(type('_F', (), {'line': 10, 'col': 0})(), 4) == True
    assert d.step_mode == StepMode.CONTINUE
    # After reset to CONTINUE, deeper calls don't pause (no breakpoint)
    assert d.should_pause_at(type('_F', (), {'line': 11, 'col': 0})(), 3) == False
    # StepOut: should pause if current_depth < step_depth
    d.set_step_mode(StepMode.STEP_OUT, 5)
    assert d.should_pause_at(type('_F', (), {'line': 12, 'col': 0})(), 4) == True
    assert d.step_mode == StepMode.CONTINUE
    # StepInto: always pause on next statement
    d.set_step_mode(StepMode.STEP_INTO, 0)
    assert d.should_pause_at(type('_F', (), {'line': 13, 'col': 0})(), 0) == True
    assert d.step_mode == StepMode.CONTINUE
    print(f"  ✅ Step mode transitions correct")
    PASS += 1
except Exception as e:
    print(f"  ❌ Step mode test: {e}")
    import traceback; traceback.print_exc()
    FAIL += 1

# ── Summary ──────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"v3.9.6.10: {PASS} passed, {FAIL} failed")
if FAIL:
    sys.exit(1)
