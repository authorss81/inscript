# InScript v1.1.0 — First Stable Release

> **839 tests passing** · **59 stdlib modules** · **Python 3.10+** · **Audit 9.5/10**  
> `pip install inscript-lang` · **v1.1.0 is the first production-ready release**

InScript is a statically-typed scripting language for 2D games — a readable, safe alternative to GDScript with 59 built-in game modules and a complete bytecode VM.

---

## Install

```bash
pip install inscript-lang                  # core
pip install "inscript-lang[game]"          # with pygame
pip install "inscript-lang[all]"           # pygame + LSP
inscript --version                         # InScript 1.1.0
```

---

## Quick Start

```bash
inscript --repl               # interactive shell
inscript game.ins             # run a file
inscript --watch game.ins     # auto-rerun on save
inscript --fmt game.ins       # format code
inscript --test               # run test_*.ins files
inscript --check game.ins     # static analysis only
```

---

## Language

```inscript
// Arrow functions
let evens = [1,2,3,4,5].filter(fn(x) => x % 2 == 0)
let names = users.map(fn(u) => u.name).sorted()

// ADT enums + exhaustive pattern matching
enum Shape { Circle(r: float)  Rect(w: float, h: float) }

fn area(s: Shape) -> float {
    return match s {
        case Shape.Circle(r) if r > 10.0 { "large" }
        case Shape.Circle(r)             { 3.14159 * r * r }
        case Shape.Rect(w, h)            { w * h }
        case 0..=5                       { 0.0 }
    }
}

// Structs with priv, super, decorators
struct Entity {
    priv id: int = 0
    name: string
    fn update(dt: float) { }
}
struct Player extends Entity {
    fn update(dt: float) {
        super.update(dt)
        self.move(dt)
    }
}

// Result type chaining
fn divide(a: float, b: float) -> Result {
    if b == 0.0 { return Err("zero") }
    return Ok(a / b)
}
let r = divide(10.0, 2.0)
    .map(fn(v) => v * 3.0)
    .unwrap_or(0.0)

// Type aliases + nullable + union
type PlayerID = int
fn find(id: PlayerID?) -> string|nil { ... }

// Rest destructuring
let [first, ...rest] = [1,2,3,4,5]
print(rest)   // [2, 3, 4, 5]
```

---

## Developer Tools

| Tool | Command |
|------|---------|
| Format | `inscript --fmt file.ins` · `--fmt-check` for CI |
| Watch | `inscript --watch file.ins` (auto-rerun on save) |
| Test | `inscript --test` (discovers `test_*.ins`) |
| REPL | `inscript --repl` · `.doc math` for live module docs |
| Check | `inscript --check file.ins` (static analysis) |
| LSP | `inscript --lsp` (VS Code extension available) |
| Playground | [authorss81.github.io/inscript/playground.html](https://authorss81.github.io/inscript/playground.html) |

---

## 59 Game Modules

```inscript
import "physics2d" as P  // RigidBody, World, collision callbacks
import "ecs"       as E  // Entity-Component-System
import "pathfind"  as N  // A*, Dijkstra, flow fields
import "tilemap"   as T  // load Tiled maps
import "camera2d"  as C  // follow, shake, zoom
import "particle"  as FX // emitter, burst, continuous
import "fsm"       as SM // state machine with guards
import "save"      as S  // save slots
import "audio"     as A  // load/play/stop/volume
import "localize"  as L  // multi-language strings
// + 49 more: animation, ecs, net_game, image, atlas, shader, ...
```

---

## Testing Your Code

```inscript
// test_game.ins
test "player moves right" {
    let p = Player{x: 0.0, y: 0.0}
    p.move(1.0, 0.0)
    assert(p.x == 5.0, "moved right")
}

test "score increases" {
    let g = Game{}
    g.add_score(100)
    assert(g.score == 100, "score added")
}
```

```bash
inscript --test              # ✅ 2/2 tests passed  12ms
inscript --test --verbose    # shows each test name
```

---

## GitHub Actions (auto-publish)

The `.github/workflows/publish.yml` workflow automatically publishes to PyPI when you push a version tag:

```bash
git tag -a v1.2.0 -m "InScript v1.2.0"
git push origin v1.2.0
# → tests run, then auto-uploads to PyPI
```

Setup: add `PYPI_API_TOKEN` to GitHub repo secrets.

---

## Upgrading

```bash
pip install --upgrade inscript-lang   # from v1.0.x
```

All v1.0.x syntax is fully backward compatible. No changes needed.

---

## Roadmap

| Version | Focus |
|---------|-------|
| **v1.1.0** ← you are here | First stable — all tooling complete |
| v1.2.0 | Type safety — generic enforcement, type narrowing |
| v1.3.0 | Performance — C extension (5-15× speedup) |
| v2.0.0 | Ecosystem — package registry, Studio IDE, WASM |

[ROADMAP.md](ROADMAP.md) · [Audit (9.5/10)](InScript_Language_Audit.md) · [Docs](https://authorss81.github.io/inscript/docs/)

---

MIT License · [GitHub](https://github.com/authorss81/inscript) · [PyPI](https://pypi.org/project/inscript-lang/)
