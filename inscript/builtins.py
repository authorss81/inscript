"""
Built-in functions for Inscript language.
Provides standard library functionality.
"""

import math
import random
import json
import os
import sys
from datetime import datetime

def inscript_print(*args):
    """Print values to console."""
    output = " ".join(str(arg) for arg in args)
    print(output)
    return None

def inscript_length(obj):
    """Get length of a sequence."""
    return len(obj)

def inscript_range(start, end=None, step=1):
    """Generate a range of numbers."""
    if end is None:
        end = start
        start = 0
    return list(range(start, end, step))

def inscript_type(obj):
    """Get the type of an object."""
    type_name = type(obj).__name__
    if type_name == 'NoneType':
        return 'null'
    return type_name

def inscript_int(value):
    """Convert to integer."""
    return int(value)

def inscript_float(value):
    """Convert to float."""
    return float(value)

def inscript_string(value):
    """Convert to string."""
    return str(value)

def inscript_list(value=None):
    """Create a list."""
    if value is None:
        return []
    return list(value)

def inscript_dict(value=None):
    """Create a dictionary."""
    if value is None:
        return {}
    return dict(value)

def inscript_boolean(value):
    """Convert to boolean."""
    if value is None or value is False:
        return False
    if value == 0 or value == "" or value == [] or value == {}:
        return False
    return True

def inscript_sum(iterable):
    """Sum all numbers in an iterable."""
    return sum(iterable)

def inscript_min(iterable):
    """Get minimum value."""
    return min(iterable)

def inscript_max(iterable):
    """Get maximum value."""
    return max(iterable)

def inscript_reverse(iterable):
    """Reverse a sequence."""
    if isinstance(iterable, str):
        return iterable[::-1]
    return list(reversed(iterable))

def inscript_sort(iterable):
    """Sort a sequence."""
    return sorted(iterable)

def inscript_contains(container, item):
    """Check if item is in container."""
    return item in container

def inscript_keys(dictionary):
    """Get dictionary keys."""
    return list(dictionary.keys())

def inscript_values(dictionary):
    """Get dictionary values."""
    return list(dictionary.values())

def inscript_input(prompt=""):
    """Read input from user."""
    return input(prompt)

def inscript_round(number, decimals=0):
    """Round a number."""
    return round(number, decimals)

def inscript_absolute(number):
    """Get absolute value."""
    return abs(number)

def inscript_power(base, exponent):
    """Calculate power."""
    return base ** exponent

def inscript_exit(code=0):
    """Exit the program."""
    import sys
    sys.exit(code)

# String functions
def inscript_upper(text):
    """Convert string to uppercase."""
    return str(text).upper()

def inscript_lower(text):
    """Convert string to lowercase."""
    return str(text).lower()

def inscript_strip(text):
    """Remove leading and trailing whitespace."""
    return str(text).strip()

def inscript_lstrip(text):
    """Remove leading whitespace."""
    return str(text).lstrip()

def inscript_rstrip(text):
    """Remove trailing whitespace."""
    return str(text).rstrip()

def inscript_replace(text, old, new):
    """Replace occurrences of substring."""
    return str(text).replace(str(old), str(new))

def inscript_split(text, delimiter=" "):
    """Split string by delimiter."""
    return str(text).split(str(delimiter))

def inscript_join(delimiter, items):
    """Join items with delimiter."""
    return str(delimiter).join(str(item) for item in items)

def inscript_startswith(text, prefix):
    """Check if string starts with prefix."""
    return str(text).startswith(str(prefix))

def inscript_endswith(text, suffix):
    """Check if string ends with suffix."""
    return str(text).endswith(str(suffix))

def inscript_find(text, substring):
    """Find index of substring (-1 if not found)."""
    return str(text).find(str(substring))

def inscript_rfind(text, substring):
    """Find last index of substring (-1 if not found)."""
    return str(text).rfind(str(substring))

def inscript_count(text, substring):
    """Count occurrences of substring."""
    return str(text).count(str(substring))

def inscript_repeat(text, times):
    """Repeat string n times."""
    return str(text) * int(times)

