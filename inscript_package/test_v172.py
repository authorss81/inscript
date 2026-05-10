#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v172.py  InScript v1.7.2 — Recursive Types tests

  * Self-referential structs (linked list, tree)
  * nil as type annotation (next: nil = nil)
  * Mutually-recursive structs
  * v1.7.1 regression: float display, // operator, null hard error

Run:  python3 test_v172.py
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

# ── 1. nil as type annotation ─────────────────────────────────────────────────
section("1. nil type annotation")

out, err = run("""
struct Node {
    value: int = 0
    next: nil = nil
}
let n = Node{value: 5}
print(n.value)
print(n.next)
""")
ok("nil type annotation parses", out == "5\nnil" and err is None, repr(out))

# ── 2. Linked list ────────────────────────────────────────────────────────────
section("2. Linked list")

LIST = """
struct Node {
    value: int = 0
    next: nil = nil
}
"""

out, err = run(LIST + """
let n2 = Node{value: 2, next: nil}
let n1 = Node{value: 1, next: n2}
print(n1.value)
print(n1.next.value)
""")
ok("2-node linked list", out == "1\n2" and err is None, repr(out))

out, err = run(LIST + """
let n3 = Node{value: 3}
let n2 = Node{value: 2, next: n3}
let n1 = Node{value: 1, next: n2}
print(n1.next.next.value)
""")
ok("3-level chain", out == "3" and err is None, repr(out))

out, err = run(LIST + """
let n3 = Node{value: 30}
let n2 = Node{value: 20, next: n3}
let n1 = Node{value: 10, next: n2}
let curr = n1
let sum = 0
while curr != nil {
    sum = sum + curr.value
    curr = curr.next
}
print(sum)
""")
ok("traverse linked list sum = 60", out == "60" and err is None, repr(out))

out, err = run(LIST + """
fn list_len(node) {
    if node == nil { return 0 }
    return 1 + list_len(node.next)
}
let n3 = Node{value: 3}
let n2 = Node{value: 2, next: n3}
let n1 = Node{value: 1, next: n2}
print(list_len(n1))
""")
ok("recursive list_len = 3", out == "3" and err is None, repr(out))

# ── 3. Binary tree ────────────────────────────────────────────────────────────
section("3. Binary tree")

TREE = """
struct TreeNode {
    val: int = 0
    left: nil = nil
    right: nil = nil
}
"""

out, err = run(TREE + """
let root = TreeNode{val: 10,
    left: TreeNode{val: 5},
    right: TreeNode{val: 15}
}
print(root.val)
print(root.left.val)
print(root.right.val)
""")
ok("binary tree 3 nodes", out == "10\n5\n15" and err is None, repr(out))

out, err = run(TREE + """
fn tree_sum(node) {
    if node == nil { return 0 }
    return node.val + tree_sum(node.left) + tree_sum(node.right)
}
let root = TreeNode{val:1,
    left: TreeNode{val:2, left: TreeNode{val:4}, right: TreeNode{val:5}},
    right: TreeNode{val:3}
}
print(tree_sum(root))
""")
ok("tree_sum = 15", out == "15" and err is None, repr(out))

out, err = run(TREE + """
fn tree_depth(node) {
    if node == nil { return 0 }
    let l = tree_depth(node.left)
    let r = tree_depth(node.right)
    if l > r { return 1 + l }
    return 1 + r
}
let root = TreeNode{val:1,
    left: TreeNode{val:2, left: TreeNode{val:4}},
    right: TreeNode{val:3}
}
print(tree_depth(root))
""")
ok("tree_depth = 3", out == "3" and err is None, repr(out))

# ── 4. Nil safety on recursive fields ─────────────────────────────────────────
section("4. Nil safety")

out, err = run(LIST + """
let n = Node{value: 42}
print(n.next)
print(n.next == nil)
""")
ok("nil next field == nil", out == "nil\ntrue" and err is None, repr(out))

out, err = run(LIST + """
let n = Node{value: 1, next: Node{value: 2}}
print(n.next?.value)
print(n.next?.next?.value)
""")
ok("optional chaining on recursive field", out == "2\nnil" and err is None, repr(out))

# ── 5. v1.7.1 regression: float, //, null ────────────────────────────────────
section("5. v1.7.1 regression")

cases = [
    ("0.1+0.2", "print(0.1 + 0.2)", "0.3"),
    ("1.0/3.0", "print(1.0 / 3.0)", "0.3333333333333333"),
    ("sqrt2",   "print(2.0**0.5)",   "1.4142135623730951"),
    ("10//3",   "print(10//3)",      "3"),
    ("-7//2",   "print(-7//2)",      "-4"),
    ("comment", "let x=5 // note\nprint(x)", "5"),
    # v1.9.5: "div kw" removed from valid-cases — div is now a hard parse error (E0056)
]
for name, code, want in cases:
    out, err = run(code)
    ok(f"v1.7.1 {name}", out == want and err is None, repr(out))

# v1.9.5: div keyword is now a hard parse error
out, err = run("print(10 div 3)")
ok("v1.9.5 div is hard error (E0056)", err is not None and "E0056" in err, repr(err))

out, err = run("print(null)")
ok("null hard error", err is not None and "removed" in err)

total = PASS + FAIL
print(f"""
{'='*56}
  v1.7.2 Test Results: {PASS}/{total} passed
  {'ALL PASS' if FAIL == 0 else f'{FAIL} FAILED'}
{'='*56}
""")
sys.exit(0 if FAIL == 0 else 1)
