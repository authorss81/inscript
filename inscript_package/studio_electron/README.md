# InScript Studio — Electron App

Native desktop wrapper around the InScript Studio web IDE.

## Requirements

- Node.js 18+
- Python 3.10+ with `pip install inscript-lang`
- (Optional) `pip install pygame` for game preview

## Development

```bash
cd studio_electron
npm install
npm start
```

## Build distributables

```bash
npm run dist
```

Produces:
- Windows: `dist/InScript Studio Setup.exe`
- macOS:   `dist/InScript Studio.dmg`
- Linux:   `dist/InScript Studio.AppImage`

## Architecture

```
Electron (Node.js)
  └─ BrowserWindow → http://localhost:8080
       └─ Python HTTP server (studio_app.py)
            └─ StudioBridge (inscript --studio)
                 ├─ File serving (/files, /read, /write)
                 ├─ RPC proxy (/rpc → StudioBridge)
                 └─ InScript runtime (interpreter.py)
```

## Limitations

- **Game preview**: pygame games open a native OS window. The Studio console
  captures stdout. An in-browser canvas preview is planned for v3.1.0 using
  the `--target web` Pyodide build.
- **Scene inspector**: works when game runs via ▶ Run (in-process). Subprocess
  games (`start_game`) can publish scene state via `import "studio_ipc" as ipc`.
- **Visual scripting editor**: the v3.0.0 release includes the `.vins` compiler
  (`inscript --visual-compile`). A drag-and-drop node graph UI is planned for v3.1.0.
