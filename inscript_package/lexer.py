# -*- coding: utf-8 -*-
# inscript/lexer.py  — Phase 1 (revised)
# Tokenizer for the InScript programming language.

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional
from errors import LexerError


class TT(Enum):
    # ── Literals ──────────────────────────────────
    INT         = auto()
    FLOAT       = auto()
    STRING      = auto()
    BOOL        = auto()
    NULL        = auto()   # null (removed — hard error)
    NIL         = auto()   # nil  (the correct nil literal)

    # ── Identifiers & Keywords ────────────────────
    IDENT       = auto()
    LET         = auto()
    CONST       = auto()
    FN          = auto()
    RETURN      = auto()
    STRUCT      = auto()
    SCENE       = auto()
    SELF        = auto()
    IF          = auto()
    ELSE        = auto()
    WHILE       = auto()
    FOR         = auto()
    IN          = auto()
    BREAK       = auto()
    CONTINUE    = auto()
    MATCH       = auto()
    CASE        = auto()
    ON_START    = auto()
    ON_UPDATE   = auto()
    ON_DRAW     = auto()
    ON_EXIT     = auto()
    # v2.7.0 — Scene System
    NODE        = auto()   # node keyword
    ON_READY    = auto()   # _ready lifecycle
    ON_NODE_UPDATE = auto()  # _update lifecycle (node variant)
    ON_NODE_DRAW   = auto()  # _draw  lifecycle (node variant)
    INT_TYPE    = auto()
    FLOAT_TYPE  = auto()
    BOOL_TYPE   = auto()
    STRING_TYPE = auto()
    VOID_TYPE   = auto()
    IMPORT      = auto()
    FROM        = auto()
    AS          = auto()
    EXPORT      = auto()   # export fn / export struct / export const
    TRY         = auto()
    CATCH       = auto()
    FINALLY     = auto()
    THROW       = auto()
    SUPER       = auto()
    ENUM        = auto()
    INTERFACE   = auto()
    IMPL        = auto()
    PUB         = auto()
    SPAWN       = auto()
    AWAIT       = auto()
    ASYNC       = auto()
    SELECT      = auto()
    THEN        = auto()
    CASE_SELECT = auto()   # re-used "case" inside select blocks
    ABSTRACT    = auto()
    YIELD       = auto()       # yield value
    IS          = auto()       # is  (type check: x is int)
    DIV         = auto()       # div (floor division keyword: 10 div 3)
    DEFER       = auto()       # v1.4.0: defer expr
    REPEAT      = auto()       # v1.4.0: repeat { } until cond
    UNTIL       = auto()       # v1.4.0: until (part of repeat)

    # ── Arithmetic ────────────────────────────────
    PLUS        = auto()
    MINUS       = auto()
    STAR        = auto()
    SLASH       = auto()
    PERCENT     = auto()
    POWER       = auto()

    # ── Comparison ────────────────────────────────
    EQ          = auto()
    NEQ         = auto()
    LT          = auto()
    GT          = auto()
    LTE         = auto()
    GTE         = auto()

    # ── Logical ───────────────────────────────────
    AND         = auto()
    OR          = auto()
    NOT         = auto()

    # ── Assignment ────────────────────────────────
    ASSIGN      = auto()
    PLUS_EQ     = auto()
    PLUSPLUS    = auto()   # ++ string concat operator
    MINUS_EQ    = auto()
    STAR_EQ     = auto()
    SLASH_EQ    = auto()
    SLASH_SLASH = auto()
    PERCENT_EQ  = auto()
    POWER_EQ    = auto()   # BUG-13 fix: **=

    # ── Delimiters ────────────────────────────────
    LPAREN      = auto()
    RPAREN      = auto()
    LBRACE      = auto()
    RBRACE      = auto()
    LBRACKET    = auto()
    RBRACKET    = auto()
    COMMA       = auto()
    DOT         = auto()
    COLON       = auto()
    SEMICOLON   = auto()
    ARROW       = auto()        # ->
    FAT_ARROW   = auto()        # =>
    DOUBLE_COLON= auto()        # ::
    PIPE        = auto()        # |   (lambda params)
    QUESTION    = auto()        # ?   (nullable / optional chaining)
    DOTDOT      = auto()        # ..  (range exclusive / spread)
    DOTDOT_EQ   = auto()        # ..= (range inclusive)
    ELLIPSIS    = auto()        # ... (spread / rest)
    HASH        = auto()        # #   (attribute / annotation)
    AT          = auto()        # @   (decorator)
    NULLISH     = auto()        # ??  (nullish coalescing)
    NULLISH_EQ  = auto()        # ??= (null-coalescing assignment)  v2.2.0
    QUESTION_DOT= auto()        # ?.  (optional chaining)
    PIPE_GT     = auto()        # |>  (pipe operator)
    FSTRING     = auto()        # f"..." (interpolated string — value is raw template)

    # ── Bitwise ───────────────────────────────────────────────────────────────
    BIT_AND     = auto()        # &
    BIT_OR      = auto()        # |  (when not | > or ||)
    BIT_XOR     = auto()        # ^
    BIT_NOT     = auto()        # ~
    LSHIFT      = auto()        # <<
    RSHIFT      = auto()        # >>
    AMP_EQ      = auto()        # &=
    PIPE_EQ     = auto()        # |=
    CARET_EQ    = auto()        # ^=
    LSHIFT_EQ   = auto()        # <<=
    RSHIFT_EQ   = auto()        # >>=

    # ── Special ───────────────────────────────────
    EOF         = auto()


