#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v150.py  InScript v1.5.0 — Standard Library Expansion tests

  * string module additions
  * array module additions
  * math module additions
  * color module additions
  * dict module (new)
  * io module additions

Run:  python3 test_v150.py
"""
import sys, io, os, tempfile
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

def run(code):
    buf = io.StringIO(); sys.stdout = buf
    try:
        Interpreter().execute(code)
        sys.stdout = sys.__stdout__
        return buf.getvalue().strip(), None
    except Exception as e:
        sys.stdout = sys.__stdout__
        return None, str(e).split('\n')[0]

# ── string module ─────────────────────────────────────────────────────────────
section("1. string module")

cases = [
    ("replace_all",  'import "string" as s; print(s.replace_all("aXbXc", "X", "-"))', "a-b-c"),
    ("trim_start",   'import "string" as s; print(s.trim_start("  hi"))',             "hi"),
    ("trim_end",     'import "string" as s; print(s.trim_end("hi  "))',               "hi"),
    ("split_lines",  'import "string" as s; print(s.split_lines("a\\nb\\nc"))', '["a", "b", "c"]'),
    ("find_last",    'import "string" as s; print(s.find_last("abab", "b"))',         "3"),
    ("remove",       'import "string" as s; print("|" ++ s.remove("hello world", "world") ++ "|")', "|hello |"),
    ("truncate",     'import "string" as s; print(s.truncate("hello world", 5))',     "hello..."),
    ("truncate_no",  'import "string" as s; print(s.truncate("hi", 5))',              "hi"),
    ("index_of",     'import "string" as s; print(s.index_of("abcd", "c"))',          "2"),
    ("slice",        'import "string" as s; print(s.slice("hello", 1, 3))',           "el"),
]
for name, code, want in cases:
    out, err = run(code)
    ok(f"string.{name}", out == want and err is None, f"got={out!r}")

# Existing functions still work
for name, code, want in [
    ("split",        'import "string" as s; print(s.split("a,b,c", ","))', '["a", "b", "c"]'),
    ("join",         'import "string" as s; print(s.join("-", ["a","b","c"]))',   "a-b-c"),
    ("upper",        'import "string" as s; print(s.upper("hi"))',               "HI"),
    ("starts_with",  'import "string" as s; print(s.starts_with("hello", "he"))', "true"),
    ("ends_with",    'import "string" as s; print(s.ends_with("hello", "lo"))',   "true"),
]:
    out, err = run(code)
    ok(f"string.{name} (existing)", out == want and err is None, f"got={out!r}")

# ── array module ──────────────────────────────────────────────────────────────
section("2. array module")

cases = [
    ("sort_by",    'import "array" as a; print(a.sort_by([3,1,2], fn(x)=>x))', "[1, 2, 3]"),
    ("sort_by_neg",'import "array" as a; print(a.sort_by([1,3,2], fn(x)=>0-x))', "[3, 2, 1]"),
    ("flat_map",   'import "array" as a; print(a.flat_map([1,2,3], fn(x)=>[x,x*10]))', "[1, 10, 2, 20, 3, 30]"),
    ("unzip",      'import "array" as a; let r=a.unzip([[1,"a"],[2,"b"]]); print(r[0])', "[1, 2]"),
    ("find_index", 'import "array" as a; print(a.find_index([1,2,3,4], fn(x)=>x>2))', "2"),
    ("window",     'import "array" as a; print(a.window([1,2,3,4], 3))', "[[1, 2, 3], [2, 3, 4]]"),
    ("difference", 'import "array" as a; print(a.difference([1,2,3,4], [2,4]))', "[1, 3]"),
    ("intersection",'import "array" as a; print(a.intersection([1,2,3], [2,3,4]))', "[2, 3]"),
    ("union",      'import "array" as a; print(a.union([1,2,3], [2,3,4]))', "[1, 2, 3, 4]"),
    ("compact",    'import "array" as a; print(a.compact([1,nil,2,false,3]))', "[1, 2, 3]"),
    ("sum_by",     'import "array" as a; print(a.sum_by([1,2,3,4], fn(x)=>x*2))', "20"),
    ("max_by",     'import "array" as a; print(a.max_by([3,1,4,1,5], fn(x)=>x))', "5"),
    ("min_by",     'import "array" as a; print(a.min_by([3,1,4,1,5], fn(x)=>x))', "1"),
    ("find_last",  'import "array" as a; print(a.find_last([1,2,3,2,1], fn(x)=>x==2))', "2"),
]
for name, code, want in cases:
    out, err = run(code)
    ok(f"array.{name}", out == want and err is None, f"got={out!r}")

# group_by returns a dict — just check keys exist
out, err = run('import "array" as a; let g=a.group_by([1,2,3,4], fn(x)=>x%2); print(g["0"])')
ok("array.group_by even group", out == "[2, 4]" and err is None, f"got={out!r}")

# Existing functions unbroken
for name, code, want in [
    ("sort",      'import "array" as a; print(a.sort([3,1,2]))',        "[1, 2, 3]"),
    ("zip",       'import "array" as a; print(a.zip([1,2],[3,4]))',     "[[1, 3], [2, 4]]"),
    ("flatten",   'import "array" as a; print(a.flatten([[1,2],[3]]))', "[1, 2, 3]"),
    ("zip_with",  'import "array" as a; print(a.zip_with([1,2],[3,4],fn(a,b)=>a+b))', "[4, 6]"),
]:
    out, err = run(code)
    ok(f"array.{name} (existing)", out == want and err is None, f"got={out!r}")

# ── math module ───────────────────────────────────────────────────────────────
section("3. math module")

cases = [
    ("wrap pos",    'import "math" as m; print(m.wrap(15, 0, 10))',             "5"),
    ("wrap neg",    'import "math" as m; print(m.wrap(-1, 0, 10))',             "9"),
    ("remap",       'import "math" as m; print(m.remap(5.0,0.0,10.0,0.0,100.0))', "50.0"),
    ("ping_pong",   'import "math" as m; print(m.ping_pong(3, 2))',             "1.0"),
    ("fract",       'import "math" as m; let f=m.fract(3.7); print(f > 0.69 && f < 0.71)', "true"),
    ("step 1",      'import "math" as m; print(m.step(0.5, 1.0))',             "1.0"),
    ("step 0",      'import "math" as m; print(m.step(0.5, 0.3))',             "0.0"),
    ("is_approx T", 'import "math" as m; print(m.is_approx(1.0, 1.0000001))', "true"),
    ("is_approx F", 'import "math" as m; print(m.is_approx(1.0, 1.1))',       "false"),
]
for name, code, want in cases:
    out, err = run(code)
    ok(f"math.{name}", out == want and err is None, f"got={out!r}")

# Existing math functions still work
for name, code, want in [
    ("lerp",   'import "math" as m; print(m.lerp(0.0,10.0,0.5))',  "5.0"),
    ("clamp",  'import "math" as m; print(m.clamp(15,0,10))',       "10"),
    ("sign",   'import "math" as m; print(m.sign(-5))',             "-1"),
    ("wrap alias","import \"math\" as m; print(m.map(5.0,0.0,10.0,0.0,100.0))", "50.0"),
]:
    out, err = run(code)
    ok(f"math.{name} (existing)", out == want and err is None, f"got={out!r}")

# ── color module ──────────────────────────────────────────────────────────────
section("4. color module")

out, err = run('import "color" as c; let col=c.from_hsv(0.0, 1.0, 1.0); print(c.to_hex(col))')
ok("color.from_hsv red = #ff0000", out == "#ff0000" and err is None, f"got={out!r}")

out, err = run('import "color" as c; print(c.brightness(c.WHITE))')
ok("color.brightness(WHITE) ~= 1.0", out is not None and abs(float(out) - 1.0) < 0.01, f"got={out!r}")

out, err = run('import "color" as c; print(c.is_dark(c.BLACK))')
ok("color.is_dark(BLACK) = true", out == "true" and err is None, f"got={out!r}")

out, err = run('import "color" as c; print(c.is_light(c.WHITE))')
ok("color.is_light(WHITE) = true", out == "true" and err is None, f"got={out!r}")

out, err = run('import "color" as c; let r=c.to_rgb255(c.RED); print(r[0])')
ok("color.to_rgb255(RED)[0] = 255", out == "255" and err is None, f"got={out!r}")

out, err = run('import "color" as c; print(c.to_rgba_tuple(c.RED))')
ok("color.to_rgba_tuple has 4 elements", out is not None and "1.0" in out and "0.0" in out, f"got={out!r}")

# Existing color functions still work
for name, code, want in [
    ("from_hex", 'import "color" as c; print(c.to_hex(c.from_hex("#ff0000")))', "#ff0000"),
    ("darken",   'import "color" as c; let d=c.darken(c.WHITE,0.5); print(d.r<1.0)',  "true"),
    ("lerp",     'import "color" as c; let m=c.lerp(c.BLACK,c.WHITE,0.5); print(m.r)', "0.5"),
]:
    out, err = run(code)
    ok(f"color.{name} (existing)", out == want and err is None, f"got={out!r}")

# ── dict module ───────────────────────────────────────────────────────────────
section("5. dict module (new)")

out, err = run('import "dict" as d; let m={"a":1,"b":2}; print(d.keys(m))')
ok("dict.keys length", out is not None and "a" in out and "b" in out, f"got={out!r}")

out, err = run('import "dict" as d; let m={"a":1,"b":2}; print(d.values(m))')
ok("dict.values length", out is not None and "1" in out and "2" in out, f"got={out!r}")

out, err = run('import "dict" as d; let m={"a":1,"b":2}; print(d.entries(m))')
ok("dict.entries length", out is not None and "a" in out and "b" in out, f"got={out!r}")

out, err = run('import "dict" as d; let m={"a":1}; print(d.has(m,"a"))')
ok("dict.has true", out == "true" and err is None, f"got={out!r}")

out, err = run('import "dict" as d; let m={"a":1}; print(d.has(m,"z"))')
ok("dict.has false", out == "false" and err is None, f"got={out!r}")

out, err = run('import "dict" as d; let m={"a":1}; print(d.get(m,"a",0))')
ok("dict.get existing key", out == "1" and err is None, f"got={out!r}")

out, err = run('import "dict" as d; let m={"a":1}; print(d.get(m,"z",99))')
ok("dict.get missing key with default", out == "99" and err is None, f"got={out!r}")

out, err = run('import "dict" as d; let m={"a":1}; d.set(m,"b",2); print(d.size(m))')
ok("dict.set and size", out == "2" and err is None, f"got={out!r}")

out, err = run('''
import "dict" as d
let m1 = {"a": 1, "b": 2}
let m2 = {"b": 3, "c": 4}
let merged = d.merge(m1, m2)
print(d.get(merged, "a", 0))
print(d.get(merged, "b", 0))
print(d.get(merged, "c", 0))
''')
ok("dict.merge", out == "1\n3\n4" and err is None, f"got={out!r}")

out, err = run('import "dict" as d; let m={"a":1,"b":2,"c":3}; let p=d.pick(m,"a","c"); print(d.size(p))')
ok("dict.pick", out == "2" and err is None, f"got={out!r}")

out, err = run('import "dict" as d; let m={"a":1,"b":2}; print(d.is_empty(m))')
ok("dict.is_empty false", out == "false" and err is None, f"got={out!r}")

out, err = run('import "dict" as d; print(d.from_entries([["x",1],["y",2]])["x"])')
ok("dict.from_entries", out == "1" and err is None, f"got={out!r}")

out, err = run('import "dict" as d; let m={"a":1,"b":2}; let mv=d.map_values(m, fn(v)=>v*10); print(d.get(mv,"a",0))')
ok("dict.map_values", out == "10" and err is None, f"got={out!r}")

# ── io module additions ───────────────────────────────────────────────────────
section("6. io module additions")

import tempfile as _tf, os as _os

# Use forward slashes — Windows accepts them and InScript strings don't escape them
_tmp = _tf.mkdtemp().replace("\\", "/")

out, err = run(f'''
import "io" as io
let dir = "{_tmp}"
let file = io.join_path(dir, "test.txt")
io.write_file(file, "hello")
print(io.file_size(file))
print(io.extension(file))
print(io.stem(file))
print(io.is_file(file))
print(io.is_dir(dir))
''')
ok("io.file_size, extension, stem, is_file, is_dir", out == "5\n.txt\ntest\ntrue\ntrue", f"got={out!r}")

_subdir = (_os.path.join(_tmp, "subdir")).replace("\\", "/")
out, err = run(f'''
import "io" as io
io.make_dir("{_subdir}")
print(io.is_dir("{_subdir}"))
''')
ok("io.make_dir", out == "true" and err is None, f"got={out!r}")

out, err = run(f'import "io" as io; let p = io.abs_path("{_tmp}"); print(len(p) > 0)')
ok("io.abs_path returns non-empty string", out == "true" and err is None, f"got={out!r}")

# io.read_lines — write temp file via Python then read via InScript
_fd, _tmpfile = _tf.mkstemp(suffix=".txt")
_os.write(_fd, b"line1\nline2\nline3"); _os.close(_fd)
_tmpfile_fwd = _tmpfile.replace("\\", "/")
out, err = run(f'import "io" as io; let lines=io.read_lines("{_tmpfile_fwd}"); print(len(lines))')
ok("io.read_lines (existing)", out == "3" and err is None, f"got={out!r}")
_os.unlink(_tmpfile)

# ── summary ───────────────────────────────────────────────────────────────────
total = PASS + FAIL
print(f"""
{'='*56}
  v1.5.0 Test Results: {PASS}/{total} passed
  {'ALL PASS' if FAIL == 0 else f'{FAIL} FAILED'}
{'='*56}
""")
sys.exit(0 if FAIL == 0 else 1)
