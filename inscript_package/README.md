<div align="center">

# 🎮 InScript

**A modern scripting language built for game development.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-501%20passing-brightgreen.svg)](#testing)
[![Version](https://img.shields.io/badge/version-1.0.2-blue.svg)](#)

</div>

---

InScript is a statically-typed scripting language designed for games. It brings Rust-style safety — pattern matching, ADT enums, Result types, generics — with Python-like readability, and runs out of the box with a single Python install.

```inscript
struct Ship {
    pos: Vec2
    hp:  int = 100

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
        case _           { }
    }
}
```

---

## Quick Start

```bash
# No install needed — just Python 3.10+
git clone https://github.com/authorss81/inscript.git
cd inscript/inscript_package

# Run a script
python inscript.py mygame.ins

# Launch the interactive REPL
python inscript.py --repl

# Run with a pygame game window (requires: pip install pygame)
python inscript.py mygame.ins --game

# Web playground in browser
python repl.py --web
```

---

## Running Games

InScript has two ways to run code:

| Mode | Command | Use for |
|------|---------|---------|
| **Script** | `python inscript.py file.ins` | Logic, tools, scripts |
| **Game window** | `python inscript.py file.ins --game` | pygame-backed games with draw/input |
| **REPL** | `python inscript.py --repl` | Exploring the language interactively |
| **Web playground** | `python repl.py --web` | Browser-based editor at `localhost:8080` |

> **Note:** You cannot run a pygame game inside the REPL. The REPL is for language features — variables, functions, structs, math, imports. For a game with a window, use `--game`.

Game window options:
```bash
python inscript.py mygame.ins --game --width 1280 --height 720 --fps 60
```

---

## Interactive REPL

The REPL lets you try any InScript expression instantly — no file needed.

```
>>> 2 ** 32
  → 4294967296

>>> let scores = [95, 87, 72, 100]
>>> filter(scores, fn(x) { return x >= 90 })
  → [95, 100]

>>> import "math" as M
>>> M.PI * 5.0 ** 2
  → 78.53981633974483
```

Multiline input — end a line with `\` to continue:

```
>>> fn greet(name: string) -> string {\
...   return f"Hello, {name}!"
... }
>>> greet("Alice")
  → Hello, Alice!
```

### REPL Commands

```
.help            Show all commands
.vars            List all variables in scope
.fns             List user-defined functions
.types           List struct / enum types
.type <expr>     Show type of an expression
.inspect <expr>  Deep field and method inspection
.doc <module>    Show stdlib module exports
.time <expr>     Benchmark (10 runs)
.bench <expr>    Statistical benchmark (100 runs)
.bytecode        Compact bytecode listing
.asm             Full annotated assembly
.vm              Toggle VM / interpreter mode
.history [n]     Show last n commands
.modules         List importable stdlib modules
.save <file>     Save session to .ins file
.load <file>     Load and run a .ins file
.export [file]   Export session as Markdown
.clear           Reset session variables
.reset           Full reset
exit / quit      Leave REPL
```

See [REPL_Tutorial.md](REPL_Tutorial.md) for the full guide.

---

## Feature Overview

### Language Core

| Feature | Notes |
|---|---|
| `let` / `const` with type annotations | Full type inference |
| Functions, closures, lambdas | First-class |
| **Generic functions** `fn id<T>(x: T) -> T` | Type-erased |
| Default parameters | ✅ |
| Multiple return values | Tuple destructuring |
| Variadic args `fn sum(...nums)` | ✅ |
| **Structs** with methods, fields, defaults | Full OOP |
| **Static fields** `static PI: float = 3.14` | ✅ |
| **Static methods** `static fn` | ✅ |
| **Struct inheritance** `extends` | Method dispatch + fields |
| **Interfaces / Traits** | `interface` + `implements` |
| **Mixins** | Horizontal code reuse |
| **Properties** `get` / `set` | Computed + validated fields |
| **Abstract methods** `abstract fn` | Enforced at instantiation |
| **Operator overloading** `operator +` | All arithmetic + comparison |
| **Generic structs** `struct Stack<T>` | Multi-param supported |
| **ADT Enums** with data fields | `Circle(radius: float)` |
| **Pattern matching** + guards | `case v if v < 10` |
| **Destructuring** | `let [a,b] = arr` / `let (x,y) = pair` |
| **Array comprehensions** | `[x*x for x in 0..10]` |
| **Generators** | `fn*` + `yield` + `gen()` or `for v in gen()` |
| **Decorators** `@name` | Function wrapping |
| **Error propagation** `?` | `Ok(v)` / `Err(e)` / `result?` |
| **Comptime evaluation** | `const N = comptime { 1024 * 4 }` |

### Operators

| Feature | Example |
|---|---|
| Ternary | `x > 0 ? "pos" : "neg"` |
| Null coalescing | `value ?? "default"` |
| Optional chaining | `obj?.field?.method()` |
| Pipe operator | `x \|> double \|> clamp` |
| Floor division | `7 // 2  → 3` |
| Bitwise | `&`, `\|`, `^`, `~`, `<<`, `>>` |
| Compound assigns | `+=`, `-=`, `*=`, `/=`, `**=`, `&=`, `\|=`, `^=` |
| F-strings | `f"Score: {player.hp * 1.5}"` |
| String repeat | `"ha" * 3  → "hahaha"` |
| Array spread | `[1, ...other, 4]` |
| Labeled break | `outer: for … { break outer }` |

### Standard Library (18 Modules)

```inscript
import "math"    // sin, cos, sqrt, floor, ceil, PI, E, INF, NAN …
import "string"  // split, join, trim, upper, lower, pad_left …
import "array"   // sort, filter, map, reduce, find, chunk, flatten …
import "json"    // encode, decode
import "io"      // read_file, write_file, read_lines, append_file
import "random"  // int(lo,hi), float(), float(lo,hi), choice, shuffle …
import "time"    // now, fps, delta, format_duration
import "color"   // rgb(r,g,b) [0-1], rgb255(r,g,b) [0-255], from_hex …
import "tween"   // linear, ease_in, ease_out, bounce, spring …
import "grid"    // Grid, get, set, neighbors, pathfind, flood_fill
import "events"  // on, emit, off, once — InScript callbacks supported ✅
import "debug"   // assert, assert_eq, log, warn, inspect, trace
import "regex"   // test(text,pat), match(text,pat), find_all, sub …
import "path"    // join, basename, stem, ext, exists, glob, mkdir
import "csv"     // parse, parse_file, to_string, from_dicts
import "uuid"    // v4, v1, nil, short, is_valid
import "http"    // get, post
import "crypto"  // sha256, md5, hmac_sign, b64_encode …
```

### Built-in Game Types

```inscript
let pos = Vec2(3.0, 4.0)
let vel = Vec3(0.0, -9.8, 0.0)
let red = Color(1.0, 0.0, 0.0)        // 0.0–1.0 scale
let box = Rect(0.0, 0.0, 800.0, 600.0)
```

---

## Language Tour

### Variables & Types

```inscript
let x: int   = 42
let name     = "Ada"                   // inferred: string
const MAX    = comptime { 1024 * 4 }   // = 4096

let scores: [int]      = [95, 87, 72]
let config: {str: int} = {"lives": 3, "level": 1}
```

### Structs

```inscript
struct Entity {
    pos:   Vec2
    speed: float = 120.0
    static MAX_SPEED: float = 400.0    // static field

    abstract fn update(dt: float)
}

struct Enemy extends Entity {
    hp: int = 50

    fn update(dt: float) {
        self.pos += Vec2(0.0, self.speed * dt)
    }
}

print(Entity.MAX_SPEED)    // 400.0
```

### Pattern Matching

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
    let raw  = read_file(path)?
    let data = json.decode(raw)?
    return Ok(data)
}

match load_level("level1.json") {
    case Ok(data)  { print(f"Loaded: {data["name"]}") }
    case Err(msg)  { print(f"Failed: {msg}") }
}
```

### Generators

```inscript
fn* wave_spawner(count: int) {
    let i = 0
    while i < count {
        yield Enemy{ pos: Vec2(random.int(0, 800), -20) }
        i += 1
    }
}

// Use in a for loop
for enemy in wave_spawner(5) {
    scene.add(enemy)
}

// Or step manually
let gen = wave_spawner(5)
let e = gen()          // advances one step
```

### Events

```inscript
import "events" as E

E.on("player_hit", fn(damage) {
    print(f"Took {damage} damage")
})

E.emit("player_hit", 25)   // → "Took 25 damage"
```

### Regex

```inscript
import "regex" as R

// All functions take (text, pattern) — text first
R.test("hello world", "\\w+")          // true
R.find_all("a1 b22 c333", "\\d+")     // ["1", "22", "333"]
R.sub("foobar", "o+", "0")            // "f0bar"
```

---

## CLI Reference

```bash
python inscript.py <file.ins>              # Run a file
python inscript.py <file.ins> --game       # Run with pygame window
python inscript.py --repl                  # Interactive REPL
python inscript.py --check <file.ins>      # Type-check without running
python inscript.py --tokens <file.ins>     # Print lexer tokens
python inscript.py --ast <file.ins>        # Print AST
python inscript.py --version               # Print version

# Game window
python inscript.py game.ins --game --width 1280 --height 720 --fps 60

# Package manager
python inscript.py --install <pkg>
python inscript.py --remove  <pkg>
python inscript.py --packages
```

---

## Project Structure

```
inscript_package/
├── inscript.py          ← CLI entry point
├── lexer.py             ← Tokenizer
├── parser.py            ← Recursive-descent parser → AST
├── ast_nodes.py         ← All AST node dataclasses
├── interpreter.py       ← Tree-walk interpreter
├── compiler.py          ← Bytecode compiler
├── vm.py                ← Register-based bytecode VM
├── analyzer.py          ← Static semantic analyzer
├── environment.py       ← Scope and variable resolution
├── errors.py            ← Error signals
├── stdlib.py            ← 18 standard library modules
├── stdlib_values.py     ← Runtime types (Vec2, Color, Range …)
├── repl.py              ← Interactive REPL + web playground
└── REPL_Tutorial.md     ← Full REPL guide
```

---

## Testing

```bash
python test_phase5.py    # 270 tests  — language core, stdlib, REPL
python test_phase6.py    # 145 tests  — bytecode compiler + VM
python test_phase7.py    #  32 tests  — operator overloading
python test_audit.py     #  54 tests  — regression suite
```

**Total: 501 tests, 0 failing.**

---

## What's New in v1.0.2

| Fix | Description |
|-----|-------------|
| **Windows REPL** | No longer crashes when `readline` is missing |
| **Large integers** | `2 ** 10000` now prints without crashing |
| **BUG-14** | Static fields on structs: `static PI: float = 3.14` now works |
| **BUG-16** | Missing required struct fields now print a clear warning |
| **BUG-17** | Float passed to `int` parameter now warns about truncation |
| **BUG-18** | `push(arr, val)` and `pop(arr)` work as free functions |
| **BUG-19** | Generator objects callable: `gen()` advances one step |
| **BUG-21** | Non-exhaustive match error shows which arms were checked |
| **BUG-25** | Regex API is now `(text, pattern)`: `R.test("hello", "\\w+")` |
| **BUG-26** | `color.rgb()` uses 0.0–1.0 scale; `rgb255()` added for 0–255 |
| **BUG-27** | `math.INF` / `math.NAN` now print as `Infinity` / `NaN` |
| **BUG-28** | `events.on()` callbacks now fire correctly from InScript |
| **BUG-29** | `fill(arr, val)` fills in-place; `fill(n, val)` makes new array |
| **BUG-30** | `random.float(lo, hi)` range form now works |

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

**InScript v1.0.2** · Built with Python 3.10+

[REPL Tutorial](REPL_Tutorial.md) · [Language Audit](InScript_Language_Audit.md)

</div>
