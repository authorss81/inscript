// InScript VS Code Extension — v2.1.0
// Launches the InScript LSP server and connects the language client.

const vscode = require('vscode');
const { LanguageClient, TransportKind } = require('vscode-languageclient/node');
const { spawn } = require('child_process');
const path = require('path');
const fs   = require('fs');

let client;

/**
 * Find the inscript LSP server entry point.
 * Checks (in order):
 *   1. inscript.serverPath config
 *   2. pip-installed location (python3 -c "import inscript_package; print(inscript_package.__file__)")
 *   3. Workspace root
 */
async function findServerPath(pythonPath) {
    const config = vscode.workspace.getConfiguration('inscript');
    const manual = config.get('serverPath', '').trim();
    if (manual && fs.existsSync(path.join(manual, 'lsp', 'server.py'))) {
        return path.join(manual, 'lsp', 'server.py');
    }

    // Try pip-installed location
    return new Promise((resolve) => {
        const proc = spawn(pythonPath, [
            '-c',
            'import inscript_package, os; print(os.path.dirname(inscript_package.__file__))'
        ]);
        let out = '';
        proc.stdout.on('data', d => out += d.toString());
        proc.on('close', code => {
            if (code === 0) {
                const p = path.join(out.trim(), 'lsp', 'server.py');
                resolve(fs.existsSync(p) ? p : null);
            } else {
                resolve(null);
            }
        });
    });
}

async function activate(context) {
    const config     = vscode.workspace.getConfiguration('inscript');
    const pythonPath = config.get('pythonPath', 'python3');

    const serverScript = await findServerPath(pythonPath);
    if (!serverScript) {
        vscode.window.showErrorMessage(
            'InScript LSP: server not found. Install with: pip install inscript-lang  ' +
            'or set inscript.serverPath in settings.'
        );
        return;
    }

    const serverOptions = {
        command: pythonPath,
        args: [serverScript],
        transport: TransportKind.stdio,
    };

    const clientOptions = {
        documentSelector: [{ scheme: 'file', language: 'inscript' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.ins'),
        },
        outputChannelName: 'InScript LSP',
    };

    client = new LanguageClient(
        'inscript-lsp',
        'InScript Language Server',
        serverOptions,
        clientOptions
    );

    client.start();
    context.subscriptions.push(client);

    console.log('InScript LSP client started, server:', serverScript);
}

async function deactivate() {
    if (client) {
        await client.stop();
    }
}

module.exports = { activate, deactivate };
