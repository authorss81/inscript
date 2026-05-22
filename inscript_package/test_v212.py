"""
test_v212.py — InScript v2.1.2
===========================================
Tests for the three new packages: vector2, tween, collision.
All tests run the package source through the InScript interpreter.
"""
import sys, os, math, subprocess
sys.path.insert(0, os.path.dirname(__file__))

import repl as repl_mod
from interpreter import Interpreter
from parser import parse

PASS = 0; FAIL = 0

def ok(name):
    global PASS
    PASS += 1
    print(f"  PASS  {name}")

def fail(name, msg=""):
    global FAIL
    FAIL += 1
    print(f"  FAIL  {name}: {msg}")

def run(src: str):
    """Run InScript source and return the Interpreter (env accessible)."""
    interp = Interpreter()
    ast = parse(src)
    interp.run(ast)
    return interp

def pkg(name: str) -> str:
    """Load a package .ins file from the packages directory."""
    path = os.path.join(os.path.dirname(__file__),
                        "inscript-packages", "packages", name, f"{name}.ins")
    with open(path, encoding="utf-8") as f:
        return f.read()

def check_close(test_name: str, got, expected, tol=1e-6):
    if abs(got - expected) <= tol:
        ok(test_name)
    else:
        fail(test_name, f"want ≈{expected}, got {got}")

def check_eq(test_name: str, got, expected):
    if got == expected:
        ok(test_name)
    else:
        fail(test_name, f"want {expected!r}, got {got!r}")

# ─────────────────────────────────────────────────────────────────────────────
# vector2 package
# ─────────────────────────────────────────────────────────────────────────────

V2 = pkg("vector2")

def test_vec2_len():
    interp = run(V2 + "\nlet r = vec2_len(3.0, 4.0)")
    check_close("vec2_len", interp._env.get("r"), 5.0)

def test_vec2_len_sq():
    interp = run(V2 + "\nlet r = vec2_len_sq(3.0, 4.0)")
    check_close("vec2_len_sq", interp._env.get("r"), 25.0)

def test_vec2_norm():
    interp = run(V2 + "\nlet r = vec2_norm(3.0, 4.0)")
    d = interp._env.get("r")
    check_close("vec2_norm_x", d["x"], 0.6)
    check_close("vec2_norm_y", d["y"], 0.8)

def test_vec2_norm_zero():
    interp = run(V2 + "\nlet r = vec2_norm(0.0, 0.0)")
    d = interp._env.get("r")
    check_close("vec2_norm_zero_x", d["x"], 0.0)
    check_close("vec2_norm_zero_y", d["y"], 0.0)

def test_vec2_dot():
    interp = run(V2 + "\nlet r = vec2_dot(1.0, 0.0, 0.0, 1.0)")
    check_close("vec2_dot_perpendicular", interp._env.get("r"), 0.0)

def test_vec2_dot_parallel():
    interp = run(V2 + "\nlet r = vec2_dot(2.0, 0.0, 3.0, 0.0)")
    check_close("vec2_dot_parallel", interp._env.get("r"), 6.0)

def test_vec2_cross():
    interp = run(V2 + "\nlet r = vec2_cross(1.0, 0.0, 0.0, 1.0)")
    check_close("vec2_cross", interp._env.get("r"), 1.0)

def test_vec2_add():
    interp = run(V2 + "\nlet r = vec2_add(1.0, 2.0, 3.0, 4.0)")
    d = interp._env.get("r")
    check_close("vec2_add_x", d["x"], 4.0)
    check_close("vec2_add_y", d["y"], 6.0)

def test_vec2_sub():
    interp = run(V2 + "\nlet r = vec2_sub(5.0, 3.0, 2.0, 1.0)")
    d = interp._env.get("r")
    check_close("vec2_sub_x", d["x"], 3.0)
    check_close("vec2_sub_y", d["y"], 2.0)

def test_vec2_scale():
    interp = run(V2 + "\nlet r = vec2_scale(2.0, 3.0, 4.0)")
    d = interp._env.get("r")
    check_close("vec2_scale_x", d["x"], 8.0)
    check_close("vec2_scale_y", d["y"], 12.0)

def test_vec2_dist():
    interp = run(V2 + "\nlet r = vec2_dist(0.0, 0.0, 3.0, 4.0)")
    check_close("vec2_dist", interp._env.get("r"), 5.0)

def test_vec2_dist_sq():
    interp = run(V2 + "\nlet r = vec2_dist_sq(0.0, 0.0, 3.0, 4.0)")
    check_close("vec2_dist_sq", interp._env.get("r"), 25.0)

def test_vec2_lerp():
    interp = run(V2 + "\nlet r = vec2_lerp(0.0, 0.0, 10.0, 20.0, 0.5)")
    d = interp._env.get("r")
    check_close("vec2_lerp_x", d["x"], 5.0)
    check_close("vec2_lerp_y", d["y"], 10.0)

