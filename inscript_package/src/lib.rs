//! InScript Lexer - Rust Implementation (v3.7.2)
//! 
//! Fast tokenization with zero-copy references
//! Compiles to: libinscript_lexer.so/.dll/.dylib

use pyo3::prelude::*;

pub mod token;
pub mod lexer;
pub mod error;

pub use token::{Token, TokenType};
pub use lexer::Lexer;
pub use error::LexError;

/// Python module initialization
#[pymodule]
fn inscript_lexer(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyLexer>()?;
    m.add_function(wrap_pyfunction!(tokenize_string, m)?)?;
    
    Ok(())
}

/// Python wrapper for Lexer
#[pyclass]
pub struct PyLexer {
    tokens: Vec<PyToken>,
}

#[pyclass]
#[derive(Clone)]
pub struct PyToken {
    pub token_type: String,
    pub value: String,
    pub line: usize,
    pub column: usize,
}

#[pymethods]
impl PyLexer {
    /// Create new lexer and tokenize
    #[new]
    fn new(code: String) -> PyResult<Self> {
        let lexer = Lexer::new(&code);
        let tokens = lexer.collect::<Result<Vec<_>, _>>()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PySyntaxError, _>(e.to_string()))?;
        
        let py_tokens = tokens
            .into_iter()
            .map(|t| PyToken {
                token_type: format!("{:?}", t.token_type),
                value: t.value.to_string(),
                line: t.line,
                column: t.column,
            })
            .collect();
        
        Ok(PyLexer {
            tokens: py_tokens,
        })
    }

    /// Get all tokens
    fn tokens(&self) -> Vec<PyToken> {
        self.tokens.clone()
    }

    /// Get token count
    fn count(&self) -> usize {
        self.tokens.len()
    }
}

/// Tokenize string directly
#[pyfunction]
fn tokenize_string(code: String) -> PyResult<Vec<PyToken>> {
    let lexer = Lexer::new(&code);
    let tokens = lexer.collect::<Result<Vec<_>, _>>()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PySyntaxError, _>(e.to_string()))?;
    
    Ok(tokens
        .into_iter()
        .map(|t| PyToken {
            token_type: format!("{:?}", t.token_type),
            value: t.value.to_string(),
            line: t.line,
            column: t.column,
        })
        .collect())
}
