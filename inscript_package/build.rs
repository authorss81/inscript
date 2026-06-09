// build.rs — InScript Workspace Build Script
//
// Checks that Cargo.toml versions match inscript.py's VERSION
// at build time to prevent version drift.

use std::env;
use std::fs;
use std::path::Path;

fn main() {
    // Only check during release builds (avoid slowing down dev cycles)
    let profile = env::var("PROFILE").unwrap_or_default();
    if profile != "release" {
        return;
    }

    // Find workspace root (where build.rs lives = inscript_package/)
    let manifest_dir = env::var("CARGO_MANIFEST_DIR").unwrap_or_default();
    let workspace_root = Path::new(&manifest_dir);

    // Read inscript.py VERSION
    let inscript_py_path = workspace_root.join("inscript.py");
    let inscript_py = fs::read_to_string(&inscript_py_path)
        .unwrap_or_else(|_| panic!("Cannot read {}", inscript_py_path.display()));

    let version_line = inscript_py.lines()
        .find(|l| l.trim().starts_with("VERSION"))
        .expect("VERSION not found in inscript.py");
    let expected: &str = version_line
        .split('"')
        .nth(1)
        .expect("Cannot parse VERSION string");

    // Read this crate's Cargo.toml version
    let cargo_toml_path = workspace_root.join("Cargo.toml");
    let cargo_toml = fs::read_to_string(&cargo_toml_path)
        .unwrap_or_else(|_| panic!("Cannot read {}", cargo_toml_path.display()));

    let actual: &str = cargo_toml.lines()
        .find(|l| l.trim().starts_with("version"))
        .and_then(|l| l.split('"').nth(1))
        .expect("Cannot parse Cargo.toml version");

    if expected != actual {
        panic!(
            "\n❌ Version mismatch!\n   inscript.py: {}\n   Cargo.toml:  {}\n\n\
             Bump the version in Cargo.toml to match inscript.py before releasing.\n",
            expected, actual
        );
    }

    println!("cargo:warning=✅ Version OK: all crates match inscript.py v{}", expected);
}