KEYWORDS: dict = {
    "let":       TT.LET,
    "const":     TT.CONST,
    "fn":        TT.FN,
    "return":    TT.RETURN,
    "struct":    TT.STRUCT,
    "scene":     TT.SCENE,
    "self":      TT.SELF,
    "if":        TT.IF,
    "else":      TT.ELSE,
    "while":     TT.WHILE,
    "for":       TT.FOR,
    "in":        TT.IN,
    "break":     TT.BREAK,
    "continue":  TT.CONTINUE,
    "match":     TT.MATCH,
    "case":      TT.CASE,
    "on_start":  TT.ON_START,
    "on_update": TT.ON_UPDATE,
    "on_draw":   TT.ON_DRAW,
    "on_exit":   TT.ON_EXIT,
    # v2.7.0
    "node":      TT.IDENT,
    "_ready":    TT.ON_READY,
    "_update":   TT.ON_NODE_UPDATE,
    "_draw":     TT.ON_NODE_DRAW,
    "int":       TT.INT_TYPE,
    "float":     TT.FLOAT_TYPE,
    "bool":      TT.BOOL_TYPE,
    "string":    TT.STRING_TYPE,
    "void":      TT.VOID_TYPE,
    "true":      TT.BOOL,
    "false":     TT.BOOL,
    "null":      TT.NULL,
    "nil":       TT.NIL,
    "import":    TT.IMPORT,
    "from":      TT.FROM,
    "as":        TT.AS,
    "is":        TT.IS,
    "div":       TT.DIV,
    "defer":     TT.DEFER,
    "repeat":    TT.REPEAT,
    "until":     TT.UNTIL,
    "export":    TT.EXPORT,
    "try":       TT.TRY,
    "catch":     TT.CATCH,
    "finally":   TT.FINALLY,
    "throw":     TT.THROW,
    "super":     TT.SUPER,
    "enum":      TT.ENUM,
    "interface": TT.INTERFACE,
    "impl":      TT.IMPL,
    "pub":       TT.PUB,
    "spawn":     TT.SPAWN,
    "await":     TT.AWAIT,
    "async":     TT.ASYNC,
    "yield":      TT.YIELD,
    "extends":    TT.IDENT,   # treated as ident, parser checks value
    "static":     TT.IDENT,
    "override":   TT.IDENT,
    "abstract":   TT.ABSTRACT,
    "then":       TT.THEN,
    "select":     TT.SELECT,
    "implements": TT.IDENT,
    "mixin":      TT.IDENT,
    "with":       TT.IDENT,
    "get":        TT.IDENT,
    "set":        TT.IDENT,
    "comptime":   TT.IDENT,
    "type":       TT.IDENT,  # soft keyword for type aliases
    "operator":   TT.IDENT,   # Phase 7: treated as ident, parser checks value
}


@dataclass
class Token:
    type:  TT
    value: object
    line:  int
    col:   int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, L{self.line}:C{self.col})"


