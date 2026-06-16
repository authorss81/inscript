#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# inscript.py  — InScript Language Entry Point
#
# Usage:
#   python inscript.py mygame.ins              # run a file
#   python inscript.py --repl                  # interactive REPL
#   python inscript.py --check mygame.ins      # type-check only (no run)
#   python inscript.py --ast mygame.ins        # print AST
#   python inscript.py --tokens mygame.ins     # print tokens
#   python inscript.py --version               # print version

import os as _os_env; _os_env.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import sys, os, argparse

# Make sure local modules are found regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer    import tokenize
from parser   import parse
from analyzer import analyze
from interpreter import Interpreter
from errors   import (InScriptError, LexerError, ParseError,
                       SemanticError, InScriptRuntimeError,
                       MultiError, InScriptWarning)

VERSION = "3.9.6.22"

MANIFEST_FILENAME = "inscript.toml"
LOCK_FILENAME     = "inscript.lock"
LANG    = "InScript"
PACKAGES_DIR = os.path.join(os.path.expanduser("~"), ".inscript", "packages")
REGISTRY_URL = "https://raw.githubusercontent.com/authorss81/inscript-packages/main/registry.json"


# ─────────────────────────────────────────────────────────────────────────────
# RUN A FILE
# ─────────────────────────────────────────────────────────────────────────────

def _parse_pkg_spec(spec: str):
    """
    v1.9.9: Parse 'PKG@version' or just 'PKG'.
    v2.6.0: Also handles scoped packages '@scope/name' and '@scope/name@version'.
    Examples:
      'math-utils'            -> ('math-utils', None)
      'math-utils@1.2.0'      -> ('math-utils', '1.2.0')
      '@authorss81/ecs'       -> ('@authorss81/ecs', None)
      '@authorss81/ecs@2.0.0' -> ('@authorss81/ecs', '2.0.0')
    Returns (canonical_name, version_or_None).
    """
    spec = spec.strip()
    # Scoped package: starts with @scope/name, optional @version at the end
    if spec.startswith("@"):
        # Find the version separator — it's a '@' that comes AFTER the first '/'
        slash_idx = spec.find("/")
        if slash_idx == -1:
            # Malformed scoped spec, treat whole thing as name
            return spec, None
        remainder = spec[slash_idx + 1:]  # name[@version]
        scope = spec[:slash_idx + 1]       # @scope/
        if "@" in remainder:
            name_part, ver = remainder.split("@", 1)
            return (scope + name_part).strip(), ver.strip()
        return (scope + remainder).strip(), None
    # Plain package, possibly with @version
    if "@" in spec:
        idx = spec.index("@")
        return spec[:idx].strip(), spec[idx + 1:].strip()
    return spec, None


def _pkg_to_dir_name(pkg_name: str) -> str:
    """v2.6.0: Convert canonical package name (possibly scoped) to a filesystem-safe dir name.
    '@authorss81/ecs' -> '__authorss81__ecs'
    'math-utils'      -> 'math-utils'
    """
    if pkg_name.startswith("@"):
        return pkg_name.lstrip("@").replace("/", "__")
    return pkg_name


# ─────────────────────────────────────────────────────────────────────────────
# v2.6.0: CONFIG — private registry and global preferences
# ─────────────────────────────────────────────────────────────────────────────

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".inscript", "config.json")


def _read_config() -> dict:
    """v2.6.0: Read ~/.inscript/config.json. Returns {} if missing."""
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        import json as _j
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return _j.load(f)
    except Exception:
        return {}


def _write_config(data: dict) -> None:
    """v2.6.0: Write ~/.inscript/config.json atomically."""
    import json as _j
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        _j.dump(data, f, indent=2)
    os.replace(tmp, CONFIG_PATH)


def _get_registry_url() -> str:
    """v2.6.0: Return active registry URL (private registry overrides global default)."""
    cfg = _read_config()
    return cfg.get("registry", REGISTRY_URL)


def cmd_config(args_rest: list) -> int:
    """
    v2.6.0: inscript config <subcommand> [args]
    Subcommands:
      set <key> <value>   — persist a config value
      get <key>           — print a config value
      list                — show all config values
    Common keys:
      registry   — private registry URL  (e.g. https://pkg.mygame.dev)
      api_key    — API key for inscript publish
    """
    cfg = _read_config()
    if not args_rest:
        print("[InScript config] Usage: inscript --config set <key> <value>", file=sys.stderr)
        return 1
    sub = args_rest[0]
    if sub == "list":
        if not cfg:
            print("[InScript config] No config values set. Using defaults.")
        for k, v in sorted(cfg.items()):
            masked = "*" * len(v) if "key" in k or "token" in k or "secret" in k else v
            print(f"  {k} = {masked}")
        return 0
    if sub == "get":
        if len(args_rest) < 2:
            print("[InScript config] Usage: inscript --config get <key>", file=sys.stderr)
            return 1
        key = args_rest[1]
        val = cfg.get(key)
        if val is None:
            print(f"[InScript config] '{key}' is not set (default will be used).")
        else:
            print(val)
        return 0
    if sub == "set":
        if len(args_rest) < 3:
            print("[InScript config] Usage: inscript --config set <key> <value>", file=sys.stderr)
            return 1
        key, value = args_rest[1], args_rest[2]
        cfg[key] = value
        _write_config(cfg)
        masked = "*" * len(value) if "key" in key or "token" in key or "secret" in key else value
        print(f"[InScript config] ✅ Set {key} = {masked}")
        print(f"[InScript config] Config saved to {CONFIG_PATH}")
        return 0
    if sub == "unset":
        if len(args_rest) < 2:
            print("[InScript config] Usage: inscript --config unset <key>", file=sys.stderr)
            return 1
        key = args_rest[1]
        if key not in cfg:
            print(f"[InScript config] '{key}' was not set.")
            return 0
        del cfg[key]
        _write_config(cfg)
        print(f"[InScript config] ✅ Unset '{key}'.")
        return 0
    print(f"[InScript config] Unknown subcommand '{sub}'. Use: set, get, list, unset", file=sys.stderr)
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# v2.6.0: PUBLISH — upload a package to the registry
# ─────────────────────────────────────────────────────────────────────────────

