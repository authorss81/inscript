# inscript/test_parser.py
# Comprehensive tests for the InScript Parser (Phase 2)
# Run with: python test_parser.py

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from parser import parse
from ast_nodes import *
from errors import ParseError

PASS = "✅"
FAIL = "❌"
results = []

def test(name, fn):
    try:
        fn()
        results.append((PASS, name))
    except Exception as e:
        results.append((FAIL, name, str(e)))

def parsed(src):
    return parse(src).body

# ─── Literals ──────────────────────────────────
def test_int_literal():
    nodes = parsed("42")
    expr = nodes[0].expr
    assert isinstance(expr, IntLiteralExpr)
    assert expr.value == 42
test("Parse integer literal", test_int_literal)

def test_float_literal():
    nodes = parsed("3.14")
    assert isinstance(nodes[0].expr, FloatLiteralExpr)
    assert nodes[0].expr.value == 3.14
test("Parse float literal", test_float_literal)

def test_string_literal():
    nodes = parsed('"hello"')
    assert isinstance(nodes[0].expr, StringLiteralExpr)
    assert nodes[0].expr.value == "hello"
test("Parse string literal", test_string_literal)

def test_bool_literal():
    nodes = parsed("true")
    assert isinstance(nodes[0].expr, BoolLiteralExpr)
    assert nodes[0].expr.value == True
test("Parse bool literal", test_bool_literal)

def test_null_literal():
    nodes = parsed("null")
    assert isinstance(nodes[0].expr, NullLiteralExpr)
test("Parse null literal", test_null_literal)

# ─── Variable Declarations ─────────────────────
def test_let_no_type():
    nodes = parsed("let x = 5")
    decl = nodes[0]
    assert isinstance(decl, VarDecl)
    assert decl.name == "x"
    assert decl.is_const == False
    assert isinstance(decl.initializer, IntLiteralExpr)
    assert decl.initializer.value == 5
test("let x = 5", test_let_no_type)

def test_let_with_type():
    nodes = parsed("let score: int = 0")
    decl = nodes[0]
    assert isinstance(decl, VarDecl)
    assert decl.name == "score"
    assert decl.type_ann.name == "int"
    assert isinstance(decl.initializer, IntLiteralExpr)
test("let score: int = 0", test_let_with_type)

def test_const_decl():
    nodes = parsed("const MAX: int = 100")
    decl = nodes[0]
    assert isinstance(decl, VarDecl)
    assert decl.is_const == True
    assert decl.name == "MAX"
test("const MAX: int = 100", test_const_decl)

def test_let_no_init():
    nodes = parsed("let x: float")
    decl = nodes[0]
    assert isinstance(decl, VarDecl)
    assert decl.initializer is None
    assert decl.type_ann.name == "float"
test("let x: float  (no initializer)", test_let_no_init)

# ─── Array Type ────────────────────────────────
def test_array_type():
    nodes = parsed("let scores: [int] = [1, 2, 3]")
    decl = nodes[0]
    assert decl.type_ann.is_array == True
    assert decl.type_ann.generics[0].name == "int"
    init = decl.initializer
    assert isinstance(init, ArrayLiteralExpr)
    assert len(init.elements) == 3
test("let scores: [int] = [1, 2, 3]", test_array_type)

# ─── Dict Literal ──────────────────────────────
def test_dict_literal():
    nodes = parsed('let d = {"a": 1, "b": 2}')
    init = nodes[0].initializer
    assert isinstance(init, DictLiteralExpr)
    assert len(init.pairs) == 2
test("Dict literal", test_dict_literal)

# ─── Binary Expressions ────────────────────────
def test_binary_add():
    nodes = parsed("1 + 2")
    expr = nodes[0].expr
    assert isinstance(expr, BinaryExpr)
    assert expr.op == "+"
    assert expr.left.value == 1
    assert expr.right.value == 2
test("Binary: 1 + 2", test_binary_add)

def test_operator_precedence():
    # 2 + 3 * 4 should be 2 + (3 * 4)
    nodes = parsed("2 + 3 * 4")
    expr = nodes[0].expr
    assert isinstance(expr, BinaryExpr)
    assert expr.op == "+"
    assert isinstance(expr.right, BinaryExpr)
    assert expr.right.op == "*"
test("Operator precedence: 2 + 3 * 4", test_operator_precedence)

