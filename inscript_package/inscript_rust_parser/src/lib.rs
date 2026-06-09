// inscript_rust_parser/src/lib.rs v3.8.2+
// Complete PyO3 module integration for full AST serialization

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

mod ast;
mod token;
mod parser;
mod lexer;
mod compiler;
mod error;

use parser::Parser;
use token::TokenInfo;
use ast::*;


/// PyO3 wrapper for the Parser
#[pyclass]
pub struct PyParser {
    tokens: Vec<TokenInfo>,
}

#[pymethods]
impl PyParser {
    #[new]
    fn new(py_tokens: Vec<PyObject>) -> PyResult<Self> {
        Python::with_gil(|py| {
            let tokens = convert_py_tokens(py, &py_tokens)?;
            Ok(PyParser { tokens })
        })
    }

    /// Parse tokens into an AST
    fn parse(&self) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let mut parser = Parser::new(self.tokens.clone());
            match parser.parse() {
                Ok(program) => program_to_python(py, &program),
                Err(e) => Err(PyErr::new::<pyo3::exceptions::PySyntaxError, _>(
                    e.to_string(),
                )),
            }
        })
    }

    /// Parse from a token list (static method)
    #[staticmethod]
    fn parse_tokens(py_tokens: Vec<PyObject>) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let tokens = convert_py_tokens(py, &py_tokens)?;
            let mut parser = Parser::new(tokens);
            match parser.parse() {
                Ok(program) => program_to_python(py, &program),
                Err(e) => Err(PyErr::new::<pyo3::exceptions::PySyntaxError, _>(
                    e.to_string(),
                )),
            }
        })
    }
}

// ─────────────────────────────────────────────────────────────────────
// Token conversion (Python → Rust)
// ─────────────────────────────────────────────────────────────────────

fn convert_py_tokens(py: Python, py_tokens: &[PyObject]) -> PyResult<Vec<TokenInfo>> {
    let mut tokens = Vec::new();
    for py_tok in py_tokens {
        let tok_dict = py_tok.downcast_bound::<PyDict>(py)?;
        
        let token_type_str: String = tok_dict.get_item("token_type")?
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing token_type"))?
            .extract()?;
        
        let value: String = tok_dict.get_item("value")?
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing value"))?
            .extract()?;
        
        let line: usize = tok_dict.get_item("line")
            .ok()
            .flatten()
            .and_then(|o| o.extract().ok())
            .unwrap_or(0);
        
        let column: usize = tok_dict.get_item("column")
            .ok()
            .flatten()
            .and_then(|o| o.extract().ok())
            .unwrap_or(0);
        
        let tok = string_to_token(&token_type_str, &value)?;
        tokens.push(TokenInfo::new(tok, line, column));
    }
    Ok(tokens)
}

fn string_to_token(type_str: &str, value: &str) -> PyResult<token::Token> {
    use token::Token::*;
    
    let tok = match type_str {
        "Let" => Let,
        "Const" => Const,
        "Fn" => Fn,
        "If" => If,
        "Else" => Else,
        "While" => While,
        "For" => For,
        "In" => In,
        "Switch" => Switch,
        "Case" => Case,
        "Class" => Class,
        "Struct" => Struct,
        "Enum" => Enum,
        "Return" => Return,
        "Break" => Break,
        "Continue" => Continue,
        "Throw" => Throw,
        "Try" => Try,
        "Catch" => Catch,
        "Finally" => Finally,
        "Async" => Async,
        "Await" => Await,
        "Yield" => Yield,
        "True" => Bool(true),
        "False" => Bool(false),
        "Nil" => Nil,
        "Int" => {
            value.parse::<i64>()
                .map(Int)
                .unwrap_or(Int(0))
        },
        "Float" => {
            value.parse::<f64>()
                .map(Float)
                .unwrap_or(Float(0.0))
        },
        "String" => String(value.to_string()),
        "Ident" => Identifier(value.to_string()),
        "Plus" => Plus,
        "Minus" => Minus,
        "Star" => Star,
        "Slash" => Slash,
        "Percent" => Percent,
        "Power" => Power,
        "Assign" => Assign,
        "Eq" => Eq,
        "Neq" => Neq,
        "Lt" => Lt,
        "Lte" => Lte,
        "Gt" => Gt,
        "Gte" => Gte,
        "BitwiseAnd" => BitwiseAnd,
        "BitwiseOr" => BitwiseOr,
        "BitwiseXor" => BitwiseXor,
        "BitwiseNot" => BitwiseNot,
        "LeftShift" => LeftShift,
        "RightShift" => RightShift,
        "And" => And,
        "Or" => Or,
        "Not" => Not,
        "Question" => Question,
        "LeftParen" | "LParen" => LeftParen,
        "RightParen" | "RParen" => RightParen,
        "LeftBrace" | "LBrace" => LeftBrace,
        "RightBrace" | "RBrace" => RightBrace,
        "LeftBracket" | "LBracket" => LeftBracket,
        "RightBracket" | "RBracket" => RightBracket,
        "Comma" => Comma,
        "Dot" => Dot,
        "Semicolon" => Semicolon,
        "Colon" => Colon,
        "Arrow" => Arrow,
        "Eof" => Eof,
        "Default" => Default,
        _ => Identifier(value.to_string()),
    };
    Ok(tok)
}