def inscript_slice(text, start, end=None):
    """Slice string from start to end."""
    text_str = str(text)
    if end is None:
        return text_str[int(start):]
    return text_str[int(start):int(end)]

def inscript_char_at(text, index):
    """Get character at index."""
    return str(text)[int(index)]

def inscript_capitalize(text):
    """Capitalize first character."""
    return str(text).capitalize()

def inscript_title(text):
    """Title case string."""
    return str(text).title()

def inscript_isdigit(text):
    """Check if string contains only digits."""
    return str(text).isdigit()

def inscript_isalpha(text):
    """Check if string contains only letters."""
    return str(text).isalpha()

def inscript_isalnum(text):
    """Check if string contains only alphanumeric characters."""
    return str(text).isalnum()

def inscript_isspace(text):
    """Check if string contains only whitespace."""
    return str(text).isspace()

# List functions
def inscript_append(lst, item):
    """Append item to list."""
    lst.append(item)
    return None

def inscript_insert(lst, index, item):
    """Insert item at index."""
    lst.insert(int(index), item)
    return None

def inscript_remove_item(lst, item):
    """Remove first occurrence of item."""
    lst.remove(item)
    return None

def inscript_pop(lst, index=-1):
    """Remove and return item at index."""
    return lst.pop(int(index))

def inscript_clear(lst):
    """Remove all items from list."""
    lst.clear()
    return None

def inscript_copy(lst):
    """Create shallow copy of list."""
    return lst.copy()

def inscript_extend(lst, other):
    """Add all items from another list."""
    lst.extend(other)
    return None

def inscript_index_of(lst, item):
    """Get index of first occurrence."""
    return lst.index(item)

def inscript_slice_list(lst, start, end=None):
    """Slice list from start to end."""
    if end is None:
        return lst[int(start):]
    return lst[int(start):int(end)]

def inscript_flatten(lst):
    """Flatten a list of lists."""
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(item)
        else:
            result.append(item)
    return result

def inscript_unique(lst):
    """Get unique items from list."""
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

def inscript_zip_lists(list1, list2):
    """Combine two lists into pairs."""
    return [[list1[i], list2[i]] for i in range(min(len(list1), len(list2)))]

# Math functions
def inscript_sqrt(n):
    """Calculate square root."""
    return math.sqrt(float(n))

def inscript_sin(n):
    """Calculate sine (radians)."""
    return math.sin(float(n))

def inscript_cos(n):
    """Calculate cosine (radians)."""
    return math.cos(float(n))

def inscript_tan(n):
    """Calculate tangent (radians)."""
    return math.tan(float(n))

def inscript_asin(n):
    """Calculate arcsine."""
    return math.asin(float(n))

def inscript_acos(n):
    """Calculate arccosine."""
    return math.acos(float(n))

def inscript_atan(n):
    """Calculate arctangent."""
    return math.atan(float(n))

def inscript_log(n, base=math.e):
    """Calculate logarithm."""
    return math.log(float(n), float(base))

def inscript_log10(n):
    """Calculate base-10 logarithm."""
    return math.log10(float(n))

def inscript_log2(n):
    """Calculate base-2 logarithm."""
    return math.log2(float(n))

def inscript_exp(n):
    """Calculate e raised to power n."""
    return math.exp(float(n))

def inscript_ceil(n):
    """Round up to nearest integer."""
    return math.ceil(float(n))

def inscript_floor(n):
    """Round down to nearest integer."""
    return math.floor(float(n))

def inscript_degrees(radians):
    """Convert radians to degrees."""
    return math.degrees(float(radians))

def inscript_radians(degrees):
    """Convert degrees to radians."""
    return math.radians(float(degrees))

def inscript_gcd(a, b):
    """Calculate greatest common divisor."""
    return math.gcd(int(a), int(b))

def inscript_factorial(n):
    """Calculate factorial."""
    return math.factorial(int(n))

def inscript_pi():
    """Get the value of pi."""
    return math.pi

def inscript_e():
    """Get the value of e."""
    return math.e

def inscript_sqrt(n):
    """Calculate square root."""
    return math.sqrt(float(n))

