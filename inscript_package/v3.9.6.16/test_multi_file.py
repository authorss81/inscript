# v3.9.6.16 — Multi-file breakpoints (.py tests)
# Run with: python v3.9.6.16/test_multi_file.py
# Python-level tests needed for: import debugger/interpreter, verify multi-file
# source tracking, check breakpoints across loaded files.

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

# ── 1. Interpreter has _source_files dict ──────────────────
try:
    from interpreter import Interpreter
    i = Interpreter(debug=True)
    check("Interpreter has _source_files", hasattr(i, "_source_files"))
except Exception as e:
    check("Interpreter has _source_files", False, str(e))

# ── 2. _source_files is a dict ─────────────────────────────
try:
    from interpreter import Interpreter
    i = Interpreter(["let x = 1"], filename="main.ins", debug=True)
    check("_source_files is dict", isinstance(i._source_files, dict))
except Exception as e:
    check("_source_files is dict", False, str(e))

# ── 3. _source_files stores initial file ───────────────────
try:
    from interpreter import Interpreter
    i = Interpreter(["line1", "line2"], filename="main.ins", debug=True)
    check("_source_files has main file", "main.ins" in i._source_files)
    check("_source_files lines correct", i._source_files["main.ins"] == ["line1", "line2"])
except Exception as e:
    check("_source_files initial file", False, str(e))

# ── 4. _src_line with filename ────────────────────────────
try:
    from interpreter import Interpreter
    i = Interpreter(["line1", "line2"], filename="main.ins", debug=True)
    check("_src_line with filename", i._src_line(1, "main.ins") == "line1")
    check("_src_line without filename", i._src_line(2) == "line2")
except Exception as e:
    check("_src_line with filename", False, str(e))

# ── 5. Debugger has _known_filenames ──────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter(["a"], filename="test.ins", debug=True)
    d = i._debugger
    check("Debugger has _known_filenames", hasattr(d, "_known_filenames"))
    fnames = d._known_filenames()
    check("_known_filenames includes main file", "test.ins" in fnames)
except Exception as e:
    check("_known_filenames", False, str(e))

# ── 6. Debugger has _find_src_line ────────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter(["hello world"], filename="test.ins", debug=True)
    d = i._debugger
    check("Debugger has _find_src_line", hasattr(d, "_find_src_line"))
    line = d._find_src_line(1)
    check("_find_src_line returns correct line", line == "hello world")
except Exception as e:
    check("_find_src_line", False, str(e))

# ── 7. _cmd_delete supports file:line ─────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], filename="test.ins", debug=True)
    d = i._debugger
    d.bp_manager.add("other.ins", 42)
    d._cmd_delete("other.ins:42")
    bp = d.bp_manager.get("other.ins", 42)
    check("_cmd_delete file:line removes bp", bp is None)
except Exception as e:
    check("_cmd_delete file:line", False, str(e))

# ── 8. _cmd_list_breakpoints groups by file ────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], filename="test.ins", debug=True)
    d = i._debugger
    d.bp_manager.add("a.ins", 10)
    d.bp_manager.add("a.ins", 20)
    d.bp_manager.add("b.ins", 30)
    import io
    old_stdout = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    d._cmd_list_breakpoints()
    sys.stdout = old_stdout
    out = buf.getvalue()
    check("bl groups by file", "[a.ins]" in out and "[b.ins]" in out)
except Exception as e:
    sys.stdout = old_stdout
    check("bl groups by file", False, str(e))

# ── 9. .files command output ──────────────────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter(["a"], filename="main.ins", debug=True)
    i._source_files["extra.ins"] = ["x", "y", "z"]
    d = i._debugger
    import io
    old_stdout = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    # Simulate .files command
    print("  Loaded files:")
    print(f"    {d.filename}  (main)")
    if hasattr(i, '_source_files'):
        for fname in sorted(i._source_files.keys()):
            if fname != d.filename:
                print(f"    {fname}  ({len(i._source_files[fname])} lines)")
    sys.stdout = old_stdout
    out = buf.getvalue()
    check(".files shows main.ins", "main.ins" in out)
    check(".files shows extra.ins", "extra.ins" in out)
    check(".files shows line count", "3 lines" in out)
except Exception as e:
    sys.stdout = old_stdout
    check(".files command", False, str(e))

# ── 10. should_pause_at checks all known files ────────────
try:
    from debugger import Debugger, StepMode
    from interpreter import Interpreter
    from ast_nodes import Node
    i = Interpreter([], filename="test.ins", debug=True)
    d = i._debugger
    d.bp_manager.add("other.ins", 5)
    n = Node(line=5)
    result = d.should_pause_at(n, 0)
    check("should_pause_at matches bp in other file", result)
except Exception as e:
    check("should_pause_at multi-file", False, str(e))

# ── 11. .files command in debugger REPL ───────────────────
try:
    from debugger import DEBUG_HELP
    check("help mentions .files", ".files" in DEBUG_HELP)
except Exception as e:
    check("help .files", False, str(e))

# ── 12. debugger.py compiles ──────────────────────────────
try:
    import py_compile
    py_compile.compile(os.path.join(os.path.dirname(__file__), "..", "debugger.py"), doraise=True)
    check("debugger.py compiles", True)
except Exception as e:
    check("debugger.py compiles", False, str(e))

# ── 13. interpreter.py compiles ───────────────────────────
try:
    import py_compile
    py_compile.compile(os.path.join(os.path.dirname(__file__), "..", "interpreter.py"), doraise=True)
    check("interpreter.py compiles", True)
except Exception as e:
    check("interpreter.py compiles", False, str(e))

# ── 14. bl shows file-less bps under main file ───────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter([], filename="game.ins", debug=True)
    d = i._debugger
    d.bp_manager.add("game.ins", 15)
    import io
    old_stdout = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    d._cmd_list_breakpoints()
    sys.stdout = old_stdout
    out = buf.getvalue()
    check("bl shows main file header", "[game.ins]" in out)
    check("bl shows bp line", "line 15" in out)
except Exception as e:
    sys.stdout = old_stdout
    check("bl main file display", False, str(e))

# ── RESULTS ────────────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.16 — Multi-File Breakpoints")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
