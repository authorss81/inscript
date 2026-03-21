# InScript v1.0.16 — Game-Focused Scripting Language

> **839 tests passing** · **59 stdlib modules** · **Python 3.10+** · **Audit score: 8.6/10**
> Pre-stable — first stable release: **v1.1.0 (Q2 2026)**

InScript is a statically-typed scripting language for 2D games — a readable, safe GDScript alternative with 59 built-in game modules and a near-complete bytecode VM.

---

## Quick Start

```bash
pip install pygame pygls
git clone https://github.com/authorss81/inscript
cd inscript/inscript_package
python inscript.py --repl              # Enhanced REPL with 30+ commands
python inscript.py examples/platformer.ins
python inscript.py --version           # InScript 1.0.16
```

---

## Language Features

```inscript
// Structs with priv fields, inheritance, super, decorators
struct Counter {
    priv count: int = 0
    fn inc()    { self.count += 1 }
    fn get()    { return self.count }
}

struct NamedCounter extends Counter {
    name: string
    fn label()  { return self.name ++ ": " ++ string(self.get()) }
}

// Decorator pattern — @name applies a function wrapper
fn memoize(f) {
    let cache = {}
    return fn(x) {
        if cache.has_key(string(x)) { return cache[string(x)] }
        let r = f(x); cache.set(string(x), r); return r
    }
}

@memoize
fn fib(n: int) -> int {
    if n <= 1 { return n }
    return fib(n-1) + fib(n-2)
}
print(fib(40))   // fast — cached

// ADT enums + pattern matching with range patterns and guards
enum Temp { Cold  Warm  Hot }

fn classify(c: float) -> string {
    return match c {
        case 0.0..=15.0  { "cold" }
        case 16.0..=25.0 { "warm" }
        case _           { "hot" }
    }
}

// Result type chaining
fn divide(a: float, b: float) -> Result {
    if b == 0.0 { return Err("zero") }
    return Ok(a / b)
}
let r = divide(10.0, 2.0)
           .map(fn(v) { return v * 3.0 })
           .unwrap_or(0.0)
print(r)   // 15.0

// try-finally guaranteed cleanup
import "fs" as FS
fn read_safe(path: string) -> Result {
    let f = FS.open(path)
    try {
        return Ok(f.read())
    } catch e {
        return Err(e)
    } finally {
        f.close()   // always runs
    }
}
```

---

## What's in v1.0.16

| Feature | Status |
|---------|--------|
| Full OOP: structs, inheritance, `super`, interfaces, mixins | ✅ Both interpreter + VM |
| `priv`/`pub` field enforcement with `_current_self` tracking | ✅ Both paths |
| `@decorator fn g()` — decorator application compiles to VM correctly | ✅ Fixed v1.0.16 |
| Pattern matching: ranges `case 1..=10`, ADT guards `case Circle(r) if r>3` | ✅ Fixed v1.0.15-16 |
| `try/catch/finally` with value-returning `try` expressions | ✅ Both paths |
| Generators `fn*`/`yield`, variadic `fn(*args)` | ✅ Both paths |
| `arr.count(val)` and `arr.count(fn)` overloads | ✅ Fixed v1.0.15 |
| `assert(cond, msg)` / `panic(msg)` — catch gets message directly | ✅ Fixed v1.0.16 |
| VM `super.method()` working | ✅ Fixed v1.0.15 |
| VM `try-finally` | ✅ Fixed v1.0.15 |
| 59 stdlib modules, all documented in REPL (`.doc module`) | ✅ Complete |
| Bytecode VM: ~feature-complete parity with interpreter | ✅ v1.0.13-16 |

## Still Missing (v1.1 targets)

- `inscript fmt` — code formatter
- Step-through debugger in VS Code
- `pip install inscript-lang` — PyPI not published yet
- Docs site (`docs.inscript.dev` returns 404)
- Web playground

---

## Tests

```bash
python test_phase6.py         # 145/145 bytecode VM
python test_phase7.py         # 32/32  operator overloading
python test_audit.py          # 54/54  audit regressions
python test_comprehensive.py  # 335/335 all features
# Total: 839 tests — all green
```

---

## 59 Stdlib Modules

| Category | Modules |
|----------|---------|
| Core | math, string, array, json, io, random, time, debug |
| Data | csv, regex, xml, toml, yaml, url, base64, uuid |
| Net/Crypto | http, ssl, crypto, hash, net |
| FS/Process | path, fs, process, compress, log |
| Date/Coll | datetime, collections, database |
| Game Visual | color, tween, image, atlas, animation, shader |
| Game IO | input, audio |
| Game World | physics2d, tilemap, camera2d, particle, pathfind |
| Game Systems | grid, events, ecs, fsm, save, localize, net_game |
| Utilities | signal, vec, pool, iter, format, template, argparse, bench, thread |

In the REPL: `.doc math` — live docs for any module.

---

## Roadmap

| Version | Target | Focus |
|---------|--------|-------|
| v1.0.16 | March 2026 | VM decorator, priv tracking, assert/panic, count overload |
| **v1.1.0** | Q2 2026 | **First stable**: formatter, debugger, PyPI, docs, playground |
| v1.2.0 | Q3 2026 | Union types, generic enforcement, null-safe types |
| v1.3.0 | Q4 2026 | C extension 5–15× speedup, standalone binary |
| v2.0.0 | 2027 | WASM, package registry, InScript Studio IDE |

[ROADMAP.md](ROADMAP.md) · [Audit (8.6/10)](InScript_Language_Audit.md) · [Tutorial](REPL_Tutorial.md)

---

MIT License · [GitHub](https://github.com/authorss81/inscript)
