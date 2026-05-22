"""
test_v230.py — InScript v2.3.0
===========================================
Concurrency & Async:
  • async fn / await
  • spawn <expr>  →  InScriptTask (.join, .done, .result)
  • channel<T>(capacity)  (.send, .recv, .try_recv, .close, .closed, .size)
  • channel<T> generic syntax
  • select { case x = ch.recv() { } ... }
  • async for var in channel { }
  • mutex(value)  (.set, .value, .lock)
  • rwlock(value) (.read, .write, .value)
  • timer.after / timer.every / timer.cancel
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

import repl as repl_mod
from interpreter import Interpreter
from parser import parse

PASS = 0; FAIL = 0

def ok(name):
    global PASS; PASS += 1; print(f"  PASS  {name}")

def fail(name, msg=""):
    global FAIL; FAIL += 1; print(f"  FAIL  {name}: {msg}")

def run(src: str) -> Interpreter:
    i = Interpreter(); i.run(parse(src)); return i

def check(name, got, expected):
    if got == expected: ok(name)
    else: fail(name, f"want {expected!r}, got {got!r}")

def check_close(name, got, expected, tol=1e-9):
    if abs(got - expected) <= tol: ok(name)
    else: fail(name, f"want ≈{expected}, got {got}")

# ─────────────────────────────────────────────────────────────────────────────
# 1. async / await
# ─────────────────────────────────────────────────────────────────────────────

def test_async_basic():
    i = run("async fn add(a: int, b: int) -> int { return a + b }\nlet r = await add(3, 4)")
    check("async fn basic", i._env.get("r"), 7)

def test_async_no_await():
    # Calling async fn without await returns a coroutine object (not an error)
    i = run("async fn f() -> int { return 99 }\nlet r = f()")
    from stdlib_values import InScriptCoroutine
    if isinstance(i._env.get("r"), InScriptCoroutine):
        ok("async without await = coroutine")
    else:
        fail("async without await = coroutine", f"got {type(i._env.get('r'))}")

def test_async_chain():
    i = run("""
async fn double(n: int) -> int { return n * 2 }
async fn quad(n: int) -> int {
    let d = await double(n)
    return await double(d)
}
let r = await quad(5)
""")
    check("async chain double", i._env.get("r"), 20)

def test_async_conditional():
    i = run("""
async fn max_of(a: int, b: int) -> int {
    if a > b { return a }
    return b
}
let r = await max_of(3, 7)
""")
    check("async conditional", i._env.get("r"), 7)

def test_async_passthrough():
    # await on a plain value should return it unchanged
    i = run("let r = await 42")
    check("await plain value passthrough", i._env.get("r"), 42)

def test_async_string():
    i = run('async fn greet(name: string) -> string { return "Hi " ++ name }\nlet r = await greet("Ada")')
    check("async string result", i._env.get("r"), "Hi Ada")

# ─────────────────────────────────────────────────────────────────────────────
# 2. spawn + InScriptTask
# ─────────────────────────────────────────────────────────────────────────────

def test_spawn_join():
    i = run("let t = spawn fn() -> int { return 21 + 21 }()\nlet r = t.join()")
    check("spawn + join result", i._env.get("r"), 42)

def test_spawn_done_after_join():
    i = run("let t = spawn fn() -> int { return 1 }()\nt.join()\nlet d = t.done")
    check("spawn done=true after join", i._env.get("d"), True)

def test_spawn_async_fn():
    i = run("""
async fn compute() -> int { return 7 * 6 }
let t = spawn compute()
let r = t.join()
""")
    check("spawn async fn", i._env.get("r"), 42)

def test_spawn_string():
    i = run('let t = spawn fn() -> string { return "hello" }()\nlet r = t.join()')
    check("spawn string", i._env.get("r"), "hello")

def test_spawn_multiple():
    i = run("""