class Lexer:
    def __init__(self, source: str, filename: str = "<stdin>"):
        self.source   = source
        self.filename = filename
        self.pos      = 0
        self.line     = 1
        self.col      = 1
        self.tokens: List[Token] = []
        self._lines   = source.splitlines()

    @property
    def current(self) -> Optional[str]:
        return self.source[self.pos] if self.pos < len(self.source) else None

    @property
    def peek(self) -> Optional[str]:
        n = self.pos + 1
        return self.source[n] if n < len(self.source) else None

    def peek_at(self, offset: int) -> Optional[str]:
        n = self.pos + offset
        return self.source[n] if n < len(self.source) else None

    def advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def match(self, expected: str) -> bool:
        if self.current == expected:
            self.advance()
            return True
        return False

    def _src_line(self, line: int) -> str:
        return self._lines[line - 1] if 1 <= line <= len(self._lines) else ""

    def _error(self, msg: str, line: int = None, col: int = None):
        l = line if line is not None else self.line
        c = col  if col  is not None else self.col
        raise LexerError(msg, l, c, self._src_line(l))

    def _emit(self, t: TT, v: object, l: int, c: int) -> Token:
        tok = Token(t, v, l, c)
        self.tokens.append(tok)
        return tok

    def tokenize(self) -> List[Token]:
        while self.current is not None:
            self._scan_token()
        self._emit(TT.EOF, None, self.line, self.col)
        return self.tokens

    def _scan_token(self):
        sl, sc = self.line, self.col
        ch = self.advance()

        if ch in (" ", "\t", "\r", "\n"):
            return

        # // — floor-division operator (v1.9.6: ALWAYS floor division, no exceptions)
        # v1.9.6: `#` is the new line-comment character.
        # `//` with or without spaces is always integer floor division: 10 // 3 → 3
        # v1.9.12: `///` is a doc-comment line — skip like a line comment.
        if ch == "/" and self.current == "/":
            self.advance()  # consume second /
            if self.current == "/":
                self.advance()  # consume third /
                self._skip_line_comment()
                return
            self._emit(TT.SLASH_SLASH, "//", sl, sc)
            return
        if ch == "/" and self.current == "*":
            self._skip_block_comment(sl, sc); return
        if ch in ('"', "'"):
            # Triple-quote multiline string
            if self.current == ch and self.peek == ch:
                self.advance(); self.advance()  # consume 2nd and 3rd quote
                self._scan_triple_string(ch, sl, sc)
            else:
                self._scan_string(ch, sl, sc)
            return
        if ch == "0" and self.current in ("x","X","b","B","o","O"):
            self._scan_prefixed_number(ch, sl, sc); return
        if ch.isdigit():
            self._scan_number(ch, sl, sc); return
        if ch.isalpha() or ch == "_":
            # Check for f"..." / rf"..." / fr"..." string prefix
            if ch in ("f", "F") and self.current in ('"', "'"):
                self._scan_fstring(self.advance(), sl, sc, raw=False)
                return
            if ch in ("f", "F") and self.current in ("r", "R") and self.peek in ('"', "'"):
                # fr"..." — raw f-string (no backslash escapes)
                self.advance()
                self._scan_fstring(self.advance(), sl, sc, raw=True)
                return
            if ch in ("r", "R") and self.current in ("f", "F") and self.peek in ('"', "'"):
                # rf"..." — raw f-string (no backslash escapes)
                self.advance()
                self._scan_fstring(self.advance(), sl, sc, raw=True)
                return
            # Check for r"..." raw string prefix
            if ch in ("r", "R") and self.current in ('"', "'"):
                self._scan_raw_string(self.advance(), sl, sc)
                return
            self._scan_identifier(ch, sl, sc); return

        self._scan_operator(ch, sl, sc)

    # ── Comments ──────────────────────────────────────

    def _skip_line_comment(self):
        while self.current is not None and self.current != "\n":
            self.advance()

    def _skip_block_comment(self, sl, sc):
        self.advance()   # '*'
        depth = 1
        while self.current is not None and depth > 0:
            ch = self.advance()
            if ch == "/" and self.current == "*":  self.advance(); depth += 1
            elif ch == "*" and self.current == "/": self.advance(); depth -= 1
        if depth > 0:
            self._error("Unterminated block comment", sl, sc)

    def _scan_triple_string(self, quote: str, sl: int, sc: int):
        """Scan \"\"\"...\"\"\" or '''...''' multiline strings."""
        chars = []
        while self.current is not None:
            if self.current == quote and self.peek == quote and self.peek_at(2) == quote:
                self.advance(); self.advance(); self.advance()  # consume closing """
                self._emit(TT.STRING, "".join(chars), sl, sc)
                return
            ch = self.advance()
            if ch == "\\" and self.current is not None:
                esc = self.advance()
                _ESC = {"n":"\n","t":"\t","r":"\r","\\":"\\",'\"':'\"',"'":"'","0":"\0"}
                chars.append(_ESC.get(esc, esc))
            else:
                chars.append(ch)
        self._error("Unterminated triple-quoted string", sl, sc)

    def _scan_fstring(self, quote: str, sl: int, sc: int, raw: bool = False):
        """Scan f"...{expr}..." or $"...{expr}..." — store the raw template as FSTRING token.
        v1.9.15: $"..." is the new preferred syntax; both prefixes share this scanner.
        {{ and }} are literal brace escapes.
        Inside {}, quote characters are allowed (e.g. d["key"]).
        If raw=True, backslash escapes are NOT processed (rf"..." / fr"...")."""
        chars = []
        brace_depth = 0
        while self.current is not None:
            if self.current == quote and brace_depth == 0:
                break
            ch = self.advance()
            if ch == "\n" and not raw:
                self._error("Unterminated f-string — newline inside string", sl, sc)
            elif ch == "{" and self.current == "{" and brace_depth == 0:
                self.advance()
                chars.append("\x00{")
            elif ch == "}" and self.current == "}" and brace_depth == 0:
                self.advance()
                chars.append("}\x00")
            elif ch == "{":
                brace_depth += 1
                chars.append(ch)
            elif ch == "}":
                brace_depth = max(0, brace_depth - 1)
                chars.append(ch)
            elif not raw and ch == "\\" and self.current is not None and brace_depth == 0:
                esc = self.advance()
                _ESC = {"n":"\n","t":"\t","r":"\r","\\":"\\",'"':'"',"\'":"\'"}
                chars.append(_ESC.get(esc, esc))
            else:
                chars.append(ch)
        if self.current is None:
            self._error("Unterminated f-string", sl, sc)
        self.advance()
        self._emit(TT.FSTRING, "".join(chars), sl, sc)

    # ── Strings ───────────────────────────────────────

    def _scan_raw_string(self, quote: str, sl: int, sc: int):
        """r\"...\" — no escape processing at all. Backslashes are literal."""
        chars = []
        while self.current is not None and self.current != quote:
            ch = self.advance()
            if ch == "\n":
                self._error("Unterminated raw string — newline inside string", sl, sc)
            chars.append(ch)
        if self.current is None:
            self._error("Unterminated raw string literal", sl, sc)
        self.advance()  # closing quote
        self._emit(TT.STRING, "".join(chars), sl, sc)

    def _scan_string(self, quote: str, sl: int, sc: int):
        chars = []
        while self.current is not None and self.current != quote:
            ch = self.advance()
            if ch == "\n":
                self._error("Unterminated string — newline inside string", sl, sc)
            if ch == "\\":
                if self.current is None:
                    self._error("Unterminated escape sequence")
                esc = self.advance()
                _ESCAPES = {"n": "\n","t": "\t","r": "\r","\\": "\\",
                                '"': '"',"'": "'","0": "\0","a": "\a","b": "\b"}
                if esc in _ESCAPES:
                    chars.append(_ESCAPES[esc])
                else:
                    self._error(f"Unknown escape sequence: \\{esc}")
            else:
                chars.append(ch)
        if self.current is None:
            self._error("Unterminated string literal", sl, sc)
        self.advance()
        self._emit(TT.STRING, "".join(chars), sl, sc)

    # ── Numbers ───────────────────────────────────────

    def _scan_prefixed_number(self, first: str, sl: int, sc: int):
        """Hex 0xFF, binary 0b1010, octal 0o77"""
        prefix = self.advance()   # x/b/o
        digits = []
        if prefix in ("x","X"):
            while self.current and (self.current in "0123456789abcdefABCDEF_"):
                digits.append(self.advance())
            if not digits:
                self._error("Expected hex digits after '0x'", sl, sc)
            self._emit(TT.INT, int("".join(digits).replace("_",""), 16), sl, sc)
        elif prefix in ("b","B"):
            while self.current and self.current in "01_":
                digits.append(self.advance())
            if not digits:
                self._error("Expected binary digits after '0b'", sl, sc)
            self._emit(TT.INT, int("".join(digits).replace("_",""), 2), sl, sc)
        elif prefix in ("o","O"):
            while self.current and self.current in "01234567_":
                digits.append(self.advance())
            if not digits:
                self._error("Expected octal digits after '0o'", sl, sc)
            self._emit(TT.INT, int("".join(digits).replace("_",""), 8), sl, sc)

    def _scan_number(self, first: str, sl: int, sc: int):
        digits = [first]
        while self.current and (self.current.isdigit() or self.current == "_"):
            digits.append(self.advance())
        is_float = False

        # Check for `..` range — stop before it
        if self.current == "." and self.peek != ".":
            is_float = True
            digits.append(self.advance())
            if not (self.current and self.current.isdigit()):
                self._error("Expected digits after decimal point", sl, sc)
            while self.current and (self.current.isdigit() or self.current == "_"):
                digits.append(self.advance())

        if self.current in ("e","E"):
            is_float = True
            digits.append(self.advance())
            if self.current in ("+","-"): digits.append(self.advance())
            if not (self.current and self.current.isdigit()):
                self._error("Expected digits in scientific notation exponent", sl, sc)
            while self.current and self.current.isdigit():
                digits.append(self.advance())

        raw = "".join(digits).replace("_","")
        self._emit(TT.FLOAT if is_float else TT.INT,
                   float(raw) if is_float else int(raw), sl, sc)

    # ── Identifiers ───────────────────────────────────

    def _scan_identifier(self, first: str, sl: int, sc: int):
        chars = [first]
        while self.current and (self.current.isalnum() or self.current == "_"):
            chars.append(self.advance())
        text = "".join(chars)
        tt   = KEYWORDS.get(text, TT.IDENT)
        if tt == TT.BOOL:   value = (text == "true")
        elif tt == TT.NIL:  value = None   # nil literal → Python None
        elif tt == TT.NULL: value = None   # null (removed keyword — still lex it so error can fire)
        else:               value = text
        self._emit(tt, value, sl, sc)

    # ── Operators ─────────────────────────────────────

    def _scan_operator(self, ch: str, sl: int, sc: int):
        def emit(tt, val=None):
            self._emit(tt, val if val is not None else ch, sl, sc)

        if   ch == "+":
            if self.match("="): emit(TT.PLUS_EQ,   "+=")
            elif self.match("+"): emit(TT.PLUSPLUS, "++")
            else:               emit(TT.PLUS,        "+")
        elif ch == "-":
            if self.match(">"): emit(TT.ARROW,      "->")
            elif self.match("="): emit(TT.MINUS_EQ, "-=")
            else:               emit(TT.MINUS,       "-")
        elif ch == "*":
            if self.match("*"):
                if self.match("="): emit(TT.POWER_EQ, "**=")  # BUG-13 fix
                else:               emit(TT.POWER,     "**")
            elif self.match("="): emit(TT.STAR_EQ,  "*=")
            else:               emit(TT.STAR,         "*")
        elif ch == "/":
            if self.match("="):   emit(TT.SLASH_EQ,    "/=")
            else:                 emit(TT.SLASH,         "/")
        elif ch == "%":
            if self.match("="): emit(TT.PERCENT_EQ, "%=")
            else:               emit(TT.PERCENT,     "%")
        elif ch == "=":
            if self.match(">"): emit(TT.FAT_ARROW,  "=>")
            elif self.match("="): emit(TT.EQ,       "==")
            else:               emit(TT.ASSIGN,       "=")
        elif ch == "!":
            if self.match("="): emit(TT.NEQ,        "!=")
            else:               emit(TT.NOT,          "!")
        elif ch == "<":
            if self.match("<"):
                if self.match("="): emit(TT.LSHIFT_EQ,   "<<=" )
                else:               emit(TT.LSHIFT,        "<<")
            elif self.match("="): emit(TT.LTE,         "<=")
            else:                 emit(TT.LT,            "<")
        elif ch == ">":
            if self.match(">"):
                if self.match("="): emit(TT.RSHIFT_EQ,   ">>=")
                else:               emit(TT.RSHIFT,        ">>")
            elif self.match("="): emit(TT.GTE,         ">=")
            else:                 emit(TT.GT,            ">")
        elif ch == "&":
            if self.match("&"): emit(TT.AND,           "&&")
            elif self.match("="): emit(TT.AMP_EQ,     "&=")
            else:               emit(TT.BIT_AND,         "&")
        elif ch == "|":
            if self.match("|"):  emit(TT.OR,            "||")
            elif self.match(">"): emit(TT.PIPE_GT,      "|>")
            elif self.match("="): emit(TT.PIPE_EQ,     "|=")
            else:                emit(TT.BIT_OR,          "|")
        elif ch == "^":
            if self.match("="): emit(TT.CARET_EQ,     "^=")
            else:               emit(TT.BIT_XOR,         "^")
        elif ch == "~":         emit(TT.BIT_NOT,         "~")
        elif ch == ".":
            if self.current == "." and self.peek == ".":
                self.advance(); self.advance()
                emit(TT.ELLIPSIS, "...")
            elif self.match("."):
                if self.match("="): emit(TT.DOTDOT_EQ, "..=")
                else:               emit(TT.DOTDOT,     "..")
            else:               emit(TT.DOT,          ".")
        elif ch == ":":
            if self.match(":"): emit(TT.DOUBLE_COLON, "::")
            else:               emit(TT.COLON,         ":")
        elif ch == "?":
            if self.match("?"):
                if self.match("="): emit(TT.NULLISH_EQ,   "??=")   # v2.2.0
                else:               emit(TT.NULLISH,       "??")
            elif self.match("."): emit(TT.QUESTION_DOT, "?.")
            else:                emit(TT.QUESTION,       "?")
        elif ch == "#":
            # v1.9.6: # is the line-comment character (was: HASH annotation token)
            self._skip_line_comment(); return
        elif ch == "$":
            # v1.9.15: $"..." interpolated string (preferred over f"...")
            if self.current in ('"', "'"):
                self._scan_fstring(self.advance(), sl, sc)
                return
            # bare $ not followed by quote — skip (not used otherwise)
        elif ch == "@":         emit(TT.AT,           "@")
        elif ch == "(":         emit(TT.LPAREN)
        elif ch == ")":         emit(TT.RPAREN)
        elif ch == "{":         emit(TT.LBRACE)
        elif ch == "}":         emit(TT.RBRACE)
        elif ch == "[":         emit(TT.LBRACKET)
        elif ch == "]":         emit(TT.RBRACKET)
        elif ch == ",":         emit(TT.COMMA)
        elif ch == ";":         emit(TT.SEMICOLON)
        elif ord(ch) > 127:
            # Non-ASCII character outside a string/comment — silently skip.
            # This handles box-drawing, em-dashes, arrows etc. in comments
            # where the comment scanner may not have consumed them yet.
            pass
        else:
            self._error(f"Unexpected character: {ch!r}", sl, sc)


