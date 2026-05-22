# -*- coding: utf-8 -*-
"""
inscript_fmt.py — InScript Code Formatter v1.0.19
===================================================
Token-based formatter using the existing Lexer.

Rules:
  - 4-space indentation (configurable)
  - Spaces around binary operators: + - * / % == != < > <= >= and or
  - No space before : in type annotations or dict literals
  - Space after , in params/args/arrays/dicts
  - Opening { on same line (K&R style)
  - Blank line between top-level declarations
  - Trailing newline
  - Max line length 100 (informational only — no hard wrap yet)

Usage:
  python inscript_fmt.py file.ins          # format in place
  python inscript_fmt.py file.ins --check  # exit 1 if not formatted
  python inscript_fmt.py file.ins --dry-run  # print without writing
  python inscript_fmt.py --stdin           # read from stdin
"""
from __future__ import annotations
import sys, os, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from lexer import Lexer, TT, Token

# ── Token categories ─────────────────────────────────────────────────────────
_BINARY_OPS = {
    TT.PLUS, TT.MINUS, TT.STAR, TT.SLASH, TT.PERCENT, TT.POWER, TT.EQ, TT.NEQ, TT.LT, TT.GT, TT.LTE, TT.GTE, TT.AND, TT.OR, TT.BIT_AND, TT.BIT_OR, TT.BIT_XOR, TT.LSHIFT, TT.RSHIFT, TT.ASSIGN, TT.PLUS_EQ, TT.MINUS_EQ, TT.STAR_EQ, TT.SLASH_EQ, TT.PERCENT_EQ, TT.POWER_EQ, TT.LSHIFT_EQ, TT.RSHIFT_EQ, TT.AMP_EQ, TT.PIPE_EQ, TT.CARET_EQ, TT.PIPE_GT, TT.PLUSPLUS, TT.FAT_ARROW
}
_OPEN_DELIM  = {TT.LBRACE, TT.LBRACKET, TT.LPAREN}
_CLOSE_DELIM = {TT.RBRACE, TT.RBRACKET, TT.RPAREN}
_UNARY_OK    = {TT.MINUS, TT.NOT, TT.BIT_NOT, TT.ELLIPSIS}
_NO_SPACE_BEFORE = {TT.COMMA, TT.SEMICOLON, TT.COLON, TT.RPAREN, TT.RBRACKET, TT.RBRACE,
                     TT.DOT, TT.QUESTION_DOT, TT.QUESTION}
_NO_SPACE_AFTER  = {TT.LPAREN, TT.LBRACKET, TT.DOT, TT.QUESTION_DOT, TT.NOT,
                     TT.BIT_NOT, TT.ELLIPSIS}

# Keywords that start blocks (followed by {)
_BLOCK_KW = {'if', 'else', 'while', 'for', 'fn', 'struct', 'enum', 'interface',
             'mixin', 'match', 'case', 'try', 'catch', 'finally', 'impl', 'comptime'}

# Keywords that are top-level declarations (blank line before them, not after imports)
_TOP_LEVEL_KW = {'fn', 'struct', 'enum', 'interface', 'mixin', 'impl'}


def _get_attr(t):
    """Safe value access for Token."""
    v = getattr(t, 'value', None)
    return str(v) if v is not None else ''