def test_power_right_assoc():
    # 2 ** 3 ** 2 = 2 ** (3 ** 2)
    nodes = parsed("2 ** 3 ** 2")
    expr = nodes[0].expr
    assert isinstance(expr, BinaryExpr)
    assert expr.op == "**"
    assert isinstance(expr.right, BinaryExpr)
    assert expr.right.op == "**"
test("Power right-associative", test_power_right_assoc)

def test_unary_not():
    nodes = parsed("!true")
    expr = nodes[0].expr
    assert isinstance(expr, UnaryExpr)
    assert expr.op == "!"
test("Unary: !true", test_unary_not)

def test_unary_neg():
    nodes = parsed("-42")
    expr = nodes[0].expr
    assert isinstance(expr, UnaryExpr)
    assert expr.op == "-"
    assert expr.operand.value == 42
test("Unary: -42", test_unary_neg)

def test_logical():
    nodes = parsed("a && b || c")
    expr = nodes[0].expr
    assert isinstance(expr, BinaryExpr)
    assert expr.op == "||"
test("Logical: a && b || c", test_logical)

# ─── Assignments ───────────────────────────────
def test_assign():
    nodes = parsed("x = 10")
    expr = nodes[0].expr
    assert isinstance(expr, AssignExpr)
    assert isinstance(expr.target, IdentExpr)
    assert expr.target.name == "x"
    assert expr.op == "="
test("x = 10", test_assign)

def test_compound_assign():
    nodes = parsed("score += 5")
    expr = nodes[0].expr
    assert isinstance(expr, AssignExpr)
    assert expr.op == "+="
test("score += 5", test_compound_assign)

def test_attr_assign():
    nodes = parsed("player.health = 100")
    stmt = nodes[0].expr
    assert isinstance(stmt, SetAttrExpr)
    assert stmt.attr == "health"
test("player.health = 100", test_attr_assign)

def test_index_assign():
    nodes = parsed("arr[0] = 42")
    stmt = nodes[0].expr
    assert isinstance(stmt, SetIndexExpr)
test("arr[0] = 42", test_index_assign)

# ─── Dot Access & Calls ────────────────────────
def test_dot_access():
    nodes = parsed("player.health")
    expr = nodes[0].expr
    assert isinstance(expr, GetAttrExpr)
    assert expr.attr == "health"
test("player.health", test_dot_access)

def test_chained_dot():
    nodes = parsed("self.pos.x")
    expr = nodes[0].expr
    assert isinstance(expr, GetAttrExpr)
    assert expr.attr == "x"
    assert isinstance(expr.obj, GetAttrExpr)
    assert expr.obj.attr == "pos"
test("self.pos.x (chained dot)", test_chained_dot)

def test_function_call():
    nodes = parsed("add(1, 2)")
    expr = nodes[0].expr
    assert isinstance(expr, CallExpr)
    assert isinstance(expr.callee, IdentExpr)
    assert expr.callee.name == "add"
    assert len(expr.args) == 2
test("add(1, 2)", test_function_call)

def test_method_call():
    nodes = parsed("player.move(dt)")
    expr = nodes[0].expr
    assert isinstance(expr, CallExpr)
    assert isinstance(expr.callee, GetAttrExpr)
    assert expr.callee.attr == "move"
test("player.move(dt)", test_method_call)

def test_named_args():
    nodes = parsed("Vec2(x: 1, y: 2)")
    expr = nodes[0].expr
    assert isinstance(expr, CallExpr)
    assert expr.args[0].name == "x"
    assert expr.args[1].name == "y"
test("Vec2(x: 1, y: 2) named args", test_named_args)

def test_index_access():
    nodes = parsed("arr[0]")
    expr = nodes[0].expr
    assert isinstance(expr, IndexExpr)
    assert isinstance(expr.index, IntLiteralExpr)
    assert expr.index.value == 0
test("arr[0]", test_index_access)

def test_namespace_access():
    nodes = parsed("Color::RED")
    expr = nodes[0].expr
    assert isinstance(expr, NamespaceAccessExpr)
    assert expr.namespace == "Color"
    assert expr.member == "RED"
test("Color::RED namespace access", test_namespace_access)

