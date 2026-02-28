# Inscript - A Clean Python-Like Programming Language

Inscript is an interpreted programming language designed with three core principles:
- **Language Feel**: Intuitive and pleasant to write
- **Clarity**: Code should be easy to understand
- **Developer Happiness**: Focus on reducing friction

It features English-style keywords, clean syntax inspired by Python, and a focus on readability.

## Quick Start

### Installation

**Option 1: Install via pip (Recommended)**
```bash
pip install inscript
inscript examples/hello.is
```

**Option 2: VS Code Extension (Coming Soon)**
- Search for "Inscript" in VS Code Extensions marketplace
- Click Install
- Use keyboard shortcut `Ctrl+Alt+I` to run scripts directly from editor
- Full syntax highlighting and integrated terminal support

**Option 3: Run from Source**
```bash
# Clone or download the repository
cd inscript

# Run a program
python inscript.py examples/hello.is

# Interactive mode
python inscript.py --repl

# For pip-like behavior, add to PATH or use batch file
# (See Development Setup section below)
```

### First Script

**Create hello.is:**
```inscript
print("Hello, Inscript!")
```

**Run it:**
```bash
# Via pip
inscript hello.is

# Or from source
python inscript.py hello.is
```

## Language Features

### Clean Syntax
```inscript
# Variables
name = "Alice"
age = 30

# If statements
if age >= 18:
{
    print(name + " is an adult")
}

# Loops
for i in range(10):
{
    print(i)
}

# Functions
function greet(person):
{
    return "Hello, " + person
}

result = greet("World")
```

### Data Types
- **Numbers**: `42`, `3.14`
- **Strings**: `"hello"`
- **Booleans**: `true`, `false`
- **Lists**: `[1, 2, 3]`
- **Dictionaries**: `{"name": "Alice"}`
- **Null**: `null`

### Built-in Functions
- I/O: `print()`, `input()`
- Type conversion: `int()`, `float()`, `string()`, `list()`, `dict()`
- Collections: `length()`, `keys()`, `values()`, `sort()`, `reverse()`
- **String functions (20+)**: `upper()`, `lower()`, `split()`, `join()`, `strip()`, `replace()`, `find()`, `startswith()`, `endswith()`, `isdigit()`, `isalpha()`, etc.
- **List functions (15+)**: `append()`, `insert()`, `remove()`, `pop()`, `copy()`, `extend()`, `unique()`, `flatten()`, `slice_list()`, `zip()`, etc.
- **Math functions (20+)**: `sqrt()`, `sin()`, `cos()`, `log()`, `ceil()`, `floor()`, `gcd()`, `factorial()`, `pi()`, `e()`, etc.
- **Dictionary functions (5+)**: `get()`, `pop_dict()`, `update()`, `has_key()`
- **File I/O (5+)**: `read()`, `write()`, `append_text()`, `readlines()`, `file_exists()`, `delete_file()`
- **Random (6+)**: `random()`, `randint()`, `choice()`, `sample()`, `shuffle()`, `seed()`
- **JSON (2+)**: `to_json()`, `from_json()`
- **Date/Time (5+)**: `now()`, `timestamp()`, `year()`, `month()`, `day()`
- **Type Checking (8+)**: `is_int()`, `is_float()`, `is_string()`, `is_list()`, `is_dict()`, `is_null()`, `type()`
- **Utilities (15+)**: `any()`, `all()`, `enumerate()`, `range()`, `abs()`, `round()`, `power()`, `ascii()`, `chr()`, `hash()`, `wait()`, etc.

**Total: 100+ built-in functions**

### Control Flow
- **if/elseif/else**: Conditional execution
- **while**: Loop while condition is true
- **for**: Iterate over sequences
- **break/continue**: Control loop flow
- **return**: Return from function

### Functions
```inscript
function fibonacci(n):
{
    if n <= 1:
        return n
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)
}
```

## Examples

See the `examples/` directory:
- `hello.is` - Hello World program
- `conditionals.is` - If/elseif/else statements
- `loops.is` - While and for loops
- `data_structures.is` - Lists and dictionaries
- `fibonacci.is` - Recursive functions
- `statistics.is` - Statistical calculations with lists
- `prime_finder.is` - Prime number analysis and patterns
- `string_analyzer.is` - String manipulation and character analysis
- `list_algorithms.is` - Advanced list operations (sort, filter, chunk, etc.)
- `json_random.is` - Random numbers and JSON processing
- `file_operations.is` - File reading, writing, and manipulation
- `string_utils.is` - String utility functions library
- `math_utils.is` - Mathematical utility functions
- `list_utils.is` - Advanced list utility functions