class Formatter:
    def __init__(self, source: str, indent: int = 4, max_line: int = 100):
        self.source   = source
        self.indent   = indent
        self.max_line = max_line
        self._tokens: list[Token] = []
        self._out:    list[str]   = []
        self._level   = 0         # current indent level
        self._col     = 0         # current column
        self._prev_tt: TT | None  = None
        self._prev_v:  str        = ''

    def _lex(self) -> list[Token]:
        try:
            return Lexer(self.source).tokenize()
        except Exception:
            return []

    def format(self) -> str:
        tokens = self._lex()
        if not tokens:
            return self.source  # fallback: return unchanged on lex error

        # Filter to non-whitespace tokens; track original line numbers
        toks = [t for t in tokens if t.type != TT.EOF]
        n = len(toks)
        if n == 0:
            return ''

        result_lines: list[str] = []
        current_line: list[str] = []
        indent_level = 0
        prev: Token | None = None
        prev2: Token | None = None
        # v2.1.1: context tracking for inline case arms and struct fields
        _in_case       = False   # True after 'case <pat>' — next { stays inline
        _struct_depths = []      # indent_levels at which struct bodies were opened
        _brace_stack   = []      # 'dict' or 'block' for each open brace
        _in_generic    = 0       # v2.1.1: depth counter for Array<T> generics

        def cur_indent():
            return ' ' * (indent_level * self.indent)

        def flush(add_blank=False):
            ln = ''.join(current_line).rstrip()
            result_lines.append(ln)
            if add_blank:
                result_lines.append('')
            current_line.clear()

        def needs_blank_before(tok: Token) -> bool:
            """Top-level fn/struct/enum etc. get a blank line before them."""
            v = _get_attr(tok)
            if v not in _TOP_LEVEL_KW:
                return False
            # Only at indent 0
            return indent_level == 0

        i = 0
        last_was_blank = False

        while i < n:
            tok  = toks[i]
            nxt  = toks[i+1] if i+1 < n else None
            tt   = tok.type
            v    = _get_attr(tok)

            # ── newlines (we generate our own) ──────────────────────────────
            # We don't emit the original newlines — we control them ourselves

            # ── opening brace → same line, then newline ──────────────────
            if tt == TT.LBRACE:
                # v2.1.1: dict/object literal { stays inline when preceded by
                # an assignment, operator, (, [, or , — not a block opener
                _dict_ctx_types = {
                    TT.ASSIGN, TT.PLUS_EQ, TT.MINUS_EQ,
                    TT.LPAREN, TT.LBRACKET, TT.COMMA, TT.COLON,
                    TT.PLUS, TT.MINUS, TT.STAR, TT.SLASH, TT.PERCENT,
                    TT.RETURN, TT.FAT_ARROW,
                }
                _is_dict_literal = prev and prev.type in _dict_ctx_types
                # Put { on same line with a space
                if current_line and current_line[-1] not in ('', ' ', '\t'):
                    current_line.append(' ')
                current_line.append('{')
                indent_level += 1
                # v2.1.1: track struct/interface bodies for field-separator newlines
                # prev is the struct NAME (e.g. 'Player'), prev2 is the 'struct' keyword
                if prev2 and _get_attr(prev2) in ('struct', 'interface', 'mixin'):
                    _struct_depths.append(indent_level)
                # v2.1.1: dict literal — keep contents on same line, don't flush
                _brace_stack.append('dict' if _is_dict_literal else 'block')
                if _is_dict_literal:
                    prev = tok; i += 1
                    continue
                # v2.1.1: case arm inline — if _in_case, keep { expr } on same line
                if _in_case:
                    _in_case = False
                    # Collect tokens until matching } into same line
                    depth2 = 1; j = i + 1
                    inline_toks = []
                    while j < n and depth2 > 0:
                        t2 = toks[j]
                        if t2.type == TT.LBRACE: depth2 += 1
                        elif t2.type == TT.RBRACE: depth2 -= 1
                        if depth2 > 0: inline_toks.append(t2)
                        j += 1
                    # Only inline if content is simple (no newlines, single expr)
                    has_nested = any(t2.type == TT.LBRACE for t2 in inline_toks)
                    if not has_nested and len(inline_toks) <= 8:
                        # Emit inline
                        current_line.append(' ')
                        for t2 in inline_toks:
                            v2 = _get_attr(t2)
                            if t2.type == TT.STRING: current_line.append('"'+v2+'"')
                            elif t2.type == TT.FSTRING: current_line.append('$"'+v2+'"')
                            else: current_line.append(str(v2) if v2 else t2.type.name.lower())
                            current_line.append(' ')
                        current_line.append('}')
                        indent_level -= 1
                        if _struct_depths and indent_level < _struct_depths[-1]:
                            _struct_depths.pop()
                        flush()
                        prev = toks[j-1]; i = j
                        continue
                flush()
                prev = tok; i += 1
                continue

            # ── closing brace → dedent then } ────────────────────────────
            if tt == TT.RBRACE:
                _brace_kind = _brace_stack.pop() if _brace_stack else 'block'
                indent_level = max(0, indent_level - 1)
                # v2.1.1: pop struct depth tracking
                if _struct_depths and indent_level < _struct_depths[-1]:
                    _struct_depths.pop()
                if _brace_kind == 'dict':
                    # Dict literal: emit } inline, no flush (keeps content on same line)
                    current_line.append('}')
                    prev = tok; i += 1
                    continue
                else:
                    # Block: flush pending content then emit } at correct indent
                    if current_line and ''.join(current_line).strip():
                        flush()
                    current_line.append(cur_indent() + '}')
                    # If next token is 'else', 'catch', 'finally' — stay on same line
                    if nxt and _get_attr(nxt) in ('else', 'catch', 'finally'):
                        current_line.append(' ')
                    else:
                        flush()
                    prev = tok; i += 1
                    continue

            # ── semicolons → newline ──────────────────────────────────────
            if tt == TT.SEMICOLON:
                flush()
                prev = tok; i += 1
                continue

            # ── start of a new token on a new line ───────────────────────
            # v2.1.1: struct field separator — flush before next field
            # Must come BEFORE `if not current_line` so indent isn't doubled
            if _struct_depths and indent_level == _struct_depths[-1]:
                if (tt == TT.IDENT and nxt and nxt.type == TT.COLON and
                        current_line and ''.join(current_line).strip()):
                    flush()  # let `if not current_line` add the indent
                    prev = None  # reset spacing context — fresh line

            if not current_line:
                # blank line before top-level declarations (except first)
                if needs_blank_before(tok) and result_lines and result_lines[-1] != '':
                    result_lines.append('')
                current_line.append(cur_indent())

            # ── spacing logic ─────────────────────────────────────────────
            needs_space = False
            _line_is_indent_only = current_line and ''.join(current_line).strip() == ''
            if prev is not None and not _line_is_indent_only:
                ptt = prev.type
                pv  = _get_attr(prev)
                # v2.1.1: always space after colon (type annotations, dict literals)
                if ptt == TT.COLON and tt not in _CLOSE_DELIM and tt != TT.COLON:
                    needs_space = True
                # Always space after comma
                if ptt == TT.COMMA:
                    needs_space = True
                # Space around binary ops
                elif tt in _BINARY_OPS and pv not in ('', ' ') and _in_generic == 0:
                    # Check it's actually binary (not unary minus after operator/open)
                    if ptt not in _OPEN_DELIM and ptt not in _BINARY_OPS:
                        needs_space = True
                    elif tt == TT.ASSIGN:
                        needs_space = True
                elif ptt in _BINARY_OPS and _in_generic == 0:
                    needs_space = True
                # No space before these
                elif tt in _NO_SPACE_BEFORE:
                    needs_space = False
                # No space after these
                elif ptt in _NO_SPACE_AFTER:
                    needs_space = False
                # Space after keyword if followed by ( or ident
                elif pv in _BLOCK_KW | {'return', 'let', 'const', 'import', 'from',
                                         'throw', 'yield', 'await', 'not', 'in',
                                         'as', 'is', 'type', 'static', 'priv', 'pub',
                                         'abstract', 'async', 'comptime'}:
                    needs_space = (tt != TT.LPAREN or pv in ('if', 'while', 'for', 'match'))
                # Space before keywords like 'if', 'in', 'as', 'is', 'and', 'or', 'not'
                elif v in ('if', 'else', 'in', 'not', 'as', 'is', 'and', 'or', 'implements',
                           'extends', 'with'):
                    needs_space = True
                # Default: space between two identifiers/literals
                elif (ptt in (TT.IDENT, TT.INT_TYPE, TT.FLOAT_TYPE, TT.STRING_TYPE,
                               TT.BOOL_TYPE, TT.INT, TT.FLOAT, TT.STRING, TT.FSTRING) and
                      tt  in (TT.IDENT, TT.INT_TYPE, TT.FLOAT_TYPE, TT.STRING_TYPE,
                               TT.BOOL_TYPE, TT.INT, TT.FLOAT, TT.STRING, TT.FSTRING,
                               TT.LBRACKET)):
                    needs_space = True

            if needs_space and current_line and current_line[-1] != ' ':
                current_line.append(' ')

            # ── emit token ────────────────────────────────────────────────
            if tt == TT.FSTRING:
                # v2.1.1: always emit $"..." (preferred syntax since v1.9.15)
                current_line.append('$"' + v + '"')
            elif tt == TT.STRING:
                # Preserve original quotes
                current_line.append('"' + v.replace('"', '\\"') + '"')
            elif tt == TT.LT and prev and prev.type == TT.IDENT and _get_attr(prev) and _get_attr(prev)[0].isupper():
                # v2.1.1: Array<T> — enter generic mode, suppress spaces around <>
                if current_line and current_line[-1] == ' ':
                    current_line.pop()
                _in_generic += 1
                current_line.append('<')
                prev = tok; i += 1
                continue
            elif tt == TT.GT and _in_generic > 0:
                # v2.1.1: closing generic >
                _in_generic -= 1
                current_line.append('>')
                prev = tok; i += 1
                continue
            elif tt == TT.GTE and _in_generic > 0:
                # v2.1.1: lexer fused '>=' — split into > (close generic) + = (assign)
                _in_generic -= 1
                current_line.append('>')
                current_line.append(' ')
                current_line.append('=')
                current_line.append(' ')
                prev = tok; i += 1
                continue
            elif tt == TT.ARROW:
                # v2.1.1: spaces around -> (return type annotation)
                if current_line and current_line[-1] not in (' ', ''):
                    current_line.append(' ')
                current_line.append('->')
                current_line.append(' ')
                prev = tok; i += 1
                continue
            elif tt == TT.FAT_ARROW:
                current_line.append('=>')
            elif tt == TT.PLUSPLUS:
                current_line.append('++')
            elif tt == TT.DOTDOT:
                current_line.append('..')
            elif tt == TT.DOTDOT_EQ:
                current_line.append('..=')
            elif tt == TT.QUESTION_DOT:
                current_line.append('?.')
            elif tt == TT.PIPE_GT:
                current_line.append('|>')
            elif v:
                current_line.append(str(v))
            else:
                current_line.append(tok.type.name.lower())

            # v2.1.1: track CASE keyword for inline arm formatting
            if tt == TT.CASE:
                _in_case = True
            elif _in_case and tt == TT.LBRACE:
                pass  # handled above
            elif _in_case and tt not in (
                    TT.IDENT, TT.INT, TT.FLOAT, TT.STRING,
                    TT.INT_TYPE, TT.FLOAT_TYPE, TT.STRING_TYPE, TT.BOOL_TYPE,
                    TT.PIPE, TT.IF, TT.CASE, TT.NOT,
                    TT.NIL, TT.BOOL,
                    TT.DOTDOT, TT.DOTDOT_EQ,
                    # guard expression operators: case h if h > 5
                    TT.EQ, TT.NEQ, TT.LT, TT.GT, TT.LTE, TT.GTE,
                    TT.AND, TT.OR, TT.PLUS, TT.MINUS, TT.STAR, TT.SLASH,
                    TT.PERCENT, TT.LPAREN, TT.RPAREN):
                _in_case = False
            prev2 = prev
            prev = tok
            i += 1

        # flush remaining
        if current_line:
            flush()

        # Remove trailing blank lines, ensure single trailing newline
        while result_lines and result_lines[-1] == '':
            result_lines.pop()
        return '\n'.join(result_lines) + '\n'


