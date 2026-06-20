# v3.9.6.27 — Physics: continuous collision detection (.py tests)
# Run: python v3.9.6.27/test_ccd.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from physics_engine import PhysicsWorld, Shape, BODY_DYNAMIC, BODY_STATIC

PASS, FAIL = 0, 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  {chr(0x2705)} {name}")
        PASS += 1
    else:
        print(f"  {chr(0x274C)} {name}  {detail}")
        FAIL += 1

# ── 1. CCD prevents tunneling through thin wall ─────
try:
    w = PhysicsWorld(0, 0)
    bullet = w.create_body(Shape.rect(4, 4), BODY_DYNAMIC, 1.0, "bullet", 50, 50)
    bullet.ccd_enabled = True
    wall = w.create_body(Shape.rect(4, 100), BODY_STATIC, 0.0, "wall", 105, 50)
    bullet.vx = 10000  # 160px/frame — would tunnel through 4px wall
    w.step(0.016)
    # With CCD, bullet should stop at or before wall
    check("CCD prevents bullet tunneling", bullet.x <= 105)
except Exception as e:
    check("CCD tunneling prevention", False, str(e))

# ── 2. Without CCD, bullet tunnels ──────────────────
try:
    w = PhysicsWorld(0, 0)
    bullet = w.create_body(Shape.rect(4, 4), BODY_DYNAMIC, 1.0, "bullet", 50, 50)
    bullet.ccd_enabled = False
    wall = w.create_body(Shape.rect(4, 100), BODY_STATIC, 0.0, "wall", 105, 50)
    bullet.vx = 10000  # 160px per frame, enough to cross wall at x=105
    w.step(0.016)
    # Without CCD, bullet passes through wall
    check("Without CCD, bullet tunnels through wall", bullet.x >= 200)
except Exception as e:
    check("No CCD tunneling", False, str(e))

# ── 3. CCD stops at wall surface with thin body ─────
try:
    w = PhysicsWorld(0, 0)
    bullet = w.create_body(Shape.rect(4, 4), BODY_DYNAMIC, 1.0, "bullet", 50, 50)
    bullet.ccd_enabled = True
    wall = w.create_body(Shape.rect(4, 100), BODY_STATIC, 0.0, "wall", 105, 50)
    bullet.vx = 10000
    w.step(0.016)
    # Bullet should be stopped at or near the wall surface
    # Wall left edge = 105 - 2 = 103, bullet right edge = bullet.x + 2
    check("CCD body stops near wall surface", bullet.x <= 103)
except Exception as e:
    check("CCD wall surface stop", False, str(e))

# ── 4. CCD with vertical movement ──────────────────
try:
    w = PhysicsWorld(0, 0)
    bullet = w.create_body(Shape.rect(4, 4), BODY_DYNAMIC, 1.0, "bullet", 50, 50)
    bullet.ccd_enabled = True
    wall = w.create_body(Shape.rect(100, 4), BODY_STATIC, 0.0, "wall", 50, 200)
    bullet.vy = 5000
    w.step(0.016)
    check("CCD prevents vertical tunneling", bullet.y < 200 and bullet.y > 50)
except Exception as e:
    check("CCD vertical", False, str(e))

# ── 5. CCD with multiple static bodies ──────────────
try:
    w = PhysicsWorld(0, 0)
    bullet = w.create_body(Shape.rect(4, 4), BODY_DYNAMIC, 1.0, "bullet", 50, 50)
    bullet.ccd_enabled = True
    w.create_body(Shape.rect(4, 100), BODY_STATIC, 0.0, "wall1", 105, 50)
    w.create_body(Shape.rect(4, 100), BODY_STATIC, 0.0, "wall2", 300, 50)
    bullet.vx = 10000
    w.step(0.016)
    # Bullet should stop at first wall
    check("CCD stops at first wall of multiple", bullet.x <= 105)
except Exception as e:
    check("CCD multiple walls", False, str(e))

# ── 6. CCD does not affect slow-moving bodies ──────
try:
    w = PhysicsWorld(0, 500)
    body = w.create_body(Shape.rect(20, 20), BODY_DYNAMIC, 1.0, "slow", 100, 50)
    body.ccd_enabled = True
    floor = w.create_body(Shape.rect(200, 20), BODY_STATIC, 0.0, "floor", 100, 100)
    for _ in range(100):
        w.step(0.016)
    # Body should sit on floor normally (small residual vy from collision resolution)
    check("CCD slow body lands on floor normally", body.y <= 82 and abs(body.vy) < 5)
except Exception as e:
    check("CCD slow body", False, str(e))

# ── 7. Body.ccd_enabled attribute exists ────────────
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(10, 10), BODY_DYNAMIC, 1.0, "test", 0, 0)
    check("Body has ccd_enabled attr", hasattr(b, "ccd_enabled"))
    check("ccd_enabled defaults to False", b.ccd_enabled is False)
    b.ccd_enabled = True
    check("ccd_enabled can be set to True", b.ccd_enabled is True)
except Exception as e:
    check("ccd_enabled attr", False, str(e))

# ── 8. CCD with circle body (AABB approximation) ────
try:
    w = PhysicsWorld(0, 0)
    bullet = w.create_body(Shape.circle(4), BODY_DYNAMIC, 1.0, "bullet", 50, 50)
    bullet.ccd_enabled = True
    wall = w.create_body(Shape.rect(4, 100), BODY_STATIC, 0.0, "wall", 105, 50)
    bullet.vx = 10000
    w.step(0.016)
    # Circle CCD uses AABB approximation
    check("CCD with circle body prevents tunneling", bullet.x <= 105)
except Exception as e:
    check("CCD circle body", False, str(e))

# ── 9. CCD with very high speed diagonal ────────────
try:
    w = PhysicsWorld(0, 0)
    bullet = w.create_body(Shape.rect(4, 4), BODY_DYNAMIC, 1.0, "bullet", 50, 50)
    bullet.ccd_enabled = True
    wall = w.create_body(Shape.rect(4, 100), BODY_STATIC, 0.0, "wall", 105, 50)
    bullet.vx = 10000
    bullet.vy = 5000
    w.step(0.016)
    check("CCD with diagonal speed stops at wall", bullet.x <= 105)
except Exception as e:
    check("CCD diagonal", False, str(e))

# ── RESULTS ──────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.27 — Physics: CCD")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
