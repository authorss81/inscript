# Inscript v0.2.0 - Extended Libraries & Functions

## Overview

Inscript has been significantly expanded with comprehensive standard library functions (100+) and advanced examples demonstrating real-world use cases. The interpreter now provides a rich, practical programming environment with extensive built-in functionality.

## Major Additions

### 1. ✅ String Functions (20+)

**Case Manipulation**
- `upper()`, `lower()`, `capitalize()`, `title()`

**String Operations**
- `strip()`, `lstrip()`, `rstrip()` - Remove whitespace
- `replace()`, `repeat()`, `slice()` - String modification
- `char_at()` - Get character by index

**String Search**
- `find()`, `rfind()`, `count()` - Search operations
- `startswith()`, `endswith()`, `contains()` - Prefix/suffix checks

**String Testing**
- `isdigit()`, `isalpha()`, `isalnum()`, `isspace()` - Character type checks

**String Splitting & Joining**
- `split()`, `join()` - String splitting and joining
- `join_str()` - Join list as space-separated string

### 2. ✅ Math Functions (20+)

**Trigonometry**
- `sin()`, `cos()`, `tan()`
- `asin()`, `acos()`, `atan()`

**Logarithms & Exponentials**
- `log()`, `log10()`, `log2()`, `exp()`
- `sqrt()` - Square root

**Rounding**
- `ceil()`, `floor()`, `round()`

**Angle Conversion**
- `degrees()`, `radians()`

**Number Theory**
- `gcd()` - Greatest common divisor
- `factorial()` - Factorial calculation
- `hypot()`, `fabs()` - Hypotenuse and absolute value

**Constants**
- `pi()`, `e()` - Mathematical constants

### 3. ✅ List Functions (15+)

**Modification**
- `append()`, `insert()`, `remove()`, `pop()`
- `extend()`, `clear()`, `copy()`

**Ordering**
- `sort()`, `sorted()`, `reverse()`, `reversed()`

**Analysis**
- `unique()` - Remove duplicates
- `flatten()` - Flatten nested lists
- `zip()` - Combine lists into pairs

**Search**
- `index()`, `find_duplicates()`, `slice_list()`

### 4. ✅ File I/O (6 functions)

- `read(filename)` - Read entire file
- `write(filename, content)` - Write to file
- `append_text(filename, content)` - Append to file
- `readlines(filename)` - Read as list of lines
- `file_exists(filename)` - Check file existence
- `delete_file(filename)` - Delete file

### 5. ✅ Random Numbers (6 functions)

- `random()` - Float between 0 and 1
- `randint(a, b)` - Random integer in range
- `choice(list)` - Random item from list
- `sample(list, k)` - k random unique items
- `shuffle(list)` - Shuffle list in-place
- `seed(value)` - Set random seed

### 6. ✅ JSON Support (2 functions)

- `to_json(obj)` - Convert object to JSON string
- `from_json(string)` - Parse JSON string to object

### 7. ✅ Date & Time (5 functions)

- `now()` - Current datetime (ISO format)
- `timestamp()` - Unix timestamp
- `year()`, `month()`, `day()` - Extract date components

### 8. ✅ Dictionary Functions (5 functions)

- `get(dict, key, default)` - Get with default
- `pop_dict(dict, key)` - Remove and return
- `update(dict, other)` - Update from another dict
- `has_key(dict, key)` - Check key existence
- `dict_copy(dict)` - Create shallow copy

### 9. ✅ Type Checking (8 functions)

- `is_int()`, `is_float()`, `is_string()`
- `is_bool()`, `is_list()`, `is_dict()`
- `is_null()`, `type()`

### 10. ✅ Utility Functions (15+)

- `any()`, `all()` - Boolean aggregates
- `enumerate()` - Index enumeration
- `ascii()`, `chr()` - Character operations
- `hash()`, `id()` - Object utilities
- `wait()` - Sleep/delay
- `hex()`, `bin()`, `oct()` - Number format conversion

## Example Programs (11 Complete)

### Basic Examples
1. **hello.is** - Hello World
2. **conditionals.is** - Conditional statements
3. **loops.is** - Loop demonstrations
4. **data_structures.is** - Lists and dictionaries
5. **fibonacci.is** - Recursive functions

### Advanced Examples

#### Statistics & Analysis
**6. statistics.is**
- Calculate mean, median, sum, min, max, range
- Demonstrates list operations and mathematical calculations
- Output: Complete statistical analysis

#### Mathematical Computing
**7. prime_finder.is**
- Find all primes up to a limit
- Analyze prime patterns (twin primes, Sophie Germain primes)
- Demonstrates mathematical algorithms and loops
- Output: Comprehensive prime analysis

#### String Processing
**8. string_analyzer.is**
- Analyze text for length, word count, character types
- Detect palindromes
- Count specific character types
- Demonstrates string manipulation functions

#### List Algorithms
**9. list_algorithms.is**
- Sorting demonstrations (ascending/descending)
- Filtering operations (even, odd, squares)
- List searching
- List chunking
- Set operations (intersection, union, difference)

#### JSON & Random
**10. json_random.is**
- JSON serialization and deserialization
- Random number generation
- Random selection and sampling
- Lottery simulator with random numbers

#### File Operations
**11. file_operations.is**
- Create and read files
- Count statistics (lines, characters, words)
- Process files line-by-line
- Append and delete files

## Utility Libraries (3 Reusable)

These are not standalone programs but functions that can be imported/included:

**string_utils.is**
- `to_camelcase()`, `to_snakecase()`
- `reverse_string()`, `is_palindrome()`
- `word_count()`, `character_frequency()`
- `truncate()`, `repeat_pattern()`

**math_utils.is**
- `is_prime()`, `get_primes()`
- `mean()`, `median()`, `variance()`, `std_dev()`
- `geometric_mean()`, `is_perfect_square()`
- `lcm()`, `distance_2d()`, `clamp()`

**list_utils.is**
- `sum_list()`, `product_list()`, `average_list()`
- `find_duplicates()`, `partition()`
- `rotate_left()`, `rotate_right()`, `chunk()`
- `intersect()`, `union()`, `difference()`

## Standard Library Documentation

Complete documentation available in `docs/STDLIB.md`:
- Function signatures
- Descriptions and behavior
- Usage examples for each function
- Organized by category
- Performance notes and best practices

## Testing Results

All major functionality tested and working:

```
✅ statistics.is        - Statistics calculation
✅ prime_finder.is      - Prime number analysis  
✅ string_analyzer.is   - String analysis
✅ list_algorithms.is   - List operations
✅ json_random.is       - JSON and random numbers
✅ file_operations.is   - File I/O
```

## Code Statistics

### Built-in Functions
- Total: **100+** functions
- String: 20+ functions
- Math: 20+ functions
- List: 15+ functions
- File I/O: 6 functions
- Random: 6 functions
- Date/Time: 5 functions
- Dictionary: 5 functions
- Type checking: 8 functions
- Utilities: 15+ functions

### Example Programs
- Basic examples: 5 programs
- Advanced examples: 6 programs
- Utility libraries: 3 libraries
- Total lines of example code: 800+

### Documentation
- Language specification: Complete
- Standard library docs: Comprehensive (100+ functions documented)
- Example code: Well-commented
- Total documentation: 5 markdown files

## Usage Examples

### String Manipulation
```inscript
text = "Hello World"
print(upper(text))           # HELLO WORLD
print(lower(text))           # hello world
words = split(text)          # ["Hello", "World"]
```

### Mathematical Calculations
```inscript
numbers = [10, 20, 30, 40, 50]
total = sum(numbers)         # 150
average = total / length(numbers)  # 30
maximum = max(numbers)       # 50
minimum = min(numbers)       # 10
```

### List Processing
```inscript
lst = [3, 1, 4, 1, 5, 9]
sorted_list = sorted(lst)    # [1, 1, 3, 4, 5, 9]
unique_list = unique(lst)    # [3, 1, 4, 5, 9]
```

### File I/O
```inscript
content = "Welcome to Inscript"
write("test.txt", content)
data = read("test.txt")
print(data)                  # Welcome to Inscript
delete_file("test.txt")
```

### JSON Operations
```inscript
data = {"name": "Alice", "age": 30}
json_str = to_json(data)
parsed = from_json(json_str)
print(parsed["name"])        # Alice
```

### Random Generation
```inscript
random_num = randint(1, 100)
random_choice = choice([1, 2, 3, 4, 5])
random_sample = sample(range(1, 10), 3)
```

## Language Features Now Supported

✅ Variables and assignments
✅ All primitive data types
✅ Collections (lists, dictionaries)
✅ All operators (arithmetic, comparison, logical)
✅ Control flow (if/elseif/else, while, for)
✅ User-defined functions
✅ 100+ built-in functions
✅ String manipulation (20+ functions)
✅ Mathematical operations (20+ functions)
✅ List processing (15+ functions)
✅ File I/O operations
✅ Random number generation
✅ JSON serialization
✅ Date/time functions
✅ Type checking functions
✅ Comments
✅ Interactive REPL

## Future Enhancements

### Planned for v0.3.0
- Classes and object-oriented programming
- Exception handling (try/catch/finally)
- Lambda functions
- List comprehensions
- Multiple file support
- Module/import system

### Planned for v1.0.0
- Regular expressions
- Async/await
- Generators
- Pattern matching
- Debugging support
- VS Code extension
- Performance optimization

## Summary

Inscript now provides a **comprehensive, practical programming environment** with:

- **100+ built-in functions** covering common tasks
- **11 example programs** demonstrating real-world use cases
- **Complete documentation** for all features
- **Rich standard library** for productivity
- **Clean, intuitive syntax** for ease of learning
- **Cross-platform compatibility** (Windows, Mac, Linux)
- **Fast development cycle** with immediate feedback (REPL)

The language is suitable for:
- Learning programming concepts
- Data processing and analysis
- Text processing and manipulation
- Mathematical calculations
- File I/O and automation
- Prototyping algorithms
- Educational purposes

## Getting Started

To explore the new functionality:

```bash
# Run examples
python inscript.py examples/statistics.is
python inscript.py examples/prime_finder.is
python inscript.py examples/string_analyzer.is
python inscript.py examples/list_algorithms.is

# View documentation
Open docs/STDLIB.md for complete function reference

# Try interactive mode
python inscript.py --repl
```

## Documentation Files

- `README.md` - Project overview
- `docs/LANGUAGE_SPEC.md` - Language specification
- `docs/STDLIB.md` - Standard library (100+ functions)
- `ROADMAP.md` - Development roadmap
- `CONTRIBUTING.md` - Contribution guidelines

---

**Inscript is rapidly becoming a practical, feature-rich language suitable for real-world use!**

Version: 0.2.0
Date: February 2026
Total Functions: 100+
Example Programs: 11
Documentation: Complete
