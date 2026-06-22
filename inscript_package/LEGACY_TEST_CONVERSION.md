# Legacy Test to .ins Conversion Plan

## COMPLETION STATUS — All 50 legacy test files covered
- **37 version directories** created (37 `.ins` test files, 979+ tests)
- **13 infrastructure-only files** documented with `# NOTE: tests remain in .py` placeholders
- All original `.py` test files retained — zero regressions
- See `AGENTS.md` progress log for the full conversion history

## Goal
Convert legacy `test_v*.py` files to `.ins` test files so all features are testable
from the InScript language level (via `inscript_test.py` runner).

## Legend
- **YES** — every test can be expressed as InScript source
- **MAYBE** — mix of InScript execution + Python API tests
- **NO** — tests Python-level infrastructure (LSP, compiler, hot-reload, etc.)

---

## Fully convertible — pure InScript, no Python deps

| Version | File | Feature Set | Plan |
|---------|------|-------------|------|
| **v1.4** | `test_v140.py` | `defer`, `repeat..until`, type-narrowing `match`, generic constraints `Comparable`/`Numeric`, regression | Create `v1.4/test_v140.ins` — all tests run `Interpreter().execute(code)` |
| **v1.5** | `test_v150.py` | `string`, `array`, `math`, `color`, `dict`, `io` stdlib modules | Create `v1.5/test_v150.ins` — all tests use `import "module"` + InScript calls |
| **v2.2** | `test_v220.py` | `??=`, `with` expr, destructuring params, named returns, impl/const/triple-string/chained `is`/labeled loops | Create `v2.2/test_v220.ins` — all pure InScript |
| **v2.3** | `test_v230.py` | `async fn`/`await`, `spawn`, `channel`, `select`, `async for`, `mutex`, `rwlock`, `timer` | Create `v2.3/test_v230.ins` — all pure InScript |

## Fully convertible — InScript + pyimport for Python API sections

| Version | File | Feature Set | Plan |
|---------|------|-------------|------|
| **v1.2** | `test_v12.py` | `path`, `regex`, `csv`, `uuid`, `crypto` stdlib + `select` + v1.1 regression + LSP diagnostics/completions/hover | Create `v1.2/test_v12.ins` — stdlib/select/regression via InScript; LSP section via `import "py:lsp.diagnostics"` etc. |
| **v1.7** | `test_v170.py` | Float/int display, `nil` vs `null`, recursive `Node`/`TreeNode`, stack traces, `InScriptCallStack` unit test, `_migrate()` | Create `v1.7/test_v170.ins` — runtime tests via InScript; stack trace unit test via `import "py:errors"` |
| **v1.9.1** | `test_v191.py` | `compat` tool, strict mode, `--no-typecheck` deprecation, regressions (method chain, enum exhaustiveness, type aliases, REPL) | Create `v1.9.1/test_v191.ins` — regressions via InScript; compat/analyzer via `import "py:inscript"`/`import "py:analyzer"` |

## Partially convertible — some sections remain `.py`

| Version | File | Convertible portion | Non-convertible portion |
|---------|------|-------------------|------------------------|
| **v1.6** | `test_v160.py` | Regression tests (pure InScript execution) | CLI flag tests (`--check-all`, `--fmt-all`, `--strict`, `--warn-as-error`) via subprocess |
| **v2.0** | `test_v200.py` | Core language + type system + error system (InScript execution) | Game mock tests, subprocess/package/version tests |
| **v2.10** | `test_v2100.py` | Sections 10-11: `import "physics"` / `import "net"` from InScript | Sections 1-9: Python-level physics/net API calls |
| **v2.7** | `test_v270.py` | Sections executing InScript source: node lifecycle, scene manager, save/load round-trip | Lexer/parser unit tests, direct `scene_tree` API calls |
| **v2.8** | `test_v280.py` | Sections 9-10: `import "asset"`, `@texture`/`@sound`/`@tilemap`/`@font` decorators | Sections 1-8: `AssetHandle`/`AssetRegistry` Python API tests, PNG generation |

