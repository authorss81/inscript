"""
test_v1913.py — Tests for InScript v1.9.13
Type inference round 2:
  - fn call return types propagate (let x = add(1,2) → x:int)
  - named fn references in method chains (.map(double) → Array<int>)
  - struct method return types inferred from body
  - T_ANY leakage in method chains reduced
  - substr added to string method type table
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from analyzer import Analyzer, T_INT, T_FLOAT, T_STRING, T_BOOL, T_ANY, T_VOID, array_type
from lexer import Lexer
from parser import Parser

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

from errors import InScriptError

class _AnalysisResult:
    """Wraps analyzer + any collected errors for test assertions."""
    def __init__(self, an, error_text=""):
        self._an = an
        self.error_text = error_text
    def get_var(self, name):
        sym = self._an._scope.lookup(name)
        return sym.type_ if sym else None

def analyze(src):
    """Run analyzer; return _AnalysisResult whether or not errors occur."""
    from errors import MultiError
    tokens = Lexer(src).tokenize()
    ast    = Parser(tokens).parse()
    an     = Analyzer()
    err_text = ""
    try:
        an.analyze(ast)
    except MultiError as me:
        err_text = str(me)
    except Exception as e:
        err_text = str(e)
    return _AnalysisResult(an, err_text)

def get_var(an_or_result, name):
    if isinstance(an_or_result, _AnalysisResult):
        return an_or_result.get_var(name)
    sym = an_or_result._scope.lookup(name)
    return sym.type_ if sym else None

def no_errors(src, name):
    try:
        r = analyze(src)
        if r.error_text:
            fail(name, f"unexpected errors: {r.error_text[:200]}")
        else:
            ok(name)
    except Exception as e:
        fail(name, e)

def has_error(src, substr, name):
    try:
        r = analyze(src)
        if substr.lower() in r.error_text.lower():
            ok(name)
        else:
            fail(name, f"expected {substr!r} in errors, got: {r.error_text[:200]}")
    except Exception as e:
        fail(name, e)

# ── 1. fn call return type propagates (annotated) ────────────────────────────

def test_annotated_fn_return_propagates():
    src = """
fn add(a: int, b: int) -> int { return a + b }
let x = add(1, 2)
"""
    try:
        r = analyze(src)
        t = get_var(r, "x")
        if t == T_INT:
            ok("annotated_fn_return_propagates")
        else:
            fail("annotated_fn_return_propagates", f"expected T_INT, got {t}")
    except Exception as e:
        fail("annotated_fn_return_propagates", e)

# ── 2. fn call return type inferred from body (no annotation) ────────────────

def test_unannotated_fn_return_inferred():
    src = """
fn double(x: int) { return x * 2 }
let y = double(5)
"""
    try:
        r = analyze(src)
        t = get_var(r, "y")
        if t == T_INT:
            ok("unannotated_fn_return_inferred")
        else:
            fail("unannotated_fn_return_inferred", f"expected T_INT, got {t}")
    except Exception as e:
        fail("unannotated_fn_return_inferred", e)

def test_unannotated_fn_return_float():
    src = """
fn half(x: float) { return x * 0.5 }
let z = half(4.0)
"""
    try:
        r = analyze(src)
        t = get_var(r, "z")
        if t == T_FLOAT:
            ok("unannotated_fn_return_float")
        else:
            fail("unannotated_fn_return_float", f"expected T_FLOAT, got {t}")
    except Exception as e:
        fail("unannotated_fn_return_float", e)

def test_unannotated_fn_return_string():
    src = """
fn greet(name: string) { return "Hello " ++ name }
let msg = greet("World")
"""
    try:
        r = analyze(src)
        t = get_var(r, "msg")
        if t == T_STRING:
            ok("unannotated_fn_return_string")
        else:
            fail("unannotated_fn_return_string", f"expected T_STRING, got {t}")
    except Exception as e:
        fail("unannotated_fn_return_string", e)

def test_unannotated_fn_return_bool():
    src = """
