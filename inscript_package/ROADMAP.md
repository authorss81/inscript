# InScript Language Roadmap — Detailed

> **Current version:** v2.8.0 (May 2026) 🎉
> **Tests:** 53 test files, 53/53 CI passing — all green
> **Assets:** `@texture/@sound/@tilemap/@font` decorators, `AssetRegistry`, `--asset-manifest`, `--bundle`, hot-reload mtime watching
> **Assessment:** Asset pipeline complete. 4 more versions before v3.0.0. Next: v2.9.0 Hot Reload.

---


## ✅ v2.0.0 — Released (May 2026)

**Status: SHIPPED**

All eight readiness gates passed. The language is stable.

Key milestones completed on the road to v2.0.0:

- v1.7.x — Stack traces, REPL stability
- v1.8.x — Type system: unions, aliases, string literals, enums, interfaces, inference
- v1.9.1–v1.9.5 — Tooling suite, compatibility checker, migrate, error catalogue
- v1.9.6 — `#` comments, `//` always floor division
- v1.9.7 — Real async/await via InScriptCoroutine
- v1.9.8–v1.9.10 — Array inference, package manager, check-v2
- v1.9.11 — Real async I/O (http, file, timer)
- v1.9.12 — Bootstrap package registry + 3 real packages
- v1.9.13 — Type inference round 2
- v1.9.14 — Working games (pong, breakout)
- v1.9.15 — String interpolation `$"..."`
- **v2.0.0** — Stable release 🎉

---

## 🔭 Post-v2.0.0 Roadmap

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


---

## 🔮 v1.7.0 — Stability & Bug Fixes

**Goal:** Fix the concrete correctness gaps that block v2.0.0. No new features.

### ✅ v1.7.1 — Float & Integer Display (released)
- [x] `_format_float()` — strip floating-point noise: `0.30000000000000004` → `0.3`; round to 14 significant figures, strip trailing zeros, keep `1.0` as `1.0` not `1`
- [x] `print(0.1 + 0.2)` → `0.3`, `print(1.0 / 3.0)` → `0.3333333333333333`
- [x] Integer division operator `//` — `10 // 3` → `3` (int); `div` keyword kept as alias
- [x] `print(10 // 3)` → `3` (int, not `3.0`)
- [x] null keyword hard error (removed from language) — float formatting + integer division edge cases

### ✅ v1.7.2 — Recursive & Self-Referential Types (released)
- [x] Struct field type resolution deferred — allow `struct Node { next: Node? = nil }` without infinite recursion during struct registration
- [x] Mutually recursive structs — `struct A { b: B? = nil }` / `struct B { a: A? = nil }` both defined in same scope
- [x] `let n = Node{value:1, next: Node{value:2}}; print(n.next.value)` → `2`
- [x] Linked list, binary tree, trie — all must work
- [x] `test_v172.py` — recursive type tests

### ✅ v1.7.3 — Stack Traces & Error Quality (released)
- [x] Full call chain in error output: `outer() → middle() → inner() → throw "err"` shows all 3 frames
- [x] Line numbers accurate in nested closures and lambdas
- [x] `InScriptCallStack.format()` shows file, function name, line, source snippet for each frame
- [x] Uncaught errors print stack trace to stderr by default (currently only shown with `--debug`)
- [x] `test_v173.py` — stack trace format and accuracy

### ✅ v1.7.4 — REPL Stability (released)
- [x] REPL error recovery — after runtime error, all previously-defined globals survive
- [x] REPL `let` re-definition — `let x = 1` then `let x = 2` in REPL re-binds instead of erroring
- [x] REPL multi-line paste — paste a full struct/fn block and REPL handles it atomically
- [x] `null` hard error — `null` emits `E0055: 'null' was removed in v1.7.4, use 'nil'`
- [x] `inscript migrate FILE` — rewrites `null` → `nil`, `x div y` → `x // y` in-place
- [x] `test_v174.py` — REPL stability + migration tool

---

## 🔮 v1.8.0 — Type System Foundations

**Goal:** Complete the type system so v2.0.0 full inference has a solid base.

### ✅ v1.8.1 — Union Types & Optionals (released)
- [ ] `int | string` union type — enforced in assignments, function params, return types
- [ ] `int?` shorthand — complete alias for `int | nil` in all contexts: params, returns, generic args
- [ ] Union narrowing in `if` — `if typeof(x) == "int" { /* x is int here */ }`
- [ ] Assignment to union: `let x: int | string = 42; x = "hello"` — both must be valid
- [ ] `test_v181.py`

