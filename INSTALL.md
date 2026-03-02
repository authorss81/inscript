# Installing Inscript

This guide covers all installation methods for the Inscript programming language.

## Option 1: pip (Recommended)

### Install from PyPI

```bash
pip install inscript
```

### Install from Source

```bash
git clone https://github.com/YourUsername/inscript.git
cd inscript
pip install -e .
```

### Verify Installation

```bash
# Check version
inscript --version

# Run a script
inscript examples/hello.is

# Start interactive REPL
inscript --repl
```

### Make `inscript` Command Available Globally

After `pip install inscript`, the command `inscript` may not be in your PATH on Windows.

#### Windows - Add Python Scripts to PATH

1. **Find your Python Scripts folder:**
   ```powershell
   python -c "import site; print(site.USER_SITE)"
   # Usually: C:\Users\YourName\AppData\Local\Python\Python311\Scripts
   ```

2. **Add to PATH:**
   - Press `Win + X`, select "System"
   - Click "Advanced system settings"
   - Click "Environment Variables"
   - Under "User variables", click "New"
   - Variable name: `Path`
   - Variable value: `C:\Users\YourName\AppData\Local\Python\Python311\Scripts`
   - Click OK twice
   - **Restart your terminal**

3. **Verify:**
   ```powershell
   inscript --version  # Should work now
   ```

#### macOS/Linux - Automatic

On macOS and Linux, `pip install` automatically adds scripts to your PATH.

```bash
inscript --version  # Should work immediately
```

If not, add `~/.local/bin` to your PATH:
```bash
export PATH="$PATH:$HOME/.local/bin"
```

## Option 2: VS Code Extension

The Inscript VS Code extension provides integrated support for developing Inscript programs.

### Install from VS Code Marketplace

1. Open VS Code
2. Go to Extensions (`Ctrl+Shift+X`)
3. Search for "Inscript"
4. Click "Install"

### Features

- 🎨 Syntax highlighting for `.is` files
- 🚀 Run scripts with `Ctrl+Alt+I`
- 🔧 Execute in terminal with `Ctrl+Alt+T`
- 💻 REPL integration
- ✨ Code folding and bracket matching

### Configuration

Open VS Code Settings and search for "inscript":

```json
{
  "inscript.pythonPath": "python",        // Path to Python executable
  "inscript.showOutputOnRun": true,       // Auto-show output panel
  "inscript.terminalMode": false          // Run in terminal (not output panel)
}
```

## Option 3: Run from Source

If you don't want to install globally, you can run scripts directly:

```bash
python inscript.py examples/hello.is
python inscript.py --repl
```

## Platform-Specific Notes

### Windows

- **Issue**: `inscript` command not found after pip install?
  - Solution: Add Python Scripts folder to PATH (see Windows section above)
  
- **Alternative**: Create a batch file wrapper
  ```batch
  @echo off
  python "%~dp0inscript.py" %*
  ```
  Save as `inscript.bat` in a folder that's in PATH

### macOS

- **M1/M2/M3 Macs**: Ensure Python 3.8+ is installed via Homebrew or python.org
  ```bash
  brew install python@3.12
  /usr/local/bin/python3.12 -m pip install inscript
  ```

### Linux

- **Ubuntu/Debian**:
  ```bash
  sudo apt-get install python3-pip
  pip3 install inscript
  inscript --version
  ```

- **Fedora/RHEL**:
  ```bash
  sudo dnf install python3-pip
  pip3 install inscript
  inscript --version
  ```

- **Arch**:
  ```bash
  sudo pacman -S python-pip
  pip install inscript
  inscript --version
  ```

## Troubleshooting

### Problem: `inscript` command not found

**Solution 1: Use python module directly**
```bash
python -m inscript.cli examples/hello.is
python -m inscript.cli --repl
```

**Solution 2: Add Scripts folder to PATH**
See the "Make `inscript` Command Available Globally" section above.

**Solution 3: Use full path**
```powershell
# Windows example
C:\Users\YourName\AppData\Local\Python\Python311\Scripts\inscript.exe examples/hello.is
```

### Problem: `pip install inscript` fails

**Check Python version:**
```bash
python --version
# Should be 3.8 or higher
```

**Upgrade pip:**
```bash
python -m pip install --upgrade pip
python -m pip install --upgrade setuptools wheel
```

**Try again:**
```bash
pip install inscript
```

### Problem: VS Code extension not finding inscript

**Configure custom Python path:**
1. Open VS Code Settings (`Ctrl+,`)
2. Search for "inscript.pythonPath"
3. Enter the full path to your Python executable
   - Example: `C:\Users\YourName\AppData\Local\Python\Python311\python.exe`

## Verification

After installing, verify everything works:

```bash
# Show version
inscript --version

# Run example
inscript examples/hello.is
# Expected output: Hello, World!

# Interactive mode
inscript
# Try: print("Hello from REPL!")
# Then: exit

# List available commands
inscript --help
```

## Uninstall

To remove Inscript:

```bash
pip uninstall inscript
```

This will:
- Remove the inscript package
- Delete the `inscript` command
- Remove all Inscript files

## Getting Help

- **Documentation**: See `docs/STDLIB.md` for built-in functions
- **Examples**: Check `examples/` directory for sample programs
- **Issues**: Report bugs on GitHub (https://github.com/YourUsername/inscript/issues)
- **Community**: Discuss on GitHub Discussions

## Next Steps

After installation:

1. **Read the Language Spec**: `docs/LANGUAGE_SPEC.md`
2. **Try Examples**: `inscript examples/hello.is`
3. **Explore Built-ins**: `docs/STDLIB.md`
4. **Create Your First Program**: Follow the Language Spec for syntax

Happy Inscripting! 🎉
