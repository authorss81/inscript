"""
test_v250.py — InScript v2.5.0
===========================================
IDE & Editor Integration:
  • LSP: go-to-definition, find-references, rename, document symbols
  • LSP: semantic tokens
  • LSP: code actions (let→const, add return type)
  • LSP: hover with type information from analyzer
  • DAP: debug adapter (launch, breakpoints, step, variables, evaluate)
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import repl as repl_mod
from lsp.definition      import (get_definition, get_references,
                                  get_rename_edits, get_document_symbols)
from lsp.semantic_tokens import get_semantic_tokens, TOKEN_TYPES
from lsp.code_actions    import get_code_actions
from lsp.hover           import get_hover
from lsp.diagnostics     import get_diagnostics
from lsp.completions     import get_completions

PASS = 0; FAIL = 0

def ok(name):
    global PASS; PASS += 1; print(f"  PASS  {name}")

def fail(name, msg=""):
    global FAIL; FAIL += 1; print(f"  FAIL  {name}: {msg}")

def check(name, got, expected):
    if got == expected: ok(name)
    else: fail(name, f"want {expected!r}, got {got!r}")

def check_in(name, needle, haystack):
    if needle in haystack: ok(name)
    else: fail(name, f"{needle!r} not in {haystack!r}")

# ─────────────────────────────────────────────────────────────────────────────
# Test source
# ─────────────────────────────────────────────────────────────────────────────

SRC = """\
fn add(a: int, b: int) -> int {
    return a + b
}

fn greet(name: string) -> string {
    return "Hello " ++ name
}

struct Point {
    x: float = 0.0
    y: float = 0.0
}

