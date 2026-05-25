"""
test_v211.py — InScript v2.1.1
inscript --fmt: auto-formatter for .ins files.

Fixes and features:
  - Type annotations: `a:int` → `a: int`
  - Arrow operator: `->` surrounded by spaces
  - Range operators: `..` and `..=` have NO spaces (were wrongly spaced)
  - $"..." normalized: f"..." → $"..." (preferred syntax)
  - Match case arms: `case 1 { expr }` stays on one line when body is simple
  - Struct fields: each field on its own line
  - Dict literals: `{"k": v}` stays inline (not a block)
  - Nested dicts: `{"a": {"x": 1}}` fully inline
  - Idempotent: formatting twice gives same result
  - --fmt flag present in --help
"""
import sys, os, subprocess, tempfile
sys.path.insert(0, os.path.dirname(__file__))

from inscript_fmt import format_source

passed = 0
failed = 0

def ok(name):
    global passed; passed += 1
    print(f"  PASS  {name}")

def fail(name, reason):
    global failed; failed += 1
    print(f"  FAIL  {name}: {reason}")

def check(name, src, expected):
    try:
        result = format_source(src).strip()
        exp    = expected.strip()
        if result == exp:
            ok(name)
        else:
            fail(name, f"\n    want: {exp!r}\n    got:  {result!r}")
    except Exception as e:
        fail(name, e)

def idempotent(name, src):
    """format_source(format_source(src)) == format_source(src)"""
    try:
        once  = format_source(src)
        twice = format_source(once)
        if once == twice:
            ok(name)
        else:
            fail(name, f"not idempotent:\n  pass1: {once!r}\n  pass2: {twice!r}")
    except Exception as e:
        fail(name, e)

# ── 1. Basic spacing ──────────────────────────────────────────────────────────

def test_basic_arithmetic():
    check("basic_arithmetic", "let x=1+2*3", "let x = 1 + 2 * 3")

def test_comparison():
    check("comparison", "if x>0&&y<10{print(x)}", "if x > 0 && y < 10 {\n    print(x)\n}")

def test_assignment_spacing():
    check("assignment_spacing", "let x=42", "let x = 42")

# ── 2. Type annotations: colon gets space after ───────────────────────────────

def test_param_type_annotation():
    check("param_type_annotation",
          "fn add(a:int,b:int)->int{return a+b}",
          "fn add(a: int, b: int) -> int {\n    return a + b\n}")

def test_let_type_annotation():
    check("let_type_annotation",
          "let x:int=5",
          "let x: int = 5")

def test_complex_type_annotation():
    check("complex_type_annotation",
          "let f:fn()->int=get_fn()",
          "let f: fn() -> int = get_fn()")

def test_array_type_annotation():
    check("array_type_annotation",
          "let a:Array<int>=[1,2,3]",
          "let a: Array<int> = [1, 2, 3]")

# ── 3. Arrow operator has spaces ──────────────────────────────────────────────

def test_arrow_spacing():
    check("arrow_spacing",
          "fn f(x:int)->string{return string(x)}",
          "fn f(x: int) -> string {\n    return string(x)\n}")

def test_arrow_void():
    check("arrow_void",
          "fn setup()->nil{print(1)}",
          "fn setup() -> nil {\n    print(1)\n}")

# ── 4. Range operators: NO spaces around .. and ..= ──────────────────────────

def test_range_no_spaces():
    check("range_no_spaces",
          "for i in 0..10{print(i)}",
          "for i in 0..10 {\n    print(i)\n}")

def test_range_inclusive_no_spaces():
    check("range_inclusive_no_spaces",
          "for i in 1..=5{print(i)}",
          "for i in 1..=5 {\n    print(i)\n}")

def test_range_step():
    check("range_step",
          "for i in 0..20 step 4{print(i)}",
          "for i in 0..20 step 4 {\n    print(i)\n}")

