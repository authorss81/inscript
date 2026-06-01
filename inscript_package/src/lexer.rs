//! High-performance lexer with state machine

use crate::token::{Token, TokenType};
use crate::error::{LexError, LexResult};

/// Fast lexer with zero-copy tokens
pub struct Lexer<'a> {
    input: &'a str,
    chars: std::str::Chars<'a>,
    current: Option<char>,
    position: usize,
    line: usize,
    column: usize,
}

impl<'a> Lexer<'a> {
    /// Create new lexer
    pub fn new(input: &'a str) -> Self {
        let mut chars = input.chars();
        let current = chars.next();
        
        Lexer {
            input,
            chars,
            current,
            position: 0,
            line: 1,
            column: 1,
        }
    }

    /// Advance to next character
    #[inline]
    fn advance(&mut self) {
        if let Some(ch) = self.current {
            if ch == '\n' {
                self.line += 1;
                self.column = 1;
            } else {
                self.column += 1;
            }
            self.position += ch.len_utf8();
        }
        self.current = self.chars.next();
    }

    /// Peek at current character
    #[inline]
    fn peek(&self) -> Option<char> {
        self.current
    }

    /// Skip whitespace and comments
    fn skip_whitespace(&mut self) {
        while let Some(ch) = self.peek() {
            match ch {
                ' ' | '\t' | '\r' => self.advance(),
                '\n' => {
                    // Newline is significant in some languages
                    break;
                }
                _ => break,
            }
        }
    }

    /// Scan number (integer or float)
    fn scan_number(&mut self, start: usize) -> LexResult<Token<'a>> {
        let start_line = self.line;
        let start_col = self.column;
        
        while let Some(ch) = self.peek() {
            if ch.is_ascii_digit() {
                self.advance();
            } else if ch == '.' && !self.input[self.position..].starts_with("..") {
                self.advance();
                while let Some(c) = self.peek() {
                    if c.is_ascii_digit() {
                        self.advance();
                    } else {
                        break;
                    }
                }
                break;
            } else {
                break;
            }
        }

