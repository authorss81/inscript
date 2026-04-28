#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v160.py  InScript v1.6.0 — Tooling & Developer Experience tests

  * inscript --check-all DIR
  * inscript --fmt-all DIR
  * inscript --strict
  * REPL .lint / .strict commands
  * Regression: all previous features

Run:  python3 test_v160.py
"""
import sys, os, subprocess, tempfile, io
from interpreter import Interpreter

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

def cli(args, src=None):
    cmd = [sys.executable, "inscript.py"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       input=src)
    return r.returncode, r.stdout, r.stderr

def run(code):
    buf = io.StringIO(); sys.stdout = buf
    try:
        Interpreter().execute(code)
        sys.stdout = sys.__stdout__
        return buf.getvalue().strip(), None
    except Exception as e:
        sys.stdout = sys.__stdout__
        return None, str(e)

def ins(content):
    """Write content to a temp .ins file, return path (forward slashes)."""
    fd, path = tempfile.mkstemp(suffix=".ins")
    os.write(fd, content.encode()); os.close(fd)
    return path.replace("\\", "/")

def ins_dir(files):
    """Create temp dir with named .ins files. files = {name: content}"""
    d = tempfile.mkdtemp().replace("\\", "/")
    for name, content in files.items():
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(content)
    return d

# ── 1. inscript --check-all ───────────────────────────────────────────────────
section("1. inscript --check-all")

# Clean directory → exit 0
d = ins_dir({"a.ins": "let x: int = 42\n", "b.ins": "fn f(n:int)->int{return n*2}\n"})
rc, out, _ = cli(["--check-all", d])
ok("check-all: clean dir exits 0", rc == 0)
ok("check-all: reports OK for clean files", "OK" in out)
ok("check-all: reports file count", "Checked 2 files" in out)

# Dir with error → exit 1
d = ins_dir({"good.ins": "let n: int = 5\n", "bad.ins": "let s: int = \"oops\"\n"})
rc, out, err = cli(["--check-all", d])
ok("check-all: error dir exits 1", rc == 1)
ok("check-all: reports ERR line", "ERR" in out or "ERR" in err)
ok("check-all: still checks all files (not just first)", "Checked 2 files" in out)

# Empty directory → exit 0
d = ins_dir({})
rc, out, _ = cli(["--check-all", d])
ok("check-all: empty dir exits 0", rc == 0)
ok("check-all: reports no files found", "No .ins files" in out)

# --check-all --strict: unused var treated as error
d = ins_dir({"unused.ins": "fn foo() { let x = 5 }\n"})
rc, out, err = cli(["--strict", "--check-all", d])
ok("check-all --strict: unused var → exit 1", rc == 1)

# ── 2. inscript --fmt-all ─────────────────────────────────────────────────────
section("2. inscript --fmt-all")

d = ins_dir({"messy.ins": "let x=1+2\nlet y=x*3\n"})
messy_path = os.path.join(d, "messy.ins")
rc, out, _ = cli(["--fmt-all", d])
ok("fmt-all: exits 0", rc == 0)
ok("fmt-all: reports FMT for changed file", "FMT" in out)

# Rerun on already-formatted → reports OK
rc2, out2, _ = cli(["--fmt-all", d])
ok("fmt-all: second run reports OK (already clean)", "OK" in out2 and "FMT" not in out2)

# Multiple files
d = ins_dir({
    "a.ins": "let a=1\n",
    "b.ins": "let b=2\n",
    "c.ins": "let c=3\n",
})
rc, out, _ = cli(["--fmt-all", d])
ok("fmt-all: processes all files in dir", "3 file" in out or "3 files" in out or "3 already" in out)

# Empty dir
d = ins_dir({})
rc, out, _ = cli(["--fmt-all", d])
ok("fmt-all: empty dir exits 0", rc == 0)

# ── 3. inscript --strict ──────────────────────────────────────────────────────
section("3. inscript --strict")

# Unused var → should fail with --strict
p = ins("fn foo() { let x = 5 }\nfoo()\n")
rc, out, err = cli(["--strict", p])
ok("--strict: unused var exits 1", rc == 1, f"exit={rc}")
os.unlink(p)

# Clean code → should pass with --strict
p = ins("fn add(a: int, b: int) -> int { return a + b }\nprint(add(1,2))\n")
rc, out, err = cli(["--strict", "--no-warn", p])
ok("--strict: clean code exits 0", rc == 0 and "3" in out, f"exit={rc} out={out!r}")
os.unlink(p)

# --strict is equivalent to --warn-as-error
p = ins("fn foo() { let x = 5 }\nfoo()\n")
rc_strict, _, _ = cli(["--strict", p])
rc_wae,    _, _ = cli(["--warn-as-error", p])
ok("--strict same behavior as --warn-as-error", rc_strict == rc_wae)
os.unlink(p)

# ── 4. _check_all_files and _fmt_all_files API ────────────────────────────────
section("4. Helper function API")

from inscript import _check_all_files, _fmt_all_files

# _check_all_files returns 0 on clean
d = ins_dir({"ok.ins": "let n: int = 1\n"})
rc = _check_all_files(d)
ok("_check_all_files: clean → 0", rc == 0)

# _check_all_files returns 1 on error
d = ins_dir({"err.ins": "let s: int = \"bad\"\n"})
rc = _check_all_files(d)
ok("_check_all_files: error → 1", rc == 1)

# _fmt_all_files returns 0
d = ins_dir({"f.ins": "let x=1\n"})
rc = _fmt_all_files(d)
ok("_fmt_all_files: exits 0", rc == 0)

# ── 5. REPL commands present ─────────────────────────────────────────────────
section("5. REPL .lint and .strict present")

# Check .lint and .strict appear in the REPL handler (not calling REPL directly)
with open("repl.py") as f:
    repl_src = f.read()
ok("repl.py has .lint handler", 'c == ".lint"' in repl_src)
ok("repl.py has .strict handler", 'c == ".strict"' in repl_src)
ok("repl.py .lint in help table", '".lint"' in repl_src)
ok("repl.py .strict in help table", '".strict"' in repl_src)

# ── 6. Regression ─────────────────────────────────────────────────────────────
section("6. Regression")

regressions = [
    ("defer",        'fn f(){defer print("d"); print("b")} f()',              "b\nd"),
    ("repeat-until", 'let i=0; repeat{print(i);i=i+1}until i>=2',           "0\n1"),
    ("type-narrow",  'fn f(v){match v{case int x{print("int")} case _{print("other")}}} f(1)',  "int"),
    ("constraint",   'fn mx<T: Comparable>(a:T,b:T)->T{if a>b{return a}return b} print(mx(3,7))', "7"),
    ("dict module",  'import "dict" as d; let m={"a":1}; print(d.has(m,"a"))', "true"),
    ("string module",'import "string" as s; print(s.replace_all("aXb","X","-"))', "a-b"),
    ("array module", 'import "array" as a; print(a.sort_by([3,1,2],fn(x)=>x))', "[1, 2, 3]"),
    ("math.wrap",    'import "math" as m; print(m.wrap(15,0,10))',            "5"),
    ("color.from_hsv",'import "color" as c; let r=c.from_hsv(0.0,1.0,1.0); print(r.r > 0.9)', "true"),
]
for name, code, want in regressions:
    out, err = run(code)
    ok(f"regression: {name}", out == want and err is None, f"got={out!r}")

total = PASS + FAIL
print(f"""
{'='*56}
  v1.6.0 Test Results: {PASS}/{total} passed
  {'ALL PASS' if FAIL == 0 else f'{FAIL} FAILED'}
{'='*56}
""")
sys.exit(0 if FAIL == 0 else 1)
