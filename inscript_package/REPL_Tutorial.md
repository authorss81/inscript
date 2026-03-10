# InScript REPL — Complete Tutorial

> **Version:** 1.0.1  
> **Start the REPL:** `python repl.py` or `python inscript.py --repl`  
> **Web Playground:** `python repl.py --web` (opens in your browser at `localhost:8080`)

---

## Table of Contents

1. [Starting the REPL](#1-starting-the-repl)
2. [Your First Lines](#2-your-first-lines)
3. [Multi-line Input](#3-multi-line-input)
4. [Tab Completion](#4-tab-completion)
5. [Session History](#5-session-history)
6. [Dot Commands Reference](#6-dot-commands-reference)
   - [.help](#help)
   - [.vars](#vars)
   - [.fns](#fns)
   - [.types](#types)
   - [.type \<expr\>](#type-expr)
   - [.time \<expr\>](#time-expr)
   - [.bytecode](#bytecode)
   - [.asm](#asm)
   - [.modules](#modules)
   - [.packages](#packages)
   - [.history](#history)
   - [.save and .load](#save-and-load)
   - [.clear and .reset](#clear-and-reset)
7. [Working with Variables](#7-working-with-variables)
8. [Working with Functions](#8-working-with-functions)
9. [Working with Structs](#9-working-with-structs)
10. [Working with Imports](#10-working-with-imports)
11. [Error Messages](#11-error-messages)
12. [The Web Playground](#12-the-web-playground)
13. [Practical Workflows](#13-practical-workflows)
14. [Known Limitations](#14-known-limitations)

---

## 1. Starting the REPL

```bash
# From the project directory:
python repl.py

# Or via the main CLI:
python inscript.py --repl

# Web playground (opens browser):
python repl.py --web
python repl.py --web --port 9000
```

When you start, you'll see the banner:

```
  ___       ____            _       _   
 |_ _|_ __ / ___|  ___ _ __(_)_ __ | |_ 
  | || `_ \\___ \ / __| `__| | `_ \| __|
  | || | | |___) | (__| |  | | |_) | |_ 
 |___|_| |_|____/ \___|_|  |_| .__/ \__|
                              |_|        
  InScript v1.0.1 — Interactive Shell
  Type .help for commands, exit to quit

>>>
```

The `>>>` prompt means the REPL is ready. Type `exit` or `quit` (or press `Ctrl+D`) to leave.

---

## 2. Your First Lines

Each expression you type is evaluated immediately. If it produces a value, the REPL shows it with a `→` arrow.

```
>>> 2 + 2
  → 4

>>> "hello" + " world"
  → hello world

>>> 10 * 10
  → 100

>>> true && false
  → false
```

`print()` outputs to stdout directly — the REPL shows that output without the `→` arrow:

```
>>> print("hello from InScript")
hello from InScript

>>> print(1, 2, 3)
1 2 3
```

Statements like `let`, `fn`, `struct` don't produce a value, so the REPL stays quiet:

```
>>> let x = 42
>>> x
  → 42

>>> x * 2
  → 84
```

---

## 3. Multi-line Input

The REPL detects when your input is incomplete (unclosed `{`, `[`, or `(`) and switches to a `...` continuation prompt automatically.

**Functions:**
```
>>> fn greet(name: string) -> string {
...     return "Hello, " + name + "!"
... }
>>> greet("Alice")
  → Hello, Alice!
```

**Structs:**
```
>>> struct Point {
...     x: float
...     y: float
...     fn distance() -> float {
...         import "math" as M
...         return M.sqrt(x * x + y * y)
...     }
... }
>>> let p = Point { x: 3.0, y: 4.0 }
>>> p.distance()
  → 5.0
```

**Control flow:**
```
>>> for i in range(5) {
...     print(i * i)
... }
0
1
4
9
16
```

**If/else:**
```
>>> let score = 85
>>> if score >= 90 {
...     print("A")
... } else if score >= 80 {
...     print("B")
... } else {
...     print("C")
... }
B
```

> **Tip:** Press `Ctrl+C` on a `...` line to cancel the current multi-line input and return to `>>>`.

---

## 4. Tab Completion

Press `Tab` at any point to auto-complete. The REPL completes:

- All language keywords (`let`, `fn`, `struct`, `match`, `for`, `while`, `return`, …)
- All built-in functions (`print`, `len`, `sort`, `filter`, `map`, `range`, `typeof`, …)
- All names you have defined in the current session (variables, functions, structs)

**Examples:**
```
>>> pri<Tab>          → print
>>> str<Tab>          → starts_with  string  stringify  str
>>> ran<Tab>          → range
>>> my_fu<Tab>        → my_function   (if you defined it earlier)
```

Completion is context-free — it matches any defined name that starts with what you typed.

---

## 5. Session History

- Use the **Up/Down arrow keys** to scroll through previous commands
- History is **saved between sessions** to `~/.inscript/history` — your commands persist after you close the REPL
- Use `.history` to see the last 20 commands (see below)

---

## 6. Dot Commands Reference

All special REPL commands start with a `.` (dot). They only work at the top-level `>>>` prompt, not inside a multi-line block.

---

### `.help`

Prints the command reference.

```
>>> .help

REPL Commands:
  .help              Show this help
  .vars              List all defined variables
  .fns               List all defined functions
  .types             List all defined structs
  .clear             Clear session (reset all variables)
  .save <file>       Save session to .ins file
  .load <file>       Load and run a .ins file
  .time <expr>       Measure execution time of expression
  .bytecode [expr]   Show compact bytecode for last (or given) expression
  .asm [expr]        Show full annotated assembly with constants/names tables
  .history           Show command history
  .reset             Full reset (interpreter + history)
  .type <expr>       Show the type of an expression
  .modules           List all importable stdlib modules
  .packages          List installed packages
```

---

### `.vars`

Lists every variable defined in the current session, with its current value.

```
>>> let x = 10
>>> let name = "Alice"
>>> let scores = [95, 87, 72]
>>> .vars
  name    = Alice
  scores  = [95, 87, 72]
  x       = 10
```

Variables are shown in alphabetical order. Built-in functions and internal names (prefixed with `_`) are hidden.

---

### `.fns`

Lists every function you have defined, with its parameter names.

```
>>> fn add(a: int, b: int) -> int { return a + b }
>>> fn greet(name: string) { print("Hi, " + name) }
>>> fn double(x: float) -> float { return x * 2.0 }
>>> .fns
  fn add(a, b)
  fn double(x)
  fn greet(name)
```

---

### `.types`

Lists every struct and enum defined in the current session.

```
>>> struct Vec2 { x: float; y: float }
>>> struct Player { name: string; hp: int }
>>> enum Dir { North South East West }
>>> .types
  struct Vec2
  struct Player
  enum Dir
```

---

### `.type <expr>`

Evaluates an expression and shows its **InScript type** and **current value**. Useful for understanding what you are working with.

```
>>> .type 42
  type: int
  value: 42

>>> .type 3.14
  type: float
  value: 3.14

>>> .type "hello"
  type: str
  value: hello

>>> .type [1, 2, 3]
  type: array
  value: [1, 2, 3]

>>> .type {"a": 1, "b": 2}
  type: dict
  value: {'a': 1, 'b': 2}

>>> .type true
  type: bool
  value: True

>>> .type nil
  type: nil
  value: None

>>> struct Point { x: float; y: float }
>>> let p = Point { x: 1.0, y: 2.0 }
>>> .type p
  type: Point
  value: Point{x: 1.0, y: 2.0}

>>> .type 2 + 2
  type: int
  value: 4

>>> .type typeof(42)
  type: str
  value: int
```

---

### `.time <expr>`

Runs an expression **10 times** and reports average, minimum, and maximum execution time in milliseconds.

```
>>> .time 100 * 100
  avg 0.02ms  min 0.01ms  max 0.04ms  (10 runs)

>>> fn fib(n: int) -> int {
...     if n <= 1 { return n }
...     return fib(n - 1) + fib(n - 2)
... }

>>> .time fib(20)
  avg 187.34ms  min 184.12ms  max 192.67ms  (10 runs)

>>> .time sort([5, 3, 1, 4, 2])
  avg 0.08ms  min 0.06ms  max 0.14ms  (10 runs)
```

Use this to profile hot paths and compare implementations. The 10-run average smooths out noise.

---

### `.bytecode`

Shows the **compact bytecode disassembly** for the last expression you ran, or for a given expression.

```
>>> 1 + 2 * 3
  → 7
>>> .bytecode
     0  LOAD_INT               1          1
     1  LOAD_INT               2          2
     2  LOAD_INT               3          3
     3  MUL                    3    1    2
     4  ADD                    4    0    3
     5  RETURN                 4    0    0

# Or give it an expression directly:
>>> .bytecode 10 > 5 ? "big" : "small"
     0  LOAD_INT              ...
     ...
```

The columns are: `address  OPCODE  dst  src1  src2`.

---

### `.asm`

Shows the **full annotated assembly** — constants table, names table, upvalues, and every instruction with inline annotations. More detailed than `.bytecode`.

```
>>> .asm fn sq(x: int) -> int { return x * x }

=== fn <main> ===
  Constants:
    [0] <fn sq>
  Names:
    [0] 'sq'
  Code  (2 instrs, 0 locals):
       0  LOAD_CONST            0      0      0  ; <fn sq>
       1  STORE_GLOBAL          0      0      0  ; 'sq'

  === fn sq ===
    Code  (4 instrs, 1 locals):
         0  LOAD_LOCAL            0      0      0
         1  LOAD_LOCAL            0      0      0
         2  MUL                   1      0      0
         3  RETURN                1      0      0
  (2 top-level instructions)
```

`.asm` also recurses into nested function definitions, making it useful for understanding how closures compile:

```
>>> .asm fn make_counter(start: int) { let n = start; return fn() { n += 1; return n } }

=== fn <main> ===
  ...
  === fn make_counter ===
    Upvalues:
      [0] (local 0)          ← 'n' captured from make_counter
    Code ...
      === fn <lambda> ===
        Upvalues:
          [0] (upval 0)      ← 'n' re-captured in the closure
        ...
```

---

### `.modules`

Lists all 18 importable standard library modules.

```
>>> .modules
  Importable stdlib modules:
    math        string      array       io
    json        random      time        color
    tween       grid        events      debug
    http        path        regex       csv
    uuid        crypto
  Usage: import "math"  or  from "math" import sin, cos
```

---

### `.packages`

Lists any packages installed via the package manager (`inscript --install <name>`).

```
>>> .packages
  No packages installed.
  Install with: inscript --install <name>
```

When packages are installed they appear as:
```
>>> .packages
  Installed packages (2):
    • inscript-vec
    • inscript-noise
```

---

### `.history`

Shows the last 20 commands from your current session.

```
>>> .history
     1  let x = 10
     2  let name = "Alice"
     3  fn greet(n: string) { print("Hi " + n) }
     4  greet(name)
     5  .vars
```

Full history (across sessions) is stored in `~/.inscript/history` and browsable with the Up arrow.

---

### `.save` and `.load`

**`.save <filename>`** writes everything you have typed in the current session to a `.ins` file. This is how you turn an interactive exploration session into a script.

```
>>> let pi = 3.14159
>>> fn circle_area(r: float) -> float { return pi * r * r }
>>> print(circle_area(5.0))
78.53975
>>> .save my_math.ins
  Saved 3 lines → my_math.ins
```

**`.load <filename>`** reads a `.ins` file and executes it in the current session, as if you had typed it all in.

```
>>> .load my_math.ins
  Loading my_math.ins…
  Loaded in 1.2ms
>>> circle_area(10.0)
  → 314.159
```

You can load any `.ins` file — example games, libraries, or scripts saved from a previous session.

```
>>> .load examples/pong.ins
```

---

### `.clear` and `.reset`

**`.clear`** resets all variables and functions you have defined, but keeps your command history.

```
>>> let x = 999
>>> .clear
  (session cleared — all variables reset)
>>> x
  [InScript NameError] E0042  Line 1: Undefined variable 'x'
```

**`.reset`** is a full wipe — clears everything including the readline history buffer.

```
>>> .reset
  (full reset)
```

Use `.clear` when you want a fresh slate without losing your history. Use `.reset` to start completely over.

---

## 7. Working with Variables

The session is stateful — everything you define persists until you `.clear` or exit.

```
>>> let health = 100
>>> let name = "Hero"
>>> let position = {"x": 0.0, "y": 0.0}

>>> health -= 25
>>> health
  → 75

>>> position.x = 10.5
>>> position
  → {'x': 10.5, 'y': 0.0}

>>> const MAX_HP = 100
>>> MAX_HP = 200
  [InScript SemanticError] E0020  Line 1: Cannot assign to constant 'MAX_HP'
```

Check types as you go:

```
>>> .type health
  type: int
  value: 75

>>> .type position
  type: dict
  value: {'x': 10.5, 'y': 0.0}
```

---

## 8. Working with Functions

Functions accumulate across the session. You can redefine them — the new definition replaces the old one.

```
>>> fn double(x: int) -> int { return x * 2 }
>>> double(5)
  → 10

>>> fn double(x: int) -> int { return x * 3 }   // redefine
>>> double(5)
  → 15

>>> fn apply(f, value: int) -> int { return f(value) }
>>> apply(double, 4)
  → 12
```

**Closures work correctly across the REPL:**

```
>>> fn make_adder(n: int) {
...     return fn(x: int) -> int { return x + n }
... }
>>> let add5 = make_adder(5)
>>> let add10 = make_adder(10)
>>> add5(3)
  → 8
>>> add10(3)
  → 13
```

**Recursive functions:**

```
>>> fn fib(n: int) -> int {
...     if n <= 1 { return n }
...     return fib(n - 1) + fib(n - 2)
... }
>>> fib(10)
  → 55
>>> .time fib(15)
  avg 24.1ms  min 23.6ms  max 25.8ms  (10 runs)
```

---

## 9. Working with Structs

Structs persist and can be used immediately after definition.

```
>>> struct Vec2 {
...     x: float
...     y: float
...
...     fn length() -> float {
...         import "math" as M
...         return M.sqrt(x*x + y*y)
...     }
...
...     fn add(other: Vec2) -> Vec2 {
...         return Vec2 { x: x + other.x, y: y + other.y }
...     }
... }

>>> let a = Vec2 { x: 3.0, y: 4.0 }
>>> let b = Vec2 { x: 1.0, y: 2.0 }
>>> a.length()
  → 5.0
>>> let c = a.add(b)
>>> c.x
  → 4.0
>>> c.y
  → 6.0
```

**Enums and pattern matching:**

```
>>> enum Direction { North South East West }

>>> fn describe(d: Direction) -> string {
...     match d {
...         case Direction.North { return "going up" }
...         case Direction.South { return "going down" }
...         case _               { return "going sideways" }
...     }
... }

>>> describe(Direction.North)
  → going up
>>> describe(Direction.East)
  → going sideways
```

**Inheritance:**

```
>>> struct Animal {
...     name: string
...     fn speak() -> string { return "..." }
... }

>>> struct Dog extends Animal {
...     fn speak() -> string { return "Woof! I'm " + name }
... }

>>> let d = Dog { name: "Rex" }
>>> d.speak()
  → Woof! I'm Rex
>>> d is Dog
  → true
>>> d is Animal
  → true
```

---

## 10. Working with Imports

Import any of the 18 stdlib modules at any time.

```
>>> import "math" as M
>>> M.sqrt(144.0)
  → 12.0
>>> M.PI
  → 3.141592653589793
>>> M.floor(3.9)
  → 3

>>> import "random" as R
>>> R.int(1, 6)        // roll a die
  → 4
>>> R.choice(["rock", "paper", "scissors"])
  → paper

>>> import "json" as J
>>> let data = {"name": "Alice", "score": 99}
>>> J.encode(data)
  → {"name": "Alice", "score": 99}

>>> import "uuid" as U
>>> U.v4()
  → "a3f4c1d2-8b7e-4f9a-bc3d-1e2f3a4b5c6d"

>>> import "time" as T
>>> T.now()
  → 1741234567.891
```

**Selective imports:**

```
>>> from "math" import sqrt, PI, floor
>>> sqrt(25.0)
  → 5.0
>>> PI
  → 3.141592653589793
```

**Importing a local `.ins` file:**

```
>>> import "./my_math.ins" as mymath
>>> mymath.circle_area(5.0)
  → 78.53975
```

---

## 11. Error Messages

The REPL catches all errors and shows them cleanly — it never crashes, even on syntax errors.

**Parse error** (with source location):
```
>>> let x = (1 + 2
  [InScript ParseError] E0010  Line 1, Col 14: Expected ')' — got end of input
    let x = (1 + 2
                  ^
  See: https://docs.inscript.dev/errors/E0010
```

**Semantic error** (caught by the static analyzer before running):
```
>>> print(undefined_variable)
  [InScript SemanticError] E0020  Line 1, Col 7: Undefined name: 'undefined_variable'
    Did you mean: 'undefined'?
  See: https://docs.inscript.dev/errors/E0020
```

**Runtime error**:
```
>>> let a = [1, 2, 3]
>>> a[10]
  [InScript InScriptRuntimeError] E0040  Line 1: Index 10 out of range (length 3)
  See: https://docs.inscript.dev/errors/E0040
```

**Type error**:
```
>>> let x: int = "hello"
  [InScript TypeError] E0030  Line 1: Type mismatch: expected 'int', got 'string'
  See: https://docs.inscript.dev/errors/E0030
```

After any error, your session state is **preserved** — variables you defined before the error are still there.

```
>>> let x = 10
>>> print(oops_undefined)
  [InScript SemanticError] ...
>>> x                        // x is still here
  → 10
```

---

## 12. The Web Playground

```bash
python repl.py --web
# Opens http://localhost:8080 in your default browser

python repl.py --web --port 9000
# Use a different port
```

The web playground is a simple browser interface where you can type InScript code and run it. It is useful for:
- Sharing code examples without requiring a terminal
- Running InScript on any machine with a browser
- Testing snippets without installing anything beyond Python

**How it works:** The playground runs a local HTTP server. Your browser sends code to `localhost:8080/run` as a POST request. The server runs it through the interpreter and returns the output as JSON. Output is displayed in the browser.

**Limitations of the web playground:**
- No persistent state between runs (each click is a fresh interpreter)
- No tab completion or history
- No dot commands (`.vars`, `.asm`, etc.)
- No access to the filesystem (`import "io"` will not be able to read local files)
- No real-time output — all output appears at once after the run completes

---

## 13. Practical Workflows

### Workflow 1: Explore → Script

Use the REPL to experiment, then save your work:

```
>>> import "math" as M
>>> fn circle_area(r: float) -> float { return M.PI * r * r }
>>> fn circle_perimeter(r: float) -> float { return 2.0 * M.PI * r }
>>> circle_area(5.0)
  → 78.53981633974483
>>> circle_perimeter(5.0)
  → 31.41592653589793
>>> .save geometry.ins
  Saved 3 lines → geometry.ins
```

Now `geometry.ins` is a reusable module:
```
>>> .clear
>>> .load geometry.ins
>>> circle_area(10.0)
  → 314.1592653589793
```

---

### Workflow 2: Profile and Optimise

```
>>> fn slow_sum(n: int) -> int {
...     let total = 0
...     for i in range(n) { total += i }
...     return total
... }
>>> .time slow_sum(10000)
  avg 48.2ms  min 47.1ms  max 51.3ms  (10 runs)

>>> fn fast_sum(n: int) -> int { return n * (n - 1) div 2 }
>>> .time fast_sum(10000)
  avg 0.04ms  min 0.03ms  max 0.07ms  (10 runs)

>>> fast_sum(10000) == slow_sum(10000)
  → true
```

---

### Workflow 3: Inspect Bytecode

Use `.asm` to understand how InScript compiles your code — useful when learning or debugging:

```
>>> .asm let x = 1 + 2 * 3

=== fn <main> ===
  Constants:
    [0] 1
    [1] 2
    [2] 3
  Code  (5 instrs, 1 locals):
       0  LOAD_CONST             0     0     0  ; 1
       1  LOAD_CONST             1     1     0  ; 2
       2  LOAD_CONST             2     2     0  ; 3
       3  MUL                    3     1     2
       4  ADD                    4     0     3
       5  STORE_GLOBAL           4     0     0  ; 'x'
```

Notice `*` is evaluated before `+` — the opcode order confirms correct precedence.

---

### Workflow 4: Interactive Debugging

The REPL is great for narrowing down bugs:

```
>>> .load buggy_game.ins
  Error: [InScript InScriptRuntimeError] E0040  Line 47: ...

>>> // Reproduce the minimal case:
>>> let player = { "hp": 100, "x": 0.0 }
>>> // test the function that was failing:
>>> take_damage(player, 150)
  [InScript InScriptRuntimeError] ...

>>> // Inspect intermediate values:
>>> .type player
  type: dict
  value: {'hp': 100, 'x': 0.0}
>>> .vars
```

---

### Workflow 5: Quick Calculations

The REPL doubles as a scientific calculator:

```
>>> import "math" as M
>>> M.PI * 5.0 * 5.0
  → 78.53981633974483

>>> 2 ** 32
  → 4294967296

>>> 0xFF & 0x0F
  → 15

>>> M.log2(1024.0)
  → 10.0

>>> M.sin(M.PI / 6.0)
  → 0.49999999999999994
```

---

## 14. Known Limitations

These are current issues to be aware of when using the REPL:

| Limitation | Detail |
|-----------|--------|
| **Operator overloading only works in the VM** | `operator +` on a struct will crash in the REPL (interpreter path). Use `.load` with `inscript run` for operator overloading. |
| **`async/await` is not real** | `async fn` and `await` parse and run, but execute synchronously. No event loop exists yet. |
| **F-strings can't contain string literals** | `f"{x > 0 ? \"yes\" : \"no\"}"` will fail to parse. Use a variable instead: `let msg = ...; f"{msg}"` |
| **`super` does not exist** | Calling `super.method()` in an override raises `NameError`. |
| **`finally` does not parse** | `try {} catch e {} finally {}` will raise a ParseError. |
| **Typed `catch` does not parse** | `catch e: string {}` raises ParseError. All catch blocks are untyped. |
| **Generators only work in `for` loops** | `let g = counter(); g()` will fail. Use `for v in counter() {}`. |
| **Math INF/NAN cannot be printed** | `import "math" as M; print(M.INF)` will crash. Use comparisons or `is_inf()`/`is_nan()` instead. |
| **Regex argument order is inverted** | `R.match("hello", "h.*o")` fails — the first argument is the pattern, second is the text. Correct call: `R.match("h.*o", "hello")`. |
| **Events module callbacks crash** | `E.on("event", fn(x){})` will crash when the event fires. The event system is broken in this version. |
| **`**=` compound assignment missing** | `x **= 2` raises ParseError. Use `x = x ** 2`. |
| **Static struct fields don't parse** | `static PI: float = 3.14` inside a struct body raises ParseError. Only `static fn` works. |
| **Missing struct fields become nil silently** | `Point { x: 1.0 }` with `y` omitted gives `p.y == nil` with no warning. |

---

*Tutorial covers InScript v1.0.1 — REPL as implemented in `repl.py`.*  
*For the full language reference, see the InScript Language Guide.*  
*For known bugs and design issues, see `InScript_Language_Audit.md`.*