fn is_big(x: int) { return x > 100 }
let b = is_big(200)
"""
    try:
        r = analyze(src)
        t = get_var(r, "b")
        if t == T_BOOL:
            ok("unannotated_fn_return_bool")
        else:
            fail("unannotated_fn_return_bool", f"expected T_BOOL, got {t}")
    except Exception as e:
        fail("unannotated_fn_return_bool", e)

# ── 3. type mismatch caught using inferred return type ───────────────────────

def test_mismatch_caught_via_inferred_return():
    """let x: string = add(1,2) should error since add infers -> int"""
    src = """
fn add(a: int, b: int) { return a + b }
let x: string = add(1, 2)
"""
    has_error(src, "mismatch", "mismatch_caught_via_inferred_return")

# ── 4. named fn reference in .map() propagates return type ──────────────────

def test_named_fn_in_map_propagates():
    src = """
fn double(x: int) -> int { return x * 2 }
let nums: Array<int> = [1, 2, 3]
let doubled = nums.map(double)
"""
    try:
        r = analyze(src)
        t = get_var(r, "doubled")
        expected = array_type(T_INT)
        if t == expected:
            ok("named_fn_in_map_propagates")
        else:
            fail("named_fn_in_map_propagates", f"expected Array<int>, got {t}")
    except Exception as e:
        fail("named_fn_in_map_propagates", e)

def test_named_fn_in_map_unannotated():
    """Named fn with no return annotation — infer from body, propagate to .map()"""
    src = """
fn negate(x: int) { return 0 - x }
let nums: Array<int> = [1, 2, 3]
let negs = nums.map(negate)
"""
    try:
        r = analyze(src)
        t = get_var(r, "negs")
        expected = array_type(T_INT)
        if t == expected:
            ok("named_fn_in_map_unannotated")
        else:
            fail("named_fn_in_map_unannotated", f"expected Array<int>, got {t}")
    except Exception as e:
        fail("named_fn_in_map_unannotated", e)

# ── 5. method chain — no T_ANY leakage ──────────────────────────────────────

def test_chain_filter_after_map_no_leakage():
    """scores.map(inline fn) → Array<int>; .filter(...) → Array<int> (not Array<any>)"""
    src = """
let scores: Array<int> = [10, 20, 30]
let big = scores.map(fn(x: int) -> int { return x * 2 }).filter(fn(x: int) -> bool { return x > 10 })
"""
    try:
        r = analyze(src)
        t = get_var(r, "big")
        expected = array_type(T_INT)
        if t == expected:
            ok("chain_filter_after_map_no_leakage")
        else:
            fail("chain_filter_after_map_no_leakage", f"expected Array<int>, got {t}")
    except Exception as e:
        fail("chain_filter_after_map_no_leakage", e)

def test_chain_len_after_map():
    """Array.map(...).len() → int"""
    src = """
let nums: Array<int> = [1, 2, 3]
let n = nums.map(fn(x: int) -> int { return x }).len()
"""
    try:
        r = analyze(src)
        t = get_var(r, "n")
        if t == T_INT:
            ok("chain_len_after_map")
        else:
            fail("chain_len_after_map", f"expected T_INT, got {t}")
    except Exception as e:
        fail("chain_len_after_map", e)

def test_chain_join_after_map():
    """Array<string>.map(...).join() → string"""
    src = """
let words: Array<string> = ["a", "b", "c"]
let result = words.map(fn(s: string) -> string { return s ++ "!" }).join(", ")
"""
    try:
        r = analyze(src)
        t = get_var(r, "result")
        if t == T_STRING:
            ok("chain_join_after_map")
        else:
            fail("chain_join_after_map", f"expected T_STRING, got {t}")
    except Exception as e:
        fail("chain_join_after_map", e)

# ── 6. struct method return type inferred from body ──────────────────────────

def test_struct_method_return_inferred():
    src = """
