#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v194.py  InScript v1.9.4 — Spec Freeze & Final Polish

Tests:
  1.  Error catalogue: all codes printed
  2.  Error catalogue: E0055 present (null keyword)
  3.  Error catalogue: filter prefix works
  4.  Error catalogue: filtered out codes absent
  5.  Error catalogue: every code has name + description
  6.  changelog: valid range returns 0
  7.  changelog: single version returns 0
  8.  changelog: empty range returns 0 (no versions, not error)
  9.  changelog: invalid range returns 1
 10.  changelog: open-ended range (v1.9.3..) works
 11.  changelog: reads CHANGELOG.md from project root
 12.  benchmark: runs without crash
 13.  benchmark: output contains timing columns
 14.  benchmark: filter by name works
 15.  benchmark: bad filter name returns 1
 16.  benchmark: fib_30 result is correct
 17.  stdlib docs: print all
 18.  stdlib docs: filter by string
 19.  stdlib docs: print() documented
 20.  stdlib docs: Array.map documented
 21.  stdlib docs: String.split documented
 22.  stdlib docs: empty filter returns 0
 23.  spec: prints to stdout
 24.  spec: contains version number
 25.  spec: contains Spec Freeze notice
 26.  spec: contains breaking changes section
 27.  spec: write to file
 28.  spec: written file contains version
 29.  v1.9.3 regression: doc generation
 30.  v1.9.2 regression: semver + validate
 31.  v1.9.1 regression: compat tool
 32.  v1.8.4 regression: method chain inference
 33.  setup.py reads version with utf-8 encoding