### v1.8.2 — Type Aliases & Literal Types
- [ ] `type PlayerID = int` — type alias stored in scope, treated as equivalent type
- [ ] `type Direction = "left" | "right" | "up" | "down"` — string literal union
- [ ] `type Callback = fn(int) -> bool` — function type alias
- [ ] Literal types in function params: `fn move(dir: "left" | "right") { }`
- [ ] Analyzer enforces literals: `move("diagonal")` → type error
- [ ] `test_v182.py`

### v1.8.3 — Enum Exhaustiveness & Interface Enforcement
- [ ] Enum exhaustiveness — analyzer warns when `match` on an enum misses a variant (no wildcard)
- [ ] `struct Sprite implements Drawable { }` — check at struct declaration, not call site; error immediately if `draw()` missing
- [ ] `never` return type — `fn crash() -> never { throw "fatal" }` — analyzer marks code after call as unreachable
- [ ] `test_v183.py`

### v1.8.4 — Type Inference for Method Chains
- [ ] `arr.filter(fn(x)=>x>0)` infers `[int]` not `any`
- [ ] `arr.map(fn(x)=>x*2)` preserves element type
- [ ] Chained: `arr.filter(...).map(...).take(5)` — type flows through
- [ ] Return type inference: `fn double(x: int) { return x * 2 }` infers `-> int` without annotation
- [ ] `test_v184.py`

---

## 🔮 v1.9.0 — Pre-2.0 Migration & Spec Freeze

**Goal:** Smooth upgrade path to v2.0.0. All deprecated features become hard errors. Spec frozen.

### v1.9.1 — Deprecation Errors & Compat Tool
- [ ] `inscript compat FILE` — report every v2.0.0 breaking change affecting the file
- [ ] `inscript compat DIR` — report across all `.ins` files in directory
- [ ] Hard errors (not warnings) for: `null`, bare `array` type without element type, `fn` without return type in strict mode
- [ ] `--no-typecheck` flag deprecated — use `--unsafe-no-check`
- [ ] `test_v191.py`

### v1.9.2 — Package Manifest Foundation
- [ ] `inscript init` — create `inscript.toml` in current directory
- [ ] `inscript.toml` schema: `name`, `version`, `description`, `inscript`, `dependencies`
- [ ] `inscript validate` — check `inscript.toml` is well-formed
- [ ] Semantic version range parsing: `">=1.9.0"`, `"^1.8.0"`, `"~1.7.2"`
- [ ] `inscript.lock` — generated lockfile pinning exact dependency versions with SHA-256
- [ ] `test_v192.py`

### v1.9.3 — Documentation Generation
- [ ] `inscript doc FILE` — extract `///` doc comments from `.ins` files, output Markdown
- [ ] `inscript doc DIR` — generate docs for entire project into `docs/api/`
- [ ] Doc comment format: `/// Description
/// @param name type desc
/// @returns type desc`
- [ ] Playground integration — doc pages include runnable examples
- [ ] `test_v193.py`

### v1.9.4 — Spec Freeze & Final Polish
- [x] Language spec document published at `docs.inscript.dev/spec`
- [x] All stdlib functions documented with type signature, example, edge cases
- [x] Error code catalogue — all E0001–E0055 documented at `docs.inscript.dev/errors/`
- [x] `inscript changelog v1.6.0..v1.9.4` — generates human-readable changelog
- [x] Performance baseline published — benchmark suite results for fib(30), game_loop_10k, struct_heavy
- [x] `test_v194.py`

### ✅ v1.9.5 — `div` Keyword Removed (Breaking)
- [x] `div` is now a hard **parse error** (E0056) — `10 div 3` fails at parse time with message pointing to `//` and `inscript migrate`
- [x] E0056 `DivKeyword` added to error catalogue (`inscript.py`) and `errors.py` registry
- [x] `inscript compat` message updated: "removed in v1.9.5 (hard error)" instead of "v2.0.0"
- [x] `inscript migrate` already rewrites `div → //` since v1.7.4 — no change needed
- [x] `test_v195.py` — 22 tests

### v1.9.6 — `#` Line Comments; `//` Always Floor Division ⚠️ Breaking
- [ ] `#` is the new line-comment character — `# this is a comment`
- [ ] `//` is **always** floor division, regardless of surrounding spaces — `10 // 3 == 3`
- [ ] The old space-sensitive rule (`space before // → comment`) is removed entirely
- [ ] `inscript migrate` rewrites `// comment` lines → `# comment` (standalone and inline)
- [ ] E0057 `SlashSlashComment` — friendly error if `//` appears where a comment was expected (i.e. nothing follows that parses as an expression)
- [ ] `/* */` block comments unchanged
- [ ] `test_v196.py`

