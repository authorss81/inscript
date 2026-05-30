# -*- coding: utf-8 -*-
"""
visual_script.py — InScript v3.0.0  Visual Scripting
================================================================
Compile a .vins (Visual InScript) JSON graph into .ins source code.

.vins file format
─────────────────
{
  "version":  "3.0.0",
  "name":     "MyGraph",
  "nodes": [
    {"id":"n1","type":"event","event":"_ready","x":100,"y":100},
    {"id":"n2","type":"fn_call","fn":"print","x":300,"y":100},
    {"id":"n3","type":"literal","value_type":"string","value":"Hello","x":200,"y":200}
  ],
  "connections": [
    {"from_node":"n1","from_port":"exec","to_node":"n2","to_port":"exec"},
    {"from_node":"n3","from_port":"value","to_node":"n2","to_port":"arg0"}
  ]
}

Node types
──────────
  event         — lifecycle entry point: _ready | _update(dt) | _draw | on_reload
  fn_call       — call any fn: {fn, arg0..argN ports}
  literal       — constant: {value_type: string|int|float|bool, value}
  variable_get  — read a let var: {name}
  variable_set  — assign a let var: {name, value port}
  if_branch     — if/else: {condition port, then exec port, else exec port}
  op            — binary operator: {operator: +|-|*|/|==|!=|<|>|<=|>=|&&|"||", left, right ports}
  not_op        — unary not: {value port}
  return        — return a value: {value port}
  comment       — documentation only, no code output
  print         — shortcut for fn_call(print): {message port}
  wait          — wait(seconds): {seconds port}
  node_get_prop — get a node property: {node_name, prop}
  node_set_prop — set a node property: {node_name, prop, value port}

CLI
───
  inscript --visual-compile game.vins         → game.ins
  inscript --visual-compile game.vins -o out.ins
"""

from __future__ import annotations
import json, os, textwrap
from typing import Any, Dict, List, Optional, Set, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

class VinsNode:
    def __init__(self, data: dict):
        self.id    = data["id"]
        self.type  = data["type"]
        self.props = {k: v for k, v in data.items()
                      if k not in ("id", "type", "x", "y")}
        self.x     = float(data.get("x", 0))
        self.y     = float(data.get("y", 0))

    def get(self, key, default=None):
        return self.props.get(key, default)

    def __repr__(self):
        return f"<VinsNode {self.id} type={self.type}>"


class VinsConnection:
    def __init__(self, data: dict):
        self.from_node = data["from_node"]
        self.from_port = data["from_port"]
        self.to_node   = data["to_node"]
        self.to_port   = data["to_port"]

    def __repr__(self):
        return (f"<Conn {self.from_node}.{self.from_port} → "
                f"{self.to_node}.{self.to_port}>")


class VinsGraph:
    def __init__(self, data: dict):
        self.version     = data.get("version", "3.0.0")
        self.name        = data.get("name", "VisualScript")
        self.description = data.get("description", "")
        self.nodes:       Dict[str, VinsNode] = {}
        self.connections: List[VinsConnection] = []

        for nd in data.get("nodes", []):
            n = VinsNode(nd)
            self.nodes[n.id] = n

        for cd in data.get("connections", []):
            self.connections.append(VinsConnection(cd))

    # ── query helpers ──────────────────────────────────────────────────────────

    def outgoing_exec(self, node_id: str) -> Optional[str]:
        """Return node_id of the next node in the exec chain, or None."""
        for c in self.connections:
            if c.from_node == node_id and c.from_port == "exec":
                return c.to_node
        return None

    def incoming_value(self, node_id: str, port: str) -> Optional[str]:
        """Return node_id that feeds value into node_id.port, or None."""
        for c in self.connections:
            if c.to_node == node_id and c.to_port == port:
                return c.from_node
        return None

    def nodes_of_type(self, node_type: str) -> List[VinsNode]:
        return [n for n in self.nodes.values() if n.type == node_type]

    @classmethod
    def load(cls, path: str) -> "VinsGraph":
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    @classmethod
    def loads(cls, text: str) -> "VinsGraph":
        return cls(json.loads(text))


# ─────────────────────────────────────────────────────────────────────────────
# Compiler
# ─────────────────────────────────────────────────────────────────────────────

INDENT = "    "

_BINARY_OPS = {
    "+": "+", "-": "-", "*": "*", "/": "/",
    "==": "==", "!=": "!=", "<": "<", ">": ">",
    "<=": "<=", ">=": ">=",
    "&&": "&&", "||": "||",
    "and": "&&", "or": "||",
}


