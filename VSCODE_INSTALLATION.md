# Installing Inscript VS Code Extension

## The VSIX File

Your extension is packaged and ready to install:
```
📦 c:\Users\Shreyasi Sarkar\Desktop\inscript\vscode-extension\inscript-0.2.0.vsix
```

## Installation Method 1: Command Line (Easiest)

Run this command in PowerShell:

```powershell
code --install-extension "c:\Users\Shreyasi Sarkar\Desktop\inscript\vscode-extension\inscript-0.2.0.vsix"
```

Then **restart VS Code**.

## Installation Method 2: VS Code UI

1. **Open VS Code**
2. Go to **Extensions** (Ctrl+Shift+X)
3. Click the three dots menu (⋯)
4. Select **Install from VSIX**
5. Navigate to: `c:\Users\Shreyasi Sarkar\Desktop\inscript\vscode-extension\inscript-0.2.0.vsix`
6. Click Open
7. Click Install
8. **Reload VS Code**

## After Installation

### Create and Run a Script

1. **Create a file** `hello.is`:
   ```inscript
   print("Hello from VS Code!")
   ```

2. **Save it** with `.is` extension

3. **Run it** with one of these methods:
   - Press `Ctrl+Alt+I` (keyboard shortcut)
   - Right-click file → "Inscript: Run Current File"
   - Click the ▶️ play button (if visible)

4. **Output appears** in the Output panel

### Other Features

**Run in Terminal** (shows more details):
- Press `Ctrl+Alt+T`
- Or right-click → "Inscript: Run in Terminal"

**Open REPL** (Interactive Mode):
- Command Palette (`Ctrl+Shift+P`)
- Search: "Inscript: Open REPL"
- Type commands and see results instantly

**Toggle Comments**:
- Press `Ctrl+/` to comment/uncomment lines

## File Association

Files with `.is` extension are automatically recognized as Inscript:
- ✨ Get syntax highlighting (colors)
- 🎨 Code folding (collapse/expand blocks)
- 🧩 Bracket matching
- 💡 IntelliSense hints

## Configuration (Optional)

Open VS Code Settings (`Ctrl+,`) and search "inscript":

```json
{
  "inscript.pythonPath": "python",      // Path to Python
  "inscript.showOutputOnRun": true,     // Auto-show output
  "inscript.terminalMode": false        // true = run in terminal, false = output panel
}
```

## Troubleshooting

### Extension not showing output
- Check "inscript.showOutputOnRun" setting is true
- Check Output panel is visible (View → Output)

### "Inscript interpreter not found"
- Verify inscript is installed: `python -m inscript.cli --version`
- Check "inscript.pythonPath" setting points to your Python

### Syntax highlighting not working
- Make sure file has `.is` extension
- Check status bar shows "Inscript" language
- Reload window: `Ctrl+Shift+P` → "Developer: Reload Window"

### Commands don't work
- Make sure Inscript is installed: `python -m pip install inscript`
- Or use the batch file: `.\inscript.bat example.is`

## Example Commands

Once installed, these all work from any `.is` file:

```powershell
# Run current file
Ctrl+Alt+I

# Run in terminal
Ctrl+Alt+T

# Toggle comment
Ctrl+/

# Open command palette
Ctrl+Shift+P
```

## Manual Uninstall

If you want to remove the extension:

1. Go to Extensions (`Ctrl+Shift+X`)
2. Search "inscript"
3. Click the gear icon → Uninstall

The VSIX file will remain in the folder if you want to reinstall it later.

---

**You're all set!** 🎉 Start creating `.is` files and run them with `Ctrl+Alt+I`
