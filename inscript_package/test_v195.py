"""
test_v195.py — v1.9.5: `div` keyword removed (E0056 hard error)

Notes:
  - `//` is always floor division (v1.9.6: spaces allowed)
  - `#` is the line comment character (v1.9.6)
  - `null` errors at RUNTIME via visit_NullLiteralExpr (not parse time)
  - `div` errors at PARSE time via parse_multiplication
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from environment import Environment

passed = failed = 0

def ok(name):
    global passed
    passed += 1
    print(f"  PASS  {name}")

def fail(name, reason=""):
    global failed
    failed += 1
    print(f"  FAIL  {name}  {reason}")

def run(src):
    lx = Lexer(src); tokens = lx.tokenize()
    pr = Parser(tokens); tree = pr.parse()
    interp = Interpreter(); interp._env = Environment()
    return interp.visit(tree)

def expect_parse_error(name, src, fragment=""):
    try:
        lx = Lexer(src); tokens = lx.tokenize()
        pr = Parser(tokens); pr.parse()
        fail(name, "expected parse error but none raised")
    except Exception as e:
        msg = str(e)
        if fragment and fragment not in msg:
            fail(name, f"expected '{fragment}' in: {msg[:120]}")
        else:
            ok(name)

def expect_runtime_error(name, src, fragment=""):
    try:
        run(src)
        fail(name, "expected runtime error but none raised")
    except Exception as e:
        msg = str(e)
        if fragment and fragment not in msg:
            fail(name, f"expected '{fragment}' in: {msg[:120]}")
        else:
            ok(name)

def expect_value(name, src, expected):
    try:
        result = run(src)
        if result == expected:
            ok(name)
        else:
            fail(name, f"got {result!r}, expected {expected!r}")
    except Exception as e:
        fail(name, f"raised {e}")

# ── 1-8: div is a hard PARSE error ───────────────────────────────────────────

expect_parse_error("div_basic_error",          "let x = 10 div 3",                  "E0056")
expect_parse_error("div_error_slashslash_hint","let x = 10 div 3",                  "//")
expect_parse_error("div_error_migrate_hint",   "let x = 10 div 3",                  "inscript migrate")
expect_parse_error("div_in_expression",        "let a = 5\nlet b = 20 div a",        "E0056")
expect_parse_error("div_chained",              "let x = 100 div 3 div 2",           "E0056")
expect_parse_error("div_in_function_body",     "fn f() -> int { return 9 div 3 }",  "E0056")
expect_parse_error("div_in_condition",         "let i=10\nif i div 2 > 0 { }",      "E0056")
expect_parse_error("div_in_print",             "print(10 div 2)",                   "E0056")

# ── 9-14: // works fine (NO spaces — lexer: space before // → comment) ───────

expect_value("slashslash_basic",       "10 // 3",                            3)  # v1.9.6: spaces ok
expect_value("slashslash_negative",    "-10 // 3",                           -4)
expect_value("slashslash_chained",     "100 // 3 // 2",                      16)
expect_value("slashslash_in_fn",
    "fn half(n: int) -> int { return n // 2 }\nhalf(10)",                    5)
expect_value("slashslash_in_array",    "[10 // 3, 20 // 4, 30 // 7]",       [3, 5, 4])
expect_value("slashslash_loop",
    "let s = 0\nfor i in [2,4,6,8] { s = s + i // 2 }\ns",               10)

# ── 15-16: null still errors at runtime (E0055) ──────────────────────────────

expect_runtime_error("null_still_errors",   "let x = null", "E0055")
expect_runtime_error("null_says_nil",       "let x = null", "nil")

# ── 17-18: E0056 in error catalogue and errors.py ────────────────────────────

def t_catalogue_e0056():
    from inscript import ERROR_CATALOGUE
    if "E0056" not in ERROR_CATALOGUE:
        return fail("catalogue_e0056", "E0056 missing")
    name, desc = ERROR_CATALOGUE["E0056"]
    if "DivKeyword" not in name:
        return fail("catalogue_e0056", f"wrong name: {name}")
    if "//" not in desc:
        return fail("catalogue_e0056", f"desc missing '//': {desc}")
    ok("catalogue_e0056")

t_catalogue_e0056()

def t_errors_py_e0056():
    from errors import ERROR_CODES
    if "DivKeyword" not in ERROR_CODES:
        return fail("errors_py_e0056", "DivKeyword missing")
    if ERROR_CODES["DivKeyword"] != "E0056":
        return fail("errors_py_e0056", f"wrong code: {ERROR_CODES['DivKeyword']}")
    ok("errors_py_e0056")

t_errors_py_e0056()

# ── 19-22: migrate tool rewrites div → // ────────────────────────────────────

import tempfile

def t_migrate_div():
    src = "let x = 10 div 3\nlet y = x div 2\n"
    with tempfile.NamedTemporaryFile(suffix=".ins", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write(src); fname = f.name
    try:
        from inscript import _migrate_files
        _migrate_files(fname)
        result = open(fname, encoding="utf-8").read()
        if " div " in result:
            fail("migrate_div", f"'div' still present: {result!r}")
        elif "//" not in result:
            fail("migrate_div", f"'//' not present: {result!r}")
        else:
            ok("migrate_div")
    finally:
        os.unlink(fname)

t_migrate_div()

def t_migrate_null_and_div():
    src = "let x = null\nlet y = 10 div 3\n"
    with tempfile.NamedTemporaryFile(suffix=".ins", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write(src); fname = f.name
    try:
        from inscript import _migrate_files
        _migrate_files(fname)
        result = open(fname, encoding="utf-8").read()
        if "null" in result or " div " in result:
            fail("migrate_null_and_div", f"old keywords still present: {result!r}")
        else:
            ok("migrate_null_and_div")
    finally:
        os.unlink(fname)

t_migrate_null_and_div()

def t_migrate_clean_unchanged():
    src = "let x = 10//3\nlet y = x//2\n"
    with tempfile.NamedTemporaryFile(suffix=".ins", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write(src); fname = f.name
    try:
        from inscript import _migrate_files
        _migrate_files(fname)
        result = open(fname, encoding="utf-8").read()
        if result != src:
            fail("migrate_clean_unchanged", "clean file was modified")
        else:
            ok("migrate_clean_unchanged")
    finally:
        os.unlink(fname)

t_migrate_clean_unchanged()

def t_compat_reports_div():
    import subprocess
    src = "let x = 10\nlet y = x div 5\n"
    with tempfile.NamedTemporaryFile(suffix=".ins", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write(src); fname = f.name
    try:
        r = subprocess.run([sys.executable, "inscript.py", "--compat", fname],
                           capture_output=True, text=True)
        output = r.stdout + r.stderr
        if "div" not in output.lower() and "E0056" not in output:
            fail("compat_reports_div", f"no div mention in: {output[:200]}")
        else:
            ok("compat_reports_div")
    finally:
        os.unlink(fname)

t_compat_reports_div()

# ── Summary ───────────────────────────────────────────────────────────────────

total = passed + failed
print()
print("=" * 58)
print(f"  v1.9.5 Test Results: {passed}/{total} passed")
print("  ALL PASS" if failed == 0 else f"  {failed} FAILED")
print("=" * 58)
sys.exit(0 if failed == 0 else 1)
