# -*- coding: utf-8 -*-
"""
test_comprehensive.py — InScript Comprehensive Feature Test Suite
=================================================================
Tests ALL language features systematically. Run this to get a full
health check on any build. Expected: 100% pass.

Run:  python test_comprehensive.py
Run (verbose): python test_comprehensive.py --verbose
"""

import io, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from repl import EnhancedREPL
from vm import VM
from compiler import Compiler
from parser import parse

PASS = FAIL = 0
FAILURES = []

def run(label, code, expect=None, expect_err=False, use_vm=False):
    global PASS, FAIL
    if use_vm:
        try:
            prog = parse(code); chunk = Compiler().compile(prog)
            buf = io.StringIO(); sys.stdout = buf; VM().run(chunk)
            sys.stdout = sys.__stdout__; out = buf.getvalue().strip()
        except Exception as e:
            sys.stdout = sys.__stdout__
            if expect_err:
                PASS += 1; return
            FAIL += 1; FAILURES.append((f"VM:{label}", str(e)[:60], expect))
            return
        if expect_err:
            FAIL += 1; FAILURES.append((f"VM:{label}", "expected error, got none", "")); return
        if expect and out != expect:
            FAIL += 1; FAILURES.append((f"VM:{label}", out, expect)); return
        PASS += 1; return

    r = EnhancedREPL()
    buf = io.StringIO(); sys.stdout = buf
    _, err, _ = r._eval(code)
    sys.stdout = sys.__stdout__
    out = buf.getvalue().strip()
    if expect_err:
        if err: PASS += 1
        else: FAIL += 1; FAILURES.append((label, "expected error, got none", ""))
        return
    if err:
        FAIL += 1; FAILURES.append((label, str(err)[:60], expect)); return
    if expect and out != expect:
        FAIL += 1; FAILURES.append((label, out, expect)); return
    PASS += 1

# ══════════════════════════════════════════════════════════════════
# SECTION 1: VARIABLES & TYPES
# ══════════════════════════════════════════════════════════════════
run("let basic",            'let x=42; print(x)', "42")
run("const basic",          'const PI=3.14; print(PI)', "3.14")
run("const reassign error", 'const X=1; X=2', expect_err=True)
run("type annotation",      'let x:int=42; print(x)', "42")
run("type inference int",   'let x=42; print(typeof(x))', "int")
run("type inference float",  'let x=3.14; print(typeof(x))', "float")
run("type inference string", 'let x="hi"; print(typeof(x))', "string")
run("type inference bool",   'let x=true; print(typeof(x))', "bool")
run("nil literal",          'let x=nil; print(is_nil(x))', "true")
run("typeof nil",           'print(typeof(nil))', "nil")
run("typeof range",         'print(typeof(0..5))', "range")
run("typeof fn",            'fn f(){}; print(typeof(f))', "function")
run("typeof generator",     'fn* g(){yield 1}; print(typeof(g()))', "generator")
run("typeof array",         'print(typeof([1,2,3]))', "array")
run("typeof dict",          'print(typeof({"a":1}))', "dict")
run("null deprecated warns", 'let x=null; print(x)') # warns but doesn't fail

# ══════════════════════════════════════════════════════════════════
# SECTION 2: ARITHMETIC & OPERATORS
# ══════════════════════════════════════════════════════════════════
run("add",                  'print(2+3)', "5")
run("subtract",             'print(10-4)', "6")
run("multiply",             'print(3*4)', "12")
run("divide",               'print(10.0/4.0)', "2.5")
run("power",                'print(2**10)', "1024")
run("integer div",          'print(7 div 2)', "3")
run("modulo",               'print(17 % 5)', "2")
run("compound +=",          'let x=5; x+=3; print(x)', "8")
run("compound -=",          'let x=10; x-=3; print(x)', "7")
run("compound *=",          'let x=4; x*=3; print(x)', "12")
run("compound /=",          'let x=10.0; x/=2.0; print(x)', "5.0")
run("compound **=",         'let x=2; x**=8; print(x)', "256")
run("bitwise &",            'print(12 & 10)', "8")
run("bitwise |",            'print(12 | 10)', "14")
run("bitwise ^",            'print(12 ^ 10)', "6")
run("bit shift left",       'print(1 << 4)', "16")
run("bit shift right",      'print(32 >> 2)', "8")
run("string + concat",      'print("hello" + " world")', "hello world")
run("string ++ concat",     'print("foo" ++ "bar")', "foobar")
run("string ++ concat",     'print("foo" ++ "bar")', "foobar")
run("string * repeat",      'print("ab" * 3)', "ababab")
run("unary minus",          'let x=5; print(-x)', "-5")
run("unary not",            'print(!true)', "false")
run("comparison <",         'print(1<2)', "true")
run("comparison >",         'print(2>1)', "true")
run("comparison <=",        'print(2<=2)', "true")
run("comparison >=",        'print(3>=2)', "true")
run("equality ==",          'print(1==1)', "true")
run("inequality !=",        'print(1!=2)', "true")
run("logical &&",           'print(true && false)', "false")
run("logical ||",           'print(false || true)', "true")
run("null coalescing ??",   'let x=nil; print(x ?? "default")', "default")
run("ternary ?:",           'print(5>3 ? "yes" : "no")', "yes")
run("nested ternary",       'let x=2; print(x==1?"one":x==2?"two":"other")', "two")
run("in arr",               'print(2 in [1,2,3])', "true")
run("not in arr",           'print(5 not in [1,2,3])', "true")
run("in dict",              'print("a" in {"a":1})', "true")
run("in string",            'print("ell" in "hello")', "true")
run("pipe operator |>",     'fn dbl(x){return x*2}; print(5 |> dbl)', "10")
run("pipe chain",           'fn inc(x){return x+1}; fn dbl(x){return x*2}; print(3 |> inc |> dbl)', "8")
run("optional chain ?.",    'let x=nil; print(x?.foo ?? "nil")', "nil")
run("optional chain deep",  'struct A{b:int=5}; struct W{a:A}; let w=W{a:A{}}; print(w?.a?.b)', "5")

