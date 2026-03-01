<div align="center">

# 🎮 InScript

**A modern programming language designed for games — clean syntax, powerful type system, batteries included.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-122%20passing-brightgreen.svg)](#testing)
[![Version](https://img.shields.io/badge/version-0.6.0-blue.svg)](#)

</div>

---

## What is InScript?

InScript is a statically-typed, dynamically-executed scripting language built specifically for game development. It brings Rust-style safety (pattern matching, ADT enums, Result types, generics) with Python-like readability — and runs right out of the box with a single Python file.

```inscript
// Structs with inheritance and operator overloading
struct Ship {
    x: float   y: float   hp: int

    fn take_damage(amount: int) { self.hp -= amount }
}

struct PlayerShip extends Ship {
    shots: int
    fn fire() -> string {
        self.shots += 1
        return f"💥 Shot #{self.shots}!"
    }
}

// ADT enums with pattern matching
enum Asteroid {
    Small(x: float, y: float)
    Large(x: float, y: float)
}

fn points(a: Asteroid) -> int {
    match a {
        case Small(x, y) { return 30 }
        case Large(x, y) { return 10 }
    }
}

// Generic data structures
struct Stack<T> {
    items: T[]
    fn push(item: T) { self.items.push(item) }
    fn pop() -> T    { return self.items.pop() }
}

// Error propagation
fn accuracy(hits: int, shots: int) -> Result {
    let r = safe_divide(float(hits), float(shots))?
    return Ok(r * 100.0)
}

// Coroutines
fn* spawn_wave(n: int) {
    let i = 0
    while i < n { yield Asteroid.Large(random_int(0,800), 0.0); i += 1 }
}
```

---

## Feature Overview

| Feature | Status | Notes |
|---|---|---|
| Variables (`let`, `const`) with type annotations | ✅ | Type inference supported |
| Structs with methods | ✅ | Full OOP |
| **Struct inheritance** (`extends`) | ✅ | Method dispatch + field inheritance |
| **Interface / Trait** system | ✅ | `interface` + `implements` |
| **Operator overloading** (`fn +()`) | ✅ | All arithmetic + comparison ops |
| **Mixins** (`with` keyword) | ✅ | Horizontal code reuse |
| **Properties** (`get`/`set`) | ✅ | Computed + validated fields |
| **Static methods** | ✅ | `static fn` on structs |
| **Generics** (`struct Stack<T>`) | ✅ | Type-erased, multi-param |
| **ADT Enums** with data fields | ✅ | `Circle(radius: float)` |
| **Pattern matching** + guards | ✅ | `case v if v < 10` |
| **ADT destructuring** | ✅ | `case Circle(r)` binds `r` |
| **Error propagation** `?` | ✅ | `Ok(v)` / `Err(e)` / `Result?` |
| **Coroutines / generators** | ✅ | `fn*` + `yield` + `.next()` |
| **Comptime evaluation** | ✅ | `comptime { 1024 * 4 }` |
| **Pipe operator** `\|>` (chainable) | ✅ | `x \|> double \|> add1` |
| **Destructuring** | ✅ | `let [a,b] = arr` / `let {x,y} = p` |
| **Spread operator** | ✅ | `fn sum(...args)` / `call(...arr)` |
| **Optional chaining** | ✅ | `obj?.field?.method()` |
| **Nullish coalescing** | ✅ | `value ?? "default"` |
| F-strings | ✅ | `f"Hello {name}!"` |
| Multi-line strings | ✅ | `"""..."""` |
| Closures / lambdas | ✅ | `\|x\| x * 2` |
| Async/await syntax | ✅ | |
| Labeled break/continue | ✅ | `outer: for ... { break outer }` |
| Built-in math, Vec2, Vec3, Color | ✅ | Game-ready primitives |
| REPL | ✅ | Interactive shell |

---

## Quick Start

### 1. Clone and run (no install needed)

```bash
git clone https://github.com/YOUR_USERNAME/inscript.git
cd inscript
python inscript.py examples/asteroid_blaster.ins
```

### 2. Try the REPL

```bash
python inscript.py --repl
```

```
InScript 0.6.0 REPL — type 'exit' or Ctrl+C to quit
>> let x = 42
>> print(f"The answer is {x}")
The answer is 42
>> struct Point { x: float  y: float }
>> let p = Point { x: 3.0, y: 4.0 }
>> print(p.x)
3.0
```

### 3. Run any `.ins` file

```bash
python inscript.py mygame.ins
```

---

## Running in VS Code

### Prerequisites

- [VS Code](https://code.visualstudio.com/) installed
- [Python extension for VS Code](https://marketplace.visualstudio.com/items?itemName=ms-python.python) installed
- Python 3.10+ on your system (`python --version`)

### Step-by-step

**1. Clone the repo and open in VS Code**
```bash
git clone https://github.com/YOUR_USERNAME/inscript.git
cd inscript
code .
```

**2. Set Python interpreter**

Press `Ctrl+Shift+P` → type `Python: Select Interpreter` → choose Python 3.10+

**3. Open the example program**

In the Explorer panel, open `examples/asteroid_blaster.ins` to browse the code.

**4. Create a run task** — create `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run InScript file",
      "type": "shell",
      "command": "python",
      "args": ["${workspaceFolder}/inscript.py", "${file}"],
      "group": {
        "kind": "build",
        "isDefault": true
      },
      "presentation": {
        "reveal": "always",
        "panel": "shared"
      },
      "problemMatcher": []
    },
    {
      "label": "Run example: Asteroid Blaster",
      "type": "shell",
      "command": "python",
      "args": ["${workspaceFolder}/inscript.py", "examples/asteroid_blaster.ins"],
      "group": "build",
      "presentation": {
        "reveal": "always",
        "panel": "shared"
      },
      "problemMatcher": []
    },
    {
      "label": "InScript REPL",
      "type": "shell",
      "command": "python",
      "args": ["${workspaceFolder}/inscript.py", "--repl"],
      "group": "build",
      "presentation": {
        "reveal": "always",
        "panel": "dedicated"
      },
      "problemMatcher": []
    }
  ]
}
```

**5. Run it!**

- Press `Ctrl+Shift+B` to run the currently open `.ins` file
- Or open Command Palette → `Tasks: Run Task` → choose any task above

**Tip:** Add this `launch.json` for F5 debugging too (`.vscode/launch.json`):

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run InScript (current file)",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/inscript.py",
      "args": ["${file}"],
      "console": "integratedTerminal"
    }
  ]
}
```

Now pressing **F5** while editing any `.ins` file will run it through InScript.

---

## Language Tour

### Variables & Types

```inscript
let x: int = 42
let name = "Ada"          // type inferred
const MAX = comptime { 1024 * 4 }   // compile-time constant = 4096
```

### Functions

```inscript
fn lerp(a: float, b: float, t: float) -> float {
    return a + (b - a) * t
}

// Closures
let doubled = [1, 2, 3].map(|x| x * 2)
```

### Structs

```inscript
struct Bullet extends Entity {
    dmg:   int = 10
    speed: float = 600.0

    fn update(dt: float) {
        self.pos += Vec2(0.0, -self.speed * dt)
    }
}
```

### Generics

```inscript
struct Pair<A, B> {
    first:  A
    second: B
}

let p = Pair<int, string> { first: 1, second: "one" }
```

### ADT Enums + Pattern Matching

```inscript
enum Shape {
    Circle(radius: float)
    Rectangle(w: float, h: float)
}

fn area(s: Shape) -> float {
    match s {
        case Circle(r)       { return 3.14159 * r * r }
        case Rectangle(w, h) { return w * h }
    }
}
```

### Error Handling

```inscript
fn load(path: string) -> Result {
    let data = read_file(path)?   // propagates Err upward
    return Ok(data)
}

let result = load("level.json")
let data   = unwrap_or(result, "{}")
```

### Coroutines

```inscript
fn* enemy_spawner() {
    while true {
        yield Enemy { x: random_int(0, 800), y: -20 }
    }
}

let spawner = enemy_spawner()
let enemy   = spawner.next()
```

### Pipe Operator

```inscript
fn clamp01(v: float) -> float { return clamp(v, 0.0, 1.0) }
fn to_pct(v: float) -> string { return f"{v * 100.0}%" }

let display = raw_value |> clamp01 |> to_pct
// → "73.5%"
```

---

## Project Structure

```
inscript/
├── inscript.py          ← Entry point (run files, REPL, flags)
├── lexer.py             ← Tokenizer
├── parser.py            ← Recursive-descent parser → AST
├── ast_nodes.py         ← All AST node dataclasses
├── interpreter.py       ← Tree-walk interpreter (122 tests)
├── analyzer.py          ← Static type analyzer
├── environment.py       ← Scope / variable resolution
├── errors.py            ← Error + signal classes
├── stdlib.py            ← Standard library
├── stdlib_values.py     ← Runtime value types (InScriptRange, etc.)
├── repl.py              ← Interactive REPL
├── setup.py             ← PyPI packaging
├── examples/
│   └── asteroid_blaster.ins   ← Full demo program
└── tests/
    ├── test_interpreter.py    ← 122 runtime tests
    ├── test_parser.py
    ├── test_lexer.py
    ├── test_analyzer.py
    └── test_stdlib.py
```

---

## Testing

```bash
# Run all interpreter tests (122 tests)
python test_interpreter.py

# Run parser tests
python test_parser.py

# Run lexer tests
python test_lexer.py
```

Expected output:
```
=================================================================
  Phase 4 Final Results
=================================================================
  122 passed, 0 failed out of 122 tests
=================================================================
```

---

## CLI Reference

```bash
python inscript.py <file.ins>          # Run a file
python inscript.py --repl             # Interactive REPL
python inscript.py --check <file.ins> # Type-check only (no run)
python inscript.py --tokens <file.ins># Print lexer tokens
python inscript.py --ast <file.ins>   # Print the AST
python inscript.py --version          # Print version
```

---

## Roadmap

- [ ] Union / intersection types (`Shape = Circle | Rectangle`)
- [ ] Abstract methods (`abstract fn update()`)
- [ ] Macro / metaprogramming system
- [ ] SIMD vector types (`float32x4`)
- [ ] LSP VS Code extension (syntax highlighting + completions)
- [ ] PyPI package (`pip install inscript-lang`)

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

Built with ❤️ and Python · InScript 0.6.0

</div>