def inscript_hypot(x, y):
    """Calculate hypotenuse."""
    return math.hypot(float(x), float(y))

def inscript_fabs(n):
    """Get absolute value as float."""
    return math.fabs(float(n))

# Dictionary functions
def inscript_get_dict(dictionary, key, default=None):
    """Get value with default."""
    return dictionary.get(key, default)

def inscript_pop_dict(dictionary, key, default=None):
    """Remove and return value."""
    return dictionary.pop(key, default)

def inscript_update_dict(dict1, dict2):
    """Update dictionary with another."""
    dict1.update(dict2)
    return None

def inscript_clear_dict(dictionary):
    """Remove all items."""
    dictionary.clear()
    return None

def inscript_dict_copy(dictionary):
    """Create shallow copy."""
    return dictionary.copy()

def inscript_has_key(dictionary, key):
    """Check if key exists."""
    return key in dictionary

# Type checking functions
def inscript_is_integer(value):
    """Check if value is an integer."""
    return isinstance(value, int) and not isinstance(value, bool)

def inscript_is_float(value):
    """Check if value is a float."""
    return isinstance(value, float)

def inscript_is_string(value):
    """Check if value is a string."""
    return isinstance(value, str)

def inscript_is_boolean(value):
    """Check if value is boolean."""
    return isinstance(value, bool)

def inscript_is_list(value):
    """Check if value is a list."""
    return isinstance(value, list)

def inscript_is_dict(value):
    """Check if value is a dictionary."""
    return isinstance(value, dict)

def inscript_is_null(value):
    """Check if value is null/None."""
    return value is None

# File I/O functions
def inscript_read_file(filename):
    """Read entire file as string."""
    try:
        with open(str(filename), 'r') as f:
            return f.read()
    except FileNotFoundError:
        raise RuntimeError(f"File not found: {filename}")
    except Exception as e:
        raise RuntimeError(f"Error reading file: {e}")

def inscript_write_file(filename, content):
    """Write string to file (overwrites)."""
    try:
        with open(str(filename), 'w') as f:
            f.write(str(content))
        return True
    except Exception as e:
        raise RuntimeError(f"Error writing file: {e}")

def inscript_append_file(filename, content):
    """Append string to file."""
    try:
        with open(str(filename), 'a') as f:
            f.write(str(content))
        return True
    except Exception as e:
        raise RuntimeError(f"Error appending to file: {e}")

def inscript_readlines_file(filename):
    """Read file as list of lines."""
    try:
        with open(str(filename), 'r') as f:
            return f.readlines()
    except FileNotFoundError:
        raise RuntimeError(f"File not found: {filename}")
    except Exception as e:
        raise RuntimeError(f"Error reading file: {e}")

def inscript_file_exists(filename):
    """Check if file exists."""
    return os.path.exists(str(filename))

def inscript_delete_file(filename):
    """Delete a file."""
    try:
        os.remove(str(filename))
        return True
    except FileNotFoundError:
        raise RuntimeError(f"File not found: {filename}")
    except Exception as e:
        raise RuntimeError(f"Error deleting file: {e}")

# Random functions
def inscript_random():
    """Generate random float between 0 and 1."""
    return random.random()

def inscript_randint(a, b):
    """Generate random integer between a and b (inclusive)."""
    return random.randint(int(a), int(b))

def inscript_choice(items):
    """Randomly select item from list."""
    return random.choice(items)

def inscript_shuffle_list(items):
    """Shuffle list in place."""
    random.shuffle(items)
    return None

def inscript_sample(items, k):
    """Randomly select k items from list."""
    return random.sample(items, int(k))

def inscript_seed(value):
    """Set random seed."""
    random.seed(int(value))
    return None

# JSON functions
def inscript_to_json(obj):
    """Convert object to JSON string."""
    return json.dumps(obj)

def inscript_from_json(json_str):
    """Parse JSON string to object."""
    try:
        return json.loads(str(json_str))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON: {e}")

# Date/Time functions
def inscript_now():
    """Get current date and time as string."""
    return datetime.now().isoformat()

def inscript_timestamp():
    """Get current Unix timestamp."""
    return datetime.now().timestamp()

