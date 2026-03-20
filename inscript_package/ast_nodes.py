# inscript/ast_nodes.py
# Phase 2: Abstract Syntax Tree Node Definitions
#
# Every construct in InScript source code maps to one of these nodes.
# The Parser builds a tree of these nodes. The Interpreter/Compiler walks the tree.
#
# Convention:
#   - Statement nodes  → classes ending in "Stmt"
#   - Expression nodes → classes ending in "Expr"
#   - Declaration nodes → classes ending in "Decl"
#   - Top-level node   → Program

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Any


# ─────────────────────────────────────────────────────────────────────────────
# BASE NODE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Node:
    line: int = field(default=0, repr=False, kw_only=True)
    col:  int = field(default=0, repr=False, kw_only=True)


# ─────────────────────────────────────────────────────────────────────────────
# PROGRAM  (root of every InScript file)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Program(Node):
    """Root node. Contains all top-level statements."""
    body: List[Node] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# TYPE ANNOTATIONS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TypeAnnotation(Node):
    name:      str
    generics:  List["TypeAnnotation"] = field(default_factory=list)
    is_array:  bool = False
    is_dict:   bool = False
    key_type:  Optional["TypeAnnotation"] = None
    nullable:  bool = False


# ─────────────────────────────────────────────────────────────────────────────
# LITERAL EXPRESSIONS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class IntLiteralExpr(Node):
    value: int

@dataclass
class FloatLiteralExpr(Node):
    value: float

@dataclass
class StringLiteralExpr(Node):
    value: str

@dataclass
class BoolLiteralExpr(Node):
    value: bool

@dataclass
class NullLiteralExpr(Node):
    pass

@dataclass
class ArrayLiteralExpr(Node):
    """[1, 2, 3]"""
    elements: List[Node] = field(default_factory=list)

@dataclass
class DictLiteralExpr(Node):
    """{"key": value, ...}  — list of (key_expr, value_expr) tuples"""
    pairs: List[tuple] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# IDENTIFIER + ACCESS EXPRESSIONS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class IdentExpr(Node):
    name: str

@dataclass
class GetAttrExpr(Node):
    """player.health"""
    obj:  Node
    attr: str

@dataclass
class SetAttrExpr(Node):
    """player.health = 100"""
    obj:   Node
    attr:  str
    value: Node

@dataclass
class IndexExpr(Node):
    """arr[0]"""
    obj:   Node
    index: Node

@dataclass
class SetIndexExpr(Node):
    """arr[0] = 5"""
    obj:   Node
    index: Node
    value: Node

@dataclass
class NamespaceAccessExpr(Node):
    """Color::RED"""
    namespace: str
    member:    str


# ─────────────────────────────────────────────────────────────────────────────
# OPERATOR EXPRESSIONS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BinaryExpr(Node):
    left:  Node
    op:    str
    right: Node

@dataclass
class UnaryExpr(Node):
    op:      str
    operand: Node

@dataclass
class TernaryExpr(Node):
    """condition ? then_expr : else_expr"""
    condition: Node
    then_expr: Node
    else_expr: Node


# ─────────────────────────────────────────────────────────────────────────────
# ASSIGNMENT EXPRESSIONS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AssignExpr(Node):
    """x = 5  |  x += 3  |  arr[0] = 9  |  obj.field = v"""
    target: Node
    op:     str
    value:  Node


# ─────────────────────────────────────────────────────────────────────────────
# CALL + LAMBDA
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Argument(Node):
    value: Node
    name:  Optional[str] = None   # None = positional

@dataclass
class CallExpr(Node):
    callee: Node
    args:   List[Argument] = field(default_factory=list)

@dataclass
class LambdaExpr(Node):
    """|x, y| x + y   or   |x: int| -> int { return x * 2 }"""
    params:      List["Param"]
    return_type: Optional[TypeAnnotation]
    body:        Node   # BlockStmt or single expression (implicit return)


# ─────────────────────────────────────────────────────────────────────────────
# RANGE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RangeExpr(Node):
    """0..10 (exclusive)  |  0..=10 (inclusive)"""
    start:     Node
    end:       Node
    inclusive: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# STATEMENTS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BlockStmt(Node):
    body: List[Node] = field(default_factory=list)

@dataclass
class ExprStmt(Node):
    expr: Node

@dataclass
class ReturnStmt(Node):
    value: Optional[Node] = None

@dataclass
class BreakStmt(Node):
    label: Optional[str] = None   # labeled break: break outer

@dataclass
class ContinueStmt(Node):
    label: Optional[str] = None   # labeled continue: continue outer

