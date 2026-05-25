# lsp/hover.py — Hover documentation with type information
# v2.5.0: Now includes inferred types from the analyzer

from __future__ import annotations
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_KEYWORD_DOCS = {
    "fn":      "**fn** — declare a function\n```\nfn name(param: Type) -> RetType { }\n```",
    "let":     "**let** — declare a mutable variable\n```\nlet x: int = 0\n```",
    "const":   "**const** — declare an immutable constant\n```\nconst PI: float = 3.14159\n```",
    "if":      "**if** — conditional branch\n```\nif condition { } else { }\n```",
    "else":    "**else** — alternative branch for if",
    "while":   "**while** — loop while condition is true\n```\nwhile i < 10 { i = i + 1 }\n```",
    "for":     "**for** — iterate over a range or collection\n```\nfor x in 0..10 { }\n```",
    "return":  "**return** — return a value from a function",
    "struct":  "**struct** — define a data type\n```\nstruct Name { field: Type = default }\n```",
    "match":   "**match** — pattern match on a value\n```\nmatch x { case 1 { } case _ { } }\n```",
    "impl":    "**impl** — implement operators or traits for a struct",
    "import":  "**import** — import a module\n```\nimport \"math\" as math\n```",
    "async":   "**async** — declare an asynchronous function",
    "await":   "**await** — wait for an async function result",
    "spawn":   "**spawn** — run expression in background thread",
    "channel": "**channel\\<T\\>(capacity)** — create a typed message queue",
    "nil":     "**nil** — the null/absent value",
    "true":    "**true** — boolean true",
    "false":   "**false** — boolean false",
}

_BUILTIN_DOCS = {
    "print":   "```\nprint(value: any) -> void\n```\nPrint a value to stdout.",
    "len":     "```\nlen(x: string | []) -> int\n```\nReturn length of string or array.",
    "str":     "```\nstr(x: any) -> string\n```\nConvert value to string.",
    "int":     "```\nint(x: any) -> int\n```\nConvert value to integer.",
    "float":   "```\nfloat(x: any) -> float\n```\nConvert value to float.",
    "range":   "```\nrange(start: int, end: int) -> Range\n```\nCreate a numeric range.",
    "type":    "```\ntype(x: any) -> string\n```\nReturn type name as string.",
    "assert":  "```\nassert(cond: bool, msg: string = \"Assertion failed\") -> void\n```",
    "map":     "```\nmap(arr: [], fn: fn(any)->any) -> []\n```\nTransform each element of an array.",
    "filter":  "```\nfilter(arr: [], pred: fn(any)->bool) -> []\n```\nKeep elements where pred returns true.",
    "reduce":  "```\nreduce(arr: [], fn: fn(any,any)->any, init: any) -> any\n```\nFold array to a single value.",
}


def _word_at(source: str, line: int, col: int) -> str:
    lines = source.splitlines()
    if line >= len(lines):
        return ""
    row = lines[line]
    start = col
    while start > 0 and (row[start-1].isalnum() or row[start-1] == '_'):
        start -= 1
    end = col
    while end < len(row) and (row[end].isalnum() or row[end] == '_'):
        end += 1
    return row[start:end]


def get_hover(source: str, line: int, col: int):
    """Return hover info dict {contents} or None."""
    word = _word_at(source, line, col)
    if not word:
        return None

    # Keyword docs
    if word in _KEYWORD_DOCS:
        return {"contents": _KEYWORD_DOCS[word]}

    # Built-in function docs
    if word in _BUILTIN_DOCS:
        return {"contents": _BUILTIN_DOCS[word]}

    # v2.5.0: Use analyzer for user-defined symbols with type info
    try:
        from parser   import parse
        from analyzer import analyze
        program = parse(source)
        symbols = analyze(program, source)
        sym = symbols.get(word)
        if sym:
            return _format_symbol_hover(sym)
    except Exception:
        pass

    return None


def _format_symbol_hover(sym) -> dict:
    """Format a Symbol into markdown hover content."""
    kind  = sym.kind
    name  = sym.name
    type_ = str(sym.type_) if sym.type_ else "unknown"
    lines = []

    if kind == "fn" and sym.fn_node is not None:
        node = sym.fn_node
        params = ", ".join(
            f"{p.name}: {p.type_ann.name if p.type_ann else 'any'}"
            for p in (node.params or [])
            if hasattr(p, 'name')
        )
        ret = node.return_type.name if (hasattr(node, 'return_type') and node.return_type) else type_
        async_kw = "async " if getattr(node, 'is_async', False) else ""
        lines.append(f"```inscript\n{async_kw}fn {name}({params}) -> {ret}\n```")
        if sym.line > 0:
            lines.append(f"*Defined at line {sym.line}*")

    elif kind == "struct" and sym.struct_node is not None:
        node = sym.struct_node
        fields = [
            f"    {f.name}: {f.type_ann.name if f.type_ann else 'any'}"
            for f in (getattr(node, 'fields', []) or [])
        ]
        body = "\n".join(fields[:8])   # cap at 8 fields in hover
        if len(getattr(node, 'fields', [])) > 8:
            body += "\n    ..."
        lines.append(f"```inscript\nstruct {name} {{\n{body}\n}}\n```")

    elif kind in ("var", "let", "const"):
        kw = "const" if sym.is_const else "let"
        lines.append(f"```inscript\n{kw} {name}: {type_}\n```")
        if sym.line > 0:
            lines.append(f"*Defined at line {sym.line}*")

    else:
        lines.append(f"```inscript\n{name}: {type_}\n```")

    return {"contents": "\n\n".join(lines)}
