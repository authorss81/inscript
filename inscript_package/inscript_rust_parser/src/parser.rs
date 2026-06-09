// inscript_rust_parser/src/parser.rs
// Recursive descent parser with operator precedence climbing

use crate::ast::*;
use crate::token::*;
use crate::error::ParseError;

pub struct Parser {
    tokens: Vec<TokenInfo>,
    current: usize,
}

impl Parser {
    pub fn new(tokens: Vec<TokenInfo>) -> Self {
        Parser { tokens, current: 0 }
    }

    pub fn parse(&mut self) -> Result<Program, ParseError> {
        let mut statements = Vec::new();
        while !self.is_at_end() {
            statements.push(self.parse_statement()?);
        }
        Ok(Program { statements })
    }

    fn parse_statement(&mut self) -> Result<Stmt, ParseError> {
        match &self.peek().token {
            Token::Let | Token::Const => self.parse_var_decl(),
            Token::Fn => self.parse_function_def(),
            Token::Class | Token::Struct => self.parse_class_def(),
            Token::Enum => self.parse_enum_def(),
            Token::If => self.parse_if(),
            Token::While => self.parse_while(),
            Token::For => self.parse_for(),
            Token::Switch => self.parse_switch(),
            Token::Return => self.parse_return(),
            Token::Break => {
                let line = self.peek().line;
                self.advance();
                self.consume_semicolon();
                Ok(Stmt::Break(line))
            }
            Token::Continue => {
                let line = self.peek().line;
                self.advance();
                self.consume_semicolon();
                Ok(Stmt::Continue(line))
            }
            Token::Throw => self.parse_throw(),
            Token::Yield => self.parse_yield_stmt(),
            Token::Try => self.parse_try(),
            _ => {
                let line = self.peek().line;
                let expr = self.parse_expression()?;
                self.consume_semicolon();
                Ok(Stmt::Expression(expr, line))
            }
        }
    }

    fn parse_var_decl(&mut self) -> Result<Stmt, ParseError> {
        let line = self.peek().line;
        let mutable = matches!(self.peek().token, Token::Let);
        self.advance(); // Let or Const

        // Handle destructuring: let [a, b] = expr
        if matches!(self.peek().token, Token::LeftBracket) {
            self.advance();
            while !matches!(self.peek().token, Token::RightBracket | Token::Eof) {
                self.consume_identifier()?;
                if matches!(self.peek().token, Token::Comma) {
                    self.advance();
                } else {
                    break;
                }
            }
            self.consume(&Token::RightBracket)?;
            if matches!(self.peek().token, Token::Assign) {
                self.advance();
                self.parse_expression()?;
            }
            self.consume_semicolon();
            return Ok(Stmt::VarDecl {
                name: String::new(),
                init: None,
                type_hint: None,
                mutable,
                line,
            });
        }

        let name = self.consume_identifier()?;
        let type_hint = if matches!(self.peek().token, Token::Colon) {
            self.advance();
            Some(self.parse_type_hint()?)
        } else {
            None
        };

        let init = if matches!(self.peek().token, Token::Assign) {
            self.advance();
            Some(self.parse_expression()?)
        } else {
            None
        };

        self.consume_semicolon();
        Ok(Stmt::VarDecl {
            name,
            init,
            type_hint,
            mutable,
            line,
        })
    }

    fn parse_function_def(&mut self) -> Result<Stmt, ParseError> {
        let line = self.peek().line;
        self.advance(); // fn
        if matches!(self.peek().token, Token::Star) {
            self.advance(); // *
        }
        let name = self.consume_identifier()?;
        self.consume(&Token::LeftParen)?;
        let params = self.parse_parameters()?;
        self.consume(&Token::RightParen)?;

        let return_type = if matches!(self.peek().token, Token::Arrow) {
            self.advance();
            Some(self.parse_type_hint()?)
        } else {
            None
        };

        self.consume(&Token::LeftBrace)?;
        let body = self.parse_block()?;
        self.consume(&Token::RightBrace)?;

        Ok(Stmt::FunctionDef {
            name,
            params,
            body,
            return_type,
            is_async: false,
            line,
        })
    }

