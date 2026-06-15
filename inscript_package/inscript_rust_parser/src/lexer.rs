// inscript_rust_parser/src/lexer.rs
// Character-by-character lexer for InScript

use crate::token::{Token, TokenInfo};

pub struct Lexer {
    source: Vec<char>,
    pos: usize,
    line: usize,
    col: usize,
    tokens: Vec<TokenInfo>,
}

impl Lexer {
    pub fn new(source: &str) -> Self {
        Lexer {
            source: source.chars().collect(),
            pos: 0,
            line: 1,
            col: 1,
            tokens: Vec::new(),
        }
    }

    pub fn tokenize(&mut self) -> Result<Vec<TokenInfo>, String> {
        while self.pos < self.source.len() {
            self.scan_token()?;
        }
        self.emit(Token::Eof);
        Ok(self.tokens.clone())
    }

    // ── Character helpers ─────────────────────────────────────────

    fn current(&self) -> Option<char> {
        self.source.get(self.pos).copied()
    }

    fn peek(&self) -> Option<char> {
        self.source.get(self.pos + 1).copied()
    }

    fn peek_at(&self, offset: usize) -> Option<char> {
        self.source.get(self.pos + offset).copied()
    }

    fn advance(&mut self) -> Option<char> {
        let ch = self.source.get(self.pos).copied()?;
        self.pos += 1;
        if ch == '\n' {
            self.line += 1;
            self.col = 1;
        } else {
            self.col += 1;
        }
        Some(ch)
    }

    fn match_char(&mut self, expected: char) -> bool {
        if self.current() == Some(expected) {
            self.advance();
            true
        } else {
            false
        }
    }

    fn emit(&mut self, token: Token) {
        let info = TokenInfo::new(token, self.line, self.col);
        self.tokens.push(info);
    }

    fn emit_with(&mut self, token: Token, line: usize, col: usize) {
        let info = TokenInfo::new(token, line, col);
        self.tokens.push(info);
    }

    fn error(&self, msg: &str) -> String {
        format!("Lexer error at {}:{}: {}", self.line, self.col, msg)
    }

    // ── Main scanner ──────────────────────────────────────────────

    fn scan_token(&mut self) -> Result<(), String> {
        let sl = self.line;
        let sc = self.col;
        let ch = self.advance().ok_or_else(|| self.error("Unexpected EOF"))?;

        // Skip whitespace
        if ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n' {
            return Ok(());
        }

        // Line comment #
        if ch == '#' {
            self.skip_line_comment();
            return Ok(());
        }

        // / operators: /// doc comment, // floor division, /* block comment, / division
        if ch == '/' {
            return self.scan_slash(sl, sc);
        }

        // String literals
        if ch == '"' || ch == '\'' {
            if self.current() == Some(ch) && self.peek() == Some(ch) {
                self.advance(); self.advance();
                return self.scan_triple_string(ch, sl, sc);
            }
            return self.scan_string(ch, sl, sc);
        }

        // Numbers: 0x, 0b, 0o prefixed, or decimal
        if ch == '0' && matches!(self.current(), Some('x' | 'X' | 'b' | 'B' | 'o' | 'O')) {
            return self.scan_prefixed_number(sl, sc);
        }
        if ch.is_ascii_digit() {
            return self.scan_number(ch, sl, sc);
        }

        // Identifiers and keywords
        if ch.is_ascii_alphabetic() || ch == '_' {
            // Check for f"...", F"...", r"...", R"..." string prefixes
            if (ch == 'f' || ch == 'F') && matches!(self.current(), Some('"' | '\'')) {
                let q = self.advance().unwrap();
                return self.scan_fstring(q, sl, sc, false);
            }
            if (ch == 'r' || ch == 'R') && matches!(self.current(), Some('"' | '\'')) {
                let q = self.advance().unwrap();
                return self.scan_raw_string(q, sl, sc);
            }
            return self.scan_identifier(ch, sl, sc);
        }

