// inscript_vm_engine/src/compile.rs
// Native compilation pipeline for hot traces (Phase 3)
//
// Converts emitted LLVM IR (.ll text) into native machine code by:
//   1. Writing IR to a temp file
//   2. Running `opt` for LLVM optimizations
//   3. Running `llc` for native codegen → object file
//   4. Linking with `cc`/`gcc`/`clang` → shared library (.so/.dll)
//   5. Loading via libloading → function pointer
//
// All steps gracefully fall back on missing toolchain.

use std::fs;
use std::path::Path;
use std::process::Command;

// ─────────────────────────────────────────────────────────────────────────────
// Public API
// ─────────────────────────────────────────────────────────────────────────────

/// Try to compile a hot trace's LLVM IR into a native function pointer.
///
/// Returns `Some(fn_ptr)` if compilation succeeds and the library loads.
/// Returns `None` if any step fails (toolchain missing, compilation error, etc).
pub fn try_compile_trace(name: &str, ir_text: &str) -> Option<usize> {
    let tmp = std::env::temp_dir().join(format!("inscript_trace_{}", sanitize(name)));

    // Step 1: Write IR to .ll file
    let ll_path = tmp.with_extension("ll");
    if fs::write(&ll_path, ir_text).is_err() {
        return None;
    }

    // Step 2: Run `opt` for optimization (optional — silently skip if missing)
    let opt_path = tmp.with_extension("opt.bc");
    let ir_after_opt = if try_run_opt(ll_path.as_path(), opt_path.as_path()) {
        // Use the optimized bitcode for llc
        opt_path.to_string_lossy().to_string()
    } else {
        // Fall back to original .ll
        ll_path.to_string_lossy().to_string()
    };

    // Step 3: Run `llc` to produce object file
    let obj_path = tmp.with_extension("o");
    if !try_run_llc(&ir_after_opt, obj_path.as_path()) {
        return None;
    }

    // Step 4: Link into shared library
    let lib_path = if cfg!(target_os = "windows") {
        tmp.with_extension("dll")
    } else if cfg!(target_os = "macos") {
        tmp.with_extension("dylib")
    } else {
        tmp.with_extension("so")
    };

    if !try_link(obj_path.as_path(), lib_path.as_path()) {
        return None;
    }

    // Step 5: Load the library and get the function pointer
    let fn_ptr = unsafe { load_function(lib_path.as_path(), name)? };

    // Clean up temp files (best-effort)
    let _ = fs::remove_file(&ll_path);
    let _ = fs::remove_file(&opt_path);
    let _ = fs::remove_file(&obj_path);
    // Keep the .so/.dll for the lifetime of the process

    Some(fn_ptr)
}

// ─────────────────────────────────────────────────────────────────────────────
// Internal helpers
// ─────────────────────────────────────────────────────────────────────────────

/// Sanitize a trace name for use as a filename.
fn sanitize(name: &str) -> String {
    name.chars().map(|c| {
        if c.is_alphanumeric() || c == '_' || c == '-' { c } else { '_' }
    }).collect()
}

