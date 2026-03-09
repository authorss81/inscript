#!/usr/bin/env python3
"""v1.2 feature tests — stdlib modules, select statement, LSP, package manager."""
import sys, os, io, contextlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from interpreter import Interpreter

PASS = FAIL = 0
RESULTS = []

def run(code: str) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Interpreter().execute(code)
    return buf.getvalue().strip()

def test(name: str, code: str, expected: str):
    global PASS, FAIL
    try:
        got = run(code)
        ok  = got.strip() == str(expected).strip()
        RESULTS.append(('PASS' if ok else 'FAIL', name, got, str(expected)))
        if ok: PASS += 1
        else:  FAIL += 1
    except Exception as e:
        RESULTS.append(('ERROR', name, str(e)[:100], str(expected)))
        FAIL += 1

def test_raises(name: str, code: str):
    global PASS, FAIL
    try:
        run(code)
        RESULTS.append(('FAIL', name, 'no error raised', 'exception'))
        FAIL += 1
    except Exception:
        RESULTS.append(('PASS', name, 'raised', 'exception'))
        PASS += 1

# ── path module ─────────────────────────────────────────────────────────────
test('path.join',
     'import "path" as path\nprint(path.join("/tmp", "a", "b.ins"))',
     '/tmp/a/b.ins')
test('path.basename',
     'import "path" as path\nprint(path.basename("/tmp/foo/bar.ins"))',
     'bar.ins')
test('path.stem',
     'import "path" as path\nprint(path.stem("/tmp/foo/bar.ins"))',
     'bar')
test('path.ext',
     'import "path" as path\nprint(path.ext("/tmp/foo/bar.ins"))',
     '.ins')
test('path.dirname',
     'import "path" as path\nprint(path.dirname("/tmp/foo/bar.ins"))',
     '/tmp/foo')
test('path.exists false',
     'import "path" as path\nprint(path.exists("/this/does/not/exist"))',
     'false')
test('path.is_file false',
     'import "path" as path\nprint(path.is_file("/this/does/not/exist"))',
     'false')
test('path.abs non-empty',
     'import "path" as path\nlet p = path.abs(".")\nprint(len(p) > 0)',
     'true')

# ── regex module ─────────────────────────────────────────────────────────────
test('regex.test true',
     'import "regex" as regex\nprint(regex.test("\\\\d+", "hello123world"))',
     'true')
test('regex.test false',
     'import "regex" as regex\nprint(regex.test("^\\\\d+$", "hello"))',
     'false')
test('regex.find_all digits',
     'import "regex" as regex\nlet m = regex.find_all("\\\\d+", "a1 b22 c333")\nprint(len(m))',
     '3')
test('regex.sub replace',
     'import "regex" as regex\nprint(regex.sub("o+", "0", "foobar"))',
     'f0bar')
test('regex.match success',
     'import "regex" as regex\nlet m = regex.match("(\\\\w+)", "hello")\nprint(m["matched"])',
     'true')
test('regex.search value',
     'import "regex" as regex\nlet m = regex.search("\\\\d+", "abc123def")\nprint(m["value"])',
     '123')
test('regex.split',
     'import "regex" as regex\nlet parts = regex.split(",\\\\s*", "a, b,c, d")\nprint(len(parts))',
     '4')
test('regex.escape',
     'import "regex" as regex\nlet e = regex.escape("a.b+c")\nprint(regex.test("^"+e+"$", "a.b+c"))',
     'true')

# ── csv module ────────────────────────────────────────────────────────────────
test('csv.parse basic',
     'import "csv" as csv\nlet r = csv.parse("name,age\\nAlice,30\\nBob,25")\nprint(len(r["data"]))',
     '2')
test('csv.parse headers',
     'import "csv" as csv\nlet r = csv.parse("x,y\\n1,2")\nprint(r["headers"][0])',
     'x')
test('csv.parse field access',
     'import "csv" as csv\nlet r = csv.parse("name,age\\nAlice,30")\nprint(r["data"][0]["name"])',
     'Alice')
test('csv.to_string roundtrip',
     'import "csv" as csv\nlet orig = "a,b\\n1,2\\n3,4"\nlet parsed = csv.parse(orig)\nlet out = csv.to_string(parsed["rows"], parsed["headers"])\nlet re_parsed = csv.parse(out)\nprint(len(re_parsed["data"]))',
     '2')
