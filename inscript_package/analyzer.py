# inscript/analyzer.py  — Phase 3: Semantic Analyzer + Type Checker
#
# Walks the AST and validates:
#   1. All names are declared before use
#   2. Types are compatible in operations
#   3. Return types match function signatures
#   4. Struct fields exist and have correct types
#   5. Break/continue only inside loops
#   6. No duplicate declarations in same scope
#
# On success  → returns a typed symbol table
# On failure  → raises SemanticError with line/col info

from __future__ import annotations
from typing import Dict, List, Optional, Set, Any
from ast_nodes import *
from errors import SemanticError


# ─────────────────────────────────────────────────────────────────────────────
# TYPE SYSTEM
# Built-in InScript types represented as strings internally.
# ─────────────────────────────────────────────────────────────────────────────

class InScriptType:
    """Represents an InScript type."""
    def __init__(self, name: str, params: list = None):
        self.name   = name
        self.params = params or []   # for generic types like Array<int>

    def __eq__(self, other):
        if not isinstance(other, InScriptType): return False
        return self.name == other.name and self.params == other.params

    def __repr__(self):
        if self.params:
            return f"{self.name}<{', '.join(str(p) for p in self.params)}>"
        return self.name

    def __hash__(self):
        return hash((self.name, tuple(self.params)))


# Singleton built-in types
T_INT    = InScriptType("int")
T_FLOAT  = InScriptType("float")
T_BOOL   = InScriptType("bool")
T_STRING = InScriptType("string")
T_VOID   = InScriptType("void")
T_NULL   = InScriptType("null")
T_ANY    = InScriptType("any")    # escape hatch — disables type checking

# Game-specific built-in types
T_VEC2   = InScriptType("Vec2")
T_VEC3   = InScriptType("Vec3")
T_VEC4   = InScriptType("Vec4")
T_COLOR  = InScriptType("Color")
T_RECT   = InScriptType("Rect")
T_TRANSFORM2D = InScriptType("Transform2D")
T_TRANSFORM3D = InScriptType("Transform3D")
T_TEXTURE = InScriptType("Texture")

BUILTIN_TYPES: Dict[str, InScriptType] = {
    # canonical names
    "int": T_INT, "float": T_FLOAT, "bool": T_BOOL,
    "string": T_STRING, "void": T_VOID, "null": T_NULL, "any": T_ANY,
    # common aliases
    "str": T_STRING, "boolean": T_BOOL, "number": T_FLOAT,
    "nil": T_NULL, "object": T_ANY, "auto": T_ANY,
    "Integer": T_INT, "Float": T_FLOAT, "String": T_STRING, "Bool": T_BOOL,
    # game types
    "Vec2": T_VEC2, "Vec3": T_VEC3, "Vec4": T_VEC4,
    "Color": T_COLOR, "Rect": T_RECT,
    "Transform2D": T_TRANSFORM2D, "Transform3D": T_TRANSFORM3D,
    "Texture": T_TEXTURE,
    # tuple / array shorthand
    "Tuple": T_ANY, "List": T_ANY, "Dict": T_ANY, "Map": T_ANY,
}

def array_type(elem: InScriptType) -> InScriptType:
    return InScriptType("Array", [elem])

def dict_type(key: InScriptType, val: InScriptType) -> InScriptType:
    return InScriptType("Dict", [key, val])

def is_numeric(t: InScriptType) -> bool:
    return t in (T_INT, T_FLOAT)

def is_vec(t: InScriptType) -> bool:
    return t.name in ("Vec2", "Vec3", "Vec4")

def numeric_result(a: InScriptType, b: InScriptType) -> InScriptType:
    """int op int → int; anything with float → float"""
    if a == T_FLOAT or b == T_FLOAT: return T_FLOAT
    return T_INT

def types_compatible(expected: InScriptType, got: InScriptType) -> bool:
    """True if `got` can be used where `expected` is required."""
    if expected == T_ANY or got == T_ANY: return True
    if expected == got: return True
    # int can widen to float
    if expected == T_FLOAT and got == T_INT: return True
    # null can be assigned to any type
    if got == T_NULL: return True
    # Array<X> compatible with Array<any> and vice versa
    if expected.name == "Array" and got.name == "Array": return True
    # Dict<K,V> compatible with Dict<any,any>
    if expected.name == "Dict" and got.name == "Dict": return True
    # User struct type vs any
    return False


# ─────────────────────────────────────────────────────────────────────────────
# SYMBOL  —  one entry in the symbol table
# ─────────────────────────────────────────────────────────────────────────────

class Symbol:
    def __init__(self, name: str, type_: InScriptType,
                 kind: str = "var",       # "var" | "const" | "fn" | "struct" | "scene"
                 is_const: bool = False,
                 fn_node: FunctionDecl = None,
                 struct_node: StructDecl = None,
                 line: int = 0, col: int = 0):
        self.name        = name
        self.type_       = type_
        self.kind        = kind
        self.is_const    = is_const
        self.fn_node     = fn_node       # for functions: the AST node
        self.struct_node = struct_node   # for structs: the AST node
        self.line        = line
        self.col         = col


# ─────────────────────────────────────────────────────────────────────────────
# SCOPE  —  one level of the scope chain
# ─────────────────────────────────────────────────────────────────────────────

class Scope:
    def __init__(self, parent: Optional["Scope"] = None, kind: str = "block"):
        self.parent:   Optional[Scope]   = parent
        self.kind:     str               = kind      # "global"|"fn"|"block"|"struct"|"scene"
        self.symbols:  Dict[str, Symbol] = {}

    def define(self, sym: Symbol, error_cb) -> None:
        if sym.name in self.symbols:
            existing = self.symbols[sym.name]
            error_cb(
                f"'{sym.name}' is already declared in this scope "
                f"(first declared at line {existing.line})",
                sym.line, sym.col
            )
        self.symbols[sym.name] = sym

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def lookup_local(self, name: str) -> Optional[Symbol]:
        return self.symbols.get(name)


# ─────────────────────────────────────────────────────────────────────────────
# SEMANTIC ANALYZER
# ─────────────────────────────────────────────────────────────────────────────