def format_source(source: str, indent: int = 4) -> str:
    return Formatter(source, indent=indent).format()


def main(argv=None):
    p = argparse.ArgumentParser(
        prog='inscript fmt',
        description='InScript code formatter'
    )
    p.add_argument('files', nargs='*', help='.ins files to format')
    p.add_argument('--check',   action='store_true',
                   help='Exit 1 if any file is not already formatted')
    p.add_argument('--dry-run', action='store_true',
                   help='Print formatted output without writing')
    p.add_argument('--stdin',   action='store_true',
                   help='Read from stdin, write to stdout')
    p.add_argument('--indent',  type=int, default=4,
                   help='Indent width (default: 4)')
    p.add_argument('--diff',    action='store_true',
                   help='Show unified diff instead of rewriting')
    args = p.parse_args(argv)

    # Colour helpers
    def green(s):  return f'\033[32m{s}\033[0m' if sys.stdout.isatty() else s
    def red(s):    return f'\033[31m{s}\033[0m' if sys.stdout.isatty() else s
    def yellow(s): return f'\033[33m{s}\033[0m' if sys.stdout.isatty() else s
    def dim(s):    return f'\033[2m{s}\033[0m'  if sys.stdout.isatty() else s

    any_changed = False

    if args.stdin:
        source   = sys.stdin.read()
        formatted = format_source(source, indent=args.indent)
        sys.stdout.write(formatted)
        return 0

    if not args.files:
        # Auto-discover .ins files in current directory
        args.files = [str(p) for p in Path('.').glob('**/*.ins')
                      if '.git' not in str(p)]
        if not args.files:
            print(dim('No .ins files found.'))
            return 0

    for path_str in args.files:
        path = Path(path_str)
        if not path.exists():
            print(red(f'error: {path} not found'))
            continue
        if path.suffix != '.ins':
            continue

        source    = path.read_text(encoding='utf-8')
        formatted = format_source(source, indent=args.indent)

        if source == formatted:
            if args.check:
                print(green(f'  ok   {path}'))
            continue

        any_changed = True

        if args.check:
            print(red(f'  FAIL {path}  (needs formatting)'))
        elif args.diff:
            import difflib
            diff = difflib.unified_diff(
                source.splitlines(keepends=True),
                formatted.splitlines(keepends=True),
                fromfile=str(path),
                tofile=str(path) + ' (formatted)'
            )
            sys.stdout.writelines(diff)
        elif args.dry_run:
            print(f'--- {path} ---')
            print(formatted)
        else:
            path.write_text(formatted, encoding='utf-8')
            print(green(f'  fmt  {path}'))

    if args.check and any_changed:
        print(red('\nSome files need formatting. Run `inscript fmt` to fix.'))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