// ─────────────────────────────────────────────────────────────────────
// AST to Python conversion (Rust → Python)
// ─────────────────────────────────────────────────────────────────────

fn program_to_python(py: Python, program: &Program) -> PyResult<PyObject> {
    let dict = PyDict::new_bound(py);
    dict.set_item("type", "Program")?;
    
    let stmts = PyList::empty_bound(py);
    for stmt in &program.statements {
        let py_stmt = stmt_to_python(py, stmt)?;
        stmts.append(py_stmt)?;
    }
    dict.set_item("statements", stmts)?;
    
    Ok(dict.into())
}

fn stmt_to_python(py: Python, stmt: &Stmt) -> PyResult<PyObject> {
    match stmt {
        Stmt::Expression(expr, ..) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "ExprStatement")?;
            dict.set_item("expression", expr_to_python(py, expr)?)?;
            Ok(dict.into())
        }
        Stmt::VarDecl { name, init, type_hint, mutable, .. } => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "VarDecl")?;
            dict.set_item("name", name.clone())?;
            dict.set_item("mutable", mutable)?;
            if let Some(expr) = init {
                dict.set_item("init", expr_to_python(py, expr)?)?;
            }
            if let Some(th) = type_hint {
                dict.set_item("type_hint", typehint_to_python(py, th)?)?;
            }
            Ok(dict.into())
        }
        Stmt::FunctionDef { name, params, body, return_type, is_async, .. } => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "FunctionDef")?;
            dict.set_item("name", name.clone())?;
            dict.set_item("is_async", is_async)?;
            
            let py_params = PyList::empty_bound(py);
            for p in params {
                let param_dict = PyDict::new_bound(py);
                param_dict.set_item("name", p.name.clone())?;
                if let Some(th) = &p.type_hint {
                    param_dict.set_item("type_hint", typehint_to_python(py, th)?)?;
                }
                if let Some(def) = &p.default {
                    param_dict.set_item("default", expr_to_python(py, def)?)?;
                }
                py_params.append(param_dict)?;
            }
            dict.set_item("params", py_params)?;
            
            let py_body = PyList::empty_bound(py);
            for s in body {
                py_body.append(stmt_to_python(py, s)?)?;
            }
            dict.set_item("body", py_body)?;
            
            if let Some(rt) = return_type {
                dict.set_item("return_type", typehint_to_python(py, rt)?)?;
            }
            Ok(dict.into())
        }
        Stmt::ClassDef { name, extends, body, .. } => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "ClassDef")?;
            dict.set_item("name", name.clone())?;
            if let Some(ext) = extends {
                dict.set_item("extends", ext.clone())?;
            }
            let py_body = PyList::empty_bound(py);
            for s in body {
                py_body.append(stmt_to_python(py, s)?)?;
            }
            dict.set_item("body", py_body)?;
            Ok(dict.into())
        }
        Stmt::If { condition, then_body, else_body, .. } => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "If")?;
            dict.set_item("condition", expr_to_python(py, condition)?)?;
            let py_then = PyList::empty_bound(py);
            for s in then_body {
                py_then.append(stmt_to_python(py, s)?)?;
            }
            dict.set_item("then_body", py_then)?;
            if let Some(else_stmts) = else_body {
                let py_else = PyList::empty_bound(py);
                for s in else_stmts {
                    py_else.append(stmt_to_python(py, s)?)?;
                }
                dict.set_item("else_body", py_else)?;
            }
            Ok(dict.into())
        }
        Stmt::While { condition, body, .. } => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "While")?;
            dict.set_item("condition", expr_to_python(py, condition)?)?;
            let py_body = PyList::empty_bound(py);
            for s in body {
                py_body.append(stmt_to_python(py, s)?)?;
            }
            dict.set_item("body", py_body)?;
            Ok(dict.into())
        }
        Stmt::For { target, iter, body, .. } => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "For")?;
            dict.set_item("target", target.clone())?;
            dict.set_item("iter", expr_to_python(py, iter)?)?;
            let py_body = PyList::empty_bound(py);
            for s in body {
                py_body.append(stmt_to_python(py, s)?)?;
            }
            dict.set_item("body", py_body)?;
            Ok(dict.into())
        }
        Stmt::Switch { expr, cases, .. } => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Switch")?;
            dict.set_item("expr", expr_to_python(py, expr)?)?;
            let py_cases = PyList::empty_bound(py);
            for (case_expr, body) in cases {
                let case_dict = PyDict::new_bound(py);
                if let Some(ce) = case_expr {
                    case_dict.set_item("expr", expr_to_python(py, ce)?)?;
                } else {
                    case_dict.set_item("expr", py.None())?;
                }
                let py_body = PyList::empty_bound(py);
                for s in body {
                    py_body.append(stmt_to_python(py, s)?)?;
                }
                case_dict.set_item("body", py_body)?;
                py_cases.append(case_dict)?;
            }
            dict.set_item("cases", py_cases)?;
            Ok(dict.into())
        }
        Stmt::Throw(expr, ..) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Throw")?;
            dict.set_item("expr", expr_to_python(py, expr)?)?;
            Ok(dict.into())
        }
        Stmt::Try { body, catch_clauses, finally_body, .. } => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Try")?;
            let py_body = PyList::empty_bound(py);
            for s in body {
                py_body.append(stmt_to_python(py, s)?)?;
            }
            dict.set_item("body", py_body)?;
            let py_catches = PyList::empty_bound(py);
            for (exc_name, handlers) in catch_clauses {
                let catch_dict = PyDict::new_bound(py);
                catch_dict.set_item("exception", exc_name.clone())?;
                let py_handlers = PyList::empty_bound(py);
                for h in handlers {
                    py_handlers.append(stmt_to_python(py, h)?)?;
                }
                catch_dict.set_item("body", py_handlers)?;
                py_catches.append(catch_dict)?;
            }
            dict.set_item("catch_clauses", py_catches)?;
            if let Some(fin) = finally_body {
                let py_finally = PyList::empty_bound(py);
                for s in fin {
                    py_finally.append(stmt_to_python(py, s)?)?;
                }
                dict.set_item("finally_body", py_finally)?;
            }
            Ok(dict.into())
        }
        Stmt::Return(expr_opt, ..) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Return")?;
            if let Some(expr) = expr_opt {
                dict.set_item("value", expr_to_python(py, expr)?)?;
            }
            Ok(dict.into())
        }
        Stmt::Break(..) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Break")?;
            Ok(dict.into())
        }
        Stmt::Continue(..) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Continue")?;
            Ok(dict.into())
        }
    }
}

