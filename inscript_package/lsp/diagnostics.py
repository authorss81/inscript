"""Convert InScript parse/analysis errors into LSP Diagnostic objects."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_diagnostics(source: str) -> list:
    """
    Run the InScript lexer + parser + analyzer on `source`.
    Returns a list of dicts:
      {"line": int, "col": int, "end_col": int, "message": str, "severity": "error"|"warning"}
    """
    from lexer    import Lexer, LexerError
    from parser   import Parser, ParseError
    from analyzer import Analyzer, SemanticError
    from errors   import InScriptError

    diagnostics = []

    try:
        tokens = Lexer(source).tokenize()
    except LexerError as e:
        diagnostics.append({
            "line":    max(0, getattr(e, "line", 1) - 1),
            "col":     max(0, getattr(e, "col",  0)),
            "end_col": max(0, getattr(e, "col",  0)) + 10,
            "message": str(e),
            "severity": "error",
        })
        return diagnostics

    try:
        from parser import Parser
        ast = Parser(tokens).parse()
    except Exception as e:
        line = max(0, getattr(e, "line", 1) - 1)
        col  = max(0, getattr(e, "col",  0))
        msg  = getattr(e, "message", str(e))
        diagnostics.append({"line": line, "col": col, "end_col": col + 20,
                             "message": msg, "severity": "error"})
        return diagnostics

    try:
        from analyzer import Analyzer
        Analyzer().analyze(ast)
    except Exception as e:
        line = max(0, getattr(e, "line", 1) - 1)
        col  = max(0, getattr(e, "col",  0))
        msg  = getattr(e, "message", str(e))
        diagnostics.append({"line": line, "col": col, "end_col": col + 20,
                             "message": msg, "severity": "warning"})

    return diagnostics
