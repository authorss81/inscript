# REPL Audit – Issues & Fix Status

## Critical
| # | File | Line | Issue | Status |
|---|------|------|-------|--------|
| 1 | repl.py | 291 | `_CMT_RE` uses `//` instead of `#` | ✅ |
| 2 | repl.py | 631-636 | `_eval_expr` double-executes on error | ✅ |
| 3 | inscript.py | 2619-2622 | Fallback REPL double-visit of last expr | ✅ |
| 4 | pygame_backend.py | 1008 | `dbgr.should_break()` doesn't exist | ✅ |
| 5 | pygame_backend.py | 946 | `cmd.lower()` corrupts vars in `.watch .set b if` | ✅ |

## High
| # | File | Line | Issue | Status |
|---|------|------|-------|--------|
| 6 | repl.py | 649-658 | `_is_complete` ignores `#` comments | ✅ |
| 7 | repl.py | 950-953 | `.lint` uses `_history` not `_session` | ✅ |
| 8 | repl.py | 867,878 | `.time`/`.bench` include failed runs | ✅ |
| 9 | pygame_backend.py | 970-971 | `bl` calls wrong function | ✅ |
| 10 | pygame_backend.py | 921-928 | `_check_hook_breakpoint` too broad | ✅ |
| 11 | repl.py | 617 | `__repl_rv__` collision + paren wrap | ✅ |
| - | - | - | Import support in REPL | ✅ |

## Medium
| # | File | Line | Issue | Status |
|---|------|------|-------|--------|
| 12 | repl.py | 298-303 | Regex highlighting color corruption | ✅ |
| 13 | repl.py | 302 | `_TY_RE` false positives on any Uppercase | ✅ |
| 14 | repl.py | 292 | `_FN_RE` misses uppercase function names | ✅ |
| 15 | repl.py | 837,844,860 | File I/O missing `encoding="utf-8"` | ✅ |
| 16 | repl.py | 444 | No readline fallback on Windows | ✅ |
| 17 | inscript.py | 2508-2513 | EnhancedREPL import error silent | ✅ |
| 18 | inscript.py | 2562-2572 | `.type` re-evaluates expression | ✅ |
| 19 | repl.py | 452 | atexit handler no error handling | ✅ |
| 20 | repl.py | 1063 vs 1074 | `_history`/`_session` diverge | ✅ |
| 21 | repl.py | 345 | `_STMT_STARTS` includes `//` | ✅ |

## Low / Cosmetic
| # | File | Line | Issue | Status |
|---|------|------|-------|--------|
| 22 | repl.py | 1151 | Playground version hardcoded `v1.0.5` | ✅ |
| 23 | debugger.py | 661 | `_cmd_globals` 80-entry cap | ✅ |
| 24 | pygame_backend.py | 985 | `.watch` help text misleading | ✅ |
| 25 | pygame_backend.py | 972-973 | `bc` semantics inconsistent | ✅ |

## Additional Fixes (round 2)
| # | File | Line | Issue | Status |
|---|------|------|-------|--------|
| 26 | interpreter.py | 447-450 | Core I/O helpers missing `encoding="utf-8"` | ✅ |
| 27 | pygame_backend.py | 1121 | IPC profile dump missing `encoding="utf-8"` | ✅ |
| 28 | repl.py | 239-352 | STDLIB_DOCS expanded with descriptions & examples | ✅ |
| 29 | repl.py | 902-950 | `.doc` handler: added `mod.func` detail, descriptions | ✅ |

## Summary
- **Total issues found:** 29
- **Total fixed:** 29
- **Files modified:**
  - `repl.py` — comment regex, double-execution, highlighting, I/O encoding, history, import, stdlib docs
  - `inscript.py` — fallback REPL double-visit, EnhancedREPL import warning, .type re-eval
  - `pygame_backend.py` — cmd.lower() corruption, bl/bc/bd semantics, bp checking, IPC encoding
  - `debugger.py` — _cmd_globals cap removed
  - `interpreter.py` — core I/O helpers encoding
- **No tags or versions pushed**
