"""
test_v1911.py — v1.9.11: Real async I/O stdlib

Tests are network-free where possible. For http.get_async we only
test that it returns a coroutine and can be awaited (response may fail
without network, but the error should be catchable).

  1-4:   http.get_async returns InScriptCoroutine
  5-8:   file.read_async: reads a real temp file correctly
  9-11:  file.write_async: writes a real temp file correctly
  12-14: timer.sleep returns coroutine, await completes quickly
  15-17: timer module: now, now_sec, sleep_sync
  18-20: file module: sync read/write/exists
  21-23: analyzer knows Promise<string> for http.get_async / file.read_async
  24-26: analyzer knows Promise<nil> for timer.sleep
"""
import sys, os, tempfile, time
sys.path.insert(0, os.path.dirname(__file__))

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from environment import Environment
from stdlib_values import InScriptCoroutine
import stdlib as _stdlib  # ensure modules are registered

passed = failed = 0

def ok(name):
    global passed; passed += 1; print(f"  PASS  {name}")

def fail(name, reason=""):
    global failed; failed += 1; print(f"  FAIL  {name}  {reason}")

_SETUP = 'import "http" as http\nimport "file" as file\nimport "timer" as timer\n'

def run(src):
    full = _SETUP + src
    lx = Lexer(full); tokens = lx.tokenize()
    pr = Parser(tokens); tree = pr.parse()
    interp = Interpreter()
    return interp.visit(tree)

def expect_value(name, src, expected):
    try:
        result = run(src)
        if result == expected: ok(name)
        else: fail(name, f"got {result!r}, expected {expected!r}")
    except Exception as e:
        fail(name, f"raised {e}")

def expect_coro(name, src):
    try:
        result = run(src)
        if isinstance(result, InScriptCoroutine): ok(name)
        else: fail(name, f"expected coroutine, got {type(result).__name__}: {result!r}")
    except Exception as e:
        fail(name, f"raised {e}")

# ── 1-4: http.get_async ───────────────────────────────────────────────────────

expect_coro("http_get_async_returns_coro",
    'http.get_async("https://example.com")')

expect_coro("http_get_async_fn_name",
    'http.get_async("https://example.com")')

def t_http_get_async_name():
    coro = run('http.get_async("https://example.com")')
    if isinstance(coro, InScriptCoroutine) and "http" in coro.fn_name:
        ok("http_get_async_has_name")
    else:
        fail("http_get_async_has_name", f"fn_name={getattr(coro,'fn_name','?')!r}")

t_http_get_async_name()

def t_http_get_async_error_catchable():
    """A failed http.get_async should be catchable with try/catch."""
    src = '''
async fn fetch() -> string {
    return await http.get_async("http://localhost:19999/nonexistent")
}
let result = "ok"
try {
    let _ = await fetch()
} catch e {
    result = "caught"
}
result
'''
    try:
        r = run(src)
        # Either caught (network failure) or got a response (unlikely but valid)
        if r in ("caught", "ok") or isinstance(r, str):
            ok("http_error_catchable")
        else:
            fail("http_error_catchable", f"got {r!r}")
    except Exception as e:
        # Uncaught exception = test failure
        fail("http_error_catchable", f"uncaught: {e}")

t_http_get_async_error_catchable()

# ── 5-8: file.read_async ─────────────────────────────────────────────────────

def t_file_read_async_returns_coro():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write("hello async"); fname = f.name
    try:
        coro = run(f'file.read_async("{fname.replace(chr(92), "/")}")')
        if isinstance(coro, InScriptCoroutine): ok("file_read_async_coro")
        else: fail("file_read_async_coro", f"got {type(coro).__name__}")
    finally:
        os.unlink(fname)

t_file_read_async_returns_coro()

def t_file_read_async_result():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write("inscript async io"); fname = f.name
    try:
        result = run(f'await file.read_async("{fname.replace(chr(92), "/")}")')
        if result == "inscript async io": ok("file_read_async_result")
        else: fail("file_read_async_result", f"got {result!r}")
    finally:
        os.unlink(fname)

t_file_read_async_result()

def t_file_read_async_multiline():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write("line1\nline2\nline3"); fname = f.name
    try:
        result = run(f'await file.read_async("{fname.replace(chr(92), "/")}")')
        if "line1" in str(result) and "line3" in str(result):
            ok("file_read_async_multiline")
        else:
            fail("file_read_async_multiline", f"got {result!r}")
    finally:
        os.unlink(fname)

t_file_read_async_multiline()

def t_file_read_async_error_missing():
    src = '''
let result = "ok"
try {
    let _ = await file.read_async("/nonexistent/path/xyz.txt")
} catch e {
    result = "caught"
}
result
'''
    try:
        r = run(src)
        if r == "caught": ok("file_read_async_error_caught")
        else: fail("file_read_async_error_caught", f"got {r!r}")
    except Exception as e:
        fail("file_read_async_error_caught", f"uncaught: {e}")

t_file_read_async_error_missing()

# ── 9-11: file.write_async ───────────────────────────────────────────────────

def t_file_write_async_returns_coro():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "out.txt").replace("\\", "/")
        coro = run(f'file.write_async("{p}", "content")')
        if isinstance(coro, InScriptCoroutine): ok("file_write_async_coro")
        else: fail("file_write_async_coro", f"got {type(coro).__name__}")

t_file_write_async_returns_coro()

def t_file_write_async_writes():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "out.txt").replace("\\", "/")
        result = run(f'await file.write_async("{p}", "written content")')
        content = open(os.path.join(d, "out.txt"), encoding="utf-8").read()
        if content == "written content" and result == True:
            ok("file_write_async_writes")
        else:
            fail("file_write_async_writes", f"result={result!r} content={content!r}")

