// inscript_v380/error_recovery/advanced_error_recovery.py
# Advanced Error Recovery & Diagnostics for InScript
# Features:
#   - Error classification and severity levels
#   - Automatic error recovery strategies
#   - Detailed diagnostic information
#   - Error context tracking
#   - Recovery suggestion engine

import traceback
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Callable
import sys

class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4

class ErrorCategory(Enum):
    """Error categories for better handling"""
    SYNTAX = "syntax"
    TYPE = "type"
    RUNTIME = "runtime"
    MEMORY = "memory"
    PERMISSION = "permission"
    IO = "io"
    LOGIC = "logic"
    STACK_OVERFLOW = "stack_overflow"
    RECURSION = "recursion"
    UNDEFINED = "undefined"
    ZERO_DIVISION = "zero_division"
    INDEX_OUT_OF_BOUNDS = "index_out_of_bounds"
    KEY_ERROR = "key_error"
    TYPE_MISMATCH = "type_mismatch"

@dataclass
class ErrorContext:
    """Rich error context information"""
    file: str
    line: int
    column: int
    function: str
    code_line: str
    surrounding_lines: List[str]
    stack_trace: List[str]
    variables_at_error: Dict[str, Any]
    
    def format(self) -> str:
        """Format context for display"""
        lines = [
            f"File: {self.file}:{self.line}:{self.column}",
            f"Function: {self.function}",
            "",
            "Code context:",
            *self.surrounding_lines,
            "",
            "Code:",
            self.code_line,
        ]
        return "\n".join(lines)

@dataclass
class ErrorDiagnostic:
    """Complete error diagnostic information"""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    context: ErrorContext
    recovery_suggestions: List[str]
    related_errors: List['ErrorDiagnostic']
    
    def format_full(self) -> str:
        """Format complete diagnostic"""
        lines = [
            f"{'='*70}",
            f"{self.severity.name}: {self.category.value.upper()}",
            f"{'='*70}",
            "",
            self.message,
            "",
            self.context.format(),
        ]
        
        if self.recovery_suggestions:
            lines.extend([
                "",
                "Recovery suggestions:",
                *[f"  • {s}" for s in self.recovery_suggestions],
            ])
        
        if self.related_errors:
            lines.extend([
                "",
                "Related errors:",
                *[f"  • {e.message}" for e in self.related_errors],
            ])
        
        return "\n".join(lines)

