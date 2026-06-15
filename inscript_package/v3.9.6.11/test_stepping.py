#!/usr/bin/env python3
import sys; sys.stdout.reconfigure(encoding='utf-8')
"""v3.9.6.11 — Debugger: step-over, step-into, step-out, continue.

Tests:
  1. Step-over pauses at next statement (same depth)
  2. Step-into pauses immediately on next node
  3. Step-out pauses after returning from function
  4. Continue runs until next breakpoint
  5. Step mode state machine: transitions to CONTINUE after pause
  6. should_pause_at with depth tracking
  7. Integration: breakpoint + continue resumes
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0

# ── Test 1: Step-over pauses at same depth ──────────────────────────────
try:
    from debugger import Debugger, StepMode, BreakpointManager
    from interpreter import Interpreter
    i = Interpreter(debug=True, filename="test.ins")
    d = i._debugger
    # Setup: step-over at depth 2, should pause when depth <= 2
    d.set_step_mode(StepMode.STEP_OVER, 2)
    # Depth 1 < 2, so should pause
    assert d.should_pause_at(type('_F', (), {'line': 1, 'col': 0})(), 1) == True
    assert d.step_mode == StepMode.CONTINUE  # resets after pause
    print(f"  ✅ Step-over pauses at same or shallower depth")
    PASS += 1
except Exception as e:
    print(f"  ❌ Step-over: {e}")
    import traceback; traceback.print_exc()
    FAIL += 1

# ── Test 2: Step-into pauses immediately ────────────────────────────────
try:
    from debugger import StepMode
    from interpreter import Interpreter
    i = Interpreter(debug=True)
    d = i._debugger
    d.set_step_mode(StepMode.STEP_INTO, 0)
    assert d.should_pause_at(type('_F', (), {'line': 1, 'col': 0})(), 3) == True
    assert d.step_mode == StepMode.CONTINUE
    print(f"  ✅ Step-into pauses on next node regardless of depth")
    PASS += 1
except Exception as e:
    print(f"  ❌ Step-into: {e}")
    FAIL += 1

# ── Test 3: Step-out pauses when depth decreases ────────────────────────
try:
    from debugger import StepMode
    from interpreter import Interpreter
    i = Interpreter(debug=True)
    d = i._debugger
    d.set_step_mode(StepMode.STEP_OUT, 5)
    # Depth 4 < 5, so we have returned from the function
    assert d.should_pause_at(type('_F', (), {'line': 1, 'col': 0})(), 4) == True
    assert d.step_mode == StepMode.CONTINUE
    # If depth >= step_cmd_depth, should NOT pause
    d.set_step_mode(StepMode.STEP_OUT, 3)
    assert d.should_pause_at(type('_F', (), {'line': 1, 'col': 0})(), 3) == False
    assert d.should_pause_at(type('_F', (), {'line': 1, 'col': 0})(), 4) == False
    print(f"  ✅ Step-out pauses when call depth decreases")
    PASS += 1
except Exception as e:
    print(f"  ❌ Step-out: {e}")
    FAIL += 1

# ── Test 4: Continue runs until next breakpoint ─────────────────────────
try:
    from debugger import StepMode
    from interpreter import Interpreter
    i = Interpreter(debug=True, filename="test.ins")
    d = i._debugger
    d.set_step_mode(StepMode.CONTINUE)
    # No breakpoint set — should NOT pause
    assert d.should_pause_at(type('_F', (), {'line': 5, 'col': 0})(), 0) == False
    # Set breakpoint at line 10
    d.bp_manager.add("test.ins", 10)
    assert d.should_pause_at(type('_F', (), {'line': 10, 'col': 0})(), 0) == True
    assert d.step_mode == StepMode.CONTINUE  # stays in CONTINUE mode
    print(f"  ✅ Continue mode: breakpoints still trigger")
    PASS += 1
except Exception as e:
    print(f"  ❌ Continue: {e}")
    FAIL += 1

# ── Test 5: Step mode state machine ─────────────────────────────────────
try:
    from debugger import StepMode
    from interpreter import Interpreter
    i = Interpreter(debug=True)
    d = i._debugger
    # Each step mode should auto-reset to CONTINUE after pause
    for mode in (StepMode.STEP_OVER, StepMode.STEP_INTO, StepMode.STEP_OUT):
        d.set_step_mode(mode, 5)
        d.should_pause_at(type('_F', (), {'line': 1, 'col': 0})(), 4)
        assert d.step_mode == StepMode.CONTINUE, f"{mode} didn't reset"
    print(f"  ✅ All step modes reset to CONTINUE after pause")
    PASS += 1
except Exception as e:
    print(f"  ❌ Step mode state machine: {e}")
    FAIL += 1

# ── Test 6: Depth-aware pausing ─────────────────────────────────────────
try:
    from debugger import StepMode
    from interpreter import Interpreter
    i = Interpreter(debug=True)
    d = i._debugger
    d.set_step_mode(StepMode.STEP_OVER, 3)
    # Depth 3 (same as threshold): should pause
    assert d.should_pause_at(type('_F', (), {'line': 1, 'col': 0})(), 3) == True
    d.set_step_mode(StepMode.STEP_OVER, 3)
    # Depth 4 (deeper): should NOT pause
    assert d.should_pause_at(type('_F', (), {'line': 1, 'col': 0})(), 4) == False
    # Depth 2 (shallower after returning): should pause
    d.set_step_mode(StepMode.STEP_OVER, 3)
    assert d.should_pause_at(type('_F', (), {'line': 1, 'col': 0})(), 2) == True
    print(f"  ✅ Depth-aware pausing works correctly")
    PASS += 1
except Exception as e:
    print(f"  ❌ Depth-aware pausing: {e}")
    FAIL += 1

# ── Test 7: Integration — interpreter visits with breakpoint ────────────
try:
    from interpreter import Interpreter
    from parser import parse
    source = """
let x = 10
let y = 20
let z = x + y
"""
    i = Interpreter(debug=True, source_lines=source.splitlines(), filename="<script>")
    # Set breakpoint at line 3 (the second let statement)
    i._debugger.bp_manager.add("<script>", 3)
    # Simulate the visit_Program flow (but don't use real debug REPL)
    prog = parse(source)
    # Test that should_pause_at returns True for statements at breakpoint lines
    from ast_nodes import VarDecl
    for stmt in prog.body:
        line = getattr(stmt, 'line', 0)
        if line == 3:
            assert i._debugger.should_pause_at(stmt, 0) == True
        elif line > 0:
            assert i._debugger.should_pause_at(stmt, 0) == False
    print(f"  ✅ Breakpoints trigger on source statements")
    PASS += 1
except Exception as e:
    print(f"  ❌ Integration test: {e}")
    import traceback; traceback.print_exc()
    FAIL += 1

# ── Summary ──────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"v3.9.6.11: {PASS} passed, {FAIL} failed")
if FAIL:
    sys.exit(1)