def inscript_year(date_str=None):
    """Get year from ISO date string or current."""
    if date_str:
        dt = datetime.fromisoformat(str(date_str))
    else:
        dt = datetime.now()
    return dt.year

def inscript_month(date_str=None):
    """Get month from ISO date string or current."""
    if date_str:
        dt = datetime.fromisoformat(str(date_str))
    else:
        dt = datetime.now()
    return dt.month

def inscript_day(date_str=None):
    """Get day from ISO date string or current."""
    if date_str:
        dt = datetime.fromisoformat(str(date_str))
    else:
        dt = datetime.now()
    return dt.day

# Conversion and parsing
def inscript_parse_int(text):
    """Parse string as integer."""
    try:
        return int(text)
    except ValueError:
        raise RuntimeError(f"Cannot parse as integer: {text}")

def inscript_parse_float(text):
    """Parse string as float."""
    try:
        return float(text)
    except ValueError:
        raise RuntimeError(f"Cannot parse as float: {text}")

def inscript_hex(n):
    """Convert integer to hexadecimal string."""
    return hex(int(n))

def inscript_bin(n):
    """Convert integer to binary string."""
    return bin(int(n))

def inscript_oct(n):
    """Convert integer to octal string."""
    return oct(int(n))

# List comprehension-like functions
def inscript_filter_func(predicate, items):
    """Filter items based on predicate function."""
    # This would need proper function support
    # For now, returns items where truthy
    return [item for item in items if inscript_to_bool(item)]

def inscript_map_func(func_name, items):
    """Map over items (limited support)."""
    # Limited implementation
    return items

# Utility functions  
def inscript_any_true(items):
    """Check if any item is truthy."""
    return any(inscript_to_bool(item) for item in items)

def inscript_all_true(items):
    """Check if all items are truthy."""
    return all(inscript_to_bool(item) for item in items)

def inscript_enumerate_list(items):
    """Get list of [index, item] pairs."""
    return [[i, item] for i, item in enumerate(items)]

def inscript_to_bool(value):
    """Convert to boolean."""
    if value is None or value is False:
        return False
    if value == 0 or value == "" or value == [] or value == {}:
        return False
    return True

def inscript_to_string(value):
    """Convert to string."""
    return str(value)

def inscript_to_float(value):
    """Convert to float."""
    return float(value)

def inscript_to_int(value):
    """Convert to integer."""
    return int(value)

def inscript_to_list(value):
    """Convert to list."""
    if isinstance(value, list):
        return value
    return list(value)

# Miscellaneous
def inscript_id(obj):
    """Get object id."""
    return id(obj)

def inscript_hash_obj(obj):
    """Get hash of object."""
    return hash(str(obj))

def inscript_sorted_with_reverse(items, reverse=False):
    """Sort items with reverse option."""
    return sorted(items, reverse=inscript_to_bool(reverse))

def inscript_reversed_list(items):
    """Reverse list and return as new list."""
    return list(reversed(items))

def inscript_wait(seconds):
    """Wait/sleep for seconds."""
    import time
    time.sleep(float(seconds))
    return None

def inscript_ascii(value):
    """Get ASCII codes of string."""
    return [ord(c) for c in str(value)]

def inscript_chr_code(code):
    """Get character from ASCII code."""
    return chr(int(code))

def inscript_join_list(items):
    """Join list items as string (space separated)."""
    return " ".join(str(item) for item in items)

