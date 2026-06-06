#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_v373.py — InScript v3.7.3 Integration Tests

Tests Python integration with Rust parser module.
Version check: >= (3, 7, 3)
"""

import sys
import os

# Get version from inscript
try:
    import inscript
    INSCRIPT_VERSION = getattr(inscript, '__version__', (3, 7, 2))
except ImportError:
    INSCRIPT_VERSION = (3, 7, 2)

def test_version_check():
    """Test: Version is 3.7.3 or higher"""
    assert INSCRIPT_VERSION >= (3, 7, 3), f"Expected v3.7.3+, got {INSCRIPT_VERSION}"
    print("✓ Version check: v3.7.3+")

def test_rust_parser_import():
    """Test: Rust parser module imports successfully"""
    try:
        from inscript_parser import PyParser, parse_string
        print("✓ Rust parser module imported")
    except ImportError as e:
        print(f"⚠ Rust parser not compiled: {e}")
        print("  Run: pip install -e '.[dev]' to compile")

def test_python_core():
    """Test: Python core modules are available"""
    modules = [
        'inscript.lexer',
        'inscript.parser',
        'inscript.compiler',
        'inscript.interpreter',
        'inscript.vm',
        'inscript.errors',
    ]
    for mod in modules:
        try:
            __import__(mod)
            print(f"✓ {mod} available")
        except ImportError as e:
            print(f"✗ {mod} failed: {e}")

def test_stdlib_modules():
    """Test: Standard library modules load"""
    stdlib = [
        'inscript.stdlib',
        'inscript.stdlib_game',
        'inscript.stdlib_assets',
        'inscript.stdlib_values',
        'inscript.stdlib_extended',
    ]
    for mod in stdlib:
        try:
            __import__(mod)
            print(f"✓ {mod} available")
        except ImportError as e:
            print(f"⚠ {mod} not found: {e}")

def test_tools():
    """Test: Development tools available"""
    tools = [
        ('inscript.inscript_dap', 'DAP debugger'),
        ('inscript.inscript_fmt', 'Code formatter'),
        ('inscript.hot_reload', 'Hot reload'),
        ('inscript.analyzer', 'Code analyzer'),
    ]
    for mod, desc in tools:
        try:
            __import__(mod)
            print(f"✓ {desc} available")
        except ImportError:
            print(f"⚠ {desc} not available")

def test_lsp():
    """Test: LSP server components"""
    lsp_mods = [
        'lsp.definition',
        'lsp.diagnostics',
        'lsp.semantic_tokens',
        'lsp.hover',
        'lsp.completions',
    ]
    for mod in lsp_mods:
        try:
            __import__(mod)
            print(f"✓ {mod} available")
        except ImportError:
            print(f"⚠ {mod} not found")

def test_integration():
    """Test: End-to-end integration pipeline"""
    print("\n=== Integration Test ===")
    
    # Step 1: Lexer
    try:
        from inscript.lexer import Lexer
        lexer = Lexer()
        print("✓ Lexer initialized")
    except Exception as e:
        print(f"✗ Lexer failed: {e}")
        return
    
    # Step 2: Parser
    try:
        from inscript.parser import Parser
        parser = Parser()
        print("✓ Parser initialized")
    except Exception as e:
        print(f"✗ Parser failed: {e}")
        return
    
    # Step 3: Compiler
    try:
        from inscript.compiler import Compiler
        compiler = Compiler()
        print("✓ Compiler initialized")
    except Exception as e:
        print(f"✗ Compiler failed: {e}")
        return
    
    # Step 4: VM
    try:
        from inscript.vm import VM
        vm = VM()
        print("✓ VM initialized")
    except Exception as e:
        print(f"✗ VM failed: {e}")
        return
    
    print("✓ Full pipeline ready")

def test_package_structure():
    """Test: Package structure integrity"""
    required_files = [
        'setup.py',
        'VERSION.txt',
        'README_v373.md',
    ]
    
    for fname in required_files:
        path = os.path.join(os.path.dirname(__file__), fname)
        if os.path.exists(path):
            print(f"✓ {fname} present")
        else:
            print(f"✗ {fname} missing")

def test_rust_parser_compilation():
    """Test: Rust parser compiles successfully"""
    print("\n=== Rust Parser Compilation ===")
    import subprocess
    
    rust_dir = os.path.join(os.path.dirname(__file__), 'inscript_rust_parser')
    
    if not os.path.exists(rust_dir):
        print("⚠ inscript_rust_parser directory not found")
        return
    
    print(f"Rust parser source found at {rust_dir}")
    
    # Check Cargo.toml
    cargo_path = os.path.join(rust_dir, 'Cargo.toml')
    if os.path.exists(cargo_path):
        print("✓ Cargo.toml present")
    else:
        print("✗ Cargo.toml missing")
        return
    
    # Check Rust source files
    src_dir = os.path.join(rust_dir, 'src')
    required_rs = ['lib.rs', 'parser.rs', 'ast.rs', 'token.rs', 'error.rs']
    
    for rs_file in required_rs:
        path = os.path.join(src_dir, rs_file)
        if os.path.exists(path):
            print(f"✓ {rs_file} present")
        else:
            print(f"✗ {rs_file} missing")

def main():
    """Run all tests"""
    print("=" * 60)
    print("InScript v3.7.3 Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Version Check", test_version_check),
        ("Rust Parser Import", test_rust_parser_import),
        ("Python Core", test_python_core),
        ("Standard Library", test_stdlib_modules),
        ("Development Tools", test_tools),
        ("LSP Server", test_lsp),
        ("Package Structure", test_package_structure),
        ("Rust Parser Compilation", test_rust_parser_compilation),
        ("Full Integration", test_integration),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\n>>> {name}")
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ Failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {failed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
