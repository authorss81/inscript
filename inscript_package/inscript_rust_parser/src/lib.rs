// inscript_rust_parser/src/lib.rs v3.8.2+
// Complete PyO3 module integration for full AST serialization

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

mod ast;
mod token;
mod parser;
mod error;

use parser::Parser;
use token::TokenInfo;
use ast::*;
use error::ParseError;

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
        let tok_dict = py_tok.downcast::<PyDict>(py)?;
        
        let token_type_str: String = tok_dict.get_item("token_type")
            .and_then(|o| o.ok())
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::ValueError, _>("Missing token_type"))?
            .extract()?;
        
        let value: String = tok_dict.get_item("value")
            .and_then(|o| o.ok())
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::ValueError, _>("Missing value"))?
            .extract()?;
        
        let line: usize = tok_dict.get_item("line")
            .and_then(|o| o.ok())
            .and_then(|o| o.extract().ok())
            .unwrap_or(0);
        
        let column: usize = tok_dict.get_item("column")
            .and_then(|o| o.ok())
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
        "True" => True,
        "False" => False,
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
        Stmt::Expression(expr) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "ExprStatement")?;
            dict.set_item("expression", expr_to_python(py, expr)?)?;
            Ok(dict.into())
        }
        Stmt::VarDecl { name, init, type_hint, mutable } => {
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
        Stmt::FunctionDef { name, params, body, return_type, is_async } => {
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
        Stmt::ClassDef { name, extends, body } => {
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
        Stmt::If { condition, then_body, else_body } => {
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
        Stmt::While { condition, body } => {
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
        Stmt::For { target, iter, body } => {
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
        Stmt::Switch { expr, cases } => {
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
        Stmt::Throw(expr) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Throw")?;
            dict.set_item("expr", expr_to_python(py, expr)?)?;
            Ok(dict.into())
        }
        Stmt::Try { body, catch_clauses, finally_body } => {
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
        Stmt::Return(expr_opt) => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Return")?;
            if let Some(expr) = expr_opt {
                dict.set_item("value", expr_to_python(py, expr)?)?;
            }
            Ok(dict.into())
        }
        Stmt::Break => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Break")?;
            Ok(dict.into())
        }
        Stmt::Continue => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "Continue")?;
            Ok(dict.into())
        }
        _ => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "UnknownStatement")?;
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
        _ => {
            let dict = PyDict::new_bound(py);
            dict.set_item("type", "UnknownExpr")?;
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
// PyO3 module definition
// ─────────────────────────────────────────────────────────────────────

#[pymodule]
#[pyo3(name = "inscript_parser")]
fn inscript_parser_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyParser>()?;
    m.add_function(wrap_pyfunction!(parse_tokens, m)?)?;
    Ok(())
}

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
