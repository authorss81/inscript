"""
Lexer for Inscript language.
Tokenizes source code into a stream of tokens.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional

class TokenType(Enum):
    # Literals
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    
    # Keywords
    FUNCTION = auto()
    RETURN = auto()
    IF = auto()
    ELSE = auto()
    ELSEIF = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    BREAK = auto()
    CONTINUE = auto()
    CLASS = auto()
    IMPORT = auto()
    FROM = auto()
    AS = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    IS = auto()
    
    # Identifiers and operators
    IDENTIFIER = auto()
    
    # Operators
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    MODULO = auto()
    POWER = auto()
    ASSIGN = auto()
    PLUS_ASSIGN = auto()
    MINUS_ASSIGN = auto()
    
    # Comparison
    EQ = auto()
    NE = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    
    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    COLON = auto()
    DOT = auto()
    SEMICOLON = auto()
    ARROW = auto()
    
    # Special
    NEWLINE = auto()
    EOF = auto()
    INDENT = auto()
    DEDENT = auto()

@dataclass
class Token:
    type: TokenType
    value: any
    line: int
    column: int

class Lexer:
    KEYWORDS = {
        'function': TokenType.FUNCTION,
        'return': TokenType.RETURN,
        'if': TokenType.IF,
        'else': TokenType.ELSE,
        'elseif': TokenType.ELSEIF,
        'while': TokenType.WHILE,
        'for': TokenType.FOR,
        'in': TokenType.IN,
        'break': TokenType.BREAK,
        'continue': TokenType.CONTINUE,
        'class': TokenType.CLASS,
        'import': TokenType.IMPORT,
        'from': TokenType.FROM,
        'as': TokenType.AS,
        'and': TokenType.AND,
        'or': TokenType.OR,
        'not': TokenType.NOT,
        'is': TokenType.IS,
        'true': TokenType.TRUE,
        'false': TokenType.FALSE,
        'null': TokenType.NULL,
    }
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        self.indent_stack = [0]
    
    def error(self, message: str):
        raise SyntaxError(f"Lexer error at line {self.line}, column {self.column}: {message}")
    
    def peek(self, offset: int = 0) -> Optional[str]:
        pos = self.pos + offset
        if pos < len(self.source):
            return self.source[pos]
        return None
    
    def advance(self) -> Optional[str]:
        if self.pos < len(self.source):
            char = self.source[self.pos]
            self.pos += 1
            if char == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            return char
        return None
    
    def skip_whitespace(self, skip_newlines=True):
        while self.peek() and self.peek() in ' \t':
            self.advance()
        
        if skip_newlines:
            while self.peek() and self.peek() in '\n\r':
                if self.peek() == '\n':
                    self.advance()
                elif self.peek() == '\r':
                    self.advance()
                    if self.peek() == '\n':
                        self.advance()
    
    def skip_comment(self):
        if self.peek() == '#':
            while self.peek() and self.peek() != '\n':
                self.advance()
    
    def read_string(self, quote: str) -> str:
        value = ""
        self.advance()  # skip opening quote
        
        while True:
            char = self.peek()
            if char is None:
                self.error("Unterminated string")
            elif char == quote:
                self.advance()
                break
            elif char == '\\':
                self.advance()
                escape_char = self.advance()
                if escape_char == 'n':
                    value += '\n'
                elif escape_char == 't':
                    value += '\t'
                elif escape_char == 'r':
                    value += '\r'
                elif escape_char == '\\':
                    value += '\\'
                elif escape_char == quote:
                    value += quote
                else:
                    value += escape_char
            else:
                value += char
                self.advance()
        
        return value
    
    def read_number(self) -> Token:
        start_line = self.line
        start_column = self.column
        value = ""
        is_float = False
        
        while self.peek() and (self.peek().isdigit() or self.peek() == '.'):
            if self.peek() == '.':
                if is_float:
                    break
                is_float = True
            value += self.peek()
            self.advance()
        
        if is_float:
            return Token(TokenType.FLOAT, float(value), start_line, start_column)
        else:
            return Token(TokenType.INTEGER, int(value), start_line, start_column)
    
    def read_identifier(self) -> Token:
        start_line = self.line
        start_column = self.column
        value = ""
        
        while self.peek() and (self.peek().isalnum() or self.peek() in '_'):
            value += self.peek()
            self.advance()
        
        token_type = self.KEYWORDS.get(value, TokenType.IDENTIFIER)
        return Token(token_type, value, start_line, start_column)
    
    def tokenize(self) -> List[Token]:
        while self.pos < len(self.source):
            self.skip_whitespace(skip_newlines=False)
            self.skip_comment()
            
            if self.pos >= len(self.source):
                break
            
            char = self.peek()
            line = self.line
            column = self.column
            
            # Newline
            if char == '\n':
                self.advance()
                self.tokens.append(Token(TokenType.NEWLINE, '\n', line, column))
                continue
            
            # Skip spaces/tabs
            if char in ' \t':
                self.advance()
                continue
            
            # Strings
            if char in '"\'':
                value = self.read_string(char)
                self.tokens.append(Token(TokenType.STRING, value, line, column))
                continue
            
            # Numbers
            if char.isdigit():
                self.tokens.append(self.read_number())
                continue
            
            # Identifiers and keywords
            if char.isalpha() or char == '_':
                self.tokens.append(self.read_identifier())
                continue
            
            # Operators and delimiters
            self.advance()
            
            if char == '+':
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.PLUS_ASSIGN, '+=', line, column))
                else:
                    self.tokens.append(Token(TokenType.PLUS, '+', line, column))
            elif char == '-':
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.MINUS_ASSIGN, '-=', line, column))
                elif self.peek() == '>':
                    self.advance()
                    self.tokens.append(Token(TokenType.ARROW, '->', line, column))
                else:
                    self.tokens.append(Token(TokenType.MINUS, '-', line, column))
            elif char == '*':
                if self.peek() == '*':
                    self.advance()
                    self.tokens.append(Token(TokenType.POWER, '**', line, column))
                else:
                    self.tokens.append(Token(TokenType.MULTIPLY, '*', line, column))
            elif char == '/':
                self.tokens.append(Token(TokenType.DIVIDE, '/', line, column))
            elif char == '%':
                self.tokens.append(Token(TokenType.MODULO, '%', line, column))
            elif char == '=':
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.EQ, '==', line, column))
                else:
                    self.tokens.append(Token(TokenType.ASSIGN, '=', line, column))
            elif char == '!':
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.NE, '!=', line, column))
                else:
                    self.error(f"Unexpected character: {char}")
            elif char == '<':
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.LE, '<=', line, column))
                else:
                    self.tokens.append(Token(TokenType.LT, '<', line, column))
            elif char == '>':
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.GE, '>=', line, column))
                else:
                    self.tokens.append(Token(TokenType.GT, '>', line, column))
            elif char == '(':
                self.tokens.append(Token(TokenType.LPAREN, '(', line, column))
            elif char == ')':
                self.tokens.append(Token(TokenType.RPAREN, ')', line, column))
            elif char == '{':
                self.tokens.append(Token(TokenType.LBRACE, '{', line, column))
            elif char == '}':
                self.tokens.append(Token(TokenType.RBRACE, '}', line, column))
            elif char == '[':
                self.tokens.append(Token(TokenType.LBRACKET, '[', line, column))
            elif char == ']':
                self.tokens.append(Token(TokenType.RBRACKET, ']', line, column))
            elif char == ',':
                self.tokens.append(Token(TokenType.COMMA, ',', line, column))
            elif char == ':':
                self.tokens.append(Token(TokenType.COLON, ':', line, column))
            elif char == '.':
                self.tokens.append(Token(TokenType.DOT, '.', line, column))
            elif char == ';':
                self.tokens.append(Token(TokenType.SEMICOLON, ';', line, column))
            else:
                self.error(f"Unexpected character: {char}")
        
        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens
