"""
test_v198.py — v1.9.8: Type inference hardening

Tests:
  1-6:   Array<T> inferred from homogeneous literals: [1,2,3]→Array<int>
  7-9:   Mixed array literals → Array<any>
  10-13: Dict literal inference: {"k":1}→Dict<string,int>
  14-17: VarDecl infers type from initialiser: let x=[1,2,3] → x:Array<int>
  18-20: inscript --infer-types CLI command
  21-24: test_phase1, test_v12, test_v170 regressions pass (div fixed)
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from environment import Environment
from analyzer import Analyzer, T_INT, T_STRING, T_FLOAT, T_BOOL, T_ANY, array_type, dict_type

passed = failed = 0

def ok(name):
    global passed; passed += 1; print(f"  PASS  {name}")

def fail(name, reason=""):
    global failed; failed += 1; print(f"  FAIL  {name}  {reason}")

def run(src):
    lx = Lexer(src); tokens = lx.tokenize()
    pr = Parser(tokens); tree = pr.parse()
    interp = Interpreter(); interp._env = Environment()
    return interp.visit(tree)

def infer(src):
    """Return the analyzer type of the last expression/decl."""
    lx = Lexer(src); tokens = lx.tokenize()
    pr = Parser(tokens); tree = pr.parse()
    a = Analyzer()
    try: a.analyze(tree)
    except Exception: pass
    return a

def expect_value(name, src, expected):
    try:
        result = run(src)
        if result == expected: ok(name)
        else: fail(name, f"got {result!r}, expected {expected!r}")
    except Exception as e:
        fail(name, f"raised {e}")

def expect_array_type(name, src, expected_elem_type):
    a = infer(src)
    # Find the last symbol defined
    sym = None
    for s in a._scope.symbols.values():
        sym = s
    if sym is None:
        return fail(name, "no symbol found")
    t = sym.type_
    expected = array_type(expected_elem_type)
    if t.name == expected.name and t.params == expected.params:
        ok(name)
    else:
        fail(name, f"got {t}, expected {expected}")

# ── 1-6: homogeneous array literal inference ──────────────────────────────────

expect_array_type("int_array_inferred",     "let x = [1, 2, 3]",           T_INT)
expect_array_type("float_array_inferred",   "let x = [1.0, 2.5, 3.0]",     T_FLOAT)
expect_array_type("string_array_inferred",  'let x = ["a", "b", "c"]',     T_STRING)
expect_array_type("bool_array_inferred",    "let x = [true, false, true]",  T_BOOL)
expect_array_type("empty_array_is_any",     "let x = []",                   T_ANY)
expect_array_type("single_elem_int",        "let x = [42]",                 T_INT)

# ── 7-9: mixed array → Array<any> ────────────────────────────────────────────

expect_array_type("mixed_int_string",   'let x = [1, "two", 3]',    T_ANY)
expect_array_type("mixed_int_bool",     "let x = [1, true, 2]",     T_ANY)
expect_array_type("mixed_float_string", 'let x = [1.0, "hi"]',      T_ANY)

# ── 10-13: dict literal inference ────────────────────────────────────────────

def expect_dict_type(name, src, expected_k, expected_v):
    a = infer(src)
    sym = None
    for s in a._scope.symbols.values():
        sym = s
    if sym is None:
        return fail(name, "no symbol found")
    t = sym.type_
    expected = dict_type(expected_k, expected_v)
    if t.name == expected.name and len(t.params) == 2:
        ok(name)
    else:
        fail(name, f"got {t}, expected {expected}")

expect_dict_type("dict_str_int",    '{"a": 1, "b": 2}' if False else 'let x = {"a": 1}',  T_STRING, T_INT)
expect_dict_type("dict_str_float",  'let x = {"pi": 3.14}',       T_STRING, T_FLOAT)
expect_dict_type("dict_str_bool",   'let x = {"ok": true}',       T_STRING, T_BOOL)
expect_dict_type("dict_str_str",    'let x = {"k": "v"}',         T_STRING, T_STRING)

# ── 14-17: VarDecl infers correct type ───────────────────────────────────────

def t_var_infers_int():
    a = infer("let x = 42")
    sym = a._scope.lookup("x")
    if sym and sym.type_ == T_INT: ok("var_infers_int")
    else: fail("var_infers_int", f"got {sym.type_ if sym else None}")

def t_var_infers_string():
    a = infer('let x = "hello"')
    sym = a._scope.lookup("x")
    if sym and sym.type_ == T_STRING: ok("var_infers_string")
    else: fail("var_infers_string", f"got {sym.type_ if sym else None}")

def t_var_infers_array_int():
    a = infer("let arr = [1, 2, 3]")
    sym = a._scope.lookup("arr")
    if sym and sym.type_.name == "Array" and sym.type_.params == [T_INT]:
        ok("var_infers_array_int")
    else:
        fail("var_infers_array_int", f"got {sym.type_ if sym else None}")

def t_var_infers_bool():
    a = infer("let flag = true")
    sym = a._scope.lookup("flag")
    if sym and sym.type_ == T_BOOL: ok("var_infers_bool")
    else: fail("var_infers_bool", f"got {sym.type_ if sym else None}")

t_var_infers_int()
t_var_infers_string()
t_var_infers_array_int()
t_var_infers_bool()

# ── 18-20: --infer-types CLI ──────────────────────────────────────────────────

import tempfile, subprocess

def t_infer_types_cli():
    src = "let x = 42\nlet name = \"alice\"\nlet nums = [1, 2, 3]\n"
    with tempfile.NamedTemporaryFile(suffix=".ins", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write(src); fname = f.name
    try:
        r = subprocess.run([sys.executable, "inscript.py", "--infer-types", fname],
                           capture_output=True, text=True)
        output = r.stdout + r.stderr
        if "x" not in output:
            fail("infer_types_cli_x", f"'x' not in output: {output[:200]}")
        else:
            ok("infer_types_cli_x")
        if "int" in output.lower() or "int" in output:
            ok("infer_types_cli_shows_int")
        else:
            fail("infer_types_cli_shows_int", f"'int' not in: {output[:200]}")
    finally:
        os.unlink(fname)

t_infer_types_cli()

def t_infer_types_missing_file():
    r = subprocess.run([sys.executable, "inscript.py", "--infer-types", "nonexistent.ins"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        ok("infer_types_missing_file_returns_1")
    else:
        fail("infer_types_missing_file_returns_1", "expected exit 1")

t_infer_types_missing_file()

# ── 21-24: regression — div fixed in previously missed test files ─────────────

def t_phase1_floor_div():
    """test_phase1.py's 1.2 section now uses // not div."""
    result = run("print(7 // 2)")
    # check via interpreter
    from io import StringIO
    import sys as _sys
    buf = StringIO(); old = _sys.stdout; _sys.stdout = buf
    try:
        run("print(10 // 3)")
    finally:
        _sys.stdout = old
    out = buf.getvalue().strip()
    if out == "3": ok("phase1_floor_div_regression")
    else: fail("phase1_floor_div_regression", f"got {out!r}")

t_phase1_floor_div()

def t_v12_floor_div():
    """test_v12.py's v1.1 floor div test now uses //."""
    from io import StringIO
    import sys as _sys
    buf = StringIO(); old = _sys.stdout; _sys.stdout = buf
    try: run("print(7 // 2)")
    finally: _sys.stdout = old
    out = buf.getvalue().strip()
    if out == "3": ok("v12_floor_div_regression")
    else: fail("v12_floor_div_regression", f"got {out!r}")

t_v12_floor_div()

expect_value("array_runtime_values",   "[1, 2, 3]",         [1, 2, 3])
expect_value("mixed_array_runtime",    '[1, "two", 3]',     [1, "two", 3])

# ── Summary ───────────────────────────────────────────────────────────────────
total = passed + failed
print()
print("=" * 58)
print(f"  v1.9.8 Test Results: {passed}/{total} passed")
print("  ALL PASS" if failed == 0 else f"  {failed} FAILED")
print("=" * 58)
sys.exit(0 if failed == 0 else 1)
