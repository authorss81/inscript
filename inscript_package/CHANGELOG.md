# InScript Changelog

All notable changes are documented here. Follows [Semantic Versioning](https://semver.org/).

---

## [1.0.0] — 2026-03-04

**First stable release.** The language, standard library, LSP server, and package manager are all considered production-ready.

### Language Features
- `let` / `const` with full type annotation and inference
- Functions with closures, lambdas `|x| x*2`, default parameters, variadic args
- **Generic functions** `fn id<T>(x: T) -> T`
- Structs with methods, inheritance (`extends`), mixins, properties, static methods
- **Abstract methods** (`abstract fn`) — enforced at struct instantiation
- Operator overloading (`fn +()`, `fn ==()`, etc.)
- **Generic structs** `struct Stack<T>` with multi-parameter support
- **ADT Enums** with data fields `Circle(radius: float)`
- Pattern matching with guards `case v if v < 10`
- Destructuring: `let [a, b] = arr` / `let (x, y) = pair`
- Array comprehensions `[x*x for x in 0..10]`
- Coroutines / generators `fn*` + `yield` + `.next()`
- Async / await syntax
- **Decorators** `@name`
- Error propagation `?` with `Ok(v)` / `Err(e)` / `Result`
- Comptime evaluation `const N = comptime { 1024 * 4 }`
- Interfaces / Traits with `implements` checking

### Operators & Expressions
- Ternary `cond ? then : else` and `if cond then x else y`
- Null coalescing `??` and optional chaining `?.`
- Pipe operator `|>` (chainable)
- Floor division `//`
- Array spread `[1, ...other, 4]`
- String indexing `s[0]` and slicing `s[1..4]`
- F-string brace escapes `f"Use {{braces}}"`
- String repeat `"ha" * 3`
- Labeled `break outer` / `continue outer`

### Control Flow
- `for v in range`, `for v in array`, `for v in MyEnum`
- `while`, `if/else if/else`, `match`
- Multi-catch: `try {} catch(e: TypeError) {} catch e {}`
- `select` statement for multi-channel concurrency

### Standard Library (18 modules)
`math`, `string`, `array`, `io`, `json`, `random`, `time`, `color`, `tween`, `grid`, `events`, `debug`, `http`, `path`, `regex`, `csv`, `uuid`, `crypto`

### Tooling
- **LSP server** — real-time diagnostics, completions, hover docs (requires `pip install pygls`)
- **Package manager** — `--install`, `--remove`, `--search`, `--info`, `--packages`
- **Enhanced REPL** — `.type`, `.modules`, `.packages`, `.time`, `.save`, `.load`, tab completion, persistent history
- **VS Code extension** — syntax highlighting, snippets, LSP integration

### Test Suite
331 tests across 6 suites, all passing.

---

## [0.11.0] — Pre-release

- Implemented `select` statement, channel `.send()` / `.recv()` methods
- Added `make_channel()` builtin with `queue.SimpleQueue` backing
- Fixed keyword attribute access (`regex.match`, `uuid.nil`)
- REPL: added `.type`, `.modules`, `.packages` commands

## [0.10.0] — Pre-release

- Added 5 new stdlib modules: `path`, `regex`, `csv`, `uuid`, `crypto`
- Added `http` module
- Improved error messages throughout

## [0.9.0] — Pre-release (v1.1 language polish)

- String indexing `s[0]`, `s[-1]`
- Floor division `//` (with comment disambiguation)
- F-string brace escapes `{{ }}` via sentinel encoding
- Enum iteration `for v in MyEnum`
- Array spread `[...arr]`
- Multi-catch blocks with type matching
- Decorator syntax `@name`
- Abstract methods with inheritance validation

## [0.6.0–0.8.0] — Pre-release

- Full type system: generics, interfaces, mixins, properties
- Pattern matching with guards and ADT destructuring
- Coroutines, async/await, pipe operator
- Built-in game types: Vec2, Vec3, Color, Rect
- Full standard library (first 13 modules)
- VS Code extension (syntax highlighting + snippets)
- REPL with tab completion and session history