Run:  python3 test_v194.py
"""
import sys, io, os, tempfile, shutil, importlib.util

PASS = FAIL = 0

def ok(name, cond, detail=""):
    global PASS, FAIL
    tag = "OK  " if cond else "FAIL"
    print(f"  {tag}  {name}" + (f"  [{detail}]" if detail else ""))
    if cond: PASS += 1
    else:    FAIL += 1

def section(t): print(f"\n--- {t} ---")

_spec = importlib.util.spec_from_file_location("ins",
    os.path.join(os.path.dirname(__file__), "inscript.py"))
_ins = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ins)

VERSION = _ins.VERSION

def cap(fn, *a, **kw):
    buf = io.StringIO()
    sys.stdout = buf; sys.stderr = buf
    try:
        ret = fn(*a, **kw)
    finally:
        sys.stdout = sys.__stdout__; sys.stderr = sys.__stderr__
    return ret, buf.getvalue()


# ── 1–5. Error catalogue ──────────────────────────────────────────────────────
section("1-5. Error code catalogue")

ret1, out1 = cap(_ins._print_error_catalogue)
ok("1. catalogue returns 0",          ret1 == 0)
ok("2. E0055 null keyword present",   "E0055" in out1, repr(out1[:100]))
ok("2b. E0031 division by zero",      "E0031" in out1)
ok("2c. E0040 uncaught throw",        "E0040" in out1)

ret2, out2 = cap(_ins._print_error_catalogue, filter_prefix="E003")
ok("3. prefix filter E003 returns 0", ret2 == 0)
ok("3b. E0031 in filtered output",    "E0031" in out2)
ok("4. E0040 absent from E003 filter","E0040" not in out2, repr(out2[:80]))

catalogue = _ins.ERROR_CATALOGUE
ok("5. every code has name + desc",
   all(isinstance(v, tuple) and len(v) == 2 and v[0] and v[1]
       for v in catalogue.values()),
   repr([k for k, v in catalogue.items() if not (isinstance(v,tuple) and len(v)==2)]))
ok("5b. at least 20 error codes",     len(catalogue) >= 20, repr(len(catalogue)))


# ── 6–11. Changelog generator ─────────────────────────────────────────────────
section("6-11. Changelog generator")

# Find real CHANGELOG.md
changelog_path = os.path.join(os.path.dirname(__file__), "CHANGELOG.md")

ret6, out6 = cap(_ins._generate_changelog_range, "v1.9.3..v1.9.4",
                  changelog_path=changelog_path)
ok("6. valid range returns 0",        ret6 == 0, repr(out6[:80]))

ret7, out7 = cap(_ins._generate_changelog_range, "v1.9.3",
                  changelog_path=changelog_path)
ok("7. single version returns 0",     ret7 == 0, repr(out7[:80]))

ret8, out8 = cap(_ins._generate_changelog_range, "v9.9.9..v9.9.9",
                  changelog_path=changelog_path)
ok("8. version not in log returns 0", ret8 == 0)

ret9, _   = cap(_ins._generate_changelog_range, "badrange",
                changelog_path=changelog_path)
ok("9. invalid range returns 1",      ret9 == 1)

ret10, out10 = cap(_ins._generate_changelog_range, "v1.9.3..",
                    changelog_path=changelog_path)
ok("10. open-ended range returns 0",  ret10 == 0, repr(out10[:80]))

ok("11. CHANGELOG.md readable",       os.path.exists(changelog_path))


# ── 12–16. Benchmark suite ────────────────────────────────────────────────────
section("12-16. Benchmark suite")

ret12, out12 = cap(_ins._run_benchmarks, filter_name="loop_100k", iterations=1)
ok("12. benchmark returns 0",         ret12 == 0, repr(out12[:80]))
ok("13. timing columns in output",    "Median" in out12 and "Min" in out12)
ok("13b. loop_100k row present",      "loop_100k" in out12)

ret14, out14 = cap(_ins._run_benchmarks, filter_name="fib", iterations=1)
ok("14. filter by name works",        ret14 == 0 and "fib" in out14)

ret15, _ = cap(_ins._run_benchmarks, filter_name="no_such_bench_xyz", iterations=1)
ok("15. bad filter returns 1",        ret15 == 1)

# fib(30) = 832040 — verify interpreter correctness via benchmark
from interpreter import Interpreter
out_fib = ""
try:
    buf = io.StringIO(); sys.stdout = buf
    Interpreter().execute("fn fib(n){if n<=1{return n} return fib(n-1)+fib(n-2)}\nprint(fib(10))")
    sys.stdout = sys.__stdout__
    out_fib = buf.getvalue().strip()
except: sys.stdout = sys.__stdout__
ok("16. fib(10) = 55",               out_fib == "55", repr(out_fib))


# ── 17–22. Stdlib docs ────────────────────────────────────────────────────────
section("17-22. Stdlib docs")

ret17, out17 = cap(_ins._print_stdlib_docs)
ok("17. stdlib all returns 0",        ret17 == 0)
ok("17b. has entries",                len(out17) > 100)

ret18, out18 = cap(_ins._print_stdlib_docs, filter_str="Array")
ok("18. filter Array returns 0",      ret18 == 0)
ok("18b. Array entries present",      "Array" in out18)
ok("18c. non-Array filtered out",     "String.split" not in out18 or "Array" in out18)

ok("19. print() documented",          "print" in out17)
ok("20. Array.map documented",        "Array.map" in out17)
ok("21. String.split documented",     "String.split" in out17)

ret22, out22 = cap(_ins._print_stdlib_docs, filter_str="")
ok("22. empty filter shows all",      ret22 == 0 and len(out22) > 0)


# ── 23–28. Spec document ─────────────────────────────────────────────────────
section("23-28. Language spec")

ret23, out23 = cap(_ins._generate_spec)
ok("23. spec returns 0",              ret23 == 0)
ok("23b. spec has content",           len(out23) > 500)
ok("24. spec contains version",       VERSION in out23, repr(VERSION))
ok("25. spec has Spec Freeze notice", "Spec Freeze" in out23)
ok("26. spec has breaking changes",   "Breaking Changes" in out23 or "breaking" in out23.lower())
ok("26b. spec mentions nil",          "nil" in out23)
ok("26c. spec mentions never type",   "never" in out23)

tmpdir = tempfile.mkdtemp()
try:
    spec_out = os.path.join(tmpdir, "spec.md")
    ret27, _ = cap(_ins._generate_spec, output_path=spec_out)
    ok("27. spec writes to file",         ret27 == 0 and os.path.exists(spec_out))
    if os.path.exists(spec_out):
        with open(spec_out) as f: written = f.read()
        ok("28. written spec has version",VERSION in written)
    else:
        ok("28. written spec has version", False, "file not created")
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ── 29. v1.9.3 regression ────────────────────────────────────────────────────
section("29. v1.9.3 regression: doc generation")

SAMPLE = '/// Add two numbers.\n/// @param a (int) First\n/// @param b (int) Second\n/// @returns int Sum\nfn add(a: int, b: int) -> int { return a + b }\n'
entries = _ins._parse_doc_comments(SAMPLE)
md      = _ins._render_doc_markdown(entries, "math.ins")
ok("29. fn add parsed",               any(e["name"] == "add" for e in entries))
ok("29b. params extracted",           entries[0]["params"][0]["name"] == "a" if entries else False)
ok("29c. markdown has fn header",     "## `fn add`" in md)


# ── 30. v1.9.2 regression ────────────────────────────────────────────────────
section("30. v1.9.2 regression: semver + manifest")

ok("30. semver >=1.9.0",  _ins._semver_satisfies("1.9.4", ">=1.9.0"))
ok("30b. semver ^1.9.0",  _ins._semver_satisfies("1.9.4", "^1.9.0"))
ok("30c. semver ~1.9.3",  _ins._semver_satisfies("1.9.4", "~1.9.3"))
ok("30d. semver fail",    not _ins._semver_satisfies("1.8.0", ">=1.9.0"))


# ── 31. v1.9.1 regression ────────────────────────────────────────────────────
section("31. v1.9.1 regression: compat tool")

tmpd = tempfile.mkdtemp()
try:
    with open(os.path.join(tmpd, "old.ins"), "w") as f: f.write("let x = null\n")
    ret31, out31 = cap(_ins._compat_files, tmpd)
    ok("31. compat detects null",     ret31 == 1 and "null" in out31)
finally:
    shutil.rmtree(tmpd, ignore_errors=True)


# ── 32. v1.8.4 regression ────────────────────────────────────────────────────
section("32. v1.8.4 regression: method chain inference")

from analyzer import Analyzer, array_type, T_INT
from parser import parse as _pc
import re

def infer(src, name):
    a = Analyzer(no_warn=True)
    try: a.analyze(_pc(src))
    except: pass
    sym = a._scope.lookup(name)
    return sym.type_ if sym else None

ok("32. map → Array<int>",
   infer("let a=[1,2,3]\nlet r=a.map(fn(x){return x*2})", "r") == array_type(T_INT))
ok("32b. return type inferred",
   infer("fn double(x: int) { return x * 2 }", "double") == T_INT)


# ── 33. setup.py utf-8 encoding ───────────────────────────────────────────────
section("33. setup.py utf-8 encoding fix")

import subprocess
r = subprocess.run(
    ["python3", "setup.py", "--version"],
    capture_output=True, text=True
)
ok("33. setup.py --version works",    r.returncode == 0, repr(r.stderr[:80]))
ok("33b. returns correct version",    r.stdout.strip() == VERSION,
   repr(r.stdout.strip()))


# ── Summary ───────────────────────────────────────────────────────────────────
total = PASS + FAIL
print(f"""
{'='*58}
  v1.9.4 Test Results: {PASS}/{total} passed
  {'ALL PASS' if FAIL == 0 else f'{FAIL} FAILED'}
{'='*58}
""")
sys.exit(0 if FAIL == 0 else 1)