def test_range_in_let():
    check("range_in_let",
          "let r=0..100",
          "let r = 0..100")

# ── 5. f"..." → $"..." normalization ─────────────────────────────────────────

def test_fstring_normalised_to_dollar():
    check("fstring_normalised_to_dollar",
          'let s=f"hello {name}"',
          'let s = $"hello {name}"')

def test_dollar_string_preserved():
    check("dollar_string_preserved",
          'let s=$"score={score}"',
          'let s = $"score={score}"')

def test_fstring_with_format_spec():
    check("fstring_with_format_spec",
          'let s=f"pi={pi:.2f}"',
          'let s = $"pi={pi:.2f}"')

# ── 6. Match case arms stay inline ────────────────────────────────────────────

def test_match_inline_string_arms():
    check("match_inline_string_arms",
          'match x{case 1{"one"}\ncase 2{"two"}\ncase _{"other"}}',
          'match x {\n    case 1 { "one" }\n    case 2 { "two" }\n    case _ { "other" }\n}')

def test_match_inline_int_arms():
    check("match_inline_int_arms",
          "match n{case 1{10}\ncase 2{20}\ncase _{0}}",
          "match n {\n    case 1 { 10 }\n    case 2 { 20 }\n    case _ { 0 }\n}")

def test_match_guard_inline():
    check("match_guard_inline",
          'match n{case h if h>5{"big"}\ncase _{"small"}}',
          'match n {\n    case h if h > 5 { "big" }\n    case _ { "small" }\n}')

def test_match_nil_arm():
    check("match_nil_arm",
          'match x{case nil{"nothing"}\ncase _{"something"}}',
          'match x {\n    case nil { "nothing" }\n    case _ { "something" }\n}')

# ── 7. Struct fields on separate lines ───────────────────────────────────────

def test_struct_two_fields():
    check("struct_two_fields",
          "struct P{x:float=0.0\ny:float=0.0}",
          "struct P {\n    x: float = 0.0\n    y: float = 0.0\n}")

def test_struct_three_fields():
    check("struct_three_fields",
          "struct V{x:float=0.0\ny:float=0.0\nz:float=0.0}",
          "struct V {\n    x: float = 0.0\n    y: float = 0.0\n    z: float = 0.0\n}")

def test_struct_int_fields():
    check("struct_int_fields",
          "struct Player{health:int=100\nscore:int=0}",
          "struct Player {\n    health: int = 100\n    score: int = 0\n}")

# ── 8. Dict literals stay inline ─────────────────────────────────────────────

def test_dict_inline():
    check("dict_inline",
          'let d={"k":1,"v":2}',
          'let d = {"k": 1, "v": 2}')

def test_dict_nested_inline():
    check("dict_nested_inline",
          'let m={"a":{"x":1}}',
          'let m = {"a": {"x": 1}}')

def test_dict_in_return():
    check("dict_in_return",
          'fn f()->dict{return {"k":1}}',
          'fn f() -> dict {\n    return {"k": 1}\n}')

def test_dict_empty():
    check("dict_empty",
          "let d={}",
          "let d = {}")

# ── 9. Spread operator ────────────────────────────────────────────────────────

def test_spread_in_array():
    check("spread_in_array",
          "let a=[...x,...y]",
          "let a = [...x, ...y]")

def test_spread_fn_call():
    check("spread_fn_call",
          "let r=add(...args)",
          "let r = add(...args)")

# ── 10. Block structures ──────────────────────────────────────────────────────

def test_if_block():
    check("if_block",
          "if x>0{print(x)}",
          "if x > 0 {\n    print(x)\n}")

def test_if_else():
    check("if_else",
          "if x>0{return 1}else{return 0}",
          "if x > 0 {\n    return 1\n} else {\n    return 0\n}")

def test_while_loop():
    check("while_loop",
          "while i<10{i=i+1}",
          "while i < 10 {\n    i = i + 1\n}")

