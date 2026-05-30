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


# ═══════════════════════════════════════════════════════════════════════════
# v2.13.0 — StudioBridge v2 additions
# ═══════════════════════════════════════════════════════════════════════════

import subprocess as _subprocess


class _GameProcess:
    """
    Manages a single game process launched by `start_game`.
    The game runs in a subprocess; the bridge stays responsive.
    """
    def __init__(self, file_path: str, python_exe: str = None):
        self.file_path  = file_path
        self._python    = python_exe or sys.executable
        self._proc:     Optional[_subprocess.Popen] = None
        self._output:   list = []   # captured stdout lines
        self._errors:   list = []
        self._thread:   Optional[threading.Thread] = None
        self._running   = False

    def start(self) -> bool:
        if self._proc is not None and self._proc.poll() is None:
            return False  # already running
        inscript_path = os.path.join(os.path.dirname(__file__), "inscript.py")
        self._proc = _subprocess.Popen(
            [self._python, inscript_path, self.file_path],
            stdout=_subprocess.PIPE,
            stderr=_subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._running = True
        self._output  = []
        self._errors  = []
        self._thread  = threading.Thread(target=self._read_output, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> bool:
        if self._proc is None:
            return False
        self._running = False
        try:
            self._proc.terminate()
            self._proc.wait(timeout=2)
        except Exception:
            try: self._proc.kill()
            except Exception: pass
        self._proc = None
        return True

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def get_output(self, since: int = 0) -> list:
        return self._output[since:]

    def _read_output(self):
        try:
            for line in self._proc.stdout:
                self._output.append(line.rstrip("\n"))
        except Exception:
            pass
        self._running = False

    def __repr__(self):
        status = "running" if self.is_running() else "stopped"
        return f"<GameProcess '{os.path.basename(self.file_path)}' {status}>"


def _extend_bridge(bridge_cls):
    """
    Monkey-patch v2.13.0 methods onto StudioBridge.
    Called once at module load.
    """
    # ── Game process management ───────────────────────────────────────────────
    bridge_cls._game_process = None

    def _rpc_start_game(self, params: dict) -> dict:
        """
        Launch a .ins game as a subprocess (non-blocking).
        Bridge stays responsive during game execution.
        """
        file_path = params.get("file", "")
        if not file_path or not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        with self._lock:
            if self._game_process and self._game_process.is_running():
                self._game_process.stop()
            self._game_process = _GameProcess(file_path)
            started = self._game_process.start()
        return {"started": started, "file": file_path,
                "pid": self._game_process._proc.pid if started else None}

    def _rpc_stop_game(self, params: dict) -> dict:
        with self._lock:
            if self._game_process is None:
                return {"stopped": False, "reason": "no game running"}
            stopped = self._game_process.stop()
            self._game_process = None
        return {"stopped": stopped}

    def _rpc_game_status(self, params: dict) -> dict:
        with self._lock:
            if self._game_process is None:
                return {"running": False, "output_lines": 0}
            since = int(params.get("since", 0))
            return {
                "running":      self._game_process.is_running(),
                "output":       self._game_process.get_output(since),
                "output_lines": len(self._game_process._output),
                "file":         self._game_process.file_path,
            }

    # ── Live scene editing ────────────────────────────────────────────────────

    def _rpc_set_node_prop(self, params: dict) -> dict:
        """
        Set a property on a live NodeInstance.
        Requires a running interpreter (from `run` RPC, not `start_game`).
        """
        node_name = params.get("node", "")
        prop      = params.get("prop", "")
        value     = params.get("value")
        if not node_name or not prop:
            raise ValueError("'node' and 'prop' are required")
        with self._lock:
            if self._interp is None:
                raise RuntimeError("No live interpreter — use 'run' first")
            from scene_tree import SceneManager, NodeInstance
            # Try to find node in global env first
            try:
                obj = self._interp._globals._store.get(node_name)
            except Exception:
                obj = None
            if isinstance(obj, NodeInstance):
                obj[prop] = value
                return {"node": node_name, "prop": prop, "value": value, "ok": True}
            # Fall back: set in global env
            try:
                self._interp._globals.set(prop, value)
                return {"prop": prop, "value": value, "ok": True, "global": True}
            except Exception as e:
                raise RuntimeError(f"Cannot set {node_name}.{prop}: {e}")

    def _rpc_add_node(self, params: dict) -> dict:
        """
        Instantiate a NodeBlueprint and add it to the live scene.
        """
        blueprint_name = params.get("blueprint", "")
        node_name      = params.get("name", blueprint_name)
        parent_name    = params.get("parent", None)
        if not blueprint_name:
            raise ValueError("'blueprint' required")
        with self._lock:
            if self._interp is None:
                raise RuntimeError("No live interpreter")
            from scene_tree import NodeBlueprint, NodeInstance
            bp = self._interp._globals._store.get(blueprint_name)
            if not isinstance(bp, NodeBlueprint):
                raise KeyError(f"No NodeBlueprint '{blueprint_name}' in env")
            inst = bp.instantiate(node_name)
            if parent_name:
                parent = self._interp._globals._store.get(parent_name)
                if isinstance(parent, NodeInstance):
                    parent.add_child(inst)
            self._interp._globals.define(node_name, inst)
        return {"added": node_name, "blueprint": blueprint_name, "ok": True}

    def _rpc_remove_node(self, params: dict) -> dict:
        """Remove a NodeInstance from its parent in the live scene."""
        node_name = params.get("node", "")
        if not node_name:
            raise ValueError("'node' required")
        with self._lock:
            if self._interp is None:
                raise RuntimeError("No live interpreter")
            from scene_tree import NodeInstance
            inst = self._interp._globals._store.get(node_name)
            if not isinstance(inst, NodeInstance):
                raise KeyError(f"No NodeInstance '{node_name}' in env")
            if inst._parent:
                inst._parent.remove_child(inst)
        return {"removed": node_name, "ok": True}

    def _rpc_get_live_scene(self, params: dict) -> dict:
        """
        Introspect the live interpreter's scene state.
        Returns all NodeInstance names, their props, and parent relationships.
        """
        with self._lock:
            if self._interp is None:
                return {"nodes": [], "count": 0, "reason": "no live interpreter"}
            from scene_tree import NodeInstance
            nodes = []
            for name, val in self._interp._globals._store.items():
                if isinstance(val, NodeInstance):
                    nodes.append({
                        "name":      name,
                        "blueprint": val.blueprint.name,
                        "parent":    val._parent.name if val._parent else None,
                        "children":  [c.name for c in val.get_children()],
                        "props":     {k: str(v) for k, v in val._props.items()
                                      if not callable(v)},
                    })
        return {"nodes": nodes, "count": len(nodes)}

    # ── DAP debugger wiring ───────────────────────────────────────────────────

    def _rpc_set_breakpoints(self, params: dict) -> dict:
        """Set breakpoints for the next debug run."""
        lines     = [int(l) for l in params.get("lines", [])]
        file_path = params.get("file", "")
        with self._lock:
            if not hasattr(self, '_debug_interp') or self._debug_interp is None:
                # Lazy-create debug interpreter on first breakpoint set
                self._debug_interp = None
                self._debug_bp_lines = lines
                self._debug_bp_file  = file_path
            else:
                self._debug_interp.set_breakpoints(lines)
        return {"breakpoints": lines, "file": file_path}

    def _rpc_debug_run(self, params: dict) -> dict:
        """Run a file with debug hooks enabled."""
        file_path = params.get("file", "")
        if not file_path or not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        from inscript_dap import DebugInterpreter
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
        with self._lock:
            self._debug_interp = DebugInterpreter(source, file_path)
            bp_lines = getattr(self, '_debug_bp_lines', [])
            self._debug_interp.set_breakpoints(bp_lines)
            self._debug_interp.launch()
        return {"debug_started": True, "file": file_path}

    def _rpc_debug_continue(self, _params: dict) -> dict:
        with self._lock:
            di = getattr(self, '_debug_interp', None)
            if di is None: raise RuntimeError("No debug session")
            di.do_continue()
        return {"continued": True}

    def _rpc_debug_step(self, params: dict) -> dict:
        mode = params.get("mode", "over")   # over | into | out
        with self._lock:
            di = getattr(self, '_debug_interp', None)
            if di is None: raise RuntimeError("No debug session")
            if mode == "into":   di.do_step_into()
            elif mode == "out":  di.do_step_out()
            else:                di.do_step_over()
        return {"stepped": mode}

    def _rpc_debug_vars(self, _params: dict) -> dict:
        with self._lock:
            di = getattr(self, '_debug_interp', None)
            if di is None: raise RuntimeError("No debug session")
            return {
                "locals":  {v["name"]: v["value"] for v in di.get_variables("locals")},
                "globals": {v["name"]: v["value"] for v in di.get_variables("globals")},
                "line":    di._current_line,
                "frames":  di.get_stack_frames(),
                "paused":  di._stopped,
            }

    def _rpc_debug_stop(self, _params: dict) -> dict:
        with self._lock:
            di = getattr(self, '_debug_interp', None)
            if di:
                try: di.do_continue()   # unblock any waiting thread
                except Exception: pass
                self._debug_interp = None
        return {"stopped": True}

    # ── Input emulation ───────────────────────────────────────────────────────

    def _rpc_emulate_input(self, params: dict) -> dict:
        """
        Inject headless input state so Studio preview can simulate key/mouse events
        without a pygame window.
        """
        from stdlib_game import _INPUT_MANAGER_INSTANCE
        mgr = _INPUT_MANAGER_INSTANCE()
        if mgr is None:
            return {"ok": False, "reason": "input manager not initialised"}
        keys    = params.get("keys", {})    # {"space": true, "left": false}
        mouse   = params.get("mouse", None) # {"x": 100, "y": 200}
        buttons = params.get("buttons", {}) # {0: true}
        for k, v in keys.items():
            mgr.emulate_key(k, bool(v))
        if mouse:
            mgr.emulate_mouse(float(mouse.get("x", 0)),
                              float(mouse.get("y", 0)),
                              {int(k): bool(v) for k, v in buttons.items()})
        return {"ok": True, "emulated_keys": list(keys.keys())}

    # ── Patch dispatch table ──────────────────────────────────────────────────

    _NEW_METHODS = {
        "start_game":      _rpc_start_game,
        "stop_game":       _rpc_stop_game,
        "game_status":     _rpc_game_status,
        "set_node_prop":   _rpc_set_node_prop,
        "add_node":        _rpc_add_node,
        "remove_node":     _rpc_remove_node,
        "get_live_scene":  _rpc_get_live_scene,
        "set_breakpoints": _rpc_set_breakpoints,
        "debug_run":       _rpc_debug_run,
        "debug_continue":  _rpc_debug_continue,
        "debug_step":      _rpc_debug_step,
        "debug_vars":      _rpc_debug_vars,
        "debug_stop":      _rpc_debug_stop,
        "emulate_input":   _rpc_emulate_input,
    }

    # Patch _dispatch to include new methods
    _orig_dispatch = bridge_cls._dispatch

    def _new_dispatch(self, method, params):
        if method in _NEW_METHODS:
            return _NEW_METHODS[method](self, params)
        return _orig_dispatch(self, method, params)

    bridge_cls._dispatch = _new_dispatch


# Apply patches
_extend_bridge(StudioBridge)


# ─────────────────────────────────────────────────────────────────────────────
# Input manager instance getter (for emulation)
# ─────────────────────────────────────────────────────────────────────────────

def _INPUT_MANAGER_INSTANCE():
    """Return the global _InputManager if initialised, else None."""
    try:
        from stdlib_game import _INPUT_MANAGER_INSTANCE as _imi
        return _imi
    except ImportError:
        return None