test('csv.parse no header',
     'import "csv" as csv\nlet r = csv.parse("1,2\\n3,4", ",", false)\nprint(len(r["rows"]))',
     '2')
test('csv.from_dicts',
     'import "csv" as csv\nlet data = [{"x": "1", "y": "2"}, {"x": "3", "y": "4"}]\nlet s = csv.from_dicts(data)\nlet p = csv.parse(s)\nprint(p["data"][1]["x"])',
     '3')

# ── uuid module ───────────────────────────────────────────────────────────────
test('uuid.v4 length',
     'import "uuid" as uuid\nlet u = uuid.v4()\nprint(len(u))',
     '36')
test('uuid.v4 format',
     'import "uuid" as uuid\nlet u = uuid.v4()\nlet parts = split(u, "-")\nprint(len(parts))',
     '5')
test('uuid.v4 unique',
     'import "uuid" as uuid\nlet a = uuid.v4()\nlet b = uuid.v4()\nprint(a != b)',
     'true')
test('uuid.short length',
     'import "uuid" as uuid\nlet s = uuid.short()\nprint(len(s))',
     '8')
test('uuid.nil value',
     'import "uuid" as uuid\nprint(uuid.nil)',
     '00000000-0000-0000-0000-000000000000')

# ── crypto module ─────────────────────────────────────────────────────────────
test('crypto.sha256 length',
     'import "crypto" as crypto\nlet h = crypto.sha256("hello")\nprint(len(h))',
     '64')
test('crypto.sha256 deterministic',
     'import "crypto" as crypto\nprint(crypto.sha256("hello") == crypto.sha256("hello"))',
     'true')
test('crypto.sha256 different',
     'import "crypto" as crypto\nprint(crypto.sha256("a") != crypto.sha256("b"))',
     'true')
test('crypto.md5 length',
     'import "crypto" as crypto\nprint(len(crypto.md5("test")))',
     '32')
test('crypto.b64 roundtrip',
     'import "crypto" as crypto\nlet encoded = crypto.b64_encode("hello world")\nlet decoded = crypto.b64_decode(encoded)\nprint(decoded)',
     'hello world')
test('crypto.hmac sign+verify',
     'import "crypto" as crypto\nlet sig = crypto.hmac_sign("secret", "message")\nprint(crypto.hmac_verify("secret", "message", sig))',
     'true')
test('crypto.hmac wrong key',
     'import "crypto" as crypto\nlet sig = crypto.hmac_sign("secret", "message")\nprint(crypto.hmac_verify("wrong", "message", sig))',
     'false')
test('crypto.constant_time_eq match',
     'import "crypto" as crypto\nprint(crypto.constant_time_eq("abc", "abc"))',
     'true')
test('crypto.constant_time_eq mismatch',
     'import "crypto" as crypto\nprint(crypto.constant_time_eq("abc", "xyz"))',
     'false')

# ── select statement (basic) ─────────────────────────────────────────────────
test('select timeout fires',
     'let done = false\nselect {\n  case timeout(0.01) { done = true }\n}\nprint(done)',
     'true')
test('select recv from full channel',
     'let ch = make_channel()\nchan_send(ch, 42)\nlet got = 0\nselect {\n  case got = ch.recv() { }\n  case timeout(0.1) { }\n}\nprint(got)',
     '42')

# ── v1.1 features still working ───────────────────────────────────────────────
test('v1.1 str index',  'print("hello"[0])',  'h')
test('v1.1 floor div',  'print(7 div 2)',      '3')
test('v1.1 fstring {{', 'print(f"{{lit}}")',   '{lit}')
test('v1.1 enum iter',
     'enum D{A B C}\nlet c=0\nfor v in D{c+=1}\nprint(c)', '3')
test('v1.1 spread',     'print([1,...[2,3],4])','[1, 2, 3, 4]')
test('v1.1 multi-catch','try{throw "e"}catch x{print(x)}', 'e')
test('v1.1 decorator',
     'fn id(f){return f}\n@id\nfn hi(){return "ok"}\nprint(hi())', 'ok')
test('v1.1 abstract',
     'struct S{abstract fn f()}\nstruct C extends S{fn f(){print("ok")}}\nC{}.f()', 'ok')

