//! Value type system for InScript

use crate::error::{VMError, VMResult};
use std::fmt;
use std::collections::HashMap;

/// InScript value types
#[derive(Debug, Clone)]
pub enum Value {
    Nil,
    Bool(bool),
    Int(i64),
    Float(f64),
    String(String),
    Array(Vec<Value>),
    Object(HashMap<String, Value>),
}

impl Value {
    /// Check if value is truthy
    pub fn is_truthy(&self) -> bool {
        match self {
            Value::Nil => false,
            Value::Bool(b) => *b,
            Value::Int(i) => *i != 0,
            Value::Float(f) => *f != 0.0,
            Value::String(s) => !s.is_empty(),
            Value::Array(a) => !a.is_empty(),
            Value::Object(o) => !o.is_empty(),
        }
    }

    /// Add two values
    pub fn add(&self, other: &Value) -> VMResult<Value> {
        match (self, other) {
            (Value::Int(a), Value::Int(b)) => Ok(Value::Int(a.saturating_add(*b))),
            (Value::Int(a), Value::Float(b)) => Ok(Value::Float(*a as f64 + b)),
            (Value::Float(a), Value::Int(b)) => Ok(Value::Float(a + *b as f64)),
            (Value::Float(a), Value::Float(b)) => Ok(Value::Float(a + b)),
            (Value::String(a), Value::String(b)) => Ok(Value::String(format!("{}{}", a, b))),
            (Value::String(a), Value::Int(b)) => Ok(Value::String(format!("{}{}", a, b))),
            _ => Err(VMError::TypeMismatch(format!("Cannot add {:?} and {:?}", self, other))),
        }
    }

    /// Subtract two values
    pub fn sub(&self, other: &Value) -> VMResult<Value> {
        match (self, other) {
            (Value::Int(a), Value::Int(b)) => Ok(Value::Int(a.saturating_sub(*b))),
            (Value::Float(a), Value::Float(b)) => Ok(Value::Float(a - b)),
            (Value::Int(a), Value::Float(b)) => Ok(Value::Float(*a as f64 - b)),
            (Value::Float(a), Value::Int(b)) => Ok(Value::Float(a - *b as f64)),
            _ => Err(VMError::TypeMismatch(format!("Cannot subtract {:?} and {:?}", self, other))),
        }
    }

    /// Multiply two values
    pub fn mul(&self, other: &Value) -> VMResult<Value> {
        match (self, other) {
            (Value::Int(a), Value::Int(b)) => Ok(Value::Int(a.saturating_mul(*b))),
            (Value::Float(a), Value::Float(b)) => Ok(Value::Float(a * b)),
            (Value::Int(a), Value::Float(b)) => Ok(Value::Float(*a as f64 * b)),
            (Value::Float(a), Value::Int(b)) => Ok(Value::Float(a * *b as f64)),
            _ => Err(VMError::TypeMismatch(format!("Cannot multiply {:?} and {:?}", self, other))),
        }
    }

    /// Divide two values
    pub fn div(&self, other: &Value) -> VMResult<Value> {
        match (self, other) {
            (Value::Int(a), Value::Int(b)) => {
                if *b == 0 {
                    Err(VMError::DivisionByZero)
                } else {
                    Ok(Value::Int(a / b))
                }
            }
            (Value::Float(a), Value::Float(b)) => {
                if *b == 0.0 {
                    Err(VMError::DivisionByZero)
                } else {
                    Ok(Value::Float(a / b))
                }
            }
            _ => Err(VMError::TypeMismatch(format!("Cannot divide {:?} and {:?}", self, other))),
        }
    }
}

impl fmt::Display for Value {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Value::Nil => write!(f, "nil"),
            Value::Bool(b) => write!(f, "{}", b),
            Value::Int(i) => write!(f, "{}", i),
            Value::Float(fl) => write!(f, "{}", fl),
            Value::String(s) => write!(f, "{}", s),
            Value::Array(_) => write!(f, "[array]"),
            Value::Object(_) => write!(f, "{{object}}"),
        }
    }
}
