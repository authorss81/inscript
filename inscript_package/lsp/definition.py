# lsp/definition.py — Go-to-definition, find-all-references, rename
# v2.5.0

from __future__ import annotations
from typing import List, Dict, Optional, Tuple
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ast_nodes import IdentExpr, GetAttrExpr, Program


def _word_at(source: str, line: int, col: int) -> str:
    """Extract the identifier word under the cursor."""
    lines = source.splitlines()
    if line >= len(lines):
        return ""
    row = lines[line]
    # Walk left to find word start
    start = col
    while start > 0 and (row[start-1].isalnum() or row[start-1] == '_'):
        start -= 1
    # Walk right to find word end
    end = col
    while end < len(row) and (row[end].isalnum() or row[end] == '_'):
        end += 1
    return row[start:end]


def get_definition(source: str, line: int, col: int) -> Optional[Dict]:
    """
    Return {uri, line, col} for the definition of the symbol at (line, col).
    Returns None if not found.
    """
    try:
        from parser   import parse
        from analyzer import analyze
        program = parse(source)
        symbols = analyze(program, source)
    except Exception:
        return None

    word = _word_at(source, line, col)
    if not word:
        return None

    sym = symbols.get(word)
    if sym and sym.line > 0:
        return {"line": sym.line - 1, "col": sym.col}
    return None


def _collect_references(node, name: str, results: list):
    """Recursively walk AST collecting all references to the given name."""
    if node is None:
        return
    t = type(node).__name__
    # IdentExpr — variable/function references
    if t == "IdentExpr" and node.name == name:
        results.append({"line": node.line - 1, "col": node.col,
                        "end_col": node.col + len(name)})
        return
    # StructInitExpr — Point{x: 1.0}
    if t == "StructInitExpr" and node.struct_name == name and node.line > 0:
        results.append({"line": node.line - 1, "col": node.col,
                        "end_col": node.col + len(name)})
    # StructDecl — the definition itself
    if t == "StructDecl" and node.name == name and node.line > 0:
        results.append({"line": node.line - 1, "col": node.col,
                        "end_col": node.col + len(name)})
    # FunctionDecl — the definition
    if t == "FunctionDecl" and node.name == name and getattr(node, 'line', 0) > 0:
        results.append({"line": node.line - 1, "col": node.col,
                        "end_col": node.col + len(name)})
    # Walk all children
    for attr in vars(node).values() if hasattr(node, '__dict__') else []:
        if hasattr(attr, '__dict__'):
            _collect_references(attr, name, results)
        elif isinstance(attr, list):
            for item in attr:
                if hasattr(item, '__dict__'):
                    _collect_references(item, name, results)


def get_references(source: str, line: int, col: int,
                   include_definition: bool = True) -> List[Dict]:
    """Return list of {line, col, end_col} for all references to symbol at cursor."""
    try:
        from parser import parse
        program = parse(source)
    except Exception:
        return []

    word = _word_at(source, line, col)
    if not word:
        return []

    results = []
    _collect_references(program, word, results)
    return results


def get_rename_edits(source: str, line: int, col: int,
                     new_name: str) -> List[Dict]:
    """
    Return list of TextEdit dicts: {line, start_col, end_col, new_text}
    for renaming all occurrences of the symbol at cursor to new_name.
    """
    refs = get_references(source, line, col, include_definition=True)
    return [
        {
            "line":      r["line"],
            "start_col": r["col"],
            "end_col":   r["end_col"],
            "new_text":  new_name,
        }
        for r in refs
    ]


def get_document_symbols(source: str) -> List[Dict]:
    """
    Return all top-level symbol definitions:
    [{name, kind, line, col, detail}, ...]
    """
    try:
        from parser   import parse
        from analyzer import analyze
        program = parse(source)
        symbols = analyze(program, source)
    except Exception:
        return []

    result = []
    for name, sym in symbols.items():
        if sym.line <= 0:
            continue   # built-ins
        result.append({
            "name":   name,
            "kind":   sym.kind,     # 'fn', 'var', 'struct', 'const', etc.
            "line":   sym.line - 1,
            "col":    sym.col,
            "detail": str(sym.type_) if sym.type_ else "",
        })
    return sorted(result, key=lambda x: x["line"])
