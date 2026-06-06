// inscript_v380/unified_ffi_bridge.rs
// Unified FFI Layer - Single interface for all Rust components
// Handles: Type marshalling, Error translation, Memory management, Thread-safe communication

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};
use pyo3::exceptions::{PyTypeError, PyValueError, PyRuntimeError};
use std::sync::Arc;
use parking_lot::RwLock;

/// Result type for FFI operations
pub type FFIResult<T> = Result<T, FFIError>;

/// FFI Error types
#[derive(Debug, Clone)]
pub enum FFIError {
    TypeMismatch { expected: String, got: String },
    ValueError(String),
    RuntimeError(String),
    Overflow(String),
    StackOverflow,
    IndexOutOfBounds { index: usize, length: usize },
    UndefinedVariable(String),
    ZeroDivision,
    InvalidOperation(String),
}

impl std::fmt::Display for FFIError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            FFIError::TypeMismatch { expected, got } => {
                write!(f, "Type mismatch: expected {}, got {}", expected, got)
            }
            FFIError::ValueError(msg) => write!(f, "Value error: {}", msg),
            FFIError::RuntimeError(msg) => write!(f, "Runtime error: {}", msg),
            FFIError::Overflow(msg) => write!(f, "Overflow: {}", msg),
            FFIError::StackOverflow => write!(f, "Stack overflow"),
            FFIError::IndexOutOfBounds { index, length } => {
                write!(f, "Index {} out of bounds (length {})", index, length)
            }
            FFIError::UndefinedVariable(name) => write!(f, "Undefined variable: '{}'", name),
            FFIError::ZeroDivision => write!(f, "Division by zero"),
            FFIError::InvalidOperation(msg) => write!(f, "Invalid operation: {}", msg),
        }
    }
}

impl std::error::Error for FFIError {}

impl From<FFIError> for PyErr {
    fn from(err: FFIError) -> Self {
        match err {
            FFIError::TypeMismatch { expected, got } => {
                PyTypeError::new_err(format!("Type mismatch: expected {}, got {}", expected, got))
            }
            FFIError::ValueError(msg) => PyValueError::new_err(msg),
            FFIError::ZeroDivision => PyValueError::new_err("Division by zero"),
            FFIError::StackOverflow => PyRuntimeError::new_err("Stack overflow"),
            FFIError::IndexOutOfBounds { index, length } => {
                PyValueError::new_err(format!("Index {} out of bounds (length {})", index, length))
            }
            FFIError::UndefinedVariable(name) => {
                PyRuntimeError::new_err(format!("Undefined variable: '{}'", name))
            }
            _ => PyRuntimeError::new_err(err.to_string()),
        }
    }
}

/// Value type for FFI
#[derive(Debug, Clone)]
pub enum Value {
    Nil,
    Bool(bool),
    Int(i64),
    Float(f64),
    String(String),
    Array(Arc<RwLock<Vec<Value>>>),
    Object(Arc<RwLock<std::collections::HashMap<String, Value>>>),
}

impl Value {
    pub fn type_name(&self) -> &'static str {
        match self {
            Value::Nil => "nil",
            Value::Bool(_) => "bool",
            Value::Int(_) => "int",
            Value::Float(_) => "float",
            Value::String(_) => "string",
            Value::Array(_) => "array",
            Value::Object(_) => "object",
        }
    }

    pub fn is_truthy(&self) -> bool {
        match self {
            Value::Nil => false,
            Value::Bool(b) => *b,
            Value::Int(n) => *n != 0,
            Value::Float(f) => *f != 0.0,
            Value::String(s) => !s.is_empty(),
            Value::Array(arr) => !arr.read().is_empty(),
            Value::Object(obj) => !obj.read().is_empty(),
        }
    }

    pub fn as_int(&self) -> FFIResult<i64> {
        match self {
            Value::Int(n) => Ok(*n),
            Value::Float(f) => Ok(*f as i64),
            _ => Err(FFIError::TypeMismatch {
                expected: "int".to_string(),
                got: self.type_name().to_string(),
            }),
        }
    }

    pub fn as_float(&self) -> FFIResult<f64> {
        match self {
            Value::Int(n) => Ok(*n as f64),
            Value::Float(f) => Ok(*f),
            _ => Err(FFIError::TypeMismatch {
                expected: "float".to_string(),
                got: self.type_name().to_string(),
            }),
        }
    }

    pub fn as_string(&self) -> FFIResult<String> {
        match self {
            Value::String(s) => Ok(s.clone()),
            _ => Err(FFIError::TypeMismatch {
                expected: "string".to_string(),
                got: self.type_name().to_string(),
            }),
        }
    }
}