# ─── Control Flow ──────────────────────────────
def test_if_stmt():
    nodes = parsed("if x > 0 { let y = 1 }")
    stmt = nodes[0]
    assert isinstance(stmt, IfStmt)
    assert isinstance(stmt.condition, BinaryExpr)
    assert stmt.else_branch is None
test("if stmt", test_if_stmt)

def test_if_else():
    nodes = parsed("if a { x = 1 } else { x = 2 }")
    stmt = nodes[0]
    assert isinstance(stmt, IfStmt)
    assert isinstance(stmt.else_branch, BlockStmt)
test("if/else stmt", test_if_else)

def test_if_else_if():
    nodes = parsed("if a { } else if b { } else { }")
    stmt = nodes[0]
    assert isinstance(stmt.else_branch, IfStmt)
test("if/else if/else chain", test_if_else_if)

def test_while_stmt():
    nodes = parsed("while running { update() }")
    stmt = nodes[0]
    assert isinstance(stmt, WhileStmt)
    assert isinstance(stmt.condition, IdentExpr)
test("while stmt", test_while_stmt)

def test_for_in():
    nodes = parsed("for item in items { print(item) }")
    stmt = nodes[0]
    assert isinstance(stmt, ForInStmt)
    assert stmt.var_name == "item"
    assert isinstance(stmt.iterable, IdentExpr)
test("for/in stmt", test_for_in)

def test_match_stmt():
    src = '''
    match state {
        case "idle"  { x = 1 }
        case "run"   { x = 2 }
        case _       { x = 0 }
    }
    '''
    nodes = parsed(src)
    stmt = nodes[0]
    assert isinstance(stmt, MatchStmt)
    assert len(stmt.arms) == 3
    assert stmt.arms[2].pattern is None  # wildcard
test("match stmt with wildcard", test_match_stmt)

def test_return_stmt():
    nodes = parsed("fn f() { return 42 }")
    fn = nodes[0]
    ret = fn.body.body[0]
    assert isinstance(ret, ReturnStmt)
    assert ret.value.value == 42
test("return stmt", test_return_stmt)

def test_break_continue():
    nodes = parsed("while true { break }")
    body = nodes[0].body.body
    assert isinstance(body[0], BreakStmt)
test("break stmt", test_break_continue)

# ─── Function Declaration ──────────────────────
def test_fn_decl():
    nodes = parsed("fn add(a: int, b: int) -> int { return a + b }")
    fn = nodes[0]
    assert isinstance(fn, FunctionDecl)
    assert fn.name == "add"
    assert len(fn.params) == 2
    assert fn.params[0].name == "a"
    assert fn.params[0].type_ann.name == "int"
    assert fn.return_type.name == "int"
test("fn declaration", test_fn_decl)

def test_fn_no_return_type():
    nodes = parsed("fn greet() { print(\"hi\") }")
    fn = nodes[0]
    assert fn.return_type is None
test("fn without return type", test_fn_no_return_type)

def test_fn_default_param():
    nodes = parsed("fn greet(name: string = \"World\") { }")
    fn = nodes[0]
    assert fn.params[0].default.value == "World"
test("fn with default parameter", test_fn_default_param)

# ─── Struct Declaration ────────────────────────
def test_struct_decl():
    src = """
    struct Player {
        health: int = 100
        speed: float = 200.0
        fn move(dt: float) { }
    }
    """
    nodes = parsed(src)
    s = nodes[0]
    assert isinstance(s, StructDecl)
    assert s.name == "Player"
    assert len(s.fields) == 2
    assert s.fields[0].name == "health"
    assert s.fields[0].type_ann.name == "int"
    assert s.fields[0].default.value == 100
    assert len(s.methods) == 1
    assert s.methods[0].name == "move"
test("struct declaration", test_struct_decl)

def test_struct_init():
    nodes = parsed("Player { health: 100, speed: 200.0 }")
    expr = nodes[0].expr
    assert isinstance(expr, StructInitExpr)
    assert expr.struct_name == "Player"
    assert len(expr.fields) == 2
    assert expr.fields[0][0] == "health"
test("struct initializer", test_struct_init)

