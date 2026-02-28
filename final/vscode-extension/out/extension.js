"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const child_process_1 = require("child_process");
const path = require("path");
let outputChannel;
function activate(context) {
    outputChannel = vscode.window.createOutputChannel('InScript');
    // ── Run File ─────────────────────────────────────────────────────────────
    context.subscriptions.push(vscode.commands.registerCommand('inscript.run', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
        const file = editor.document.fileName;
        if (!file.endsWith('.ins')) {
            vscode.window.showWarningMessage('Open an .ins file to run it.');
            return;
        }
        editor.document.save().then(() => runFile(file));
    }));
    // ── Type Check ────────────────────────────────────────────────────────────
    context.subscriptions.push(vscode.commands.registerCommand('inscript.check', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
        const file = editor.document.fileName;
        editor.document.save().then(() => checkFile(file));
    }));
    // ── Build for Web ─────────────────────────────────────────────────────────
    context.subscriptions.push(vscode.commands.registerCommand('inscript.buildWeb', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
        const file = editor.document.fileName;
        const outDir = path.join(path.dirname(file), 'dist');
        editor.document.save().then(() => buildWeb(file, outDir));
    }));
    // ── Show AST ──────────────────────────────────────────────────────────────
    context.subscriptions.push(vscode.commands.registerCommand('inscript.showAST', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
        const file = editor.document.fileName;
        editor.document.save().then(() => showAST(file));
    }));
    // ── Diagnostics on save ───────────────────────────────────────────────────
    const diagCollection = vscode.languages.createDiagnosticCollection('inscript');
    context.subscriptions.push(diagCollection);
    vscode.workspace.onDidSaveTextDocument(doc => {
        if (doc.languageId === 'inscript') {
            runDiagnostics(doc, diagCollection);
        }
    });
    vscode.workspace.onDidCloseTextDocument(doc => {
        diagCollection.delete(doc.uri);
    });
    console.log('InScript extension activated');
}
function getPython() {
    return vscode.workspace.getConfiguration('inscript').get('pythonPath', 'python3');
}
function runFile(filePath) {
    outputChannel.clear();
    outputChannel.show(true);
    outputChannel.appendLine(`▶ Running ${path.basename(filePath)}...\n`);
    const proc = (0, child_process_1.spawn)(getPython(), ['-m', 'inscript', filePath], {
        cwd: path.dirname(filePath)
    });
    proc.stdout.on('data', d => outputChannel.append(d.toString()));
    proc.stderr.on('data', d => outputChannel.append(d.toString()));
    proc.on('close', code => {
        outputChannel.appendLine(`\n${code === 0 ? '✅' : '❌'} Exited with code ${code}`);
    });
}
function checkFile(filePath) {
    outputChannel.clear();
    outputChannel.show(true);
    outputChannel.appendLine(`🔍 Type-checking ${path.basename(filePath)}...\n`);
    (0, child_process_1.execFile)(getPython(), ['-m', 'inscript', '--check', filePath], (err, stdout, stderr) => {
        outputChannel.append(stdout);
        if (stderr)
            outputChannel.append(stderr);
        if (!err) {
            outputChannel.appendLine('✅ No type errors found.');
        }
    });
}
function buildWeb(filePath, outDir) {
    outputChannel.clear();
    outputChannel.show(true);
    outputChannel.appendLine(`🌐 Building web export → ${outDir}...\n`);
    const proc = (0, child_process_1.spawn)(getPython(), [
        '-m', 'inscript', 'build', '--target', 'web', filePath, '--out', outDir
    ], { cwd: path.dirname(filePath) });
    proc.stdout.on('data', d => outputChannel.append(d.toString()));
    proc.stderr.on('data', d => outputChannel.append(d.toString()));
    proc.on('close', code => {
        if (code === 0) {
            vscode.window.showInformationMessage(`✅ Web export complete → ${outDir}`, 'Open Folder').then(action => {
                if (action === 'Open Folder') {
                    vscode.commands.executeCommand('revealFileInOS', vscode.Uri.file(outDir));
                }
            });
        }
    });
}
function showAST(filePath) {
    (0, child_process_1.execFile)(getPython(), ['-m', 'inscript', '--ast', filePath], (err, stdout) => {
        const doc = vscode.workspace.openTextDocument({
            content: stdout, language: 'json'
        });
        doc.then(d => vscode.window.showTextDocument(d, { preview: true, viewColumn: vscode.ViewColumn.Beside }));
    });
}
function runDiagnostics(doc, collection) {
    (0, child_process_1.execFile)(getPython(), ['-m', 'inscript', '--check', doc.fileName], (err, stdout, stderr) => {
        const diagnostics = [];
        const text = stderr || stdout;
        // Parse "filename.ins:LINE:COL: error: message"
        const re = /\.ins:(\d+):(\d+):\s*(error|warning):\s*(.+)/g;
        let m;
        while ((m = re.exec(text)) !== null) {
            const line = parseInt(m[1]) - 1;
            const col = parseInt(m[2]) - 1;
            const sev = m[3] === 'error'
                ? vscode.DiagnosticSeverity.Error
                : vscode.DiagnosticSeverity.Warning;
            const range = new vscode.Range(line, col, line, col + 100);
            diagnostics.push(new vscode.Diagnostic(range, m[4], sev));
        }
        collection.set(doc.uri, diagnostics);
    });
}
function deactivate() {
    outputChannel?.dispose();
}
//# sourceMappingURL=extension.js.map