# -*- coding: utf-8 -*-
"""
studio_bridge.py — InScript v2.12.0  Electron Bridge
================================================================
A lightweight JSON-RPC HTTP server that the InScript Studio Electron
shell calls to drive the runtime.

Start from CLI:
  inscript --studio-bridge [--bridge-port 8765]

Or from Python:
  from studio_bridge import StudioBridge
  bridge = StudioBridge(port=8765)
  bridge.start()   # non-blocking daemon thread
  bridge.stop()

JSON-RPC protocol (HTTP POST to /rpc):
  Request:  { "method": "run",       "id": 1, "params": {"file": "src/main.ins"} }
  Response: { "result": "ok",        "id": 1 }
  Error:    { "error": "...",        "id": 1 }

Methods
───────
  run          — execute a .ins file; returns {"status": "ok"|"error", "output": [...]}
  stop         — stop a running interpreter
  hot_reload   — trigger hot reload on a file
  scene_list   — return all scene/node declarations in project
  inspect      — full project introspection (scenes, nodes, fns, assets)
  eval         — evaluate an InScript expression in live env
  ping         — health check; returns {"pong": true}
  version      — returns {"version": "2.12.0"}
"""

from __future__ import annotations
import json, threading, sys, os, io
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional

DEFAULT_PORT = 8765


class _RpcHandler(BaseHTTPRequestHandler):
    """HTTP handler — all requests are POST to /rpc."""

    def log_message(self, fmt, *args):
        pass  # suppress default access log

    def do_POST(self):
        if self.path != "/rpc":
            self._reply(404, {"error": "Not found — POST to /rpc"})
            return
        try:
            length  = int(self.headers.get("Content-Length", 0))
            body    = self.rfile.read(length)
            request = json.loads(body)
        except Exception as e:
            self._reply(400, {"error": f"Bad JSON: {e}", "id": None})
            return

        req_id  = request.get("id")
        method  = request.get("method", "")
        params  = request.get("params", {})

        try:
            result = self.server._bridge._dispatch(method, params)
            self._reply(200, {"result": result, "id": req_id})
        except Exception as e:
            self._reply(200, {"error": str(e), "id": req_id})

    def _reply(self, status: int, data: dict):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


class StudioBridge:
    """
    Lightweight JSON-RPC bridge between the InScript runtime and
    the Electron Studio shell.
    """
    def __init__(self, port: int = DEFAULT_PORT):
        self._port    = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._interp  = None   # live Interpreter (created on first run)
        self._lock    = threading.Lock()
        self._running = False

    # ── lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> "StudioBridge":
        """Start the HTTP server in a daemon thread. Non-blocking."""
        self._server = HTTPServer(("localhost", self._port), _RpcHandler)
        self._server._bridge = self
        self._running = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        """Shut down the HTTP server."""
        self._running = False
        if self._server:
            self._server.shutdown()

    @property
    def port(self) -> int:
        return self._port

    @property
    def url(self) -> str:
        return f"http://localhost:{self._port}/rpc"

    # ── RPC dispatch ──────────────────────────────────────────────────────────

    def _dispatch(self, method: str, params: dict) -> Any:
        handlers = {
            "ping":        self._rpc_ping,
            "version":     self._rpc_version,
            "run":         self._rpc_run,
            "stop":        self._rpc_stop,
            "hot_reload":  self._rpc_hot_reload,
            "scene_list":  self._rpc_scene_list,
            "inspect":     self._rpc_inspect,
            "eval":        self._rpc_eval,
        }
        handler = handlers.get(method)
        if handler is None:
            raise ValueError(f"Unknown method '{method}'. Available: {sorted(handlers)}")
        return handler(params)

    # ── RPC handlers ──────────────────────────────────────────────────────────

    def _rpc_ping(self, _params: dict) -> dict:
        return {"pong": True, "port": self._port}

    def _rpc_version(self, _params: dict) -> dict:
        from inscript import VERSION
        return {"version": VERSION, "bridge": "1.0"}

    def _rpc_run(self, params: dict) -> dict:
        """Run a .ins file and return captured output + errors."""
        file_path = params.get("file", "")
        if not file_path:
            raise ValueError("'file' parameter required")
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, encoding="utf-8") as f:
            source = f.read()

        output_lines: list = []
        errors: list = []

        # Redirect stdout
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            from interpreter import Interpreter
            from errors import InScriptError
            with self._lock:
                self._interp = Interpreter()
            self._interp.execute(source)
            output_lines = sys.stdout.getvalue().splitlines()
        except Exception as e:
            from errors import InScriptError
            if isinstance(e, InScriptError):
                errors.append(e.to_dict())
            else:
                errors.append({"type": "error", "code": "E0000",
                                "class": type(e).__name__, "message": str(e),
                                "line": 0, "col": 0})
            output_lines = sys.stdout.getvalue().splitlines()
        finally:
            sys.stdout = old_stdout

        return {
            "status": "error" if errors else "ok",
            "output": output_lines,
            "errors": errors,
        }

    def _rpc_stop(self, _params: dict) -> dict:
        with self._lock:
            self._interp = None
        return {"stopped": True}

    def _rpc_hot_reload(self, params: dict) -> dict:
        """Trigger a hot reload on a running file."""
        file_path = params.get("file", "")
        if not file_path:
            raise ValueError("'file' parameter required")
        with self._lock:
            if self._interp is None:
                raise RuntimeError("No running interpreter — call 'run' first")
            from hot_reload import HotReloader
            reloader = HotReloader(file_path, self._interp)
            result   = reloader.tick()
        return {
            "changed":    result.changed,
            "success":    result.success,
            "patched":    result.patched,
            "restored":   len(result.restored),
            "errors":     result.errors,
            "elapsed_ms": result.elapsed_ms,
        }

    def _rpc_scene_list(self, params: dict) -> dict:
        """Return all scene and node declarations in a project directory."""
        project_dir = params.get("dir", ".")
        from inscript_studio_api import project_inspect
        data = project_inspect(project_dir)
        return {"scenes": data["scenes"], "nodes": data["nodes"]}

    def _rpc_inspect(self, params: dict) -> dict:
        """Full project introspection."""
        project_dir = params.get("dir", ".")
        from inscript_studio_api import project_inspect
        return project_inspect(project_dir)

    def _rpc_eval(self, params: dict) -> dict:
        """Evaluate an InScript expression in the live interpreter environment."""
        expr = params.get("expr", "")
        if not expr:
            raise ValueError("'expr' parameter required")
        with self._lock:
            if self._interp is None:
                raise RuntimeError("No running interpreter — call 'run' first")
            result = self._interp.execute(expr)
        return {"result": result, "type": type(result).__name__}

    def __repr__(self):
        status = "running" if self._running else "stopped"
        return f"<StudioBridge port={self._port} {status}>"