class VisualScriptCompiler:
    """
    Compiles a VinsGraph into InScript source code.

    compile() returns the full .ins source as a string.
    """

    def __init__(self, graph: VinsGraph):
        self.graph       = graph
        self._errors:    List[str] = []
        self._vars:      Set[str]  = set()   # let-declared variables
        self._hooks:     Dict[str, List[str]] = {}  # event_name → code lines

    # ── public API ─────────────────────────────────────────────────────────────

    def compile(self) -> str:
        g = self.graph
        self._errors  = []
        self._vars    = set()
        self._hooks   = {}

        # Gather all variable_set / variable_get names to declare with let
        for node in g.nodes.values():
            if node.type in ("variable_set", "variable_get"):
                name = node.get("name", "")
                if name:
                    self._vars.add(name)

        # Compile each event entry point
        event_nodes = g.nodes_of_type("event")
        if not event_nodes:
            # No events → emit a simple script-style file (no node wrapper)
            lines = self._compile_orphan_graph()
            return "\n".join(lines) + "\n"

        for ev_node in sorted(event_nodes, key=lambda n: n.y):
            event_name = ev_node.get("event", "_ready")
            body_lines = []
            self._compile_exec_chain(ev_node.id, body_lines, depth=0)
            self._hooks[event_name] = body_lines

        # Build node declaration
        lines = [f"# Generated by InScript Visual Scripting v{self.graph.version}"]
        if self.graph.description:
            lines.append(f"# {self.graph.description}")
        lines.append("")

        # Variable declarations
        for var_name in sorted(self._vars):
            lines.append(f"let {var_name}: any = nil")
        if self._vars:
            lines.append("")

        lines.append(f"node {_safe_name(self.graph.name)} {{")

        for event_name, body in self._hooks.items():
            param = "(dt)" if "update" in event_name.lower() else "()"
            lines.append(f"{INDENT}{event_name}{param} {{")
            if body:
                for bl in body:
                    lines.append(f"{INDENT}{INDENT}{bl}")
            else:
                lines.append(f"{INDENT}{INDENT}# (empty)")
            lines.append(f"{INDENT}}}")

        lines.append("}")
        return "\n".join(lines) + "\n"

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    # ── exec chain walker ──────────────────────────────────────────────────────

    def _compile_exec_chain(self, start_id: str, out: List[str],
                             depth: int, visited: Set[str] = None) -> None:
        if visited is None:
            visited = set()

        current_id = self.graph.outgoing_exec(start_id)
        while current_id and current_id not in visited:
            visited.add(current_id)
            node = self.graph.nodes.get(current_id)
            if node is None:
                break

            stmt = self._compile_node_stmt(node, depth)
            if stmt is not None:
                out.extend(stmt if isinstance(stmt, list) else [stmt])

            # If/branch forks the chain
            if node.type == "if_branch":
                break

            current_id = self.graph.outgoing_exec(current_id)

    def _compile_node_stmt(self, node: VinsNode, depth: int) -> Optional[Any]:
        t = node.type

        if t == "fn_call":
            return self._compile_fn_call(node)

        if t == "print":
            msg = self._resolve_value(node.id, "message", default='"..."')
            return f"print({msg})"

        if t == "wait":
            secs = self._resolve_value(node.id, "seconds", default="1.0")
            return f"wait({secs})"

        if t == "variable_set":
            name  = node.get("name", "_unnamed")
            value = self._resolve_value(node.id, "value", default="nil")
            return f"{name} = {value}"

        if t == "node_set_prop":
            nname = node.get("node_name", "self")
            prop  = node.get("prop", "x")
            value = self._resolve_value(node.id, "value", default="nil")
            return f"{nname}.{prop} = {value}"

        if t == "return":
            value = self._resolve_value(node.id, "value", default="nil")
            return f"return {value}"

        if t == "if_branch":
            return self._compile_if(node, depth)

        if t in ("event", "comment", "literal", "variable_get",
                 "op", "not_op", "node_get_prop"):
            return None   # data/entry nodes — no statement

        self._errors.append(f"Unknown exec node type '{t}' (id={node.id})")
        return f"# [unknown node type: {t}]"

    def _compile_fn_call(self, node: VinsNode) -> str:
        fn = node.get("fn", "print")
        # Collect arg ports (arg0, arg1, arg2 …)
        args = []
        i = 0
        while True:
            port     = f"arg{i}"
            src_id   = self.graph.incoming_value(node.id, port)
            if src_id is None and i >= 3:
                break
            val = self._resolve_value(node.id, port, default=None)
            if val is None and i >= 2:
                break
            if val is not None:
                args.append(val)
            i += 1
        return f"{fn}({', '.join(args)})"

    def _compile_if(self, node: VinsNode, depth: int) -> List[str]:
        cond = self._resolve_value(node.id, "condition", default="true")
        lines = [f"if {cond} {{"]

        # then-branch
        then_lines: List[str] = []
        then_first = None
        for c in self.graph.connections:
            if c.from_node == node.id and c.from_port == "then":
                then_first = c.to_node
        if then_first:
            self._compile_exec_chain(
                _fake_entry(then_first, self.graph), then_lines, depth + 1
            )
        for tl in then_lines:
            lines.append(f"{INDENT}{tl}")

        # else-branch
        else_lines: List[str] = []
        else_first = None
        for c in self.graph.connections:
            if c.from_node == node.id and c.from_port == "else":
                else_first = c.to_node
        if else_first:
            lines.append("} else {")
            self._compile_exec_chain(
                _fake_entry(else_first, self.graph), else_lines, depth + 1
            )
            for el in else_lines:
                lines.append(f"{INDENT}{el}")

        lines.append("}")
        return lines

    # ── value resolver ─────────────────────────────────────────────────────────

    def _resolve_value(self, consumer_id: str, port: str,
                       default: Optional[str] = None) -> Optional[str]:
        src_id = self.graph.incoming_value(consumer_id, port)
        if src_id is None:
            return default
        src = self.graph.nodes.get(src_id)
        if src is None:
            return default
        return self._emit_value_expr(src)

    def _emit_value_expr(self, node: VinsNode) -> str:
        t = node.type

        if t == "literal":
            vtype = node.get("value_type", "string")
            val   = node.get("value", "")
            if vtype == "string":
                escaped = str(val).replace('"', '\\"')
                return f'"{escaped}"'
            if vtype == "bool":
                return "true" if str(val).lower() in ("true", "1", "yes") else "false"
            return str(val)   # int / float

        if t == "variable_get":
            return str(node.get("name", "_var"))

        if t == "node_get_prop":
            nname = node.get("node_name", "self")
            prop  = node.get("prop", "x")
            return f"{nname}.{prop}"

        if t == "op":
            operator = _BINARY_OPS.get(node.get("operator", "+"), "+")
            left  = self._resolve_value(node.id, "left",  default="0")
            right = self._resolve_value(node.id, "right", default="0")
            return f"({left} {operator} {right})"

        if t == "not_op":
            val = self._resolve_value(node.id, "value", default="false")
            return f"!{val}"

        if t == "fn_call":
            # Value-mode fn_call (used as expression)
            fn   = node.get("fn", "fn")
            args = []
            i    = 0
            while True:
                val = self._resolve_value(node.id, f"arg{i}", default=None)
                if val is None and i >= 2:
                    break
                if val is not None:
                    args.append(val)
                i += 1
            return f"{fn}({', '.join(args)})"

        return f"/* unknown value node {node.id} */"

    # ── orphan graph (no events) ───────────────────────────────────────────────

    def _compile_orphan_graph(self) -> List[str]:
        lines = [f"# Generated by InScript Visual Scripting v{self.graph.version}", ""]
        for var_name in sorted(self._vars):
            lines.append(f"let {var_name}: any = nil")
        if self._vars:
            lines.append("")
        # Emit variable_set nodes in y-order
        set_nodes = sorted(
            [n for n in self.graph.nodes.values() if n.type == "variable_set"],
            key=lambda n: n.y
        )
        for node in set_nodes:
            stmt = self._compile_node_stmt(node, 0)
            if stmt:
                lines.append(stmt)
        return lines


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_name(name: str) -> str:
    """Convert a graph name to a valid InScript identifier."""
    import re
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if safe and safe[0].isdigit():
        safe = "_" + safe
    return safe or "VisualScript"