    fn parse_class_def(&mut self) -> Result<Stmt, ParseError> {
        let line = self.peek().line;
        self.advance(); // class or struct
        let name = self.consume_identifier()?;

        // Skip optional generic type parameters: Name<T1, T2, ...>
        if matches!(self.peek().token, Token::Lt) {
            self.advance(); // <
            let mut depth = 1;
            while depth > 0 && !matches!(self.peek().token, Token::Eof) {
                match &self.peek().token {
                    Token::Lt => depth += 1,
                    Token::Gt => depth -= 1,
                    _ => {}
                }
                self.advance();
            }
        }

        let extends = if self.consume_keyword("extends") {
            Some(self.consume_identifier()?)
        } else {
            None
        };

        self.consume(&Token::LeftBrace)?;
        let mut body = Vec::new();

        while !matches!(self.peek().token, Token::RightBrace | Token::Eof) {
            if matches!(self.peek().token, Token::Fn) {
                body.push(self.parse_function_def()?);
            } else if matches!(self.peek().token, Token::Let | Token::Const) {
                body.push(self.parse_var_decl()?);
            } else {
                let ident = self.consume_identifier()?;
                // Event hook or getter/setter: ident (params?) { body }
                let has_params = matches!(self.peek().token, Token::LeftParen);
                let has_block = matches!(self.peek().token, Token::LeftBrace);
                if has_params || has_block {
                    if has_params {
                        self.advance();
                        while !matches!(self.peek().token, Token::RightParen | Token::Eof) {
                            self.advance();
                        }
                        self.consume(&Token::RightParen).ok();
                    }
                    if matches!(self.peek().token, Token::Arrow) {
                        self.advance();
                        self.parse_type_hint().ok();
                    }
                    if matches!(self.peek().token, Token::LeftBrace) {
                        self.advance();
                        let mut depth = 1;
                        while depth > 0 && !matches!(self.peek().token, Token::Eof) {
                            match &self.peek().token {
                                Token::LeftBrace => depth += 1,
                                Token::RightBrace => depth -= 1,
                                _ => {}
                            }
                            self.advance();
                        }
                    }
                } else {
                    let field_line = self.peek().line;
                    // Field declaration: name : Type = expr?
                    let type_hint = if matches!(self.peek().token, Token::Colon) {
                        self.advance();
                        Some(self.parse_type_hint()?)
                    } else {
                        None
                    };
                    if matches!(self.peek().token, Token::Assign) {
                        self.advance();
                        self.parse_expression()?;
                    }
                    body.push(Stmt::VarDecl {
                        name: ident,
                        init: None,
                        type_hint,
                        mutable: true,
                        line: field_line,
                    });
                }
            }
        }

        self.consume(&Token::RightBrace)?;

        Ok(Stmt::ClassDef {
            name,
            extends,
            body,
            line,
        })
    }

    fn parse_enum_def(&mut self) -> Result<Stmt, ParseError> {
        let line = self.peek().line;
        self.advance(); // enum
        let name = self.consume_identifier()?;
        self.consume(&Token::LeftBrace)?;
        let mut body = Vec::new();
        while !matches!(self.peek().token, Token::RightBrace | Token::Eof) {
            let variant_line = self.peek().line;
            let variant_name = self.consume_identifier()?;
            // Variant may have optional fields: Variant(f1: T1, f2: T2)
            if matches!(self.peek().token, Token::LeftParen) {
                self.advance();
                while !matches!(self.peek().token, Token::RightParen | Token::Eof) {
                    self.consume_identifier()?; // field name
                    if matches!(self.peek().token, Token::Colon) {
                        self.advance();
                        self.parse_type_hint()?;
                    }
                    if matches!(self.peek().token, Token::Comma) {
                        self.advance();
                    } else {
                        break;
                    }
                }
                self.consume(&Token::RightParen)?;
            }
            body.push(Stmt::VarDecl {
                name: variant_name,
                init: None,
                type_hint: None,
                mutable: false,
                line: variant_line,
            });
        }
        self.consume(&Token::RightBrace)?;
        Ok(Stmt::ClassDef {
            name,
            extends: None,
            body,
            line,
        })
    }