def test_nested_blocks():
    check("nested_blocks",
          "fn outer(){if x{return 1}}",
          "fn outer() {\n    if x {\n        return 1\n    }\n}")

# ── 11. Idempotency ───────────────────────────────────────────────────────────

def test_idempotent_fn():
    idempotent("idempotent_fn",
               "fn add(a:int,b:int)->int{return a+b}")

def test_idempotent_struct():
    idempotent("idempotent_struct",
               "struct P{x:float=0.0\ny:float=0.0}")

def test_idempotent_match():
    idempotent("idempotent_match",
               'match x{case 1{"a"}\ncase _{"b"}}')

def test_idempotent_dict():
    idempotent("idempotent_dict",
               'let d={"k":1,"v":2}')

def test_idempotent_already_formatted():
    src = "fn add(a: int, b: int) -> int {\n    return a + b\n}\n"
    idempotent("idempotent_already_formatted", src)

# ── 12. --fmt CLI flag ────────────────────────────────────────────────────────

def test_fmt_flag_in_help():
    r = subprocess.run(
        ["python3", "inscript.py", "--help"],
        capture_output=True, text=True,
        cwd=os.path.dirname(__file__)
    )
    if "--fmt" in r.stdout:
        ok("fmt_flag_in_help")
    else:
        fail("fmt_flag_in_help", "--fmt not in --help")

def test_fmt_formats_file():
    """--fmt FILE rewrites the file in place."""
    src = "fn f(x:int)->int{return x*2}"
    expected = "fn f(x: int) -> int {\n    return x * 2\n}\n"
    with tempfile.NamedTemporaryFile(suffix=".ins", mode="w", delete=False) as f:
        f.write(src)
        path = f.name
    try:
        r = subprocess.run(
            ["python3", "inscript.py", "--fmt", path],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        )
        with open(path) as f:
            result = f.read()
        if result == expected:
            ok("fmt_formats_file")
        else:
            fail("fmt_formats_file", f"got: {result!r}")
    finally:
        os.unlink(path)

# ── 13. version ───────────────────────────────────────────────────────────────

def test_version_is_211():
    import repl
    if tuple(int(x) for x in repl.VERSION.split(".")) >= (2, 1, 1):
        ok("version_is_at_least_2_1_1")
    else:
        fail("version_is_at_least_2_1_1", f"got {repl.VERSION}")

# ── run all ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("test_v211.py — v2.1.1: inscript --fmt formatter")
    print("=" * 60)

    test_basic_arithmetic()
    test_comparison()
    test_assignment_spacing()

    test_param_type_annotation()
    test_let_type_annotation()
    test_complex_type_annotation()
    test_array_type_annotation()

    test_arrow_spacing()
    test_arrow_void()

    test_range_no_spaces()
    test_range_inclusive_no_spaces()
    test_range_step()
    test_range_in_let()

    test_fstring_normalised_to_dollar()
    test_dollar_string_preserved()
    test_fstring_with_format_spec()

    test_match_inline_string_arms()
    test_match_inline_int_arms()
    test_match_guard_inline()
    test_match_nil_arm()

    test_struct_two_fields()
    test_struct_three_fields()
    test_struct_int_fields()

    test_dict_inline()
    test_dict_nested_inline()
    test_dict_in_return()
    test_dict_empty()

    test_spread_in_array()
    test_spread_fn_call()

    test_if_block()
    test_if_else()
    test_while_loop()
    test_nested_blocks()

    test_idempotent_fn()
    test_idempotent_struct()
    test_idempotent_match()
    test_idempotent_dict()
    test_idempotent_already_formatted()

    test_fmt_flag_in_help()
    test_fmt_formats_file()

    test_version_is_211()

    total = passed + failed
    print("=" * 60)
    print(f"{passed}/{total} passed  ({failed} failed)")
    if failed:
        sys.exit(1)