# Built-in functions available to Inscript programs
builtin_functions = {
    # I/O
    'print': inscript_print,
    'input': inscript_input,
    
    # Type conversion
    'int': inscript_int,
    'float': inscript_float,
    'string': inscript_string,
    'list': inscript_list,
    'dict': inscript_dict,
    'boolean': inscript_boolean,
    
    # Collections
    'length': inscript_length,
    'range': inscript_range,
    'type': inscript_type,
    'contains': inscript_contains,
    
    # Collections - advanced
    'keys': inscript_keys,
    'values': inscript_values,
    'sort': inscript_sort,
    'reverse': inscript_reverse,
    
    # Math - basic
    'sum': inscript_sum,
    'min': inscript_min,
    'max': inscript_max,
    'absolute': inscript_absolute,
    'round': inscript_round,
    'power': inscript_power,
    
    # Math - advanced
    'sqrt': inscript_sqrt,
    'sin': inscript_sin,
    'cos': inscript_cos,
    'tan': inscript_tan,
    'asin': inscript_asin,
    'acos': inscript_acos,
    'atan': inscript_atan,
    'log': inscript_log,
    'log10': inscript_log10,
    'log2': inscript_log2,
    'exp': inscript_exp,
    'ceil': inscript_ceil,
    'floor': inscript_floor,
    'degrees': inscript_degrees,
    'radians': inscript_radians,
    'gcd': inscript_gcd,
    'factorial': inscript_factorial,
    'pi': inscript_pi,
    'e': inscript_e,
    'hypot': inscript_hypot,
    'fabs': inscript_fabs,
    
    # String functions
    'upper': inscript_upper,
    'lower': inscript_lower,
    'strip': inscript_strip,
    'lstrip': inscript_lstrip,
    'rstrip': inscript_rstrip,
    'replace': inscript_replace,
    'split': inscript_split,
    'join': inscript_join,
    'startswith': inscript_startswith,
    'endswith': inscript_endswith,
    'find': inscript_find,
    'rfind': inscript_rfind,
    'count': inscript_count,
    'repeat': inscript_repeat,
    'slice': inscript_slice,
    'char_at': inscript_char_at,
    'capitalize': inscript_capitalize,
    'title': inscript_title,
    'isdigit': inscript_isdigit,
    'isalpha': inscript_isalpha,
    'isalnum': inscript_isalnum,
    'isspace': inscript_isspace,
    
    # List functions
    'append': inscript_append,
    'insert': inscript_insert,
    'remove': inscript_remove_item,
    'pop': inscript_pop,
    'clear': inscript_clear,
    'copy': inscript_copy,
    'extend': inscript_extend,
    'index': inscript_index_of,
    'slice_list': inscript_slice_list,
    'flatten': inscript_flatten,
    'unique': inscript_unique,
    'zip': inscript_zip_lists,
    
    # Dictionary functions
    'get': inscript_get_dict,
    'pop_dict': inscript_pop_dict,
    'update': inscript_update_dict,
    'has_key': inscript_has_key,
    
    # Type checking
    'is_int': inscript_is_integer,
    'is_float': inscript_is_float,
    'is_string': inscript_is_string,
    'is_bool': inscript_is_boolean,
    'is_list': inscript_is_list,
    'is_dict': inscript_is_dict,
    'is_null': inscript_is_null,
    
    # File I/O
    'read': inscript_read_file,
    'write': inscript_write_file,
    'append_text': inscript_append_file,
    'readlines': inscript_readlines_file,
    'file_exists': inscript_file_exists,
    'delete_file': inscript_delete_file,
    
    # Random
    'random': inscript_random,
    'randint': inscript_randint,
    'choice': inscript_choice,
    'shuffle': inscript_shuffle_list,
    'sample': inscript_sample,
    'seed': inscript_seed,
    
    # JSON
    'to_json': inscript_to_json,
    'from_json': inscript_from_json,
    
    # Date/Time
    'now': inscript_now,
    'timestamp': inscript_timestamp,
    'year': inscript_year,
    'month': inscript_month,
    'day': inscript_day,
    
    # Parsing
    'parse_int': inscript_parse_int,
    'parse_float': inscript_parse_float,
    'hex': inscript_hex,
    'bin': inscript_bin,
    'oct': inscript_oct,
    
    # Utility
    'any': inscript_any_true,
    'all': inscript_all_true,
    'enumerate': inscript_enumerate_list,
    'enumerate': inscript_enumerate_list,
    'join_str': inscript_join_list,
    'sorted': inscript_sorted_with_reverse,
    'reversed': inscript_reversed_list,
    'wait': inscript_wait,
    'ascii': inscript_ascii,
    'chr': inscript_chr_code,
    'id': inscript_id,
    'hash': inscript_hash_obj,
    
    # System
    'exit': inscript_exit,
}