/// Run `opt -O2` on the IR file, writing bitcode to `out_path`. Returns true on success.
fn try_run_opt(ll_path: &Path, out_path: &Path) -> bool {
    Command::new("opt")
        .args(["-O2", "-o"])
        .arg(out_path)
        .arg(ll_path)
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

/// Run `llc` to compile IR/bitcode to a native object file.
fn try_run_llc(input: &str, obj_path: &Path) -> bool {
    // Try with `-filetype=obj` first
    let result = Command::new("llc")
        .args(["-filetype=obj", "-o"])
        .arg(obj_path)
        .arg(input)
        .output();

    if result.as_ref().map(|o| o.status.success()).unwrap_or(false) {
        return true;
    }

    // Fallback: emit assembly and invoke assembler
    let asm_path = obj_path.with_extension("s");
    if !Command::new("llc")
        .args(["-o"])
        .arg(&asm_path)
        .arg(input)
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
    {
        return false;
    }

    // Assemble with system assembler
    let asm_ok = if cfg!(target_os = "windows") {
        Command::new("ml64")
            .args(["-c", "-Fo"])
            .arg(obj_path)
            .arg(&asm_path)
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    } else {
        Command::new("cc")
            .args(["-c", "-o"])
            .arg(obj_path)
            .arg(&asm_path)
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    };

    let _ = fs::remove_file(&asm_path);
    asm_ok
}

/// Link an object file into a shared library.
fn try_link(obj_path: &Path, lib_path: &Path) -> bool {
    if cfg!(target_os = "windows") {
        // Try `link.exe`
        if Command::new("link")
            .arg("/DLL")
            .arg("/NOLOGO")
            .arg(format!("/OUT:{}", lib_path.display()))
            .arg(obj_path)
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
        {
            return true;
        }
        // Fallback: `gcc` on Windows
        Command::new("gcc")
            .args(["-shared", "-o"])
            .arg(lib_path)
            .arg(obj_path)
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    } else {
        let mut cmd = Command::new("cc");
        cmd.args(["-shared", "-fPIC", "-o"])
            .arg(lib_path)
            .arg(obj_path);
        if cfg!(target_os = "macos") {
            cmd.arg("-undefined").arg("dynamic_lookup");
        }
        if cmd.output().map(|o| o.status.success()).unwrap_or(false) {
            return true;
        }
        // Fallback: `ld` on Linux
        if cfg!(target_os = "linux") {
            Command::new("ld")
                .args(["-shared", "-o"])
                .arg(lib_path)
                .arg(obj_path)
                .args(["-lc", "-lm"])
                .output()
                .map(|o| o.status.success())
                .unwrap_or(false)
        } else {
            false
        }
    }
}

/// Load a shared library and get a function pointer by symbol name.
///
/// # Safety
///
/// The caller must ensure the library path is valid and the symbol exists.
unsafe fn load_function(lib_path: &Path, name: &str) -> Option<usize> {
    let lib = libloading::Library::new(lib_path).ok()?;
    let leaked: &'static libloading::Library = Box::leak(Box::new(lib));

    let fn_name = name.to_owned();
    // Try exact name first
    let sym = leaked.get::<unsafe extern "C" fn() -> i64>(fn_name.as_bytes());
    let func: libloading::Symbol<unsafe extern "C" fn() -> i64> = match sym {
        Ok(f) => f,
        Err(_) => {
            // Try without trace_ prefix
            let alt = name.strip_prefix("trace_").unwrap_or(name);
            leaked.get::<unsafe extern "C" fn() -> i64>(alt.as_bytes()).ok()?
        }
    };
    let raw: *const () = *func as *const ();
    Some(raw as usize)
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sanitize() {
        assert_eq!(sanitize("trace_42"), "trace_42");
        assert_eq!(sanitize("my loop!"), "my_loop_");
        assert_eq!(sanitize(""), "");
    }

    #[test]
    fn test_opt_not_found_graceful() {
        // Should return false when opt is not available
        let ll = std::env::temp_dir().join("_test_nonexistent.ll");
        let out = std::env::temp_dir().join("_test_nonexistent.bc");
        // Don't create the input file — expect false
        assert!(!try_run_opt(&ll, &out));
    }

    #[test]
    fn test_llc_not_found_graceful() {
        let obj = std::env::temp_dir().join("_test_nonexistent.o");
        assert!(!try_run_llc("/nonexistent/input.ll", &obj));
    }

    #[test]
    fn test_link_not_found_graceful() {
        let obj = std::env::temp_dir().join("_test_nonexistent.o");
        let lib = std::env::temp_dir().join("_test_nonexistent.so");
        assert!(!try_link(&obj, &lib));
    }

    #[test]
    fn test_compile_full_pipeline_graceful_on_missing_toolchain() {
        // This should return None if llc is not available (which is the expected case
        // in most dev environments without LLVM installed).
        let ir = "; ModuleID = 'test'
target triple = \"x86_64-unknown-linux-gnu\"
define i64 @test_fn() {
  ret i64 42
}
";
        let result = try_compile_trace("test_fn", ir);
        // On CI/dev machines without llc, this returns None — that's fine.
        // The test just verifies no panic/crash.
        if result.is_some() {
            // If llc IS available, the function pointer should be non-null
            assert_ne!(result.unwrap(), 0);
        }
    }

    #[test]
    fn test_compile_with_opt_and_llc() {
        // Test with opt+llc pipeline if both tools are available
        let ir = "; ModuleID = 'test'
target triple = \"x86_64-unknown-linux-gnu\"
define i64 @my_trace() {
  %1 = add i64 0, 1
  ret i64 %1
}
";
        // Check if opt is available
        let has_opt = Command::new("opt")
            .arg("--version")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false);

        let has_llc = Command::new("llc")
            .arg("--version")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false);

        if has_opt && has_llc {
            let result = try_compile_trace("my_trace", ir);
            assert!(result.is_some(), "Expected compilation to succeed with opt+llc available");
        }
        // If tools aren't available, test still passes (graceful degradation)
    }
}
