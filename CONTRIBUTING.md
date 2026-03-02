# Contributing to Inscript

Thank you for your interest in contributing to Inscript! We welcome contributions from everyone and appreciate your effort to improve the language.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- A clear description of the bug
- Steps to reproduce it
- Expected vs actual behavior
- Your environment (Python version, OS, etc.)

### Requesting Features

For feature requests, please:
- Clearly describe the feature
- Explain why it would be useful
- If possible, provide example code

### Code Contributions

1. **Fork the repository**
2. **Create a new branch** for your feature: `git checkout -b feature/your-feature-name`
3. **Make your changes** with clear, descriptive commits
4. **Write or update tests** for your changes
5. **Update documentation** as needed
6. **Submit a pull request** with a clear description

## Development Setup

```bash
# Clone the repository
git clone <your-fork-url>
cd inscript

# Install in development mode
pip install -e .

# Run tests
python -m pytest tests/ -v
```

## Code Style

- Follow PEP 8 for Python code
- Use clear variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small

## What We're Looking For

### High Priority
- Bug fixes
- Performance improvements
- Test coverage
- Documentation improvements

### Medium Priority
- New built-in functions
- Error message improvements
- Example programs
- Tutorial content

### Future Features
- Classes and OOP support
- Exception handling
- Module/import system
- File I/O operations
- List comprehensions
- VS Code extension

## File Structure

When adding new features, consider:
- **lexer.py**: Add new token types if needed
- **parser.py**: Add AST nodes for new constructs
- **interpreter.py**: Add evaluation logic
- **builtins.py**: Add new built-in functions
- **examples/**: Create example programs
- **docs/**: Update language specification
- **tests/**: Add test cases

## Language Design Principles

Remember our three core principles when contributing:

1. **Language Feel**: Is it pleasant to write?
2. **Clarity**: Is the code self-documenting?
3. **Developer Happiness**: Does it reduce friction?

## Testing

- All new features should have tests
- Run `python tests/test_interpreter.py` before submitting
- For pytest users: `pytest tests/ -v`

## Documentation

- Update [docs/LANGUAGE_SPEC.md](docs/LANGUAGE_SPEC.md) for language changes
- Update [README.md](README.md) for project changes
- Add example programs for new features
- Include docstrings in code

## Questions?

Feel free to:
- Open an issue for discussion
- Comment on existing issues
- Reach out to the community

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Support other contributors
- Keep discussions professional

Thank you for contributing to Inscript! 🎉