fn expr_to_python(py: Python, expr: &Expr) -> PyResult<PyObject> {
    match expr {
        Expr::Literal(lit) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Literal")?;
            match lit {
                Literal::Nil => dict.set_item("value", py.None())?,
                Literal::Bool(b) => dict.set_item("value", b)?,
                Literal::Int(i) => dict.set_item("value", i)?,
                Literal::Float(f) => dict.set_item("value", f)?,
                Literal::String(s) => dict.set_item("value", s.clone())?,
            }
            Ok(dict.into())
        }
        Expr::Identifier(name) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Identifier")?;
            dict.set_item("name", name.clone())?;
            Ok(dict.into())
        }
        Expr::Binary { left, op, right } => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "BinaryOp")?;
            dict.set_item("left", expr_to_python(py, left)?)?;
            dict.set_item("op", format!("{:?}", op))?;
            dict.set_item("right", expr_to_python(py, right)?)?;
            Ok(dict.into())
        }
        Expr::Unary { op, operand } => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "UnaryOp")?;
            dict.set_item("op", format!("{:?}", op))?;
            dict.set_item("operand", expr_to_python(py, operand)?)?;
            Ok(dict.into())
        }
        Expr::Call { callee, args } => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Call")?;
            dict.set_item("callee", expr_to_python(py, callee)?)?;
            let py_args = PyList::empty_bound(py);
            for arg in args {
                py_args.append(expr_to_python(py, arg)?)?;
            }
            dict.set_item("args", py_args)?;
            Ok(dict.into())
        }
        Expr::Index { object, index } => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Index")?;
            dict.set_item("object", expr_to_python(py, object)?)?;
            dict.set_item("index", expr_to_python(py, index)?)?;
            Ok(dict.into())
        }
        Expr::Member { object, property } => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Member")?;
            dict.set_item("object", expr_to_python(py, object)?)?;
            dict.set_item("property", property.clone())?;
            Ok(dict.into())
        }
        Expr::Array(exprs) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Array")?;
            let py_elems = PyList::empty_bound(py);
            for e in exprs {
                py_elems.append(expr_to_python(py, e)?)?;
            }
            dict.set_item("elements", py_elems)?;
            Ok(dict.into())
        }
        Expr::Ternary { condition, then_expr, else_expr } => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Ternary")?;
            dict.set_item("condition", expr_to_python(py, condition)?)?;
            dict.set_item("then_expr", expr_to_python(py, then_expr)?)?;
            dict.set_item("else_expr", expr_to_python(py, else_expr)?)?;
            Ok(dict.into())
        }
        Expr::Object(pairs) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Object")?;
            let obj_dict = PyDict::new_bound(py);
            for (k, v) in pairs {
                obj_dict.set_item(k.clone(), expr_to_python(py, v)?)?;
            }
            dict.set_item("properties", obj_dict)?;
            Ok(dict.into())
        }
        Expr::Lambda { params, body, return_type } => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Lambda")?;
            let py_params = PyList::empty_bound(py);
            for p in params {
                let param_dict = PyDict::new_bound(py);
                param_dict.set_item("name", p.name.clone())?;
                if let Some(th) = &p.type_hint {
                    param_dict.set_item("type_hint", typehint_to_python(py, th)?)?;
                }
                if let Some(def) = &p.default {
                    param_dict.set_item("default", expr_to_python(py, def)?)?;
                }
                py_params.append(param_dict)?;
            }
            dict.set_item("params", py_params)?;
            dict.set_item("body", expr_to_python(py, body)?)?;
            if let Some(rt) = return_type {
                dict.set_item("return_type", typehint_to_python(py, rt)?)?;
            }
            Ok(dict.into())
        }
        Expr::StringInterpolation(parts) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "StringInterpolation")?;
            let py_parts = PyList::empty_bound(py);
            for part in parts {
                match part {
                    InterpolationPart::String(s) => {
                        let pdict = PyDict::new_bound(py);
                        pdict.set_item("type", "StringPart")?;
                        pdict.set_item("value", s.clone())?;
                        py_parts.append(pdict)?;
                    }
                    InterpolationPart::Expr(e) => {
                        let pdict = PyDict::new_bound(py);
                        pdict.set_item("type", "ExprPart")?;
                        pdict.set_item("expr", expr_to_python(py, e)?)?;
                        py_parts.append(pdict)?;
                    }
                }
            }
            dict.set_item("parts", py_parts)?;
            Ok(dict.into())
        }
        Expr::Await(expr) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Await")?;
            dict.set_item("expr", expr_to_python(py, expr)?)?;
            Ok(dict.into())
        }
        Expr::Yield(expr_opt) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Yield")?;
            if let Some(e) = expr_opt {
                dict.set_item("value", expr_to_python(py, e)?)?;
            }
            Ok(dict.into())
        }
        Expr::Propagate(expr) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Propagate")?;
            dict.set_item("expr", expr_to_python(py, expr)?)?;
            Ok(dict.into())
        }
    }
}

