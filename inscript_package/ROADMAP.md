# InScript Language Roadmap — Detailed

> **Current version:** v1.0.11 (March 2026)
> **Tests:** 836 total (501 regression + 335 comprehensive) — all passing
> **Stdlib:** 59 modules
> **Assessment:** Feature-complete for 2D game scripting. Pre-stable (missing formatter, debugger, docs, PyPI).

---

## ✅ v1.0.x — Feature Complete (DONE)

Everything below is implemented, tested, and working in both interpreter and VM.

### Core Language
- [x] `let` / `const` with type annotations and inference
- [x] All primitive types: `int` `float` `string` `bool` `nil`
- [x] All operators: arithmetic, bitwise, comparison, logical, `in`/`not in`, `|>`, `?:`, `??`, `?.`
- [x] String concat: `+` and `++` (concatenation operator)
- [x] Float division by zero returns `Infinity`; int/0 throws
- [x] Functions with defaults, named args, variadics, closures
- [x] Structs with inheritance, mixins, interfaces, operator overloading
- [x] `priv`/`pub` field access control (enforced at runtime)
- [x] `super` keyword for parent method dispatch
- [x] Static fields and methods on structs
- [x] Generic structs `struct Stack<T>` (syntax only — no runtime enforcement)
- [x] ADT Enums with data fields: `enum Shape { Circle(r: float) }`
- [x] Pattern matching: guards, binding, `as` expression, ADT variants, Ok/Err
- [x] Non-exhaustive match warns in REPL
- [x] Array/tuple/struct destructuring
- [x] Array comprehensions with multi-clause
- [x] Dict comprehensions with multi-var `for k,v in entries(d)`
- [x] Generators: `fn*` / `yield` / `next()` / `.next()` method
- [x] `async fn` (syntactically complete; executes synchronously — warns)
- [x] Decorators `@name` and `@name(args)` (named decorators only, not lambda)
- [x] Error propagation `?` with `Ok` / `Err` / `Result`
- [x] `try { } catch e { }` as expression returning value
- [x] Typed catch: `catch e:int { }`
- [x] `finally` block
- [x] `assert(cond, msg)`, `panic(msg)`, `unreachable(msg)` builtins
- [x] `do-while`, `for-else`, `while-else`
- [x] Multi-variable for: `for k,v in entries(d)`
- [x] Labeled break/continue: `outer: for ... { break outer }`
- [x] Range: `0..5` exclusive, `0..=5` inclusive, `range(start,end,step)`
- [x] F-strings with format specs: `f"{x:.2f}"` `f"{n:06d}"` `f"{s:>10}"`
- [x] F-strings with expressions, ternaries, dict key access

### Type System
- [x] `typeof(v)` returns clean names for all types
- [x] `x is T` type check for primitives, arrays, dicts, structs, inheritance
- [x] Type mismatch at call site warns in REPL (literal args vs annotated params)
- [x] Missing return in typed functions warns in REPL
- [x] Arg-count mismatch warns in REPL
- [x] Duplicate function definition warns in REPL

### Array Methods (40+)
- [x] Core: `push` `pop` `pop_at` `insert` `remove` `contains` `includes` `clear`
- [x] Functional: `map` `filter` `reduce(fn)` `reduce(init,fn)` `find` `each`
- [x] FP extras: `flat_map` `any` `all` `count(fn)` `sum` `min_by` `max_by` `group_by`
- [x] Ordering: `sort(fn?)` `sorted(fn?)` `reverse`
- [x] Slicing: `slice` `take` `skip` `chunk`
- [x] Set-like: `unique`
- [x] Query: `index_of` `first` `last` `is_empty`
- [x] Structural: `flatten` `zip` `flat_map`
- [x] Display: quoted strings in nested position `[1, "two", true]`

### String Methods (30+)
- [x] Case: `upper` `lower` `to_upper` `to_lower`
- [x] Trim: `trim` `trim_start` `trim_end`
- [x] Search: `contains` `starts_with` `ends_with` `index` `count`
- [x] Transform: `replace` `reverse` `repeat` `split(sep, limit?)`
- [x] Pad: `pad_left` `pad_right`
- [x] Extract: `substr` `char_at` `chars`
- [x] Convert: `to_int` `to_float` `to_string`
- [x] Check: `is_empty` `is_alpha` `is_numeric` `is_alnum`
- [x] Format: `format(pos...)` `format(named:...)`
- [x] Negative indexing: `s[-1]` for last char

