//! Token definitions

use std::fmt;

/// Token types
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TokenType {
    // Literals
    Number,
    String,
    Identifier,
    
    // Keywords
    If,
    Else,
    While,
    For,
    Function,
    Return,
    True,
    False,
    Nil,
    
    // Operators
    Plus,
    Minus,
    Star,
    Slash,
    Percent,
    Equal,
    EqualEqual,
    NotEqual,
    Less,
    LessEqual,
    Greater,
    GreaterEqual,
    And,
    Or,
    Not,
    
    // Delimiters
    LeftParen,
    RightParen,
    LeftBrace,
    RightBrace,
    LeftBracket,
    RightBracket,
    Comma,
    Dot,
    Semicolon,
    Colon,
    Arrow,
    
    // Special
    Newline,
    EOF,
}

impl fmt::Display for TokenType {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{:?}", self)
    }
}

/// Token with metadata
#[derive(Debug, Clone)]
pub struct Token<'a> {
    pub token_type: TokenType,
    pub value: &'a str,
    pub line: usize,
    pub column: usize,
}

impl<'a> Token<'a> {
    /// Create new token
    pub fn new(token_type: TokenType, value: &'a str, line: usize, column: usize) -> Self {
        Token {
            token_type,
            value,
            line,
            column,
        }
    }

    /// Check if keyword
    pub fn is_keyword(value: &str) -> Option<TokenType> {
        match value {
            "if" => Some(TokenType::If),
            "else" => Some(TokenType::Else),
            "while" => Some(TokenType::While),
            "for" => Some(TokenType::For),
            "fn" => Some(TokenType::Function),
            "return" => Some(TokenType::Return),
            "true" => Some(TokenType::True),
            "false" => Some(TokenType::False),
            "nil" => Some(TokenType::Nil),
            "and" => Some(TokenType::And),
            "or" => Some(TokenType::Or),
            "not" => Some(TokenType::Not),
            _ => None,
        }
    }
}
