# inscript/parser.py
# Phase 2: Recursive Descent Parser
#
# Turns a flat list of Tokens (from the Lexer) into an Abstract Syntax Tree (AST).
#
# Operator Precedence (lowest → highest):
#   1.  Assignment:      =  +=  -=  *=  /=
#   2.  Ternary:         ? :
#   3.  Logical OR:      ||
#   4.  Logical AND:     &&
#   5.  Equality:        ==  !=
#   6.  Comparison:      <  >  <=  >=
#   7.  Addition:        +  -
#   8.  Multiplication:  *  /  %
#   9.  Power:           **
#   10. Unary:           -  !
#   11. Postfix:         .attr  [index]  (call)
#   12. Primary:         literals, identifiers, (grouped), [array], {dict}

from __future__ import annotations
from typing import List, Optional
from lexer import Token, TT, tokenize
from ast_nodes import *
from errors import ParseError


class Parser:
    """
    Recursive descent parser for InScript.

    Usage:
        parser = Parser(tokens)
        ast = parser.parse()   # returns a Program node
    """

    def __init__(self, tokens: List[Token], source_lines: List[str] = None):
        self.tokens       = tokens
        self.pos          = 0
        self._src_lines   = source_lines or []

    # ─────────────────────────────────────────────
    # UTILITIES
    # ─────────────────────────────────────────────

    @property
    def current(self) -> Token:
        return self.tokens[self.pos]

    @property
    def peek(self) -> Token:
        idx = self.pos + 1
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

    def peek_at(self, offset: int) -> Token:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

    def is_at_end(self) -> bool:
        return self.current.type == TT.EOF

    def check(self, *types: TT) -> bool:
        return self.current.type in types

    def match(self, *types: TT) -> bool:
        """Consume current token if it matches any of the given types."""
        if self.current.type in types:
            self.pos += 1
            return True
        return False

    def advance(self) -> Token:
        """Consume and return the current token."""
        tok = self.current
        if not self.is_at_end():
            self.pos += 1
        return tok

    def expect(self, type: TT, msg: str = None) -> Token:
        """Consume the current token if it matches type, else raise ParseError."""
        if self.current.type == type:
            return self.advance()
        error_msg = msg or f"Expected '{type.name}' but got '{self.current.type.name}' ({self.current.value!r})"
        self._error(error_msg)

    def expect_ident(self, msg: str = None) -> str:
        """Expect an identifier and return its name string."""
        tok = self.expect(TT.IDENT, msg or "Expected identifier")
        return tok.value

    def _error(self, msg: str, tok: Token = None) -> None:
        t = tok or self.current
        src = self._src_lines[t.line - 1] if self._src_lines and 0 < t.line <= len(self._src_lines) else ""
        raise ParseError(msg, t.line, t.col, src)

    def _pos(self) -> tuple:
        """Return (line, col) of current token."""
        return self.current.line, self.current.col

    # ─────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ─────────────────────────────────────────────

    def parse(self) -> Program:
        """Parse the full program and return the root AST node."""
        line, col = self._pos()
        body = []
        while not self.is_at_end():
            stmt = self.parse_top_level()
            if stmt is not None:
                body.append(stmt)
        return Program(body=body, line=line, col=col)

    def parse_top_level(self) -> Optional[Node]:
        """Parse one top-level declaration or statement."""
        # Skip stray semicolons
        if self.match(TT.SEMICOLON):
            return None

        tok = self.current

        # --- Import ---
        if tok.type == TT.IMPORT:
            return self.parse_import()
        if tok.type == TT.FROM:
            return self.parse_from_import()
        # --- Try / Catch ---
        if tok.type == TT.TRY:
            return self.parse_try_catch()

        # --- Throw ---
        if tok.type == TT.THROW:
            return self.parse_throw()

        # --- Async/Await ---
        if tok.type == TT.ASYNC:
            return self.parse_async_fn()

        # --- Await expr ---
        if tok.type == TT.AWAIT:
            return self.parse_expr_stmt()

        # --- Sync variable ---
        if tok.type == TT.IDENT and tok.value == "sync":
            return self.parse_sync_var()

        # --- RPC function ---
        if tok.type == TT.IDENT and tok.value == "rpc":
            return self.parse_rpc_fn()

        # --- Let / Const ---
        if tok.type in (TT.LET, TT.CONST):
            return self.parse_var_decl()

        # --- Function ---
        if tok.type == TT.FN:
            # fn* name() { yield ... }  — generator function
            if self.peek.type == TT.STAR:
                return self.parse_generator_fn()
            return self.parse_function_decl()

        # --- Struct ---
        if tok.type == TT.STRUCT:
            return self.parse_struct_decl()

        # --- Enum ---
        if tok.type == TT.ENUM:
            return self.parse_enum_decl()

        # --- Scene ---
        if tok.type == TT.SCENE:
            return self.parse_scene_decl()

        # --- AI block ---
        if tok.type == TT.IDENT and tok.value == "ai":
            return self.parse_ai_decl()

        # --- Shader ---
        if tok.type == TT.IDENT and tok.value == "shader":
            return self.parse_shader_decl()

        # --- Interface declaration ---
        if tok.type == TT.INTERFACE:
            return self.parse_interface_decl()

        # --- Impl block (trait implementation) ---
        if tok.type == TT.IMPL:
            return self.parse_impl_decl()

        # --- Mixin declaration ---
        if tok.type == TT.IDENT and tok.value == "mixin":
            return self.parse_mixin_decl()

        # --- Expression statement ---
        return self.parse_stmt()

    # ─────────────────────────────────────────────
    # IMPORT
    # ─────────────────────────────────────────────

    def parse_import(self) -> ImportDecl:
        """
        import "module"
        import "module" as Alias
        import math            ← bare identifier (built-in module)
        import math as M
        from "module" import Name1, Name2
        """
        line, col = self._pos()
        self.advance()  # consume 'import'

        # Accept both string literal and bare identifier
        if self.check(TT.STRING):
            path = self.advance().value
        else:
            # bare identifier: import math, import os, etc.
            path = self.expect_ident("Expected module name or string path after 'import'")

        names = []
        alias = None

        if self.match(TT.AS):
            alias = self.expect_ident("Expected alias name after 'as'")

        self.match(TT.SEMICOLON)
        return ImportDecl(path=path, names=names, alias=alias, line=line, col=col)

    def parse_from_import(self) -> ImportDecl:
        """from "module" import Name1, Name2"""
        line, col = self._pos()
        self.advance()   # consume 'from'
        path_tok = self.expect(TT.STRING, "Expected module path after 'from'")
        path = path_tok.value
        self.expect(TT.IMPORT, "Expected 'import' after module path")
        names = []
        names.append(self.expect_ident("Expected name after 'import'"))
        while self.match(TT.COMMA):
            if self.check(TT.SEMICOLON, TT.EOF): break
            names.append(self.expect_ident("Expected name"))
        self.match(TT.SEMICOLON)
        return ImportDecl(path=path, names=names, alias=None, line=line, col=col)

    # ─────────────────────────────────────────────
    # VARIABLE DECLARATION
    # ─────────────────────────────────────────────

    def parse_var_decl(self, is_sync: bool = False) -> VarDecl:
        line, col = self._pos()
        is_const = self.current.type == TT.CONST
        self.advance()  # consume 'let' or 'const'

        # Destructuring: let [a, b, c] = arr  |  let {x, y} = point
        if self.check(TT.LBRACKET):
            return self._parse_array_destructure(is_const, line, col)
        if self.check(TT.LBRACE):
            return self._parse_object_destructure(is_const, line, col)

        name = self.expect_ident("Expected variable name")
        type_ann = None

        if self.match(TT.COLON):
            type_ann = self.parse_type_annotation()

        initializer = None
        if self.match(TT.ASSIGN):
            initializer = self.parse_expr()

        self.match(TT.SEMICOLON)
        return VarDecl(
            name=name, is_const=is_const, type_ann=type_ann,
            initializer=initializer, is_sync=is_sync,
            line=line, col=col
        )

    def _parse_array_destructure(self, is_const: bool, line: int, col: int) -> DestructureDecl:
        """let [a, b, c] = expr"""
        self.advance()  # consume '['
        names = []
        while not self.check(TT.RBRACKET) and not self.is_at_end():
            if self.check(TT.IDENT):
                names.append(self.advance().value)
            else:
                names.append("_")  # placeholder for skipped positions
                self.advance()
            if not self.match(TT.COMMA):
                break
        self.expect(TT.RBRACKET, "Expected ']' in array destructure")
        self.expect(TT.ASSIGN, "Expected '=' in destructure declaration")
        initializer = self.parse_expr()
        self.match(TT.SEMICOLON)
        return DestructureDecl(names=names, is_object=False, is_const=is_const,
                               initializer=initializer, line=line, col=col)

    def _parse_object_destructure(self, is_const: bool, line: int, col: int) -> DestructureDecl:
        """let {x, y, z: renamed} = expr"""
        self.advance()  # consume '{'
        names = []; aliases = []
        while not self.check(TT.RBRACE) and not self.is_at_end():
            key = self.expect_ident("Expected field name in object destructure")
            if self.match(TT.COLON):
                alias = self.expect_ident("Expected alias after ':' in destructure")
                names.append(key); aliases.append(alias)
            else:
                names.append(key); aliases.append(key)
            if not self.match(TT.COMMA):
                break
        self.expect(TT.RBRACE, "Expected '}' in object destructure")
        self.expect(TT.ASSIGN, "Expected '=' in destructure declaration")
        initializer = self.parse_expr()
        self.match(TT.SEMICOLON)
        return DestructureDecl(names=names, aliases=aliases, is_object=True,
                               is_const=is_const, initializer=initializer,
                               line=line, col=col)

    def parse_sync_var(self) -> VarDecl:
        self.advance()  # consume 'sync'
        decl = self.parse_var_decl(is_sync=True)
        return decl

    # ─────────────────────────────────────────────
    # TYPE ANNOTATION
    # ─────────────────────────────────────────────

    def parse_type_annotation(self) -> TypeAnnotation:
        """Parse a type like: int, float, Vec2, Stack<T>, [int], {string: int}, int?"""
        line, col = self._pos()

        # Array type: [int]
        if self.match(TT.LBRACKET):
            inner = self.parse_type_annotation()
            self.expect(TT.RBRACKET, "Expected ']' to close array type")
            ann = TypeAnnotation(name="Array", is_array=True,
                                 generics=[inner], line=line, col=col)
        # Dict type: {string: int}
        elif self.match(TT.LBRACE):
            key = self.parse_type_annotation()
            self.expect(TT.COLON, "Expected ':' in dict type")
            val = self.parse_type_annotation()
            self.expect(TT.RBRACE, "Expected '}' to close dict type")
            ann = TypeAnnotation(name="Dict", is_dict=True,
                                 key_type=key, generics=[val], line=line, col=col)
        else:
            # Named type: int, float, Vec2, etc.
            # Accept both keyword-types (INT_TYPE etc.) and plain IDENTs
            tok = self.current
            if tok.type in (TT.INT_TYPE, TT.FLOAT_TYPE, TT.BOOL_TYPE,
                            TT.STRING_TYPE, TT.VOID_TYPE, TT.IDENT):
                name = tok.value
                self.advance()
            else:
                self._error(f"Expected type name, got '{tok.value}'")
            ann = TypeAnnotation(name=name, line=line, col=col)

            # Generic type args: Stack<T>, Map<string, int>
            if self.check(TT.LT):
                # Disambiguate: only parse as generic args if this looks like a type
                # Save position to backtrack if needed
                saved_pos = self.pos
                try:
                    self.advance()  # consume '<'
                    generic_args = [self.parse_type_annotation()]
                    while self.match(TT.COMMA):
                        generic_args.append(self.parse_type_annotation())
                    if self.check(TT.GT):
                        self.advance()  # consume '>'
                        ann.generics = generic_args
                    else:
                        # Not a generic — restore position
                        self.pos = saved_pos
                except Exception:
                    self.pos = saved_pos

        # Array shorthand suffix: T[]
        if self.check(TT.LBRACKET):
            peek_idx = self.pos + 1
            if peek_idx < len(self.tokens) and self.tokens[peek_idx].type == TT.RBRACKET:
                self.advance()  # consume '['
                self.advance()  # consume ']'
                ann = TypeAnnotation(name="Array", is_array=True,
                                     generics=[ann], line=line, col=col)

        # Nullable: `int?`
        if self.current.type == TT.NOT and self.current.value == "!":
            pass  # '!' is NOT, not nullable marker
        # We use a future `?` token for nullable — skip for now

        return ann

    # ─────────────────────────────────────────────
    # FUNCTION DECLARATION
    # ─────────────────────────────────────────────

    def parse_function_decl(self, is_method: bool = False,
                             is_rpc: bool = False) -> FunctionDecl:
        line, col = self._pos()
        self.advance()  # consume 'fn'

        # Operator overloading: fn +(other)  fn -(other)  fn *(other)  fn ==(other)
        _OP_TOKENS = {
            TT.PLUS: "__add__", TT.MINUS: "__sub__", TT.STAR: "__mul__",
            TT.SLASH: "__div__", TT.PERCENT: "__mod__", TT.POWER: "__pow__",
            TT.EQ: "__eq__", TT.NEQ: "__ne__", TT.LT: "__lt__", TT.GT: "__gt__",
            TT.LTE: "__le__", TT.GTE: "__ge__",
        }
        if self.current.type in _OP_TOKENS:
            name = _OP_TOKENS[self.current.type]
            self.advance()
        else:
            name = self.expect_ident("Expected function name after 'fn'")

        params = self.parse_param_list()

        return_type = None
        if self.match(TT.ARROW):
            return_type = self.parse_type_annotation()

        body = self.parse_block()
        return FunctionDecl(
            name=name, params=params, return_type=return_type,
            body=body, is_method=is_method, is_rpc=is_rpc,
            line=line, col=col
        )

    def parse_rpc_fn(self) -> FunctionDecl:
        self.advance()  # consume 'rpc'
        return self.parse_function_decl(is_rpc=True)

    def parse_generator_fn(self) -> "GeneratorFnDecl":
        """fn* name(params) { yield value; ... }"""
        line, col = self._pos()
        self.advance()  # consume 'fn'
        self.advance()  # consume '*'
        name = self.expect_ident("Expected generator function name after 'fn*'")
        params = self.parse_param_list()
        ret = None
        if self.match(TT.ARROW):
            ret = self.parse_type_annotation()
        body = self.parse_block()
        from ast_nodes import GeneratorFnDecl
        return GeneratorFnDecl(name=name, params=params, return_type=ret,
                               body=body, line=line, col=col)

    def parse_param_list(self) -> List[Param]:
        """Parse (param1: type = default, param2: type, ...)"""
        params = []
        self.expect(TT.LPAREN, "Expected '(' before parameter list")

        if not self.check(TT.RPAREN):
            params.append(self.parse_param())
            while self.match(TT.COMMA):
                if self.check(TT.RPAREN):
                    break  # trailing comma
                params.append(self.parse_param())

        self.expect(TT.RPAREN, "Expected ')' after parameter list")
        return params

    def parse_param(self) -> Param:
        line, col = self._pos()
        name = self.expect_ident("Expected parameter name")
        type_ann = None
        if self.match(TT.COLON):
            type_ann = self.parse_type_annotation()
        default = None
        if self.match(TT.ASSIGN):
            default = self.parse_expr()
        return Param(name=name, type_ann=type_ann, default=default,
                     line=line, col=col)

    # ─────────────────────────────────────────────
    # STRUCT DECLARATION
    # ─────────────────────────────────────────────

    def parse_struct_decl(self) -> StructDecl:
        line, col = self._pos()
        self.advance()  # consume 'struct'
        name = self.expect_ident("Expected struct name")

        # Optional generic type params: struct Stack<T>  struct Map<K, V>
        type_params = []
        if self.check(TT.LT):
            self.advance()  # consume '<'
            type_params.append(self.expect_ident("Expected type parameter name"))
            while self.match(TT.COMMA):
                type_params.append(self.expect_ident("Expected type parameter name"))
            self.expect(TT.GT, "Expected '>' to close type parameters")

        # Optional inheritance: struct Dog extends Animal { ... }
        parent_name = None
        if self.check(TT.IDENT) and self.current.value == "extends":
            self.advance()  # consume 'extends'
            parent_name = self.expect_ident("Expected parent struct name after 'extends'")

        # Optional interface implementations: struct Sprite implements Drawable, Collidable { ... }
        interfaces = []
        if self.check(TT.IDENT) and self.current.value == "implements":
            self.advance()  # consume 'implements'
            interfaces.append(self.expect_ident("Expected interface name after 'implements'"))
            while self.match(TT.COMMA):
                interfaces.append(self.expect_ident("Expected interface name"))

        # Optional mixin: struct Player with Serializable { ... }
        mixins = []
        if self.check(TT.IDENT) and self.current.value == "with":
            self.advance()  # consume 'with'
            mixins.append(self.expect_ident("Expected mixin name after 'with'"))
            while self.match(TT.COMMA):
                mixins.append(self.expect_ident("Expected mixin name"))

        self.expect(TT.LBRACE, "Expected '{' after struct name")

        fields          = []
        methods         = []
        static_methods  = []
        properties      = {}   # name -> PropertyDecl

        while not self.check(TT.RBRACE) and not self.is_at_end():
            if self.match(TT.SEMICOLON):
                continue
            # static fn foo() { ... }
            if self.check(TT.IDENT) and self.current.value == "static":
                self.advance()  # consume 'static'
                m = self.parse_function_decl(is_method=False)
                static_methods.append(m)
            # get name() -> T { ... }
            elif self.check(TT.IDENT) and self.current.value == "get":
                p = self._parse_getter()
                if p.name not in properties:
                    properties[p.name] = p
                else:
                    properties[p.name].getter_body = p.getter_body
                    properties[p.name].return_type = p.return_type
            # set name(v) { ... }
            elif self.check(TT.IDENT) and self.current.value == "set":
                p = self._parse_setter()
                if p.name not in properties:
                    properties[p.name] = p
                else:
                    properties[p.name].setter_body  = p.setter_body
                    properties[p.name].setter_param = p.setter_param
            elif self.check(TT.FN):
                methods.append(self.parse_function_decl(is_method=True))
            else:
                fields.append(self.parse_struct_field())

        self.expect(TT.RBRACE, "Expected '}' to close struct")
        return StructDecl(name=name, fields=fields, methods=methods,
                          parent_name=parent_name, static_methods=static_methods,
                          interfaces=interfaces, mixins=mixins,
                          properties=list(properties.values()),
                          type_params=type_params,
                          line=line, col=col)

    def _parse_getter(self) -> "PropertyDecl":
        """get radius() -> float { return self._radius }"""
        line, col = self._pos()
        self.advance()  # consume 'get'
        name = self.expect_ident("Expected property name after 'get'")
        self.expect(TT.LPAREN, "Expected '(' after property name")
        self.expect(TT.RPAREN, "Expected ')' in getter")
        ret = None
        if self.match(TT.ARROW):
            ret = self.parse_type_annotation()
        body = self.parse_block()
        from ast_nodes import PropertyDecl
        return PropertyDecl(name=name, getter_body=body, return_type=ret,
                            line=line, col=col)

    def _parse_setter(self) -> "PropertyDecl":
        """set radius(v: float) { self._radius = max(0.0, v) }"""
        line, col = self._pos()
        self.advance()  # consume 'set'
        name = self.expect_ident("Expected property name after 'set'")
        self.expect(TT.LPAREN, "Expected '(' in setter")
        param_name = self.expect_ident("Expected parameter name in setter")
        self.match(TT.COLON)
        if not self.check(TT.RPAREN):
            self.parse_type_annotation()   # consume type, ignore for now
        self.expect(TT.RPAREN, "Expected ')' in setter")
        body = self.parse_block()
        from ast_nodes import PropertyDecl
        return PropertyDecl(name=name, setter_body=body, setter_param=param_name,
                            line=line, col=col)

    def parse_struct_field(self) -> StructField:
        line, col = self._pos()
        name = self.expect_ident("Expected field name")
        self.expect(TT.COLON, "Expected ':' after field name")
        type_ann = self.parse_type_annotation()
        default = None
        if self.match(TT.ASSIGN):
            default = self.parse_expr()
        self.match(TT.SEMICOLON)
        return StructField(name=name, type_ann=type_ann, default=default,
                           line=line, col=col)

    # ─────────────────────────────────────────────
    # SCENE DECLARATION
    # ─────────────────────────────────────────────

    def parse_scene_decl(self) -> SceneDecl:
        line, col = self._pos()
        self.advance()  # consume 'scene'
        name = self.expect_ident("Expected scene name")
        self.expect(TT.LBRACE, "Expected '{' after scene name")

        vars_   = []
        hooks   = []
        methods = []

        while not self.check(TT.RBRACE) and not self.is_at_end():
            if self.match(TT.SEMICOLON):
                continue

            tok = self.current

            if tok.type in (TT.LET, TT.CONST):
                vars_.append(self.parse_var_decl())

            elif tok.type == TT.FN:
                methods.append(self.parse_function_decl(is_method=True))

            elif tok.type in (TT.ON_START, TT.ON_UPDATE, TT.ON_DRAW, TT.ON_EXIT):
                hooks.append(self.parse_lifecycle_hook())

            else:
                self._error(f"Unexpected token in scene body: '{tok.value}'")

        self.expect(TT.RBRACE, "Expected '}' to close scene")
        return SceneDecl(name=name, vars=vars_, hooks=hooks, methods=methods,
                         line=line, col=col)

    def parse_lifecycle_hook(self) -> LifecycleHook:
        line, col = self._pos()
        hook_type = self.current.value   # "on_start", "on_update", etc.
        self.advance()

        params = []
        if self.check(TT.LPAREN):
            params = self.parse_param_list()

        body = self.parse_block()
        return LifecycleHook(hook_type=hook_type, params=params,
                             body=body, line=line, col=col)

    # ─────────────────────────────────────────────
    # AI DECLARATION
    # ─────────────────────────────────────────────

    def parse_ai_decl(self) -> AIDecl:
        line, col = self._pos()
        self.advance()  # consume 'ai'
        name = self.expect_ident("Expected AI name")
        self.expect(TT.LBRACE, "Expected '{' after AI name")

        states = []
        while not self.check(TT.RBRACE) and not self.is_at_end():
            if self.match(TT.SEMICOLON):
                continue
            if self.current.type == TT.IDENT and self.current.value == "state":
                states.append(self.parse_ai_state())
            else:
                self._error(f"Expected 'state' in AI block, got '{self.current.value}'")

        self.expect(TT.RBRACE, "Expected '}' to close AI block")
        return AIDecl(name=name, states=states, line=line, col=col)

    def parse_ai_state(self) -> AIState:
        line, col = self._pos()
        self.advance()  # consume 'state'
        name = self.expect_ident("Expected state name")
        self.expect(TT.LBRACE, "Expected '{' after state name")

        hooks = []
        while not self.check(TT.RBRACE) and not self.is_at_end():
            if self.match(TT.SEMICOLON):
                continue
            if self.current.type in (TT.ON_START, TT.ON_UPDATE, TT.ON_DRAW, TT.ON_EXIT):
                hooks.append(self.parse_lifecycle_hook())
            else:
                self._error(f"Expected lifecycle hook in AI state, got '{self.current.value}'")

        self.expect(TT.RBRACE, "Expected '}' to close state")
        return AIState(name=name, hooks=hooks, line=line, col=col)

    # ─────────────────────────────────────────────
    # SHADER DECLARATION
    # ─────────────────────────────────────────────

    def parse_shader_decl(self) -> ShaderDecl:
        line, col = self._pos()
        self.advance()  # consume 'shader'
        name = self.expect_ident("Expected shader name")
        self.expect(TT.LBRACE, "Expected '{' after shader name")

        uniforms = []
        vertex   = None
        fragment = None

        while not self.check(TT.RBRACE) and not self.is_at_end():
            if self.match(TT.SEMICOLON):
                continue
            tok = self.current

            if tok.type == TT.IDENT and tok.value == "uniform":
                uniforms.append(self.parse_shader_uniform())
            elif tok.type == TT.IDENT and tok.value == "vertex":
                self.advance()
                params       = self.parse_param_list()
                return_type  = None
                if self.match(TT.ARROW):
                    return_type = self.parse_type_annotation()
                body         = self.parse_block()
                vertex       = FunctionDecl("vertex", params, return_type, body,
                                            line=tok.line, col=tok.col)
            elif tok.type == TT.IDENT and tok.value == "fragment":
                self.advance()
                params       = self.parse_param_list()
                return_type  = None
                if self.match(TT.ARROW):
                    return_type = self.parse_type_annotation()
                body         = self.parse_block()
                fragment     = FunctionDecl("fragment", params, return_type, body,
                                            line=tok.line, col=tok.col)
            else:
                self._error(f"Unexpected token in shader: '{tok.value}'")

        self.expect(TT.RBRACE, "Expected '}' to close shader")
        return ShaderDecl(name=name, uniforms=uniforms,
                          vertex=vertex, fragment=fragment,
                          line=line, col=col)

    def parse_shader_uniform(self) -> ShaderUniform:
        line, col = self._pos()
        self.advance()  # consume 'uniform'
        name     = self.expect_ident("Expected uniform name")
        self.expect(TT.COLON, "Expected ':' after uniform name")
        type_ann = self.parse_type_annotation()
        default  = None
        if self.match(TT.ASSIGN):
            default = self.parse_expr()
        self.match(TT.SEMICOLON)
        return ShaderUniform(name=name, type_ann=type_ann, default=default,
                             line=line, col=col)

    # ─────────────────────────────────────────────
    # STATEMENTS
    # ─────────────────────────────────────────────

    def parse_stmt(self) -> Node:
        """Parse any statement."""
        if self.match(TT.SEMICOLON):
            return None  # empty stmt

        tok = self.current

        if tok.type in (TT.LET, TT.CONST):
            return self.parse_var_decl()

        if tok.type == TT.FN:
            return self.parse_function_decl()

        if tok.type == TT.RETURN:
            return self.parse_return()

        if tok.type == TT.YIELD:
            line, col = self._pos()
            self.advance()  # consume 'yield'
            value = None
            if not self.check(TT.RBRACE) and not self.check(TT.SEMICOLON):
                value = self.parse_expr()
            self.match(TT.SEMICOLON)
            return YieldStmt(value=value, line=line, col=col)

        if tok.type == TT.BREAK:
            self.advance()
            label = None
            if self.check(TT.IDENT):  # break outer
                label = self.advance().value
            self.match(TT.SEMICOLON)
            return BreakStmt(label=label, line=tok.line, col=tok.col)

        if tok.type == TT.CONTINUE:
            self.advance()
            label = None
            if self.check(TT.IDENT):  # continue outer
                label = self.advance().value
            self.match(TT.SEMICOLON)
            return ContinueStmt(label=label, line=tok.line, col=tok.col)

        if tok.type == TT.IF:
            return self.parse_if()

        if tok.type == TT.WHILE:
            return self.parse_while()

        if tok.type == TT.FOR:
            return self.parse_for_in()

        if tok.type == TT.MATCH:
            return self.parse_match()

        # Labeled statement: outer: for ... { break outer }
        if tok.type == TT.IDENT and self.peek.type == TT.COLON:
            label = tok.value
            self.advance()  # consume label name
            self.advance()  # consume ':'
            inner = self.parse_stmt()
            return LabeledStmt(label=label, stmt=inner, line=tok.line, col=tok.col)

        if tok.type == TT.LBRACE:
            # Disambiguate: {key: val} dict literal vs {stmt} block
            if self._looks_like_dict_literal():
                return self.parse_expr_stmt()  # full expr with postfix chain
            return self.parse_block()

        # Try / Catch
        if tok.type == TT.TRY:
            return self.parse_try_catch()

        # Throw
        if tok.type == TT.THROW:
            return self.parse_throw()

        # Enum (local enum)
        if tok.type == TT.ENUM:
            return self.parse_enum_decl()

        # Struct (local struct)
        if tok.type == TT.STRUCT:
            return self.parse_struct_decl()

        # Await as statement
        if tok.type == TT.AWAIT:
            return self.parse_expr_stmt()

        # built-in print
        if tok.type == TT.IDENT and tok.value == "print":
            return self.parse_print()

        # Expression statement
        return self.parse_expr_stmt()

    def parse_block(self) -> BlockStmt:
        line, col = self._pos()
        self.expect(TT.LBRACE, "Expected '{'")
        body = []
        while not self.check(TT.RBRACE) and not self.is_at_end():
            stmt = self.parse_stmt()
            if stmt is not None:
                body.append(stmt)
        self.expect(TT.RBRACE, "Expected '}'")
        return BlockStmt(body=body, line=line, col=col)

    def parse_return(self) -> ReturnStmt:
        line, col = self._pos()
        self.advance()  # consume 'return'
        value = None
        if not self.check(TT.RBRACE) and not self.check(TT.SEMICOLON) and not self.is_at_end():
            value = self.parse_expr()
        self.match(TT.SEMICOLON)
        return ReturnStmt(value=value, line=line, col=col)

    def parse_if(self) -> IfStmt:
        line, col = self._pos()
        self.advance()  # consume 'if'
        condition   = self.parse_expr()
        then_branch = self.parse_block()

        else_branch = None
        if self.match(TT.ELSE):
            if self.check(TT.IF):
                else_branch = self.parse_if()   # else if chain
            else:
                else_branch = self.parse_block()

        return IfStmt(condition=condition, then_branch=then_branch,
                      else_branch=else_branch, line=line, col=col)

    def parse_while(self) -> WhileStmt:
        line, col = self._pos()
        self.advance()  # consume 'while'
        condition = self.parse_expr()
        body      = self.parse_block()
        return WhileStmt(condition=condition, body=body, line=line, col=col)

    def parse_for_in(self) -> ForInStmt:
        line, col = self._pos()
        self.advance()  # consume 'for'
        var_name = self.expect_ident("Expected variable name after 'for'")
        self.expect(TT.IN, "Expected 'in' after for variable")
        iterable = self.parse_expr()
        body     = self.parse_block()
        return ForInStmt(var_name=var_name, iterable=iterable,
                         body=body, line=line, col=col)

    def parse_match(self) -> MatchStmt:
        line, col = self._pos()
        self.advance()  # consume 'match'
        subject   = self.parse_expr()
        self.expect(TT.LBRACE, "Expected '{' after match subject")
        arms = []

        while not self.check(TT.RBRACE) and not self.is_at_end():
            if self.match(TT.SEMICOLON):
                continue
            arms.append(self.parse_match_arm())

        self.expect(TT.RBRACE, "Expected '}' to close match")
        return MatchStmt(subject=subject, arms=arms, line=line, col=col)

    def parse_match_arm(self) -> MatchArm:
        line, col = self._pos()
        self.expect(TT.CASE, "Expected 'case' in match arm")

        # Wildcard arm: `case _ { ... }`
        if self.current.type == TT.IDENT and self.current.value == "_":
            self.advance()
            pattern = None
            binding = None
        # Binding with guard: `case h if h <= 0 { ... }`
        elif self.current.type == TT.IDENT and self.peek.type == TT.IF:
            binding = self.advance().value   # consume binding name 'h'
            pattern = None                   # binding matches anything
        else:
            pattern = self.parse_expr()
            binding = None

        # Optional guard: `if condition`  (TT.IF is the keyword token)
        guard = None
        if self.check(TT.IF):
            self.advance()   # consume 'if'
            guard = self.parse_expr()

        body = self.parse_block()
        return MatchArm(pattern=pattern, body=body, guard=guard, binding=binding,
                        line=line, col=col)

    def parse_print(self) -> PrintStmt:
        line, col = self._pos()
        self.advance()  # consume 'print'
        self.expect(TT.LPAREN, "Expected '(' after 'print'")
        args = []
        if not self.check(TT.RPAREN):
            args.append(self.parse_expr())
            while self.match(TT.COMMA):
                if self.check(TT.RPAREN):
                    break
                args.append(self.parse_expr())
        self.expect(TT.RPAREN, "Expected ')' after print arguments")
        self.match(TT.SEMICOLON)
        return PrintStmt(args=args, line=line, col=col)

    def parse_expr_stmt(self) -> ExprStmt:
        line, col = self._pos()
        expr = self.parse_expr()
        self.match(TT.SEMICOLON)
        return ExprStmt(expr=expr, line=line, col=col)

    # ─────────────────────────────────────────────
    # EXPRESSIONS  (operator precedence climbing)
    # ─────────────────────────────────────────────

    def parse_expr(self) -> Node:
        """Top-level: parse assignment (lowest precedence)."""
        return self.parse_assignment()

    def parse_assignment(self) -> Node:
        """Assignment: x = v | x += v | obj.field = v | arr[i] = v"""
        line, col = self._pos()
        expr = self.parse_ternary()

        ASSIGN_OPS = {
            TT.ASSIGN:   "=",
            TT.PLUS_EQ:  "+=",
            TT.MINUS_EQ: "-=",
            TT.STAR_EQ:  "*=",
            TT.SLASH_EQ: "/=",
        }

        if self.current.type in ASSIGN_OPS:
            op  = ASSIGN_OPS[self.current.type]
            self.advance()
            val = self.parse_assignment()  # right-associative

            # Determine which assignment node to create
            if isinstance(expr, IdentExpr):
                return AssignExpr(target=expr, op=op, value=val,
                                  line=line, col=col)
            elif isinstance(expr, GetAttrExpr):
                if op == "=":
                    return SetAttrExpr(obj=expr.obj, attr=expr.attr,
                                       value=val, line=line, col=col)
                else:
                    # x.y += 5  →  SetAttrExpr(x.y, BinaryExpr(x.y, +, 5))
                    binop = op[0]  # '+', '-', '*', '/'
                    rhs   = BinaryExpr(left=expr, op=binop, right=val,
                                       line=line, col=col)
                    return SetAttrExpr(obj=expr.obj, attr=expr.attr,
                                       value=rhs, line=line, col=col)
            elif isinstance(expr, IndexExpr):
                if op == "=":
                    return SetIndexExpr(obj=expr.obj, index=expr.index,
                                        value=val, line=line, col=col)
                else:
                    binop = op[0]
                    rhs   = BinaryExpr(left=expr, op=binop, right=val,
                                       line=line, col=col)
                    return SetIndexExpr(obj=expr.obj, index=expr.index,
                                        value=rhs, line=line, col=col)
            else:
                self._error("Invalid assignment target")

        return expr

    def parse_ternary(self) -> Node:
        """cond ? then : else   |   x ?? default   |   x |> fn"""
        line, col = self._pos()
        expr = self.parse_or()

        # Ternary: cond ? then_expr : else_expr
        if self.check(TT.QUESTION):
            self.advance()  # consume '?'
            then_expr = self.parse_expr()
            self.expect(TT.COLON, "Expected ':' in ternary expression")
            else_expr = self.parse_ternary()
            return TernaryExpr(condition=expr, then_expr=then_expr,
                               else_expr=else_expr, line=line, col=col)

        # Nullish coalescing: x ?? default
        if self.check(TT.NULLISH):
            self.advance()  # consume '??'
            right = self.parse_ternary()
            return NullishExpr(left=expr, right=right, line=line, col=col)

        # Pipe: value |> fn  (chainable: a |> f |> g |> h)
        while self.check(TT.PIPE_GT):
            self.advance()  # consume '|>'
            fn = self.parse_or()
            expr = PipeExpr(value=expr, fn=fn, line=line, col=col)

        return expr

    def parse_or(self) -> Node:
        line, col = self._pos()
        left = self.parse_and()
        while self.check(TT.OR):
            op    = self.advance().value
            right = self.parse_and()
            left  = BinaryExpr(left=left, op=op, right=right,
                                line=line, col=col)
        return left

    def parse_and(self) -> Node:
        line, col = self._pos()
        left = self.parse_equality()
        while self.check(TT.AND):
            op    = self.advance().value
            right = self.parse_equality()
            left  = BinaryExpr(left=left, op=op, right=right,
                                line=line, col=col)
        return left

    def parse_equality(self) -> Node:
        line, col = self._pos()
        left = self.parse_comparison()
        while self.check(TT.EQ, TT.NEQ):
            op    = self.advance().value
            right = self.parse_comparison()
            left  = BinaryExpr(left=left, op=op, right=right,
                                line=line, col=col)
        return left

    def parse_comparison(self) -> Node:
        line, col = self._pos()
        left = self.parse_addition()

        # Range: start..end  or  start..=end
        if self.check(TT.DOTDOT, TT.DOTDOT_EQ):
            inclusive = (self.current.type == TT.DOTDOT_EQ)
            self.advance()
            right = self.parse_addition()
            return RangeExpr(start=left, end=right, inclusive=inclusive,
                             line=line, col=col)

        while self.check(TT.LT, TT.GT, TT.LTE, TT.GTE):
            op    = self.advance().value
            right = self.parse_addition()
            left  = BinaryExpr(left=left, op=op, right=right,
                                line=line, col=col)
        return left

    def parse_addition(self) -> Node:
        line, col = self._pos()
        left = self.parse_multiplication()
        while self.check(TT.PLUS, TT.MINUS):
            op    = self.advance().value
            right = self.parse_multiplication()
            left  = BinaryExpr(left=left, op=op, right=right,
                                line=line, col=col)
        return left

    def parse_multiplication(self) -> Node:
        line, col = self._pos()
        left = self.parse_power()
        while self.check(TT.STAR, TT.SLASH, TT.PERCENT):
            op    = self.advance().value
            right = self.parse_power()
            left  = BinaryExpr(left=left, op=op, right=right,
                                line=line, col=col)
        return left

    def parse_power(self) -> Node:
        """Power is right-associative: 2 ** 3 ** 2 = 2 ** (3 ** 2)"""
        line, col = self._pos()
        base = self.parse_unary()
        if self.check(TT.POWER):
            self.advance()
            exp = self.parse_power()  # right-recursive
            return BinaryExpr(left=base, op="**", right=exp,
                              line=line, col=col)
        return base

    def parse_unary(self) -> Node:
        line, col = self._pos()
        if self.check(TT.NOT):
            op      = self.advance().value
            operand = self.parse_unary()
            return UnaryExpr(op=op, operand=operand, line=line, col=col)
        if self.check(TT.MINUS):
            self.advance()
            operand = self.parse_unary()
            return UnaryExpr(op="-", operand=operand, line=line, col=col)
        return self.parse_postfix()

    def parse_postfix(self) -> Node:
        """Handle dot access, index access, function calls."""
        line, col = self._pos()
        expr = self.parse_primary()

        while True:
            # Dot access: expr.attr  or  expr.method(args)
            if self.check(TT.DOT):
                self.advance()
                attr_tok = self.current
                if attr_tok.type not in (TT.IDENT,):
                    # allow keyword-looking attrs: obj.in? obj.for? - unlikely but handle gracefully
                    self._error(f"Expected attribute name after '.', got '{attr_tok.value}'")
                attr = attr_tok.value
                self.advance()

                if self.check(TT.LPAREN):
                    # Method call: expr.method(args)
                    args = self.parse_arg_list()
                    expr = CallExpr(
                        callee=GetAttrExpr(obj=expr, attr=attr,
                                           line=attr_tok.line, col=attr_tok.col),
                        args=args, line=line, col=col
                    )
                else:
                    expr = GetAttrExpr(obj=expr, attr=attr,
                                       line=line, col=col)

            # Index access: expr[index]
            elif self.check(TT.LBRACKET):
                self.advance()
                index = self.parse_expr()
                self.expect(TT.RBRACKET, "Expected ']' after index expression")
                expr = IndexExpr(obj=expr, index=index, line=line, col=col)

            # Function call: expr(args)
            elif self.check(TT.LPAREN):
                args = self.parse_arg_list()
                expr = CallExpr(callee=expr, args=args, line=line, col=col)

            # Optional chaining: expr?.member  or  expr?.method(args)
            elif self.check(TT.QUESTION_DOT):
                self.advance()  # consume '?.'
                attr = self.expect_ident("Expected member name after '?.'")
                if self.check(TT.LPAREN):
                    args = self.parse_arg_list()
                    opt  = OptChainExpr(obj=expr, member=attr, line=line, col=col)
                    expr = CallExpr(callee=opt, args=args, line=line, col=col)
                else:
                    expr = OptChainExpr(obj=expr, member=attr, line=line, col=col)

            # Error propagation: expr?  (NOT a ternary — check next token)
            # Ternary ? is followed by an expression-start token (string, ident, num, paren…)
            # Propagate ? is followed by newline, }, ), ,, ;, EOF
            elif self.check(TT.QUESTION):
                _EXPR_START = {
                    TT.STRING, TT.INT, TT.FLOAT, TT.BOOL, TT.NULL,
                    TT.IDENT, TT.LPAREN, TT.LBRACKET, TT.LBRACE,
                    TT.PIPE, TT.OR, TT.NOT, TT.MINUS, TT.FSTRING,
                    TT.INT_TYPE, TT.FLOAT_TYPE, TT.STRING_TYPE, TT.BOOL_TYPE,
                    TT.SELF,
                }
                _peek = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else self.tokens[-1]
                if _peek.type not in _EXPR_START:
                    # PropagateExpr: expr? where ? is NOT followed by an expression
                    self.advance()  # consume '?'
                    expr = PropagateExpr(expr=expr, line=line, col=col)
                else:
                    break  # it's a ternary ? — let parse_ternary handle it

            # Namespace: Name::member (already parsed in primary — but handle chaining)
            else:
                break

        return expr

    def parse_arg_list(self) -> List[Argument]:
        """Parse (arg1, name: arg2, ...) — supports named args."""
        args = []
        self.expect(TT.LPAREN, "Expected '(' to start argument list")

        if not self.check(TT.RPAREN):
            args.append(self.parse_argument())
            while self.match(TT.COMMA):
                if self.check(TT.RPAREN):
                    break  # trailing comma
                args.append(self.parse_argument())

        self.expect(TT.RPAREN, "Expected ')' to end argument list")
        return args

    def parse_argument(self) -> Argument:
        line, col = self._pos()

        # Spread argument: ...expr
        if self.check(TT.ELLIPSIS):
            self.advance()  # consume '...'
            value = SpreadExpr(expr=self.parse_expr(), line=line, col=col)
            return Argument(value=value, name=None, line=line, col=col)

        # Named argument: `name: value`
        if (self.current.type == TT.IDENT
                and self.peek.type == TT.COLON):
            name = self.current.value
            self.advance()  # consume name
            self.advance()  # consume ':'
            value = self.parse_expr()
            return Argument(value=value, name=name, line=line, col=col)

        value = self.parse_expr()
        return Argument(value=value, name=None, line=line, col=col)

    def parse_primary(self) -> Node:
        """Lowest-level expressions: literals, identifiers, grouped exprs, arrays, dicts."""
        line, col = self._pos()
        tok = self.current

        # Integer literal
        if tok.type == TT.INT:
            self.advance()
            return IntLiteralExpr(value=tok.value, line=line, col=col)

        # Float literal
        if tok.type == TT.FLOAT:
            self.advance()
            return FloatLiteralExpr(value=tok.value, line=line, col=col)

        # String literal
        if tok.type == TT.STRING:
            self.advance()
            return StringLiteralExpr(value=tok.value, line=line, col=col)

        # Interpolated f-string: f"Hello {name}!"
        if tok.type == TT.FSTRING:
            self.advance()
            return FStringExpr(template=tok.value, line=line, col=col)

        # Boolean
        if tok.type == TT.BOOL:
            self.advance()
            return BoolLiteralExpr(value=tok.value, line=line, col=col)

        # Null
        if tok.type == TT.NULL:
            self.advance()
            return NullLiteralExpr(line=line, col=col)

        # Grouped expression: (expr)
        if tok.type == TT.LPAREN:
            self.advance()
            expr = self.parse_expr()
            self.expect(TT.RPAREN, "Expected ')' to close grouped expression")
            return expr

        # Array literal: [elem1, elem2, ...]
        if tok.type == TT.LBRACKET:
            return self.parse_array_literal()

        # Dict literal: {"key": val, ...}
        if tok.type == TT.LBRACE:
            return self.parse_dict_literal()

        # Lambda: |params| body  (|x| x*2  or  || expr)
        if tok.type in (TT.PIPE, TT.OR):
            return self.parse_lambda()

        # Identifier, keyword-ident, struct init, namespace access
        if tok.type == TT.IDENT:
            # comptime { ... } — evaluated immediately at runtime (dynamic interpreter)
            if tok.value == "comptime":
                self.advance()  # consume 'comptime'
                body = self.parse_block()
                return ComptimeExpr(body=body, line=line, col=col)
            return self.parse_ident_or_struct_init()

        # Type keywords used as constructors: Vec2(…) → these lex as IDENT anyway
        # but handle INT_TYPE etc. used as function names (rare)
        if tok.type in (TT.INT_TYPE, TT.FLOAT_TYPE, TT.BOOL_TYPE,
                        TT.STRING_TYPE, TT.SELF):
            name = tok.value
            self.advance()
            return IdentExpr(name=name, line=line, col=col)

        self._error(
            f"Unexpected token '{tok.value}' ({tok.type.name}) — expected an expression"
        )

    def parse_ident_or_struct_init(self) -> Node:
        """
        Identifier or struct initializer:
          `x`               → IdentExpr
          `Player { ... }`  → StructInitExpr
          `Color::RED`      → NamespaceAccessExpr
        """
        line, col = self._pos()
        name = self.current.value
        self.advance()

        # Namespace access: Name::member
        if self.check(TT.DOUBLE_COLON):
            self.advance()
            member = self.expect_ident("Expected member name after '::'")
            return NamespaceAccessExpr(namespace=name, member=member,
                                       line=line, col=col)

        # Struct initializer: Name { field: val, ... }
        # Disambiguate from block statements: only parse as struct init if
        # next is `{` followed by `ident :` (not a bare statement block)
        if self.check(TT.LBRACE) and self._looks_like_struct_init():
            return self.parse_struct_init(name, line, col)

        # Generic struct init: Name<T> { field: val, ... }  e.g.  Stack<int> {}
        # Consume and discard the type args (runtime is dynamically typed)
        if self.check(TT.LT) and self._looks_like_generic_struct_init(name):
            saved = self.pos
            try:
                self.advance()  # consume '<'
                # parse comma-separated type args until '>'
                depth = 1
                while not self.is_at_end() and depth > 0:
                    if self.current.type == TT.LT:
                        depth += 1
                        self.advance()
                    elif self.current.type == TT.GT:
                        depth -= 1
                        if depth == 0:
                            self.advance()  # consume final '>'
                        else:
                            self.advance()
                    else:
                        self.advance()
                if self.check(TT.LBRACE):
                    return self.parse_struct_init(name, line, col)
                else:
                    # Not a struct init — restore
                    self.pos = saved
            except Exception:
                self.pos = saved

        # Range: ident..end  (rare but possible)
        # Handled in parse_addition context — skip here

        return IdentExpr(name=name, line=line, col=col)

    def _looks_like_generic_struct_init(self, name: str) -> bool:
        """Returns True if Name<...> { looks like a generic struct init."""
        if not name or not name[0].isupper():
            return False
        # Scan ahead past <...> to see if { follows
        saved = self.pos
        try:
            self.advance()  # consume '<'
            depth = 1
            while not self.is_at_end() and depth > 0:
                if self.current.type == TT.LT:
                    depth += 1
                    self.advance()
                elif self.current.type == TT.GT:
                    depth -= 1
                    self.advance()
                else:
                    self.advance()
            result = self.check(TT.LBRACE)
        except Exception:
            result = False
        self.pos = saved
        return result

    def _looks_like_dict_literal(self) -> bool:
        """Peek inside { to see if it looks like a dict: {key: val} not a block."""
        # { }  → empty — ambiguous, treat as block (empty dict use Dict() constructor)
        # { STRING : ...}  → dict
        # { IDENT  : ...}  → could be dict or struct init — treat as dict here
        saved = self.pos
        self.advance()  # consume '{'
        result = False
        if self.current.type in (TT.STRING, TT.INT, TT.FLOAT):
            # {  "key" :  or  {  42 :
            result = self.peek.type == TT.COLON
        # Note: IDENT { is handled by struct init. Here we only check string/num keys.
        self.pos = saved
        return result

    def _looks_like_struct_init(self) -> bool:
        # Heuristic: treat Name { } as struct init ONLY if:
        #   (a) the name starts with an uppercase letter (PascalCase = type), AND
        #   (b) the brace body is empty OR starts with  ident :
        # This prevents `if condition { }` from being mis-parsed.
        name_tok = self.tokens[self.pos - 1]
        name_val = name_tok.value if isinstance(name_tok.value, str) else ""
        if not name_val or not name_val[0].isupper():
            return False
        saved = self.pos
        self.advance()   # consume '{'
        result = (
            self.check(TT.RBRACE)   # empty  Counter {}
            or (self.current.type == TT.IDENT and self.peek.type == TT.COLON)
        )
        self.pos = saved
        return result

    def parse_struct_init(self, name: str, line: int, col: int) -> StructInitExpr:
        """Player { pos: Vec2(0,0), health: 100 }"""
        self.advance()  # consume '{'
        fields = []

        while not self.check(TT.RBRACE) and not self.is_at_end():
            if self.match(TT.SEMICOLON) or self.match(TT.COMMA):
                continue
            field_name = self.expect_ident("Expected field name in struct initializer")
            self.expect(TT.COLON, f"Expected ':' after field name '{field_name}'")
            value = self.parse_expr()
            fields.append((field_name, value))
            self.match(TT.COMMA)

        self.expect(TT.RBRACE, "Expected '}' to close struct initializer")
        return StructInitExpr(struct_name=name, fields=fields, line=line, col=col)

    def parse_array_literal(self) -> ArrayLiteralExpr:
        line, col = self._pos()
        self.advance()  # consume '['
        elements = []

        if not self.check(TT.RBRACKET):
            elements.append(self.parse_expr())
            while self.match(TT.COMMA):
                if self.check(TT.RBRACKET):
                    break
                elements.append(self.parse_expr())

        self.expect(TT.RBRACKET, "Expected ']' to close array literal")
        return ArrayLiteralExpr(elements=elements, line=line, col=col)

    def parse_dict_literal(self) -> DictLiteralExpr:
        line, col = self._pos()
        self.advance()  # consume '{'
        pairs = []

        if not self.check(TT.RBRACE):
            key   = self.parse_expr()
            self.expect(TT.COLON, "Expected ':' in dict literal")
            value = self.parse_expr()
            pairs.append((key, value))

            while self.match(TT.COMMA):
                if self.check(TT.RBRACE):
                    break
                key   = self.parse_expr()
                self.expect(TT.COLON, "Expected ':' in dict literal")
                value = self.parse_expr()
                pairs.append((key, value))

        self.expect(TT.RBRACE, "Expected '}' to close dict literal")
        return DictLiteralExpr(pairs=pairs, line=line, col=col)

    def parse_lambda(self) -> LambdaExpr:
        """
        Lambda forms:
          || expr                           (no params)
          |x| x * 2                        (one param, implicit return)
          |x: int, y: int| x + y           (typed params)
          |x: int| -> int { return x * 2 } (explicit return type + block)
        """
        line, col = self._pos()
        params = []

        if self.check(TT.OR):
            self.advance()   # || = empty params
        elif self.check(TT.PIPE):
            self.advance()   # consume opening |
            if not self.check(TT.PIPE):
                params.append(self.parse_lambda_param())
                while self.match(TT.COMMA):
                    if self.check(TT.PIPE): break
                    params.append(self.parse_lambda_param())
            self.expect(TT.PIPE, "Expected '|' to close lambda parameters")
        else:
            self._error("Expected '|' to start lambda")

        return_type = None
        if self.match(TT.ARROW):
            return_type = self.parse_type_annotation()

        if self.check(TT.LBRACE):
            body = self.parse_block()
        else:
            body = self.parse_expr()

        return LambdaExpr(params=params, return_type=return_type,
                          body=body, line=line, col=col)

    def parse_lambda_param(self) -> Param:
        line, col = self._pos()
        name     = self.expect_ident("Expected parameter name in lambda")
        type_ann = None
        if self.match(TT.COLON):
            type_ann = self.parse_type_annotation()
        return Param(name=name, type_ann=type_ann, line=line, col=col)


    def parse_try_catch(self) -> "TryCatchStmt":
        """try { ... } catch (e) { ... } or catch (e: ErrorType) { ... }"""
        line, col = self._pos()
        self.advance()  # consume 'try'
        body = self.parse_block()

        catch_var = None
        catch_type = None
        handler = BlockStmt(body=[], line=line, col=col)

        if self.match(TT.CATCH):
            if self.match(TT.LPAREN):
                catch_var = self.expect_ident("Expected error variable name")
                if self.match(TT.COLON):
                    catch_type = self.parse_type_annotation()
                self.expect(TT.RPAREN, "Expected ')' after catch variable")
            handler = self.parse_block()

        from ast_nodes import TryCatchStmt
        return TryCatchStmt(body=body, catch_var=catch_var,
                             catch_type=catch_type, handler=handler,
                             line=line, col=col)

    def parse_throw(self) -> "ThrowStmt":
        """throw expression"""
        line, col = self._pos()
        self.advance()  # consume 'throw'
        value = self.parse_expr()
        self.match(TT.SEMICOLON)
        from ast_nodes import ThrowStmt
        return ThrowStmt(value=value, line=line, col=col)

    def parse_async_fn(self) -> "FunctionDecl":
        """async fn name(...) -> type { ... }"""
        line, col = self._pos()
        self.advance()  # consume 'async'
        if not self.check(TT.FN):
            self._error("Expected 'fn' after 'async'", line, col)
        fn = self.parse_function_decl()
        fn.is_async = True
        return fn

    def parse_enum_decl(self) -> "EnumDecl":
        """enum Direction { North, South = 10, East, West }
        Also supports ADT: enum Shape { Circle(r: float), Rect(w: float, h: float) }"""
        line, col = self._pos()
        self.advance()  # consume 'enum'
        name = self.expect_ident("Expected enum name")
        self.expect(TT.LBRACE, "Expected '{' after enum name")
        variants = []
        while not self.check(TT.RBRACE) and not self.is_at_end():
            self.match(TT.COMMA); self.match(TT.SEMICOLON)
            if self.check(TT.RBRACE): break
            v_line, v_col = self._pos()
            v_name = self.expect_ident("Expected enum variant name")
            v_val  = None
            fields = []
            # ADT variant with fields: Circle(r: float)
            if self.check(TT.LPAREN):
                self.advance()  # consume '('
                while not self.check(TT.RPAREN) and not self.is_at_end():
                    fname = self.expect_ident("Expected field name in enum variant")
                    self.expect(TT.COLON, "Expected ':' in enum variant field")
                    ftype = self.parse_type_annotation()
                    fields.append((fname, ftype))
                    if not self.match(TT.COMMA): break
                self.expect(TT.RPAREN, "Expected ')' after enum variant fields")
            elif self.match(TT.ASSIGN):
                v_val = self.parse_expr()
            from ast_nodes import EnumVariant, EnumDecl
            variants.append(EnumVariant(name=v_name, value=v_val, fields=fields,
                                        line=v_line, col=v_col))
            self.match(TT.COMMA)
        self.expect(TT.RBRACE, "Expected '}' to close enum")
        from ast_nodes import EnumDecl
        return EnumDecl(name=name, variants=variants, line=line, col=col)

    def _parse_abstract_method(self) -> FunctionDecl:
        """Parse a method signature with optional empty body (for interfaces/abstract)."""
        line, col = self._pos()
        self.advance()  # consume 'fn'
        name = self.expect_ident("Expected method name")
        params = self.parse_param_list()
        ret = None
        if self.match(TT.ARROW):
            ret = self.parse_type_annotation()
        # Body is optional — interface methods may have no body
        if self.check(TT.LBRACE):
            body = self.parse_block()
        else:
            # Abstract: empty body as placeholder
            from ast_nodes import BlockStmt
            body = BlockStmt(body=[], line=line, col=col)
            self.match(TT.SEMICOLON)
        return FunctionDecl(name=name, params=params, return_type=ret,
                            body=body, is_method=True, line=line, col=col)

    def parse_interface_decl(self) -> "InterfaceDecl":
        """interface Drawable { fn draw() -> void  fn area() -> float }"""
        line, col = self._pos()
        self.advance()  # consume 'interface'
        name = self.expect_ident("Expected interface name")

        # Extends another interface: interface Shape extends Drawable { ... }
        parents = []
        if self.check(TT.IDENT) and self.current.value == "extends":
            self.advance()
            parents.append(self.expect_ident("Expected parent interface name"))
            while self.match(TT.COMMA):
                parents.append(self.expect_ident("Expected interface name"))

        self.expect(TT.LBRACE, "Expected '{' after interface name")
        methods = []
        while not self.check(TT.RBRACE) and not self.is_at_end():
            self.match(TT.SEMICOLON)
            if self.check(TT.RBRACE): break
            if self.check(TT.FN):
                m = self._parse_abstract_method()
                methods.append(m)
            else:
                self._error(f"Expected 'fn' in interface body, got '{self.current.value}'")
        self.expect(TT.RBRACE, "Expected '}' to close interface")
        from ast_nodes import InterfaceDecl
        return InterfaceDecl(name=name, methods=methods, parents=parents,
                             line=line, col=col)

    def parse_impl_decl(self) -> "ImplDecl":
        """impl Drawable for Sprite { fn draw() { ... } }"""
        line, col = self._pos()
        self.advance()  # consume 'impl'
        trait_name = self.expect_ident("Expected interface/trait name after 'impl'")
        # 'for' is not a reserved keyword in InScript, it's an IDENT here
        if not (self.check(TT.IDENT) and self.current.value == "for") and not self.check(TT.FOR):
            self._error("Expected 'for' after interface name in impl")
        self.advance()  # consume 'for'
        struct_name = self.expect_ident("Expected struct name after 'for'")
        self.expect(TT.LBRACE, "Expected '{'")
        methods = []
        while not self.check(TT.RBRACE) and not self.is_at_end():
            self.match(TT.SEMICOLON)
            if self.check(TT.RBRACE): break
            methods.append(self.parse_function_decl(is_method=True))
        self.expect(TT.RBRACE, "Expected '}' to close impl block")
        from ast_nodes import ImplDecl
        return ImplDecl(trait_name=trait_name, struct_name=struct_name,
                        methods=methods, line=line, col=col)

    def parse_mixin_decl(self) -> "MixinDecl":
        """mixin Serializable { fn to_json() { ... } }"""
        line, col = self._pos()
        self.advance()  # consume 'mixin'
        name = self.expect_ident("Expected mixin name")
        self.expect(TT.LBRACE, "Expected '{' after mixin name")
        methods = []
        while not self.check(TT.RBRACE) and not self.is_at_end():
            self.match(TT.SEMICOLON)
            if self.check(TT.RBRACE): break
            methods.append(self.parse_function_decl(is_method=True))
        self.expect(TT.RBRACE, "Expected '}' to close mixin")
        from ast_nodes import MixinDecl
        return MixinDecl(name=name, methods=methods, line=line, col=col)

# ─────────────────────────────────────────────
# CONVENIENCE FUNCTION
# ─────────────────────────────────────────────

def parse(source: str, filename: str = "<stdin>") -> Program:
    """Lex and parse InScript source code, returning the root Program AST node."""
    tokens      = tokenize(source, filename)
    source_lines = source.splitlines()
    parser      = Parser(tokens, source_lines)
    return parser.parse()
