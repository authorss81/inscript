"""
test_v220.py — InScript v2.2.0
===========================================
Language enhancements:
  • ??=  null-coalescing assignment
  • with expr { .field = val }  clone-and-modify
  • fn f({x,y}: T) / fn f([h,...t]: [])  destructuring params
  • fn f() -> (name: Type, ...)  named return values
  (already present: impl sugar, const, \"\"\", chained comparisons, is, labeled loops)
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import repl as repl_mod
from interpreter import Interpreter
from parser import parse

PASS = 0; FAIL = 0

def ok(name):
    global PASS; PASS += 1; print(f"  PASS  {name}")

def fail(name, msg=""):
    global FAIL; FAIL += 1; print(f"  FAIL  {name}: {msg}")

def run(src: str) -> Interpreter:
    i = Interpreter(); i.run(parse(src)); return i

def check(name, got, expected):
    if got == expected: ok(name)
    else: fail(name, f"want {expected!r}, got {got!r}")

def check_close(name, got, expected, tol=1e-9):
    if abs(got - expected) <= tol: ok(name)
    else: fail(name, f"want ≈{expected}, got {got}")

# ─────────────────────────────────────────────────────────────────────────────
# 1. ??=  null-coalescing assignment
# ─────────────────────────────────────────────────────────────────────────────

def test_nullish_assign_nil():
    i = run("let x = nil\nx ??= 42")
    check("??= writes when nil", i._env.get("x"), 42)

def test_nullish_assign_non_nil():
    i = run("let x = 10\nx ??= 99")
    check("??= skips when non-nil", i._env.get("x"), 10)

def test_nullish_assign_zero_is_not_nil():
    i = run("let x = 0\nx ??= 99")
    check("??= treats 0 as non-nil", i._env.get("x"), 0)

def test_nullish_assign_false_is_not_nil():
    i = run("let x = false\nx ??= true")
    check("??= treats false as non-nil", i._env.get("x"), False)

def test_nullish_assign_string():
    i = run('let s = nil\ns ??= "hello"')
    check("??= assigns string", i._env.get("s"), "hello")

def test_nullish_assign_chain():
    i = run("let a = nil\nlet b = nil\nlet c = 7\na ??= 1\nb ??= 2\nc ??= 99")
    check("??= chain a", i._env.get("a"), 1)
    check("??= chain b", i._env.get("b"), 2)
    check("??= chain c unchanged", i._env.get("c"), 7)

def test_nullish_assign_expr_rhs():
    i = run("let x = nil\nlet n = 5\nx ??= n * n")
    check("??= evaluates rhs expr", i._env.get("x"), 25)

def test_nullish_assign_only_once():
    # second ??= should not overwrite after first assigns
    i = run("let x = nil\nx ??= 10\nx ??= 20")
    check("??= only assigns once", i._env.get("x"), 10)

# ─────────────────────────────────────────────────────────────────────────────
# 2. with  clone-and-modify
# ─────────────────────────────────────────────────────────────────────────────

def test_with_dict_changes_field():
    i = run('let p = {"x": 1.0, "y": 2.0}\nlet q = with p { .x = 99.0 }')
    check("with dict changes field", i._env.get("q")["x"], 99.0)

def test_with_dict_keeps_other_fields():
    i = run('let p = {"x": 1.0, "y": 2.0}\nlet q = with p { .x = 99.0 }')
    check("with dict keeps other field", i._env.get("q")["y"], 2.0)

def test_with_dict_does_not_mutate_original():
    i = run('let p = {"x": 1.0, "y": 2.0}\nlet q = with p { .x = 99.0 }')
    check("with dict original unchanged", i._env.get("p")["x"], 1.0)

def test_with_dict_multiple_fields():
    i = run('let p = {"x": 1, "y": 2, "z": 3}\nlet q = with p { .x = 10, .z = 30 }')
    check("with dict multi x", i._env.get("q")["x"], 10)
    check("with dict multi y", i._env.get("q")["y"], 2)
    check("with dict multi z", i._env.get("q")["z"], 30)

def test_with_struct_changes_field():
    i = run('struct Vec { x: float = 0.0\n y: float = 0.0 }\nlet v = Vec{x: 1.0, y: 2.0}\nlet w = with v { .x = 50.0 }')
    check("with struct changes", i._env.get("w").fields["x"], 50.0)

def test_with_struct_keeps_field():
    i = run('struct Vec { x: float = 0.0\n y: float = 0.0 }\nlet v = Vec{x: 1.0, y: 2.0}\nlet w = with v { .x = 50.0 }')
    check("with struct keeps", i._env.get("w").fields["y"], 2.0)

def test_with_struct_no_mutation():
    i = run('struct Vec { x: float = 0.0\n y: float = 0.0 }\nlet v = Vec{x: 1.0, y: 2.0}\nlet w = with v { .x = 50.0 }')
    check("with struct original unchanged", i._env.get("v").fields["x"], 1.0)

def test_with_chained():
    i = run('let p = {"a": 1, "b": 2}\nlet q = with (with p { .a = 10 }) { .b = 20 }')
    check("with chained a", i._env.get("q")["a"], 10)
    check("with chained b", i._env.get("q")["b"], 20)

def test_with_new_field():
    i = run('let p = {"x": 1}\nlet q = with p { .y = 42 }')
    check("with can add new dict field", i._env.get("q")["y"], 42)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Destructuring params
# ─────────────────────────────────────────────────────────────────────────────

def test_dict_destruct_basic():
    i = run('fn sq({x, y}: dict) -> float { return x*x + y*y }\nlet r = sq({"x": 3.0, "y": 4.0})')
    check_close("dict destruct basic", i._env.get("r"), 25.0)

def test_dict_destruct_subset():
    i = run('fn greet({name}: dict) -> string { return "Hi " ++ name }\nlet r = greet({"name": "Ada", "age": 30})')
    check("dict destruct subset", i._env.get("r"), "Hi Ada")

def test_dict_destruct_rest():
    i = run('fn first({name, ...rest}: dict) -> int { return rest["age"] }\nlet r = first({"name": "Ada", "age": 30})')
    check("dict destruct rest", i._env.get("r"), 30)

def test_dict_destruct_three_fields():
    i = run('fn vol({w, h, d}: dict) -> float { return w * h * d }\nlet r = vol({"w": 2.0, "h": 3.0, "d": 4.0})')
    check_close("dict destruct three fields", i._env.get("r"), 24.0)

def test_array_destruct_basic():
    i = run('fn add([a, b]: []) -> int { return a + b }\nlet r = add([3, 7])')
    check("array destruct basic", i._env.get("r"), 10)

def test_array_destruct_head():
    i = run('fn head([h, ...rest]: []) -> int { return h }\nlet r = head([42, 1, 2])')
    check("array destruct head", i._env.get("r"), 42)

def test_array_destruct_rest():
    i = run('fn tail([h, ...rest]: []) -> [] { return rest }\nlet r = tail([1, 2, 3, 4])')
    check("array destruct rest", i._env.get("r"), [2, 3, 4])

def test_array_destruct_multiple():
    i = run('fn third([a, b, c, ...rest]: []) -> int { return c }\nlet r = third([10, 20, 30, 40])')
    check("array destruct third element", i._env.get("r"), 30)

def test_array_destruct_empty_rest():
    i = run('fn pair([a, b]: []) -> [] { return [a, b] }\nlet r = pair([5, 6])')
    check("array destruct no rest", i._env.get("r"), [5, 6])

def test_dict_destruct_with_struct():
    i = run('''
struct Point { x: float = 0.0\n y: float = 0.0 }
fn from_dict({x, y}: dict) -> Point {
    return Point{x: x, y: y}
}
let p = from_dict({"x": 3.0, "y": 4.0})
''')
    inst = i._env.get("p")
    check_close("dict destruct into struct x", inst.fields["x"], 3.0)
    check_close("dict destruct into struct y", inst.fields["y"], 4.0)

# ─────────────────────────────────────────────────────────────────────────────
# 4. Named return values
# ─────────────────────────────────────────────────────────────────────────────

def test_named_return_basic():
    i = run('fn bounds() -> (lo: float, hi: float) { return (lo: 0.0, hi: 100.0) }\nlet r = bounds()')
    check_close("named return lo", i._env.get("r")["lo"], 0.0)
    check_close("named return hi", i._env.get("r")["hi"], 100.0)

def test_named_return_conditional():
    i = run('''
fn minmax(a: float, b: float) -> (mn: float, mx: float) {
    if a < b { return (mn: a, mx: b) }
    return (mn: b, mx: a)
}
let r = minmax(7.0, 3.0)
''')
    check_close("named return mn", i._env.get("r")["mn"], 3.0)
    check_close("named return mx", i._env.get("r")["mx"], 7.0)

def test_named_return_three_fields():
    i = run('''
fn stats(a: float, b: float, c: float) -> (sum: float, avg: float, count: int) {
    return (sum: a+b+c, avg: (a+b+c)/3.0, count: 3)
}
let r = stats(1.0, 2.0, 3.0)
''')
    check_close("named return sum",   i._env.get("r")["sum"],   6.0)
    check_close("named return avg",   i._env.get("r")["avg"],   2.0)
    check("named return count", i._env.get("r")["count"], 3)

def test_named_return_used_in_expr():
    i = run('''
fn divmod(a: int, b: int) -> (q: int, rem: int) {
    return (q: a // b, rem: a % b)
}
let r = divmod(17, 5)
let total = r["q"] * 5 + r["rem"]
''')
    check("named return used in expr", i._env.get("total"), 17)

def test_named_return_with_destruct():
    # Named return value used with a with expression
    i = run('''
fn origin() -> (x: float, y: float) {
    return (x: 0.0, y: 0.0)
}
let p = origin()
let q = with p { .x = 5.0 }
''')
    check_close("named return + with x", i._env.get("q")["x"], 5.0)
    check_close("named return + with y", i._env.get("q")["y"], 0.0)

# ─────────────────────────────────────────────────────────────────────────────
# 5. Already-implemented features (regression smoke)
# ─────────────────────────────────────────────────────────────────────────────

def test_impl_operator_overload():
    i = run('''
struct V2 { x: float = 0.0\n y: float = 0.0 }
impl Add for V2 {
    fn +(other: V2) -> V2 {
        return V2{x: self.x + other.x, y: self.y + other.y}
    }
}
let a = V2{x: 1.0, y: 2.0}
let b = V2{x: 3.0, y: 4.0}
let c = a + b
''')
    check_close("impl + x", i._env.get("c").fields["x"], 4.0)
    check_close("impl + y", i._env.get("c").fields["y"], 6.0)

def test_const_eval():
    i = run("const TAU: float = 6.28318\nlet r = TAU / 2.0")
    check_close("const float", i._env.get("r"), 3.14159)

def test_triple_string():
    i = run('let s = """hello\nworld"""')
    check("triple string", i._env.get("s"), "hello\nworld")

def test_chained_comparison():
    i = run("let x = 5\nlet r = 0 < x < 10")
    check("chained comparison true", i._env.get("r"), True)

def test_chained_comparison_false():
    i = run("let x = 15\nlet r = 0 < x < 10")
    check("chained comparison false", i._env.get("r"), False)

def test_is_type_check():
    i = run("let x = 42\nlet r = x is int")
    check("is type check", i._env.get("r"), True)

def test_labeled_loop():
    i = run('''
let r = 0
outer: for j in 0..3 {
    for k in 0..3 {
        if k == 1 { break outer }
        r = r + 1
    }
}
''')
    check("labeled loop break outer", i._env.get("r"), 1)

# ─────────────────────────────────────────────────────────────────────────────
# 6. Version
# ─────────────────────────────────────────────────────────────────────────────

def test_version_is_220():
    if repl_mod.VERSION == "2.2.0":
        ok("version_is_2.2.0")
    else:
        fail("version_is_2.2.0", f"got {repl_mod.VERSION}")

# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("test_v220.py — v2.2.0: language enhancements")
    print("=" * 60)

    # ??=
    test_nullish_assign_nil()
    test_nullish_assign_non_nil()
    test_nullish_assign_zero_is_not_nil()
    test_nullish_assign_false_is_not_nil()
    test_nullish_assign_string()
    test_nullish_assign_chain()
    test_nullish_assign_expr_rhs()
    test_nullish_assign_only_once()

    # with
    test_with_dict_changes_field()
    test_with_dict_keeps_other_fields()
    test_with_dict_does_not_mutate_original()
    test_with_dict_multiple_fields()
    test_with_struct_changes_field()
    test_with_struct_keeps_field()
    test_with_struct_no_mutation()
    test_with_chained()
    test_with_new_field()

    # destructuring params
    test_dict_destruct_basic()
    test_dict_destruct_subset()
    test_dict_destruct_rest()
    test_dict_destruct_three_fields()
    test_array_destruct_basic()
    test_array_destruct_head()
    test_array_destruct_rest()
    test_array_destruct_multiple()
    test_array_destruct_empty_rest()
    test_dict_destruct_with_struct()

    # named return
    test_named_return_basic()
    test_named_return_conditional()
    test_named_return_three_fields()
    test_named_return_used_in_expr()
    test_named_return_with_destruct()

    # regressions
    test_impl_operator_overload()
    test_const_eval()
    test_triple_string()
    test_chained_comparison()
    test_chained_comparison_false()
    test_is_type_check()
    test_labeled_loop()

    # version
    test_version_is_220()

    total = PASS + FAIL
    print("=" * 60)
    print(f"{PASS}/{total} passed  ({FAIL} failed)")
    sys.exit(0 if FAIL == 0 else 1)
