"""
test_v1912.py — Tests for InScript v1.9.12
Bootstrap registry + 3 real .ins packages (math-utils, color-utils, easing).
All tests run locally — no network required.
"""
import sys, os, json, tempfile, shutil
sys.path.insert(0, os.path.dirname(__file__))

from lexer import Lexer
from parser import Parser
from analyzer import Analyzer
from interpreter import Interpreter
from environment import Environment

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

def run_ins_file(path):
    """Parse and execute a .ins file, return the Interpreter."""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    interp = Interpreter()
    interp.execute(src)
    return interp

def call_fn(interp, name, *args):
    """Call a top-level InScript function by name with Python args."""
    fn = interp._env.get(name)
    return interp._call_fn(fn, list(args))

PACKAGES_DIR = os.path.join(os.path.dirname(__file__), "inscript-packages", "packages")
REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "inscript-packages", "registry.json")
MATH_UTILS = os.path.join(PACKAGES_DIR, "math-utils", "math-utils.ins")
COLOR_UTILS = os.path.join(PACKAGES_DIR, "color-utils", "color-utils.ins")
EASING_INS  = os.path.join(PACKAGES_DIR, "easing", "easing.ins")

# ── registry.json structure ──────────────────────────────────────────────────

def test_registry_is_valid_json():
    try:
        with open(REGISTRY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        ok("registry_is_valid_json")
    except Exception as e:
        fail("registry_is_valid_json", e)

def test_registry_has_three_packages():
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        data = json.load(f)
    if set(data.keys()) == {"math-utils", "color-utils", "easing"}:
        ok("registry_has_three_packages")
    else:
        fail("registry_has_three_packages", f"got keys: {list(data.keys())}")

def test_registry_entries_have_required_fields():
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        data = json.load(f)
    required = {"version", "description", "url", "tags", "min_inscript", "author"}
    all_ok = True
    for pkg, info in data.items():
        missing = required - set(info.keys())
        if missing:
            fail("registry_entries_have_required_fields", f"{pkg} missing: {missing}")
            all_ok = False
            break
    if all_ok:
        ok("registry_entries_have_required_fields")

def test_registry_urls_end_in_ins():
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        data = json.load(f)
    for pkg, info in data.items():
        if not info["url"].endswith(".ins"):
            fail("registry_urls_end_in_ins", f"{pkg} url={info['url']}")
            return
    ok("registry_urls_end_in_ins")

# ── _parse_pkg_spec ──────────────────────────────────────────────────────────

def test_parse_pkg_spec_bare():
    from inscript import _parse_pkg_spec
    name, ver = _parse_pkg_spec("math-utils")
    if name == "math-utils" and ver is None:
        ok("parse_pkg_spec_bare")
    else:
        fail("parse_pkg_spec_bare", f"got ({name!r}, {ver!r})")

def test_parse_pkg_spec_versioned():
    from inscript import _parse_pkg_spec
    name, ver = _parse_pkg_spec("easing@1.0.0")
    if name == "easing" and ver == "1.0.0":
        ok("parse_pkg_spec_versioned")
    else:
        fail("parse_pkg_spec_versioned", f"got ({name!r}, {ver!r})")

def test_parse_pkg_spec_color_utils():
    from inscript import _parse_pkg_spec
    name, ver = _parse_pkg_spec("color-utils@1.0.0")
    if name == "color-utils" and ver == "1.0.0":
        ok("parse_pkg_spec_color_utils")
    else:
        fail("parse_pkg_spec_color_utils", f"got ({name!r}, {ver!r})")

# ── math-utils ───────────────────────────────────────────────────────────────

def _load_math():
    return run_ins_file(MATH_UTILS)

def test_math_gcd():
    try:
        interp = _load_math()
        result = call_fn(interp, "gcd", 12, 8)
        if result == 4:
            ok("math_gcd")
        else:
            fail("math_gcd", f"expected 4, got {result}")
    except Exception as e:
        fail("math_gcd", e)

def test_math_lcm():
    try:
        interp = _load_math()
        result = call_fn(interp, "lcm", 4, 6)
        if result == 12:
            ok("math_lcm")
        else:
            fail("math_lcm", f"expected 12, got {result}")
    except Exception as e:
        fail("math_lcm", e)

def test_math_clamp():
    try:
        interp = _load_math()
        r1 = call_fn(interp, "clamp", 5.0, 0.0, 10.0)
        r2 = call_fn(interp, "clamp", -3.0, 0.0, 10.0)
        r3 = call_fn(interp, "clamp", 15.0, 0.0, 10.0)
        if r1 == 5.0 and r2 == 0.0 and r3 == 10.0:
            ok("math_clamp")
        else:
            fail("math_clamp", f"got {r1}, {r2}, {r3}")
    except Exception as e:
        fail("math_clamp", e)

def test_math_lerp():
    try:
        interp = _load_math()
        result = call_fn(interp, "lerp", 0.0, 10.0, 0.5)
        if abs(result - 5.0) < 1e-9:
            ok("math_lerp")
        else:
            fail("math_lerp", f"expected 5.0, got {result}")
    except Exception as e:
        fail("math_lerp", e)

def test_math_is_prime():
    try:
        interp = _load_math()
        r1 = call_fn(interp, "is_prime", 7)
        r2 = call_fn(interp, "is_prime", 9)
        r3 = call_fn(interp, "is_prime", 2)
        if r1 == True and r2 == False and r3 == True:
            ok("math_is_prime")
        else:
            fail("math_is_prime", f"got {r1}, {r2}, {r3}")
    except Exception as e:
        fail("math_is_prime", e)

def test_math_factorial():
    try:
        interp = _load_math()
        result = call_fn(interp, "factorial", 5)
        if result == 120:
            ok("math_factorial")
        else:
            fail("math_factorial", f"expected 120, got {result}")
    except Exception as e:
        fail("math_factorial", e)

def test_math_fib():
    try:
        interp = _load_math()
        results = [call_fn(interp, "fib", i) for i in range(7)]
        expected = [0, 1, 1, 2, 3, 5, 8]
        if results == expected:
            ok("math_fib")
        else:
            fail("math_fib", f"expected {expected}, got {results}")
    except Exception as e:
        fail("math_fib", e)

def test_math_sign():
    try:
        interp = _load_math()
        r1 = call_fn(interp, "sign", 5.0)
        r2 = call_fn(interp, "sign", -3.0)
        r3 = call_fn(interp, "sign", 0.0)
        if r1 == 1 and r2 == -1 and r3 == 0:
            ok("math_sign")
        else:
            fail("math_sign", f"got {r1}, {r2}, {r3}")
    except Exception as e:
        fail("math_sign", e)

# ── color-utils ──────────────────────────────────────────────────────────────

def _load_color():
    return run_ins_file(COLOR_UTILS)

def test_color_rgb_to_hex():
    try:
        interp = _load_color()
        result = call_fn(interp, "rgb_to_hex", 255, 0, 128)
        if result == "#ff0080":
            ok("color_rgb_to_hex")
        else:
            fail("color_rgb_to_hex", f"expected '#ff0080', got {result!r}")
    except Exception as e:
        fail("color_rgb_to_hex", e)

def test_color_brightness():
    try:
        interp = _load_color()
        result = call_fn(interp, "brightness", 255, 255, 255)
        if abs(result - 255.0) < 0.01:
            ok("color_brightness")
        else:
            fail("color_brightness", f"expected ~255.0, got {result}")
    except Exception as e:
        fail("color_brightness", e)

# ── easing ───────────────────────────────────────────────────────────────────

def _load_easing():
    return run_ins_file(EASING_INS)

def test_easing_smooth_endpoints():
    try:
        interp = _load_easing()
        r0 = call_fn(interp, "smooth", 0.0)
        r1 = call_fn(interp, "smooth", 1.0)
        if abs(r0) < 1e-9 and abs(r1 - 1.0) < 1e-9:
            ok("easing_smooth_endpoints")
        else:
            fail("easing_smooth_endpoints", f"got {r0}, {r1}")
    except Exception as e:
        fail("easing_smooth_endpoints", e)

def test_easing_ease_in_midpoint():
    try:
        interp = _load_easing()
        result = call_fn(interp, "ease_in", 0.5)
        if abs(result - 0.25) < 1e-9:
            ok("easing_ease_in_midpoint")
        else:
            fail("easing_ease_in_midpoint", f"expected 0.25, got {result}")
    except Exception as e:
        fail("easing_ease_in_midpoint", e)

def test_easing_ease_out_midpoint():
    try:
        interp = _load_easing()
        result = call_fn(interp, "ease_out", 0.5)
        if abs(result - 0.75) < 1e-9:
            ok("easing_ease_out_midpoint")
        else:
            fail("easing_ease_out_midpoint", f"expected 0.75, got {result}")
    except Exception as e:
        fail("easing_ease_out_midpoint", e)

def test_easing_bounce_out_at_one():
    try:
        interp = _load_easing()
        result = call_fn(interp, "bounce_out", 1.0)
        if abs(result - 1.0) < 0.01:
            ok("easing_bounce_out_at_one")
        else:
            fail("easing_bounce_out_at_one", f"expected ~1.0, got {result}")
    except Exception as e:
        fail("easing_bounce_out_at_one", e)

# ── install_package with file:// URL ─────────────────────────────────────────

def test_install_package_ins_url():
    """install_package() with a file:// .ins URL must write main.ins."""
    try:
        from inscript import install_package, PACKAGES_DIR as PKG_DIR
        import urllib.request

        tmp_pkgs = tempfile.mkdtemp()
        try:
            # Patch PACKAGES_DIR for this test
            import inscript as _ins_mod
            orig = _ins_mod.PACKAGES_DIR
            _ins_mod.PACKAGES_DIR = tmp_pkgs

            # Build a minimal fake registry served via file://
            # We'll monkey-patch urllib.request.urlopen for the registry call,
            # then let the second call (the .ins file) use a real file:// URL.
            ins_content = b'fn hello() -> string { return "hi" }\n'
            ins_file = os.path.join(tmp_pkgs, "test_pkg.ins")
            with open(ins_file, "wb") as f:
                f.write(ins_content)

            import urllib.request as _ur
            import io as _io
            real_urlopen = _ur.urlopen

            call_count = [0]
            def fake_urlopen(url, timeout=10):
                call_count[0] += 1
                if call_count[0] == 1:
                    # First call: registry
                    ins_url = "file://" + ins_file.replace("\\", "/")
                    registry_data = json.dumps({
                        "test-pkg": {
                            "version": "1.0.0",
                            "url": ins_url
                        }
                    }).encode()
                    return _io.BytesIO(registry_data)
                else:
                    # Second call: the .ins file itself
                    return real_urlopen(url, timeout=timeout)

            _ur.urlopen = fake_urlopen
            try:
                ret = install_package("test-pkg")
            finally:
                _ur.urlopen = real_urlopen
                _ins_mod.PACKAGES_DIR = orig

            expected = os.path.join(tmp_pkgs, "test-pkg", "main.ins")
            if ret == 0 and os.path.exists(expected):
                with open(expected, "rb") as f:
                    content = f.read()
                if content == ins_content:
                    ok("install_package_ins_url")
                else:
                    fail("install_package_ins_url", f"main.ins content mismatch")
            else:
                fail("install_package_ins_url", f"ret={ret}, exists={os.path.exists(expected)}")
        finally:
            shutil.rmtree(tmp_pkgs, ignore_errors=True)
    except Exception as e:
        fail("install_package_ins_url", e)

# ── run all ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("test_v1912.py — v1.9.12 bootstrap registry + packages")
    print("=" * 60)

    test_registry_is_valid_json()
    test_registry_has_three_packages()
    test_registry_entries_have_required_fields()
    test_registry_urls_end_in_ins()

    test_parse_pkg_spec_bare()
    test_parse_pkg_spec_versioned()
    test_parse_pkg_spec_color_utils()

    test_math_gcd()
    test_math_lcm()
    test_math_clamp()
    test_math_lerp()
    test_math_is_prime()
    test_math_factorial()
    test_math_fib()
    test_math_sign()

    test_color_rgb_to_hex()
    test_color_brightness()

    test_easing_smooth_endpoints()
    test_easing_ease_in_midpoint()
    test_easing_ease_out_midpoint()
    test_easing_bounce_out_at_one()

    test_install_package_ins_url()

    total = passed + failed
    print("=" * 60)
    print(f"{passed}/{total} passed  ({failed} failed)")
    if failed:
        sys.exit(1)