def _fake_entry(first_node_id: str, graph: VinsGraph) -> str:
    """
    Return a synthetic 'entry' id so _compile_exec_chain starts at first_node_id.
    We do this by injecting a temporary exec connection.
    """
    # Create a synthetic node id
    fake_id = f"__fake__{first_node_id}"
    conn = VinsConnection({
        "from_node": fake_id,
        "from_port": "exec",
        "to_node":   first_node_id,
        "to_port":   "exec",
    })
    graph.connections.append(conn)
    # Create a fake node
    fake_node = VinsNode({"id": fake_id, "type": "comment"})
    graph.nodes[fake_id] = fake_node
    return fake_id


# ─────────────────────────────────────────────────────────────────────────────
# File I/O helpers
# ─────────────────────────────────────────────────────────────────────────────

def compile_file(vins_path: str, output_path: str = None) -> str:
    """
    Compile a .vins file to .ins source.
    Returns the output path.
    """
    graph  = VinsGraph.load(vins_path)
    compiler = VisualScriptCompiler(graph)
    source = compiler.compile()

    if compiler.errors:
        for e in compiler.errors:
            print(f"[visual] Warning: {e}")

    if output_path is None:
        output_path = os.path.splitext(vins_path)[0] + ".ins"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(source)

    print(f"[visual] ✅ {vins_path} → {output_path} ({len(source)} chars)")
    return output_path


def make_template(name: str = "MyGraph", event: str = "_ready") -> dict:
    """Return a minimal .vins template dict for the given event."""
    return {
        "version": "3.0.0",
        "name":    name,
        "nodes": [
            {"id": "n1", "type": "event",   "event": event,
             "x": 80,  "y": 120},
            {"id": "n2", "type": "print",
             "x": 300, "y": 120},
            {"id": "n3", "type": "literal", "value_type": "string",
             "value": f"Hello from {name}!", "x": 300, "y": 220},
        ],
        "connections": [
            {"from_node": "n1", "from_port": "exec",
             "to_node":   "n2", "to_port":   "exec"},
            {"from_node": "n3", "from_port": "value",
             "to_node":   "n2", "to_port":   "message"},
        ],
    }
