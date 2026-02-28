"""
Basic tests for Inscript interpreter.
Run with: python -m pytest tests/test_interpreter.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from inscript.lexer import Lexer, TokenType
from inscript.parser import Parser
from inscript.interpreter import Interpreter

def run_inscript(source: str):
    """Helper to run Inscript code and return result."""
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    interpreter = Interpreter()
    return interpreter.interpret(ast)

class TestBasics:
    def test_numbers(self):
        assert run_inscript("42") == 42
        assert run_inscript("3.14") == 3.14
    
    def test_strings(self):
        assert run_inscript('"hello"') == "hello"
        assert run_inscript('"hello" + " world"') == "hello world"
    
    def test_booleans(self):
        assert run_inscript("true") == True
        assert run_inscript("false") == False
    
    def test_arithmetic(self):
        assert run_inscript("10 + 5") == 15
        assert run_inscript("10 - 5") == 5
        assert run_inscript("10 * 5") == 50
        assert run_inscript("10 / 5") == 2.0
        assert run_inscript("10 % 3") == 1
        assert run_inscript("2 ** 3") == 8
    
    def test_comparison(self):
        assert run_inscript("5 == 5") == True
        assert run_inscript("5 != 5") == False
        assert run_inscript("5 < 10") == True
        assert run_inscript("5 > 10") == False
        assert run_inscript("5 <= 5") == True
        assert run_inscript("5 >= 5") == True
    
    def test_logical(self):
        assert run_inscript("true and true") == True
        assert run_inscript("true and false") == False
        assert run_inscript("true or false") == True
        assert run_inscript("not true") == False
        assert run_inscript("not false") == True

class TestVariables:
    def test_assignment(self):
        code = """
        x = 42
        x
        """
        assert run_inscript(code) == 42
    
    def test_multiple_assignments(self):
        code = """
        x = 10
        y = 20
        x + y
        """
        assert run_inscript(code) == 30

class TestLists:
    def test_list_creation(self):
        assert run_inscript("[1, 2, 3]") == [1, 2, 3]
    
    def test_list_indexing(self):
        assert run_inscript("[10, 20, 30][0]") == 10
        assert run_inscript("[10, 20, 30][2]") == 30

class TestDictionaries:
    def test_dict_creation(self):
        result = run_inscript('{"name": "Alice", "age": 30}')
        assert result["name"] == "Alice"
        assert result["age"] == 30
    
    def test_dict_indexing(self):
        assert run_inscript('{"x": 42}["x"]') == 42

class TestFunctions:
    def test_simple_function(self):
        code = """
        function add(a, b):
        {
            return a + b
        }
        add(10, 20)
        """
        assert run_inscript(code) == 30
    
    def test_fibonacci(self):
        code = """
        function fib(n):
        {
            if n <= 1:
                return n
            else:
                return fib(n - 1) + fib(n - 2)
        }
        fib(6)
        """
        assert run_inscript(code) == 8

class TestControlFlow:
    def test_if_then(self):
        code = """
        if true:
        {
            42
        }
        """
        assert run_inscript(code) == 42
    
    def test_if_else(self):
        code = """
        if false:
        {
            0
        }
        else:
        {
            42
        }
        """
        assert run_inscript(code) == 42

class TestBuiltins:
    def test_length(self):
        assert run_inscript('length([1, 2, 3])') == 3
        assert run_inscript('length("hello")') == 5
    
    def test_range(self):
        assert run_inscript('range(3)') == [0, 1, 2]
        assert run_inscript('range(1, 4)') == [1, 2, 3]
    
    def test_type(self):
        assert run_inscript('type(42)') == 'int'
        assert run_inscript('type("hello")') == 'str'
        assert run_inscript('type([])') == 'list'

if __name__ == '__main__':
    # Run tests manually
    test_basics = TestBasics()
    test_basics.test_numbers()
    test_basics.test_strings()
    test_basics.test_arithmetic()
    print("✓ Basic tests passed")
    
    test_vars = TestVariables()
    test_vars.test_assignment()
    print("✓ Variable tests passed")
    
    test_lists = TestLists()
    test_lists.test_list_creation()
    print("✓ List tests passed")
    
    test_funcs = TestFunctions()
    test_funcs.test_simple_function()
    print("✓ Function tests passed")
    
    test_control = TestControlFlow()
    test_control.test_if_then()
    print("✓ Control flow tests passed")
    
    test_builtins = TestBuiltins()
    test_builtins.test_length()
    print("✓ Built-in tests passed")
    
    print("\n✅ All tests passed!")
