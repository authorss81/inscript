# -*- coding: utf-8 -*-
# inscript/errors.py — Phase 3: Error Quality
#
# Changes from Phase 1:
#   • Error codes  (E0001–E0099)
#   • Improved multi-line format with source context + caret
#   • MultiError: collect N errors, report them all at once
#   • InScriptWarning: warning class with --no-warn / --warn-as-error support
#   • InScriptCallStack: lightweight call-stack for runtime traces

from __future__ import annotations
from typing import List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Error code registry
# ─────────────────────────────────────────────────────────────────────────────

ERROR_CODES = {
    # Lexer
    "LexerError":              "E0001",
    "UnknownChar":             "E0002",
    "UnterminatedString":      "E0003",

    # Parser
    "ParseError":              "E0010",
    "UnexpectedToken":         "E0011",
    "MissingToken":            "E0012",
    "UnbalancedBrace":         "E0013",

    # Semantic / analyzer
    "SemanticError":           "E0020",
    "UndefinedName":           "E0021",
    "AlreadyDeclared":         "E0022",
    "TypeMismatch":            "E0023",
    "UndefinedField":          "E0024",
    "UndefinedMethod":         "E0025",
    "NotCallable":             "E0026",
    "WrongArgCount":           "E0027",
    "ReturnOutsideFunction":   "E0028",
    "BreakOutsideLoop":        "E0029",
    "ContinueOutsideLoop":     "E0030",
    "InterfaceNotImplemented": "E0031",

    # Runtime
    "InScriptRuntimeError":    "E0040",
    "TypeError_":              "E0041",
    "NameError_":              "E0042",
    "IndexError_":             "E0043",
    "ImportError_":            "E0044",
    "DivisionByZero":          "E0045",
    "StackOverflow":           "E0046",
    "MatchError":              "E0047",
    "PropertyError":           "E0048",
    "NilAccess":               "E0049",
}

DOCS_BASE = "https://docs.inscript.dev/errors"


# ─────────────────────────────────────────────────────────────────────────────
# Base error
# ─────────────────────────────────────────────────────────────────────────────

class InScriptError(Exception):
    """Base class for all InScript compile/runtime errors."""

    def __init__(self, message: str, line: int = 0, col: int = 0,
                 source_line: str = "",
                 hint: str = "",           # "Did you mean 'foo'?"
                 call_trace: list = None,  # [(fn_name, file, line), ...]
                 code: str = ""):
        self.message     = message
        self.line        = line
        self.col         = col
        self.source_line = source_line
        self.hint        = hint
        self.call_trace  = call_trace or []
        # Determine code from subclass name if not given
        cls_name = type(self).__name__
        self.code = code or ERROR_CODES.get(cls_name, "E0000")
        super().__init__(self._format())

    def _format(self) -> str:
        code   = self.code
        cls    = type(self).__name__
        header = f"\n[InScript {cls}] {code}  Line {self.line}"
        if self.col:
            header += f", Col {self.col}"
        header += f": {self.message}"

        parts = [header]

        # Source context
        if self.source_line:
            stripped = self.source_line.rstrip()
            parts.append(f"  {stripped}")
            if self.col > 0:
                arrow = " " * (self.col + 1) + "^"
                parts.append(f"  {arrow}")

        # "Did you mean?" hint
        if self.hint:
            parts.append(f"  Hint: {self.hint}")

        # Call trace (runtime only)
        if self.call_trace:
            parts.append("\nCall stack (most recent last):")
            for fn, file, ln in self.call_trace:
                parts.append(f"  File \"{file}\", line {ln}, in {fn}")

        # Docs link
        parts.append(f"  See: {DOCS_BASE}/{code}")

        return "\n".join(parts)

    def with_hint(self, hint: str) -> "InScriptError":
        """Return a copy with a hint attached (for did-you-mean suggestions)."""
        self.hint = hint
        self.args = (self._format(),)
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Concrete error types
# ─────────────────────────────────────────────────────────────────────────────

class LexerError(InScriptError):
    """Unrecognized character or malformed token."""
    pass

class ParseError(InScriptError):
    """Unexpected token during parsing."""
    pass

class SemanticError(InScriptError):
    """Type error or scope violation detected before running."""
    pass

class InScriptRuntimeError(InScriptError):
    """Error raised at runtime during interpretation."""
    pass

class TypeError_(InScriptError):
    """Wrong type in an operation."""
    pass

class NameError_(InScriptError):
    """Reference to an undefined name."""
    pass

class IndexError_(InScriptError):
    """Index out of bounds."""
    pass