def test_vec2_rotate_90():
    interp = run(V2 + f"\nlet r = vec2_rotate(1.0, 0.0, {math.pi / 2})")
    d = interp._env.get("r")
    check_close("vec2_rotate_x", d["x"], 0.0, tol=1e-5)
    check_close("vec2_rotate_y", d["y"], 1.0, tol=1e-5)

def test_vec2_angle():
    interp = run(V2 + "\nlet r = vec2_angle(1.0, 0.0)")
    check_close("vec2_angle_right", interp._env.get("r"), 0.0)

def test_vec2_reflect():
    # Reflect (1, -1) off normal (0, 1) → should give (1, 1)
    interp = run(V2 + "\nlet r = vec2_reflect(1.0, -1.0, 0.0, 1.0)")
    d = interp._env.get("r")
    check_close("vec2_reflect_x", d["x"], 1.0)
    check_close("vec2_reflect_y", d["y"], 1.0)

def test_vec2_project():
    # Project (3, 4) onto (1, 0) → should give (3, 0)
    interp = run(V2 + "\nlet r = vec2_project(3.0, 4.0, 1.0, 0.0)")
    d = interp._env.get("r")
    check_close("vec2_project_x", d["x"], 3.0)
    check_close("vec2_project_y", d["y"], 0.0)

# ─────────────────────────────────────────────────────────────────────────────
# tween package
# ─────────────────────────────────────────────────────────────────────────────

TW = pkg("tween")

def test_tween_tick_advance():
    interp = run(TW + "\nlet r = tween_tick(0.2, 1.0, 0.3)")
    check_close("tween_tick_advance", interp._env.get("r"), 0.5)

def test_tween_tick_clamp():
    interp = run(TW + "\nlet r = tween_tick(0.9, 1.0, 0.5)")
    check_close("tween_tick_clamp", interp._env.get("r"), 1.0)

def test_tween_done_false():
    interp = run(TW + "\nlet r = tween_done(0.5, 1.0)")
    check_eq("tween_done_false", interp._env.get("r"), False)

def test_tween_done_true():
    interp = run(TW + "\nlet r = tween_done(1.0, 1.0)")
    check_eq("tween_done_true", interp._env.get("r"), True)

def test_tween_t_mid():
    interp = run(TW + "\nlet r = tween_t(0.5, 2.0)")
    check_close("tween_t_mid", interp._env.get("r"), 0.25)

def test_tween_t_zero_duration():
    interp = run(TW + "\nlet r = tween_t(0.0, 0.0)")
    check_close("tween_t_zero_duration", interp._env.get("r"), 1.0)

def test_tween_float():
    interp = run(TW + "\nlet r = tween_float(0.0, 100.0, 0.25)")
    check_close("tween_float", interp._env.get("r"), 25.0)

def test_tween_int():
    interp = run(TW + "\nlet r = tween_int(0, 10, 0.5)")
    check_eq("tween_int", interp._env.get("r"), 5)

def test_tween_angle_wrap():
    # Tweening from 0 to 3π/2 should take the short path via -π/2
    interp = run(TW + f"\nlet r = tween_angle(0.0, {3 * math.pi / 2}, 1.0)")
    # Expected: shortest arc → -π/2
    got = interp._env.get("r")
    # Allow either representation: -π/2 ≈ -1.5708
    check_close("tween_angle_wrap", got, -math.pi / 2, tol=1e-4)

def test_tween_smooth_endpoints():
    interp = run(TW + "\nlet a = tween_smooth(0.0, 1.0, 0.0)\nlet b = tween_smooth(0.0, 1.0, 1.0)")
    check_close("tween_smooth_start", interp._env.get("a"), 0.0)
    check_close("tween_smooth_end", interp._env.get("b"), 1.0)

def test_tween_ease_in():
    interp = run(TW + "\nlet r = tween_ease_in(0.0, 100.0, 0.5)")
    check_close("tween_ease_in", interp._env.get("r"), 25.0)

def test_tween_ease_out():
    interp = run(TW + "\nlet r = tween_ease_out(0.0, 100.0, 0.5)")
    check_close("tween_ease_out", interp._env.get("r"), 75.0)

def test_tween_loop():
    interp = run(TW + "\nlet r = tween_loop(2.5, 1.0)")
    check_close("tween_loop", interp._env.get("r"), 0.5)

def test_tween_pingpong_forward():
    interp = run(TW + "\nlet r = tween_pingpong(0.25, 1.0)")
    check_close("tween_pingpong_forward", interp._env.get("r"), 0.25)

def test_tween_pingpong_back():
    interp = run(TW + "\nlet r = tween_pingpong(1.5, 1.0)")
    check_close("tween_pingpong_back", interp._env.get("r"), 0.5)