### v1.9.7 — True async/await via asyncio
- [ ] `async fn` functions execute as real Python coroutines (not synchronous stubs)
- [ ] `await expr` suspends the coroutine and drives the asyncio event loop
- [ ] `Promise<T>` added to the type system (analyzer + type map)
- [ ] Multiple sequential `await` calls in the same function work correctly
- [ ] Graceful fallback: `await` on a plain value returns it unchanged
- [ ] `test_v197.py`

### v1.9.8 — Type Inference Hardening (reduce T_ANY leakage)
- [ ] `let x = [1, 2, 3]` infers `Array<int>` not `T_ANY`
- [ ] `let d = {"k": 1}` infers `Dict<string, int>` not `T_ANY`
- [ ] Array/dict literals with mixed types infer `Array<any>` / `Dict<string, any>` instead of crashing
- [ ] `inscript check --infer-types FILE` — print inferred type for every `let`/`const` declaration
- [ ] `test_v198.py`

### v1.9.9 — Package Manager Hardening
- [ ] `inscript install` (no args) — reads `inscript.toml` `[dependencies]` and installs all
- [ ] `inscript install PKG@version` — pins exact version into `inscript.lock`
- [ ] `inscript outdated` — lists packages where a newer version is available
- [ ] `inscript update PKG` — upgrades to latest, rewrites lock entry
- [ ] Offline mode: install from lock file hashes if registry unreachable
- [ ] `test_v199.py`

### v1.9.10 — v2.0.0 Readiness Gate ✅
- [x] `inscript check-v2` command — runs all pre-v2.0.0 readiness checks, prints pass/fail per gate
- [x] Gates: `div` removed ✓, `null` removed ✓, `#` comments ✓, bare `array` removed ✓, async/await real ✓, type inference coverage ✓, package manager lockfile valid ✓, inscript.toml present ✓
- [x] Exit code 0 = all gates pass (ready for v2.0.0), exit 1 = one or more fail
- [x] No rewrites — only adds `check-v2` command on top of existing work
- [x] `test_v1910.py`

---

### v1.9.11 — Real Async I/O Stdlib

**Goal:** Give `async/await` something meaningful to await. Right now `async fn` works but there are zero async I/O primitives — nothing to actually suspend on. This version adds three real async functions backed by asyncio.

**What to implement:**
- `http.get_async(url: string) -> Promise<string>` — async HTTP GET via `asyncio` + `urllib`. Returns response body as string. Times out after 10s. Works: `let body = await http.get_async("https://example.com")`.
- `file.read_async(path: string) -> Promise<string>` — async file read via `asyncio.to_thread`. Returns full file content. Works: `let src = await file.read_async("data.json")`.
- `timer.sleep(ms: int) -> Promise<nil>` — async sleep via `asyncio.sleep(ms / 1000)`. Works: `await timer.sleep(500)`.
- All three return real `InScriptCoroutine` objects. `await` on them drives the asyncio event loop.
- Analyzer: `http.get_async` → `Promise<string>`, `file.read_async` → `Promise<string>`, `timer.sleep` → `Promise<nil>`.
- Graceful error handling: if network unreachable, `http.get_async` raises `InScriptRuntimeError` with a clear message.
- `test_v1911.py` — tests that all three functions return coroutines, that await drives them, that errors are catchable.

---

### v1.9.12 — Bootstrap the Package Registry

**Goal:** Make `inscript install` actually work. Right now the registry URL returns 403 and there are zero installable packages. This version creates three real packages as `.ins` files and a `registry.json` that `inscript install` can fetch.

**What to implement:**
- Create `inscript-packages/` directory structure with `registry.json` and 3 real packages:
  - `math-utils` — `gcd(a,b)`, `lcm(a,b)`, `clamp(x, min, max)`, `lerp(a, b, t)`, `map_range(x, a, b, c, d)`
  - `color-utils` — `hex_to_rgb(hex)`, `rgb_to_hex(r,g,b)`, `lerp_color(c1, c2, t)`, `lighten(c, amount)`, `darken(c, amount)`
  - `grid` — `Grid` struct with `new(w,h)`, `get(x,y)`, `set(x,y,v)`, `in_bounds(x,y)`, `neighbours(x,y)`, `fill(v)`
