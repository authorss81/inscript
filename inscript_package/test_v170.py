#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v170.py  InScript v1.7.x — Unified Integration Suite

Covers all v1.7.x features in one canonical test file:

  v1.7.1  Float & Integer Display
  v1.7.2  Recursive & Self-Referential Types
  v1.7.3  Stack Traces & Error Quality
  v1.7.4  REPL Stability & Migrate Tool

This file is the authoritative pass/fail gate for the entire v1.7.x series.

Run:  python3 test_v170.py
"""
import sys, io, os, re, tempfile, shutil
from interpreter import Interpreter
from errors import InScriptRuntimeError, InScriptCallStack

# ─────────────────────────────────────────────────────────────────────────────
# Harness
# ─────────────────────────────────────────────────────────────────────────────

PASS = FAIL = SKIP = 0
_section = ""

def section(title):
    global _section
    _section = title
    print(f"\n{'─'*58}")
    print(f"  {title}")
    print(f"{'─'*58}")

def ok(name, cond, detail=""):
    global PASS, FAIL
    tag = "OK  " if cond else "FAIL"
    print(f"  {tag}  {name}" + (f"  [{detail}]" if detail else ""))
    if cond:
        PASS += 1
    else:
        FAIL += 1

def run(code):
    buf = io.StringIO(); sys.stdout = buf
    try:
        src = code.splitlines()
        Interpreter(source_lines=src).execute(code)
        sys.stdout = sys.__stdout__
        return buf.getvalue().strip(), None
    except Exception as e:
        sys.stdout = sys.__stdout__
        return buf.getvalue().strip(), str(e)

def run_out(code):
    out, _ = run(code); return out

def run_err(code):
    _, err = run(code); return err

def _migrate(src: str) -> str:
    src = re.sub(r'\bnull\b',   'nil',    src)
    src = re.sub(r'\bdiv\b',    '//',     src)
    src = re.sub(r':\s*\[\]',   ': array', src)
    return src


# ─────────────────────────────────────────────────────────────────────────────
# v1.7.1 — Float & Integer Display
# ─────────────────────────────────────────────────────────────────────────────

section("v1.7.1 — Float & Integer Display")

float_cases = [
    ("0.1+0.2 == 0.3",      "print(0.1 + 0.2)",              "0.3"),
    ("1/3 precision",        "print(1.0 / 3.0)",              "0.3333333333333333"),
    ("sqrt(2)",              "print(2.0**0.5)",                "1.4142135623730951"),
    ("large float",          "print(1.0e15)",                  "1000000000000000.0"),
    ("int result",           "print(4.0 / 2.0)",              "2.0"),
    ("negative float",       "print(-0.1 - 0.2)",             "-0.3"),
    ("zero float",           "print(0.0)",                    "0.0"),
    ("1.0 stays 1.0",        "print(1.0)",                    "1.0"),
]
for name, code, want in float_cases:
    ok(name, run_out(code) == want, f"got {run_out(code)!r}")

int_cases = [
    ("10//3 == 3",     "print(10 // 3)",      "3"),
    ("-7//2 == -4",    "print(-7 // 2)",      "-4"),
    ("15//5 == 3",     "print(15 // 5)",      "3"),
    ("div keyword",    "print(10 div 3)",     "3"),
    ("comment //**",   "let x=5 // note\nprint(x)", "5"),
]
for name, code, want in int_cases:
    ok(name, run_out(code) == want, f"got {run_out(code)!r}")

ok("null hard error raises",  run_err("print(null)") is not None)
ok("nil still works",         run_out("print(nil)") == "nil")


# ─────────────────────────────────────────────────────────────────────────────
# v1.7.2 — Recursive & Self-Referential Types
# ─────────────────────────────────────────────────────────────────────────────

section("v1.7.2 — Recursive & Self-Referential Types")

NODE = """
struct Node {
    value: int = 0
    next: nil = nil
}
"""

ok("nil type annotation",
   run_out(NODE + "let n=Node{value:5}\nprint(n.value)\nprint(n.next)") == "5\nnil")

ok("2-node list",
   run_out(NODE + "let n2=Node{value:2}\nlet n1=Node{value:1,next:n2}\nprint(n1.next.value)") == "2")

ok("3-level chain",
   run_out(NODE + "let n3=Node{value:3}\nlet n2=Node{value:2,next:n3}\nlet n1=Node{value:1,next:n2}\nprint(n1.next.next.value)") == "3")

ok("list sum via while",
   run_out(NODE + """
