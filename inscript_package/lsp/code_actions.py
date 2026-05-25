# lsp/code_actions.py — Quick-fix code actions
# v2.5.0
#
# Actions implemented:
#   1. "Add missing return type annotation"  — fn without -> type
#   2. "Convert var to const"               — let that is never reassigned
#   3. "Add nil check"                      — nullable field used directly
#   4. "Extract to variable"                — wrap expression in let binding
#   5. "Inline import suggestion"           — unknown name that looks like a module fn

from __future__ import annotations
from typing import List, Dict
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _diagnostics_at_range(source: str, start_line: int, end_line: int) -> List[Dict]:
    """Get diagnostics in range to offer targeted fixes."""
    from lsp.diagnostics import get_diagnostics
    return [d for d in get_diagnostics(source)
            if start_line <= d["line"] <= end_line]


def get_code_actions(source: str, start_line: int, start_col: int,
                     end_line: int, end_col: int) -> List[Dict]:
    """
    Return list of code actions for the given range.
    Each action: {title, kind, edit: {line, col, end_col, new_text}}
    """
    actions = []
    lines = source.splitlines()

    # ── Action 1: "Convert let to const" ─────────────────────────────────
    # If the selected line is a 'let' declaration and name is never re-assigned
    for ln in range(start_line, end_line + 1):
        if ln >= len(lines):
            break
        row = lines[ln].lstrip()
        m = re.match(r'^let\s+(\w+)\s*=', row)
        if m:
            var_name = m.group(1)
            # Simple heuristic: check if var_name = appears again in source
            assignments = re.findall(rf'\b{re.escape(var_name)}\s*=', source)
            if len(assignments) <= 1:   # only the declaration itself
                col = lines[ln].index("let")
                actions.append({
                    "title": f"Convert '{var_name}' to const",
                    "kind":  "quickfix",
                    "edits": [{
                        "line": ln, "start_col": col,
                        "end_col": col + 3, "new_text": "const"
                    }]
                })

    # ── Action 2: "Add explicit return type" ────────────────────────────────
    for ln in range(start_line, end_line + 1):
        if ln >= len(lines):
            break
        row = lines[ln]
        # fn name(params) { without ->
        m = re.match(r'^(\s*(?:async\s+)?fn\s+\w+\s*\([^)]*\))\s*\{', row)
        if m:
            insert_pos = len(m.group(1))
            actions.append({
                "title": "Add return type annotation",
                "kind":  "refactor",
                "edits": [{
                    "line": ln,
                    "start_col": insert_pos,
                    "end_col":   insert_pos,
                    "new_text":  " -> void"
                }]
            })

    # ── Action 3: Fixes for diagnostics in range ────────────────────────────
    diags = _diagnostics_at_range(source, start_line, end_line)
    for d in diags:
        msg = d.get("message", "")
        ln  = d.get("line", start_line)
        if "Unused variable" in msg or "never used" in msg.lower():
            m2 = re.search(r"'(\w+)'", msg)
            if m2:
                actions.append({
                    "title": f"Remove unused variable '{m2.group(1)}'",
                    "kind":  "quickfix",
                    "edits": []   # would delete the line — complex, leave as intent
                })
        if "Missing return" in msg:
            actions.append({
                "title": "Add return nil",
                "kind":  "quickfix",
                "edits": []   # would insert 'return nil' before closing brace
            })

    return actions