- Each package is a single `.ins` file with `///` doc comments on every function.
- `registry.json` format: `{"math-utils": {"version": "1.0.0", "url": "...", "description": "...", "tags": [...]}}`
- Update `REGISTRY_URL` in `inscript.py` to point to the real file (GitHub raw URL).
- Update `install_package` offline test to use the new registry structure.
- `test_v1912.py` — tests that all 3 packages parse and run correctly as `.ins` files; tests that `_parse_pkg_spec` and lock file work with real package names; does NOT require live network (packages embedded in test).

---

### v1.9.13 — Type Inference Round 2

**Goal:** Eliminate the most common `T_ANY` leakage. After v1.9.8, array/dict literals infer correctly. But `let x = add(1, 2)` still gives `x: any` because function call return types don't propagate. This version fixes the three most impactful leakage points.

**What to implement:**
- **Function call return type propagation**: `let x = add(1, 2)` → `x: int` if `add` is declared `-> int`. Look up the callee symbol's `fn_node.return_type` and resolve it. Works for user-defined functions and known stdlib functions.
- **Method chain type propagation**: `[1,2,3].map(fn(x) x*2)` → `Array<int>` not `T_ANY`. `"hello".split(",")` → `Array<string>`. Patch `_infer_method_call_type` for the 10 most common array/string methods.
- **Ternary expression inference**: `let x = cond ? 1 : 2` → `x: int` not `T_ANY`. Infer from both branches; if they match, use that type; if they differ, use union.
- **`inscript --infer-types` improvements**: show `→ Array<int>` not `→ any` for all fixed cases.
- No changes to existing type-checking rules — only inference improvements (more specific types, never breaking valid code).
- `test_v1913.py` — tests for each of the three fixed leakage points, before/after comparison showing `T_ANY` → specific type.

---

### v1.9.14 — Ship a Working Game

**Goal:** Prove the language works end-to-end by making `examples/pong.ins` fully runnable. This is the most important version — a language that can't run its own examples isn't ready for v2.0.0.

**What to implement:**
- Audit `examples/pong.ins` against the current interpreter. Find every runtime error, parser failure, and missing stdlib function.
- Fix each blocker found. Document every fix as a bug in CHANGELOG.
- Add any missing game stdlib functions that `pong.ins` needs (ball physics, score display, input handling via keyboard events).
- Verify `python inscript.py --game examples/pong.ins` launches a Pygame window and the game is playable.
- Do the same for `examples/breakout.ins` — fix blockers, make it runnable.
- `test_v1914.py` — parses and type-checks both `pong.ins` and `breakout.ins` without errors; runs key functions from each (ball update, collision, score) in isolation and checks outputs.

---

### v1.9.15 — String Interpolation

**Goal:** Add `$"Hello {name}, score: {score}"` string interpolation. This is the single most-requested feature for a game scripting language — every print statement in every game currently requires string concatenation.

**What to implement:**
- **Lexer**: detect `$"..."` prefix. Inside the string, `{expr}` is an interpolation hole. Tokenise as `INTERP_STRING_START`, `INTERP_EXPR`, `INTERP_STRING_END` tokens, or handle entirely in the lexer by splitting into parts.
- **Parser**: parse interpolated string as `InterpolatedStringExpr(parts: List[str | Expr])`. Simpler approach: lexer fully evaluates the segments and emits a `StringConcatExpr` tree.
- **Interpreter**: evaluate each `{expr}`, call `str()` on the result, concatenate. `$"x={x}"` is identical to `"x=" ++ str(x)`.
- **Analyzer**: `InterpolatedStringExpr` always returns `T_STRING`. Each embedded expression is type-checked; warn if a non-stringifiable type is embedded.
- **Error messages**: if `{` is unclosed inside `$"..."`, emit `[E0057] Unclosed interpolation in string literal`.
- **`inscript migrate`**: no migration needed — this is additive syntax.
- `test_v1915.py` — basic interpolation, nested expressions `$"{a + b}"`, multiline, empty holes `$""`, type-check of embedded exprs, error on unclosed brace.

---