fn typehint_to_python(py: Python, th: &TypeHint) -> PyResult<PyObject> {
    let dict = PyDict::new_bound(py);
    dict.set_item("name", th.name.clone())?;
    dict.set_item("nullable", th.nullable)?;
    let py_generics = PyList::empty_bound(py);
    for g in &th.generics {
        py_generics.append(typehint_to_python(py, g)?)?;
    }
    dict.set_item("generics", py_generics)?;
    Ok(dict.into())
}

// ─────────────────────────────────────────────────────────────────────
// Token-to-string helpers (for lex output)
// ─────────────────────────────────────────────────────────────────────

fn token_type_name(token: &token::Token) -> &'static str {
    use token::Token::*;
    match token {
        Int(_) => "Int",
        Float(_) => "Float",
        String(_) => "String",
        Bool(_) => "Bool",
        Identifier(_) => "Ident",
        Nil => "Nil",
        Let => "Let",
        Const => "Const",
        Fn => "Fn",
        Struct => "Struct",
        Enum => "Enum",
        Class => "Class",
        If => "If",
        Else => "Else",
        While => "While",
        For => "For",
        In => "In",
        Return => "Return",
        Break => "Break",
        Continue => "Continue",
        Switch => "Switch",
        Case => "Case",
        Default => "Default",
        Try => "Try",
        Catch => "Catch",
        Finally => "Finally",
        Throw => "Throw",
        Yield => "Yield",
        Async => "Async",
        Await => "Await",
        And => "And",
        Or => "Or",
        Not => "Not",
        OnStart => "OnStart",
        OnUpdate => "OnUpdate",
        OnDraw => "OnDraw",
        OnExit => "OnExit",
        Node => "Node",
        OnReady => "OnReady",
        OnNodeUpdate => "OnNodeUpdate",
        OnNodeDraw => "OnNodeDraw",
        IntType => "IntType",
        FloatType => "FloatType",
        BoolType => "BoolType",
        StringType => "StringType",
        VoidType => "VoidType",
        Import => "Import",
        From => "From",
        As => "As",
        Export => "Export",
        SelfKw => "Self",
        Super => "Super",
        Null => "Null",
        Spawn => "Spawn",
        Select => "Select",
        Then => "Then",
        Abstract => "Abstract",
        Interface => "Interface",
        Impl => "Impl",
        Pub => "Pub",
        Is => "Is",
        Div => "Div",
        Defer => "Defer",
        Repeat => "Repeat",
        Until => "Until",
        Plus => "Plus",
        Minus => "Minus",
        Star => "Star",
        Slash => "Slash",
        Percent => "Percent",
        Power => "Power",
        PlusPlus => "PlusPlus",
        SlashSlash => "SlashSlash",
        PlusEq | MinusEq | StarEq | SlashEq | PercentEq | PowerEq => "Assign",
        Eq => "Eq",
        Neq => "Neq",
        Lt => "Lt",
        Lte => "Lte",
        Gt => "Gt",
        Gte => "Gte",
        BitwiseAnd => "BitwiseAnd",
        BitwiseOr => "BitwiseOr",
        BitwiseXor => "BitwiseXor",
        BitwiseNot => "BitwiseNot",
        LeftShift => "LeftShift",
        RightShift => "RightShift",
        AmpEq | PipeEq | CaretEq | LShiftEq | RShiftEq => "Assign",
        Assign => "Assign",
        Arrow => "Arrow",
        FatArrow => "FatArrow",
        Question => "Question",
        QuestionDot => "QuestionDot",
        Nullish => "Nullish",
        NullishEq => "NullishEq",
        Pipe => "Pipe",
        PipeGt => "PipeGt",
        LeftParen => "LeftParen",
        RightParen => "RightParen",
        LeftBrace => "LeftBrace",
        RightBrace => "RightBrace",
        LeftBracket => "LeftBracket",
        RightBracket => "RightBracket",
        Comma => "Comma",
        Dot => "Dot",
        Semicolon => "Semicolon",
        Colon => "Colon",
        DoubleColon => "DoubleColon",
        At => "At",
        DotDot => "DotDot",
        DotDotEq => "DotDotEq",
        Ellipsis => "Ellipsis",
        FString(_) => "FString",
        Eof => "Eof",
    }
}