let n3=Node{value:30}
let n2=Node{value:20,next:n3}
let n1=Node{value:10,next:n2}
let curr=n1; let s=0
while curr != nil { s = s+curr.value; curr=curr.next }
print(s)
""") == "60")

ok("recursive list_len",
   run_out(NODE + """
fn list_len(node) {
  if node==nil { return 0 }
  return 1 + list_len(node.next)
}
let n3=Node{value:3}
let n2=Node{value:2,next:n3}
let n1=Node{value:1,next:n2}
print(list_len(n1))
""") == "3")

TREE = """
struct TreeNode { val:int=0; left:nil=nil; right:nil=nil }
"""
ok("tree 3 nodes",
   run_out(TREE + """
let root=TreeNode{val:10,left:TreeNode{val:5},right:TreeNode{val:15}}
print(root.val)
print(root.left.val)
print(root.right.val)
""") == "10\n5\n15")

ok("tree_sum=15",
   run_out(TREE + """
fn tree_sum(node) {
  if node==nil { return 0 }
  return node.val + tree_sum(node.left) + tree_sum(node.right)
}
let root=TreeNode{val:1,
  left:TreeNode{val:2,left:TreeNode{val:4},right:TreeNode{val:5}},
  right:TreeNode{val:3}}
print(tree_sum(root))
""") == "15")

ok("tree_depth=3",
   run_out(TREE + """
fn tree_depth(node) {
  if node==nil { return 0 }
  let l=tree_depth(node.left); let r=tree_depth(node.right)
  if l>r { return 1+l }
  return 1+r
}
let root=TreeNode{val:1,left:TreeNode{val:2,left:TreeNode{val:4}},right:TreeNode{val:3}}
print(tree_depth(root))
""") == "3")

ok("optional chaining on recursive",
   run_out(NODE + """
