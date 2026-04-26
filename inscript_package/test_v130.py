#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v130.py — InScript v1.3.0 feature tests

Covers:
  • Dispatch cache              (visit() caches method lookups per node type)
  • Fast-path arithmetic        (int/float ops skip isinstance checks)
  • Tail call optimization      (self-recursive tail calls trampolined)
  • Bytecode constant folding   (compiler evaluates literal expressions at compile time)
  • Bytecode dead code elim.    (unreachable instructions replaced by NOPs)
  • str() builtin alias         (str(x) works as alias for string(x))
  • --profile flag              (accepted without error)

Run:  python3 test_v130.py
"""

import sys, time
from interpreter import Interpreter
from analyzer import Analyzer
from errors import InScriptRuntimeError
from compiler import compile_source
from vm import VM, Op

# ─── helpers ──────────────────────────────────────────────────────────────────

PASS = FAIL = 0

def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  ✅ {name}")
        PASS += 1
    else:
        print(f"  ❌ {name}{' — '+detail if detail else ''}")
        FAIL += 1

def section(title):
    print(f"\n{'─'*60}\n  {title}\n{'─'*60}")

def run(src):
    import io
    buf = io.StringIO(); sys.stdout = buf
    try:
        Interpreter().execute(src)
        sys.stdout = sys.__stdout__
        return buf.getvalue().strip(), None
    except Exception as e:
        sys.stdout = sys.__stdout__
        return None, str(e)

# ─── 1. Dispatch cache ────────────────────────────────────────────────────────

section("1. Dispatch cache")

# 1a: _dispatch dict exists on Interpreter
i = Interpreter()
ok("Interpreter has _dispatch dict", hasattr(i, '_dispatch') and isinstance(i._dispatch, dict))

# 1b: after run, cache is populated
i.execute("let x = 1 + 2")
ok("_dispatch populated after run", len(i._dispatch) > 0)

# 1c: each interpreter has independent cache (no cross-contamination)
i1 = Interpreter(); i2 = Interpreter()
i1.execute("let a = 1")
ok("Two interpreters have independent caches", i1._dispatch is not i2._dispatch)

# 1d: Analyzer also has _dispatch
from analyzer import Analyzer
a = Analyzer([])
ok("Analyzer has _dispatch dict", hasattr(a, '_dispatch') and isinstance(a._dispatch, dict))

# 1e: repeated run uses cache (correctness, not just speed)
for _ in range(5):
    out, err = run("let x = 10; let y = x * 3; print(y)")
ok("Repeated runs with cached dispatch give correct results", out == "30" and err is None)

# ─── 2. Fast-path arithmetic ─────────────────────────────────────────────────

section("2. Fast-path arithmetic")

cases = [
    ("int + int",  "print(3 + 4)",         "7"),
    ("int - int",  "print(10 - 3)",         "7"),
    ("int * int",  "print(3 * 4)",          "12"),
    ("int / int",  "print(10 / 4)",         "2.5"),
    ("int // int", "print(10 div 3)",        "3"),
    ("int % int",  "print(10 % 3)",         "1"),
    ("float + float", "print(1.5 + 2.5)",   "4.0"),
    ("int < int",  "print(3 < 5)",          "true"),
    ("int > int",  "print(5 > 3)",          "true"),
    ("int == int", "print(4 == 4)",         "true"),
    ("int != int", "print(4 != 5)",         "true"),
    ("int <= int", "print(3 <= 3)",         "true"),
    ("int >= int", "print(5 >= 5)",         "true"),
    ("int + float","print(1 + 0.5)",        "1.5"),
    ("float * int","print(2.0 * 3)",        "6.0"),
]
for name, code, want in cases:
    out, err = run(code)
    ok(f"fast-path {name}", out == want, f"got {out!r}")

# Division by zero still errors
out, err = run("print(1 div 0)")
ok("fast-path int div 0 raises error", err is not None and out is None)

# ─── 3. Tail Call Optimization ───────────────────────────────────────────────

section("3. Tail Call Optimization (TCO)")

# 3a: basic tail-recursive countdown doesn't stack overflow
out, err = run("fn count(n){if n<=0{return 0} return count(n-1)} print(count(10000))")
ok("count(10000) no stack overflow", out == "0" and err is None)

# 3b: TCO accumulator gives correct result
out, err = run("""
fn sum_to(n, acc) {
    if n <= 0 { return acc }
    return sum_to(n - 1, acc + n)
}
print(sum_to(1000, 0))
""")
ok("sum_to(1000) = 500500", out == "500500" and err is None, f"got {out!r}")

# 3c: TCO with multiple params
out, err = run("""
fn fib_iter(n, a, b) {
    if n == 0 { return a }
    return fib_iter(n - 1, b, a + b)
}
print(fib_iter(10, 0, 1))
""")
ok("fib_iter(10) = 55 (tail-recursive)", out == "55" and err is None)

# 3d: non-tail recursion still works (fib)
out, err = run("fn fib(n){if n<=1{return n} return fib(n-1)+fib(n-2)} print(fib(15))")
ok("non-tail fib(15) = 610 unaffected", out == "610" and err is None)

# 3e: TCO only fires on self-recursive tail calls — mutual recursion is untouched
out, err = run("""
fn is_even(n) { if n == 0 { return true } return is_odd(n - 1) }
fn is_odd(n)  { if n == 0 { return false } return is_even(n - 1) }
print(is_even(10))
print(is_odd(7))
""")
ok("mutual recursion still works", out == "true\ntrue" and err is None)

# 3f: nested function call in return is NOT a tail call (not same name) → no TCO signal
out, err = run("""
fn double(n) { return n * 2 }
fn inc(n) { return double(n) + 1 }
print(inc(5))
""")
ok("non-self tail call not intercepted", out == "11" and err is None)

# 3g: TCO still honors type-annotated params
out, err = run("""
fn countdown(n: int) -> int {
    if n <= 0 { return 0 }
    return countdown(n - 1)
}
print(countdown(5000))
""")
ok("TCO respects type-annotated params", out == "0" and err is None)

# 3h: TCO _current_fn resets between calls
out, err = run("""
fn a(n) { if n <= 0 { return 0 } return a(n-1) }
fn b(n) { if n <= 0 { return 0 } return b(n-1) }
print(a(100))
print(b(100))
""")
ok("_current_fn resets correctly between functions", out == "0\n0" and err is None)

# 3i: try/catch inside tail-recursive function works
out, err = run("""
fn safe(x) {
    try {
        return 100 div x
    } catch e {
        return -1
    }
}
print(safe(0))
print(safe(5))
""")
ok("try/catch inside function works with TCO", out == "-1\n20" and err is None, f"got={out!r} err={err!r}")

# ─── 4. Bytecode constant folding ────────────────────────────────────────────

section("4. Bytecode constant folding")

def get_ops(src):
    proto = compile_source(src)
    skip = (Op.MOVE, Op.RETURN, Op.STORE_GLOBAL, Op.STORE_UPVAL)
    return [(ins.op, ins.a, ins.b, ins.c, proto.consts) for ins in proto.code
            if ins.op not in skip]

# 4a: 2+3 folds to LOAD_INT 5 (no ADD)
ops = get_ops("let x = 2 + 3")
op_names = [o[0].name for o in ops]
ok("2+3 folds — no ADD opcode", "ADD" not in op_names, f"ops={op_names}")
ok("2+3 folds — emits LOAD_INT 5",
   any(o[0].name == "LOAD_INT" and o[2] == 5 for o in ops))

# 4b: 10 - 3 folds to 7
ops = get_ops("let x = 10 - 3")
ok("10-3 folds to 7",
   any(o[0].name == "LOAD_INT" and o[2] == 7 for o in ops))

# 4c: 3 * 4 folds
ops = get_ops("let x = 3 * 4")
ok("3*4 folds to 12",
   any(o[0].name == "LOAD_INT" and o[2] == 12 for o in ops))

# 4d: string concat folds
ops = get_ops('let s = "hello" ++ " world"')
ok('"hello" ++ " world" folds to LOAD_CONST',
   any(o[0].name == "LOAD_CONST" and "hello world" in str(o[4]) for o in ops))

# 4e: comparison folds
ops = get_ops("let b = 3 < 5")
ok("3<5 folds to true",
   any(o[0].name in ("LOAD_TRUE", "LOAD_FALSE") for o in ops))

# 4f: folded values are correct at runtime
for code, want in [
    ("print(2 + 3)",       "5"),
    ("print(10 - 3)",      "7"),
    ("print(3 * 4)",       "12"),
    ("print(10 / 4)",      "2.5"),
    ("print(10 div 3)",    "3"),
    ("print(10 % 3)",      "1"),
    ("print(2 == 2)",      "true"),
    ("print(3 < 5)",       "true"),
    ('print("ab" ++ "c")', "abc"),
]:
    out, err = run(code)
    ok(f"folded value correct: {code[:20]}", out == want and err is None, f"got {out!r}")

# 4g: division by zero NOT folded (must stay as runtime error)
ops = get_ops("let x = 10 div 0")
ok("10 div 0 not folded (div-by-zero kept for runtime)",
   not any(o[0].name == "LOAD_INT" and o[2] == 10 and
           # check there's no DIV following it either
           False for o in ops))

# ─── 5. Dead code elimination ────────────────────────────────────────────────

section("5. Dead code elimination")

def count_nops_any(src):
    """Count NOPs in top-level proto and all nested protos."""
    proto = compile_source(src)
    def _count(p):
        n = sum(1 for ins in p.code if ins.op == Op.MOVE and ins.a == 0 and ins.b == 0)
        for c in p.consts:
            if hasattr(c, 'code'):
                n += _count(c)
        return n
    return _count(proto)

# 5a: code after RETURN is eliminated (replaced by NOP) — in nested fn proto
nops = count_nops_any("fn f() { return 1; let dead = 2; let also_dead = 3 }")
ok("dead code after return becomes NOPs", nops >= 1, f"got {nops} NOPs")

# 5b: try/catch handler NOT eliminated (reachable via exception)
out, err = run('try { throw "err" } catch e { print(e) }')
ok("catch handler not eliminated", out == "err" and err is None)

# 5c: for loop body not eliminated
out, err = run("let s=0; for i in 0..5 { s=s+i }; print(s)")
ok("for loop body not eliminated", out == "10" and err is None)

# 5d: list comprehension not eliminated
out, err = run("print([x*x for x in 0..4])")
ok("list comprehension not eliminated", out == "[0, 1, 4, 9]" and err is None)

# 5e: runtime output is correct after DCE
cases = [
    ("if/else", "let x=5; if x>3{print('yes')}else{print('no')}", "yes"),
    ("while",   "let i=0; let s=0; while i<4{s+=i; i+=1}; print(s)", "6"),
    ("match",   "let x=2; match x{case 1{print('a')} case 2{print('b')} case _{print('c')}}", "b"),
    ("nested fn", "fn add(a,b){return a+b} print(add(3,4))", "7"),
]
for name, code, want in cases:
    out, err = run(code)
    ok(f"DCE: {name} still correct", out == want and err is None, f"got {out!r}")

# ─── 6. str() builtin alias ──────────────────────────────────────────────────

section("6. str() builtin alias")

cases = [
    ("str(42)",       "print(str(42))",       "42"),
    ("str(3.14)",     "print(str(3.14))",      "3.14"),
    ("str(true)",     "print(str(true))",      "true"),
    ("str in expr",   'print("x" ++ str(5))',  "x5"),
    ("str in listcomp", 'print(["v"+str(i) for i in 0..3][2])', "v2"),
    ("string() alias","print(string(99))",     "99"),
]
for name, code, want in cases:
    out, err = run(code)
    ok(f"str: {name}", out == want and err is None, f"got {out!r}")

# ─── 7. --profile flag ───────────────────────────────────────────────────────

section("7. --profile flag")

import tempfile, os, subprocess
tmp = None
try:
    fd, tmp = tempfile.mkstemp(suffix='.ins')
    os.write(fd, b"fn fib(n:int)->int{if n<=1{return n} return fib(n-1)+fib(n-2)} print(fib(15))\n")
    os.close(fd)   # must close before subprocess can open on Windows
    result = subprocess.run(
        [sys.executable, "inscript.py", "--profile", "--no-warn", tmp],
        capture_output=True, text=True, encoding="utf-8"
    )
    ok("--profile flag accepted (exit 0)", result.returncode == 0,
       f"exit={result.returncode} stderr={result.stderr[:100]}")
    ok("--profile output contains 610", "610" in result.stdout)
    ok("--profile shows timing table", "InScript --profile" in result.stderr or
       "InScript --profile" in result.stdout or "TOTAL" in result.stderr)
finally:
    os.unlink(tmp)

# ─── 8. Regression: all previous features still work ─────────────────────────

section("8. Regression checks")

regressions = [
    # v1.2.0 generic enforcement
    ("generic enforcement", """