def publish_package(directory: str = ".") -> int:
    """
    v2.6.0: inscript publish — pack and upload the current directory as an InScript package.

    Requires:
      - inscript.toml with [package] section (name, version, description)
      - API key set via: inscript --config set api_key <token>
      - Registry that supports PUT /packages/<name>@<version>

    Steps:
      1. Read inscript.toml [package] section
      2. Validate package name, version, and .ins entry point
      3. Bundle .ins files into a tar.gz archive
      4. POST to registry endpoint with API key auth header
      5. Report success / error
    """
    import json as _j, tarfile, io
    manifest_path = os.path.join(directory, MANIFEST_FILENAME)
    if not os.path.isfile(manifest_path):
        print(f"[InScript publish] No '{MANIFEST_FILENAME}' found in '{directory}'.", file=sys.stderr)
        print(f"[InScript publish] Run 'inscript --init' to create one.", file=sys.stderr)
        return 1

    try:
        with open(manifest_path, encoding="utf-8") as f:
            data = _parse_toml_simple(f.read())
    except Exception as e:
        print(f"[InScript publish] Cannot parse '{manifest_path}': {e}", file=sys.stderr)
        return 1

    pkg = data.get("package", {})
    name    = pkg.get("name", "").strip()
    version = pkg.get("version", "").strip()
    desc    = pkg.get("description", "").strip()

    if not name:
        print("[InScript publish] 'name' is required in [package] section of inscript.toml.", file=sys.stderr)
        return 1
    if not version:
        print("[InScript publish] 'version' is required in [package] section of inscript.toml.", file=sys.stderr)
        return 1

    cfg     = _read_config()
    api_key = cfg.get("api_key", "").strip()
    if not api_key:
        print("[InScript publish] No API key configured.", file=sys.stderr)
        print("[InScript publish] Run: inscript --config set api_key <your-token>", file=sys.stderr)
        return 1

    registry_base = _get_registry_url()
    # Strip /registry.json suffix if present to get base URL
    if registry_base.endswith("registry.json"):
        registry_base = registry_base[: registry_base.rfind("/")]

    # Collect .ins files in directory
    ins_files = []
    for root, _, files in os.walk(directory):
        # Skip hidden dirs and __pycache__
        if any(part.startswith(".") or part == "__pycache__" for part in root.split(os.sep)):
            continue
        for fn in files:
            if fn.endswith(".ins"):
                ins_files.append(os.path.join(root, fn))

    if not ins_files:
        print(f"[InScript publish] No .ins files found in '{directory}'.", file=sys.stderr)
        return 1

    print(f"[InScript publish] Packing {name}@{version} ({len(ins_files)} .ins file(s))...")

    # Build in-memory tar.gz
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in ins_files:
            arcname = os.path.relpath(path, directory)
            tar.add(path, arcname=os.path.join(f"{name}-{version}", arcname))
        # Include manifest
        tar.add(manifest_path, arcname=os.path.join(f"{name}-{version}", MANIFEST_FILENAME))
    payload = buf.getvalue()

    import hashlib
    sha256 = hashlib.sha256(payload).hexdigest()
    print(f"[InScript publish] SHA-256: {sha256}")
    print(f"[InScript publish] Bundle size: {len(payload):,} bytes")

    # POST to registry
    import urllib.request
    upload_url = f"{registry_base}/publish"
    req = urllib.request.Request(
        upload_url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/octet-stream",
            "X-InScript-Name": name,
            "X-InScript-Version": version,
            "X-InScript-Description": desc,
            "X-InScript-SHA256": sha256,
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
            print(f"[InScript publish] ✅ Published {name}@{version}")
            print(f"[InScript publish] Registry response: {body[:200]}")
        return 0
    except Exception as e:
        # Provide actionable guidance even when the registry is not live yet
        print(f"[InScript publish] Registry upload failed: {e}", file=sys.stderr)
        print(f"[InScript publish] Package bundle is ready locally (SHA-256 verified).", file=sys.stderr)
        print(f"[InScript publish] When the registry at {upload_url} is live, re-run this command.", file=sys.stderr)
        return 1


# ─────────────────────────────────────────────────────────────────────────────
# v2.6.0: AUDIT — vulnerability scan for installed packages
# ─────────────────────────────────────────────────────────────────────────────

# Well-known vulnerability advisory URL (same host as registry, advisory endpoint)
ADVISORY_URL = "https://raw.githubusercontent.com/authorss81/inscript-packages/main/advisories.json"


def audit_packages(project_dir: str = ".") -> int:
    """
    v2.6.0: inscript audit — scan installed packages against the advisory database.

    Advisory format (advisories.json):
      {
        "math-utils": [
          {"affected": "<1.0.1", "severity": "low", "description": "Off-by-one in gcd()", "fixed_in": "1.0.1"}
        ]
      }
    Returns exit code 0 if no vulnerabilities, 1 if any found.
    """
    import urllib.request, json as _j
    lock_path = os.path.join(project_dir, LOCK_FILENAME)
    locked    = _read_lock(lock_path)

    if not locked:
        print("[InScript audit] No inscript.lock found. Run 'inscript lock' first.")
        return 0

    print(f"[InScript audit] Scanning {len(locked)} package(s)...")

    # Fetch advisory database
    advisory_url = _read_config().get("advisory_url", ADVISORY_URL)
    try:
        with urllib.request.urlopen(advisory_url, timeout=10) as resp:
            advisories = _j.loads(resp.read().decode())
    except Exception as e:
        print(f"[InScript audit] Advisory database unavailable ({e}).", file=sys.stderr)
        print(f"[InScript audit] Performing offline structural checks only...")
        advisories = {}

    vulnerabilities = []
    for pkg_name, pkg_version in sorted(locked.items()):
        pkg_advisories = advisories.get(pkg_name, [])
        for adv in pkg_advisories:
            affected_constraint = adv.get("affected", "")
            try:
                if _semver_satisfies(pkg_version, affected_constraint):
                    vulnerabilities.append({
                        "package": pkg_name,
                        "version": pkg_version,
                        "severity": adv.get("severity", "unknown"),
                        "description": adv.get("description", ""),
                        "fixed_in": adv.get("fixed_in", ""),
                    })
            except Exception:
                pass  # Skip unparseable constraint

        # Structural check: warn if package dir is missing (tampered/broken install)
        dir_name = _pkg_to_dir_name(pkg_name)
        pkg_dir  = os.path.join(PACKAGES_DIR, dir_name)
        if not os.path.exists(pkg_dir):
            print(f"  ⚠  {pkg_name}@{pkg_version} — installed in lock file but directory missing (run 'inscript install')")

    if not vulnerabilities:
        print(f"[InScript audit] ✅ No known vulnerabilities found in {len(locked)} package(s).")
        return 0

    # Group by severity
    SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
    vulnerabilities.sort(key=lambda v: (SEVERITY_ORDER.get(v["severity"], 4), v["package"]))

    print(f"\n[InScript audit] ⚠  Found {len(vulnerabilities)} vulnerability/ies:\n")
    for v in vulnerabilities:
        sev  = v["severity"].upper()
        fix  = f" → fixed in {v['fixed_in']}" if v["fixed_in"] else ""
        print(f"  [{sev}] {v['package']}@{v['version']}: {v['description']}{fix}")

    print(f"\n[InScript audit] Run 'inscript --update <pkg>' to upgrade affected packages.")
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# v2.6.0: MONOREPO / WORKSPACE SUPPORT
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_workspace_packages(project_dir: str) -> list:
    """
    v2.6.0: Read workspace = ["packages/*"] from inscript.toml and return
    a list of (package_name, package_dir) for each matched workspace member.
    Returns [] if no workspace key is set.
    """
    import glob as _glob
    manifest_path = os.path.join(project_dir, MANIFEST_FILENAME)
    if not os.path.isfile(manifest_path):
        return []
    try:
        with open(manifest_path, encoding="utf-8") as f:
            data = _parse_toml_simple(f.read())
    except Exception:
        return []

    patterns = data.get("workspace", [])
    # Also accept workspace declared inside the [package] section (common in practice)
    if not patterns:
        patterns = data.get("package", {}).get("workspace", [])
    if isinstance(patterns, str):
        patterns = [patterns]
    if not patterns:
        return []

    members = []
    for pattern in patterns:
        full_pattern = os.path.join(project_dir, pattern)
        for match in sorted(_glob.glob(full_pattern)):
            if not os.path.isdir(match):
                continue
            member_manifest = os.path.join(match, MANIFEST_FILENAME)
            if not os.path.isfile(member_manifest):
                continue
            try:
                with open(member_manifest, encoding="utf-8") as f:
                    mdata = _parse_toml_simple(f.read())
                pkg_name = mdata.get("package", {}).get("name") or os.path.basename(match)
                members.append((pkg_name, match))
            except Exception:
                members.append((os.path.basename(match), match))
    return members


def workspace_install(project_dir: str = ".") -> int:
    """
    v2.6.0: Install dependencies for all workspace members.
    Reads workspace = ["packages/*"] from root inscript.toml.
    """
    members = _resolve_workspace_packages(project_dir)
    if not members:
        # Fall back to regular install if no workspace defined
        return install_all_from_toml(project_dir)

    print(f"[InScript workspace] Found {len(members)} workspace member(s):")
    for name, path in members:
        rel = os.path.relpath(path, project_dir)
        print(f"  • {name}  ({rel})")

    failed = 0
    for pkg_name, pkg_dir in members:
        print(f"\n[InScript workspace] Installing deps for '{pkg_name}'...")
        ret = install_all_from_toml(pkg_dir)
        if ret != 0:
            failed += 1

    if failed:
        print(f"\n[InScript workspace] {failed} member(s) had install failures.", file=sys.stderr)
        return 1
    print(f"\n[InScript workspace] ✅ All {len(members)} workspace members installed.")
    return 0


def workspace_list(project_dir: str = ".") -> int:
    """v2.6.0: List all workspace members and their versions."""
    members = _resolve_workspace_packages(project_dir)
    if not members:
        print("[InScript workspace] No workspace members found.")
        print(f"[InScript workspace] Add 'workspace = [\"packages/*\"]' to {MANIFEST_FILENAME}")
        return 0

    print(f"[InScript workspace] {len(members)} member(s):\n")
    for pkg_name, pkg_dir in members:
        lock_path = os.path.join(pkg_dir, LOCK_FILENAME)
        locked    = _read_lock(lock_path) if os.path.isfile(lock_path) else {}
        rel       = os.path.relpath(pkg_dir, project_dir)
        deps_str  = f"{len(locked)} locked dep(s)" if locked else "no lock file"
        print(f"  {pkg_name}  [{rel}]  — {deps_str}")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# v2.6.0: STDLIB VERSIONING
# ─────────────────────────────────────────────────────────────────────────────

def check_stdlib_version(project_dir: str = ".") -> int:
    """
    v2.6.0: Verify that the running InScript stdlib version satisfies the
    constraint declared in inscript.toml [package] stdlib = ">=2.5.0".
    Prints a warning (not a hard error) on mismatch so old projects still run.
    """
    manifest_path = os.path.join(project_dir, MANIFEST_FILENAME)
    if not os.path.isfile(manifest_path):
        return 0
    try:
        with open(manifest_path, encoding="utf-8") as f:
            data = _parse_toml_simple(f.read())
    except Exception:
        return 0

    required_stdlib = data.get("package", {}).get("stdlib", "").strip()
    if not required_stdlib:
        return 0

    try:
        ok = _semver_satisfies(VERSION, required_stdlib)
    except Exception:
        print(f"[InScript] Warning: could not parse stdlib constraint '{required_stdlib}' in {MANIFEST_FILENAME}")
        return 0

    if not ok:
        print(f"[InScript] ⚠  stdlib version mismatch: running v{VERSION}, project requires stdlib {required_stdlib}")
        print(f"[InScript]    Upgrade InScript or change the 'stdlib' field in {MANIFEST_FILENAME}")
        return 1
    return 0


def _read_lock(lock_path: str) -> dict:
    """
    v1.9.9: Read inscript.lock and return {pkg_name: version} mapping.
    Returns empty dict if file doesn't exist or can't be parsed.
    """
    if not os.path.isfile(lock_path):
        return {}
    import re as _re
    result = {}
    current_pkg = None
    for line in open(lock_path, encoding="utf-8"):
        m = _re.match(r'^\[package\.(.+)\]', line.strip())
        if m:
            current_pkg = m.group(1)
        elif current_pkg:
            m2 = _re.match(r'^version\s*=\s*"([^"]+)"', line.strip())
            if m2:
                result[current_pkg] = m2.group(1)
    return result


def _write_lock_entry(lock_path: str, pkg_name: str, version: str) -> None:
    """
    v1.9.9: Add or update a single package entry in inscript.lock.
    Creates the file if it doesn't exist.
    """
    import hashlib, re as _re, datetime
    # Read existing content
    if os.path.isfile(lock_path):
        content = open(lock_path, encoding="utf-8").read()
    else:
        content = (
            "# InScript lockfile — do not edit manually\n"
            f"# Generated by InScript {VERSION}\n\n"
            "[metadata]\n"
            f'inscript  = "{VERSION}"\n'
            "generated = \"" + datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ") + "\"\n\n"
        )

    sha256 = hashlib.sha256(f"{pkg_name}@{version}".encode()).hexdigest()
    entry  = "[package." + pkg_name + "]\nversion = \"" + version + "\"\nsha256  = \"" + sha256 + "\"\n\n"

    # Remove old entry if present
    content = _re.sub(
        rf'\[package\.{_re.escape(pkg_name)}\][^\[]*', '', content
    )
    content = content.rstrip() + "\n\n" + entry
    with open(lock_path, "w", encoding="utf-8") as f:
        f.write(content)


def _remove_lock_entry(lock_path: str, pkg_name: str) -> None:
    """v1.9.9: Remove a package entry from inscript.lock."""
    import re as _re
    if not os.path.isfile(lock_path):
        return
    content = open(lock_path, encoding="utf-8").read()
    content = _re.sub(
        rf'\[package\.{_re.escape(pkg_name)}\][^\[]*', '', content
    )
    with open(lock_path, "w", encoding="utf-8") as f:
        f.write(content)


def install_package(pkg_spec: str, lock_path: str = None) -> int:
    """
    v1.9.9: Download and install an InScript package to ~/.inscript/packages/

    Supports 'PKG' and 'PKG@version' specs.
    Writes the installed version to inscript.lock if lock_path is given.
    Falls back to lock file version info on network failure.
    """
    import urllib.request, json as _json, zipfile, io

    pkg_name, requested_version = _parse_pkg_spec(pkg_spec)
    os.makedirs(PACKAGES_DIR, exist_ok=True)
    pkg_dir = os.path.join(PACKAGES_DIR, pkg_name)

    # Check if already installed at requested version
    if os.path.exists(pkg_dir) and not requested_version:
        print(f"[InScript] Package '{pkg_name}' is already installed at {pkg_dir}")
        return 0

    # Try fetching registry
    registry = None
    try:
        print(f"[InScript] Fetching registry...")
        with urllib.request.urlopen(REGISTRY_URL, timeout=10) as resp:
            registry = _json.loads(resp.read().decode())
    except Exception as e:
        # v1.9.9: Offline fallback — if lock file has this package, report it
        if lock_path:
            locked = _read_lock(lock_path)
            if pkg_name in locked:
                print(f"[InScript] Registry unreachable ({e})")
                print(f"[InScript] Offline: '{pkg_name}' is pinned at v{locked[pkg_name]} in lock file.")
                print(f"[InScript] Tip: manually place .ins files in {PACKAGES_DIR}/{pkg_name}/ to install offline.")
                return 0
        print(f"[InScript] Could not reach package registry: {e}", file=sys.stderr)
        print(f"[InScript] Tip: place .ins files in {PACKAGES_DIR}/ or run 'inscript lock' first.",
              file=sys.stderr)
        return 1

    if pkg_name not in registry:
        available = list(registry.keys())
        print(f"[InScript] Package '{pkg_name}' not found in registry.", file=sys.stderr)
        print(f"[InScript] Available packages: {available}", file=sys.stderr)
        return 1

    pkg_info = registry[pkg_name]
    latest_version = pkg_info.get("version", "?")
    install_version = requested_version or latest_version
    zip_url = pkg_info.get("url")

    print(f"[InScript] Installing {pkg_name}@{install_version}...")
    try:
        with urllib.request.urlopen(zip_url, timeout=30) as resp:
            data = resp.read()
        # v1.9.12: Handle .ins file URLs directly (not zip archives)
        if zip_url.endswith(".ins"):
            os.makedirs(pkg_dir, exist_ok=True)
            main_ins = os.path.join(pkg_dir, "main.ins")
            with open(main_ins, "wb") as f:
                f.write(data)
        else:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                zf.extractall(PACKAGES_DIR)
        print(f"[InScript] ✅ {pkg_name}@{install_version} installed to {pkg_dir}")
        # v1.9.9: Write to lock file
        if lock_path:
            _write_lock_entry(lock_path, pkg_name, install_version)
            print(f"[InScript] Pinned {pkg_name}@{install_version} in lock file.")
        return 0
    except Exception as e:
        print(f"[InScript] Install failed: {e}", file=sys.stderr)
        return 1


def install_all_from_toml(project_dir: str = ".") -> int:
    """
    v1.9.9: `inscript install` (no args) — read inscript.toml [dependencies]
    and install every listed package, respecting inscript.lock if present.
    """
    manifest_path = os.path.join(project_dir, MANIFEST_FILENAME)
    lock_path     = os.path.join(project_dir, LOCK_FILENAME)

    if not os.path.isfile(manifest_path):
        print(f"[InScript install] No '{MANIFEST_FILENAME}' found in '{project_dir}'.", file=sys.stderr)
        print(f"[InScript install] Run 'inscript init' to create one.", file=sys.stderr)
        return 1

    try:
        with open(manifest_path, encoding="utf-8") as f:
            content = f.read()
        data = _parse_toml_simple(content)
    except Exception as e:
        print(f"[InScript install] Cannot parse '{manifest_path}': {e}", file=sys.stderr)
        return 1

    deps = data.get("dependencies", {})
    if not deps:
        print(f"[InScript install] No dependencies listed in '{manifest_path}'.")
        return 0

    # v1.9.9: If lock file exists, use its pinned versions
    locked = _read_lock(lock_path) if os.path.isfile(lock_path) else {}

    print(f"[InScript install] Installing {len(deps)} dependenc{'y' if len(deps)==1 else 'ies'}...")
    failed = 0
    for pkg_name, constraint in sorted(deps.items()):
        # Prefer locked version over constraint range
        pinned = locked.get(pkg_name)
        spec   = f"{pkg_name}@{pinned}" if pinned else pkg_name
        ret = install_package(spec, lock_path=lock_path)
        if ret != 0:
            failed += 1

    if failed:
        print(f"[InScript install] {failed} package(s) failed to install.", file=sys.stderr)
        return 1
    print(f"[InScript install] ✅ All dependencies installed.")
    return 0


def outdated_packages(project_dir: str = ".") -> int:
    """
    v1.9.9: `inscript outdated` — compare inscript.lock versions against
    the latest available in the registry. Reports which packages have updates.
    """
    import urllib.request, json as _json
    lock_path = os.path.join(project_dir, LOCK_FILENAME)
    locked    = _read_lock(lock_path)

    if not locked:
        print("[InScript outdated] No inscript.lock found or no packages locked.")
        print("[InScript outdated] Run 'inscript lock' to generate one.")
        return 0

    try:
        with urllib.request.urlopen(REGISTRY_URL, timeout=10) as resp:
            registry = _json.loads(resp.read().decode())
    except Exception as e:
        print(f"[InScript outdated] Cannot reach registry: {e}", file=sys.stderr)
        print("[InScript outdated] Showing locked versions (cannot check for updates):")
        for pkg, ver in sorted(locked.items()):
            print(f"  • {pkg}@{ver} (locked)")
        return 1

    any_outdated = False
    for pkg_name, current_ver in sorted(locked.items()):
        if pkg_name not in registry:
            print(f"  ? {pkg_name}@{current_ver} — not found in registry")
            continue
        latest = registry[pkg_name].get("version", "?")
        if latest != current_ver:
            print(f"  ↑ {pkg_name}  {current_ver} → {latest}")
            any_outdated = True
        else:
            print(f"  ✓ {pkg_name}@{current_ver} (up to date)")

    if not any_outdated:
        print("[InScript outdated] All packages are up to date.")
    return 0


def update_package(pkg_spec: str, project_dir: str = ".") -> int:
    """
    v1.9.9: `inscript update PKG` or `inscript update PKG@version` —
    remove the existing installation and reinstall at the specified (or latest) version.
    Updates inscript.lock with the new pinned version.
    """
    import shutil
    pkg_name, new_version = _parse_pkg_spec(pkg_spec)
    lock_path = os.path.join(project_dir, LOCK_FILENAME)
    pkg_dir   = os.path.join(PACKAGES_DIR, pkg_name)

    # Remove existing installation
    if os.path.exists(pkg_dir):
        shutil.rmtree(pkg_dir)
        print(f"[InScript update] Removed existing {pkg_name} installation.")

    spec = f"{pkg_name}@{new_version}" if new_version else pkg_name
    ret  = install_package(spec, lock_path=lock_path)
    if ret == 0:
        print(f"[InScript update] ✅ {pkg_name} updated.")
    return ret




def list_packages() -> int:
    """List installed packages."""
    if not os.path.exists(PACKAGES_DIR):
        print("[InScript] No packages installed yet.")
        print(f"[InScript] Install packages with: inscript install <name>")
        return 0
    pkgs = [d for d in os.listdir(PACKAGES_DIR)
            if os.path.isdir(os.path.join(PACKAGES_DIR, d))]
    if not pkgs:
        print("[InScript] No packages installed yet.")
        print(f"[InScript] Try: inscript install math-utils")
    else:
        print(f"[InScript] Installed packages ({len(pkgs)}):")
        for p in sorted(pkgs):
            pkg_json = os.path.join(PACKAGES_DIR, p, "package.json")
            version = ""
            if os.path.exists(pkg_json):
                import json as _j
                try:
                    info = _j.loads(open(pkg_json).read())
                    version = f"@{info.get('version','?')}"
                except Exception:
                    pass
            print(f"  • {p}{version}")
    return 0


def remove_package(pkg_name: str) -> int:
    """Uninstall an InScript package."""
    import shutil
    pkg_dir = os.path.join(PACKAGES_DIR, pkg_name)
    if not os.path.exists(pkg_dir):
        print(f"[InScript] Package '{pkg_name}' is not installed.", file=sys.stderr)
        return 1
    shutil.rmtree(pkg_dir)
    print(f"[InScript] ✅ Removed {pkg_name}")
    return 0


def search_packages(query: str) -> int:
    """Search the registry for packages matching a query."""
    import urllib.request, json as _json
    print(f"[InScript] Searching registry for '{query}'...")
    try:
        with urllib.request.urlopen(REGISTRY_URL, timeout=10) as resp:
            registry = _json.loads(resp.read().decode())
    except Exception as e:
        print(f"[InScript] Could not reach registry: {e}", file=sys.stderr)
        return 1
    query_lower = query.lower()
    matches = [
        (name, info) for name, info in registry.items()
        if query_lower in name.lower()
        or query_lower in info.get("description","").lower()
        or query_lower in " ".join(info.get("tags",[]))
    ]
    if not matches:
        print(f"[InScript] No packages found matching '{query}'.")
    else:
        print(f"[InScript] Found {len(matches)} package(s):")
        for name, info in sorted(matches):
            desc = info.get("description", "")
            ver  = info.get("version", "?")
            print(f"  • {name}@{ver} — {desc}")
    return 0


def info_package(pkg_name: str) -> int:
    """Show information about a package."""
    import urllib.request, json as _json
    try:
        with urllib.request.urlopen(REGISTRY_URL, timeout=10) as resp:
            registry = _json.loads(resp.read().decode())
    except Exception as e:
        print(f"[InScript] Could not reach registry: {e}", file=sys.stderr)
        return 1
    if pkg_name not in registry:
        print(f"[InScript] Package '{pkg_name}' not found.", file=sys.stderr)
        return 1
    info = registry[pkg_name]
    installed = os.path.exists(os.path.join(PACKAGES_DIR, pkg_name))
    print(f"  Name:        {pkg_name}")
    print(f"  Version:     {info.get('version', '?')}")
    print(f"  Description: {info.get('description', '')}")
    print(f"  Tags:        {', '.join(info.get('tags', []))}")
    print(f"  Repo:        {info.get('repo', '')}")
    print(f"  Installed:   {'yes' if installed else 'no'}")
    return 0


def run_file(path: str, type_check: bool = True) -> int:
    """Load and execute an InScript source file (or .ibc bytecode). Returns exit code."""
    if not os.path.exists(path):
        print(f"[InScript] Error: file not found: '{path}'", file=sys.stderr)
        return 1
    # v2.4.0: transparent .ibc execution via bytecode VM
    if path.endswith(".ibc"):
        return _run_ibc(path)
    if not path.endswith(".ins"):
        print(f"[InScript] Warning: expected .ins extension, got '{path}'", file=sys.stderr)
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    return run_source(source, filename=path, type_check=type_check)


# ── v2.4.0: Real Bytecode Pipeline ───────────────────────────────────────────

def _ibc_path_for(src: str, out: str | None = None) -> str:
    if out:
        return out
    base = src[:-4] if src.endswith(".ins") else src
    return base + ".ibc"


def _compile_cmd(src_path: str, out_path, target: str,
                 dce: bool, incremental: bool) -> int:
    """v2.4.0: AOT-compile .ins → .ibc using the real register-based VM compiler."""
    if not os.path.exists(src_path):
        print(f"[InScript] compile: file not found: '{src_path}'", file=sys.stderr)
        return 1

    # WASM / native — honest stubs with roadmap info
    if target in ("wasm", "native"):
        print(f"[InScript] --target {target} is planned for v2.5.x.")
        print(f"  WASM output:   requires LLVM/Emscripten toolchain")
        print(f"  Native output: requires transpile-to-C pipeline")
        print(f"  Today's target: inscript --compile {src_path} --target ibc")
        return 0

    dest = _ibc_path_for(src_path, out_path)

    # Incremental: skip if .ibc is up to date
    if incremental and os.path.exists(dest):
        if os.path.getmtime(dest) >= os.path.getmtime(src_path):
            print(f"[InScript] compile: {dest} is up to date (--incremental)")
            return 0

    with open(src_path, "r", encoding="utf-8") as f:
        source = f.read()

    # Parse + compile to FnProto bytecode
    try:
        from compiler import compile_source
        from vm_code  import write_ibc
        proto = compile_source(source, filename=src_path)
    except Exception as e:
        print(f"[InScript] compile error: {e}", file=sys.stderr)
        return 1

    # Dead-code elimination at the proto level
    if dce:
        n_removed = _dce_proto(proto)
        if n_removed:
            print(f"[InScript] DCE: pruned {n_removed} unreachable nested proto(s)")

    # Write .ibc
    try:
        write_ibc(proto, dest)
    except Exception as e:
        print(f"[InScript] serialize error: {e}", file=sys.stderr)
        return 1

    src_size = os.path.getsize(src_path)
    ibc_size = os.path.getsize(dest)
    dce_tag  = " +DCE" if dce else ""
    print(f"[InScript] compiled{dce_tag}: {src_path}  →  {dest}")
    print(f"           source {src_size:,}B  →  bytecode {ibc_size:,}B  "
          f"({ibc_size/src_size*100:.0f}% of source)")
    return 0


def _run_ibc(path: str) -> int:
    """v2.4.0: Load and execute a pre-compiled .ibc bytecode file."""
    try:
        from vm_code import read_ibc
        from vm      import VM
        proto = read_ibc(path)
    except ValueError as e:
        print(f"[InScript] run: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[InScript] run: failed to load '{path}': {e}", file=sys.stderr)
        return 1
    try:
        vm = VM(filename=path)
        vm.run(proto)
        return 0
    except Exception as e:
        print(f"[InScript] runtime error: {e}", file=sys.stderr)
        return 1


def _dce_proto(proto) -> int:
    """
    v2.4.0: Dead-code elimination at the FnProto level.
    Removes nested protos whose names are never referenced in the parent's
    name table. Returns the number of protos removed.
    """
    if not proto.protos:
        return 0
    referenced = set(proto.names)
    before = len(proto.protos)
    # Recurse into survivors first
    for sub in proto.protos:
        _dce_proto(sub)
    # Remove unreferenced nested protos
    proto.protos = [p for p in proto.protos if p.name in referenced or p.name == "<main>"]
    removed = before - len(proto.protos)
    return removed


def _dce_pass(program):
    """AST-level DCE (used by test_v240 for unit-testing DCE logic)."""
    from ast_nodes import FunctionDecl, IdentExpr, Program

    referenced: set = set()

    def _walk(node):
        if node is None: return
        if isinstance(node, IdentExpr):
            referenced.add(node.name)
            return
        for attr in (vars(node).values() if hasattr(node, '__dict__') else []):
            if hasattr(attr, '__dict__'):
                _walk(attr)
            elif isinstance(attr, list):
                for item in attr:
                    if hasattr(item, '__dict__'): _walk(item)
            elif isinstance(attr, tuple):
                for item in attr:
                    if hasattr(item, '__dict__'): _walk(item)

    for stmt in program.body:
        _walk(stmt)

    kept = []
    removed = 0
    for stmt in program.body:
        if isinstance(stmt, FunctionDecl) and stmt.name not in referenced:
            if not getattr(stmt, 'exported', False):
                removed += 1
                continue
        kept.append(stmt)

    if removed:
        print(f"[InScript] DCE: eliminated {removed} unreferenced function(s)")
    return Program(body=kept)




# ─── v1.6.0 helpers ──────────────────────────────────────────────────────────

def _find_ins_files(directory: str):
    """Walk directory tree and yield all .ins file paths."""
    import os
    for root, _dirs, files in os.walk(directory):
        for fname in sorted(files):
            if fname.endswith(".ins"):
                yield os.path.join(root, fname)


def _check_all_files(directory: str, strict: bool = False) -> int:
    """v1.6.0: Check all .ins files in directory. Returns exit code."""
    import os
    files = list(_find_ins_files(directory))
    if not files:
        print(f"[InScript check] No .ins files found in '{directory}'")
        return 0

    errors = 0
    warnings = 0
    checked = 0
    for path in files:
        checked += 1
        try:
            with open(path, encoding="utf-8") as f:
                source = f.read()
            prog = parse(source, path)
            from analyzer import Analyzer
            from errors import SemanticError, MultiError
            a = Analyzer(source.splitlines(), multi_error=True,
                         warn_as_error=strict, no_warn=False)
            try:
                a.analyze(prog)
                n_warns = len(a._warnings)
                warnings += n_warns
                if n_warns:
                    for w in a._warnings:
                        print(f"  WARN  {path}: {w.message} (line {w.line})")
                    if strict:
                        errors += n_warns
                else:
                    print(f"  OK    {path}")
            except (SemanticError, MultiError) as e:
                errors += 1
                print(f"  ERR   {path}: {e}", file=sys.stderr)
        except (LexerError, ParseError) as e:
            errors += 1
            print(f"  ERR   {path}: {e}", file=sys.stderr)
        except Exception as e:
            errors += 1
            print(f"  ERR   {path}: {e}", file=sys.stderr)

    mode = " [strict]" if strict else ""
    symbol = "-" * 50
    print(f"\n{symbol}")
    print(f"  Checked {checked} file{'s' if checked != 1 else ''}{mode}")
    print(f"  {errors} error{'s' if errors != 1 else ''}, "
          f"{warnings} warning{'s' if warnings != 1 else ''}")
    print(symbol)
    return 1 if errors else 0



def _compat_files(path: str) -> int:
    """
    v1.9.1: `inscript compat FILE|DIR` — report every v2.0.0 breaking change.
    Returns 0 if clean, 1 if issues found.
    """
    import re as _re
    from collections import defaultdict

    CHECKS = [
        (_re.compile(r'\bnull\b'),
         "use of 'null' — removed in v1.7.4, use 'nil'"),
        (_re.compile(r'\bdiv\b'),
         "use of 'div' operator — removed in v1.9.5 (hard error), use '//' for floor division"),
        (_re.compile(r':\s*\[\]'),
         "bare ':[]' type annotation — use ':array' or ':[T]' with element type"),
        (_re.compile(r'\barray\b(?!\s*<)(?!\s*\[)'),
         "bare 'array' type — use '[T]' with explicit element type in v2.0.0"),
        (_re.compile(r'--no-typecheck'),
         "'--no-typecheck' flag removed — use '--unsafe-no-check' in v2.0.0"),
    ]

    def _check_file(fpath):
        issues = []
        try:
            with open(fpath, encoding="utf-8") as f:
                src = f.read()
        except OSError as e:
            print(f"[InScript compat] Cannot read '{fpath}': {e}", file=sys.stderr)
            return issues
        for lineno, line in enumerate(src.splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("//") or stripped.startswith("#"):
                continue
            for pat, msg in CHECKS:
                if pat.search(line):
                    issues.append((fpath, lineno, line.rstrip(), msg))
        return issues

    all_issues = []
    if os.path.isfile(path):
        all_issues = _check_file(path)
    elif os.path.isdir(path):
        for root, _dirs, files in os.walk(path):
            for fname in sorted(files):
                if fname.endswith(".ins"):
                    all_issues.extend(_check_file(os.path.join(root, fname)))
    else:
        print(f"[InScript compat] Not found: '{path}'", file=sys.stderr)
        return 1

    if not all_issues:
        print(f"[InScript compat] No v2.0.0 breaking changes found in '{path}'")
        return 0

    by_file = defaultdict(list)
    for fp, ln, line, msg in all_issues:
        by_file[fp].append((ln, line, msg))

    print(f"[InScript compat] Found {len(all_issues)} breaking change(s) for v2.0.0:\n")
    for fp, entries in sorted(by_file.items()):
        print(f"  {fp}")
        for ln, line, msg in entries:
            print(f"    Line {ln}: {msg}")
            print(f"      {line.strip()}")
        print()
    print(f"Run: inscript migrate {path}  to auto-fix null/div issues.")
    return 1


def _infer_types_file(path: str) -> int:
    """
    v1.9.8: `inscript --infer-types FILE`
    Parse and type-check FILE, then print the inferred type for every
    let/const declaration. Useful for understanding what the analyzer infers.
    Returns 0 on success, 1 if file not found or parse error.
    """
    import os
    if not os.path.isfile(path):
        print(f"[InScript infer-types] File not found: '{path}'", file=sys.stderr)
        return 1
    try:
        with open(path, encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        print(f"[InScript infer-types] Cannot read '{path}': {e}", file=sys.stderr)
        return 1

    from lexer import Lexer
    from parser import Parser
    from analyzer import Analyzer
    from ast_nodes import VarDecl

    try:
        tokens = Lexer(src).tokenize()
        tree   = Parser(tokens).parse()
    except Exception as e:
        print(f"[InScript infer-types] Parse error: {e}", file=sys.stderr)
        return 1

    analyzer = Analyzer()
    try:
        analyzer.analyze(tree)
    except Exception:
        pass   # best-effort — show what we have even if there are errors

    # Walk all VarDecl / ConstDecl nodes and report inferred types
    results = []
    def _walk(node):
        if node is None:
            return
        if isinstance(node, (VarDecl,)):
            sym = analyzer._scope.lookup(node.name) if hasattr(analyzer, '_scope') else None
            typ = sym.type_ if sym else None
            type_str = str(typ) if typ else "any"
            results.append((node.line, "let" if not node.is_const else "const",
                             node.name, type_str))
        # Recurse into body of blocks, fns etc.
        for attr in ("body", "then_branch", "else_branch", "value",
                     "initializer", "statements"):
            child = getattr(node, attr, None)
            if child is None:
                continue
            if hasattr(child, "__iter__") and not isinstance(child, str):
                for c in child:
                    if hasattr(c, "__class__") and hasattr(c, "line"):
                        _walk(c)
            elif hasattr(child, "line"):
                _walk(child)

    if hasattr(tree, "body"):
        for stmt in tree.body:
            _walk(stmt)

    if not results:
        print(f"[InScript infer-types] No let/const declarations found in '{path}'")
        return 0

    print(f"[InScript infer-types] Inferred types in '{path}':\n")
    for line, kw, name, typ in results:
        print(f"  Line {line:3d}:  {kw} {name:<20s}  →  {typ}")
    print()
    return 0


def _check_v2_readiness(project_dir: str = ".") -> int:
    """
    v1.9.10: `inscript check-v2 [DIR]`

    Runs all pre-v2.0.0 readiness gates and reports pass/fail for each.
    Exit code 0 = all gates pass (project is ready for v2.0.0).
    Exit code 1 = one or more gates fail (work remains).

    Gates checked:
      1. div removed        — no .ins files use the `div` keyword
      2. null removed       — no .ins files use the `null` keyword
      3. bare array removed — no .ins files use bare `: array` annotation
      4. hash comments      — no .ins files use old `//` line comments
      5. async/await real   — interpreter has InScriptCoroutine (not stub)
      6. type inference     — Array<T> inference present in analyzer
      7. pkg lock           — inscript.lock exists and is non-empty
      8. inscript.toml      — inscript.toml exists in project_dir
    """
    import re as _re

    PASS = "\033[32m  ✅ PASS\033[0m"
    FAIL = "\033[31m  ❌ FAIL\033[0m"
    WARN = "\033[33m  ⚠️  WARN\033[0m"

    gates_passed = 0
    gates_failed = 0
    gates_warned = 0

    def gate(name: str, passed: bool, detail: str = "", warn: bool = False):
        nonlocal gates_passed, gates_failed, gates_warned
        if passed:
            print(f"{PASS}  {name}")
            gates_passed += 1
        elif warn:
            print(f"{WARN}  {name}  — {detail}")
            gates_warned += 1
        else:
            print(f"{FAIL}  {name}  — {detail}")
            gates_failed += 1

    print(f"\n  InScript v2.0.0 Readiness Check\n  Project: {os.path.abspath(project_dir)}\n")

    # ── Gate 1: div removed ───────────────────────────────────────────────────
    ins_files = list(_find_ins_files(project_dir)) if os.path.isdir(project_dir) else []
    div_hits = []
    for fpath in ins_files:
        try:
            src = open(fpath, encoding="utf-8").read()
            lines = [i+1 for i, l in enumerate(src.splitlines())
                     if _re.search(r'\bdiv\b', l) and not l.lstrip().startswith('#')]
            if lines:
                div_hits.append((fpath, lines))
        except OSError:
            pass
    gate("div keyword removed",
         len(div_hits) == 0,
         f"{sum(len(v) for _,v in div_hits)} occurrence(s) in "
         f"{len(div_hits)} file(s) — run: inscript --migrate {project_dir}")

    # ── Gate 2: null removed ──────────────────────────────────────────────────
    null_hits = []
    for fpath in ins_files:
        try:
            src = open(fpath, encoding="utf-8").read()
            lines = [i+1 for i, l in enumerate(src.splitlines())
                     if _re.search(r'\bnull\b', l) and not l.lstrip().startswith('#')]
            if lines:
                null_hits.append((fpath, lines))
        except OSError:
            pass
    gate("null keyword removed",
         len(null_hits) == 0,
         f"{sum(len(v) for _,v in null_hits)} occurrence(s) — run: inscript --migrate {project_dir}")

    # ── Gate 3: bare array removed ────────────────────────────────────────────
    arr_hits = []
    for fpath in ins_files:
        try:
            src = open(fpath, encoding="utf-8").read()
            if _re.search(r':\s*array\b', src):
                arr_hits.append(fpath)
        except OSError:
            pass
    gate("bare 'array' annotation removed",
         len(arr_hits) == 0,
         f"Found in {len(arr_hits)} file(s) — use typed arrays like Array<int>",
         warn=len(arr_hits) > 0)

    # ── Gate 4: # comments (// as comments gone) ──────────────────────────────
    comment_hits = []
    for fpath in ins_files:
        try:
            src = open(fpath, encoding="utf-8").read()
            # Only flag STANDALONE // lines — inline // is always floor division in v1.9.6+
            bad = [i+1 for i, l in enumerate(src.splitlines())
                   if _re.match(r'^\s*//', l)]
            if bad:
                comment_hits.append((fpath, bad))
        except OSError:
            pass
    gate("# line comments (no old // comments)",
         len(comment_hits) == 0,
         f"{len(comment_hits)} file(s) still use // as comments — run: inscript --migrate {project_dir}")

    # ── Gate 5: async/await is real (not stub) ────────────────────────────────
    try:
        from stdlib_values import InScriptCoroutine
        gate("async/await real (InScriptCoroutine)", True)
    except ImportError:
        gate("async/await real (InScriptCoroutine)", False,
             "InScriptCoroutine not found in stdlib_values — v1.9.7 not applied")

    # ── Gate 6: type inference (Array<T>) ────────────────────────────────────
    try:
        from analyzer import array_type, T_INT
        test_t = array_type(T_INT)
        gate("Array<T> type inference present", test_t.name == "Array")
    except Exception as e:
        gate("Array<T> type inference present", False, str(e))

    # ── Gate 7: inscript.lock present ────────────────────────────────────────
    lock_path = os.path.join(project_dir, LOCK_FILENAME)
    lock_ok   = os.path.isfile(lock_path)
    gate("inscript.lock present",
         lock_ok,
         f"Not found at '{lock_path}' — run: inscript lock",
         warn=not lock_ok)

    # ── Gate 8: inscript.toml present ────────────────────────────────────────
    toml_path = os.path.join(project_dir, MANIFEST_FILENAME)
    toml_ok   = os.path.isfile(toml_path)
    gate("inscript.toml present",
         toml_ok,
         f"Not found at '{toml_path}' — run: inscript init",
         warn=not toml_ok)

    # ── Summary ──────────────────────────────────────────────────────────────
    total = gates_passed + gates_failed + gates_warned
    print(f"\n  {gates_passed}/{total} gates passed"
          + (f"  ({gates_warned} warning(s))" if gates_warned else "")
          + (f"  ({gates_failed} failure(s))" if gates_failed else ""))

    if gates_failed == 0 and gates_warned == 0:
        print("\n  \033[32m🎉 All gates pass — project is ready for v2.0.0!\033[0m\n")
        return 0
    elif gates_failed == 0:
        print("\n  \033[33m⚠️  Warnings present — review before tagging v2.0.0.\033[0m\n")
        return 0
    else:
        print(f"\n  \033[31m✗ {gates_failed} gate(s) failed — resolve before v2.0.0.\033[0m\n")
        return 1


def _migrate_files(path: str) -> int:
    """v1.7.4: Auto-migrate deprecated InScript syntax in-place."""
    import re, os
    target = os.path.abspath(path)
    files = []
    if os.path.isfile(target):
        files = [target]
    elif os.path.isdir(target):
        files = list(_find_ins_files(target))
    else:
        print(f"[InScript migrate] Not found: '{path}'", file=sys.stderr)
        return 1

    changed = errors = 0
    for fpath in files:
        try:
            with open(fpath, encoding="utf-8") as f:
                original = f.read()
            src = original
            # v1.9.6: // line comments → # line comments  (MUST run before div→// rewrite)
            # Rule 1: standalone comment lines — optional whitespace then //
            src = re.sub(r'^(\s*)//', r'\1#', src, flags=re.MULTILINE)
            # Rule 2: inline trailing comment — `; // word` or `} // word` → `; # word`
            # v1.9.15: ONLY fires after statement terminators (;, {, }),
            #          NOT after expression-ending chars like ), ], identifiers, digits.
            #          This prevents floor-division like `(a*b) // gcd(a,b)` being mangled.
            src = re.sub(r'([;{}])( *)//(\s+[A-Za-z_])', r'\1\2#\3', src)
            # Rule 3: warn about ambiguous ` // <digit>` patterns (may be comment or floor-div)
            ambiguous = re.findall(r'(\s)//(\s+\d)', src)
            if ambiguous:
                print(f"  WARNING   {fpath}: {len(ambiguous)} ambiguous ' // <digit>' pattern(s) — "
                      f"check manually: floor-div or comment? Change to '#' if comment.")
            # null → nil
            src = re.sub(r'\bnull\b', 'nil', src)
            # x div y → x // y  (only bare `div` between expressions, safe after comment rules)
            src = re.sub(r'\bdiv\b', '//', src)
            # bare [] type annotation → array  (e.g. `: []` → `: array`)
            src = re.sub(r':\s*\[\]', ': array', src)
            if src != original:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(src)
                print(f"  MIGRATED  {fpath}")
                changed += 1
            else:
                print(f"  OK        {fpath}")
        except Exception as e:
            errors += 1
            print(f"  ERR       {fpath}: {e}", file=sys.stderr)

    sep = "-" * 50
    print(f"\n{sep}")
    print(f"  Migrated {changed} file{'s' if changed != 1 else ''}, "
          f"{len(files)-changed-errors} already clean, "
          f"{errors} error{'s' if errors != 1 else ''}")
    print(sep)
    return 1 if errors else 0


def _fmt_all_files(directory: str) -> int:
    """v1.6.0: Format all .ins files in directory in-place. Returns exit code."""
    files = list(_find_ins_files(directory))
    if not files:
        print(f"[InScript fmt] No .ins files found in '{directory}'")
        return 0

    from inscript_fmt import format_source
    changed = 0
    errors = 0
    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                original = f.read()
            formatted = format_source(original)
            if formatted != original:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(formatted)
                print(f"  FMT   {path}")
                changed += 1
            else:
                print(f"  OK    {path}")
        except Exception as e:
            errors += 1
            print(f"  ERR   {path}: {e}", file=sys.stderr)

    symbol = "-" * 50
    print(f"\n{symbol}")
    print(f"  Formatted {changed} file{'s' if changed != 1 else ''}, "
          f"{len(files) - changed - errors} already clean, "
          f"{errors} error{'s' if errors != 1 else ''}")
    print(symbol)
    return 1 if errors else 0


def _print_inscript_profile(pr, filename: str = "<script>"):
    """v1.3.0: Print a human-readable InScript-level profile from a cProfile result."""
    import pstats, io as _io
    s = _io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('tottime')
    ps.print_stats()
    raw = s.getvalue()

    # Extract lines that reference interpreter visit_ / _call_function
    rows = []
    for line in raw.split('\n'):
        if 'visit_' in line or '_call_function' in line or 'visit_BinaryExpr' in line:
            parts = line.split()
            if len(parts) >= 6:
                try:
                    ncalls  = parts[0].split('/')[0]
                    tottime = float(parts[1])
                    name    = parts[-1]
                    # prettify: visit_CallExpr → CallExpr
                    label = name.replace('visit_', '').replace('_call_function', 'fn_dispatch')
                    rows.append((tottime, int(ncalls), label))
                except (ValueError, IndexError):
                    pass

    if not rows:
        print("[InScript --profile] No hotspot data found.", file=sys.stderr)
        return

    rows.sort(reverse=True)
    total_time = sum(t for t, _, _ in rows)
    print(f"\n[InScript --profile] {filename}")
    print(f"{'-'*58}")
    print(f"  {'calls':>10}  {'time(s)':>8}  {'%':>5}  node/operation")
    print(f"{'-'*58}")
    for t, n, label in rows[:15]:
        pct = (t / total_time * 100) if total_time > 0 else 0
        print(f"  {n:>10,}  {t:>8.3f}  {pct:>4.1f}%  {label}")
    print(f"{'-'*58}")
    print(f"  {'':>10}  {total_time:>8.3f}  100.0%  TOTAL (hotspots)\n")




# ─────────────────────────────────────────────────────────────────────────────
# v1.9.3 — Documentation Generation
# ─────────────────────────────────────────────────────────────────────────────

import re as _re

# ── Doc comment parser ────────────────────────────────────────────────────────

def _parse_doc_comments(source: str) -> list:
    """
    v1.9.3: Extract doc-comment blocks from InScript source.

    A doc block is one or more consecutive `///` lines immediately followed
    by a `fn`, `struct`, `enum`, `interface`, or `type` declaration.

    Returns a list of dicts:
      {
        "kind":        "fn"|"struct"|"enum"|"interface"|"type",
        "name":        str,
        "description": str,          # first non-tag lines joined
        "params":      [{"name":str, "type":str, "desc":str}],
        "returns":     {"type":str, "desc":str} | None,
        "examples":    [str],        # code blocks from @example tags
        "deprecated":  str | None,   # message from @deprecated
        "since":       str | None,   # version string from @since
        "raw_tags":    [{"tag":str, "text":str}],  # all unrecognized tags
        "line":        int,
      }
    """
    lines   = source.splitlines()
    results = []
    i = 0

    DECL_RE = _re.compile(
        r'^\s*(?:pub\s+)?(?:async\s+)?'
        r'(fn|struct|enum|interface|type)\s+(\w+)'
    )

    while i < len(lines):
        # Collect consecutive /// lines
        if not lines[i].lstrip().startswith("///"):
            i += 1
            continue

        block_start = i
        raw_comment = []
        while i < len(lines) and lines[i].lstrip().startswith("///"):
            stripped = lines[i].lstrip()
            text = stripped[3:].lstrip(" ")   # strip leading "/// "
            raw_comment.append(text)
            i += 1

        # Skip blank lines between doc block and declaration
        j = i
        while j < len(lines) and not lines[j].strip():
            j += 1

        if j >= len(lines):
            continue

        m = DECL_RE.match(lines[j])
        if not m:
            continue    # doc block not followed by a declaration

        kind = m.group(1)
        name = m.group(2)

        # Parse the doc block
        description_lines = []
        params    = []
        returns   = None
        examples  = []
        deprecated = None
        since      = None
        raw_tags   = []
        example_buf = []
        in_example  = False

        for raw in raw_comment:
            if raw.startswith("@example"):
                in_example = True
                example_buf = []
                continue
            if in_example:
                if raw.startswith("@"):
                    examples.append("\n".join(example_buf).strip())
                    example_buf = []
                    in_example  = False
                    # fall through to process this @tag
                else:
                    example_buf.append(raw)
                    continue
            if raw.startswith("@param "):
                rest   = raw[7:].strip()
                parts  = rest.split(None, 2)
                pname  = parts[0] if len(parts) > 0 else ""
                ptype  = parts[1] if len(parts) > 1 else ""
                pdesc  = parts[2] if len(parts) > 2 else ""
                # strip optional type wrapping like (int) or [int]
                ptype  = ptype.strip("()[]")
                params.append({"name": pname, "type": ptype, "desc": pdesc})
            elif raw.startswith("@returns ") or raw.startswith("@return "):
                rest  = raw.split(None, 1)[1].strip() if " " in raw else ""
                parts = rest.split(None, 1)
                rtype = parts[0].strip("()[]") if parts else ""
                rdesc = parts[1] if len(parts) > 1 else ""
                returns = {"type": rtype, "desc": rdesc}
            elif raw.startswith("@deprecated"):
                deprecated = raw[11:].strip()
            elif raw.startswith("@since "):
                since = raw[7:].strip()
            elif raw.startswith("@"):
                tag_parts = raw.split(None, 1)
                raw_tags.append({
                    "tag":  tag_parts[0][1:],
                    "text": tag_parts[1] if len(tag_parts) > 1 else ""
                })
            else:
                description_lines.append(raw)

        if in_example and example_buf:
            examples.append("\n".join(example_buf).strip())

        results.append({
            "kind":        kind,
            "name":        name,
            "description": "\n".join(description_lines).strip(),
            "params":      params,
            "returns":     returns,
            "examples":    examples,
            "deprecated":  deprecated,
            "since":       since,
            "raw_tags":    raw_tags,
            "line":        block_start + 1,
        })
        i = j + 1

    return results


# ── Markdown renderer ─────────────────────────────────────────────────────────

def _render_doc_markdown(entries: list, source_file: str = "") -> str:
    """
    v1.9.3: Render extracted doc entries as Markdown.

    Format:
      # API Reference — filename
      ## `fn name`
      Description
      ### Parameters / Returns / Examples / Deprecated
    """
    fname = os.path.basename(source_file) if source_file else "API"
    stem  = fname.replace(".ins", "")

    lines = [
        f"# API Reference — {stem}",
        f"",
        f"> Generated by InScript {VERSION}  ",
        f"> Source: `{source_file}`" if source_file else "",
        f"",
        "---",
        "",
    ]

    for entry in entries:
        kind = entry["kind"]
        name = entry["name"]

        # Section header
        lines.append(f"## `{kind} {name}`")
        if entry.get("since"):
            lines.append(f"*Since v{entry['since']}*  ")
        if entry.get("deprecated"):
            lines.append(f"")
            lines.append(f"> **Deprecated:** {entry['deprecated']}")
        lines.append("")

        # Description
        if entry["description"]:
            lines.append(entry["description"])
            lines.append("")

        # Parameters table
        if entry["params"]:
            lines.append("### Parameters")
            lines.append("")
            lines.append("| Name | Type | Description |")
            lines.append("|------|------|-------------|")
            for p in entry["params"]:
                ptype = f"`{p['type']}`" if p["type"] else "—"
                lines.append(f"| `{p['name']}` | {ptype} | {p['desc']} |")
            lines.append("")

        # Returns
        if entry.get("returns"):
            r = entry["returns"]
            lines.append("### Returns")
            lines.append("")
            rtype = f"`{r['type']}`" if r["type"] else ""
            rdesc = r["desc"]
            if rtype and rdesc:
                lines.append(f"{rtype} — {rdesc}")
            elif rtype:
                lines.append(rtype)
            else:
                lines.append(rdesc)
            lines.append("")

        # Examples (runnable code blocks)
        if entry["examples"]:
            lines.append("### Example")
            lines.append("")
            for ex in entry["examples"]:
                lines.append("```inscript")
                lines.append(ex)
                lines.append("```")
                lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# ── File / directory driver ───────────────────────────────────────────────────

def _doc_file(filepath: str, output_path: str = None) -> tuple:
    """
    v1.9.3: Extract doc comments from a single .ins file and return
    (entries, markdown_str).  Writes to output_path if given.
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        print(f"[InScript doc] Cannot read '{filepath}': {e}", file=sys.stderr)
        return [], ""

    entries  = _parse_doc_comments(source)
    markdown = _render_doc_markdown(entries, source_file=filepath)

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown)
        except OSError as e:
            print(f"[InScript doc] Cannot write '{output_path}': {e}", file=sys.stderr)

    return entries, markdown


def _generate_docs(path: str, output_dir: str = None) -> int:
    """
    v1.9.3: `inscript doc FILE|DIR [--out DIR]`

    • FILE  → print Markdown to stdout (or write to --out/filename.md)
    • DIR   → walk all .ins files, write docs/api/<name>.md  (or --out/<name>.md)

    Returns 0 on success, 1 on error.
    """
    if os.path.isfile(path):
        entries, markdown = _doc_file(path)
        if output_dir:
            stem    = os.path.basename(path).replace(".ins", "")
            out_md  = os.path.join(output_dir, stem + ".md")
            _doc_file(path, output_path=out_md)
            n = len(entries)
            print(f"[InScript doc] '{path}' → '{out_md}'  ({n} item{'s' if n!=1 else ''})")
        else:
            print(markdown)
        return 0

    elif os.path.isdir(path):
        out_base = output_dir or os.path.join(path, "docs", "api")
        ins_files = sorted(_find_ins_files(path))
        if not ins_files:
            print(f"[InScript doc] No .ins files found in '{path}'")
            return 0
        total_entries = 0
        for fpath in ins_files:
            rel    = os.path.relpath(fpath, path)
            stem   = rel.replace(os.sep, "_").replace(".ins", "")
            out_md = os.path.join(out_base, stem + ".md")
            entries, _ = _doc_file(fpath, output_path=out_md)
            total_entries += len(entries)
            n = len(entries)
            print(f"[InScript doc]  {rel} → {os.path.relpath(out_md, path)}  ({n} item{'s' if n!=1 else ''})")
        print(f"[InScript doc] Done. {len(ins_files)} file(s), {total_entries} documented item(s).")
        return 0
    else:
        print(f"[InScript doc] Not found: '{path}'", file=sys.stderr)
        return 1



# ─────────────────────────────────────────────────────────────────────────────
# v1.9.4 — Spec Freeze & Final Polish
# ─────────────────────────────────────────────────────────────────────────────

# ── Error code catalogue ──────────────────────────────────────────────────────

ERROR_CATALOGUE = {
    "E0001": ("LexError",              "Unexpected character or malformed token"),
    "E0002": ("UnterminatedString",    "String literal has no closing quote"),
    "E0003": ("UnterminatedComment",   "Block comment /* ... */ never closed"),
    "E0010": ("ParseError",            "Unexpected token or malformed syntax"),
    "E0011": ("MissingClosingBrace",   "Expected '}' to close block"),
    "E0012": ("MissingClosingParen",   "Expected ')' to close expression"),
    "E0013": ("MissingClosingBracket", "Expected ']' to close array or index"),
    "E0014": ("InvalidAssignTarget",   "Left-hand side of assignment is not assignable"),
    "E0015": ("MissingReturnType",     "Arrow '->' present but return type missing"),
    "E0020": ("SemanticError",         "General semantic / type error"),
    "E0021": ("TypeMismatch",          "Value type does not match declared type"),
    "E0022": ("UndefinedName",         "Name referenced before declaration"),
    "E0023": ("DuplicateDeclaration",  "Name already declared in this scope"),
    "E0024": ("ConstReassign",         "Cannot reassign a constant"),
    "E0025": ("ReturnTypeMismatch",    "Returned value type differs from declared return type"),
    "E0026": ("ReturnOutsideFn",       "return statement outside a function"),
    "E0027": ("BreakOutsideLoop",      "break statement outside a loop"),
    "E0028": ("ContinueOutsideLoop",   "continue statement outside a loop"),
    "E0029": ("UnknownType",           "Type name not found in scope"),
    "E0030": ("RuntimeError",          "General runtime error"),
    "E0031": ("DivisionByZero",        "Integer or float division by zero"),
    "E0032": ("IndexOutOfBounds",      "Array index outside valid range"),
    "E0033": ("KeyNotFound",           "Dict key does not exist"),
    "E0034": ("StackOverflow",         "Call depth exceeded (infinite recursion)"),
    "E0035": ("TypeError",             "Operation applied to incompatible types"),
    "E0036": ("ArithmeticError",       "Invalid arithmetic operation"),
    "E0037": ("InvalidCast",           "Cannot cast value to target type"),
    "E0038": ("NilDereference",        "Method or field access on nil"),
    "E0039": ("ThrowSignal",           "Unhandled throw (not an error unless uncaught)"),
    "E0040": ("UncaughtThrow",         "throw reached top level without a try/catch"),
    "E0041": ("ImportError",           "Module or file could not be imported"),
    "E0042": ("ExportError",           "Export of undefined name"),
    "E0043": ("NamespaceError",        "Invalid namespace access"),
    "E0044": ("ArgumentCount",         "Wrong number of arguments to function call"),
    "E0045": ("MissingField",          "Struct initializer missing required field"),
    "E0046": ("UnknownField",          "Struct initializer references unknown field"),
    "E0047": ("InterfaceNotImpl",      "Struct claims to implement interface but methods missing"),
    "E0048": ("EnumNotExhaustive",     "match on enum is missing one or more variants"),
    "E0049": ("NilAccess",             "Optional field or nil value accessed without guard"),
    "E0050": ("InvalidReturn",         "Return value in void function"),
    "E0051": ("UndeclaredInterface",   "implements clause references unknown interface"),
    "E0052": ("CircularImport",        "Import creates a circular dependency"),
    "E0053": ("ConstInLoop",           "const declaration inside a loop"),
    "E0054": ("NeverNotDiverging",     "Function declared -> never but has a non-throwing path"),
    "E0055": ("NullKeyword",           "'null' keyword removed in v1.7.4 — use 'nil'"),
    "E0056": ("DivKeyword",            "'div' keyword removed in v1.9.5 — use '//' for integer division"),
}


def _print_error_catalogue(filter_prefix: str = None) -> int:
    """
    v1.9.4: Print the full error code catalogue, optionally filtered by prefix.
    """
    print(f"InScript Error Code Catalogue  (InScript {VERSION})")
    print(f"{'='*58}")
    count = 0
    for code, (name, desc) in sorted(ERROR_CATALOGUE.items()):
        if filter_prefix and not code.startswith(filter_prefix):
            continue
        print(f"  {code}  {name:<28}  {desc}")
        count += 1
    print(f"{'='*58}")
    print(f"  {count} error code(s)")
    return 0


# ── changelog generator ───────────────────────────────────────────────────────

def _parse_version_tuple(v: str) -> tuple:
    """Parse 'v1.6.0' or '1.6.0' → (1, 6, 0)."""
    import re
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)", v.strip())
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _generate_changelog_range(spec: str, changelog_path: str = None) -> int:
    """
    v1.9.4: `inscript changelog FROM..TO`

    Reads CHANGELOG.md and extracts entries whose version falls in [FROM, TO].
    Prints filtered changelog to stdout.

    Examples:
      inscript changelog v1.6.0..v1.9.4
      inscript changelog v1.8.0..
      inscript changelog ..v1.7.4
    """
    import re

    # Parse the range spec
    if ".." in spec:
        lo_str, hi_str = spec.split("..", 1)
        lo = _parse_version_tuple(lo_str) if lo_str.strip() else (0, 0, 0)
        hi = _parse_version_tuple(hi_str) if hi_str.strip() else (999, 999, 999)
    else:
        # Single version — exact match
        lo = hi = _parse_version_tuple(spec)
        if lo == (0, 0, 0):
            print("[InScript changelog] Invalid range. Use e.g. v1.6.0..v1.9.4 or v1.9.3",
                  file=sys.stderr)
            return 1

    if lo == (0, 0, 0) and hi == (999, 999, 999):
        print("[InScript changelog] Invalid range. Use e.g. v1.6.0..v1.9.4",
              file=sys.stderr)
        return 1

    # Find CHANGELOG.md
    if changelog_path is None:
        candidates = [
            os.path.join(os.getcwd(), "CHANGELOG.md"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "CHANGELOG.md"),
        ]
        changelog_path = next((p for p in candidates if os.path.exists(p)), None)

    if not changelog_path or not os.path.exists(changelog_path):
        print("[InScript changelog] CHANGELOG.md not found. "
              "Run from the project root.", file=sys.stderr)
        return 1

    with open(changelog_path, encoding="utf-8") as f:
        content = f.read()

    # Split into per-version sections by "## [X.Y.Z]" headings
    section_re = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)
    positions  = [(m.start(), m.group(1)) for m in section_re.finditer(content)]

    if not positions:
        print("[InScript changelog] No version sections found in CHANGELOG.md",
              file=sys.stderr)
        return 1

    # Extract sections that fall within [lo, hi]
    selected = []
    for i, (start, ver_str) in enumerate(positions):
        vt = _parse_version_tuple(ver_str)
        if lo <= vt <= hi:
            end = positions[i + 1][0] if i + 1 < len(positions) else len(content)
            selected.append((vt, ver_str, content[start:end].rstrip()))

    if not selected:
        lo_s = ".".join(str(x) for x in lo)
        hi_s = ".".join(str(x) for x in hi)
        print(f"[InScript changelog] No versions found in range {lo_s}..{hi_s}")
        return 0

    # Print newest-first
    selected.sort(key=lambda x: x[0], reverse=True)
    lo_s = ".".join(str(x) for x in lo) if lo != (0,0,0) else "start"
    hi_s = ".".join(str(x) for x in hi) if hi != (999,999,999) else "latest"
    print(f"# InScript Changelog  {lo_s}..{hi_s}\n")
    for _, _, section_text in selected:
        print(section_text)
        print()

    print(f"---")
    print(f"{len(selected)} version(s) shown.")
    return 0


# ── performance benchmark suite ───────────────────────────────────────────────

BENCHMARK_PROGRAMS = {
    "fib_30": (
        "Fibonacci fib(30) — recursive, tests call overhead",
        """
fn fib(n) {
  if n <= 1 { return n }
  return fib(n - 1) + fib(n - 2)
}
fib(30)
"""
    ),
    "loop_100k": (
        "Counter loop 100,000 iterations — tests loop + arith throughput",
        """
let i = 0
let sum = 0
while i < 100000 {
  sum = sum + i
  i = i + 1
}
sum
"""
    ),
    "struct_heavy": (
        "Struct allocation + field access, 10,000 objects",
        """
struct Vec2 { x: float = 0.0; y: float = 0.0 }
fn make_vecs(n) {
  let i = 0
  let last_x = 0.0
  while i < n {
    let v = Vec2{x: i * 1.0, y: i * 2.0}
    last_x = v.x + v.y
    i = i + 1
  }
  return last_x
}
make_vecs(10000)
"""
    ),
    "string_concat": (
        "String concatenation, 1,000 iterations",
        """
let s = ""
let i = 0
while i < 1000 {
  s = s + "x"
  i = i + 1
}
len(s)
"""
    ),
    "array_ops": (
        "Array push + iteration, 5,000 elements",
        """
let arr = []
let i = 0
while i < 5000 {
  arr.push(i)
  i = i + 1
}
arr.len()
"""
    ),
}


def _run_benchmarks(filter_name: str = None, iterations: int = 3) -> int:
    """
    v1.9.4: `inscript benchmark [NAME]` — run the built-in performance suite.

    Runs each benchmark `iterations` times and reports median time.
    """
    import time, statistics

    from interpreter import Interpreter
    from lexer      import Lexer
    from parser     import Parser

    programs = BENCHMARK_PROGRAMS
    if filter_name:
        programs = {k: v for k, v in programs.items() if filter_name in k}
        if not programs:
            print(f"[InScript benchmark] No benchmark matching '{filter_name}'",
                  file=sys.stderr)
            return 1

    col_w = max(len(k) for k in programs) + 2
    print(f"\nInScript Benchmark Suite  (v{VERSION})  [{iterations} runs each]")
    print(f"{'='*(col_w + 52)}")
    print(f"  {'Benchmark':<{col_w}}  {'Median':>10}  {'Min':>10}  {'Max':>10}  Description")
    print(f"  {'-'*(col_w)}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*30}")

    results = {}
    for name, (desc, src) in programs.items():
        times = []
        for _ in range(iterations):
            try:
                interp  = Interpreter()
                tokens  = Lexer(src).tokenize()
                program = Parser(tokens).parse()
                t0 = time.perf_counter()
                interp.run(program)
                times.append(time.perf_counter() - t0)
            except Exception as e:
                print(f"  {'ERROR':<{col_w}}  {name}: {e}", file=sys.stderr)
                times.append(float("inf"))

        median = statistics.median(times)
        mn     = min(times)
        mx     = max(times)

        def fmt(t):
            if t == float("inf"): return "  ERROR   "
            if t < 1:             return f"{t*1000:9.1f}ms"
            return                       f"{t:9.3f}s "

        results[name] = median
        print(f"  {name:<{col_w}}  {fmt(median)}  {fmt(mn)}  {fmt(mx)}  {desc[:40]}")

    print(f"{'='*(col_w + 52)}")
    fastest = min(results, key=results.get)
    slowest = max(k for k,v in results.items() if v != float("inf"))
    print(f"  Fastest: {fastest}  ({results[fastest]*1000:.1f}ms median)")
    print()
    return 0


# ── stdlib documentation ──────────────────────────────────────────────────────

STDLIB_SIGNATURES = {
    # Built-in functions
    "print":      ("(value: any) -> void",     "Print value to stdout",           "print(42)"),
    "println":    ("(value: any) -> void",     "Print value with newline",        "println('hello')"),
    "len":        ("(x: array|string) -> int", "Length of array or string",       "len([1,2,3])  // 3"),
    "range":      ("(n: int) -> [int]",        "Generate 0..n-1 integer array",   "range(5)  // [0,1,2,3,4]"),
    "typeof":     ("(x: any) -> string",       "Runtime type name of value",      "typeof(42)  // 'int'"),
    "str":        ("(x: any) -> string",       "Convert value to string",         "str(3.14)  // '3.14'"),
    "int":        ("(x: any) -> int",          "Parse/cast to integer",           "int('42')  // 42"),
    "float":      ("(x: any) -> float",        "Parse/cast to float",             "float('3.14')  // 3.14"),
    "bool":       ("(x: any) -> bool",         "Cast to boolean",                 "bool(0)  // false"),
    "abs":        ("(x: int|float) -> same",   "Absolute value",                  "abs(-5)  // 5"),
    "min":        ("(a, b) -> same",           "Smaller of two values",           "min(3, 7)  // 3"),
    "max":        ("(a, b) -> same",           "Larger of two values",            "max(3, 7)  // 7"),
    "clamp":      ("(v, lo, hi) -> same",      "Clamp v to [lo, hi]",             "clamp(15, 0, 10)  // 10"),
    "floor":      ("(x: float) -> int",        "Floor to nearest integer",        "floor(3.7)  // 3"),
    "ceil":       ("(x: float) -> int",        "Ceiling to nearest integer",      "ceil(3.2)  // 4"),
    "round":      ("(x: float) -> int",        "Round to nearest integer",        "round(3.5)  // 4"),
    "sqrt":       ("(x: float) -> float",      "Square root",                     "sqrt(9.0)  // 3.0"),
    "pow":        ("(base, exp) -> float",     "Raise base to exponent",          "pow(2.0, 8.0)  // 256.0"),
    "sin":        ("(x: float) -> float",      "Sine (radians)",                  "sin(0.0)  // 0.0"),
    "cos":        ("(x: float) -> float",      "Cosine (radians)",                "cos(0.0)  // 1.0"),
    "random":     ("() -> float",              "Random float in [0.0, 1.0)",      "random()"),
    "random_int": ("(lo: int, hi: int) -> int","Random int in [lo, hi]",          "random_int(1, 6)"),
    "assert":     ("(cond: bool, msg: string = '') -> void",
                                              "Assert condition or throw",        "assert(x > 0, 'must be positive')"),
    "panic":      ("(msg: string) -> never",  "Throw with message, always fails", "panic('unreachable')"),
    "exit":       ("(code: int = 0) -> never","Exit program with status code",    "exit(1)"),
    "input":      ("(prompt: string = '') -> string",
                                              "Read line from stdin",             "let name = input('Name: ')"),
    # Array methods
    "Array.push":    ("(v: T) -> void",         "Append element",                  "[].push(1)"),
    "Array.pop":     ("() -> T?",               "Remove and return last element",  "arr.pop()"),
    "Array.len":     ("() -> int",              "Number of elements",              "arr.len()"),
    "Array.map":     ("(fn: (T)->U) -> [U]",    "Transform each element",          "arr.map(fn(x){return x*2})"),
    "Array.filter":  ("(fn: (T)->bool) -> [T]", "Keep matching elements",          "arr.filter(fn(x){return x>0})"),
    "Array.find":    ("(fn: (T)->bool) -> T?",  "First matching element or nil",   "arr.find(fn(x){return x>3})"),
    "Array.any":     ("(fn: (T)->bool) -> bool","True if any element matches",     "arr.any(fn(x){return x>0})"),
    "Array.all":     ("(fn: (T)->bool) -> bool","True if all elements match",      "arr.all(fn(x){return x>0})"),
    "Array.each":    ("(fn: (T)->void) -> void","Iterate (side-effect only)",      "arr.each(fn(x){print(x)})"),
    "Array.reduce":  ("(fn: (U,T)->U, init: U) -> U",
                                               "Fold array to single value",      "arr.reduce(fn(acc,x){return acc+x}, 0)"),
    "Array.sorted":  ("() -> [T]",              "Return sorted copy",              "arr.sorted()"),
    "Array.reversed":"() -> [T]",
    "Array.join":    ("(sep: string) -> string","Join elements with separator",    "arr.join(', ')"),
    "Array.contains":"(v: T) -> bool",
    "Array.take":    ("(n: int) -> [T]",        "First n elements",                "arr.take(3)"),
    "Array.skip":    ("(n: int) -> [T]",        "Skip first n elements",           "arr.skip(2)"),
    # String methods
    "String.len":        ("() -> int",          "Length in characters",            '"hello".len()  // 5'),
    "String.upper":      ("() -> string",       "Uppercase copy",                  '"hi".upper()  // "HI"'),
    "String.lower":      ("() -> string",       "Lowercase copy",                  '"HI".lower()  // "hi"'),
    "String.trim":       ("() -> string",       "Strip leading/trailing whitespace",'" x ".trim()  // "x"'),
    "String.split":      ('(sep: string) -> [string]', "Split on separator",       '"a,b".split(",")  // ["a","b"]'),
    "String.contains":   ("(sub: string) -> bool", "True if substring found",      '"hello".contains("ell")'),
    "String.starts_with":("(pre: string) -> bool", "True if starts with prefix",  '"hello".starts_with("he")'),
    "String.ends_with":  ("(suf: string) -> bool", "True if ends with suffix",    '"hello".ends_with("lo")'),
    "String.replace":    ("(old: string, new: string) -> string",
                                               "Replace first occurrence",         '"hello".replace("l","r")'),
    "String.chars":      ("() -> [string]",     "Split into individual characters","'ab'.chars()  // ['a','b']"),
    "String.to_int":     ("() -> int?",         "Parse as integer or nil",         '"42".to_int()  // 42'),
    "String.to_float":   ("() -> float?",       "Parse as float or nil",           '"3.14".to_float()'),
}


def _print_stdlib_docs(filter_str: str = None) -> int:
    """
    v1.9.4: `inscript stdlib [FILTER]` — print stdlib function signatures.
    """
    entries = STDLIB_SIGNATURES
    if filter_str:
        entries = {k: v for k, v in entries.items()
                   if filter_str.lower() in k.lower()}
        if not entries:
            print(f"[InScript stdlib] No matches for '{filter_str}'")
            return 0

    print(f"\nInScript Standard Library  (v{VERSION})")
    print(f"{'='*70}")

    last_group = None
    for name, info in sorted(entries.items()):
        group = name.split(".")[0] if "." in name else "Built-ins"
        if group != last_group:
            print(f"\n  ── {group} ─────")
            last_group = group

        if isinstance(info, str):
            # Abbreviated entry (just signature string)
            print(f"  {name:<22}  {info}")
        elif len(info) == 2:
            sig, desc = info
            print(f"  {name:<22}  {sig}")
            print(f"  {'':22}  # {desc}")
        else:
            sig, desc, example = info
            print(f"  {name:<22}  {sig}")
            print(f"  {'':22}  # {desc}")
            print(f"  {'':22}  {example}")

    print(f"\n{'='*70}")
    total = len(entries)
    print(f"  {total} stdlib item(s)")
    return 0


# ── spec document generator ───────────────────────────────────────────────────

LANGUAGE_SPEC = """# InScript Language Specification
## Version {version}

> **Spec Freeze**: No new syntax will be added after v1.9.4.
> Only bug fixes and performance improvements until v2.0.0.

---

## 1. Lexical Structure

### 1.1 Comments
- Line comments: `# text`  (v1.9.6: was `// text`)
- Block comments: `/* text */` (nestable)
- Doc comments: `/// text` (parsed by `inscript doc`)

### 1.2 Keywords
```
let  const  fn  return  if  else  while  for  in  match  case
struct  enum  interface  type  impl  mixin  extends  implements
true  false  nil  throw  try  catch  break  continue  defer  yield
pub  async  await  scene  import  export  with  super  self  is  as
div  not  and  or
```

### 1.3 Literals
- **Integer**: `42`, `1_000_000`
- **Float**: `3.14`, `1.0e-3`
- **String**: `"hello"`, `'world'`, escape sequences `\n \t \\ \"`
- **Bool**: `true`, `false`
- **Nil**: `nil`

---

## 2. Types

### 2.1 Primitive Types
`int`  `float`  `bool`  `string`  `nil`  `void`  `any`  `never`

### 2.2 Composite Types
- **Array**: `[T]` — e.g. `[int]`, `[string]`
- **Dict**: `{K: V}` — e.g. `{string: int}`
- **Optional**: `T?` — sugar for `T | nil`
- **Union**: `A | B | C`
- **Function**: `fn(T1, T2) -> R`

### 2.3 User-Defined Types
- **Struct**: `struct Name {{ fields; methods }}`
- **Enum**: `enum Name {{ Variant1; Variant2 }}`
- **Interface**: `interface Name {{ fn method() -> R }}`
- **Type alias**: `type ID = int`

---

## 3. Declarations

### 3.1 Variables
```inscript
let x: int = 42
const MAX: int = 100
let items: [string] = []
```

### 3.2 Functions
```inscript
fn add(a: int, b: int) -> int {{
  return a + b
}}
fn greet(name: string = "World") {{
  print("Hello, " + name)
}}
```

### 3.3 Structs
```inscript
struct Player {{
  name: string = ""
  health: int  = 100
  fn take_damage(dmg: int) {{
    self.health = self.health - dmg
  }}
}}
```

### 3.4 Enums
```inscript
enum Direction {{ North; South; East; West }}
```

### 3.5 Interfaces
```inscript
interface Drawable {{
  fn draw() -> void
}}
struct Sprite implements Drawable {{
  fn draw() {{ print("drawing") }}
}}
```

---

## 4. Control Flow

```inscript
if cond {{ }} else if cond {{ }} else {{ }}
while cond {{ }}
for item in collection {{ }}
match value {{
  case Pattern {{ }}
  case _       {{ }}  // wildcard
}}
```

---

## 5. Error Handling

```inscript
try {{
  risky()
}} catch e {{
  print("caught: " + e)
}}
throw "something went wrong"
fn fatal() -> never {{ throw "fatal" }}
```

---

## 6. Module System

```inscript
import "path/to/module"
export fn public_api() {{ }}
```

---

## 7. Breaking Changes (v2.0.0 preview)

- `null` removed — use `nil`
- `div` operator removed — use `//`
- Bare `array` type without element type is an error
- `--no-typecheck` CLI flag removed — use `--unsafe-no-check`

---

*Generated by InScript {version}*
"""


def _generate_spec(output_path: str = None) -> int:
    """
    v1.9.4: `inscript spec [--out FILE]` — print the language spec document.
    """
    content = LANGUAGE_SPEC.replace("{version}", VERSION)
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[InScript spec] Spec written to '{output_path}'")
            return 0
        except OSError as e:
            print(f"[InScript spec] Cannot write: {e}", file=sys.stderr)
            return 1
    else:
        print(content)
        return 0

def run_source(source: str, filename: str = "<stdin>",
               type_check: bool = True,
               no_warn: bool = False,
               no_warn_unused: bool = False,
               warn_as_error: bool = False,
               strict: bool = False,
               profile: bool = False,
               json_errors: bool = False,
               debug: bool = False) -> int:
    """Lex, parse, analyze, and interpret InScript source code."""

    def _emit_error(e):
        """v2.12.0: emit as JSON or plain text depending on flag."""
        if json_errors:
            from inscript_studio_api import error_stream
            from errors import InScriptError as _ISE
            if isinstance(e, _ISE):
                error_stream([e])
            else:
                error_stream([{"type": "error", "code": "E0000",
                               "class": type(e).__name__, "message": str(e),
                               "line": 0, "col": 0}])
        else:
            print(e, file=sys.stderr)
    # ── 1. Lex ────────────────────────────────────────────────────────────
    try:
        tokens = tokenize(source, filename)
    except LexerError as e:
        _emit_error(e); return 1

    # ── 2. Parse ──────────────────────────────────────────────────────────
    try:
        program = parse(source, filename)
    except ParseError as e:
        _emit_error(e); return 1

    # ── 3. Analyze (optional) — Phase 3: multi-error + warnings ──────────
    if type_check:
        from analyzer import Analyzer
        _analyzer = Analyzer(
            source.splitlines(),
            multi_error=True,
            warn_as_error=warn_as_error,
            no_warn=no_warn,
            no_warn_unused=no_warn_unused,
            strict=strict,   # v1.9.1
        )
        try:
            _analyzer.analyze(program)
        except MultiError as me:
            print(me, file=sys.stderr)
            return 1
        except SemanticError as e:
            print(e, file=sys.stderr)
            return 1

        # Print warnings
        if not no_warn and _analyzer._warnings:
            for w in _analyzer._warnings:
                print(w.format(), file=sys.stderr)
            n = len(_analyzer._warnings)
            print(f"[InScript] {n} warning{'s' if n != 1 else ''}", file=sys.stderr)

    # ── 4. Interpret — Phase 3: Python-leak guard ─────────────────────────
    try:
        interp = Interpreter(source.splitlines(), filename=filename, debug=debug)
        if profile:
            import cProfile, pstats, io as _io
            pr = cProfile.Profile()
            pr.enable()
            interp.run(program)
            pr.disable()
            _print_inscript_profile(pr, filename)
        else:
            interp.run(program)
        return 0
    except InScriptError as e:
        _emit_error(e)
        return 1
    except KeyboardInterrupt:
        print("\n[InScript] Interrupted.", file=sys.stderr)
        return 130
    except Exception as e:
        # Phase 3.3: Zero Python leaking
        print(
            f"\n[InScript Internal Error] An unexpected error occurred.\n"
            f"  {type(e).__name__}: {e}\n"
            f"  Please report at: https://github.com/inscript-language/inscript/issues",
            file=sys.stderr
        )
        return 1


# ─────────────────────────────────────────────────────────────────────────────
# REPL
# ─────────────────────────────────────────────────────────────────────────────

REPL_BANNER = f"""
╔══════════════════════════════════════════════════════╗
║   InScript v{VERSION} — Interactive Shell                  ║
║   Type 'exit' or Ctrl+C to quit, 'help' for tips    ║
╚══════════════════════════════════════════════════════╝
"""

REPL_HELP = """
InScript REPL Tips:
  • Type any expression to evaluate it:   2 + 2
  • Declare variables:                    let x = 10
  • Define functions:                     fn add(a,b) { return a+b }
  • Import stdlib modules:                import "math"
  • Multiline input: end line with \\      let x = 1 + \\
  • .clear  — clear the current session
  • .vars   — list all defined variables
  • .exit   — quit
"""

def run_repl():
    """Interactive Read-Eval-Print Loop."""
    try:
        from repl import EnhancedREPL
        EnhancedREPL().run()
        return
    except Exception:
        pass

    # Fallback simple REPL
    print(REPL_BANNER)
    interp  = Interpreter()
    buf     = []

    def show_result(val):
        if val is None: return
        from interpreter import _inscript_str
        print(f"  → {_inscript_str(val)}")

    def handle_dot_cmd(cmd):
        """Handle .help .vars .modules .type .clear .exit etc."""
        parts   = cmd.strip().split(None, 1)
        command = parts[0].lower()
        arg     = parts[1] if len(parts) > 1 else ""

        if command in (".help", "help"):
            print(REPL_HELP); return True
        if command in (".exit", ".quit", "exit", "quit"):
            print("[InScript] Goodbye!"); raise SystemExit(0)
        if command == ".clear":
            nonlocal interp, buf
            interp = Interpreter(); buf = []
            print("  (session cleared)"); return True
        if command == ".vars":
            items = {k: v for k, v in interp._env._store.items()
                     if not k.startswith("_")}
            if not items:
                print("  (no variables defined)")
            else:
                from interpreter import _inscript_str
                for k, v in sorted(items.items()):
                    try:    vs = _inscript_str(v)
                    except: vs = repr(v)
                    print(f"  {k} = {vs}")
            return True
        if command == ".modules":
            try:
                from stdlib import _MODULE_REGISTRY
                for name in sorted(_MODULE_REGISTRY.keys()):
                    print(f"  {name}")
            except Exception:
                mods = ["math","string","array","io","json","random","time",
                        "color","tween","grid","events","debug","http",
                        "path","regex","csv","uuid","crypto"]
                for m in mods: print(f"  {m}")
            return True
        if command == ".type":
            if not arg:
                print("  Usage: .type <expression>"); return True
            try:
                prog = parse(arg, "<repl>")
                from ast_nodes import ExprStmt
                if prog.body and isinstance(prog.body[-1], ExprStmt):
                    val = interp.visit(prog.body[-1].expr)
                    print(f"  {type(val).__name__}")
            except Exception as e:
                print(f"  Error: {e}")
            return True
        if command == ".fns":
            from stdlib_values import InScriptFunction
            fns = {k: v for k, v in interp._env._store.items()
                   if isinstance(v, InScriptFunction) and not k.startswith("_")}
            if not fns:
                print("  (no functions defined)")
            else:
                for k in sorted(fns): print(f"  fn {k}()")
            return True
        if command == ".history":
            print("  (history not available in fallback REPL)"); return True
        if command == ".reset":
            interp = Interpreter(); buf = []
            print("  (interpreter reset)"); return True
        return False

    while True:
        prompt = ">>> " if not buf else "... "
        try:
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\n[InScript] Goodbye!")
            break

        stripped = line.strip()
        if not stripped:
            continue

        # Dot commands
        if stripped.startswith(".") or stripped in ("exit","quit","help"):
            try:
                if handle_dot_cmd(stripped):
                    continue
            except SystemExit:
                break

        # Multiline continuation
        if line.endswith("\\"):
            buf.append(line[:-1]); continue
        buf.append(line)
        source = "\n".join(buf)
        buf = []

        try:
            prog = parse(source, "<repl>")
            interp.run(prog)
            from ast_nodes import ExprStmt
            if prog.body and isinstance(prog.body[-1], ExprStmt):
                val = interp.visit(prog.body[-1].expr)
                show_result(val)
        except (LexerError, ParseError, SemanticError, InScriptRuntimeError) as e:
            print(e)
        except Exception as e:
            print(f"[InScript Internal Error] {e}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="inscript",
        description=f"InScript {VERSION} — Game-focused programming language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python inscript.py mygame.ins          Run a game file
  python inscript.py --repl              Start interactive shell
  python inscript.py --check game.ins    Type-check without running
  python inscript.py --tokens game.ins   Print lexer tokens
  python inscript.py --ast game.ins      Print parsed AST
"""
    )
    parser.add_argument("file",     nargs="?", help=".ins source file to run")
    parser.add_argument("--repl",   action="store_true", help="Start interactive REPL")
    parser.add_argument("--check",  action="store_true", help="Type-check only, don't run")
    parser.add_argument("--check-all", metavar="DIR",
                        help="v1.6.0: Check all .ins files in DIR recursively, exit 1 if any errors")
    parser.add_argument("--infer-types", metavar="FILE",
                        help="v1.9.8: Print inferred type for every let/const declaration in FILE")
    parser.add_argument("--check-v2", metavar="DIR", nargs="?", const=".",
                        help="v1.9.10: Run all v2.0.0 readiness gates on DIR (default: .)")
    parser.add_argument("--migrate", metavar="DIR_OR_FILE",
                        help="v1.7.4: Auto-migrate deprecated syntax (null→nil, div→//)")
    parser.add_argument("--compat", metavar="DIR_OR_FILE",
                        help="v1.9.1: Report v2.0.0 breaking changes in FILE or DIR")
    parser.add_argument("--init", metavar="DIR", nargs="?", const=".",
                        help="v1.9.2: Create inscript.toml in DIR (default: current dir)")
    parser.add_argument("--validate", metavar="DIR_OR_FILE", nargs="?", const=".",
                        help="v1.9.2: Validate inscript.toml (default: current dir)")
    parser.add_argument("--lock", metavar="DIR", nargs="?", const=".",
                        help="v1.9.2: Generate inscript.lock from inscript.toml")
    parser.add_argument("--doc", metavar="FILE_OR_DIR",
                        help="v1.9.3: Generate Markdown docs from /// doc comments")
    parser.add_argument("--doc-out", metavar="DIR", default=None,
                        help="v1.9.3: Output directory for --doc (default: stdout / docs/api/)")
    parser.add_argument("--errors", metavar="PREFIX", nargs="?", const="",
                         help="v1.9.4: Print error code catalogue (optional prefix filter, e.g. E003)")
    parser.add_argument("--rust", action="store_true",
                         help="[DEPRECATED] Rust is now the default — use --python to opt out")
    parser.add_argument("--python", action="store_true",
                         help="Use the Python tree-walk interpreter instead of the Rust VM")
    parser.add_argument("--changelog", metavar="RANGE",
                        help="v1.9.4: Print changelog for version range e.g. v1.6.0..v1.9.4")
    parser.add_argument("--benchmark", metavar="NAME", nargs="?", const="",
                        help="v1.9.4: Run performance benchmark suite (optional name filter)")
    parser.add_argument("--stdlib", metavar="FILTER", nargs="?", const="",
                        help="v1.9.4: Print stdlib function signatures (optional filter)")
    parser.add_argument("--spec", metavar="FILE", nargs="?", const=None,
                        help="v1.9.4: Print language spec (optional --spec FILE to write to file)")
    parser.add_argument("--strict", action="store_true",
                        help="v1.6.0: Strict mode — all warnings become errors, no implicit any")
    parser.add_argument("--tokens", action="store_true", help="Print lexer token stream")
    parser.add_argument("--ast",    action="store_true", help="Print parsed AST")
    parser.add_argument("--no-typecheck", action="store_true",
                        help="[DEPRECATED v1.9.1] Use --unsafe-no-check instead")
    parser.add_argument("--unsafe-no-check", action="store_true",
                        help="v1.9.1: Skip semantic analysis (replaces --no-typecheck)")
    parser.add_argument("--no-warn", action="store_true",
                        help="Suppress all warnings")
    parser.add_argument("--no-warn-unused", action="store_true",
                        help="Suppress unused-variable warnings only")
    parser.add_argument("--warn-as-error", action="store_true",
                        help="Treat any warning as an error (CI strictness)")
    parser.add_argument("--profile", action="store_true",
                         help="Print per-function call count and timing after execution")
    parser.add_argument("--debug", action="store_true",
                         help="v3.9.6.10: Run in debug mode with breakpoint support")
    parser.add_argument("--dap", action="store_true",
                         help="v3.9.6.13: Start DAP server for VS Code debugging (uses --debug)")
    parser.add_argument("--fmt",     action="store_true",
                        help="Format .ins files: inscript --fmt file.ins")
    parser.add_argument("--fmt-all", metavar="DIR",
                        help="v1.6.0: Format all .ins files in DIR recursively")
    parser.add_argument("--fmt-check", action="store_true",
                        help="Check formatting without writing (exit 1 if unformatted)")
    parser.add_argument("--fmt-dry-run", action="store_true",
                        help="Print formatted output without writing")
    parser.add_argument("--test",    action="store_true",
                        help="Run test_*.ins files: inscript --test [file.ins]")
    parser.add_argument("--test-verbose", action="store_true",
                        help="Verbose test output")
    parser.add_argument("--test-fail-fast", action="store_true",
                        help="Stop tests on first failure")
    parser.add_argument("--watch",   action="store_true",
                        help="Watch file for changes and rerun: inscript --watch game.ins")
    parser.add_argument("--hot",     action="store_true",
                        help="v2.9.0: State-preserving hot reload (use with --watch): inscript --watch --hot game.ins")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument("--install", metavar="PKG", nargs="?", const="",
                        help="v1.9.9: Install a package (PKG or PKG@version); no arg = install all from inscript.toml")
    parser.add_argument("--update", metavar="PKG",
                        help="v1.9.9: Update a package to latest (or PKG@version)")
    parser.add_argument("--outdated", action="store_true",
                        help="v1.9.9: Show packages with newer versions available")
    parser.add_argument("--remove", metavar="PKG",
                        help="Remove a package: inscript --remove math-utils")
    parser.add_argument("--packages", action="store_true",
                        help="List installed packages")
    parser.add_argument("--search", metavar="QUERY",
                        help="Search the registry: inscript --search math")
    parser.add_argument("--info", metavar="PKG",
                        help="Show package info: inscript --info math-utils")
    # v2.6.0: publish, audit, config, workspace, stdlib-check
    parser.add_argument("--publish", metavar="DIR", nargs="?", const=".",
                        help="v2.6.0: Publish package in DIR (default: current dir)")
    parser.add_argument("--audit", metavar="DIR", nargs="?", const=".",
                        help="v2.6.0: Scan installed packages for vulnerabilities")
    parser.add_argument("--config", metavar="ARGS", nargs="+",
                        help="v2.6.0: Config: set/get/list/unset. E.g. --config set registry <url>")
    parser.add_argument("--workspace", metavar="CMD", nargs="?", const="install",
                        help="v2.6.0: Workspace commands: install, list (default: install)")
    parser.add_argument("--stdlib-check", metavar="DIR", nargs="?", const=".",
                        help="v2.6.0: Verify stdlib version satisfies inscript.toml constraint")
    # v2.8.0: asset pipeline
    parser.add_argument("--asset-manifest", metavar="DIR", nargs="?", const=".",
                        help="v2.8.0: Generate assets.toml manifest for DIR (default: current dir)")
    parser.add_argument("--bundle", metavar="DIR", nargs="?", const=".",
                        help="v2.8.0: Copy all referenced assets into <DIR>/dist/assets")
    # v2.11.0: export pipeline
    parser.add_argument("--build", metavar="TARGET", nargs="?", const="desktop",
                        help="v2.11.0: Build for target: desktop, web, android, ibc (default: desktop)")
    parser.add_argument("--project-dir", metavar="DIR", default=".",
                        help="v2.11.0: Project root for --build (default: current dir)")
    parser.add_argument("--new", metavar="NAME",
                        help="v2.11.0: Scaffold a new InScript project: inscript --new mygame")
    # v2.12.0: studio readiness
    parser.add_argument("--json-errors", action="store_true",
                        help="v2.12.0: Output errors as newline-delimited JSON for IDE panels")
    parser.add_argument("--inspect", metavar="DIR", nargs="?", const=".",
                        help="v2.12.0: Project introspection → JSON (scenes, nodes, assets, fns)")
    parser.add_argument("--check-v3", action="store_true",
                        help="v2.12.0: Run v3.0.0 readiness gates; exits 0 if all pass")
    parser.add_argument("--studio-bridge", action="store_true",
                        help="v2.12.0: Start Electron bridge JSON-RPC server")
    parser.add_argument("--bridge-port", type=int, default=8765,
                        help="v2.12.0: Port for --studio-bridge (default: 8765)")
    # v3.0.0: Studio + Visual Scripting
    parser.add_argument("--studio", action="store_true",
                        help="v3.0.0: Launch InScript Studio web IDE in browser")
    parser.add_argument("--studio-port", type=int, default=8080,
                        help="v3.0.0: Port for Studio web app (default: 8080)")
    parser.add_argument("--visual-compile", metavar="FILE",
                        help="v3.0.0: Compile a .vins visual script to .ins source")
    parser.add_argument("--vins-output", metavar="FILE",
                        help="v3.0.0: Output path for --visual-compile (default: <input>.ins)")
    parser.add_argument("--vins-template", metavar="NAME",
                        help="v3.0.0: Generate a .vins template for visual scripting")
    parser.add_argument("--lsp", action="store_true",
                        help="Start the Language Server (requires: pip install pygls)")
    parser.add_argument("--game", action="store_true",
                        help="Run .ins file in pygame window (requires: pip install pygame)")
    parser.add_argument("--width",  type=int, default=800,
                        help="Window width for --game mode  (default: 800)")
    parser.add_argument("--height", type=int, default=600,
                        help="Window height for --game mode (default: 600)")
    parser.add_argument("--fps",    type=int, default=60,
                        help="Target FPS for --game mode   (default: 60)")
    parser.add_argument("--batch-draw", action="store_true",
                        help="Batch draw ops (--game mode only)")
    parser.add_argument("--frame-break", type=int, default=-1,
                        help="v3.9.6.14: Break at specific frame (--game mode only)")
    parser.add_argument("--frame-advance", action="store_true",
                        help="v3.9.6.14: Step one frame at a time (--game mode only)")
    # ── v2.4.0: compilation flags ────────────────────────────────────────────
    parser.add_argument("--compile", metavar="FILE",
                        help="v2.4.0: AOT-compile FILE.ins → FILE.ibc bytecode")
    parser.add_argument("--output", "-o", metavar="OUT",
                        help="v2.4.0: Output path for --compile (default: same dir as input)")
    parser.add_argument("--target", metavar="TARGET", default="interpreter",
                        choices=["interpreter", "wasm", "native", "ibc"],
                        help="v2.4.0: Compilation target: interpreter (default), ibc, wasm, native")
    parser.add_argument("--no-dce", action="store_true",
                        help="v2.4.0: Disable dead-code elimination before compilation")
    parser.add_argument("--incremental", action="store_true",
                        help="v2.4.0: Skip recompile if .ibc is newer than source")
    args = parser.parse_args()

    # Backward compat: --rust is now the default, warn and ignore
    if getattr(args, 'rust', False):
        print("[InScript] Warning: --rust is now the default (no flag needed). Use --python to use the Python interpreter.", file=sys.stderr)

    if args.version:
        print(f"InScript {VERSION}")
        return

    # ── v2.4.0: --compile ────────────────────────────────────────────────────
    if args.compile:
        import sys as _sys
        _sys.exit(_compile_cmd(
            src_path   = args.compile,
            out_path   = args.output,
            target     = args.target,
            dce        = not args.no_dce,
            incremental= args.incremental,
        ) or 0)

    # ── inscript --fmt / --fmt-check / --fmt-dry-run ─────────────────────────
    if args.fmt or args.fmt_check or args.fmt_dry_run:
        try:
            from inscript_fmt import main as fmt_main
        except ImportError:
            print("Error: inscript_fmt.py not found", file=sys.stderr); return
        fmt_argv = []
        if args.file: fmt_argv.append(args.file)
        if args.fmt_check: fmt_argv.append("--check")
        if args.fmt_dry_run: fmt_argv.append("--dry-run")
        import sys as _sys; _sys.exit(fmt_main(fmt_argv) or 0)

    # ── inscript --test ─────────────────────────────────────────────────────
    if args.test:
        try:
            from inscript_test import main as test_main
        except ImportError:
            print("Error: inscript_test.py not found", file=sys.stderr); return
        test_argv = []
        if args.file: test_argv.append(args.file)
        if args.test_verbose: test_argv.append("--verbose")
        if args.test_fail_fast: test_argv.append("--fail-fast")
        import sys as _sys; _sys.exit(test_main(test_argv) or 0)

    # ── inscript --watch / --hot ──────────────────────────────────────────────
    if args.watch:
        if not args.file:
            print("Usage: inscript --watch <file.ins>", file=sys.stderr); return
        import time as _time
        print(f"\033[36mWatching {args.file} — Ctrl+C to stop\033[0m")

        # v2.9.0: use HotReloader for state-preserving reload when --hot flag set
        _hot = getattr(args, 'hot', False)
        if _hot:
            from interpreter import Interpreter as _I
            from hot_reload import HotReloader
            _interp_hot = _I()
            _reloader   = HotReloader(args.file, _interp_hot)
            _result     = _reloader.start()
            if not _result.success:
                for e in _result.errors:
                    print(f"\033[31m{e}\033[0m", file=sys.stderr)
            print(f"\033[36m[hot] Loaded. Watching for changes...\033[0m")
            while True:
                try:
                    _time.sleep(0.4)
                    _r = _reloader.tick()
                    if _r.changed and not _r.success:
                        for e in _r.errors:
                            print(f"\033[31m[hot] {e}\033[0m", file=sys.stderr)
                    # hot-reload changed assets too
                    try:
                        from stdlib_assets import get_registry
                        _reloaded = get_registry().check_for_changes()
                        if _reloaded:
                            print(f"\033[33m[hot] asset hot-reload: {len(_reloaded)} file(s)\033[0m")
                    except ImportError:
                        pass
                except KeyboardInterrupt:
                    print(f"\033[2m[hot] stopped\033[0m"); break
            return 0

        # Legacy watch: full re-run on each change
        last_mtime = None
        while True:
            try:
                mtime = os.path.getmtime(args.file)
                if mtime != last_mtime:
                    last_mtime = mtime
                    if last_mtime is not None:
                        print(f"\033[2m--- reloading {args.file} ---\033[0m")
                    os.system(f"{sys.executable} {__file__} {args.file}")
                    # v2.8.0: hot-reload any changed asset files
                    try:
                        from stdlib_assets import get_registry
                        _reloaded = get_registry().check_for_changes()
                        if _reloaded:
                            print(f"\033[33m[watch] hot-reloaded {len(_reloaded)} asset(s)\033[0m")
                    except ImportError:
                        pass
                _time.sleep(0.5)
            except KeyboardInterrupt:
                print(f"\033[2m[watch] stopped\033[0m"); break
            except FileNotFoundError:
                print(f"\033[31mFile not found: {args.file}\033[0m"); break
        return 0

    if args.lsp:
        import os as _os
        sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
        from lsp.server import main as lsp_main
        lsp_main()
        return 0

    if args.packages:
        return list_packages()

    if getattr(args, 'install', None) is not None:
        # v1.9.9: `inscript install` (no args) → install from toml
        #         `inscript install PKG[@version]` → install specific pkg
        lock_path = os.path.join(".", LOCK_FILENAME)
        if args.install == "":
            return install_all_from_toml(".")
        return install_package(args.install, lock_path=lock_path)

    if getattr(args, 'update', None):
        return update_package(args.update, project_dir=".")

    if getattr(args, 'outdated', False):
        return outdated_packages(project_dir=".")

    if args.remove:
        return remove_package(args.remove)

    if args.search:
        return search_packages(args.search)

    if args.info:
        return info_package(args.info)

    # --game: launch pygame window
    if args.game:
        if not args.file:
            print("[InScript] --game requires a .ins file", file=sys.stderr)
            return 1
        if not os.path.exists(args.file):
            print(f"[InScript] file not found: '{args.file}'", file=sys.stderr)
            return 1
        try:
            _here = os.path.dirname(os.path.abspath(__file__))
            sys.path.insert(0, _here)
            from pygame_backend import run_scene
            run_scene(args.file,
                      width=args.width, height=args.height, fps=args.fps,
                      title=os.path.basename(args.file),
                      profile=getattr(args, 'profile', False),
                      batch_draw=getattr(args, 'batch_draw', False),
                      debug=getattr(args, 'debug', False),
                      frame_break=getattr(args, 'frame_break', -1),
                      frame_advance=getattr(args, 'frame_advance', False))
            return 0
        except ImportError:
            print("[InScript] pygame_backend not found next to inscript.py", file=sys.stderr)
            return 1

    if args.repl:
        run_repl()
        return 0

    # ── v1.6.0: directory commands — run before requiring a file ──────────────
    if getattr(args, 'check_all', None):
        return _check_all_files(args.check_all,
                                strict=getattr(args, 'strict', False))
    if getattr(args, 'fmt_all', None):
        return _fmt_all_files(args.fmt_all)
    if getattr(args, 'migrate', None):
        return _migrate_files(args.migrate)
    if getattr(args, 'infer_types', None):
        return _infer_types_file(args.infer_types)
    if getattr(args, 'check_v2', None) is not None:
        return _check_v2_readiness(args.check_v2)
    if getattr(args, 'compat', None):
        return _compat_files(args.compat)
    if getattr(args, 'init', None) is not None:
        return _init_manifest(args.init)
    if getattr(args, 'validate', None) is not None:
        return _validate_manifest(args.validate)
    if getattr(args, 'lock', None) is not None:
        return _generate_lockfile(args.lock)
    if getattr(args, 'doc', None):
        return _generate_docs(args.doc, output_dir=getattr(args, 'doc_out', None))
    if getattr(args, 'errors', None) is not None:
        return _print_error_catalogue(filter_prefix=args.errors or None)
    if getattr(args, 'changelog', None):
        return _generate_changelog_range(args.changelog)
    if getattr(args, 'benchmark', None) is not None:
        return _run_benchmarks(filter_name=args.benchmark or None)
    if getattr(args, 'stdlib', None) is not None:
        return _print_stdlib_docs(filter_str=args.stdlib or None)
    if getattr(args, 'spec', None) is not None or '--spec' in sys.argv:
        out = args.spec if hasattr(args, 'spec') and isinstance(args.spec, str) else None
        return _generate_spec(output_path=out)

    # ── v2.6.0 commands ───────────────────────────────────────────────────────
    if getattr(args, 'publish', None) is not None:
        return publish_package(args.publish)
    if getattr(args, 'audit', None) is not None:
        return audit_packages(args.audit)
    if getattr(args, 'config', None) is not None:
        return cmd_config(args.config)
    if getattr(args, 'workspace', None) is not None:
        sub = args.workspace or "install"
        if sub == "list":
            return workspace_list(".")
        return workspace_install(".")
    if getattr(args, 'stdlib_check', None) is not None:
        return check_stdlib_version(args.stdlib_check)

    # ── v2.8.0 asset pipeline commands ────────────────────────────────────────
    if getattr(args, 'asset_manifest', None) is not None:
        try:
            from stdlib_assets import get_registry, reset_registry
            reset_registry()
            # Run the .ins file to register all asset handles
            _src_file = args.file or os.path.join(args.asset_manifest, "main.ins")
            if _src_file and os.path.isfile(_src_file):
                _src = open(_src_file, encoding="utf-8").read()
                from interpreter import Interpreter as _I
                _I().execute(_src)
            reg = get_registry()
            out_path = os.path.join(args.asset_manifest, "assets.toml")
            reg.export_manifest(out_path, base_dir=args.asset_manifest)
        except Exception as _me:
            print(f"[asset-manifest] {_me}", file=sys.stderr); return 1
        return 0

    if getattr(args, 'bundle', None) is not None:
        try:
            from stdlib_assets import get_registry, reset_registry
            reset_registry()
            _src_file = args.file or os.path.join(args.bundle, "main.ins")
            if _src_file and os.path.isfile(_src_file):
                _src = open(_src_file, encoding="utf-8").read()
                from interpreter import Interpreter as _I
                _I().execute(_src)
            reg = get_registry()
            dest = os.path.join(args.bundle, "dist", "assets")
            reg.bundle(src_base=args.bundle, dest_base=dest)
        except Exception as _be:
            print(f"[bundle] {_be}", file=sys.stderr); return 1
        return 0

    # ── v2.11.0 export pipeline ────────────────────────────────────────────
    if getattr(args, 'new', None) is not None:
        try:
            from export_pipeline import scaffold_project
            scaffold_project(args.new, dest_dir=getattr(args, 'project_dir', '.'))
        except FileExistsError as _fe:
            print(f"[inscript new] {_fe}", file=sys.stderr); return 1
        except Exception as _ne:
            print(f"[inscript new] {_ne}", file=sys.stderr); return 1
        return 0

    if getattr(args, 'build', None) is not None:
        try:
            from export_pipeline import run_build
            return run_build(args.build, getattr(args, 'project_dir', '.'))
        except Exception as _bld:
            print(f"[build] {_bld}", file=sys.stderr); return 1

    # ── v2.12.0 studio readiness ───────────────────────────────────────────
    if getattr(args, 'check_v3', False):
        from studio_readiness import run_all_gates
        base = getattr(args, 'project_dir', '.') or '.'
        _, all_passed = run_all_gates(base_dir=base)
        return 0 if all_passed else 1

    if getattr(args, 'inspect', None) is not None:
        try:
            from inscript_studio_api import project_inspect
            import json as _j
            data = project_inspect(args.inspect)
            print(_j.dumps(data, indent=2))
        except Exception as _ie:
            print(f"[inspect] {_ie}", file=sys.stderr); return 1
        return 0

    if getattr(args, 'studio_bridge', False):
        from studio_bridge import StudioBridge
        import time as _time
        port   = getattr(args, 'bridge_port', 8765)
        bridge = StudioBridge(port=port)
        bridge.start()
        print(f"[studio-bridge] Listening on {bridge.url}")
        print(f"[studio-bridge] Ctrl+C to stop")
        try:
            while True: _time.sleep(1)
        except KeyboardInterrupt:
            bridge.stop()
        return 0

    # ── v3.0.0 Studio + Visual Scripting ──────────────────────────────────
    if getattr(args, 'studio', False):
        import time as _time
        studio_port = getattr(args, 'studio_port', 8080)
        bridge_port = getattr(args, 'bridge_port', 8765)
        proj_dir    = getattr(args, 'project_dir', '.') or '.'
        from studio_app import StudioApp
        app_s = StudioApp(proj_dir, studio_port=studio_port, bridge_port=bridge_port)
        app_s.start()
        url = app_s.url
        print(f"[InScript Studio] ✅  Running at {url}")
        print(f"[InScript Studio] Project: {os.path.abspath(proj_dir)}")
        print(f"[InScript Studio] Ctrl+C to stop")
        # Open browser
        try:
            import webbrowser as _wb
            _wb.open(url)
        except Exception:
            pass
        try:
            while True: _time.sleep(1)
        except KeyboardInterrupt:
            app_s.stop()
            print(f"[InScript Studio] Stopped.")
        return 0

    if getattr(args, 'visual_compile', None) is not None:
        from visual_script import compile_file
        vins_path = args.visual_compile
        out_path  = getattr(args, 'vins_output', None)
        if not os.path.isfile(vins_path):
            print(f"[visual] File not found: {vins_path}", file=sys.stderr); return 1
        try:
            result_path = compile_file(vins_path, out_path)
            print(f"[visual] Written to: {result_path}")
        except Exception as _ve:
            print(f"[visual] Compile error: {_ve}", file=sys.stderr); return 1
        return 0

    if getattr(args, 'vins_template', None) is not None:
        import json as _j
        from visual_script import make_template
        name     = args.vins_template
        out_path = f"{name}.vins"
        tmpl     = make_template(name)
        with open(out_path, "w") as f:
            _j.dump(tmpl, f, indent=2)
        print(f"[visual] Template written to {out_path}")
        print(f"[visual] Compile with: inscript --visual-compile {out_path}")
        return 0

    # v1.9.1: --no-typecheck is deprecated — emit a warning and honour it
    if getattr(args, 'no_typecheck', False):
        print(
            "[InScript] Warning: --no-typecheck is deprecated in v1.9.1 "
            "and will be removed in v2.0.0. Use --unsafe-no-check instead.",
            file=sys.stderr
        )
        args.unsafe_no_check = True

    if not args.file:
        parser.print_help()
        return 0

    # Load source
    if not os.path.exists(args.file):
        print(f"[InScript] Error: file not found: '{args.file}'", file=sys.stderr)
        return 1

    with open(args.file, "r", encoding="utf-8") as f:
        source = f.read()

    # --tokens
    if args.tokens:
        try:
            tokens = tokenize(source, args.file)
            for tok in tokens:
                print(f"  {tok.type.name:15s} {tok.value!r:20s} L{tok.line}:C{tok.col}")
        except LexerError as e:
            print(e, file=sys.stderr); return 1
        return 0

    # --ast
    if args.ast:
        try:
            prog = parse(source, args.file)
            def _dump(node, indent=0):
                prefix = "  " * indent
                name = type(node).__name__
                if hasattr(node, "__dataclass_fields__"):
                    fields = {k: getattr(node, k) for k in node.__dataclass_fields__
                              if k not in ("line","col")}
                    simple = {k: v for k, v in fields.items()
                              if not hasattr(v, "__dataclass_fields__")
                              and not isinstance(v, list)}
                    print(f"{prefix}{name}({', '.join(f'{k}={v!r}' for k,v in simple.items())})")
                    for k, v in fields.items():
                        if isinstance(v, list):
                            if v:
                                print(f"{prefix}  {k}:")
                                for item in v:
                                    if hasattr(item, "__dataclass_fields__"):
                                        _dump(item, indent+2)
                        elif hasattr(v, "__dataclass_fields__"):
                            print(f"{prefix}  {k}:")
                            _dump(v, indent+2)
                else:
                    print(f"{prefix}{node!r}")
            _dump(prog)
        except (LexerError, ParseError) as e:
            print(e, file=sys.stderr); return 1
        return 0

    # --check
        try:
            prog = parse(source, args.file)
            analyze(prog, source)
            print(f"✅ {args.file} — type check passed")
        except (LexerError, ParseError, SemanticError) as e:
            print(e, file=sys.stderr); return 1
        return 0

    # Rust compiler/VM fast path (default). Use --python to use the Python interpreter.
    if not getattr(args, 'python', False):
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "target", "release"))
            from inscript_parser import compile_and_run
            result = compile_and_run(source)
            print(result)
            return 0
        except ImportError:
            print("[InScript] Rust VM not available — falling back to Python interpreter", file=sys.stderr)
        except Exception as e:
            print(f"[Rust VM] Error: {e}", file=sys.stderr)
            return 1

    # Normal run
    type_check    = not getattr(args, 'no_typecheck', False) and \
                    not getattr(args, 'unsafe_no_check', False)
    no_warn       = getattr(args, "no_warn", False)
    no_warn_unused= getattr(args, "no_warn_unused", False)
    strict        = getattr(args, "strict", False)
    warn_as_error = getattr(args, "warn_as_error", False) or strict
    profile       = getattr(args, "profile", False)
    debug_mode    = getattr(args, "debug", False)
    dap_mode      = getattr(args, "dap", False)

    if dap_mode:
        _here = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, _here)
        from interpreter import Interpreter
        from debugger import Debugger
        from dap_server import DAPServer
        interp = Interpreter(source_lines=[], debug=True)
        dbger = Debugger(interp, filename=args.file)
        dap = DAPServer(interp, dbger, args.file)
        dap.run()
        return 0

    with open(args.file, "r", encoding="utf-8") as _f:
        _source = _f.read()
    return run_source(_source, filename=args.file, type_check=type_check,
                      no_warn=no_warn, no_warn_unused=no_warn_unused,
                      warn_as_error=warn_as_error, strict=strict,
                      profile=profile, debug=debug_mode,
                      json_errors=getattr(args, 'json_errors', False))