```
April 2026   v1.0.18   ✅ SHIPPED — VM complete, 839 tests, audit 8.8/10
             v1.0.19   ✅ SHIPPED — fmt + arrow fn + rest destructure + stdlib fixes
             v1.0.20   ✅ SHIPPED — --watch + inscript test + run improvements
             v1.0.21   ✅ SHIPPED — pip install inscript-lang (PyPI v1.0.x upgrade from v0.6)
             v1.0.22   ✅ SHIPPED — docs site + all E0XXX error pages
             v1.0.23   ✅ SHIPPED — web playground (Pyodide)

Q2 2026      v1.1.0    ✅ SHIPPED — FIRST STABLE RELEASE

Q3 2026      v1.2.0    ✅ SHIPPED — Type safety + generic enforcement

Q4 2026      v1.3.0    ✅ SHIPPED — Performance (5-15× via C extension)

             v1.9.5    ✅ SHIPPED — div hard error (E0056)
             v1.9.6    ✅ SHIPPED — # comments; // always floor division
             v1.9.7    ✅ SHIPPED — True async/await via asyncio
             v1.9.8    ✅ SHIPPED — Type inference hardening (reduce T_ANY leakage)
             v1.9.9    ✅ SHIPPED — Package manager hardening (install/update/outdated/lock)
             v1.9.10   ✅ SHIPPED — v2.0.0 readiness gate (inscript check-v2)
             v1.9.11   ✅ SHIPPED — real async I/O: http.get_async, file.read_async, timer.sleep
             v1.9.12   ✅ SHIPPED — bootstrap package registry (3 real packages)
             v1.9.13   ✅ SHIPPED — type inference round 2 (fn call return, method chains)
             v1.9.14   ✅ SHIPPED — ship a working game (pong.ins + breakout.ins run)
             v1.9.15   ✅ SHIPPED — string interpolation $"Hello {name}"

May 2026     v2.0.0    ✅ SHIPPED — Production Ready — all 5 gaps closed
             v2.1.1    ✅ SHIPPED — Security & Sandboxing
             v2.2.0    ✅ SHIPPED — Language Enhancements
             v2.3.0    ✅ SHIPPED — Concurrency & Async
             v2.4.0    ✅ SHIPPED — Native & WebAssembly Targets
             v2.5.0    ✅ SHIPPED — IDE & Editor Integration (49/49 CI ✅)
             v2.6.0    ✅ SHIPPED — Package Ecosystem (50/50 CI ✅)
             v2.7.0    ✅ SHIPPED — Scene System (51/51 CI ✅)
             v2.8.0    ✅ SHIPPED — Asset Pipeline (53/53 CI ✅)
             STATUS: 53 test files, all green. Next: v2.9.0 Hot Reload.

2027         v3.0.0    🔮 — InScript Studio (Electron IDE, visual scripting, hot reload)
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
| v1.9.5 | 2026-05-09 | `div` hard error E0056 — breaking, use `//` |
| **v1.9.6** | *next* | `#` line comments; `//` always floor division (breaking) |
| **v1.9.7** | *next* | True async/await via asyncio event loop |
| **v1.9.8** | *next* | Type inference hardening — reduce T_ANY leakage |
| **v1.9.9** | *next* | Package manager — install/update/outdated/lock |
| **v1.9.10** | 2026-05-09 | v2.0.0 readiness gate — `inscript check-v2` ✅ |
| **v1.9.11** | *next* | Real async I/O — `http.get_async`, `file.read_async`, `timer.sleep` |
| **v1.9.12** | *next* | Bootstrap package registry — 3 real installable packages |
| **v1.9.13** | *next* | Type inference round 2 — fn call return, method chains, ternary |
| **v1.9.14** | *next* | Ship a working game — `pong.ins` + `breakout.ins` run end-to-end |
| **v1.9.15** | *next* | String interpolation — `$"Hello {name}"` |
| **v2.0.0** | May 2026 | **Production Ready** — all 5 gaps closed, games ship, registry live |
| v2.1.1 | May 2026 | Security & Sandboxing — `--sandbox`, `@allow`, resource limits, audit log, secret scanning |
| v2.2.0 | May 2026 | Language Enhancements — `impl` sugar, param destructuring, named returns, `with`, `??=`, chained comparisons |
| v2.3.0 | May 2026 | Concurrency & Async — `spawn`, `channel<T>`, `select`, async iterators, `mutex`/`rwlock`, timer builtins |
| v2.4.0 | May 2026 | Native & WASM — `--target wasm`, C transpile, AOT `.ibc`, incremental compile, DCE, inline caching |
| **v2.5.0** | May 2026 | **IDE & Editor Integration** — LSP v2, hover types, DAP debugger, VS Code ext v2, Neovim plugin |
| **v2.6.0** | May 2026 | **Package Ecosystem** — `inscript publish`, scoped pkgs, `inscript audit`, monorepo, private registries, stdlib versioning |

---

## PyPI Notes

Your package `inscript-lang` exists on PyPI at v0.6.
To upgrade to v1.0.x: update `setup.py` or add `pyproject.toml`, then `twine upload`.
Migration from v0.6 to v1.0: syntax is **fully backward compatible** — no changes needed.

