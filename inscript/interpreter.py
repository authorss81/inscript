"""
Interpreter for Inscript language.
Executes AST nodes to run the program.
"""

from typing import Any, Dict, List, Optional
from .parser import *
from .builtins import builtin_functions

class ReturnValue(Exception):
    def __init__(self, value):
        self.value = value

class BreakException(Exception):
    pass

class ContinueException(Exception):
    pass

class Environment:
    """Represents a scope for variable bindings."""
    
    def __init__(self, parent: Optional['Environment'] = None):
        self.parent = parent
        self.variables: Dict[str, Any] = {}
    
    def define(self, name: str, value: Any):
        self.variables[name] = value
    
    def get(self, name: str) -> Any:
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.get(name)
        raise NameError(f"Undefined variable: {name}")
    
    def set(self, name: str, value: Any):
        if name in self.variables:
            self.variables[name] = value
        elif self.parent:
            self.parent.set(name, value)
        else:
            self.variables[name] = value

class InscriptFunction:
    """Represents a user-defined function."""
    
    def __init__(self, params: List[str], body: List[ASTNode], closure: Environment):
        self.params = params
        self.body = body
        self.closure = closure

class Interpreter:
    def __init__(self):
        self.global_env = Environment()
        self.current_env = self.global_env
        self._setup_builtins()
    
    def _setup_builtins(self):
        """Register built-in functions."""
        for name, func in builtin_functions.items():
            self.global_env.define(name, func)
    
    def interpret(self, program: Program) -> Any:
        """Execute the program."""
        result = None
        for statement in program.statements:
            result = self.evaluate(statement)
        return result
    
    def evaluate(self, node: ASTNode) -> Any:
        """Evaluate an AST node."""
        
        if isinstance(node, Program):
            result = None
            for stmt in node.statements:
                result = self.evaluate(stmt)
            return result
        
        elif isinstance(node, Number):
            return node.value
        
        elif isinstance(node, String):
            return node.value
        
        elif isinstance(node, Boolean):
            return node.value
        
        elif isinstance(node, Null):
            return None
        
        elif isinstance(node, ListLiteral):
            return [self.evaluate(elem) for elem in node.elements]
        
        elif isinstance(node, DictLiteral):
            result = {}
            for key_node, value_node in node.pairs:
                key = self.evaluate(key_node)
                value = self.evaluate(value_node)
                result[key] = value
            return result
        
        elif isinstance(node, Identifier):
            return self.current_env.get(node.name)
        
        elif isinstance(node, BinaryOp):
            return self.evaluate_binary_op(node)
        
        elif isinstance(node, UnaryOp):
            return self.evaluate_unary_op(node)
        
        elif isinstance(node, Assignment):
            value = self.evaluate(node.value)
            self.current_env.set(node.target, value)
            return value
        
        elif isinstance(node, FunctionDef):
            func = InscriptFunction(node.params, node.body, self.current_env)
            self.current_env.define(node.name, func)
            return None
        
        elif isinstance(node, FunctionCall):
            return self.evaluate_function_call(node)
        
        elif isinstance(node, MethodCall):
            return self.evaluate_method_call(node)
        
        elif isinstance(node, IfStatement):
            return self.evaluate_if_statement(node)
        
        elif isinstance(node, WhileStatement):
            return self.evaluate_while_statement(node)
        
        elif isinstance(node, ForStatement):
            return self.evaluate_for_statement(node)
        
        elif isinstance(node, ReturnStatement):
            value = None
            if node.value:
                value = self.evaluate(node.value)
            raise ReturnValue(value)
        
        elif isinstance(node, BreakStatement):
            raise BreakException()
        
        elif isinstance(node, ContinueStatement):
            raise ContinueException()
        
        elif isinstance(node, IndexAccess):
            obj = self.evaluate(node.obj)
            index = self.evaluate(node.index)
            return obj[index]
        
        elif isinstance(node, AttributeAccess):
            obj = self.evaluate(node.obj)
            if isinstance(obj, dict):
                return obj.get(node.attribute)
            return getattr(obj, node.attribute)
        
        else:
            raise RuntimeError(f"Unknown node type: {type(node)}")
    
    def evaluate_binary_op(self, node: BinaryOp) -> Any:
        left = self.evaluate(node.left)
        
        # Short-circuit evaluation for logical operators
        if node.operator == 'and':
            return left and self.evaluate(node.right)
        elif node.operator == 'or':
            return left or self.evaluate(node.right)
        
        right = self.evaluate(node.right)
        
        # Arithmetic
        if node.operator == '+':
            return left + right
        elif node.operator == '-':
            return left - right
        elif node.operator == '*':
            return left * right
        elif node.operator == '/':
            if right == 0:
                raise RuntimeError("Division by zero")
            return left / right
        elif node.operator == '%':
            return left % right
        elif node.operator == '**':
            return left ** right
        
        # Comparison
        elif node.operator == '==':
            return left == right
        elif node.operator == '!=':
            return left != right
        elif node.operator == '<':
            return left < right
        elif node.operator == '<=':
            return left <= right
        elif node.operator == '>':
            return left > right
        elif node.operator == '>=':
            return left >= right
        elif node.operator == 'is':
            return left is right
        
        else:
            raise RuntimeError(f"Unknown operator: {node.operator}")
    
    def evaluate_unary_op(self, node: UnaryOp) -> Any:
        operand = self.evaluate(node.operand)
        
        if node.operator == '-':
            return -operand
        elif node.operator == '+':
            return +operand
        elif node.operator == 'not':
            return not operand
        else:
            raise RuntimeError(f"Unknown unary operator: {node.operator}")
    
    def evaluate_function_call(self, node: FunctionCall) -> Any:
        func = self.current_env.get(node.name)
        args = [self.evaluate(arg) for arg in node.args]
        
        # Built-in function
        if callable(func) and not isinstance(func, InscriptFunction):
            return func(*args)
        
        # User-defined function
        if isinstance(func, InscriptFunction):
            if len(args) != len(func.params):
                raise RuntimeError(
                    f"Function {node.name} expects {len(func.params)} arguments, got {len(args)}"
                )
            
            # Create new environment for function execution
            func_env = Environment(func.closure)
            for param, arg in zip(func.params, args):
                func_env.define(param, arg)
            
            # Save current environment and switch to function environment
            prev_env = self.current_env
            self.current_env = func_env
            
            try:
                result = None
                for stmt in func.body:
                    result = self.evaluate(stmt)
                return result
            except ReturnValue as ret:
                return ret.value
            finally:
                self.current_env = prev_env
        
        raise RuntimeError(f"{node.name} is not callable")
    
    def evaluate_method_call(self, node: MethodCall) -> Any:
        obj = self.evaluate(node.obj)
        args = [self.evaluate(arg) for arg in node.args]
        
        # Built-in methods for strings, lists, dicts
        if isinstance(obj, str):
            method = getattr(obj, node.method, None)
            if method:
                return method(*args)
        
        elif isinstance(obj, list):
            if node.method == 'append':
                obj.append(args[0])
                return None
            elif node.method == 'remove':
                obj.remove(args[0])
                return None
            elif node.method == 'pop':
                return obj.pop(*args)
            elif node.method == 'length':
                return len(obj)
        
        elif isinstance(obj, dict):
            if node.method == 'keys':
                return list(obj.keys())
            elif node.method == 'values':
                return list(obj.values())
        
        raise RuntimeError(f"Object has no method {node.method}")
    
    def evaluate_if_statement(self, node: IfStatement) -> Any:
        condition = self.evaluate(node.condition)
        
        if self._is_truthy(condition):
            result = None
            for stmt in node.then_body:
                result = self.evaluate(stmt)
            return result
        
        # Check elseif conditions
        for elif_condition, elif_body in node.elseif_parts:
            condition = self.evaluate(elif_condition)
            if self._is_truthy(condition):
                result = None
                for stmt in elif_body:
                    result = self.evaluate(stmt)
                return result
        
        # Execute else body
        if node.else_body:
            result = None
            for stmt in node.else_body:
                result = self.evaluate(stmt)
            return result
        
        return None
    
    def evaluate_while_statement(self, node: WhileStatement) -> Any:
        result = None
        while self._is_truthy(self.evaluate(node.condition)):
            try:
                for stmt in node.body:
                    result = self.evaluate(stmt)
            except BreakException:
                break
            except ContinueException:
                continue
        return result
    
    def evaluate_for_statement(self, node: ForStatement) -> Any:
        iterable = self.evaluate(node.iterable)
        result = None
        
        for value in iterable:
            self.current_env.define(node.variable, value)
            try:
                for stmt in node.body:
                    result = self.evaluate(stmt)
            except BreakException:
                break
            except ContinueException:
                continue
        
        return result
    
    @staticmethod
    def _is_truthy(value: Any) -> bool:
        """Determine if a value is truthy."""
        if value is None or value is False:
            return False
        if value == 0 or value == "" or value == [] or value == {}:
            return False
        return True
