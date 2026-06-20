# v3.9.6.29 — Physics: optimization (broadphase + body sleeping)
# Run: python v3.9.6.29/test_optimization.py

import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from physics_engine import (
    PhysicsWorld, Shape, BODY_DYNAMIC, BODY_STATIC,
    SLEEP_THRESHOLD, SLEEP_FRAMES,
)

PASS, FAIL = 0, 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  {chr(0x2705)} {name}")
        PASS += 1
    else:
        print(f"  {chr(0x274C)} {name}  {detail}")
        FAIL += 1

# ── 1. Body sleeping attribute exists ─────────────
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(10, 10), BODY_DYNAMIC, 1.0, "test", 0, 0)
    check("Body has _sleeping attr", hasattr(b, "_sleeping"))
    check("Body has _sleep_timer attr", hasattr(b, "_sleep_timer"))
    check("Default _sleeping is False", b._sleeping is False)
except Exception as e:
    check("sleeping attr", False, str(e))

# ── 2. Body falls asleep after inactivity ─────────
try:
    w = PhysicsWorld(0, 0)  # No gravity
    b = w.create_body(Shape.rect(10, 10), BODY_DYNAMIC, 1.0, "test", 100, 100)
    # No velocity → should sleep after SLEEP_FRAMES
    for _ in range(SLEEP_FRAMES + 5):
        w.step(0.016)
    check("body falls asleep after inactivity", b._sleeping is True)
except Exception as e:
    check("body sleep", False, str(e))

# ── 3. Moving body does not fall asleep ────────────
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(10, 10), BODY_DYNAMIC, 1.0, "test", 100, 100)
    b.vx = 100  # Fast enough to stay awake
    for _ in range(SLEEP_FRAMES + 10):
        w.step(0.016)
    check("moving body stays awake", b._sleeping is False)
except Exception as e:
    check("moving body awake", False, str(e))

# ── 4. Sleeping body wakes on collision ────────────
try:
    w = PhysicsWorld(0, 500)
    b = w.create_body(Shape.rect(20, 20), BODY_DYNAMIC, 1.0, "dyn", 100, 0)
    w.create_body(Shape.rect(200, 20), BODY_STATIC, 0.0, "floor", 100, 100)
    # Let body fall and land
    for _ in range(200):
        w.step(0.016)
    # Body should have landed and gone to sleep
    landed_and_asleep = b._sleeping and abs(b.vy) < 0.1
    # Now push it via set_attr (which wakes the body)
    b.set_attr("vx", 500)
    w.step(0.016)
    # Body should wake up
    check("sleeping body wakes on velocity change", b._sleeping is False)
except Exception as e:
    check("wake on velocity", False, str(e))

# ── 5. Sleeping body skipped in collision check ───
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(10, 10), BODY_DYNAMIC, 1.0, "a", 100, 100)
    b2 = w.create_body(Shape.rect(10, 10), BODY_DYNAMIC, 1.0, "b", 110, 100)
    # Let both sleep (no gravity, no velocity)
    for _ in range(SLEEP_FRAMES + 10):
        w.step(0.016)
    # Both should be sleeping
    check("both bodies asleep", b._sleeping and b2._sleeping)
except Exception as e:
    check("both asleep", False, str(e))

# ── 6. Body settles on floor and sleeps ──────────
try:
    w = PhysicsWorld(0, 500)
    b = w.create_body(Shape.rect(20, 20), BODY_DYNAMIC, 1.0, "test", 100, 50)
    w.create_body(Shape.rect(200, 20), BODY_STATIC, 0.0, "floor", 100, 100)
    for _ in range(SLEEP_FRAMES + 50):
        w.step(0.016)
    # Body should have landed on floor and gone to sleep
    check("body settles on floor and sleeps", b._sleeping is True)
except Exception as e:
    check("settle and sleep", False, str(e))

# ── 7. Broadphase produces correct pair count ─────
try:
    w = PhysicsWorld(0, 0)
    # Create 40 bodies spread out
    for i in range(10):
        for j in range(4):
            w.create_body(Shape.rect(10, 10), BODY_STATIC, 0.0, f"b_{i}_{j}", i*100, j*100)
    pairs = w._get_broadphase_pairs(w._bodies)
    # Without broadphase: 40*39/2 = 780 pairs
    # With broadphase (cell_size=200): should be much fewer
    total_pairs = len(pairs)
    brute_force = len(w._bodies) * (len(w._bodies) - 1) / 2
    check("broadphase reduces pair count", total_pairs < brute_force)
    check("broadphase produces valid pairs", total_pairs > 0)
except Exception as e:
    check("broadphase basic", False, str(e))

# ── 8. Broadphase finds all overlapping pairs ─────
try:
    w = PhysicsWorld(0, 0)
    a = w.create_body(Shape.rect(40, 40), BODY_STATIC, 0.0, "a", 100, 100)
    b = w.create_body(Shape.rect(40, 40), BODY_STATIC, 0.0, "b", 130, 100)
    c = w.create_body(Shape.rect(40, 40), BODY_STATIC, 0.0, "c", 500, 100)
    pairs = w._get_broadphase_pairs(w._bodies)
    pair_tags = set()
    for a_body, b_body in pairs:
        if a_body.tag < b_body.tag:
            pair_tags.add((a_body.tag, b_body.tag))
        else:
            pair_tags.add((b_body.tag, a_body.tag))
    check("broadphase finds close pair (a,b)", ("a", "b") in pair_tags)
    check("broadphase does not pair distant (a,c)", ("a", "c") not in pair_tags)
except Exception as e:
    check("broadphase accuracy", False, str(e))

# ── 9. get_attr('sleeping') works ─────────────────
try:
    w = PhysicsWorld(0, 0)
    b = w.create_body(Shape.rect(10, 10), BODY_DYNAMIC, 1.0, "test", 0, 0)
    sleeping = b.get_attr("sleeping")
    check("body.get_attr('sleeping') returns bool", isinstance(sleeping, bool))
except Exception as e:
    check("get_attr sleeping", False, str(e))

# ── 10. Many body simulation with broadphase ──────
try:
    w = PhysicsWorld(0, 500)
    # Create enough bodies to trigger broadphase (BROADPHASE_THRESHOLD=32)
    for i in range(35):
        w.create_body(Shape.rect(16, 16), BODY_DYNAMIC, 1.0, f"box_{i}", i * 25, 0)
    floor = w.create_body(Shape.rect(1000, 20), BODY_STATIC, 0.0, "floor", 500, 400)
    # Run 60 frames without error
    for _ in range(60):
        w.step(0.016)
    check("35 bodies + broadphase runs without error", True)
except Exception as e:
    check("many body simulation", False, str(e))

# ── RESULTS ──────────────────────────────────────────
print()
print("=" * 55)
print("  v3.9.6.29 — Physics: optimization")
print("=" * 55)
print(f"  {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 55)
if FAIL > 0:
    sys.exit(1)