The package name stays `inscript-lang` (not `inscript` — already taken on PyPI by another project).
`pip install inscript-lang` is the install command. The CLI entry point is `inscript`.

---

## ✅ v2.1.0 — Security & Sandboxing

**Status: SHIPPED (v2.1.1, May 2026)**

**Goal:** Make InScript safe to embed in untrusted contexts (game modding, user scripts, plugins).

- [x] **Sandbox mode** — `inscript run --sandbox file.ins` restricts filesystem, network, subprocess access
- [x] **Capability system** — explicit `@allow(io, network)` annotations required for sensitive stdlib access
- [x] **Resource limits** — `--max-memory`, `--max-ops`, `--timeout` flags; hard-kill on breach
- [x] **Safe import whitelist** — `--allow-modules math,string,array` restricts which stdlib modules can be imported
- [x] **Code injection prevention** — harden `eval()`-style dynamic execution; disable `__builtins__` escape paths
- [x] **Audit log** — `--audit-log file.log` records every file/network access for intrusion detection
- [x] **Secret scanning** — `inscript check --secrets file.ins` warns on hardcoded tokens, passwords, keys
- [x] **Dependency integrity** — SHA-256 lockfile for packages (`inscript.lock`), verify on install
- [x] `test_v210.py`

## ✅ v2.2.0 — Language Enhancements

**Status: SHIPPED (May 2026)**

**Goal:** Fill expressiveness gaps identified from real game projects.

- [x] **Operator overloading sugar** — `impl Add for Vec2 { fn +(other) }` syntax instead of `operator +`
- [x] **Destructuring in function params** — `fn f({x, y}: Vec2) { }` and `fn f([head, ...tail]: []) { }`
- [x] **Named return values** — `fn bounds() -> (min: float, max: float) { return (min: 0, max: 1) }`
- [x] **`with` expression** — `let v = with Vec2{x: 1} { .y = 2 }` — clone-and-modify pattern
- [x] **String templates (multiline)** — `let sql = """ SELECT * FROM ... """`
- [x] **Compile-time constants** — `const PI: float = 3.14159` evaluated at parse time, inlined in bytecode
- [x] **`is` type-check expression** — `if val is Vec2 { ... }` (complement to type-narrowing match)
- [x] **Chained comparisons** — `0 < x < 10` desugars to `0 < x && x < 10`
- [x] **Null-coalescing assignment** — `x ??= default_val`
- [x] **Labelled loops** — `outer: while true { inner: for i in 0..5 { break outer } }`
- [x] `test_v220.py`

## ✅ v2.3.0 — Concurrency & Async

**Status: SHIPPED (May 2026)**

**Goal:** Real async support for networked games, servers, and IO-heavy scripts.

- [x] **`async/await`** — wire to Python asyncio; `async fn fetch(url)`, `await http.get(url)`
- [x] **`spawn` keyword** — `spawn fn()` creates a coroutine; returns a handle
- [x] **`channel<T>`** — typed message-passing: `let ch = channel<int>(capacity: 10)`
- [x] **`select` expression** — multiplex over channels: `select { case ch1 -> v { } case ch2 -> v { } }`
- [x] **Async iterators** — `async for item in stream { }` for event streams, WebSocket frames
- [x] **`mutex` and `rwlock`** — `let m = mutex(value); m.lock(fn(v) { v.count += 1 })`
- [x] **Timer builtins** — `timer.after(1000, fn() { })`, `timer.every(16, fn() { })`
- [x] `test_v230.py`

## ✅ v2.4.0 — Native & WebAssembly Targets

**Status: SHIPPED (May 2026)**

**Goal:** Ship InScript games to web and native without Python runtime dependency.

- [x] **WASM compilation target** — `inscript build --target wasm file.ins` outputs `.wasm` + JS glue
- [x] **Native binary output** — compile to C via transpilation, then `gcc`/`clang`; no Python needed at runtime
- [x] **Pyodide bundle optimisation** — tree-shake stdlib, lazy-load modules; reduce playground load time from ~3s to <1s
- [x] **Ahead-of-time (AOT) compilation** — `inscript compile file.ins` → `.ibc` bytecode; `inscript run file.ibc`
- [x] **Incremental compilation** — cache `.ibc` per file, recompile only changed files
- [x] **Dead code elimination (IR level)** — whole-program DCE before code generation
- [x] **Inline caching** — monomorphic call sites cached at runtime for 2-4x method call speedup
- [x] `test_v240.py`

## ✅ v2.5.0 — IDE & Editor Integration

**Status: SHIPPED (May 2026)**

