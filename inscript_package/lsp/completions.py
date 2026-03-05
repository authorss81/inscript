"""Completion items for InScript LSP."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Built-in functions and keywords
BUILTIN_FUNCTIONS = [
    "print","len","string","int","float","bool","typeof","range",
    "push","pop","contains","sort","reverse","map","filter","reduce",
    "zip","enumerate","flatten","unique","chunk","take","skip",
    "sum","min","max","abs","sqrt","floor","ceil","round",
    "split","join","trim","upper","lower","replace","starts_with","ends_with",
    "substring","char_code","from_code","parse_int","parse_float",
    "has_key","keys","values","entries","delete","merge",
    "is_nil","is_int","is_float","is_str","is_bool","is_array","is_dict",
    "Ok","Err","thread","chan_send","chan_recv","sleep","implements","fields_of",
]

KEYWORDS = [
    "let","const","fn","struct","enum","interface","mixin","impl","extends",
    "implements","return","if","else","for","while","in","break","continue",
    "match","case","import","from","export","async","await","yield","throw",
    "try","catch","abstract","select","true","false","nil","self",
]

SNIPPETS = [
    {"label": "fn", "insert": "fn ${1:name}(${2:params}) -> ${3:type} {\n\t$0\n}", "detail": "Function declaration"},
    {"label": "struct", "insert": "struct ${1:Name} {\n\t${2:field}: ${3:type}\n}", "detail": "Struct declaration"},
    {"label": "enum", "insert": "enum ${1:Name} {\n\t${2:Variant1}\n\t${3:Variant2}\n}", "detail": "Enum declaration"},
    {"label": "match", "insert": "match ${1:value} {\n\tcase ${2:pattern} { $0 }\n\tcase _ { }\n}", "detail": "Pattern match"},
    {"label": "for", "insert": "for ${1:i} in ${2:0..10} {\n\t$0\n}", "detail": "For range loop"},
    {"label": "async fn", "insert": "async fn ${1:name}(${2:params}) -> Result {\n\t$0\n}", "detail": "Async function"},
    {"label": "if", "insert": "if ${1:cond} {\n\t$0\n}", "detail": "If statement"},
    {"label": "while", "insert": "while ${1:cond} {\n\t$0\n}", "detail": "While loop"},
    {"label": "try", "insert": "try {\n\t$0\n} catch e {\n\t\n}", "detail": "Try/catch"},
    {"label": "select", "insert": "select {\n\tcase ${1:v} = ${2:ch}.recv() { $0 }\n\tcase timeout(${3:1.0}) { }\n}", "detail": "Select (multi-channel)"},
]

STDLIB_MODULES = [
    "math","string","array","io","json","random","time","color","tween",
    "grid","events","debug","http","path","regex","csv","uuid","crypto",
]

def get_completions(source: str, line: int, col: int) -> list:
    """Return completion items at the given position."""
    items = []

    # Extract variable names from source (simple regex scan)
    import re
    let_names = re.findall(r'\blet\s+(\w+)', source)
    fn_names  = re.findall(r'\bfn\s+(\w+)', source)
    const_names = re.findall(r'\bconst\s+(\w+)', source)

    # Get the word being typed
    lines = source.split('\n')
    cur_line = lines[line] if line < len(lines) else ''
    prefix = ''
    for i in range(col - 1, -1, -1):
        if i < len(cur_line) and (cur_line[i].isalnum() or cur_line[i] == '_'):
            prefix = cur_line[i] + prefix
        else:
            break

    all_words = (
        list(set(let_names + fn_names + const_names)) +
        BUILTIN_FUNCTIONS + KEYWORDS
    )
    for word in sorted(set(all_words)):
        if word.startswith(prefix) or not prefix:
            kind = "keyword" if word in KEYWORDS else "function"
            items.append({"label": word, "kind": kind, "detail": ""})

    # Add snippets
    for s in SNIPPETS:
        if s["label"].startswith(prefix) or not prefix:
            items.append({"label": s["label"], "kind": "snippet",
                          "detail": s["detail"], "insert": s["insert"]})

    return items