## Project Structure

```
inscript/
├── inscript/              # Main package
│   ├── __init__.py       # Package initialization
│   ├── lexer.py          # Tokenizer (lexical analysis)
│   ├── parser.py         # Parser (syntax analysis)
│   ├── interpreter.py    # Interpreter (execution)
│   └── builtins.py       # Built-in functions
├── inscript.py           # CLI entry point
├── examples/             # Example programs
│   ├── hello.is
│   ├── fibonacci.is
│   ├── loops.is
│   ├── conditionals.is
│   └── data_structures.is
├── tests/                # Test suite
├── docs/                 # Documentation
│   └── LANGUAGE_SPEC.md  # Full language specification
└── README.md             # This file
```

## Architecture

Inscript uses a classic three-stage interpreter architecture:

1. **Lexer** (`lexer.py`): Tokenizes source code into a stream of tokens
2. **Parser** (`parser.py`): Converts tokens into an Abstract Syntax Tree (AST)
3. **Interpreter** (`interpreter.py`): Walks the AST and executes the program

### Files

- **lexer.py**: 
  - `Lexer` class: Main tokenizer
  - `Token` dataclass: Represents individual tokens
  - `TokenType` enum: All token types

- **parser.py**:
  - `Parser` class: Converts tokens to AST
  - AST Node classes: `BinaryOp`, `FunctionDef`, `IfStatement`, etc.

- **interpreter.py**:
  - `Interpreter` class: Executes AST nodes
  - `Environment` class: Manages variable scopes
  - `InscriptFunction` class: User-defined functions

- **builtins.py**:
  - Built-in functions available to Inscript programs

## Command Line Interface

### Run a program file
```bash
python inscript.py <filename.is>
```

### Start interactive REPL
```bash
python inscript.py --repl
# or
python inscript.py -i
```

### View help
```bash
python inscript.py
```

## Features Implemented

✅ Variables and assignment
✅ All primitive data types
✅ Lists and dictionaries
✅ Arithmetic operators
✅ Comparison operators
✅ Logical operators
✅ If/elseif/else statements
✅ While loops
✅ For loops
✅ Functions
✅ Built-in functions (25+)
✅ REPL (Read-Eval-Print Loop)
✅ Comments

## Planned Features

- Classes and objects
- Module/import system
- Exception handling (try/catch/finally)
- Lambda functions
- List comprehensions
- Decorators
- Multiple file support
- File I/O operations
- More string methods
- First-class functions
- Closure support

## Design Principles

### 1. Language Feel
The language should be pleasant and intuitive to write. Keywords are English words that clearly express intent.

### 2. Clarity
Code written in Inscript should be self-documenting. We prioritize readability over cleverness.

### 3. Developer Happiness
The language removes unnecessary friction:
- Simple, predictable syntax
- Helpful error messages
- Quick feedback loop (REPL)
- Extensive documentation
- Practical built-in functions

## Getting Started with Development

### Understanding the Code

1. Start with `lexer.py` to understand tokenization
2. Move to `parser.py` to see AST construction
3. Study `interpreter.py` to see execution
4. Check `builtins.py` for available functions

### Running Examples

```bash
# Run each example to see the language in action
python inscript.py examples/hello.is
python inscript.py examples/conditionals.is
python inscript.py examples/loops.is
python inscript.py examples/data_structures.is
python inscript.py examples/fibonacci.is
python inscript.py examples/statistics.is              # Statistics
python inscript.py examples/prime_finder.is           # Prime numbers
python inscript.py examples/string_analyzer.is        # String analysis
python inscript.py examples/list_algorithms.is        # List operations
python inscript.py examples/json_random.is            # JSON & Random
```

### Writing Your First Program

Create a new file `myprogram.is`:

```inscript
# Say hello
print("Welcome to Inscript!")

# Simple calculation
sum = 10 + 20
print("10 + 20 = " + string(sum))

# Lists
numbers = [1, 2, 3, 4, 5]
for num in numbers:
{
    print(num)
}
```

Run it:
```bash
python inscript.py myprogram.is
```

## Contributing

This is an open-source language project. Areas for contribution:

1. **Core Features**: Implement planned features
2. **Built-in Functions**: Add more standard library functions
3. **Documentation**: Write guides and tutorials
4. **Examples**: Create interesting example programs
5. **Testing**: Write comprehensive test suite
6. **Performance**: Optimize interpreter
7. **VS Code Extension**: Syntax highlighting, debugging support

