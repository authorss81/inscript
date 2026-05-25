# -*- coding: utf-8 -*-
"""
hot_reload.py — InScript v2.9.0  Hot Reload Engine
================================================================
Provides state-preserving hot reload:

  • Snapshot the live interpreter's global scope (scalar values / asset
    handles / node instances) before reloading.
  • Re-parse the changed source.
  • Replay only declaration statements: fn, struct, node, const, @decorators.
  • Patch callables in the live env without resetting runtime state (score,
    position, health, etc. survive the reload).
  • Restore non-callable values that existed before the reload.
  • Call on_reload() if defined, so game code can react (re-register assets,
    reset physics contacts, etc.)
  • Collect and report parse/type errors; keep old code running on failure.

@hot_reload annotation
──────────────────────
Mark a function as stable so the hot-reload engine skips patching it:

    @hot_reload
    fn expensive_precompute(data) { ... }

The function is patched only on first load; subsequent reloads leave it
unchanged even if the source changed.  Useful for computationally expensive
setup that should not re-run every save.

Usage
─────
    from hot_reload import HotReloader
    reloader = HotReloader(source_path, interp)
    reloader.start()          # initial load
    changed = reloader.tick() # call every save (from --watch loop)
    reloader.stop()
"""

from __future__ import annotations
import os, time
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from interpreter import Interpreter

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_DECLARATION_NODE_TYPES = frozenset({
    "FunctionDecl", "StructDecl", "NodeDecl",
    "ExportDecl",   "DecoratedDecl",
})

_SKIP_RESTORE_TYPES = frozenset({
    # Never restore these from snapshot — they're always re-declared fresh
    "InScriptFunction", "NodeBlueprint",
})

# Primitive types safe to snapshot/restore across a reload
_SCALAR_TYPES = (int, float, str, bool, type(None), list, dict, tuple)


def _is_callable_value(v: Any) -> bool:
    """True for InScript functions, structs, node blueprints, Python callables."""
    from ast_nodes import StructDecl
    try:
        from scene_tree import NodeBlueprint
        if isinstance(v, NodeBlueprint):
            return True
    except ImportError:
        pass
    try:
        from interpreter import InScriptFunction
        if isinstance(v, InScriptFunction):
            return True
    except ImportError:
        pass
    if isinstance(v, StructDecl):
        return True
    return callable(v)


def _snapshot_globals(interp: "Interpreter") -> Dict[str, Any]:
    """
    Capture non-callable, non-private names from the global scope.
    These are the values that must survive the reload (game state).
    """
    snap = {}
    for name, val in list(interp._globals._store.items()):
        if name.startswith("_"):
            continue
        if _is_callable_value(val):
            continue
        snap[name] = val
    return snap


def _restore_snapshot(interp: "Interpreter",
                       snap: Dict[str, Any],
                       patched_callables: Set[str]) -> None:
    """
    Re-inject snapshot values for names that were NOT redeclared by the reload
    and whose values are scalar (i.e. game state, not code).
    """
    for name, val in snap.items():
        if name in patched_callables:
            continue  # This name was re-declared; new version wins
        try:
            interp._globals.set(name, val)
        except Exception:
            try:
                interp._globals.define(name, val)
            except Exception:
                pass


def _collect_declared_names(program) -> Set[str]:
    """Walk the top-level AST and collect every declared name."""
    names = set()
    for stmt in program.body:
        cls = type(stmt).__name__
        if cls == "FunctionDecl":
            names.add(stmt.name)
        elif cls == "StructDecl":
            names.add(stmt.name)
        elif cls == "NodeDecl":
            names.add(stmt.name)
        elif cls == "ExportDecl":
            inner = getattr(stmt, "decl", None)
            if inner is not None:
                names.add(getattr(inner, "name", None) or "")
        elif cls == "DecoratedDecl":
            inner = getattr(stmt, "target", None)
            inner2 = getattr(inner, "decl", inner)
            names.add(getattr(inner2, "name", None) or "")
        elif cls == "VarDecl" and getattr(stmt, "name", None):
            names.add(stmt.name)
    names.discard("")
    return names


# ─────────────────────────────────────────────────────────────────────────────
# ReloadResult
# ─────────────────────────────────────────────────────────────────────────────

class ReloadResult:
    """Returned by HotReloader.tick() describing what happened."""
    def __init__(self, changed: bool, success: bool,
                 patched: List[str], restored: List[str],
                 errors: List[str], elapsed_ms: float):
        self.changed    = changed      # True if the source file changed
        self.success    = success      # True if reload completed without errors
        self.patched    = patched      # names that were re-declared
        self.restored   = restored     # names restored from snapshot
        self.errors     = errors       # parse/runtime error strings (if any)
        self.elapsed_ms = elapsed_ms   # wall-clock time in milliseconds

    def __repr__(self):
        status = "OK" if self.success else "ERR"
        return (f"<ReloadResult {status} patched={self.patched} "
                f"restored={len(self.restored)} errors={len(self.errors)} "
                f"{self.elapsed_ms:.1f}ms>")


# ─────────────────────────────────────────────────────────────────────────────
# HotReloader
# ─────────────────────────────────────────────────────────────────────────────

