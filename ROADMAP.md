# Inscript Development Roadmap

This roadmap outlines the planned development of Inscript from current alpha stage to a production-ready language with VS Code integration and community support.

## Version 0.1.0 (Current - Alpha)

**Current Status**: ✅ Complete

### Core Features
- [x] Lexer (tokenization)
- [x] Parser (AST generation)
- [x] Interpreter (execution engine)
- [x] Variables and assignments
- [x] All primitive data types (numbers, strings, booleans, null)
- [x] Collections (lists, dictionaries)
- [x] Operators (arithmetic, comparison, logical)
- [x] Control flow (if/elseif/else, while, for)
- [x] Functions (user-defined)
- [x] 25+ built-in functions
- [x] REPL (interactive mode)
- [x] Basic examples

## Version 0.2.0 (Beta - Core Language Enhancement)

**Timeline**: Q2 2026

### Language Features
- [ ] Classes and object-oriented programming
  - [ ] Class definitions
  - [ ] Constructors (__init__)
  - [ ] Instance methods and variables
  - [ ] Inheritance
  - [ ] Static methods
- [ ] Exception handling
  - [ ] try/catch/finally blocks
  - [ ] raise statement
  - [ ] Custom exception types
- [ ] Advanced functions
  - [ ] Default parameters
  - [ ] Variable arguments (*args, **kwargs)
  - [ ] Lambda functions
  - [ ] First-class functions
- [ ] List and dictionary comprehensions
- [ ] Context managers (with statement)
- [ ] Decorators

### Standard Library
- [ ] File I/O (open, read, write)
- [ ] String methods (split, join, strip, etc.)
- [ ] Collection methods
- [ ] Math module
- [ ] Random module
- [ ] JSON support

### Testing & Quality
- [ ] Comprehensive test suite (pytest)
- [ ] Code coverage reports
- [ ] Performance benchmarks
- [ ] Static type checking (optional)

### Documentation
- [ ] Tutorial for beginners
- [ ] API documentation
- [ ] Performance guide
- [ ] Best practices guide

## Version 0.3.0 (Release Candidate - Modules & Tooling)

**Timeline**: Q3 2026

### Module System
- [ ] Module/import system
  - [ ] `import` statement
  - [ ] `from ... import` statement
  - [ ] Package structure
  - [ ] Standard library modules
- [ ] Package manager (inscript-pkg or similar)
- [ ] Virtual environment support

### Development Tools
- [ ] Debugger
  - [ ] Breakpoints
  - [ ] Step through code
  - [ ] Variable inspection
- [ ] Profiler
- [ ] Linter
- [ ] Code formatter
- [ ] REPL enhancements
  - [ ] History
  - [ ] Auto-completion
  - [ ] Syntax highlighting

### VS Code Integration (Preview)
- [ ] Install as VS Code extension
- [ ] Basic syntax highlighting
- [ ] Code snippets
- [ ] Run button in editor

## Version 1.0.0 (Stable - Production Ready)

**Timeline**: Q4 2026

### Complete VS Code Extension
- [ ] Full syntax highlighting
- [ ] IntelliSense / auto-completion
- [ ] Integrated debugger
- [ ] Code formatting on save
- [ ] Linting with inline errors
- [ ] Test runner integration
- [ ] Snippet support
- [ ] Project templates
- [ ] Theme support

### Language Completeness
- [ ] Type annotations (optional)
- [ ] Async/await support
- [ ] Generator functions
- [ ] Pattern matching
- [ ] Standard library completion
- [ ] Performance optimizations

### Publishing & Distribution
- [ ] VS Code Marketplace listing
- [ ] PyPI package
- [ ] Standalone executables (Windows, Mac, Linux)
- [ ] Official website
- [ ] Community package repository

### Documentation & Community
- [ ] Official documentation website
- [ ] Video tutorials
- [ ] Community forum
- [ ] Example projects
- [ ] Contributing guidelines refinement

## Beyond 1.0

### Future Enhancements
- [ ] Compiler to bytecode
- [ ] Just-In-Time (JIT) compilation for performance
- [ ] Static compilation to native code
- [ ] Web runtime (run in browsers)
- [ ] Mobile support
- [ ] GPU computation support
- [ ] Concurrency improvements
- [ ] Database integration
- [ ] Web framework

### Ecosystem
- [ ] Web framework (Inscript-Web)
- [ ] Data science library (Inscript-Data)
- [ ] Machine learning library (Inscript-ML)
- [ ] Game development library
- [ ] Cross-platform desktop framework

## Breaking Down the Work

### For Current Contributors

1. **Start with Version 0.1.x**:
   - Bug fixes
   - More built-in functions
   - More examples
   - Better error messages
   - Documentation improvements

2. **Move to Version 0.2.0**:
   - Classes and OOP
   - Exception handling
   - Standard library expansion
   - File I/O
   - Testing infrastructure

3. **VS Code Extension**:
   - This can happen in parallel
   - Start with basic syntax highlighting
   - Progressively add features

## Milestones

```
v0.1.0 (Now)
  ├─ Core language ✅
  ├─ Basic examples ✅
  └─ Simple documentation ✅

v0.2.0 (6-8 weeks)
  ├─ OOP support
  ├─ Exception handling
  ├─ Standard library
  └─ Pytest integration

v0.3.0 (12-16 weeks)
  ├─ Module system
  ├─ Debugging tools
  ├─ VS Code preview
  └─ Package manager

v1.0.0 (24-28 weeks)
  ├─ Complete VS Code extension
  ├─ Stable language spec
  ├─ Comprehensive documentation
  └─ Official release

Beyond
  └─ Ecosystem & specialized libraries
```

## Priorities

### Phase 1: Language Foundation (NOW)
- ✅ Core interpreter
- In progress: More examples
- In progress: Better error handling

### Phase 2: Standard Library (Next)
- File I/O
- String/list/dict methods
- Math and utilities
- Exception handling

### Phase 3: Developer Experience (Following)
- Debugging
- Profiling
- Better error messages
- REPL improvements
- VS Code extension basics

### Phase 4: Production Ready (Final)
- Full VS Code integration
- Performance optimization
- Complete documentation
- Community tooling

## Getting Help

- Check [CONTRIBUTING.md](CONTRIBUTING.md) for details
- Issues are organized by version
- Look for "help wanted" labels
- Join discussions on specific features

## Feedback & Suggestions

Have ideas for the roadmap? Please:
1. Open an issue with the `enhancement` label
2. Describe the feature or improvement
3. Explain why it's important
4. Include any example use cases

This roadmap is a living document and may change based on community feedback and priorities.

**Last Updated**: February 2026