# ── Rust lexer bridge ───────────────────────────────────────────

_RUST_TT: dict = {
    "Int":   TT.INT,   "Float": TT.FLOAT, "String": TT.STRING,
    "Bool":  TT.BOOL,  "Ident": TT.IDENT, "Nil":    TT.NIL,
    "Let":   TT.LET,   "Const": TT.CONST, "Fn":     TT.FN,
    "If":    TT.IF,    "Else":  TT.ELSE,  "While":  TT.WHILE,
    "For":   TT.FOR,   "In":    TT.IN,    "Return": TT.RETURN,
    "Break": TT.BREAK, "Continue": TT.CONTINUE,
    "Struct": TT.STRUCT, "Enum": TT.ENUM, "Class": TT.SCENE,
    "Switch": TT.MATCH,  "Case": TT.CASE, "Default": TT.CASE,
    "Try":  TT.TRY,  "Catch": TT.CATCH, "Finally": TT.FINALLY,
    "Throw": TT.THROW, "Yield": TT.YIELD,
    "Async": TT.ASYNC, "Await": TT.AWAIT,
    "And":  TT.AND,  "Or": TT.OR,  "Not": TT.NOT,
    "OnStart": TT.ON_START, "OnUpdate": TT.ON_UPDATE,
    "OnDraw":  TT.ON_DRAW,  "OnExit":   TT.ON_EXIT,
    "Node": TT.NODE, "OnReady": TT.ON_READY,
    "OnNodeUpdate": TT.ON_NODE_UPDATE, "OnNodeDraw": TT.ON_NODE_DRAW,
    "IntType": TT.INT_TYPE, "FloatType": TT.FLOAT_TYPE,
    "BoolType": TT.BOOL_TYPE, "StringType": TT.STRING_TYPE,
    "VoidType": TT.VOID_TYPE,
    "Import": TT.IMPORT, "From": TT.FROM, "As": TT.AS,
    "Export": TT.EXPORT,
    "Self":  TT.SELF,  "Super": TT.SUPER, "Null": TT.NULL,
    "Spawn": TT.SPAWN, "Select": TT.SELECT, "Then": TT.THEN,
    "Abstract": TT.ABSTRACT, "Interface": TT.INTERFACE,
    "Impl": TT.IMPL, "Pub": TT.PUB,
    "Is": TT.IS, "Div": TT.DIV,
    "Defer": TT.DEFER, "Repeat": TT.REPEAT, "Until": TT.UNTIL,
    "Plus": TT.PLUS, "Minus": TT.MINUS, "Star": TT.STAR,
    "Slash": TT.SLASH, "Percent": TT.PERCENT, "Power": TT.POWER,
    "Eq": TT.EQ, "Neq": TT.NEQ, "Lt": TT.LT, "Lte": TT.LTE,
    "Gt": TT.GT, "Gte": TT.GTE,
    "BitwiseAnd": TT.BIT_AND, "BitwiseOr": TT.BIT_OR,
    "BitwiseXor": TT.BIT_XOR, "BitwiseNot": TT.BIT_NOT,
    "LeftShift": TT.LSHIFT, "RightShift": TT.RSHIFT,
    "PlusPlus": TT.PLUSPLUS, "SlashSlash": TT.SLASH_SLASH,
    "Question": TT.QUESTION, "QuestionDot": TT.QUESTION_DOT,
    "Nullish": TT.NULLISH, "NullishEq": TT.NULLISH_EQ,
    "PipeGt": TT.PIPE_GT,
    "Arrow": TT.ARROW, "FatArrow": TT.FAT_ARROW,
    "LeftParen": TT.LPAREN, "RightParen": TT.RPAREN,
    "LeftBrace": TT.LBRACE, "RightBrace": TT.RBRACE,
    "LeftBracket": TT.LBRACKET, "RightBracket": TT.RBRACKET,
    "Comma": TT.COMMA, "Dot": TT.DOT, "Semicolon": TT.SEMICOLON,
    "Colon": TT.COLON, "DoubleColon": TT.DOUBLE_COLON,
    "At": TT.AT,
    "DotDot": TT.DOTDOT, "DotDotEq": TT.DOTDOT_EQ,
    "Ellipsis": TT.ELLIPSIS,
    "FString": TT.FSTRING, "Eof": TT.EOF,
    "Pipe": TT.PIPE, "Assign": TT.ASSIGN,
    "PlusEq": TT.PLUS_EQ, "MinusEq": TT.MINUS_EQ,
    "StarEq": TT.STAR_EQ, "SlashEq": TT.SLASH_EQ,
    "PercentEq": TT.PERCENT_EQ, "PowerEq": TT.POWER_EQ,
    "AmpEq": TT.AMP_EQ, "PipeEq": TT.PIPE_EQ,
    "CaretEq": TT.CARET_EQ, "LShiftEq": TT.LSHIFT_EQ,
    "RShiftEq": TT.RSHIFT_EQ,
}