class HotReloader:
    """
    Manages hot reload for a single .ins source file against a live interpreter.

    Typical usage (headless / test):
        reloader = HotReloader("game.ins", interp)
        reloader.start()
        # ... mutate source file ...
        result = reloader.tick()   # detects change, reloads, returns ReloadResult

    Typical usage (game loop / --watch):
        reloader = HotReloader("game.ins", interp)
        reloader.start()
        while running:
            result = reloader.tick()
            if result.changed and not result.success:
                show_error_overlay(result.errors)
    """

    def __init__(self, source_path: str, interp: "Interpreter"):
        self.source_path     = source_path
        self._interp         = interp
        self._last_mtime:    Optional[float] = None
        self._stable_names:  Set[str] = set()   # @hot_reload-marked names
        self._reload_count   = 0

    # ── public API ─────────────────────────────────────────────────────────────

    def start(self) -> ReloadResult:
        """Initial load.  Equivalent to a cold run with snapshot setup."""
        return self._do_reload(initial=True)

    def tick(self) -> ReloadResult:
        """
        Check if source file changed; reload if so.
        Returns a ReloadResult with changed=False if nothing changed.
        """
        try:
            mtime = os.path.getmtime(self.source_path)
        except FileNotFoundError:
            return ReloadResult(False, False, [], [], [f"File not found: {self.source_path}"], 0.0)

        if self._last_mtime is not None and mtime <= self._last_mtime:
            return ReloadResult(False, True, [], [], [], 0.0)

        return self._do_reload(initial=False)

    def stop(self):
        """No-op; hooks into game loop cleanup."""
        pass

    @property
    def reload_count(self) -> int:
        return self._reload_count

    # ── internals ──────────────────────────────────────────────────────────────

    def _do_reload(self, initial: bool) -> ReloadResult:
        t0 = time.perf_counter()
        errors: List[str] = []
        patched: List[str] = []
        restored: List[str] = []

        try:
            mtime = os.path.getmtime(self.source_path)
        except FileNotFoundError:
            return ReloadResult(True, False, [], [],
                                [f"File not found: {self.source_path}"], 0.0)

        # 1. Read source
        try:
            with open(self.source_path, encoding="utf-8") as f:
                source = f.read()
        except OSError as e:
            return ReloadResult(True, False, [], [], [str(e)], 0.0)

        # 2. Parse (fail-safe: keep old code running on syntax error)
        try:
            from parser import parse as _parse
            program = _parse(source)
        except Exception as e:
            errors.append(f"Parse error: {e}")
            elapsed = (time.perf_counter() - t0) * 1000
            return ReloadResult(True, False, patched, restored, errors, elapsed)

        # 3. Snapshot current game state (skip on initial load)
        snap: Dict[str, Any] = {}
        if not initial:
            snap = _snapshot_globals(self._interp)

        # 4. Determine which names will be patched
        declared = _collect_declared_names(program)

        # 5. Execute only declaration nodes (fn, struct, node, const, decorated)
        #    Skip @hot_reload-marked stable names (unless initial load)
        for stmt in program.body:
            cls = type(stmt).__name__
            if not initial:
                # Hot reload: only patch code declarations, never re-run VarDecl
                # (that would reset game state like score, player position, etc.)
                if cls not in _DECLARATION_NODE_TYPES:
                    continue

            # Determine the name of this declaration
            name = None
            if cls == "FunctionDecl":
                name = stmt.name
            elif cls in ("StructDecl", "NodeDecl"):
                name = stmt.name
            elif cls == "DecoratedDecl":
                inner = getattr(getattr(stmt, "target", None), "decl",
                                stmt.target)
                name = getattr(inner, "name", None)
                # Detect @hot_reload — register as stable
                for dec_name, _ in stmt.decorators:
                    if dec_name == "hot_reload":
                        if name:
                            self._stable_names.add(name)

            # Skip stable names on subsequent reloads
            if not initial and name and name in self._stable_names:
                continue

            # Execute the declaration
            try:
                self._interp.visit(stmt)
                if name:
                    patched.append(name)
            except Exception as e:
                errors.append(f"Reload error in '{name or cls}': {e}")

        # 6. Restore snapshot values for names NOT re-declared
        if not initial and snap:
            for k, v in snap.items():
                if k not in declared:
                    try:
                        self._interp._globals.set(k, v)
                    except Exception:
                        try:
                            self._interp._globals.define(k, v)
                        except Exception:
                            pass
                    restored.append(k)

        # 7. Call on_reload() if defined
        if not initial:
            try:
                on_reload_fn = self._interp._globals._store.get("on_reload")
                if on_reload_fn is not None and callable(on_reload_fn):
                    self._interp._call_fn(on_reload_fn, [])
            except Exception as e:
                errors.append(f"on_reload() error: {e}")

        self._last_mtime  = mtime
        self._reload_count += 1
        elapsed = (time.perf_counter() - t0) * 1000

        success = len(errors) == 0
        if not initial:
            status = "✅" if success else "❌"
            print(f"[hot_reload] {status} #{self._reload_count}  "
                  f"patched={patched}  restored={len(restored)}  "
                  f"{elapsed:.1f}ms")

        return ReloadResult(
            changed    = True,
            success    = success,
            patched    = patched,
            restored   = restored,
            errors     = errors,
            elapsed_ms = elapsed,
        )