**Goal:** First-class IDE support making InScript as pleasant as TypeScript to work with.

- [x] **LSP v2** — go-to-definition, find-all-references, rename symbol, document symbols
- [x] **Hover types** — hover any expression to see inferred type
- [x] **Inline diagnostics** — squiggly underlines for errors + warnings in real time
- [x] **Auto-import** — type `Vec2` → LSP offers `import "math" as math`
- [x] **Code actions** — quick fix: add missing interface method, rename to fix typo
- [x] **Semantic tokens** — richer syntax highlighting (function calls vs variable reads)
- [x] **VS Code extension v2** — publish to marketplace as `inscript-lang.inscript`
- [x] **Neovim plugin** — `inscript.nvim` via nvim-lspconfig
- [x] **Debugger (DAP)** — breakpoints, step-over/into/out, variable watch via Debug Adapter Protocol
- [x] `test_v250.py` (LSP integration tests)

## ✅ v2.6.0 — Package Ecosystem

**Status: SHIPPED (May 2026)**

**Goal:** A real package registry so the community can share InScript libraries.

- [x] **`inscript.toml`** — project manifest: name, version, dependencies, scripts
- [x] **`inscript install pkg@1.0.0`** — download from registry, verify hash, add to `inscript.lock`
- [x] **`inscript publish`** — upload a package to registry (requires API key via `inscript --config set api_key`)
- [x] **Package registry** — hosted at `pkg.inscript.dev`; search by tag (game, math, physics, ui)
- [x] **Scoped packages** — `@authorss81/ecs`, `@community/pathfinding`
- [x] **`inscript audit`** — scan installed packages for known vulnerabilities
- [x] **Monorepo support** — `workspace = ["packages/*"]` in `inscript.toml`
- [x] **Private registries** — `inscript config set registry https://internal.example.com`
- [x] **Stdlib versioning** — pin stdlib version in `inscript.toml` for reproducible builds
- [x] `test_v260.py` (package manager integration tests)

## ✅ v2.7.0 — Scene System

**Status: SHIPPED (May 2026)**

**Goal:** A proper scene tree that v3.0.0 Studio can edit. Without this the Studio's scene editor has nothing to work with.

- [x] **`node` keyword** — `node PlayerNode { _ready() {} _update(dt) {} _draw() {} }` — lexer, parser, `NodeDecl` AST
- [x] **`NodeBlueprint`** — immutable compiled description; registered in interpreter env by name
- [x] **`NodeInstance`** — live instance; isolated `_props` dict so 100s of instances can coexist
- [x] **`_ready` / `_update(dt)` / `_draw`** — node lifecycle hooks with depth-first propagation
- [x] **Scene tree ops** — `add_child`, `remove_child`, `get_node`, `get_children`, `child_count`, reparenting
- [x] **`SceneTree`** — root container; drives `start` / `update(dt)` / `draw` / `stop`
- [x] **`SceneManager`** — `switch_to`, `push`, `pop`, scene stack, frame-safe pending transitions
- [x] **`scene_manager`** — bound in game env; callable from .ins scripts
- [x] **`.inscene` serialisation** — `save_inscene(tree, path)` / `load_inscene(path, sm)` — human-editable TOML-like format
- [x] **Backward compat** — legacy `scene GameScene { on_start ... }` unchanged
- [x] **`scene_tree.py`** — new module (450 lines)
- [x] `test_v270.py` (62/62)

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


---

## ✅ v2.8.0 — Asset Pipeline

**Status: SHIPPED (May 2026)**

**Goal:** `@texture`, `@sound`, `@tilemap`, `@font` annotations + `AssetRegistry`. Studio's asset browser needs this before v3.0.0.

- [x] **`AssetHandle`** — lazy-loading descriptor; type-validated; SHA-256 integrity; `exists()`, `reload()`
- [x] **`AssetRegistry`** — global singleton; `load_all(base_dir)`, `check_for_changes()` (mtime hot-reload), `clear()`
- [x] **`asset` stdlib module** — `asset.texture(path)`, `asset.sound(path)`, `asset.tilemap(path)`, `asset.font(path, size)`
- [x] **`@texture` / `@sound` / `@tilemap` / `@font`** — decorator form on `let` decl; special-cased in `visit_DecoratedDecl`
- [x] **`asset.registry`** proxy — `count()`, `all()`, `load_all()`, `export_manifest()`, `bundle()` callable from InScript
- [x] **`export_manifest(path)`** — writes `assets.toml` with type, path, SHA-256, exists for every asset
- [x] **`bundle(src, dest)`** — copies all referenced asset files; skip_missing flag; copy summary
- [x] **`--watch` hot-reload** — after each .ins save, calls `check_for_changes()` on all registered assets
- [x] **`--asset-manifest DIR`** — CLI command; runs .ins, dumps `assets.toml` to DIR
- [x] **`--bundle DIR`** — CLI command; runs .ins, copies assets to `DIR/dist/assets`
- [x] **`stdlib_assets.py`** — new module (240 lines)
- [x] `test_v280.py` (72/72)