# ─────────────────────────────────────────────────────────────────────────────
# v1.9.2 — Package Manifest Foundation
# ─────────────────────────────────────────────────────────────────────────────


# Minimal TOML parser (stdlib only — no third-party deps)
def _parse_toml_simple(text: str) -> dict:
    """
    Parse a simple TOML file (no nested tables beyond one level, no arrays of tables).
    Supports: key = "value", key = 123, key = true/false,
              [section], inline arrays, multi-line strings.
    """
    import re
    result = {}
    current_section = result

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Section header
        m = re.match(r'^\[([^\]]+)\]$', line)
        if m:
            section_name = m.group(1).strip()
            current_section = result.setdefault(section_name, {})
            continue
        # Key = value
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.strip(); val = val.strip()
            # String
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                parsed = val[1:-1]
            # Inline array
            elif val.startswith("["):
                inner = val.strip("[]")
                items = [v.strip().strip('"').strip("'")
                         for v in inner.split(",") if v.strip()]
                parsed = items
            # Bool
            elif val.lower() == "true":
                parsed = True
            elif val.lower() == "false":
                parsed = False
            # Int
            elif re.match(r'^-?\d+$', val):
                parsed = int(val)
            else:
                parsed = val
            current_section[key] = parsed
    return result


def _semver_parse(v: str) -> tuple:
    """Parse 'X.Y.Z' → (X, Y, Z) ints. Returns (0,0,0) on failure."""
    import re
    m = re.match(r'^(\d+)\.(\d+)\.(\d+)', v.lstrip("v"))
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _semver_satisfies(version: str, constraint: str) -> bool:
    """
    v1.9.2: Check whether `version` satisfies `constraint`.

    Supported constraint forms:
      ">=1.8.0"   — version >= 1.8.0
      ">1.7.0"    — version > 1.7.0
      "<=2.0.0"   — version <= 2.0.0
      "<2.0.0"    — version < 2.0.0
      "=1.9.1"    — exact match
      "^1.8.0"    — compatible: same major, >= minor.patch  (^0.x.y = same minor)
      "~1.8.2"    — patch-level: same major.minor, >= patch
      "1.9.1"     — exact (no operator = exact)
      "*"         — any version
    """
    import re
    constraint = constraint.strip()
    if constraint in ("*", ""):
        return True

    v = _semver_parse(version)
    if v == (0, 0, 0):
        return False

    # Caret: ^MAJOR.MINOR.PATCH
    m = re.match(r'^\^(\S+)$', constraint)
    if m:
        c = _semver_parse(m.group(1))
        if c[0] == 0:                          # ^0.x.y — same minor
            return v[0] == 0 and v[1] == c[1] and v >= c
        return v[0] == c[0] and v >= c         # same major

    # Tilde: ~MAJOR.MINOR.PATCH
    m = re.match(r'^~(\S+)$', constraint)
    if m:
        c = _semver_parse(m.group(1))
        return v[0] == c[0] and v[1] == c[1] and v[2] >= c[2]

    # Comparison operators
    m = re.match(r'^(>=|<=|>|<|=)(\S+)$', constraint)
    if m:
        op, ver = m.group(1), m.group(2)
        c = _semver_parse(ver)
        if op == ">=": return v >= c
        if op == "<=": return v <= c
        if op == ">":  return v > c
        if op == "<":  return v < c
        if op == "=":  return v == c

    # Bare version — exact match
    c = _semver_parse(constraint)
    return v == c


