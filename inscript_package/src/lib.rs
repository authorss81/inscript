//! InScript Virtual Machine - Rust Implementation
//! 
//! Fast, safe bytecode interpreter with PyO3 bindings
//! Compiles to: libinscript_vm.so (Linux), .dll (Windows), .dylib (macOS)

use pyo3::prelude::*;

pub mod value;
pub mod bytecode;
pub mod vm;
pub mod stack;
pub mod error;

pub use value::Value;
pub use bytecode::{ByteCode, OpCode};
pub use vm::VirtualMachine;
pub use error::VMError;

/// Python module initialization
#[pymodule]
fn inscript_vm(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyVM>()?;
    m.add_function(wrap_pyfunction!(execute_bytecode, m)?)?;
    m.add_function(wrap_pyfunction!(compile_code, m)?)?;
    
    Ok(())
}

/// PyO3-wrapped VM for Python
#[pyclass]
pub struct PyVM {
    vm: VirtualMachine,
}

#[pymethods]
impl PyVM {
    /// Create new VM instance
    #[new]
    fn new() -> Self {
        PyVM {
            vm: VirtualMachine::new(),
        }
    }

    /// Execute bytecode
    fn execute(&mut self, bytecode_bytes: Vec<u8>) -> PyResult<String> {
        match self.vm.execute(&bytecode_bytes) {
            Ok(result) => Ok(result),
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string())),
        }
    }

    /// Get VM statistics
    fn stats(&self) -> PyResult<String> {
        Ok(format!(
            "VM Stats: Executions={}, Stack Depth={}",
            self.vm.execution_count(),
            self.vm.stack_depth()
        ))
    }
}

/// Execute bytecode directly
#[pyfunction]
fn execute_bytecode(bytecode: Vec<u8>) -> PyResult<String> {
    let mut vm = VirtualMachine::new();
    match vm.execute(&bytecode) {
        Ok(result) => Ok(result),
        Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string())),
    }
}

/// Compile code (placeholder)
#[pyfunction]
fn compile_code(code: String) -> PyResult<Vec<u8>> {
    // In real implementation, would parse and compile
    // For now, return empty bytecode
    Ok(vec![])
}
