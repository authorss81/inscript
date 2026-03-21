# -*- coding: utf-8 -*-
# InScript — Game-Focused Scripting Language

> **v1.0.12** · 839 tests passing · 59 stdlib modules · Python 3.10+
> **Pre-stable** — first stable release targets **v1.1.0 Q2 2026**

InScript is a statically-typed scripting language designed as a readable, safe GDScript alternative. It ships with 59 built-in modules for 2D games — physics, audio, ECS, pathfinding, networking — with no external engine required.

---

## Quick Start

```bash
pip install pygame pygls

git clone https://github.com/authorss81/inscript
cd inscript/inscript_package

python inscript.py --repl               # Start REPL
python inscript.py examples/platformer.ins   # Run a game
python test_comprehensive.py            # 335/335 tests
```

---

## Language Sample

```inscript
// ADT enums + pattern matching as expression
enum Shape { Circle(r: float)  Rect(w: float, h: float) }

fn area(s: Shape) -> float {
    return match s {
        case Shape.Circle(r)   { 3.14159 * r * r }
        case Shape.Rect(w, h)  { w * h }
        case _ { 0.0 }
    }
}

// Result type + try-catch as expression
fn divide(a: float, b: float) -> Result {
    if b == 0.0 { return Err("div by zero") }
    return Ok(a / b)
}
let safe = try { divide(10.0, 0.0) } catch e { Err(e) }

// Generators
fn* fibonacci() {
    let a=0; let b=1
    while true { yield a; [a,b] = [b, a+b] }
}

// 59 game modules
import "physics2d" as P
import "pathfind"  as Nav
let path = Nav.astar(grid, start, goal)
let body = P.step(player, dt)
```

---

## What Works (v1.0.12)

- Core language: types, operators, control flow, destructuring
- OOP: structs, single/multi-inheritance, interfaces, operator overloading, `priv`/`pub`
- Pattern matching: guards, ADTs, match-as-expression, Ok/Err
- Generators (`fn*` / `yield`) in both interpreter and VM
- Error handling: try/catch/finally, typed catch, Result, assert/panic
- Closures, decorators `@name`, pipe operator `|>`, optional chaining `?.`
- Bytecode VM (register-based, 60+ opcodes) with full feature parity
- 59 stdlib modules — all tested and documented
- Enhanced REPL: 30+ commands, `.doc module`, `.vm`, `.tutorial`
- Static analyzer: type mismatches, missing returns, arg counts, exhaustive match
- LSP server + VS Code extension (syntax highlighting, completions, diagnostics)
- Windows, macOS, Linux — UTF-8 clean

## Missing (v1.1 targets)

- `inscript fmt` formatter
- Step-through debugger in VS Code
- `pip install inscript-lang` (PyPI not live yet)
- Live docs site (docs.inscript.dev returns 404)
- Web playground

---

## Test Suites

```
python test_phase5.py          # 270 core language
python test_phase6.py          # 145 bytecode VM
python test_phase7.py          # 32  operator overloading
python test_audit.py           # 54  audit regressions
python test_comprehensive.py   # 335 full feature coverage
# Total: 836+ tests — all passing
```

---

## Stdlib (59 modules)

math, string, array, json, io, random, datetime, collections, regex,
crypto, uuid, path, fs, http, database, physics2d, tilemap, camera2d,
input, audio, particle, ecs, fsm, pathfind, events, net_game, save,
localize, vec, tween, color, image, atlas, animation, shader, signal,
pool, grid, bench, thread, debug, process, log, compress, url,
base64, yaml, toml, csv, xml, ssl, hash, net, argparse, iter,
template, format, time + more.

In the REPL: `.doc math` shows live documentation for any module.

---

## Roadmap

| Version | Target | Highlights |
|---------|--------|------------|
| v1.0.12 | Mar 2026 | int.to_hex/bin, range props, Queue API, UTF-8 clean |
| v1.1.0 | Q2 2026 | formatter, debugger, PyPI, docs, playground |
| v1.2.0 | Q3 2026 | union types, generic enforcement, null-safe |
| v1.3.0 | Q4 2026 | C extension 5-15x speed, standalone binary |
| v2.0.0 | 2027 | WASM, package registry, InScript Studio IDE |

See [ROADMAP.md](ROADMAP.md) for full detail.

---

## Honest Assessment

InScript is **public beta** — the language is complete for 2D game scripting.
Gap to v1.1 "first stable": ~2-3 months of tooling work. Total cost: ~$9/yr (domain).

---

MIT License · [GitHub](https://github.com/authorss81/inscript) · [Audit](InScript_Language_Audit.md) · [Roadmap](ROADMAP.md)
