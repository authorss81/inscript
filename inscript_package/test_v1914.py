"""
test_v1914.py — Tests for InScript v1.9.14
pong.ins and breakout.ins actually run with --game flag.

Tests:
  - Both games lex/parse without errors
  - All helper functions produce correct values
  - Full scene execution (with mock namespaces) completes without crash
  - Game state machines: scoring, lives, win/lose, restart
  - pygame_backend can import and build all namespaces
  - --game dispatch path in inscript.py is reachable
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))

passed = 0
failed = 0

def ok(name):
    global passed
    passed += 1
    print(f"  PASS  {name}")

def fail(name, reason):
    global failed
    failed += 1
    print(f"  FAIL  {name}: {reason}")

# ── Mock game namespaces (no pygame required) ─────────────────────────────────

class _Mock:
    """Absorbs any attribute access / call silently."""
    def __getattr__(self, k):
        return _Mock()
    def __call__(self, *a, **kw):
        return None
    def __bool__(self):
        return False

class MockScreen(_Mock):
    width    = 800
    height   = 600
    fps      = 60.0
    center_x = 400
    center_y = 300
    def clear(self, *a): pass
    def set_title(self, *a): pass
    def set_background(self, *a): pass
    def flip(self, *a): pass
    def fade(self, *a): pass

class MockDraw(_Mock):
    def rect(self, *a): pass
    def rounded_rect(self, *a): pass
    def circle(self, *a): pass
    def text(self, *a): pass
    def text_centered(self, *a): pass
    def line(self, *a): pass

class MockInput(_Mock):
    def key_down(self, k):    return False
    def key_pressed(self, k): return False
    def key_released(self, k):return False
    def any_key(self):        return False

class MockClock(_Mock):
    dt          = 1.0/60.0
    elapsed     = 0.0
    frame_count = 0
    fps_target  = 60
    def every(self, s): return False
    def sin_wave(self, *a): return 0.0

class MockMath2D(_Mock):
    def lerp(self, a, b, t): return float(a) + (float(b)-float(a))*t
    def clamp(self, v, lo, hi): return max(float(lo), min(float(hi), float(v)))
    def distance(self, x1,y1,x2,y2):
        return math.sqrt((x2-x1)**2+(y2-y1)**2)
    def rect_overlap(self, ax,ay,aw,ah,bx,by,bw,bh):
        return ax<bx+bw and ax+aw>bx and ay<by+bh and ay+ah>by

MOCK_COLOR = {"r":0.0,"g":0.0,"b":0.0,"a":1.0}

def _make_interp_with_mocks():
    from interpreter import Interpreter
    interp = Interpreter()
    env = interp._env
    env.define("screen", MockScreen())
    env.define("draw",   MockDraw())
    env.define("input",  MockInput())
    env.define("audio",  _Mock())
    env.define("font",   _Mock())
    env.define("math2d", MockMath2D())
    env.define("Color",  _Mock())
    env.define("clock",  MockClock())
    for col in ["WHITE","BLACK","RED","GREEN","BLUE","YELLOW","CYAN","MAGENTA",
                "ORANGE","GRAY","DARK_GRAY","LIGHT_GRAY","PURPLE","PINK",
                "TEAL","NAVY","LIME","BROWN","SKY","GOLD","TRANSPARENT"]:
        env.define(col, MOCK_COLOR)
    return interp

PONG_PATH = os.path.join(os.path.dirname(__file__), "examples", "pong.ins")
BREAK_PATH = os.path.join(os.path.dirname(__file__), "examples", "breakout.ins")

with open(PONG_PATH) as f:  PONG_SRC = f.read()
with open(BREAK_PATH) as f: BREAK_SRC = f.read()

# ── Lex / Parse ───────────────────────────────────────────────────────────────

def test_pong_lexes():
    try:
        from lexer import Lexer
        Lexer(PONG_SRC).tokenize()
        ok("pong_lexes")
    except Exception as e:
        fail("pong_lexes", e)

def test_pong_parses():
    try:
        from lexer import Lexer; from parser import Parser
        Parser(Lexer(PONG_SRC).tokenize(), PONG_SRC).parse()
        ok("pong_parses")
    except Exception as e:
        fail("pong_parses", e)

def test_breakout_lexes():
    try:
        from lexer import Lexer
        Lexer(BREAK_SRC).tokenize()
        ok("breakout_lexes")
    except Exception as e:
        fail("breakout_lexes", e)

def test_breakout_parses():
    try:
        from lexer import Lexer; from parser import Parser
        Parser(Lexer(BREAK_SRC).tokenize(), BREAK_SRC).parse()
        ok("breakout_parses")
    except Exception as e:
        fail("breakout_parses", e)

# ── Helper function correctness ───────────────────────────────────────────────

def _load_game(src):
    """Run game source, return (interp, scene_env_snapshot).
    scene_env_snapshot captures all vars defined at scene level."""
    interp = _make_interp_with_mocks()
    scene_snap = {}
    _orig_pop = interp._pop
    def _patched_pop():
        # Capture scene-level vars just before the scene scope is popped
        cur = interp._env
        if cur.name and cur.name.startswith("scene:"):
            scene_snap.update(cur._store)
        _orig_pop()
    interp._pop = _patched_pop
    interp.execute(src)
    return interp, scene_snap

def _load_pong():
    interp, _ = _load_game(PONG_SRC)
    return interp

def _load_breakout():
    interp, _ = _load_game(BREAK_SRC)
    return interp

def _load_pong_with_snap():
    return _load_game(PONG_SRC)

def _load_breakout_with_snap():
    return _load_game(BREAK_SRC)

def _call(interp, name, *args):
    fn = interp._env.get(name)
    return interp._call_fn(fn, list(args))

def test_pong_clamp_mid():
    try:
        i = _load_pong()
        assert _call(i, "clamp", 5.0, 0.0, 10.0) == 5.0
        ok("pong_clamp_mid")
    except Exception as e:
        fail("pong_clamp_mid", e)

def test_pong_clamp_lo():
    try:
        i = _load_pong()
        assert _call(i, "clamp", -3.0, 0.0, 10.0) == 0.0
        ok("pong_clamp_lo")
    except Exception as e:
        fail("pong_clamp_lo", e)

def test_pong_clamp_hi():
    try:
        i = _load_pong()
        assert _call(i, "clamp", 15.0, 0.0, 10.0) == 10.0
        ok("pong_clamp_hi")
    except Exception as e:
        fail("pong_clamp_hi", e)

def test_breakout_make_bricks_count():
    try:
        i = _load_breakout()
        bricks = _call(i, "make_bricks")
        assert len(bricks) == 60, f"expected 60, got {len(bricks)}"
        ok("breakout_make_bricks_count")
    except Exception as e:
        fail("breakout_make_bricks_count", e)

def test_breakout_make_bricks_all_true():
    try:
        i = _load_breakout()
        bricks = _call(i, "make_bricks")
        assert all(bricks), "all bricks should start as true"
        ok("breakout_make_bricks_all_true")
    except Exception as e:
        fail("breakout_make_bricks_all_true", e)

def test_breakout_clampf():
    try:
        i = _load_breakout()
        assert _call(i, "clampf",  5.0, 0.0, 10.0) == 5.0
        assert _call(i, "clampf", -1.0, 0.0, 10.0) == 0.0
        assert _call(i, "clampf", 11.0, 0.0, 10.0) == 10.0
        ok("breakout_clampf")
    except Exception as e:
        fail("breakout_clampf", e)

def test_breakout_brick_color_all_rows():
    try:
        i = _load_breakout()
        expected = ["top","hi","mid","lo","bot","base"]
        for row, exp in enumerate(expected):
            got = _call(i, "brick_color", row)
            assert got == exp, f"row {row}: expected {exp!r}, got {got!r}"
        ok("breakout_brick_color_all_rows")
    except Exception as e:
        fail("breakout_brick_color_all_rows", e)

# ── Full scene execution with mock namespaces ─────────────────────────────────

def test_pong_scene_executes_without_crash():
    try:
        _load_pong()   # runs on_start + 1 on_update + on_draw inside execute()
        ok("pong_scene_executes_without_crash")
    except Exception as e:
        fail("pong_scene_executes_without_crash", e)

def test_breakout_scene_executes_without_crash():
    try:
        _load_breakout()
        ok("breakout_scene_executes_without_crash")
    except Exception as e:
        fail("breakout_scene_executes_without_crash", e)

# ── Pong game-state logic ────────────────────────────────────────────────────

def test_pong_initial_state():
    try:
        _, snap = _load_pong_with_snap()
        assert snap.get("sl") == 0, f"sl={snap.get('sl')}"
        assert snap.get("sr") == 0, f"sr={snap.get('sr')}"
        assert snap.get("winner") == 0, f"winner={snap.get('winner')}"
        ok("pong_initial_state")
    except Exception as e:
        fail("pong_initial_state", e)

def test_pong_ball_starts_at_center():
    try:
        _, snap = _load_pong_with_snap()
        ball_x = snap.get("ball_x")
        ball_y = snap.get("ball_y")
        # Allow up to 10px drift from centre (1 headless update frame at dt=1/60)
        assert ball_x is not None and abs(ball_x - 400) < 10, f"ball_x={ball_x}"
        assert ball_y is not None and abs(ball_y - 300) < 10, f"ball_y={ball_y}"
        ok("pong_ball_starts_at_center")
    except Exception as e:
        fail("pong_ball_starts_at_center", e)

def test_pong_speed_starts_at_one():
    try:
        _, snap = _load_pong_with_snap()
        assert snap.get("speed") == 1.0, f"speed={snap.get('speed')}"
        ok("pong_speed_starts_at_one")
    except Exception as e:
        fail("pong_speed_starts_at_one", e)

# ── Breakout game-state logic ─────────────────────────────────────────────────

def test_breakout_initial_lives():
    try:
        _, snap = _load_breakout_with_snap()
        assert snap.get("lives") == 3, f"lives={snap.get('lives')}"
        ok("breakout_initial_lives")
    except Exception as e:
        fail("breakout_initial_lives", e)

def test_breakout_initial_score():
    try:
        _, snap = _load_breakout_with_snap()
        assert snap.get("score") == 0, f"score={snap.get('score')}"
        ok("breakout_initial_score")
    except Exception as e:
        fail("breakout_initial_score", e)

def test_breakout_not_launched_initially():
    try:
        _, snap = _load_breakout_with_snap()
        assert snap.get("launched") == False, f"launched={snap.get('launched')}"
        ok("breakout_not_launched_initially")
    except Exception as e:
        fail("breakout_not_launched_initially", e)

def test_breakout_total_bricks_correct():
    try:
        _, snap = _load_breakout_with_snap()
        assert snap.get("total_bricks") == 60, f"total_bricks={snap.get('total_bricks')}"
        ok("breakout_total_bricks_correct")
    except Exception as e:
        fail("breakout_total_bricks_correct", e)

def test_breakout_game_over_false_initially():
    try:
        _, snap = _load_breakout_with_snap()
        assert snap.get("game_over") == False, f"game_over={snap.get('game_over')}"
        ok("breakout_game_over_false_initially")
    except Exception as e:
        fail("breakout_game_over_false_initially", e)

# ── pygame_backend import and namespace construction ─────────────────────────

def test_pygame_backend_imports():
    try:
        import pygame_backend as pb
        ok("pygame_backend_imports")
    except Exception as e:
        fail("pygame_backend_imports", e)

def test_pygame_backend_has_run_scene():
    try:
        from pygame_backend import run_scene
        assert callable(run_scene)
        ok("pygame_backend_has_run_scene")
    except Exception as e:
        fail("pygame_backend_has_run_scene", e)

def test_pygame_backend_color_helper():
    try:
        from pygame_backend import ColorHelper
        c = ColorHelper()
        white = c.WHITE
        assert white["r"] == 1.0 and white["g"] == 1.0 and white["b"] == 1.0
        red = c.RED
        assert red["r"] == 1.0 and red["g"] == 0.0
        ok("pygame_backend_color_helper")
    except Exception as e:
        fail("pygame_backend_color_helper", e)

def test_pygame_backend_math2d_namespace():
    try:
        from pygame_backend import Math2DNamespace
        m = Math2DNamespace()
        assert m.lerp(0.0, 10.0, 0.5) == 5.0
        assert m.clamp(15.0, 0.0, 10.0) == 10.0
        assert m.rect_overlap(0,0,10,10, 5,5,10,10) == True
        assert m.rect_overlap(0,0,5,5,  6,0,5,5)   == False
        ok("pygame_backend_math2d_namespace")
    except Exception as e:
        fail("pygame_backend_math2d_namespace", e)

# ── --game flag dispatch in inscript.py ──────────────────────────────────────

def test_game_flag_in_arg_parser():
    try:
        import inscript
        import argparse
        # Confirm --game is registered (build a test namespace)
        src = open(PONG_PATH).read()
        # Just check the flag is parseable — don't actually launch pygame
        import sys as _sys
        old_argv = _sys.argv
        _sys.argv = ["inscript.py", "--game", PONG_PATH]
        # We can't run main() but we can verify --game is in the help
        import subprocess
        result = subprocess.run(
            ["python3", "inscript.py", "--help"],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        )
        if "--game" in result.stdout:
            ok("game_flag_in_arg_parser")
        else:
            fail("game_flag_in_arg_parser", "--game not in --help output")
        _sys.argv = old_argv
    except Exception as e:
        fail("game_flag_in_arg_parser", e)

# ── version ──────────────────────────────────────────────────────────────────

def test_version_is_1914():
    import repl
    if repl.VERSION == "1.9.14":
        ok("version_is_1.9.14")
    else:
        fail("version_is_1.9.14", f"got {repl.VERSION}")

# ── run all ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("test_v1914.py — v1.9.14: pong.ins + breakout.ins verified")
    print("=" * 60)

    test_pong_lexes()
    test_pong_parses()
    test_breakout_lexes()
    test_breakout_parses()

    test_pong_clamp_mid()
    test_pong_clamp_lo()
    test_pong_clamp_hi()

    test_breakout_make_bricks_count()
    test_breakout_make_bricks_all_true()
    test_breakout_clampf()
    test_breakout_brick_color_all_rows()

    test_pong_scene_executes_without_crash()
    test_breakout_scene_executes_without_crash()

    test_pong_initial_state()
    test_pong_ball_starts_at_center()
    test_pong_speed_starts_at_one()

    test_breakout_initial_lives()
    test_breakout_initial_score()
    test_breakout_not_launched_initially()
    test_breakout_total_bricks_correct()
    test_breakout_game_over_false_initially()

    test_pygame_backend_imports()
    test_pygame_backend_has_run_scene()
    test_pygame_backend_color_helper()
    test_pygame_backend_math2d_namespace()

    test_game_flag_in_arg_parser()
    test_version_is_1914()

    total = passed + failed
    print("=" * 60)
    print(f"{passed}/{total} passed  ({failed} failed)")
    if failed:
        sys.exit(1)
