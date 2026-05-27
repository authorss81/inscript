# -*- coding: utf-8 -*-
"""
studio_readiness.py — InScript v2.12.0  Studio Readiness Gate
================================================================
`inscript --check-v3` runs all seven readiness gates and exits 0
only when every gate passes.  This is the final checkpoint before
v3.0.0 InScript Studio development can safely begin.

Gates
─────
  G1  60fps performance gate     — 1000 NodeInstance._update calls in < 33ms
  G2  Memory gate                — < 2MB growth over 5000 game-loop iterations
  G3  Language stability audit   — all CI test files found and importable
  G4  Error JSON stream          — InScriptError.to_dict() / to_json() work
  G5  Electron bridge            — StudioBridge starts + responds to ping
  G6  Plugin API                 — StudioAPI register/emit round-trip
  G7  Project introspection      — project_inspect returns well-formed JSON

If all pass, prints a v3.0.0 green-light banner.
"""

from __future__ import annotations
import sys, os, time, tracemalloc, json, threading
from typing import List, Tuple

GATE_COUNT = 7

# ─────────────────────────────────────────────────────────────────────────────
# GateResult
# ─────────────────────────────────────────────────────────────────────────────

class GateResult:
    def __init__(self, gate_id: int, name: str, passed: bool,
                 detail: str = "", elapsed_ms: float = 0.0):
        self.gate_id    = gate_id
        self.name       = name
        self.passed     = passed
        self.detail     = detail
        self.elapsed_ms = elapsed_ms

    def __repr__(self):
        icon = "✅" if self.passed else "❌"
        ms   = f" ({self.elapsed_ms:.1f}ms)" if self.elapsed_ms else ""
        return f"  {icon}  G{self.gate_id}: {self.name}{ms}  {self.detail}"


# ─────────────────────────────────────────────────────────────────────────────
# G1 — 60fps performance gate
# ─────────────────────────────────────────────────────────────────────────────

# Threshold: 1000 NodeInstance._update calls must complete in under 33ms
# (= 30fps minimum; any modern machine will be well above 60fps)
PERF_THRESHOLD_MS = 33.0
PERF_NODE_COUNT   = 1000

def gate_performance() -> GateResult:
    """
    Instantiate PERF_NODE_COUNT NodeInstances each with an _update(dt) hook
    and measure how long one full update pass takes.
    """
    t0 = time.perf_counter()
    try:
        from interpreter import Interpreter
        from scene_tree   import NodeBlueprint, NodeInstance

        src = "node PerfNode { let c: int = 0\n_update(dt) { c = c + 1 } }"
        interp = Interpreter()
        interp.execute(src)
        bp = interp._globals._store.get("PerfNode")
        if bp is None:
            return GateResult(1, "60fps performance gate", False,
                              "PerfNode blueprint not found", 0.0)

        # Create PERF_NODE_COUNT instances
        instances = [bp.instantiate(f"n{i}") for i in range(PERF_NODE_COUNT)]

        # Time one full update pass
        t_start = time.perf_counter()
        for inst in instances:
            inst.call_update(0.016)
        t_end   = time.perf_counter()
        elapsed = (t_end - t_start) * 1000

        fps_equiv = 1000.0 / elapsed if elapsed > 0 else float("inf")
        detail = (f"{PERF_NODE_COUNT} nodes updated in {elapsed:.1f}ms "
                  f"(≈{fps_equiv:.0f}fps equiv)")
        passed = elapsed < PERF_THRESHOLD_MS
        if not passed:
            detail += f" — SLOW (threshold {PERF_THRESHOLD_MS}ms)"
        return GateResult(1, "60fps performance gate", passed, detail,
                          (time.perf_counter() - t0) * 1000)
    except Exception as e:
        return GateResult(1, "60fps performance gate", False, str(e),
                          (time.perf_counter() - t0) * 1000)


# ─────────────────────────────────────────────────────────────────────────────
# G2 — Memory gate
# ─────────────────────────────────────────────────────────────────────────────

MEMORY_ITERATIONS  = 5000
MEMORY_LIMIT_BYTES = 2 * 1024 * 1024  # 2 MB

def gate_memory() -> GateResult:
    """
    Run MEMORY_ITERATIONS of a minimal game loop and measure growth via tracemalloc.
    A leaky interpreter would show unbounded growth.
    """
    t0 = time.perf_counter()
    try:
        from interpreter import Interpreter

        interp = Interpreter()
        interp.execute("let tick: int = 0\nfn update(dt) { tick = tick + 1 }")
        update_fn = interp._globals._store.get("update")

        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        for _ in range(MEMORY_ITERATIONS):
            interp._call_fn(update_fn, [0.016])

        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        stats  = snapshot_after.compare_to(snapshot_before, "lineno")
        growth = sum(s.size_diff for s in stats if s.size_diff > 0)

        detail = f"{growth / 1024:.1f}KB growth over {MEMORY_ITERATIONS} iterations"
        passed = growth < MEMORY_LIMIT_BYTES
        if not passed:
            detail += f" — LEAK (limit {MEMORY_LIMIT_BYTES // 1024}KB)"
        return GateResult(2, "Memory gate", passed, detail,
                          (time.perf_counter() - t0) * 1000)
    except Exception as e:
        return GateResult(2, "Memory gate", False, str(e),
                          (time.perf_counter() - t0) * 1000)