---

## 🔮 v2.9.0 — Hot Reload

**Goal:** True state-preserving hot reload for game development iteration speed. Studio's live preview depends on this.

- [ ] **Module-level hot reload** — `inscript run --hot file.ins`; file watcher detects saves
- [ ] **Function patching** — reparse changed functions, patch interpreter env; running code picks up new version next frame
- [ ] **Struct/node method patching** — update method bodies on live instances without resetting props
- [ ] **`@hot_reload`** — opt-in annotation; skip reload for functions marked stable
- [ ] **State preservation** — `let` vars at scene level survive reload; struct instances keep field values
- [ ] **Reload boundary** — on syntax/type error, keep old version running; show error overlay in game window
- [ ] **Reload events** — `on_reload()` hook called after a successful hot reload (re-register assets, reset physics)
- [ ] `test_v290.py`

---

## 🔮 v2.10.0 — Physics & Multiplayer

**Goal:** The two feature categories Studio-tier games universally need.

- [ ] **`physics.world(gravity)`** — 2D physics world via `pymunk`
- [ ] **`physics.body(mass, shape)`** — dynamic / static / kinematic body
- [ ] **`physics.collider(body, shape)`** — attach shapes; circle, box, polygon, segment
- [ ] **Collision callbacks** — `on_collide(body_a, body_b, impulse)` registered per body
- [ ] **`physics.ray_cast(origin, dir, distance)`** — returns first hit body + normal
- [ ] **`net.connect(url)`** — WebSocket client (wraps asyncio + websockets)
- [ ] **`net.serve(port)`** — simple game server; handles N clients
- [ ] **`net.broadcast(data)`** — send to all connected peers
- [ ] **`net.sync(state_dict)`** — delta-compress and broadcast struct state
- [ ] **`net.on_message(fn)`** — callback on incoming message
- [ ] `test_v2100.py`

---

## 🔮 v2.11.0 — Export Pipeline

**Goal:** `inscript build` produces runnable artefacts. Studio's "Export Game" button needs this.

- [ ] **Project structure spec** — `project/src/`, `project/assets/`, `project/scenes/`, `inscript.toml`
- [ ] **`inscript build --target desktop`** — bundles Python + InScript runtime → `.exe` / `.app` / `.AppImage`
- [ ] **`inscript build --target web`** — game-oriented WASM (Pyodide + assets) with index.html shell
- [ ] **`inscript build --target android`** — APK via BeeWare Briefcase
- [ ] **Asset embedding** — all `@texture` / `@sound` / `@tilemap` assets bundled into output
- [ ] **Dependency bundling** — stdlib + installed packages embedded; no runtime install needed
- [ ] **Build manifest** — `build.toml` records target, version, asset hashes, entry point
- [ ] **`inscript new <name>`** — scaffold a new project with standard layout and starter scene
- [ ] `test_v2110.py`

---

## 🔮 v2.12.0 — Studio Readiness Gate

**Goal:** Prove the runtime is solid enough for v3.0.0 to build an Electron IDE on top of it.

- [ ] **60fps performance gate** — benchmark: 1000 active `NodeInstance`s, each with `_update`, at ≥60fps on mid-range hardware
- [ ] **Memory gate** — no leaks over 10-minute game loop (measured via `tracemalloc`)
- [ ] **Language stability audit** — zero open E0xxx regressions; all edge-case tests green
- [ ] **Electron bridge PoC** — `studio_bridge.py`: JSON-RPC server the Electron shell calls for run/stop/hot-reload/scene-list
- [ ] **Plugin API** — `inscript_studio_api.py`: stable extension points (scene serialise, asset list, error stream, breakpoint API)
- [ ] **Error stream** — structured JSON error output (`--json-errors`) for IDE error-panel consumption
- [ ] **Project introspection** — `inscript inspect project/` → JSON list of scenes, nodes, exports; consumed by Studio
- [ ] **v3.0.0 readiness checklist** — all 7 items above pass; gate script `inscript check-v3` exits 0
- [ ] `test_v2120.py`

---

## 🔮 v3.0.0 — InScript Studio (Long-term)
