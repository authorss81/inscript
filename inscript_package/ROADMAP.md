# InScript Language Roadmap — Detailed

> **Current version:** v1.0.18 (April 2026)
> **Tests:** 839 total (145 VM + 32 operators + 54 audit + 335 comprehensive + 273 core) — all passing
> **Stdlib:** 59 modules
> **Audit score:** 8.8/10
> **Assessment:** Language feature-complete. VM at full parity. Pre-stable: missing formatter, PyPI v1.x, docs site.

---

## ✅ Completed — v1.0.0 through v1.0.18

### Core Language — ALL DONE ✅
- [x] `let` / `const` with type annotations and inference
- [x] All primitive types: `int` `float` `string` `bool` `nil`
- [x] All operators: arithmetic, bitwise, comparison, logical, `in`/`not in`, `|>`, `??`, `?.`
- [x] String concat `++`, array concat `++`
- [x] Float division by zero → `Infinity`; int/0 throws
- [x] Functions: defaults, named args, variadics `*args`, closures
- [x] Arrow function `fn(x) => x*2` — PENDING v1.0.19
- [x] Structs: inheritance, mixins, interfaces, operator overloading
- [x] `priv`/`pub` field access control (VM + interpreter, `_current_self` tracking)
- [x] `super` keyword (VM + interpreter)
- [x] Static fields and methods on structs (VM + interpreter)
- [x] Generic structs `struct Stack<T>` (syntax only)
- [x] ADT Enums with data fields: `enum Shape { Circle(r: float) }`
- [x] Pattern matching: guards, ADT bindings, ranges `case 1..=5`, Ok/Err, binding
- [x] Non-exhaustive match warning
- [x] Array/tuple/struct destructuring
- [x] Array comprehensions, dict comprehensions
- [x] Generators `fn*` / `yield`
- [x] Decorators `@name` (VM + interpreter, local binding updated)
- [x] Error propagation `?` with `Ok` / `Err` / `Result`
- [x] `try/catch/finally` as expression
- [x] Typed catch `catch e:int`
- [x] `assert` / `panic` / `unreachable` — catch gets message directly
- [x] `do-while`, `for-else`, `while-else`, labeled `break`/`continue`
- [x] Multi-variable for `for k,v in entries(d)`
- [x] Range `0..5` / `0..=5` / `range(start,end,step)`
- [x] F-strings with format specs, ternaries, dict key access
- [x] `comptime{}` block — variables leak to outer scope
- [x] `type ID = int` type aliases
- [x] `int?` nullable type annotations
- [x] `int|string` union type annotations

### Type System — ALL DONE ✅
- [x] `typeof(v)` returns clean names
- [x] `x is T` type check
- [x] `x as T` cast
- [x] Type mismatch warns in REPL (literals at call sites)
- [x] Missing return in typed functions warns
- [x] Arg-count mismatch warns

### Array Methods — ALL DONE ✅ (50+)
Core, functional, FP extras, ordering, slicing, set-like, query, structural.
**v1.0.17 additions:** `take_while` `drop_while` `window` `partition` `none` `index_where` `last_where`

### String Methods — ALL DONE ✅ (35+)
Case, trim, search, transform, pad, extract, convert, check, format.
**v1.0.18 additions:** `is_upper` `is_lower` `swapcase` `is_space` `is_digit` `zfill`

### Dict Methods — ALL DONE ✅ (25+)
Including `filter(fn)` `map_values(fn)` `map_keys(fn)` `each(fn)` `any_value` `all_values` `count_values`

### VM (Bytecode Engine) — ALL DONE ✅
- [x] Full parity with interpreter
- [x] `match` as expression, `try` as expression
- [x] ADT patterns, range patterns, match guards + ADT bindings (v1.0.15-17)
- [x] Decorators compile correctly — local variable updated after wrapping (v1.0.16)
- [x] `priv` field enforcement with `_current_self` tracking (v1.0.16)
- [x] `super.method()` working (v1.0.15)
- [x] `try-finally` (v1.0.15)
- [x] Static fields and methods (v1.0.13)
- [x] Variadic `fn(*args)` (v1.0.13)
- [x] Mixin expansion in compiler (v1.0.18)
- [x] `throw struct` — catch binds actual struct (v1.0.14)
- [x] `arr ++ arr` concat (v1.0.14)
- [x] `1.0/0.0 = Infinity` (v1.0.13)
- [x] All dict/string methods via `_do_method` fallback (v1.0.13-14)

