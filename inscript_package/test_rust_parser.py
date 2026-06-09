"""Test the Rust parser against real InScript files."""
import sys, os, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "target", "release"))

from lexer import Lexer, TT
from inscript_parser import parse_tokens as rust_parse

_TOKEN_MAP = {
    "LET": "Let", "CONST": "Const", "FN": "Fn", "IF": "If", "ELSE": "Else",
    "WHILE": "While", "FOR": "For", "IN": "In",
    "BREAK": "Break", "CONTINUE": "Continue",
    "RETURN": "Return", "THROW": "Throw",
    "TRY": "Try", "CATCH": "Catch", "FINALLY": "Finally",
    "ASYNC": "Async", "AWAIT": "Await", "YIELD": "Yield",
    "TRUE": "True", "FALSE": "False", "NIL": "Nil",
    "INT": "Int", "FLOAT": "Float", "STRING": "String", "IDENT": "Ident",
    "PLUS": "Plus", "MINUS": "Minus", "STAR": "Star", "SLASH": "Slash",
    "PERCENT": "Percent", "POWER": "Power", "ASSIGN": "Assign",
    "EQ": "Eq", "NEQ": "Neq", "LT": "Lt", "LTE": "Lte", "GT": "Gt", "GTE": "Gte",
    "AND": "And", "OR": "Or", "NOT": "Not", "QUESTION": "Question",
    "BAND": "BitwiseAnd", "BOR": "BitwiseOr", "BXOR": "BitwiseXor",
    "BNOT": "BitwiseNot", "LSHIFT": "LeftShift", "RSHIFT": "RightShift",
    "LPAREN": "LeftParen", "RPAREN": "RightParen",
    "LBRACE": "LeftBrace", "RBRACE": "RightBrace",
    "LBRACKET": "LeftBracket", "RBRACKET": "RightBracket",
    "COMMA": "Comma", "DOT": "Dot", "SEMICOLON": "Semicolon",
    "COLON": "Colon", "ARROW": "Arrow", "EOF": "Eof",
    "DEFAULT": "Default", "STRUCT": "Struct", "ENUM": "Enum",
    "MATCH": "Switch", "CASE": "Case", "CLASS": "Class", "SCENE": "Class",
    "VOID_TYPE": "Ident", "INT_TYPE": "Ident", "FLOAT_TYPE": "Ident",
    "STRING_TYPE": "Ident", "BOOL_TYPE": "Ident",
    "IMPORT": "Ident", "FROM": "Ident", "AS": "Ident",
    "SELF": "Ident", "SUPER": "Ident", "EXPORT": "Ident",
    "SPAWN": "Ident", "SELECT": "Ident", "THEN": "Ident",
    "ABSTRACT": "Ident", "INTERFACE": "Ident", "IMPL": "Ident", "PUB": "Ident",
    "PLUS_EQ": "Assign", "MINUS_EQ": "Assign", "STAR_EQ": "Assign", "SLASH_EQ": "Assign",
    "PERCENT_EQ": "Assign", "POWER_EQ": "Assign",
    "SLASH_SLASH": "Slash",
    "PLUSPLUS": "Plus",
    "REPEAT": "Ident", "UNTIL": "Ident", "DEFER": "Ident",
    "IS": "Eq",
}

fpath = sys.argv[1] if len(sys.argv) > 1 else "examples/asteroid_blaster.ins"
with open(fpath, encoding="utf-8") as f:
    source = f.read()
fname = os.path.basename(fpath)

tokens = Lexer(source).tokenize()
tok_list = []
for t in tokens:
    type_str = _TOKEN_MAP.get(t.type.name, "Ident")
    tok_list.append({
        "token_type": type_str,
        "value": str(t.value) if t.value is not None else "",
        "line": t.line,
        "column": t.col,
    })

# Debug: print tokens around line 11
print("Tokens at lines 10-12:")
for i, t in enumerate(tokens):
    if 10 <= t.line <= 12:
        mapped = _TOKEN_MAP.get(t.type.name, "?")
        print(f"  [{i}] line={t.line}:{t.col}  {t.type.name:15s} -> {mapped:15s}  val={t.value!r}")
print()

try:
    result = rust_parse(tok_list)
    print(f"\nPASS: {fpath}")
except Exception as e:
    print(f"\nFAIL: {e}")