/// Main FFI Bridge struct
pub struct FFIBridge {
    // Internal state
    type_cache: Arc<RwLock<std::collections::HashMap<String, String>>>,
}

impl FFIBridge {
    pub fn new() -> Self {
        FFIBridge {
            type_cache: Arc::new(RwLock::new(std::collections::HashMap::new())),
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // MARSHALLING: Python ↔ Rust Type Conversion
    // ═══════════════════════════════════════════════════════════════════════

    /// Convert Python value to Rust Value
    pub fn python_to_rust(py: Python, obj: &PyAny) -> FFIResult<Value> {
        // Nil / None
        if obj.is_none() {
            return Ok(Value::Nil);
        }

        // Bool
        if let Ok(b) = obj.downcast::<pyo3::types::PyBool>() {
            return Ok(Value::Bool(b.is_true()));
        }

        // Int
        if let Ok(i) = obj.extract::<i64>() {
            return Ok(Value::Int(i));
        }

        // Float
        if let Ok(f) = obj.extract::<f64>() {
            return Ok(Value::Float(f));
        }

        // String
        if let Ok(s) = obj.extract::<String>() {
            return Ok(Value::String(s));
        }

        // List → Array
        if let Ok(list) = obj.downcast::<PyList>() {
            let mut arr = Vec::new();
            for item in list.iter() {
                arr.push(Self::python_to_rust(py, item)?);
            }
            return Ok(Value::Array(Arc::new(RwLock::new(arr))));
        }

        // Dict → Object
        if let Ok(dict) = obj.downcast::<PyDict>() {
            let mut obj_map = std::collections::HashMap::new();
            for (k, v) in dict.iter() {
                let key = k.extract::<String>()?;
                let val = Self::python_to_rust(py, v)?;
                obj_map.insert(key, val);
            }
            return Ok(Value::Object(Arc::new(RwLock::new(obj_map))));
        }

        Err(FFIError::TypeMismatch {
            expected: "value".to_string(),
            got: format!("{:?}", obj.get_type()),
        })
    }

    /// Convert Rust Value to Python object
    pub fn rust_to_python(py: Python, value: &Value) -> PyResult<PyObject> {
        match value {
            Value::Nil => Ok(py.None()),
            Value::Bool(b) => Ok(b.into_py(py)),
            Value::Int(n) => Ok(n.into_py(py)),
            Value::Float(f) => Ok(f.into_py(py)),
            Value::String(s) => Ok(s.into_py(py)),
            Value::Array(arr) => {
                let list = PyList::new(py, &[]);
                for item in arr.read().iter() {
                    list.append(Self::rust_to_python(py, item)?)?;
                }
                Ok(list.into_py(py))
            }
            Value::Object(obj) => {
                let dict = PyDict::new(py);
                for (k, v) in obj.read().iter() {
                    dict.set_item(k, Self::rust_to_python(py, v)?)?;
                }
                Ok(dict.into_py(py))
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // ERROR HANDLING: FFI Error ↔ Python Exception
    // ═══════════════════════════════════════════════════════════════════════

    /// Convert FFI error to Python exception
    pub fn ffi_error_to_py(err: FFIError) -> PyErr {
        match err {
            FFIError::TypeMismatch { expected, got } => {
                PyTypeError::new_err(format!("Type mismatch: expected {}, got {}", expected, got))
            }
            FFIError::ValueError(msg) => PyValueError::new_err(msg),
            FFIError::RuntimeError(msg) => PyRuntimeError::new_err(msg),
            FFIError::ZeroDivision => PyValueError::new_err("Division by zero"),
            FFIError::StackOverflow => PyRuntimeError::new_err("Stack overflow"),
            FFIError::IndexOutOfBounds { index, length } => {
                PyValueError::new_err(format!("Index {} out of bounds (length {})", index, length))
            }
            FFIError::UndefinedVariable(name) => {
                PyRuntimeError::new_err(format!("Undefined variable: '{}'", name))
            }
            _ => PyRuntimeError::new_err(err.to_string()),
        }
    }

    /// Convert Python exception to FFI error
    pub fn py_error_to_ffi(err: &PyErr) -> FFIError {
        if err.is_instance_of::<pyo3::exceptions::PyTypeError>() {
            FFIError::TypeMismatch {
                expected: "unknown".to_string(),
                got: "unknown".to_string(),
            }
        } else if err.is_instance_of::<pyo3::exceptions::PyValueError>() {
            FFIError::ValueError(err.to_string())
        } else if err.is_instance_of::<pyo3::exceptions::PyRuntimeError>() {
            FFIError::RuntimeError(err.to_string())
        } else {
            FFIError::RuntimeError(err.to_string())
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // VALIDATION: Type checking and validation
    // ═══════════════════════════════════════════════════════════════════════

    /// Validate value type
    pub fn validate_type(value: &Value, expected_type: &str) -> FFIResult<()> {
        if value.type_name() != expected_type {
            return Err(FFIError::TypeMismatch {
                expected: expected_type.to_string(),
                got: value.type_name().to_string(),
            });
        }
        Ok(())
    }

    /// Check bounds
    pub fn check_bounds(index: usize, length: usize) -> FFIResult<()> {
        if index >= length {
            return Err(FFIError::IndexOutOfBounds { index, length });
        }
        Ok(())
    }

    /// Check for overflow
    pub fn check_overflow(value: i64, max: i64) -> FFIResult<()> {
        if value > max {
            return Err(FFIError::Overflow(format!("Value {} exceeds max {}", value, max)));
        }
        Ok(())
    }

    // ═══════════════════════════════════════════════════════════════════════
    // PERFORMANCE: Caching and optimization
    // ═══════════════════════════════════════════════════════════════════════

    /// Cache type information
    pub fn cache_type(&self, key: String, type_name: String) {
        self.type_cache.write().insert(key, type_name);
    }

    /// Get cached type
    pub fn get_cached_type(&self, key: &str) -> Option<String> {
        self.type_cache.read().get(key).cloned()
    }

    /// Clear type cache
    pub fn clear_type_cache(&self) {
        self.type_cache.write().clear();
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PyO3 MODULE BINDING
// ═══════════════════════════════════════════════════════════════════════════

#[pyclass]
pub struct PyFFIBridge {
    bridge: FFIBridge,
}

#[pymethods]
impl PyFFIBridge {
    #[new]
    fn new() -> Self {
        PyFFIBridge {
            bridge: FFIBridge::new(),
        }
    }

    /// Convert Python to Rust (and back) with validation
    fn convert_type(&self, py: Python, py_obj: &PyAny, target_type: &str) -> PyResult<PyObject> {
        let value = FFIBridge::python_to_rust(py, py_obj)
            .map_err(FFIBridge::ffi_error_to_py)?;

        FFIBridge::validate_type(&value, target_type)
            .map_err(FFIBridge::ffi_error_to_py)?;

        FFIBridge::rust_to_python(py, &value)
    }

    /// Get type name
    fn get_type(&self, py: Python, py_obj: &PyAny) -> PyResult<String> {
        let value = FFIBridge::python_to_rust(py, py_obj)
            .map_err(FFIBridge::ffi_error_to_py)?;
        Ok(value.type_name().to_string())
    }

    /// Check bounds safely
    fn check_bounds(&self, index: usize, length: usize) -> PyResult<()> {
        FFIBridge::check_bounds(index, length)
            .map_err(FFIBridge::ffi_error_to_py)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_value_int() {
        let val = Value::Int(42);
        assert_eq!(val.type_name(), "int");
        assert_eq!(val.as_int().unwrap(), 42);
    }

    #[test]
    fn test_value_float() {
        let val = Value::Float(3.14);
        assert_eq!(val.type_name(), "float");
        assert!((val.as_float().unwrap() - 3.14).abs() < 0.001);
    }

    #[test]
    fn test_value_string() {
        let val = Value::String("hello".to_string());
        assert_eq!(val.type_name(), "string");
        assert_eq!(val.as_string().unwrap(), "hello");
    }

    #[test]
    fn test_type_mismatch() {
        let val = Value::String("hello".to_string());
        assert!(val.as_int().is_err());
    }

    #[test]
    fn test_bounds_check() {
        assert!(FFIBridge::check_bounds(0, 10).is_ok());
        assert!(FFIBridge::check_bounds(9, 10).is_ok());
        assert!(FFIBridge::check_bounds(10, 10).is_err());
    }

    #[test]
    fn test_overflow_check() {
        assert!(FFIBridge::check_overflow(100, 1000).is_ok());
        assert!(FFIBridge::check_overflow(2000, 1000).is_err());
    }
}