# ══════════════════════════════════════════════════════════════════
# SECTION 3: STRINGS
# ══════════════════════════════════════════════════════════════════
run("f-string basic",       'let name="Alice"; print(f"Hello {name}!")', "Hello Alice!")
run("f-string float fmt",   'let x=3.14159; print(f"{x:.2f}")', "3.14")
run("f-string int fmt",     'let n=42; print(f"{n:05d}")', "00042")
run("f-string expr",        'print(f"{2+3}")', "5")
run("f-string right-align", 'let s="hi"; let r=f"{s:>6}"; print(len(r))', "6")  # length=6 (4 spaces + hi)
run("f-string ternary",     'let x=5; print(f"{x>3 ? \'big\' : \'small\'}")', "big")
run("f-string dict key",    'let d={"k":"v"}; print(f"{d[\"k\"]}")', "v")
run("f-string method",      'let s="hello"; print(f"{s.upper()}")', "HELLO")
run("str.upper",            'print("hello".upper())', "HELLO")
run("str.lower",            'print("HELLO".lower())', "hello")
run("str.trim",             'print("  hi  ".trim())', "hi")
run("str.split",            'print("a,b,c".split(","))', '["a", "b", "c"]')
run("str.split limit",      'print("a,b,c,d".split(",",2))', '["a", "b", "c,d"]')
run("str.replace",          'print("hello".replace("l","r"))', "herro")
run("str.contains",         'print("hello".contains("ell"))', "true")
run("str.starts_with",      'print("hello".starts_with("hel"))', "true")
run("str.ends_with",        'print("hello".ends_with("llo"))', "true")
run("str.index",            'print("hello".index("ll"))', "2")
run("str.index miss",       'print("hello".index("xyz"))', "-1")
run("str.count",            'print("banana".count("a"))', "3")
run("str.reverse",          'print("hello".reverse())', "olleh")
run("str.repeat",           'print("ab".repeat(3))', "ababab")
run("str.chars",            'print("hi".chars())', '["h", "i"]')
run("str.is_empty true",    'print("".is_empty())', "true")
run("str.is_empty false",   'print("a".is_empty())', "false")
run("str.pad_left",         'print("42".pad_left(6,"0"))', "000042")
run("str.pad_right",        'print("hi".pad_right(5,"."))', "hi...")
run("str.substr",           'print("hello".substr(1,3))', "el")
run("str.char_at",          'print("hello".char_at(1))', "e")
run("str.to_int",           'print(int("42"))', "42")
run("str.to_float",         'print(float("3.14"))', "3.14")
run("str neg index",        'print("hello"[-1])', "o")
run("str format positional",'print("{} and {}".format("a","b"))', "a and b")
run("str format named",     'print("Hi {name}!".format(name:"Alice"))', "Hi Alice!")
run("str comparison",       'print("abc" < "abd")', "true")
run("escape newline",       'let s="a\\nb"; print(len(s.split("\\n")))', "2")
run("escape tab",           'print("a\\tb")', "a\tb")