### Dict Methods (20+)
- [x] `get(k, default)` `set(k,v)` `has(k)` `has_key(k)` `has_value(v)` `remove(k)` `pop(k)`
- [x] `keys()` `values()` `items()` `to_pairs()`
- [x] `merge(other)` `update(other)` `copy()` `clear()` `is_empty()`
- [x] Spread: `{...a, "y":2}` in dict literals
- [x] Display: `{"k": "v"}` double-quote style

### Execution Engines
- [x] Tree-walk interpreter (full feature support)
- [x] Register-based bytecode VM (near-parity with interpreter)
- [x] VM: `match` as expression
- [x] VM: `try { } catch e { }` as expression
- [x] VM: dict comprehension with multi-var
- [x] VM: struct `.copy()` with deep-copy of list/dict fields
- [x] VM: all array/string instance methods via `_list_method`/`_str_method`
- [x] VM: named args in method calls (kwargs dict)
- [x] VM: `in`/`not in` as `CONTAINS`/`NOT_CONTAINS` opcodes
- [x] VM: for-else / while-else / do-while
- [x] VM: source line tracking per instruction (errors show Line N)

### Standard Library (59 modules — all working)
Core, Data, Format/Iter, Net/Crypto, FS/Process, Date/Collections, Threading/Bench,
Game Visual, Game IO, Game World, Game Systems, Utilities — see audit Section VI.

### Tooling
- [x] Enhanced REPL with pixel-art banner, 30+ commands
- [x] `.doc <module>` live documentation for all 59 modules
- [x] Complete REPL tutorial (REPL_Tutorial.md)
- [x] LSP server (pygls-based)
- [x] VS Code extension (syntax highlighting, snippets, LSP)
- [x] Package manager (inscript install/remove/search — stub implementation)
- [x] Bytecode save/load (`.ibc` files)
- [x] 836 tests: 270 Phase 5 + 145 Phase 6 + 32 Phase 7 + 54 Audit + 335 Comprehensive

---

## 📋 v1.1.0 — Developer-Ready Stable (Q2 2026, ~2-3 months)

**Goal:** First release that a developer can use professionally. Focus on tooling, not new language features. **Zero breaking changes.**

### 🔴 Critical (blocks stable label)

#### Formatter — `inscript fmt`
- Token-based formatter (no full AST round-trip required)
- Consistent indentation (2 spaces)
- Consistent spacing around operators
- Max line length 100 (configurable)
- Trailing comma in multi-line arrays/dicts
- `inscript fmt --check` for CI
- Integration in VS Code extension (format on save)
- **Implementation:** ~1 week using existing lexer

#### Package Publication
- `pyproject.toml` with `[project]` metadata
- `pip install inscript` via PyPI (free account)
- Entry point: `inscript` CLI command in PATH
- Version: `inscript --version` outputs `InScript 1.1.0`

#### Documentation Site
- GitHub Pages at `inscript-lang.dev` (or `authorss81.github.io/inscript`)
- Sections: Getting Started, Language Guide, Stdlib Reference, Error Codes
- All `https://docs.inscript.dev/errors/E0XXX` URLs return real content
- Auto-generated stdlib reference from `_MODULES` docstrings

### 🟡 High Priority

#### Debugger (VS Code)
- DAP (Debug Adapter Protocol) server in Python — free spec
- Breakpoints in `.ins` files
- Variable watch panel
- Call stack display
- Step over / step into / step out
- **Implementation:** ~2 weeks using `debugpy` as reference

#### Watch Mode
- `inscript --watch game.ins` reruns on file change
- Uses `watchdog` Python library (free, `pip install watchdog`)
- Clears terminal on rerun
- Shows error location with colored output

#### Web Playground
- Single-page app on GitHub Pages
- Uses Pyodide (Python in WASM) to run InScript in browser
- Code editor: CodeMirror 6 (free, MIT)
- 10 example programs included
- Share button (GitHub Gist API — free)

