#!/usr/bin/env python3
"""
InScript LSP Server v2.5.0
============================
Capabilities:
  • Diagnostics        (errors / warnings, real-time)
  • Completions        (keywords, functions, snippets, struct fields)
  • Hover              (type info, docs, fn signatures)
  • Go-to-definition   (jump to where a symbol is defined)
  • Find-all-references (all uses of a symbol)
  • Rename symbol      (rename across entire file)
  • Document symbols   (outline: all fns / structs / vars)
  • Semantic tokens    (richer syntax highlighting)
  • Code actions       (quick fixes: let→const, add return type, …)

Requirements:  pip install pygls
"""
import sys, os, logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(filename="/tmp/inscript_lsp.log", level=logging.DEBUG,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("inscript-lsp")

try:
    from pygls.server import LanguageServer
    from lsprotocol.types import (
        # Lifecycle
        INITIALIZE,
        InitializeParams,
        InitializeResult,
        ServerCapabilities,
        TextDocumentSyncKind,
        # Document sync
        TEXT_DOCUMENT_DID_OPEN,
        TEXT_DOCUMENT_DID_CHANGE,
        TEXT_DOCUMENT_DID_SAVE,
        DidOpenTextDocumentParams,
        DidChangeTextDocumentParams,
        DidSaveTextDocumentParams,
        # Completions
        TEXT_DOCUMENT_COMPLETION,
        CompletionParams,
        CompletionList,
        CompletionItem,
        CompletionItemKind,
        CompletionOptions,
        # Hover
        TEXT_DOCUMENT_HOVER,
        HoverParams,
        Hover,
        MarkupContent,
        MarkupKind,
        # Diagnostics
        Diagnostic,
        DiagnosticSeverity,
        Position,
        Range,
        # Go-to-definition
        TEXT_DOCUMENT_DEFINITION,
        DefinitionParams,
        Location,
        # References
        TEXT_DOCUMENT_REFERENCES,
        ReferenceParams,
        # Rename
        TEXT_DOCUMENT_RENAME,
        RenameParams,
        WorkspaceEdit,
        TextEdit,
        # Document symbols
        TEXT_DOCUMENT_DOCUMENT_SYMBOL,
        DocumentSymbolParams,
        DocumentSymbol,
        SymbolKind,
        # Semantic tokens
        TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
        SemanticTokensParams,
        SemanticTokens,
        SemanticTokensLegend,
        SemanticTokensOptions,
        # Code actions
        TEXT_DOCUMENT_CODE_ACTION,
        CodeActionParams,
        CodeAction,
        CodeActionKind,
    )
    HAS_PYGLS = True
except ImportError:
    HAS_PYGLS = False
    log.warning("pygls not installed — run: pip install pygls")

from .diagnostics    import get_diagnostics
from .completions    import get_completions
from .hover          import get_hover
from .definition     import (get_definition, get_references,
                              get_rename_edits, get_document_symbols)
from .semantic_tokens import get_semantic_tokens, TOKEN_TYPES, TOKEN_MODIFIERS
from .code_actions   import get_code_actions

# ── Document store ────────────────────────────────────────────────────────────
_documents: dict = {}

def _severity(s: str):
    return DiagnosticSeverity.Error if s == "error" else DiagnosticSeverity.Warning

def _make_range(line, col, end_col=None):
    return Range(
        start=Position(line=line, character=col),
        end=Position(line=line, character=end_col or col + 20),
    )

def _publish_diags(ls, uri: str, source: str):
    raw = get_diagnostics(source)
    diags = [
        Diagnostic(
            range=_make_range(d["line"], d["col"], d.get("end_col")),
            message=d["message"],
            severity=_severity(d["severity"]),
            source="inscript",
        )
        for d in raw
    ]
    ls.publish_diagnostics(uri, diags)

# ── Symbol kind mapping (only available when pygls is installed) ──────────────
if HAS_PYGLS:
    _SYM_KIND = {
        "fn":     SymbolKind.Function,
        "struct": SymbolKind.Struct,
        "const":  SymbolKind.Constant,
        "var":    SymbolKind.Variable,
        "let":    SymbolKind.Variable,
        "enum":   SymbolKind.Enum,
    }
else:
    _SYM_KIND = {}   # fallback — never used when pygls absent

# ── Server ────────────────────────────────────────────────────────────────────
if HAS_PYGLS:
    server = LanguageServer(
        name="inscript-lsp",
        version="3.9.4",
        text_document_sync_kind=TextDocumentSyncKind.Full,
    )

    # ── Document sync ──────────────────────────────────────────────────────

    @server.feature(TEXT_DOCUMENT_DID_OPEN)
    def on_open(ls, params: DidOpenTextDocumentParams):
        uri    = params.text_document.uri
        source = params.text_document.text
        _documents[uri] = source
        _publish_diags(ls, uri, source)

    @server.feature(TEXT_DOCUMENT_DID_CHANGE)
    def on_change(ls, params: DidChangeTextDocumentParams):
        uri    = params.text_document.uri
        source = params.content_changes[-1].text
        _documents[uri] = source
        _publish_diags(ls, uri, source)

    @server.feature(TEXT_DOCUMENT_DID_SAVE)
    def on_save(ls, params: DidSaveTextDocumentParams):
        uri    = params.text_document.uri
        source = _documents.get(uri, "")
        _publish_diags(ls, uri, source)

    # ── Completions ────────────────────────────────────────────────────────

    @server.feature(
        TEXT_DOCUMENT_COMPLETION,
        CompletionOptions(trigger_characters=[".", ":", " "]),
    )
    def on_completion(ls, params: CompletionParams) -> CompletionList:
        uri    = params.text_document.uri
        source = _documents.get(uri, "")
        line   = params.position.line
        col    = params.position.character
        raw    = get_completions(source, line, col)
        _KIND  = {
            "keyword":  CompletionItemKind.Keyword,
            "function": CompletionItemKind.Function,
            "snippet":  CompletionItemKind.Snippet,
            "variable": CompletionItemKind.Variable,
            "struct":   CompletionItemKind.Struct,
            "field":    CompletionItemKind.Field,
        }
        items = [
            CompletionItem(
                label=r["label"],
                kind=_KIND.get(r.get("kind", "function"), CompletionItemKind.Text),
                detail=r.get("detail", ""),
                insert_text=r.get("insert", r["label"]),
                documentation=MarkupContent(
                    kind=MarkupKind.Markdown,
                    value=r.get("documentation", "")
                ) if r.get("documentation") else None,
            )
            for r in raw
        ]
        return CompletionList(is_incomplete=False, items=items)

    # ── Hover ──────────────────────────────────────────────────────────────

    @server.feature(TEXT_DOCUMENT_HOVER)
    def on_hover(ls, params: HoverParams):
        uri    = params.text_document.uri
        source = _documents.get(uri, "")
        info   = get_hover(source, params.position.line, params.position.character)
        if not info:
            return None
        return Hover(
            contents=MarkupContent(
                kind=MarkupKind.Markdown,
                value=info["contents"],
            )
        )

    # ── Go-to-definition ──────────────────────────────────────────────────

    @server.feature(TEXT_DOCUMENT_DEFINITION)
    def on_definition(ls, params: DefinitionParams):
        uri    = params.text_document.uri
        source = _documents.get(uri, "")
        defn   = get_definition(source, params.position.line,
                                 params.position.character)
        if not defn:
            return None
        return Location(
            uri=uri,
            range=_make_range(defn["line"], defn["col"]),
        )

    # ── Find all references ───────────────────────────────────────────────

    @server.feature(TEXT_DOCUMENT_REFERENCES)
    def on_references(ls, params: ReferenceParams):
        uri    = params.text_document.uri
        source = _documents.get(uri, "")
        refs   = get_references(source, params.position.line,
                                 params.position.character,
                                 include_definition=params.context.include_declaration)
        return [
            Location(uri=uri, range=_make_range(r["line"], r["col"], r["end_col"]))
            for r in refs
        ]

    # ── Rename symbol ─────────────────────────────────────────────────────

    @server.feature(TEXT_DOCUMENT_RENAME)
    def on_rename(ls, params: RenameParams):
        uri      = params.text_document.uri
        source   = _documents.get(uri, "")
        new_name = params.new_name
        edits    = get_rename_edits(source, params.position.line,
                                    params.position.character, new_name)
        text_edits = [
            TextEdit(
                range=_make_range(e["line"], e["start_col"], e["end_col"]),
                new_text=e["new_text"],
            )
            for e in edits
        ]
        return WorkspaceEdit(changes={uri: text_edits})

    # ── Document symbols (outline) ────────────────────────────────────────

    @server.feature(TEXT_DOCUMENT_DOCUMENT_SYMBOL)
    def on_document_symbols(ls, params: DocumentSymbolParams):
        uri    = params.text_document.uri
        source = _documents.get(uri, "")
        syms   = get_document_symbols(source)
        return [
            DocumentSymbol(
                name=s["name"],
                kind=_SYM_KIND.get(s["kind"], SymbolKind.Variable),
                range=_make_range(s["line"], s["col"]),
                selection_range=_make_range(s["line"], s["col"]),
                detail=s.get("detail", ""),
            )
            for s in syms
        ]

    # ── Semantic tokens ───────────────────────────────────────────────────

    @server.feature(
        TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
        SemanticTokensOptions(
            legend=SemanticTokensLegend(
                token_types=TOKEN_TYPES,
                token_modifiers=TOKEN_MODIFIERS,
            ),
            full=True,
        ),
    )
    def on_semantic_tokens(ls, params: SemanticTokensParams):
        uri    = params.text_document.uri
        source = _documents.get(uri, "")
        data   = get_semantic_tokens(source)
        return SemanticTokens(data=data)

    # ── Code actions ──────────────────────────────────────────────────────

    @server.feature(TEXT_DOCUMENT_CODE_ACTION)
    def on_code_action(ls, params: CodeActionParams):
        uri    = params.text_document.uri
        source = _documents.get(uri, "")
        r      = params.range
        raw    = get_code_actions(
            source,
            r.start.line, r.start.character,
            r.end.line,   r.end.character,
        )
        actions = []
        for a in raw:
            text_edits = [
                TextEdit(
                    range=_make_range(e["line"], e["start_col"], e["end_col"]),
                    new_text=e["new_text"],
                )
                for e in a.get("edits", [])
            ]
            actions.append(CodeAction(
                title=a["title"],
                kind=CodeActionKind.QuickFix if a.get("kind") == "quickfix"
                     else CodeActionKind.Refactor,
                edit=WorkspaceEdit(changes={uri: text_edits}) if text_edits else None,
            ))
        return actions


def main():
    if not HAS_PYGLS:
        print("ERROR: pygls is not installed.")
        print("       Run:  pip install pygls")
        print("       Then: inscript --lsp")
        sys.exit(1)
    log.info("InScript LSP server v2.5.0 starting on stdio")
    print("InScript LSP v2.5.0 ready", file=sys.stderr)
    server.start_io()

if __name__ == "__main__":
    main()