        Ok(Token::new(
            TokenType::Number,
            &self.input[start..self.position],
            start_line,
            start_col,
        ))
    }

    /// Scan string literal
    fn scan_string(&mut self, quote: char, start: usize) -> LexResult<Token<'a>> {
        let start_line = self.line;
        let start_col = self.column;
        
        self.advance(); // Skip opening quote

        while let Some(ch) = self.peek() {
            if ch == quote {
                self.advance(); // Skip closing quote
                break;
            } else if ch == '\\' {
                self.advance();
                self.advance(); // Skip escaped character
            } else if ch == '\n' {
                return Err(LexError::new("Unterminated string", self.line, self.column));
            } else {
                self.advance();
            }
        }

        Ok(Token::new(
            TokenType::String,
            &self.input[start..self.position],
            start_line,
            start_col,
        ))
    }

    /// Scan identifier or keyword
    fn scan_identifier(&mut self, start: usize) -> LexResult<Token<'a>> {
        let start_line = self.line;
        let start_col = self.column;
        
        while let Some(ch) = self.peek() {
            if ch.is_alphanumeric() || ch == '_' {
                self.advance();
            } else {
                break;
            }
        }

        let value = &self.input[start..self.position];
        let token_type = Token::is_keyword(value).unwrap_or(TokenType::Identifier);

        Ok(Token::new(token_type, value, start_line, start_col))
    }

    /// Get next token
    pub fn next_token(&mut self) -> LexResult<Option<Token<'a>>> {
        self.skip_whitespace();

        let ch = match self.peek() {
            Some(c) => c,
            None => return Ok(None),
        };

        let start = self.position;
        let start_line = self.line;
        let start_col = self.column;

        let token_type = match ch {
            // Delimiters
            '(' => {
                self.advance();
                TokenType::LeftParen
            }
            ')' => {
                self.advance();
                TokenType::RightParen
            }
            '{' => {
                self.advance();
                TokenType::LeftBrace
            }
            '}' => {
                self.advance();
                TokenType::RightBrace
            }
            '[' => {
                self.advance();
                TokenType::LeftBracket
            }
            ']' => {
                self.advance();
                TokenType::RightBracket
            }
            ',' => {
                self.advance();
                TokenType::Comma
            }
            '.' => {
                self.advance();
                TokenType::Dot
            }
            ';' => {
                self.advance();
                TokenType::Semicolon
            }
            ':' => {
                self.advance();
                TokenType::Colon
            }
            
            // Operators
            '+' => {
                self.advance();
                TokenType::Plus
            }
            '-' => {
                self.advance();
                if self.peek() == Some('>') {
                    self.advance();
                    TokenType::Arrow
                } else {
                    TokenType::Minus
                }
            }
            '*' => {
                self.advance();
                TokenType::Star
            }
            '/' => {
                self.advance();
                TokenType::Slash
            }
            '%' => {
                self.advance();
                TokenType::Percent
            }
            '=' => {
                self.advance();
                if self.peek() == Some('=') {
                    self.advance();
                    TokenType::EqualEqual
                } else {
                    TokenType::Equal
                }
            }
            '!' => {
                self.advance();
                if self.peek() == Some('=') {
                    self.advance();
                    TokenType::NotEqual
                } else {
                    TokenType::Not
                }
            }
            '<' => {
                self.advance();
                if self.peek() == Some('=') {
                    self.advance();
                    TokenType::LessEqual
                } else {
                    TokenType::Less
                }
            }
            '>' => {
                self.advance();
                if self.peek() == Some('=') {
                    self.advance();
                    TokenType::GreaterEqual
                } else {
                    TokenType::Greater
                }
            }
            
            // Numbers
            '0'..='9' => {
                return self.scan_number(start).map(Some);
            }
            
            // Strings
            '"' | '\'' => {
                return self.scan_string(ch, start).map(Some);
            }
            
            // Identifiers and keywords
            'a'..='z' | 'A'..='Z' | '_' => {
                return self.scan_identifier(start).map(Some);
            }
            
            _ => {
                self.advance();
                return Err(LexError::new(
                    format!("Unexpected character: '{}'", ch),
                    self.line,
                    self.column,
                ));
            }
        };

        Ok(Some(Token::new(
            token_type,
            &self.input[start..self.position],
            start_line,
            start_col,
        )))
    }
}

/// Iterator implementation for convenience
impl<'a> Iterator for Lexer<'a> {
    type Item = LexResult<Token<'a>>;

    fn next(&mut self) -> Option<Self::Item> {
        match self.next_token() {
            Ok(Some(token)) => Some(Ok(token)),
            Ok(None) => None,
            Err(e) => Some(Err(e)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simple_tokens() {
        let lexer = Lexer::new("let x = 42;");
        let tokens: Vec<_> = lexer.collect::<Result<_, _>>().unwrap();
        
        assert_eq!(tokens.len(), 5); // let, x, =, 42, ;
        assert_eq!(tokens[0].token_type, TokenType::Identifier);
        assert_eq!(tokens[2].token_type, TokenType::Equal);
        assert_eq!(tokens[3].token_type, TokenType::Number);
    }

    #[test]
    fn test_keywords() {
        let lexer = Lexer::new("if true else false");
        let tokens: Vec<_> = lexer.collect::<Result<_, _>>().unwrap();
        
        assert_eq!(tokens[0].token_type, TokenType::If);
        assert_eq!(tokens[1].token_type, TokenType::True);
        assert_eq!(tokens[2].token_type, TokenType::Else);
        assert_eq!(tokens[3].token_type, TokenType::False);
    }

    #[test]
    fn test_strings() {
        let lexer = Lexer::new(r#""hello" 'world'"#);
        let tokens: Vec<_> = lexer.collect::<Result<_, _>>().unwrap();
        
        assert_eq!(tokens.len(), 2);
        assert_eq!(tokens[0].token_type, TokenType::String);
        assert_eq!(tokens[1].token_type, TokenType::String);
    }
}
