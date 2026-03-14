# InScript REPL — Complete Tutorial

> **Version:** 1.0.5  
> **Start the REPL:** `python inscript.py --repl`  
> **Quick help in REPL:** `.help`  `.modules`  `.doc <module>`

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
10. [Dot Commands — Overview](#10-dot-commands-overview)
11. [Inspecting Your Session](#11-inspecting-your-session)
12. [Timing and Benchmarking](#12-timing-and-benchmarking)
13. [Session Management](#13-session-management)
14. [Stdlib Reference — All 59 Modules](#14-stdlib-reference)
    - [Core](#141-core-modules) · [Data](#142-data-modules) · [Format/Iter](#143-formatiter-modules)
    - [Net/Crypto](#144-netcrypto-modules) · [FS/Process](#145-fsprocess-modules) · [Date/Collections](#146-datecollections-modules)
    - [Threading/Bench](#147-threadingbench-modules) · [Game Visual](#148-game-visual-modules) · [Game IO](#149-game-io-modules)
    - [Game World](#1410-game-world-modules) · [Game Systems](#1411-game-systems-modules) · [Utilities](#1412-utility-modules)
15. [Known Limitations](#15-known-limitations)

---

## 1. What is the REPL?

**REPL** = **Read → Evaluate → Print → Loop**. Type InScript, press Enter, see the result immediately — no files, no compile step.

```
>>> 2 ** 10
  → 1024
>>> let name = "world"
>>> print(f"Hello {name}!")
Hello world!
```

Everything you define persists until you type `exit` or `.reset`.

---

## 2. Starting the REPL

```bash
python inscript.py --repl        # standard
python repl.py                   # direct
python inscript.py --repl --vm   # start in VM mode
```

You will see the pixel-art InScript banner, then the `>>>` prompt.

To exit: type `exit`, `quit`, or press **Ctrl+C**.

---

## 3. Auto-Print

Bare expressions automatically print their value — no need for `print()`:

```
>>> 2 + 2
  → 4
>>> "hello".upper()
  → HELLO
>>> [1,2,3].map(fn(x){return x*2})
  → [2, 4, 6]
```

Statements (assignments, `if`, `for`) do not auto-print.

---

## 4. Variables and Persistent State

All variables persist across lines:

```
>>> let x = 10
>>> let y = 20
>>> x + y
  → 30
>>> x = 99          ← reassignment (use let for first declaration)
>>> x
  → 99
```

Use `const` for constants that cannot be reassigned:
```
>>> const MAX = 100
>>> MAX = 200        ← error: cannot reassign const
```

---

## 5. Multiline Input

Open a `{` and press Enter — the REPL waits for you to close it:

```
>>> fn double(x) {
...   return x * 2
... }
>>> double(21)
  → 42
```

End any line with `\` to force continuation:
```
>>> let result = 1 + \
...              2 + \
...              3
>>> result
  → 6
```

---

## 6. Functions

```
>>> fn greet(name: string, greeting: string = "Hello") {
...   print(f"{greeting}, {name}!")
... }
>>> greet("Alice")
Hello, Alice!
>>> greet("Bob", greeting: "Hi")
Hi, Bob!
```

Lambdas:
```
>>> let square = fn(x) { return x * x }
>>> [1,2,3,4,5].map(square)
  → [1, 4, 9, 16, 25]
```

Generators:
```
>>> fn* range_gen(n) { let i=0; while i<n { yield i; i+=1 } }
>>> for v in range_gen(4) { print(v) }
0
1
2
3
```

---

## 7. Structs and Enums

```
>>> struct Player {
...   name: string
...   health: int = 100
...   pub score: int = 0
... }
>>> let p = Player { name: "Hero" }
>>> p.health
  → 100
>>> p.copy()        ← built-in: returns an isolated copy
>>> p.to_dict()     ← built-in: returns field dict
>>> p.has("name")   ← built-in: checks if field exists
```

Generics (type params are annotations only, not enforced at runtime):
```
>>> struct Stack<T> { items: [] }
>>> let s = Stack { items: [1,2,3] }
>>> s.items.push(4)
>>> s.items
  → [1, 2, 3, 4]
```

Enums:
```
>>> enum Dir { North South East West }
>>> let d = Dir.North
>>> match d {
...   case Dir.North { print("going north") }
...   case _         { print("other") }
... }
going north
```

---

## 8. Error Handling

```
>>> try {
...   throw "something went wrong"
... } catch e {
...   print("caught: " + e)
... }
caught: something went wrong
```

Typed catch:
```
>>> try { throw 42 }
... catch e: string { print("string error") }
... catch e         { print("other error:", e) }
other error: 42
```

Assert and panic:
```
>>> assert(1 == 1, "math is broken")    ← passes silently
>>> assert(false, "boom")               ← throws AssertionError
>>> panic("fatal error")                ← unconditional throw
```

Result types:
```
>>> fn divide(a: float, b: float) {
...   if b == 0.0 { return Err("division by zero") }
...   return Ok(a / b)
... }
>>> let r = divide(10.0, 2.0)
>>> r?   ← unwrap or propagate
  → 5.0
```

---

## 9. Imports and the Standard Library

```
>>> import "math" as M         ← preferred: gives module a namespace
>>> M.sqrt(16.0)
  → 4.0

>>> from "string" import upper, trim    ← import specific names
>>> upper("hello")
  → HELLO

>>> import "random"            ← unqualified: dumps all exports into scope
                               ← Warning: may shadow existing names
```

Quick help:
```
>>> .modules          ← shows all 59 modules in categories
>>> .doc math         ← lists everything math exports
>>> .doc vec          ← lists vec module exports
```

---

## 10. Dot Commands — Overview

| Command | Description |
|---------|-------------|
| `.help` | Full coloured help |
| `.vars` | All defined variables |
| `.fns` | All defined functions |
| `.types` | All struct/enum types |
| `.modules` | All 59 stdlib modules by category |
| `.doc <mod>` | Module export list |
| `.clear` | Reset session variables |
| `.reset` | Full reset (interpreter + history) |
| `.vm` | Toggle VM / interpreter mode |
| `.time <expr>` | Measure execution time |
| `.bench <expr>` | Statistical benchmark (100 runs) |
| `.bytecode` | Show bytecode for last expression |
| `.history [n]` | Show last n commands |
| `.save <file>` | Save session to .ins file |
| `.load <file>` | Load and run a .ins file |

---

## 11. Inspecting Your Session

```
>>> let x = 42
>>> let name = "Alice"
>>> fn add(a,b) { return a+b }
>>> .vars
  x     → 42
  name  → "Alice"

>>> .fns
  add(a, b)

>>> .type x
  int

>>> .inspect [1,"two",3.0]
  Array[3]:
    [0] int    → 1
    [1] string → "two"
    [2] float  → 3.0
```

---

## 12. Timing and Benchmarking

```
>>> .time import "math" as M; M.fib(20)
  10 runs · avg 0.21ms · min 0.19ms · max 0.26ms

>>> .bench let a=[]; for i in 0..1000 { a.push(i) }
  100 runs · avg 1.4ms · p95 1.8ms · p99 2.1ms
```

---

## 13. Session Management

```
>>> .save my_session         ← saves to my_session.ins
>>> .load my_session.ins     ← loads and runs the file
>>> .export report.md        ← exports session as Markdown
>>> .history 10              ← show last 10 commands
>>> !!                       ← repeat last command
```

---

## 14. Stdlib Reference

Use `.doc <module>` in the REPL for the live export list. The examples below show the most common usage patterns.

---

### 14.1 Core Modules

#### `math` — Mathematics
```
>>> import "math" as M
>>> M.sqrt(2.0)           → 1.4142...
>>> M.sin(M.PI / 2.0)     → 1.0
>>> M.floor(3.7)          → 3
>>> M.log2(1024.0)        → 10.0
>>> M.clamp(15.0, 0.0, 10.0) → 10.0
>>> M.INF                 → Infinity
>>> M.PI                  → 3.14159...
```
Key exports: `sin cos tan asin acos atan atan2 sqrt log log2 exp abs floor ceil round pow clamp lerp PI E TAU INF NAN`

---

#### `string` — String utilities
```
>>> import "string" as S
>>> S.upper("hello")       → "HELLO"
>>> S.trim("  hi  ")       → "hi"
>>> S.split("a,b,c", ",")  → ["a","b","c"]
>>> S.join(["x","y"], "-") → "x-y"
>>> S.repeat("ab", 3)      → "ababab"
>>> S.starts_with("hello", "he") → true
>>> S.replace("foo bar", "bar", "baz") → "foo baz"
>>> S.pad_left("42", 6, "0")     → "000042"
```

---

#### `array` — Array utilities
```
>>> import "array" as A
>>> A.chunk([1,2,3,4,5], 2)      → [[1,2],[3,4],[5]]
>>> A.zip([1,2,3], ["a","b","c"]) → [[1,"a"],[2,"b"],[3,"c"]]
>>> A.flatten([[1,2],[3,4]])      → [1,2,3,4]
>>> A.unique([1,2,2,3,1])        → [1,2,3]
>>> A.shuffle([1,2,3,4,5])       → (shuffled copy)
>>> A.binary_search([1,2,3,4,5], 3) → 2
>>> A.average([1.0, 2.0, 3.0])   → 2.0
>>> A.count([1,2,1,3,1], 1)      → 3
```

---

#### `json` — JSON encode/decode
```
>>> import "json" as J
>>> let s = J.encode({"name": "Alice", "score": 42})
>>> s
  → '{"name": "Alice", "score": 42}'
>>> J.decode(s)
  → {"name": "Alice", "score": 42}
>>> J.encode([1, true, nil])
  → '[1, true, null]'
```

---

#### `io` — File and console I/O
```
>>> import "io" as IO
>>> IO.write_file("hello.txt", "Hello, world!")
>>> IO.read_file("hello.txt")
  → "Hello, world!"
>>> IO.file_exists("hello.txt")  → true
>>> IO.read_lines("hello.txt")   → ["Hello, world!"]
>>> IO.list_dir(".")             → ["hello.txt", ...]
>>> let name = IO.input("Your name: ")
```

---

#### `random` — Random numbers
```
>>> import "random" as R
>>> R.int(1, 6)            → (dice roll 1–6)
>>> R.float(0.0, 1.0)      → 0.7342...
>>> R.choice(["a","b","c"]) → "b"
>>> R.choices([1,2,3,4,5], 3) → [3,1,5]
>>> R.shuffle_in_place([1,2,3,4,5])
>>> R.gaussian(0.0, 1.0)   → -0.23...
>>> R.bool()               → true/false
>>> R.direction()          → random unit Vec2
```

---

#### `time` — Timing
```
>>> import "time" as T
>>> T.now()          → 1710000000.0  (Unix timestamp)
>>> T.sleep(0.1)     → (waits 100ms)
>>> T.reset()        → resets internal stopwatch
>>> T.elapsed()      → seconds since last reset
>>> T.fps()          → frames per second (game loop)
```

---

#### `debug` — Debug utilities
```
>>> import "debug" as D
>>> D.log("player spawned", {x: 10, y: 20})
>>> D.assert(1 == 1, "math failed")
>>> D.assert_eq(2 + 2, 4)
>>> D.inspect({"a": [1,2,3]})   ← deep pretty-print
>>> D.print_type(42)             → "int"
>>> D.stats([1,2,3,4,5])         → {min, max, mean, std}
```

---

### 14.2 Data Modules

#### `csv` — CSV files
```
>>> import "csv" as CSV
>>> let data = CSV.parse("name,age\nAlice,30\nBob,25")
>>> data["headers"]   → ["name", "age"]
>>> data["rows"][0]   → {"name": "Alice", "age": "30"}
>>> CSV.write_file("out.csv", CSV.from_dicts([{"x":1,"y":2}]))
```

---

#### `regex` — Regular expressions
```
>>> import "regex" as R
>>> R.test("hello@world.com", R.EMAIL)  → true
>>> R.match("hello123", R.WORD)
  → {"matched": true, "value": "hello123", ...}
>>> R.find_all("one 1 two 2 three 3", R.DIGITS)
  → ["1", "2", "3"]
>>> R.replace("foo_bar_baz", "_", "-")
  → "foo-bar-baz"
```
Built-in patterns: `EMAIL URL WORD DIGITS WHITESPACE`

---

#### `xml` — XML parsing
```
>>> import "xml" as X
>>> let doc = X.parse("<root><item id='1'>hello</item></root>")
>>> X.find(doc, "item")
>>> X.get_attr(doc, "id")
>>> X.children(doc)
```

---

#### `toml` — TOML config files
```
>>> import "toml" as T
>>> let cfg = T.parse_file("config.toml")
>>> T.get(cfg, "server.port")   → 8080
>>> T.to_string({"name": "app", "version": "1.0"})
```

---

#### `yaml` — YAML files
```
>>> import "yaml" as Y
>>> let data = Y.parse("name: Alice\nage: 30")
>>> data["name"]   → "Alice"
>>> Y.to_string({"x": 1, "y": 2})
```

---

#### `url` — URL parsing/building
```
>>> import "url" as U
>>> U.encode("hello world!")        → "hello%20world%21"
>>> U.build("https://example.com", {"q": "inscript", "page": "1"})
  → "https://example.com?q=inscript&page=1"
>>> U.get_host("https://example.com/path")  → "example.com"
>>> U.get_path("https://example.com/a/b")   → "/a/b"
```

---

#### `base64` — Base64 encoding
```
>>> import "base64" as B
>>> B.encode("Hello, world!")   → "SGVsbG8sIHdvcmxkIQ=="
>>> B.decode("SGVsbG8sIHdvcmxkIQ==")  → "Hello, world!"
>>> B.encode_url("Hello+World")  → URL-safe variant
```

---

#### `uuid` — Unique IDs
```
>>> import "uuid" as U
>>> U.v4()     → "f47ac10b-58cc-4372-a567-0e02b2c3d479"
>>> U.short()  → "f47ac10b"  (first 8 chars)
>>> U.is_valid("f47ac10b-58cc-4372-a567-0e02b2c3d479")  → true
```

---

### 14.3 Format/Iter Modules

#### `format` — String formatting utilities
```
>>> import "format" as F
>>> F.number(1234567.89, ",")      → "1,234,567.89"
>>> F.file_size(1048576)           → "1.0 MB"
>>> F.duration(3661)               → "1h 1m 1s"
>>> F.hex(255)                     → "0xff"
>>> F.bin(42)                      → "0b101010"
>>> F.indent("line1\nline2", 4)    → "    line1\n    line2"
>>> F.camel_case("hello_world")    → "helloWorld"
>>> F.pad_table([["a","b"],["cc","dd"]], [8,8])
```

---

#### `iter` — Functional iteration
```
>>> import "iter" as I
>>> I.map([1,2,3,4,5], fn(x){return x*x})
  → [1, 4, 9, 16, 25]
>>> I.filter([1,2,3,4,5], fn(x){return x%2==0})
  → [2, 4]
>>> I.reduce([1,2,3,4,5], 0, fn(acc,x){return acc+x})
  → 15
>>> I.zip([1,2,3], ["a","b","c"])
  → [[1,"a"],[2,"b"],[3,"c"]]
>>> I.flat_map([[1,2],[3,4]], fn(x){return x})
  → [1,2,3,4]
>>> I.take([1,2,3,4,5], 3)     → [1,2,3]
>>> I.skip([1,2,3,4,5], 2)     → [3,4,5]
>>> I.enumerate(["a","b","c"])  → [[0,"a"],[1,"b"],[2,"c"]]
>>> I.group_by([1,2,3,4,6], fn(x){return x%2==0 ? "even" : "odd"})
  → {"odd":[1,3],"even":[2,4,6]}
>>> I.count_by(["a","b","a","c","b","a"], fn(x){return x})
  → {"a":3,"b":2,"c":1}
```

---

#### `template` — String templates
```
>>> import "template" as T
>>> let tmpl = T.compile("Hello {{name}}, you have {{count}} messages.")
>>> T.render(tmpl, {"name": "Alice", "count": 3})
  → "Hello Alice, you have 3 messages."
>>> T.render_str("Score: {{score}}", {"score": 42})
  → "Score: 42"
```

---

#### `argparse` — CLI argument parsing
```
>>> import "argparse" as A
>>> A.option("--name", "Your name", "World")
>>> A.flag("--verbose", "Enable verbose output")
>>> A.positional("file", "Input file")
>>> let args = A.parse()
>>> args["name"]
```

---

### 14.4 Net/Crypto Modules

#### `http` — HTTP requests
```
>>> import "http" as H
>>> let resp = H.get("https://httpbin.org/json")
>>> resp["status"]    → 200
>>> resp["body"]      → "{...}"
>>> H.post("https://example.com/api", {"key": "value"})
```
*Note: requires network access; disabled in sandbox environments.*

---

#### `ssl` — HTTPS / TLS
```
>>> import "ssl" as S
>>> let html = S.https_get("https://example.com")
>>> let ctx = S.create_context()
```

---

#### `crypto` — Cryptography
```
>>> import "crypto" as C
>>> C.sha256("hello")
  → "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
>>> C.md5("hello")        → "5d41402abc4b2a76b9719d911017c592"
>>> C.hmac_sign("secret", "message")
>>> C.random_bytes(16)    → [...16 random bytes...]
>>> C.b64_encode("data")  → base64 string
```

---

#### `hash` — Hashing algorithms
```
>>> import "hash" as H
>>> H.blake3("hello")
>>> H.adler32("hello")   → checksum int
>>> H.algorithms()       → list of available algorithms
>>> H.compare(h1, h2)    → constant-time comparison
```

---

#### `net` — TCP/UDP networking
```
>>> import "net" as N
>>> N.local_ip()          → "192.168.1.100"
>>> N.hostname()          → "my-machine"
>>> N.is_port_open("localhost", 8080)  → true/false
>>> let server = N.TcpServer(8080)
>>> let client = N.TcpClient("localhost", 8080)
```

---

### 14.5 FS/Process Modules

#### `path` — File path utilities
```
>>> import "path" as P
>>> P.join("src", "utils", "main.ins")  → "src/utils/main.ins"
>>> P.basename("src/main.ins")          → "main.ins"
>>> P.dirname("src/utils/main.ins")     → "src/utils"
>>> P.ext("main.ins")                   → ".ins"
>>> P.exists("main.ins")               → true/false
>>> P.glob("src/*.ins")                → ["src/main.ins", ...]
>>> P.home()                           → "/home/user"
>>> P.cwd()                            → current directory
```

---

#### `fs` — File system operations
```
>>> import "fs" as FS
>>> FS.read("hello.txt")
>>> FS.write("out.txt", "content")
>>> FS.append("log.txt", "new line\n")
>>> FS.copy("a.txt", "b.txt")
>>> FS.delete("old.txt")
>>> FS.mkdir("new_dir")
>>> FS.list(".")          → directory listing
>>> FS.glob("**/*.ins")   → recursive glob
```

---

#### `process` — Process and environment
```
>>> import "process" as P
>>> P.platform()          → "windows" / "linux" / "darwin"
>>> P.env("HOME")         → "/home/user"
>>> P.args()              → command line args
>>> P.pid()               → current process ID
>>> P.cwd()               → working directory
>>> P.python_version()    → "3.12.0"
>>> P.exit(0)             → exit with code
```

---

#### `compress` — Compression
```
>>> import "compress" as C
>>> let compressed = C.gzip("lots of repeated text text text")
>>> C.gunzip(compressed)   → original string
>>> C.zip_files("archive.zip", ["a.txt","b.txt"])
>>> C.unzip("archive.zip", "output_dir/")
```

---

#### `log` — Structured logging
```
>>> import "log" as L
>>> L.info("Server started on port 8080")
>>> L.debug("Processing request", {method: "GET", path: "/api"})
>>> L.error("Database connection failed", {retry: 3})
>>> L.set_level("debug")     ← show all levels
>>> L.set_level("error")     ← errors only
>>> L.to_file("app.log")
>>> L.structured(true)       ← JSON output format
```

---

### 14.6 Date/Collections Modules

#### `datetime` — Dates and times
```
>>> import "datetime" as DT
>>> let now = DT.now()
>>> DT.format(now, "%Y-%m-%d")    → "2026-03-14"
>>> DT.format(now, "%H:%M:%S")    → "14:30:00"
>>> let d = DT.date(2026, 3, 14)
>>> DT.add(d, {days: 7})         → date 7 days later
>>> DT.diff_seconds(d1, d2)      → difference in seconds
>>> DT.MONTHS                    → ["January", ...]
>>> DT.WEEKDAYS                  → ["Monday", ...]
```

---

#### `collections` — Data structures
```
>>> import "collections" as C

// Set — unordered unique values
>>> let s = C.Set([1,2,2,3,3])
>>> C.set_size(s)           → 3
>>> C.set_add(s, 4)
>>> C.set_has(s, 2)         → true
>>> C.set_union(s1, s2)     → new Set
>>> C.set_intersect(s1, s2) → new Set
>>> s.to_array()            → [1,2,3,4]

// Queue (FIFO)
>>> let q = C.Queue()
>>> q.enqueue(1); q.enqueue(2)
>>> q.dequeue()    → 1

// Deque (double-ended queue)
>>> let d = C.Deque()
>>> d.push_front(0); d.push_back(3)

// PriorityQueue
>>> let pq = C.PriorityQueue()
>>> pq.push(5, "low"); pq.push(1, "urgent")
>>> pq.pop()    → "urgent"  (lowest priority number first)

// Helpers
>>> C.counter(["a","b","a","c","a"])  → {"a":3,"b":1,"c":1}
>>> C.flatten([[1,2],[3,[4,5]]])      → [1,2,3,4,5]
>>> C.sliding_window([1,2,3,4,5], 3) → [[1,2,3],[2,3,4],[3,4,5]]
```

---

#### `database` — SQLite database
```
>>> import "database" as DB
>>> let db = DB.open("game.db")         ← file-backed
>>> let mem = DB.open_memory()          ← in-memory

// Database object methods:
>>> db.exec("CREATE TABLE scores (name TEXT, value INT)")
>>> db.exec("INSERT INTO scores VALUES (?, ?)", ["Alice", 100])
>>> let rows = db.query("SELECT * FROM scores")
>>> rows     → [{"name": "Alice", "value": 100}]
>>> db.close()
```

---

### 14.7 Threading/Bench Modules

#### `thread` — Multi-threading
```
>>> import "thread" as T
>>> let t = T.spawn(fn() { print("hello from thread") })
>>> T.join_all([t])
>>> T.sleep(0.5)                ← sleep 500ms

// Mutex for shared state
>>> let mu = T.Mutex()
>>> mu.lock(); mu.unlock()
>>> mu.with(fn() { /* critical section */ })

// Channel for communication
>>> let ch = T.Channel()
>>> T.spawn(fn() { ch.send(42) })
>>> ch.recv()    → 42
```
⚠️ InScript closures are not thread-safe. Use Python callables for thread functions.

---

#### `bench` — Benchmarking
```
>>> import "bench" as B
>>> let result = B.time(fn() { return 2**32 })
>>> result["ms"]    → execution time in ms
>>> B.run([
...   B.Case("fib20", fn() { return fib(20) }),
...   B.Case("fib25", fn() { return fib(25) }),
... ])
>>> B.compare(fn_a, fn_b, 100)   ← compare two functions over N runs
```

---

### 14.8 Game Visual Modules

#### `color` — Color operations
```
>>> import "color" as C
>>> let red = C.rgb(1.0, 0.0, 0.0)       ← 0.0-1.0 scale
>>> let blue = C.from_hex("#0000FF")
>>> C.mix(red, blue, 0.5)                ← 50% blend
>>> C.darken(red, 0.2)                   ← 20% darker
>>> C.lighten(blue, 0.3)                 ← 30% lighter
>>> C.to_hex(red)                        → "#FF0000"
>>> C.RED; C.GREEN; C.BLUE               ← named constants
>>> C.BLACK; C.WHITE; C.TRANSPARENT
```

---

#### `tween` — Easing and interpolation
```
>>> import "tween" as T

// 1-arg form: maps t ∈ [0,1] through easing curve
>>> T.linear(0.5)           → 0.5
>>> T.ease_in(0.5)          → 0.25   (quadratic)
>>> T.ease_out(0.5)         → 0.75
>>> T.ease_in_out(0.5)      → 0.5
>>> T.ease_in_bounce(0.8)   → (bouncy value)

// 3-arg form: interpolate from→to over t
>>> T.linear(0.5, 0.0, 100.0)     → 50.0
>>> T.ease_in(0.5, 0.0, 100.0)    → 25.0
>>> T.ease_out_elastic(0.7, 0.0, 1.0)

// Full tween with custom easing:
>>> T.tween(0.0, 100.0, 0.5, T.ease_in_cubic)  → 12.5
```
Available: `linear ease_in ease_out ease_in_out ease_in_quad ease_out_quad ease_in_cubic ease_out_cubic ease_in_sine ease_out_sine ease_in_expo ease_out_expo ease_in_bounce ease_out_bounce ease_in_elastic ease_out_elastic ease_in_back ease_out_back`

---

#### `image` — Image loading and manipulation
```
>>> import "image" as I
>>> let img = I.load("sprite.png")
>>> I.get_pixel(img, 10, 20)       → [r, g, b, a]
>>> let grey = I.grayscale(img)
>>> let flipped = I.flip_h(img)
>>> let cropped = I.crop(img, 0, 0, 64, 64)
>>> I.blit(dest, src, 100, 200)    ← draw src onto dest at (100,200)
```

---

#### `atlas` — Sprite atlases
```
>>> import "atlas" as A
>>> let atlas = A.load("sprites.png", "sprites.json")
>>> let frame = atlas.get("player_walk_1")
>>> let packed = A.pack(["a.png","b.png","c.png"])
```

---

#### `animation` — Sprite animation
```
>>> import "animation" as A
>>> let clip = A.Clip("walk", ["frame1","frame2","frame3"], fps: 12.0, loop: true)
>>> let anim = A.Animator()
>>> anim.add_clip(clip)
>>> anim.play("walk")
>>> anim.update(0.016)   ← delta time in seconds
>>> anim.current_frame() → current frame name
```

---

#### `shader` — Shader effects
```
>>> import "shader" as S
>>> let sh = S.load("blur.glsl")
>>> S.screen_effect(sh, {radius: 2.0})
>>> S.screen_pass(sh)
```
*Note: shader execution requires a pygame/OpenGL window context.*

---

### 14.9 Game IO Modules

#### `input` — Input management
```
>>> import "input" as I
>>> let mgr = I.Manager()
>>> I.map(mgr, "jump", keys: ["space", "up"])
>>> I.map(mgr, "left", keys: ["left", "a"])
>>> I.map(mgr, "right", keys: ["right", "d"])

// Per-frame (call inside game loop):
>>> I.pressed(mgr, "jump")    → true on press frame
>>> I.held(mgr, "left")       → true while held
>>> I.axis(mgr, "horizontal") → -1.0 to 1.0
>>> I.mouse_pos(mgr)          → [x, y]
>>> I.mouse_pressed(mgr, 0)   → left button
```

---

#### `audio` — Sound and music
```
>>> import "audio" as A
>>> let sfx = A.load("explosion.wav")
>>> A.play(sfx)
>>> A.play(sfx, volume: 0.5, loops: 0)
>>> let music = A.Sound("theme.ogg")
>>> A.play_music(music)
>>> A.pause_music()
>>> A.resume_music()
>>> A.fade_out(1000)         ← fade out over 1 second
>>> A.mute(true)
>>> A.ENABLED                → true if pygame.mixer available
```

---

### 14.10 Game World Modules

#### `physics2d` — 2D physics
```
>>> import "physics2d" as P
>>> let world = P.World(gravity: P.Vec2(0.0, 9.8))
>>> let body = P.RigidBody(mass: 1.0, pos: P.Vec2(0.0, 0.0))
>>> let ground = P.StaticBody(shape: P.Rect(0.0, 10.0, 20.0, 1.0))
>>> world.add(body); world.add(ground)
>>> world.step(0.016)            ← advance simulation by 16ms
>>> body.pos                     → Vec2 after physics step
>>> let circle = P.Circle(radius: 0.5, pos: P.Vec2(5.0, 0.0))
>>> let area = P.Area(shape: P.Rect(0.0,0.0,10.0,10.0))
```

---

#### `tilemap` — Tile maps
```
>>> import "tilemap" as T
>>> let map = T.load("level1.tmj")
>>> T.get_tile(map, "ground", 5, 3)    → tile id at (5,3) on "ground" layer
>>> T.get_layer(map, "ground")         → layer data
>>> T.get_objects(map, "enemies")      → list of object dicts
>>> T.draw_layer(map, "ground", camera_x: 0, camera_y: 0)
```

---

#### `camera2d` — 2D camera
```
>>> import "camera2d" as C
>>> let cam = C.Camera2D()
>>> C.set_target(cam, 400.0, 300.0)   ← look at this world point
>>> C.follow(cam, player.x, player.y) ← smooth follow
>>> C.shake(cam, intensity: 8.0, duration: 0.3)
>>> C.update(cam, dt)                 ← call every frame
>>> C.begin(cam)                      ← start camera transform
>>> // draw world objects here
>>> C.end(cam)                        ← restore transform
>>> C.world_to_screen(cam, 100.0, 200.0)  → [sx, sy]
>>> C.bounds(cam)                     → visible world rect
```

---

#### `particle` — Particle systems
```
>>> import "particle" as P
>>> let emitter = P.Emitter(400.0, 300.0)
>>> P.rate(emitter, 30)           ← 30 particles/second
>>> P.lifetime(emitter, 1.5)      ← each lives 1.5s
>>> P.speed(emitter, 80.0)
>>> P.angle(emitter, 45.0)        ← emit direction degrees
>>> P.color_start(emitter, 1.0, 0.5, 0.0, 1.0)   ← orange
>>> P.color_end(emitter, 1.0, 0.0, 0.0, 0.0)     ← red, fade out
>>> P.gravity(emitter, 0.0, 50.0)
>>> P.start(emitter)
>>> P.burst(emitter, 20)          ← instant burst of 20
>>> P.update(emitter, dt)         ← call every frame
>>> P.count(emitter)              → active particle count
```

---

#### `pathfind` — Pathfinding
```
>>> import "pathfind" as PF
>>> let grid = PF.Grid(20, 15)       ← 20×15 tile grid
>>> grid.set_walkable(5, 3, false)   ← block a tile
>>> let path = PF.astar(grid, [0,0], [19,14])
>>> path    → [[0,0],[1,0],[2,1],...]  (list of [x,y] steps)
>>> PF.dijkstra(grid, [0,0])         → distance map
>>> let flow = PF.flow_field(grid, [10,7])
>>> PF.sample_flow(flow, 3, 4)       → direction at (3,4)
```

---

### 14.11 Game Systems Modules

#### `ecs` — Entity Component System
```
>>> import "ecs" as E
>>> let world = E.World()

// Spawn entities with component dicts
>>> let player = E.spawn(world, {pos: [0.0,0.0], vel: [0.0,0.0], health: 100})
>>> let enemy  = E.spawn(world, {pos: [5.0,0.0], vel: [0.0,0.0], ai: "chase"})

// Query entities with specific components
>>> let movers = E.query(world, "pos", "vel")
>>> for eid, comps in movers {
...   comps["pos"][0] += comps["vel"][0]
... }

// Get/set individual components
>>> E.get(world, player, "health")   → 100
>>> E.mark_dead(world, enemy)
>>> E.remove_dead(world)
>>> E.alive_count(world)             → 1
```

---

#### `fsm` — Finite State Machine
```
>>> import "fsm" as F
>>> let ai = F.Machine("idle")
>>> F.add_state(ai, "idle",    on_update: fn(dt){ print("idle") })
>>> F.add_state(ai, "chase",   on_enter: fn(){ print("start chase!") })
>>> F.add_state(ai, "attack",  on_enter: fn(){ print("attacking!") })
>>> F.add_transition(ai, "idle",  "chase",  fn(){ return player_nearby })
>>> F.add_transition(ai, "chase", "attack", fn(){ return player_in_range })
>>> F.update(ai, dt)        ← checks transitions, calls on_update
>>> F.current(ai)           → "idle"
>>> F.in_state(ai, "chase") → false
>>> F.history(ai)           → ["idle"]
```

---

#### `save` — Save game slots
```
>>> import "save" as S
>>> let slot = S.Slot("save1.dat")
>>> slot.set("player_name", "Alice")
>>> slot.set("level", 5)
>>> slot.set("inventory", ["sword", "shield"])
>>> slot.save()
>>> slot.load()
>>> slot.get("level")         → 5
>>> S.list_slots()            → ["save1.dat", ...]
>>> S.copy_slot("save1.dat", "backup.dat")
```

---

#### `localize` — Localization / i18n
```
>>> import "localize" as L
>>> let loc = L.Localizer()
>>> L.load(loc, "en.json")    ← {"greeting": "Hello", "farewell": "Goodbye"}
>>> L.load(loc, "es.json")    ← {"greeting": "Hola", "farewell": "Adiós"}
>>> L.set_language(loc, "es")
>>> L.get(loc, "greeting")    → "Hola"
>>> L.set_fallback(loc, "en") ← use English for missing keys
>>> L.available_languages(loc) → ["en", "es"]
```

---

#### `grid` — 2D grid utilities
```
>>> import "grid" as G
>>> let g = G.Grid(10, 10, default: 0)  ← 10×10 grid filled with 0
>>> g.set(3, 4, 99)
>>> g.get(3, 4)               → 99
>>> G.manhattan([0,0], [3,4]) → 7
>>> G.euclidean([0,0], [3,4]) → 5.0
>>> G.chebyshev([0,0], [3,4]) → 4
>>> G.to_index(g, 3, 4)       → 43  (row-major flat index)
>>> G.from_index(g, 43)       → [3, 4]
```

---

#### `events` — Event bus
```
>>> import "events" as E
>>> E.on("player_died", fn(data){ print("Player died at", data["x"]) })
>>> E.on("level_complete", fn(data){ print("Level", data["level"], "done!") })
>>> E.emit("player_died", {"x": 100, "y": 200})
Player died at 100
>>> E.once("game_start", fn(){ print("Started!") })  ← fires once only
>>> E.off("player_died")     ← remove all listeners for event
>>> E.clear()                ← remove all listeners
```

---

#### `net_game` — Multiplayer networking
```
>>> import "net_game" as N
>>> let server = N.GameServer(port: 7777)
>>> let client = N.GameClient()
>>> client.connect("localhost", 7777)
>>> client.send(N.pack({"type": "move", "x": 100, "y": 200}))
>>> let msg = N.unpack(client.recv())
>>> msg["type"]    → "move"
```

---

### 14.12 Utility Modules

#### `signal` — Typed pub/sub signals
```
>>> import "signal" as S

// Signals are typed event channels you attach to objects
>>> let on_hit    = S.Signal("on_hit")
>>> let on_death  = S.Signal("on_death")

>>> S.connect(on_hit, fn(damage){ print("Hit for", damage) })
>>> S.once(on_death, fn(){ print("Died!") })   ← fires once only

>>> S.emit(on_hit, 25)
Hit for 25
>>> S.emit(on_death)
Died!
>>> S.emit(on_death)     ← once listener already removed

>>> S.listener_count(on_hit)  → 1
>>> S.disconnect(on_hit, my_fn)
>>> S.clear(on_hit)
```

---

#### `vec` — 2D/3D vector math
```
>>> import "vec" as V

// Create vectors (plain arrays [x,y] or [x,y,z])
>>> let a = V.v2(3.0, 4.0)
>>> let b = V.v2(1.0, 0.0)
>>> V.len(a)               → 5.0
>>> V.norm(a)              → [0.6, 0.8]
>>> V.add(a, b)            → [4.0, 4.0]
>>> V.sub(a, b)            → [2.0, 4.0]
>>> V.scale(a, 2.0)        → [6.0, 8.0]
>>> V.dot(a, b)            → 3.0
>>> V.dist(a, b)           → 4.472...
>>> V.lerp(a, b, 0.5)      → [2.0, 2.0]
>>> V.angle(b)             → 0.0  (radians)
>>> V.from_angle(1.57)     → [0.0, 1.0]  (approx)
>>> V.perp(b)              → [0.0, 1.0]  (rotate 90°)
>>> V.reflect(a, V.up())   → reflection vector

// 3D
>>> let c = V.v3(1.0, 0.0, 0.0)
>>> let d = V.v3(0.0, 1.0, 0.0)
>>> V.cross(c, d)           → [0.0, 0.0, 1.0]

// Direction constants
>>> V.up()    → [0.0, -1.0]
>>> V.down()  → [0.0, 1.0]
>>> V.left()  → [-1.0, 0.0]
>>> V.right() → [1.0, 0.0]
>>> V.zero2() → [0.0, 0.0]
>>> V.forward() → [0.0, 0.0, -1.0]
```

---

#### `pool` — Object pool (game performance)
```
>>> import "pool" as P

// Pre-allocate bullet objects, reuse without GC pressure
>>> let bullets = P.Pool(
...   fn() { return {x:0.0, y:0.0, active:false} },
...   capacity: 100
... )

>>> let b = P.acquire(bullets)   ← get a bullet from pool
>>> b["x"] = 100.0; b["y"] = 50.0; b["active"] = true

>>> P.release(bullets, b)        ← return bullet to pool
>>> P.release_all(bullets)       ← return all active bullets

>>> P.active_count(bullets)   → 0
>>> P.free_count(bullets)     → 1
>>> P.capacity(bullets)       → 100
```

---

## 15. Known Limitations

- **Performance:** InScript is ~40–130× slower than Python for CPU-intensive code. Game logic that runs once per frame (AI, physics queries) is fine; tight loops over thousands of items each frame are not. This will be addressed in Phase 6.2 (C extension).
- **`async/await`:** Accepted by the parser but executes synchronously. Use `thread` module for real concurrency.
- **Generics:** `struct Stack<T>` accepts type parameters but does not enforce them at runtime. `Stack<int>` and `Stack<string>` are identical.
- **Struct assignment:** `let b = a` creates an alias, not a copy. Use `a.copy()` when you need isolation.
- **VM mode (`.vm`):** The VM and interpreter now produce identical results for most programs. A few edge cases remain. The interpreter is the default and recommended mode.
- **Windows:** Tab-completion and arrow-key history require the `readline` module (not installed by default on Windows). The REPL works fully without it.
- **Shader/Audio/Network:** These modules require pygame and network access. They print stub messages in environments where these are unavailable.