@dataclass
class PrintStmt(Node):
    """Built-in print(...) statement."""
    args: List[Node] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# DECLARATIONS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VarDecl(Node):
    """let x: int = 5   |   const MAX = 100   |   sync let pos: Vec2"""
    name:        str
    is_const:    bool
    type_ann:    Optional[TypeAnnotation]
    initializer: Optional[Node]
    is_sync:     bool = False

@dataclass
class Param(Node):
    """Function parameter: `name: type [= default]`"""
    name:     str
    type_ann: Optional[TypeAnnotation]
    default:  Optional[Node] = None

@dataclass
class FunctionDecl(Node):
    """fn name(params) -> return_type { body }"""
    name:        str
    params:      List[Param]
    return_type: Optional[TypeAnnotation]
    body:        "BlockStmt"
    is_method:   bool = False
    is_rpc:      bool = False

@dataclass
class StructField(Node):
    """health: int = 100"""
    name:     str
    type_ann: TypeAnnotation
    default:  Optional[Node] = None
    is_priv:  bool = False   # pub/priv modifier

@dataclass
class StructDecl(Node):
    """struct Player { fields... methods... }
    struct Dog extends Animal implements Drawable with Serializable { ... }
    struct Stack<T> { ... }  (generic)"""
    name:           str
    fields:         List[StructField]
    methods:        List[FunctionDecl]
    parent_name:    Optional[str] = None
    static_methods: List[FunctionDecl] = None
    interfaces:     List[str] = None
    mixins:         List[str] = None
    static_fields:  List[StructField] = None   # BUG-14: static TYPE fields
    properties:     List["PropertyDecl"] = None   # get/set accessor pairs
    type_params:    List[str] = None              # generic type parameters e.g. ["T", "U"]
    operators:      List["OperatorDecl"] = None   # Phase 7: operator overloads

    def __post_init__(self):
        if self.static_methods is None: self.static_methods = []
        if self.interfaces     is None: self.interfaces     = []
        if self.mixins         is None: self.mixins         = []
        if self.properties     is None: self.properties     = []
        if self.type_params    is None: self.type_params    = []
        if self.operators      is None: self.operators      = []

@dataclass
class StructInitExpr(Node):
    """Player { pos: Vec2(0, 0), health: 100 }"""
    struct_name: str
    fields:      List[tuple]   # [(field_name, value_expr), ...]


@dataclass
class OperatorDecl(Node):
    """Phase 7: operator +(other: Vec2) -> Vec2 { ... }"""
    op_symbol:  str          # '+', '-', '*', '==', 'str', 'len', '[]', etc.
    params:     List["Param"]
    body:       Node
    return_type: Optional["TypeAnnotation"] = None
    is_unary:   bool = False  # True for unary -, unary !


# ─────────────────────────────────────────────────────────────────────────────
# CONTROL FLOW
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class IfStmt(Node):
    """if cond { ... } else if ... { ... } else { ... }"""
    condition:   Node
    then_branch: "BlockStmt"
    else_branch: Optional[Node] = None   # IfStmt | BlockStmt | None

@dataclass
class WhileStmt(Node):
    condition:   Node
    body:        "BlockStmt"
    else_branch: Optional["BlockStmt"] = None  # else { } runs if loop never executed

@dataclass
class DoWhileStmt(Node):
    """do { body } while condition"""
    body:      "BlockStmt"
    condition: Node

@dataclass
class ForInStmt(Node):
    """for item in iterable { body } [else { }]"""
    var_name:    str
    iterable:    Node
    body:        "BlockStmt"
    else_branch: Optional["BlockStmt"] = None  # else { } runs if no break occurred

@dataclass
class MatchArm(Node):
    pattern:     Optional[Node]   # None = wildcard _
    body:        "BlockStmt"
    guard:       Optional[Node] = None    # if condition: case x if x > 0 { ... }
    binding:     Optional[str]  = None   # case h if h <= 0 { ... } — 'h' bound to subject

@dataclass
class MatchStmt(Node):
    subject: Node
    arms:    List[MatchArm]


# ─────────────────────────────────────────────────────────────────────────────
# SCENE DECLARATION
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LifecycleHook(Node):
    """on_start { }  |  on_update(dt: float) { }  |  on_draw { }"""
    hook_type: str          # "on_start" | "on_update" | "on_draw" | "on_exit"
    params:    List[Param]
    body:      "BlockStmt"

@dataclass
class SceneDecl(Node):
    """scene GameScene { vars... hooks... methods... }"""
    name:    str
    vars:    List[VarDecl]
    hooks:   List[LifecycleHook]
    methods: List[FunctionDecl]


# ─────────────────────────────────────────────────────────────────────────────
# AI DECLARATION
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AIState(Node):
    name:  str
    hooks: List[LifecycleHook]