fn token_value(token: &token::Token) -> String {
    use token::Token::*;
    match token {
        Int(n) => n.to_string(),
        Float(f) => f.to_string(),
        String(s) => s.clone(),
        Bool(b) => b.to_string(),
        FString(s) => s.clone(),
        Identifier(s) => s.clone(),
        PlusPlus => "++".to_string(),
        SlashSlash => "//".to_string(),
        PlusEq => "+=".to_string(),
        MinusEq => "-=".to_string(),
        StarEq => "*=".to_string(),
        SlashEq => "/=".to_string(),
        PercentEq => "%=".to_string(),
        PowerEq => "**=".to_string(),
        AmpEq => "&=".to_string(),
        PipeEq => "|=".to_string(),
        CaretEq => "^=".to_string(),
        LShiftEq => "<<=".to_string(),
        RShiftEq => ">>=".to_string(),
        Assign => "=".to_string(),
        Arrow => "->".to_string(),
        FatArrow => "=>".to_string(),
        Nullish => "??".to_string(),
        NullishEq => "??=".to_string(),
        QuestionDot => "?.".to_string(),
        PipeGt => "|>".to_string(),
        DoubleColon => "::".to_string(),
        At => "@".to_string(),
        DotDot => "..".to_string(),
        DotDotEq => "..=".to_string(),
        Ellipsis => "...".to_string(),
        _ => std::string::String::new(),
    }
}