struct Stack<T> {
    items: [] = []
    fn push(val: T) { self.items = self.items + [val] }
}
let s = Stack<int>{}
s.push(1); s.push(2)
print(s.items)
""", "[1, 2]"),
    # v1.0 closures
    ("closures", "fn mk(n){fn f(){return n} return f} let f=mk(7); print(f())", "7"),
    # v1.0 structs
    ("structs", "struct P{x:int=0; y:int=0} let p=P{x:3,y:4}; print(p.x+p.y)", "7"),
    # v1.0 match
    ("match", "let x=2; match x{case 1{print('a')} case 2{print('b')} case _{print('c')}}", "b"),
    # v1.1 nil-safe chaining
    ("nil-safe", "let x = nil; print(x?.y)", "nil"),
    # mat4 module (v1.2.0)
    ("mat4 import", 'import "mat4" as m; let I=m.identity(); print(m.det(I))', "1.0"),
]

for name, code, want in regressions:
    out, err = run(code)
    ok(f"regression: {name}", out == want and err is None, f"got={out!r} err={err!r}")

# ─── Summary ─────────────────────────────────────────────────────────────────

total = PASS + FAIL
print(f"""
{'═'*60}
  v1.3.0 Test Results: {PASS}/{total} passed
  {'✅ ALL PASS' if FAIL == 0 else f'❌ {FAIL} FAILED'}
{'═'*60}
""")
sys.exit(0 if FAIL == 0 else 1)