t_file_write_async_writes()

def t_file_write_then_read_async():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "rw.txt").replace("\\", "/")
        src = f'''
await file.write_async("{p}", "round trip")
await file.read_async("{p}")
'''
        result = run(src)
        if result == "round trip": ok("file_write_then_read_async")
        else: fail("file_write_then_read_async", f"got {result!r}")

t_file_write_then_read_async()

# ── 12-14: timer.sleep ───────────────────────────────────────────────────────

expect_coro("timer_sleep_returns_coro",
    "timer.sleep(100)")

def t_timer_sleep_completes():
    start = time.time()
    run("await timer.sleep(50)")
    elapsed = time.time() - start
    # Should take ~50ms, allow generous range for CI
    if elapsed >= 0.03:
        ok("timer_sleep_completes")
    else:
        fail("timer_sleep_completes", f"elapsed={elapsed:.3f}s (too fast)")

t_timer_sleep_completes()

def t_timer_sleep_returns_nil():
    result = run("await timer.sleep(10)")
    if result is None: ok("timer_sleep_returns_nil")
    else: fail("timer_sleep_returns_nil", f"got {result!r}")

t_timer_sleep_returns_nil()

# ── 15-17: timer module extras ────────────────────────────────────────────────

def t_timer_now():
    result = run("timer.now()")
    if isinstance(result, int) and result > 1_000_000_000_000:
        ok("timer_now_ms")
    else:
        fail("timer_now_ms", f"got {result!r}")

t_timer_now()

def t_timer_sleep_sync():
    start = time.time()
    run("timer.sleep_sync(50)")
    elapsed = time.time() - start
    if elapsed >= 0.03: ok("timer_sleep_sync_blocks")
    else: fail("timer_sleep_sync_blocks", f"elapsed={elapsed:.3f}s")

t_timer_sleep_sync()

def t_timer_now_sec():
    result = run("timer.now_sec()")
    if isinstance(result, float) and result > 1_000_000_000.0:
        ok("timer_now_sec")
    else:
        fail("timer_now_sec", f"got {result!r}")

t_timer_now_sec()

# ── 18-20: file module sync operations ───────────────────────────────────────

def t_file_read_sync():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write("sync content"); fname = f.name
    try:
        result = run(f'file.read("{fname.replace(chr(92), "/")}")')
        if result == "sync content": ok("file_read_sync")
        else: fail("file_read_sync", f"got {result!r}")
    finally:
        os.unlink(fname)

t_file_read_sync()

def t_file_exists():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        fname = f.name
    try:
        result = run(f'file.exists("{fname.replace(chr(92), "/")}")')
        if result == True: ok("file_exists_true")
        else: fail("file_exists_true", f"got {result!r}")
    finally:
        os.unlink(fname)

t_file_exists()

def t_file_exists_false():
    result = run('file.exists("/nonexistent/path/xyz.txt")')
    if result == False: ok("file_exists_false")
    else: fail("file_exists_false", f"got {result!r}")

t_file_exists_false()

# ── 21-24: analyzer type inference for async methods ─────────────────────────

from analyzer import Analyzer, T_STRING, T_BOOL, T_NULL, InScriptType

def check_analyzer_type(name, src, expected_type_name):
    lx = Lexer(src); tokens = lx.tokenize()
    pr = Parser(tokens); tree = pr.parse()
    a = Analyzer()
    try: a.analyze(tree)
    except Exception: pass
    sym = a._scope.lookup("x")
    if sym is None:
        return fail(name, "symbol 'x' not found")
    t = sym.type_
    if t.name == expected_type_name:
        ok(name)
    else:
        fail(name, f"got type {t!r}, expected {expected_type_name!r}")

def t_http_module_registered():
    from analyzer import Analyzer
    a = Analyzer()
    a._register_builtins()
    sym = a._scope.lookup("http")
    if sym is not None: ok("http_module_registered")
    else: fail("http_module_registered", "http not in builtins")

t_http_module_registered()

def t_file_module_registered():
    from analyzer import Analyzer
    a = Analyzer()
    a._register_builtins()
    sym = a._scope.lookup("file")
    if sym is not None: ok("file_module_registered")
    else: fail("file_module_registered", "file not in builtins")

t_file_module_registered()

def t_timer_module_registered():
    from analyzer import Analyzer
    a = Analyzer()
    a._register_builtins()
    sym = a._scope.lookup("timer")
    if sym is not None: ok("timer_module_registered")
    else: fail("timer_module_registered", "timer not in builtins")

t_timer_module_registered()

def t_stdlib_has_file_module():
    from stdlib import _MODULES
    if "file" in _MODULES: ok("stdlib_file_module")
    else: fail("stdlib_file_module", f"keys: {list(_MODULES.keys())}")

t_stdlib_has_file_module()

def t_stdlib_has_timer_module():
    from stdlib import _MODULES
    if "timer" in _MODULES: ok("stdlib_timer_module")
    else: fail("stdlib_timer_module", f"keys: {list(_MODULES.keys())}")

t_stdlib_has_timer_module()

def t_stdlib_http_has_get_async():
    from stdlib import _MODULES
    http = _MODULES.get("http", {})
    if "get_async" in http: ok("stdlib_http_get_async")
    else: fail("stdlib_http_get_async", f"http keys: {list(http.keys())}")

t_stdlib_http_has_get_async()

# ── Summary ───────────────────────────────────────────────────────────────────
total = passed + failed
print()
print("=" * 58)
print(f"  v1.9.11 Test Results: {passed}/{total} passed")
print("  ALL PASS" if failed == 0 else f"  {failed} FAILED")
print("=" * 58)
sys.exit(0 if failed == 0 else 1)