// ─────────────────────────────────────────────────────────────────────
// Lex function — Rust lexer exposed to Python
// ─────────────────────────────────────────────────────────────────────

#[pyfunction]
fn lex(source: &str) -> PyResult<Vec<PyObject>> {
    Python::with_gil(|py| {
        use lexer::Lexer;
        let mut lx = Lexer::new(source);
        match lx.tokenize() {
            Ok(tokens) => {
                let mut result = Vec::with_capacity(tokens.len());
                for ti in &tokens {
                    let d = PyDict::new_bound(py);
                    d.set_item("token_type", token_type_name(&ti.token))?;
                    d.set_item("value", token_value(&ti.token))?;
                    d.set_item("line", ti.line)?;
                    d.set_item("column", ti.column)?;
                    result.push(d.into());
                }
                Ok(result)
            }
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PySyntaxError, _>(e)),
        }
    })
}

// ─────────────────────────────────────────────────────────────────────
// PyO3 module definition
// ─────────────────────────────────────────────────────────────────────

#[pymodule]
#[pyo3(name = "inscript_parser")]
fn inscript_parser_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyParser>()?;
    m.add_function(wrap_pyfunction!(lex, m)?)?;
    m.add_function(wrap_pyfunction!(parse_tokens, m)?)?;
    m.add_function(wrap_pyfunction!(compile, m)?)?;
    m.add_function(wrap_pyfunction!(compile_and_run, m)?)?;
    Ok(())
}

// ─────────────────────────────────────────────────────────────────────
// Compile function — AST to bytecode
// ─────────────────────────────────────────────────────────────────────

use inscript_vm_engine::{VMEngine, OpCode, Value, FuncDef};
use inscript_vm_engine::compiler::optimize;
use std::sync::Arc;
use std::collections::HashMap;

#[pyfunction]
fn compile(source: &str) -> PyResult<(Vec<u8>, Vec<u8>)> {
    use compiler::Compiler;
    use lexer::Lexer;
    use parser::Parser;

    let mut lx = Lexer::new(source);
    let tokens = lx.tokenize().map_err(|e| {
        PyErr::new::<pyo3::exceptions::PySyntaxError, _>(e)
    })?;

    let mut parser = Parser::new(tokens);
    let program = parser.parse().map_err(|e| {
        PyErr::new::<pyo3::exceptions::PySyntaxError, _>(format!("{}", e))
    })?;

    let (opcodes, constants, _functions, _source_map) = Compiler::compile(&program);

    // Serialize opcodes for Python: each OpCode → its discriminant byte
    {
        let op_bytes: Vec<u8> = opcodes.iter().map(|op| opcode_discriminant(op)).collect();
        let const_bytes = serialize_constants(&constants);
        Ok((op_bytes, const_bytes))
    }
}

