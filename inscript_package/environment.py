# -*- coding: utf-8 -*-
# inscript/environment.py  — Variable scope environment
# Each function call and block gets its own Environment chained to its parent.

from __future__ import annotations
from typing import Any, Dict, Optional
from errors import NameError_, InScriptRuntimeError, hint_for_name


class Environment:
    """
    A single scope level.  Chains to a parent for variable lookup.
    """
    def __init__(self, parent: Optional["Environment"] = None, name: str = "block"):
        self.parent:  Optional[Environment]  = parent
        self.name:    str                    = name
        self._store:   Dict[str, Any]         = {}
        self._consts: set                    = set()   # names that cannot be reassigned
        # v1.7.4: when True, `let` re-declarations silently re-bind (REPL mode)
        self._repl_mode: bool                = False

    # ── Define ────────────────────────────────────────────────────────────────
    def define(self, name: str, value: Any, is_const: bool = False) -> None:
        # v1.7.4: in REPL mode, re-declaring an existing non-const `let` just
        # re-binds it.  Attempting to re-declare a const is still an error.
        if self._repl_mode and name in self._store and name in self._consts:
            raise InScriptRuntimeError(
                f"Cannot re-declare constant '{name}' in REPL", 0)
        self._store[name]   = value
        if is_const:
            self._consts.add(name)

    # ── Get ───────────────────────────────────────────────────────────────────
    def get(self, name: str, line: int = 0, col: int = 0) -> Any:
        if name in self._store:
            return self._store[name]
        if self.parent:
            return self.parent.get(name, line, col)
        # Phase 3.1: did-you-mean
        hint = hint_for_name(name, self._all_names())
        raise NameError_(f"Undefined variable: '{name}'", line, hint=hint)

    def _all_names(self) -> list:
        names = list(self._store.keys())
        if self.parent:
            names.extend(self.parent._all_names())
        return names

    # ── Set (assignment) ──────────────────────────────────────────────────────
    def set(self, name: str, value: Any, line: int = 0, col: int = 0) -> None:
        if name in self._store:
            if name in self._consts:
                raise InScriptRuntimeError(f"Cannot assign to constant '{name}'", line)
            self._store[name] = value
            return
        if self.parent:
            self.parent.set(name, value, line)
            return
        raise NameError_(f"Undefined variable: '{name}' (use 'let' to declare it first)",
                         line, hint=hint_for_name(name, self._all_names()))

    # ── Check ─────────────────────────────────────────────────────────────────
    def has_local(self, name: str) -> bool:
        return name in self._store

    def __repr__(self) -> str:
        return f"Env({self.name}, vars={list(self._store.keys())})"
