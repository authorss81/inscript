# Phase 7 Roadmap — Real Game Loop Optimization

## The Problem

Benchmarks on pong.ins (Phase 6) revealed the hard truth:

| Execution path | on\_update | on\_draw | Combined (1000 frames) |
|:---|---:|---:|---:|
| AST tree‑walk | 34.6 µs | **2153 µs** | 1065 ms |
| Bytecode VM (Python) | 23.7 µs | **2772 µs** | 2398 ms |
| **VM vs AST** | **1.5× faster** | **0.8× slower** | **0.4× slower** |

The Python bytecode VM **loses to the tree‑walk interpreter** — pure‑Python opcode dispatch (while + if/elif + register bounds checks) is irreducibly slower than CPython method call dispatch. Of the ~2.6 ms per frame, **>95 %** is spent in `on_draw` → pygame draw calls, not script dispatch.

Industry research confirms this:
- **dubroy (2024)**: bytecode interpreter in TypeScript **2–3× slower** than tree‑walk on V8.
- **liquidev (Rust VMs, 2023)**: register‑based switch VM is **4× faster** than tree‑walk, but **only in Rust** (computed goto). Pure‑Python cannot match this.
- **CPython's own eval loop** runs in C (`ceval.c`) — a Python‑on‑Python bytecode VM suffers double interpretation.

## The Strategy

**Stop trying to speed up dispatch. Remove dispatch entirely.**

Instead of interpreting AST nodes or bytecodes at runtime, **compile InScript game hooks to Python code objects** at load time. The generated code runs directly in CPython's C-coded evaluation loop — the same speed as hand‑written Python.

This approach is used by **CoffeeScript → JavaScript**, **TypeScript → JavaScript**, and **Haxe → multiple targets**. All of them transpile to the host language and achieve **native-speed execution** with no runtime interpreter overhead.

### Expected speedup

| Workload | vs tree‑walk | Reason |
|:---|---:|:---|
| Compute (on\_update) | **5–50×** | CPython C‑coded eval loop vs Python method dispatch |
| Draw‑heavy (on\_draw) | **1–2×** | Still bound by pygame C calls, but dispatch overhead eliminated |
| Combined game loop | **~3–10×** | |

---

## Plan

### P7.1 — InScript → Python AST Compiler  `py_compiler.py`

New module that converts InScript AST nodes (`ast_nodes.*`) to Python AST nodes (`ast.*`):

**Input**: `BlockStmt`, `ExprStmt`, `VarDecl`, `AssignExpr`, `IfStmt`, `WhileStmt`, `ForInStmt`, `BinaryExpr`, `UnaryExpr`, `CallExpr`, `GetAttrExpr`, `IdentExpr`, literals, `ReturnStmt`, `BreakStmt`, `ContinueStmt`

**Output**: `ast.FunctionDef` containing the converted body, with:
- InScript `let` → Python local variables
- InScript function calls → Python function calls (same name/obj lookup)
- InScript `if` / `while` → Python `if` / `while`
- InScript `null` → Python `None`
- InScript operators → Python operators (with div/floor-div mapping)
- Game namespace objects (`draw`, `screen`, `input`) passed as closure or globals

**Key design decisions:**
- Wraps every hook in a `def _hook(dt):` so Python uses `LOAD_FAST`/`STORE_FAST` (3–4× faster than module‑level `LOAD_NAME`)
- `compile()` at load time, `exec()` into a callable once — zero per‑frame compilation overhead
- Falls back to AST walker on any error

**Expected output format:** `PyCodeHook(code_object, param_names)`

### P7.2 — Hook Execution Router  `game_engine.py` (refactor)

Replace the current `run_hook_compiled` / AST fallback with a three‑path router:

```
              ┌──────────────────────────────┐
              │  Hook at load time            │
              └──────────┬───────────────────┘
                         │
              ┌──────────▼──────────┐
              │  Try py_compiler    │
              │  compile → code obj │
              └──────────┬──────────┘
                    ┌────┴────┐
                    ▼         ▼ no
              ┌─────────┐  ┌────────┐
              │ Python  │  │ Try    │
              │ code obj│  │ Rust   │
              │ callable│  │ compile│
              └─────────┘  └───┬────┘
                              ┌┴┐
                              ▼ ▼ no
                         ┌─────────┐
                         │ Fallback│
                         │ AST     │
                         │ walker  │
                         └─────────┘
```

- Python code‑object path is preferred (fastest)
- Rust VM path is backup (when parser supports the syntax)
- AST walker is last resort (when both compilers fail)
- Bytecode VM (Path B) is **removed** for game hooks — it's slower than the AST walker

### P7.3 — Native Draw Call Batching  `BatchedDrawNamespace` rewrite

Current `BatchedDrawNamespace` queues individual ops and calls flush. Rewrite to use **pygame's native batch APIs**:

- Replace per‑op `pygame.draw.rect()` calls with `Screen.blits()` for texture draws
- Batch same‑type draw ops together (all rects → one batch, all circles → one batch)
- Group by color to minimize SDL render state changes
- Use `pygame.Rect` pooling to reduce allocation overhead

**Expected gain**: 30–50% reduction in draw‑call overhead for scenes with many primitives.

### P7.4 — Deprecate Python Bytecode VM for Game Path

- Remove `compile_body` / `VMClosure` / `VM.call` from the game hook code path
- Keep the bytecode VM for REPL and direct `--compile` / `.ibc` file execution (non‑game use)
- The compiler (`compiler.py`) stays — it's needed for Rust VM compatibility and `.ibc` output
- Update `pygame_backend.py` to never use `run_hook_compiled`

### P7.5 — Profile‑Guided Path Selection (stretch)

After P7.2 is stable, add a profiling warmup:
- Run the first 60 frames through both the Python code‑object AND the AST walker
- Track per‑frame µs for each path
- Pick the faster path for the remaining session
- Log the selection to stderr (`--verbose` flag)

This accounts for edge cases where the generated Python code has unexpected overhead (e.g., very large dict literals) and the AST walker might be faster.

---

## Success Criteria

| Metric | Current (VM path) | Target (Phase 7) |
|:---|---:|---:|
| on\_update | 23.7 µs | **<10 µs** (CPython native) |
| on\_draw | 2772 µs | **<1500 µs** (dispatch eliminated + batching) |
| Combined per frame | 2591 µs | **<1500 µs** |
| Budget used (60 fps) | 15.5 % | **<9 %** |
| Theoretical max fps | 386 | **>600** |
| Draw batching overhead | 3.5 µs (+63 %) | **<1 µs** (native blits) |

---

## Non‑goals

- **Full language transpilation**: Only game hooks (on\_update, on\_draw, on\_start, on\_exit). The REPL and standalone scripts keep using the existing interpreter.
- **JIT compilation**: Tracing JITs (LuaJIT‑style) are extremely complex and require warmup time. The Python `compile()` approach gives near‑native speed with zero warmup.
- **Removing the Rust VM**: Keep it for when the parser supports the full language — but don't gate anything on it.
- **PyPy support**: PyPy + pygame historically underperforms CPython + pygame due to CFFI overhead (0.72–0.95× in real games). Stay CPython‑focused.

## References

- CoffeeScript compilation model: https://coffeescript.org/
- dubroy (2024) — Bytecode vs Tree‑walk in TypeScript
- liquidev (2023) — Rust VM performance analysis
- pygame `blits()` benchmark (PR #439): ~15 % faster than per‑surface blit
- Godot 2D batching docs: https://docs.godotengine.org/en/stable/tutorials/2d/2d_optimization.html
- Marr et al. (2023 OOPSLA) — AST vs Bytecode on GraalVM
