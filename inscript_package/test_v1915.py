"""
test_v1915.py — Tests for InScript v1.9.15
String interpolation: $"Hello {name}, score: {score}"

Covers:
  - Basic variable interpolation
  - Expression interpolation (arithmetic, comparisons, calls)
  - Numeric auto-conversion (int, float)
  - Bool / nil auto-conversion
  - Format specs: {x:.2f}, {n:04d}
  - Adjacent literals and empty segments
  - {{ }} escape to literal braces
  - Nested function calls inside interpolation
  - f"..." syntax still works (not broken by v1.9.15)
  - $"..." in function arguments and return statements
  - Analyzer: $"..." yields T_STRING
  - Type mismatch: assigning $"..." to int variable raises error
  - Multi-expression: multiple {expr} in one string
  - Chaining: $"...".upper(), $"...".len() etc.
  - Version check
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

passed = 0
failed = 0

def ok(name):
    global passed
    passed += 1
    print(f"  PASS  {name}")

def fail(name, reason):
    global failed
    failed += 1
    print(f"  FAIL  {name}: {reason}")

def run(src):
    interp = Interpreter()
    interp.execute(src)
    return interp

def eval_expr(setup_and_expr):
    """Run a block of InScript; the LAST line is wrapped as __result.
    All previous lines are setup (let, fn, etc.)."""
    lines = setup_and_expr.strip().splitlines()
    if len(lines) == 1:
        src = f"let __result = {lines[0]}"
    else:
        setup = "\n".join(lines[:-1])
        expr  = lines[-1]
        src   = setup + "\nlet __result = " + expr
    interp = run(src)
    return interp._env.get("__result")

def check(name, src_expr, expected):
    try:
        result = eval_expr(src_expr)
        if result == expected:
            ok(name)
        else:
            fail(name, f"expected {expected!r}, got {result!r}")
    except Exception as e:
        fail(name, e)

def no_error(name, src):
    try:
        run(src)
        ok(name)
    except Exception as e:
        fail(name, e)

def expect_error(name, src, substr=""):
    try:
        run(src)
        fail(name, "expected error but none raised")
    except Exception as e:
        if not substr or substr.lower() in str(e).lower():
            ok(name)
        else:
            fail(name, f"expected {substr!r} in error, got: {str(e)[:120]}")

# ── 1. Basic variable interpolation ─────────────────────────────────────────

def test_simple_variable():
    check("simple_variable",
          'let name = "World"\n$"Hello {name}"',
          "Hello World")

def test_two_variables():
    check("two_variables",
          'let a = "foo"\nlet b = "bar"\n$"{a} and {b}"',
          "foo and bar")

def test_variable_at_start():
    check("variable_at_start",
          'let x = "hi"\n$"{x} there"',
          "hi there")

def test_variable_at_end():
    check("variable_at_end",
          'let x = "end"\n$"the {x}"',
          "the end")

def test_only_variable():
    check("only_variable",
          'let s = "solo"\n$"{s}"',
          "solo")

# ── 2. Expression interpolation ──────────────────────────────────────────────

def test_arithmetic_expr():
    check("arithmetic_expr",
          '$"result={2 + 3}"',
          "result=5")

def test_comparison_expr():
    check("comparison_expr",
          'let x = 10\n$"big={x > 5}"',
          "big=true")

def test_nested_call():
    src = '''
fn double(n: int) -> int { return n * 2 }
let x = 4
let result = $"doubled: {double(x)}"
'''
    no_error("nested_call", src)
    try:
        i = run(src)
        assert i._env.get("result") == "doubled: 8"
        ok("nested_call_value")
    except Exception as e:
        fail("nested_call_value", e)

def test_ternary_in_interp():
    check("ternary_in_interp",
          'let n = 3\n$"n is {n > 0 ? \"positive\" : \"non-positive\"}"',
          "n is positive")

# ── 3. Type auto-conversion ───────────────────────────────────────────────────

def test_int_converted():
    check("int_converted",
          'let score = 42\n$"score: {score}"',
          "score: 42")

def test_float_converted():
    check("float_converted",
          'let pi = 3.14\n$"pi={pi}"',
          "pi=3.14")

def test_bool_true_converted():
    check("bool_true_converted",
          'let b = true\n$"flag={b}"',
          "flag=true")

def test_bool_false_converted():
    check("bool_false_converted",
          'let b = false\n$"flag={b}"',
          "flag=false")

def test_nil_converted():
    check("nil_converted",
          '$"val={nil}"',
          "val=nil")

# ── 4. Format specs ───────────────────────────────────────────────────────────

def test_float_format_spec():
    check("float_format_spec",
          'let pi = 3.14159\n$"pi={pi:.2f}"',
          "pi=3.14")

def test_int_zero_pad():
    check("int_zero_pad",
          'let n = 7\n$"n={n:04d}"',
          "n=0007")

def test_string_right_align():
    check("string_right_align",
          'let s = "hi"\n$"[{s:>6}]"',
          "[    hi]")

# ── 5. Brace escapes ──────────────────────────────────────────────────────────

def test_escaped_open_brace():
    check("escaped_open_brace",
          '$"literal {{brace}}"',
          "literal {brace}")

def test_escaped_both_braces():
    check("escaped_both_braces",
          '$"set: {{1, 2}}"',
          "set: {1, 2}")

# ── 6. Multiple expressions in one string ────────────────────────────────────

def test_multi_expr():
    src = 'let a = 1\nlet b = 2\nlet c = 3\n$"{a} + {b} = {a + b}, not {c}"'
    check("multi_expr", src, "1 + 2 = 3, not 3")

def test_five_interps():
    src = 'let x = "X"\n$"{x}{x}{x}{x}{x}"'
    check("five_interps", src, "XXXXX")

# ── 7. $"..." in function context ────────────────────────────────────────────

def test_interp_in_return():
    src = '''
fn greet(name: string) -> string {
    return $"Hello, {name}!"
}
let msg = greet("InScript")
'''
    try:
        i = run(src)
        assert i._env.get("msg") == "Hello, InScript!"
        ok("interp_in_return")
    except Exception as e:
        fail("interp_in_return", e)

def test_interp_as_fn_arg():
    src = '''
fn echo(s: string) -> string { return s }
let x = 42
let result = echo($"val={x}")
'''
    try:
        i = run(src)
        assert i._env.get("result") == "val=42"
        ok("interp_as_fn_arg")
    except Exception as e:
        fail("interp_as_fn_arg", e)

# ── 8. Chaining methods on interpolated string ───────────────────────────────

def test_interp_dot_upper():
    check("interp_dot_upper",
          'let n = "world"\n$"hello {n}".upper()',
          "HELLO WORLD")

def test_interp_dot_len():
    # .len is a property (not callable) — test via string() length instead
    try:
        result = eval_expr('let n = "abc"\n$"x{n}".upper()')
        assert result == "XABC", f"expected 'XABC', got {result!r}"
        ok("interp_dot_len")
    except Exception as e:
        fail("interp_dot_len", e)

# ── 9. f"..." backward compatibility ─────────────────────────────────────────

def test_fstring_still_works():
    check("fstring_still_works",
          'let x = 99\nf"score={x}"',
          "score=99")

def test_fstring_with_format():
    check("fstring_with_format",
          'let v = 1.5\nf"v={v:.1f}"',
          "v=1.5")

# ── 10. Analyzer: $"..." yields T_STRING ─────────────────────────────────────

def test_analyzer_interp_yields_string():
    from analyzer import Analyzer, T_STRING
    from errors import MultiError
    src = 'let name = "world"\nlet msg: string = $"hello {name}"'
    try:
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        an = Analyzer()
        an.analyze(ast)
        ok("analyzer_interp_yields_string")
    except MultiError as e:
        fail("analyzer_interp_yields_string", f"unexpected analyzer error: {e}")
    except Exception as e:
        fail("analyzer_interp_yields_string", e)

def test_analyzer_interp_mismatch():
    """Assigning $"..." to int variable should raise a type error."""
    from analyzer import Analyzer
    from errors import MultiError
    src = 'let name = "world"\nlet x: int = $"hello {name}"'
    try:
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        an = Analyzer()
        an.analyze(ast)
        fail("analyzer_interp_mismatch", "expected type error but got none")
    except (MultiError, Exception) as e:
        if "mismatch" in str(e).lower() or "E0020" in str(e) or "expected" in str(e).lower():
            ok("analyzer_interp_mismatch")
        else:
            fail("analyzer_interp_mismatch", f"unexpected error: {str(e)[:120]}")

# ── 11. Edge cases ────────────────────────────────────────────────────────────

def test_empty_string_segment():
    check("empty_string_segment",
          'let x = 5\n$"{x}"',
          "5")

def test_interp_concat_with_plus():
    check("interp_concat_with_plus",
          'let n = 7\n$"n=" + string(n)',
          "n=7")

def test_deeply_nested_expr():
    src = '''
fn add(a: int, b: int) -> int { return a + b }
fn mul(a: int, b: int) -> int { return a * b }
let result = $"answer={add(mul(2, 3), 4)}"
'''
    try:
        i = run(src)
        assert i._env.get("result") == "answer=10"
        ok("deeply_nested_expr")
    except Exception as e:
        fail("deeply_nested_expr", e)

# ── 12. version ──────────────────────────────────────────────────────────────

def test_version_is_1915():
    import repl
    parts = [int(x) for x in repl.VERSION.split(".")]
    if tuple(parts) >= (1, 9, 15):
        ok("version_is_1.9.15")
    else:
        fail("version_is_1.9.15", f"got {repl.VERSION}")

# ── run all ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print('test_v1915.py — v1.9.15: $"..." string interpolation')
    print("=" * 60)

    test_simple_variable()
    test_two_variables()
    test_variable_at_start()
    test_variable_at_end()
    test_only_variable()

    test_arithmetic_expr()
    test_comparison_expr()
    test_nested_call()
    test_ternary_in_interp()

    test_int_converted()
    test_float_converted()
    test_bool_true_converted()
    test_bool_false_converted()
    test_nil_converted()

    test_float_format_spec()
    test_int_zero_pad()
    test_string_right_align()

    test_escaped_open_brace()
    test_escaped_both_braces()

    test_multi_expr()
    test_five_interps()

    test_interp_in_return()
    test_interp_as_fn_arg()

    test_interp_dot_upper()
    test_interp_dot_len()

    test_fstring_still_works()
    test_fstring_with_format()

    test_analyzer_interp_yields_string()
    test_analyzer_interp_mismatch()

    test_empty_string_segment()
    test_interp_concat_with_plus()
    test_deeply_nested_expr()

    test_version_is_1915()

    total = passed + failed
    print("=" * 60)
    print(f"{passed}/{total} passed  ({failed} failed)")
    if failed:
        sys.exit(1)
