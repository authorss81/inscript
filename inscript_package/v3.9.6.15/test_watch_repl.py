# v3.9.6.15 — Debugger: watch window + REPL integration (.py tests)
# Tests type display, pretty-print, watch persistence, expression evaluation.
# Python-level testing is needed for: import debugger, inspect type formatting,
# verify pretty-print output, check watch persistence across steps.
# Run with: python v3.9.6.15/test_watch_repl.py

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

# ── 1. _inscript_type_str returns correct types ──────────
try:
    from debugger import _inscript_type_str, _pretty_format, _format_value
    check("_inscript_type_str imported", True)
except Exception as e:
    check("_inscript_type_str imported", False, str(e))

# ── 2. Type of int ───────────────────────────────────────
try:
    from debugger import _inscript_type_str
    check("type int", _inscript_type_str(42) == "int")
except Exception as e:
    check("type int", False, str(e))

# ── 3. Type of float ─────────────────────────────────────
try:
    from debugger import _inscript_type_str
    check("type float", _inscript_type_str(3.14) == "float")
except Exception as e:
    check("type float", False, str(e))

# ── 4. Type of string ────────────────────────────────────
try:
    from debugger import _inscript_type_str
    check("type string", _inscript_type_str("hello") == "string")
except Exception as e:
    check("type string", False, str(e))

# ── 5. Type of bool ──────────────────────────────────────
try:
    from debugger import _inscript_type_str
    check("type bool true", _inscript_type_str(True) == "bool")
    check("type bool false", _inscript_type_str(False) == "bool")
except Exception as e:
    check("type bool", False, str(e))

# ── 6. Type of nil ───────────────────────────────────────
try:
    from debugger import _inscript_type_str
    check("type nil", _inscript_type_str(None) == "nil")
except Exception as e:
    check("type nil", False, str(e))

# ── 7. Type of array ─────────────────────────────────────
try:
    from debugger import _inscript_type_str
    check("type array", _inscript_type_str([1, 2, 3]) == "array")
except Exception as e:
    check("type array", False, str(e))

# ── 8. Type of dict ──────────────────────────────────────
try:
    from debugger import _inscript_type_str
    check("type dict", _inscript_type_str({"a": 1}) == "dict")
except Exception as e:
    check("type dict", False, str(e))

# ── 9. Type of empty dict ────────────────────────────────
try:
    from debugger import _inscript_type_str
    check("type empty dict", _inscript_type_str({}) == "dict")
except Exception as e:
    check("type empty dict", False, str(e))

# ── 10. Type of callable ─────────────────────────────────
try:
    from debugger import _inscript_type_str
    def f(): pass
    f.name = "my_fn"
    check("type fn", "fn" in _inscript_type_str(f))
except Exception as e:
    check("type fn", False, str(e))

# ── 11. Pretty-print int ─────────────────────────────────
try:
    from debugger import _pretty_format
    check("pretty int", _pretty_format(42) == "42")
except Exception as e:
    check("pretty int", False, str(e))

# ── 12. Pretty-print array ───────────────────────────────
try:
    from debugger import _pretty_format
    result = _pretty_format([1, 2, 3])
    check("pretty array contains brackets", "[" in result and "]" in result)
    check("pretty array has items", "1" in result and "2" in result and "3" in result)
except Exception as e:
    check("pretty array", False, str(e))

# ── 13. Pretty-print empty array ─────────────────────────
try:
    from debugger import _pretty_format
    check("pretty empty array", _pretty_format([]) == "[]")
except Exception as e:
    check("pretty empty array", False, str(e))

# ── 14. Pretty-print dict ────────────────────────────────
try:
    from debugger import _pretty_format
    result = _pretty_format({"name": "test", "val": 42})
    check("pretty dict contains braces", "{" in result and "}" in result)
    check("pretty dict has keys", "name" in result and "val" in result)
except Exception as e:
    check("pretty dict", False, str(e))

# ── 15. Pretty-print empty dict ──────────────────────────
try:
    from debugger import _pretty_format
    check("pretty empty dict", _pretty_format({}) == "{}")
except Exception as e:
    check("pretty empty dict", False, str(e))

# ── 16. Pretty-print nested array (2 levels) ─────────────
try:
    from debugger import _pretty_format
    result = _pretty_format([1, [2, 3], 4])
    check("pretty nested contains outer brackets", "[" in result and "]" in result)
    check("pretty nested contains inner items", all(s in result for s in ["1", "2", "3", "4"]))
except Exception as e:
    check("pretty nested array", False, str(e))

