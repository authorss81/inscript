# Inscript VS Code Extension

Beautiful, clean syntax highlighting and execution support for the **Inscript** programming language - a Python-like interpreted language with English-style keywords.

## Features

✨ **Syntax Highlighting** - Full syntax coloring for `.is` files with support for:
- Keywords (if, while, function, etc.)
- Strings, numbers, and comments
- Functions, variables, and operators
- Built-in function names

🚀 **Run Inscript Files** - Execute scripts directly from VS Code:
- Press `Ctrl+Alt+I` to run the current file
- Or right-click and select "Inscript: Run Current File"
- Output appears in the Output panel

🔧 **Terminal Integration** - Run files in integrated terminal:
- Press `Ctrl+Alt+T` to run in terminal
- Full interactive output with proper formatting
- Kill and restart execution anytime

💻 **Interactive REPL** - Launch Inscript interactive mode:
- Command: "Inscript: Open REPL"
- Full interactive programming environment
- Type scripts line by line

🎨 **Language Support** - Automatic detection of `.is` files:
- Proper bracket matching and auto-closing
- Comment toggling with `Ctrl+/`
- Code folding for functions and blocks

## Installation

### Option 1: Install from VS Code Marketplace (Coming Soon)
1. Search for "Inscript" in VS Code Extensions
2. Click Install

### Option 2: Manual Installation from File
1. Download the extension package
2. In VS Code: `Extensions` → `⋯` → `Install from VSIX`
3. Select the `.vsix` file

### Option 3: Install from Source
1. Clone this repository
2. Run `npm install` in the `vscode-extension` folder
3. Press `F5` to open a new VS Code window with the extension loaded

## Setup

### Prerequisites
- Python 3.8 or higher
- Inscript language installed via pip:
```bash
pip install inscript
```

Or use the local workspace version if you have the source code.

### Configuration

Open VS Code Settings and search for "Inscript" to customize:

- **Python Path** (`inscript.pythonPath`) - Path to Python executable
  - Default: `python`
  - Example: `C:\Python311\python.exe`

- **Show Output on Run** (`inscript.showOutputOnRun`) - Auto-show output panel
  - Default: `true`

- **Terminal Mode** (`inscript.terminalMode`) - Run in terminal instead of output panel
  - Default: `false`

## Usage

### Running Scripts

1. **Open an `.is` file** in VS Code
2. **Choose one of the following:**

   - Press `Ctrl+Alt+I` - Run immediately
   - Press `Ctrl+Alt+T` - Run in terminal
   - Right-click → "Inscript: Run Current File"
   - Click the ▶️ icon in the editor toolbar

3. **View output** in the Output panel (or Terminal if enabled)

### Example Script

Create a file `hello.is`:
```inscript
print("Hello from Inscript!")

numbers = [1, 2, 3, 4, 5]
for num in numbers
  print(num)
end
```

Then press `Ctrl+Alt+I` to run it!

### Opening the REPL

- Command Palette: `Ctrl+Shift+P` → "Inscript: Open REPL"
- Opens an interactive terminal for live coding

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Alt+I` | Run current file |
| `Ctrl+Alt+T` | Run in terminal |
| `Ctrl+/` | Toggle comment |

## Troubleshooting

### "Inscript interpreter not found"
Ensure Inscript is installed:
```bash
pip install inscript
```

Or if using workspace version, check `inscript.pythonPath` setting points to correct Python.

### Syntax highlighting not working
1. Make sure file extension is `.is`
2. Verify file is recognized as Inscript language (bottom-right of VS Code)
3. Reload VS Code window (`Ctrl+R`)

### Scripts won't run
1. Check Python path in settings
2. Verify script has no syntax errors
3. Check output panel for error messages
4. Try running from terminal with `Ctrl+Alt+T` for more details

## Requirements

- VS Code 1.70.0+
- Python 3.8+
- Inscript 0.2.0+ (via pip or workspace)

## Extension Commands

| Command | Binding |
|---------|---------|
| Inscript: Run Current File | `Ctrl+Alt+I` |
| Inscript: Run in Terminal | `Ctrl+Alt+T` |
| Inscript: Open REPL | Command Palette |

## Development

To develop this extension:

1. Clone the repository
2. Navigate to `vscode-extension` folder
3. Run `npm install`
4. Press `F5` to start debugging
5. Make changes and test in the new window
6. Reload (`Ctrl+R`) to see changes

### Building for Distribution

```bash
# Requires vsce installed globally
npm install -g vsce

# Build the .vsix package
vsce package

# Publish to marketplace (requires publisher account)
vsce publish
```

## License

MIT License - See LICENSE file in the main Inscript repository

## Links

- **Main Repository**: https://github.com/YourUsername/inscript
- **Language Documentation**: https://github.com/YourUsername/inscript/tree/main/docs
- **Report Issues**: https://github.com/YourUsername/inscript/issues

## Support

For issues or feature requests:
1. Check existing issues on GitHub
2. Create a new issue with details
3. Include your OS, VS Code version, and extension version

---

**Happy Inscripting!** 🎉

Made with ❤️ for the Inscript Community
