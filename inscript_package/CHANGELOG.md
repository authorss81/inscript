# InScript Changelog

All notable changes are documented here. Follows [Semantic Versioning](https://semver.org/).

---

## [1.9.11] — 2026-05-09

### Real async I/O stdlib

- **`http.get_async(url: string) -> Promise<string>`** — async HTTP GET via `asyncio` + `urllib.request`. Returns the response body as a string. Times out after 10s. Errors are catchable via `try/catch`.
- **`file.read_async(path: string) -> Promise<string>`** — async file read via `asyncio` + `run_in_executor`. Returns full UTF-8 file content.
- **`file.write_async(path: string, content: string) -> Promise<bool>`** — async file write. Returns `true` on success.
- **`file` module** added with both sync (`read`, `write`, `exists`) and async variants.
- **`timer.sleep(ms: int) -> Promise<nil>`** — async sleep for `ms` milliseconds via `asyncio.sleep`. Use `await timer.sleep(500)` in any async function.
- **`timer` module** added: `sleep`, `sleep_sync`, `now` (ms epoch), `now_sec` (float seconds).
- **`http.get_async`** added to existing `http` module alongside `get` and `post`.
- **Analyzer**: `http`, `file`, `timer` registered as builtin module symbols. Method calls `http.get_async`, `file.read_async`, `file.write_async`, `timer.sleep` infer `Promise<string>` / `Promise<bool>` / `Promise<nil>` return types.
- All three new async functions return real `InScriptCoroutine` objects — `await` drives them to completion.

---



### v2.0.0 Readiness Gate — `inscript check-v2`

- **`inscript --check-v2 [DIR]`** — new command that runs 8 pre-v2.0.0 readiness gates on a project directory and reports ✅/❌ per gate.
- **Gates checked:**
  1. `div` keyword removed — no `.ins` files use `div` (E0056)
  2. `null` keyword removed — no `.ins` files use `null` (E0055)
  3. bare `array` annotation removed — use `Array<T>` instead
  4. `#` line comments — no files still use `//` as comments
  5. `async/await` is real — `InScriptCoroutine` present (v1.9.7 applied)
  6. `Array<T>` type inference present — array_type helper works (v1.9.8 applied)
  7. `inscript.lock` present in project dir
  8. `inscript.toml` present in project dir
- **Exit code 0** = all hard gates pass (warnings allowed); **exit code 1** = one or more failures.
- **Pure addition** — no existing code was rewritten; only `_check_v2_readiness()` added and `--check-v2` argument wired.

---



### Package manager hardening

- **`inscript install PKG@version`** — version pinning: `inscript --install math-utils@1.2.0` installs exactly that version and writes it to `inscript.lock`.
- **`inscript install` (no args)** — reads `[dependencies]` from `inscript.toml` and installs every listed package. If `inscript.lock` exists, uses its pinned versions.
- **`inscript update PKG`** — removes existing installation and reinstalls at latest (or `PKG@version`). Updates `inscript.lock` entry.
- **`inscript outdated`** — compares `inscript.lock` pinned versions against the registry and reports which packages have updates available.
- **Offline mode** — if the registry is unreachable, `install` checks `inscript.lock` for a pinned version record and reports it rather than hard-failing.
- **Lock file integration**: `_write_lock_entry` / `_read_lock` / `_remove_lock_entry` helpers added — all package operations now read and write `inscript.lock` consistently.
- **`_parse_pkg_spec`** helper — parses `PKG@version` into `(name, version)` tuple, used throughout.

---



### Type inference hardening + missed test fixes

- **Array literal inference**: `[1, 2, 3]` → `Array<int>`, `[1.0, 2.5]` → `Array<float>`. Mixed-type arrays `[1, "two"]` now correctly infer `Array<any>` instead of `Array<first_type>`.
- **`inscript --infer-types FILE`**: new CLI flag — parses and type-checks FILE then prints the inferred type of every `let`/`const` declaration. Useful for debugging inference.
- **`test_phase1.py`, `test_v12.py`, `test_v170.py` added to CI workflows** — these files existed but were never included in the workflow runs, allowing `div`-related failures to reach GitHub Actions undetected. All three are now in both `test.yml` and `publish.yml`.
- **`div` fixed in `test_phase1.py` and `test_v12.py`** — the `v1.2 div keyword` section and `v1.1 floor div` regression test were still running `div` in InScript source strings; updated to `//` (the correct operator since v1.9.5).

---



### True async/await via asyncio

- **`async fn`** declarations now produce real Python coroutines at call time, not synchronous stubs. Calling an `async fn` returns an `InScriptCoroutine` object.
- **`await expr`** drives the coroutine to completion using `asyncio.run()`. Plain `await value` (non-coroutine) is a passthrough — backwards-compatible.
- **`Promise<T>`** added to the type system. The analyzer marks `async fn` return types as `Promise<T>` where `T` is the declared or inferred return type.
- **`InScriptCoroutine`** class added to `stdlib_values.py` — holds the Python coroutine and function name for repr/error messages.
- Multiple sequential `await` calls in the same function work correctly.
- Nested async calls (async fn calling async fn with await) work correctly.

---



### Breaking: `#` line comments; `//` always floor division

- **`#` is now the line-comment character** — `# this is a comment`, `let x = 5 # inline`. This matches Python, Ruby, Shell, and TOML — immediately familiar to any reader.
- **`//` is always floor division**, regardless of surrounding spaces — `10 // 3 == 3`, `10//3 == 3`, `a // b == a // b`. The old space-sensitive rule (space before `//` → comment) is completely removed.
- **`/* */` block comments** are unchanged.
- **`inscript migrate`** updated with two new rules: (1) standalone `// comment` lines → `# comment`, (2) inline ` // word` → ` # word`. Does not touch `x // 2` style floor division.
- **Migration path**: run `inscript migrate <file>` — all `//` comment usages are auto-converted to `#`.

### Why now
The old rule made `10 // 3` silently return `10` if there was a space before `//`, producing wrong answers with no error. Any auto-formatter adding spaces would silently break code.

---



### Breaking: `div` keyword removed (E0056)

- **`div` is now a hard parse error** — `10 div 3` raises `[E0056] 'div' was removed in v1.9.5 — use '//' for integer division`. This was deprecated since v1.7.1 when `//` was introduced.
- **E0056 `DivKeyword`** added to error catalogue and `errors.py` registry.
- **`inscript migrate`** already rewrites `div → //` — no change needed there; the tool has handled this since v1.7.4.
- **`inscript compat`** check message updated to say "removed in v1.9.5 (hard error)" rather than "v2.0.0".
- **Migration path**: run `inscript migrate <file>` before upgrading; all `div` uses are auto-rewritten to `//`.

---


## [1.8.1] — 2026-05-04

### Union Types & Optionals

- **`int | string` union type** — declared in `let`, `const`, function params, return types, and struct fields; enforced at static analysis time
- **`T?` optional shorthand** — `int?` is full sugar for `int | nil` in all positions
- **Union assignment** — both member types are accepted; non-members are a `SemanticError`
- **Argument type checking** — `visit_CallExpr` now validates each argument against its declared param type (union-aware); previously only arg *count* was checked
- **Union narrowing** — `if typeof(x) == "int" { }` narrows `x` to `int` inside the then-branch; uses a scope shadow so the narrowed binding is visible to all body statements
- **Nested union flattening** — `union_type((int|string), bool)` → `Union<int, string, bool>`; single-member unions collapse to the plain type
- **`types_compatible` upgraded** — handles `Union` on both sides, `T?` nil-check, int→float widening inside unions
- **`union_type()`, `optional_type()`, `union_members()`** — new helpers in `analyzer.py`
- **`E0055` in `BUILTIN_TYPES`** — `null` and `nil` both resolve to `T_NULL` cleanly

---



### REPL Stability

- **Error recovery** — after a runtime error all previously-defined globals survive; partial side-effects from the failed block are rolled back via an env snapshot/restore on every `_eval()` call
- **`let` re-definition** — `let x = 1` followed by `let x = 2` in the REPL re-binds without error (`_repl_mode` flag on the root environment)
- **`null` hard error** — `null` now emits `E0055` with an explicit error code, consistent with the full error-code registry
- **`inscript migrate FILE`** — rewrites `null → nil`, `div → //`, `: [] → : array` in-place; was wired in v1.7.3, now promoted and fully documented

### Bug Fixes
- `E0055` added to `ERROR_CODES` registry in `errors.py`
- `visit_NullLiteralExpr` raises `InScriptRuntimeError(code="E0055")` directly instead of routing through `_error()` so the code is always stamped correctly

---

## [1.7.3] — 2026-05-03

### Stack Traces — Full Call Chain in Error Output

- **Source snippets per frame** — every call-stack frame now shows the exact source line being executed, matching Python's traceback style:
  ```
  Call stack (most recent last):
    File "<script>", line 9, in outer
      middle()
    File "<script>", line 6, in middle
      inner()
    File "<script>", line 3, in inner
      throw "deep error"
  ```
- **Accurate line numbers in nested closures and lambdas** — `Interpreter.visit()` now overrides `Visitor.visit()` and calls `_call_stack.update_top_line(node.line)` on every node dispatch; frames track the *currently executing* line, not just the call-site
- **`InScriptCallStack` enhanced** — accepts `src_lines` at construction; `push()` stores the source snippet for each frame; `update_top_line()` updates both line and snippet as execution proceeds
- **`CallFrame` upgraded** — `source_line: str` slot added; `as_tuple()` unchanged for backwards compatibility
- **Stack trace shown by default** — already printed via `InScriptError._format()` / `call_trace`; now includes source snippets without requiring `--debug`

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

## [1.8.2] — 2026-05-04

### Type Aliases, Literal Types & fn Types

- **`type ID = T`** — type aliases fully enforced in `let`, `const`, function params, return types, and struct fields; aliases are hoisted in a pre-pass so functions can reference an alias declared after them
- **`type Dir = "left" | "right"`** — union-of-string-literals; passing any non-member literal is a `SemanticError`
- **`type Pred = fn(int) -> bool`** — function type aliases; any `fn` literal or named function is accepted at the call site
- **Inline literal types** — `fn move(d: "left" | "right")` works directly without a named alias; invalid string arguments are caught statically
- **`visit_StringLiteralExpr` returns `literal_type()`** — string literals now carry their value as a type so literal-union checking is exact
- **Chained aliases** — `type UID = PlayerID` where `PlayerID` is itself an alias resolves correctly
- **`_hoist_top_level` two-pass** — aliases and structs registered first, functions second; eliminates "Unknown type" errors when a function's return type references an alias declared earlier in the file
- **New helpers** — `literal_type()`, `fn_type()`, `is_literal_type()`, `literal_value()` in `analyzer.py`
- **`TypeAnnotation`** — gained `literal_value`, `fn_params`, `fn_return` fields
- **`TypeAliasDecl`** — gained `type_ann: TypeAnnotation` field (backwards-compatible; `target: str` kept)
