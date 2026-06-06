// inscript_rust_parser/src/error.rs
// Parser error types with context

use std::fmt;

#[derive(Debug, Clone)]
pub struct ParseError {
    pub message: String,
    pub line: usize,
    pub column: usize,
    pub context: String,
}

impl ParseError {
    pub fn new(message: impl Into<String>, line: usize, column: usize) -> Self {
        ParseError {
            message: message.into(),
            line,
            column,
            context: String::new(),
        }
    }

    pub fn with_context(mut self, context: impl Into<String>) -> Self {
        self.context = context.into();
        self
    }
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(
            f,
            "ParseError at {}:{}: {}{}",
            self.line,
            self.column,
            self.message,
            if self.context.is_empty() {
                String::new()
            } else {
                format!("\n  Context: {}", self.context)
            }
        )
    }
}

impl std::error::Error for ParseError {}
