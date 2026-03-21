# -*- coding: utf-8 -*-
"""
test_phase7.py — Phase 7: Operator Overloading Tests
=====================================================
Tests that struct types can define custom operator behaviour using:
    operator + (rhs) { ... }
    operator str ()  { ... }  (toString)
    operator len ()  { ... }
    operator [] (i)  { ... }  (index)
    operator - ()    { ... }  (unary negate)
    operator == / != / < / <= / > / >= (rhs) { ... }

Run:  python test_phase7.py
"""
import io, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from vm import run_source

PASS = FAIL = 0
FAILURES = []

def run(src):
    buf = io.StringIO(); sys.stdout = buf
    try:
        run_source(src); sys.stdout = sys.__stdout__
        return buf.getvalue().strip(), None
    except Exception as e:
        sys.stdout = sys.__stdout__
        return None, str(e)

def T(src, expected, label=None):
    global PASS, FAIL
    out, err = run(src)
    ok = (err is None and out == expected)
    if ok:
        PASS += 1
    else:
        FAIL += 1
        tag = label or src[:60].replace('\n',' ')
        got = err[:100] if err else repr(out)
        FAILURES.append(f"  FAIL  {tag}\n        got : {got}\n        want: {expected!r}")

def section(name):
    print(f"  {name}")

VEC2 = '''struct Vec2 {
    x: float
    y: float
    operator + (rhs) { return Vec2{x:self.x+rhs.x, y:self.y+rhs.y} }
    operator - (rhs) { return Vec2{x:self.x-rhs.x, y:self.y-rhs.y} }
    operator * (s)   { return Vec2{x:self.x*s,     y:self.y*s}     }
    operator / (s)   { return Vec2{x:self.x/s,     y:self.y/s}     }
    operator - ()    { return Vec2{x:-self.x,       y:-self.y}      }
    operator == (o)  { return self.x==o.x && self.y==o.y }
    operator < (o)   { return self.x*self.x+self.y*self.y < o.x*o.x+o.y*o.y }
    operator str ()  { return f"({self.x},{self.y})" }
    operator len ()  { return 2 }
}
'''

