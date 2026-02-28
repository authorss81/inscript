# Inscript Language Specification

## Overview

Inscript is a clean, Python-like interpreted programming language designed with three core principles:
- **Language Feel**: Intuitive and pleasant to write
- **Clarity**: Code should be easy to understand
- **Developer Happiness**: Focus on reducing friction

## Data Types

### Primitive Types
- **Numbers**: `42`, `3.14` (integers and floats)
- **Strings**: `"hello"`, `'world'` (with escape sequences)
- **Booleans**: `true`, `false`
- **Null**: `null` (represents absence of value)

### Collection Types
- **Lists**: `[1, 2, 3]` or `[1, "hello", true]`
- **Dictionaries**: `{"key": "value", "count": 42}`

### Type Conversion
```inscript
int("42")           # Convert to integer: 42
float("3.14")       # Convert to float: 3.14
string(42)          # Convert to string: "42"
boolean(0)          # Convert to boolean: false
list([1, 2, 3])     # Create list
dict({"a": 1})      # Create dictionary
```

## Variables and Assignment

Variables are declared and assigned in a single statement:

```inscript
name = "Alice"
age = 30
score = 95.5
active = true
hobbies = ["reading", "coding", "gaming"]
```

Variables are dynamically typed and can change types:

```inscript
x = 42                  # integer
x = "hello"             # string
x = [1, 2, 3]          # list
```

## Operators

### Arithmetic
```inscript
x = 10 + 5              # Addition: 15
x = 10 - 5              # Subtraction: 5
x = 10 * 5              # Multiplication: 50
x = 10 / 5              # Division: 2.0
x = 10 % 3              # Modulo: 1
x = 2 ** 3              # Power: 8
```

### Comparison
```inscript
x == y                  # Equal to
x != y                  # Not equal to
x < y                   # Less than
x <= y                  # Less than or equal
x > y                   # Greater than
x >= y                  # Greater than or equal
x is y                  # Identity check
```

### Logical
```inscript
true and false          # Conjunction: false
true or false           # Disjunction: true
not true                # Negation: false
```

### String Concatenation
```inscript
greeting = "Hello" + ", " + "World"  # "Hello, World"
repeated = "ha" * 3                   # "hahaha"
```

## Control Flow

### If Statement
```inscript
if condition:
{
    # then body
}
elseif another_condition:
{
    # elseif body
}
else:
{
    # else body
}
```

### While Loop
```inscript
while condition:
{
    # loop body
}
```

### For Loop
```inscript
for item in iterable:
{
    # loop body
}
```

Loop Control:
```inscript
break           # Exit loop
continue        # Skip to next iteration
```

## Functions

### Function Definition
```inscript
function greet(name):
{
    print("Hello, " + name)
}

function add(a, b):
{
    return a + b
}

result = add(10, 20)    # result: 30
```

### Built-in Functions

#### I/O
- `print(...values)` - Print values to console
- `input(prompt)` - Read input from user

#### Type Information
- `type(value)` - Get type name
- `length(container)` - Get length

#### Collections
- `range(end)` - Create range: 0 to end-1
- `range(start, end)` - Create range: start to end-1
- `range(start, end, step)` - Create range with step
- `list(iterable)` - Convert to list
- `dict()` - Create empty dictionary
- `keys(dictionary)` - Get dictionary keys
- `values(dictionary)` - Get dictionary values

#### Sequence Operations
- `sort(iterable)` - Sort and return new sequence
- `reverse(iterable)` - Reverse sequence
- `contains(container, item)` - Check membership
- `sum(iterable)` - Sum all numbers
- `min(iterable)` - Get minimum value
- `max(iterable)` - Get maximum value

#### Math
- `absolute(number)` - Get absolute value
- `round(number, decimals)` - Round number
- `power(base, exponent)` - Calculate power

#### System
- `exit(code)` - Exit program

## Collections

### Lists
```inscript
fruits = ["apple", "banana", "cherry"]

# Access elements
first = fruits[0]                   # "apple"

# Modify
fruits[1] = "blueberry"

# Add items
fruits.append("date")

# Remove items
fruits.remove("apple")

# Check membership
if contains(fruits, "banana"):
{
    print("Found banana")
}

# Iterate
for fruit in fruits:
{
    print(fruit)
}
```

### Dictionaries
```inscript
person = {
    "name": "Alice",
    "age": 30,
    "city": "New York"
}

# Access
name = person["name"]

# Modify
person["age"] = 31

# Get all keys and values
all_keys = person.keys()
all_values = person.values()

# Iterate over keys
for key in person.keys():
{
    print(key + ": " + string(person[key]))
}
```

## Comments

Comments start with `#` and extend to end of line:

```inscript
# This is a comment
x = 42          # This is also a comment
```

## Best Practices

1. **Use Clear Variable Names**: `user_age` instead of `ua`
2. **Keep Functions Small**: Single responsibility principle
3. **Use Meaningful Comments**: Explain the "why", not the "what"
4. **Prefer Readability**: Extra spaces and lines for clarity
5. **Handle Edge Cases**: Check bounds and null values

## Example Programs

See the `examples/` directory for complete programs demonstrating:
- Basic arithmetic and strings
- Loops and conditionals
- Functions
- Data structures
- Control flow

## Running Inscript Programs

```bash
# Run a program file
python inscript.py hello.is

# Start interactive mode
python inscript.py --repl
```

## Future Features

- Classes and objects
- Module system
- Exception handling (try/catch)
- Lambda functions
- List comprehensions
- Decorators
- Native type methods
- File I/O
