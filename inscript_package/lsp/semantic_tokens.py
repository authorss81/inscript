# lsp/semantic_tokens.py — Semantic token classification for richer highlighting
# v2.5.0
#
# Token types published to the client:
#   0=namespace, 1=type, 2=class, 3=enum, 4=interface,
#   5=struct, 6=typeParam, 7=param, 8=variable, 9=property,
#   10=enumMember, 11=event, 12=function, 13=method,
#   14=macro, 15=keyword, 16=modifier, 17=comment,
#   18=string, 19=number, 20=operator, 21=decorator

from __future__ import annotations
from typing import List
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TOKEN_TYPES = [
    "namespace", "type", "class", "enum", "interface",
    "struct", "typeParam", "parameter", "variable", "property",
    "enumMember", "event", "function", "method",
    "macro", "keyword", "modifier", "comment",
    "string", "number", "operator", "decorator",
]

TOKEN_MODIFIERS = ["declaration", "definition", "readonly",
                   "static", "deprecated", "abstract",
                   "async", "modification", "documentation", "defaultLibrary"]

_TT_FUNCTION   = TOKEN_TYPES.index("function")
_TT_METHOD     = TOKEN_TYPES.index("method")
_TT_STRUCT     = TOKEN_TYPES.index("struct")
_TT_VARIABLE   = TOKEN_TYPES.index("variable")
_TT_PARAMETER  = TOKEN_TYPES.index("parameter")
_TT_KEYWORD    = TOKEN_TYPES.index("keyword")
_TT_STRING     = TOKEN_TYPES.index("string")
_TT_NUMBER     = TOKEN_TYPES.index("number")
_TT_PROPERTY   = TOKEN_TYPES.index("property")

_MOD_DECL      = 1 << TOKEN_MODIFIERS.index("declaration")
_MOD_READONLY  = 1 << TOKEN_MODIFIERS.index("readonly")
_MOD_ASYNC     = 1 << TOKEN_MODIFIERS.index("async")


def _classify_node(node, symbols: dict, tokens: list):
    """Walk AST and emit semantic tokens."""
    if node is None:
        return
    t = type(node).__name__

    if t == "FunctionDecl":
        if node.name and node.line > 0:
            mods = _MOD_DECL | (_MOD_ASYNC if getattr(node, 'is_async', False) else 0)
            tokens.append((node.line - 1, node.col, len(node.name),
                           _TT_FUNCTION, mods))
        # Walk params
        for p in (node.params or []):
            if hasattr(p, 'name') and p.name and getattr(p, 'line', 0) > 0:
                tokens.append((p.line - 1, p.col, len(p.name),
                               _TT_PARAMETER, _MOD_DECL))

    elif t == "StructDecl":
        if node.name and node.line > 0:
            tokens.append((node.line - 1, node.col, len(node.name),
                           _TT_STRUCT, _MOD_DECL))

    elif t in ("VarDecl", "ConstDecl"):
        if node.name and getattr(node, 'line', 0) > 0:
            mods = _MOD_DECL | (_MOD_READONLY if t == "ConstDecl" else 0)
            tokens.append((node.line - 1, node.col, len(node.name),
                           _TT_VARIABLE, mods))

    elif t == "IdentExpr":
        sym = symbols.get(node.name)
        if sym and node.line > 0:
            if sym.kind == "fn":
                tokens.append((node.line - 1, node.col, len(node.name),
                               _TT_FUNCTION, 0))
            elif sym.kind == "struct":
                tokens.append((node.line - 1, node.col, len(node.name),
                               _TT_STRUCT, 0))
            elif sym.kind in ("var", "let"):
                tokens.append((node.line - 1, node.col, len(node.name),
                               _TT_VARIABLE, 0))

    elif t == "GetAttrExpr":
        if node.line > 0:
            tokens.append((node.line - 1,
                           # col of the attribute (after the dot)
                           node.col,
                           len(node.attr),
                           _TT_PROPERTY, 0))

    # Recurse into all children
    for attr in vars(node).values() if hasattr(node, '__dict__') else []:
        if hasattr(attr, '__dict__') and hasattr(attr, 'line'):
            _classify_node(attr, symbols, tokens)
        elif isinstance(attr, list):
            for item in attr:
                if hasattr(item, '__dict__') and hasattr(item, 'line'):
                    _classify_node(item, symbols, tokens)


def get_semantic_tokens(source: str) -> List[int]:
    """
    Return the flat integer array for textDocument/semanticTokens/full.
    Format: [deltaLine, deltaStartChar, length, tokenType, tokenModifiers, ...]
    """
    try:
        from parser   import parse
        from analyzer import analyze
        program = parse(source)
        symbols = analyze(program, source)
    except Exception:
        return []

    raw_tokens = []
    _classify_node(program, symbols, raw_tokens)

    # Sort by line then col
    raw_tokens.sort(key=lambda t: (t[0], t[1]))

    # Encode as delta values
    encoded = []
    prev_line = 0
    prev_col  = 0
    for (line, col, length, tok_type, tok_mods) in raw_tokens:
        if length <= 0:
            continue
        delta_line = line - prev_line
        delta_col  = col - prev_col if delta_line == 0 else col
        encoded += [delta_line, delta_col, length, tok_type, tok_mods]
        prev_line = line
        prev_col  = col

    return encoded
