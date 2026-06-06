# InScript v3.9.1 — Build Notes

## What changed from v3.8.2 + v3.9.0

### Files REPLACED / UPDATED from v3.9.0
| File | Reason |
|------|--------|
| `rust_vm_engine/` (entire crate) | New v3.9.0 VM with compiler passes; version bumped to 3.9.1 |
| `inscript_rust_parser/` (entire crate) | New v3.7.3 parser replacing old flat src/ |
| `inscript_unified_hybrid.py` | Updated Rust-Python bridge from v3.9.0 |
| `test_all_150_bugs_FINAL.py` | Final consolidated test suite from v3.9.0 |
| `CHANGELOG.md` | Updated changelog |
| `Cargo.toml` | Replaced single-crate lexer with workspace (2 crates) |
| `inscript.toml` | Version bumped to 3.9.1 |
| `VERSION.txt` | Updated |

### Files ADDED (new in v3.9.1)
| File | Reason |
|------|--------|
| `rust_vm_engine/src/ir.rs` | LLVM IR emitter — v3.9.1 headline feature |
| `OPTIMIZATION_SUMMARY.md` | From v3.9.0 build |
| `OPTIMIZATION_APPLIED_V3.9.0.md` | From v3.9.0 build |
| `PHASE3_INTEGRATION_COMPLETE.md` | From v3.9.0 build |

### Files REMOVED
| File | Reason |
|------|--------|
| `src/` (old flat Rust lexer crate) | Superseded by `inscript_rust_parser/` |

### Python Core (unchanged from v3.8.2)
All Python files, tests, LSP, packages, docs, ast_cache, error_recovery, lsp/,
inscript-packages/, hybrid_architecture/, and the full 150-bug test suite are
**unchanged** from v3.8.2.

## Cargo workspace layout (new)

```
inscript_v391/
├── Cargo.toml                    ← workspace root (members: rust_vm_engine, inscript_rust_parser)
├── rust_vm_engine/
│   ├── Cargo.toml                ← inscript-vm-engine v3.9.1
│   └── src/
│       ├── lib.rs                ← Value, OpCode, pub mod ir (NEW)
│       ├── vm.rs                 ← VMEngine (v3.8.4 base + v3.9.0 passes)
│       ├── compiler.rs           ← 5-pass optimiser (v3.9.0)
│       ├── pool.rs               ← Object/Array pools (v3.8.4)
│       └── ir.rs                 ← LLVM IR emitter (v3.9.1) ← NEW
└── inscript_rust_parser/
    ├── Cargo.toml                ← inscript-parser v3.7.3
    └── src/
        ├── lib.rs
        ├── parser.rs
        ├── ast.rs
        ├── token.rs
        └── error.rs
```

## Building the Rust components

```powershell
# From the repo root (inscript_v391/)
cargo build --release                       # builds both crates
cargo test                                  # runs all Rust unit tests
cargo test -p inscript-vm-engine            # VM engine tests only
cargo test -p inscript-parser               # parser tests only
```

## Python tests (no Rust required)

```powershell
cd inscript_v391
python test_all_150_bugs.py                 # original 150 bug regression tests
python test_all_150_bugs_FINAL.py           # final consolidated suite from v3.9.0
python inscript_test.py                     # core interpreter tests
```