# ─────────────────────────────────────────────────────────────────────────────
# collision package
# ─────────────────────────────────────────────────────────────────────────────

COL = pkg("collision")

def test_circle_circle_hit():
    interp = run(COL + "\nlet r = circle_circle(0.0, 0.0, 5.0, 3.0, 0.0, 3.0)")
    check_eq("circle_circle_hit", interp._env.get("r"), True)

def test_circle_circle_miss():
    interp = run(COL + "\nlet r = circle_circle(0.0, 0.0, 2.0, 10.0, 0.0, 2.0)")
    check_eq("circle_circle_miss", interp._env.get("r"), False)

def test_circle_circle_depth_hit():
    interp = run(COL + "\nlet r = circle_circle_depth(0.0, 0.0, 5.0, 8.0, 0.0, 5.0)")
    check_close("circle_circle_depth_hit", interp._env.get("r"), 2.0)

def test_circle_circle_depth_miss():
    interp = run(COL + "\nlet r = circle_circle_depth(0.0, 0.0, 2.0, 10.0, 0.0, 2.0)")
    # depth should be negative (no overlap)
    got = interp._env.get("r")
    if got < 0:
        ok("circle_circle_depth_miss")
    else:
        fail("circle_circle_depth_miss", f"expected negative, got {got}")

def test_aabb_aabb_hit():
    interp = run(COL + "\nlet r = aabb_aabb(0.0, 0.0, 10.0, 10.0, 5.0, 5.0, 10.0, 10.0)")
    check_eq("aabb_aabb_hit", interp._env.get("r"), True)

def test_aabb_aabb_miss():
    interp = run(COL + "\nlet r = aabb_aabb(0.0, 0.0, 5.0, 5.0, 10.0, 0.0, 5.0, 5.0)")
    check_eq("aabb_aabb_miss", interp._env.get("r"), False)

def test_aabb_aabb_touching():
    # Touching edges: ax+aw == bx → no overlap
    interp = run(COL + "\nlet r = aabb_aabb(0.0, 0.0, 5.0, 5.0, 5.0, 0.0, 5.0, 5.0)")
    check_eq("aabb_aabb_touching", interp._env.get("r"), False)

def test_aabb_aabb_mtv_x():
    interp = run(COL + "\nlet r = aabb_aabb_mtv(0.0, 0.0, 10.0, 10.0, 8.0, 0.0, 10.0, 10.0)")
    d = interp._env.get("r")
    # Overlap in X = (10+10)/2 - |5 - 13| = 10 - 8 = 2, dy should be 0
    check_close("aabb_aabb_mtv_dx_nonzero", abs(d["dx"]), 2.0)
    check_close("aabb_aabb_mtv_dy_zero", d["dy"], 0.0)

def test_aabb_aabb_mtv_miss():
    interp = run(COL + "\nlet r = aabb_aabb_mtv(0.0, 0.0, 5.0, 5.0, 20.0, 0.0, 5.0, 5.0)")
    d = interp._env.get("r")
    check_close("aabb_aabb_mtv_miss", d["dx"], 0.0)

def test_circle_aabb_hit():
    interp = run(COL + "\nlet r = circle_aabb(5.0, 5.0, 3.0, 0.0, 0.0, 10.0, 10.0)")
    check_eq("circle_aabb_hit", interp._env.get("r"), True)

def test_circle_aabb_miss():
    interp = run(COL + "\nlet r = circle_aabb(20.0, 20.0, 3.0, 0.0, 0.0, 10.0, 10.0)")
    check_eq("circle_aabb_miss", interp._env.get("r"), False)

def test_circle_aabb_corner():
    # Circle just reaching the corner
    interp = run(COL + "\nlet r = circle_aabb(11.0, 11.0, 2.0, 0.0, 0.0, 10.0, 10.0)")
    # dist from (11,11) to corner (10,10) = sqrt(2) ≈ 1.414 < 2 → hit
    check_eq("circle_aabb_corner_hit", interp._env.get("r"), True)

def test_point_in_aabb_inside():
    interp = run(COL + "\nlet r = point_in_aabb(5.0, 5.0, 0.0, 0.0, 10.0, 10.0)")
    check_eq("point_in_aabb_inside", interp._env.get("r"), True)

def test_point_in_aabb_outside():
    interp = run(COL + "\nlet r = point_in_aabb(15.0, 5.0, 0.0, 0.0, 10.0, 10.0)")
    check_eq("point_in_aabb_outside", interp._env.get("r"), False)

def test_point_in_circle_inside():
    interp = run(COL + "\nlet r = point_in_circle(3.0, 4.0, 0.0, 0.0, 6.0)")
    check_eq("point_in_circle_inside", interp._env.get("r"), True)