## Publishing for VS Code

### VS Code Extension

The Inscript VS Code extension provides:
- ✨ Syntax highlighting for `.is` files
- 🚀 Run scripts with keyboard shortcuts (`Ctrl+Alt+I`)
- 🔧 Terminal integration for interactive debugging
- 💻 REPL integration for live coding

**See `vscode-extension/README.md` for detailed instructions on:**
- Installing from source
- Publishing to marketplace
- Development workflow
- Building distribution packages

### Development Setup

#### Setting up for Local Development

```bash
# Clone the repository
git clone https://github.com/YourUsername/inscript.git
cd inscript

# Install Python dependencies (none required!)
# Python 3.8+ is the only requirement

# Install locally in editable mode
pip install -e .

# Now inscript command works everywhere
inscript examples/hello.is
```

#### Building the pip Package

```bash
# Install build tools
pip install build twine

# Build distribution
python -m build

# Upload to PyPI (requires account)
python -m twine upload dist/*
```

#### Developing the VS Code Extension

```bash
# Install Node.js dependencies
cd vscode-extension
npm install

# Start development mode
npm run esbuild-watch

# Test the extension (F5 in VS Code)
# Package for distribution
npm run vscode:prepublish

# Create VSIX package
npx vsce package

# Publish to marketplace
npx vsce publish
```

## Distribution & Installation Methods

Inscript is available through multiple channels:

| Method | Install Command | Best For |
|--------|-----------------|----------|
| **pip** | `pip install inscript` | Python developers, system scripts |
| **VS Code** | Search Extensions for "Inscript" | VS Code users, interactive development |
| **GitHub** | `git clone ...` | Contributing, latest source code |
| **Standalone** | Download `.exe` from releases | No Python required (Windows) |
| **Docker** | `docker pull inscript:latest` | Cloud, reproducible environments |

## Requirements

- **Runtime**: Python 3.8 or higher
- **For VS Code Extension**: VS Code 1.70.0+
- **For Development**: Node.js 14+ (for VS Code extension only)

## Package Structure

```
inscript/
├── inscript/                    # Core language package
│   ├── __init__.py             # Package initialization
│   ├── cli.py                  # Command-line interface
│   ├── lexer.py                # Tokenization
│   ├── parser.py               # AST parsing
│   ├── interpreter.py          # Code execution
│   └── builtins.py             # Built-in functions (100+)
├── vscode-extension/           # VS Code extension
│   ├── extension.js            # Extension logic
│   ├── package.json            # Extension metadata
│   ├── syntaxes/inscript.json  # Syntax highlighting
│   └── README.md               # Extension documentation
├── examples/                   # Sample programs (11 total)
├── docs/                       # Documentation
│   ├── LANGUAGE_SPEC.md        # Language specification
│   └── STDLIB.md               # Standard library reference
├── setup.py                    # pip package configuration
├── inscript.py                 # Legacy entry point
└── README.md                   # This file
```

## Roadmap

### Current (v0.2.0)
- ✅ Core language with 100+ built-in functions
- ✅ Complete REPL
- ✅ pip package distribution
- ✅ VS Code extension with syntax highlighting and execution
- ✅ Comprehensive standard library
- ✅ 11 example programs

### Next (v0.3.0)
- 🔄 Classes and OOP support
- 🔄 Exception handling (try/catch)
- 🔄 Lambda functions
- 🔄 List comprehensions
- 🔄 Module/import system

### Future (v1.0.0)
- Regular expressions
- Async/await
- Generators
- Pattern matching
- Full VS Code debugging support
- Performance optimization

Future roadmap includes:
1. Syntax highlighting extension
2. Language server protocol (LSP) support
3. Debugging support
4. One-click installation from VS Code Marketplace

## License

[Specify your chosen license here]

## Author

Created with focus on developer happiness.

## Resources

For detailed information:
- **Complete Language Spec**: [docs/LANGUAGE_SPEC.md](docs/LANGUAGE_SPEC.md)
- **Standard Library**: [docs/STDLIB.md](docs/STDLIB.md) - 100+ built-in functions
- **Development Roadmap**: [ROADMAP.md](ROADMAP.md)
- **How to Contribute**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Example Programs**: [examples/](examples/)

---

**Start coding in Inscript today and experience the joy of a language designed for clarity and developer happiness!**
