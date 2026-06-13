#!/usr/bin/env python3
"""Sync all non-Python version references to match inscript.py:VERSION.

Run after bumping VERSION in inscript.py:
    python tools/sync_versions.py

This updates:
    - Cargo.toml (rust_parser, rust_vm_engine)
    - inscript.toml
    - studio_electron/package.json
    - README.md badges and footer
"""
import os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG  = os.path.join(REPO, "inscript_package")

def read_version():
    vfile = os.path.join(PKG, "inscript.py")
    with open(vfile, encoding="utf-8") as f:
        m = re.search(r'^VERSION\s*=\s*"([^"]+)"', f.read(), re.M)
    if not m:
        print("ERROR: VERSION not found in inscript.py"); sys.exit(1)
    return m.group(1)

def sync_file(path, pattern, replace_with=lambda m, v: m.string[:m.start()] + v + m.string[m.end():]):
    """Read file, replace version, write back."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    ver = read_version()
    new_content = pattern.sub(lambda m: replace_with(m, ver), content)
    if new_content != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  ✓ {os.path.relpath(path, REPO)}")
        return True
    print(f"  - {os.path.relpath(path, REPO)}  (already up to date)")
    return False

def main():
    ver = read_version()
    print(f"Syncing all files to v{ver}\n")

    sync_file(
        os.path.join(PKG, "inscript_rust_parser", "Cargo.toml"),
        re.compile(r'^version = "[\d.]+"', re.M),
        lambda m, v: f'version = "{v}"',
    )
    sync_file(
        os.path.join(PKG, "rust_vm_engine", "Cargo.toml"),
        re.compile(r'^version = "[\d.]+"', re.M),
        lambda m, v: f'version = "{v}"',
    )
    sync_file(
        os.path.join(PKG, "inscript.toml"),
        re.compile(r'^version = "[\d.]+"', re.M),
        lambda m, v: f'version = "{v}"',
    )
    sync_file(
        os.path.join(PKG, "studio_electron", "package.json"),
        re.compile(r'"version": "[\d.]+"'),
        lambda m, v: f'"version": "{v}"',
    )
    # README badges and footer
    sync_file(
        os.path.join(REPO, "README.md"),
        re.compile(r'version-[\d.]+\w*'),
        lambda m, v: f'version-{v}',
    )

    print(f"\nDone. All files synced to v{ver}.")

if __name__ == "__main__":
    main()
