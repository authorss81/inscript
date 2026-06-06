// inscript_rust_parser/src/lib.rs
// PyO3 module initialization and Python-facing API

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
    fn new(tokens: Vec<PyObject>) -> PyResult<Self> {
        // Convert Python token list to Rust TokenInfo
        let tokens = tokens
            .iter()
            .map(|_| TokenInfo::new(token::Token::Eof, 0, 0))
            .collect();
        Ok(PyParser { tokens })
    }

    /// Parse tokens into an AST
    fn parse(&self) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let mut parser = Parser::new(self.tokens.clone());
            match parser.parse() {
                Ok(program) => {
                    let result = ast_to_python(py, &program)?;
                    Ok(result)
                }
                Err(e) => Err(PyErr::new::<pyo3::exceptions::PySyntaxError, _>(
                    e.to_string(),
                )),
            }
        })
    }

    /// Parse from a token list (static method)
    #[staticmethod]
    fn parse_tokens(tokens: Vec<PyObject>) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let token_infos: Vec<TokenInfo> = tokens
                .iter()
                .map(|_| TokenInfo::new(token::Token::Eof, 0, 0))
                .collect();

            let mut parser = Parser::new(token_infos);
            match parser.parse() {
                Ok(program) => {
                    let result = ast_to_python(py, &program)?;
                    Ok(result)
                }
                Err(e) => Err(PyErr::new::<pyo3::exceptions::PySyntaxError, _>(
                    e.to_string(),
                )),
            }
        })
    }
}

/// Convert Rust AST to Python objects
fn ast_to_python(py: Python, program: &Program) -> PyResult<PyObject> {
    let dict = PyDict::new_bound(py);
    
    let stmts = PyList::new_bound(py, program.statements.iter().map(|_| "Stmt"));
    dict.set_item("statements", stmts)?;
    dict.set_item("type", "Program")?;
    
    Ok(dict.into())
}

/// PyO3 module definition
#[pymodule]
#[pyo3(name = "inscript_parser")]
fn inscript_parser_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyParser>()?;
    
    // Add parser function
    m.add_function(wrap_pyfunction!(parse_string, m)?)?;
    
    Ok(())
}

/// Convenience function to parse InScript source code
#[pyfunction]
fn parse_string(source: &str, tokens: Vec<PyObject>) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let token_infos: Vec<TokenInfo> = tokens
            .iter()
            .map(|_| TokenInfo::new(token::Token::Eof, 0, 0))
            .collect();

        let mut parser = Parser::new(token_infos);
        match parser.parse() {
            Ok(program) => {
                let result = ast_to_python(py, &program)?;
                Ok(result)
            }
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PySyntaxError, _>(
                format!("Parse error: {}", e),
            )),
        }
    })
}
