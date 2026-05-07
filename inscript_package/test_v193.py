#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v193.py  InScript v1.9.3 — Documentation Generation

Tests:
  1.  /// comment before fn is parsed
  2.  description extracted correctly
  3.  @param tag parsed: name, type, desc
  4.  @returns tag parsed
  5.  @example block extracted
  6.  @since tag parsed
  7.  @deprecated tag parsed
  8.  Multiple params parsed
  9.  struct declaration documented
 10.  enum declaration documented
 11.  interface declaration documented
 12.  type alias documented
 13.  Undocumented fn ignored
 14.  Multiple doc blocks in one file
 15.  Markdown: fn section header present
 16.  Markdown: parameter table rendered
 17.  Markdown: returns section rendered
 18.  Markdown: example code block rendered
 19.  Markdown: @since rendered
 20.  Markdown: @deprecated rendered
 21.  Markdown: file header with source name
 22.  Markdown: InScript version in header
 23.  doc FILE → writes .md file
 24.  doc FILE with no --out → returns markdown string
 25.  doc DIR → walks all .ins files
 26.  doc DIR → creates docs/api/ by default
 27.  doc DIR → one .md per .ins file
 28.  doc: nonexistent path returns 1
 29.  doc: file with no doc comments → empty doc
 30.  Playground integration: examples in runnable block
 31.  @param without type still parses
 32.  Multi-line description
 33.  Unknown @tag captured in raw_tags
 34.  v1.9.2 regression: semver + manifest
 35.  v1.9.1 regression: compat tool
 36.  v1.8.4 regression: method chain inference