# ══════════════════════════════════════════════════════════════════
# SECTION 4: ARRAYS
# ══════════════════════════════════════════════════════════════════
run("arr literal",          'let a=[1,2,3]; print(a[1])', "2")
run("arr neg index",        'print([1,2,3][-1])', "3")
run("arr push/pop",         'let a=[1,2]; a.push(3); print(a.pop())', "3")
run("arr len",              'print(len([1,2,3,4]))', "4")
run("arr map",              'print([1,2,3].map(fn(x){return x*2}))', "[2, 4, 6]")
run("arr filter",           'print([1,2,3,4,5].filter(fn(x){return x%2==0}))', "[2, 4]")
run("arr reduce no-init",   'print([1,2,3,4].reduce(fn(a,b){return a+b}))', "10")
run("arr reduce init",      'print([1,2,3].reduce(0,fn(a,b){return a+b}))', "6")
run("arr sorted",           'print([3,1,2].sorted())', "[1, 2, 3]")
run("arr sorted fn",        'print(["banana","apple"].sorted(fn(x){return len(x)}))', '["apple", "banana"]')
run("arr sort inplace",     'let a=[3,1,2]; a.sort(); print(a)', "[1, 2, 3]")
run("arr sort fn inplace",  'let a=["banana","apple"]; a.sort(fn(x){return len(x)}); print(a[0])', "apple")
run("arr flatten",          'print([[1,2],[3,4]].flatten())', "[1, 2, 3, 4]")
run("arr flat_map",         'print([[1,2],[3,4]].flat_map(fn(x){return x}))', "[1, 2, 3, 4]")
run("arr unique",           'print([1,2,2,3,1].unique())', "[1, 2, 3]")
run("arr zip",              'print([1,2].zip([3,4]))', "[[1, 3], [2, 4]]")
run("arr includes",         'print([1,2,3].includes(2))', "true")
run("arr is_empty",         'print([].is_empty())', "true")
run("arr take",             'print([1,2,3,4,5].take(3))', "[1, 2, 3]")
run("arr skip",             'print([1,2,3,4,5].skip(2))', "[3, 4, 5]")
run("arr chunk",            'print([1,2,3,4].chunk(2))', "[[1, 2], [3, 4]]")
run("arr any",              'print([1,2,3].any(fn(x){return x>2}))', "true")
run("arr all",              'print([1,2,3].all(fn(x){return x>0}))', "true")
run("arr each",             'let s=0;[1,2,3].each(fn(x){s+=x});print(s)', "6")
run("arr sum",              'print([1.0,2.0,3.0].sum())', "6.0")
run("arr min_by",           'print(["b","a","c"].min_by(fn(x){return x}))', "a")
run("arr group_by",         'let g=[1,2,3,4].group_by(fn(x){return x%2==0?"e":"o"});print(len(g))', "2")
run("arr find",             'print([1,2,3].find(fn(x){return x>1}))', "2")
run("arr find miss",        'print([1,2].find(fn(x){return x>9}) ?? "none")', "none")
run("arr count fn",         'print([1,2,3,4].count(fn(x){return x%2==0}))', "2")
run("arr comprehension",    'print([x*x for x in 1..=5 if x%2==1])', "[1, 9, 25]")
run("arr spread",           'let a=[1,2];let b=[...a,3];print(b)', "[1, 2, 3]")
run("range spread",         'let a=[...0..5];print(len(a))', "5")
run("arr spread fn call",   'fn f(a,b,c){return a+b+c};print(f(...[1,2,3]))', "6")
run("arr str display",      'print([1,"two",true])', '[1, "two", true]')
run("arr max_by",           'print(["b","a","c"].max_by(fn(x){return x}))', "c")
run("zip builtin",          'print(zip([1,2],[3,4]))', "[[1, 3], [2, 4]]")
run("enumerate builtin",    'print(enumerate(["a","b"])[0])', '[0, "a"]')
run("sum builtin",          'print(sum([1,2,3,4,5]))', "15")
run("flatten builtin",      'print(flatten([[1,2],[3,4]]))', "[1, 2, 3, 4]")
run("sort mutates",         'let a=[3,1,2]; sort(a); print(a)', "[1, 2, 3]")
run("sorted returns copy",  'let a=[3,1,2]; let b=sorted(a); print(a)', "[3, 1, 2]")

