# Inscript Standard Library Documentation

Inscript includes an extensive standard library with 100+ built-in functions organized by category.

## Table of Contents

1. [I/O Functions](#io-functions)
2. [Type Conversion](#type-conversion)
3. [String Functions](#string-functions)
4. [List Functions](#list-functions)
5. [Dictionary Functions](#dictionary-functions)
6. [Math Functions](#math-functions)
7. [File I/O](#file-io)
8. [Random Numbers](#random-numbers)
9. [JSON](#json)
10. [Date/Time](#datetime)
11. [Type Checking](#type-checking)
12. [Utility Functions](#utility-functions)

## I/O Functions

### `print(*values)`
Print values to console, space-separated.
```inscript
print("Hello", "World")           # Output: Hello World
print(42, 3.14, true)             # Output: 42 3.14 True
```

### `input(prompt="")`
Read a line from user input.
```inscript
name = input("Enter your name: ")
```

## Type Conversion

### `int(value)`
Convert to integer.
```inscript
int("42")                          # 42
int(3.99)                          # 3
int(true)                          # 1
```

### `float(value)`
Convert to float.
```inscript
float("3.14")                      # 3.14
float(42)                          # 42.0
```

### `string(value)`
Convert to string.
```inscript
string(42)                         # "42"
string([1, 2, 3])                 # "[1, 2, 3]"
```

### `list(value)`
Convert to list.
```inscript
list("abc")                        # ['a', 'b', 'c']
list(range(3))                     # [0, 1, 2]
```

### `dict()`
Create empty dictionary.
```inscript
d = dict()                         # {}
```

### `boolean(value)`
Convert to boolean.
```inscript
boolean(0)                         # false
boolean(1)                         # true
boolean("")                        # false
```

## String Functions

### Case Conversion
```inscript
upper("hello")                     # "HELLO"
lower("HELLO")                     # "hello"
capitalize("hello")                # "Hello"
title("hello world")               # "Hello World"
```

### String Manipulation
```inscript
strip("  hello  ")                 # "hello"
lstrip("  hello  ")                # "hello  "
rstrip("  hello  ")                # "  hello"
replace("hello world", "world", "inscript")  # "hello inscript"
repeat("ha", 3)                    # "hahaha"
slice("hello", 1, 4)               # "ell"
```

### String Search
```inscript
find("hello", "ll")                # 2
rfind("hello", "l")                # 3
count("hello", "l")                # 2
contains("hello", "ll")            # true
startswith("hello", "he")          # true
endswith("hello", "lo")            # true
```

### String Testing
```inscript
isdigit("12345")                   # true
isalpha("hello")                   # true
isalnum("abc123")                  # true
isspace("   ")                     # true
```

### String Splitting & Joining
```inscript
split("hello world")               # ["hello", "world"]
split("a,b,c", ",")                # ["a", "b", "c"]
join(",", ["a", "b", "c"])         # "a,b,c"
join_str([1, 2, 3])                # "1 2 3"
```

## List Functions

### List Modification
```inscript
lst = [1, 2, 3]
append(lst, 4)                     # lst is now [1, 2, 3, 4]
insert(lst, 1, 99)                 # lst is now [1, 99, 2, 3, 4]
remove(lst, 99)                    # lst is now [1, 2, 3, 4]
pop(lst)                           # 4, lst is now [1, 2, 3]
pop(lst, 1)                        # 2, lst is now [1, 3]
clear(lst)                         # lst is now []
```

### List Operations
```inscript
copy([1, 2, 3])                    # [1, 2, 3]
extend([1, 2], [3, 4])             # [1, 2, 3, 4]
reverse([1, 2, 3])                 # [3, 2, 1]
sort([3, 1, 2])                    # [1, 2, 3]
sorted([3, 1, 2], true)            # [3, 2, 1] (reverse)
flatten([[1, 2], [3, 4]])          # [1, 2, 3, 4]
```

### List Search
```inscript
contains([1, 2, 3], 2)             # true
index([1, 2, 3], 2)                # 1
find_duplicates([1, 1, 2, 2, 3])   # [1, 2]
```

### List Slicing
```inscript
slice_list([1, 2, 3, 4, 5], 1, 4)  # [2, 3, 4]
slice_list([1, 2, 3], 2)           # [3]
unique([1, 1, 2, 2, 3])            # [1, 2, 3]
zip([1, 2], ["a", "b"])            # [[1, "a"], [2, "b"]]
```

## Dictionary Functions

### Dictionary Operations
```inscript
d = {"a": 1, "b": 2}
keys(d)                            # ["a", "b"]
values(d)                          # [1, 2]
get(d, "a")                        # 1
get(d, "c", 0)                     # 0 (default)
has_key(d, "a")                    # true
```

### Dictionary Modification
```inscript
d = {"a": 1}
d["b"] = 2                         # {"a": 1, "b": 2}
update(d, {"c": 3})                # {"a": 1, "b": 2, "c": 3}
pop_dict(d, "a")                   # 1, d is now {"b": 2, "c": 3}
```

## Math Functions

### Basic Math
```inscript
absolute(-42)                      # 42
round(3.7)                         # 4
round(3.14159, 2)                  # 3.14
power(2, 3)                        # 8
```

### Collection Math
```inscript
sum([1, 2, 3])                     # 6
min([1, 2, 3])                     # 1
max([1, 2, 3])                     # 3
length([1, 2, 3])                  # 3
```

### Advanced Math
```inscript
sqrt(16)                           # 4.0
sin(0)                             # 0.0
cos(0)                             # 1.0
tan(0)                             # 0.0
log(2.718)                         # 1.0
log10(100)                         # 2.0
log2(8)                            # 3.0
exp(1)                             # 2.718...
```

### Rounding
```inscript
ceil(3.2)                          # 4
floor(3.8)                         # 3
```

### Angle Conversion
```inscript
degrees(3.14159)                   # ~180
radians(180)                       # ~3.14159
```

### Number Theory
```inscript
gcd(12, 8)                         # 4
factorial(5)                       # 120
```

### Constants
```inscript
pi()                               # 3.14159...
e()                                # 2.71828...
```

## File I/O

### Reading Files
```inscript
content = read("file.txt")         # Read entire file
lines = readlines("file.txt")      # Read as list of lines
exists = file_exists("file.txt")   # Check if file exists
```

### Writing Files
```inscript
write("file.txt", "content")       # Overwrite file
append_text("file.txt", "more")    # Append to file
delete_file("file.txt")            # Delete file
```

## Random Numbers

### Random Generation
```inscript
random()                           # Float between 0 and 1
randint(1, 10)                     # Integer between 1 and 10 (inclusive)
choice([1, 2, 3, 4, 5])            # Random item from list
sample([1, 2, 3, 4, 5], 3)         # 3 unique random items
shuffle([1, 2, 3])                 # Shuffle list in place
seed(42)                           # Set random seed
```

## JSON

### JSON Conversion
```inscript
data = {"name": "Alice", "age": 30}
json_str = to_json(data)           # '{"name": "Alice", "age": 30}'
parsed = from_json(json_str)       # Back to dictionary
```

## Date/Time

### Current Time
```inscript
now()                              # Current datetime as ISO string
timestamp()                        # Unix timestamp
```

### Date Components
```inscript
year()                             # Current year
month()                            # Current month
day()                              # Current day

year("2026-02-18")                # 2026
month("2026-02-18")               # 2
day("2026-02-18")                 # 18
```

## Type Checking

### Type Predicates
```inscript
is_int(42)                         # true
is_float(3.14)                     # true
is_string("hello")                 # true
is_bool(true)                      # true
is_list([1, 2, 3])                 # true
is_dict({"a": 1})                  # true
is_null(null)                      # true
type(42)                           # "int"
```

## Utility Functions

### List Utilities
```inscript
range(5)                           # [0, 1, 2, 3, 4]
range(1, 5)                        # [1, 2, 3, 4]
range(0, 10, 2)                    # [0, 2, 4, 6, 8]
enumerate([1, 2, 3])               # [[0, 1], [1, 2], [2, 3]]
reversed([1, 2, 3])                # [3, 2, 1]
```

### Boolean Aggregates
```inscript
any([false, false, true])          # true
all([true, true, false])           # false
```

### Character Operations
```inscript
ascii("ABC")                       # [65, 66, 67]
chr(65)                            # "A"
```

### Hashing and Identity
```inscript
id(obj)                            # Unique object id
hash("hello")                      # Hash value
```

### Other Utilities
```inscript
wait(2)                            # Sleep for 2 seconds
exit(0)                            # Exit program
```

## Examples

### String Processing
```inscript
text = "Hello World"
print(upper(text))                 # HELLO WORLD
print(lower(text))                 # hello world
words = split(text)
print(length(words))               # 2
```

### List Processing
```inscript
numbers = [3, 1, 4, 1, 5, 9, 2, 6]
print(sorted(numbers))             # [1, 1, 2, 3, 4, 5, 6, 9]
print(unique(numbers))             # [3, 1, 4, 5, 9, 2, 6]
print(sum(numbers))                # 31
print(average(numbers))            # 3.875
```

### File Processing
```inscript
content = "line1\nline2\nline3"
write("data.txt", content)
lines = readlines("data.txt")
for line in lines:
{
    print(strip(line))
}
delete_file("data.txt")
```

### JSON Data
```inscript
person = {"name": "Alice", "age": 30, "hobbies": ["reading", "coding"]}
json_str = to_json(person)
write("person.json", json_str)
loaded = from_json(read("person.json"))
print(loaded["name"])
```

### Mathematical Calculations
```inscript
numbers = [10, 20, 30, 40, 50]
print("Sum: " + string(sum(numbers)))
print("Average: " + string(average(numbers)))
print("Max: " + string(max(numbers)))
print("Min: " + string(min(numbers)))
```

## Library Modules (Examples)

The `/examples` directory includes library-like files:

- `string_utils.is` - String manipulation utilities
- `math_utils.is` - Mathematical helper functions
- `list_utils.is` - Advanced list operations

These can be studied and copied into your own programs.

## Performance Notes

- String operations create new strings (immutable)
- List operations work on references
- Dictionary operations are efficient
- Math functions use Python's math library directly
- File I/O is buffered for efficiency

## Error Handling

Most functions will raise an error if given invalid arguments:

```inscript
int("not a number")               # Error: Cannot parse as integer
read("nonexistent.txt")           # Error: File not found
split(42)                         # Error: Cannot split non-string
```

For safer operations, check types first:

```inscript
if is_string(value):
{
    result = split(value)
}
```

## Future Additions

Planned for future versions:
- Regular expressions
- Database access
- HTTP requests
- Path manipulation
- Environmental variables
- Process control
- Threading/concurrency
- Advanced data structures

---

**Total Built-in Functions: 100+**

Visit [LANGUAGE_SPEC.md](LANGUAGE_SPEC.md) for language syntax details.