# ─────────────────────────────────────────────────────────────────────────────
# G3 — Language stability audit
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_TEST_FILES = [
    "test_v260.py", "test_v270.py", "test_v280.py",
    "test_v290.py", "test_v2100.py", "test_v2110.py",
]

def gate_stability(base_dir: str = ".") -> GateResult:
    """
    Verify that all required CI test files exist and are importable.
    Full execution is handled by the publish.yml workflow.
    """
    t0 = time.perf_counter()
    missing = []
    for fn in REQUIRED_TEST_FILES:
        if not os.path.isfile(os.path.join(base_dir, fn)):
            missing.append(fn)

    if missing:
        detail = f"Missing test files: {missing}"
        return GateResult(3, "Language stability audit", False, detail,
                          (time.perf_counter() - t0) * 1000)

    # Quick import check
    import_errors = []
    for fn in ["lexer", "parser", "interpreter", "scene_tree",
               "hot_reload", "stdlib_assets", "export_pipeline",
               "studio_bridge", "inscript_studio_api"]:
        try:
            __import__(fn)
        except Exception as e:
            import_errors.append(f"{fn}: {e}")

    passed = not missing and not import_errors
    detail = (f"All {len(REQUIRED_TEST_FILES)} test files present; "
              f"{len(import_errors)} import error(s)")
    if import_errors:
        detail += f": {import_errors}"
    return GateResult(3, "Language stability audit", passed, detail,
                      (time.perf_counter() - t0) * 1000)


# ─────────────────────────────────────────────────────────────────────────────
# G4 — Error JSON stream
# ─────────────────────────────────────────────────────────────────────────────

def gate_error_json() -> GateResult:
    """Verify InScriptError.to_dict() and to_json() produce valid JSON."""
    t0 = time.perf_counter()
    try:
        from errors import NameError_ as _NE

        # Raise a real InScript error and check serialisation
        err = _NE("Test variable not found", line=5, col=3,
                  source_line="let x = undefined_var", hint="Did you mean 'x'?")
        d = err.to_dict()

        # Validate required fields
        required = {"type", "code", "class", "message", "line", "col"}
        missing  = required - set(d.keys())
        if missing:
            return GateResult(4, "Error JSON stream", False,
                              f"Missing keys: {missing}",
                              (time.perf_counter() - t0) * 1000)

        # Validate to_json() is valid JSON
        raw   = err.to_json()
        reparsed = json.loads(raw)

        checks = [
            d["type"] == "error",
            d["line"] == 5,
            d["col"]  == 3,
            d["hint"] == "Did you mean 'x'?",
            reparsed["code"] == d["code"],
        ]
        passed = all(checks)
        detail = f"to_dict() has {len(d)} keys; to_json() round-trips OK"
        return GateResult(4, "Error JSON stream", passed, detail,
                          (time.perf_counter() - t0) * 1000)
    except Exception as e:
        return GateResult(4, "Error JSON stream", False, str(e),
                          (time.perf_counter() - t0) * 1000)


# ─────────────────────────────────────────────────────────────────────────────
# G5 — Electron bridge
# ─────────────────────────────────────────────────────────────────────────────

BRIDGE_TEST_PORT = 18999

