#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v140.py  InScript v1.4.0 feature tests

  * defer statement
  * repeat..until loop
  * Type-narrowing match arms  (case int x, case string s, case Vec2 v)
  * Generic constraints         (fn max<T: Comparable>)
  * str() builtin already in scope (regression)

Run:  python3 test_v140.py
"""

import sys, io
from interpreter import Interpreter
from errors import InScriptRuntimeError

PASS = FAIL = 0

def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  OK  {name}")
        PASS += 1
    else:
        print(f"  FAIL  {name}" + (f"  [{detail}]" if detail else ""))
        FAIL += 1

def section(t): print(f"\n--- {t} ---")

def run(code):
    buf = io.StringIO(); sys.stdout = buf
    try:
        Interpreter().execute(code)
        sys.stdout = sys.__stdout__
        return buf.getvalue().strip(), None
    except Exception as e:
        sys.stdout = sys.__stdout__
        return None, str(e)

# ── 1. defer ──────────────────────────────────────────────────────────────────
section("1. defer")

out, err = run("""
fn f() {
    defer print("c")
    defer print("b")
    defer print("a")
    print("body")
}
f()
""")
ok("defer runs LIFO after body", out == "body\na\nb\nc", out)

out, err = run("""
fn f() {
    defer print("deferred")
    return 42
}
print(f())
""")
ok("defer runs before return value consumed", out == "deferred\n42", out)

out, err = run("""
fn cleanup() {
    defer print("cleaned")
    throw "oops"
}
try { cleanup() } catch e { print("caught") }
""")
ok("defer runs even on throw", out == "cleaned\ncaught", out)

out, err = run("""
fn f() {
    let i = 0
    while i < 3 {
        defer print("d" ++ str(i))
        i = i + 1
    }
}
f()
""")
ok("multiple defer in loop accumulate", out is not None and "d" in out, out)

out, err = run("""
fn outer() {
    defer print("outer-defer")
    fn inner() {
        defer print("inner-defer")
        print("inner-body")
    }
    inner()
    print("outer-body")
}
outer()
""")
ok("nested fn each has own defer stack",
   out == "inner-body\ninner-defer\nouter-body\nouter-defer", out)

# ── 2. repeat..until ──────────────────────────────────────────────────────────
section("2. repeat..until")

out, _ = run("""
let i = 0
let s = 0
repeat {
    s = s + i
    i = i + 1
} until i >= 5
print(s)
""")
ok("repeat..until sums 0..4 = 10", out == "10", out)

out, _ = run("""
let ran = false
repeat {
    ran = true
} until true
print(ran)
""")
ok("repeat body runs at least once even if condition true initially", out == "true", out)

out, _ = run("""
let i = 0
repeat {
    i = i + 1
    if i == 3 { break }
} until i >= 10
print(i)
""")
ok("break exits repeat..until", out == "3", out)

out, _ = run("""
let i = 0
let evens = 0
repeat {
    i = i + 1
    if i % 2 != 0 { continue }
    evens = evens + 1
} until i >= 6
print(evens)
""")
ok("continue skips in repeat..until", out == "3", out)

# ── 3. Type-narrowing match ───────────────────────────────────────────────────
section("3. Type-narrowing match")

out, _ = run("""
fn kind(v) {
    match v {
        case int x    { return "int:" ++ str(x) }
        case float f  { return "float:" ++ str(f) }
        case string s { return "str:" ++ s }
        case bool b   { return "bool:" ++ str(b) }
        case _ { return "other" }
    }
}
print(kind(42))
print(kind(3.14))
print(kind("hi"))
print(kind(true))
print(kind(nil))
""")
ok("primitive type narrowing all branches", out == "int:42\nfloat:3.14\nstr:hi\nbool:true\nother", out)

out, _ = run("""
fn describe(v) {
    match v {
        case int x { print(x * 2) }
        case _ { print("skip") }
    }
}
describe(5)
describe("x")
""")
ok("bound variable is usable in body", out == "10\nskip", out)

out, _ = run("""
struct Circle { r: float = 0.0 }
struct Square { s: float = 0.0 }
fn area(shape) {
    match shape {
        case Circle c { return 3.14159 * c.r * c.r }
        case Square sq { return sq.s * sq.s }
        case _ { return 0.0 }
    }
}
print(area(Circle{r: 1.0}))
print(area(Square{s: 4.0}))
""")
ok("struct type narrowing", out == "3.14159\n16.0", out)

out, _ = run("""
fn f(v) {
    match v {
        case int x if x > 10 { return "big" }
        case int x { return "small" }
        case _ { return "other" }
    }
}
print(f(20))
print(f(5))
print(f("x"))
""")
ok("type narrowing with guard", out == "big\nsmall\nother", out)

out, _ = run("""
fn f(v) {
    match v {
        case int x  { print("int") }
        case string s { print("str") }
    }
}
f(1)
f("a")
""")
ok("no wildcard arm needed when all cases covered", out == "int\nstr", out)

# ── 4. Generic constraints ────────────────────────────────────────────────────
section("4. Generic constraints")

out, err = run("""
fn biggest<T: Comparable>(a: T, b: T, c: T) -> T {
    let m = a
    if b > m { m = b }
    if c > m { m = c }
    return m
}
print(biggest(3, 1, 4))
print(biggest("a", "c", "b"))
""")
ok("Comparable: ints and strings pass", out == "4\nc" and err is None, out)

_, err = run("""
fn biggest<T: Comparable>(a: T, b: T, c: T) -> T {
    if a > b { return a }
    return b
}
biggest([1], [2], [3])
""")
ok("Comparable: array rejected", err is not None and "constraint" in err.lower(), err[:80] if err else "no err")

_, err = run("""
fn biggest<T: Comparable>(a: T, b: T, c: T) -> T {
    if a > b { return a }
    return b
}
fn dummy() {}
biggest(dummy, dummy, dummy)
""")
ok("Comparable: function rejected", err is not None and "constraint" in err.lower(), err[:80] if err else "no err")

out, err = run("""
fn add_all<T: Numeric>(a: T, b: T, c: T) -> T {
    return a + b + c
}
print(add_all(1, 2, 3))
print(add_all(1.5, 2.5, 3.0))
""")
ok("Numeric: int and float pass", out == "6\n7.0" and err is None, out)

_, err = run("""
fn add_all<T: Numeric>(a: T, b: T, c: T) -> T {
    return a + b + c
}
add_all("a", "b", "c")
""")
ok("Numeric: string rejected", err is not None and "constraint" in err.lower())

out, err = run("""
interface Drawable {
    fn draw()
}
struct Sprite {
    name: string = ""
    fn draw() { print("drawing " ++ self.name) }
}
fn render<T: Drawable>(item: T) {
    item.draw()
}
render(Sprite{name: "hero"})
""")
ok("interface as constraint: Drawable Sprite passes", out == "drawing hero" and err is None, f"{out!r} {err}")

_, err = run("""
interface Drawable { fn draw() }
struct Plain { x: int = 0 }
fn render<T: Drawable>(item: T) { }
render(Plain{x: 1})
""")
ok("interface as constraint: non-implementing struct rejected",
   err is not None and "constraint" in err.lower(), err[:80] if err else "no err")

# ── 5. Regression ─────────────────────────────────────────────────────────────
section("5. Regression")

regressions = [
    ("str()",        'print(str(42))',         "42"),
    ("closures",     "fn mk(n){fn f(){return n} return f} print(mk(7)())", "7"),
    ("TCO",          "fn f(n){if n<=0{return 0} return f(n-1)} print(f(5000))", "0"),
    ("mat4",         'import "mat4" as m; print(m.det(m.identity()))', "1.0"),
    ("generic Stack","struct Stack<T>{items:[]=[];fn push(v:T){self.items=self.items+[v]}} let s=Stack<int>{}; s.push(1); print(s.items)", "[1]"),
    ("existing match","let x=2; match x{case 1{print('a')} case 2{print('b')} case _{print('c')}}", "b"),
    ("ADT match",    "enum S{A(n:int),B} let v=S.A(n:5); match v{case S.A{print(n)} case S.B{print('b')}}", "5"),
]
for name, code, want in regressions:
    out, err = run(code)
    ok(f"regression: {name}", out == want and err is None, f"got={out!r} err={err!r}")

total = PASS + FAIL
print(f"""
{'='*56}
  v1.4.0 Test Results: {PASS}/{total} passed
  {'ALL PASS' if FAIL == 0 else f'{FAIL} FAILED'}
{'='*56}
""")
sys.exit(0 if FAIL == 0 else 1)