class ErrorRecoveryEngine:
    """Advanced error recovery and diagnostics"""
    
    def __init__(self):
        self.errors: List[ErrorDiagnostic] = []
        self.recovery_strategies: Dict[ErrorCategory, List[Callable]] = {}
        self.error_history: List[ErrorDiagnostic] = []
        self._setup_recovery_strategies()
    
    def _setup_recovery_strategies(self):
        """Setup error recovery strategies"""
        self.recovery_strategies = {
            ErrorCategory.SYNTAX: [
                self._recover_syntax_error,
                self._suggest_similar_keywords,
            ],
            ErrorCategory.TYPE: [
                self._recover_type_error,
                self._suggest_type_conversion,
            ],
            ErrorCategory.UNDEFINED: [
                self._recover_undefined_variable,
                self._suggest_defined_variables,
            ],
            ErrorCategory.ZERO_DIVISION: [
                self._recover_zero_division,
                self._suggest_division_check,
            ],
            ErrorCategory.INDEX_OUT_OF_BOUNDS: [
                self._recover_index_error,
                self._suggest_bounds_check,
            ],
            ErrorCategory.RECURSION: [
                self._recover_recursion,
                self._suggest_max_depth_increase,
            ],
            ErrorCategory.STACK_OVERFLOW: [
                self._recover_stack_overflow,
                self._suggest_memory_optimization,
            ],
        }
    
    def capture_error(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity,
        message: str,
        file: str,
        line: int,
        column: int,
        function: str,
        code_line: str,
        surrounding_lines: List[str],
        variables_at_error: Optional[Dict[str, Any]] = None,
    ) -> ErrorDiagnostic:
        """Capture and process error with full context"""
        
        context = ErrorContext(
            file=file,
            line=line,
            column=column,
            function=function,
            code_line=code_line,
            surrounding_lines=surrounding_lines,
            stack_trace=self._capture_stack(),
            variables_at_error=variables_at_error or {},
        )
        
        suggestions = self._generate_recovery_suggestions(category, message, context)
        related = self._find_related_errors(category)
        
        diagnostic = ErrorDiagnostic(
            category=category,
            severity=severity,
            message=message,
            context=context,
            recovery_suggestions=suggestions,
            related_errors=related,
        )
        
        self.errors.append(diagnostic)
        self.error_history.append(diagnostic)
        
        return diagnostic
    
    def _capture_stack(self) -> List[str]:
        """Capture current stack trace"""
        return traceback.format_stack()[:-1]
    
    def _generate_recovery_suggestions(
        self,
        category: ErrorCategory,
        message: str,
        context: ErrorContext,
    ) -> List[str]:
        """Generate recovery suggestions based on error"""
        suggestions = []
        
        strategies = self.recovery_strategies.get(category, [])
        for strategy in strategies:
            result = strategy(message, context)
            if result:
                suggestions.append(result)
        
        return suggestions
    
    def _find_related_errors(self, category: ErrorCategory) -> List[ErrorDiagnostic]:
        """Find related errors from history"""
        return [
            e for e in self.error_history[-10:]
            if e.category == category and e != self.errors[-1] if self.errors
        ]
    
    # Recovery strategies
    def _recover_syntax_error(self, message: str, context: ErrorContext) -> Optional[str]:
        """Suggest syntax error recovery"""
        if "expected" in message.lower():
            return "Check parentheses, brackets, and braces are balanced"
        if "unexpected" in message.lower():
            return f"Remove unexpected token on line {context.line}"
        return None
    
    def _suggest_similar_keywords(self, message: str, context: ErrorContext) -> Optional[str]:
        """Suggest similar keywords"""
        keywords = {"if", "else", "while", "for", "fn", "class", "return", "break"}
        words = context.code_line.split()
        for word in words:
            if word not in keywords and len(word) > 2:
                similar = self._find_similar(word, keywords)
                if similar:
                    return f"Did you mean '{similar}' instead of '{word}'?"
        return None
    
    def _recover_type_error(self, message: str, context: ErrorContext) -> Optional[str]:
        """Suggest type error recovery"""
        return "Ensure variable is the correct type before operation"
    
    def _suggest_type_conversion(self, message: str, context: ErrorContext) -> Optional[str]:
        """Suggest type conversion"""
        if "int" in message.lower():
            return "Try converting to int: int(value)"
        if "string" in message.lower():
            return "Try converting to string: str(value)"
        if "float" in message.lower():
            return "Try converting to float: float(value)"
        return None
    
    def _recover_undefined_variable(self, message: str, context: ErrorContext) -> Optional[str]:
        """Suggest undefined variable recovery"""
        return "Check variable is defined before use"
    
    def _suggest_defined_variables(self, message: str, context: ErrorContext) -> Optional[str]:
        """Suggest similar defined variables"""
        undefined_var = self._extract_variable_name(message)
        if undefined_var and context.variables_at_error:
            similar = self._find_similar(undefined_var, context.variables_at_error.keys())
            if similar:
                return f"Did you mean '{similar}' instead of '{undefined_var}'?"
        return None
    
    def _recover_zero_division(self, message: str, context: ErrorContext) -> Optional[str]:
        """Suggest zero division recovery"""
        return "Add check: if divisor != 0 before division"
    
    def _suggest_division_check(self, message: str, context: ErrorContext) -> Optional[str]:
        """Suggest division check pattern"""
        return "Use pattern: if y != 0 { result = x / y } else { result = nil }"
    
    def _recover_index_error(self, message: str, context: ErrorContext) -> Optional[str]:
        """Suggest index error recovery"""
        return "Check index is within array bounds (0 <= index < length)"
    
    def _suggest_bounds_check(self, message: str, context: ErrorContext) -> Optional[str]:
        """Suggest bounds check"""
        return "Use safe indexing: arr[i] if i >= 0 && i < arr.length"
    
    def _recover_recursion(self, message: str, context: ErrorContext) -> Optional[str]:
        """Suggest recursion recovery"""
        return "Add base case to stop recursion"
    
    def _suggest_max_depth_increase(self, message: str, context: ErrorContext) -> Optional[str]:
        """Suggest max depth increase"""
        return "Increase max recursion depth or refactor to iteration"
    
    def _recover_stack_overflow(self, message: str, context: ErrorContext) -> Optional[str]:
        """Suggest stack overflow recovery"""
        return "Optimize memory usage or increase stack size"
    
    def _suggest_memory_optimization(self, message: str, context: ErrorContext) -> Optional[str]:
        """Suggest memory optimization"""
        return "Profile memory usage and optimize hot paths"
    
    # Utilities
    def _find_similar(self, target: str, candidates: Any) -> Optional[str]:
        """Find similar string using edit distance"""
        if isinstance(candidates, dict):
            candidates = list(candidates.keys())
        
        def edit_distance(s1: str, s2: str) -> int:
            if len(s1) < len(s2):
                return edit_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)
            
            prev_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                curr_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = prev_row[j + 1] + 1
                    deletions = curr_row[j] + 1
                    substitutions = prev_row[j] + (0 if c1 == c2 else 1)
                    curr_row.append(min(insertions, deletions, substitutions))
                prev_row = curr_row
            return prev_row[-1]
        
        distances = [(edit_distance(target, c), c) for c in candidates]
        closest = min(distances, default=(999, None))
        
        if closest[0] <= 2:  # Allow up to 2 edit distance
            return closest[1]
        return None
    
    def _extract_variable_name(self, message: str) -> Optional[str]:
        """Extract variable name from error message"""
        if "'" in message:
            parts = message.split("'")
            if len(parts) >= 2:
                return parts[1]
        return None
    
    def print_all_errors(self):
        """Print all captured errors"""
        if not self.errors:
            print("No errors captured.")
            return
        
        for i, error in enumerate(self.errors, 1):
            print(f"\n{'='*70}")
            print(f"Error {i}/{len(self.errors)}")
            print(error.format_full())
    
    def get_summary(self) -> Dict[str, Any]:
        """Get error summary statistics"""
        return {
            "total_errors": len(self.errors),
            "by_severity": {
                s.name: len([e for e in self.errors if e.severity == s])
                for s in ErrorSeverity
            },
            "by_category": {
                c.name: len([e for e in self.errors if e.category == c])
                for c in ErrorCategory
            },
        }

# Global error recovery engine
_error_engine = ErrorRecoveryEngine()

def capture_error(
    category: ErrorCategory,
    severity: ErrorSeverity,
    message: str,
    **kwargs
) -> ErrorDiagnostic:
    """Capture error with context"""
    return _error_engine.capture_error(
        category=category,
        severity=severity,
        message=message,
        **kwargs
    )

def get_error_engine() -> ErrorRecoveryEngine:
    """Get global error engine"""
    return _error_engine

# Example usage
if __name__ == "__main__":
    engine = ErrorRecoveryEngine()
    
    # Simulate error capture
    diag = engine.capture_error(
        category=ErrorCategory.UNDEFINED,
        severity=ErrorSeverity.ERROR,
        message="Undefined variable 'x'",
        file="script.ins",
        line=42,
        column=10,
        function="calculate",
        code_line="  result = x + y",
        surrounding_lines=["  let y = 10", "  result = x + y", "  return result"],
        variables_at_error={"y": 10, "result": None},
    )
    
    print(diag.format_full())
    print("\nSummary:", engine.get_summary())
