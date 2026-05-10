"""
test_v197.py — v1.9.7: True async/await via asyncio

Tests:
  1-4:   async fn returns InScriptCoroutine, not plain value
  5-10:  await drives coroutine to completion — correct result
  11-14: sequential awaits in same function
  15-17: nested async (async fn calling async fn)
  18-20: await on plain value is passthrough (backwards compatible)
  21-22: async fn in analyzer returns Promise<T> type
  23-24: InScriptCoroutine repr is human-readable
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from environment import Environment
from stdlib_values import InScriptCoroutine

import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning, message='coroutine.*never awaited')

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

def expect_value(name, src, expected):
    try:
        result = run(src)
        if result == expected: ok(name)
        else: fail(name, f"got {result!r}, expected {expected!r}")
    except Exception as e:
        fail(name, f"raised {e}")

def expect_type(name, src, typ):
    try:
        result = run(src)
        if isinstance(result, typ): ok(name)
        else: fail(name, f"got {type(result).__name__}, expected {typ.__name__}")
    except Exception as e:
        fail(name, f"raised {e}")

# ── 1-4: calling async fn returns a coroutine, not immediate value ────────────

expect_type("async_fn_returns_coroutine",
    "async fn greet() -> string { return \"hello\" }\ngreet()",
    InScriptCoroutine)

expect_type("async_fn_with_arg_returns_coroutine",
    "async fn double(n: int) -> int { return n * 2 }\ndouble(5)",
    InScriptCoroutine)

expect_type("async_fn_no_return_type_returns_coroutine",
    "async fn noop() { }\nnoop()",
    InScriptCoroutine)

def t_coroutine_has_fn_name():
    src = "async fn greet() -> string { return \"hello\" }\ngreet()"
    coro = run(src)
    if not isinstance(coro, InScriptCoroutine):
        return fail("coroutine_has_fn_name", f"expected coroutine, got {type(coro)}")
    if "greet" not in repr(coro):
        fail("coroutine_has_fn_name", f"fn name missing from repr: {repr(coro)}")
    else:
        ok("coroutine_has_fn_name")

t_coroutine_has_fn_name()

# ── 5-10: await drives coroutine to correct result ────────────────────────────

expect_value("await_string_return",
    'async fn greet() -> string { return "hello" }\nawait greet()',
    "hello")

expect_value("await_int_return",
    "async fn double(n: int) -> int { return n * 2 }\nawait double(5)",
    10)

expect_value("await_bool_return",
    "async fn is_even(n: int) -> bool { return n % 2 == 0 }\nawait is_even(4)",
    True)

expect_value("await_arithmetic",
    "async fn add(a: int, b: int) -> int { return a + b }\nawait add(3, 7)",
    10)

expect_value("await_with_local_var",
    "async fn compute() -> int {\n"
    "    let x = 10\n"
    "    let y = x * 3\n"
    "    return y\n"
    "}\nawait compute()",
    30)

expect_value("await_stored_in_var",
    "async fn fetch() -> int { return 42 }\n"
    "let result = await fetch()\n"
    "result",
    42)

# ── 11-14: sequential awaits in same scope ────────────────────────────────────

expect_value("two_sequential_awaits",
    "async fn one() -> int { return 1 }\n"
    "async fn two() -> int { return 2 }\n"
    "let a = await one()\n"
    "let b = await two()\n"
    "a + b",
    3)

expect_value("three_sequential_awaits",
    "async fn val(n: int) -> int { return n }\n"
    "let x = await val(10)\n"
    "let y = await val(20)\n"
    "let z = await val(30)\n"
    "x + y + z",
    60)

expect_value("await_in_expression",
    "async fn double(n: int) -> int { return n * 2 }\n"
    "let result = (await double(3)) + (await double(4))\n"
    "result",
    14)

expect_value("await_result_used_in_condition",
    "async fn positive(n: int) -> bool { return n > 0 }\n"
    "let is_pos = await positive(5)\n"
    "if is_pos { 1 } else { 0 }",
    1)

# ── 15-17: nested async (async fn calling async fn via await) ─────────────────

expect_value("nested_async_basic",
    "async fn inner() -> int { return 99 }\n"
    "async fn outer() -> int { return await inner() }\n"
    "await outer()",
    99)

expect_value("nested_async_chain",
    "async fn base() -> int { return 5 }\n"
    "async fn mid() -> int { return (await base()) * 2 }\n"
    "async fn top() -> int { return (await mid()) + 1 }\n"
    "await top()",
    11)

expect_value("nested_async_with_arg",
    "async fn square(n: int) -> int { return n * n }\n"
    "async fn sum_squares(a: int, b: int) -> int {\n"
    "    return (await square(a)) + (await square(b))\n"
    "}\n"
    "await sum_squares(3, 4)",
    25)

# ── 18-20: await on plain value is passthrough ────────────────────────────────

expect_value("await_plain_int",        "await 42",        42)
expect_value("await_plain_string",     'await "hello"',   "hello")
expect_value("await_plain_bool",       "await true",      True)

# ── 21-22: analyzer: Promise<T> type registered ───────────────────────────────

def t_promise_in_builtin_types():
    from analyzer import BUILTIN_TYPES, T_PROMISE
    if "Promise" not in BUILTIN_TYPES:
        return fail("promise_in_builtins", "Promise not in BUILTIN_TYPES")
    if BUILTIN_TYPES["Promise"] is not T_PROMISE:
        return fail("promise_in_builtins", "wrong object for Promise type")
    ok("promise_in_builtins")

t_promise_in_builtin_types()

def t_async_fn_analyzed():
    """async fn should not raise a SemanticError during analysis."""
    from analyzer import Analyzer
    src = "async fn fetch(url: string) -> string { return url }"
    lx = Lexer(src); tokens = lx.tokenize()
    pr = Parser(tokens); tree = pr.parse()
    a = Analyzer()
    errors = a.analyze(tree)
    errs = [e for e in errors if "Promise" in str(e) or "async" in str(e).lower()]
    if errs:
        fail("async_fn_analyzed", f"unexpected async errors: {errs}")
    else:
        ok("async_fn_analyzed")

t_async_fn_analyzed()

# ── 23-24: InScriptCoroutine repr ────────────────────────────────────────────

def t_coro_repr():
    src = "async fn my_task() -> int { return 1 }\nmy_task()"
    coro = run(src)
    r = repr(coro)
    if "my_task" not in r:
        fail("coro_repr_has_name", f"fn name not in repr: {r!r}")
    else:
        ok("coro_repr_has_name")

t_coro_repr()

def t_coro_is_inscript_coroutine():
    src = "async fn task() -> int { return 7 }\ntask()"
    result = run(src)
    if not hasattr(result, 'coro') or not hasattr(result, 'fn_name'):
        fail("coro_has_attrs", f"missing coro/fn_name attrs on {result!r}")
    else:
        ok("coro_has_attrs")

t_coro_is_inscript_coroutine()

# ── Summary ───────────────────────────────────────────────────────────────────
total = passed + failed
print()
print("=" * 58)
print(f"  v1.9.7 Test Results: {passed}/{total} passed")
print("  ALL PASS" if failed == 0 else f"  {failed} FAILED")
print("=" * 58)
sys.exit(0 if failed == 0 else 1)
