//! Lexer error types

use std::fmt;

#[derive(Debug, Clone)]
pub struct LexError {
    pub message: String,
    pub line: usize,
    pub column: usize,
}

impl LexError {
    pub fn new(message: impl Into<String>, line: usize, column: usize) -> Self {
        LexError {
            message: message.into(),
            line,
            column,
        }
    }
}

impl fmt::Display for LexError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}:{}: {}", self.line, self.column, self.message)
    }
}

impl std::error::Error for LexError {}

pub type LexResult<T> = Result<T, LexError>;