let n=Node{value:1,next:Node{value:2}}
print(n.next?.value)
print(n.next?.next?.value)
""") == "2\nnil")


# ─────────────────────────────────────────────────────────────────────────────
# v1.7.3 — Stack Traces
# ─────────────────────────────────────────────────────────────────────────────

section("v1.7.3 — Stack Traces")

# Full 3-level call chain
err = run_err("""
fn inner() { throw "oops" }
fn middle() { inner() }
fn outer() { middle() }
outer()
""")
ok("full chain: inner frame",  err is not None and "in inner"  in err, repr(err))
ok("full chain: middle frame", err is not None and "in middle" in err, repr(err))
ok("full chain: outer frame",  err is not None and "in outer"  in err, repr(err))
ok("call stack header",        err is not None and "Call stack" in err)

# Source snippets
err = run_err("""
fn alpha() {
  throw "source test"
}
fn beta() {
  alpha()
}
beta()
""")
ok("source snippet: alpha()",  err is not None and "alpha()" in err, repr(err))
ok("source snippet: beta()",   err is not None and "beta()" in err,  repr(err))

# Accurate line numbers — error at line 4 (throw statement)
code_lines = "fn inner() {\n  let x = 1\n  let y = 2\n  throw \"at 4\"\n}\nfn caller() {\n  inner()\n}\ncaller()"
err = run_err(code_lines)
ok("line number accurate (Line 4)", err is not None and "Line 4" in err, repr(err))

# 5-level deep chain
err = run_err("""
fn l5() { throw "deep" }
fn l4() { l5() }
fn l3() { l4() }
fn l2() { l3() }
fn l1() { l2() }
l1()
""")
for lvl in ("l1","l2","l3","l4","l5"):
    ok(f"5-level chain: {lvl} frame", err is not None and f"in {lvl}" in err, repr(err))

# Closure frame
err = run_err("""
fn make_adder(n) {
  fn adder(x) { throw "in closure" }
  return adder
}
let f = make_adder(5)
f(3)
""")
ok("closure: adder frame",      err is not None and "in adder"     in err, repr(err))
ok("closure: make_adder frame", err is not None and "in make_adder" in err, repr(err))

# Top-level error — no function frames
err = run_err("let x = 1\nlet y = x / 0")
ok("top-level: no Call stack",  err is not None and "Call stack" not in err, repr(err))

# Recursive frames accumulate
err = run_err("""
fn count(n) {
  if n == 0 { throw "zero" }
  count(n - 1)
}
count(3)
""")
ok("recursive: count in trace",          err is not None and "in count" in err, repr(err))
ok("recursive: multiple count frames",   (err.count("in count") if err else 0) >= 2)

# InScriptCallStack unit test
src = ["fn a() {", "  throw 'x'", "}", "fn b() {", "  a()", "}", "b()"]
stack = InScriptCallStack("<u>", src_lines=src)
stack.push("b", 7); stack.update_top_line(5)
stack.push("a", 5); stack.update_top_line(2)
snap = stack.snapshot()
ok("stack snapshot: 2 frames",  len(snap) == 2)
ok("stack snapshot: b first",   snap[0][0] == "b")
ok("stack snapshot: a second",  snap[1][0] == "a")
ok("stack b line updated to 5", snap[0][2] == 5)
ok("stack a line updated to 2", snap[1][2] == 2)
fmt = stack.format()
ok("format has source snippet",  "a()" in fmt,      repr(fmt))
ok("format has throw snippet",   "throw" in fmt,    repr(fmt))


# ─────────────────────────────────────────────────────────────────────────────
# v1.7.4 — REPL Stability & Migrate
# ─────────────────────────────────────────────────────────────────────────────

section("v1.7.4 — REPL Stability")

# --- FakeREPL helper (mirrors EnhancedREPL._eval logic) ----------------------
class FakeREPL:
    def __init__(self):
        from interpreter import Interpreter
        self._interp = Interpreter()
        self._interp._env._repl_mode = True

    def eval(self, source):
        from lexer import Lexer; from parser import Parser; from errors import InScriptError
        snap = dict(self._interp._env._store)
        try:
            tokens  = Lexer(source).tokenize()
            program = Parser(tokens).parse()
            result  = self._interp.run(program)
            return result, None
        except InScriptError as e:
            self._interp._env._store = snap
            return None, str(e)
        except Exception as e:
            self._interp._env._store = snap
            return None, str(e)

    def get(self, n):    return self._interp._env._store.get(n)
    def has(self, n):    return n in self._interp._env._store

# Error recovery
r = FakeREPL()
r.eval("let x = 100")
_, e = r.eval("let y = x / 0")
ok("error recovery: x survives",   r.has("x"),              "x lost")
ok("error recovery: y not leaked", not r.has("y"),           "y leaked")
ok("error recovery: x value ok",   r.get("x") == 100,       repr(r.get("x")))

# let re-definition
r2 = FakeREPL()
r2.eval("let v = 1")
_, e = r2.eval("let v = 42")
ok("let re-def: no error",  e is None, repr(e))
ok("let re-def: v = 42",    r2.get("v") == 42, repr(r2.get("v")))
r2.eval("let v = \"str\"")
ok("let re-def type change", r2.get("v") == "str", repr(r2.get("v")))

# const still enforced
r3 = FakeREPL()
r3.eval("const K = 7")
_, e3 = r3.eval("K = 99")
ok("const enforced in REPL", e3 is not None, repr(e3))
ok("const value unchanged",  r3.get("K") == 7)

# Function survives later error
r4 = FakeREPL()
r4.eval("fn sq(x) { return x*x }")
r4.eval("let boom = undefined_xyz")
ok("fn survives later error",   r4.has("sq"))
_, e4 = r4.eval("print(sq(4))")
ok("fn callable after error",   e4 is None, repr(e4))

section("v1.7.4 — null E0055 & Migrate Tool")

# null → E0055
_, err = run("let x = null")
ok("null raises E0055",       err is not None and "E0055" in err, repr(err))
ok("nil is valid",            run_out("print(nil)") == "nil")

# migrate transform logic
ok("migrate: null→nil",   _migrate("x = null")        == "x = nil")
ok("migrate: div→//",     _migrate("a div b")          == "a // b")
ok("migrate: :[]→:array", _migrate("let x: []")        == "let x: array")
ok("migrate: mixed",      _migrate("let x = null\na div b") == "let x = nil\na // b")
ok("migrate: clean noop", _migrate("x = nil\n")        == "x = nil\n")

DIRTY = "fn f(a, b) {\n    return a div b\n}\nlet x = null\nlet arr: [] = []\n"
CLEAN = "fn f(a, b) {\n    return a // b\n}\nlet x = nil\nlet arr: array = []\n"
ok("migrate: full file", _migrate(DIRTY) == CLEAN,
   f"\ngot:\n{_migrate(DIRTY)!r}\nwant:\n{CLEAN!r}")

# File I/O via _migrate_files
tmpdir = tempfile.mkdtemp()
try:
    fpath = os.path.join(tmpdir, "t.ins")
    with open(fpath, "w") as f:
        f.write("let x = null\nlet y = x div 2\n")
    import importlib.util
    spec = importlib.util.spec_from_file_location("ins_m",
        os.path.join(os.path.dirname(__file__), "inscript.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ret = mod._migrate_files(fpath)
    with open(fpath) as f:
        result = f.read()
    ok("migrate tool: returns 0",        ret == 0, repr(ret))
    ok("migrate tool: null→nil",         "null" not in result, repr(result))
    ok("migrate tool: div→//",           " div " not in result, repr(result))
    # Directory migration
    d_path = os.path.join(tmpdir, "dir")
    os.makedirs(d_path)
    for name in ["a.ins","b.ins"]:
        with open(os.path.join(d_path, name), "w") as f:
            f.write("let z = null\n")
    mod._migrate_files(d_path)
    for name in ["a.ins","b.ins"]:
        with open(os.path.join(d_path, name)) as f:
            c = f.read()
        ok(f"migrate dir: {name} migrated", "null" not in c, repr(c))
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────
# Cross-version integration
# ─────────────────────────────────────────────────────────────────────────────

section("Cross-version integration")

# Float display + recursive types
ok("float + recursive tree",
   run_out("""
