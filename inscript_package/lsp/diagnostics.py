"""
lsp/diagnostics.py — InScript LSP diagnostics
v2.1.0: reports ALL errors (MultiError), correct 0-indexed line/col.
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _parse_error_location(err_str: str):
    m = re.search(r'Line\s+(\d+)[,\s]+Col\s+(\d+)', err_str, re.IGNORECASE)
    if m:
        return max(0, int(m.group(1)) - 1), max(0, int(m.group(2)) - 1)
    return 0, 0


def _error_to_diag(err_str: str, severity: str = "error") -> dict:
    line, col = _parse_error_location(err_str)
    clean = re.sub(r'\x1b\[[0-9;]*m', '', err_str).strip()
    clean = re.sub(r'\s*See: https?://\S+', '', clean).strip()
    code_match = re.search(r'(E\d{4})', clean)
    return {
        "line":     line,
        "col":      col,
        "end_col":  col + 30,
        "message":  clean,
        "severity": severity,
        "code":     code_match.group(1) if code_match else "",
    }


def get_diagnostics(source: str) -> list:
    """Run lex → parse → analyze on source. Returns all diagnostics."""
    from lexer  import Lexer
    from parser import Parser
    from errors import MultiError

    diagnostics = []

    try:
        tokens = Lexer(source).tokenize()
    except Exception as e:
        return [_error_to_diag(str(e), "error")]

    try:
        ast = Parser(tokens, source).parse()
    except Exception as e:
        return [_error_to_diag(str(e), "error")]

    try:
        from analyzer import Analyzer
        Analyzer().analyze(ast)
    except MultiError as me:
        for err in me.errors:
            diagnostics.append(_error_to_diag(str(err), "error"))
    except Exception as e:
        diagnostics.append(_error_to_diag(str(e), "warning"))

    return diagnostics
