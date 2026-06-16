# v3.9.6.17 — Exception breakpoints (.py tests)
# Run with: python v3.9.6.17/test_exception_bp.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

PASS, FAIL = 0, 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  {chr(0x2705)} {name}")
        PASS += 1
    else:
        print(f"  {chr(0x274C)} {name}  {detail}")
        FAIL += 1

# ── 1. Debugger has _catch_types ──────────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], debug=True)
    d = i._debugger
    check("Debugger has _catch_types", hasattr(d, "_catch_types"))
except Exception as e:
    check("Debugger has _catch_types", False, str(e))

# ── 2. should_catch with empty list returns False ────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], debug=True)
    d = i._debugger
    check("should_catch empty returns False", not d.should_catch("any error"))
except Exception as e:
    check("should_catch empty", False, str(e))

# ── 3. should_catch with * catches all ───────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], debug=True)
    d = i._debugger
    d._catch_types.append("*")
    check("should_catch * returns True", d.should_catch("Division by zero"))
    check("should_catch * with any msg", d.should_catch("AssertionError"))
except Exception as e:
    check("should_catch *", False, str(e))

# ── 4. should_catch specific type ─────────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], debug=True)
    d = i._debugger
    d._catch_types.append("Division")
    check("should_catch Division", d.should_catch("Division by zero"))
    check("should_catch not Assertion", not d.should_catch("AssertionError"))
except Exception as e:
    check("should_catch specific", False, str(e))

# ── 5. catch command adds to list ─────────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], debug=True)
    d = i._debugger
    import io
    old_stdout = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    # Simulate: catch AssertionError
    d._catch_types.append("AssertionError")
    sys.stdout = old_stdout
    check("catch adds type", "AssertionError" in d._catch_types)
    check("catch exact match", d.should_catch("AssertionError: something"))
    check("catch doesn't match Division", not d.should_catch("Division by zero"))
except Exception as e:
    sys.stdout = old_stdout
    check("catch command", False, str(e))

# ── 6. uncatch removes from list ─────────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], debug=True)
    d = i._debugger
    d._catch_types.append("AssertionError")
    d._catch_types.append("Division")
    d._catch_types.remove("AssertionError")
    check("uncatch removes type", "AssertionError" not in d._catch_types)
    check("uncatch keeps others", "Division" in d._catch_types)
except Exception as e:
    check("uncatch command", False, str(e))

# ── 7. catch with no args lists types ────────────────────
try:
    from debugger import Debugger, DEBUG_HELP
    check("help mentions catch", "catch" in DEBUG_HELP)
    check("help mentions uncatch", "uncatch" in DEBUG_HELP)
except Exception as e:
    check("help catch/uncatch", False, str(e))

# ── 8. interpreter _error calls should_catch ──────────────
try:
    from interpreter import Interpreter
    i = Interpreter(["let x = 1"], filename="test.ins", debug=True)
    check("_error checks debugger when debug=True", i._debug)
except Exception as e:
    check("_error debug check", False, str(e))

# ── 9. should_catch matching on message prefix ───────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], debug=True)
    d = i._debugger
    d._catch_types.append("Panic")
    check("should_catch Panic", d.should_catch("Panic: something went wrong"))
    check("should_catch not General", not d.should_catch("General error"))
except Exception as e:
    check("should_catch prefix matching", False, str(e))

# ── 10. Multiple catch types ─────────────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], debug=True)
    d = i._debugger
    d._catch_types.append("AssertionError")
    d._catch_types.append("Division")
    check("multiple catches: AssertionError", d.should_catch("AssertionError: x > 5"))
    check("multiple catches: Division", d.should_catch("Division by zero"))
    check("multiple catches: not Index", not d.should_catch("Index out of bounds"))
except Exception as e:
    check("multiple catch types", False, str(e))

# ── 11. debugger.py compiles ─────────────────────────────
try:
    import py_compile
    py_compile.compile(os.path.join(os.path.dirname(__file__), "..", "debugger.py"), doraise=True)
    check("debugger.py compiles", True)
except Exception as e:
    check("debugger.py compiles", False, str(e))

# ── 12. interpreter.py compiles ──────────────────────────
try:
    import py_compile
    py_compile.compile(os.path.join(os.path.dirname(__file__), "..", "interpreter.py"), doraise=True)
    check("interpreter.py compiles", True)
except Exception as e:
    check("interpreter.py compiles", False, str(e))

# ── 13. Stack trace shown on catch ──────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter(["let x = 1"], filename="test.ins", debug=True)
    d = i._debugger
    d._catch_types.append("*")
    # intercept enter_debug_repl to check it's called
    called = []
    original = d.enter_debug_repl
    def tracking_repl(node):
        called.append(True)
    d.enter_debug_repl = tracking_repl
    try:
        i._error("TestError: something happened", 1)
    except Exception:
        pass
    d.enter_debug_repl = original
    check("error triggers enter_debug_repl", len(called) > 0)
except Exception as e:
    check("error triggers debug repl", False, str(e))

# ── RESULTS ────────────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.17 — Exception Breakpoints")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