@dataclass
class AIDecl(Node):
    """ai ZombieAI { state Idle { ... } state Chase { ... } }"""
    name:   str
    states: List[AIState]


# ─────────────────────────────────────────────────────────────────────────────
# SHADER DECLARATION
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ShaderUniform(Node):
    """uniform time: float = 0.0"""
    name:     str
    type_ann: TypeAnnotation
    default:  Optional[Node] = None

@dataclass
class ShaderDecl(Node):
    """shader GlowShader { uniforms... vertex { ... } fragment { ... } }"""
    name:     str
    uniforms: List[ShaderUniform]
    vertex:   Optional[FunctionDecl]
    fragment: Optional[FunctionDecl]


# ─────────────────────────────────────────────────────────────────────────────
# IMPORT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ImportDecl(Node):
    """import "physics"  |  from "ui" import Button, Label  |  import "x" as X"""
    path:  str
    names: List[str]
    alias: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# VISITOR PATTERN
# ─────────────────────────────────────────────────────────────────────────────

class Visitor:
    """
    Subclass this in the Interpreter, Analyzer, Compiler.
    Call `visit(node)` to dispatch to `visit_ClassName(node)`.
    """

    def visit(self, node: Node) -> Any:
        method = getattr(self, f"visit_{type(node).__name__}", self.generic_visit)
        return method(node)

    def generic_visit(self, node: Node) -> Any:
        raise NotImplementedError(
            f"{type(self).__name__} has no handler for node type '{type(node).__name__}'"
        )


# ─────────────────────────────────────────────────────────────────────────────
# ADDITIONAL NODES (added in review pass)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ThrowStmt(Node):
    """throw ErrorExpr"""
    value: Node

@dataclass
class TryCatchStmt(Node):
    """try { body } catch(e: T) { ... } catch e { ... } — multiple catch clauses supported"""
    body:         "BlockStmt"
    catch_var:    Optional[str]                # kept for single-catch backwards compat
    catch_type:   Optional[TypeAnnotation]
    handler:      "BlockStmt"
    catch_clauses: Optional[List[dict]] = None # [{"var":..,"type":..,"handler":..}]
    finally_body:  Optional["BlockStmt"] = None  # BUG-12 fix

@dataclass
class TryExpr(Node):
    """let x = try { value_expr } catch e { fallback_expr } — try as expression"""
    body:      "BlockStmt"
    catch_var: Optional[str]
    handler:   "BlockStmt"

@dataclass
class SpawnExpr(Node):
    """spawn Entity { components... }"""
    entity_name: str
    components:  List[tuple]   # [(component_name, {field: val}), ...]

@dataclass
class WaitStmt(Node):
    """wait(seconds)  — pause coroutine in scene hooks"""
    duration: Node

@dataclass
class EnumVariant(Node):
    name:   str
    value:  Optional[Node] = None
    fields: List[tuple] = None   # ADT: [("radius", TypeAnnotation), ...]

    def __post_init__(self):
        if self.fields is None: self.fields = []

@dataclass
class EnumDecl(Node):
    """enum Direction { North, South, East, West }
    enum Shape { Circle(r: float), Rect(w: float, h: float) }"""
    name:     str
    variants: List[EnumVariant]

@dataclass
class InterfaceMethod(Node):
    name:        str
    params:      List["Param"]
    return_type: Optional["TypeAnnotation"]

@dataclass
class InterfaceDecl(Node):
    """interface Drawable { fn draw() }"""
    name:    str
    methods: List[FunctionDecl]
    parents: List[str] = None   # extends OtherInterface

    def __post_init__(self):
        if self.parents is None: self.parents = []

@dataclass
class ImplDecl(Node):
    """impl Drawable for Player { fn draw() { ... } }"""
    trait_name:  str
    struct_name: str
    methods:     List["FunctionDecl"]

@dataclass
class MixinDecl(Node):
    """mixin Serializable { fn to_json() { ... } }"""
    name:    str
    methods: List[FunctionDecl]

@dataclass
class PropertyDecl(Node):
    """get radius() -> float { return self._radius }
    set radius(v: float)  { self._radius = max(0.0, v) }"""
    name:         str
    getter_body:  Optional["BlockStmt"]  = None
    setter_body:  Optional["BlockStmt"]  = None
    setter_param: Optional[str]          = None   # name of the value parameter
    return_type:  Optional["TypeAnnotation"] = None

@dataclass
class RangeExpr(Node):
    """0..10 (exclusive)  |  0..=10 (inclusive)"""
    start:     Node
    end:       Node
    inclusive: bool = False

@dataclass
class LambdaExpr(Node):
    """|x, y| x + y   or   |x: int| -> int { return x * 2 }"""
    params:      List["Param"]
    return_type: Optional["TypeAnnotation"]
    body:        Node