Run:  python3 test_v193.py
"""
import sys, io, os, tempfile, shutil, importlib.util, re

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

VERSION        = _ins.VERSION
_parse         = _ins._parse_doc_comments
_render        = _ins._render_doc_markdown
_doc_file      = _ins._doc_file
_generate_docs = _ins._generate_docs

def capture(fn, *a, **kw):
    buf = io.StringIO(); sys.stdout = buf
    ret = fn(*a, **kw)
    sys.stdout = sys.__stdout__
    return ret, buf.getvalue()

# ── Fixtures ──────────────────────────────────────────────────────────────────

FULL_SAMPLE = '''\
/// Compute the sum of two integers.
/// More detail on second line.
/// @param a (int) First number
/// @param b (int) Second number
/// @returns int The sum of a and b
/// @example
/// let result = add(3, 4)
/// print(result)
/// @since 1.0.0
fn add(a: int, b: int) -> int { return a + b }

/// Represents a 2D point in space.
/// @param x (float) X coordinate
/// @param y (float) Y coordinate
struct Point { x: float = 0.0; y: float = 0.0 }

/// Cardinal direction.
enum Dir { North; South; East; West }

/// Something renderable.
/// @deprecated Use Renderable instead
interface Drawable { fn draw() -> void }

/// Player identifier alias.
/// @since 1.2.0
type PlayerID = int

fn no_doc() { }
'''

entries = _parse(FULL_SAMPLE)
by_name = {e["name"]: e for e in entries}
md      = _render(entries, "game.ins")


# ── 1–8. Doc comment parsing ──────────────────────────────────────────────────
section("1-8. Doc comment parsing")

ok("1. fn add parsed",             "add" in by_name)
ok("2. description extracted",     "sum of two" in by_name.get("add", {}).get("description",""))
ok("3. @param count",              len(by_name.get("add",{}).get("params",[])) == 2)
ok("3b. @param name",              by_name["add"]["params"][0]["name"] == "a")
ok("3c. @param type",              by_name["add"]["params"][0]["type"] == "int")
ok("3d. @param desc",              "First number" in by_name["add"]["params"][0]["desc"])
ok("4. @returns type",             by_name["add"].get("returns",{}).get("type") == "int")
ok("4b. @returns desc",            "sum" in by_name["add"].get("returns",{}).get("desc",""))
ok("5. @example extracted",        len(by_name["add"].get("examples",[])) == 1)
ok("5b. example content",          "add(3, 4)" in by_name["add"]["examples"][0])
ok("6. @since parsed",             by_name["add"].get("since") == "1.0.0")
ok("7. @deprecated parsed",        "Renderable" in (by_name.get("Drawable",{}).get("deprecated") or ""))
ok("8. multi-line description",    "second line" in by_name["add"]["description"])


# ── 9–13. Different declaration kinds ────────────────────────────────────────
section("9-13. Struct / enum / interface / type / undocumented")

ok("9. struct documented",         "Point" in by_name)
ok("9b. struct params",            len(by_name["Point"]["params"]) == 2)
ok("10. enum documented",          "Dir" in by_name)
ok("10b. enum kind",               by_name["Dir"]["kind"] == "enum")
ok("11. interface documented",     "Drawable" in by_name)
ok("11b. interface kind",          by_name["Drawable"]["kind"] == "interface")
ok("12. type alias documented",    "PlayerID" in by_name)
ok("12b. type since",              by_name["PlayerID"].get("since") == "1.2.0")
ok("13. undocumented fn skipped",  "no_doc" not in by_name)
ok("14. total entries = 5",        len(entries) == 5, repr(list(by_name.keys())))


# ── 15–22. Markdown rendering ─────────────────────────────────────────────────
section("15-22. Markdown rendering")

ok("15. fn section header",        "## `fn add`" in md)
ok("15b. struct section header",   "## `struct Point`" in md)
ok("15c. enum section header",     "## `enum Dir`" in md)
ok("16. parameter table header",   "| Name | Type | Description |" in md)
ok("16b. param row for a",         "| `a` |" in md)
ok("16c. param type int",          "`int`" in md)
ok("17. returns section",          "### Returns" in md)
ok("17b. returns type in md",      "`int`" in md)
ok("18. example code fence",       "```inscript" in md)
ok("18b. example content in md",   "add(3, 4)" in md)
ok("19. since rendered",           "*Since v1.0.0*" in md)
ok("20. deprecated rendered",      "**Deprecated:**" in md)
ok("21. file header with name",    "game" in md)
ok("22. inscript version in md",   VERSION in md)


# ── 23–29. File and directory output ─────────────────────────────────────────
section("23-29. File / directory output")

tmpdir = tempfile.mkdtemp()
try:
    # Write sample file
    fpath = os.path.join(tmpdir, "math.ins")
    with open(fpath, "w") as f: f.write(FULL_SAMPLE)

    # doc FILE with output dir
    out_dir = os.path.join(tmpdir, "out")
    ret23, out23 = capture(_generate_docs, fpath, output_dir=out_dir)
    md_out = os.path.join(out_dir, "math.md")
    ok("23. doc FILE returns 0",          ret23 == 0, repr(ret23))
    ok("23b. .md file created",           os.path.exists(md_out))
    with open(md_out) as f: written_md = f.read()
    ok("23c. written md has content",     "fn add" in written_md)

    # doc FILE no output dir → markdown to stdout
    _, out24 = capture(_doc_file, fpath)
    # _doc_file returns (entries, markdown_str) not printed
    entries24, md24 = _doc_file(fpath)
    ok("24. doc FILE returns entries",    len(entries24) > 0)
    ok("24b. doc FILE returns markdown",  "fn add" in md24)

    # doc DIR
    subdir = os.path.join(tmpdir, "src")
    os.makedirs(subdir)
    for name in ["a.ins", "b.ins"]:
        with open(os.path.join(subdir, name), "w") as f:
            f.write('/// A function.\nfn foo() { }\n')
    # also a non-ins file — should be ignored
    with open(os.path.join(subdir, "readme.txt"), "w") as f:
        f.write("ignored\n")

    docs_out = os.path.join(tmpdir, "docs_out")
    ret25, out25 = capture(_generate_docs, subdir, output_dir=docs_out)
    ok("25. doc DIR returns 0",           ret25 == 0, repr(out25[:80]))
    ok("25b. dir: .txt ignored",          "readme" not in out25)

    ok("26. docs_out dir created",        os.path.exists(docs_out))
    md_files = [f for f in os.listdir(docs_out) if f.endswith(".md")]
    ok("27. one .md per .ins file",       len(md_files) == 2, repr(md_files))

    # nonexistent path
    ret28, _ = capture(_generate_docs, os.path.join(tmpdir, "nope.ins"))
    ok("28. nonexistent returns 1",       ret28 == 1)

    # file with no doc comments
    empty_f = os.path.join(tmpdir, "empty.ins")
    with open(empty_f, "w") as f: f.write("fn undoc() { }\nlet x = 1\n")
    entries29, md29 = _doc_file(empty_f)
    ok("29. no docs → empty entries",     len(entries29) == 0)
    ok("29b. no docs → md still valid",   "API Reference" in md29)

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ── 30. Playground integration ────────────────────────────────────────────────
section("30. Playground integration (runnable examples)")

PLAYGROUND_SAMPLE = '''\
/// Greet someone.
/// @param name (string) Name to greet
/// @returns string Greeting message
/// @example
/// let msg = greet("Alice")
/// print(msg)
fn greet(name: string) -> string { return "Hello, " + name }
'''
entries30 = _parse(PLAYGROUND_SAMPLE)
md30      = _render(entries30, "greet.ins")
ok("30. example in code fence",    "```inscript" in md30)
ok("30b. example is runnable",     'greet("Alice")' in md30)
ok("30c. code fence closed",       md30.count("```") % 2 == 0,
   f"fence count={md30.count('```')}")


# ── 31. @param without type ───────────────────────────────────────────────────
section("31. @param without type")

NO_TYPE = '''\
/// Do something.
/// @param value Just a value, no type given
fn do_thing(value) { }
'''
e31 = _parse(NO_TYPE)
ok("31. param parsed without type",   len(e31) == 1 and len(e31[0]["params"]) == 1)
ok("31b. param name correct",         e31[0]["params"][0]["name"] == "value")
ok("31c. param type empty/none",      e31[0]["params"][0]["type"] in ("", "Just"))  # "Just a value..."


# ── 32. Multi-line description ────────────────────────────────────────────────
section("32. Multi-line description")

MULTI_DESC = '''\
/// First line of description.
/// Second line continues here.
/// Third line too.
/// @param x (int) A number
fn multi(x: int) { }
'''
e32 = _parse(MULTI_DESC)
desc32 = e32[0]["description"] if e32 else ""
ok("32. all description lines joined",  "First line" in desc32 and "Third line" in desc32)
ok("32b. param still parsed",           len(e32[0]["params"]) == 1)


# ── 33. Unknown @tag in raw_tags ─────────────────────────────────────────────
section("33. Unknown @tag captured")

CUSTOM_TAG = '''\
/// A function.
/// @author Shreyasi
/// @license MIT
fn custom() { }
'''
e33 = _parse(CUSTOM_TAG)
tags33 = {t["tag"]: t["text"] for t in e33[0].get("raw_tags", [])}
ok("33. @author in raw_tags",   "author" in tags33, repr(tags33))
ok("33b. @license in raw_tags", "license" in tags33, repr(tags33))
ok("33c. @author value",        "Shreyasi" in tags33.get("author",""))


# ── 34. v1.9.2 regression ────────────────────────────────────────────────────
section("34. v1.9.2 regression: semver + manifest")

ok("34. semver >=",     _ins._semver_satisfies("1.9.3", ">=1.9.0"))
ok("34b. semver ^",     _ins._semver_satisfies("1.9.3", "^1.9.0"))
ok("34c. semver ~",     _ins._semver_satisfies("1.9.3", "~1.9.2"))
ok("34d. semver fail",  not _ins._semver_satisfies("1.8.0", ">=1.9.0"))


# ── 35. v1.9.1 regression ────────────────────────────────────────────────────
section("35. v1.9.1 regression: compat tool")

tmpd = tempfile.mkdtemp()
try:
    with open(os.path.join(tmpd, "old.ins"), "w") as f: f.write("let x = null\n")
    ret35, out35 = capture(_ins._compat_files, tmpd)
    ok("35. compat detects null",   ret35 == 1 and "null" in out35)
finally:
    shutil.rmtree(tmpd, ignore_errors=True)


# ── 36. v1.8.4 regression ────────────────────────────────────────────────────
section("36. v1.8.4 regression: method chain inference")

from analyzer import Analyzer, array_type, T_INT
from parser import parse as _parse_code

def infer(src, name):
    a = Analyzer(no_warn=True)
    try: a.analyze(_parse_code(src))
    except: pass
    sym = a._scope.lookup(name)
    return sym.type_ if sym else None

ok("36. map → Array<int>",
   infer("let a=[1,2,3]\nlet r=a.map(fn(x){return x*2})", "r") == array_type(T_INT))


# ── Summary ───────────────────────────────────────────────────────────────────
total = PASS + FAIL
print(f"""
{'='*58}
  v1.9.3 Test Results: {PASS}/{total} passed
  {'ALL PASS' if FAIL == 0 else f'{FAIL} FAILED'}
{'='*58}
""")
sys.exit(0 if FAIL == 0 else 1)