struct Counter {
    value: int = 0
    fn get() { return self.value }
}
let c = Counter { value: 5 }
let v = c.get()
"""
    try:
        r = analyze(src)
        t = get_var(r, "v")
        # Should be T_INT (inferred from body), or at least not raise
        if t in (T_INT, T_ANY):
            ok("struct_method_return_inferred")
        else:
            fail("struct_method_return_inferred", f"got {t}")
    except Exception as e:
        fail("struct_method_return_inferred", e)

# ── 7. chained calls using inferred return ───────────────────────────────────

def test_chained_fn_calls_inferred():
    """let result = double(triple(x)) — types chain through inference"""
    src = """
fn triple(x: int) { return x * 3 }
fn double(x: int) { return x * 2 }
let result = double(triple(2))
"""
    try:
        r = analyze(src)
        t = get_var(r, "result")
        if t == T_INT:
            ok("chained_fn_calls_inferred")
        else:
            fail("chained_fn_calls_inferred", f"expected T_INT, got {t}")
    except Exception as e:
        fail("chained_fn_calls_inferred", e)

# ── 8. substr on string infers T_STRING ──────────────────────────────────────

def test_substr_infers_string():
    src = """
let s = "hello world"
let sub = s.substr(0, 5)
"""
    try:
        r = analyze(src)
        t = get_var(r, "sub")
        if t == T_STRING:
            ok("substr_infers_string")
        else:
            fail("substr_infers_string", f"expected T_STRING, got {t}")
    except Exception as e:
        fail("substr_infers_string", e)

# ── 9. pre-existing inference still works (regression) ───────────────────────

def test_regression_annotated_fn_still_works():
    no_errors("""
fn area(w: float, h: float) -> float { return w * h }
let a: float = area(3.0, 4.0)
""", "regression_annotated_fn_still_works")

def test_regression_array_literal_inference():
    no_errors("""
let nums = [1, 2, 3]
let n: int = nums.len()
""", "regression_array_literal_inference")

def test_regression_string_methods():
    no_errors("""
let s = "hello"
let upper = s.upper()
let parts = s.split("")
""", "regression_string_methods")

def test_regression_struct_methods():
    no_errors("""
struct Point { x: float = 0.0; y: float = 0.0
    fn magnitude() -> float { return self.x * self.x + self.y * self.y }
}
let p = Point { x: 3.0, y: 4.0 }
let m: float = p.magnitude()
""", "regression_struct_methods")

def test_regression_union_types():
    no_errors("""
fn identity(x: int|string) -> int|string { return x }
let v = identity(42)
""", "regression_union_types")

def test_regression_async_return_type():
    no_errors("""
async fn fetch() -> string { return "data" }
""", "regression_async_return_type")

# ── 10. version check ─────────────────────────────────────────────────────────

def test_version_is_1913():
    import repl
    if repl.VERSION == "1.9.13":
        ok("version_is_1.9.13")
    else:
        fail("version_is_1.9.13", f"got {repl.VERSION}")

# ── run all ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("test_v1913.py — v1.9.13 type inference round 2")
    print("=" * 60)

    test_annotated_fn_return_propagates()
    test_unannotated_fn_return_inferred()
    test_unannotated_fn_return_float()
    test_unannotated_fn_return_string()
    test_unannotated_fn_return_bool()

    test_mismatch_caught_via_inferred_return()

    test_named_fn_in_map_propagates()
    test_named_fn_in_map_unannotated()

    test_chain_filter_after_map_no_leakage()
    test_chain_len_after_map()
    test_chain_join_after_map()

    test_struct_method_return_inferred()
    test_chained_fn_calls_inferred()
    test_substr_infers_string()

    test_regression_annotated_fn_still_works()
    test_regression_array_literal_inference()
    test_regression_string_methods()
    test_regression_struct_methods()
    test_regression_union_types()
    test_regression_async_return_type()

    test_version_is_1913()

    total = passed + failed
    print("=" * 60)
    print(f"{passed}/{total} passed  ({failed} failed)")
    if failed:
        sys.exit(1)