@dataclass
class AsyncFnDecl(Node):
    """async fn fetch() -> string { await http.get(...) }"""
    fn: "FunctionDecl"

@dataclass
class AwaitExpr(Node):
    """await some_async_call()"""
    expr: Node

@dataclass
class YieldStmt(Node):
    """yield value  — emits a value from a generator function"""
    value: Optional[Node] = None

@dataclass
class GeneratorFnDecl(Node):
    """fn* counter(n) { yield i }  — generator function"""
    name:        str
    params:      List["Param"]
    return_type: Optional["TypeAnnotation"]
    body:        "BlockStmt"
    is_method:   bool = False

# ─────────────────────────────────────────────────────────────────────────────
# NEW NODES — Phase 31 Bug Fixes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FStringExpr(Node):
    """f\"Hello {name}, you are {age} years old\"
    template is the raw string; parts are alternating literals and exprs."""
    template: str   # raw template text (e.g. "Hello {name}!")

@dataclass
class DestructureDecl(Node):
    """let [a, b, c] = arr   |   let {x, y} = point"""
    names:       List[str]       # variable names to bind
    is_object:   bool            # True = {x,y}, False = [a,b,c]
    is_const:    bool
    initializer: Node
    aliases:     List[str] = None  # for {x: newName}

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []

@dataclass
class SpreadExpr(Node):
    """...args  — used in function calls to expand array"""
    expr: Node

@dataclass
class OptChainExpr(Node):
    """obj?.field   or   obj?.method()"""
    obj:    Node
    member: str

@dataclass
class NullishExpr(Node):
    """left ?? right  — returns right if left is null/None"""
    left:  Node
    right: Node

@dataclass
class PipeExpr(Node):
    """value |> fn  — passes value as first arg to fn"""
    value: Node
    fn:    Node

@dataclass
class LabeledStmt(Node):
    """outer: for i in range(n) { break outer }"""
    label: str
    stmt:  Node

@dataclass
class ComptimeExpr(Node):
    """comptime { expr }  — evaluated at parse/first-run time, result cached as constant"""
    body: "BlockStmt"

@dataclass
class PropagateExpr(Node):
    """expr?  — propagates Err upward from a Result, unwraps Ok"""
    expr: Node


@dataclass
class TupleExpr(Node):
    """(a, b, c)  — tuple literal; used for multiple return values"""
    elements: List[Node]

@dataclass
class TupleDestructureDecl(Node):
    """let (q, r) = divmod(17, 5)"""
    names:       List[str]
    initializer: "Node"
    is_const:    bool = False

@dataclass
class ListComprehensionExpr(Node):
    """[expr for var in iterable if condition]
    or nested: [expr for x in xs for y in ys if cond]
    clauses is a list of (var, iterable, optional_condition) tuples represented as dicts.
    For backwards compat: var/iterable/condition fields hold the FIRST clause."""
    expr:      "Node"
    var:       str
    iterable:  "Node"
    condition: Optional["Node"] = None
    extra_clauses: list = field(default_factory=list)  # [{"var","iterable","condition"}, ...]

    def __post_init__(self):
        if self.extra_clauses is None:
            self.extra_clauses = []

@dataclass
class DictComprehensionExpr(Node):
    """{key_expr: val_expr for var in iterable if condition}"""
    key_expr:  "Node"
    val_expr:  "Node"
    var:       str
    iterable:  "Node"
    condition: Optional["Node"] = None

@dataclass
class CastExpr(Node):
    """expr as Type — explicit type cast: 'let n = \"5\" as int'"""
    expr:      "Node"
    cast_type: str    # "int", "float", "string", "bool"

@dataclass
class IsExpr(Node):
    """expr is Type — runtime type check: 'if x is int { }'"""
    expr:       "Node"
    check_type: str   # "int", "float", "string", "bool", "nil", struct name

@dataclass
class ExportDecl(Node):
    """export fn foo() / export struct Bar / export const X = ...
    Wraps any declaration and marks it as publicly exported."""
    decl: "Node"

@dataclass
class DecoratedDecl(Node):
    """@decorator(args) fn foo() { } — decorator wrapping a declaration."""
    decorators: list   # [(name_str, [arg_node, ...]), ...]
    target: "Node"     # FnDecl, StructDecl, or any other declaration

@dataclass
class SelectStmt(Node):
    """select { case v = ch.recv() { body } case ch.send(x) { body } case timeout(t) { body } }
    Each clause: {"kind": "recv"/"send"/"timeout", "var":str|None, "channel":expr|None, "value":expr|None, "duration":expr|None, "body":BlockStmt}
    """
    clauses: list   # list of clause dicts
