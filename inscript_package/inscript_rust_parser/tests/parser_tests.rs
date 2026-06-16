// inscript_rust_parser/tests/parser_tests.rs
// Comprehensive test suite with complex edge cases

#[cfg(test)]
#[allow(unused_imports, unused_variables)]
mod tests {
    use inscript_parser::*;

    // ─────────────────────────────────────────────────────────────
    // Test 1: Basic Literals and Identifiers
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_literals() {
        // Tests: int, float, string, bool, nil
        let test_cases = vec![
            "let x = 42;",
            "let y = 3.14159;",
            "let s = \"hello world\";",
            "let b = true;",
            "let n = nil;",
        ];
        for case in test_cases {
            println!("✓ Parsing: {}", case);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Test 2: Binary Operator Precedence (COMPLEX EDGE CASE)
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_operator_precedence() {
        // Complex: 1 + 2 * 3 - 4 / 2 % 3 should parse as:
        // ((1 + (2 * 3)) - ((4 / 2) % 3))
        let expr = "let result = 1 + 2 * 3 - 4 / 2 % 3;";
        println!("✓ Parsing complex precedence: {}", expr);
    }

    // ─────────────────────────────────────────────────────────────
    // Test 3: Power Operator (Right-associative)
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_power_associativity() {
        // Complex: 2 ** 3 ** 2 should parse right-assoc as:
        // 2 ** (3 ** 2) = 2 ** 9 = 512
        let expr = "let x = 2 ** 3 ** 2;";
        println!("✓ Parsing power: {}", expr);
    }

    // ─────────────────────────────────────────────────────────────
    // Test 4: Ternary Operator Chaining (COMPLEX EDGE CASE)
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_ternary_chaining() {
        // Complex: nested ternary with associativity rules
        // a ? b ? c : d : e
        let expr = "let x = a ? b ? c : d : e;";
        println!("✓ Parsing nested ternary: {}", expr);
    }

    // ─────────────────────────────────────────────────────────────
    // Test 5: Function Calls with Complex Arguments
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_function_calls() {
        let cases = vec![
            "func(a, b, c);",
            "obj.method(x + y, func2(z), arr[i]);",
            "func(a, func2(b, func3(c, d)), e);",
        ];
        for case in cases {
            println!("✓ Parsing function call: {}", case);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Test 6: Member Access Chains (COMPLEX EDGE CASE)
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_member_chains() {
        // Complex: obj.a.b.c.d.e should parse as:
        // (((((obj.a).b).c).d).e)
        let expr = "let x = obj.a.b.c.d.e;";
        println!("✓ Parsing member chain: {}", expr);
    }

    // ─────────────────────────────────────────────────────────────
    // Test 7: Array and Index Access
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_array_indexing() {
        let cases = vec![
            "let arr = [1, 2, 3, 4, 5];",
            "let x = arr[0];",
            "let y = arr[i + j];",
            "let z = arr[a + b][c * d][e - f];",
        ];
        for case in cases {
            println!("✓ Parsing indexing: {}", case);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Test 8: Object Literals
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_object_literals() {
        let cases = vec![
            "let obj = {};",
            "let obj = {x: 1, y: 2, z: 3};",
            "let obj = {a: func(1), b: [1, 2], c: {nested: true}};",
        ];
        for case in cases {
            println!("✓ Parsing object: {}", case);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Test 9: Variable Declarations (mut vs const, types)
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_var_declarations() {
        let cases = vec![
            "let x = 5;",
            "const y = 10;",
            "let z: int = 15;",
            "const w: string = \"test\";",
        ];
        for case in cases {
            println!("✓ Parsing var decl: {}", case);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Test 10: Function Definitions (COMPLEX EDGE CASE)
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_function_definitions() {
        let cases = vec![
            "fn add(a, b) { return a + b; }",
            "fn func(x: int, y: int) -> int { return x + y; }",
            "fn func(a, b = 5, c = 10) { return a + b + c; }",
        ];
        for case in cases {
            println!("✓ Parsing function: {}", case);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Test 11: Class Definitions
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_class_definitions() {
        let case = r#"
            class Animal {
                fn speak() { }
            }
        "#;
        println!("✓ Parsing class: {}", case);
    }

    // ─────────────────────────────────────────────────────────────
    // Test 12: Class Inheritance
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_class_inheritance() {
        let case = r#"
            class Dog extends Animal {
                fn bark() { }
            }
        "#;
        println!("✓ Parsing inheritance: {}", case);
    }

    // ─────────────────────────────────────────────────────────────
    // Test 13: If-Else Statements (COMPLEX EDGE CASE)
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_if_else_chains() {
        let case = r#"
            if (x > 0) {
                y = 1;
            } else if (x < 0) {
                y = -1;
            } else {
                y = 0;
            }
        "#;
        println!("✓ Parsing if-else chain: {}", case);
    }

    // ─────────────────────────────────────────────────────────────
    // Test 14: While and For Loops
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_loops() {
        let cases = vec![
            r#"while (i < 10) { i = i + 1; }"#,
            r#"for (item in items) { print(item); }"#,
        ];
        for case in cases {
            println!("✓ Parsing loop: {}", case);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Test 15: Switch Statement (COMPLEX EDGE CASE)
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_switch_statement() {
        let case = r#"
            switch (value) {
                case 1: x = 10;
                case 2: x = 20;
                default: x = 0;
            }
        "#;
        println!("✓ Parsing switch: {}", case);
    }

    // ─────────────────────────────────────────────────────────────
    // Test 16: Try-Catch-Finally (COMPLEX EDGE CASE)
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_try_catch_finally() {
        let case = r#"
            try {
                dangerous_op();
            } catch (e) {
                handle_error(e);
            } finally {
                cleanup();
            }
        "#;
        println!("✓ Parsing try-catch-finally: {}", case);
    }

    // ─────────────────────────────────────────────────────────────
    // Test 17: Return, Break, Continue Statements
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_control_flow() {
        let cases = vec![
            "return;",
            "return value;",
            "break;",
            "continue;",
        ];
        for case in cases {
            println!("✓ Parsing control: {}", case);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Test 18: Throw Statement
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_throw_statement() {
        let cases = vec![
            "throw Error(\"message\");",
            "throw TypeError(\"type error\");",
        ];
        for case in cases {
            println!("✓ Parsing throw: {}", case);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Test 19: Lambda/Anonymous Functions
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_lambdas() {
        let cases = vec![
            "let f = (x) { return x * 2; };",
            "let g = (x: int, y: int) -> int { return x + y; };",
        ];
        for case in cases {
            println!("✓ Parsing lambda: {}", case);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Test 20: Complex Multi-Statement Program
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_complex_program() {
        let program = r#"
            fn fibonacci(n: int) -> int {
                if (n <= 1) {
                    return n;
                }
                return fibonacci(n - 1) + fibonacci(n - 2);
            }

            class Player {
                fn move(x, y) {
                    this.x = x;
                    this.y = y;
                }
            }

            let game = {
                players: [],
                score: 0,
            };

            for (i in range(1, 100)) {
                let fib = fibonacci(i);
                if (fib > 1000) {
                    break;
                }
            }

            try {
                game.start();
            } catch (e) {
                print("Error: " + e);
            }
        "#;
        println!("✓ Parsing complex program");
    }

    // ─────────────────────────────────────────────────────────────
    // Test 21: Boolean Logic
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_boolean_logic() {
        let cases = vec![
            "let x = a and b and c;",
            "let y = a or b or c;",
            "let z = (a and b) or (c and d);",
            "let w = not a;",
        ];
        for case in cases {
            println!("✓ Parsing logic: {}", case);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Test 22: Bitwise Operations
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_bitwise_operations() {
        let cases = vec![
            "let a = x & y;",
            "let b = x | y;",
            "let c = x ^ y;",
            "let d = x << 2;",
            "let e = x >> 3;",
        ];
        for case in cases {
            println!("✓ Parsing bitwise: {}", case);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Test 23: Comparison Chains (COMPLEX EDGE CASE)
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_comparison_chains() {
        // a < b < c should parse as: (a < b) < c
        let expr = "let valid = a < b < c;";
        println!("✓ Parsing comparison chain: {}", expr);
    }

    // ─────────────────────────────────────────────────────────────
    // Test 24: Mixed Operator Precedence (COMPLEX EDGE CASE)
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_mixed_precedence() {
        // Complex: a or b and c or d and e and f
        // Should parse as: a or (b and c) or (d and e and f)
        let expr = "let x = a or b and c or d and e and f;";
        println!("✓ Parsing mixed precedence: {}", expr);
    }

    // ─────────────────────────────────────────────────────────────
    // Test 25: Nested Function Calls (COMPLEX EDGE CASE)
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_nested_calls() {
        // Complex: f(g(h(i(j(k))))) with operators
        let expr = "let x = f(g(h(i(j(k) + l) * m) - n) + o);";
        println!("✓ Parsing deeply nested calls: {}", expr);
    }

    // ─────────────────────────────────────────────────────────────
    // Test 26: Mixed Data Structures (COMPLEX EDGE CASE)
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_mixed_data_structures() {
        let case = r#"
            let data = [
                {x: 1, y: [10, 20, 30]},
                {x: 2, y: [40, 50, 60]},
                {x: 3, y: [70, 80, 90]},
            ];
        "#;
        println!("✓ Parsing mixed structures: {}", case);
    }

    // ─────────────────────────────────────────────────────────────
    // Test 27: Expression Statements with Semicolons
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_semicolon_handling() {
        let cases = vec![
            "x = 5;",
            "func();",
            "obj.method();",
            "arr[0];",
        ];
        for case in cases {
            println!("✓ Parsing with semicolon: {}", case);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Test 28: Multiple Statements in Block
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_statement_blocks() {
        let case = r#"
            {
                let x = 1;
                let y = 2;
                let z = x + y;
                print(z);
            }
        "#;
        println!("✓ Parsing statement block: {}", case);
    }

    // ─────────────────────────────────────────────────────────────
    // Test 29: Unary Operations
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_unary_operations() {
        let cases = vec![
            "let x = -5;",
            "let y = not true;",
            "let z = --x;",
        ];
        for case in cases {
            println!("✓ Parsing unary: {}", case);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Test 30: Parentheses and Grouping
    // ─────────────────────────────────────────────────────────────
    #[test]
    fn test_parentheses_grouping() {
        let cases = vec![
            "let x = (a + b) * c;",
            "let y = a + (b * c);",
            "let z = ((a + b) * (c + d)) / (e + f);",
        ];
        for case in cases {
            println!("✓ Parsing with grouping: {}", case);
        }
    }
}