    fn parse_if(&mut self) -> Result<Stmt, ParseError> {
        let line = self.peek().line;
        self.advance(); // if
        let condition = self.parse_expression()?;

        self.consume(&Token::LeftBrace)?;
        let then_body = self.parse_block()?;
        self.consume(&Token::RightBrace)?;

        let else_body = if matches!(self.peek().token, Token::Else) {
            self.advance();
            if matches!(self.peek().token, Token::If) {
                // else if — chain as nested if
                let nested = self.parse_if()?;
                Some(vec![nested])
            } else {
                self.consume(&Token::LeftBrace)?;
                let body = self.parse_block()?;
                self.consume(&Token::RightBrace)?;
                Some(body)
            }
        } else {
            None
        };

        Ok(Stmt::If {
            condition,
            then_body,
            else_body,
            line,
        })
    }

    fn parse_while(&mut self) -> Result<Stmt, ParseError> {
        let line = self.peek().line;
        self.advance(); // while
        let condition = self.parse_expression()?;

        self.consume(&Token::LeftBrace)?;
        let body = self.parse_block()?;
        self.consume(&Token::RightBrace)?;

        Ok(Stmt::While { condition, body, line })
    }

    fn parse_for(&mut self) -> Result<Stmt, ParseError> {
        let line = self.peek().line;
        self.advance(); // for
        let target = self.consume_identifier()?;
        self.consume(&Token::In)?;
        let iter = self.parse_expression()?;

        self.consume(&Token::LeftBrace)?;
        let body = self.parse_block()?;
        self.consume(&Token::RightBrace)?;

        Ok(Stmt::For { target, iter, body, line })
    }

    fn parse_switch(&mut self) -> Result<Stmt, ParseError> {
        let line = self.peek().line;
        self.advance(); // switch/match
        let expr = self.parse_expression()?;
        self.consume(&Token::LeftBrace)?;

        let mut cases = Vec::new();
        while !matches!(self.peek().token, Token::RightBrace | Token::Eof) {
            if matches!(self.peek().token, Token::Case) {
                self.advance();
                let value = self.parse_expression()?;
                // Skip optional guard: pattern if condition { body }
                while !matches!(self.peek().token, Token::LeftBrace | Token::Colon | Token::RightBrace | Token::Eof) {
                    self.advance();
                }
                if matches!(self.peek().token, Token::Colon) {
                    self.advance();
                    let body = self.parse_case_body()?;
                    cases.push((Some(value), body));
                } else if matches!(self.peek().token, Token::LeftBrace) {
                    self.advance();
                    let body = self.parse_block()?;
                    self.consume(&Token::RightBrace)?;
                    cases.push((Some(value), body));
                } else {
                    let body = Vec::new();
                    cases.push((Some(value), body));
                }
            } else if matches!(self.peek().token, Token::Default) {
                self.advance();
                self.consume(&Token::Colon)?;
                let body = self.parse_case_body()?;
                cases.push((None, body));
            } else {
                break;
            }
        }

        self.consume(&Token::RightBrace)?;
        Ok(Stmt::Switch { expr, cases, line })
    }

    fn parse_return(&mut self) -> Result<Stmt, ParseError> {
        let line = self.peek().line;
        self.advance(); // return
        let value = if !matches!(self.peek().token, Token::Semicolon | Token::RightBrace) {
            Some(self.parse_expression()?)
        } else {
            None
        };
        self.consume_semicolon();
        Ok(Stmt::Return(value, line))
    }

    fn parse_throw(&mut self) -> Result<Stmt, ParseError> {
        let line = self.peek().line;
        self.advance(); // throw
        let expr = self.parse_expression()?;
        self.consume_semicolon();
        Ok(Stmt::Throw(expr, line))
    }

    fn parse_yield_stmt(&mut self) -> Result<Stmt, ParseError> {
        let line = self.peek().line;
        self.advance(); // yield
        let value = if !matches!(self.peek().token, Token::Semicolon | Token::RightBrace) {
            Some(self.parse_expression()?)
        } else {
            None
        };
        self.consume_semicolon();
        Ok(Stmt::Expression(Expr::Yield(value.map(Box::new)), line))
    }

    fn parse_try(&mut self) -> Result<Stmt, ParseError> {
        let line = self.peek().line;
        self.advance(); // try
        self.consume(&Token::LeftBrace)?;
        let body = self.parse_block()?;
        self.consume(&Token::RightBrace)?;

        let mut catch_clauses = Vec::new();
        while matches!(self.peek().token, Token::Catch) {
            self.advance();
            let error_var = if matches!(self.peek().token, Token::LeftParen) {
                self.advance();
                let name = self.consume_identifier()?;
                self.consume(&Token::RightParen)?;
                name
            } else {
                self.consume_identifier()?
            };
            self.consume(&Token::LeftBrace)?;
            let catch_body = self.parse_block()?;
            self.consume(&Token::RightBrace)?;
            catch_clauses.push((error_var, catch_body));
        }

        let finally_body = if matches!(self.peek().token, Token::Finally) {
            self.advance();
            self.consume(&Token::LeftBrace)?;
            let body = self.parse_block()?;
            self.consume(&Token::RightBrace)?;
            Some(body)
        } else {
            None
        };

        Ok(Stmt::Try {
            body,
            catch_clauses,
            finally_body,
            line,
        })
    }

