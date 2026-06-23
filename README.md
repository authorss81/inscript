<div align="center">

# 🎮 InScript

**A modern scripting language built for game development.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-287%20passing-brightgreen.svg)](#testing)
[![Version](https://img.shields.io/badge/version-3.9.6.33-blue.svg)](#)

</div>

---

InScript is a statically-typed scripting language designed for games. It brings Rust-style safety — pattern matching, ADT enums, Result types, generics — with Python-like readability.

**Game hooks run at CPython native speed** via Phase 7 Python AST transpilation — 67× faster than the tree-walk interpreter, 122× faster than the bytecode VM (benchmarked on pong.ins).

```inscript
struct Ship {
    pos: Vec2    hp: int = 100

    fn take_damage(amount: int) { self.hp -= amount }
    fn alive() -> bool          { return self.hp > 0 }
}

struct PlayerShip extends Ship {
    shots: int = 0
    fn fire() -> string {
        self.shots += 1
        return f"💥 Shot #{self.shots}!"
    }
}

enum Pickup { Health(amount: int)  Shield(duration: float) }

fn apply(p: Pickup, ship: Ship) {
    match p {
        case Health(n)   { ship.hp = min(ship.hp + n, 100) }
        case Shield(dur) { print(f"Shield active for {dur}s") }
    }
}
```

---

## Quick Start

```bash
# No install needed — just Python 3.10+
git clone https://github.com/YOUR_USERNAME/inscript.git
cd inscript/inscript_package

# Launch a game
python inscript.py --game examples/pong.ins

# Or the REPL
python inscript.py --repl
```

**Install via pip:**
```bash
pip install inscript-lang
inscript mygame.ins
inscript --game mygame.ins       # Run as a game (requires pygame)
inscript --repl
```

---

## Feature Overview

### Language Core

| Feature | Notes |
|---|---|
| `let` / `const` with type annotations | Full type inference |
| Functions, closures, lambdas `\|x\| x*2` | First-class |
| **Generic functions** `fn id<T>(x: T) -> T` | Type-erased |
| Default parameters `fn greet(name = "World")` | ✅ |
| Multiple return values `-> (int, string)` | Tuple destructuring |
| Variadic args `fn sum(...nums)` | ✅ |
| **Structs** with methods, fields, defaults | Full OOP |
| **Struct inheritance** `extends` | Method dispatch + fields |
| **Interfaces / Traits** | `interface` + `implements` |
| **Mixins** | Horizontal code reuse |
| **Properties** `get` / `set` | Computed + validated fields |
| **Static methods** `static fn` | ✅ |
| **Abstract methods** `abstract fn` | Enforced at instantiation |
| **Operator overloading** `fn +()` | All arithmetic + comparison |
| **Generic structs** `struct Stack<T>` | Multi-param supported |
| **ADT Enums** with data fields | `Circle(radius: float)` |
| **Pattern matching** + guards | `case v if v < 10` |
| **Destructuring** | `let [a,b] = arr` / `let (x,y) = pair` |
| **Array comprehensions** | `[x*x for x in 0..10]` |
| **Coroutines / generators** | `fn*` + `yield` + `.next()` |
| **Async / await** | Non-blocking syntax |
| **Decorators** `@name` | Function wrapping |
| **Error propagation** `?` | `Ok(v)` / `Err(e)` / `result?` |
| **Comptime evaluation** | `const N = comptime { 1024 * 4 }` |

### Operators & Expressions

| Feature | Example |
|---|---|
| **Ternary** `?:` | `x > 0 ? "pos" : "neg"` |
| **Inline if-then-else** | `if x > 0 then "pos" else "neg"` |
| **Null coalescing** `??` | `value ?? "default"` |
| **Optional chaining** `?.` | `obj?.field?.method()` |
| **Pipe operator** `\|>` | `x \|> double \|> clamp` |
| **Floor division** `//` | `7 // 2  → 3` |
| **Array spread** | `[1, ...other, 4]` |
| **String indexing** | `"hello"[0]  → 'h'` |
| **String slicing** | `"hello"[1..4]  → 'ell'` |
| **F-string brace escapes** | `f"Use {{braces}}"` |
| **String repeat** | `"ha" * 3  → "hahaha"` |
| **Labeled break/continue** | `outer: for … { break outer }` |

### Control Flow

| Feature | Example |
|---|---|
| `if / else if / else` | Standard |
| `while` | Standard |
| `for v in range` / `for v in array` | ✅ |
| **Enum iteration** `for v in MyEnum` | ✅ |
| **Pattern match** with guards | `match shape { case Circle(r) { … } }` |
| **Multi-catch** | `try {} catch(e: TypeError) {} catch e {}` |
| **Select** (channels) | `select { case v = ch.recv() {} case timeout(1.0) {} }` |

### Standard Library (18 Modules)

```inscript
import "math"    # floor, ceil, sin, cos, clamp, lerp, map_range ...
import "string"  # format, pad_left, reverse, words, truncate ...
import "array"   # binary_search, shuffle, group_by, zip_with ...
import "json"    # parse, stringify
import "io"      # read_file, write_file, read_lines, append_file
import "random"  # int, float, choice, shuffle, normal, seed
import "time"    # now, fps, delta, format_duration
import "color"   # Color, lerp, from_hex, blend, hsl, to_hex
import "tween"   # linear, ease_in, ease_out, bounce, spring ...
import "grid"    # Grid, get, set, neighbors, pathfind, flood_fill
import "events"  # EventBus, on, emit, off, once
import "debug"   # assert, assert_eq, log, warn, inspect, trace
import "http"    # get, post
import "path"    # join, basename, stem, ext, exists, glob, mkdir
import "regex"   # test, match, find_all, sub, split, escape
import "csv"     # parse, parse_file, to_string, from_dicts
import "uuid"    # v4, v1, nil, short, is_valid
import "crypto"  # sha256, md5, hmac_sign, hmac_verify, b64_encode ...
```

### Built-in Game Types

```inscript
let pos = Vec2(3.0, 4.0)
let vel = Vec3(0.0, -9.8, 0.0)
let red = Color(1.0, 0.0, 0.0)
let box = Rect(0.0, 0.0, 800.0, 600.0)
```

---

## Language Tour

### Variables & Types

```inscript
let x: int = 42
let name = "Ada"                       # inferred: str
const MAX = comptime { 1024 * 4 }      # = 4096 at compile time

let scores: [int]       = [95, 87, 72]
let config: {str: int}  = {"lives": 3, "level": 1}
```

### Functions

```inscript
fn lerp(a: float, b: float, t: float) -> float {
    return a + (b - a) * t
}

# Generic function
fn first<T>(arr: [T]) -> T { return arr[0] }
print(first([10, 20, 30]))             # 10
print(first(["a", "b", "c"]))         # a

# Closure / lambda
let double = |x| x * 2

# Default parameters
fn spawn(x: float, y: float = 0.0, hp: int = 100) -> Ship {
    return Ship { pos: Vec2(x, y), hp: hp }
}

# Multiple return values
fn minmax(arr: [float]) -> (float, float) {
    return (min(arr), max(arr))
}
let (lo, hi) = minmax([3.0, 1.0, 4.0, 5.0])
```

### Structs & Inheritance

```inscript
struct Entity {
    pos: Vec2
    abstract fn update(dt: float)
}

struct Enemy extends Entity {
    hp:    int   = 50
    speed: float = 120.0

    fn update(dt: float) {
        self.pos += Vec2(0.0, self.speed * dt)
    }

    fn take_damage(dmg: int) {
        self.hp -= dmg
        if self.hp <= 0 { print("Enemy destroyed!") }
    }
}
```

### ADT Enums + Pattern Matching

```inscript
enum GameEvent {
    Collision(a: string, b: string)
    Pickup(item: string, value: int)
    LevelComplete(time: float, stars: int)
}

fn handle(event: GameEvent) {
    match event {
        case Collision(a, b)           { print(f"{a} hit {b}") }
        case Pickup(item, v) if v > 50 { print(f"Rare: {item}!") }
        case Pickup(item, v)           { print(f"Got {item}") }
        case LevelComplete(t, 3)       { print(f"Perfect! {t}s") }
        case _                         { }
    }
}
```

### Error Handling

```inscript
fn load_level(path: string) -> Result {
    let raw  = read_file(path)?        # propagates Err automatically
    let data = json.parse(raw)?
    return Ok(data)
}

match load_level("level1.json") {
    case Ok(data) { print(f"Loaded: {data["name"]}") }
    case Err(msg) { print(f"Failed: {msg}") }
}
```

### Decorators

```inscript
fn memoize(fn_) {
    let cache = {}
    return |n| {
        let key = string(n)
        if !has_key(cache, key) { cache[key] = fn_(n) }
        return cache[key]
    }
}

@memoize
fn fibonacci(n: int) -> int {
    if n <= 1 { return n }
    return fibonacci(n - 1) + fibonacci(n - 2)
}
```

### Channels & Select

```inscript
let ch = make_channel()
thread(|| { sleep(0.05); chan_send(ch, "done") })

select {
    case result = ch.recv() { print(f"Got: {result}") }
    case timeout(1.0)       { print("Timed out") }
}
```

### Coroutines

```inscript
fn* wave_spawner(count: int) {
    let i = 0
    while i < count {
        yield Enemy { pos: Vec2(random.int(0, 800), -20) }
        i += 1
    }
}

let spawner = wave_spawner(5)
while !spawner.done {
    let enemy = spawner.next()
    # add enemy to scene
}
```

---

## CLI Reference

```bash
inscript <file.ins>                # Run a file
inscript --repl                    # Interactive REPL
inscript --game <file.ins>         # Run as pygame game
inscript --check <file.ins>        # Type-check without running
inscript --fmt <file.ins>          # Format source code
inscript --tokens <file.ins>       # Print lexer tokens
inscript --ast <file.ins>          # Print AST
inscript --profile                 # Show per-frame timings (with --game)
inscript --batch-draw              # Batch sprite draws (with --game)
inscript --version                 # Print version
```

### REPL Commands

```
.help            Show all commands
.vars            List variables in scope
.fns             List functions
.types           List structs / enums
.type <expr>     Show type and value of an expression
.modules         List all importable stdlib modules
.packages        List installed packages
.time <expr>     Benchmark execution time
.save <file>     Save session to .ins file
.load <file>     Load and run a .ins file
.clear           Reset session variables
.history         Show last 20 commands
exit / Ctrl+D    Quit
```

---

## Project Structure

```
inscript_package/               ← All real source code
├── inscript.py                 ← CLI entry point + package manager
├── lexer.py                    ← Tokenizer
├── parser.py                   ← Recursive-descent parser → AST
├── ast_nodes.py                ← AST node dataclasses
├── interpreter.py              ← Tree-walk interpreter
├── analyzer.py                 ← Static semantic analyzer
├── environment.py              ← Scope and variable resolution
├── errors.py                   ← Error signals
├── compiler.py                 ← InScript bytecode compiler
├── vm.py                       ← Register-based bytecode VM
├── py_compiler.py              ← Phase 7: InScript→Python AST transpiler (67× speedup)
├── pygame_backend.py           ← pygame game loop + draw namespaces
├── pyproject.toml              ← Build config (dynamic version from VERSION)
├── stdlib.py                   ← 18 standard library modules
├── stdlib_values.py            ← Runtime types (Vec2, Color, Range …)
├── repl.py                     ← Enhanced interactive REPL + web playground
├── _version.py                 ← Dynamic version reader (change inscript.py:VERSION only)
├── lsp/
│   ├── server.py               ← LSP server (pygls-based)
│   ├── diagnostics.py          ← Real-time error reporting
│   └── completions.py          ← Keyword, builtin, symbol completions
├── examples/
│   ├── pong.ins                ← Pong game (W/S/LEFT/RIGHT + UP/DOWN)
│   ├── breakout.ins            ← Breakout clone
│   ├── dino.ins                ← Dino runner
│   └── particles.ins           ← Particle system demo
└── studio_electron/            ← Electron desktop app for Studio IDE
```

---

## Testing

```bash
python test_lexer.py          # 25 tests   — tokenization
python test_parser.py         # 49 tests   — parsing + AST
python test_analyzer.py       # 35 tests   — semantic analysis
python test_interpreter.py    # 123 tests  — runtime behavior
python test_v12.py            # 55 tests   — stdlib + LSP + channels
python test_py_compiler.py    # Compile + execute all pong.ins hooks
```

**Total: 287+ tests, 0 failing** (run from `inscript_package/`).

Benchmarks:
```bash
python bench_phase7.py        # Phase 7 vs AST walker vs bytecode VM
python bench_phase6.py        # Legacy Phase 6 benchmarks
```

---

## VS Code Extension

The InScript extension provides syntax highlighting, code snippets, and — with `pip install pygls` — live error squiggles and autocomplete.

**Install:** Search `InScript Language` in the VS Code Marketplace.

**Enable LSP diagnostics:**
```bash
pip install pygls
```
The extension will auto-detect and start the language server.

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

**InScript v3.9.6** · Built with Python 3.10+

[Documentation](https://inscript-lang.dev) · [Package Registry](https://github.com/YOUR_USERNAME/inscript-packages) · [VS Code Extension](https://marketplace.visualstudio.com/items?itemName=inscript.inscript-lang)

</div>