def test_point_in_circle_outside():
    interp = run(COL + "\nlet r = point_in_circle(5.0, 0.0, 0.0, 0.0, 4.0)")
    check_eq("point_in_circle_outside", interp._env.get("r"), False)

def test_ray_aabb_hit():
    # Ray from (0,5) going right (+x), rect at x=10..20, y=0..10 → should hit
    interp = run(COL + "\nlet r = ray_aabb(0.0, 5.0, 1.0, 0.0, 10.0, 0.0, 10.0, 10.0)")
    got = interp._env.get("r")
    if got >= 0:
        ok("ray_aabb_hit")
    else:
        fail("ray_aabb_hit", f"expected >= 0, got {got}")

def test_ray_aabb_miss():
    # Ray going left from origin, rect to the right → miss
    interp = run(COL + "\nlet r = ray_aabb(0.0, 5.0, -1.0, 0.0, 10.0, 0.0, 10.0, 10.0)")
    got = interp._env.get("r")
    check_close("ray_aabb_miss", got, -1.0)

def test_ray_aabb_distance():
    # Ray from (0,5) going right, rect at x=10..20, y=0..10 → hit at t=10
    interp = run(COL + "\nlet r = ray_aabb(0.0, 5.0, 1.0, 0.0, 10.0, 0.0, 10.0, 10.0)")
    check_close("ray_aabb_distance", interp._env.get("r"), 10.0)

# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────

def test_registry_has_six_packages():
    import json
    path = os.path.join(os.path.dirname(__file__), "inscript-packages", "registry.json")
    with open(path) as f:
        reg = json.load(f)
    if len(reg) == 6:
        ok("registry_has_six_packages")
    else:
        fail("registry_has_six_packages", f"expected 6, got {len(reg)}")

def test_registry_new_packages_present():
    import json
    path = os.path.join(os.path.dirname(__file__), "inscript-packages", "registry.json")
    with open(path) as f:
        reg = json.load(f)
    for name in ("vector2", "tween", "collision"):
        if name in reg:
            ok(f"registry_has_{name}")
        else:
            fail(f"registry_has_{name}", "missing from registry.json")

def test_package_files_exist():
    base = os.path.join(os.path.dirname(__file__), "inscript-packages", "packages")
    for name in ("vector2", "tween", "collision"):
        path = os.path.join(base, name, f"{name}.ins")
        if os.path.exists(path):
            ok(f"package_file_{name}")
        else:
            fail(f"package_file_{name}", f"{path} not found")

def test_version_is_212():
    if repl_mod.VERSION == "2.1.2":
        ok("version_is_2.1.2")
    else:
        fail("version_is_2.1.2", f"got {repl_mod.VERSION}")

# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("test_v212.py — v2.1.2: vector2, tween, collision packages")
    print("=" * 60)

    # vector2
    test_vec2_len();        test_vec2_len_sq()
    test_vec2_norm();       test_vec2_norm_zero()
    test_vec2_dot();        test_vec2_dot_parallel()
    test_vec2_cross()
    test_vec2_add();        test_vec2_sub();    test_vec2_scale()
    test_vec2_dist();       test_vec2_dist_sq()
    test_vec2_lerp()
    test_vec2_rotate_90();  test_vec2_angle()
    test_vec2_reflect();    test_vec2_project()

    # tween
    test_tween_tick_advance();  test_tween_tick_clamp()
    test_tween_done_false();    test_tween_done_true()
    test_tween_t_mid();         test_tween_t_zero_duration()
    test_tween_float();         test_tween_int()
    test_tween_angle_wrap()
    test_tween_smooth_endpoints()
    test_tween_ease_in();       test_tween_ease_out()
    test_tween_loop()
    test_tween_pingpong_forward(); test_tween_pingpong_back()

    # collision
    test_circle_circle_hit();   test_circle_circle_miss()
    test_circle_circle_depth_hit(); test_circle_circle_depth_miss()
    test_aabb_aabb_hit();       test_aabb_aabb_miss();  test_aabb_aabb_touching()
    test_aabb_aabb_mtv_x();     test_aabb_aabb_mtv_miss()
    test_circle_aabb_hit();     test_circle_aabb_miss(); test_circle_aabb_corner()
    test_point_in_aabb_inside(); test_point_in_aabb_outside()
    test_point_in_circle_inside(); test_point_in_circle_outside()
    test_ray_aabb_hit();        test_ray_aabb_miss();   test_ray_aabb_distance()

    # meta
    test_registry_has_six_packages()
    test_registry_new_packages_present()
    test_package_files_exist()
    test_version_is_212()

    total = PASS + FAIL
    print("=" * 60)
    print(f"{PASS}/{total} passed  ({FAIL} failed)")
    sys.exit(0 if FAIL == 0 else 1)
