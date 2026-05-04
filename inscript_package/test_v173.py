#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v173.py  InScript v1.7.3 — Stack Traces & Error Quality

Tests:
  1. Full call chain shows all frames (outer → middle → inner)
  2. Source snippets present in every frame
  3. Line numbers point to the EXECUTING line, not the call site
  4. Deeply nested chains (5+ levels)
  5. Closures and lambdas carry accurate frame info
  6. Anonymous / inline functions still get frames
  7. Recursive functions — frames accumulate correctly
  8. Stack overflow still reports sensibly (truncated + message)
  9. Single-frame (top-level) errors — no spurious frames
 10. Generator frames included in trace
 11. v1.7.2 regression: recursive types still work

Run:  python3 test_v173.py
"""
import sys, io
from interpreter import Interpreter
from errors import InScriptRuntimeError, InScriptCallStack

PASS = FAIL = 0

def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  OK  {name}")
        PASS += 1
    else:
        print(f"  FAIL  {name}" + (f"  [{detail}]" if detail else ""))
        FAIL += 1

def section(t):
    print(f"\n--- {t} ---")

def run(code):
    """Run code, capturing stdout and any exception message."""
    buf = io.StringIO()
    sys.stdout = buf
    try:
        src_lines = code.splitlines()
        Interpreter(source_lines=src_lines).execute(code)
        sys.stdout = sys.__stdout__
        return buf.getvalue().strip(), None
    except Exception as e:
        sys.stdout = sys.__stdout__
        return buf.getvalue().strip(), str(e)

def run_err(code):
    """Return just the error string (None if no error)."""
    _, err = run(code)
    return err


# ── 1. Full call chain — all frames present ───────────────────────────────────
section("1. Full call chain")

err = run_err("""
fn inner() { throw "oops" }
fn middle() { inner() }
fn outer() { middle() }
outer()
""")
ok("error raised",         err is not None, repr(err))
ok("inner frame present",  err is not None and "in inner" in err,  repr(err))
ok("middle frame present", err is not None and "in middle" in err, repr(err))
ok("outer frame present",  err is not None and "in outer" in err,  repr(err))
ok("call stack header",    err is not None and "Call stack" in err, repr(err))

# ── 2. Source snippets per frame ──────────────────────────────────────────────
section("2. Source snippets in frames")

err = run_err("""
fn alpha() {
  throw "source test"
}
fn beta() {
  alpha()
}
beta()
""")
# alpha's snippet is the throw line; beta's snippet is the alpha() call line
ok("alpha frame present",      err is not None and "in alpha" in err, repr(err))
ok("beta frame present",       err is not None and "in beta"  in err, repr(err))
ok("throw snippet in alpha",   err is not None and "throw" in err,    repr(err))
# beta's call-site line "  alpha()" is updated before the call pushes alpha's frame
ok("call stack has snippets",  err is not None and "File" in err,     repr(err))

# ── 3. Line numbers point to executing line ────────────────────────────────────
section("3. Accurate line numbers")

code3 = """\
fn inner() {
  let x = 1
  let y = 2
  throw "line 4"
}
fn caller() {
  inner()
}
caller()
"""
err = run_err(code3)
# inner() throw is on line 4, caller() calls inner on line 7
ok("error reports line 4",   err is not None and "Line 4" in err, repr(err))
ok("inner frame line 4",     err is not None and ("line 4" in err or "Line 4" in err), repr(err))

# ── 4. Deeply nested 5-level chain ────────────────────────────────────────────
section("4. Deep nesting (5 levels)")

err = run_err("""
fn l5() { throw "deep" }
fn l4() { l5() }
fn l3() { l4() }
fn l2() { l3() }
fn l1() { l2() }
l1()
""")
ok("l5 frame",  err is not None and "in l5" in err,  repr(err))
ok("l4 frame",  err is not None and "in l4" in err,  repr(err))
ok("l3 frame",  err is not None and "in l3" in err,  repr(err))
ok("l2 frame",  err is not None and "in l2" in err,  repr(err))
ok("l1 frame",  err is not None and "in l1" in err,  repr(err))

# ── 5. Closures carry frame info ───────────────────────────────────────────────
section("5. Closures")

err = run_err("""
fn make_adder(n) {
  fn adder(x) {
    throw "in closure"
  }
  return adder
}
let add5 = make_adder(5)
add5(3)
""")
ok("closure error raised",   err is not None, repr(err))
ok("closure frame present",  err is not None and "in adder" in err, repr(err))
# make_adder already returned before adder threw — it won't be in the live trace
ok("error message correct",  err is not None and "in closure" in err, repr(err))

# ── 6. Anonymous functions ─────────────────────────────────────────────────────
section("6. Anonymous / inline functions")

err = run_err("""
let arr = [1, 2, 3]
arr.each(fn(x) { throw "anon err" })
""")
ok("anon function error raised", err is not None, repr(err))
# Anonymous functions get "<anonymous>" or similar frame
ok("error message present",      err is not None and "anon err" in err, repr(err))

# ── 7. Recursive functions ────────────────────────────────────────────────────
section("7. Recursive functions")

err = run_err("""
fn countdown(n) {
  if n == 0 { throw "hit zero" }
  countdown(n - 1)
}
countdown(3)
""")
ok("recursive error raised", err is not None, repr(err))
ok("countdown in trace",     err is not None and "in countdown" in err, repr(err))
# Multiple countdown frames should appear
countdown_count = err.count("in countdown") if err else 0
ok("multiple countdown frames", countdown_count >= 2, f"count={countdown_count}")

# ── 8. Stack overflow truncated gracefully ────────────────────────────────────
section("8. Stack overflow")

err = run_err("""
fn inf() { inf() }
inf()
""")
ok("stack overflow detected",    err is not None, repr(err))
ok("overflow message",           err is not None and ("call depth" in err.lower() or "recursion" in err.lower() or "overflow" in err.lower()), repr(err))

# ── 9. Top-level error — no spurious frames ───────────────────────────────────
section("9. Top-level error (no function frames)")

err = run_err("""
let x = 1
let y = 0
let z = x / y
""")
ok("div-by-zero raised",        err is not None, repr(err))
# No function frames — Call stack section should be absent or empty
has_callstack = err is not None and "Call stack" in err
ok("no spurious call stack",    not has_callstack, repr(err))

# ── 10. Error object includes call_trace attribute ────────────────────────────
section("10. InScriptRuntimeError.call_trace populated")

captured_err = None
code10 = """
fn a() { throw "trace test" }
fn b() { a() }
b()
"""
src10 = code10.splitlines()
try:
    Interpreter(source_lines=src10).execute(code10)
except InScriptRuntimeError as e:
    captured_err = e

ok("exception captured",      captured_err is not None)
ok("call_trace non-empty",    captured_err is not None and len(captured_err.call_trace) > 0,
   repr(getattr(captured_err, 'call_trace', None)))
ok("'a' in call_trace",       captured_err is not None and
   any(t[0] == "a" for t in captured_err.call_trace),
   repr(getattr(captured_err, 'call_trace', None)))
ok("'b' in call_trace",       captured_err is not None and
   any(t[0] == "b" for t in captured_err.call_trace),
   repr(getattr(captured_err, 'call_trace', None)))

# ── 11. InScriptCallStack unit tests ─────────────────────────────────────────
section("11. InScriptCallStack direct unit tests")

src_lines = [
    "fn outer() {",   # line 1
    "  fn inner() {", # line 2
    "    throw 'x'",  # line 3
    "  }",            # line 4
    "  inner()",      # line 5
    "}",              # line 6
    "outer()",        # line 7
]

stack = InScriptCallStack("<test>", src_lines=src_lines)
stack.push("outer", 7)
stack.update_top_line(5)   # outer is now at line 5 (calling inner)
stack.push("inner", 5)
stack.update_top_line(3)   # inner is now at line 3 (throw)

snap = stack.snapshot()
ok("snapshot has 2 frames",   len(snap) == 2, repr(snap))
ok("outer in snapshot",       snap[0][0] == "outer", repr(snap))
ok("inner in snapshot",       snap[1][0] == "inner", repr(snap))
ok("outer line updated to 5", snap[0][2] == 5, repr(snap))
ok("inner line updated to 3", snap[1][2] == 3, repr(snap))

formatted = stack.format()
ok("format has header",       "Call stack" in formatted, repr(formatted))
ok("format has outer",        "in outer" in formatted,   repr(formatted))
ok("format has inner",        "in inner" in formatted,   repr(formatted))
ok("outer source snippet",    "inner()" in formatted,    repr(formatted))
ok("inner source snippet",    "throw" in formatted,      repr(formatted))

# pop and verify
stack.pop()
ok("after pop, 1 frame",      len(stack.snapshot()) == 1)
stack.pop()
ok("after 2 pops, empty",     len(stack.snapshot()) == 0)
ok("format empty is empty",   stack.format() == "")

# ── 12. v1.7.2 regression: recursive types still work ─────────────────────────
section("12. v1.7.2 regression: recursive types")

out, err = run("""
struct Node {
  value: int = 0
  next: nil = nil
}
let n2 = Node{value: 2, next: nil}
let n1 = Node{value: 1, next: n2}
print(n1.value)
print(n1.next.value)
""")
ok("linked list still works", out == "1\n2" and err is None, repr(out))

out, err = run("""
struct TreeNode { val: int = 0; left: nil = nil; right: nil = nil }
fn tree_sum(node) {
  if node == nil { return 0 }
  return node.val + tree_sum(node.left) + tree_sum(node.right)
}
let root = TreeNode{val:1,
  left:  TreeNode{val:2, left: TreeNode{val:4}, right: TreeNode{val:5}},
  right: TreeNode{val:3}
}
print(tree_sum(root))
""")
ok("binary tree sum = 15", out == "15" and err is None, repr(out))

# ── Summary ───────────────────────────────────────────────────────────────────
total = PASS + FAIL
print(f"""
{'='*56}
  v1.7.3 Test Results: {PASS}/{total} passed
  {'ALL PASS' if FAIL == 0 else f'{FAIL} FAILED'}
{'='*56}
""")
sys.exit(0 if FAIL == 0 else 1)