## Not convertible — infrastructure tests remain `.py`

| Version | File | Reason |
|---------|------|--------|
| **v2.1** | `test_v210.py` | LSP server module functions (`get_diagnostics`, `get_completions`, `get_hover`), CLI flags, file existence |
| **v2.4** | `test_v240.py` | Bytecode compiler, `.ibc` binary format, DCE pass, VM executor, pipeline commands |
| **v2.5** | `test_v250.py` | LSP/DAP Python APIs: go-to-def, references, rename, document symbols, semantic tokens, DAPServer |
| **v2.6** | `test_v260.py` | Package ecosystem: publish, audit, workspace, monkey-patching `urllib.request.urlopen` |
| **v2.9** | `test_v290.py` | `HotReloader` class with real file I/O, mtime manipulation, function patching |
| **v3.0** | `test_v300.py` | `StudioApp` HTTP server, `VisualScriptCompiler`, `StudioBridge` RPC, Electron scaffold |
| **v3.7.3** | `test_v373.py` | Package readiness: module importability, Rust compilation status, file existence checks |

## Other legacy test files (unversioned)

| File | Convertible? | Notes |
|------|-------------|-------|
| `test_v130.py` | YES | InScript execution |
| `test_v172.py` | YES | InScript execution |
| `test_v173.py` | YES | InScript execution |
| `test_v174.py` | YES | InScript execution |
| `test_v181.py` | YES | InScript execution |
| `test_v182.py` | YES | InScript execution |
| `test_v183.py` | YES | InScript execution |
| `test_v184.py` | YES | InScript execution |
| `test_v1910.py` | NO | Infrastructure-only — `--check-v2` CLI flags |
| `test_v1911.py` | YES | InScript execution — timer module import (converted) |
| `test_v1912.py` | YES | InScript execution — math-utils/color-utils/easing (converted) |
| `test_v1913.py` | NO | Infrastructure-only — type inference analytics |
| `test_v1914.py` | NO | Infrastructure-only — game execution runner |
| `test_v1915.py` | YES | InScript execution — string interpolation (converted) |
| `test_v192.py` | NO | Infrastructure-only — package manifest |
| `test_v193.py` | NO | Infrastructure-only — doc generation |
| `test_v194.py` | NO | Infrastructure-only — spec freeze |
| `test_v195.py` | YES | InScript execution |
| `test_v196.py` | YES | InScript execution |
| `test_v197.py` | YES | InScript execution |
| `test_v198.py` | YES | InScript execution |
| `test_v199.py` | NO | Infrastructure-only — package manager |
| `test_v201.py` | YES | InScript execution |
| `test_v202.py` | YES | InScript execution |
| `test_v203.py` | YES | InScript execution |
| `test_v211.py` | NO | Infrastructure-only — `format_source()` function tests, CLI subprocess |
| `test_v2110.py` | NO | Infrastructure-only — export pipeline, directory I/O, TOML manifest |
| `test_v212.py` | YES | InScript execution (already converted) |
| `test_v2120.py` | NO | Infrastructure-only — Studio Readiness Gates, plugin API, HTTP bridge |
| `test_v2130.py` | NO | Infrastructure-only — Studio Bridge v2, iOS export, input emulation |

## Execution plan

1. `v1.4/` — defer, repeat..until, match type-narrowing, generic constraints (pure InScript)
2. `v1.5/` — string, array, math, color, dict, io stdlib (pure InScript)
3. `v2.2/` — ??=, with, destructuring, named returns (pure InScript)
4. `v2.3/` — async/await, spawn, channel, select, async for, mutex, rwlock, timer (pure InScript)
5. `v1.2/` — stdlib + select + regression + LSP via pyimport
6. `v1.7/` — runtime + stack traces + InScriptCallStack via pyimport
7. `v1.9.1/` — regressions + compat + analyzer via pyimport
8. Partial conversions: v1.6, v2.0, v2.10, v2.7, v2.8
9. Remaining unversioned test files (30 files — 17 YES, 13 NO) — ALL DONE
