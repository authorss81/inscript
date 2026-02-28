# Building and Publishing the Inscript VS Code Extension

This guide covers developing, testing, and publishing the Inscript VS Code extension.

## Prerequisites

- Node.js 14+ ([Download](https://nodejs.org/))
- npm (comes with Node.js)
- VS Code 1.70+
- Inscript installed (`pip install inscript`)
- Git

## Quick Start

### Setup Development Environment

```bash
# Navigate to extension directory
cd vscode-extension

# Install dependencies
npm install

# Launch extension in development mode
npm run esbuild-watch
```

Then press `F5` in VS Code to start debugging.

## Development Workflow

### 1. Make Changes

Edit the following files as needed:
- `extension.js` - Main extension logic
- `syntaxes/inscript.json` - Syntax highlighting rules
- `package.json` - Extension configuration and commands
- `language-configuration.json` - Language rules

### 2. Test Changes

In the debug VS Code window (opened by F5):
1. Open a `.is` file
2. Make your changes
3. Reload the extension with `Ctrl+R`
4. Test your changes

### 3. Check for Errors

You can check the extension console in VS Code:
- Help → Toggle Developer Tools
- Check the Console tab for errors

## Building for Distribution

### Prerequisites

```bash
npm install -g vsce      # VS Code Extension CLI
npm install -g esbuild   # Bundler (optional, for optimized builds)
```

### Build Steps

1. **Update version in package.json**
   ```json
   {
     "version": "0.2.1"  // Update this
   }
   ```

2. **Build the extension**
   ```bash
   npm run vscode:prepublish   # Creates minified version
   ```

3. **Create VSIX package** (installable file)
   ```bash
   vsce package
   # Creates: inscript-0.2.1.vsix
   ```

4. **Test locally before publishing**
   ```bash
   code --install-extension inscript-0.2.1.vsix
   ```

## Publishing to VS Code Marketplace

### Setup Publisher Account

1. Go to https://marketplace.visualstudio.com
2. Sign in with GitHub or Microsoft account
3. Create a new publisher account
4. Note your **publisher name** (will use it below)

### Update package.json

```json
{
  "name": "inscript",
  "displayName": "Inscript Language Support",
  "publisher": "your-publisher-name",  // Change this
  "version": "0.2.1"
}
```

### Create Personal Access Token (PAT)

1. Go to https://dev.azure.com/
2. Go to Personal Access Tokens
3. Create new token with:
   - Scopes: `Marketplace (manage)`
   - Validity: 90 days or longer
4. Copy the token

### Publish

```bash
# First time setup
vsce login your-publisher-name
# Paste your PAT when prompted

# Publish
vsce publish

# Or publish with version update
vsce publish minor  # increments 0.2.0 → 0.2.1
vsce publish major  # increments 0.2.0 → 1.0.0
```

## Extension Features

### Commands

Registered commands (in `package.json` contributes):

- `inscript.run` - Run current file (`Ctrl+Alt+I`)
- `inscript.runInTerminal` - Run in terminal (`Ctrl+Alt+T`)
- `inscript.repl` - Open REPL

### Language Support

- **File Extension**: `.is`
- **Language ID**: `inscript`
- **Syntax Highlighting**: TextMate grammar in `syntaxes/inscript.json`
- **Language Configuration**: `language-configuration.json`

### Settings

Users can configure:
- `inscript.pythonPath` - Path to Python executable
- `inscript.showOutputOnRun` - Auto-show output panel
- `inscript.terminalMode` - Run in terminal instead of output

## Customizing Syntax Highlighting

Edit `syntaxes/inscript.json` to modify colors and scopes:

```json
{
  "name": "keyword.control.inscript",
  "match": "\\b(if|while|for)\\b"
}
```

### TextMate Scope Names

Common scopes for styling:
- `keyword.control` - Control keywords
- `keyword.operator` - Operators
- `string.quoted.double` - Strings
- `comment.line` - Comments
- `constant.numeric` - Numbers
- `support.function.builtin` - Built-in functions
- `entity.name.function` - User functions

## Debugging

### View Extension Console

1. In the extension's VS Code window, press `Ctrl+Shift+P`
2. Search for "Developer: Toggle Developer Tools"
3. Go to Console tab
4. Errors appear here

### Debug with Breakpoints

1. In `extension.js`, click line number to set breakpoint
2. Press F5 to start debugging
3. Breakpoints will pause execution
4. Step through code with F10/F11

### Log Output

Use console.log in extension.js:

```javascript
console.log('Debug message:', value);
// View in Developer Tools Console
```

## Extension Lifecycle

### Activation Events

The extension activates when:
- A `.is` file is opened (`onLanguage:inscript`)
- Commands are triggered (`inscript.run`, `inscript.runInTerminal`, etc.)

### Deactivation

The extension deactivates when:
- VS Code closes
- Extensions are disabled

## Troubleshooting

### Extension won't load

1. Check VS Code version (need 1.70+)
2. Check Node.js version (`node --version`, need 14+)
3. Look at console for errors
4. Try reinstalling dependencies: `npm install`

### Syntax highlighting not working

1. Verify file extension is `.is`
2. Check console for grammar errors
3. Language ID should be `inscript` in status bar
4. Reload window: `Ctrl+Shift+P` → "Developer: Reload Window"

### Commands not appearing

1. Check `package.json` command definitions
2. Verify command IDs match in `extension.js`
3. Check activation events in `package.json`

### Python/Inscript not found

1. Check `inscript.pythonPath` setting
2. Verify inscript is installed: `pip list | grep inscript`
3. Test inscript works: `inscript --version`
4. Update setting to full Python path if needed

## Version Updates

### Semantic Versioning

- `0.2.1` → `0.2.2` (patch): Bug fixes
- `0.2.0` → `0.3.0` (minor): New features
- `0.2.0` → `1.0.0` (major): Breaking changes

### Update Checklist

- [ ] Update version in `package.json`
- [ ] Update version in extension changelog (if applicable)
- [ ] Test all features locally
- [ ] Build: `npm run vscode:prepublish`
- [ ] Package: `vsce package`
- [ ] Test VSIX locally: `code --install-extension inscript-X.Y.Z.vsix`
- [ ] Publish: `vsce publish`

## Resources

- [VS Code Extension API](https://code.visualstudio.com/api)
- [TextMate Grammar](https://macromates.com/manual/en/language_grammars)
- [VS Code Extension Best Practices](https://code.visualstudio.com/api/extension-guides/overview)
- [vsce Documentation](https://github.com/microsoft/vscode-vsce)

## Support

- **Issues**: Report on GitHub https://github.com/YourUsername/inscript/issues
- **Feature Requests**: GitHub Issues with `[extension]` label
- **Questions**: Start a GitHub Discussion

---

Happy developing! 🎉