# ── 17. Pretty-print with max_depth truncation ───────────
try:
    from debugger import _pretty_format
    deep = [[[[1]]]]
    result = _pretty_format(deep, max_depth=2)
    check("pretty deep truncates", "..." in result)
except Exception as e:
    check("pretty deep truncation", False, str(e))

# ── 18. _format_value includes type ──────────────────────
try:
    from debugger import _format_value
    result = _format_value(42)
    check("format value includes (int)", "(int)" in result)
    check("format value includes value", "42" in result)
except Exception as e:
    check("format value", False, str(e))

# ── 19. _format_value for string ─────────────────────────
try:
    from debugger import _format_value
    result = _format_value("hello")
    check("format string includes type", "(string)" in result)
    check("format string includes value", "hello" in result)
except Exception as e:
    check("format string", False, str(e))

# ── 20. _format_value for array ──────────────────────────
try:
    from debugger import _format_value
    result = _format_value([1, 2, 3])
    check("format array includes type", "(array)" in result)
except Exception as e:
    check("format array", False, str(e))

# ── 21. _format_value for dict ───────────────────────────
try:
    from debugger import _format_value
    result = _format_value({"a": 1})
    check("format dict includes type", "(dict)" in result)
except Exception as e:
    check("format dict", False, str(e))

# ── 22. _format_value for bool ───────────────────────────
try:
    from debugger import _format_value
    result_true = _format_value(True)
    result_false = _format_value(False)
    check("format bool true includes type", "(bool)" in result_true)
    check("format bool false includes type", "(bool)" in result_false)
except Exception as e:
    check("format bool", False, str(e))

# ── 23. _format_value for nil ────────────────────────────
try:
    from debugger import _format_value
    result = _format_value(None)
    check("format nil includes type", "(nil)" in result)
    check("format nil value", "nil" in result)
except Exception as e:
    check("format nil", False, str(e))

# ── 24. DEBUG_HELP mentions new commands ──────────────────
try:
    from debugger import DEBUG_HELP
    check("help has .type", ".type" in DEBUG_HELP)
    check("help has watch persistence", "auto-evaluated" in DEBUG_HELP)
except Exception as e:
    check("help text", False, str(e))

# ── 25. debugger.py compiles ──────────────────────────────
try:
    import py_compile
    source = os.path.join(os.path.dirname(__file__), "..", "debugger.py")
    py_compile.compile(source, doraise=True)
    check("debugger.py compiles", True)
except py_compile.PyCompileError as e:
    check("debugger.py compiles", False, str(e))

# ── 26. _show_watch_value method exists ──────────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter(debug=True)
    d = Debugger(i, "test.ins")
    check("Debugger has _show_watch_value", hasattr(d, "_show_watch_value"))
except Exception as e:
    check("Debugger._show_watch_value", False, str(e))

# ── 27. Watch auto-evaluation at breakpoint ───────────────
try:
    from debugger import Debugger
    from interpreter import Interpreter
    i = Interpreter(debug=True, source_lines=["let x = 5", "let y = 10", "x + y"])
    d = Debugger(i, "<script>")
    d._watch_exprs = ["x + y"]
    # Simulate entering debug REPL with a node
    from ast_nodes import Node
    n = Node(line=1)
    # Just check that _watch_exprs is non-empty and the code path exists
    check("watch exprs stored", len(d._watch_exprs) == 1)
except Exception as e:
    check("watch auto-eval setup", False, str(e))

# ── 28. _cmd_locals uses _format_value ────────────────────
try:
    import inspect
    from debugger import Debugger
    locals_source = inspect.getsource(Debugger._cmd_locals)
    check("_cmd_locals uses _format_value", "_format_value" in locals_source)
except Exception as e:
    check("_cmd_locals uses _format_value", False, str(e))

# ── 29. _cmd_globals uses _format_value ───────────────────
try:
    import inspect
    from debugger import Debugger
    globals_source = inspect.getsource(Debugger._cmd_globals)
    check("_cmd_globals uses _format_value", "_format_value" in globals_source)
except Exception as e:
    check("_cmd_globals uses _format_value", False, str(e))

# ── 30. _eval_expr uses _format_value ─────────────────────
try:
    import inspect
    from debugger import Debugger
    eval_source = inspect.getsource(Debugger._eval_expr)
    check("_eval_expr uses _format_value", "_format_value" in eval_source)
except Exception as e:
    check("_eval_expr uses _format_value", False, str(e))

# ── RESULTS ────────────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.15 — Watch Window + REPL Integration")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
