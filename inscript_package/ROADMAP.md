# InScript Language Roadmap

> **Current version:** v1.0.7 (March 2026)
> **Tests passing:** 501 (270 Ph5 + 145 Ph6 + 32 Ph7 + 54 Audit)
> **Stdlib modules:** 59
> **Status:** Active development — language is usable, bugs being fixed iteratively

---

## ✅ Shipped — v1.0.x (March 2026)

### Core Language
- [x] `let` / `const` with type annotations and inference
- [x] Functions, closures, lambdas, default params, variadics, named args
- [x] Generic functions `fn id<T>(x: T) -> T`
- [x] Structs with inheritance, mixins, properties, static fields/methods
- [x] Abstract methods enforced at instantiation
- [x] Operator overloading
- [x] Generic structs `struct Stack<T> { items: [] }` — bare literal defaults
- [x] `pub` / `priv` modifiers on struct fields (parsed, not yet enforced)
- [x] Struct `.copy()`, `.to_dict()`, `.has(field)` built-ins
- [x] ADT Enums with data fields
- [x] Pattern matching with guards, binding, typed catch
- [x] Array/tuple/struct destructuring
- [x] Array comprehensions
- [x] Dict comprehensions `{k: v*2 for k in arr if cond}`
- [x] Coroutines / generators `fn* counter(n) { yield i }`
- [x] `async fn` — executes synchronously, warns user (DESIGN-01 acknowledged)
- [x] Decorators `@name` and `@name(args)`
- [x] Error propagation `?` with `Ok` / `Err` / `Result`
- [x] `comptime` evaluation
- [x] Interfaces with `implements` checking and default methods
- [x] `super` keyword for parent method dispatch
- [x] `finally` block in try/catch
- [x] `do-while` loops
- [x] `for-else` / `while-else`
- [x] Multi-variable for — `for k, v in entries(d) { }`

### Built-ins
- [x] `assert(cond, msg)`, `panic(msg)`, `unreachable(msg)` — new v1.0.5
- [x] `typeof(v)` — returns clean names: `"int"` `"string"` `"array"` `"function"` `"range"` etc.
- [x] `entries(d)` — works on dicts and struct instances
- [x] `sort(arr)` in-place; `sorted(arr)` returns copy; both accept key fn

### Array Instance Methods (v1.0.6)
- [x] `flat_map` `zip` `count(fn)` `any(fn)` `all(fn)` `each` `sum` `min_by` `max_by` `group_by` `unique`
- [x] (plus all existing: `map` `filter` `reduce` `find` `sort` `reverse` `push` `pop` `join` etc.)

### String Instance Methods (v1.0.6)
- [x] `reverse` `repeat` `pad_left` `pad_right` `format` `is_empty` `count` `index` `substr` `char_at`
- [x] (plus all existing: `upper` `lower` `trim` `split` `replace` `contains` `starts_with` etc.)

### Execution Engines
- [x] Tree-walk interpreter (default, full feature support)
- [x] Register-based bytecode VM (`.vm` mode, matches interpreter behaviour)
- [x] IBC bytecode save/load

### Static Analyzer (live in REPL)
- [x] Undefined variables, const reassignment, return type mismatches
- [x] Non-exhaustive match, unreachable code, shadowed variables
- [x] Arg-count mismatch warnings (v1.0.5)
- [x] Missing-return in typed functions (v1.0.6)
- [x] Async fn synchronous warning (v1.0.6)

### Standard Library — 59 Modules
Core: `math` `string` `array` `json` `io` `random` `time` `debug`
Data: `csv` `regex` `xml` `toml` `yaml` `url` `base64` `uuid`
Format/Iter: `format` `iter` `template` `argparse`
Net/Crypto: `http` `ssl` `crypto` `hash` `net`
FS/Process: `path` `fs` `process` `compress` `log`
Date/Collections: `datetime` `collections` `database`
Threading/Bench: `thread` `bench`
Game Visual: `color` `tween` `image` `atlas` `animation` `shader`
Game IO: `input` `audio`
Game World: `physics2d` `tilemap` `camera2d` `particle` `pathfind`
Game Systems: `grid` `events` `ecs` `fsm` `save` `localize` `net_game`
Utilities: `signal` `vec` `pool`

