"""
lsp/completions.py — InScript LSP completion provider
v2.1.0: uses analyzer symbol table + dot-completions for arrays/strings/structs.
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KEYWORDS = [
    "let","const","fn","struct","enum","interface","return",
    "if","else","for","while","in","break","continue",
    "match","case","import","async","await","true","false","nil","self",
    "type","implements","extends","step",
]

BUILTIN_FUNCTIONS = [
    "print","string","int","float","bool","typeof","range",
    "sqrt","abs","floor","ceil","round","min","max","sum",
    "parse_int","parse_float","is_nil","is_int","is_float",
    "is_str","is_bool","is_array","is_dict",
    "has_key","keys","values","entries","delete","merge",
    "Ok","Err","sleep","implements","fields_of","len",
]

ARRAY_METHODS = [
    "len","push","pop","shift","unshift","map","filter","reduce",
    "find","find_index","contains","index_of","reverse","sort",
    "slice","concat","flatten","unique","zip","enumerate",
    "join","take","skip","chunk","sum","min","max","first","last",
    "any","all","count",
]

STRING_METHODS = [
    "len","upper","lower","trim","lstrip","rstrip","split","replace",
    "starts_with","ends_with","contains","index_of","substr","repeat",
    "char_at","char_code","reverse","pad_left","pad_right",
]

STDLIB_MODULES = [
    "http","file","timer","math","string","array","json","random",
    "io","path","color","tween","events","debug",
]

SNIPPETS = [
    {"label":"fn",       "insert":"fn ${1:name}(${2:params}) -> ${3:type} {\n\t$0\n}",      "detail":"Function declaration"},
    {"label":"struct",   "insert":"struct ${1:Name} {\n\t${2:field}: ${3:type} = ${4:val}\n}","detail":"Struct declaration"},
    {"label":"enum",     "insert":"enum ${1:Name} {\n\t${2:Variant1},\n\t${3:Variant2}\n}",  "detail":"Enum declaration"},
    {"label":"match",    "insert":"match ${1:value} {\n\tcase ${2:pattern} { $0 }\n\tcase _ { }\n}","detail":"Pattern match"},
    {"label":"for",      "insert":"for ${1:i} in ${2:0..10} {\n\t$0\n}",                    "detail":"For range loop"},
    {"label":"for step", "insert":"for ${1:i} in ${2:0}..${3:10} step ${4:2} {\n\t$0\n}",  "detail":"For loop with step"},
    {"label":"async fn", "insert":"async fn ${1:name}() -> ${2:string} {\n\t$0\n}",         "detail":"Async function"},
    {"label":"if",       "insert":"if ${1:cond} {\n\t$0\n}",                                "detail":"If statement"},
    {"label":"if else",  "insert":"if ${1:cond} {\n\t$0\n} else {\n\t\n}",                  "detail":"If/else"},
    {"label":"while",    "insert":"while ${1:cond} {\n\t$0\n}",                             "detail":"While loop"},
    {"label":"try",      "insert":"try {\n\t$0\n} catch e {\n\t\n}",                        "detail":"Try/catch"},
    {"label":"import",   "insert":"import \"${1:module}\" as ${2:alias}",                   "detail":"Import module"},
    {"label":"let",      "insert":"let ${1:name} = $0",                                     "detail":"Variable declaration"},
    {"label":"interp",   "insert":"\\$\"${1:text} {${2:expr}}\"",                           "detail":"String interpolation"},
]


def _extract_symbols(source: str) -> dict:
    """Extract let/fn/struct/enum names from source via regex for fast completion."""
    syms = {"variables": [], "functions": [], "structs": [], "enums": []}
    syms["variables"] = re.findall(r'\blet\s+(\w+)', source)
    syms["variables"] += re.findall(r'\bconst\s+(\w+)', source)
    syms["functions"]  = re.findall(r'\bfn\s+(\w+)', source)
    syms["structs"]    = re.findall(r'\bstruct\s+(\w+)', source)
    syms["enums"]      = re.findall(r'\benum\s+(\w+)', source)
    return syms


def _get_struct_fields(source: str, struct_name: str) -> list:
    """Extract field names from a struct definition."""
    pattern = rf'\bstruct\s+{re.escape(struct_name)}\s*\{{([^}}]*)\}}'
    m = re.search(pattern, source, re.DOTALL)
    if not m:
        return []
    body = m.group(1)
    fields = re.findall(r'\b(\w+)\s*:', body)
    methods = re.findall(r'\bfn\s+(\w+)\s*\(', body)
    return fields + methods


def _get_prefix_and_dot(source: str, line: int, col: int):
    """Return (prefix, dot_object) where dot_object is the word before '.'."""
    lines = source.split('\n')
    cur = lines[line] if line < len(lines) else ''
    # Find word being typed
    prefix_end = col
    prefix_start = col
    while prefix_start > 0 and (cur[prefix_start-1].isalnum() or cur[prefix_start-1] == '_'):
        prefix_start -= 1
    prefix = cur[prefix_start:prefix_end]

    # Check if we're in dot-completion: word.| or word.|prefix
    dot_pos = prefix_start - 1
    if dot_pos >= 0 and cur[dot_pos] == '.':
        obj_end = dot_pos
        obj_start = dot_pos
        while obj_start > 0 and (cur[obj_start-1].isalnum() or cur[obj_start-1] == '_'):
            obj_start -= 1
        dot_object = cur[obj_start:obj_end]
        return prefix, dot_object
    return prefix, None


def get_completions(source: str, line: int, col: int) -> list:
    """Return completion items at (line, col)."""
    prefix, dot_object = _get_prefix_and_dot(source, line, col)
    items = []

    # ── Dot completion ─────────────────────────────────────────────────────
    if dot_object is not None:
        # Try to infer type from source
        # Check if dot_object is a stdlib module
        if dot_object in STDLIB_MODULES:
            if dot_object == "http":
                meths = ["get","post","get_async","post_async"]
            elif dot_object == "file":
                meths = ["read","write","read_async","write_async","exists","delete"]
            elif dot_object == "timer":
                meths = ["sleep","now","elapsed"]
            elif dot_object == "math":
                meths = ["sqrt","abs","floor","ceil","round","sin","cos","tan","pow","log"]
            else:
                meths = []
            for m in meths:
                if not prefix or m.startswith(prefix):
                    items.append({"label": m, "kind": "function", "detail": f"{dot_object}.{m}()"})
            return items

        # Infer type: look for `let dot_object: Type` or `let dot_object = Struct{`
        type_hint = None
        m = re.search(rf'\blet\s+{re.escape(dot_object)}\s*:\s*(\w+)', source)
        if m:
            type_hint = m.group(1)
        else:
            m = re.search(rf'\blet\s+{re.escape(dot_object)}\s*=\s*(\w+)\s*\{{', source)
            if m:
                type_hint = m.group(1)

        if type_hint in ("string", "str"):
            candidates = STRING_METHODS
        elif type_hint in ("Array", "array") or type_hint and type_hint.startswith("Array"):
            candidates = ARRAY_METHODS
        else:
            # Try struct fields
            struct_fields = _get_struct_fields(source, dot_object.capitalize())
            if not struct_fields and type_hint:
                struct_fields = _get_struct_fields(source, type_hint)
            if struct_fields:
                for f in struct_fields:
                    if not prefix or f.startswith(prefix):
                        items.append({"label": f, "kind": "variable", "detail": f"{dot_object}.{f}"})
                return items
            # Default: array and string methods both
            candidates = list(set(ARRAY_METHODS + STRING_METHODS))

        for m in sorted(candidates):
            if not prefix or m.startswith(prefix):
                items.append({"label": m, "kind": "function", "detail": f".{m}()"})
        return items

    # ── Normal completion ──────────────────────────────────────────────────
    syms = _extract_symbols(source)

    all_words = sorted(set(
        syms["variables"] + syms["functions"] + syms["structs"] + syms["enums"] +
        BUILTIN_FUNCTIONS + KEYWORDS
    ))
    for word in all_words:
        if not prefix or word.startswith(prefix):
            if word in KEYWORDS:
                kind = "keyword"
            elif word in syms["functions"] or word in BUILTIN_FUNCTIONS:
                kind = "function"
            elif word[0].isupper():
                kind = "variable"
            else:
                kind = "variable"
            items.append({"label": word, "kind": kind, "detail": ""})

    # Snippets
    for s in SNIPPETS:
        if not prefix or s["label"].startswith(prefix) or s["label"].replace(" ","").startswith(prefix):
            items.append({"label": s["label"], "kind": "snippet",
                          "detail": s["detail"], "insert": s["insert"]})

    return items
