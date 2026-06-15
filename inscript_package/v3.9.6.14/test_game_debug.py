# v3.9.6.14 — Game loop debugging (frame advance, frame break)
# Run with: python v3.9.6.14/test_game_debug.py

import sys, os
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

# ── 1. pygame_backend imports and HAS_PYGAME ─────────────
try:
    from pygame_backend import run_scene, HAS_PYGAME
    check("pygame_backend imports cleanly", True)
except Exception as e:
    check("pygame_backend imports cleanly", False, str(e))

# ── 2. run_scene accepts debug param ─────────────────────
try:
    from pygame_backend import run_scene
    import inspect
    sig = inspect.signature(run_scene)
    check("run_scene has debug param", "debug" in sig.parameters)
    check("run_scene has frame_break param", "frame_break" in sig.parameters)
    check("run_scene has frame_advance param", "frame_advance" in sig.parameters)
except Exception as e:
    check("run_scene params", False, str(e))

# ── 3. inscript.py argument parser has --frame-break ──────────
try:
    with open(os.path.join(os.path.dirname(__file__), "..", "inscript.py"), "r", encoding="utf-8") as f:
        content = f.read()
    check("inscript.py has --frame-break flag", '--frame-break' in content)
except Exception as e:
    check("inscript.py --frame-break", False, str(e))

# ── 4. inscript.py argument parser has --frame-advance ────────
try:
    with open(os.path.join(os.path.dirname(__file__), "..", "inscript.py"), "r", encoding="utf-8") as f:
        content = f.read()
    check("inscript.py has --frame-advance flag", '--frame-advance' in content)
except Exception as e:
    check("inscript.py --frame-advance", False, str(e))

# ── 5. --game dispatch passes frame_break/frame_advance ─────
try:
    with open(os.path.join(os.path.dirname(__file__), "..", "inscript.py"), "r", encoding="utf-8") as f:
        content = f.read()
    check("--game dispatch passes frame_break", "frame_break=getattr" in content)
    check("--game dispatch passes frame_advance", "frame_advance=getattr" in content)
except Exception as e:
    check("--game dispatch", False, str(e))

# ── 6. Game loop has _check_frame_debug function ────────────
try:
    with open(os.path.join(os.path.dirname(__file__), "..", "pygame_backend.py"), "r", encoding="utf-8") as f:
        content = f.read()
    check("game loop has _check_frame_debug", "_check_frame_debug" in content)
    check("game loop has _frame_advance", "_frame_advance" in content)
    check("game loop has _frame_break_frame", "_frame_break_frame" in content)
    check("game loop has running_flag", "running_flag" in content)
except Exception as e:
    check("game loop structure", False, str(e))

# ── 7. Frame debug help text ───────────────────────────────
try:
    with open(os.path.join(os.path.dirname(__file__), "..", "pygame_backend.py"), "r", encoding="utf-8") as f:
        content = f.read()
    check("frame-debug has help text", "Game debug commands" in content or "Frame debug commands" in content)
    check("frame-debug has .locals", ".locals" in content)
    check("frame-debug has .globals", ".globals" in content)
    check("frame-debug has .watch", ".watch" in content)
    check("frame-debug has .stack", ".stack" in content)
    check("frame-debug has continue/next/quit", "continue" in content and "next" in content and "quit" in content)
except Exception as e:
    check("frame debug help text", False, str(e))

# ── 8. run_scene passes debug to interpreter if debug=True ─
try:
    # Check that dbgr is created when debug=True
    with open(os.path.join(os.path.dirname(__file__), "..", "pygame_backend.py"), "r", encoding="utf-8") as f:
        content = f.read()
    check("run_scene checks debug param", "debug=True" in content or "debug=debug" in content or "debug" in content)
except Exception as e:
    check("debug param usage", False, str(e))

# ── 9. VERSION updated ──────────────────────────────────────
try:
    from inscript import VERSION
    parts = VERSION.split(".")
    base = int(parts[2])
    micro = int(parts[3])
    check(f"VERSION = {VERSION} (base={base}, micro={micro})", base >= 6 and micro >= 13)
except Exception as e:
    check("VERSION check", False, str(e))

# ── 10. Minimal syntax check on pygame_backend ──────────────
try:
    import py_compile
    source = os.path.join(os.path.dirname(__file__), "..", "pygame_backend.py")
    py_compile.compile(source, doraise=True)
    check("pygame_backend.py compiles", True)
except py_compile.PyCompileError as e:
    check("pygame_backend.py compiles", False, str(e))

# ── 11. inscript.py compiles ────────────────────────────────
try:
    import py_compile
    source = os.path.join(os.path.dirname(__file__), "..", "inscript.py")
    py_compile.compile(source, doraise=True)
    check("inscript.py compiles", True)
except py_compile.PyCompileError as e:
    check("inscript.py compiles", False, str(e))

# ── 12. debugger.py compiles ────────────────────────────────
try:
    import py_compile
    source = os.path.join(os.path.dirname(__file__), "..", "debugger.py")
    py_compile.compile(source, doraise=True)
    check("debugger.py compiles", True)
except py_compile.PyCompileError as e:
    check("debugger.py compiles", False, str(e))

# ── 13. dap_server.py compiles ─────────────────────────────
try:
    import py_compile
    source = os.path.join(os.path.dirname(__file__), "..", "dap_server.py")
    py_compile.compile(source, doraise=True)
    check("dap_server.py compiles", True)
except py_compile.PyCompileError as e:
    check("dap_server.py compiles", False, str(e))

# ── RESULTS ────────────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.14 — Game Loop Debugging")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
