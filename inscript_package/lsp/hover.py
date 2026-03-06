"""Hover documentation for InScript built-ins."""

HOVER_DOCS = {
    "print":       "print(value) — Print a value to stdout",
    "len":         "len(arr) -> int — Length of an array or string",
    "string":      "string(v) -> str — Convert any value to a string",
    "int":         "int(v) -> int — Convert value to integer",
    "float":       "float(v) -> float — Convert value to float",
    "bool":        "bool(v) -> bool — Convert value to boolean",
    "typeof":      "typeof(v) -> str — Return the type name of v",
    "push":        "push(arr, item) — Append item to array (mutates)",
    "pop":         "pop(arr) — Remove and return last item",
    "map":         "map(arr, fn) -> arr — Transform each element",
    "filter":      "filter(arr, fn) -> arr — Keep elements where fn returns true",
    "reduce":      "reduce(arr, fn, init) — Fold array into single value",
    "sort":        "sort(arr) or sort(arr, key_fn) — Sort array in place",
    "contains":    "contains(arr, v) -> bool — True if v is in arr",
    "split":       "split(str, sep) -> arr — Split string on separator",
    "join":        "join(arr, sep) -> str — Join array with separator",
    "trim":        "trim(str) -> str — Remove leading/trailing whitespace",
    "upper":       "upper(str) -> str — Convert to uppercase",
    "lower":       "lower(str) -> str — Convert to lowercase",
    "replace":     "replace(str, from, to) -> str — Replace occurrences",
    "sqrt":        "sqrt(n) -> float — Square root",
    "abs":         "abs(n) — Absolute value",
    "floor":       "floor(n) -> int — Round down",
    "ceil":        "ceil(n) -> int — Round up",
    "round":       "round(n, decimals?) -> float — Round to N decimal places",
    "min":         "min(a, b) or min(arr) — Minimum value",
    "max":         "max(a, b) or max(arr) — Maximum value",
    "sum":         "sum(arr) — Sum of all elements",
    "zip":         "zip(a, b) -> arr — Pair up elements from two arrays",
    "enumerate":   "enumerate(arr) -> arr — [[index, value], ...]",
    "flatten":     "flatten(arr) -> arr — Flatten one level of nesting",
    "unique":      "unique(arr) -> arr — Remove duplicates",
    "has_key":     "has_key(dict, key) -> bool — True if key exists in dict",
    "keys":        "keys(dict) -> arr — All keys",
    "values":      "values(dict) -> arr — All values",
    "entries":     "entries(dict) -> arr — [[key, value], ...]",
    "delete":      "delete(dict, key) — Remove key from dict",
    "merge":       "merge(d1, d2, ...) -> dict — Merge multiple dicts",
    "is_nil":      "is_nil(v) -> bool — True if v is nil",
    "is_int":      "is_int(v) -> bool — True if v is an integer",
    "is_float":    "is_float(v) -> bool — True if v is a float",
    "is_str":      "is_str(v) -> bool — True if v is a string",
    "is_bool":     "is_bool(v) -> bool — True if v is a boolean",
    "is_array":    "is_array(v) -> bool — True if v is an array",
    "is_dict":     "is_dict(v) -> bool — True if v is a dict",
    "Ok":          "Ok(value) — Wrap a success value in Result",
    "Err":         "Err(message) — Wrap an error in Result",
    "thread":      "thread(fn) — Spawn fn in a background thread",
    "chan_send":   "chan_send(ch, value) — Send value to channel",
    "chan_recv":   "chan_recv(ch) — Receive value from channel (blocks)",
    "sleep":       "sleep(seconds) — Pause execution",
    "implements":  "implements(obj, 'InterfaceName') -> bool",
    "fields_of":   "fields_of(struct_instance) -> arr — Field names",
    "parse_int":   "parse_int(str) -> int — Parse integer from string",
    "parse_float": "parse_float(str) -> float — Parse float from string",
}

def get_hover(source: str, line: int, col: int) -> dict | None:
    """Return hover documentation for the word at (line, col)."""
    lines = source.split('\n')
    if line >= len(lines):
        return None
    cur_line = lines[line]

    # Find word boundaries
    start = col
    while start > 0 and (cur_line[start-1].isalnum() or cur_line[start-1] == '_'):
        start -= 1
    end = col
    while end < len(cur_line) and (cur_line[end].isalnum() or cur_line[end] == '_'):
        end += 1

    word = cur_line[start:end]
    if not word:
        return None

    if word in HOVER_DOCS:
        return {"contents": HOVER_DOCS[word], "word": word}

    return None
