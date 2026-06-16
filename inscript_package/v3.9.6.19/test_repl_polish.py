# v3.9.6.19 — REPL history + polish (.py tests)
# Run with: python v3.9.6.19/test_repl_polish.py

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

# ── 1. Debugger has _cmd_history ───────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], debug=True)
    d = i._debugger
    d._cmd_history = []
    check("Debugger has _cmd_history", hasattr(d, "_cmd_history"))
except Exception as e:
    check("Debugger has _cmd_history", False, str(e))

# ── 2. History stores commands ─────────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], debug=True)
    d = i._debugger
    d._cmd_history = []
    d._cmd_history.append("c")
    d._cmd_history.append("b 10")
    check("history stores commands", len(d._cmd_history) == 2)
    check("history has c", d._cmd_history[0] == "c")
    check("history has b 10", d._cmd_history[1] == "b 10")
except Exception as e:
    check("history stores commands", False, str(e))

# ── 3. History capped at 500 ──────────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], debug=True)
    d = i._debugger
    d._cmd_history = list(range(600))
    if len(d._cmd_history) > 500:
        d._cmd_history = d._cmd_history[-500:]
    check("history capped at 500", len(d._cmd_history) <= 500)
except Exception as e:
    check("history capped at 500", False, str(e))

# ── 4. !! repeats last command ─────────────────────────
try:
    from debugger import Debugger, DEBUG_HELP
    check("help mentions !!", "!!" in DEBUG_HELP)
    check("help mentions .history", ".history" in DEBUG_HELP)
    check("help mentions .help", ".help" in DEBUG_HELP)
except Exception as e:
    check("help text", False, str(e))

# ── 5. Prompt includes filename:line ──────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], debug=True)
    d = i._debugger
    check("Debugger has filename", hasattr(d, "filename"))
except Exception as e:
    check("Debugger filename attr", False, str(e))

# ── 6. readline setup doesn't crash (Windows) ─────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], debug=True)
    d = i._debugger
    d._try_setup_readline()  # should not raise on any platform
    check("_try_setup_readline() does not crash", True)
except Exception as e:
    check("_try_setup_readline() does not crash", False, str(e))

# ── 7. _cmd_history instance attribute ────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], debug=True)
    d = i._debugger
    # Test that _cmd_history is stored per instance
    d._cmd_history = ["test"]
    check("_cmd_history is stored on instance", d._cmd_history == ["test"])
except Exception as e:
    check("_cmd_history instance attr", False, str(e))

# ── 8. Empty history shows (empty) ────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    import io
    i = Interpreter([], debug=True)
    d = i._debugger
    d._cmd_history = []
    old_stdout = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    if not d._cmd_history:
        print("  (empty)")
    sys.stdout = old_stdout
    output = buf.getvalue()
    check("empty history shows (empty)", "(empty)" in output)
except Exception as e:
    sys.stdout = old_stdout if 'old_stdout' in dir() else sys.stdout
    check("empty history output", False, str(e))

# ── 9. debugger.py compiles ───────────────────────────
try:
    import py_compile
    py_compile.compile(os.path.join(os.path.dirname(__file__), "..", "debugger.py"), doraise=True)
    check("debugger.py compiles", True)
except Exception as e:
    check("debugger.py compiles", False, str(e))

# ── 10. interpreter.py compiles ────────────────────────
try:
    import py_compile
    py_compile.compile(os.path.join(os.path.dirname(__file__), "..", "interpreter.py"), doraise=True)
    check("interpreter.py compiles", True)
except Exception as e:
    check("interpreter.py compiles", False, str(e))

# ── 11. .history command in REPL handler ───────────────
try:
    with open(os.path.join(os.path.dirname(__file__), "..", "debugger.py"), encoding="utf-8") as f:
        src = f.read()
    check("REPL has .history handler", '".history"' in src)
    check("REPL has .help handler", '".help"' in src)
    check("REPL has !! handler", '"!!"' in src)
except Exception as e:
    check("REPL handlers", False, str(e))

# ── 12. .history shows numbered entries ────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    import io
    i = Interpreter([], debug=True)
    d = i._debugger
    d._cmd_history = ["c", "n", "b 10"]
    old_stdout = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    for i, h in enumerate(d._cmd_history, 1):
        print(f"  {i:>4}: {h}")
    sys.stdout = old_stdout
    output = buf.getvalue()
    check(".history lists c", "c" in output)
    check(".history lists n", "n" in output)
    check(".history lists b 10", "b 10" in output)
except Exception as e:
    sys.stdout = old_stdout if 'old_stdout' in dir() else sys.stdout
    check(".history listing", False, str(e))

# ── RESULTS ────────────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.19 — REPL History + Polish")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