# ── Compound assign → TT map ──────────────────────────────────

_COMPOUND_ASSIGN: dict = {
    "+=": TT.PLUS_EQ,   "-=": TT.MINUS_EQ,  "*=": TT.STAR_EQ,
    "/=": TT.SLASH_EQ,  "%=": TT.PERCENT_EQ, "**=": TT.POWER_EQ,
    "&=": TT.AMP_EQ,    "|=": TT.PIPE_EQ,   "^=": TT.CARET_EQ,
    "<<=": TT.LSHIFT_EQ, ">>=": TT.RSHIFT_EQ,
}

# ── Rust lexer operator values (empty from Rust, fill with symbols) ─

_RUST_OP_VALUES: dict = {
    "Plus": "+", "Minus": "-", "Star": "*", "Slash": "/",
    "Percent": "%", "Power": "**",
    "Eq": "==", "Neq": "!=", "Lt": "<", "Lte": "<=",
    "Gt": ">", "Gte": ">=",
    "BitwiseAnd": "&", "BitwiseOr": "|", "BitwiseXor": "^",
    "BitwiseNot": "~", "LeftShift": "<<", "RightShift": ">>",
    "PlusPlus": "++", "SlashSlash": "//",
    "Assign": "=", "Arrow": "->", "FatArrow": "=>",
    "Colon": ":", "DoubleColon": "::",
    "Comma": ",", "Dot": ".", "Semicolon": ";",
    "LeftParen": "(", "RightParen": ")",
    "LeftBrace": "{", "RightBrace": "}",
    "LeftBracket": "[", "RightBracket": "]",
    "Pipe": "|", "At": "@",
    "DotDot": "..", "DotDotEq": "..=",
    "Question": "?", "QuestionDot": "?.",
    "Nullish": "??", "NullishEq": "??=",
    "Ellipsis": "...", "PipeGt": "|>",
    "And": "&&", "Or": "||", "Not": "!",
    "PlusEq": "+=", "MinusEq": "-=",
    "StarEq": "*=", "SlashEq": "/=",
    "PercentEq": "%=", "PowerEq": "**=",
    "AmpEq": "&=", "PipeEq": "|=",
    "CaretEq": "^=", "LShiftEq": "<<=",
    "RShiftEq": ">>=",
    "OnStart": "on_start", "OnUpdate": "on_update",
    "OnDraw": "on_draw", "OnExit": "on_exit",
    "Node": "node", "OnReady": "_ready",
    "OnNodeUpdate": "_update", "OnNodeDraw": "_draw",
    "IntType": "int", "FloatType": "float",
    "BoolType": "bool", "StringType": "string",
    "VoidType": "void",
    "Null": "null", "Self": "self", "Super": "super",
    "Import": "import", "From": "from", "As": "as",
    "Export": "export",
    "Is": "is", "Div": "div",
}

