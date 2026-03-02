/**
 * Inscript VS Code Extension
 * Provides syntax highlighting, running, and debugging support for Inscript files
 */

const vscode = require('vscode');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

let outputChannel;
let extensionPath;

/**
 * Activate the extension
 */
function activate(context) {
    extensionPath = context.extensionPath;
    outputChannel = vscode.window.createOutputChannel('Inscript');
    
    console.log('Inscript extension activated');

    // Command: Run current file
    let runCommand = vscode.commands.registerCommand('inscript.run', () => {
        runInscriptFile(false);
    });

    // Command: Run in terminal
    let runTerminalCommand = vscode.commands.registerCommand('inscript.runInTerminal', () => {
        runInscriptFile(true);
    });

    // Command: Open REPL
    let replCommand = vscode.commands.registerCommand('inscript.repl', () => {
        openREPL();
    });

    context.subscriptions.push(runCommand);
    context.subscriptions.push(runTerminalCommand);
    context.subscriptions.push(replCommand);
    context.subscriptions.push(outputChannel);

    // Save files before running (optional)
    vscode.workspace.onDidSaveTextDocument((document) => {
        if (document.languageId === 'inscript') {
            console.log('Inscript file saved:', document.fileName);
        }
    });
}

/**
 * Run the current Inscript file
 */
function runInscriptFile(useTerminal) {
    const editor = vscode.window.activeTextEditor;
    
    if (!editor) {
        vscode.window.showErrorMessage('No file is currently open');
        return;
    }

    const document = editor.document;
    
    if (document.languageId !== 'inscript') {
        vscode.window.showErrorMessage('Current file is not an Inscript file (.is)');
        return;
    }

    // Save the document if it has unsaved changes
    if (document.isDirty) {
        document.save();
    }

    const filePath = document.fileName;
    const fileName = path.basename(filePath);

    if (useTerminal) {
        runInTerminal(filePath, fileName);
    } else {
        runInOutputPanel(filePath, fileName);
    }
}

/**
 * Run Inscript file in the integrated terminal
 */
function runInTerminal(filePath, fileName) {
    let terminal = vscode.window.terminals.find(t => t.name === 'Inscript');
    
    if (!terminal) {
        terminal = vscode.window.createTerminal('Inscript');
    }

    terminal.show();
    
    const config = vscode.workspace.getConfiguration('inscript');
    const pythonPath = config.get('pythonPath', 'python');
    const inscriptPath = findInscriptPath();
    
    if (!inscriptPath) {
        vscode.window.showErrorMessage(
            'Inscript interpreter not found. Make sure to install it: pip install inscript'
        );
        return;
    }

    terminal.sendText(`${pythonPath} "${inscriptPath}" "${filePath}"`, true);
}

/**
 * Run Inscript file and show output in output panel
 */
function runInOutputPanel(filePath, fileName) {
    const config = vscode.workspace.getConfiguration('inscript');
    const pythonPath = config.get('pythonPath', 'python');
    const inscriptPath = findInscriptPath();
    
    if (!inscriptPath) {
        vscode.window.showErrorMessage(
            'Inscript interpreter not found. Make sure to install it: pip install inscript'
        );
        return;
    }

    outputChannel.clear();
    outputChannel.appendLine(`Running: ${fileName}`);
    outputChannel.appendLine(`Path: ${filePath}`);
    outputChannel.appendLine('─'.repeat(80));
    
    if (config.get('showOutputOnRun', true)) {
        outputChannel.show();
    }

    const child = spawn(pythonPath, [inscriptPath, filePath], {
        cwd: path.dirname(filePath),
        stdio: ['pipe', 'pipe', 'pipe']
    });

    let output = '';
    let errorOutput = '';

    child.stdout.on('data', (data) => {
        output += data.toString();
        outputChannel.append(data.toString());
    });

    child.stderr.on('data', (data) => {
        errorOutput += data.toString();
        outputChannel.append(data.toString());
    });

    child.on('close', (code) => {
        outputChannel.appendLine('─'.repeat(80));
        
        if (code === 0) {
            outputChannel.appendLine('✓ Execution completed successfully');
        } else {
            outputChannel.appendLine(`✗ Execution failed with code ${code}`);
        }
    });

    child.on('error', (error) => {
        outputChannel.appendLine(`Error executing file: ${error.message}`);
        vscode.window.showErrorMessage(`Failed to run Inscript file: ${error.message}`);
    });
}

/**
 * Open the Inscript REPL in a new terminal
 */
function openREPL() {
    const config = vscode.workspace.getConfiguration('inscript');
    const pythonPath = config.get('pythonPath', 'python');
    const inscriptPath = findInscriptPath();
    
    if (!inscriptPath) {
        vscode.window.showErrorMessage(
            'Inscript interpreter not found. Make sure to install it: pip install inscript'
        );
        return;
    }

    const terminal = vscode.window.createTerminal('Inscript REPL');
    terminal.show();
    terminal.sendText(`${pythonPath} "${inscriptPath}" --repl`, true);
}

/**
 * Find the Inscript interpreter path
 * First tries to use pip-installed version, then falls back to workspace version
 */
function findInscriptPath() {
    // Try to find inscript in the workspace
    const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath;
    
    if (workspacePath) {
        const localInscript = path.join(workspacePath, 'inscript.py');
        if (fs.existsSync(localInscript)) {
            return localInscript;
        }
    }

    // Try to find in extension directory
    const extensionInscript = path.join(extensionPath, '..', '..', 'inscript.py');
    if (fs.existsSync(extensionInscript)) {
        return extensionInscript;
    }

    // Return 'inscript' command (assumes pip installation)
    return 'inscript';
}

/**
 * Deactivate the extension
 */
function deactivate() {
    console.log('Inscript extension deactivated');
}

module.exports = {
    activate,
    deactivate
};