class Analyzer(Visitor):
    """
    Walks the AST in two passes:
      Pass 1: Register all top-level struct/scene/fn names (hoisting)
      Pass 2: Full type-checking walk
    """

    def __init__(self, source_lines: List[str] = None):
        self._src      = source_lines or []
        self._scope    = Scope(kind="global")
        self._warnings: List[str] = []

        # State for context-sensitive checks
        self._current_fn_return_type: Optional[InScriptType] = None
        self._loop_depth:  int  = 0
        self._in_scene:    bool = False
        self._in_match_arm: bool = False
        self._struct_defs: Dict[str, StructDecl] = {}

        # Pre-register built-in global functions
        self._register_builtins()

    def _src_line(self, line: int) -> str:
        return self._src[line - 1] if self._src and 0 < line <= len(self._src) else ""

    def _error(self, msg: str, line: int = 0, col: int = 0):
        raise SemanticError(msg, line, col, self._src_line(line))

    def _warn(self, msg: str, line: int = 0):
        self._warnings.append(f"Warning (line {line}): {msg}")

    def _define(self, sym: Symbol):
        self._scope.define(sym, self._error)

    def _lookup(self, name: str, line: int = 0, col: int = 0) -> Symbol:
        sym = self._scope.lookup(name)
        if sym is None:
            # Inside a match arm, unknown names may be ADT field bindings
            # injected at runtime — treat them as any rather than erroring
            if self._in_match_arm:
                return Symbol(name, T_ANY, kind="var")
            self._error(f"Undefined name: '{name}'", line, col)
        return sym

    def _resolve_type_ann(self, ann: Optional[TypeAnnotation]) -> InScriptType:
        """Convert a TypeAnnotation AST node into an InScriptType."""
        if ann is None:
            return T_ANY

        if ann.is_array:
            inner = self._resolve_type_ann(ann.generics[0]) if ann.generics else T_ANY
            return array_type(inner)

        if ann.is_dict:
            k = self._resolve_type_ann(ann.key_type) if ann.key_type else T_STRING
            v = self._resolve_type_ann(ann.generics[0]) if ann.generics else T_ANY
            return dict_type(k, v)

        if ann.name in BUILTIN_TYPES:
            return BUILTIN_TYPES[ann.name]

        # Check user-defined structs
        if ann.name in self._struct_defs:
            return InScriptType(ann.name)

        self._error(f"Unknown type: '{ann.name}'", ann.line, ann.col)

    def _push_scope(self, kind: str = "block") -> Scope:
        self._scope = Scope(parent=self._scope, kind=kind)
        return self._scope

    def _pop_scope(self) -> Scope:
        old = self._scope
        self._scope = self._scope.parent
        return old

    # ── Built-in registrations ────────────────────────────────────────────────

    def _register_builtins(self):
        """Pre-populate the global scope with built-in functions and constants."""
        builtins = [
            # print / output
            Symbol("print",   T_VOID,   kind="fn"),
            Symbol("println", T_VOID,   kind="fn"),
            # type inspection
            Symbol("typeof",  T_STRING, kind="fn"),
            Symbol("type",    T_STRING, kind="fn"),
            Symbol("is_nil",  T_BOOL,   kind="fn"),
            Symbol("is_null", T_BOOL,   kind="fn"),
            Symbol("isinstance", T_BOOL, kind="fn"),
            # math
            Symbol("sin",     T_FLOAT, kind="fn"),
            Symbol("cos",     T_FLOAT, kind="fn"),
            Symbol("tan",     T_FLOAT, kind="fn"),
            Symbol("sqrt",    T_FLOAT, kind="fn"),
            Symbol("abs",     T_FLOAT, kind="fn"),
            Symbol("floor",   T_INT,   kind="fn"),
            Symbol("ceil",    T_INT,   kind="fn"),
            Symbol("round",   T_INT,   kind="fn"),
            Symbol("clamp",   T_FLOAT, kind="fn"),
            Symbol("lerp",    T_FLOAT, kind="fn"),
            Symbol("min",     T_FLOAT, kind="fn"),
            Symbol("max",     T_FLOAT, kind="fn"),
            Symbol("pow",     T_FLOAT, kind="fn"),
            Symbol("log",     T_FLOAT, kind="fn"),
            Symbol("random",  T_FLOAT, kind="fn"),
            # collections
            Symbol("len",     T_INT,   kind="fn"),
            Symbol("range",   T_ANY,   kind="fn"),
            Symbol("next",    T_ANY,   kind="fn"),
            Symbol("has_key", T_BOOL,  kind="fn"),
            Symbol("keys",    T_ANY,   kind="fn"),
            Symbol("values",  T_ANY,   kind="fn"),
            Symbol("zip",     T_ANY,   kind="fn"),
            Symbol("map",     T_ANY,   kind="fn"),
            Symbol("filter",  T_ANY,   kind="fn"),
            Symbol("reduce",  T_ANY,   kind="fn"),
            Symbol("sorted",  T_ANY,   kind="fn"),
            Symbol("reversed",T_ANY,   kind="fn"),
            Symbol("enumerate",T_ANY,  kind="fn"),
            # Result types
            Symbol("Ok",      T_ANY,   kind="fn"),
            Symbol("Err",     T_ANY,   kind="fn"),
            # type conversions
            Symbol("int",     T_INT,   kind="fn"),
            Symbol("float",   T_FLOAT, kind="fn"),
            Symbol("string",  T_STRING, kind="fn"),
            Symbol("str",     T_STRING, kind="fn"),
            Symbol("bool",    T_BOOL,  kind="fn"),
            # I/O
            Symbol("input_str", T_STRING, kind="fn"),
            Symbol("read_file", T_STRING, kind="fn"),
            Symbol("write_file", T_VOID,  kind="fn"),
            # game built-ins (constructors / namespaces)
            Symbol("Vec2",    T_VEC2,  kind="fn"),
            Symbol("Vec3",    T_VEC3,  kind="fn"),
            Symbol("Vec4",    T_VEC4,  kind="fn"),
            Symbol("Color",   T_COLOR, kind="fn"),
            Symbol("Rect",    T_RECT,  kind="fn"),
            # global objects
            Symbol("input",   T_ANY,   kind="var"),
            Symbol("draw",    T_ANY,   kind="var"),
            Symbol("draw3d",  T_ANY,   kind="var"),
            Symbol("audio",   T_ANY,   kind="var"),
            Symbol("scene",   T_ANY,   kind="var"),
            Symbol("world",   T_ANY,   kind="var"),
            Symbol("network", T_ANY,   kind="var"),
            Symbol("navmesh", T_ANY,   kind="var"),
            Symbol("time",    T_ANY,   kind="var"),
        ]
        for sym in builtins:
            self._scope.symbols[sym.name] = sym

    # ── Main entry point ──────────────────────────────────────────────────────

    def analyze(self, program: Program) -> Dict[str, Symbol]:
        """
        Analyze a full program.
        Returns the global symbol table on success.
        Raises SemanticError on the first error found.
        """
        # Pass 1: hoist top-level names so they can reference each other
        self._hoist_top_level(program)
        # Pass 2: full type-checking walk
        self.visit(program)
        return self._scope.symbols

    def _hoist_top_level(self, program: Program):
        """Register structs, scenes, and top-level functions before checking bodies."""
        for node in program.body:
            if isinstance(node, StructDecl):
                self._struct_defs[node.name] = node
                self._scope.symbols[node.name] = Symbol(
                    node.name, InScriptType(node.name),
                    kind="struct", struct_node=node,
                    line=node.line, col=node.col
                )
            elif isinstance(node, FunctionDecl):
                ret  = self._resolve_type_ann(node.return_type)
                self._scope.symbols[node.name] = Symbol(
                    node.name, ret, kind="fn", fn_node=node,
                    line=node.line, col=node.col
                )
            elif isinstance(node, SceneDecl):
                self._scope.symbols[node.name] = Symbol(
                    node.name, T_ANY, kind="scene",
                    line=node.line, col=node.col
                )
            elif isinstance(node, EnumDecl):
                self._scope.symbols[node.name] = Symbol(
                    node.name, InScriptType(node.name), kind="enum",
                    line=node.line, col=node.col
                )

    # ── Visitor methods ───────────────────────────────────────────────────────

    def visit_Program(self, node: Program) -> InScriptType:
        for stmt in node.body:
            self.visit(stmt)
        return T_VOID

    # ── Declarations ──────────────────────────────────────────────────────────

    def visit_VarDecl(self, node: VarDecl) -> InScriptType:
        declared_type = self._resolve_type_ann(node.type_ann)
        init_type     = T_ANY

        if node.initializer:
            init_type = self.visit(node.initializer)
            if declared_type != T_ANY and not types_compatible(declared_type, init_type):
                self._error(
                    f"Type mismatch in declaration of '{node.name}': "
                    f"expected '{declared_type}', got '{init_type}'",
                    node.line, node.col
                )
        # Infer type from initializer if no annotation
        if declared_type == T_ANY and node.initializer:
            declared_type = init_type

        self._define(Symbol(
            node.name, declared_type,
            kind="const" if node.is_const else "var",
            is_const=node.is_const,
            line=node.line, col=node.col
        ))
        return declared_type

    def visit_TupleDestructureDecl(self, node) -> InScriptType:
        """let (a, b) = expr  — register each name as a variable."""
        if hasattr(node, "initializer") and node.initializer:
            self.visit(node.initializer)
        for name in node.names:
            self._define(Symbol(name, T_ANY, kind="var", line=node.line))
        return T_ANY

    def visit_DestructureDecl(self, node) -> InScriptType:
        """let [a, b] = arr  or  let {x, y} = obj — register each name."""
        if hasattr(node, "initializer") and node.initializer:
            self.visit(node.initializer)
        names = getattr(node, "names", []) or getattr(node, "targets", [])
        for name in names:
            if isinstance(name, str):
                self._define(Symbol(name, T_ANY, kind="var", line=node.line))
        return T_ANY

    def visit_FunctionDecl(self, node: FunctionDecl) -> InScriptType:
        ret_type = self._resolve_type_ann(node.return_type)

        # Register in current scope (if not already hoisted)
        if not self._scope.lookup_local(node.name):
            self._define(Symbol(
                node.name, ret_type, kind="fn",
                fn_node=node, line=node.line, col=node.col
            ))

        # Analyze body in a new scope
        self._push_scope("fn")
        prev_ret = self._current_fn_return_type
        self._current_fn_return_type = ret_type

        # Register parameters
        for param in node.params:
            p_type = self._resolve_type_ann(param.type_ann)
            self._define(Symbol(
                param.name, p_type, kind="var",
                line=param.line, col=param.col
            ))

        # Analyze body
        self.visit(node.body)

        self._current_fn_return_type = prev_ret
        self._pop_scope()
        return ret_type

    def visit_StructDecl(self, node: StructDecl) -> InScriptType:
        struct_type = InScriptType(node.name)
        self._push_scope("struct")

        # Register self
        self._define(Symbol("self", struct_type, kind="var", line=node.line))

        # Register fields
        for field in node.fields:
            f_type = self._resolve_type_ann(field.type_ann)
            self._define(Symbol(
                field.name, f_type, kind="var",
                line=field.line, col=field.col
            ))
            if field.default:
                default_type = self.visit(field.default)
                if not types_compatible(f_type, default_type):
                    self._error(
                        f"Struct field '{field.name}' default type mismatch: "
                        f"expected '{f_type}', got '{default_type}'",
                        field.line, field.col
                    )

        # Analyze methods
        for method in node.methods:
            self.visit_FunctionDecl(method)

        self._pop_scope()
        return struct_type

    def visit_SceneDecl(self, node: SceneDecl) -> InScriptType:
        self._push_scope("scene")
        self._in_scene = True

        # Register scene-level vars
        for var in node.vars:
            self.visit_VarDecl(var)

        # Analyze lifecycle hooks
        for hook in node.hooks:
            self._push_scope("fn")
            prev_ret = self._current_fn_return_type
            self._current_fn_return_type = T_VOID

            for param in hook.params:
                p_type = self._resolve_type_ann(param.type_ann)
                self._define(Symbol(param.name, p_type, "var",
                                    line=param.line, col=param.col))

            self.visit(hook.body)
            self._current_fn_return_type = prev_ret
            self._pop_scope()

        # Analyze scene methods
        for method in node.methods:
            self.visit_FunctionDecl(method)

        self._in_scene = False
        self._pop_scope()
        return T_VOID

    def visit_EnumDecl(self, node: EnumDecl) -> InScriptType:
        enum_type = InScriptType(node.name)
        for variant in node.variants:
            # Register each variant as a constant in the global scope
            self._scope.symbols[f"{node.name}::{variant.name}"] = Symbol(
                f"{node.name}::{variant.name}", enum_type, kind="const",
                line=variant.line, col=variant.col
            )
        return enum_type

    def visit_ImportDecl(self, node: ImportDecl) -> InScriptType:
        """Register imported symbols so the type checker knows about them."""
        try:
            import stdlib as _stdlib
            mod = _stdlib.load_module(node.path)
        except Exception:
            # Unknown module - skip analysis, interpreter will catch it
            return T_VOID

        if node.alias:
            self._define(Symbol(node.alias, T_ANY, kind="var",
                                line=node.line, col=node.col))
        elif node.names:
            for name in node.names:
                self._define(Symbol(name, T_ANY, kind="var",
                                    line=node.line, col=node.col))
        else:
            # import "math" — register all exported names
            for name in mod:
                if not self._scope.lookup_local(name):
                    self._scope.symbols[name] = Symbol(name, T_ANY, kind="var",
                                                        line=node.line, col=node.col)
        return T_VOID

    # ── Statements ────────────────────────────────────────────────────────────

    def visit_BlockStmt(self, node: BlockStmt) -> InScriptType:
        self._push_scope("block")
        for stmt in node.body:
            self.visit(stmt)
        self._pop_scope()
        return T_VOID

    def visit_ExprStmt(self, node: ExprStmt) -> InScriptType:
        return self.visit(node.expr)

    def visit_PrintStmt(self, node: PrintStmt) -> InScriptType:
        for arg in node.args:
            self.visit(arg)
        return T_VOID

    def visit_ReturnStmt(self, node: ReturnStmt) -> InScriptType:
        if self._current_fn_return_type is None:
            self._error("'return' outside of function", node.line, node.col)

        ret_type = T_VOID
        if node.value:
            ret_type = self.visit(node.value)

        if not types_compatible(self._current_fn_return_type, ret_type):
            self._error(
                f"Return type mismatch: function expects "
                f"'{self._current_fn_return_type}', got '{ret_type}'",
                node.line, node.col
            )
        return ret_type

    def visit_BreakStmt(self, node: BreakStmt) -> InScriptType:
        if self._loop_depth == 0:
            self._error("'break' outside of loop", node.line, node.col)
        return T_VOID

    def visit_ContinueStmt(self, node: ContinueStmt) -> InScriptType:
        if self._loop_depth == 0:
            self._error("'continue' outside of loop", node.line, node.col)
        return T_VOID

    def visit_IfStmt(self, node: IfStmt) -> InScriptType:
        cond_type = self.visit(node.condition)
        if cond_type not in (T_BOOL, T_ANY):
            self._warn(
                f"Condition expression has type '{cond_type}' (expected bool) — "
                f"non-bool conditions will be truthy/falsy at runtime",
                node.line
            )
        self.visit(node.then_branch)
        if node.else_branch:
            self.visit(node.else_branch)
        return T_VOID

    def visit_WhileStmt(self, node: WhileStmt) -> InScriptType:
        self.visit(node.condition)
        self._loop_depth += 1
        self.visit(node.body)
        self._loop_depth -= 1
        return T_VOID

    def visit_ForInStmt(self, node: ForInStmt) -> InScriptType:
        iter_type = self.visit(node.iterable)
        self._push_scope("block")

        # Infer element type from iterable type
        if isinstance(iter_type, InScriptType) and iter_type.name == "Array" and iter_type.params:
            elem_type = iter_type.params[0]
        elif isinstance(iter_type, InScriptType) and iter_type.name in ("Range",):
            elem_type = T_INT
        else:
            elem_type = T_ANY  # unknown iterable

        self._define(Symbol(node.var_name, elem_type, "var",
                            line=node.line, col=node.col))
        self._loop_depth += 1
        self.visit(node.body)
        self._loop_depth -= 1
        self._pop_scope()
        return T_VOID

    def visit_MatchStmt(self, node: MatchStmt) -> InScriptType:
        self.visit(node.subject)
        for arm in node.arms:
            self._push_scope("match_arm")
            if arm.binding:
                self._define(Symbol(arm.binding, T_ANY, kind="var", line=node.line))
            if arm.pattern:
                self.visit(arm.pattern)
            if arm.guard:
                self.visit(arm.guard)
            prev = self._in_match_arm
            self._in_match_arm = True
            self.visit(arm.body)
            self._in_match_arm = prev
            self._pop_scope()
        return T_VOID

    def visit_ThrowStmt(self, node: ThrowStmt) -> InScriptType:
        self.visit(node.value)
        return T_VOID

    def visit_TryCatchStmt(self, node: TryCatchStmt) -> InScriptType:
        self.visit(node.body)
        self._push_scope("block")
        if node.catch_var:
            catch_t = self._resolve_type_ann(node.catch_type) if node.catch_type else T_ANY
            self._define(Symbol(node.catch_var, catch_t, "var", line=node.line))
        self.visit(node.handler)
        self._pop_scope()
        return T_VOID

    # ── Expressions ───────────────────────────────────────────────────────────

    def visit_IntLiteralExpr(self, node: IntLiteralExpr)   -> InScriptType: return T_INT
    def visit_FloatLiteralExpr(self, node: FloatLiteralExpr) -> InScriptType: return T_FLOAT
    def visit_StringLiteralExpr(self, node: StringLiteralExpr) -> InScriptType: return T_STRING
    def visit_BoolLiteralExpr(self, node: BoolLiteralExpr) -> InScriptType: return T_BOOL
    def visit_NullLiteralExpr(self, node: NullLiteralExpr) -> InScriptType: return T_NULL

    def visit_IdentExpr(self, node: IdentExpr) -> InScriptType:
        sym = self._lookup(node.name, node.line, node.col)
        return sym.type_

    def visit_ArrayLiteralExpr(self, node: ArrayLiteralExpr) -> InScriptType:
        if not node.elements:
            return array_type(T_ANY)
        first_type = self.visit(node.elements[0])
        for elem in node.elements[1:]:
            et = self.visit(elem)
            if not types_compatible(first_type, et):
                self._warn(f"Mixed types in array literal: '{first_type}' and '{et}'",
                           node.line)
        return array_type(first_type)

    def visit_DictLiteralExpr(self, node: DictLiteralExpr) -> InScriptType:
        if not node.pairs:
            return dict_type(T_ANY, T_ANY)
        k_type = self.visit(node.pairs[0][0])
        v_type = self.visit(node.pairs[0][1])
        for k, v in node.pairs[1:]:
            self.visit(k); self.visit(v)
        return dict_type(k_type, v_type)

    def visit_BinaryExpr(self, node: BinaryExpr) -> InScriptType:
        left  = self.visit(node.left)
        right = self.visit(node.right)
        op    = node.op

        # Comparison operators always return bool
        if op in ("==", "!=", "<", ">", "<=", ">="):
            return T_BOOL

        # Logical operators require bool (but we allow any and warn)
        if op in ("&&", "||"):
            return T_BOOL

        # Arithmetic
        if op in ("+", "-", "*", "/", "%", "**"):
            # String concatenation — any + string, or string + any → string
            if op == "+" and (left == T_STRING or right == T_STRING):
                return T_STRING
            if is_numeric(left) and is_numeric(right):
                return numeric_result(left, right)
            # Vector arithmetic
            if is_vec(left) and is_vec(right) and left == right:
                return left
            if is_vec(left) and is_numeric(right):
                return left
            if is_numeric(left) and is_vec(right):
                return right
            if left == T_ANY or right == T_ANY:
                return T_ANY
            self._error(
                f"Operator '{op}' cannot be applied to types '{left}' and '{right}'",
                node.line, node.col
            )

        return T_ANY

    def visit_UnaryExpr(self, node: UnaryExpr) -> InScriptType:
        operand = self.visit(node.operand)
        if node.op == "!":
            return T_BOOL
        if node.op == "-":
            if is_numeric(operand) or is_vec(operand) or operand == T_ANY:
                return operand
            self._error(f"Unary '-' cannot be applied to type '{operand}'",
                        node.line, node.col)
        return T_ANY

    def visit_AssignExpr(self, node: AssignExpr) -> InScriptType:
        val_type = self.visit(node.value)

        if isinstance(node.target, IdentExpr):
            sym = self._lookup(node.target.name, node.line, node.col)
            if sym.is_const:
                self._error(f"Cannot assign to constant '{sym.name}'",
                            node.line, node.col)
            if not types_compatible(sym.type_, val_type):
                self._error(
                    f"Type mismatch in assignment to '{sym.name}': "
                    f"expected '{sym.type_}', got '{val_type}'",
                    node.line, node.col
                )
            return sym.type_
        else:
            # Attribute or index assignment — check the target is valid
            self.visit(node.target)
            return val_type

    def visit_SetAttrExpr(self, node: SetAttrExpr) -> InScriptType:
        self.visit(node.obj)
        return self.visit(node.value)

    def visit_SetIndexExpr(self, node: SetIndexExpr) -> InScriptType:
        self.visit(node.obj)
        self.visit(node.index)
        return self.visit(node.value)

    def visit_GetAttrExpr(self, node: GetAttrExpr) -> InScriptType:
        obj_type = self.visit(node.obj)

        # If the object is a known struct type, validate field/method access
        # Walk the full inheritance chain: child → parent → grandparent
        if obj_type.name in self._struct_defs:
            name = obj_type.name
            while name and name in self._struct_defs:
                struct = self._struct_defs[name]
                for field in struct.fields:
                    if field.name == node.attr:
                        return self._resolve_type_ann(field.type_ann)
                for method in struct.methods:
                    if method.name == node.attr:
                        return self._resolve_type_ann(method.return_type)
                name = getattr(struct, "parent_name", None)
            self._error(
                f"Struct '{obj_type.name}' has no field or method '{node.attr}'",
                node.line, node.col
            )

        # For built-in game types, return any (we trust the runtime)
        return T_ANY

    def visit_IndexExpr(self, node: IndexExpr) -> InScriptType:
        obj_type = self.visit(node.obj)
        self.visit(node.index)
        if obj_type.name == "Array" and obj_type.params:
            return obj_type.params[0]
        if obj_type.name == "Dict" and obj_type.params:
            return obj_type.params[1] if len(obj_type.params) > 1 else T_ANY
        return T_ANY

    def visit_CallExpr(self, node: CallExpr) -> InScriptType:
        callee_type = self.visit(node.callee)
        for arg in node.args:
            self.visit(arg.value)

        # If callee is a known function, return its declared return type
        if isinstance(node.callee, IdentExpr):
            sym = self._scope.lookup(node.callee.name)
            if sym and sym.kind == "fn" and sym.fn_node:
                return self._resolve_type_ann(sym.fn_node.return_type)
            if sym:
                # Constructor call for struct
                if sym.kind == "struct":
                    return InScriptType(sym.name)
                return sym.type_

        if isinstance(node.callee, GetAttrExpr):
            # method call — return any for now
            return T_ANY

        return T_ANY

    def visit_NamespaceAccessExpr(self, node: NamespaceAccessExpr) -> InScriptType:
        # Color::RED, Vec2::ZERO, etc.  — return T_ANY for now
        return T_ANY

    def visit_StructInitExpr(self, node: StructInitExpr) -> InScriptType:
        if node.struct_name not in self._struct_defs:
            self._error(
                f"Unknown struct: '{node.struct_name}'",
                node.line, node.col
            )
        # Collect fields from the full inheritance chain
        field_map = {}
        chain = []
        name = node.struct_name
        while name and name in self._struct_defs:
            chain.append(self._struct_defs[name])
            parent = getattr(self._struct_defs[name], "parent_name", None)
            name = parent
        for struct in reversed(chain):      # parent fields first, child overrides
            for f in struct.fields:
                field_map[f.name] = f

        for field_name, value_node in node.fields:
            if field_name not in field_map:
                self._error(
                    f"Struct '{node.struct_name}' has no field '{field_name}'",
                    node.line, node.col
                )
            val_type = self.visit(value_node)
            expected = self._resolve_type_ann(field_map[field_name].type_ann)
            if not types_compatible(expected, val_type):
                self._error(
                    f"Struct field '{field_name}': expected '{expected}', got '{val_type}'",
                    node.line, node.col
                )

        return InScriptType(node.struct_name)

    def visit_RangeExpr(self, node: RangeExpr) -> InScriptType:
        s = self.visit(node.start)
        e = self.visit(node.end)
        if s not in (T_INT, T_ANY) or e not in (T_INT, T_ANY):
            self._error(f"Range bounds must be int, got '{s}' and '{e}'",
                        node.line, node.col)
        return InScriptType("Range", [T_INT])

    def visit_LambdaExpr(self, node: LambdaExpr) -> InScriptType:
        self._push_scope("fn")
        prev_ret = self._current_fn_return_type
        ret_type = self._resolve_type_ann(node.return_type)
        self._current_fn_return_type = ret_type

        for param in node.params:
            p_type = self._resolve_type_ann(param.type_ann)
            self._define(Symbol(param.name, p_type, "var",
                                line=param.line, col=param.col))
        self.visit(node.body)

        self._current_fn_return_type = prev_ret
        self._pop_scope()
        return InScriptType("Function")

    def visit_AwaitExpr(self, node: AwaitExpr) -> InScriptType:
        return self.visit(node.expr)

    def visit_SpawnExpr(self, node: SpawnExpr) -> InScriptType:
        return T_ANY   # entity type

    def visit_WaitStmt(self, node: WaitStmt) -> InScriptType:
        dur = self.visit(node.duration)
        if not types_compatible(T_FLOAT, dur):
            self._error(f"'wait' expects a float duration, got '{dur}'",
                        node.line, node.col)
        return T_VOID

    def visit_AIDecl(self, node: AIDecl) -> InScriptType:
        for state in node.states:
            self._push_scope("fn")
            for hook in state.hooks:
                self._push_scope("fn")
                prev_ret = self._current_fn_return_type
                self._current_fn_return_type = T_VOID
                for param in hook.params:
                    p_type = self._resolve_type_ann(param.type_ann)
                    self._define(Symbol(param.name, p_type, "var", line=param.line))
                self.visit(hook.body)
                self._current_fn_return_type = prev_ret
                self._pop_scope()
            self._pop_scope()
        return T_VOID

    def visit_ShaderDecl(self, node: ShaderDecl) -> InScriptType:
        return T_VOID  # Shader analysis is Phase 14

    def visit_MatchArm(self, node: MatchArm) -> InScriptType:
        if node.pattern:
            self.visit(node.pattern)
        self.visit(node.body)
        return T_VOID

    def generic_visit(self, node: Node) -> InScriptType:
        # Silently pass through nodes we haven't handled yet
        return T_ANY


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def analyze(program: Program, source: str = "") -> Dict[str, Symbol]:
    """Run the semantic analyzer on a parsed program. Returns symbol table."""
    src_lines = source.splitlines() if source else []
    return Analyzer(src_lines).analyze(program)