fn opcode_discriminant(op: &OpCode) -> u8 {
    // Match each variant to a unique byte
    match op {
        OpCode::Push(_) => 0x01,
        OpCode::Pop => 0x02,
        OpCode::Duplicate => 0x03,
        OpCode::Swap => 0x04,
        OpCode::Negate => 0x05,
        OpCode::Concat => 0x06,
        OpCode::Length => 0x07,
        OpCode::Add => 0x10,
        OpCode::Sub => 0x11,
        OpCode::Mul => 0x12,
        OpCode::Div => 0x13,
        OpCode::Mod => 0x14,
        OpCode::Power => 0x15,
        OpCode::Equal => 0x20,
        OpCode::NotEqual => 0x21,
        OpCode::LessThan => 0x22,
        OpCode::LessEqual => 0x23,
        OpCode::GreaterThan => 0x24,
        OpCode::GreaterEqual => 0x25,
        OpCode::And => 0x30,
        OpCode::Or => 0x31,
        OpCode::Not => 0x32,
        OpCode::Halt => 0xFF,
        // Parameterized opcodes — not serializable via simple byte
        OpCode::Jump(_) | OpCode::JumpIfFalse(_) | OpCode::JumpIfTrue(_)
        | OpCode::Call(_) | OpCode::StoreReg(_) | OpCode::LoadReg(_)
        | OpCode::StoreGlobal(_) | OpCode::LoadGlobal(_)
        | OpCode::CreateArray(_) | OpCode::CreateObject(_)
        | OpCode::LoadConst(_) => 0xFE,
        OpCode::Nop => 0x00,
        _ => 0xFE,
    }
}

fn serialize_constants(constants: &[Value]) -> Vec<u8> {
    let mut bytes = Vec::new();
    for val in constants {
        match val {
            Value::Nil => bytes.push(0),
            Value::Bool(b) => {
                bytes.push(1);
                bytes.push(if *b { 1 } else { 0 });
            }
            Value::Int(n) => {
                bytes.push(2);
                bytes.extend_from_slice(&n.to_le_bytes());
            }
            Value::Float(f) => {
                bytes.push(3);
                bytes.extend_from_slice(&f.to_le_bytes());
            }
            Value::String(s) => {
                bytes.push(4);
                let len = s.len() as u32;
                bytes.extend_from_slice(&len.to_le_bytes());
                bytes.extend_from_slice(s.as_bytes());
            }
            _ => {
                bytes.push(0); // unsupported → nil
            }
        }
    }
    bytes
}

/// Compile and execute source in one shot (pure Rust pipeline)
#[pyfunction]
fn compile_and_run(source: &str) -> PyResult<String> {
    use compiler::Compiler;
    use lexer::Lexer;
    use parser::Parser;

    let mut lx = Lexer::new(source);
    let tokens = lx.tokenize()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PySyntaxError, _>(format!("Lex error: {}", e)))?;

    let mut parser = Parser::new(tokens);
    let program = parser.parse()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PySyntaxError, _>(format!("Parse error: {}", e)))?;

    let (opcodes, raw_constants, raw_functions, source_map) = Compiler::compile(&program);

    // Run optimization passes on main opcodes
    let (opcodes, opt_stats) = optimize(opcodes);

    // Convert constants to Arc<Value> for the VM
    let constants: Vec<Arc<Value>> = raw_constants.into_iter()
        .map(|v| Arc::new(v))
        .collect();

    // Build function table for the VM
    let func_table: HashMap<String, FuncDef> = raw_functions.into_iter().collect();

    let mut vm = VMEngine::from_opcodes_with_source_map(opcodes, constants, source_map, func_table, opt_stats);
    match vm.execute() {
        Ok(val) => Ok(val.to_string()),
        Err(e) => Ok(format!("Runtime error: {}", e)),
    }
}

// ─────────────────────────────────────────────────────────────────────
// Update module exports
// ─────────────────────────────────────────────────────────────────────

/// Main parsing function
#[pyfunction]
fn parse_tokens(py_tokens: Vec<PyObject>) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let tokens = convert_py_tokens(py, &py_tokens)?;
        let mut parser = Parser::new(tokens);
        match parser.parse() {
            Ok(program) => program_to_python(py, &program),
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PySyntaxError, _>(
                format!("Parse error: {}", e),
            )),
        }
    })
}