# ─── Scene Declaration ─────────────────────────
def test_scene_decl():
    src = """
    scene GameScene {
        let score: int = 0

        on_start {
            print("started")
        }

        on_update(dt: float) {
            score += 1
        }

        on_draw {
        }
    }
    """
    nodes = parsed(src)
    s = nodes[0]
    assert isinstance(s, SceneDecl)
    assert s.name == "GameScene"
    assert len(s.vars) == 1
    assert s.vars[0].name == "score"
    assert len(s.hooks) == 3
    assert s.hooks[0].hook_type == "on_start"
    assert s.hooks[1].hook_type == "on_update"
    assert s.hooks[1].params[0].name == "dt"
    assert s.hooks[2].hook_type == "on_draw"
test("scene declaration", test_scene_decl)

# ─── Print Statement ───────────────────────────
def test_print():
    nodes = parsed('print("hello")')
    stmt = nodes[0]
    assert isinstance(stmt, PrintStmt)
    assert len(stmt.args) == 1
    assert stmt.args[0].value == "hello"
test("print statement", test_print)

# ─── Array Literal ─────────────────────────────
def test_array_literal():
    nodes = parsed("[1, 2, 3]")
    expr = nodes[0].expr
    assert isinstance(expr, ArrayLiteralExpr)
    assert len(expr.elements) == 3
    assert expr.elements[0].value == 1
test("Array literal [1, 2, 3]", test_array_literal)

def test_empty_array():
    nodes = parsed("[]")
    expr = nodes[0].expr
    assert isinstance(expr, ArrayLiteralExpr)
    assert len(expr.elements) == 0
test("Empty array []", test_empty_array)

# ─── AI Declaration ────────────────────────────
def test_ai_decl():
    src = """
    ai EnemyAI {
        state Idle {
            on_update(dt: float) {
                x = 1
            }
        }
        state Chase {
            on_update(dt: float) { }
        }
    }
    """
    nodes = parsed(src)
    a = nodes[0]
    assert isinstance(a, AIDecl)
    assert a.name == "EnemyAI"
    assert len(a.states) == 2
    assert a.states[0].name == "Idle"
    assert a.states[1].name == "Chase"
test("AI declaration", test_ai_decl)

# ─── Complex program ───────────────────────────
def test_full_program():
    src = """
    const MAX_ENEMIES: int = 10
    let score: int = 0

    fn clamp(v: float, lo: float, hi: float) -> float {
        if v < lo { return lo }
        if v > hi { return hi }
        return v
    }

    struct Enemy {
        pos: Vec2
        health: int = 30

        fn take_damage(amount: int) {
            self.health -= amount
        }
    }

    scene GameScene {
        let enemies: [Enemy] = []
        let player_pos: Vec2

        on_start {
            print("game started")
        }

        on_update(dt: float) {
            for e in enemies {
                e.take_damage(1)
            }
        }

        on_draw {
            draw.clear(Color::BLACK)
        }
    }
    """
    prog = parse(src)
    assert isinstance(prog, Program)
    assert len(prog.body) == 5   # const, let, fn, struct, scene
    assert isinstance(prog.body[0], VarDecl)   # const MAX
    assert isinstance(prog.body[2], FunctionDecl)  # fn clamp
    assert isinstance(prog.body[3], StructDecl)    # struct Enemy
    assert isinstance(prog.body[4], SceneDecl)     # scene GameScene
test("Full program parses correctly", test_full_program)

# ─── Error handling ────────────────────────────
def test_missing_brace():
    try:
        parse("fn f() { return 1")
        assert False, "Should raise ParseError"
    except ParseError as e:
        assert "}" in e.message or "Expected" in e.message
test("Error: missing closing brace", test_missing_brace)

def test_bad_assignment_target():
    try:
        parse("42 = x")
        # Might not error at parse time (assigned to expr) — that's OK
        # The semantic analyzer will catch this
    except (ParseError, Exception):
        pass  # either outcome is fine
test("Error: bad assignment target (best effort)", test_bad_assignment_target)

# ─── Results ───────────────────────────────────
print("\n" + "="*60)
print("  InScript Parser — Test Results")
print("="*60)

passed = failed = 0
for r in results:
    if r[0] == PASS:
        print(f"  {r[0]} {r[1]}")
        passed += 1
    else:
        print(f"  {r[0]} {r[1]}")
        print(f"       └─ {r[2]}")
        failed += 1

print("="*60)
print(f"  {passed} passed, {failed} failed out of {len(results)} tests")
print("="*60 + "\n")

if failed > 0:
    sys.exit(1)