### Standard Library — ALL DONE ✅
59 modules across Core, Data, Format/Iter, Net/Crypto, FS/Process, Date/Collections,
Threading/Bench, Game Visual, Game IO, Game World, Game Systems, Utilities.

### Tooling — PARTIALLY DONE
- [x] Enhanced REPL — pixel-art banner, 30+ commands, tab completion, history
- [x] `.doc <module>` — live docs for all 59 modules
- [x] LSP server + VS Code extension
- [x] Bytecode `.ibc` save/load
- [x] `inscript check` — static analysis
- [x] Web playground (basic, in repl.py `--web`)
- [ ] `inscript fmt` — formatter (v1.0.19)
- [ ] `inscript --watch` — watch mode (v1.0.20)
- [ ] `inscript test` — `.ins` test runner (v1.0.21)
- [ ] `pyproject.toml` + PyPI v1.x release (v1.0.22)
- [ ] Docs site (v1.0.23)

---

## 🔧 v1.0.19 — Formatter + Arrow Functions + Rest Destructuring

**Goal:** Polish + missing syntax. 1–2 sessions.

### `inscript fmt` — Token-based formatter
- [ ] `inscript fmt file.ins` — formats in place
- [ ] `inscript fmt --check file.ins` — exits 1 if not formatted (for CI)
- [ ] `inscript fmt --dry-run` — print without writing
- [ ] Rules: 2-space indent, spaces around operators, trailing newline
- [ ] Max line length 100 (break long fn signatures)
- [ ] Trailing comma in multi-line arrays/dicts/params
- [ ] Implementation: ~250 lines using existing `Lexer` token stream

### Arrow function syntax `=>`
- [ ] `let f = fn(x) => x*2` — single expression, no braces needed
- [ ] `let f = fn(x, y) => x + y`
- [ ] Works in interpreter and VM
- [ ] Chaining: `[1,2,3].map(fn(x) => x*2).filter(fn(x) => x>2)`

### Rest destructuring `...rest`
- [ ] `let [a, b, ...rest] = [1,2,3,4,5]` → `rest = [3,4,5]`
- [ ] In function params: `fn f(first, ...rest)` (already works as `*args` — add `...` syntax alias)
- [ ] Spread in array literals: `let c = [...a, ...b]`

