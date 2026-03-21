# -*- coding: utf-8 -*-
# inscript/test_analyzer.py  — Phase 3 Semantic Analyzer Tests
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from parser import parse
from analyzer import analyze, Analyzer, T_INT, T_FLOAT, T_STRING, T_BOOL, T_VEC2
from errors import SemanticError, MultiError

PASS, FAIL = "✅", "❌"
results = []

def test(name, fn):
    try: fn(); results.append((PASS, name))
    except Exception as e: results.append((FAIL, name, str(e)))

def ok(src):
    prog = parse(src)
    return analyze(prog, src)

def err(src):
    try:
        prog = parse(src)
        analyze(prog, src)
        return None   # no error raised
    except MultiError as me:
        return me.errors[0] if me.errors else None  # return first error
    except SemanticError as e:
        return e


# ── Variable declarations ──────────────────────────────────────────────────
def t_let_int():
    syms = ok("let x: int = 5")
    assert syms["x"].type_.name == "int"
test("let x: int = 5 — type registered", t_let_int)

def t_let_infer():
    syms = ok("let name = \"Alice\"")
    assert syms["name"].type_.name == "string"
test("Type inferred from string literal", t_let_infer)

def t_let_float_infer():
    syms = ok("let speed = 3.14")
    assert syms["speed"].type_.name == "float"
test("Type inferred from float literal", t_let_float_infer)

def t_type_mismatch():
    e = err("let x: int = 3.14")
    assert e is not None, "Expected SemanticError"
    assert "mismatch" in e.message.lower()
test("Error: int = float mismatch", t_type_mismatch)

def t_const_no_reassign():
    e = err("const MAX: int = 100\nMAX = 5")
    assert e is not None
    assert "constant" in e.message.lower()
test("Error: cannot assign to const", t_const_no_reassign)

def t_undefined_var():
    e = err("let y = x + 1")
    assert e is not None
    assert "undefined" in e.message.lower() or "Undefined" in e.message
test("Error: undefined variable 'x'", t_undefined_var)

def t_duplicate_var():
    e = err("let x = 1\nlet x = 2")
    assert e is not None
    assert "already declared" in e.message.lower()
test("Error: duplicate declaration", t_duplicate_var)


# ── Function declarations ─────────────────────────────────────────────────
def t_fn_decl():
    syms = ok("fn add(a: int, b: int) -> int { return a + b }")
    assert "add" in syms
test("fn add declared in symbol table", t_fn_decl)

def t_fn_return_mismatch():
    e = err("fn f() -> int { return 3.14 }")
    assert e is not None
    assert "return" in e.message.lower() or "mismatch" in e.message.lower()
test("Error: return type mismatch float vs int", t_fn_return_mismatch)

def t_fn_return_void_ok():
    e = err("fn greet() { return }")
    assert e is None
test("fn void return is ok", t_fn_return_void_ok)

def t_fn_params_scoped():
    # params visible inside fn, not outside
    syms = ok("fn f(x: int) -> int { return x }")
    assert "x" not in syms   # x should not leak to global scope
test("fn params scoped to function body", t_fn_params_scoped)

def t_return_outside_fn():
    e = err("return 5")
    assert e is not None
    assert "outside" in e.message.lower()
test("Error: return outside function", t_return_outside_fn)


# ── Struct declarations ────────────────────────────────────────────────────
def t_struct_decl():
    src = "struct Player { health: int = 100 }"
    syms = ok(src)
    assert "Player" in syms
test("Struct declared in symbol table", t_struct_decl)

def t_struct_field_type():
    src = "struct Enemy { pos: Vec2 }"
    e = err(src)
    assert e is None
test("Struct with Vec2 field is valid", t_struct_field_type)

def t_struct_field_mismatch():
    e = err("struct X { n: int = 3.14 }")
    assert e is not None
test("Error: struct field default type mismatch", t_struct_field_mismatch)

def t_struct_bad_field():
    e = err("""
    struct Player { health: int = 100 }
    let p = Player { health: 100, foo: 5 }
    """)
    assert e is not None
    assert "no field" in e.message.lower()
test("Error: struct init with unknown field", t_struct_bad_field)

def t_struct_init_ok():
    e = err("""
    struct Player { health: int = 100 }
    let p = Player { health: 50 }
    """)
    assert e is None
test("Struct initializer with correct fields ok", t_struct_init_ok)

def t_unknown_struct():
    e = err("let p = Ghost { health: 100 }")
    assert e is not None
    assert "unknown struct" in e.message.lower()
test("Error: initializing unknown struct", t_unknown_struct)


