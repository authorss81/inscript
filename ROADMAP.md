# InScript Roadmap — Microversion Plan

> **Current:** v3.9.4 — Phase 7 (Python AST transpilation) shipped. 67× game hook speedup.

---

## v3.9.5 — Resolve loose files

- [ ] Review + commit or delete untracked files: `bench_phase4.py`, `test_native_bindings.py`, `test_native_bindings2.py`
- [ ] Clean up stale build artifacts in `test_env/`, `dist/`, `__pycache__/`
- [ ] Remove dead Rust VM integration code from `pygame_backend.py` (`--rust-vm` flag, trial compilation)

## v3.9.6 — py_compiler compilation speed

- [ ] Profile `py_compiler.compile_hook()` — currently 2.4ms vs `compile_body` 0.7ms (3.4× slower)
- [ ] Cache `ast.fix_missing_locations()` tree reuse
- [ ] Lazy `_collect_names()` — only walk if names haven't changed
- [ ] Reduce `isinstance` dispatches in `_convert` (pre-compute method table)

## v3.9.7 — py_compiler feature parity

- [ ] `MatchStmt` → Python `match`/`case` (3.10+)
- [ ] F-string support (`"hello {name}"`)
- [ ] Lambda/closure expressions
- [ ] `ForExpr` (list comprehensions)
- [ ] `FunctionDecl` inside hooks (nested functions)
- [ ] Class method calls (`obj.method(args)` with named args)

## v3.9.8 — Sprite-heavy benchmark & blits validation

- [ ] Find or create a sprite-heavy `.ins` game (platformer, breakout, etc.)
- [ ] Validate `BatchedDrawNamespace.sprite()` → `Surface.blits()` works correctly
- [ ] Benchmark Phase 7 on sprite-heavy workload vs AST walker
- [ ] Fix any sprite transform bugs (alpha, rotation pivot, scale)

## v3.9.9 — Rust VM assessment

- [ ] Benchmark Rust VM (`--rust-vm`) vs Phase 7 on pong.ins hooks
- [ ] If Rust VM is slower: deprecate, remove from game path, keep for `.ibc`/`--compile`
- [ ] If Rust VM is faster: document when to use each path
- [ ] Remove `_ast_to_source` and trial compilation (already dead code)

## v3.10.0 — Phase 8: Studio integration

- [ ] Wire Phase 7 compilation into Studio's live-preview / hot-reload
- [ ] Show "compiled" badge per hook in Studio scene inspector
- [ ] Expose `--profile` hook-level timing in Studio debug panel

---

**Longer-term (post-v3.10.0):**
- InScript→Python transpilation of entire scripts (not just game hooks)
- WASM target for web deployment
- TypeScript type definitions for `.ins` files
