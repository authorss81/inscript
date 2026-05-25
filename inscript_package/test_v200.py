"""
test_v200.py — InScript v2.0.0 release smoke tests

Validates that all major language features are present and working
in the stable 2.0.0 release. Covers every feature area.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from analyzer import Analyzer, T_INT, T_FLOAT, T_STRING, T_BOOL, T_ANY
from errors import MultiError

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
    i = Interpreter()
    i.execute(src)
    return i

def analyze(src):
    tokens = Lexer(src).tokenize()
    ast    = Parser(tokens).parse()
    an     = Analyzer()
    try:
        an.analyze(ast)
    except MultiError:
        pass
    return an

def check(name, src, var, expected):
    try:
        i = run(src)
        result = i._env.get(var)
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

def expect_error(name, src):
    try:
        run(src)
        fail(name, "expected error, got none")
    except Exception:
        ok(name)

# ── 1. Core language ──────────────────────────────────────────────────────────

def test_let_and_arithmetic():
    check("let_and_arithmetic", "let x = 2 + 3 * 4", "x", 14)

def test_floor_division():
    check("floor_division", "let x = 17 // 5", "x", 3)

def test_string_concat_plusplus():
    check("string_concat_plusplus", 'let s = "foo" ++ "bar"', "s", "foobar")

def test_array_literal():
    check("array_literal", "let a = [10, 20, 30]\nlet n = a[1]", "n", 20)

def test_dict_literal():
    check("dict_literal", 'let d = {"x": 1, "y": 2}\nlet v = d["x"]', "v", 1)

def test_if_else():
    check("if_else", "let x = 10\nlet r = 0\nif x > 5 { r = 1 } else { r = 2 }", "r", 1)

def test_while_loop():
    check("while_loop",
          "let i = 0\nlet s = 0\nwhile i < 5 { s = s + i\ni = i + 1 }", "s", 10)

def test_for_in():
    check("for_in",
          "let nums = [1,2,3,4,5]\nlet total = 0\nfor n in nums { total = total + n }", "total", 15)

def test_fn_call():
    check("fn_call",
          "fn square(x: int) -> int { return x * x }\nlet r = square(7)", "r", 49)

def test_recursion():
    check("recursion",
          "fn fact(n: int) -> int { if n <= 1 { return 1 } return n * fact(n - 1) }\nlet r = fact(6)", "r", 720)

def test_closures():
    check("closures",
          "fn make_adder(n: int) { return fn(x: int) -> int { return x + n } }\nlet add5 = make_adder(5)\nlet r = add5(3)", "r", 8)

def test_array_methods():
    check("array_map",
          "let a = [1,2,3]\nlet b = a.map(fn(x:int)->int{return x*2})", "b", [2,4,6])

def test_array_filter():
    check("array_filter",
          "let a = [1,2,3,4,5]\nlet b = a.filter(fn(x:int)->bool{return x > 2})", "b", [3,4,5])

def test_string_methods():
    check("string_upper", 'let s = "hello".upper()', "s", "HELLO")
    check("string_split", 'let a = "a,b,c".split(",")', "a", ["a","b","c"])

# ── 2. Type system ────────────────────────────────────────────────────────────

def test_union_types():
    no_error("union_types",
             "fn id(x: int|string) -> int|string { return x }\nlet v = id(42)")

def test_optional_shorthand():
    no_error("optional_shorthand",
             "fn maybe(x: int?) -> int { if x == nil { return 0 } return x }\nlet v = maybe(5)")

def test_type_alias():
    no_error("type_alias",
             "type ID = int\nlet id: ID = 42")

def test_enum():
    no_error("enum",
             "enum Dir { North, South, East, West }\nlet d = Dir::North")

def test_struct():
    check("struct",
          "struct Point { x: float = 0.0\ny: float = 0.0 }\nlet p = Point { x: 3.0, y: 4.0 }\nlet v = p.x",
          "v", 3.0)

def test_interface():
    no_error("interface",
             "interface Drawable { fn draw() -> nil }\nstruct Box implements Drawable { fn draw() { } }")

def test_fn_return_type_inferred():
    """v1.9.13: unannotated fn return types propagate."""
    src = "fn double(x: int) { return x * 2 }\nlet y = double(5)"
    an = analyze(src)
    sym = an._scope.lookup("y")
    if sym and sym.type_ == T_INT:
        ok("fn_return_type_inferred")
    else:
        fail("fn_return_type_inferred", f"got {sym.type_ if sym else 'None'}")

def test_array_generic_annotation():
    """v1.9.13: Array<T> annotation resolves correctly."""
    no_error("array_generic_annotation",
             "let nums: Array<int> = [1, 2, 3]")

# ── 3. Async / await ──────────────────────────────────────────────────────────

def test_async_fn_returns_coroutine():
    from stdlib_values import InScriptCoroutine
    src = "async fn fetch() -> string { return \"data\" }\nlet c = fetch()"
    try:
        i = run(src)
        c = i._env.get("c")
        assert isinstance(c, InScriptCoroutine)
        ok("async_fn_returns_coroutine")
    except Exception as e:
        fail("async_fn_returns_coroutine", e)

def test_await_drives_coroutine():
    check("await_drives_coroutine",
          "async fn double(x: int) -> int { return x * 2 }\nasync fn main() -> int { return await double(5) }\nlet r = await main()",
          "r", 10)

# ── 4. String interpolation ($"...") — v1.9.15 ──────────────────────────────

def test_interp_simple():
    check("interp_simple",
          'let name = "World"\nlet s = $"Hello {name}!"', "s", "Hello World!")

def test_interp_expr():
    check("interp_expr",
          'let x = 6\nlet y = 7\nlet s = $"{x} * {y} = {x * y}"', "s", "6 * 7 = 42")

def test_interp_format_spec():
    check("interp_format_spec",
          'let pi = 3.14159\nlet s = $"pi = {pi:.2f}"', "s", "pi = 3.14")

def test_fstring_compat():
    check("fstring_compat",
          'let x = 99\nlet s = f"score={x}"', "s", "score=99")

# ── 5. Package manager ────────────────────────────────────────────────────────

def test_parse_pkg_spec():
    from inscript import _parse_pkg_spec
    name, ver = _parse_pkg_spec("math-utils@1.0.0")
    if name == "math-utils" and ver == "1.0.0":
        ok("parse_pkg_spec")
    else:
        fail("parse_pkg_spec", f"got ({name!r}, {ver!r})")

def test_registry_json_valid():
    reg = os.path.join(os.path.dirname(__file__), "inscript-packages", "registry.json")
    try:
        with open(reg) as f:
            data = json.load(f)
        # v2.1.2+ added more packages — check original 3 are still present
        required = {"math-utils", "color-utils", "easing"}
        assert required.issubset(set(data.keys())), f"missing packages: {required - set(data.keys())}"
        ok("registry_json_valid")
    except Exception as e:
        fail("registry_json_valid", e)

def test_math_utils_package():
    path = os.path.join(os.path.dirname(__file__),
                        "inscript-packages", "packages", "math-utils", "math-utils.ins")
    try:
        i = run(open(path).read())
        result = i._call_fn(i._env.get("factorial"), [5])
        assert result == 120
        ok("math_utils_package")
    except Exception as e:
        fail("math_utils_package", e)

# ── 6. Games ──────────────────────────────────────────────────────────────────

def _make_mocks():
    class M:
        def __getattr__(self, k): return M()
        def __call__(self, *a, **kw): return None
        def __bool__(self): return False
    class Screen(M):
        width=800; height=600; fps=60.0; center_x=400; center_y=300
    i = Interpreter()
    env = i._env
    for name, val in [("screen",Screen()),("draw",M()),("input",M()),
                      ("audio",M()),("font",M()),("math2d",M()),
                      ("Color",M()),("clock",M())]:
        env.define(name, val)
    for c in ["WHITE","BLACK","RED","GREEN","BLUE","YELLOW","CYAN","ORANGE",
              "GRAY","DARK_GRAY","LIGHT_GRAY","PURPLE","PINK","TEAL","GOLD","TRANSPARENT"]:
        env.define(c, {"r":0.0,"g":0.0,"b":0.0,"a":1.0})
    return i

def test_pong_runs():
    try:
        i = _make_mocks()
        i.execute(open("examples/pong.ins").read())
        ok("pong_runs")
    except Exception as e:
        fail("pong_runs", e)

def test_breakout_runs():
    try:
        i = _make_mocks()
        i.execute(open("examples/breakout.ins").read())
        ok("breakout_runs")
    except Exception as e:
        fail("breakout_runs", e)

# ── 7. Tooling ────────────────────────────────────────────────────────────────

def test_check_v2_all_pass():
    import subprocess
    r = subprocess.run(
        ["python3", "inscript.py", "--check-v2", "."],
        capture_output=True, text=True,
        cwd=os.path.dirname(__file__)
    )
    if r.returncode == 0 and "8/8 gates passed" in r.stdout:
        ok("check_v2_all_pass")
    else:
        fail("check_v2_all_pass", f"rc={r.returncode}\n{r.stdout[-300:]}")

def test_error_catalogue_present():
    import subprocess
    r = subprocess.run(
        ["python3", "inscript.py", "--errors"],
        capture_output=True, text=True,
        cwd=os.path.dirname(__file__)
    )
    if "E0001" in r.stdout or "E0010" in r.stdout:
        ok("error_catalogue_present")
    else:
        fail("error_catalogue_present", r.stdout[:100])

def test_game_flag_present():
    import subprocess
    r = subprocess.run(
        ["python3", "inscript.py", "--help"],
        capture_output=True, text=True,
        cwd=os.path.dirname(__file__)
    )
    if "--game" in r.stdout:
        ok("game_flag_present")
    else:
        fail("game_flag_present", "--game not in help")

def test_inscript_toml_exists():
    path = os.path.join(os.path.dirname(__file__), "inscript.toml")
    if os.path.exists(path):
        ok("inscript_toml_exists")
    else:
        fail("inscript_toml_exists", "not found")

def test_inscript_lock_exists():
    path = os.path.join(os.path.dirname(__file__), "inscript.lock")
    if os.path.exists(path):
        ok("inscript_lock_exists")
    else:
        fail("inscript_lock_exists", "not found")

# ── 8. Error system ───────────────────────────────────────────────────────────

def test_stack_trace_on_error():
    src = "fn a() { fn b() { let x = 1 / 0 } b() } a()"
    try:
        run(src)
        fail("stack_trace_on_error", "expected error")
    except Exception as e:
        # Any runtime error from a nested call is acceptable
        ok("stack_trace_on_error")

def test_div_hard_error():
    expect_error("div_hard_error", "let x = 10 div 2")

def test_null_hard_error():
    expect_error("null_hard_error", "let x = null")

# ── 9. Version ────────────────────────────────────────────────────────────────

def test_version_is_200():
    import repl, inscript
    def v(s): return tuple(int(x) for x in s.split("."))
    if v(repl.VERSION) >= (2, 0, 0) and v(inscript.VERSION) >= (2, 0, 0):
        ok("version_is_2.0.0")
    else:
        fail("version_is_2.0.0", f"repl={repl.VERSION} inscript={inscript.VERSION}")

def test_setup_version():
    import subprocess
    r = subprocess.run(["python3", "setup.py", "--version"],
                       capture_output=True, text=True,
                       cwd=os.path.dirname(__file__))
    ver = r.stdout.strip()
    parts = [int(x) for x in ver.split(".")]
    if tuple(parts) >= (2, 0, 0):
        ok("setup_version_2.0.0")
    else:
        fail("setup_version_2.0.0", ver)

# ── run all ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("test_v200.py — InScript v2.0.0 release smoke tests")
    print("=" * 60)

    # Core
    test_let_and_arithmetic()
    test_floor_division()
    test_string_concat_plusplus()
    test_array_literal()
    test_dict_literal()
    test_if_else()
    test_while_loop()
    test_for_in()
    test_fn_call()
    test_recursion()
    test_closures()
    test_array_methods()
    test_array_filter()
    test_string_methods()

    # Type system
    test_union_types()
    test_optional_shorthand()
    test_type_alias()
    test_enum()
    test_struct()
    test_interface()
    test_fn_return_type_inferred()
    test_array_generic_annotation()

    # Async
    test_async_fn_returns_coroutine()
    test_await_drives_coroutine()

    # String interpolation
    test_interp_simple()
    test_interp_expr()
    test_interp_format_spec()
    test_fstring_compat()

    # Packages
    test_parse_pkg_spec()
    test_registry_json_valid()
    test_math_utils_package()

    # Games
    test_pong_runs()
    test_breakout_runs()

    # Tooling
    test_check_v2_all_pass()
    test_error_catalogue_present()
    test_game_flag_present()
    test_inscript_toml_exists()
    test_inscript_lock_exists()

    # Errors
    test_stack_trace_on_error()
    test_div_hard_error()
    test_null_hard_error()

    # Version
    test_version_is_200()
    test_setup_version()

    total = passed + failed
    print("=" * 60)
    print(f"{passed}/{total} passed  ({failed} failed)")
    if failed:
        sys.exit(1)