    fn parse_block(&mut self) -> Result<Vec<Stmt>, ParseError> {
        let mut statements = Vec::new();
        while !matches!(self.peek().token, Token::RightBrace | Token::Eof) {
            statements.push(self.parse_statement()?);
        }
        Ok(statements)
    }

    fn parse_case_body(&mut self) -> Result<Vec<Stmt>, ParseError> {
        let mut body = Vec::new();
        while !matches!(
            self.peek().token,
            Token::Case | Token::Default | Token::RightBrace | Token::Eof
        ) {
            body.push(self.parse_statement()?);
        }
        Ok(body)
    }

    fn parse_expression(&mut self) -> Result<Expr, ParseError> {
        self.parse_ternary()
    }

    fn parse_ternary(&mut self) -> Result<Expr, ParseError> {
        let mut expr = self.parse_binary(1)?;

        if matches!(self.peek().token, Token::Question) {
            // Distinguish ternary (expr ? then : else) from propagate (expr?)
            // If ? is followed by a statement-ending token, it's propagate.
            let is_ternary = matches!(
                self.tokens.get(self.current + 1).map(|t| &t.token),
                Some(Token::Identifier(_))
                    | Some(Token::Int(_))
                    | Some(Token::Float(_))
                    | Some(Token::String(_))
                    |                 Some(Token::Bool(true))
                    | Some(Token::Bool(false))
                    | Some(Token::Nil)
                    | Some(Token::LeftParen)
                    | Some(Token::LeftBracket)
                    | Some(Token::Not)
                    | Some(Token::Minus)
                    | Some(Token::Plus)

            );
            if is_ternary {
                self.advance();
                let then_expr = self.parse_expression()?;
                self.consume(&Token::Colon)?;
                let else_expr = self.parse_expression()?;
                expr = Expr::Ternary {
                    condition: Box::new(expr),
                    then_expr: Box::new(then_expr),
                    else_expr: Box::new(else_expr),
                };
            } else {
                // Error propagation operator: consume ?
                self.advance();
                expr = Expr::Propagate(Box::new(expr));
            }
        }

        Ok(expr)
    }

    fn parse_binary(&mut self, min_prec: u8) -> Result<Expr, ParseError> {
        let mut left = self.parse_unary()?;

        while precedence(&self.peek().token) >= min_prec {
            let op = self.parse_binary_op()?;
            let right = self.parse_binary(precedence(&binop_to_token(&op)) + 1)?;
            left = Expr::Binary {
                left: Box::new(left),
                op,
                right: Box::new(right),
            };
        }

        Ok(left)
    }

    fn parse_unary(&mut self) -> Result<Expr, ParseError> {
        match &self.peek().token {
            Token::Minus => {
                self.advance();
                let operand = self.parse_unary()?;
                Ok(Expr::Unary {
                    op: UnaryOp::Neg,
                    operand: Box::new(operand),
                })
            }
            Token::Not => {
                self.advance();
                let operand = self.parse_unary()?;
                Ok(Expr::Unary {
                    op: UnaryOp::Not,
                    operand: Box::new(operand),
                })
            }
            _ => self.parse_postfix(),
        }
    }