# ── LSP diagnostics (no pygls needed) ────────────────────────────────────────
def test_lsp(name, source, expect_errors, expect_clean=False):
    global PASS, FAIL
    try:
        from lsp.diagnostics import get_diagnostics
        diags = get_diagnostics(source)
        has_errors = len(diags) > 0
        ok = (has_errors == expect_errors)
        RESULTS.append(('PASS' if ok else 'FAIL', name, f'{len(diags)} diags', f'errors={expect_errors}'))
        if ok: PASS += 1
        else:  FAIL += 1
    except Exception as e:
        RESULTS.append(('ERROR', name, str(e)[:80], 'n/a'))
        FAIL += 1

test_lsp('LSP clean code', 'let x = 42\nprint(x)', expect_errors=False)
test_lsp('LSP parse error', 'let x = ', expect_errors=True)
test_lsp('LSP valid struct', 'struct Point { x: int  y: int }\nlet p = Point{x:1, y:2}\nprint(p.x)', expect_errors=False)

# ── completions ───────────────────────────────────────────────────────────────
def test_completions(name, source, line, col, expect_label):
    global PASS, FAIL
    try:
        from lsp.completions import get_completions
        items = get_completions(source, line, col)
        labels = [i['label'] for i in items]
        ok = expect_label in labels
        RESULTS.append(('PASS' if ok else 'FAIL', name, str(labels[:5]), f'contains {expect_label}'))
        if ok: PASS += 1
        else:  FAIL += 1
    except Exception as e:
        RESULTS.append(('ERROR', name, str(e)[:80], 'n/a'))
        FAIL += 1

test_completions('LSP complete print', 'pr', 0, 2, 'print')
test_completions('LSP complete let',   'le', 0, 2, 'let')
test_completions('LSP complete fn',    'fn', 0, 2, 'fn')

# ── hover docs ────────────────────────────────────────────────────────────────
def test_hover(name, source, line, col, expect_word):
    global PASS, FAIL
    try:
        from lsp.hover import get_hover
        info = get_hover(source, line, col)
        ok = info is not None and info.get('word') == expect_word
        RESULTS.append(('PASS' if ok else 'FAIL', name, str(info), f'word={expect_word}'))
        if ok: PASS += 1
        else:  FAIL += 1
    except Exception as e:
        RESULTS.append(('ERROR', name, str(e)[:80], 'n/a'))
        FAIL += 1

test_hover('LSP hover print', 'print("hi")', 0, 2, 'print')
test_hover('LSP hover len',   'len(arr)',    0, 1, 'len')
test_hover('LSP hover map',   'map(a, f)',   0, 1, 'map')

# ── Print results ─────────────────────────────────────────────────────────────
CATS = {
    'path module':     [r for r in RESULTS if r[1].startswith('path.')],
    'regex module':    [r for r in RESULTS if r[1].startswith('regex.')],
    'csv module':      [r for r in RESULTS if r[1].startswith('csv.')],
    'uuid module':     [r for r in RESULTS if r[1].startswith('uuid.')],
    'crypto module':   [r for r in RESULTS if r[1].startswith('crypto.')],
    'select stmt':     [r for r in RESULTS if r[1].startswith('select')],
    'v1.1 regression': [r for r in RESULTS if r[1].startswith('v1.1')],
    'LSP server':      [r for r in RESULTS if r[1].startswith('LSP')],
}

print('\n' + '═'*62)
print('  InScript v1.2 — Feature Test Suite')
print('═'*62)
total_p = total_f = 0
for cat, rows in CATS.items():
    p = sum(1 for r in rows if r[0] == 'PASS')
    f = len(rows) - p
    total_p += p; total_f += f
    icon = '✅' if f == 0 else '❌'
    print(f'  {icon} {cat:<22}  {p}/{len(rows)}')
    for r in rows:
        if r[0] != 'PASS':
            print(f'       ✗ {r[1]}')
            print(f'         got: {repr(r[2][:70])}')
            print(f'         exp: {repr(r[3][:50])}')

print('═'*62)
print(f'  TOTAL: {total_p}/{total_p+total_f} passing')
print('═'*62)
sys.exit(0 if total_f == 0 else 1)
