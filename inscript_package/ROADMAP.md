# InScript Roadmap

## Released

### ✅ v1.0.0 — Stable Release (2026-03-04)

The complete language. Everything below is shipped and working.

**Core language**
- [x] `let` / `const` with type annotations + inference
- [x] Functions, closures, lambdas, default params, variadics
- [x] Generic functions `fn id<T>(x: T) -> T`
- [x] Structs with inheritance, mixins, properties, static methods
- [x] Abstract methods (enforced at instantiation)
- [x] Operator overloading
- [x] Generic structs `struct Stack<T>`
- [x] ADT Enums with data fields
- [x] Pattern matching with guards
- [x] Array/tuple destructuring
- [x] Array comprehensions
- [x] Coroutines / generators
- [x] Async / await
- [x] Decorators `@name`
- [x] Error propagation `?` + `Ok` / `Err` / `Result`
- [x] Comptime evaluation
- [x] Interfaces + `implements` checking

**Operators & expressions**
- [x] Ternary `?:` and `if x then a else b`
- [x] Null coalescing `??`
- [x] Optional chaining `?.`
- [x] Pipe operator `|>`
- [x] Floor division `//`
- [x] Array spread `[...arr]`
- [x] String indexing and slicing
- [x] F-string brace escapes
- [x] Labeled break/continue
- [x] String repeat

**Control flow**
- [x] `for v in range / array / enum`
- [x] Multi-catch
- [x] `select` statement with channels

**Standard library (18 modules)**
- [x] `math`, `string`, `array`, `io`, `json`, `random`, `time`
- [x] `color`, `tween`, `grid`, `events`, `debug`
- [x] `http`, `path`, `regex`, `csv`, `uuid`, `crypto`

**Tooling**
- [x] LSP server (diagnostics, completions, hover)
- [x] Package manager (install, remove, search, info)
- [x] Enhanced REPL (.type, .modules, .packages, .time, .save, .load)
- [x] VS Code extension (syntax highlighting, snippets)
- [x] 331 tests passing

---

## Planned

### v1.1.0 — Developer Experience (Q3 2026)

- [ ] `inscript fmt` — auto-formatter
- [ ] `inscript doc` — generate HTML docs from `///` comments
- [ ] REPL: multi-line paste mode
- [ ] Better error messages with fix suggestions
- [ ] Watch mode `inscript --watch file.ins`
- [ ] Source maps for stack traces
- [ ] Web playground (hosted at inscript-lang.dev)

### v1.2.0 — Type System (Q4 2026)

- [ ] Union types `Shape = Circle | Rectangle`
- [ ] Intersection types `T & U`
- [ ] Type aliases `type ID = int`
- [ ] Recursive types
- [ ] Improved generic constraints `<T: Numeric>`
- [ ] Type narrowing in match arms

### v2.0.0 — Performance (2027)

- [ ] Bytecode compiler + VM (10–50× speedup)
- [ ] Static type checker (separate pass, zero-overhead)
- [ ] WebAssembly target
- [ ] JIT compilation via LLVM (experimental)
- [ ] Native binary output (via Cython/Nuitka bridge)

---

## Timeline

```
Mar 2026   v1.0.0   Stable release — full language + 18 stdlib modules + LSP
Q3  2026   v1.1.0   Developer tooling (formatter, docs, watch mode)
Q4  2026   v1.2.0   Type system improvements (unions, intersections, aliases)
2027       v2.0.0   Bytecode VM + static checker + WASM target
```
