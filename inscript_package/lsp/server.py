#!/usr/bin/env python3
"""
InScript LSP Server
====================
Provides: diagnostics (errors/warnings), completions, hover documentation.

Requirements:
    pip install pygls

Usage:
    # Start the server (VS Code extension launches this automatically)
    python -m inscript_package.lsp.server

    # Or run directly
    python server.py
"""
import sys, os, logging

# Ensure inscript_package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(filename="/tmp/inscript_lsp.log", level=logging.DEBUG,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("inscript-lsp")

# ── Try to import pygls ────────────────────────────────────────────────────
try:
    from pygls.server import LanguageServer
    from lsprotocol.types import (
        TEXT_DOCUMENT_DID_OPEN,
        TEXT_DOCUMENT_DID_CHANGE,
        TEXT_DOCUMENT_COMPLETION,
        TEXT_DOCUMENT_HOVER,
        DidOpenTextDocumentParams,
        DidChangeTextDocumentParams,
        CompletionParams,
        CompletionList,
        CompletionItem,
        CompletionItemKind,
        HoverParams,
        Hover,
        MarkupContent,
        MarkupKind,
        Diagnostic,
        DiagnosticSeverity,
        Position,
        Range,
        CompletionOptions,
        TextDocumentSyncKind,
    )
    HAS_PYGLS = True
except ImportError:
    HAS_PYGLS = False
    log.warning("pygls not installed — LSP server will not start. Run: pip install pygls")

from .diagnostics import get_diagnostics
from .completions  import get_completions
from .hover        import get_hover

# ── Document store ─────────────────────────────────────────────────────────
_documents: dict[str, str] = {}

def _severity(s: str) -> "DiagnosticSeverity":
    return DiagnosticSeverity.Error if s == "error" else DiagnosticSeverity.Warning

def _make_diagnostics(uri: str, source: str) -> list:
    raw = get_diagnostics(source)
    diags = []
    for d in raw:
        line    = d["line"]
        col     = d["col"]
        end_col = d.get("end_col", col + 20)
        diags.append(Diagnostic(
            range=Range(
                start=Position(line=line, character=col),
                end=Position(line=line, character=end_col),
            ),
            message=d["message"],
            severity=_severity(d["severity"]),
            source="inscript",
        ))
    return diags

# ── Server ─────────────────────────────────────────────────────────────────
if HAS_PYGLS:
    server = LanguageServer(
        name="inscript-lsp",
        version="1.0.0",
        text_document_sync_kind=TextDocumentSyncKind.Full,
    )

    @server.feature(TEXT_DOCUMENT_DID_OPEN)
    def on_open(ls: LanguageServer, params: DidOpenTextDocumentParams):
        uri    = params.text_document.uri
        source = params.text_document.text
        _documents[uri] = source
        log.debug(f"Opened {uri}")
        ls.publish_diagnostics(uri, _make_diagnostics(uri, source))

    @server.feature(TEXT_DOCUMENT_DID_CHANGE)
    def on_change(ls: LanguageServer, params: DidChangeTextDocumentParams):
        uri    = params.text_document.uri
        source = params.content_changes[-1].text
        _documents[uri] = source
        ls.publish_diagnostics(uri, _make_diagnostics(uri, source))

    @server.feature(
        TEXT_DOCUMENT_COMPLETION,
        CompletionOptions(trigger_characters=[".", ":"]),
    )
    def on_completion(ls: LanguageServer, params: CompletionParams) -> CompletionList:
        uri    = params.text_document.uri
        source = _documents.get(uri, "")
        line   = params.position.line
        col    = params.position.character
        raw    = get_completions(source, line, col)

        _KIND = {
            "keyword":  CompletionItemKind.Keyword,
            "function": CompletionItemKind.Function,
            "snippet":  CompletionItemKind.Snippet,
            "variable": CompletionItemKind.Variable,
        }

        items = [
            CompletionItem(
                label=r["label"],
                kind=_KIND.get(r.get("kind", "function"), CompletionItemKind.Text),
                detail=r.get("detail", ""),
                insert_text=r.get("insert", r["label"]),
            )
            for r in raw
        ]
        return CompletionList(is_incomplete=False, items=items)

    @server.feature(TEXT_DOCUMENT_HOVER)
    def on_hover(ls: LanguageServer, params: HoverParams) -> Hover | None:
        uri    = params.text_document.uri
        source = _documents.get(uri, "")
        line   = params.position.line
        col    = params.position.character
        info   = get_hover(source, line, col)
        if not info:
            return None
        return Hover(
            contents=MarkupContent(kind=MarkupKind.Markdown, value=f"```\n{info['contents']}\n```")
        )

def main():
    if not HAS_PYGLS:
        print("ERROR: pygls is not installed.")
        print("       Run:  pip install pygls")
        print("       Then: python -m inscript_package.lsp.server")
        sys.exit(1)
    log.info("InScript LSP server starting on stdio")
    print("InScript LSP server ready", file=sys.stderr)
    server.start_io()

if __name__ == "__main__":
    main()