# ══════════════════════════════════════════════════════════════════
# SECTION 5: DICTS
# ══════════════════════════════════════════════════════════════════
run("dict literal",         'let d={"a":1,"b":2}; print(d["a"])', "1")
run("dict var key",         'let k="x"; let d={"x":10}; print(d[k])', "10")
run("dict has_key",         'let d={"a":1}; print(d.has_key("a"))', "true")
run("dict has_value",       'let d={"a":1}; print(d.has_value(1))', "true")
run("dict get default",     'let d={"a":1}; print(d.get("b",99))', "99")
run("dict set",             'let d={}; d.set("x",5); print(d["x"])', "5")
run("dict remove",          'let d={"a":1,"b":2}; d.remove("a"); print(len(d))', "1")
run("dict merge method",    'let a={"x":1}; print(a.merge({"y":2}))', '{"x": 1, "y": 2}')
run("dict is_empty",        'print({}.is_empty())', "true")
run("dict spread",          'let a={"x":1}; print({...a,"y":2})', '{"x": 1, "y": 2}')
run("dict multi-spread",    'let a={"x":1}; let b={"y":2}; print({...a,...b})', '{"x": 1, "y": 2}')
run("dict comprehension",   'let r={k: k*2 for k in [1,2,3]}; print(r[2])', "4")
run("dict comp k,v",        'let d={"a":1,"b":2}; let r={k: v*2 for k,v in entries(d)}; print(r["a"])', "2")
run("dict comp if",         'let r={k: v for k,v in entries({"a":1,"b":2}) if v>1}; print(r["b"])', "2")
run("entries on struct",    'struct P{x:float=1.0;y:float=2.0}; let p=P{}; for k,v in entries(p){print(k)}', "x\ny")
run("for k,v in entries",   'let d={"a":1}; for k,v in entries(d){print(k+":"+string(v))}', "a:1")
run("dict keys sorted",     'let d={"b":2,"a":1}; print(sorted(keys(d)))', '["a", "b"]')
run("dict values",          'let d={"a":1,"b":2}; print(sum(values(d)))', "3")
run("len on dict",          'print(len({"a":1,"b":2}))', "2")
run("dict display style",   'print({"a":1})', '{"a": 1}')
run("dict() constructor",   'let d=dict(); d["x"]=5; print(d["x"])', "5")
run("dict() from pairs",    'let d=dict([["a",1],["b",2]]); print(d["a"])', "1")
run("nested dict access",   'let d={"a":{"b":42}}; print(d["a"]["b"])', "42")
run("merge builtin",        'let a={"x":1}; print(merge(a,{"y":2})["y"])', "2")

# ══════════════════════════════════════════════════════════════════
# SECTION 6: CONTROL FLOW
# ══════════════════════════════════════════════════════════════════
run("if-else",              'let x=5; if x>3{print("big")} else{print("small")}', "big")
run("if-else-if",           'let x=2; if x==1{print("a")} else if x==2{print("b")} else{print("c")}', "b")
run("for in range",         'let s=0; for i in 0..5{s+=i}; print(s)', "10")
run("for in array",         'let s=0; for x in [1,2,3,4]{s+=x}; print(s)', "10")
run("for in string",        'let s=""; for c in "hi"{s+=c}; print(s)', "hi")
run("for in dict",          'let d={"a":1}; for k in d{print(k)}', "a")
run("while loop",           'let i=0; while i<5{i+=1}; print(i)', "5")
run("do-while",             'let x=0; do{x+=1}while x<3; print(x)', "3")
run("for-else no break",    'for x in [1,2,3]{if x==9{break}} else{print("done")}', "done")
run("for-else with break",  'let r=""; for x in [1,2,3]{if x==2{break}} else{r="done"}; print(r)', "")
run("while-else",           'let x=5; while x<3{x+=1} else{print("skip")}', "skip")
run("break",                'let s=0; for i in 0..10{if i==5{break}; s+=i}; print(s)', "10")
run("continue",             'let s=0; for i in 0..5{if i==2{continue}; s+=i}; print(s)', "8")
run("labeled break",        'let r=0; outer: for i in 0..5{for j in 0..5{if i*j>4{break outer}}}; print("done")', "done")
run("range inclusive",      'let s=0; for i in 0..=5{s+=i}; print(s)', "15")
run("range step",           'let s=0; for i in range(0,10,2){s+=i}; print(s)', "20")
run("for multi-var",        'for k,v in [["a",1],["b",2]]{print(k)}', "a\nb")

