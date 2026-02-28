"""
Parser for Inscript language.
Converts token stream into Abstract Syntax Tree (AST).
"""

from dataclasses import dataclass
from typing import List, Optional, Any
from .lexer import Token, TokenType

# AST Node definitions
@dataclass
class ASTNode:
    pass

@dataclass
class Program(ASTNode):
    statements: List[ASTNode]

@dataclass
class BinaryOp(ASTNode):
    left: ASTNode
    operator: str
    right: ASTNode

@dataclass
class UnaryOp(ASTNode):
    operator: str
    operand: ASTNode

@dataclass
class Number(ASTNode):
    value: float

@dataclass
class String(ASTNode):
    value: str

@dataclass
class Boolean(ASTNode):
    value: bool

@dataclass
class Null(ASTNode):
    pass

@dataclass
class Identifier(ASTNode):
    name: str

@dataclass
class Assignment(ASTNode):
    target: str
    value: ASTNode

@dataclass
class FunctionDef(ASTNode):
    name: str
    params: List[str]
    body: List[ASTNode]

@dataclass
class FunctionCall(ASTNode):
    name: str
    args: List[ASTNode]

@dataclass
class MethodCall(ASTNode):
    obj: ASTNode
    method: str
    args: List[ASTNode]

@dataclass
class IfStatement(ASTNode):
    condition: ASTNode
    then_body: List[ASTNode]
    elseif_parts: List[tuple]  # (condition, body) pairs
    else_body: Optional[List[ASTNode]]

@dataclass
class WhileStatement(ASTNode):
    condition: ASTNode
    body: List[ASTNode]

@dataclass
class ForStatement(ASTNode):
    variable: str
    iterable: ASTNode
    body: List[ASTNode]

@dataclass
class ReturnStatement(ASTNode):
    value: Optional[ASTNode]

@dataclass
class BreakStatement(ASTNode):
    pass

@dataclass
class ContinueStatement(ASTNode):
    pass

@dataclass
class ListLiteral(ASTNode):
    elements: List[ASTNode]

@dataclass
class DictLiteral(ASTNode):
    pairs: List[tuple]  # (key, value) pairs

@dataclass
class IndexAccess(ASTNode):
    obj: ASTNode
    index: ASTNode

