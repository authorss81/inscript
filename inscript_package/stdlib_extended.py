# inscript/stdlib_extended.py
# General-purpose stdlib extension — Part 1 of 2
#
# Adds 7 new modules:
#   collections  — Set, Queue, Deque, PriorityQueue, RingBuffer
#   datetime     — Date, Time, Duration, formatting, parsing
#   fs           — Full file system (read, write, walk, stat, copy, delete)
#   process      — Subprocess, environment variables, args, exit
#   log          — Structured logging with levels and file sinks
#   test         — Unit testing framework (describe/it/assert_eq)
#   compress     — zip, gzip, lz4-style compression
#
# Rules enforced throughout:
#   1. Every Python exception is caught and re-raised as a clean InScript message
#   2. No raw Python tracebacks reach the user
#   3. thread module NOT included here — unsafe with tree-walk interpreter

from __future__ import annotations
import os as _os
import sys as _sys

# ─── pull in the registry from stdlib.py ─────────────────────────────────────
from stdlib import register_module


def _guard(module_name: str, fn):
    """Wrap fn so any Python exception becomes a clean [module] Error: message."""
    import functools
    @functools.wraps(fn)
    def _wrap(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:
            # Don't double-wrap already-wrapped errors
            msg = str(e)
            if msg.startswith(f"[{module_name}]"):
                raise
            raise Exception(f"[{module_name}] {type(e).__name__}: {msg}") from None
    return _wrap

def _wrapmod(d: dict, name: str) -> dict:
    return {k: (_guard(name, v) if callable(v) else v) for k, v in d.items()}


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 1 — collections
# ─────────────────────────────────────────────────────────────────────────────
import collections as _col
import heapq as _hq

class _Set:
    """Unordered collection of unique values."""
    def __init__(self, items=None):
        self._data = set(items) if items else set()
    def add(self, v):
        self._data.add(v); return None
    def remove(self, v):
        self._data.discard(v); return None
    def has(self, v):
        return v in self._data
    def size(self):
        return len(self._data)
    def to_array(self):
        return list(self._data)
    def clear(self):
        self._data.clear(); return None
    def union(self, other):
        return _Set(self._data | other._data)
    def intersect(self, other):
        return _Set(self._data & other._data)
    def difference(self, other):
        return _Set(self._data - other._data)
    def is_subset(self, other):
        return self._data <= other._data
    def __repr__(self):
        return f"Set({sorted(list(self._data), key=str)})"


class _Queue:
    """FIFO queue."""
    def __init__(self):
        self._data = _col.deque()
    def push(self, v):
        self._data.append(v); return None
    def pop(self):
        if not self._data:
            raise Exception("[collections] Queue.pop: queue is empty")
        return self._data.popleft()
    def peek(self):
        if not self._data:
            raise Exception("[collections] Queue.peek: queue is empty")
        return self._data[0]
    def size(self):
        return len(self._data)
    def is_empty(self):
        return len(self._data) == 0
    def to_array(self):
        return list(self._data)
    def clear(self):
        self._data.clear(); return None
    def __repr__(self):
        return f"Queue({list(self._data)})"


class _Deque:
    """Double-ended queue."""
    def __init__(self):
        self._data = _col.deque()
    def push_front(self, v):
        self._data.appendleft(v); return None
    def push_back(self, v):
        self._data.append(v); return None
    def pop_front(self):
        if not self._data:
            raise Exception("[collections] Deque.pop_front: deque is empty")
        return self._data.popleft()
    def pop_back(self):
        if not self._data:
            raise Exception("[collections] Deque.pop_back: deque is empty")
        return self._data.pop()
    def peek_front(self):
        return self._data[0] if self._data else None
    def peek_back(self):
        return self._data[-1] if self._data else None
    def size(self):
        return len(self._data)
    def is_empty(self):
        return len(self._data) == 0
    def to_array(self):
        return list(self._data)
    def __repr__(self):
        return f"Deque({list(self._data)})"


class _PriorityQueue:
    """Min-heap priority queue. Lower priority number = dequeued first."""
    def __init__(self):
        self._heap = []
        self._counter = 0
    def push(self, value, priority=0):
        _hq.heappush(self._heap, (priority, self._counter, value))
        self._counter += 1; return None
    def pop(self):
        if not self._heap:
            raise Exception("[collections] PriorityQueue.pop: queue is empty")
        _, _, v = _hq.heappop(self._heap)
        return v
    def peek(self):
        if not self._heap:
            raise Exception("[collections] PriorityQueue.peek: queue is empty")
        return self._heap[0][2]
    def size(self):
        return len(self._heap)
    def is_empty(self):
        return len(self._heap) == 0
    def __repr__(self):
        return f"PriorityQueue(size={len(self._heap)})"


class _RingBuffer:
    """Fixed-capacity circular buffer. Oldest values overwritten when full."""
    def __init__(self, capacity):
        self._cap = int(capacity)
        if self._cap <= 0:
            raise Exception("[collections] RingBuffer capacity must be > 0")
        self._data = _col.deque(maxlen=self._cap)
    def push(self, v):
        self._data.append(v); return None
    def pop(self):
        if not self._data:
            raise Exception("[collections] RingBuffer.pop: buffer is empty")
        return self._data.popleft()
    def peek(self):
        return self._data[0] if self._data else None
    def size(self):
        return len(self._data)
    def capacity(self):
        return self._cap
    def is_full(self):
        return len(self._data) == self._cap
    def is_empty(self):
        return len(self._data) == 0
    def to_array(self):
        return list(self._data)
    def __repr__(self):
        return f"RingBuffer({list(self._data)}, cap={self._cap})"


def _counter(lst):
    return dict(_col.Counter(lst))

def _group_by(lst, key_fn):
    result = {}
    for x in lst:
        k = key_fn(x) if callable(key_fn) else x
        if k not in result:
            result[k] = []
        result[k].append(x)
    return result

register_module("collections", _wrapmod({
    "Set":           lambda items=None: _Set(items),
    "set":           lambda items=None: _Set(items),   # lowercase alias
    "Queue":         lambda: _Queue(),
    "queue":         lambda: _Queue(),
    "Deque":         lambda: _Deque(),
    "deque":         lambda: _Deque(),
    "PriorityQueue": lambda: _PriorityQueue(),
    "RingBuffer":    lambda cap: _RingBuffer(cap),
    "counter":       _counter,
    "group_by":      _group_by,
    "zip_dicts":     lambda keys, vals: dict(zip(keys, vals)),
    "flatten":       lambda lst: [x for sub in lst for x in (sub if isinstance(sub, list) else [sub])],
    "sliding_window":lambda lst, n: [lst[i:i+n] for i in range(len(lst)-int(n)+1)],
    # Convenience helpers that work on Set objects
    "set_add":       lambda s, v: s.add(v),
    "set_remove":    lambda s, v: s.remove(v),
    "set_has":       lambda s, v: s.has(v),
    "set_size":      lambda s: s.size(),
    "set_to_array":  lambda s: s.to_array(),
    "set_union":     lambda a, b: a.union(b),
    "set_intersect": lambda a, b: a.intersect(b),
    "set_diff":      lambda a, b: a.difference(b),
}, "collections"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 2 — datetime
# ─────────────────────────────────────────────────────────────────────────────
import datetime as _dt_mod
import time as _time_mod

def _dt_now():
    n = _dt_mod.datetime.now()
    return {"year": n.year, "month": n.month, "day": n.day,
            "hour": n.hour, "minute": n.minute, "second": n.second,
            "millisecond": n.microsecond // 1000,
            "timestamp": n.timestamp(),
            "isoformat": n.isoformat()}

def _dt_utcnow():
    n = _dt_mod.datetime.utcnow()
    return {"year": n.year, "month": n.month, "day": n.day,
            "hour": n.hour, "minute": n.minute, "second": n.second,
            "timestamp": n.timestamp(),
            "isoformat": n.isoformat()}

def _dt_date(year, month, day):
    d = _dt_mod.date(int(year), int(month), int(day))
    return {"year": d.year, "month": d.month, "day": d.day,
            "weekday": d.weekday(),
            "weekday_name": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][d.weekday()],
            "isoformat": d.isoformat()}

def _dt_duration(days=0, hours=0, minutes=0, seconds=0, milliseconds=0):
    td = _dt_mod.timedelta(days=int(days), hours=int(hours),
                           minutes=int(minutes), seconds=int(seconds),
                           milliseconds=int(milliseconds))
    ts = td.total_seconds()
    return {"total_seconds": ts,
            "days": td.days,
            "hours": int(ts // 3600),
            "minutes": int((ts % 3600) // 60),
            "seconds": int(ts % 60)}

def _dt_format(dt_dict, fmt="YYYY-MM-DD HH:mm:ss"):
    f = (str(fmt)
         .replace("YYYY", "%Y").replace("YY", "%y")
         .replace("MM", "%m").replace("DD", "%d")
         .replace("HH", "%H").replace("mm", "%M").replace("ss", "%S"))
    d = _dt_mod.datetime(
        int(dt_dict.get("year", 2000)), int(dt_dict.get("month", 1)),
        int(dt_dict.get("day", 1)),    int(dt_dict.get("hour", 0)),
        int(dt_dict.get("minute", 0)), int(dt_dict.get("second", 0)))
    return d.strftime(f)

def _dt_parse(s, fmt="YYYY-MM-DD"):
    f = (str(fmt)
         .replace("YYYY", "%Y").replace("YY", "%y")
         .replace("MM", "%m").replace("DD", "%d")
         .replace("HH", "%H").replace("mm", "%M").replace("ss", "%S"))
    d = _dt_mod.datetime.strptime(str(s), f)
    return {"year": d.year, "month": d.month, "day": d.day,
            "hour": d.hour, "minute": d.minute, "second": d.second,
            "timestamp": d.timestamp(), "isoformat": d.isoformat()}

def _dt_add(dt_dict, days=0, hours=0, minutes=0, seconds=0):
    d = _dt_mod.datetime.fromtimestamp(float(dt_dict["timestamp"]))
    d2 = d + _dt_mod.timedelta(days=int(days), hours=int(hours),
                                minutes=int(minutes), seconds=int(seconds))
    return {"year": d2.year, "month": d2.month, "day": d2.day,
            "hour": d2.hour, "minute": d2.minute, "second": d2.second,
            "timestamp": d2.timestamp(), "isoformat": d2.isoformat()}

def _dt_diff_seconds(a, b):
    """Difference between two datetime dicts in seconds (a - b)."""
    return float(a.get("timestamp", 0)) - float(b.get("timestamp", 0))

def _dt_timestamp():
    return _time_mod.time()

def _dt_from_timestamp(ts):
    d = _dt_mod.datetime.fromtimestamp(float(ts))
    return {"year": d.year, "month": d.month, "day": d.day,
            "hour": d.hour, "minute": d.minute, "second": d.second,
            "timestamp": d.timestamp(), "isoformat": d.isoformat()}

register_module("datetime", _wrapmod({
    "now":            _dt_now,
    "utcnow":         _dt_utcnow,
    "date":           _dt_date,
    "duration":       _dt_duration,
    "format":         _dt_format,
    "parse":          _dt_parse,
    "add":            _dt_add,
    "diff_seconds":   _dt_diff_seconds,
    "timestamp":      _dt_timestamp,
    "from_timestamp": _dt_from_timestamp,
    "WEEKDAYS": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],
    "MONTHS":   ["January","February","March","April","May","June",
                 "July","August","September","October","November","December"],
}, "datetime"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 3 — fs  (file system)
# ─────────────────────────────────────────────────────────────────────────────
import shutil as _shutil
import glob as _glob_mod
import stat as _stat_mod

def _fs_read_text(path, encoding="utf-8"):
    with open(str(path), encoding=str(encoding)) as f:
        return f.read()

def _fs_write_text(path, content, encoding="utf-8"):
    with open(str(path), "w", encoding=str(encoding)) as f:
        f.write(str(content))
    return None

def _fs_append_text(path, content, encoding="utf-8"):
    with open(str(path), "a", encoding=str(encoding)) as f:
        f.write(str(content))
    return None

def _fs_read_lines(path, encoding="utf-8"):
    with open(str(path), encoding=str(encoding)) as f:
        return [line.rstrip("\n") for line in f]

def _fs_read_bytes(path):
    with open(str(path), "rb") as f:
        return list(f.read())   # list of ints (0-255)

def _fs_write_bytes(path, data):
    with open(str(path), "wb") as f:
        f.write(bytes(int(b) for b in data))
    return None

def _fs_delete(path):
    p = str(path)
    if _os.path.isdir(p):
        _shutil.rmtree(p)
    elif _os.path.exists(p):
        _os.remove(p)
    return None

def _fs_copy(src, dst):
    if _os.path.isdir(str(src)):
        _shutil.copytree(str(src), str(dst))
    else:
        _shutil.copy2(str(src), str(dst))
    return None

def _fs_move(src, dst):
    _shutil.move(str(src), str(dst)); return None

def _fs_mkdir(path, exist_ok=True):
    _os.makedirs(str(path), exist_ok=bool(exist_ok)); return None

def _fs_list_dir(path="."):
    return sorted(_os.listdir(str(path)))

def _fs_walk(path=".", pattern=None):
    results = []
    for root, dirs, files in _os.walk(str(path)):
        for fname in files:
            full = _os.path.join(root, fname).replace("\\", "/")
            if pattern is None or _glob_mod.fnmatch.fnmatch(fname, str(pattern)):
                results.append(full)
    return results

def _fs_stat(path):
    s = _os.stat(str(path))
    return {"size": s.st_size,
            "modified": s.st_mtime,
            "created": s.st_ctime,
            "is_file": _os.path.isfile(str(path)),
            "is_dir": _os.path.isdir(str(path)),
            "permissions": oct(s.st_mode)}

def _fs_glob(pattern):
    return [p.replace("\\", "/") for p in _glob_mod.glob(str(pattern), recursive=True)]

def _fs_rename(src, dst):
    _os.rename(str(src), str(dst)); return None

def _fs_temp_file(suffix="", prefix="inscript_"):
    import tempfile as _tf
    fd, path = _tf.mkstemp(suffix=str(suffix), prefix=str(prefix))
    _os.close(fd)
    return path.replace("\\", "/")

def _fs_temp_dir(prefix="inscript_"):
    import tempfile as _tf
    return _tf.mkdtemp(prefix=str(prefix)).replace("\\", "/")

register_module("fs", _wrapmod({
    "read_text":   _fs_read_text,
    "write_text":  _fs_write_text,
    "append_text": _fs_append_text,
    "read_lines":  _fs_read_lines,
    "read_bytes":  _fs_read_bytes,
    "write_bytes": _fs_write_bytes,
    "delete":      _fs_delete,
    "remove":      _fs_delete,       # alias
    "copy":        _fs_copy,
    "move":        _fs_move,
    "rename":      _fs_rename,
    "mkdir":       _fs_mkdir,
    "list_dir":    _fs_list_dir,
    "walk":        _fs_walk,
    "glob":        _fs_glob,
    "stat":        _fs_stat,
    "exists":      lambda p: _os.path.exists(str(p)),
    "is_file":     lambda p: _os.path.isfile(str(p)),
    "is_dir":      lambda p: _os.path.isdir(str(p)),
    "size":        lambda p: _os.path.getsize(str(p)),
    "cwd":         lambda: _os.getcwd().replace("\\", "/"),
    "home":        lambda: _os.path.expanduser("~").replace("\\", "/"),
    "abs_path":    lambda p: _os.path.abspath(str(p)).replace("\\", "/"),
    "temp_file":   _fs_temp_file,
    "temp_dir":    _fs_temp_dir,
}, "fs"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 4 — process
# ─────────────────────────────────────────────────────────────────────────────
import subprocess as _sp

def _proc_run(cmd, args=None, cwd=None, timeout=30, capture=True):
    """Run a command. cmd is a string, args is a list of strings."""
    full = [str(cmd)] + [str(a) for a in (args or [])]
    try:
        r = _sp.run(full,
                    capture_output=bool(capture),
                    text=True,
                    cwd=str(cwd) if cwd else None,
                    timeout=int(timeout))
        return {"stdout": r.stdout or "",
                "stderr": r.stderr or "",
                "exit_code": r.returncode,
                "ok": r.returncode == 0}
    except _sp.TimeoutExpired:
        return {"stdout": "", "stderr": "Process timed out", "exit_code": -1, "ok": False}

def _proc_shell(cmd, cwd=None, timeout=30):
    """Run a shell command string (uses shell=True — be careful with untrusted input)."""
    try:
        r = _sp.run(str(cmd), shell=True, capture_output=True, text=True,
                    cwd=str(cwd) if cwd else None, timeout=int(timeout))
        return {"stdout": r.stdout or "", "stderr": r.stderr or "",
                "exit_code": r.returncode, "ok": r.returncode == 0}
    except _sp.TimeoutExpired:
        return {"stdout": "", "stderr": "Timed out", "exit_code": -1, "ok": False}

def _proc_env(key, default=None):
    return _os.environ.get(str(key), default)

def _proc_set_env(key, value):
    _os.environ[str(key)] = str(value); return None

def _proc_all_env():
    return dict(_os.environ)

def _proc_args():
    return list(_sys.argv[1:])

register_module("process", _wrapmod({
    "run":     _proc_run,
    "shell":   _proc_shell,
    "env":     _proc_env,
    "set_env": _proc_set_env,
    "all_env": _proc_all_env,
    "args":    _proc_args,
    "exit":    lambda code=0: _sys.exit(int(code)),
    "cwd":     lambda: _os.getcwd().replace("\\", "/"),
    "pid":     lambda: _os.getpid(),
    "platform":lambda: _sys.platform,
    "python_version": lambda: _sys.version.split()[0],
}, "process"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 5 — log
# ─────────────────────────────────────────────────────────────────────────────
import logging as _logging
import json as _json_log

# Create a dedicated InScript logger
_inscript_logger = _logging.getLogger("inscript")
_inscript_handler = _logging.StreamHandler()
_inscript_handler.setFormatter(
    _logging.Formatter("[%(levelname)s %(asctime)s] %(message)s",
                       datefmt="%H:%M:%S"))
_inscript_logger.addHandler(_inscript_handler)
_inscript_logger.setLevel(_logging.DEBUG)
_inscript_logger.propagate = False

_LOG_LEVELS = {"debug": _logging.DEBUG, "info": _logging.INFO,
               "warn": _logging.WARNING, "warning": _logging.WARNING,
               "error": _logging.ERROR, "critical": _logging.CRITICAL}

def _log_set_level(level):
    lvl = _LOG_LEVELS.get(str(level).lower(), _logging.INFO)
    _inscript_logger.setLevel(lvl); return None

def _log_to_file(path, mode="a"):
    fh = _logging.FileHandler(str(path), mode=str(mode), encoding="utf-8")
    fh.setFormatter(_logging.Formatter("[%(levelname)s %(asctime)s] %(message)s",
                                       datefmt="%Y-%m-%d %H:%M:%S"))
    _inscript_logger.addHandler(fh); return None

def _log_structured(data):
    """Log a dict as a JSON line."""
    import time as _t
    record = {**data, "_time": _t.time()}
    _inscript_logger.info(_json_log.dumps(record, default=str))

register_module("log", _wrapmod({
    "debug":      lambda msg, **kw: _inscript_logger.debug(str(msg)),
    "info":       lambda msg, **kw: _inscript_logger.info(str(msg)),
    "warn":       lambda msg, **kw: _inscript_logger.warning(str(msg)),
    "error":      lambda msg, **kw: _inscript_logger.error(str(msg)),
    "critical":   lambda msg, **kw: _inscript_logger.critical(str(msg)),
    "set_level":  _log_set_level,
    "to_file":    _log_to_file,
    "structured": _log_structured,
    "LEVELS":     ["debug", "info", "warn", "error", "critical"],
}, "log"))


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 6 — test  (unit testing framework)
# ─────────────────────────────────────────────────────────────────────────────

class _TestRunner:
    def __init__(self):
        self._passed = 0
        self._failed = 0
        self._errors = []
        self._suite  = None

    def describe(self, name, fn):
        """Group tests under a name."""
        prev = self._suite
        self._suite = str(name)
        try:
            fn()
        finally:
            self._suite = prev

    def it(self, name, fn):
        """Run a single test."""
        label = f"{self._suite} > {name}" if self._suite else name
        try:
            fn()
            self._passed += 1
            print(f"  [PASS] {label}")
        except AssertionError as e:
            self._failed += 1
            self._errors.append((label, str(e)))
            print(f"  [FAIL] {label}: {e}")
        except Exception as e:
            self._failed += 1
            self._errors.append((label, f"{type(e).__name__}: {e}"))
            print(f"  [ERROR] {label}: {type(e).__name__}: {e}")

    def assert_eq(self, actual, expected, msg=None):
        if actual != expected:
            raise AssertionError(
                msg or f"Expected {repr(expected)}, got {repr(actual)}")

    def assert_ne(self, actual, expected, msg=None):
        if actual == expected:
            raise AssertionError(
                msg or f"Expected values to differ, both are {repr(actual)}")

    def assert_true(self, value, msg=None):
        if not value:
            raise AssertionError(msg or f"Expected truthy, got {repr(value)}")

    def assert_false(self, value, msg=None):
        if value:
            raise AssertionError(msg or f"Expected falsy, got {repr(value)}")

    def assert_raises(self, fn, error_contains=None):
        try:
            fn()
            raise AssertionError("Expected an exception but none was raised")
        except AssertionError:
            raise
        except Exception as e:
            if error_contains and str(error_contains) not in str(e):
                raise AssertionError(
                    f"Expected error containing '{error_contains}', got: {e}")

    def assert_approx(self, actual, expected, tolerance=1e-6, msg=None):
        if abs(float(actual) - float(expected)) > float(tolerance):
            raise AssertionError(
                msg or f"Expected ~{expected} (±{tolerance}), got {actual}")

    def assert_contains(self, collection, item, msg=None):
        if item not in collection:
            raise AssertionError(
                msg or f"Expected {repr(collection)} to contain {repr(item)}")

    def assert_len(self, collection, length, msg=None):
        if len(collection) != int(length):
            raise AssertionError(
                msg or f"Expected length {length}, got {len(collection)}")

    def summary(self):
        total = self._passed + self._failed
        print(f"\n  Results: {self._passed}/{total} passed", end="")
        if self._failed:
            print(f", {self._failed} failed")
        else:
            print(" -- all passed")
        return {"passed": self._passed, "failed": self._failed,
                "total": total, "errors": self._errors}

    def reset(self):
        self._passed = 0; self._failed = 0
        self._errors = []; self._suite = None


_TEST = _TestRunner()

register_module("test", {
    "describe":       lambda name, fn: _TEST.describe(name, fn),
    "it":             lambda name, fn: _TEST.it(name, fn),
    "assert_eq":      lambda a, b, msg=None: _TEST.assert_eq(a, b, msg),
    "assert_ne":      lambda a, b, msg=None: _TEST.assert_ne(a, b, msg),
    "assert_true":    lambda v, msg=None: _TEST.assert_true(v, msg),
    "assert_false":   lambda v, msg=None: _TEST.assert_false(v, msg),
    "assert_raises":  lambda fn, contains=None: _TEST.assert_raises(fn, contains),
    "assert_approx":  lambda a, b, tol=1e-6, msg=None: _TEST.assert_approx(a, b, tol, msg),
    "assert_contains":lambda col, item, msg=None: _TEST.assert_contains(col, item, msg),
    "assert_len":     lambda col, n, msg=None: _TEST.assert_len(col, n, msg),
    "summary":        lambda: _TEST.summary(),
    "reset":          lambda: _TEST.reset(),
    # Bare assert shorthand
    "ok":             lambda cond, msg="Assertion failed": (_ for _ in ()).throw(AssertionError(msg)) if not cond else None,
})

# Fix 'ok' — Python doesn't allow throw in lambda
def _test_ok(cond, msg="Assertion failed"):
    if not cond:
        raise AssertionError(str(msg))

register_module("test", {
    "describe":        lambda name, fn: _TEST.describe(name, fn),
    "it":              lambda name, fn: _TEST.it(name, fn),
    "assert_eq":       lambda a, b, msg=None: _TEST.assert_eq(a, b, msg),
    "assert_ne":       lambda a, b, msg=None: _TEST.assert_ne(a, b, msg),
    "assert_true":     lambda v, msg=None: _TEST.assert_true(v, msg),
    "assert_false":    lambda v, msg=None: _TEST.assert_false(v, msg),
    "assert_raises":   lambda fn, contains=None: _TEST.assert_raises(fn, contains),
    "assert_approx":   lambda a, b, tol=1e-6, msg=None: _TEST.assert_approx(a, b, tol, msg),
    "assert_contains": lambda col, item, msg=None: _TEST.assert_contains(col, item, msg),
    "assert_len":      lambda col, n, msg=None: _TEST.assert_len(col, n, msg),
    "summary":         lambda: _TEST.summary(),
    "reset":           lambda: _TEST.reset(),
    "ok":              _test_ok,
})


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 7 — compress
# ─────────────────────────────────────────────────────────────────────────────
import zipfile as _zf
import gzip as _gz
import io as _io_mod

def _compress_zip_dir(src_dir, output_zip):
    """Zip an entire directory."""
    src = str(src_dir)
    out = str(output_zip)
    with _zf.ZipFile(out, "w", _zf.ZIP_DEFLATED) as z:
        for root, dirs, files in _os.walk(src):
            for fname in files:
                fpath = _os.path.join(root, fname)
                arcname = _os.path.relpath(fpath, src)
                z.write(fpath, arcname)
    return out

def _compress_zip_files(files, output_zip):
    """Zip a list of file paths."""
    out = str(output_zip)
    with _zf.ZipFile(out, "w", _zf.ZIP_DEFLATED) as z:
        for f in files:
            z.write(str(f), _os.path.basename(str(f)))
    return out

def _compress_unzip(zip_path, output_dir="."):
    """Extract a zip file."""
    out = str(output_dir)
    with _zf.ZipFile(str(zip_path), "r") as z:
        z.extractall(out)
    return out

def _compress_zip_list(zip_path):
    """List files in a zip archive."""
    with _zf.ZipFile(str(zip_path), "r") as z:
        return z.namelist()

def _compress_gzip(text_or_bytes):
    """Compress a string to gzip bytes (list of ints)."""
    if isinstance(text_or_bytes, str):
        data = text_or_bytes.encode("utf-8")
    else:
        data = bytes(int(b) for b in text_or_bytes)
    buf = _io_mod.BytesIO()
    with _gz.GzipFile(fileobj=buf, mode="wb") as f:
        f.write(data)
    return list(buf.getvalue())

def _compress_gunzip(data):
    """Decompress gzip bytes (list of ints) to string."""
    raw = bytes(int(b) for b in data)
    return _gz.decompress(raw).decode("utf-8")

def _compress_gzip_file(src, dst=None):
    """Compress a file with gzip."""
    out = str(dst) if dst else str(src) + ".gz"
    with open(str(src), "rb") as f_in:
        with _gz.open(out, "wb") as f_out:
            f_out.write(f_in.read())
    return out

def _compress_gunzip_file(src, dst=None):
    """Decompress a .gz file."""
    out = str(dst) if dst else str(src).rstrip(".gz")
    with _gz.open(str(src), "rb") as f_in:
        with open(out, "wb") as f_out:
            f_out.write(f_in.read())
    return out

register_module("compress", _wrapmod({
    "zip_dir":    _compress_zip_dir,
    "zip_files":  _compress_zip_files,
    "unzip":      _compress_unzip,
    "zip_list":   _compress_zip_list,
    "gzip":       _compress_gzip,
    "gunzip":     _compress_gunzip,
    "gzip_file":  _compress_gzip_file,
    "gunzip_file":_compress_gunzip_file,
    "is_zip":     lambda p: _zf.is_zipfile(str(p)),
}, "compress"))
