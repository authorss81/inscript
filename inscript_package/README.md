# InScript Lexer - Rust Implementation (v3.7.2)

**Real, compilable Rust tokenizer** for InScript language.

## Features

✅ Zero-copy token references (fast, memory efficient)
✅ State machine lexer (no backtracking)
✅ 30+ token types (keywords, operators, literals)
✅ Accurate line/column tracking
✅ Comprehensive error reporting
✅ Python FFI via PyO3
✅ Full test coverage

## Build

```bash
cargo build --release
```

## Token Types Supported

### Literals
- Numbers (integers and floats)
- Strings (single and double quoted)
- Identifiers

### Keywords
- if, else, while, for, fn, return
- true, false, nil
- and, or, not

### Operators
- Arithmetic: +, -, *, /, %
- Comparison: ==, !=, <, <=, >, >=
- Assignment: =
- Logical: and, or, not

### Delimiters
- Parentheses: ( )
- Braces: { }
- Brackets: [ ]
- Punctuation: , . ; : ->

## Rust Usage

```rust
use inscript_lexer::Lexer;

fn main() {
    let code = "let x = 42;";
    let lexer = Lexer::new(code);
    
    for token in lexer {
        match token {
            Ok(t) => println!("{:?}: {}", t.token_type, t.value),
            Err(e) => eprintln!("Error: {}", e),
        }
    }
}
```

## Python Usage (after compilation)

```python
from inscript_lexer import PyLexer, tokenize_string

# Method 1: Using PyLexer class
lexer = PyLexer("let x = 42;")
tokens = lexer.tokens()
print(f"Found {lexer.count()} tokens")

# Method 2: Direct tokenization
tokens = tokenize_string("if true then x else y")
for token in tokens:
    print(f"{token.token_type}: {token.value}")
```

## Performance

### Expected Benchmarks
- Simple tokens: < 100ns per token
- Complex code: < 10µs per 100 tokens
- Memory: O(1) per token

### Optimizations
- Inline hot paths
- No allocations in common cases
- SIMD-friendly string scanning
- Zero-copy string references

## Testing

```bash
# Run tests
cargo test

# Run with output
cargo test -- --nocapture

# Benchmark
cargo bench
```

## Accuracy

✅ Correct line/column tracking
✅ Handles escape sequences
✅ Detects unterminated strings
✅ Error recovery

## License

MIT