    fn parse_postfix(&mut self) -> Result<Expr, ParseError> {
        let mut expr = self.parse_primary()?;

        loop {
            match &self.peek().token {
                Token::LeftParen => {
                    self.advance();
                    let args = self.parse_arguments()?;
                    self.consume(&Token::RightParen)?;
                    expr = Expr::Call {
                        callee: Box::new(expr),
                        args,
                    };
                }
                Token::LeftBracket => {
                    self.advance();
                    let index = self.parse_expression()?;
                    self.consume(&Token::RightBracket)?;
                    expr = Expr::Index {
                        object: Box::new(expr),
                        index: Box::new(index),
                    };
                }
                Token::Dot => {
                    self.advance();
                    let property = self.consume_identifier()?;
                    expr = Expr::Member {
                        object: Box::new(expr),
                        property,
                    };
                }
                Token::LeftBrace => {
                    // comptime { ... } — skip the block
                    if let Expr::Identifier(name) = &expr {
                        if name == "comptime" {
                            self.advance();
                            let mut depth = 1;
                            while depth > 0 && !matches!(self.peek().token, Token::Eof) {
                                match &self.peek().token {
                                    Token::LeftBrace => depth += 1,
                                    Token::RightBrace => depth -= 1,
                                    _ => {}
                                }
                                self.advance();
                            }
                            continue;
                        }
                    }
                    break;
                }
                _ => break,
            }
        }

        Ok(expr)
    }

    fn parse_primary(&mut self) -> Result<Expr, ParseError> {
        match &self.peek().token {
            Token::Int(n) => {
                let n = *n;
                self.advance();
                Ok(Expr::Literal(Literal::Int(n)))
            }
            Token::Float(f) => {
                let f = *f;
                self.advance();
                Ok(Expr::Literal(Literal::Float(f)))
            }
            Token::String(s) => {
                let s = s.clone();
                self.advance();
                Ok(Expr::Literal(Literal::String(s)))
            }
            Token::FString(s) => {
                let parts = self.parse_fstring_content(s)?;
                self.advance();
                if parts.len() == 1 && matches!(&parts[0], InterpolationPart::String(_)) {
                    // No interpolation — treat as plain string
                    if let InterpolationPart::String(text) = parts.into_iter().next().unwrap() {
                        Ok(Expr::Literal(Literal::String(text)))
                    } else {
                        unreachable!()
                    }
                } else {
                    Ok(Expr::StringInterpolation(parts))
                }
            }
            Token::Bool(val) => {
                let v = *val;
                self.advance();
                Ok(Expr::Literal(Literal::Bool(v)))
            }
            Token::Nil => {
                self.advance();
                Ok(Expr::Literal(Literal::Nil))
            }
            Token::Identifier(name) => {
                let name = name.clone();
                self.advance();
                Ok(Expr::Identifier(name))
            }
            Token::LeftParen => {
                self.advance();
                let expr = self.parse_expression()?;
                self.consume(&Token::RightParen)?;
                Ok(expr)
            }
            Token::LeftBracket => {
                self.advance();
                let mut elements = Vec::new();
                while !matches!(self.peek().token, Token::RightBracket | Token::Eof) {
                    elements.push(self.parse_expression()?);
                    if matches!(self.peek().token, Token::Comma) {
                        self.advance();
                    } else {
                        break;
                    }
                }
                self.consume(&Token::RightBracket)?;
                Ok(Expr::Array(elements))
            }
            Token::LeftBrace => {
                self.advance();
                let mut pairs = Vec::new();
                while !matches!(self.peek().token, Token::RightBrace | Token::Eof) {
                    let key = self.consume_identifier()?;
                    self.consume(&Token::Colon)?;
                    let value = self.parse_expression()?;
                    pairs.push((key, value));
                    if matches!(self.peek().token, Token::Comma) {
                        self.advance();
                    } else {
                        break;
                    }
                }
                self.consume(&Token::RightBrace)?;
                Ok(Expr::Object(pairs))
            }
            Token::Fn => {
                // Lambda expression: fn(params) body_expr  or  fn(params) { stmts }
                self.advance(); // consume fn
                self.consume(&Token::LeftParen)?;
                let mut params = Vec::new();
                while !matches!(self.peek().token, Token::RightParen | Token::Eof) {
                    let name = self.consume_identifier()?;
                    let type_hint = if matches!(self.peek().token, Token::Colon) {
                        self.advance();
                        Some(self.parse_type_hint()?)
                    } else {
                        None
                    };
                    let default = if matches!(self.peek().token, Token::Assign) {
                        self.advance();
                        Some(Box::new(self.parse_expression()?))
                    } else {
                        None
                    };
                    params.push(Param { name, type_hint, default });
                    if matches!(self.peek().token, Token::Comma) {
                        self.advance();
                    } else {
                        break;
                    }
                }
                self.consume(&Token::RightParen)?;
                // Body: either a single expression or a { ... } block
                let body = if matches!(self.peek().token, Token::LeftBrace) {
                    // Block body — parse as a brace-enclosed expression
                    self.advance(); // consume {
                    let expr = self.parse_expression()?;
                    self.consume(&Token::RightBrace)?;
                    expr
                } else {
                    self.parse_expression()?
                };
                Ok(Expr::Lambda {
                    params,
                    body: Box::new(body),
                    return_type: None,
                })
            }
            _ => Err(ParseError::new(
                format!("Unexpected token: {:?}", self.peek().token),
                self.peek().line,
                self.peek().column,
            )),
        }
    }