@dataclass
class AttributeAccess(ASTNode):
    obj: ASTNode
    attribute: str

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
    
    def error(self, message: str):
        token = self.current_token()
        raise SyntaxError(f"Parse error at line {token.line}, column {token.column}: {message}")
    
    def current_token(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]  # EOF token
    
    def peek_token(self, offset=1) -> Token:
        pos = self.pos + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return self.tokens[-1]  # EOF token
    
    def advance(self) -> Token:
        token = self.current_token()
        if token.type != TokenType.EOF:
            self.pos += 1
        return token
    
    def match(self, *types: TokenType) -> bool:
        return self.current_token().type in types
    
    def consume(self, token_type: TokenType) -> Token:
        if self.current_token().type != token_type:
            self.error(f"Expected {token_type}, got {self.current_token().type}")
        return self.advance()
    
    def skip_newlines(self):
        while self.match(TokenType.NEWLINE):
            self.advance()
    
    def parse(self) -> Program:
        statements = []
        self.skip_newlines()
        
        while not self.match(TokenType.EOF):
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
            self.skip_newlines()
        
        return Program(statements)
    
    def parse_statement(self) -> Optional[ASTNode]:
        self.skip_newlines()
        
        if self.match(TokenType.FUNCTION):
            return self.parse_function_def()
        elif self.match(TokenType.IF):
            return self.parse_if_statement()
        elif self.match(TokenType.WHILE):
            return self.parse_while_statement()
        elif self.match(TokenType.FOR):
            return self.parse_for_statement()
        elif self.match(TokenType.RETURN):
            return self.parse_return_statement()
        elif self.match(TokenType.BREAK):
            self.advance()
            return BreakStatement()
        elif self.match(TokenType.CONTINUE):
            self.advance()
            return ContinueStatement()
        else:
            return self.parse_expression_statement()
    
    def parse_expression_statement(self) -> ASTNode:
        expr = self.parse_expression()
        if self.match(TokenType.NEWLINE, TokenType.SEMICOLON, TokenType.EOF):
            self.advance()
        return expr
    
    def parse_function_def(self) -> FunctionDef:
        self.consume(TokenType.FUNCTION)
        name = self.consume(TokenType.IDENTIFIER).value
        
        self.consume(TokenType.LPAREN)
        params = []
        
        if not self.match(TokenType.RPAREN):
            params.append(self.consume(TokenType.IDENTIFIER).value)
            while self.match(TokenType.COMMA):
                self.advance()
                params.append(self.consume(TokenType.IDENTIFIER).value)
        
        self.consume(TokenType.RPAREN)
        self.consume(TokenType.COLON)
        
        body = self.parse_block()
        return FunctionDef(name, params, body)
    
    def parse_if_statement(self) -> IfStatement:
        self.consume(TokenType.IF)
        condition = self.parse_expression()
        self.consume(TokenType.COLON)
        then_body = self.parse_block()
        self.skip_newlines()
        
        elseif_parts = []
        while self.match(TokenType.ELSEIF):
            self.advance()
            elif_condition = self.parse_expression()
            self.consume(TokenType.COLON)
            elif_body = self.parse_block()
            self.skip_newlines()
            elseif_parts.append((elif_condition, elif_body))
        
        else_body = None
        if self.match(TokenType.ELSE):
            self.advance()
            self.consume(TokenType.COLON)
            else_body = self.parse_block()
        
        return IfStatement(condition, then_body, elseif_parts, else_body)
    
    def parse_while_statement(self) -> WhileStatement:
        self.consume(TokenType.WHILE)
        condition = self.parse_expression()
        self.consume(TokenType.COLON)
        body = self.parse_block()
        return WhileStatement(condition, body)
    
    def parse_for_statement(self) -> ForStatement:
        self.consume(TokenType.FOR)
        variable = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.IN)
        iterable = self.parse_expression()
        self.consume(TokenType.COLON)
        body = self.parse_block()
        return ForStatement(variable, iterable, body)
    
    def parse_return_statement(self) -> ReturnStatement:
        self.consume(TokenType.RETURN)
        value = None
        if not self.match(TokenType.NEWLINE, TokenType.SEMICOLON, TokenType.EOF):
            value = self.parse_expression()
        return ReturnStatement(value)
    
    def parse_block(self) -> List[ASTNode]:
        statements = []
        self.skip_newlines()
        
        if self.match(TokenType.LBRACE):
            self.advance()
            while not self.match(TokenType.RBRACE):
                self.skip_newlines()
                if self.match(TokenType.RBRACE):
                    break
                stmt = self.parse_statement()
                if stmt:
                    statements.append(stmt)
            self.consume(TokenType.RBRACE)
        else:
            # Single statement
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
        
        return statements
    
    def parse_expression(self) -> ASTNode:
        return self.parse_or_expression()
    
    def parse_or_expression(self) -> ASTNode:
        left = self.parse_and_expression()
        
        while self.match(TokenType.OR):
            op = self.advance().value
            right = self.parse_and_expression()
            left = BinaryOp(left, op, right)
        
        return left
    
    def parse_and_expression(self) -> ASTNode:
        left = self.parse_not_expression()
        
        while self.match(TokenType.AND):
            op = self.advance().value
            right = self.parse_not_expression()
            left = BinaryOp(left, op, right)
        
        return left
    
    def parse_not_expression(self) -> ASTNode:
        if self.match(TokenType.NOT):
            op = self.advance().value
            operand = self.parse_not_expression()
            return UnaryOp(op, operand)
        
        return self.parse_comparison()
    
    def parse_comparison(self) -> ASTNode:
        left = self.parse_additive()
        
        while self.match(TokenType.EQ, TokenType.NE, TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE, TokenType.IS):
            op = self.advance().value
            right = self.parse_additive()
            left = BinaryOp(left, op, right)
        
        return left
    
    def parse_additive(self) -> ASTNode:
        left = self.parse_multiplicative()
        
        while self.match(TokenType.PLUS, TokenType.MINUS):
            op = self.advance().value
            right = self.parse_multiplicative()
            left = BinaryOp(left, op, right)
        
        return left
    
    def parse_multiplicative(self) -> ASTNode:
        left = self.parse_power()
        
        while self.match(TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO):
            op = self.advance().value
            right = self.parse_power()
            left = BinaryOp(left, op, right)
        
        return left
    
    def parse_power(self) -> ASTNode:
        left = self.parse_unary()
        
        if self.match(TokenType.POWER):
            op = self.advance().value
            right = self.parse_power()
            left = BinaryOp(left, op, right)
        
        return left
    
    def parse_unary(self) -> ASTNode:
        if self.match(TokenType.MINUS, TokenType.PLUS):
            op = self.advance().value
            operand = self.parse_unary()
            return UnaryOp(op, operand)
        
        return self.parse_postfix()
    
    def parse_postfix(self) -> ASTNode:
        expr = self.parse_primary()
        
        while True:
            if self.match(TokenType.LPAREN):
                # Function call
                self.advance()
                args = []
                if not self.match(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        self.advance()
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN)
                
                if isinstance(expr, Identifier):
                    expr = FunctionCall(expr.name, args)
                else:
                    self.error("Can only call functions")
            
            elif self.match(TokenType.LBRACKET):
                # Index access
                self.advance()
                index = self.parse_expression()
                self.consume(TokenType.RBRACKET)
                expr = IndexAccess(expr, index)
            
            elif self.match(TokenType.DOT):
                # Attribute or method access
                self.advance()
                attr = self.consume(TokenType.IDENTIFIER).value
                
                if self.match(TokenType.LPAREN):
                    # Method call
                    self.advance()
                    args = []
                    if not self.match(TokenType.RPAREN):
                        args.append(self.parse_expression())
                        while self.match(TokenType.COMMA):
                            self.advance()
                            args.append(self.parse_expression())
                    self.consume(TokenType.RPAREN)
                    expr = MethodCall(expr, attr, args)
                else:
                    # Attribute access
                    expr = AttributeAccess(expr, attr)
            
            elif self.match(TokenType.ASSIGN) and isinstance(expr, Identifier):
                # Assignment
                self.advance()
                value = self.parse_expression()
                expr = Assignment(expr.name, value)
                break
            
            else:
                break
        
        return expr
    
    def parse_primary(self) -> ASTNode:
        if self.match(TokenType.INTEGER, TokenType.FLOAT):
            return Number(self.advance().value)
        
        elif self.match(TokenType.STRING):
            return String(self.advance().value)
        
        elif self.match(TokenType.TRUE):
            self.advance()
            return Boolean(True)
        
        elif self.match(TokenType.FALSE):
            self.advance()
            return Boolean(False)
        
        elif self.match(TokenType.NULL):
            self.advance()
            return Null()
        
        elif self.match(TokenType.IDENTIFIER):
            return Identifier(self.advance().value)
        
        elif self.match(TokenType.LPAREN):
            self.advance()
            expr = self.parse_expression()
            self.consume(TokenType.RPAREN)
            return expr
        
        elif self.match(TokenType.LBRACKET):
            return self.parse_list()
        
        elif self.match(TokenType.LBRACE):
            return self.parse_dict()
        
        else:
            self.error(f"Unexpected token: {self.current_token()}")
    
    def parse_list(self) -> ListLiteral:
        self.consume(TokenType.LBRACKET)
        elements = []
        
        if not self.match(TokenType.RBRACKET):
            elements.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                self.advance()
                if self.match(TokenType.RBRACKET):
                    break
                elements.append(self.parse_expression())
        
        self.consume(TokenType.RBRACKET)
        return ListLiteral(elements)
    
    def parse_dict(self) -> DictLiteral:
        self.consume(TokenType.LBRACE)
        pairs = []
        
        if not self.match(TokenType.RBRACE):
            key = self.parse_expression()
            self.consume(TokenType.COLON)
            value = self.parse_expression()
            pairs.append((key, value))
            
            while self.match(TokenType.COMMA):
                self.advance()
                if self.match(TokenType.RBRACE):
                    break
                key = self.parse_expression()
                self.consume(TokenType.COLON)
                value = self.parse_expression()
                pairs.append((key, value))
        
        self.consume(TokenType.RBRACE)
        return DictLiteral(pairs)