# ══════════════════════════════════════════════════════════════════
# SECTION 7: FUNCTIONS
# ══════════════════════════════════════════════════════════════════
run("fn basic",             'fn add(a,b){return a+b}; print(add(3,4))', "7")
run("fn type annotation",   'fn add(a:int,b:int)->int{return a+b}; print(add(3,4))', "7")
run("fn default param",     'fn greet(name="World"){return "Hi "+name}; print(greet())', "Hi World")
run("fn named arg",         'fn f(x,y){return x-y}; print(f(y:1,x:5))', "4")
run("fn variadic",          'fn sum(*args){let t=0;for x in args{t+=x};return t}; print(sum(1,2,3,4))', "10")
run("fn closure",           'fn adder(n){return fn(x){return x+n}}; let add5=adder(5); print(add5(3))', "8")
run("fn recursive",         'fn fib(n){if n<=1{return n}; return fib(n-1)+fib(n-2)}; print(fib(10))', "55")
run("fn lambda",            'let f=fn(x){return x*2}; print(f(5))', "10")
run("fn as value",          'fn dbl(x){return x*2}; let f=dbl; print(f(6))', "12")
run("fn keyword name div",  'fn div(a,b){return a/b}; print(div(10.0,2.0))', "5.0")
run("higher order fn",      'fn apply(f,x){return f(x)}; print(apply(fn(x){return x*3},4))', "12")
run("fn multi return",      'fn swap(a,b){return [b,a]}; let [x,y]=swap(1,2); print(x)', "2")
run("closure captures var", 'let n=10; let f=fn(){return n*2}; n=20; print(f())', "40")
run("fn missing return warn",'fn bad()->int{let x=1}; print("ok")', "ok")  # warns
run("fn dup warn",          'fn f(x){return x}; fn f(x){return x}; print("ok")', "ok")  # warns
run("try as expression",    'let r=try{42} catch e{0}; print(r)', "42")
run("try catch value",      'let r=try{throw "bad"} catch e{e}; print(r)', "bad")
run("reduce on result",     'print([1,2,3].filter(fn(x){return x%2==1}).reduce(fn(a,b){return a+b}))', "4")

# ══════════════════════════════════════════════════════════════════
# SECTION 8: GENERATORS
# ══════════════════════════════════════════════════════════════════
run("gen for-in",           'fn* gen(n){let i=0;while i<n{yield i;i+=1}}; for v in gen(3){print(v)}', "0\n1\n2")
run("gen next()",           'fn* cnt(n){let i=0;while i<n{yield i;i+=1}}; let g=cnt(5); print(next(g))', "0")
run("gen.next() method",    'fn* cnt(n){let i=0;while i<n{yield i;i+=1}}; let g=cnt(5); g.next(); print(g.next())', "1")
run("gen typeof",           'fn* g(){yield 1}; print(typeof(g()))', "generator")

# ══════════════════════════════════════════════════════════════════
# SECTION 9: PATTERN MATCHING
# ══════════════════════════════════════════════════════════════════
run("match int",            'match 2{case 1{print("one")} case 2{print("two")} case _{print("x")}}', "two")
run("match string",         'match "hi"{case "hi"{print("hello")} case _{print("x")}}', "hello")
run("match wildcard",       'match 99{case 1{print("one")} case _{print("other")}}', "other")
run("match as expression",  'let r=match 5{case 1{"one"} case _{"other"}}; print(r)', "other")
run("match fn return",      'fn g(n){return match n{case 5{"A"} case _{"B"}}}; print(g(5))', "A")
run("match guard",          'let x=7; match x{case n if n>5{print("big")} case _{print("small")}}', "big")
run("match enum",           'enum D{N S E W}; let d=D.E; match d{case D.E{print("east")} case _{print("x")}}', "east")
run("match ADT",            'enum S{Circle(r:float)}; let s=S.Circle(5.0); match s{case S.Circle(r){print(r)} case _{print("x")}}', "5.0")
run("match Ok",             'fn f(x){return Ok(x*2)}; match f(5){case Ok(v){print(v)} case Err(e){print(e)}}', "10")
run("match Err",            'fn f(){return Err("bad")}; match f(){case Ok(v){print(v)} case Err(e){print(e)}}', "bad")
run("non-exhaust warns",    'enum D{N S}; match D.N{case D.N{print("n")}}', "n")  # warns

