# -*- coding: utf-8 -*-
# inscript/stdlib_extended_2.py
# General-purpose stdlib extension — Part 2 of 2
#
# Adds 14 new modules:
#   iter       — functional iterators (filter, map, reduce, zip, chain, scan, ...)
#   format     — number/string formatting (number, percent, duration, file_size, table, ...)
#   url        — URL parsing, encoding, building, joining
#   xml        — XML parse, find, find_all, get_attr, get_text, to_string
#   toml       — TOML parse, parse_file, to_string (Python 3.11+ tomllib)
#   yaml       — YAML parse, parse_file, to_string (requires pyyaml)
#   argparse   — CLI argument parsing (flag, option, positional, parse)
#   hash       — sha256, sha512, md5, blake2b, hmac, bcrypt (optional), crc32, file_hash
#   base64     — encode, decode, encode_url, decode_url, encode_bytes
#   database   — SQLite: open, exec, query, transaction, close
#   bench      — microbenchmarking: run, compare, Case
#   template   — string templates with {{var}}, {{if}}, {{for}} blocks
#   net        — synchronous TCP client/server + UDP socket
#   thread     — spawn, join, Mutex, Semaphore, Pool, Event
#                NOTE: InScript closures cannot be passed to threads — Python callables only
#
# Rules enforced throughout:
#   1. Every Python exception caught and re-raised as clean [module] Error: message
#   2. No raw Python tracebacks reach user
#   3. Graceful fallback for optional deps (bcrypt, pyyaml)

from __future__ import annotations
import sys as _sys

from stdlib import register_module


