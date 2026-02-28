#!/usr/bin/env python3
"""
Command-line interface for Inscript language interpreter.
Allows running inscript from command line after pip install.
"""

import sys
import os
from pathlib import Path

from .interpreter import Interpreter
from .lexer import Lexer
from .parser import Parser


def print_version():
    """Print Inscript version."""
    print("Inscript v0.2.0")
    print("A Python-like interpreted programming language")


def print_help():
    """Print help message."""
    print_version()
    print("\nUsage:")
    print("  inscript <script.is>              Run an Inscript script")
    print("  inscript --repl                   Start interactive REPL")
    print("  inscript --version                Show version")
    print("  inscript --help                   Show this help message")
    print("\nExamples:")
    print("  inscript examples/hello.is")
    print("  inscript")
    print("  inscript --repl")


def run_repl():
    """Run interactive REPL (Read-Eval-Print Loop)."""
    interpreter = Interpreter()
    print_version()
    print("\nWelcome to Inscript interactive mode!")
    print("Type 'exit' or 'quit' to exit, 'help' for commands.\n")

    while True:
        try:
            source = input(">>> ")

            if not source.strip():
                continue

            if source.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            if source.lower() == "help":
                print("\nInscript commands:")
                print("  exit, quit     - Exit the REPL")
                print("  help           - Show this message")
                print("\nEnter Inscript code to execute.\n")
                continue

            lexer = Lexer(source)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast = parser.parse()
            result = interpreter.evaluate(ast)

            if result is not None:
                print(result)

        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'exit' to quit.")
        except Exception as e:
            print(f"Error: {e}")


def run_file(filename):
    """Run an Inscript script file."""
    # Handle relative and absolute paths
    filepath = Path(filename)

    if not filepath.exists():
        print(f"Error: File '{filename}' not found")
        sys.exit(1)

    if not filepath.suffix == ".is":
        print(f"Warning: File doesn't have .is extension")

    try:
        source = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        interpreter = Interpreter()
        interpreter.evaluate(ast)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    """Main entry point for CLI."""
    if len(sys.argv) == 1:
        # No arguments - start REPL
        run_repl()
    elif len(sys.argv) == 2:
        arg = sys.argv[1]

        if arg in ["--help", "-h", "help"]:
            print_help()
        elif arg in ["--version", "-v", "version"]:
            print_version()
        elif arg in ["--repl", "repl"]:
            run_repl()
        else:
            # Assume it's a script file
            run_file(arg)
    else:
        print("Error: Unexpected number of arguments")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