def run_all():
    # ── 7.1 Arithmetic operators ─────────────────────────────────────────────
    section("7.1  Arithmetic operators")

    T(VEC2 + '''
let a=Vec2{x:1.0,y:2.0}
let b=Vec2{x:3.0,y:4.0}
let c=a+b
print(c.x)
print(c.y)''', '4\n6', 'Vec2 +')

    T(VEC2 + '''
let a=Vec2{x:5.0,y:7.0}
let b=Vec2{x:2.0,y:3.0}
let c=a-b
print(c.x)
print(c.y)''', '3\n4', 'Vec2 -')

    T(VEC2 + '''
let v=Vec2{x:2.0,y:3.0}
let w=v*4.0
print(w.x)
print(w.y)''', '8\n12', 'Vec2 scalar *')

    T(VEC2 + '''
let v=Vec2{x:6.0,y:9.0}
let w=v/3.0
print(w.x)
print(w.y)''', '2\n3', 'Vec2 scalar /')

    T('''struct Fraction {
    n: int; d: int
    operator + (o) {
        return Fraction{n:self.n*o.d+o.n*self.d, d:self.d*o.d}
    }
    operator str () { return f"{self.n}/{self.d}" }
}
let a=Fraction{n:1,d:2}
let b=Fraction{n:1,d:3}
let c=a+b
print(str(c))''', '5/6', 'Fraction + str')

    # ── 7.2 Unary operators ──────────────────────────────────────────────────
    section("7.2  Unary operators")

    T(VEC2 + '''
let v=Vec2{x:3.0,y:-2.0}
let n=-v
print(n.x)
print(n.y)''', '-3\n2', 'unary negate')

    T(VEC2 + '''
let a=Vec2{x:1.0,y:2.0}
let b=Vec2{x:3.0,y:4.0}
let c=-(a+b)
print(c.x)
print(c.y)''', '-4\n-6', 'negate of sum')

    # ── 7.3 Equality operators ───────────────────────────────────────────────
    section("7.3  Equality operators")

    T(VEC2 + '''
let a=Vec2{x:1.0,y:2.0}
let b=Vec2{x:1.0,y:2.0}
let c=Vec2{x:9.0,y:2.0}
print(a==b)
print(a==c)''', 'true\nfalse', '==')

    T(VEC2 + '''
let a=Vec2{x:1.0,y:2.0}
let b=Vec2{x:1.0,y:2.0}
let c=Vec2{x:9.0,y:2.0}
print(a!=c)
print(a!=b)''', 'true\nfalse', '!= derived from ==')

    T('''struct Str {
    val: string
    operator == (o) { return self.val == o.val }
}
let a=Str{val:"hello"}
let b=Str{val:"hello"}
let c=Str{val:"world"}
print(a==b)
print(a!=c)''', 'true\ntrue', 'string wrapper ==')

    # ── 7.4 Comparison operators ─────────────────────────────────────────────
    section("7.4  Comparison operators")

    T(VEC2 + '''
let small=Vec2{x:1.0,y:0.0}
let big=Vec2{x:3.0,y:4.0}
print(small<big)
print(big<small)''', 'true\nfalse', '<')

    T('''struct Priority {
    level: int
    operator <  (o) { return self.level < o.level }
    operator <= (o) { return self.level <= o.level }
    operator >  (o) { return self.level > o.level }
    operator >= (o) { return self.level >= o.level }
}
let low=Priority{level:1}
let mid=Priority{level:5}
let hi=Priority{level:10}
print(low<mid)
print(hi>mid)
print(mid<=mid)
print(mid>=mid)''', 'true\ntrue\ntrue\ntrue', 'all comparison ops')

    T('''struct Version {
    major: int; minor: int
    operator < (o) {
        if self.major != o.major { return self.major < o.major }
        return self.minor < o.minor
    }
}
let v1=Version{major:1,minor:9}
let v2=Version{major:2,minor:0}
let v3=Version{major:1,minor:5}
print(v1<v2)
print(v3<v1)''', 'true\ntrue', 'complex comparison logic')

    # ── 7.5 str operator (toString) ─────────────────────────────────────────
    section("7.5  str operator (toString)")

    T(VEC2 + 'print(str(Vec2{x:3.0,y:4.0}))', '(3,4)', 'str(v)')

    T(VEC2 + '''
let a=Vec2{x:1.0,y:2.0}
let b=Vec2{x:3.0,y:4.0}
let c=a+b
print(str(c))''', '(4,6)', 'str of computed result')

    T('''struct Matrix2x2 {
    a: float; b: float
    c: float; d: float
    operator str () { return f"[[{self.a},{self.b}],[{self.c},{self.d}]]" }
}
let m=Matrix2x2{a:1.0,b:2.0,c:3.0,d:4.0}
print(str(m))''', '[[1,2],[3,4]]', 'matrix str')

    # ── 7.6 [] (index) operator ──────────────────────────────────────────────
    section("7.6  [] index operator")

    T('''struct Matrix {
    data: array
    cols: int
    operator [] (i) { return self.data[i] }
}
let m=Matrix{data:[10,20,30,40],cols:2}
print(m[0])
print(m[3])''', '10\n40', '[] basic')

    T('''struct Grid {
    rows: array
    operator [] (row) { return self.rows[row] }
}
let g=Grid{rows:[[1,2,3],[4,5,6],[7,8,9]]}
print(g[1][2])
print(g[2][0])''', '6\n7', '[] returning array')

    T('''struct BitSet {
    bits: array
    operator [] (i) { return self.bits[i] }
}
let b=BitSet{bits:[1,0,1,1,0]}
print(b[0])
print(b[1])
print(b[2])
print(b[3])''', '1\n0\n1\n1', '[] array-backed index')

    # ── 7.7 len operator ─────────────────────────────────────────────────────
    section("7.7  len operator")

    T('''struct MySet {
    items: array
    operator len () { return self.items.length }
}
let s=MySet{items:[1,2,3,4,5]}
print(len(s))''', '5', 'len basic')

    T(VEC2 + '''let v=Vec2{x:1.0,y:2.0}
print(len(v))''', '2', 'len constant 2')

    T('''struct SparseVec {
    data: array
    operator len () { return self.data.length }
}
let v=SparseVec{data:[1,0,3,0,5]}
print(len(v))''', '5', 'len of sparse vec')

    # ── 7.8 Operators in control flow ────────────────────────────────────────
    section("7.8  Operators in control flow")

    T(VEC2 + '''
let a=Vec2{x:1.0,y:0.0}
let b=Vec2{x:3.0,y:4.0}
if a<b { print("a smaller") } else { print("b smaller") }''', 'a smaller', 'op in if')

    T('''struct Counter {
    n: int
    operator < (o) { return self.n < o.n }
    operator + (o) { return Counter{n:self.n+1} }
}
let c=Counter{n:0}
let limit=Counter{n:3}
let sum=0
while c<limit {
    sum += c.n
    c=c+c
}
print(sum)''', '3', 'op in while')

    T(VEC2 + '''
let vecs=[Vec2{x:1.0,y:0.0}, Vec2{x:0.0,y:1.0}, Vec2{x:2.0,y:2.0}]
let total=Vec2{x:0.0,y:0.0}
for v in vecs {
    total = total + v
}
print(str(total))''', '(3,3)', 'op in for loop')

    # ── 7.9 Operator chaining ────────────────────────────────────────────────
    section("7.9  Operator chaining")

    T(VEC2 + '''
let a=Vec2{x:1.0,y:1.0}
let b=Vec2{x:2.0,y:2.0}
let c=Vec2{x:3.0,y:3.0}
let r=a+b+c
print(str(r))''', '(6,6)', 'chained +')

    T(VEC2 + '''
let a=Vec2{x:10.0,y:10.0}
let b=Vec2{x:2.0,y:2.0}
let c=Vec2{x:1.0,y:1.0}
let r=a-b-c
print(str(r))''', '(7,7)', 'chained -')

    T(VEC2 + '''
let v=Vec2{x:1.0,y:2.0}
let r=v*2.0*3.0
print(str(r))''', '(6,12)', 'chained *')

    # ── 7.10 Operators in functions ──────────────────────────────────────────
    section("7.10  Operators in functions")

    T(VEC2 + '''
fn dot(a, b) { return a.x*b.x + a.y*b.y }
fn length(v) { return sqrt(v.x*v.x + v.y*v.y) }
fn normalize(v) {
    let len = length(v)
    return v / len
}
let v=Vec2{x:3.0,y:4.0}
print(length(v))
let n=normalize(v)
print(n.x)''', '5\n0.6', 'vec2 in functions')

    T(VEC2 + '''
fn scale(v, s) { return v*s }
fn translate(v, d) { return v+d }
let pos=Vec2{x:1.0,y:1.0}
let delta=Vec2{x:2.0,y:0.0}
let moved=translate(scale(pos,2.0), delta)
print(str(moved))''', '(4,2)', 'chained function calls with ops')

    # ── 7.11 Multiple structs with operators ─────────────────────────────────
    section("7.11  Multiple structs with operators")

    T('''struct Vec2 {
    x: float; y: float
    operator + (o) { return Vec2{x:self.x+o.x, y:self.y+o.y} }
    operator str () { return f"V({self.x},{self.y})" }
}
struct Color {
    r: int; g: int; b: int
    operator + (o) { return Color{r:self.r+o.r, g:self.g+o.g, b:self.b+o.b} }
    operator str () { return f"C({self.r},{self.g},{self.b})" }
}
let v1=Vec2{x:1.0,y:2.0}; let v2=Vec2{x:3.0,y:4.0}
let c1=Color{r:10,g:20,b:30}; let c2=Color{r:5,g:5,b:5}
print(str(v1+v2))
print(str(c1+c2))''', 'V(4,6)\nC(15,25,35)', 'two structs with operators')

    # ── 7.12 Operators with inheritance ──────────────────────────────────────
    section("7.12  Operators with inheritance")

    T('''struct Shape {
    color: string
}
struct Circle extends Shape {
    r: float
    operator == (o) { return self.r == o.r }
    operator str ()  { return f"Circle(r={self.r},c={self.color})" }
}
let c1=Circle{r:5.0,color:"red"}
let c2=Circle{r:5.0,color:"blue"}
let c3=Circle{r:3.0,color:"red"}
print(c1==c2)
print(c1==c3)
print(str(c1))''', 'true\nfalse\nCircle(r=5,c=red)', 'operator on subclass')


if __name__ == '__main__':
    print()
    print('══════════════════════════════════════════════════════════════')
    print('  Phase 7 — Operator Overloading Tests')
    print('══════════════════════════════════════════════════════════════')
    print()

    run_all()

    if FAILURES:
        print()
        for f in FAILURES:
            print(f)

    total = PASS + FAIL
    print()
    print('══════════════════════════════════════════════════════════════')
    print(f'  Phase 7 Results: {PASS}/{total} passed', end='')
    if FAIL == 0:
        print('  ✅ ALL PASS')
    else:
        print(f'  ❌ {FAIL} FAILED')
    print('══════════════════════════════════════════════════════════════')
    print()

    import sys; sys.exit(0 if FAIL == 0 else 1)
