"""
lsp/hover.py — InScript LSP hover provider
v2.1.0: user-defined symbols (variables, functions, structs) + built-in docs.
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HOVER_DOCS = {
    "print":       "print(...values) — Print values to stdout",
    "string":      "string(v) -> string — Convert any value to a string",
    "int":         "int(v) -> int — Convert value to integer",
    "float":       "float(v) -> float — Convert value to float",
    "bool":        "bool(v) -> bool — Convert value to boolean",
    "typeof":      "typeof(v) -> string — Return the type name of v as a string",
    "range":       "range(stop) | range(start, stop, step?) -> Range — Integer range",
    "len":         "len(arr_or_str) -> int — Length of array or string",
    "push":        "arr.push(item) — Append item to array (mutates)",
    "pop":         "arr.pop() — Remove and return last item",
    "map":         "arr.map(fn(x) -> T) -> Array<T> — Transform each element",
    "filter":      "arr.filter(fn(x) -> bool) -> Array<T> — Keep matching elements",
    "reduce":      "arr.reduce(fn(acc, x) -> T, init) -> T — Fold array",
    "sort":        "arr.sort() | arr.sort(key_fn) — Sort array",
    "contains":    "arr.contains(v) -> bool — True if v is in array",
    "find":        "arr.find(fn(x)->bool) -> T|nil — First matching element",
    "join":        "arr.join(sep) -> string — Join array with separator",
    "split":       "str.split(sep) -> Array<string> — Split string on separator",
    "trim":        "str.trim() -> string — Remove leading/trailing whitespace",
    "upper":       "str.upper() -> string — Convert to uppercase",
    "lower":       "str.lower() -> string — Convert to lowercase",
    "replace":     "str.replace(from, to) -> string — Replace occurrences",
    "starts_with": "str.starts_with(prefix) -> bool",
    "ends_with":   "str.ends_with(suffix) -> bool",
    "substr":      "str.substr(start, end?) -> string — Substring",
    "sqrt":        "sqrt(n) -> float — Square root",
    "abs":         "abs(n) -> number — Absolute value",
    "floor":       "floor(n) -> int — Round down to nearest integer",
    "ceil":        "ceil(n) -> int — Round up to nearest integer",
    "round":       "round(n, decimals?) -> float — Round to N decimal places",
    "min":         "min(a, b) | min(arr) — Minimum value",
    "max":         "max(a, b) | max(arr) — Maximum value",
    "sum":         "sum(arr) -> number — Sum of all elements",
    "keys":        "keys(dict) -> Array<string> — All keys in dict",
    "values":      "values(dict) -> Array<any> — All values in dict",
    "entries":     "entries(dict) -> Array<[key, value]> — Key-value pairs",
    "has_key":     "has_key(dict, key) -> bool — True if key exists",
    "merge":       "merge(d1, d2, ...) -> dict — Merge multiple dicts",
    "delete":      "delete(dict, key) — Remove key from dict",
    "is_nil":      "is_nil(v) -> bool — True if v is nil",
    "is_int":      "is_int(v) -> bool — True if v is an integer",
    "is_float":    "is_float(v) -> bool — True if v is a float",
    "is_str":      "is_str(v) -> bool — True if v is a string",
    "is_array":    "is_array(v) -> bool — True if v is an array",
    "is_dict":     "is_dict(v) -> bool — True if v is a dict",
    "parse_int":   "parse_int(s) -> int — Parse integer from string",
    "parse_float": "parse_float(s) -> float — Parse float from string",
    "Ok":          "Ok(value) — Wrap a success value in Result<T>",
    "Err":         "Err(message) — Wrap an error in Result<T>",
    "sleep":       "await sleep(seconds) — Pause execution (async)",
    "fields_of":   "fields_of(instance) -> Array<string> — Field names of a struct",
    "implements":  "implements(obj, 'Interface') -> bool — Runtime interface check",
    "true":        "true — Boolean literal",
    "false":       "false — Boolean literal",
    "nil":         "nil — Null / absent value (type: nil)",
    "self":        "self — Reference to the current struct instance (inside methods)",
    "await":       "await expr — Drive an async coroutine to completion",
    "async":       "async fn name() -> T — Declare an asynchronous function",
}


def _word_at(source: str, line: int, col: int) -> str:
    lines = source.split('\n')
    if line >= len(lines):
        return ""
    cur = lines[line]
    start = col
    while start > 0 and (cur[start-1].isalnum() or cur[start-1] == '_'):
        start -= 1
    end = col
    while end < len(cur) and (cur[end].isalnum() or cur[end] == '_'):
        end += 1
    return cur[start:end]


def _lookup_user_symbol(source: str, word: str) -> str | None:
    """Find user-defined fn / let / struct / enum in source and build a doc string."""
    # Function: fn name(params) -> rettype { ... }
    m = re.search(
        rf'\b(async\s+)?fn\s+{re.escape(word)}\s*\(([^)]*)\)(\s*->\s*([^\{{]+))?',
        source
    )
    if m:
        async_prefix = "async " if m.group(1) else ""
        params = m.group(2).strip()
        ret    = (m.group(4) or "nil").strip()
        return f"{async_prefix}fn **{word}**({params}) -> {ret}"

    # Variable: let name: Type = ...  or  let name = ...
    m = re.search(rf'\blet\s+{re.escape(word)}\s*:\s*([^\s=]+)', source)
    if m:
        return f"let **{word}**: {m.group(1)}"
    m = re.search(rf'\blet\s+{re.escape(word)}\s*=\s*([^\n{{]+)', source)
    if m:
        val_preview = m.group(1).strip()[:40]
        return f"let **{word}** = {val_preview}"

    # Const
    m = re.search(rf'\bconst\s+{re.escape(word)}\s*:\s*([^\s=]+)', source)
    if m:
        return f"const **{word}**: {m.group(1)}"

    # Struct
    m = re.search(rf'\bstruct\s+{re.escape(word)}\b', source)
    if m:
        # Collect field names
        struct_m = re.search(
            rf'\bstruct\s+{re.escape(word)}\s*\{{([^}}]{{0,400}})}}', source, re.DOTALL
        )
        if struct_m:
            fields = re.findall(r'\b(\w+)\s*:\s*(\w[\w<>,\s]*?)(?:\s*=|\s*\n|\s*;|\s*\})', struct_m.group(1))
            field_str = ", ".join(f"{f}: {t.strip()}" for f, t in fields[:6])
            return f"struct **{word}** {{ {field_str} }}"
        return f"struct **{word}**"

    # Enum
    m = re.search(rf'\benum\s+{re.escape(word)}\b', source)
    if m:
        enum_m = re.search(rf'\benum\s+{re.escape(word)}\s*\{{([^}}]*)}}', source)
        if enum_m:
            variants = [v.strip() for v in re.findall(r'\b([A-Z]\w*)\b', enum_m.group(1))]
            return f"enum **{word}** {{ {', '.join(variants[:8])} }}"
        return f"enum **{word}**"

    # Type alias
    m = re.search(rf'\btype\s+{re.escape(word)}\s*=\s*([^\n]+)', source)
    if m:
        return f"type **{word}** = {m.group(1).strip()}"

    return None


def get_hover(source: str, line: int, col: int) -> dict | None:
    """Return hover info for the symbol at (line, col)."""
    word = _word_at(source, line, col)
    if not word:
        return None

    # 1. Check built-in docs
    if word in HOVER_DOCS:
        return {"contents": HOVER_DOCS[word], "word": word}

    # 2. Check user-defined symbols in source
    user_doc = _lookup_user_symbol(source, word)
    if user_doc:
        return {"contents": user_doc, "word": word}

    return None
