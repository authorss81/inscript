# inscript/errors.py
# All error and signal types for the InScript language.

class InScriptError(Exception):
    """Base class for all InScript compile/runtime errors."""
    def __init__(self, message: str, line: int = 0, col: int = 0, source_line: str = ""):
        self.message    = message
        self.line       = line
        self.col        = col
        self.source_line = source_line
        super().__init__(self._format())

    def _format(self) -> str:
        kind   = type(self).__name__
        header = f"\n[InScript {kind}] Line {self.line}, Col {self.col}: {self.message}"
        if self.source_line:
            arrow = " " * max(0, self.col - 1) + "^"
            return f"{header}\n  {self.source_line}\n  {arrow}"
        return header


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


# ── Control-flow signals ──────────────────────────────────────────────────────
# These are NOT errors — they are used internally by the interpreter to
# implement return / break / continue without using goto.

class ReturnSignal(Exception):
    """Raised by `return val` — caught by the function call handler."""
    def __init__(self, value=None):
        self.value = value

class BreakSignal(Exception):
    """Raised by `break` or `break label` — caught by while/for/labeled handler."""
    def __init__(self, label=None):
        self.label = label

class ContinueSignal(Exception):
    """Raised by `continue` or `continue label` — caught by while/for/labeled handler."""
    def __init__(self, label=None):
        self.label = label


class YieldSignal(Exception):
    """Raised by `yield value` inside a generator function body."""
    def __init__(self, value=None):
        self.value = value

class PropagateSignal(Exception):
    """Raised by `expr?` when the result is Err — causes enclosing fn to return the Err."""
    def __init__(self, err_val):
        self.err_val = err_val