#### Test Runner
- `inscript test` command runs `test_*.ins` files
- `.ins` test format: `assert(expr, "message")`
- Output: pass/fail count, colored output, timing
- JUnit XML output for CI integration

### 🟢 Nice to Have

- `inscript check` — static analysis without execution
- Source maps for full stack traces in `.ins` files
- REPL multi-line paste mode
- Tree-sitter grammar (for Neovim/Emacs support)
- `inscript doc` — generates HTML from `///` doc comments
- Homebrew formula
- Right-click "Run with InScript" in VS Code

### v1.1.0 — What Does NOT Change
- Language syntax (frozen at v1.0.11)
- Standard library API (no breaking changes)
- VM/interpreter behaviour
- All 836 existing tests must continue to pass

---

## 🔮 v1.2.0 — Type-Safe (Q3 2026)

**Goal:** Add real type system features. May include minor breaking changes (if any, announced 2 releases ahead).

### Type System
- [ ] Union types: `type Shape = Circle | Rectangle`
- [ ] Type aliases: `type ID = int`
- [ ] Generic enforcement: `Stack<int>` rejects non-int values at push time
- [ ] Generic constraints: `fn sort<T: Comparable>(arr: [T]) -> [T]`
- [ ] Type narrowing in match arms
- [ ] Recursive types: linked list, tree nodes
- [ ] Null-safe types: `int?` for nullable integers
- [ ] Type error messages show expected vs actual type

### Analyzer Improvements
- [ ] Type mismatch for non-literal expressions (variables, fn returns)
- [ ] Missing return in all branches (nested if/match fully traversed)
- [ ] Unused variable detection with `--no-warn-unused` flag
- [ ] Dead code after unreachable statement
- [ ] Unreachable match arms

### Language Features
- [ ] `async/await` — either wire to asyncio or formally deprecate and document
- [ ] `comptime` — restrict to compile-time-evaluatable expressions; reject runtime calls
- [ ] Struct value semantics option: `@value struct Point { ... }` for copy-on-assign
- [ ] `match` on ranges: `case 1..10 { }`
- [ ] String template literals with `${expr}` alternative syntax
- [ ] `interface` static methods
- [ ] `mat4` stdlib module for 3D math (no NumPy dependency)

---

## 🚀 v1.3.0 — Performant (Q4 2026)

**Goal:** Make InScript fast enough for real game loops. This is Phase 6.2 from the original plan.

### Performance — Phase 6.2 C Extension

The current interpreter is ~40× slower than Python for tight loops. Target: 5-15× speedup.

**Approach:**
1. Profile a real game loop (not microbenchmarks) to find actual bottlenecks
2. Write C extension for the 3-5 most expensive operations:
   - Environment lookup (`_env.get()`)
   - Function call dispatch (`_call_function()`)
   - Integer arithmetic (avoids Python boxing)
3. Use `cffi` or `ctypes` (no compilation required from user) — free
4. Estimated result: fib(20) from ~200ms to ~20ms

**Why not now:** The VM needs language correctness first. Building a C layer on an
inconsistent VM locks in bugs permanently. v1.0.11 achieved VM parity — now it's safe.

### Other v1.3 Goals
- [ ] Tail call optimisation (removes Python 1000-frame stack limit)
- [ ] Bytecode optimisation passes: constant folding, dead code elimination, inlining
- [ ] JIT via `numba` for numeric hot paths (optional, free)
- [ ] WASM exploration: can InScript run in the browser via Pyodide?
- [ ] Standalone binary: `pyinstaller` wrapper for one-click distribution (free)
- [ ] InScript Studio IDE — begin development (Electron/Tauri)

### NumPy Integration Decision Point
After Phase 6.2, benchmark whether InScript's native arrays are fast enough for:
- 4×4 matrix multiplication (for 3D transforms)
- Batch AABB collision detection (100+ objects)

If not: add optional `inscript_numpy` bridge (separate package, `pip install inscript-numpy`).
If yes: native arrays are sufficient.

---

## 🌐 v2.0.0 — Ecosystem (2027)