### Stdlib quick fixes
- [ ] `random.int(min, max)` — fix off-by-one (currently `R.int(1,6)` doesn't always work)
- [ ] `iter.range(start, end, step)` — fix to return list with step correctly
- [ ] `format.number(n)` — add comma-separated thousands (`1234567` → `"1,234,567"`)

---

## 🔧 v1.0.20 — Watch Mode + Test Runner + `inscript run`

**Goal:** Developer workflow tools. 1 session.

### `inscript --watch file.ins`
- [ ] Watch for file changes using `os.stat` polling (no `watchdog` dep — keep it stdlib-only)
- [ ] Clear terminal and rerun on change
- [ ] Show error location with colored output and file:line reference
- [ ] `Ctrl+C` to stop
- [ ] Also watch imported files

### `inscript test`
- [ ] Discovers and runs `test_*.ins` files in current directory
- [ ] Test format: `assert(expr, "message")` — any assert failure = test fail
- [ ] Named tests: `test "addition works" { assert(1+1==2) }`
- [ ] Output: colored pass/fail count, timing per test, total time
- [ ] `--verbose` flag shows all test names
- [ ] Exit code: 0 = all pass, 1 = any fail (CI compatible)

### `inscript run` improvements
- [ ] `inscript run file.ins --vm` — force VM mode
- [ ] `inscript run file.ins --profile` — print per-function timing
- [ ] Better error output: file path + line + source context + caret

---

## 🔧 v1.0.21 — PyPI Release (v1.0.x on PyPI)

**Goal:** `pip install inscript-lang` works. You already have a PyPI account with v0.6 published.

### `pyproject.toml`
- [ ] Replace or augment `setup.py` with `pyproject.toml`
- [ ] Package name: `inscript-lang` (matches your existing PyPI package)
- [ ] Version: `1.0.21`
- [ ] Entry point: `inscript` → `inscript.py:main`
- [ ] Dependencies: `pygame>=2.0` (optional), `pygls>=1.0` (optional)
- [ ] Python: `>=3.10`

### PyPI upload
- [ ] `python -m build` produces wheel + sdist
- [ ] `python -m twine upload dist/*` uploads to PyPI
- [ ] Test: `pip install inscript-lang==1.0.21` in a fresh venv works
- [ ] `inscript --version` prints `InScript 1.0.21`

### Upgrade from v0.6
- [ ] Note in README: "Upgrade from v0.6: `pip install --upgrade inscript-lang`"
- [ ] v0.6 → v1.0 migration guide (one paragraph — syntax is backward compatible)

---

## 🔧 v1.0.22 — Docs Site + Error Pages

**Goal:** All error links in error messages point to real content.

### GitHub Pages docs (authorss81.github.io/inscript)
- [ ] `/` — landing page (already updated with index.html)
- [ ] `/docs/` — language guide (Getting Started, Syntax, Types, Functions, Structs)
- [ ] `/docs/stdlib/` — stdlib reference (auto-generated from `STDLIB_DOCS` in `repl.py`)
- [ ] `/docs/errors/` — error code index
- [ ] `/docs/errors/E0040/` — one page per error code with example + fix
- [ ] Navigation menu, search (just browser Ctrl+F — no JS needed for v1)
- [ ] All written in Markdown, rendered by GitHub Pages (Jekyll or just HTML)

### Error codes covered
- [ ] E0001 — LexerError (unterminated string etc.)
- [ ] E0010 — ParseError
- [ ] E0040 — RuntimeError
- [ ] E0042 — NameError (undefined variable)
- [ ] E0050 — AssertionError
- [ ] E0051 — Panic
- [ ] All codes in `errors.py`

---

## 🔧 v1.0.23 — Web Playground (Pyodide)

**Goal:** Run InScript in the browser — no install needed.

### Implementation
- [ ] Host on `authorss81.github.io/inscript/playground`
- [ ] Use Pyodide (Python in WASM) to run InScript engine in browser
- [ ] Code editor: CodeMirror 6 (MIT, CDN)
- [ ] InScript syntax highlighting via CodeMirror language extension
- [ ] 10 built-in examples (fibonacci, fizzbuzz, sorting, struct demo, game loop)
- [ ] Share button (encode code in URL hash — no backend needed)
- [ ] Runs completely client-side — zero server costs

---

## ✅ v1.1.0 — First Stable Release (released)

**Goal:** A developer can use InScript professionally. All tooling complete.
**Gate:** v1.0.19 through v1.0.23 must all be done. Zero breaking changes.

### Checklist (all must be ✅ before tagging v1.1.0)
- [ ] `inscript fmt` working and integrated in VS Code
- [ ] `inscript --watch` working
- [ ] `inscript test` working
- [ ] `pip install inscript-lang` installs current version from PyPI
- [ ] `inscript --version` prints `InScript 1.1.0`
- [ ] All error URLs (`https://docs.inscript.dev/errors/E0040`) return real pages
- [ ] GitHub Pages docs site has Getting Started, Language Guide, Stdlib Reference
- [ ] Web playground running at GitHub Pages URL
- [ ] All 839+ tests still passing
- [ ] README updated for v1.1.0

### What v1.1.0 does NOT change
- Language syntax (frozen — no new features in v1.1.0 itself)
- Standard library API (no breaking changes)
- VM/interpreter behavior
- All 839 existing tests pass unchanged

---

## ✅ v1.2.0 — Type Safety (released)

**Goal:** Add real type enforcement. May include minor breaking changes (announced 2 releases ahead).

- [x] Generic enforcement: `Stack<int>` rejects non-int at push time
- [x] `@value struct Point` — copy-on-assign semantics  *(completed in v1.2.0-dev)*
- [x] `struct Stack<T>{}` — type_args captured on StructInitExpr  *(completed in v1.2.0-dev)*
- [x] Unused variable warnings in analyzer — `--no-warn-unused` to suppress
- [x] Unreachable code warnings after return/break/continue/throw
- [x] `mat4` stdlib for 3D math (17 functions, no NumPy)
- [ ] Generic constraints: `fn sort<T: Comparable>(arr: [T]) -> [T]`  → deferred to v1.3.0
- [ ] Type narrowing in match arms  → deferred to v1.3.0
- [ ] Recursive types: linked list, tree nodes  → deferred to v1.3.0
- [ ] `async/await` — formally documented as sync-only, event loop deferred
- [ ] Interface static methods  → deferred to v1.3.0

---


## ✅ v1.3.0 — Performance (released)

- [x] Dispatch cache — `_dispatch` dict on Visitor; eliminates per-visit `getattr`
- [x] Fast-path arithmetic — int/float hot path in `visit_BinaryExpr`
- [x] Tail call optimization — `return f(args)` trampolined; `count(10000)` works
- [x] Bytecode constant folding — `2+3` → `LOAD_INT 5` at compile time
- [x] Bytecode dead code elimination — CFG pass; `PUSH_HANDLER` + `ITER_NEXT` handled
- [x] `str()` builtin alias
- [x] `--profile` flag — per-function timing table
- [x] `test_v130.py` — 69 tests

## ✅ v1.4.0 — Language Completeness (released)

- [x] `defer` statement — runs at function exit, LIFO, fires even on throw/error
- [x] `repeat..until` — do-while: body runs at least once
- [x] Type-narrowing match arms — `case int x`, `case string s`, `case Vec2 v`
- [x] Generic constraints — `fn max<T: Comparable>`, built-in + interface constraints
- [x] `test_v140.py` — 28 tests

## ✅ v1.5.0 — Standard Library Expansion (released)

**Goal:** Richer stdlib so games need fewer workarounds.

- [x] `string` module — `split()`, `join()`, `trim()`, `starts_with()`, `ends_with()`, `replace_all()`
- [x] `array` module — `sort()`, `sort_by()`, `flat_map()`, `zip()`, `chunk()`, `flatten()`, `group_by()`
- [x] `math` module additions — `lerp()`, `smoothstep()`, `sign()`, `wrap()`, `remap()`
- [x] `color` module — `from_hsv()`, `lerp()`, `darken()`, `lighten()`, `to_hex()`, `from_hex()`
- [x] `dict` module (new) — `keys()`, `values()`, `entries()`, `merge()`, `filter_keys()`, `map_values()`
- [x] `io` module — `read_file()`, `write_file()`, `file_exists()`, `list_dir()`
- [x] `test_v150.py` — 73 tests

## ✅ v1.6.0 — Tooling & Developer Experience (released)

**Goal:** Make InScript pleasant in a real project.

- [x] `inscript check` — analyzer-only, exit 1 on errors
- [x] `inscript fmt --all` — recursively format all `.ins` files
- [-] Source maps (deferred to v2.0.0) — errors show original `.ins` line even when running bytecode
- [x] REPL improvements — multiline, history, tab completion
- [x] `--strict` mode — all warnings become errors, no implicit `any`
- [x] `test_v160.py` — 33 tests

## 🔮 v2.0.0 — Production Ready

**Goal:** First major stable release. Some breaking changes (announced in v1.9.0).

- [ ] Full type inference — infer variable types from initializer
- [ ] Recursive types — `struct Node { value: int; next: Node? = nil }`
- [ ] True `async/await` via asyncio event loop
- [ ] C extension hot path — cffi/ctypes for env lookup (5-15x target)
- [ ] Package manager — `inscript install pkg`, `inscript.toml`
- [ ] Breaking: remove deprecated `null` (use `nil`)
- [ ] `test_v200.py`

## Timeline

```
April 2026   v1.0.18   Current — VM complete, 839 tests, audit 8.8/10
             STATUS: Early adopter ready. Missing tooling for general use.

             v1.0.19   fmt + arrow fn + rest destructure + stdlib fixes
             v1.0.20   --watch + inscript test + run improvements
             v1.0.21   pip install inscript-lang (PyPI v1.0.x upgrade from v0.6)
             v1.0.22   docs site + all E0XXX error pages
             v1.0.23   web playground (Pyodide)

Q2 2026      v1.1.0    FIRST STABLE RELEASE
             STATUS: ✅ Ready for professional use

Q3 2026      v1.2.0    Type safety + generic enforcement

Q4 2026      v1.3.0    Performance (5-15× via C extension)

2027         v2.0.0    Ecosystem (registry, Studio IDE, WASM)
```

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| v0.6 | 2025 | **PyPI release** — initial public release on PyPI as `inscript-lang` |
| v1.0.0 | 2026-03-04 | Full language + 18 stdlib + VM + LSP |
| v1.0.1–11 | Mar 2026 | VM parity, 100+ bug fixes, 59 modules, 836 tests |
| v1.0.12 | Mar 2026 | VM arr++arr, throw struct, dict/str methods |
| v1.0.13 | Mar 2026 | VM variadic fn(*args), static fields/methods, int/float methods |
| v1.0.14 | Mar 2026 | VM dict.filter/map_values, str.lines/bytes/title, 1.0/0=Inf |
| v1.0.15 | Mar 2026 | match ranges case 1..=5, VM super, VM try-finally, arr.count(val) |
| v1.0.16 | Mar 2026 | VM @decorator, priv _current_self tracking, VMInstance slots fix |
| v1.0.17 | Apr 2026 | int? nullable, int\|string union, type alias, take_while/drop_while/partition |
| v1.0.18 | Apr 2026 | VM mixin, str.is_upper/lower/swapcase, 839 tests, audit 8.8/10 |
| **v1.0.19** | *next* | fmt, arrow fn =>, rest destructure [...rest], stdlib fixes |
| **v1.0.20** | *next* | --watch, inscript test runner |
| **v1.0.21** | *next* | **PyPI upgrade** — pip install inscript-lang (from v0.6 → v1.x) |
| **v1.0.22** | *next* | docs site + E0XXX error pages |
| **v1.0.23** | *next* | web playground (Pyodide) |
| **v1.1.0** | Q2 2026 | **FIRST STABLE** — all tooling complete |

---

## PyPI Notes

Your package `inscript-lang` exists on PyPI at v0.6.
To upgrade to v1.0.x: update `setup.py` or add `pyproject.toml`, then `twine upload`.
Migration from v0.6 to v1.0: syntax is **fully backward compatible** — no changes needed.

The package name stays `inscript-lang` (not `inscript` — already taken on PyPI by another project).
`pip install inscript-lang` is the install command. The CLI entry point is `inscript`.

---

## 🔮 v2.1.0 — Security & Sandboxing

**Goal:** Make InScript safe to embed in untrusted contexts (game modding, user scripts, plugins).

- [ ] **Sandbox mode** — `inscript run --sandbox file.ins` restricts filesystem, network, subprocess access
- [ ] **Capability system** — explicit `@allow(io, network)` annotations required for sensitive stdlib access
- [ ] **Resource limits** — `--max-memory`, `--max-ops`, `--timeout` flags; hard-kill on breach
- [ ] **Safe import whitelist** — `--allow-modules math,string,array` restricts which stdlib modules can be imported
- [ ] **Code injection prevention** — harden `eval()`-style dynamic execution; disable `__builtins__` escape paths
- [ ] **Audit log** — `--audit-log file.log` records every file/network access for intrusion detection
- [ ] **Secret scanning** — `inscript check --secrets file.ins` warns on hardcoded tokens, passwords, keys
- [ ] **Dependency integrity** — SHA-256 lockfile for packages (`inscript.lock`), verify on install
- [ ] `test_v210.py`

## 🔮 v2.2.0 — Language Enhancements

**Goal:** Fill expressiveness gaps identified from real game projects.

- [ ] **Operator overloading sugar** — `impl Add for Vec2 { fn +(other) }` syntax instead of `operator +`
- [ ] **Destructuring in function params** — `fn f({x, y}: Vec2) { }` and `fn f([head, ...tail]: []) { }`
- [ ] **Named return values** — `fn bounds() -> (min: float, max: float) { return (min: 0, max: 1) }`
- [ ] **`with` expression** — `let v = with Vec2{x: 1} { .y = 2 }` — clone-and-modify pattern
- [ ] **String templates (multiline)** — `let sql = """ SELECT * FROM ... """`
- [ ] **Compile-time constants** — `const PI: float = 3.14159` evaluated at parse time, inlined in bytecode
- [ ] **`is` type-check expression** — `if val is Vec2 { ... }` (complement to type-narrowing match)
- [ ] **Chained comparisons** — `0 < x < 10` desugars to `0 < x && x < 10`
- [ ] **Null-coalescing assignment** — `x ??= default_val`
- [ ] **Labelled loops** — `outer: while true { inner: for i in 0..5 { break outer } }`
- [ ] `test_v220.py`

## 🔮 v2.3.0 — Concurrency & Async

**Goal:** Real async support for networked games, servers, and IO-heavy scripts.

- [ ] **`async/await`** — wire to Python asyncio; `async fn fetch(url)`, `await http.get(url)`
- [ ] **`spawn` keyword** — `spawn fn()` creates a coroutine; returns a handle
- [ ] **`channel<T>`** — typed message-passing: `let ch = channel<int>(capacity: 10)`
- [ ] **`select` expression** — multiplex over channels: `select { case ch1 -> v { } case ch2 -> v { } }`
- [ ] **Async iterators** — `async for item in stream { }` for event streams, WebSocket frames
- [ ] **`mutex` and `rwlock`** — `let m = mutex(value); m.lock(fn(v) { v.count += 1 })`
- [ ] **Timer builtins** — `timer.after(1000, fn() { })`, `timer.every(16, fn() { })`
- [ ] `test_v230.py`

## 🔮 v2.4.0 — Native & WebAssembly Targets

**Goal:** Ship InScript games to web and native without Python runtime dependency.

- [ ] **WASM compilation target** — `inscript build --target wasm file.ins` outputs `.wasm` + JS glue
- [ ] **Native binary output** — compile to C via transpilation, then `gcc`/`clang`; no Python needed at runtime
- [ ] **Pyodide bundle optimisation** — tree-shake stdlib, lazy-load modules; reduce playground load time from ~3s to <1s
- [ ] **Ahead-of-time (AOT) compilation** — `inscript compile file.ins` → `.ibc` bytecode; `inscript run file.ibc`
- [ ] **Incremental compilation** — cache `.ibc` per file, recompile only changed files
- [ ] **Dead code elimination (IR level)** — whole-program DCE before code generation
- [ ] **Inline caching** — monomorphic call sites cached at runtime for 2-4x method call speedup
- [ ] `test_v240.py`

## 🔮 v2.5.0 — IDE & Editor Integration

**Goal:** First-class IDE support making InScript as pleasant as TypeScript to work with.

- [ ] **LSP v2** — go-to-definition, find-all-references, rename symbol, document symbols
- [ ] **Hover types** — hover any expression to see inferred type
- [ ] **Inline diagnostics** — squiggly underlines for errors + warnings in real time
- [ ] **Auto-import** — type `Vec2` → LSP offers `import "math" as math`
- [ ] **Code actions** — quick fix: add missing interface method, rename to fix typo
- [ ] **Semantic tokens** — richer syntax highlighting (function calls vs variable reads)
- [ ] **VS Code extension v2** — publish to marketplace as `inscript-lang.inscript`
- [ ] **Neovim plugin** — `inscript.nvim` via nvim-lspconfig
- [ ] **Debugger (DAP)** — breakpoints, step-over/into/out, variable watch via Debug Adapter Protocol
- [ ] `test_v250.py` (LSP integration tests)

## 🔮 v2.6.0 — Package Ecosystem

**Goal:** A real package registry so the community can share InScript libraries.

- [ ] **`inscript.toml`** — project manifest: name, version, dependencies, scripts
- [ ] **`inscript install pkg@1.0.0`** — download from registry, verify hash, add to `inscript.lock`
- [ ] **`inscript publish`** — upload a package to registry (requires API key)
- [ ] **Package registry** — hosted at `pkg.inscript.dev`; search by tag (game, math, physics, ui)
- [ ] **Scoped packages** — `@authorss81/ecs`, `@community/pathfinding`
- [ ] **`inscript audit`** — scan installed packages for known vulnerabilities
- [ ] **Monorepo support** — `workspace = ["packages/*"]` in `inscript.toml`
- [ ] **Private registries** — `inscript config set registry https://internal.example.com`
- [ ] **Stdlib versioning** — pin stdlib version in `inscript.toml` for reproducible builds
- [ ] `test_v260.py` (package manager integration tests)

## 🔮 v3.0.0 — InScript Studio (Long-term)

**Goal:** A complete game development environment built around InScript.

- [ ] **InScript Studio** — Electron-based IDE with scene editor, asset browser, live preview
- [ ] **Visual scripting** — node-based editor that compiles to InScript source
- [ ] **Hot reload** — live-reload scripts in running game without restart
- [ ] **Asset pipeline** — `@texture`, `@sound`, `@tilemap` annotations for auto-loading assets
- [ ] **Scene system** — built-in scene tree, node lifecycle (`_ready`, `_update`, `_draw`)
- [ ] **Physics integration** — first-class 2D/3D physics via Box2D/Jolt bindings
- [ ] **Multiplayer stdlib** — `net.connect()`, `net.broadcast()`, `net.sync(state)`
- [ ] **Mobile export** — iOS/Android via Kivy or BeeWare bridge
- [ ] **Console export** — Nintendo Switch / PlayStation via platform SDK wrappers