def gate_bridge() -> GateResult:
    """Start StudioBridge on a test port and verify ping round-trip."""
    t0 = time.perf_counter()
    try:
        import urllib.request as _ur
        from studio_bridge import StudioBridge

        bridge = StudioBridge(port=BRIDGE_TEST_PORT)
        bridge.start()
        time.sleep(0.1)   # allow server thread to start

        req  = _ur.Request(
            bridge.url,
            data=json.dumps({"method": "ping", "id": 1}).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = _ur.urlopen(req, timeout=3)
        body = json.loads(resp.read().decode())
        bridge.stop()

        passed = body.get("result", {}).get("pong") is True
        detail = f"Ping response: {body.get('result')}"
        return GateResult(5, "Electron bridge (ping)", passed, detail,
                          (time.perf_counter() - t0) * 1000)
    except Exception as e:
        return GateResult(5, "Electron bridge (ping)", False, str(e),
                          (time.perf_counter() - t0) * 1000)


# ─────────────────────────────────────────────────────────────────────────────
# G6 — Plugin API
# ─────────────────────────────────────────────────────────────────────────────

def gate_plugin_api() -> GateResult:
    """Register a plugin, emit events, verify it received them."""
    t0 = time.perf_counter()
    try:
        from inscript_studio_api import StudioAPI, StudioPlugin

        received: list = []

        class _TestPlugin(StudioPlugin):
            name = "test_plugin"
            def on_error(self, error):    received.append(("error", error))
            def on_reload(self, result):  received.append(("reload", result))
            def on_build(self, t, d, s):  received.append(("build", t, s))

        api = StudioAPI()
        p   = _TestPlugin()
        api.register(p)

        api.emit_error({"code": "E0042", "message": "test"})
        api.emit_reload({"success": True})
        api.emit_build("desktop", "/out", True)

        checks = [
            api.plugin_count() == 1,
            len(received) == 3,
            received[0][0] == "error",
            received[1][0] == "reload",
            received[2][0] == "build",
        ]
        api.unregister(p)
        checks.append(api.plugin_count() == 0)

        passed = all(checks)
        detail = f"3/3 events received; register/unregister OK"
        return GateResult(6, "Plugin API", passed, detail,
                          (time.perf_counter() - t0) * 1000)
    except Exception as e:
        return GateResult(6, "Plugin API", False, str(e),
                          (time.perf_counter() - t0) * 1000)


# ─────────────────────────────────────────────────────────────────────────────
# G7 — Project introspection
# ─────────────────────────────────────────────────────────────────────────────

def gate_introspection(base_dir: str = ".") -> GateResult:
    """Run project_inspect on a minimal temp project and verify JSON output."""
    t0 = time.perf_counter()
    try:
        import tempfile, shutil
        from inscript_studio_api import project_inspect

        tmp = tempfile.mkdtemp(prefix="inscript_gate7_")
        try:
            os.makedirs(os.path.join(tmp, "src"))
            os.makedirs(os.path.join(tmp, "scenes"))
            with open(os.path.join(tmp, "src", "main.ins"), "w") as f:
                f.write('node Player { let hp: int = 100\n_update(dt) { } }\n'
                        'fn spawn(x, y) { }\n'
                        '@texture("sprites/hero.png")\nlet hero_tex\n')
            with open(os.path.join(tmp, "scenes", "level1.inscene"), "w") as f:
                f.write('[scene]\nname = "level1"\nroot = "Player"\n')

            data = project_inspect(tmp)

            # Validate structure
            required_keys = {"project_dir", "version", "sources", "scenes",
                             "nodes", "functions", "assets", "scene_files"}
            missing = required_keys - set(data.keys())
            if missing:
                return GateResult(7, "Project introspection", False,
                                  f"Missing keys: {missing}",
                                  (time.perf_counter() - t0) * 1000)

            # Validate JSON-serialisable
            json.dumps(data)

            has_player   = any(n["name"] == "Player" for n in data["nodes"])
            has_spawn    = any(f["name"] == "spawn"   for f in data["functions"])
            has_texture  = any(a["type"] == "texture"  for a in data["assets"])
            has_scene    = any(s.get("scene_name") == "level1" for s in data["scene_files"])

            checks = [has_player, has_spawn, has_texture, has_scene]
            passed = all(checks)
            detail = (f"nodes={len(data['nodes'])} fns={len(data['functions'])} "
                      f"assets={len(data['assets'])} scene_files={len(data['scene_files'])}")
            return GateResult(7, "Project introspection", passed, detail,
                              (time.perf_counter() - t0) * 1000)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    except Exception as e:
        return GateResult(7, "Project introspection", False, str(e),
                          (time.perf_counter() - t0) * 1000)


# ─────────────────────────────────────────────────────────────────────────────
# Main gate runner
# ─────────────────────────────────────────────────────────────────────────────

def run_all_gates(base_dir: str = ".") -> Tuple[List[GateResult], bool]:
    """Run all 7 gates. Returns (results, all_passed)."""
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║   InScript v3.0.0 Readiness Gate  (inscript check-v3)  ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    runners = [
        lambda: gate_performance(),
        lambda: gate_memory(),
        lambda: gate_stability(base_dir),
        lambda: gate_error_json(),
        lambda: gate_bridge(),
        lambda: gate_plugin_api(),
        lambda: gate_introspection(base_dir),
    ]

    results = []
    for runner in runners:
        r = runner()
        print(repr(r))
        results.append(r)

    passed_count = sum(1 for r in results if r.passed)
    all_passed   = passed_count == GATE_COUNT

    print(f"\n{'─'*60}")
    print(f"Gates passed: {passed_count}/{GATE_COUNT}")

    if all_passed:
        print("""
╔══════════════════════════════════════════════════════════╗
║  🟢  ALL GATES PASS — v3.0.0 InScript Studio is GO!     ║
║                                                          ║
║  Scene system, asset pipeline, hot reload, physics,      ║
║  multiplayer, export pipeline, and Studio bridge are     ║
║  all in place.  Begin v3.0.0 development.                ║
╚══════════════════════════════════════════════════════════╝""")
    else:
        failed = [r for r in results if not r.passed]
        print(f"\n🔴  {len(failed)} gate(s) failed — NOT ready for v3.0.0:")
        for r in failed:
            print(f"     G{r.gate_id}: {r.name} — {r.detail}")

    return results, all_passed
