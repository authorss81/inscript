#!/usr/bin/env python3
"""
Quick start guide for developers working on Inscript.
Run this script to verify your setup is correct.
"""

import sys
import os

def check_python_version():
    """Verify Python 3.8+ is installed."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print(f"✅ Python {sys.version.split()[0]}")
    return True

def check_imports():
    """Verify all Inscript modules can be imported."""
    try:
        from inscript import lexer, parser, interpreter
        print("✅ Inscript modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Inscript: {e}")
        return False

def run_simple_test():
    """Run a simple Inscript program."""
    try:
        from inscript.lexer import Lexer
        from inscript.parser import Parser
        from inscript.interpreter import Interpreter
        
        source = 'print("Inscript is working!")'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        interpreter = Interpreter()
        interpreter.interpret(ast)
        print("✅ Simple test executed successfully")
        return True
    except Exception as e:
        print(f"❌ Simple test failed: {e}")
        return False

def run_example():
    """Run an example program."""
    try:
        example_file = os.path.join(os.path.dirname(__file__), "examples", "fibonacci.is")
        if not os.path.exists(example_file):
            print(f"⚠️  Example file not found: {example_file}")
            return False
        
        from inscript.lexer import Lexer
        from inscript.parser import Parser
        from inscript.interpreter import Interpreter
        
        with open(example_file, 'r') as f:
            source = f.read()
        
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        interpreter = Interpreter()
        interpreter.interpret(ast)
        print("✅ Example program executed successfully")
        return True
    except Exception as e:
        print(f"⚠️  Example execution failed (non-critical): {e}")
        return True  # Don't fail on this

def main():
    print("=" * 50)
    print("Inscript Development Environment Check")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Module Imports", check_imports),
        ("Simple Test", run_simple_test),
        ("Example Program", run_example),
    ]
    
    results = []
    for name, check in checks:
        print(f"\n{name}:")
        result = check()
        results.append(result)
    
    print("\n" + "=" * 50)
    if all(results):
        print("✅ All checks passed! You're ready to develop.")
        print("\nNext steps:")
        print("1. Run an example: python inscript.py examples/hello.is")
        print("2. Start REPL: python inscript.py --repl")
        print("3. Run tests: python tests/test_interpreter.py")
        print("4. Read docs: See docs/LANGUAGE_SPEC.md")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