        // $"...": interpolated string (preferred over f"...")
        if ch == '$' && matches!(self.current(), Some('"' | '\'')) {
            let q = self.advance().unwrap();
            return self.scan_fstring(q, sl, sc, true);
        }

        // Non-ASCII: skip silently
        if !ch.is_ascii() {
            return Ok(());
        }

        // Operators
        self.scan_operator(ch, sl, sc)
    }

    // ── Comments ──────────────────────────────────────────────────

    fn skip_line_comment(&mut self) {
        while self.current().is_some() && self.current() != Some('\n') {
            self.advance();
        }
    }

    // ── Slash variants ──────────────────────────────────────────

    fn scan_slash(&mut self, sl: usize, sc: usize) -> Result<(), String> {
        match self.current() {
            // /// doc comment → skip
            Some('/') if self.peek() == Some('/') => {
                self.advance();
                self.advance();
                self.skip_line_comment();
                Ok(())
            }
            // // floor division
            Some('/') => {
                self.advance();
                self.emit_with(Token::SlashSlash, sl, sc);
                Ok(())
            }
            // /* block comment
            Some('*') => {
                self.advance();
                self.skip_block_comment(sl, sc)
            }
            // /= compound assign
            Some('=') => {
                self.advance();
                self.emit_with(Token::SlashEq, sl, sc);
                Ok(())
            }
            // / division
            _ => {
                self.emit_with(Token::Slash, sl, sc);
                Ok(())
            }
        }
    }

    fn skip_block_comment(&mut self, sl: usize, sc: usize) -> Result<(), String> {
        let mut depth = 1usize;
        while self.current().is_some() && depth > 0 {
            let ch = self.advance().unwrap();
            if ch == '/' && self.current() == Some('*') {
                self.advance();
                depth += 1;
            } else if ch == '*' && self.current() == Some('/') {
                self.advance();
                depth -= 1;
            }
        }
        if depth > 0 {
            return Err(format!("Unterminated block comment at {}:{}", sl, sc));
        }
        Ok(())
    }

    // ── Strings ───────────────────────────────────────────────────

    fn scan_string(&mut self, quote: char, sl: usize, sc: usize) -> Result<(), String> {
        let mut chars = Vec::new();
        loop {
            match self.current() {
                None => return Err(self.error("Unterminated string literal")),
                Some(c) if c == quote => {
                    self.advance();
                    break;
                }
                Some('\n') => return Err(self.error("Unterminated string — newline inside string")),
                Some('\\') => {
                    self.advance();
                    match self.advance() {
                        None => return Err(self.error("Unterminated escape sequence")),
                        Some('n') => chars.push('\n'),
                        Some('t') => chars.push('\t'),
                        Some('r') => chars.push('\r'),
                        Some('\\') => chars.push('\\'),
                        Some('"') => chars.push('"'),
                        Some('\'') => chars.push('\''),
                        Some('0') => chars.push('\0'),
                        Some('a') => chars.push('\x07'),
                        Some('b') => chars.push('\x08'),
                        Some(c) => return Err(format!("Unknown escape sequence: \\{}", c)),
                    }
                }
                Some(c) => {
                    chars.push(c);
                    self.advance();
                }
            }
        }
        let s: String = chars.into_iter().collect();
        self.emit_with(Token::String(s), sl, sc);
        Ok(())
    }

    fn scan_raw_string(&mut self, quote: char, sl: usize, sc: usize) -> Result<(), String> {
        let mut chars = Vec::new();
        loop {
            match self.current() {
                None => return Err(self.error("Unterminated raw string literal")),
                Some(c) if c == quote => {
                    self.advance();
                    break;
                }
                Some('\n') => return Err(self.error("Unterminated raw string — newline inside string")),
                Some(c) => {
                    chars.push(c);
                    self.advance();
                }
            }
        }
        let s: String = chars.into_iter().collect();
        self.emit_with(Token::String(s), sl, sc);
        Ok(())
    }

    fn scan_triple_string(&mut self, quote: char, sl: usize, sc: usize) -> Result<(), String> {
        let mut chars = Vec::new();
        loop {
            match self.current() {
                None => return Err(self.error("Unterminated triple-quoted string")),
                Some(c) if c == quote && self.peek() == Some(quote) && self.peek_at(2) == Some(quote) => {
                    self.advance(); self.advance(); self.advance();
                    break;
                }
                Some('\\') => {
                    self.advance();
                    match self.advance() {
                        None => return Err(self.error("Unterminated escape in triple-quoted string")),
                        Some('n') => chars.push('\n'),
                        Some('t') => chars.push('\t'),
                        Some('r') => chars.push('\r'),
                        Some('\\') => chars.push('\\'),
                        Some('"') => chars.push('"'),
                        Some('\'') => chars.push('\''),
                        Some('0') => chars.push('\0'),
                        Some(c) => chars.push(c),
                    }
                }
                Some(c) => {
                    chars.push(c);
                    self.advance();
                }
            }
        }
        let s: String = chars.into_iter().collect();
        self.emit_with(Token::String(s), sl, sc);
        Ok(())
    }

    fn scan_fstring(&mut self, quote: char, sl: usize, sc: usize, _dollar: bool) -> Result<(), String> {
        // Store raw template; {{ → \x00{, }} → }\x00 (brace escapes)
        let mut chars = Vec::new();
        let mut brace_depth = 0usize;
        loop {
            match self.current() {
                None => return Err(self.error("Unterminated f-string")),
                Some(c) if c == quote && brace_depth == 0 => {
                    self.advance();
                    break;
                }
                Some('\n') => return Err(self.error("Unterminated f-string — newline inside string")),
                Some('{') if self.peek() == Some('{') && brace_depth == 0 => {
                    self.advance(); // consume first {
                    self.advance(); // consume second {
                    chars.push('\x00');
                    chars.push('{');
                }
                Some('}') if self.peek() == Some('}') && brace_depth == 0 => {
                    self.advance(); // consume first }
                    self.advance(); // consume second }
                    chars.push('}');
                    chars.push('\x00');
                }
                Some('{') => {
                    brace_depth += 1;
                    chars.push('{');
                    self.advance();
                }
                Some('}') => {
                    brace_depth = brace_depth.saturating_sub(1);
                    chars.push('}');
                    self.advance();
                }
                Some('\\') if brace_depth == 0 => {
                    self.advance();
                    match self.advance() {
                        None => return Err(self.error("Unterminated escape in f-string")),
                        Some('n') => chars.push('\n'),
                        Some('t') => chars.push('\t'),
                        Some('r') => chars.push('\r'),
                        Some('\\') => chars.push('\\'),
                        Some('"') => chars.push('"'),
                        Some('\'') => chars.push('\''),
                        Some(c) => chars.push(c),
                    }
                }
                Some(c) => {
                    chars.push(c);
                    self.advance();
                }
            }
        }
        let s: String = chars.into_iter().collect();
        self.emit_with(Token::FString(s), sl, sc);
        Ok(())
    }

    // ── Numbers ───────────────────────────────────────────────────

    fn scan_prefixed_number(&mut self, sl: usize, sc: usize) -> Result<(), String> {
        let prefix = self.advance().unwrap(); // x, X, b, B, o, O
        let mut digits = Vec::new();
        match prefix {
            'x' | 'X' => {
                while let Some(c) = self.current() {
                    if c.is_ascii_hexdigit() || c == '_' {
                        digits.push(self.advance().unwrap());
                    } else {
                        break;
                    }
                }
                if digits.is_empty() {
                    return Err(self.error("Expected hex digits after '0x'"));
                }
                let raw: String = digits.iter().filter(|&&c| c != '_').collect();
                let val = i64::from_str_radix(&raw, 16).unwrap_or(0);
                self.emit_with(Token::Int(val), sl, sc);
            }
            'b' | 'B' => {
                while let Some(c) = self.current() {
                    if c == '0' || c == '1' || c == '_' {
                        digits.push(self.advance().unwrap());
                    } else {
                        break;
                    }
                }
                if digits.is_empty() {
                    return Err(self.error("Expected binary digits after '0b'"));
                }
                let raw: String = digits.iter().filter(|&&c| c != '_').collect();
                let val = i64::from_str_radix(&raw, 2).unwrap_or(0);
                self.emit_with(Token::Int(val), sl, sc);
            }
            'o' | 'O' => {
                while let Some(c) = self.current() {
                    if c.is_ascii_digit() && c != '8' && c != '9' || c == '_' {
                        digits.push(self.advance().unwrap());
                    } else {
                        break;
                    }
                }
                if digits.is_empty() {
                    return Err(self.error("Expected octal digits after '0o'"));
                }
                let raw: String = digits.iter().filter(|&&c| c != '_').collect();
                let val = i64::from_str_radix(&raw, 8).unwrap_or(0);
                self.emit_with(Token::Int(val), sl, sc);
            }
            _ => unreachable!(),
        }
        Ok(())
    }

    fn scan_number(&mut self, first: char, sl: usize, sc: usize) -> Result<(), String> {
        let mut digits = vec![first];
        // Integer part
        while let Some(c) = self.current() {
            if c.is_ascii_digit() || c == '_' {
                digits.push(self.advance().unwrap());
            } else {
                break;
            }
        }
        let mut is_float = false;

        // Decimal point — but check it's not `..` (range operator)
        if self.current() == Some('.') && self.peek() != Some('.') {
            is_float = true;
            digits.push(self.advance().unwrap());
            if !self.current().map_or(false, |c| c.is_ascii_digit()) {
                return Err(self.error("Expected digits after decimal point"));
            }
            while let Some(c) = self.current() {
                if c.is_ascii_digit() || c == '_' {
                    digits.push(self.advance().unwrap());
                } else {
                    break;
                }
            }
        }

        // Scientific notation
        if matches!(self.current(), Some('e' | 'E')) {
            is_float = true;
            digits.push(self.advance().unwrap());
            if matches!(self.current(), Some('+' | '-')) {
                digits.push(self.advance().unwrap());
            }
            if !self.current().map_or(false, |c| c.is_ascii_digit()) {
                return Err(self.error("Expected digits in scientific notation exponent"));
            }
            while let Some(c) = self.current() {
                if c.is_ascii_digit() {
                    digits.push(self.advance().unwrap());
                } else {
                    break;
                }
            }
        }

        let raw: String = digits.iter().filter(|&&c| c != '_').collect();
        if is_float {
            let val: f64 = raw.parse().unwrap_or(0.0);
            self.emit_with(Token::Float(val), sl, sc);
        } else {
            let val: i64 = raw.parse().unwrap_or(0);
            self.emit_with(Token::Int(val), sl, sc);
        }
        Ok(())
    }

    // ── Identifiers & Keywords ────────────────────────────────────

    fn scan_identifier(&mut self, first: char, sl: usize, sc: usize) -> Result<(), String> {
        let mut chars = vec![first];
        while let Some(c) = self.current() {
            if c.is_ascii_alphanumeric() || c == '_' {
                chars.push(self.advance().unwrap());
            } else {
                break;
            }
        }
        let text: String = chars.into_iter().collect();
        let token = self.keyword_or_ident(&text);
        self.emit_with(token, sl, sc);
        Ok(())
    }

    fn keyword_or_ident(&self, text: &str) -> Token {
        match text {
            // Keywords mapped to dedicated variants
            "let" => Token::Let,
            "const" => Token::Const,
            "fn" => Token::Fn,
            "if" => Token::If,
            "else" => Token::Else,
            "while" => Token::While,
            "for" => Token::For,
            "in" => Token::In,
            "return" => Token::Return,
            "break" => Token::Break,
            "continue" => Token::Continue,
            "struct" => Token::Struct,
            "class" => Token::Class,
            "enum" => Token::Enum,
            "scene" => Token::Class,
            "match" => Token::Switch,
            "case" => Token::Case,
            "true" => Token::Bool(true),
            "false" => Token::Bool(false),
            "nil" => Token::Nil,
            "null" => Token::Null,
            "try" => Token::Try,
            "catch" => Token::Catch,
            "finally" => Token::Finally,
            "throw" => Token::Throw,
            "async" => Token::Async,
            "await" => Token::Await,
            "yield" => Token::Yield,
            "and" => Token::And,
            "or" => Token::Or,
            "not" => Token::Not,
            "is" => Token::Is,
            "div" => Token::Div,

            // Keywords mapped to Identifier (soft keywords)
            "import" => Token::Identifier("import".to_string()),
            "from" => Token::Identifier("from".to_string()),
            "as" => Token::Identifier("as".to_string()),
            "export" => Token::Identifier("export".to_string()),
            "self" => Token::Identifier("self".to_string()),
            "super" => Token::Identifier("super".to_string()),
            "spawn" => Token::Identifier("spawn".to_string()),
            "select" => Token::Identifier("select".to_string()),
            "then" => Token::Identifier("then".to_string()),
            "abstract" => Token::Identifier("abstract".to_string()),
            "interface" => Token::Identifier("interface".to_string()),
            "impl" => Token::Identifier("impl".to_string()),
            "pub" => Token::Identifier("pub".to_string()),
            "defer" => Token::Identifier("defer".to_string()),
            "repeat" => Token::Identifier("repeat".to_string()),
            "until" => Token::Identifier("until".to_string()),

            // Lifecycle keywords
            "on_start" => Token::OnStart,
            "on_update" => Token::OnUpdate,
            "on_draw" => Token::OnDraw,
            "on_exit" => Token::OnExit,
            "node" => Token::Node,
            "_ready" => Token::OnReady,
            "_update" => Token::OnNodeUpdate,
            "_draw" => Token::OnNodeDraw,

            // Type names
            "int" => Token::IntType,
            "float" => Token::FloatType,
            "bool" => Token::BoolType,
            "string" => Token::StringType,
            "void" => Token::VoidType,

            // Other soft keywords → Identifier
            "extends" => Token::Identifier("extends".to_string()),
            "static" => Token::Identifier("static".to_string()),
            "override" => Token::Identifier("override".to_string()),
            "implements" => Token::Identifier("implements".to_string()),
            "mixin" => Token::Identifier("mixin".to_string()),
            "with" => Token::Identifier("with".to_string()),
            "get" => Token::Identifier("get".to_string()),
            "set" => Token::Identifier("set".to_string()),
            "comptime" => Token::Identifier("comptime".to_string()),
            "type" => Token::Identifier("type".to_string()),
            "operator" => Token::Identifier("operator".to_string()),

            // Default: regular identifier
            _ => Token::Identifier(text.to_string()),
        }
    }

    // ── Operators ─────────────────────────────────────────────────

    #[rustfmt::skip]
    fn scan_operator(&mut self, ch: char, sl: usize, sc: usize) -> Result<(), String> {
        match ch {
            '+' => {
                if self.match_char('=') { self.emit_with(Token::PlusEq, sl, sc); }
                else if self.match_char('+') { self.emit_with(Token::PlusPlus, sl, sc); }
                else { self.emit_with(Token::Plus, sl, sc); }
            }
            '-' => {
                if self.match_char('>') { self.emit_with(Token::Arrow, sl, sc); }
                else if self.match_char('=') { self.emit_with(Token::MinusEq, sl, sc); }
                else { self.emit_with(Token::Minus, sl, sc); }
            }
            '*' => {
                if self.match_char('*') {
                    if self.match_char('=') { self.emit_with(Token::PowerEq, sl, sc); }
                    else { self.emit_with(Token::Power, sl, sc); }
                } else if self.match_char('=') { self.emit_with(Token::StarEq, sl, sc); }
                else { self.emit_with(Token::Star, sl, sc); }
            }
            '/' => {
                // Already handled in scan_slash — shouldn't reach here
                if self.match_char('=') { self.emit_with(Token::SlashEq, sl, sc); }
                else { self.emit_with(Token::Slash, sl, sc); }
            }
            '%' => {
                if self.match_char('=') { self.emit_with(Token::PercentEq, sl, sc); }
                else { self.emit_with(Token::Percent, sl, sc); }
            }
            '=' => {
                if self.match_char('>') { self.emit_with(Token::FatArrow, sl, sc); }
                else if self.match_char('=') { self.emit_with(Token::Eq, sl, sc); }
                else { self.emit_with(Token::Assign, sl, sc); }
            }
            '!' => {
                if self.match_char('=') { self.emit_with(Token::Neq, sl, sc); }
                else { self.emit_with(Token::Not, sl, sc); }
            }
            '<' => {
                if self.match_char('<') {
                    if self.match_char('=') { self.emit_with(Token::LShiftEq, sl, sc); }
                    else { self.emit_with(Token::LeftShift, sl, sc); }
                } else if self.match_char('=') { self.emit_with(Token::Lte, sl, sc); }
                else { self.emit_with(Token::Lt, sl, sc); }
            }
            '>' => {
                if self.match_char('>') {
                    if self.match_char('=') { self.emit_with(Token::RShiftEq, sl, sc); }
                    else { self.emit_with(Token::RightShift, sl, sc); }
                } else if self.match_char('=') { self.emit_with(Token::Gte, sl, sc); }
                else { self.emit_with(Token::Gt, sl, sc); }
            }
            '&' => {
                if self.match_char('&') { self.emit_with(Token::And, sl, sc); }
                else if self.match_char('=') { self.emit_with(Token::AmpEq, sl, sc); }
                else { self.emit_with(Token::BitwiseAnd, sl, sc); }
            }
            '|' => {
                if self.match_char('|') { self.emit_with(Token::Or, sl, sc); }
                else if self.match_char('>') { self.emit_with(Token::PipeGt, sl, sc); }
                else if self.match_char('=') { self.emit_with(Token::PipeEq, sl, sc); }
                else { self.emit_with(Token::BitwiseOr, sl, sc); }
            }
            '^' => {
                if self.match_char('=') { self.emit_with(Token::CaretEq, sl, sc); }
                else { self.emit_with(Token::BitwiseXor, sl, sc); }
            }
            '~' => {
                self.emit_with(Token::BitwiseNot, sl, sc);
            }
            '.' => {
                if self.current() == Some('.') && self.peek() == Some('.') {
                    self.advance(); self.advance();
                    self.emit_with(Token::Ellipsis, sl, sc);
                } else if self.match_char('.') {
                    if self.match_char('=') { self.emit_with(Token::DotDotEq, sl, sc); }
                    else { self.emit_with(Token::DotDot, sl, sc); }
                } else {
                    self.emit_with(Token::Dot, sl, sc);
                }
            }
            ':' => {
                if self.match_char(':') { self.emit_with(Token::DoubleColon, sl, sc); }
                else { self.emit_with(Token::Colon, sl, sc); }
            }
            '?' => {
                if self.match_char('?') {
                    if self.match_char('=') { self.emit_with(Token::NullishEq, sl, sc); }
                    else { self.emit_with(Token::Nullish, sl, sc); }
                } else if self.match_char('.') { self.emit_with(Token::QuestionDot, sl, sc); }
                else { self.emit_with(Token::Question, sl, sc); }
            }
            '@' => self.emit_with(Token::At, sl, sc),
            '(' => self.emit_with(Token::LeftParen, sl, sc),
            ')' => self.emit_with(Token::RightParen, sl, sc),
            '{' => self.emit_with(Token::LeftBrace, sl, sc),
            '}' => self.emit_with(Token::RightBrace, sl, sc),
            '[' => self.emit_with(Token::LeftBracket, sl, sc),
            ']' => self.emit_with(Token::RightBracket, sl, sc),
            ',' => self.emit_with(Token::Comma, sl, sc),
            ';' => self.emit_with(Token::Semicolon, sl, sc),
            '$' => {
                // $ not followed by a quote — skip (not used otherwise)
            }
            _ => return Err(format!("Unexpected character: {:?}", ch)),
        }
        Ok(())
    }
}