**Goal:** Production-ready with full ecosystem. Zero breaking changes from v1.x.

### Native & WASM
- [ ] JIT compilation via LLVM (experimental, via `llvmlite` — free)
- [ ] Native binary output via Cython/Nuitka bridge (free tools)
- [ ] Full WASM target — run InScript games in a browser without Python
- [ ] iOS/Android via WASM + PWA wrapper

### Ecosystem
- [ ] Package registry at `inscript-lang.dev/packages` (self-hosted, free)
- [ ] `inscript publish` / `inscript install <package>` end-to-end
- [ ] 10+ first-party game templates
- [ ] InScript Studio v1.0 — embedded script editor, scene graph, asset browser
- [ ] Godot plugin — use InScript as an alternative to GDScript inside Godot
- [ ] Static type checker as separate CLI tool (`inscript typecheck`)

---

## Timeline Summary

```
March 2026   v1.0.11   Feature-complete, 836 tests, 100+ bugs fixed
                       STATUS: Public beta / early adopters only
                       MISSING: formatter, debugger, docs, PyPI, no users

Q2 2026      v1.1.0    Developer-ready stable
             ~2-3mo    formatter ✅ debugger ✅ PyPI ✅ docs site ✅ playground ✅
                       STATUS: ✅ FIRST STABLE RELEASE (recommend for early adopters)

Q3 2026      v1.2.0    Type-safe
             ~3-4mo    union types, generic enforcement, null safety, type narrowing
                       STATUS: ✅ Stable for production 2D games

Q4 2026      v1.3.0    Performant
             ~3-4mo    C extension (5-15× speedup), TCO, standalone binary
                       STATUS: ✅ Stable for performance-sensitive games

2027         v2.0.0    Ecosystem
             ~6mo      WASM, package registry, InScript Studio IDE
                       STATUS: ✅ Production stable, comparable to Lua/GDScript
```

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| v1.0.0 | 2026-03-04 | Initial stable — full language + 18 stdlib + VM + LSP |
| v1.0.1 | 2026-03-08 | VM fixes BUG-01–05, REPL improvements |
| v1.0.2 | 2026-03-10 | 20 bug fixes BUG-06–30, 56 stdlib modules, 501 tests |
| v1.0.3 | 2026-03-13 | Pixel-art banner, tween/iter/collections fixes |
| v1.0.4 | 2026-03-14 | `.doc` all 59 modules, dict comprehensions, `do-while` |
| v1.0.5 | 2026-03-14 | `pub` fields, `for-else`, `assert`/`panic`, arg-count warnings |
| v1.0.6 | 2026-03-14 | `typeof` clean, 21 new array/string methods, struct print |
| v1.0.7 | 2026-03-14 | `x in arr`, 15 new methods, VM parity phase 1 |
| v1.0.8 | 2026-03-14 | `reduce(fn)`, `dict()`, f-string dict key, `try` as expr, VM builtins |
| v1.0.9 | 2026-03-14 | VM line numbers, struct copy deep, match-expr, type warnings, priv fields |
| v1.0.10 | 2026-03-14 | VM parity phase 2: 25+ methods, dict comp, named args, match fn |
| v1.0.11 | 2026-03-14 | `++` operator, Err display, chain-call double-eval fix, float/0=Inf, 335 tests |

---

## Notes on Python Library Strategy

**InScript does NOT need NumPy, Pandas, or TensorFlow.**

InScript is a game scripting language targeting GDScript parity. The correct dependencies are:
- `pygame` — game backend (already required)
- `pygls` — LSP server (already required)
- `sqlite3` — database module (Python built-in)
- `watchdog` — watch mode, add at v1.1 (free, 1MB)
- `Pillow` — image module improvements, optional at v1.1 (free, MIT)

Scientific/ML libraries would massively bloat the install, require complex type bridging,
and serve a use case (data science) that is completely outside InScript's scope.

At v1.3.0, evaluate whether a thin NumPy bridge is needed for 3D matrix math.
Default assumption: native InScript arrays + a `mat4` module are sufficient.

**Total additional Python dependencies needed to reach v2.0: 2-3 packages, all free.**
