"""
test_v203.py — InScript v2.0.3
Spread operator `...` — complete coverage.

Features:
  - `fn(...args)` — spread array into fn call arguments
  - `fn(a, ...rest)` — spread with leading positional args
  - `fn(...a, ...b)` — double spread
  - `[...a, ...b]` — spread in array literal
  - `[...range]` — spread range into array
  - `P{...dict}` — spread dict into struct initializer
  - `P{...base, field: val}` — spread struct instance with override
  - `print(...arr)` — spread in print()
  - `fn(...args: T)` — rest parameter declaration
  - rest with zero args, rest after positional params
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from interpreter import Interpreter

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

# ── 1. Spread into function calls ─────────────────────────────────────────────

def test_spread_basic():
    check("spread_basic",
          "fn sum3(a:int,b:int,c:int)->int{return a+b+c}\nlet args=[1,2,3]\nlet r=sum3(...args)",
          "r", 6)

def test_spread_with_leading_positional():
    check("spread_with_leading_positional",
          "fn f(a:int,b:int,c:int)->int{return a+b+c}\nlet tail=[20,30]\nlet r=f(10,...tail)",
          "r", 60)

def test_spread_trailing_positional():
    check("spread_trailing_positional",
          "fn f(a:int,b:int,c:int)->int{return a+b+c}\nlet r=f(...[1,2],3)",
          "r", 6)

def test_double_spread():
    check("double_spread",
          "fn f(a:int,b:int,c:int,d:int)->int{return a+b+c+d}\nlet x=[1,2]\nlet y=[3,4]\nlet r=f(...x,...y)",
          "r", 10)

def test_spread_empty_array():
    check("spread_empty_array",
          "fn f(a:int,b:int)->int{return a+b}\nlet e=[]\nlet r=f(1,...e,2)",
          "r", 3)

def test_spread_string_array():
    check("spread_string_array",
          'fn join3(a:string,b:string,c:string)->string{return a++b++c}\nlet parts=["x","y","z"]\nlet r=join3(...parts)',
          "r", "xyz")

def test_spread_inline_literal():
    check("spread_inline_literal",
          "fn sum3(a:int,b:int,c:int)->int{return a+b+c}\nlet r=sum3(...[4,5,6])",
          "r", 15)

def test_spread_fn_result():
    check("spread_fn_result",
          "fn get_args()->Array<int>{return [7,8,9]}\nfn sum3(a:int,b:int,c:int)->int{return a+b+c}\nlet r=sum3(...get_args())",
          "r", 24)

# ── 2. Spread in array literals ───────────────────────────────────────────────

def test_spread_concat_arrays():
    check("spread_concat_arrays",
          "let a=[1,2]\nlet b=[3,4]\nlet c=[...a,...b]",
          "c", [1,2,3,4])

def test_spread_array_with_literals():
    check("spread_array_with_literals",
          "let a=[2,3]\nlet b=[0,1,...a,4,5]",
          "b", [0,1,2,3,4,5])

def test_spread_range_into_array():
    check("spread_range_into_array",
          "let a=[...0..5]",
          "a", [0,1,2,3,4])

def test_spread_range_inclusive():
    check("spread_range_inclusive",
          "let a=[...1..=5]",
          "a", [1,2,3,4,5])

def test_spread_range_step():
    check("spread_range_step",
          "let a=[...0..10 step 2]",
          "a", [0,2,4,6,8])

def test_spread_three_arrays():
    check("spread_three_arrays",
          "let a=[1]\nlet b=[2]\nlet c=[3]\nlet d=[...a,...b,...c]",
          "d", [1,2,3])

# ── 3. Spread in struct initializers ─────────────────────────────────────────

def test_spread_dict_into_struct():
    check("spread_dict_into_struct",
          'let d={"x":3.0,"y":4.0}\nstruct P{x:float=0.0\ny:float=0.0}\nlet p=P{...d}\nlet r=p.x',
          "r", 3.0)

def test_spread_struct_instance():
    check("spread_struct_instance",
          'struct P{x:float=0.0\ny:float=0.0}\nlet base=P{x:1.0,y:2.0}\nlet p=P{...base}\nlet r=p.y',
          "r", 2.0)

def test_spread_struct_with_override():
    check("spread_struct_with_override",
          'struct P{x:float=0.0\ny:float=0.0}\nlet base=P{x:1.0,y:2.0}\nlet p=P{...base,y:99.0}\nlet r=p.y',
          "r", 99.0)

def test_spread_struct_override_preserves_rest():
    check("spread_struct_override_preserves_rest",
          'struct P{x:int=0\ny:int=0}\nlet base=P{x:5,y:10}\nlet p=P{...base,x:99}\nlet r=p.y',
          "r", 10)

# ── 4. Spread in print() ─────────────────────────────────────────────────────

def test_spread_in_print():
    no_error("spread_in_print",
             "let a=[1,2,3]\nprint(...a)")

def test_spread_in_print_mixed():
    no_error("spread_in_print_mixed",
             'let a=["b","c"]\nprint("a",...a,"d")')

# ── 5. Rest parameters ────────────────────────────────────────────────────────

def test_rest_param_basic():
    check("rest_param_basic",
          "fn vsum(...args:int)->int{let s=0\nfor x in args{s=s+x}\nreturn s}\nlet r=vsum(1,2,3,4,5)",
          "r", 15)

def test_rest_param_zero_args():
    check("rest_param_zero_args",
          "fn vsum(...args:int)->int{let s=0\nfor x in args{s=s+x}\nreturn s}\nlet r=vsum()",
          "r", 0)

def test_rest_param_one_arg():
    check("rest_param_one_arg",
          "fn vsum(...args:int)->int{let s=0\nfor x in args{s=s+x}\nreturn s}\nlet r=vsum(42)",
          "r", 42)

def test_rest_after_positional():
    check("rest_after_positional",
          'fn f(prefix:string,...nums:int)->string{let s=0\nfor n in nums{s=s+n}\nreturn prefix++string(s)}\nlet r=f("sum:",1,2,3)',
          "r", "sum:6")

def test_rest_len():
    check("rest_len",
          "fn count(...args:int)->int{return args.len}\nlet r=count(10,20,30)",
          "r", 3)

def test_rest_spread_forward():
    check("rest_spread_forward",
          "fn add3(a:int,b:int,c:int)->int{return a+b+c}\nfn relay(...args:int)->int{return add3(...args)}\nlet r=relay(1,2,3)",
          "r", 6)

# ── 6. Spread in nested contexts ─────────────────────────────────────────────

def test_spread_in_map_arg():
    check("spread_in_map_arg",
          "let parts=[[1,2],[3,4]]\nlet flat=[]\nfor chunk in parts{flat=[...flat,...chunk]}\n",
          "flat", [1,2,3,4])

def test_spread_in_fn_returning_array():
    check("spread_in_fn_returning_array",
          "fn prepend(x:int,arr:Array<int>)->Array<int>{return [x,...arr]}\nlet r=prepend(0,[1,2,3])",
          "r", [0,1,2,3])

def test_spread_in_for_accumulator():
    check("spread_in_for_accumulator",
          "let result=[]\nfor i in 0..3{result=[...result,i*i]}",
          "result", [0,1,4])

# ── 7. version ────────────────────────────────────────────────────────────────

def test_version_is_203():
    import repl
    if repl.VERSION == "2.0.3":
        ok("version_is_2.0.3")
    else:
        fail("version_is_2.0.3", f"got {repl.VERSION}")

# ── run all ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("test_v203.py — v2.0.3: spread operator complete coverage")
    print("=" * 60)

    test_spread_basic()
    test_spread_with_leading_positional()
    test_spread_trailing_positional()
    test_double_spread()
    test_spread_empty_array()
    test_spread_string_array()
    test_spread_inline_literal()
    test_spread_fn_result()

    test_spread_concat_arrays()
    test_spread_array_with_literals()
    test_spread_range_into_array()
    test_spread_range_inclusive()
    test_spread_range_step()
    test_spread_three_arrays()

    test_spread_dict_into_struct()
    test_spread_struct_instance()
    test_spread_struct_with_override()
    test_spread_struct_override_preserves_rest()

    test_spread_in_print()
    test_spread_in_print_mixed()

    test_rest_param_basic()
    test_rest_param_zero_args()
    test_rest_param_one_arg()
    test_rest_after_positional()
    test_rest_len()
    test_rest_spread_forward()

    test_spread_in_map_arg()
    test_spread_in_fn_returning_array()
    test_spread_in_for_accumulator()

    test_version_is_203()

    total = passed + failed
    print("=" * 60)
    print(f"{passed}/{total} passed  ({failed} failed)")
    if failed:
        sys.exit(1)
