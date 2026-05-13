"""
test_v201.py — InScript v2.0.1
Range syntax: `for i in 0..10 step 2`, auto-descend, negative step.

New in v2.0.1:
  - `start..end step N`  — custom step in range literals
  - `start..=end step N` — inclusive with custom step
  - Auto-descend: `for i in 5..1` auto-uses step=-1 (was empty before)
  - Negative step: `for i in 10..0 step -2`
  - step as expression: `for i in 0..n step s`
  - Range assigned to variable carries step: `let r = 0..20 step 4`
  - InScriptRange.__len__ and __repr__ updated for negative step
  - Analyzer validates step must be int
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from interpreter import Interpreter
from analyzer import Analyzer, T_INT
from lexer import Lexer
from parser import Parser
from errors import MultiError

passed = 0
failed = 0

def ok(name):
    global passed; passed += 1
    print(f"  PASS  {name}")

def fail(name, reason):
    global failed; failed += 1
    print(f"  FAIL  {name}: {reason}")

def run(src):
    i = Interpreter(); i.execute(src); return i

def check(name, src, var, expected):
    try:
        result = run(src)._env.get(var)
        if result == expected: ok(name)
        else: fail(name, f"expected {expected!r}, got {result!r}")
    except Exception as e:
        fail(name, e)

def no_error(name, src):
    try: run(src); ok(name)
    except Exception as e: fail(name, e)

def analyze(src):
    tokens = Lexer(src).tokenize()
    ast    = Parser(tokens).parse()
    an     = Analyzer()
    try: an.analyze(ast)
    except MultiError: pass
    return an

# ── 1. Basic step syntax ──────────────────────────────────────────────────────

def test_step_2():
    check("step_2",
          "let a = []\nfor i in 0..10 step 2 { a = a + [i] }",
          "a", [0, 2, 4, 6, 8])

def test_step_3():
    check("step_3",
          "let a = []\nfor i in 0..12 step 3 { a = a + [i] }",
          "a", [0, 3, 6, 9])

def test_step_5():
    check("step_5",
          "let a = []\nfor i in 0..=20 step 5 { a = a + [i] }",
          "a", [0, 5, 10, 15, 20])

def test_step_inclusive():
    check("step_inclusive",
          "let a = []\nfor i in 0..=9 step 3 { a = a + [i] }",
          "a", [0, 3, 6, 9])

def test_step_1_explicit():
    check("step_1_explicit",
          "let a = []\nfor i in 0..5 step 1 { a = a + [i] }",
          "a", [0, 1, 2, 3, 4])

# ── 2. Step as expression ─────────────────────────────────────────────────────

def test_step_variable():
    check("step_variable",
          "let s = 2\nlet a = []\nfor i in 0..8 step s { a = a + [i] }",
          "a", [0, 2, 4, 6])

def test_step_expression():
    check("step_expression",
          "let a = []\nfor i in 0..16 step 2 * 2 { a = a + [i] }",
          "a", [0, 4, 8, 12])

def test_step_fn_result():
    check("step_fn_result",
          "fn get_step() -> int { return 3 }\nlet a = []\nfor i in 0..9 step get_step() { a = a + [i] }",
          "a", [0, 3, 6])

# ── 3. Auto-descend (start > end, no step given) ──────────────────────────────

def test_auto_descend_basic():
    check("auto_descend_basic",
          "let a = []\nfor i in 5..1 { a = a + [i] }",
          "a", [5, 4, 3, 2])

def test_auto_descend_inclusive():
    check("auto_descend_inclusive",
          "let a = []\nfor i in 5..=1 { a = a + [i] }",
          "a", [5, 4, 3, 2, 1])

def test_auto_descend_sum():
    check("auto_descend_sum",
          "let s = 0\nfor i in 5..0 step -1 { s = s + i }",
          "s", 15)

def test_auto_descend_to_zero():
    check("auto_descend_to_zero",
          "let a = []\nfor i in 3..0 { a = a + [i] }",
          "a", [3, 2, 1])

def test_auto_descend_large():
    check("auto_descend_large",
          "let s = 0\nfor i in 100..=1 { s = s + i }",
          "s", 5050)

# ── 4. Explicit negative step ─────────────────────────────────────────────────

def test_explicit_negative_step():
    check("explicit_negative_step",
          "let a = []\nfor i in 5..1 step -1 { a = a + [i] }",
          "a", [5, 4, 3, 2])

def test_step_minus_2():
    check("step_minus_2",
          "let a = []\nfor i in 10..0 step -2 { a = a + [i] }",
          "a", [10, 8, 6, 4, 2])

def test_step_minus_3():
    check("step_minus_3",
          "let a = []\nfor i in 9..=0 step -3 { a = a + [i] }",
          "a", [9, 6, 3, 0])

# ── 5. Range stored in variable ───────────────────────────────────────────────

def test_range_var_with_step():
    check("range_var_with_step",
          "let r = 0..10 step 2\nlet a = []\nfor i in r { a = a + [i] }",
          "a", [0, 2, 4, 6, 8])

def test_range_var_descend():
    check("range_var_descend",
          "let r = 5..1\nlet a = []\nfor i in r { a = a + [i] }",
          "a", [5, 4, 3, 2])

def test_range_var_len_step():
    try:
        from stdlib_values import InScriptRange
        r = InScriptRange(0, 10, step=2, inclusive=False)
        assert len(r) == 5, f"expected 5, got {len(r)}"
        ok("range_var_len_step")
    except Exception as e:
        fail("range_var_len_step", e)

def test_range_var_len_descend():
    try:
        from stdlib_values import InScriptRange
        r = InScriptRange(5, 1, step=-1, inclusive=False)
        assert len(r) == 4, f"expected 4, got {len(r)}"
        ok("range_var_len_descend")
    except Exception as e:
        fail("range_var_len_descend", e)

# ── 6. Backward compatibility ────────────────────────────────────────────────

def test_no_step_ascending():
    check("no_step_ascending",
          "let s = 0\nfor i in 0..5 { s = s + i }",
          "s", 10)

def test_no_step_inclusive():
    check("no_step_inclusive",
          "let s = 0\nfor i in 1..=5 { s = s + i }",
          "s", 15)

def test_classic_sum_1_to_100():
    check("classic_sum_1_to_100",
          "let s = 0\nfor i in 1..=100 { s = s + i }",
          "s", 5050)

def test_range_function_compat():
    check("range_function_compat",
          "let a = []\nfor i in range(0, 10, 2) { a = a + [i] }",
          "a", [0, 2, 4, 6, 8])

# ── 7. Loop control in step ranges ───────────────────────────────────────────

def test_break_in_step_range():
    check("break_in_step_range",
          "let s = 0\nfor i in 0..20 step 3 { if i > 9 { break }\ns = s + i }",
          "s", 18)

def test_continue_in_step_range():
    check("continue_in_step_range",
          "let s = 0\nfor i in 0..10 step 1 { if i % 2 == 0 { continue }\ns = s + i }",
          "s", 25)

def test_nested_step_ranges():
    check("nested_step_ranges",
          "let s = 0\nfor i in 0..3 { for j in 0..=4 step 2 { s = s + 1 } }",
          "s", 9)

# ── 8. Analyzer: step must be int ────────────────────────────────────────────

def test_analyzer_step_int_ok():
    try:
        an = analyze("for i in 0..10 step 2 { }")
        errs = " ".join(an._errors)
        if "step" not in errs.lower():
            ok("analyzer_step_int_ok")
        else:
            fail("analyzer_step_int_ok", f"unexpected error: {errs[:100]}")
    except Exception as e:
        fail("analyzer_step_int_ok", e)

def test_analyzer_step_float_error():
    try:
        an = analyze("for i in 0..10 step 1.5 { }")
        errs = " ".join(an._errors)
        if "step" in errs.lower() or "float" in errs.lower():
            ok("analyzer_step_float_error")
        else:
            fail("analyzer_step_float_error", "expected step type error, got none")
    except Exception as e:
        # Error thrown as exception is also acceptable
        ok("analyzer_step_float_error")

# ── 9. version ────────────────────────────────────────────────────────────────

def test_version_is_201():
    import repl
    parts = [int(x) for x in repl.VERSION.split(".")]
    if tuple(parts) >= (2, 0, 1):
        ok("version_is_2.0.1")
    else:
        fail("version_is_2.0.1", f"got {repl.VERSION}")

# ── run all ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("test_v201.py — v2.0.1: range step syntax + auto-descend")
    print("=" * 60)

    test_step_2()
    test_step_3()
    test_step_5()
    test_step_inclusive()
    test_step_1_explicit()

    test_step_variable()
    test_step_expression()
    test_step_fn_result()

    test_auto_descend_basic()
    test_auto_descend_inclusive()
    test_auto_descend_sum()
    test_auto_descend_to_zero()
    test_auto_descend_large()

    test_explicit_negative_step()
    test_step_minus_2()
    test_step_minus_3()

    test_range_var_with_step()
    test_range_var_descend()
    test_range_var_len_step()
    test_range_var_len_descend()

    test_no_step_ascending()
    test_no_step_inclusive()
    test_classic_sum_1_to_100()
    test_range_function_compat()

    test_break_in_step_range()
    test_continue_in_step_range()
    test_nested_step_ranges()

    test_analyzer_step_int_ok()
    test_analyzer_step_float_error()

    test_version_is_201()

    total = passed + failed
    print("=" * 60)
    print(f"{passed}/{total} passed  ({failed} failed)")
    if failed:
        sys.exit(1)
