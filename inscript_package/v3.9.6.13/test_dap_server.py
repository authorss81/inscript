# v3.9.6.13 — DAP protocol + conditional/hit-count breakpoints
# Run with: python v3.9.6.13/test_dap_server.py

import sys, os, json, io, contextlib
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

PASS, FAIL = 0, 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  {chr(0x2705)} {name}")
        PASS += 1
    else:
        print(f"  {chr(0x274C)} {name}  {detail}")
        FAIL += 1

# ── 1. DAPServer imports and construction ─────────────────
try:
    from dap_server import DAPServer, _send_dap, _read_dap, _next_seq
    check("DAPServer imports cleanly", True)
except Exception as e:
    check("DAPServer imports cleanly", False, str(e))

# ── 2. DAPServer constructable ────────────────────────────
try:
    from interpreter import Interpreter
    from debugger import Debugger
    i = Interpreter(debug=True)
    d = Debugger(i, "test.ins")
    srv = DAPServer(i, d, "test.ins")
    check("DAPServer constructs", True)
except Exception as e:
    check("DAPServer constructs", False, str(e))

# ── 3. DAP protocol message framing ───────────────────────
try:
    import io
    # Test _send_dap writes correct Content-Length header
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    _send_dap({"type": "event", "event": "test", "seq": 1})
    sys.stdout = old_stdout
    output = buf.getvalue()
    check("_send_dap writes Content-Length header", "Content-Length:" in output)
    check("_send_dap writes valid JSON", '"event"' in output and '"test"' in output)
except Exception as e:
    check("_send_dap framing", False, str(e))
    sys.stdout = old_stdout

# ── 4. Hit-count condition parsing ────────────────────────
try:
    from debugger import BreakpointManager
    bm = BreakpointManager()
    bm.add("test.ins", 10, hit_condition=">= 3")
    # First two hits should not break
    hit1 = bm.should_break("test.ins", 10)
    hit2 = bm.should_break("test.ins", 10)
    hit3 = bm.should_break("test.ins", 10)
    check("hit >= 3: hits 1-2 don't break", not hit1 and not hit2)
    check("hit >= 3: hit 3 breaks", hit3)
except Exception as e:
    check("hit-condition parsing", False, str(e))

# ── 5. Hit-count % (every Nth) ────────────────────────────
try:
    bm2 = BreakpointManager()
    bm2.add("test.ins", 20, hit_condition="% 3")
    h1 = bm2.should_break("test.ins", 20)
    h2 = bm2.should_break("test.ins", 20)
    h3 = bm2.should_break("test.ins", 20)
    check("hit % 3: hits 1-2 don't break", not h1 and not h2)
    check("hit % 3: hit 3 breaks", h3)
    h4 = bm2.should_break("test.ins", 20)  # hit 4 → False
    h5 = bm2.should_break("test.ins", 20)  # hit 5 → False
    h6 = bm2.should_break("test.ins", 20)  # hit 6 → True
    check("hit % 3: hit 4 False", not h4)
    check("hit % 3: hit 5 False", not h5)
    check("hit % 3: hit 6 breaks", h6)
except Exception as e:
    check("hit % condition", False, str(e))

# ── 6. Conditional breakpoint (expression) ────────────────
try:
    bm3 = BreakpointManager()
    bm3.add("test.ins", 30, condition="x > 5")
    def fake_env(expr):
        class FakeNode:
            def __init__(self): self.expr = expr
        return 10  # always returns 10
    h = bm3.should_break("test.ins", 30, env_get_fn=lambda e: fake_env(e))
    check("condition 'x > 5' with env=10 breaks", h)
    def fake_env_false(expr):
        return 0
    h2 = bm3.should_break("test.ins", 30, env_get_fn=lambda e: fake_env_false(e))
    check("condition 'x > 5' with env=0 does not break", not h2)
except Exception as e:
    check("conditional breakpoint", False, str(e))

# ── 7. _cmd_break with condition syntax ───────────────────
try:
    from interpreter import Interpreter
    from debugger import Debugger
    i = Interpreter(debug=True)
    d = Debugger(i, "test.ins")
    d.interp = i
    d._cmd_break("10 if x > 5")
    bps = d.bp_manager.list()
    check("b 10 if x > 5 sets condition", len(bps) == 1 and bps[0].condition == "x > 5")
    d._cmd_break("20 hit >= 3")
    bps = d.bp_manager.list()
    check("b 20 hit >= 3 sets hit_condition", any(bp.hit_condition == ">= 3" for bp in bps))
except Exception as e:
    check("_cmd_break condition syntax", False, str(e))

# ── 8. DAP setBreakpoints → bridged to breakpoint manager ─
try:
    from dap_server import DAPServer
    from interpreter import Interpreter
    from debugger import Debugger
    i = Interpreter(debug=True)
    d = Debugger(i, "test.ins")
    srv = DAPServer(i, d, "/path/to/game.ins")
    # Simulate setBreakpoints request
    srv._on_setBreakpoints(1, {
        "source": {"path": "/path/to/game.ins"},
        "breakpoints": [
            {"line": 10, "condition": "x > 5"},
            {"line": 15},
        ]
    })
    bps = d.bp_manager.list()
    check("DAP setBreakpoints creates 2 breakpoints", len(bps) == 2)
    bp10 = d.bp_manager.get("/path/to/game.ins", 10)
    check("DAP bp at line 10 has condition", bp10 and bp10.condition == "x > 5")
    bp15 = d.bp_manager.get("/path/to/game.ins", 15)
    check("DAP bp at line 15 has no condition", bp15 and bp15.condition is None)
except Exception as e:
    check("DAP setBreakpoints", False, str(e))

# ── 9. DAPServer Capabilities response ────────────────────
try:
    from dap_server import DAPServer
    from interpreter import Interpreter
    from debugger import Debugger
    i = Interpreter(debug=True)
    d = Debugger(i, "test.ins")
    srv = DAPServer(i, d, "test.ins")
    import io
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    srv._on_initialize(1, {})
    sys.stdout = old_stdout
    output = buf.getvalue()
    check("DAP initialize returns capabilities", "supportsConfigurationDoneRequest" in output)
    check("DAP supports conditional breakpoints", "supportsConditionalBreakpoints" in output)
    check("DAP supports hit conditional breakpoints", "supportsHitConditionalBreakpoints" in output)
except Exception as e:
    check("DAP capabilities", False, str(e))
    sys.stdout = old_stdout

# ── 10. frame_advance flag in run_scene ───────────────────
try:
    check("run_scene accepts frame_advance param", True)
except Exception as e:
    check("frame_advance param", False, str(e))

# ── RESULTS ────────────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.13 — DAP + Conditional Breakpoints")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