    fn parse_binary_op(&mut self) -> Result<BinOp, ParseError> {
        let op = match &self.peek().token {
            Token::Plus => BinOp::Add,
            Token::Minus => BinOp::Sub,
            Token::Star => BinOp::Mul,
            Token::Slash => BinOp::Div,
            Token::Percent => BinOp::Mod,
            Token::Power => BinOp::Power,
            Token::Eq => BinOp::Eq,
            Token::Neq => BinOp::Neq,
            Token::Lt => BinOp::Lt,
            Token::Lte => BinOp::Lte,
            Token::Gt => BinOp::Gt,
            Token::Gte => BinOp::Gte,
            Token::And => BinOp::And,
            Token::Or => BinOp::Or,
            Token::BitwiseAnd => BinOp::BitwiseAnd,
            Token::BitwiseOr => BinOp::BitwiseOr,
            Token::BitwiseXor => BinOp::BitwiseXor,
            Token::LeftShift => BinOp::LeftShift,
            Token::RightShift => BinOp::RightShift,
            Token::Assign => BinOp::Assign,
            _ => {
                return Err(ParseError::new(
                    "Expected binary operator",
                    self.peek().line,
                    self.peek().column,
                ))
            }
        };
        self.advance();
        Ok(op)
    }

    fn parse_parameters(&mut self) -> Result<Vec<Param>, ParseError> {
        let mut params = Vec::new();
        while !matches!(self.peek().token, Token::RightParen | Token::Eof) {
            let name = self.consume_identifier()?;
            let type_hint = if matches!(self.peek().token, Token::Colon) {
                self.advance();
                Some(self.parse_type_hint()?)
            } else {
                None
            };
            let default = if matches!(self.peek().token, Token::Assign) {
                self.advance();
                Some(Box::new(self.parse_expression()?))
            } else {
                None
            };
            params.push(Param {
                name,
                type_hint,
                default,
            });
            if matches!(self.peek().token, Token::Comma) {
                self.advance();
            } else {
                break;
            }
        }
        Ok(params)
    }

    fn parse_arguments(&mut self) -> Result<Vec<Expr>, ParseError> {
        let mut args = Vec::new();
        while !matches!(self.peek().token, Token::RightParen | Token::Eof) {
            args.push(self.parse_expression()?);
            if matches!(self.peek().token, Token::Comma) {
                self.advance();
            } else {
                break;
            }
        }
        Ok(args)
    }

    fn parse_type_hint(&mut self) -> Result<TypeHint, ParseError> {
        // Handle array types: [T] or [[T]] (recursive)
        if matches!(self.peek().token, Token::LeftBracket) {
            self.advance();
            let inner = self.parse_type_hint()?;
            self.consume(&Token::RightBracket)?;
            return Ok(TypeHint {
                name: format!("{}[]", inner.name),
                generics: Vec::new(),
                nullable: false,
            });
        }
        let mut name = self.consume_identifier()?;
        // Handle postfix array types: T[]
        if matches!(self.peek().token, Token::LeftBracket) {
            self.advance();
            if matches!(self.peek().token, Token::RightBracket) {
                self.advance();
                name = format!("{}[]", name);
            }
        }
        Ok(TypeHint {
            name,
            generics: Vec::new(),
            nullable: false,
        })
    }

    fn peek(&self) -> TokenInfo {
        self.tokens
            .get(self.current)
            .cloned()
            .unwrap_or_else(|| TokenInfo::new(Token::Eof, 0, 0))
    }

    fn advance(&mut self) {
        if !self.is_at_end() {
            self.current += 1;
        }
    }

    fn is_at_end(&self) -> bool {
        matches!(self.peek().token, Token::Eof)
    }