# ── Ident value overrides (non-string values) ─────────────────

_IDENT_MAP: dict = {
    "true": True, "false": False, "nil": None, "null": None,
}

# Rust lexer maps these keywords to Identifier(value); convert to proper token type
_RUST_SOFT_KEYWORDS: dict = {
    "import":    TT.IMPORT,
    "from":      TT.FROM,
    "as":        TT.AS,
    "export":    TT.EXPORT,
    "self":      TT.SELF,
    "super":     TT.SUPER,
    "interface": TT.INTERFACE,
    "impl":      TT.IMPL,
    "pub":       TT.PUB,
    "spawn":     TT.SPAWN,
    "select":    TT.SELECT,
    "then":      TT.THEN,
    "abstract":  TT.ABSTRACT,
    "defer":     TT.DEFER,
    "repeat":    TT.REPEAT,
    "until":     TT.UNTIL,
}

def tokenize(source: str, filename: str = "<stdin>") -> List[Token]:
    try:
        from inscript_parser import lex as _rust_lex
        try:
            raw_result = _rust_lex(source)
        except Exception as e:
            raise LexerError(str(e))
        tokens = []
        for d in raw_result:
            tt_name = d["token_type"]
            tt = _RUST_TT.get(tt_name)
            if tt is None:
                continue
            val_str = d["value"]
            line, col = d["line"], d["column"]

            # Disambiguate compound assigns
            if tt == TT.ASSIGN and val_str in _COMPOUND_ASSIGN:
                tt = _COMPOUND_ASSIGN[val_str]
            # Disambiguate // floor division vs / division
            elif tt == TT.SLASH and val_str == "//":
                tt = TT.SLASH_SLASH
            # Disambiguate ++ string concat vs + addition
            elif tt == TT.PLUS and val_str == "++":
                tt = TT.PLUSPLUS
            # Rust lexer maps some keywords to Identifier (soft keywords)
            elif tt == TT.IDENT and val_str in _RUST_SOFT_KEYWORDS:
                tt = _RUST_SOFT_KEYWORDS[val_str]

            # Convert value to correct Python type
            if tt == TT.INT:
                val = int(val_str) if val_str else 0
            elif tt == TT.FLOAT:
                val = float(val_str) if val_str else 0.0
            elif tt == TT.BOOL:
                val = val_str == "true"
            elif tt == TT.STRING:
                val = val_str
            elif tt == TT.FSTRING:
                val = val_str
            elif tt == TT.NIL or tt == TT.NULL:
                val = None
            elif tt == TT.IDENT and val_str in _IDENT_MAP:
                val = _IDENT_MAP[val_str]
            else:
                val = val_str if val_str else _RUST_OP_VALUES.get(tt_name, tt_name.lower())

            tokens.append(Token(tt, val, line, col))
        return tokens
    except ImportError:
        return Lexer(source, filename).tokenize()