let t1 = spawn fn() -> int { return 10 }()
let t2 = spawn fn() -> int { return 20 }()
let r = t1.join() + t2.join()
""")
    check("spawn multiple", i._env.get("r"), 30)

# ─────────────────────────────────────────────────────────────────────────────
# 3. channel
# ─────────────────────────────────────────────────────────────────────────────

def test_channel_send_recv():
    i = run("let ch = channel(10)\nch.send(42)\nlet v = ch.recv()")
    check("channel send/recv", i._env.get("v"), 42)

def test_channel_generic_syntax():
    i = run("let ch = channel<int>(10)\nch.send(99)\nlet v = ch.recv()")
    check("channel<T> generic syntax", i._env.get("v"), 99)

def test_channel_string_generic():
    i = run('let ch = channel<string>(5)\nch.send("hello")\nlet v = ch.recv()')
    check("channel<string>", i._env.get("v"), "hello")

def test_channel_try_recv_empty():
    i = run("let ch = channel(5)\nlet v = ch.try_recv()")
    check("try_recv empty = nil", i._env.get("v"), None)

def test_channel_try_recv_value():
    i = run("let ch = channel(5)\nch.send(7)\nlet v = ch.try_recv()")
    check("try_recv with value", i._env.get("v"), 7)

def test_channel_size():
    i = run("let ch = channel(10)\nch.send(1)\nch.send(2)\nlet s = ch.size")
    check("channel size", i._env.get("s"), 2)

def test_channel_is_empty():
    i = run("let ch = channel(5)\nlet e = ch.is_empty")
    check("channel is_empty true", i._env.get("e"), True)

def test_channel_close():
    i = run("let ch = channel(5)\nch.close()\nlet c = ch.closed")
    check("channel closed", i._env.get("c"), True)

def test_channel_multiple_messages():
    i = run("""
let ch = channel(10)
ch.send(10)
ch.send(20)
ch.send(30)
let a = ch.recv()
let b = ch.recv()
let c = ch.recv()
let total = a + b + c
""")
    check("channel multiple messages", i._env.get("total"), 60)

def test_channel_fifo_order():
    i = run("""
let ch = channel(10)
ch.send(1)
ch.send(2)
ch.send(3)
let first = ch.recv()
""")
    check("channel FIFO order", i._env.get("first"), 1)

# ─────────────────────────────────────────────────────────────────────────────
# 4. select statement
# ─────────────────────────────────────────────────────────────────────────────

def test_select_recv():
    i = run("""
let ch = channel(5)
ch.send(42)
let result = 0
select {
    case x = ch.recv() { result = x }
    case timeout(0) { result = -1 }
}
""")
    check("select recv branch", i._env.get("result"), 42)

def test_select_timeout_fallback():
    i = run("""
let ch = channel(5)
let result = 0
select {
    case x = ch.recv() { result = x }
    case timeout(0) { result = -1 }
}
""")
    check("select timeout fallback", i._env.get("result"), -1)

def test_select_send():
    i = run("""
let ch = channel(10)
let sent = false
select {
    case ch.send(99) { sent = true }
    case timeout(0) { sent = false }
}
let v = ch.recv()
""")
    check("select send", i._env.get("sent"), True)
    check("select send value received", i._env.get("v"), 99)

# ─────────────────────────────────────────────────────────────────────────────
# 5. async for
# ─────────────────────────────────────────────────────────────────────────────

def test_async_for_sum():
    i = run("""
let ch = channel(10)
ch.send(1)
ch.send(2)
ch.send(3)
ch.close()
let total = 0
async for v in ch {
    total = total + v
}
""")
    check("async for sum", i._env.get("total"), 6)

def test_async_for_count():
    i = run("""
let ch = channel(10)
ch.send(10)
ch.send(20)
ch.send(30)
ch.close()
let count = 0
async for v in ch {
    count = count + 1
}
""")
    check("async for count", i._env.get("count"), 3)

def test_async_for_empty_channel():
    i = run("""
