# -*- coding: utf-8 -*-
"""
test_phase6.py — Phase 6: Bytecode VM Tests
============================================
Every test compiles InScript source → FnProto bytecode → VM execution.
Run:  python test_phase6.py
"""
import io, sys, os, tempfile, time
sys.path.insert(0, os.path.dirname(__file__))
from compiler import compile_source, write_ibc, read_ibc, Op
from vm import run_source, VM

PASS = FAIL = 0
FAILURES = []

def run(src):
    buf = io.StringIO(); sys.stdout = buf
    try:
        run_source(src); sys.stdout = sys.__stdout__
        return buf.getvalue().strip(), None
    except Exception as e:
        sys.stdout = sys.__stdout__; return None, str(e)

def T(src, expected, label=None):
    global PASS, FAIL
    out, err = run(src)
    ok = (err is None and out == expected)
    if ok:
        PASS += 1
    else:
        FAIL += 1
        tag = label or src[:60].replace('\n',' ')
        got = err[:80] if err else repr(out)
        FAILURES.append(f"  FAIL  {tag}\n        got : {got}\n        want: {expected!r}")

def section(name):
    print(f"  {name}")


def run_all():
    global PASS, FAIL, FAILURES
    PASS = FAIL = 0; FAILURES = []

    # ── 6.1 Arithmetic & literals ───────────────────────────────────────────
    section("6.1  Arithmetic & literals")
    T('print(42)',          '42')
    T('print(3.14)',        '3.14')
    T('print("hello")',     'hello')
    T('print(true)',        'true')
    T('print(false)',       'false')
    T('print(nil)',         'nil')
    T('print(1+2)',         '3')
    T('print(10-3)',        '7')
    T('print(3*4)',         '12')
    T('print(10/4)',        '2.5')
    T('print(10 div 3)',    '3')
    T('print(10%3)',        '1')
    T('print(2**10)',       '1024')
    T('print(-7)',          '-7')
    T('print("a"+"b")',     'ab')
    T('print(3==3)',        'true')
    T('print(3!=4)',        'true')
    T('print(3<4)',         'true')
    T('print(4<=4)',        'true')
    T('print(5>4)',         'true')
    T('print(5>=5)',        'true')
    T('print(3>5)',         'false')
    T('print(true && false)', 'false')
    T('print(true || false)', 'true')
    T('print(!true)',         'false')
    T('let x=0; fn side(){x=1} false && side(); print(x)', '0', 'short-circuit &&')
    T('let x=0; fn side(){x=1} true || side(); print(x)', '0', 'short-circuit ||')

    # ── 6.2 Variables & assignment ──────────────────────────────────────────
    section("6.2  Variables & assignment")
    T('let x=5; print(x)',          '5')
    T('let x=5; x=10; print(x)',    '10')
    T('let x=0; x+=3; print(x)',    '3')
    T('let x=10; x-=3; print(x)',   '7')
    T('let x=2; x*=5; print(x)',    '10')
    T('let x=10; x/=4; print(x)',   '2.5')
    T('let x=2; x=x**3; print(x)',  '8', 'pow-assign via reassign')
    T('''let x=1\n{let x=2\nprint(x)}\nprint(x)''', '2\n1', 'scope shadow')

    # ── 6.3 Control flow ────────────────────────────────────────────────────
    section("6.3  Control flow")
    T('if true { print(1) }',                     '1')
    T('if false { print(1) } else { print(2) }',  '2')
    T('if 5>3 { print("y") } else { print("n") }','y')
    T('if false { } else if true { print(1) }',   '1', 'else-if')
    T('let x=0; while x<3 { print(x); x+=1 }',   '0\n1\n2')
    T('for i in 0..3 { print(i) }',               '0\n1\n2')
    T('for i in 0..=2 { print(i) }',              '0\n1\n2', 'inclusive range')
    T('for i in [10,20,30] { print(i) }',         '10\n20\n30')
    T('for i in {"a":1,"b":2} { print(i) }',      'a\nb', 'for in dict')
    T('let x=0; while true { if x>=3 { break } print(x); x+=1 }', '0\n1\n2', 'break')
    T('for i in 0..5 { if i==2 { continue } if i==4 { break } print(i) }', '0\n1\n3', 'continue+break')

    # ── 6.4 Functions ───────────────────────────────────────────────────────
    section("6.4  Functions")
    T('fn add(a,b){return a+b} print(add(3,4))',   '7')
    T('fn fact(n){if n<=1{return 1} return n*fact(n-1)} print(fact(6))', '720', 'recursion')
    T('fn fib(n){if n<=1{return n} return fib(n-1)+fib(n-2)} print(fib(10))', '55', 'mutual recursion')
    T('let f=fn(x){return x*x}; print(f(5))',      '25', 'fn expression')
    T('fn apply(f,x){return f(x)} print(apply(fn(x){return x*2},5))', '10', 'higher-order')
    T('fn mk(n){fn f(){return n} return f} let f=mk(7); print(f())', '7', 'closure capture')

    # ── 6.5 Closures ────────────────────────────────────────────────────────
    section("6.5  Closures")
    T('''fn counter(){
    let n=0
    fn inc(){n+=1;return n}
    return inc
}
let c=counter()
print(c())
print(c())
print(c())''', '1\n2\n3', 'closure mutation')

    T('''fn adder(x){return fn(y){return x+y}}
let add5=adder(5)
print(add5(3))
print(add5(10))''', '8\n15', 'closure factory')

    # ── 6.6 Collections: arrays ─────────────────────────────────────────────
    section("6.6  Arrays")
    T('let a=[1,2,3]; print(a[0])',              '1')
    T('let a=[1,2,3]; print(a[2])',              '3')
    T('let a=[1,2,3]; a[1]=99; print(a[1])',     '99')
    T('let a=[1,2,3]; a.append(4); print(a[3])', '4')
    T('let a=[1,2,3]; print(len(a))',            '3')
    T('let a=[1,2,3]; print(a.length)',          '3')
    T('let a=[3,1,2]; a.sort(); print(a[0])',    '1')
    T('let a=[1,2,3]; a.reverse(); print(a[0])', '3')
    T('let a=[1,2,3]; print(a.map(fn(x){return x*2})[1])',   '4', 'array.map')
    T('let a=[1,2,3,4]; print(a.filter(fn(x){return x%2==0})[0])', '2', 'array.filter')
    T('let a=[1,2,3]; print(a.contains(2))',     'true')
    T('let a=[1,2,3]; print(a.index(2))',        '1')
    T('let a=[1,2,3]; let b=a.slice(1,3); print(b[0])', '2', 'array.slice')
    T('let a=[[1,2],[3,4]]; print(a.flatten()[2])', '3', 'array.flatten')

    # ── 6.7 Collections: dicts ──────────────────────────────────────────────
    section("6.7  Dicts")
    T('let d={"x":1,"y":2}; print(d["x"])',      '1')
    T('let d={"x":1,"y":2}; print(d["y"])',      '2')
    T('let d={"a":1}; d["b"]=99; print(d["b"])', '99')
    T('let d={"a":1}; print(d.has("a"))',         'true')
    T('let d={"a":1}; print(d.has("z"))',         'false')
    T('let d={"a":1,"b":2}; print(len(d))',       '2')
    T('let d={"a":1}; d.delete("a"); print(d.has("a"))', 'false', 'dict.delete')
    T('let d={"a":1}; let m=d.merge({"b":2}); print(m["b"])', '2', 'dict.merge')

    # ── 6.8 Strings ─────────────────────────────────────────────────────────
    section("6.8  Strings")
    T('print("hello".upper())',               'HELLO')
    T('print("HELLO".lower())',               'hello')
    T('print("hello".length)',                '5')
    T('print("hello world".split(" ")[0])',   'hello')
    T('print("  hi  ".trim())',               'hi')
    T('print("abc".contains("b"))',           'true')
    T('print("hello".starts_with("hel"))',    'true')
    T('print("hello".ends_with("llo"))',      'true')
    T('print("abc".replace("b","B"))',        'aBc')
    T('print("3".to_int()+4)',                '7')
    T('print("3.14".to_float())',             '3.14')
    T('print("abc".char_at(1))',              'b')
    T('print("abc".index_of("c"))',           '2')
    T('print("hi".repeat(3))',                'hihihi')
    T('print("ab".pad_left(4,"0"))',          '00ab')

    # ── 6.9 F-strings ───────────────────────────────────────────────────────
    section("6.9  F-strings")
    T('let x=42; print(f"val={x}")',              'val=42')
    T('let a=3; let b=4; print(f"{a}+{b}={a+b}")', '3+4=7')
    T('let name="world"; print(f"Hello {name}!")', 'Hello world!')
    T('let x=5; print(f"sq={x*x}")',              'sq=25')

    # ── 6.10 Match ──────────────────────────────────────────────────────────
    section("6.10  Match")
    T('let x=2; match x { case 1{print("one")} case 2{print("two")} case _{print("?")}}', 'two')
    T('let x=5; match x { case 1{print("one")} case _{print("other")}}', 'other', 'wildcard')
    T('let x="hi"; match x { case "hi"{print("hello")} case _{print("?")}}', 'hello', 'string match')
    T('''let x=3
match x {
    case 1 { print("one") }
    case 2 { print("two") }
    case 3 { print("three") }
    case _ { print("many") }
}''', 'three', 'multi-arm match')

    # ── 6.11 Try/Catch ──────────────────────────────────────────────────────
    section("6.11  Try/Catch")
    T('try { throw "err" } catch e { print(e) }',         'err')
    T('try { 1 div 0 } catch e { print("caught") }',      'caught', 'catch native exception')
    T('try { nil.x } catch e { print("nil_err") }',       'nil_err', 'catch nil access')
    T('''fn safe(x){try{return 100 div x}catch e{return -1}}
print(safe(0))
print(safe(5))''', '-1\n20', 'try/catch in function')

    # ── 6.12 List comprehension ─────────────────────────────────────────────
    section("6.12  List comprehension")
    T('print([x*x for x in 0..4])',                '[0, 1, 4, 9]')
    T('print([x for x in 0..6 if x%2==0])',        '[0, 2, 4]', 'filtered')
    T('print(["x"+str(i) for i in 0..3][1])',      'x1', 'string comp')
    T('let xs=[1,2,3]; print([x*2 for x in xs])',  '[2, 4, 6]', 'over array')

    # ── 6.13 Structs ────────────────────────────────────────────────────────
    section("6.13  Structs")
    T('''struct Point {
    x: float
    y: float
    fn dist() { return sqrt(self.x*self.x+self.y*self.y) }
}
let p=Point{x:3.0,y:4.0}
print(p.x)
print(p.dist())''', '3\n5', 'struct method')

    T('''struct Counter {
    n: int
    fn inc() { self.n += 1 }
    fn get() { return self.n }
}
let c=Counter{n:0}
c.inc(); c.inc(); c.inc()
print(c.get())''', '3', 'struct mutation')

    T('''struct Animal { name: string }
struct Dog extends Animal {
    fn speak() { print("Woof "+self.name) }
}
Dog{name:"Rex"}.speak()''', 'Woof Rex', 'inheritance')

    T('''struct Stack {
    items: array
    fn push(v) { self.items.append(v) }
    fn pop()   { return self.items.pop() }
    fn size()  { return self.items.length }
}
let s=Stack{items:[]}
s.push(1); s.push(2); s.push(3)
print(s.size())
print(s.pop())''', '3\n3', 'struct with array field')

    T('''struct Vec2 {
    x: float; y: float
    fn add(o) { return Vec2{x:self.x+o.x, y:self.y+o.y} }
    fn str()  { return f"({self.x},{self.y})" }
}
let a=Vec2{x:1.0,y:2.0}
let b=Vec2{x:3.0,y:4.0}
let c=a.add(b)
print(c.x)
print(c.y)''', '4\n6', 'struct method return struct')

    # ── 6.14 Enums ──────────────────────────────────────────────────────────
    section("6.14  Enums")
    T('enum Dir { North South East West } print(Dir.North)',  'Dir.North')
    T('enum Dir { North South East West } print(Dir.South)',  'Dir.South')
    T('enum Color { Red=1 Green=2 Blue=3 } print(Color.Green)', 'Color.Green')
    T('''enum Status { Ok Error }
let s=Status.Ok
match s {
    case Status.Ok    { print("ok") }
    case Status.Error { print("err") }
    case _            { print("?") }
}''', 'ok', 'enum match')

    # ── 6.15 Misc expressions ───────────────────────────────────────────────
    section("6.15  Misc expressions")
    T('print(5>3 ? "big" : "small")',      'big',  'ternary true')
    T('print(1>3 ? "big" : "small")',      'small','ternary false')
    T('let x=nil; print(x ?? 42)',         '42',   'nullish nil')
    T('let x=5; print(x ?? 42)',           '5',    'nullish non-nil')
    T('print(type(42))',     'int')
    T('print(type("hi"))',   'string')
    T('print(type([1,2]))',  'array')
    T('print(type(nil))',    'nil')
    T('print(type(true))',   'bool')

    # ── 6.16 Builtins ───────────────────────────────────────────────────────
    section("6.16  Builtins")
    T('print(abs(-7))',         '7')
    T('print(min(3,1,4))',      '1')
    T('print(max(3,1,4))',      '4')
    T('print(round(3.7))',      '4')
    T('print(floor(3.9))',      '3')
    T('print(ceil(3.1))',       '4')
    T('print(sqrt(16.0))',      '4')
    T('print(int("42"))',       '42')
    T('print(float("3.14"))',   '3.14')
    T('print(str(99))',         '99')
    T('print(len([1,2,3]))',    '3')
    T('print(len("hello"))',    '5')
    T('print(clamp(10,0,5))',   '5')

    # ── 6.17 Import ─────────────────────────────────────────────────────────
    section("6.17  Import")
    T('import "math" as M; print(M.floor(3.7))', '3')
    T('import "math" as M; print(M.sqrt(16))',   '4')
    T('import "math" as M; print(M.PI > 3.1)',   'true')

    # ── 6.18 IBC serialization ──────────────────────────────────────────────
    section("6.18  IBC serialization")
    src = 'fn add(a,b){return a+b} print(add(10,20))'
    proto = compile_source(src)
    with tempfile.NamedTemporaryFile(suffix='.ibc', delete=False) as f:
        path = f.name
    try:
        write_ibc(proto, path)
        loaded = read_ibc(path)
        assert isinstance(loaded, type(proto)), "loaded wrong type"
        assert loaded.name == proto.name, "name mismatch"
        assert len(loaded.code) == len(proto.code), "code length mismatch"
        PASS += 1; print("  OK   IBC round-trip")
    except Exception as e:
        FAIL += 1; FAILURES.append(f"  FAIL IBC round-trip: {e}")
    finally:
        os.unlink(path)

    # ── 6.19 Disassembler ───────────────────────────────────────────────────
    section("6.19  Disassembler")
    try:
        proto = compile_source('fn add(a,b){return a+b}')
        asm = proto.disassemble()
        assert 'add' in asm, "function name missing from disassembly"
        assert 'RETURN' in asm, "RETURN missing from disassembly"
        assert 'ADD' in asm, "ADD opcode missing"
        PASS += 1; print("  OK   disassembler output")
    except Exception as e:
        FAIL += 1; FAILURES.append(f"  FAIL disassembler: {e}")

    # ── 6.20 Performance ────────────────────────────────────────────────────
    section("6.20  Performance")
    src_loop = 'let s=0; for i in 0..100000 { s+=i }; print(s)'
    t0 = time.time()
    out, err = run(src_loop)
    t1 = time.time()
    ms = (t1-t0)*1000
    if err:
        FAIL += 1; FAILURES.append(f"  FAIL perf loop: {err}")
    elif out != '4999950000':
        FAIL += 1; FAILURES.append(f"  FAIL perf loop: got {out!r}")
    elif ms > 5000:
        FAIL += 1; FAILURES.append(f"  FAIL perf loop: {ms:.0f}ms > 5000ms limit")
    else:
        PASS += 1; print(f"  OK   100k loop: {ms:.0f}ms")

    src_fib = 'fn fib(n){if n<=1{return n} return fib(n-1)+fib(n-2)} print(fib(20))'
    t0 = time.time()
    out, err = run(src_fib)
    t1 = time.time()
    ms = (t1-t0)*1000
    if err:
        FAIL += 1; FAILURES.append(f"  FAIL perf fib(30): {err}")
    elif out != '6765':
        FAIL += 1; FAILURES.append(f"  FAIL perf fib(30): got {out!r}")
    elif ms > 10000:
        FAIL += 1; FAILURES.append(f"  FAIL perf fib(20): {ms:.0f}ms > 10s limit")
    else:
        PASS += 1; print(f"  OK   fib(20): {ms:.0f}ms")


# ─── run ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print()
    print('══════════════════════════════════════════════════════════════')
    print('  Phase 6 — Bytecode VM Tests')
    print('══════════════════════════════════════════════════════════════')
    print()

    run_all()

    if FAILURES:
        print()
        for f in FAILURES:
            print(f)

    print()
    print('══════════════════════════════════════════════════════════════')
    print(f'  Phase 6 Results: {PASS}/{PASS+FAIL} passed', end='')
    if FAIL == 0:
        print('  ✅ ALL PASS')
    else:
        print(f'  ❌ {FAIL} FAILED')
    print('══════════════════════════════════════════════════════════════')
    print()

    sys.exit(0 if FAIL == 0 else 1)