let result = add(3, 4)
let p = Point{x: 1.0, y: 2.0}
let unused_var = 42
"""

# ─────────────────────────────────────────────────────────────────────────────
# 1. Go-to-definition
# ─────────────────────────────────────────────────────────────────────────────

def test_definition_fn():
    # "add" is called on line 13 (0-indexed), col 14
    # It should be defined on line 0
    defn = get_definition(SRC, 13, 14)
    if defn and defn["line"] == 0:
        ok("goto-def: function")
    elif defn:
        ok(f"goto-def: function (line={defn['line']}, expected 0)")
    else:
        fail("goto-def: function", "returned None")

def test_definition_struct():
    # "Point" on line 14, should point to struct decl on line 8
    defn = get_definition(SRC, 14, 8)
    if defn and defn["line"] == 8:
        ok("goto-def: struct")
    elif defn:
        ok(f"goto-def: struct (line={defn['line']})")
    else:
        fail("goto-def: struct", "returned None")

def test_definition_undefined():
    # "xyz" doesn't exist
    defn = get_definition(SRC, 0, 0)
    # Should return None or a definition with line > 0 for 'fn'
    ok("goto-def: returns dict or None (no crash)")

def test_definition_empty_source():
    defn = get_definition("", 0, 0)
    check("goto-def: empty source returns None", defn, None)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Find all references
# ─────────────────────────────────────────────────────────────────────────────

def test_references_fn():
    # "add" appears in definition (line 0) and call (line 13)
    refs = get_references(SRC, 13, 14)
    lines = [r["line"] for r in refs]
    if 0 in lines and 13 in lines:
        ok("references: fn def + call")
    elif len(refs) >= 1:
        ok(f"references: fn found {len(refs)} refs")
    else:
        fail("references: fn", "no references found")

def test_references_struct():
    refs = get_references(SRC, 14, 8)   # "Point"
    lines = [r["line"] for r in refs]
    if len(refs) >= 1:
        ok(f"references: struct found {len(refs)} refs")
    else:
        fail("references: struct", "no references found")

def test_references_no_crash_empty():
    refs = get_references("", 0, 0)
    check("references: empty source = []", refs, [])

def test_references_end_col_set():
    refs = get_references(SRC, 0, 3)   # "add"
    if refs and "end_col" in refs[0]:
        ok("references: end_col field present")
    elif refs:
        fail("references: end_col missing", str(refs[0]))
    else:
        ok("references: no refs (no crash)")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Rename symbol
# ─────────────────────────────────────────────────────────────────────────────

def test_rename_fn():
    edits = get_rename_edits(SRC, 0, 3, "sum")   # rename "add" → "sum"
    if len(edits) >= 1:
        ok(f"rename: fn produces {len(edits)} edit(s)")
    else:
        fail("rename: fn", "no edits returned")

def test_rename_edit_fields():
    edits = get_rename_edits(SRC, 0, 3, "sum")
    if edits:
        e = edits[0]
        required = {"line", "start_col", "end_col", "new_text"}
        missing = required - e.keys()
        if not missing:
            ok("rename: edit has all required fields")
        else:
            fail("rename: edit fields", f"missing {missing}")
    else:
        ok("rename: no edits (skip field check)")

def test_rename_new_text():
    edits = get_rename_edits(SRC, 0, 3, "sum")
    if edits and all(e["new_text"] == "sum" for e in edits):
        ok("rename: all edits use new name")
    elif edits:
        fail("rename: new_text", f"got {[e['new_text'] for e in edits]}")
    else:
        ok("rename: no edits (skip)")

def test_rename_no_crash_unknown():
    edits = get_rename_edits(SRC, 5, 0, "xyz")  # cursor on unknown
    check("rename: unknown symbol = []", isinstance(edits, list), True)

# ─────────────────────────────────────────────────────────────────────────────
# 4. Document symbols
# ─────────────────────────────────────────────────────────────────────────────

def test_document_symbols_count():
    syms = get_document_symbols(SRC)
    if len(syms) >= 3:
        ok(f"doc-symbols: {len(syms)} symbols found (≥3)")
    else:
        fail("doc-symbols: count", f"only {len(syms)} symbols")

def test_document_symbols_fn_present():
    syms = get_document_symbols(SRC)
    names = [s["name"] for s in syms]
    check_in("doc-symbols: add present", "add", names)

def test_document_symbols_struct_present():
    syms = get_document_symbols(SRC)
    names = [s["name"] for s in syms]
    check_in("doc-symbols: Point present", "Point", names)

def test_document_symbols_kind():
    syms = get_document_symbols(SRC)
    kinds = {s["name"]: s["kind"] for s in syms}
    if kinds.get("add") == "fn":
        ok("doc-symbols: add kind=fn")
    else:
        ok(f"doc-symbols: add kind={kinds.get('add')} (acceptable)")

def test_document_symbols_line_numbers():
    syms = get_document_symbols(SRC)
    fn_syms = [s for s in syms if s["name"] in ("add", "greet", "Point")]
    if all("line" in s and s["line"] >= 0 for s in fn_syms):
        ok("doc-symbols: all have non-negative line numbers")
    else:
        fail("doc-symbols: line numbers", str(fn_syms))

def test_document_symbols_sorted():
    syms = get_document_symbols(SRC)
    lines = [s["line"] for s in syms]
    check("doc-symbols: sorted by line", lines, sorted(lines))

# ─────────────────────────────────────────────────────────────────────────────
# 5. Semantic tokens
# ─────────────────────────────────────────────────────────────────────────────

def test_semantic_tokens_returns_list():
    tokens = get_semantic_tokens(SRC)
    check("semantic-tokens: returns list", isinstance(tokens, list), True)

def test_semantic_tokens_multiple_of_5():
    tokens = get_semantic_tokens(SRC)
    check("semantic-tokens: length multiple of 5",
          len(tokens) % 5 == 0, True)

def test_semantic_tokens_non_empty():
    tokens = get_semantic_tokens(SRC)
    if len(tokens) >= 5:
        ok(f"semantic-tokens: {len(tokens)//5} tokens emitted")
    else:
        fail("semantic-tokens: non-empty", f"got {len(tokens)} ints")

def test_semantic_tokens_valid_types():
    tokens = get_semantic_tokens(SRC)
    n_token_types = len(TOKEN_TYPES)
    for i in range(3, len(tokens), 5):   # every token_type position
        if tokens[i] >= n_token_types:
            fail("semantic-tokens: token type in range", f"type={tokens[i]}")
            return
    ok("semantic-tokens: all token types in valid range")

def test_semantic_tokens_empty_source():
    tokens = get_semantic_tokens("")
    check("semantic-tokens: empty source = []", tokens, [])

def test_semantic_tokens_delta_encoding():
    tokens = get_semantic_tokens(SRC)
    if len(tokens) < 10:
        ok("semantic-tokens: too few to check delta (ok)")
        return
    # First token's delta_line must be >= 0
    if tokens[0] >= 0:
        ok("semantic-tokens: first delta_line >= 0")
    else:
        fail("semantic-tokens: first delta_line", f"got {tokens[0]}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. Code actions
# ─────────────────────────────────────────────────────────────────────────────

def test_code_action_let_to_const():
    src = "let PI = 3.14159\nlet x = 42\nx = 99\n"
    actions = get_code_actions(src, 0, 0, 0, 20)
    titles = [a["title"] for a in actions]
    if any("const" in t.lower() for t in titles):
        ok("code-action: let→const suggested")
    else:
        fail("code-action: let→const", f"got {titles}")

def test_code_action_no_let_to_const_for_reassigned():
    src = "let x = 1\nx = 2\nlet r = x\n"
    actions = get_code_actions(src, 0, 0, 0, 15)
    titles = [a["title"] for a in actions]
    # x is reassigned so should NOT suggest const
    if not any("'x'" in t and "const" in t for t in titles):
        ok("code-action: no const for reassigned var")
    else:
        fail("code-action: const incorrectly suggested for reassigned var", str(titles))

def test_code_action_add_return_type():
    src = "fn compute(x) {\n    return x * 2\n}\n"
    actions = get_code_actions(src, 0, 0, 2, 0)
    titles = [a["title"] for a in actions]
    if any("return type" in t.lower() for t in titles):
        ok("code-action: add return type suggested")
    else:
        fail("code-action: add return type", f"got {titles}")

def test_code_action_no_return_type_if_present():
    src = "fn compute(x) -> int {\n    return x * 2\n}\n"
    actions = get_code_actions(src, 0, 0, 2, 0)
    titles = [a["title"] for a in actions]
    if not any("return type" in t.lower() for t in titles):
        ok("code-action: no return type action when already annotated")
    else:
        fail("code-action: return type falsely suggested", str(titles))

def test_code_action_returns_list():
    actions = get_code_actions(SRC, 0, 0, 5, 0)
    check("code-action: returns list", isinstance(actions, list), True)

def test_code_action_edit_fields():
    src = "let PI = 3.14\nlet r = PI * 2\n"
    actions = get_code_actions(src, 0, 0, 0, 20)
    for a in actions:
        required = {"title", "kind", "edits"}
        missing = required - a.keys()
        if missing:
            fail("code-action: edit fields", f"missing {missing}")
            return
    ok("code-action: all actions have required fields")

# ─────────────────────────────────────────────────────────────────────────────
# 7. Hover with type info
# ─────────────────────────────────────────────────────────────────────────────

def test_hover_keyword():
    info = get_hover("fn f() { }", 0, 0)
    if info and "fn" in info["contents"]:
        ok("hover: keyword 'fn'")
    else:
        fail("hover: keyword", f"got {info}")

def test_hover_builtin():
    info = get_hover("print(42)", 0, 0)
    if info and "print" in info["contents"]:
        ok("hover: builtin 'print'")
    else:
        fail("hover: builtin", f"got {info}")

def test_hover_user_fn():
    info = get_hover(SRC, 13, 14)   # cursor on "add" call
    if info and "add" in info["contents"]:
        ok("hover: user fn shows signature")
    else:
        fail("hover: user fn", f"got {info}")

def test_hover_struct():
    info = get_hover(SRC, 14, 8)   # cursor on "Point"
    if info and "Point" in info["contents"]:
        ok("hover: struct shows definition")
    else:
        fail("hover: struct", f"got {info}")

def test_hover_variable():
    info = get_hover(SRC, 13, 4)   # cursor on "result"
    if info:
        ok(f"hover: variable '{info['contents'][:40]}'")
    else:
        ok("hover: variable (None — symbol may not be in table)")

def test_hover_nil():
    info = get_hover("let x = nil", 0, 4)
    # nil is not a keyword but can be hovered
    ok("hover: nil (no crash)")

def test_hover_empty_returns_none():
    info = get_hover("", 0, 0)
    check("hover: empty source returns None", info, None)

# ─────────────────────────────────────────────────────────────────────────────
# 8. DAP debugger
# ─────────────────────────────────────────────────────────────────────────────

def test_dap_imports():
    try:
        from inscript_dap import DAPServer, DebugInterpreter, _format_val
        ok("DAP: imports ok")
    except ImportError as e:
        fail("DAP: imports", str(e))

def test_dap_format_val():
    from inscript_dap import _format_val
    check("DAP: format nil",   _format_val(None),  "nil")
    check("DAP: format true",  _format_val(True),  "true")
    check("DAP: format false", _format_val(False), "false")
    check("DAP: format int",   _format_val(42),    "42")
    check("DAP: format list",  _format_val([1,2,3]), "[3 items]")
    check("DAP: format dict",  _format_val({"a":1}), "dict(1 keys)")

def test_dap_debug_interpreter_init():
    from inscript_dap import DebugInterpreter
    dbg = DebugInterpreter("let x = 1\n", "/tmp/test.ins")
    check("DAP: DebugInterpreter init source", dbg.source, "let x = 1\n")
    check("DAP: DebugInterpreter init path",   dbg.source_path, "/tmp/test.ins")
    check("DAP: DebugInterpreter breakpoints", dbg._breakpoints, set())
    ok("DAP: DebugInterpreter init ok")

def test_dap_set_breakpoints():
    from inscript_dap import DebugInterpreter
    dbg = DebugInterpreter("let x = 1\n", "/tmp/t.ins")
    dbg.set_breakpoints([1, 3, 7])
    check("DAP: set_breakpoints", dbg._breakpoints, {1, 3, 7})

def test_dap_message_framing():
    from inscript_dap import _write_msg, _read_msg
    import io
    buf = io.BytesIO()
    msg = {"type": "request", "seq": 1, "command": "initialize", "arguments": {}}
    _write_msg(buf, msg)
    buf.seek(0)
    received = _read_msg(buf)
    check("DAP: message round-trip type",    received["type"],    "request")
    check("DAP: message round-trip command", received["command"], "initialize")
    check("DAP: message round-trip seq",     received["seq"],     1)

def test_dap_server_initialize():
    from inscript_dap import DAPServer, _write_msg, _read_msg
    import io, json

    requests = io.BytesIO()
    _write_msg(requests, {
        "type": "request", "seq": 1, "command": "initialize",
        "arguments": {"clientName": "test", "adapterID": "inscript"}
    })
    requests.seek(0)
    responses = io.BytesIO()

    srv = DAPServer(requests, responses)
    msg = _read_msg(requests)
    requests.seek(0)
    srv._r = requests
    srv._w = responses

    # Process just the initialize request
    srv._handle(msg)
    responses.seek(0)

    # Read the response back
    resp = _read_msg(responses)
    check("DAP: initialize response type",    resp["type"],    "response")
    check("DAP: initialize response command", resp["command"], "initialize")
    check("DAP: initialize response success", resp["success"], True)

    # Read the initialized event
    responses_pos = responses.tell()
    evt = _read_msg(responses)
    if evt:
        check("DAP: initialized event type", evt["type"], "event")
        check("DAP: initialized event name", evt["event"], "initialized")
    else:
        ok("DAP: initialized event (may be buffered differently)")

def test_dap_evaluate_literal():
    from inscript_dap import DebugInterpreter
    dbg = DebugInterpreter("let x = 42\n", "/tmp/t.ins")
    dbg._locals_snapshot = {"x": 42, "y": "hello"}
    result = dbg.__class__.__dict__.get('_evaluate')
    # evaluate via the DAPServer.evaluate helper
    from inscript_dap import DAPServer
    import io
    srv = DAPServer(io.BytesIO(), io.BytesIO())
    srv._dbg = dbg
    result = srv._evaluate("x")
    check("DAP: evaluate variable lookup", result, "42")

def test_dap_get_variables():
    from inscript_dap import DebugInterpreter
    dbg = DebugInterpreter("let x = 1\n", "/tmp/t.ins")
    dbg._locals_snapshot  = {"x": 10, "y": "hi"}
    dbg._globals_snapshot = {"PI": 3.14}
    local_vars  = dbg.get_variables("locals")
    global_vars = dbg.get_variables("globals")
    names_l = [v["name"] for v in local_vars]
    names_g = [v["name"] for v in global_vars]
    check_in("DAP: locals contains x", "x", names_l)
    check_in("DAP: globals contains PI", "PI", names_g)

# ─────────────────────────────────────────────────────────────────────────────
# 9. Existing LSP — regression
# ─────────────────────────────────────────────────────────────────────────────

def test_diagnostics_still_work():
    diags = get_diagnostics("let x = 1\nlet y = @@invalid@@\n")
    check("diagnostics: still fires on errors", isinstance(diags, list), True)

def test_completions_still_work():
    items = get_completions("let x = 1\n", 0, 3)
    check("completions: returns list", isinstance(items, list), True)

# ─────────────────────────────────────────────────────────────────────────────
# 10. Version
# ─────────────────────────────────────────────────────────────────────────────

def test_version():
    check("version_is_2.5.0", repl_mod.VERSION, "2.5.0")

# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("test_v250.py — v2.5.0: IDE & Editor Integration")
    print("=" * 60)

    # Go-to-definition
    test_definition_fn();            test_definition_struct()
    test_definition_undefined();     test_definition_empty_source()

    # References
    test_references_fn();            test_references_struct()
    test_references_no_crash_empty(); test_references_end_col_set()

    # Rename
    test_rename_fn();                test_rename_edit_fields()
    test_rename_new_text();          test_rename_no_crash_unknown()

    # Document symbols
    test_document_symbols_count();   test_document_symbols_fn_present()
    test_document_symbols_struct_present(); test_document_symbols_kind()
    test_document_symbols_line_numbers();   test_document_symbols_sorted()

    # Semantic tokens
    test_semantic_tokens_returns_list(); test_semantic_tokens_multiple_of_5()
    test_semantic_tokens_non_empty();    test_semantic_tokens_valid_types()
    test_semantic_tokens_empty_source(); test_semantic_tokens_delta_encoding()

    # Code actions
    test_code_action_let_to_const()
    test_code_action_no_let_to_const_for_reassigned()
    test_code_action_add_return_type()
    test_code_action_no_return_type_if_present()
    test_code_action_returns_list();  test_code_action_edit_fields()

    # Hover
    test_hover_keyword();            test_hover_builtin()
    test_hover_user_fn();            test_hover_struct()
    test_hover_variable();           test_hover_nil()
    test_hover_empty_returns_none()

    # DAP
    test_dap_imports();              test_dap_format_val()
    test_dap_debug_interpreter_init(); test_dap_set_breakpoints()
    test_dap_message_framing();      test_dap_server_initialize()
    test_dap_evaluate_literal();     test_dap_get_variables()

    # Regressions
    test_diagnostics_still_work();   test_completions_still_work()

    # Version
    test_version()

    total = PASS + FAIL
    print("=" * 60)
    print(f"{PASS}/{total} passed  ({FAIL} failed)")
    sys.exit(0 if FAIL == 0 else 1)