let ch = channel(10)
ch.close()
let count = 0
async for v in ch {
    count = count + 1
}
""")
    check("async for empty channel", i._env.get("count"), 0)

# ─────────────────────────────────────────────────────────────────────────────
# 6. mutex
# ─────────────────────────────────────────────────────────────────────────────

def test_mutex_set_value():
    i = run("let m = mutex(0)\nm.set(42)\nlet v = m.value")
    check("mutex set + value", i._env.get("v"), 42)

def test_mutex_initial_value():
    i = run("let m = mutex(100)\nlet v = m.value")
    check("mutex initial value", i._env.get("v"), 100)

def test_mutex_nil_value():
    i = run("let m = mutex(nil)\nlet v = m.value")
    check("mutex nil value", i._env.get("v"), None)

# ─────────────────────────────────────────────────────────────────────────────
# 7. rwlock
# ─────────────────────────────────────────────────────────────────────────────

def test_rwlock_initial_value():
    i = run("let rw = rwlock(10)\nlet v = rw.value")
    check("rwlock initial value", i._env.get("v"), 10)

def test_rwlock_string():
    i = run('let rw = rwlock("hello")\nlet v = rw.value')
    check("rwlock string value", i._env.get("v"), "hello")

# ─────────────────────────────────────────────────────────────────────────────
# 8. timer namespace
# ─────────────────────────────────────────────────────────────────────────────

def test_timer_after_returns_handle():
    i = run('import "timer" as timer\nlet h = timer.after(10000, fn() { })')
    from stdlib_values import InScriptTimerHandle
    h = i._env.get("h")
    if hasattr(h, 'cancel'):
        ok("timer.after returns cancellable handle")
    else:
        fail("timer.after returns cancellable handle", f"got {type(h)}")

def test_timer_after_cancel():
    i = run('import "timer" as timer\nlet h = timer.after(10000, fn() { })\nh.cancel()')
    ok("timer.after cancel no error")

def test_timer_every_cancel():
    i = run('import "timer" as timer\nlet h = timer.every(10000, fn() { })\nh.cancel()')
    ok("timer.every cancel no error")

def test_timer_now_is_int():
    i = run('import "timer" as timer\nlet t = timer.now()')
    v = i._env.get("t")
    if isinstance(v, int) and v > 0:
        ok("timer.now is positive int")
    else:
        fail("timer.now is positive int", f"got {v!r}")

# ─────────────────────────────────────────────────────────────────────────────
# 9. version
# ─────────────────────────────────────────────────────────────────────────────

def test_version_is_230():
    if repl_mod.VERSION == "2.3.0":
        ok("version_is_2.3.0")
    else:
        fail("version_is_2.3.0", f"got {repl_mod.VERSION}")

# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("test_v230.py — v2.3.0: Concurrency & Async")
    print("=" * 60)

    # async/await
    test_async_basic()
    test_async_no_await()
    test_async_chain()
    test_async_conditional()
    test_async_passthrough()
    test_async_string()

    # spawn
    test_spawn_join()
    test_spawn_done_after_join()
    test_spawn_async_fn()
    test_spawn_string()
    test_spawn_multiple()

    # channel
    test_channel_send_recv()
    test_channel_generic_syntax()
    test_channel_string_generic()
    test_channel_try_recv_empty()
    test_channel_try_recv_value()
    test_channel_size()
    test_channel_is_empty()
    test_channel_close()
    test_channel_multiple_messages()
    test_channel_fifo_order()

    # select
    test_select_recv()
    test_select_timeout_fallback()
    test_select_send()

    # async for
    test_async_for_sum()
    test_async_for_count()
    test_async_for_empty_channel()

    # mutex
    test_mutex_set_value()
    test_mutex_initial_value()
    test_mutex_nil_value()

    # rwlock
    test_rwlock_initial_value()
    test_rwlock_string()

    # timer
    test_timer_after_returns_handle()
    test_timer_after_cancel()
    test_timer_every_cancel()
    test_timer_now_is_int()

    # version
    test_version_is_230()

    total = PASS + FAIL
    print("=" * 60)
    print(f"{PASS}/{total} passed  ({FAIL} failed)")
    sys.exit(0 if FAIL == 0 else 1)