class ImportError_(InScriptError):
    """Failed to load a module."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Multi-error collector  (3.5)
# ─────────────────────────────────────────────────────────────────────────────

class MultiError(Exception):
    """
    Holds multiple InScriptErrors collected during a single analysis pass.
    Raised by Analyzer when --multi-error mode is on.
    """
    MAX_ERRORS = 20   # Stop collecting after this many to avoid noise cascade

    def __init__(self, errors: List[InScriptError]):
        self.errors = errors[:self.MAX_ERRORS]
        super().__init__(self._format())

    def _format(self) -> str:
        n = len(self.errors)
        lines = [f"\nFound {n} error{'s' if n != 1 else ''}:\n"]
        for i, e in enumerate(self.errors, 1):
            lines.append(f"{i}. {str(e).lstrip()}")
        return "\n".join(lines)

    def __iter__(self):
        return iter(self.errors)


# ─────────────────────────────────────────────────────────────────────────────
# Warning  (3.6)
# ─────────────────────────────────────────────────────────────────────────────

WARN_CODES = {
    "unused_var":         "W0001",
    "unused_import":      "W0002",
    "unreachable":        "W0003",
    "shadow":             "W0004",
    "missing_return_ann": "W0005",
    "long_function":      "W0006",
    "implicit_any":       "W0007",
    "exhaustive_match":   "W0008",
}

class InScriptWarning:
    """A non-fatal diagnostic. Collected and printed after analysis."""
    def __init__(self, kind: str, message: str, line: int = 0,
                 source_line: str = ""):
        self.kind        = kind
        self.message     = message
        self.line        = line
        self.source_line = source_line
        self.code        = WARN_CODES.get(kind, "W0000")

    def format(self) -> str:
        loc = f"Line {self.line}" if self.line else "?"
        msg = f"[InScript Warning] {self.code}  {loc}: {self.message}"
        if self.source_line:
            msg += f"\n  {self.source_line.rstrip()}"
        return msg


# ─────────────────────────────────────────────────────────────────────────────
# Call stack frame  (3.4)
# ─────────────────────────────────────────────────────────────────────────────

class CallFrame:
    __slots__ = ("fn_name", "file", "line")
    def __init__(self, fn_name: str, file: str, line: int):
        self.fn_name = fn_name
        self.file    = file
        self.line    = line

    def as_tuple(self) -> Tuple[str, str, int]:
        return (self.fn_name, self.file, self.line)


class InScriptCallStack:
    """
    Lightweight call stack maintained by the interpreter.
    Stored on Interpreter as self._call_stack.
    """
    MAX_FRAMES = 200

    def __init__(self, filename: str = "<script>"):
        self._frames: List[CallFrame] = []
        self._file   = filename

    def push(self, fn_name: str, line: int):
        if len(self._frames) < self.MAX_FRAMES:
            self._frames.append(CallFrame(fn_name, self._file, line))

    def pop(self):
        if self._frames:
            self._frames.pop()

    def snapshot(self) -> List[Tuple[str, str, int]]:
        """Return a copy of current frames as list of (fn, file, line) tuples."""
        return [f.as_tuple() for f in self._frames]

    def update_top_line(self, line: int):
        """Keep top frame's line number current as execution proceeds."""
        if self._frames:
            self._frames[-1].line = line

    def format(self) -> str:
        if not self._frames:
            return ""
        lines = ["Call stack (most recent last):"]
        shown = self._frames
        truncated = 0
        if len(shown) > 20:
            truncated = len(shown) - 20
            shown = shown[-20:]
        if truncated:
            lines.append(f"  ... {truncated} earlier frame(s) ...")
        for f in shown:
            lines.append(f'  File "{f.file}", line {f.line}, in {f.fn_name}')
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Levenshtein / "Did you mean?"  (3.1)
# ─────────────────────────────────────────────────────────────────────────────

def levenshtein(a: str, b: str) -> int:
    """Compute edit distance between two strings."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0: return lb
    if lb == 0: return la
    # Use a flat dp array (O(lb) space)
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        curr = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            curr[j] = min(curr[j-1] + 1, prev[j] + 1, prev[j-1] + cost)
        prev = curr
    return prev[lb]


def did_you_mean(name: str, candidates: List[str],
                 max_dist: int = 2, max_len: int = 12) -> Optional[str]:
    """
    Return the closest candidate to `name` within `max_dist` edit distance,
    or None if nothing close enough found.
    Filters candidates longer than max_len to avoid silly suggestions.
    """
    best_dist  = max_dist + 1
    best_name  = None
    name_lower = name.lower()
    for c in candidates:
        if len(c) > max_len:
            continue
        d = levenshtein(name_lower, c.lower())
        if d < best_dist:
            best_dist = d
            best_name = c
    return best_name


def hint_for_name(name: str, candidates: List[str]) -> str:
    """Return a formatted hint string, or ''."""
    suggestion = did_you_mean(name, candidates)
    if suggestion and suggestion != name:
        return f"Did you mean: '{suggestion}'?"
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Control-flow signals  (unchanged from Phase 1)
# ─────────────────────────────────────────────────────────────────────────────

class ReturnSignal(Exception):
    def __init__(self, value=None):
        self.value = value

class BreakSignal(Exception):
    def __init__(self, label=None):
        self.label = label

class ContinueSignal(Exception):
    def __init__(self, label=None):
        self.label = label

class YieldSignal(Exception):
    def __init__(self, value=None):
        self.value = value

class PropagateSignal(Exception):
    def __init__(self, err_val):
        self.err_val = err_val

class TailCallSignal(Exception):
    """v1.3.0: raised by a self-recursive tail call to trampoline in _call_function."""
    __slots__ = ("arg_vals",)
    def __init__(self, arg_vals):
        self.arg_vals = arg_vals