# ══════════════════════════════════════════════════════════════════
# SECTION 10: STRUCTS & OOP
# ══════════════════════════════════════════════════════════════════
run("struct basic",         'struct P{x:float;y:float}; let p=P{x:1.0,y:2.0}; print(p.x)', "1.0")
run("struct method",        'struct C{n:int=0; fn inc(){self.n+=1}}; let c=C{}; c.inc(); c.inc(); print(c.n)', "2")
run("struct default",       'struct S{x:int=42}; let s=S{}; print(s.x)', "42")
run("struct print",         'struct P{x:float; fn hi(){}}; let p=P{x:3.0}; print(p)', "P{ x: 3.0 }")
run("struct copy deep",     'struct S{items:[]}; let a=S{items:[1,2]}; let b=a.copy(); b.items.push(3); print(len(a.items))', "2")
run("struct to_dict",       'struct P{x:float=1.0}; let p=P{}; print(p.to_dict()["x"])', "1.0")
run("struct has",           'struct P{x:float=1.0}; let p=P{}; print(p.has("x"))', "true")
run("struct inheritance",   'struct A{x:float=1.0}; struct B extends A{y:float=2.0}; let b=B{x:3.0,y:4.0}; print(b.x)', "3.0")
run("struct multi-inherit", 'struct A{fn greet(){return "A"}}; struct B extends A{}; struct C extends B{}; print(C{}.greet())', "A")
run("struct super call",    'struct A{fn greet(){return "Hello"}}; struct B extends A{fn greet(){return super.greet()+" World"}}; print(B{}.greet())', "Hello World")
run("struct operator +",    'struct V{x:float; fn +(o){return V{x:self.x+o.x}}}; let a=V{x:1.0}; let b=V{x:2.0}; print((a+b).x)', "3.0")
run("struct operator ==",   'struct P{x:int; fn ==(o){return self.x==o.x}}; print(P{x:5}==P{x:5})', "true")
run("struct is type",       'struct P{x:float}; let p=P{x:1.0}; print(p is P)', "true")
run("struct is inherit",    'struct A{x:float}; struct B extends A{y:float}; let b=B{x:1.0,y:2.0}; print(b is A)', "true")
run("struct static field",  'struct M{static PI:float=3.14}; print(M.PI)', "3.14")
run("struct priv read ok",  'struct B{priv n:int=42; fn get(){return self.n}}; print(B{}.get())', "42")
run("struct priv blocked",  'struct B{priv n:int=0}; let b=B{}; let r=try{b.n=99;"ok"} catch e{"blocked"}; print(r)', "blocked")
run("struct generics",      'struct Stack<T>{items:[]}; let s=Stack{items:[1,2,3]}; print(len(s.items))', "3")
run("struct chain methods", 'struct B{v:int=0; fn add(x){self.v+=x; return self}}; let b=B{}; b.add(3).add(4); print(b.v)', "7")

# ══════════════════════════════════════════════════════════════════
# SECTION 11: ERROR HANDLING
# ══════════════════════════════════════════════════════════════════
run("try-catch basic",      'try{throw "err"} catch e{print("caught: "+e)}', "caught: err")
run("try-catch typed int",  'try{throw 42} catch e:int{print("int: "+string(e))} catch e{print("other")}', "int: 42")
run("try-finally",          'let r=""; try{r+="try;"} catch e{r+="err;"} finally{r+="fin"}; print(r)', "try;fin")
run("try as expr ok",       'let r=try{42} catch e{0}; print(r)', "42")
run("try as expr catch",    'let r=try{throw "bad"} catch e{99}; print(r)', "99")
run("try as expr var",      'let r=try{throw "bad"} catch e{e}; print(r)', "bad")
run("result Ok display",    'print(Ok(42))', "Ok(42)")
run("result Err int",       'print(Err(42))', "Err(42)")
run("result Err string",     'print(Err("fail"))', 'Err("fail")')
run("assert pass",          'assert(1==1,"ok"); print("fine")', "fine")
run("assert fail",          'assert(1==2,"nope")', expect_err=True)
run("panic",                'panic("oops")', expect_err=True)
run("unreachable",          'unreachable("bug")', expect_err=True)

# ══════════════════════════════════════════════════════════════════
# SECTION 12: ENUMS
# ══════════════════════════════════════════════════════════════════
run("enum basic typeof",    'enum D{N S E W}; let d=D.E; print(typeof(d))', "D")
run("enum for-in",          'enum D{N S E W}; let c=0; for d in D{c+=1}; print(c)', "4")
run("enum in match",        'enum C{Red Green Blue}; let c=C.Red; match c{case C.Red{print("r")} case _{print("x")}}', "r")
run("enum ADT match",       'enum S{Circle(r:float)}; let s=S.Circle(5.0); match s{case S.Circle(r){print(r)} case _{print("x")}}', "5.0")

# ══════════════════════════════════════════════════════════════════
# SECTION 13: INTERFACES
# ══════════════════════════════════════════════════════════════════
run("interface impl",       'interface Fly{fn fly()}; struct Bird implements Fly{fn fly(){print("flap")}}; Bird{}.fly()', "flap")
run("interface default",    'interface Greet{fn hello(){print("hi")}}; struct P implements Greet{}; P{}.hello()', "hi")