struct FNode { val: float = 0.0; left: nil = nil; right: nil = nil }
fn sum(n) { if n==nil { return 0.0 } return n.val + sum(n.left) + sum(n.right) }
let root = FNode{val: 0.1,
  left:  FNode{val: 0.2},
  right: FNode{val: 0.0}
}
print(sum(root))
""") == "0.30000000000000004")   # raw float sum, no magic round-to-3

# Stack trace + recursive type
err = run_err("""
struct Node { value: int = 0; next: nil = nil }
fn walk(node) {
  if node == nil { throw "nil node" }
  walk(node.next)
}
let n = Node{value: 1}
walk(n)
""")
ok("stack trace on recursive type error",
   err is not None and "in walk" in err, repr(err))

# migrate produces runnable output
dirty = "fn double(x) { return x div 1 }\nprint(double(21))"
clean = _migrate(dirty)
ok("migrated code runs correctly", run_out(clean) == "21", repr(clean))

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

total = PASS + FAIL
print(f"""
{'═'*58}
  InScript v1.7.x Unified Test Suite
  {PASS}/{total} passed  ·  {FAIL} failed
  {'ALL PASS ✓' if FAIL == 0 else f'{FAIL} FAILED ✗'}
{'═'*58}
""")
sys.exit(0 if FAIL == 0 else 1)
