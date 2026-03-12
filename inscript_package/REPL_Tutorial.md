# InScript REPL — Complete Tutorial

> **Version:** 1.0.2  
> **Start the REPL:** `python repl.py` or `python inscript.py --repl`  
> **Web Playground:** `python repl.py --web` (opens browser at `localhost:8080`)

---

## Table of Contents

1. [What is the REPL?](#1-what-is-the-repl)
2. [Starting the REPL](#2-starting-the-repl)
3. [Auto-Print — Expressions Show Their Value](#3-auto-print)
4. [Variables and Persistent State](#4-variables-and-persistent-state)
5. [Multiline Input](#5-multiline-input)
6. [Functions](#6-functions)
7. [Structs and Enums](#7-structs-and-enums)
8. [Error Handling](#8-error-handling)
9. [Imports and the Standard Library](#9-imports-and-the-standard-library)
10. [History and Repeat](#10-history-and-repeat)
11. [Dot Commands — Overview](#11-dot-commands-overview)
12. [Inspecting Your Session](#12-inspecting-your-session)
13. [Timing and Benchmarking](#13-timing-and-benchmarking)
14. [Bytecode Inspection](#14-bytecode-inspection)
15. [VM Mode](#15-vm-mode)
16. [Session Management](#16-session-management)
17. [Tab Completion](#17-tab-completion)
18. [The Web Playground](#18-the-web-playground)
19. [Practical Workflows](#19-practical-workflows)
20. [Known Limitations](#20-known-limitations)

---

## 1. What is the REPL?

**REPL** stands for **Read → Evaluate → Print → Loop**.

You type one line (or a block) of InScript, press Enter, and the result appears immediately. You do not need to write a file, save it, and run it — the REPL lets you try things out instantly.

Think of it like a calculator that also knows the entire InScript language.

Basic idea:
- Type an expression → see its value
- Define a variable → use it in the next line
- Define a function → call it immediately
- Make a mistake → see the error with the line highlighted

Everything you define stays alive until you type `exit` or run `.reset`.

---

## 2. Starting the REPL

```bash
# Standard way:
python repl.py

# Via the main CLI:
python inscript.py --repl

# Web playground in browser:
python repl.py --web
```

You will see the banner:

```
  InScript v1.0.2 — Interactive Shell
  Type .help for commands, exit to quit

>>>
```

The `>>>` is the prompt. Type here and press Enter.

To leave the REPL at any time:
```
>>> exit
```
or `quit`, or press **`Ctrl+C`** (Windows) / `Ctrl+D` (Linux/macOS).

> **If you see `v1.0.1` in the banner** — you are running the old REPL. Follow the publish guide to copy the new `repl.py` to your machine.

> **Windows note:** Tab-completion and persistent arrow-key history require the `readline` module which is not available on Windows by default. The REPL still works fully — you just use the normal terminal Up/Down keys for history instead.

---

## 3. Auto-Print

**Basic idea:** You do not need `print()` for expressions. If you type a bare expression, the REPL shows its value automatically with a `→` arrow.

```
>>> 2 + 2
  → 4

>>> 3 ** 4
  → 81

>>> "hello".upper()
  → HELLO

>>> true
  → true

>>> nil
  → nil
```

**Statements do not auto-print.** A `let` or `print()` call is a statement — it runs but shows nothing extra:

```
>>> let x = 10
>>> print(x)
10
```

**Advanced: any expression works**, including method calls, array indexing, dict access:

```
>>> [1, 2, 3, 4, 5]
  → [1, 2, 3, 4, 5]

>>> [10, 20, 30][1]
  → 20

>>> {"name": "Alice", "age": 30}["name"]
  → Alice

>>> len("hello world")
  → 11

>>> range(5)
  → [0, 1, 2, 3, 4]
```

If execution takes more than 100ms, the REPL also shows the time taken:

```
>>> sort(range(10000))
  → [0, 1, 2, ...]
  (143ms)
```

---

## 4. Variables and Persistent State

**Basic idea:** Variables you define in one line are available in every line after it. The REPL remembers everything until you reset.

```
>>> let x = 10
>>> let y = 20
>>> x + y
  → 30
```

You can reassign variables freely:

```
>>> let score = 0
>>> score += 100
>>> score += 50
>>> score
  → 150
```

**All compound assignment operators work:**

```
>>> let n = 2
>>> n **= 10
>>> n
  → 1024

>>> let flags = 0xFF
>>> flags &= 0x0F
>>> flags
  → 15

>>> let bits = 0b0101
>>> bits |= 0b1010
>>> bits
  → 15

>>> let v = 0b1100
>>> v ^= 0b0110
>>> v
  → 10
```

**Advanced: closures capture state across calls:**

```
>>> fn make_counter() {\
...   let n = 0\
...   return fn() { n += 1; return n }\
... }
>>> let c = make_counter()
>>> c()
  → 1
>>> c()
  → 2
>>> c()
  → 3
```

The counter's internal `n` persists between calls — that is closure state.

---

## 5. Multiline Input

**Basic idea:** Some code spans multiple lines. The REPL handles this in two ways.

### Method 1 — End a line with `\`

End any line with a backslash `\` to force continuation to the next line. The REPL strips the `\` and joins the lines together before evaluating. This is the **reliable method that works everywhere**.

```
>>> while x <= 100 { \
... print(x)\
... x = x + 1}
1
2
3
...
```

```
>>> let result = 1 + \
...   2 + \
...   3
>>> result
  → 6
```

Long expressions split across lines:

```
>>> let message = "Hello, " + \
...   "world!"
>>> message
  → Hello, world!
```

Multiline function with `\` on every line:

```
>>> fn make_counter() {\
...   let n = 0\
...   return fn() { n += 1; return n }\
... }
>>> let c = make_counter()
>>> c()
  → 1
>>> c()
  → 2
>>> c()
  → 3
```

### Method 2 — Open a brace `{` and press Enter

When you open a `{` and press Enter, the REPL detects the unbalanced brace and waits for you to close it. Continuation lines show `...` as a prompt.

```
>>> fn add(a: int, b: int) -> int {
...   return a + b
... }
>>> add(3, 7)
  → 10
```

> **Note:** The line numbers (`...2`, `...3`) shown in this tutorial are for readability. Your terminal may show plain `...` — that is normal and correct.

### Cancel multiline input

Press `Ctrl+C` to cancel whatever you have typed and return to the `>>>` prompt.

---

## 6. Functions

**Basic idea:** Define a function, then call it. It stays defined for the rest of the session.

```
>>> fn greet(name: string) -> string {
...2   return f"Hello, {name}!"
...3 }
>>> greet("Alice")
  → Hello, Alice!
>>> greet("World")
  → Hello, World!
```

Functions with default parameters:

```
>>> fn power(base: int, exp: int = 2) -> int {
...2   return base ** exp
...3 }
>>> power(5)
  → 25
>>> power(3, 4)
  → 81
```

**Advanced: pipe operator `|>`**

The pipe operator passes the result of the left side as the first argument to the right:

```
>>> fn double(x: int) -> int { return x * 2 }
>>> fn add_one(x: int) -> int { return x + 1 }

>>> 5 |> double
  → 10

>>> 5 |> double |> add_one
  → 11
```

**Advanced: generator functions with `fn*`**

Generator functions yield values one at a time and are iterable in `for` loops:

```
>>> fn* countdown(n: int) {
...2   while n > 0 {
...3     yield n
...4     n -= 1
...5   }
...6 }
>>> for v in countdown(5) {
...2   print(v)
...3 }
5
4
3
2
1
```

**Advanced: closures and higher-order functions**

```
>>> fn make_adder(n: int) {
...2   return fn(x: int) { return x + n }
...3 }
>>> let add10 = make_adder(10)
>>> add10(5)
  → 15
>>> add10(100)
  → 110
```

---

## 7. Structs and Enums

**Basic idea:** Define a struct type, then create instances of it.

```
>>> struct Point {
...2   x: float
...3   y: float
...4 }
>>> let p = Point{x: 3.0, y: 4.0}
>>> p.x
  → 3.0
>>> p.y
  → 4.0
```

Structs with methods:

```
>>> struct Circle {
...2   radius: float
...3   fn area() -> float {
...4     return 3.14159 * self.radius * self.radius
...5   }
...6   fn describe() -> string {
...7     return f"Circle with radius {self.radius}"
...8   }
...9 }
>>> let c = Circle{radius: 5.0}
>>> c.area()
  → 78.53975
>>> c.describe()
  → Circle with radius 5.0
```

**Advanced: inheritance with `extends`**

```
>>> struct Animal {
...2   name: string
...3   fn speak() -> string { return "..." }
...4 }
>>> struct Dog extends Animal {
...2   fn speak() -> string { return f"{self.name} says: Woof!" }
...3 }
>>> let d = Dog{name: "Rex"}
>>> d.speak()
  → Rex says: Woof!
```

**Enums:**

```
>>> enum Direction { North; South; East; West }
>>> let dir = Direction.North
>>> dir
  → Direction.North
```

---

## 8. Error Handling

**Basic idea:** The REPL shows errors clearly with the line that caused them.

```
>>> 1 / 0
  ✗ [InScript InScriptRuntimeError] E0010  Line 1: Division by zero
    1 / 0
    ^
  See: https://docs.inscript.dev/errors/E0010
```

The `^` caret points to the exact position of the error.

After an error, the session continues normally — nothing is lost:

```
>>> let x = 10
>>> x / 0
  ✗ Division by zero
>>> x
  → 10
```

**`try / catch / finally`:**

```
>>> try {
...2   throw "something went wrong"
...3 } catch e {
...4   print("caught:", e)
...5 } finally {
...6   print("always runs")
...7 }
caught: something went wrong
always runs
```

**Typed catch clauses:**

```
>>> try {
...2   throw 42
...3 } catch e: int {
...4   print("caught int:", e)
...5 } catch e: string {
...6   print("caught string:", e)
...7 }
caught int: 42
```

**Result type (`Ok` / `Err`):**

```
>>> fn safe_divide(a: int, b: int) {
...2   if b == 0 { return Err("division by zero") }
...3   return Ok(a / b)
...4 }
>>> let r = safe_divide(10, 2)
>>> is_ok(r)
  → true
>>> unwrap(r)
  → 5.0

>>> let bad = safe_divide(10, 0)
>>> is_err(bad)
  → true
>>> unwrap_err(bad)
  → division by zero
```

---

## 9. Imports and the Standard Library

**Basic idea:** Use `import` to bring in a stdlib module, then access its functions with dot notation.

```
>>> import "math" as M
>>> M.PI
  → 3.141592653589793
>>> M.sqrt(16.0)
  → 4.0
>>> M.sin(M.PI / 2.0)
  → 1.0
```

Common modules:

```
>>> import "random" as R
>>> R.int(1, 10)
  → 7

>>> import "json" as J
>>> J.encode({"name": "Alice", "age": 30})
  → {"name": "Alice", "age": 30}

>>> import "string" as S
>>> S.split("hello world foo", " ")
  → [hello, world, foo]
```

Use `.doc <module>` to see what a module exports (see [Section 12](#12-inspecting-your-session)).

Use `.modules` to list every available module:

```
>>> .modules
  Importable stdlib modules:
    math      string    array     io
    json      random    time      color
    tween     grid      events    debug    ...
```

**Advanced: chaining stdlib calls**

```
>>> import "string" as S
>>> S.split("apple,banana,cherry", ",")
  → [apple, banana, cherry]

>>> map(S.split("apple,banana,cherry", ","), fn(s) { return upper(s) })
  → [APPLE, BANANA, CHERRY]
```

---

## 10. History and Repeat

**Basic idea:** The REPL remembers what you have typed. Use the Up/Down arrow keys to navigate back through previous commands.

> **Windows note:** Arrow-key history navigation requires `readline`. On Windows without readline, use `!!` to repeat the last command, or retype commands manually.

**`!!` — repeat the last command:**

Type `!!` and press Enter to re-run the last thing you typed.

```
>>> let n = 0
>>> n += 1
>>> !!
>>> !!
>>> n
  → 3
```

> **Note:** `!!` only works in the new REPL v1.0.2. In v1.0.1 it was not supported.

**`.history` — see recent commands:**

```
>>> .history
```

Shows the last 20 commands. To see more or fewer:

```
>>> .history 5
>>> .history 50
```

Example output:

```
  [1]  let x = 10
  [2]  let y = 20
  [3]  x + y
  [4]  fn add(a,b) { return a+b }
  [5]  add(x, y)
```

> **Note:** `.history` and all dot commands (`.time`, `.doc`, `.bench`, etc.) are features of the **new REPL v1.0.2** (`repl.py`). If you see `(history not available in fallback REPL)` or a parse error on `.time`, you are running the old v1.0.1 REPL. Copy the new `repl.py` from the zip to your machine.

---

## 11. Dot Commands — Overview

**Basic idea:** All REPL meta-commands start with a dot `.`. They let you inspect your session, manage files, measure performance, and more.

Type `.help` to see the full list at any time:

```
>>> .help

REPL Commands:
  .help                Show this help
  .vars                List all defined variables
  .fns                 List all defined functions
  .types               List all defined struct/enum types
  .env                 Show full environment tree
  .inspect <expr>      Deep field/method inspection
  .type <expr>         Show the type of an expression
  .doc <module>        Show stdlib module exports
  .clear               Reset session variables
  .reset               Full reset (interpreter + history)
  .save <file>         Save session to .ins file
  .load / .run <file>  Load and run a .ins file
  .export [file]       Export session as Markdown
  .time <expr>         Measure execution time (10 runs)
  .bench <expr>        Statistical benchmark (100 runs)
  .bytecode [expr]     Compact bytecode listing
  .asm [expr]          Full annotated assembly
  .vm                  Toggle VM / interpreter execution mode
  .history [n]         Show last n commands (default 20)
  .modules             List importable stdlib modules
  .packages            List installed packages
  exit / quit          Leave REPL

Shortcuts:
  Up/Down   Navigate history        Tab   Auto-complete
  !!        Repeat last command      Ctrl+C  Cancel input
```

---

## 12. Inspecting Your Session

These commands let you see what is currently defined and understand types and values.

---

### `.vars` — all defined names

Shows every name in scope — your variables, built-in functions, and global stubs.

```
>>> let x = 42
>>> let name = "Alice"
>>> let scores = [10, 20, 30]
>>> .vars
  ...
  name          :string     Alice
  scores        :array      [10, 20, 30]
  x             :int        42
  ...
```

Your user-defined names appear alphabetically mixed with builtins. User variables show their type and value. Built-in functions show `:function` or `:builtin_function_or_method`.

---

### `.fns` — all user-defined functions

Shows only functions you have defined (not builtins):

```
>>> fn add(a, b) { return a + b }
>>> fn greet(name) { return f"Hello, {name}!" }
>>> .fns
  fn add(a, b)
  fn greet(name)
```

---

### `.types` — all struct and enum types

```
>>> struct Point { x: float; y: float }
>>> enum Color { Red; Green; Blue }
>>> .types
  struct Point
    x: float
    y: float
  enum Color
    Red
    Green
    Blue
```

---

### `.type <expr>` — type of any expression

**Basic idea:** Find out the type of any value or expression.

```
>>> .type 42
  int  →  42

>>> .type 3.14
  float  →  3.14

>>> .type "hello"
  string  →  hello

>>> .type [1, 2, 3]
  array  →  [1, 2, 3]

>>> .type true
  bool  →  true

>>> .type nil
  nil  →  nil
```

Works on variables and expressions too:

```
>>> let x = 100
>>> .type x
  int  →  100

>>> .type x * 3.14
  float  →  314.0
```

---

### `.inspect <expr>` — deep inspection

**Basic idea:** For structs and complex values, `.inspect` shows every field and method.

```
>>> struct Vec2 { x: float; y: float }
>>> let v = Vec2{x: 1.0, y: 2.0}
>>> .inspect v
  InScriptInstance: Vec2{ x=1.0, y=2.0 }
    methods: get, set
```

**Advanced:** Inspect anything — arrays, dicts, imported modules:

```
>>> .inspect [10, 20, 30]
  array (3 items): [10, 20, 30]

>>> .inspect {"a": 1, "b": 2}
  dict (2 keys): a, b
```

---

### `.env` — full environment tree

Shows the raw environment scope chain — every name at every scope level. More detailed than `.vars`, useful when debugging scope issues:

```
>>> .env
global:
  x: int = 42
  name: string = Alice
  add: function = ...
```

---

### `.doc <module>` — stdlib module exports

**Basic idea:** Find out what functions a module provides before or after importing it.

```
>>> .doc math
  math stdlib module (17 exports):
    sin(x)     cos(x)     tan(x)
    sqrt(x)    pow(x,y)   abs(x)
    floor(x)   ceil(x)    round(x)
    log(x)     log2(x)    log10(x)
    PI         E          ...
```

```
>>> .doc json
>>> .doc random
>>> .doc string
>>> .doc array
```

---

## 13. Timing and Benchmarking

**Basic idea:** Measure how fast your code runs.

### `.time <expr>` — quick timing

Runs the expression 10 times and reports average, min, and max:

```
>>> .time 1 + 1
  avg 0.03ms  min 0.02ms  max 0.04ms  (10 runs)
```

```
>>> .time sort(range(1000))
  avg 2.1ms  min 1.9ms  max 2.8ms  (10 runs)
```

### `.bench <expr>` — full statistical benchmark

Runs 100 times with a warm-up phase, then gives full statistics:

```
>>> .bench 1 + 1
  Warming up (5 runs)…
  Benchmarking (100 runs)…
  Benchmark (100 runs):
    mean   0.023ms   stddev 0.005ms
    min    0.020ms   max    0.039ms
    p50    0.021ms   p95    0.035ms
```

**Advanced: compare two implementations**

```
>>> fn slow_sum(n: int) -> int {
...2   let s = 0
...3   for i in range(n) { s += i }
...4   return s
...5 }

>>> fn fast_sum(n: int) -> int {
...2   return n * (n - 1) / 2
...3 }

>>> .bench slow_sum(1000)
    mean  1.2ms

>>> .bench fast_sum(1000)
    mean  0.03ms
```

---

## 14. Bytecode Inspection

**Basic idea:** InScript has a bytecode compiler (Phase 6). These commands let you see what bytecode the compiler produces. Useful for learning and for debugging performance.

### `.bytecode [expr]` — compact bytecode

Shows a compact listing of opcodes:

```
>>> .bytecode 1 + 2 * 3
=== fn <main> ===
  LOAD_INT  1
  LOAD_INT  2
  LOAD_INT  3
  MUL
  ADD
  RETURN
```

Notice `MUL` comes before `ADD` — the compiler correctly applies `*` before `+`.

### `.asm [expr]` — full annotated assembly

Shows the full register-level assembly with instruction numbers, register slots, and constants:

```
>>> .asm 1 + 2 * 3
=== fn <main> ===
  Code (6 instrs, 5 locals):
       0  LOAD_INT                    1      1      0  ; 1
       1  LOAD_INT                    3      2      0  ; 2
       2  LOAD_INT                    4      3      0  ; 3
       3  MUL                         2      3      4
       4  ADD                         0      1      2
       5  RETURN                  65535      0      0
```

**Advanced: inspect a function's compiled form**

```
>>> fn factorial(n: int) -> int {
...2   if n <= 1 { return 1 }
...3   return n * factorial(n - 1)
...4 }
>>> .asm factorial(5)
```

This shows exactly how the recursion is compiled — registers allocated, the conditional jump, the recursive call opcode.

---

## 15. VM Mode

**Basic idea:** InScript has two execution engines — the tree-walk **interpreter** (default) and the register-based **bytecode VM**. Toggle between them with `.vm`.

```
>>> .vm
  Execution mode: VM (bytecode)

>>> .vm
  Execution mode: Interpreter (tree-walk)
```

When VM mode is active, the prompt shows `[VM]`:

```
>>> [VM] let x = 10
>>> [VM] x * 2
  → 20
```

**State persists across the toggle.** Variables defined in interpreter mode are available in VM mode and vice versa.

**Why use VM mode?**

The VM mode is the future direction of InScript. Use it to:
- Test that your code works the same way in both engines
- Inspect bytecode output with `.asm` for code you are running in VM
- Develop a feel for how the compiler works

```
>>> .vm
>>> fn fib(n: int) -> int {
...2   if n <= 1 { return n }
...3   return fib(n-1) + fib(n-2)
...4 }
>>> fib(10)
  → 55
>>> .asm fib(10)
```

---

## 16. Session Management

**Basic idea:** Save your session to a file, load files to run them, and export a session as a Markdown report.

### `.save <file>` — save session as runnable code

Saves every statement from the session as a `.ins` file you can run later:

```
>>> let x = 10
>>> fn double(n) { return n * 2 }
>>> .save my_session.ins
  Session saved to my_session.ins
```

The saved file contains:

```inscript
let x = 10
fn double(n) { return n * 2 }
```

### `.load <file>` / `.run <file>` — run a file

Load and execute a `.ins` file as if you had typed it in:

```
>>> .load my_session.ins
>>> .run examples/pong.ins
```

After loading, all definitions from the file are available in the REPL.

### `.export [file]` — export session as Markdown

Exports the session as an annotated Markdown document, useful for sharing or documentation:

```
>>> .export
```

Prints the Markdown to the screen. To save it to a file:

```
>>> .export session_notes.md
  Exported to session_notes.md
```

The Markdown file includes each command you ran with its output, formatted as code blocks.

### `.clear` — reset variables, keep history

Clears all user-defined variables and functions. History and REPL settings are kept.

```
>>> let x = 10
>>> .clear
  Session cleared.
>>> x
  ✗ Undefined variable 'x'
```

### `.reset` — full reset

Clears everything — variables, functions, history, interpreter state — as if you just started the REPL.

```
>>> .reset
  REPL reset.
```

---

## 17. Tab Completion

Press **Tab** to auto-complete:

- **Dot commands:** type `.` then Tab to see all commands; type `.h` then Tab to complete to `.help`
- **Variable names:** type the start of a name then Tab
- **Method access:** type `myobj.` then Tab to see available methods and fields

```
>>> .h[Tab]
  .help   .history

>>> let person = {name: "Alice"}
>>> person.[Tab]
  (shows available dict methods)
```

---

## 18. The Web Playground

**Basic idea:** A browser-based version of the REPL, useful when you want a graphical interface or want to share InScript with someone who does not have Python installed locally.

```bash
python repl.py --web
```

Opens at `http://localhost:8080` in your browser.

Features:
- Full InScript editor with syntax highlighting
- Run button (or `Ctrl+Enter`) to execute
- VM / Interpreter toggle switch
- 8 built-in example programs to load and run
- Tab key inserts 2 spaces (not a tab character)
- Output appears in the panel below the editor

The 8 built-in examples cover: hello world, fibonacci, structs, closures, generators, error handling, imports, and pattern matching.

The web playground uses the same interpreter as the terminal REPL — all language features work identically.

---

## 19. Practical Workflows

### Workflow 1: Explore an idea quickly

Start the REPL and try things without planning a file structure:

```
>>> import "math" as M

>>> fn circle_area(r: float) -> float {
...2   return M.PI * r * r
...3 }

>>> circle_area(5.0)
  → 78.53981633974483

>>> circle_area(10.0)
  → 314.1592653589793

>>> // happy with this? save it.
>>> .save geometry.ins
```

---

### Workflow 2: Incremental struct development

Build a struct step by step, testing each method as you add it:

```
>>> struct Stack {
...2   items: array
...3   fn push(val) { items = items ++ [val] }
...4   fn pop() { let v = last(items); items = items[:len(items)-1]; return v }
...5   fn peek() { return last(items) }
...6   fn is_empty() -> bool { return len(items) == 0 }
...7 }

>>> let s = Stack{items: []}
>>> s.is_empty()
  → true

>>> s.push(10)
>>> s.push(20)
>>> s.push(30)
>>> s.peek()
  → 30

>>> s.pop()
  → 30
>>> s.pop()
  → 20
```

---

### Workflow 3: Load a file and poke at its internals

```
>>> .load my_game.ins
>>> .vars
>>> .fns
>>> // test a specific function with edge cases:
>>> handle_collision(player, wall, 0.0)
>>> handle_collision(player, wall, 90.0)
```

---

### Workflow 4: Compare two implementations

```
>>> fn naive_fib(n: int) -> int {
...2   if n <= 1 { return n }
...3   return naive_fib(n-1) + naive_fib(n-2)
...4 }

>>> fn fast_fib(n: int) -> int {
...2   let a = 0; let b = 1
...3   for i in range(n) { let t = a + b; a = b; b = t }
...4   return a
...5 }

>>> .bench naive_fib(20)
    mean  48ms

>>> .bench fast_fib(20)
    mean  0.04ms
```

---

### Workflow 5: Use the REPL as a calculator

```
>>> import "math" as M

>>> // Area of a sphere radius 7
>>> 4.0 * M.PI * 7.0 ** 2
  → 615.7521601035994

>>> // Convert 98.6°F to Celsius
>>> (98.6 - 32.0) * 5.0 / 9.0
  → 37.0

>>> // Bits in a 32-bit value
>>> 2 ** 32
  → 4294967296

>>> // Bitwise AND mask
>>> 0b11001100 & 0b10101010
  → 136

>>> // Hex to int
>>> 0xFF
  → 255
```

---

### Workflow 6: Multiline with backslash for long expressions

When an expression is very long, break it across lines with `\`:

```
>>> let result = filter([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], \
...2               fn(x) { return x % 2 == 0 })
>>> result
  → [2, 4, 6, 8, 10]
```

```
>>> let total = 100 + 200 + 300 + \
...2            400 + 500
>>> total
  → 1500
```

---

### Workflow 7: Inspect bytecode to understand operator precedence

```
>>> .asm 2 + 3 * 4 - 1
```

Read the opcode order — `MUL` before `ADD` confirms `*` binds tighter than `+`.

```
>>> .asm -2 ** 2
```

Confirm that `-2 ** 2` equals `-4` (unary minus applied after exponentiation).

---

## 20. Known Limitations

These are known issues in v1.0.2. Workarounds are provided where they exist.

| Limitation | Workaround |
|-----------|------------|
| **`async/await` is not real** | `async fn` parses and runs but is synchronous. No event loop exists yet. |
| **F-strings cannot contain string literals** | `f"{x > 0 ? \"yes\" : \"no\"}"` fails. Use a variable: `let msg = x > 0 ? "yes" : "no"; f"{msg}"` |
| **Static struct fields do not parse** | `static PI: float = 3.14` inside a struct body raises ParseError. Only `static fn` works. |
| **Missing struct fields become nil silently** | `Point{x: 1.0}` with `y` omitted gives `p.y == nil` with no warning. |
| **Math INF/NAN crash when printed** | `import "math" as M; print(M.INF)` crashes. Use `is_inf(x)` / `is_nan(x)` for comparisons instead. |
| **Regex argument order is inverted** | `R.match("hello", "h.*o")` fails. Correct: `R.match("h.*o", "hello")` — pattern first, text second. |
| **Events module callbacks crash** | `E.on("event", fn(x){})` crashes when the event fires. Avoid the events module for now. |
| **Generators only work in `for` loops** | `let g = counter(); g()` fails. Use `for v in counter() {}`. |
| **`.vars` includes all builtins** | You cannot currently filter `.vars` to show only user-defined variables. Use `.fns` for functions and `.types` for structs. |

---

*Tutorial covers InScript v1.0.2 — REPL as implemented in `repl.py`.*  
*For the full language reference, see the InScript Language Guide.*  
*For known bugs and design issues, see `InScript_Language_Audit.md`.*