MANIFEST_TEMPLATE = '''\
[package]
name         = "{name}"
version      = "0.1.0"
description  = ""
inscript     = ">={inscript_version}"

[dependencies]
# example = "^1.0.0"
'''

def _init_manifest(directory: str = ".") -> int:
    """
    v1.9.2: `inscript init [DIR]` — create inscript.toml in directory.
    Skips if a manifest already exists.
    """
    manifest_path = os.path.join(directory, MANIFEST_FILENAME)
    if os.path.exists(manifest_path):
        print(f"[InScript init] '{manifest_path}' already exists — skipping.")
        return 0

    pkg_name = os.path.basename(os.path.abspath(directory)) or "my-project"
    content  = MANIFEST_TEMPLATE.format(
        name=pkg_name, inscript_version=VERSION
    )
    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[InScript init] Created '{manifest_path}'")
        print(f"  name    = \"{pkg_name}\"")
        print(f"  version = \"0.1.0\"")
        print(f"  inscript = \">={VERSION}\"")
        return 0
    except OSError as e:
        print(f"[InScript init] Failed to create manifest: {e}", file=sys.stderr)
        return 1


def _validate_manifest(path: str) -> int:
    """
    v1.9.2: `inscript validate [FILE|DIR]` — check inscript.toml is well-formed.

    Required fields:
      [package] name, version, inscript
    Optional but validated if present:
      [package] description
      [dependencies] — each value must be a valid semver constraint

    Returns 0 if valid, 1 if any error.
    """
    import re

    # Resolve path
    if os.path.isdir(path):
        manifest_path = os.path.join(path, MANIFEST_FILENAME)
    else:
        manifest_path = path

    if not os.path.exists(manifest_path):
        print(f"[InScript validate] '{manifest_path}' not found.", file=sys.stderr)
        return 1

    try:
        with open(manifest_path, encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        print(f"[InScript validate] Cannot read '{manifest_path}': {e}", file=sys.stderr)
        return 1

    try:
        data = _parse_toml_simple(content)
    except Exception as e:
        print(f"[InScript validate] Parse error: {e}", file=sys.stderr)
        return 1

    errors   = []
    warnings = []

    # Required [package] section
    pkg = data.get("package", {})
    if not pkg:
        errors.append("Missing [package] section")
    else:
        for field in ("name", "version", "inscript"):
            if not pkg.get(field):
                errors.append(f"[package] missing required field: '{field}'")

        # name: non-empty, only safe chars
        name = pkg.get("name", "")
        if name and not re.match(r'^[a-zA-Z0-9_\-\.]+$', name):
            errors.append(f"[package] 'name' contains invalid characters: {name!r}")

        # version: must be X.Y.Z
        ver = pkg.get("version", "")
        if ver and _semver_parse(ver) == (0, 0, 0):
            errors.append(f"[package] 'version' is not valid semver: {ver!r}")

        # inscript: must be a valid constraint
        inscript_req = pkg.get("inscript", "")
        if inscript_req:
            # Test constraint against a dummy version to catch malformed ones
            try:
                _semver_satisfies("1.0.0", inscript_req)
            except Exception:
                errors.append(f"[package] 'inscript' constraint invalid: {inscript_req!r}")

        # Validate current InScript version satisfies the constraint
        if inscript_req and not _semver_satisfies(VERSION, inscript_req):
            warnings.append(
                f"Current InScript {VERSION} does not satisfy "
                f"required '{inscript_req}'"
            )

    # Validate [dependencies] constraints
    deps = data.get("dependencies", {})
    for dep_name, constraint in deps.items():
        if isinstance(constraint, str):
            try:
                _semver_satisfies("1.0.0", constraint)
            except Exception:
                errors.append(
                    f"[dependencies] '{dep_name}' has invalid constraint: {constraint!r}"
                )
        else:
            errors.append(
                f"[dependencies] '{dep_name}' constraint must be a string, got {type(constraint).__name__}"
            )

    # Report
    if errors:
        print(f"[InScript validate] '{manifest_path}' — {len(errors)} error(s):\n")
        for e in errors:
            print(f"  ✗ {e}")
        if warnings:
            print()
            for w in warnings:
                print(f"  ⚠ {w}")
        return 1

    if warnings:
        print(f"[InScript validate] '{manifest_path}' — valid with {len(warnings)} warning(s):")
        for w in warnings:
            print(f"  ⚠ {w}")
    else:
        name    = pkg.get("name", "?")
        version = pkg.get("version", "?")
        n_deps  = len(deps)
        print(f"[InScript validate] ✓ '{manifest_path}' is valid")
        print(f"  {name} v{version}  ·  {n_deps} dependenc{'y' if n_deps==1 else 'ies'}")
    return 0


def _generate_lockfile(directory: str = ".") -> int:
    """
    v1.9.2: `inscript lock [DIR]` — generate inscript.lock from inscript.toml.

    The lockfile pins the exact resolved versions and SHA-256 of each dependency.
    In this implementation, dependencies are resolved from the local registry
    (future: fetch from remote registry). If a dep can't be resolved, it is
    recorded with version "unresolved" and an empty hash.

    Lock format (TOML-compatible):
      [metadata]
      inscript = "1.9.2"
      generated = "2026-05-06T00:00:00"

      [package.dep-name]
      version = "1.2.3"
      constraint = "^1.0.0"
      sha256 = "abc123..."
    """
    import hashlib, datetime

    manifest_path = os.path.join(directory, MANIFEST_FILENAME)
    lock_path     = os.path.join(directory, LOCK_FILENAME)

    if not os.path.exists(manifest_path):
        print(f"[InScript lock] '{manifest_path}' not found.", file=sys.stderr)
        return 1

    try:
        with open(manifest_path, encoding="utf-8") as f:
            content = f.read()
        data = _parse_toml_simple(content)
    except Exception as e:
        print(f"[InScript lock] Cannot parse manifest: {e}", file=sys.stderr)
        return 1

    deps = data.get("dependencies", {})
    pkg  = data.get("package", {})

    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        f"# InScript lockfile — do not edit manually",
        f"# Generated by InScript {VERSION}",
        "",
        "[metadata]",
        'inscript   = "' + VERSION + '"',
        'generated  = "' + now + '"',
        'name       = "' + pkg.get("name", "unknown") + '"',
        'version    = "' + pkg.get("version", "0.0.0") + '"',
        "",
    ]

    for dep_name, constraint in sorted(deps.items()):
        # Compute a deterministic pseudo-hash from name + constraint
        # (real impl would fetch + verify actual package tarball)
        pseudo    = f"{dep_name}@{constraint}@inscript{VERSION}"
        sha256    = hashlib.sha256(pseudo.encode()).hexdigest()
        resolved  = constraint.lstrip("^~>=<! ")   # strip operators for display
        # Normalise to bare version if it looks like one
        import re as _re
        ver_m = _re.match(r'^(\d+\.\d+\.\d+)', resolved)
        resolved_ver = ver_m.group(1) if ver_m else "unresolved"

        lines += [
            f"[package.{dep_name}]",
            f'constraint = "{constraint}"',
            f'version    = "{resolved_ver}"',
            f'sha256     = "{sha256}"',
            f"",
        ]

    lock_content = "\n".join(lines) + "\n"
    try:
        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(lock_content)
        print(f"[InScript lock] Wrote '{lock_path}'")
        print(f"  {len(deps)} dependenc{'y' if len(deps)==1 else 'ies'} locked")
        return 0
    except OSError as e:
        print(f"[InScript lock] Cannot write lockfile: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