### REPL and Tooling
- [x] Pixel-art ASCII banner with gradient, `.help`, `.modules`, `.doc <any of 59 modules>`
- [x] Live arg-count + missing-return analysis pass on every input
- [x] Deprecated builtin warnings (`is_str`, `stringify`, `dict_items`, `is_null`)
- [x] Unqualified import warning
- [x] LSP server, VS Code extension, package manager
- [x] Complete REPL tutorial covering all 59 modules

---

## 🔄 In Progress — v1.0.x patches

- [ ] `pub`/`priv` actual enforcement at runtime
- [ ] `async`/`await` — either implement with asyncio or formally deprecate
- [ ] Generic type enforcement — `Stack<int>` should reject non-int values
- [ ] Type mismatch at call-site not caught by analyzer
- [ ] Duplicate function definition detection
- [ ] VM error line numbers (still Line 0 in some error paths)

---

## 📋 v1.1.0 — Stability (Q2 2026)

- [ ] `inscript fmt` — auto-formatter
- [ ] `inscript doc` — generate docs from `///` comments
- [ ] `inscript check` — static analysis without executing
- [ ] Watch mode `inscript --watch file.ins`
- [ ] Better error messages with fix suggestions
- [ ] Source maps for stack traces
- [ ] Web playground (hosted)
- [ ] REPL multi-line paste mode
- [ ] `match` on ranges: `case 1..10 { }`
- [ ] Expand `test` module with runner CLI
- [ ] 600+ tests target

---

## 🔮 v1.2.0 — Type System (Q3 2026)

- [ ] Union types `type Shape = Circle | Rectangle`
- [ ] Type aliases `type ID = int`
- [ ] Generic constraints `<T: Numeric>`
- [ ] Type narrowing in match arms
- [ ] Recursive types

---

## 🚀 v1.3.0 — Performance / Phase 6.2 (Q4 2026)

- [ ] Profile real game-loop hot paths (not microbenchmarks)
- [ ] C extension for inner-loop operations (env lookup, dispatch, arithmetic)
- [ ] Bytecode optimisation pass (constant folding, dead code elimination)
- [ ] Tail call optimisation (lift Python 1000-frame stack limit)
- [ ] Target: 5–15× speedup over current interpreter

> **Why not now?** The VM is currently 3× slower than the interpreter due to Python
> dispatch overhead. Build the C layer only after language correctness is fully proven
> and real profiling data identifies the actual bottleneck. Optimising the wrong thing
> now wastes weeks and locks in unstable APIs.

---

## 🌐 v2.0.0 — Native/WASM (2027)

- [ ] JIT via LLVM (experimental)
- [ ] Native binary output via Cython/Nuitka bridge
- [ ] WASM target for browser-based InScript
- [ ] Static type checker as separate pass
- [ ] Package registry at inscript-lang.dev
- [ ] Official game templates

---

## Timeline

```
Mar  2026   v1.0.6   Ongoing patches — 59 modules, 501 tests, all major VM bugs fixed
Q2   2026   v1.1.0   Stability: formatter, checker, 600+ tests, web playground
Q3   2026   v1.2.0   Type system: unions, aliases, generic constraints
Q4   2026   v1.3.0   Phase 6.2 performance: C extension, TCO, bytecode opts
2027        v2.0.0   JIT, WASM, native binary, package registry
```

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| v1.0.0 | 2026-03-04 | Initial stable release — full language + 18 stdlib + VM + LSP |
| v1.0.1 | 2026-03-08 | VM fixes (BUG-01–05), REPL improvements |
| v1.0.2 | 2026-03-10 | 20 bug fixes (BUG-06–30), 56 stdlib modules, 501 tests |
| v1.0.3 | 2026-03-13 | Pixel-art banner, tween/iter/collections fixes, interface defaults |
| v1.0.4 | 2026-03-14 | `.doc` all 59 modules, dict comprehensions, `do-while`, struct `.copy()` |
| v1.0.5 | 2026-03-14 | `pub` fields, `for-else`, `assert`/`panic`, generics bare defaults, arg-count warnings |
| v1.0.6 | 2026-03-14 | `typeof` clean names, 21 new array/string methods, struct print, missing-return + async warnings |
| v1.0.7 | 2026-03-14 | `x in arr/dict/string`, `not in`, 15 new methods, for/while/do-while in VM, full audit update |
