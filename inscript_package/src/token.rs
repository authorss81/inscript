// inscript_rust_parser/src/token.rs
// Token types and token stream

#[derive(Debug, Clone, PartialEq)]
pub enum Token {
    // Literals
    Int(i64),
    Float(f64),
    String(String),
    Identifier(String),
    
    // Keywords
    Let, Const, Fn, Class, If, Else, While, For, In,
    Return, Break, Continue, Switch, Case, Default,
    True, False, Nil,
    Try, Catch, Finally, Throw,
    Async, Await, Yield,
    And, Or, Not,
    
    // Operators
    Plus, Minus, Star, Slash, Percent, Power,
    Assign,
    Eq, Neq, Lt, Lte, Gt, Gte,
    BitwiseAnd, BitwiseOr, BitwiseXor, BitwiseNot,
    LeftShift, RightShift,
    Question,
    
    // Delimiters
    LeftParen, RightParen,
    LeftBrace, RightBrace,
    LeftBracket, RightBracket,
    Comma, Dot, Semicolon, Colon,
    Arrow,
    
    // Special
    Eof,
}

#[derive(Debug, Clone)]
pub struct TokenInfo {
    pub token: Token,
    pub line: usize,
    pub column: usize,
}

impl TokenInfo {
    pub fn new(token: Token, line: usize, column: usize) -> Self {
        TokenInfo { token, line, column }
    }
}

pub fn precedence(token: &Token) -> u8 {
    match token {
        Token::Or => 1,
        Token::And => 2,
        Token::Eq | Token::Neq => 3,
        Token::Lt | Token::Lte | Token::Gt | Token::Gte => 4,
        Token::BitwiseOr => 5,
        Token::BitwiseXor => 6,
        Token::BitwiseAnd => 7,
        Token::LeftShift | Token::RightShift => 8,
        Token::Plus | Token::Minus => 9,
        Token::Star | Token::Slash | Token::Percent => 10,
        Token::Power => 11,
        _ => 0,
    }
}