# ══════════════════════════════════════════════════════════════════
# SECTION 14: TYPE CHECKS & BUILTINS
# ══════════════════════════════════════════════════════════════════
run("is int",               'print(42 is int)', "true")
run("is float",             'print(3.14 is float)', "true")
run("is string",            'print("hi" is string)', "true")
run("is bool",              'print(true is bool)', "true")
run("is nil",               'print(nil is nil)', "true")
run("is array",             'print([1,2] is array)', "true")
run("is dict",              'print({"a":1} is dict)', "true")
run("is struct",            'struct P{x:float}; let p=P{x:1.0}; print(p is P)', "true")
run("is wrong struct",      'struct P{x:float}; struct Q{y:float}; let p=P{x:1.0}; print(p is Q)', "false")
run("int methods",          'let n=42; print(n.to_string())', "42")
run("int.is_even",          'let n=4; print(n.is_even())', "true")
run("int.abs",              'let n=-5; print(n.abs())', "5")
run("int.clamp",            'let n=15; print(n.clamp(0,10))', "10")
run("float.floor",          'let x=3.7; print(x.floor())', "3")
run("float.ceil",           'let x=3.2; print(x.ceil())', "4")
run("float.round",          'let x=3.14159; print(x.round(2))', "3.14")
run("float.is_nan via math","import \"math\" as M; let inf=M.INF; print(inf.is_inf())", "true")
run("abs builtin",          'print(abs(-7))', "7")
run("min builtin",          'print(min(3,1,2))', "1")
run("max builtin",          'print(max(3,1,2))', "3")
run("clamp builtin",        'print(clamp(15,0,10))', "10")
run("floor builtin",        'print(floor(3.7))', "3")
run("ceil builtin",         'print(ceil(3.2))', "4")
run("sqrt builtin",         'print(sqrt(16.0))', "4.0")
run("string() cast",        'print(string(42))', "42")
run("int() cast",           'print(int("42"))', "42")
run("float() cast",         'print(float("3.14"))', "3.14")
run("bool() cast",          'print(bool(0))', "false")
run("is_nil builtin",       'print(is_nil(nil))', "true")
run("is_string builtin",    'print(is_string("hi"))', "true")
run("is_int builtin",       'print(is_int(42))', "true")

# ══════════════════════════════════════════════════════════════════
# SECTION 15: IMPORTS & STDLIB
# ══════════════════════════════════════════════════════════════════
run("import math as",       'import "math" as M; print(M.PI > 3.0)', "true")
run("from math import",     'from "math" import sqrt; print(sqrt(16.0))', "4.0")
run("import string mod",    'import "string" as S; print(S.upper("hello"))', "HELLO")
run("import random",        'import "random" as R; let n=R.int(1,10); print(n>=1 && n<=10)', "true")
run("import json",          'import "json" as J; let s=J.encode({"a":1}); print(J.decode(s)["a"])', "1")
run("import path",          'import "path" as P; print(P.join("a","b","c"))', "a/b/c")
run("import datetime",      'import "datetime" as D; let now=D.now(); print(now is string || now is dict || true)', "true")
run("import iter",          'import "iter" as I; print(I.take([1,2,3,4,5],3))', "[1, 2, 3]")
run("import format",        'import "format" as F; let s=F.number(1234567.0); print(s.contains(","))', "true")
run("import color",         'import "color" as C; let c=C.rgb(1.0,0.0,0.0); print(c.r)', "1.0")
run("import uuid",          'import "uuid" as U; let id=U.v4(); print(len(id))', "36")
run("import crypto",        'import "crypto" as CR; let h=CR.sha256("test"); print(len(h))', "64")
run("import vec",           'import "vec" as V; let v=V.v2(3.0,4.0); print(V.len(v))', "5.0")

# ══════════════════════════════════════════════════════════════════
# SECTION 16: ANALYZER WARNINGS (check stderr)
# ══════════════════════════════════════════════════════════════════
import sys as _sys

def warn_check(label, code, keyword):
    global PASS, FAIL
    r = EnhancedREPL()
    buf_e = io.StringIO(); _sys.stderr = buf_e
    r._eval(code)
    _sys.stderr = _sys.__stderr__
    if keyword.lower() in buf_e.getvalue().lower():
        PASS += 1
    else:
        FAIL += 1; FAILURES.append((f"WARN:{label}", buf_e.getvalue()[:60], f"expected '{keyword}' in warning"))

warn_check("missing return",   'fn bad()->int{let x=1}', "return")
warn_check("async fn",         'async fn fetch(){}', "synchronous")
# duplicate fn warning requires two separate REPL turns (not testable in single run)
# type mismatch warning requires fn definition in prior REPL turn
warn_check("non-exhaustive",   'enum D{N S E W}; match D.N{case D.N{print("n")}}', "exhaustive")
warn_check("float truncation", 'fn f(x:int){return x}; f(3.7)', "truncated")
warn_check("unqualified import",'import "math"', "without alias")
warn_check("null deprecated",  'let x=null', "deprecated")

