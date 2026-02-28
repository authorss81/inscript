#!/usr/bin/env python3
"""
Inscript - A clean, Python-like interpreted programming language.
Focus: Language feel, clarity, and developer happiness.
"""

import sys
import os
from inscript.lexer import Lexer
from inscript.parser import Parser
from inscript.interpreter import Interpreter

def run_file(filename: str):
    """Run an Inscript file."""
    try:
        with open(filename, 'r') as f:
            source = f.read()
        run_source(source)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def run_source(source: str):
    """Run Inscript source code."""
    try:
        # Lexical analysis
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        # Parsing
        parser = Parser(tokens)
        ast = parser.parse()
        
        # Interpretation
        interpreter = Interpreter()
        interpreter.interpret(ast)
    
    except SyntaxError as e:
        print(f"Syntax Error: {e}")
        sys.exit(1)
    except NameError as e:
        print(f"Name Error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"Runtime Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def repl():
    """Start an interactive REPL."""
    print("Inscript 0.1.0 - Interactive Mode")
    print("Type 'exit' or 'quit' to exit")
    print("-" * 40)
    
    interpreter = Interpreter()
    
    while True:
        try:
            source = input(">>> ")
            if source.lower() in ('exit', 'quit'):
                print("Goodbye!")
                break
            
            if not source.strip():
                continue
            
            # Lexical analysis
            lexer = Lexer(source)
            tokens = lexer.tokenize()
            
            # Parsing
            parser = Parser(tokens)
            ast = parser.parse()
            
            # Interpretation
            result = interpreter.interpret(ast)
            if result is not None:
                print(result)
        
        except SyntaxError as e:
            print(f"Syntax Error: {e}")
        except NameError as e:
            print(f"Name Error: {e}")
        except RuntimeError as e:
            print(f"Runtime Error: {e}")
        except KeyboardInterrupt:
            print("\nKeyboardInterrupt")
        except Exception as e:
            print(f"Error: {e}")

def main():
    if len(sys.argv) < 2:
        print("Inscript 0.1.0")
        print("Usage: inscript <script.is> or inscript --repl")
        sys.exit(0)
    
    if sys.argv[1] in ('--repl', '-i', 'repl'):
        repl()
    else:
        run_file(sys.argv[1])

if __name__ == '__main__':
    main()