    fn consume(&mut self, expected: &Token) -> Result<(), ParseError> {
        if std::mem::discriminant(&self.peek().token) == std::mem::discriminant(expected) {
            self.advance();
            Ok(())
        } else {
            Err(ParseError::new(
                format!("Expected {:?}, found {:?}", expected, self.peek().token),
                self.peek().line,
                self.peek().column,
            ))
        }
    }

    fn consume_identifier(&mut self) -> Result<String, ParseError> {
        match &self.peek().token {
            Token::Identifier(name) => {
                let name = name.clone();
                self.advance();
                Ok(name)
            }
            _ => Err(ParseError::new(
                "Expected identifier",
                self.peek().line,
                self.peek().column,
            )),
        }
    }

    fn consume_keyword(&mut self, keyword: &str) -> bool {
        if let Token::Identifier(name) = &self.peek().token {
            if name == keyword {
                self.advance();
                return true;
            }
        }
        false
    }

    fn consume_semicolon(&mut self) {
        if matches!(self.peek().token, Token::Semicolon) {
            self.advance();
        }
    }

    /// Parse f-string content into interpolation parts.
    /// Handles the lexer's special encoding:
    ///   `\x00{` — literal `{` (escaped `{{`)
    ///   `}\x00` — literal `}` (escaped `}}`)
    ///   `{expr}` — interpolation expression
    fn parse_fstring_content(&mut self, content: &str) -> Result<Vec<InterpolationPart>, ParseError> {
        let mut parts: Vec<InterpolationPart> = Vec::new();
        let mut text = String::new();
        let mut chars = content.chars().peekable();
        let null_marker: char = '\x00';

        while let Some(ch) = chars.next() {
            if ch == null_marker {
                // \x00 marks an escaped brace
                // \x00{ → literal { (from {{ escape)
                if chars.peek() == Some(&'{') {
                    chars.next(); // consume {
                    text.push('{');
                }
                // Otherwise: orphaned null byte — ignore
            } else if ch == '}' && chars.peek() == Some(&null_marker) {
                // }\x00 → literal } (from }} escape)
                chars.next(); // consume \x00
                text.push('}');
            } else if ch == '{' {
                // Start of interpolation expression
                if !text.is_empty() {
                    parts.push(InterpolationPart::String(std::mem::take(&mut text)));
                }
                // Parse expression until matching }
                let mut expr_text = String::new();
                let mut depth = 1;
                while let Some(ec) = chars.next() {
                    if ec == '{' { depth += 1; }
                    else if ec == '}' {
                        depth -= 1;
                        if depth == 0 { break; }
                    }
                    if depth > 0 {
                        expr_text.push(ec);
                    }
                }
                if !expr_text.is_empty() {
                    let mut sub_lex = crate::lexer::Lexer::new(&expr_text);
                    let sub_tokens = sub_lex.tokenize().map_err(|e| {
                        ParseError::new(format!("In f-string: {}", e), 0, 0)
                    })?;
                    let mut sub_parser = Parser::new(sub_tokens);
                    let expr = sub_parser.parse_expression().map_err(|e| {
                        ParseError::new(format!("In f-string: {}", e), 0, 0)
                    })?;
                    parts.push(InterpolationPart::Expr(Box::new(expr)));
                }
            } else {
                text.push(ch);
            }
        }
        if !text.is_empty() {
            parts.push(InterpolationPart::String(text));
        }
        Ok(parts)
    }
}

fn binop_to_token(op: &BinOp) -> Token {
    match op {
        BinOp::Add => Token::Plus,
        BinOp::Sub => Token::Minus,
        BinOp::Mul => Token::Star,
        BinOp::Div => Token::Slash,
        BinOp::Mod => Token::Percent,
        BinOp::Power => Token::Power,
        BinOp::Eq => Token::Eq,
        BinOp::Neq => Token::Neq,
        BinOp::Lt => Token::Lt,
        BinOp::Lte => Token::Lte,
        BinOp::Gt => Token::Gt,
        BinOp::Gte => Token::Gte,
        BinOp::And => Token::And,
        BinOp::Or => Token::Or,
        BinOp::Assign => Token::Assign,
        BinOp::BitwiseAnd => Token::BitwiseAnd,
        BinOp::BitwiseOr => Token::BitwiseOr,
        BinOp::BitwiseXor => Token::BitwiseXor,
        BinOp::LeftShift => Token::LeftShift,
        BinOp::RightShift => Token::RightShift,
    }
}