def _guard(module_name: str, fn):
    import functools
    @functools.wraps(fn)
    def _wrap(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:
            msg = str(e)
            if msg.startswith(f"[{module_name}]"):
                raise
            raise Exception(f"[{module_name}] {type(e).__name__}: {msg}") from None
    return _wrap

def _wrapmod(d: dict, name: str) -> dict:
    return {k: (_guard(name, v) if callable(v) else v) for k, v in d.items()}


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 1 — iter
# ─────────────────────────────────────────────────────────────────────────────
import itertools as _it
import functools as _ft

def _iter_filter(lst, fn): return [x for x in lst if fn(x)]
def _iter_map(lst, fn): return [fn(x) for x in lst]
def _iter_reduce(lst, initial, fn):
    acc = initial
    for x in lst: acc = fn(acc, x)
    return acc
def _iter_take(lst, n): return list(lst[:int(n)])
def _iter_skip(lst, n): return list(lst[int(n):])
def _iter_zip(*lists): return [list(t) for t in zip(*lists)]
def _iter_chain(*lists): return [x for lst in lists for x in lst]
def _iter_enumerate(lst, start=0): return [[int(start)+i, x] for i, x in enumerate(lst)]
def _iter_flat_map(lst, fn): return [y for x in lst for y in (fn(x) if isinstance(fn(x), list) else [fn(x)])]
def _iter_scan(lst, initial, fn):
    result, acc = [], initial
    for x in lst:
        acc = fn(acc, x)
        result.append(acc)
    return result
def _iter_group_by(lst, fn):
    result = {}
    for x in lst:
        k = fn(x)
        result.setdefault(k, []).append(x)
    return result
def _iter_count_by(lst):
    result = {}
    for x in lst:
        result[x] = result.get(x, 0) + 1
    return result
def _iter_any(lst, fn): return any(fn(x) for x in lst)
def _iter_all(lst, fn): return all(fn(x) for x in lst)
def _iter_none(lst, fn): return not any(fn(x) for x in lst)
def _iter_first_where(lst, fn):
    for x in lst:
        if fn(x): return x
    return None
def _iter_last_where(lst, fn):
    result = None
    for x in lst:
        if fn(x): result = x
    return result
def _iter_partition(lst, fn):
    yes, no = [], []
    for x in lst:
        (yes if fn(x) else no).append(x)
    return [yes, no]
def _iter_unique(lst):
    seen, result = set(), []
    for x in lst:
        k = x if not isinstance(x, list) else tuple(x)
        if k not in seen:
            seen.add(k)
            result.append(x)
    return result
def _iter_flatten(lst, depth=1):
    if depth == 0: return list(lst)
    result = []
    for x in lst:
        if isinstance(x, list): result.extend(_iter_flatten(x, depth-1))
        else: result.append(x)
    return result
def _iter_sliding_window(lst, n):
    n = int(n)
    return [lst[i:i+n] for i in range(len(lst)-n+1)]
def _iter_chunks(lst, size):
    size = int(size)
    return [lst[i:i+size] for i in range(0, len(lst), size)]
def _iter_interleave(*lists):
    result = []
    for row in _it.zip_longest(*lists):
        result.extend(x for x in row if x is not None)
    return result
def _iter_collect(lst): return list(lst)
def _iter_sort_by(lst, fn, reverse=False):
    return sorted(lst, key=fn, reverse=bool(reverse))
def _iter_min_by(lst, fn): return min(lst, key=fn) if lst else None
def _iter_max_by(lst, fn): return max(lst, key=fn) if lst else None
def _iter_sum_by(lst, fn): return sum(fn(x) for x in lst)
def _iter_count(lst, fn=None):
    if fn is None: return len(lst)
    return sum(1 for x in lst if fn(x))
def _iter_pairwise(lst):
    return [[lst[i], lst[i+1]] for i in range(len(lst)-1)]
def _iter_product(*lists): return [list(t) for t in _it.product(*lists)]

register_module("iter", _wrapmod({
    "filter":         _iter_filter,
    "map":            _iter_map,
    "reduce":         _iter_reduce,
    "take":           _iter_take,
    "skip":           _iter_skip,
    "zip":            _iter_zip,
    "chain":          _iter_chain,
    "enumerate":      _iter_enumerate,
    "flat_map":       _iter_flat_map,
    "scan":           _iter_scan,
    "group_by":       _iter_group_by,
    "count_by":       _iter_count_by,
    "any":            _iter_any,
    "all":            _iter_all,
    "none":           _iter_none,
    "first_where":    _iter_first_where,
    "last_where":     _iter_last_where,
    "partition":      _iter_partition,
    "unique":         _iter_unique,
    "flatten":        _iter_flatten,
    "sliding_window": _iter_sliding_window,
    "chunks":         _iter_chunks,
    "interleave":     _iter_interleave,
    "collect":        _iter_collect,
    "sort_by":        _iter_sort_by,
    "min_by":         _iter_min_by,
    "max_by":         _iter_max_by,
    "sum_by":         _iter_sum_by,
    "count":          _iter_count,
    "pairwise":       _iter_pairwise,
    "product":        _iter_product,
    "range":          lambda start, stop=None, step=1: (
        list(range(int(start), int(stop), int(step))) if stop is not None
        else list(range(int(start)))
    ),
    "repeat":         lambda val, n: [val] * int(n),
    "cycle":          lambda lst, n: list(_it.islice(_it.cycle(lst), int(n))),
    "from":           lambda x: list(x) if not isinstance(x, list) else x,
}, "iter"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 2 — format
# ─────────────────────────────────────────────────────────────────────────────
import math as _math_mod
import re as _re_fmt

def _fmt_number(n, decimals=2, thousands=",", decimal_sep="."):
    n = float(n)
    d = int(decimals)
    # Format with desired decimal places
    if d == 0:
        int_part = str(abs(int(round(n))))
    else:
        formatted = f"{abs(n):.{d}f}"
        int_part, dec_part = formatted.split(".")
    # Add thousands separator
    if thousands:
        int_part = _re_fmt.sub(r"(?<=\d)(?=(\d{3})+$)", str(thousands), int_part)
    sign = "-" if n < 0 else ""
    if d == 0:
        return f"{sign}{int_part}"
    return f"{sign}{int_part}{decimal_sep}{dec_part}"

def _fmt_percent(n, decimals=1):
    return f"{float(n)*100:.{int(decimals)}f}%"

def _fmt_duration(seconds):
    s = abs(int(seconds))
    parts = []
    if s >= 3600:   parts.append(f"{s//3600}h"); s %= 3600
    if s >= 60:     parts.append(f"{s//60}m"); s %= 60
    if s > 0 or not parts: parts.append(f"{s}s")
    return " ".join(parts)

def _fmt_duration_ms(ms):
    ms = float(ms)
    if ms >= 3600000: return f"{ms/3600000:.1f}h"
    if ms >= 60000:   return f"{ms/60000:.1f}m"
    if ms >= 1000:    return f"{ms/1000:.2f}s".rstrip("0").rstrip(".")+"s" if ms >= 1000 else f"{ms:.0f}ms"
    if ms >= 1000:    return f"{ms/1000:.1f}s"
    return f"{ms:.0f}ms"

def _fmt_file_size(n, style="decimal"):
    n = int(n)
    if style == "binary":
        units = ["B","KiB","MiB","GiB","TiB","PiB"]
        base = 1024
    else:
        units = ["B","KB","MB","GB","TB","PB"]
        base = 1000
    if n == 0: return "0 B"
    i = min(int(_math_mod.log(n, base)), len(units)-1) if n > 0 else 0
    val = n / (base ** i)
    return f"{val:.1f} {units[i]}"

def _fmt_pad_left(s, width, char=" "):
    return str(s).rjust(int(width), str(char)[0])

def _fmt_pad_right(s, width, char=" "):
    return str(s).ljust(int(width), str(char)[0])

def _fmt_pad_center(s, width, char=" "):
    return str(s).center(int(width), str(char)[0])

def _fmt_truncate(s, max_len, suffix="..."):
    s, suffix = str(s), str(suffix)
    max_len = int(max_len)
    if len(s) <= max_len: return s
    return s[:max_len - len(suffix)] + suffix

def _fmt_scientific(n, sig=3):
    return f"{float(n):.{int(sig)-1}e}"

def _fmt_hex(n, prefix=True):
    s = hex(int(n))
    return s if prefix else s[2:]

def _fmt_bin(n, prefix=True):
    s = bin(int(n))
    return s if prefix else s[2:]

def _fmt_octal(n, prefix=True):
    s = oct(int(n))
    return s if prefix else s[2:]

def _fmt_ordinal(n):
    n = int(n)
    suffix = {1:"st", 2:"nd", 3:"rd"}.get(n % 10 if n % 100 not in (11,12,13) else 0, "th")
    return f"{n}{suffix}"

def _fmt_pluralize(n, singular, plural=None):
    plural = plural or (singular + "s")
    return f"{n} {singular if int(n)==1 else plural}"

def _fmt_table(headers, rows, align="left"):
    """Render a list of rows as an ASCII table."""
    cols = len(headers)
    # Compute column widths
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row[:cols]):
            widths[i] = max(widths[i], len(str(cell)))
    def _row(cells, sep="|"):
        parts = []
        for i, cell in enumerate(cells[:cols]):
            s = str(cell)
            w = widths[i]
            if align == "right":  s = s.rjust(w)
            elif align == "center": s = s.center(w)
            else: s = s.ljust(w)
            parts.append(f" {s} ")
        return sep + sep.join(parts) + sep
    divider = "+" + "+".join("-" * (w+2) for w in widths) + "+"
    lines = [divider, _row(headers), divider]
    for row in rows:
        lines.append(_row(row))
    lines.append(divider)
    return "\n".join(lines)

def _fmt_wrap(text, width=80):
    """Word-wrap text to width."""
    import textwrap as _tw
    return _tw.fill(str(text), int(width))

def _fmt_indent(text, spaces=4, prefix=None):
    prefix = prefix or (" " * int(spaces))
    return "\n".join(prefix + line for line in str(text).splitlines())

register_module("format", _wrapmod({
    "number":    _fmt_number,
    "percent":   _fmt_percent,
    "duration":  _fmt_duration,
    "duration_ms": _fmt_duration_ms,
    "file_size": _fmt_file_size,
    "pad_left":  _fmt_pad_left,
    "pad_right": _fmt_pad_right,
    "pad_center":_fmt_pad_center,
    "truncate":  _fmt_truncate,
    "scientific":_fmt_scientific,
    "hex":       _fmt_hex,
    "bin":       _fmt_bin,
    "octal":     _fmt_octal,
    "ordinal":   _fmt_ordinal,
    "pluralize": _fmt_pluralize,
    "table":     _fmt_table,
    "wrap":      _fmt_wrap,
    "indent":    _fmt_indent,
    "repeat_str":lambda s, n: str(s) * int(n),
    "title_case":lambda s: str(s).title(),
    "snake_case":lambda s: _re_fmt.sub(r"(?<!^)(?=[A-Z])", "_", str(s)).lower(),
    "camel_case":lambda s: s[0].lower() + _re_fmt.sub(r"[_ ](.)", lambda m: m.group(1).upper(), str(s)[1:]),
}, "format"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 3 — url
# ─────────────────────────────────────────────────────────────────────────────
import urllib.parse as _urlparse

def _url_parse(s):
    p = _urlparse.urlparse(str(s))
    q = dict(_urlparse.parse_qsl(p.query))
    return {
        "scheme":   p.scheme,
        "host":     p.netloc.split(":")[0],
        "port":     int(p.netloc.split(":")[1]) if ":" in p.netloc else None,
        "path":     p.path,
        "query":    q,
        "query_string": p.query,
        "fragment": p.fragment,
        "username": p.username,
        "password": p.password,
        "full":     str(s),
    }

def _url_build(scheme, host, path="", query=None, fragment="", port=None):
    netloc = str(host) + (f":{port}" if port else "")
    qs = _urlparse.urlencode(query or {})
    return _urlparse.urlunparse((str(scheme), netloc, str(path), "", qs, str(fragment)))

def _url_join(base, *parts):
    result = str(base)
    for part in parts:
        result = _urlparse.urljoin(result, str(part))
    return result

def _url_encode(s, safe=""):
    return _urlparse.quote(str(s), safe=str(safe))

def _url_decode(s):
    return _urlparse.unquote(str(s))

def _url_encode_params(d):
    return _urlparse.urlencode({str(k): str(v) for k, v in d.items()})

def _url_decode_params(s):
    return dict(_urlparse.parse_qsl(str(s)))

def _url_is_valid(s):
    try:
        p = _urlparse.urlparse(str(s))
        return bool(p.scheme and p.netloc)
    except Exception:
        return False

register_module("url", _wrapmod({
    "parse":         _url_parse,
    "build":         _url_build,
    "join":          _url_join,
    "encode":        _url_encode,
    "decode":        _url_decode,
    "encode_params": _url_encode_params,
    "decode_params": _url_decode_params,
    "is_valid":      _url_is_valid,
    "get_scheme":    lambda s: _urlparse.urlparse(str(s)).scheme,
    "get_host":      lambda s: _urlparse.urlparse(str(s)).netloc.split(":")[0],
    "get_path":      lambda s: _urlparse.urlparse(str(s)).path,
    "get_query":     lambda s: dict(_urlparse.parse_qsl(_urlparse.urlparse(str(s)).query)),
    "strip_query":   lambda s: _urlparse.urlunparse(_urlparse.urlparse(str(s))._replace(query="", fragment="")),
}, "url"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 4 — xml
# ─────────────────────────────────────────────────────────────────────────────
import xml.etree.ElementTree as _ET

def _xml_parse(s):
    return _ET.fromstring(str(s))

def _xml_parse_file(path):
    tree = _ET.parse(str(path))
    return tree.getroot()

def _xml_find(node, tag):
    return node.find(str(tag))

def _xml_find_all(node, tag):
    return node.findall(str(tag))

def _xml_get_attr(node, attr, default=None):
    return node.get(str(attr), default)

def _xml_get_text(node):
    return (node.text or "").strip()

def _xml_get_tail(node):
    return (node.tail or "").strip()

def _xml_get_tag(node):
    return node.tag

def _xml_children(node):
    return list(node)

def _xml_to_string(node, pretty=False):
    if pretty:
        _ET.indent(node, space="  ")
    return _ET.tostring(node, encoding="unicode")

def _xml_to_dict(node):
    """Convert an XML element tree to a nested dict."""
    d = {}
    for attr_key, attr_val in node.attrib.items():
        d[f"@{attr_key}"] = attr_val
    text = (node.text or "").strip()
    if text:
        d["#text"] = text
    children = list(node)
    if children:
        child_dict = {}
        for child in children:
            cd = _xml_to_dict(child)
            if child.tag in child_dict:
                if not isinstance(child_dict[child.tag], list):
                    child_dict[child.tag] = [child_dict[child.tag]]
                child_dict[child.tag].append(cd)
            else:
                child_dict[child.tag] = cd
        d.update(child_dict)
    return d if d else text

def _xml_new_element(tag, text=None, attrs=None):
    el = _ET.Element(str(tag), attrib={str(k): str(v) for k, v in (attrs or {}).items()})
    if text is not None:
        el.text = str(text)
    return el

def _xml_add_child(parent, child):
    parent.append(child)
    return parent

def _xml_set_attr(node, key, value):
    node.set(str(key), str(value))
    return node

def _xml_set_text(node, text):
    node.text = str(text)
    return node

def _xml_write(node, path, pretty=True):
    if pretty:
        _ET.indent(node, space="  ")
    tree = _ET.ElementTree(node)
    tree.write(str(path), encoding="unicode", xml_declaration=False)

def _xml_xpath(node, expr):
    """Basic XPath support via ElementTree's findall."""
    return node.findall(str(expr))

register_module("xml", _wrapmod({
    "parse":       _xml_parse,
    "parse_file":  _xml_parse_file,
    "find":        _xml_find,
    "find_all":    _xml_find_all,
    "get_attr":    _xml_get_attr,
    "get_text":    _xml_get_text,
    "get_tail":    _xml_get_tail,
    "get_tag":     _xml_get_tag,
    "children":    _xml_children,
    "to_string":   _xml_to_string,
    "to_dict":     _xml_to_dict,
    "new":         _xml_new_element,
    "add_child":   _xml_add_child,
    "set_attr":    _xml_set_attr,
    "set_text":    _xml_set_text,
    "write":       _xml_write,
    "xpath":       _xml_xpath,
    "attribs":     lambda node: dict(node.attrib),
}, "xml"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 5 — toml
# ─────────────────────────────────────────────────────────────────────────────
import tomllib as _tomllib_mod

def _toml_parse(s):
    return _tomllib_mod.loads(str(s))

def _toml_parse_file(path):
    with open(str(path), "rb") as f:
        return _tomllib_mod.load(f)

def _toml_to_string(data):
    """Pure-Python TOML serializer (no tomli_w needed)."""
    lines = []
    def _val(v):
        if isinstance(v, bool):   return "true" if v else "false"
        if isinstance(v, int):    return str(v)
        if isinstance(v, float):  return str(v)
        if isinstance(v, str):    return '"' + v.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n') + '"'
        if isinstance(v, list):
            inner = ", ".join(_val(x) for x in v)
            return f"[{inner}]"
        return str(v)
    def _section(d, prefix=""):
        simple, tables = {}, {}
        for k, v in d.items():
            if isinstance(v, dict): tables[k] = v
            else: simple[k] = v
        for k, v in simple.items():
            lines.append(f"{k} = {_val(v)}")
        for k, v in tables.items():
            header = f"{prefix}.{k}" if prefix else k
            lines.append(f"\n[{header}]")
            _section(v, header)
    _section(data)
    return "\n".join(lines)

def _toml_write(path, data):
    with open(str(path), "w", encoding="utf-8") as f:
        f.write(_toml_to_string(data))

def _toml_get(data, key_path, default=None):
    """Dot-notation getter: toml.get(cfg, 'package.name')"""
    parts = str(key_path).split(".")
    cur = data
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

register_module("toml", _wrapmod({
    "parse":      _toml_parse,
    "parse_file": _toml_parse_file,
    "to_string":  _toml_to_string,
    "write":      _toml_write,
    "get":        _toml_get,
}, "toml"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 6 — yaml
# ─────────────────────────────────────────────────────────────────────────────
try:
    import yaml as _yaml_mod
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

def _yaml_check():
    if not _YAML_AVAILABLE:
        raise Exception("[yaml] pyyaml not installed — run: pip install pyyaml")

def _yaml_parse(s):
    _yaml_check()
    return _yaml_mod.safe_load(str(s))

def _yaml_parse_all(s):
    _yaml_check()
    return list(_yaml_mod.safe_load_all(str(s)))

def _yaml_parse_file(path):
    _yaml_check()
    with open(str(path), encoding="utf-8") as f:
        return _yaml_mod.safe_load(f)

def _yaml_to_string(data, indent=2):
    _yaml_check()
    return _yaml_mod.dump(data, default_flow_style=False, allow_unicode=True, indent=int(indent))

def _yaml_write(path, data, indent=2):
    _yaml_check()
    with open(str(path), "w", encoding="utf-8") as f:
        _yaml_mod.dump(data, f, default_flow_style=False, allow_unicode=True, indent=int(indent))

def _yaml_get(data, key_path, default=None):
    """Dot-notation getter: yaml.get(data, 'server.host')"""
    parts = str(key_path).split(".")
    cur = data
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

register_module("yaml", _wrapmod({
    "parse":      _yaml_parse,
    "parse_all":  _yaml_parse_all,
    "parse_file": _yaml_parse_file,
    "to_string":  _yaml_to_string,
    "write":      _yaml_write,
    "get":        _yaml_get,
    "available":  lambda: _YAML_AVAILABLE,
}, "yaml"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 7 — argparse
# ─────────────────────────────────────────────────────────────────────────────
import argparse as _ap_mod

class _ArgSpec:
    """Internal: one argument specification."""
    def __init__(self, kind, name, short=None, help="", default=None,
                 type_name="string", required=False, choices=None):
        self.kind       = kind       # "flag", "option", "positional"
        self.name       = name       # "--output" or "input"
        self.short      = short      # "-o"
        self.help       = help
        self.default    = default
        self.type_name  = type_name  # "string", "int", "float", "bool"
        self.required   = required
        self.choices    = choices

def _ap_flag(name, short=None, help=""):
    return _ArgSpec("flag", str(name), short=short, help=str(help))

def _ap_option(name, short=None, default=None, help="", type="string",
               required=False, choices=None):
    return _ArgSpec("option", str(name), short=short, help=str(help),
                    default=default, type_name=str(type), required=bool(required),
                    choices=choices)

def _ap_positional(name, help="", default=None, type="string"):
    return _ArgSpec("positional", str(name), help=str(help),
                    default=default, type_name=str(type))

def _ap_parse(specs, args=None):
    """Parse arguments from sys.argv[1:] or a custom list."""
    parser = _ap_mod.ArgumentParser(add_help=True)
    _TYPE_MAP = {"string": str, "int": int, "float": float, "bool": bool}
    for spec in specs:
        t = _TYPE_MAP.get(str(spec.type_name), str)
        if spec.kind == "flag":
            names = [spec.name]
            if spec.short: names.append(spec.short)
            parser.add_argument(*names, action="store_true", help=spec.help, default=False)
        elif spec.kind == "option":
            names = [spec.name]
            if spec.short: names.append(spec.short)
            kw = {"help": spec.help, "default": spec.default, "type": t}
            if spec.required: kw["required"] = True
            if spec.choices:  kw["choices"] = spec.choices
            parser.add_argument(*names, **kw)
        elif spec.kind == "positional":
            kw = {"help": spec.help, "type": t}
            if spec.default is not None: kw["nargs"] = "?"
            parser.add_argument(spec.name.lstrip("-"), **kw)
    if args is not None:
        ns = parser.parse_args([str(a) for a in args])
    else:
        ns = parser.parse_args()
    # Convert Namespace to dict with clean keys
    result = {}
    for k, v in vars(ns).items():
        clean_key = k.replace("-", "_").lstrip("_")
        result[clean_key] = v
    return result

def _ap_help(specs):
    """Generate a help string without actually parsing."""
    lines = ["Arguments:"]
    for spec in specs:
        if spec.kind == "flag":
            flag = f"  {spec.name}"
            if spec.short: flag += f", {spec.short}"
            lines.append(f"{flag:<30} {spec.help}")
        elif spec.kind == "option":
            opt = f"  {spec.name} <{spec.type_name}>"
            if spec.short: opt = f"  {spec.name}, {spec.short} <{spec.type_name}>"
            default = f" (default: {spec.default})" if spec.default is not None else ""
            lines.append(f"{opt:<30} {spec.help}{default}")
        elif spec.kind == "positional":
            lines.append(f"  {spec.name:<28} {spec.help}")
    return "\n".join(lines)

register_module("argparse", _wrapmod({
    "flag":       _ap_flag,
    "option":     _ap_option,
    "positional": _ap_positional,
    "parse":      _ap_parse,
    "help":       _ap_help,
}, "argparse"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 8 — hash
# ─────────────────────────────────────────────────────────────────────────────
import hashlib as _hl
import hmac as _hmac_mod
import binascii as _ba

def _hash_bytes(data):
    if isinstance(data, str):
        return data.encode("utf-8")
    elif isinstance(data, (list, tuple)):
        return bytes(int(b) for b in data)
    elif isinstance(data, bytes):
        return data
    return str(data).encode("utf-8")

def _hash_sha256(data):
    return _hl.sha256(_hash_bytes(data)).hexdigest()

def _hash_sha512(data):
    return _hl.sha512(_hash_bytes(data)).hexdigest()

def _hash_sha1(data):
    return _hl.sha1(_hash_bytes(data)).hexdigest()  # noqa: S324 — user-requested

def _hash_md5(data):
    return _hl.md5(_hash_bytes(data)).hexdigest()

def _hash_blake2b(data, digest_size=32):
    return _hl.blake2b(_hash_bytes(data), digest_size=int(digest_size)).hexdigest()

def _hash_blake2s(data, digest_size=16):
    return _hl.blake2s(_hash_bytes(data), digest_size=int(digest_size)).hexdigest()

def _hash_hmac(secret, data, algorithm="sha256"):
    alg = str(algorithm).lower()
    return _hmac_mod.new(_hash_bytes(secret), _hash_bytes(data), alg).hexdigest()

def _hash_crc32(data):
    import zlib as _zl
    return _zl.crc32(_hash_bytes(data)) & 0xFFFFFFFF

def _hash_adler32(data):
    import zlib as _zl
    return _zl.adler32(_hash_bytes(data)) & 0xFFFFFFFF

def _hash_file(path, algorithm="sha256"):
    h = _hl.new(str(algorithm).lower())
    with open(str(path), "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def _hash_compare(a, b):
    """Constant-time comparison to prevent timing attacks."""
    return _hmac_mod.compare_digest(str(a), str(b))

def _hash_bcrypt_hash(password):
    try:
        import bcrypt as _bcrypt
        return _bcrypt.hashpw(str(password).encode(), _bcrypt.gensalt()).decode()
    except ImportError:
        raise Exception("[hash] bcrypt not installed — run: pip install bcrypt")

def _hash_bcrypt_verify(password, hashed):
    try:
        import bcrypt as _bcrypt
        return _bcrypt.checkpw(str(password).encode(), str(hashed).encode())
    except ImportError:
        raise Exception("[hash] bcrypt not installed — run: pip install bcrypt")

def _hash_pbkdf2(password, salt, iterations=260000, algorithm="sha256", length=32):
    return _hl.pbkdf2_hmac(
        str(algorithm), _hash_bytes(password), _hash_bytes(salt),
        int(iterations), dklen=int(length)
    ).hex()

def _hash_bytes_to_hex(data):
    return _ba.hexlify(_hash_bytes(data)).decode()

def _hash_hex_to_bytes(hex_str):
    return list(_ba.unhexlify(str(hex_str)))

register_module("hash", _wrapmod({
    "sha256":        _hash_sha256,
    "sha512":        _hash_sha512,
    "sha1":          _hash_sha1,
    "md5":           _hash_md5,
    "blake2b":       _hash_blake2b,
    "blake2s":       _hash_blake2s,
    "blake3":        _hash_blake2b,   # alias — use blake2b as blake3 substitute
    "hmac":          _hash_hmac,
    "crc32":         _hash_crc32,
    "adler32":       _hash_adler32,
    "file_hash":     _hash_file,
    "compare":       _hash_compare,
    "bcrypt_hash":   _hash_bcrypt_hash,
    "bcrypt_verify": _hash_bcrypt_verify,
    "pbkdf2":        _hash_pbkdf2,
    "to_hex":        _hash_bytes_to_hex,
    "from_hex":      _hash_hex_to_bytes,
    "algorithms":    lambda: sorted(_hl.algorithms_available),
}, "hash"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 9 — base64
# ─────────────────────────────────────────────────────────────────────────────
import base64 as _b64_mod

def _b64_encode(data):
    if isinstance(data, str):
        raw = data.encode("utf-8")
    elif isinstance(data, (list, tuple)):
        raw = bytes(int(b) for b in data)
    else:
        raw = data
    return _b64_mod.b64encode(raw).decode("ascii")

def _b64_decode(s):
    return _b64_mod.b64decode(str(s)).decode("utf-8")

def _b64_decode_bytes(s):
    return list(_b64_mod.b64decode(str(s)))

def _b64_encode_url(data):
    if isinstance(data, str):
        raw = data.encode("utf-8")
    elif isinstance(data, (list, tuple)):
        raw = bytes(int(b) for b in data)
    else:
        raw = data
    return _b64_mod.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def _b64_decode_url(s):
    # Add padding
    s = str(s)
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return _b64_mod.urlsafe_b64decode(s).decode("utf-8")

def _b64_encode_bytes(byte_list):
    raw = bytes(int(b) for b in byte_list)
    return _b64_mod.b64encode(raw).decode("ascii")

def _b64_is_valid(s):
    try:
        _b64_mod.b64decode(str(s), validate=True)
        return True
    except Exception:
        return False

register_module("base64", _wrapmod({
    "encode":       _b64_encode,
    "decode":       _b64_decode,
    "decode_bytes": _b64_decode_bytes,
    "encode_url":   _b64_encode_url,
    "decode_url":   _b64_decode_url,
    "encode_bytes": _b64_encode_bytes,
    "is_valid":     _b64_is_valid,
}, "base64"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 10 — database (SQLite)
# ─────────────────────────────────────────────────────────────────────────────
import sqlite3 as _sqlite3

class _Database:
    def __init__(self, path):
        self._path = str(path)
        self._conn = _sqlite3.connect(
            self._path,
            check_same_thread=False,
            detect_types=_sqlite3.PARSE_DECLTYPES
        )
        self._conn.row_factory = _sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")

    def exec(self, sql, params=None):
        try:
            cur = self._conn.execute(str(sql), params or [])
            self._conn.commit()
            return cur.rowcount
        except Exception as e:
            raise Exception(f"[database] SQL error: {e}") from None

    def exec_many(self, sql, rows):
        try:
            self._conn.executemany(str(sql), rows)
            self._conn.commit()
        except Exception as e:
            raise Exception(f"[database] SQL error: {e}") from None

    def query(self, sql, params=None):
        try:
            cur = self._conn.execute(str(sql), params or [])
            return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            raise Exception(f"[database] SQL error: {e}") from None

    def query_one(self, sql, params=None):
        try:
            cur = self._conn.execute(str(sql), params or [])
            row = cur.fetchone()
            return dict(row) if row else None
        except Exception as e:
            raise Exception(f"[database] SQL error: {e}") from None

    def transaction(self, fn):
        try:
            with self._conn:
                fn()
        except Exception as e:
            raise Exception(f"[database] Transaction error: {e}") from None

    def last_insert_id(self):
        return self._conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def table_exists(self, name):
        row = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", [str(name)]
        ).fetchone()
        return row is not None

    def list_tables(self):
        rows = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]

    def close(self):
        self._conn.close()

    def __repr__(self):
        return f"Database({self._path!r})"

def _db_open(path):
    return _Database(path)

def _db_open_memory():
    return _Database(":memory:")

register_module("database", _wrapmod({
    "open":        _db_open,
    "open_memory": _db_open_memory,
}, "database"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 11 — bench
# ─────────────────────────────────────────────────────────────────────────────
import time as _time_bench
import statistics as _stats

class _BenchCase:
    def __init__(self, name, fn):
        self.name = str(name)
        self.fn   = fn
    def __repr__(self):
        return f"BenchCase({self.name!r})"

def _bench_run(name, fn, warmup=3, runs=20):
    name = str(name)
    warmup = int(warmup)
    runs = int(runs)
    # Warmup
    for _ in range(warmup):
        fn()
    # Timed runs
    times = []
    for _ in range(runs):
        t0 = _time_bench.perf_counter()
        fn()
        times.append((_time_bench.perf_counter() - t0) * 1000)  # ms
    result = {
        "name":    name,
        "runs":    runs,
        "mean_ms": round(_stats.mean(times), 4),
        "min_ms":  round(min(times), 4),
        "max_ms":  round(max(times), 4),
        "std_ms":  round(_stats.stdev(times) if len(times)>1 else 0.0, 4),
        "total_ms":round(sum(times), 4),
    }
    return result

def _bench_compare(cases, warmup=3, runs=20):
    results = []
    for case in cases:
        r = _bench_run(case.name, case.fn, warmup=warmup, runs=runs)
        results.append(r)
    if not results:
        return results
    # Print comparison table
    results.sort(key=lambda x: x["mean_ms"])
    fastest = results[0]["mean_ms"]
    headers = ["Name", "Mean ms", "Min ms", "Max ms", "Std ms", "vs fastest"]
    rows = []
    for r in results:
        ratio = f"{r['mean_ms']/fastest:.2f}x" if fastest > 0 else "1.00x"
        rows.append([r["name"], r["mean_ms"], r["min_ms"], r["max_ms"], r["std_ms"], ratio])
    from stdlib_extended_2 import _fmt_table
    print(_fmt_table(headers, rows))
    return results

def _bench_time(fn):
    """Simple: time a single call, return ms."""
    t0 = _time_bench.perf_counter()
    result = fn()
    elapsed_ms = (_time_bench.perf_counter() - t0) * 1000
    return {"result": result, "elapsed_ms": round(elapsed_ms, 4)}

register_module("bench", _wrapmod({
    "run":     _bench_run,
    "compare": _bench_compare,
    "time":    _bench_time,
    "Case":    lambda name, fn: _BenchCase(name, fn),
}, "bench"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 12 — template
# ─────────────────────────────────────────────────────────────────────────────
import re as _re_tmpl

class _Template:
    def __init__(self, source: str):
        self.source = str(source)
    def render(self, ctx: dict) -> str:
        return _tmpl_render(self.source, ctx)
    def __repr__(self):
        preview = self.source[:40].replace("\n", "\\n")
        return f"Template({preview!r}...)"

def _tmpl_render(source: str, ctx: dict) -> str:
    """
    Mini template engine supporting:
      {{var}}           — variable substitution
      {{if expr}}...{{end}}         — conditional (expr is a key name, truthy check)
      {{for item in list}}...{{end}} — loop
      {{! comment }}    — comment (removed)
    """
    src = str(source)
    # Remove comments
    src = _re_tmpl.sub(r'\{\{!.*?\}\}', '', src, flags=_re_tmpl.DOTALL)
    # Process
    return _tmpl_process(src, dict(ctx))

def _tmpl_process(src: str, ctx: dict) -> str:
    result = []
    i = 0
    while i < len(src):
        start = src.find("{{", i)
        if start == -1:
            result.append(src[i:])
            break
        result.append(src[i:start])
        end = src.find("}}", start)
        if end == -1:
            result.append(src[start:])
            break
        tag = src[start+2:end].strip()
        i = end + 2

        if tag.startswith("if "):
            # Find matching {{end}}
            expr = tag[3:].strip()
            inner, i = _tmpl_find_block(src, i)
            val = ctx.get(expr, None)
            if val is None:
                # Try simple truthiness of Python expression using ctx vars
                try:
                    val = eval(expr, {"__builtins__": {}}, ctx)
                except Exception:
                    val = False
            if val:
                result.append(_tmpl_process(inner, ctx))

        elif tag.startswith("for ") and " in " in tag:
            # {{for item in items}}
            m = _re_tmpl.match(r"for (\w+) in (\w+)", tag)
            if m:
                var_name, list_name = m.group(1), m.group(2)
                inner, i = _tmpl_find_block(src, i)
                items = ctx.get(list_name, [])
                for item in items:
                    sub_ctx = {**ctx, var_name: item}
                    result.append(_tmpl_process(inner, sub_ctx))

        elif tag.startswith("else"):
            # {{else}} handled by if block — skip standalone else
            pass

        else:
            # Variable substitution: {{name}} or {{name|default}}
            if "|" in tag:
                key, default_val = tag.split("|", 1)
                val = ctx.get(key.strip(), default_val.strip())
            else:
                val = ctx.get(tag, "")
            result.append(str(val) if val is not None else "")

    return "".join(result)

def _tmpl_find_block(src: str, start: int):
    """Find content between current position and matching {{end}}, handling nesting."""
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        open_idx  = src.find("{{", i)
        close_idx = src.find("{{end}}", i)
        if open_idx == -1 and close_idx == -1:
            break
        if open_idx != -1 and (close_idx == -1 or open_idx < close_idx):
            tag_end = src.find("}}", open_idx)
            if tag_end != -1:
                tag = src[open_idx+2:tag_end].strip()
                if tag.startswith(("if ", "for ")):
                    depth += 1
                i = tag_end + 2
        else:
            if depth == 1:
                inner = src[start:close_idx]
                return inner, close_idx + 7  # len("{{end}}")
            depth -= 1
            i = close_idx + 7
    return src[start:], len(src)

def _tmpl_compile(source):
    return _Template(source)

def _tmpl_from_file(path):
    with open(str(path), encoding="utf-8") as f:
        return _Template(f.read())

def _tmpl_render_string(source, ctx):
    return _tmpl_render(source, ctx)

register_module("template", _wrapmod({
    "compile":   _tmpl_compile,
    "from_file": _tmpl_from_file,
    "render":    lambda tmpl, ctx: (tmpl.render(ctx) if isinstance(tmpl, _Template) else _tmpl_render(str(tmpl), ctx)),
    "render_str":_tmpl_render_string,
}, "template"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 13 — net (synchronous TCP/UDP)
# ─────────────────────────────────────────────────────────────────────────────
import socket as _socket_mod
import threading as _net_threading
import struct as _struct

class _TcpClient:
    def __init__(self, host, port, timeout=30):
        self._sock = _socket_mod.socket(_socket_mod.AF_INET, _socket_mod.SOCK_STREAM)
        self._sock.settimeout(float(timeout))
        self._sock.connect((str(host), int(port)))
    def send(self, data):
        if isinstance(data, str): data = data.encode("utf-8")
        elif isinstance(data, list): data = bytes(int(b) for b in data)
        self._sock.sendall(data); return None
    def recv(self, size=4096):
        data = self._sock.recv(int(size))
        try:
            return data.decode("utf-8")
        except Exception:
            return list(data)
    def recv_bytes(self, size=4096):
        return list(self._sock.recv(int(size)))
    def close(self):
        self._sock.close(); return None
    def set_timeout(self, seconds):
        self._sock.settimeout(float(seconds)); return None
    def local_addr(self):
        return list(self._sock.getsockname())
    def peer_addr(self):
        return list(self._sock.getpeername())
    def __repr__(self):
        return f"TcpClient(peer={self._sock.getpeername()})"


class _TcpConnection:
    """One side of an accepted server connection."""
    def __init__(self, sock, addr):
        self._sock = sock
        self._addr = addr
        self.id = f"{addr[0]}:{addr[1]}"
    def send(self, data):
        if isinstance(data, str): data = data.encode("utf-8")
        elif isinstance(data, list): data = bytes(int(b) for b in data)
        try: self._sock.sendall(data)
        except Exception: pass
        return None
    def recv(self, size=4096):
        try:
            data = self._sock.recv(int(size))
            if not data: return ""
            try: return data.decode("utf-8")
            except Exception: return list(data)
        except Exception:
            return ""
    def recv_bytes(self, size=4096):
        try: return list(self._sock.recv(int(size)))
        except Exception: return []
    def close(self):
        try: self._sock.close()
        except Exception: pass
        return None
    def addr(self):
        return {"host": self._addr[0], "port": self._addr[1]}
    def __repr__(self):
        return f"TcpConnection(id={self.id!r})"


class _TcpServer:
    """Simple synchronous TCP server with threaded connection handling."""
    def __init__(self, host="0.0.0.0", port=8080, backlog=10):
        self._host = str(host)
        self._port = int(port)
        self._sock = _socket_mod.socket(_socket_mod.AF_INET, _socket_mod.SOCK_STREAM)
        self._sock.setsockopt(_socket_mod.SOL_SOCKET, _socket_mod.SO_REUSEADDR, 1)
        self._sock.bind((self._host, self._port))
        self._sock.listen(int(backlog))
        self._on_connect_cb = None
        self._running = False
    def on_connect(self, fn):
        self._on_connect_cb = fn; return self
    def listen(self, blocking=True):
        self._running = True
        def _accept_loop():
            while self._running:
                try:
                    client_sock, addr = self._sock.accept()
                    conn = _TcpConnection(client_sock, addr)
                    if self._on_connect_cb:
                        t = _net_threading.Thread(target=self._on_connect_cb,
                                                  args=(conn,), daemon=True)
                        t.start()
                except Exception:
                    if self._running: raise
        if blocking:
            _accept_loop()
        else:
            t = _net_threading.Thread(target=_accept_loop, daemon=True)
            t.start()
    def stop(self):
        self._running = False
        try: self._sock.close()
        except Exception: pass
    def __repr__(self):
        return f"TcpServer({self._host}:{self._port})"


class _UdpSocket:
    def __init__(self, timeout=None):
        self._sock = _socket_mod.socket(_socket_mod.AF_INET, _socket_mod.SOCK_DGRAM)
        if timeout: self._sock.settimeout(float(timeout))
    def bind(self, host, port):
        self._sock.bind((str(host), int(port))); return self
    def send_to(self, host, port, data):
        if isinstance(data, str): data = data.encode("utf-8")
        elif isinstance(data, list): data = bytes(int(b) for b in data)
        self._sock.sendto(data, (str(host), int(port))); return None
    def recv_from(self, size=4096):
        data, addr = self._sock.recvfrom(int(size))
        try: msg = data.decode("utf-8")
        except Exception: msg = list(data)
        return [msg, {"host": addr[0], "port": addr[1]}]
    def close(self):
        self._sock.close(); return None
    def set_timeout(self, s):
        self._sock.settimeout(float(s)); return self
    def __repr__(self):
        return "UdpSocket()"

def _net_resolve(hostname):
    return _socket_mod.gethostbyname(str(hostname))

def _net_local_ip():
    try:
        s = _socket_mod.socket(_socket_mod.AF_INET, _socket_mod.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def _net_is_port_open(host, port, timeout=2):
    try:
        s = _socket_mod.socket(_socket_mod.AF_INET, _socket_mod.SOCK_STREAM)
        s.settimeout(float(timeout))
        s.connect((str(host), int(port)))
        s.close()
        return True
    except Exception:
        return False

register_module("net", _wrapmod({
    "TcpClient":   lambda host, port, timeout=30: _TcpClient(host, port, timeout),
    "TcpServer":   lambda host="0.0.0.0", port=8080: _TcpServer(host, port),
    "UdpSocket":   lambda timeout=None: _UdpSocket(timeout),
    "resolve":     _net_resolve,
    "local_ip":    _net_local_ip,
    "is_port_open":_net_is_port_open,
    "hostname":    lambda: _socket_mod.gethostname(),
}, "net"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 14 — thread
# ─────────────────────────────────────────────────────────────────────────────
# ⚠️ CRITICAL CONSTRAINT:
#   InScript closures CANNOT be safely passed to threads.
#   The tree-walk interpreter is NOT thread-safe.
#   Only Python callables should be used as thread functions.
#   This restriction is lifted when the bytecode VM (Phase 6) is complete.
#
#   InScript-level usage example:
#       import "thread" as T
#       let mu = T.Mutex()
#       let t  = T.spawn(some_python_callable)
#       t.join()

import threading as _threading
import queue as _queue_mod
import concurrent.futures as _futures

class _Thread:
    def __init__(self, fn, args=None, daemon=True):
        self._fn   = fn
        self._args = list(args or [])
        self._exc  = None
        self._result = None
        def _run():
            try:
                self._result = fn(*self._args)
            except Exception as e:
                self._exc = e
        self._t = _threading.Thread(target=_run, daemon=bool(daemon))
        self._t.start()
    def join(self, timeout=None):
        self._t.join(timeout=float(timeout) if timeout else None)
        if self._exc:
            raise Exception(f"[thread] Thread raised: {self._exc}")
        return self._result
    def is_alive(self):
        return self._t.is_alive()
    def result(self):
        return self._result
    def __repr__(self):
        return f"Thread(alive={self._t.is_alive()})"


class _Mutex:
    def __init__(self):
        self._lock = _threading.Lock()
    def lock(self):
        self._lock.acquire(); return None
    def unlock(self):
        self._lock.release(); return None
    def try_lock(self):
        return self._lock.acquire(blocking=False)
    def with_lock(self, fn):
        with self._lock: return fn()
    def __repr__(self):
        return f"Mutex(locked={self._lock.locked()})"


class _RWLock:
    """Reader-Writer lock: multiple simultaneous readers, exclusive writers."""
    def __init__(self):
        self._read_count = 0
        self._read_lock  = _threading.Lock()
        self._write_lock = _threading.Lock()
    def read_lock(self):
        with self._read_lock:
            self._read_count += 1
            if self._read_count == 1:
                self._write_lock.acquire()
    def read_unlock(self):
        with self._read_lock:
            self._read_count -= 1
            if self._read_count == 0:
                self._write_lock.release()
    def write_lock(self):
        self._write_lock.acquire()
    def write_unlock(self):
        self._write_lock.release()


class _Semaphore:
    def __init__(self, value=1):
        self._sem = _threading.Semaphore(int(value))
    def acquire(self): self._sem.acquire(); return None
    def release(self): self._sem.release(); return None
    def try_acquire(self): return self._sem.acquire(blocking=False)


class _Event:
    def __init__(self):
        self._ev = _threading.Event()
    def set(self): self._ev.set(); return None
    def clear(self): self._ev.clear(); return None
    def wait(self, timeout=None):
        return self._ev.wait(timeout=float(timeout) if timeout else None)
    def is_set(self): return self._ev.is_set()


class _Channel:
    """Thread-safe message channel (like Go channels, bounded)."""
    def __init__(self, capacity=0):
        self._q = _queue_mod.Queue(maxsize=int(capacity))
    def send(self, value, timeout=None):
        self._q.put(value, timeout=float(timeout) if timeout else None); return None
    def recv(self, timeout=None):
        return self._q.get(timeout=float(timeout) if timeout else None)
    def try_recv(self):
        try: return [True, self._q.get_nowait()]
        except _queue_mod.Empty: return [False, None]
    def size(self): return self._q.qsize()
    def is_empty(self): return self._q.empty()


class _Pool:
    """Thread pool backed by concurrent.futures.ThreadPoolExecutor."""
    def __init__(self, workers=4):
        self._ex = _futures.ThreadPoolExecutor(max_workers=int(workers))
        self._futures = []
    def submit(self, fn, *args):
        f = self._ex.submit(fn, *args)
        self._futures.append(f)
        return f
    def map(self, fn, items):
        return list(self._ex.map(fn, items))
    def wait(self):
        _futures.wait(self._futures)
        for f in self._futures:
            if f.exception():
                raise Exception(f"[thread] Pool task raised: {f.exception()}")
    def shutdown(self, wait=True):
        self._ex.shutdown(wait=bool(wait))
    def __repr__(self):
        return f"Pool(workers={self._ex._max_workers})"


def _thread_spawn(fn, args=None, daemon=True):
    return _Thread(fn, args=args, daemon=daemon)

def _thread_run(fn, args=None):
    """Spawn a thread and wait for its result — synchronous convenience wrapper."""
    t = _Thread(fn, args=args, daemon=True)
    return t.join(timeout=30)

def _thread_spawn_many(n, fn):
    return [_Thread(fn, args=[i]) for i in range(int(n))]

def _thread_join_all(threads, timeout=None):
    results = []
    for t in threads:
        results.append(t.join(timeout=timeout))
    return results

def _thread_sleep(seconds):
    import time as _t
    _t.sleep(float(seconds)); return None

def _thread_current_id():
    return _threading.get_ident()

def _thread_count():
    return _threading.active_count()

register_module("thread", _wrapmod({
    "spawn":       _thread_spawn,
    "run":         _thread_run,
    "spawn_many":  _thread_spawn_many,
    "join_all":    _thread_join_all,
    "sleep":       _thread_sleep,
    "current_id":  _thread_current_id,
    "count":       _thread_count,
    "Mutex":       lambda: _Mutex(),
    "RWLock":      lambda: _RWLock(),
    "Semaphore":   lambda value=1: _Semaphore(value),
    "Event":       lambda: _Event(),
    "Channel":     lambda capacity=0: _Channel(capacity),
    "Pool":        lambda workers=4: _Pool(workers),
    # ⚠️ Warning exposed as a string constant
    "THREAD_SAFETY_NOTE": (
        "InScript closures cannot be passed to threads — interpreter is not thread-safe. "
        "Use Python callables only. This restriction is lifted in Phase 6 (bytecode VM)."
    ),
}, "thread"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE — signal  (typed pub/sub signal channels)
# ─────────────────────────────────────────────────────────────────────────────

class _Signal:
    """A typed pub/sub signal. Listeners are InScript callables."""
    def __init__(self, name="signal"):
        self._name      = name
        self._listeners = []
        self._interp    = None    # set by _wire_interp when first used in REPL

    def connect(self, fn):
        self._listeners.append(fn)
        return None

    def disconnect(self, fn):
        self._listeners = [f for f in self._listeners if f is not fn]
        return None

    def emit(self, *args):
        for fn in list(self._listeners):
            if callable(fn):
                fn(*args)
        return None

    def once(self, fn):
        """Connect a listener that auto-disconnects after first emit."""
        wrapper = [None]
        def _once(*args):
            fn(*args)
            self.disconnect(wrapper[0])
        wrapper[0] = _once
        self.connect(wrapper[0])
        return None

    def clear(self):
        self._listeners.clear()
        return None

    def listener_count(self):
        return len(self._listeners)

    def __repr__(self):
        return f"Signal({self._name!r}, {len(self._listeners)} listeners)"


register_module("signal", _wrapmod({
    "Signal":          lambda name="signal": _Signal(name),
    "connect":         lambda sig, fn: sig.connect(fn),
    "disconnect":      lambda sig, fn: sig.disconnect(fn),
    "emit":            lambda sig, *args: sig.emit(*args),
    "once":            lambda sig, fn: sig.once(fn),
    "clear":           lambda sig: sig.clear(),
    "listener_count":  lambda sig: sig.listener_count(),
}, "signal"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE — vec  (2D/3D vector math helpers without needing Vec2/Vec3 types)
# ─────────────────────────────────────────────────────────────────────────────

import math as _math

def _v2(x, y):           return [float(x), float(y)]
def _v3(x, y, z):        return [float(x), float(y), float(z)]
def _v2_add(a, b):       return [a[0]+b[0], a[1]+b[1]]
def _v2_sub(a, b):       return [a[0]-b[0], a[1]-b[1]]
def _v2_scale(v, s):     return [v[0]*s, v[1]*s]
def _v2_dot(a, b):       return a[0]*b[0] + a[1]*b[1]
def _v2_len(v):          return _math.sqrt(v[0]**2 + v[1]**2)
def _v2_norm(v):
    l = _v2_len(v)
    return [v[0]/l, v[1]/l] if l > 0 else [0.0, 0.0]
def _v2_dist(a, b):      return _v2_len(_v2_sub(b, a))
def _v2_lerp(a, b, t):   return [a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t]
def _v2_angle(v):        return _math.atan2(v[1], v[0])
def _v2_from_angle(a, l=1.0): return [_math.cos(a)*l, _math.sin(a)*l]
def _v2_perp(v):         return [-v[1], v[0]]
def _v2_reflect(v, n):
    d = 2 * _v2_dot(v, n)
    return [v[0]-d*n[0], v[1]-d*n[1]]
def _v3_add(a, b):       return [a[0]+b[0], a[1]+b[1], a[2]+b[2]]
def _v3_sub(a, b):       return [a[0]-b[0], a[1]-b[1], a[2]-b[2]]
def _v3_scale(v, s):     return [v[0]*s, v[1]*s, v[2]*s]
def _v3_dot(a, b):       return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def _v3_cross(a, b):     return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
def _v3_len(v):          return _math.sqrt(v[0]**2+v[1]**2+v[2]**2)
def _v3_norm(v):
    l = _v3_len(v)
    return [v[0]/l, v[1]/l, v[2]/l] if l > 0 else [0.0, 0.0, 0.0]
def _v3_lerp(a, b, t):   return [a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t, a[2]+(b[2]-a[2])*t]

register_module("vec", _wrapmod({
    # 2D constructors / ops
    "v2":          _v2,
    "v3":          _v3,
    "add":         lambda a, b: _v2_add(a, b) if len(a)==2 else _v3_add(a, b),
    "sub":         lambda a, b: _v2_sub(a, b) if len(a)==2 else _v3_sub(a, b),
    "scale":       lambda v, s: _v2_scale(v, s) if len(v)==2 else _v3_scale(v, s),
    "dot":         lambda a, b: _v2_dot(a, b) if len(a)==2 else _v3_dot(a, b),
    "cross":       _v3_cross,
    "len":         lambda v: _v2_len(v) if len(v)==2 else _v3_len(v),
    "norm":        lambda v: _v2_norm(v) if len(v)==2 else _v3_norm(v),
    "dist":        _v2_dist,
    "lerp":        lambda a, b, t: _v2_lerp(a, b, t) if len(a)==2 else _v3_lerp(a, b, t),
    "angle":       _v2_angle,
    "from_angle":  _v2_from_angle,
    "perp":        _v2_perp,
    "reflect":     _v2_reflect,
    "zero2":       lambda: [0.0, 0.0],
    "one2":        lambda: [1.0, 1.0],
    "up":          lambda: [0.0, -1.0],
    "down":        lambda: [0.0,  1.0],
    "left":        lambda: [-1.0, 0.0],
    "right":       lambda: [1.0,  0.0],
    "zero3":       lambda: [0.0, 0.0, 0.0],
    "forward":     lambda: [0.0, 0.0, -1.0],
}, "vec"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE — pool  (object pool for game-performance memory reuse)
# ─────────────────────────────────────────────────────────────────────────────

class _ObjectPool:
    """Fixed-capacity object pool. Acquire / release without allocation."""
    def __init__(self, factory, capacity=64):
        self._factory  = factory
        self._capacity = int(capacity)
        self._free     = []
        self._active   = []

    def acquire(self):
        if self._free:
            obj = self._free.pop()
        elif len(self._active) < self._capacity:
            obj = self._factory() if callable(self._factory) else None
        else:
            return None   # pool exhausted
        self._active.append(obj)
        return obj

    def release(self, obj):
        if obj in self._active:
            self._active.remove(obj)
            self._free.append(obj)
        return None

    def release_all(self):
        self._free.extend(self._active)
        self._active.clear()
        return None

    def active_count(self):  return len(self._active)
    def free_count(self):    return len(self._free)
    def capacity(self):      return self._capacity

    def __repr__(self):
        return f"Pool(active={len(self._active)}, free={len(self._free)}, cap={self._capacity})"


register_module("pool", _wrapmod({
    "Pool":         lambda factory=None, capacity=64: _ObjectPool(factory, capacity),
    "acquire":      lambda p: p.acquire(),
    "release":      lambda p, obj: p.release(obj),
    "release_all":  lambda p: p.release_all(),
    "active_count": lambda p: p.active_count(),
    "free_count":   lambda p: p.free_count(),
    "capacity":     lambda p: p.capacity(),
}, "pool"))