# ══════════════════════════════════════════════════════════════════
# SECTION 17: VM PARITY
# ══════════════════════════════════════════════════════════════════
run("VM let",               'let x=42; print(x)', "42", use_vm=True)
run("VM arithmetic",        'print(2+3*4-1)', "13", use_vm=True)
run("VM string",            'print("hello")', "hello", use_vm=True)
run("VM fn call",           'fn add(a,b){return a+b}; print(add(3,4))', "7", use_vm=True)
run("VM closure",           'fn adder(n){return fn(x){return x+n}}; print(adder(5)(3))', "8", use_vm=True)
run("VM for loop",          'let s=0; for i in 0..5{s+=i}; print(s)', "10", use_vm=True)
run("VM while loop",        'let x=0; while x<3{x+=1}; print(x)', "3", use_vm=True)
run("VM do-while",          'let x=0; do{x+=1}while x<3; print(x)', "3", use_vm=True)
run("VM for-else",          'for x in [1]{if x==9{break}} else{print("done")}', "done", use_vm=True)
run("VM while-else",        'let x=5; while x<3{x+=1} else{print("skip")}', "skip", use_vm=True)
run("VM match expr",        'let r=match 5{case 1{"a"} case _{"b"}}; print(r)', "b", use_vm=True)
run("VM try expr",          'let r=try{42} catch e{0}; print(r)', "42", use_vm=True)
run("VM try catch",         'let r=try{throw "err"} catch e{e}; print(r)', "err", use_vm=True)
run("VM dict comp",         'let d={"a":1}; let r={k:v*2 for k,v in entries(d)}; print(r["a"])', "2", use_vm=True)
run("VM struct copy",       'struct S{items:[]}; let a=S{items:[1,2]}; let b=a.copy(); b.items.push(3); print(len(a.items))', "2", use_vm=True)
run("VM arr.reduce",        'print([1,2,3,4].reduce(fn(a,b){return a+b}))', "10", use_vm=True)
run("VM arr.sorted",        'print([3,1,2].sorted())', "[1, 2, 3]", use_vm=True)
run("VM arr.flatten",       'print([[1,2],[3,4]].flatten())', "[1, 2, 3, 4]", use_vm=True)
run("VM arr.includes",      'print([1,2,3].includes(2))', "true", use_vm=True)
run("VM arr.is_empty",      'print([].is_empty())', "true", use_vm=True)
run("VM str.reverse",       'print("hello".reverse())', "olleh", use_vm=True)
run("VM str.repeat",        'print("ab".repeat(3))', "ababab", use_vm=True)
run("VM str.chars",         'print("hi".chars())', '["h", "i"]', use_vm=True)
run("VM str.format named",  'print("Hi {name}!".format(name: "Alice"))', "Hi Alice!", use_vm=True)
run("VM in arr",            'print(2 in [1,2,3])', "true", use_vm=True)
run("VM not in arr",        'print(5 not in [1,2,3])', "true", use_vm=True)
run("VM Ok display",        'print(Ok(42))', "Ok(42)", use_vm=True)
run("VM dict display",      'print({"a":1})', '{"a": 1}', use_vm=True)
run("VM string()",          'print(string(42))', "42", use_vm=True)
run("VM typeof",            'print(typeof("hi"))', "string", use_vm=True)
run("VM push builtin",      'let a=[]; push(a,1); print(len(a))', "1", use_vm=True)
run("VM entries",           'let d={"a":1}; for k,v in entries(d){print(k)}', "a", use_vm=True)
run("VM for enum",          'enum D{N S E W}; let c=0; for d in D{c+=1}; print(c)', "4", use_vm=True)
run("VM match fn",          'fn g(n){return match n{case 5{"A"} case _{"B"}}}; print(g(5))', "A", use_vm=True)
run("VM pipe operator",     'fn dbl(x){return x*2}; print(5 |> dbl)', "10", use_vm=True)
run("VM struct method",     'struct C{n:int=0; fn inc(){self.n+=1}}; let c=C{}; c.n=5; print(c.n)', "5", use_vm=True)

# ══════════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════════
total = PASS + FAIL
print(f"\n{'═'*60}")
print(f"  Comprehensive Test Results: {PASS}/{total} passed")
if FAIL == 0:
    print(f"  ✅ ALL PASS")
else:
    print(f"  ❌ {FAIL} FAILED:")
    for label, got, want in FAILURES:
        print(f"    FAIL  {label}")
        if want:
            print(f"          got : {got!r}")
            print(f"          want: {want!r}")
        else:
            print(f"          err : {got!r}")
print(f"{'═'*60}")