# ── Scene declarations ─────────────────────────────────────────────────────
def t_scene_decl():
    src = """
    scene GameScene {
        let score: int = 0
        on_start { print("ok") }
        on_update(dt: float) { score += 1 }
    }
    """
    e = err(src)
    assert e is None
test("Scene declaration is valid", t_scene_decl)

def t_scene_var_scoped():
    src = """
    scene S {
        let x: int = 0
        on_update(dt: float) { x = 1 }
    }
    """
    e = err(src)
    # x should be reachable inside on_update because it's in scene scope
    # This might fail if scoping is wrong — test it
    assert e is None
test("Scene var accessible from lifecycle hook", t_scene_var_scoped)


# ── Control flow ─────────────────────────────────────────────────────────
def t_if_stmt():
    e = err("let x = 5\nif x > 0 { let y = 1 }")
    assert e is None
test("if stmt valid", t_if_stmt)

def t_while_break():
    e = err("while true { break }")
    assert e is None
test("break inside while is valid", t_while_break)

def t_break_outside_loop():
    e = err("break")
    assert e is not None
    assert "outside" in e.message.lower()
test("Error: break outside loop", t_break_outside_loop)

def t_continue_outside_loop():
    e = err("continue")
    assert e is not None
    assert "outside" in e.message.lower()
test("Error: continue outside loop", t_continue_outside_loop)

def t_for_in_range():
    e = err("for i in 0..10 { print(i) }")
    assert e is None
test("for i in 0..10 valid", t_for_in_range)

def t_match_stmt():
    src = """
    let s = "idle"
    match s {
        case "idle" { let a = 1 }
        case _      { let b = 2 }
    }
    """
    e = err(src)
    assert e is None
test("match stmt valid", t_match_stmt)


# ── Binary expressions ───────────────────────────────────────────────────
def t_int_plus_int():
    src = "let x: int = 1 + 2"
    e = err(src); assert e is None
test("int + int = int ok", t_int_plus_int)

def t_float_plus_int():
    src = "let x: float = 1.0 + 2"
    e = err(src); assert e is None
test("float + int = float ok (widening)", t_float_plus_int)

def t_string_plus_string():
    src = 'let x: string = "hello" + " world"'
    e = err(src); assert e is None
test("string + string ok", t_string_plus_string)

def t_bad_type_op():
    e = err('let x = "hello" - 5')
    assert e is not None
test('Error: "hello" - 5 invalid', t_bad_type_op)

def t_vec_arithmetic():
    e = err("let v: Vec2 = Vec2(1, 0) + Vec2(0, 1)")
    assert e is None
test("Vec2 + Vec2 ok", t_vec_arithmetic)


# ── Builtin functions ─────────────────────────────────────────────────────
def t_print_builtin():
    e = err('print("hello")')
    assert e is None
test("print() builtin accessible", t_print_builtin)

def t_sin_builtin():
    e = err("let x = sin(3.14)")
    assert e is None
test("sin() builtin accessible", t_sin_builtin)


# ── Enum declarations ────────────────────────────────────────────────────
def t_enum_decl():
    src = "enum Dir { North, South, East, West }"
    e = err(src)
    assert e is None
test("Enum declaration valid", t_enum_decl)


# ── Complex program ──────────────────────────────────────────────────────
def t_full_program():
    src = """
    const GRAVITY: float = 9.8

    struct Ball {
        pos: Vec2
        vel: Vec2
        radius: float = 10.0
    }

    fn reflect(v: Vec2, normal: Vec2) -> Vec2 {
        return v
    }

    scene Demo {
        let ball = Ball { pos: Vec2(400, 300), vel: Vec2(100, 50), radius: 15.0 }
        let score: int = 0

        on_start {
            print("Demo started")
        }

        on_update(dt: float) {
            score += 1
        }

        on_draw {
            draw.clear(Color(0, 0, 0))
        }
    }
    """
    e = err(src)
    assert e is None, str(e)
test("Full complex program passes analysis", t_full_program)


# ── Results ──────────────────────────────────────────────────────────────
print("\n" + "="*62)
print("  InScript Semantic Analyzer — Test Results")
print("="*62)
passed = failed = 0
for r in results:
    if r[0] == PASS:
        print(f"  {r[0]} {r[1]}"); passed += 1
    else:
        print(f"  {r[0]} {r[1]}"); print(f"       └─ {r[2]}"); failed += 1
print("="*62)
print(f"  {passed} passed, {failed} failed out of {len(results)} tests")
print("="*62 + "\n")
if failed: sys.exit(1)
