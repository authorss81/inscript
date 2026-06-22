# InScript Roadmap — Production-Grade Microversion Plan

> **Current:** v3.9.6.29 — Physics: optimization (sleeping + broadphase). Phase 10 done.
> 
> **Version scheme:** MAJOR.MINOR.PATCH.MICRO — each micro targets a discrete production feature.
> After v3.9.6.99, roll to v3.9.7.0 for the next feature cluster.

---

## Testability: What .ins Tests Can and Cannot Cover

Tests should be written as `.ins` files (`test "name" { assert(...) }`) **whenever possible**. The `.py` tests are reserved for infrastructure that InScript cannot reach.

### Can test from `.ins`
- Language features (math, strings, control flow, functions)
- Standard library (math, json, io, collections)
- `dbg()` function (doesn't crash, produces output)
- Logic/algorithm validation (hit-count simulation, conditional evaluation)
- State dict manipulation (scene variable model)

### Cannot test from `.ins` (use `.py`)
- **DAP protocol** — requires raw stdin/stdout bytes, Content-Length framing, JSON-RPC message cycle
- **BreakpointManager internals** — `should_break()`, hit count tracking, condition evaluation — these are Python classes wrapping the interpreter
- **Interactive debug REPL** — `.locals`, `.globals`, `.stack`, `.watch` — requires simulated stdin input
- **CLI flags** — `--frame-break`, `--frame-advance`, `--debug`, `--dap` — require argparse in Python
- **Python module imports** — importing `debugger`, `dap_server`, `pygame_backend` and asserting on their internals
- **Compilation/pyc checks** — verifying Python source files compile without syntax errors

### Test runner
`inscript_test.py` uses a balanced-brace parser to extract test bodies, so nested `{}` inside `test "..." { ... }` are supported.

---

InScript is designed as a **game-scripting language** — scene lifecycle hooks, sprite/draw/input APIs, simple types running inside a host (pygame loop, browser, game engine). This is intentionally narrower than general-purpose languages.

### What this means for tooling

The debugger, DAP server, profiler, and formatter are all written in Python (the host), not InScript. This is the same pattern as:

| Language | Debugger | Host language | Self-hosted? |
|----------|----------|---------------|--------------|
| Lua | `lua.c` debug hook | C | No |
| Python | `pdb` | Python | Yes (has `sys.settrace`) |
| JS/V8 | DevTools | C++ | No (but `ndb` exists using Node APIs) |
| Ruby | `byebug` | C + Ruby | Partial |
| **InScript** | Debugger | **Python** | **No** |

### Roadmap to self-hosting

**Phase A (now — v3.9.6.x): Python-hosted tooling**
All debugger/DAP/profiler logic lives in Python. Zero language changes needed. Reusable protocol knowledge (Content-Length framing, JSON-RPC, breakpoint state machine) for later porting.

**Phase B (v3.9.7+): Expose I/O and JSON as built-in functions**
```inscript
let line = io.stdin.read_line()
let msg = json.parse(line)
io.stdout.write("Content-Length: 128\r\n\r\n{data}")
```
This lets users write scripts that parse/produce JSON and handle raw I/O — enough for a DAP server or any line-oriented protocol.

**Phase C (v3.10+): Expose debug hooks as callable functions**
```inscript
let bp = debug.breakpoint()    # file, line, condition of current hit
let frame = debug.frame(0)     # {locals, globals, pc}
```
Longer-term: `net.listen()`, `net.accept()`, coroutines for async I/O.

**Decision point:** If the community needs general-purpose scripting (file mgmt, web servers, automation), InScript would grow into that territory. For now, the focus stays on game development — but the infrastructure we build (DAP, profile IPC, py_compiler) is designed to be reusable regardless of which language hosts the tooling.

---

### v3.9.6.1 — py_compiler feature parity: MatchStmt ✅
- [x] `MatchStmt` → Python `match`/`case` (3.10+)
- [x] Match arm guards compile correctly
- [x] Wildcard `_` and binding patterns work
- [x] Type-narrowing patterns (`int x`, `string s`, struct patterns)
- [x] Verify with test suite (14/14 tests pass)

### v3.9.6.2 — py_compiler feature parity: F-strings ✅
- [x] F-string `"hello {name}"` → Python f-string
- [x] F-string expression substitution (nested exprs)
- [x] F-string brace escapes `{{` `}}`
- [x] Raw f-strings `rf"..."` support
- [x] Format specifiers `{x:.2f}` work correctly
- [x] Namespace access `::` inside f-string expressions
- [x] `_visit_NamespaceAccessExpr` handler added (Color::RED → Color.RED)
- [x] Verify with test suite (14/14 tests pass)

### v3.9.6.3 — py_compiler feature parity: Lambdas + closures
- [x] `|x| x * 2` → Python lambda
- [x] Closure capture of outer scope variables
- [x] Multi-parameter and zero-parameter lambdas
- [x] Lambda in function call args `map(arr, |x| x * 2)`
- [x] Type-annotated lambda params `|x: int, y: int| x + y`
- [x] Block body lambda `|x| { return x * 2 }`
- [x] Lambda returns lambda (curried calls)
- [x] Scene variable name resolution (state["x"] vs Python builtins)
- [x] Parser: `_suppress_union_type` flag for lambda param type annotations
- [x] _GLOBAL_NAMES extended with InScript stdlib functions

### v3.9.6.4 — py_compiler feature parity: Comprehensions + nested fns
- [x] List comprehensions `[x*x for x in arr]`
- [x] Dict comprehensions `{k: v for k,v in items}`
- [x] Nested `FunctionDecl` inside hooks
- [ ] ~~Generator expressions `(x for x in items)`~~ — not supported by InScript grammar

### v3.9.6.5 — py_compiler feature parity: Class methods + named args
- [x] `obj.method(args)` with positional args
- [x] Named/keyword arguments `obj.method(a: 1, b: 2)` (uses `:` not `=`)
- [x] Chained method calls `obj.foo().bar().baz()`
- [x] Static method calls `Type.method()`
- [x] Named args with scene variable values
- [x] Method returns callable (higher-order)
- [x] Method with side effects (mutates object state)

### v3.9.6.6 — py_compiler compilation speed optimization
- [x] Fixed `_names_cache` to use monotonic counter (not stale `id()`)
- [x] Added `compile_scene_hooks()` with `ThreadPoolExecutor` parallel support
- [x] Benchmark: `compile_hook` avg 0.38ms (per hook)
- [x] No regressions: all 69 microversion tests + 335 comprehensive pass

### v3.9.6.7 — Sprite & draw batching validation
- [x] Sprite-heavy benchmark game (~1000 sprites)
- [x] Validate `BatchedDrawNamespace.blits()` correctness (pixel-identical output)
- [x] Fix `set_alpha()` on per-pixel-alpha surfaces (use `BLEND_RGBA_MULT` instead)
- [x] Fix `BatchedDrawNamespace.sprite_ex` centering offset (was missing `-iw//2, -ih//2`)
- [x] Benchmark: basic sprite batching ~1.0x, transformed ~0.9x (transforms dominate)

### v3.9.6.8 — Rust VM final assessment
- [x] Build `.pyd` and benchmark Rust VM `compile_and_run` vs Phase 7
- [x] Rust VM is **36.7x faster** for standalone scripts (native compilation)
- [x] Phase 7 per-hook execution: **1.47µs** — Rust extension lacks `run()` API for per-hook use
- [x] Formally deprecated `--rust-vm` flag in game path (dead code, removed)
- [x] Removed `rust_vm` parameter from `run_scene()` and all callers

### v3.9.6.9 — Studio live-preview + hot-reload
- [x] Added `compile_hooks` RPC — compiles hooks via Phase 7, returns per-hook status
- [x] Added `profile_data` RPC — reads per-frame hook timing from IPC file
- [x] `pygame_backend.py` now writes profile timing to `_IPC_STATE_FILE` each frame
- [x] Electron `main.js` handles both dev and production paths for `inscript.py`
- [x] Fixed Electron `findPython()` to not use nonexistent venv paths
- [x] All 6 new tests pass; all existing microversion tests pass

---

## Phase 9 — Debugger (v3.9.6.10–v3.9.6.19)

**P0 gap:** No step debugger is the single biggest blocker for production game dev.

### v3.9.6.10 — Debugger: breakpoint infrastructure ✅
- [x] `dbg` built-in function (`dbg(expr)` prints value + location)
- [x] Breakpoint class: file, line, condition, enabled flag
- [x] Breakpoint manager (add, remove, list, clear)
- [x] `--debug` CLI flag to enter debug mode

### v3.9.6.11 — Debugger: step-over + step-into ✅
- [x] Execution pause at breakpoints
- [x] Step-over (next statement, skip into calls)
- [x] Step-into (enter function calls)
- [x] Step-out (return to caller)
- [x] Continue (resume until next breakpoint)

### v3.9.6.12 — Debugger: variable inspection ✅
- [x] `.locals` — list all variables in current scope
- [x] `.globals` — list global variables
- [x] `.watch <expr>` — evaluate expression at breakpoint
- [x] `.stack` — print call stack with line numbers
- [x] `.set` — modify variable at breakpoint
- [x] Expression evaluation in debug REPL

### v3.9.6.13 — Debugger: DAP protocol for VS Code ✅
- [x] Debug Adapter Protocol (DAP) server
- [x] VS Code launch config integration
- [x] Hit-count breakpoints (`b 10 hit >= 3`)
- [x] Conditional breakpoints (`b 10 if x > 5`)
- [x] DAP stdin/stdout Content-Length framing
- [x] `--dap` CLI flag
- [x] Tests: `.ins` (22 tests — dbg, hit/condition logic) + `.py` (22 tests — DAP framing, breakpoint internals)

### v3.9.6.13.1 — Rust lexer synchronization ✅
Parallel microversion to v3.9.6.13. Fixes 6 pre-existing Rust lexer tests by bringing the Rust lexer into parity with the Python lexer.
- [x] `keyword_or_ident()` emits `OnStart`, `OnUpdate`, `OnDraw`, `OnExit`, `IntType`, `FloatType`, `BoolType`, `StringType`, `VoidType` token variants (not `Identifier`)
- [x] `scan_operator()` emits `PlusEq`, `MinusEq`, `StarEq`, `SlashEq` for compound assignment (not plain `Assign`)
- [x] `scan_slash()` emits `SlashSlash`, `SlashEq` variants
- [x] PyO3 bridge wraps Rust lexer errors as `LexerError` (not `SyntaxError`)
- [x] `token_type_name()` in `lib.rs` returns correct string for every variant
- [x] Rebuild `inscript_parser.pyd` and verify `test_lexer.py` 25/25 pass

### v3.9.6.14 — Debugger: game loop debugging ✅
- [x] Frame advance (step one game frame)
- [x] Pause game loop at specific frame count (`--frame-break N`)
- [x] Frame-advance REPL with `.locals`, `.globals`, `.stack`, `.watch`, `.state`
- [x] `--frame-advance` flag (step every frame)
- [x] Break in `on_update` / `on_draw` / `on_start` (breakpoint integration with game loop)
- [x] Inspect scene state mid-frame (state dict via `.state` command)
- [x] Set/clear breakpoints from game debug REPL (`b`, `bl`, `bc` commands)
- [x] Tests: `.ins` (20 tests — frame counting, state dict, profile structure) + `.py` (24 tests — CLI flags, game loop structure, compilation checks)

### v3.9.6.15 — Debugger: watch window + REPL integration ✅
- [x] Expression evaluation in debug REPL (via `else:` fallback in REPL loop)
- [x] Persistent watch list auto-evaluated at every breakpoint pause
- [x] Type display for all values (`_inscript_type_str` — int, float, string, bool, nil, array, dict, fn, enum, struct, range)
- [x] Pretty-print for structs, arrays, enums (`_pretty_format` with indentation + depth limit)
- [x] `.type <expr>` command — shows type name + pretty-printed value
- [x] `_format_value(val)` — returns `(type) pretty_value` string, used by `.locals`, `.globals`, `.watch`, `_eval_expr`
- [x] Tests: `.ins` (20 tests — type/pretty-print via language features) + `.py` (39 tests — type formatting, pretty-print output, watch persistence)

### v3.9.6.16 — Debugger: multi-file breakpoints
- [x] `b file.ins:line` syntax works across multiple loaded files
- [x] Dynamic filename tracking in `should_pause_at` (uses interpreter's current file)
- [x] Source-line display from any file via `_source_files` dict
- [x] `bl` groups breakpoints by file
- [x] `.files` command lists all loaded files
- [ ] Tests: `.ins` + `.py`

### v3.9.6.17 — Debugger: exception breakpoints
- [ ] `catch <error-type>` — pause when InScript raises matching error
- [ ] `uncatch <error-type>` — remove catchpoint
- [ ] `catch` — list active catchpoints
- [ ] Interceptor in interpreter's error path
- [ ] Shows error type + message + stack trace on catch
- [ ] Tests: `.ins` + `.py`

### v3.9.6.18 — Debugger: data breakpoints (watchpoints)
- [ ] `watchvar <name>` — break when variable changes value
- [ ] `unwatch <name>` — remove watchpoint
- [ ] `watchvar` — list active watchpoints
- [ ] Tracks variable writes at statement level
- [ ] Shows old → new value on change
- [ ] Tests: `.ins` + `.py`

### v3.9.6.19 — Debugger: REPL history + tab completion + polish
- [ ] Command history with up/down arrow (persistent via `~/.inscript_debug_history`)
- [ ] Tab completion for debugger commands
- [ ] Better error messages with suggestions for similar commands
- [ ] `.locals` highlights current breakpoint line in scope
- [ ] Tests: `.ins` + `.py`

---

## Phase 10 — Physics Engine (v3.9.6.20–v3.9.6.29)

**P0 gap:** No physics engine — only primitive AABB/circle overlap.

### v3.9.6.20 — Physics: Box2D binding (native extension)
- [x] `PhysicsWorld` — world creation, step, gravity (`physics_engine.py`)
- [x] `Body` types: static, dynamic, kinematic (with `get_attr`/`set_attr`)
- [x] Shape types: rectangle, circle (with factory methods)
- [x] InScript builtins: `PhysicsWorld`, `PhysicsShape`, constants
- [x] `physics` namespace module (`physics::World`, `physics::Body`, `physics::DYNAMIC`)
- [x] Tests: 49/49

### v3.9.6.21 — Physics: collision events + callbacks
- [x] `on_begin_contact(body_a, body_b, contact)` — collision start callback
- [x] `on_end_contact(body_a, body_b)` — collision separation
- [x] `on_pre_solve(body_a, body_b, contact)` — allow/disallow collision
- [x] Contact info: normal_x, normal_y, point_x, point_y, penetration, body_a, body_b
- [x] Tests: 24/24

### v3.9.6.22 — Physics: joints + constraints
- [x] Distance joint (spring with stiffness/damping)
- [x] Revolute joint (hinge with angle limits + motor)
- [x] Prismatic joint (sliding with axis + limits)
- [x] Weld joint (rigid connection)
- [x] Mouse joint (click-drag with max force)
- [x] Tests: 26/26

### v3.9.6.23 — Physics: triggers + sensors
- [ ] Sensor bodies (detect overlap without collision response)
- [ ] `on_trigger_enter(other)`, `on_trigger_exit(other)`
- [ ] Area detection queries
- [ ] Ray-cast and shape-cast queries

### v3.9.6.24 — Physics: scene integration ✅
- [x] `on_physics(dt)` lifecycle hook (fixed timestep, 60Hz accumulator)
- [x] Physics debug draw (F1 toggle — shape wireframes, contact normals, joint lines)
- [x] Body + shape serialization (`to_dict()`, `save_scene()`, `load_scene()`)
- [x] Restitution, friction, density parameters (friction wired into collision resolution)

### v3.9.6.25 — Physics: character controller ✅
- [x] `CharacterBody` — move_and_slide, move_and_collide
- [x] Slope handling, stair stepping
- [x] Platform collision (one-way platforms)
- [x] Knockback / impulse API
- [x] Tests: `.ins` (11 tests — floor/wall/ceiling, knockback, move_and_collide, one-way platforms) + `.py` (19 tests)

### v3.9.6.26 — Physics: world queries ✅
- [x] `query_aabb` / `query_circle`
- [x] `contact_points` (from `_last_contacts` stored during `step()`)
- [x] `ray_cast` (closest) / `ray_cast_all` (all hits sorted by distance)
- [x] Tests: `.ins` (9 tests — hit/miss, sorted multi-hit, aabb/circle find, contacts) + `.py` (32 tests)

### v3.9.6.27 — Physics: continuous collision detection (CCD) ✅
- [x] `Body.ccd_enabled` flag
- [x] Swept-AABB TOI computation (`_sweep_to_static`)
- [x] CCD bodies sub-step to collision point
- [x] Works with rect and circle shapes
- [x] Tests: `.ins` (6 tests — CCD on/off for rect+circle) + `.py` (11 tests)

### v3.9.6.28 — Physics: collision filtering ✅
- [x] `Body.collision_group` / `Body.collision_mask` bitmasks
- [x] `_can_collide()` static helper
- [x] Filtering applied in `_step_bodies`, `_sweep_to_static`, CCD TOI resolution
- [x] Tests: `.ins` (5 tests — allow/block/mask=0/default) + `.py` (12 tests)

### v3.9.6.29 — Physics: optimization (sleeping + broadphase) ✅
- [x] Spatial grid broadphase (`_get_broadphase_pairs`) activated >32 bodies
- [x] Body sleeping: `_sleep_timer` increments when speed < threshold
- [x] Sleeping bodies skip gravity, integration, and collision checks
- [x] Wake on velocity/force change or collision
- [x] Tests: `.ins` (5 tests — settle/wake/sleep/stay) + `.py` (14 tests)

---

## Phase 11 — GUI System (v3.9.6.30–v3.9.6.39)

**P0 gap:** No GUI system — every game must hand-code UI rendering from scratch.

### v3.9.6.30 — GUI: core widget types
- [ ] `gui` namespace module
- [ ] `Button` — text, icon, click handler, states (normal/hover/pressed/disabled)
- [ ] `Label` — text, font, color, alignment, wrapping
- [ ] `Panel` — container with background, border, padding
- [ ] `Image` — sprite widget with stretch/fit/tile modes

### v3.9.6.31 — GUI: layout system
- [ ] `HBox` — horizontal box layout
- [ ] `VBox` — vertical box layout
- [ ] `Grid` — row/column grid layout
- [ ] Size policies: fixed, fill, expand, shrink
- [ ] Anchors and margins (screen-relative positioning)

### v3.9.6.32 — GUI: input widgets
- [ ] `TextInput` — single-line text entry with cursor, selection
- [ ] `TextArea` — multi-line text input
- [ ] `Slider` — horizontal/vertical value slider
- [ ] `Checkbox` — toggle with label
- [ ] `Dropdown` — selection menu

### v3.9.6.33 — GUI: containers + navigation
- [ ] `ScrollView` — scrollable content area
- [ ] `TabContainer` — tabbed panels
- [ ] `Splitter` — resizable split panes
- [ ] `Menu` / `MenuBar` — dropdown menus
- [ ] Keyboard focus navigation (Tab, arrows, Enter)

### v3.9.6.34 — GUI: styling + theming
- [ ] Theme system: colors, fonts, sizes, margins
- [ ] Style property inheritance (parent → child)
- [ ] Hover, pressed, disabled, focused visual states
- [ ] Custom stylesheets per widget type
- [ ] Rounded corners, drop shadows, gradients

### v3.9.6.35 — GUI: data binding + MVC
- [ ] Model-View pattern: widget ↔ variable binding
- [ ] Observable variables (auto-redraw on change)
- [ ] List model for dropdowns, grids
- [ ] Form validation (required, min, max, pattern)
- [ ] Dialog system (message boxes, file picker, color picker)

---

## Phase 12 — Particle & Animation Systems (v3.9.6.40–v3.9.6.49)

**P1 gap:** Particle system is demo-only, animation system is a standalone script.

### v3.9.6.40 — Particles: built-in particle API
- [ ] `particles` namespace module
- [ ] `ParticleEmitter` — position, rate, lifetime, max particles
- [ ] Particle properties: position, velocity, color, size, rotation, alpha
- [ ] Emission shapes: point, circle, rectangle, cone
- [ ] GPU acceleration (pre-compute batch for sprite drawing)

### v3.9.6.41 — Particles: curve-based property modulation
- [ ] Size-over-lifetime curve
- [ ] Color-over-lifetime gradient
- [ ] Velocity-over-lifetime (wind, gravity wells)
- [ ] Alpha/fade-over-lifetime
- [ ] Rotation-over-lifetime

### v3.9.6.42 — Particles: advanced features
- [ ] Sub-emitters (emit on death, on collision)
- [ ] Attractor / repeller zones
- [ ] Particle trails / ribbons
- [ ] Particle collision with scene bodies
- [ ] Pre-warm (simulate N seconds at spawn)

### v3.9.6.43 — Animation: animation player
- [ ] `AnimationPlayer` namespace
- [ ] Property keyframing: position, rotation, scale, color, etc.
- [ ] Interpolation modes: linear, ease, cubic, bounce, elastic
- [ ] Animation tracks: parallel, sequential
- [ ] Play, pause, stop, seek, speed control

### v3.9.6.44 — Animation: state machine
- [ ] `AnimationStateMachine` — states + transitions
- [ ] Transition conditions: time, variable threshold, event
- [ ] Blend trees (cross-fade between animations)
- [ ] Animation events (callbacks at specific frames)
- [ ] Blend spaces (2D parameter-driven animation mixing)

### v3.9.6.45 — Animation: tween system
- [ ] Built-in `tween` namespace (not just a package)
- [ ] `Tween.to(obj, "property", target, duration)`
- [ ] Easing presets: 30+ functions
- [ ] Sequence / parallel tween groups
- [ ] Ping-pong, loop, delay, on_complete callback

---

## Phase 13 — Visual Editor (v3.9.6.50–v3.9.6.59)

**P0 gap:** No visual editor — everything is code-only.

### v3.9.6.50 — Editor: scene viewport
- [ ] Electron Studio: replace text editor with hybrid scene view
- [ ] 2D viewport with pan/zoom/grid
- [ ] Node tree panel (list all nodes in current scene)
- [ ] Click-to-select nodes in viewport
- [ ] Property inspector panel (read/write node properties)

### v3.9.6.51 — Editor: drag-drop placement
- [ ] Drag sprites/shapes from asset panel into viewport
- [ ] Snap-to-grid placement
- [ ] Transform handles (move, rotate, scale)
- [ ] Multi-select + group move
- [ ] Undo/redo for all editor actions

### v3.9.6.52 — Editor: scene file round-trip
- [ ] `.inscene` visual format → `SceneTree` deserialization
- [ ] Editor modifications saved back to `.inscene` files
- [ ] Node component system (attach scripts to nodes)
- [ ] Script-to-node binding (edit `.ins` from node inspector)
- [ ] Hot-reload scene changes without restart

### v3.9.6.53 — Editor: tilemap editor
- [ ] Tile palette panel
- [ ] Brush tools: paint, fill, erase, pick
- [ ] Layer management (multiple tile layers with z-order)
- [ ] Auto-tiling (rule-based tile placement)
- [ ] Collision layer visualization

### v3.9.6.54 — Editor: animation editor
- [ ] Timeline panel with keyframe tracks
- [ ] Keyframe insertion/deletion/moving
- [ ] Animation curve editor (Bezier handles)
- [ ] Onion skinning (previous frame ghost)
- [ ] Skeleton animation support (bone hierarchy)

### v3.9.6.55 — Editor: audio + asset management
- [ ] Asset browser (sprites, sounds, fonts, scenes)
- [ ] Drag-drop asset reference into code editor
- [ ] Audio preview (play sounds in editor)
- [ ] Sprite-sheet slicing tool
- [ ] Texture atlas packing

---

## Phase 14 — Platform Export & Deployment (v3.9.6.60–v3.9.6.69)

**P1 gap:** No mobile/web export, desktop build is manual.

### v3.9.6.60 — Export: WASM web target
- [ ] InScript → Python → Pyodide/WASM compilation pipeline
- [ ] WebGL rendering backend (replay SDL2 calls via WebGL)
- [ ] Touch input mapping (touch → mouse/keyboard events)
- [ ] Asset bundling for web (embed assets in WASM)
- [ ] Audio: WebAudio API integration

### v3.9.6.61 — Export: mobile target (Android)
- [ ] Android APK build pipeline (python-for-android or chaquopy)
- [ ] Touch input: multi-touch, gestures (swipe, pinch, tap)
- [ ] Screen resolution scaling
- [ ] Back button, lifecycle management (pause/resume)
- [ ] Performance profile: 60fps on mid-range devices

### v3.9.6.62 — Export: mobile target (iOS)
- [ ] iOS IPA build pipeline
- [ ] Metal rendering backend for iOS
- [ ] iOS-specific input (haptic feedback, tilt sensor)
- [ ] App icon, splash screen, orientation config
- [ ] App Store compliance checklist

### v3.9.6.63 — Export: desktop installer
- [ ] `--build` flag produces standalone executable (PyInstaller/Nuitka)
- [ ] Asset bundling (single `.insgame` file)
- [ ] Auto-update mechanism
- [ ] Steam SDK integration (achievements, leaderboards, cloud saves)
- [ ] Windows installer (.msi), macOS (.dmg), Linux (.AppImage)

### v3.9.6.64 — Export: asset pipeline
- [ ] Texture compression (PVRTC, ETC2, ASTC for mobile)
- [ ] Audio compression (Vorbis → MP3/OGG per platform)
- [ ] Font subsetting (include only used characters)
- [ ] Asset hot-reload toggle for development builds
- [ ] Content manifest + integrity checks

---

## Phase 15 — Networking & Multiplayer (v3.9.6.70–v3.9.6.79)

**P2 gap:** No real networking — only local single-player.

### v3.9.6.70 — Networking: WebSocket client
- [ ] `net` namespace module
- [ ] `WebSocket.connect(url)` — client connection
- [ ] `send(data)`, `on_message`, `on_open`, `on_close`
- [ ] Text and binary message support
- [ ] Auto-reconnect with backoff

### v3.9.6.71 — Networking: WebSocket server
- [ ] Built-in WebSocket server (embedded in game process)
- [ ] Client management (connect, disconnect, list)
- [ ] Broadcast, send_to, send_except
- [ ] Room/lobby management
- [ ] Server-authoritative game loop skeleton

### v3.9.6.72 — Networking: UDP transport
- [ ] Low-latency UDP transport
- [ ] Packet serialization (binary protocol)
- [ ] Sequence numbers and ACK
- [ ] Reliability layer (selective retransmit)
- [ ] Connection state machine (handshake, heartbeat, timeout)

### v3.9.6.73 — Networking: state synchronization
- [ ] Authoritative server state broadcasting
- [ ] Client-side prediction + reconciliation
- [ ] Entity interpolation (smooth remote movement)
- [ ] Delta compression (send only changed state)
- [ ] Lag compensation (rollback + resimulate)

### v3.9.6.74 — Networking: matchmaking + lobbies
- [ ] Lobby discovery (LAN broadcast)
- [ ] Join-by-code (peer-to-peer)
- [ ] Simple matchmaking (Elosystem)
- [ ] Player profiles + authentication
- [ ] NAT punch-through for peer-to-peer

---

## Phase 16 — 3D Rendering & Graphics (v3.9.6.80–v3.9.6.89)

**P3 gap:** 2D-only via pygame. No 3D, no shader execution.

### v3.9.6.80 — 3D: rendering backend
- [ ] OpenGL 3.3+ core rendering backend
- [ ] Camera system (perspective/orthographic)
- [ ] 3D mesh loading (.obj, .glTF)
- [ ] Material system (diffuse, normal, specular, emission maps)
- [ ] Lighting: directional, point, spot lights

### v3.9.6.81 — 3D: scene graph
- [ ] 3D scene node hierarchy
- [ ] Transform: position, rotation (quaternion), scale
- [ ] MeshInstance, Light, Camera node types
- [ ] Frustum culling
- [ ] Level-of-detail (LOD) system

### v3.9.6.82 — 3D: skeletal animation
- [ ] Skeleton + bone hierarchy
- [ ] Skinned mesh rendering (GPU skinning)
- [ ] Animation retargeting
- [ ] Blend shapes / morph targets
- [ ] Ragdoll physics integration

### v3.9.6.83 — Shader: runtime execution
- [ ] InScript shader AST → GLSL compilation
- [ ] Shader uniform binding from InScript code
- [ ] Post-processing pipeline (bloom, DOF, SSAO)
- [ ] Compute shaders for particle simulation
- [ ] Shader hot-reload (edit shader → see result live)

### v3.9.6.84 — 3D: post-processing + effects
- [ ] HDR rendering + tone mapping
- [ ] Shadow mapping (directional/spot)
- [ ] Reflections (SSR, reflection probes)
- [ ] Skybox system
- [ ] Fog (distance, height, volumetric)

---

## Phase 17 — Rust VM Production (v3.9.6.90–v3.9.6.99)

**P3 gap:** Rust VM is incomplete — JIT not wired, LLVM IR uses tagged ints.

### v3.9.6.90 — Rust: wire JIT into execution loop
- [ ] After hot trace detected + native code compiled, swap VM dispatch to native fn
- [ ] Native function cache with LRU eviction
- [ ] Deoptimization (guard failure → fall back to interpreted)
- [ ] OSR (on-stack replacement) for long-running loops
- [ ] Benchmark JIT speed vs non-JIT, publish results

### v3.9.6.91 — Rust: LLVM IR native types
- [ ] Replace tagged `i64` scheme with native LLVM types (`i32`, `double`, `i1`)
- [ ] Type-inference-guided IR generation (use specialized types when known)
- [ ] Auto-vectorization hints (`llvm.memcpy`, `llvm.assume`)
- [ ] Function inlining across InScript call boundaries
- [ ] Tail-call optimization for recursive functions

### v3.9.6.92 — Rust: exception handling + Try/Throw
- [ ] Rust-side unwind/panic handling for InScript try/catch
- [ ] `Throw` opcode implementation in Rust VM
- [ ] `Try` opcode with catch block dispatch
- [ ] Stack unwinding with frame cleanup (`defer`)
- [ ] Cross-FFI exception propagation (Rust → Python)

### v3.9.6.93 — Rust: async/coroutine support
- [ ] Generator frame allocation in Rust VM
- [ ] `yield` opcode: suspend/resume execution
- [ ] `await` opcode: suspend until future resolves
- [ ] Channel operations in Rust VM (recv/send/select)
- [ ] Event loop integration (wake on IO)

### v3.9.6.94 — Rust: full standalone runtime
- [ ] Separate `inscript` binary (no Python dependency)
- [ ] SDL2/GLFW-based game loop in Rust
- [ ] InScript bytecode → native executable pipeline
- [ ] Zero-copy FFI between runtime and compiled hooks
- [ ] Benchmark: standalone Rust runtime vs Phase 7 + CPython

### v3.9.6.95 — Rust: build + CI pipeline
- [ ] Pre-built wheels for all platforms (macOS ARM/x64, Windows, Linux)
- [ ] CI publishes `.pyd` / `.so` / `.dylib` on every tag
- [ ] Criterion benchmarks in CI (track perf regressions)
- [ ] Fuzz testing for Rust lexer/parser/compiler
- [ ] Property-based testing for VM opcodes

---

## Phase 18 — Ecosystem & Community (v3.9.6.96–v3.9.6.99)

**P2 gap:** Tiny ecosystem, no community, no tutorials.

### v3.9.6.96 — Documentation site
- [ ] Full documentation website (VitePress / Docusaurus)
- [ ] Language reference: every construct with examples
- [ ] Standard library reference: every function with signatures
- [ ] Tutorial: "Your first InScript game" (step-by-step)
- [ ] API docs auto-generated from source

### v3.9.6.97 — Tutorial games + cookbook
- [ ] 5 tutorial games: Pong, Breakout, Platformer, Top-down RPG, Puzzle
- [ ] Cookbook: 50+ common patterns (movement, shooting, state machines, etc.)
- [ ] Video series: "InScript in 30 minutes"
- [ ] Migration guide: Lua/Unity/GDScript → InScript
- [ ] Best practices guide: project structure, performance, debugging

### v3.9.6.98 — Package ecosystem growth
- [ ] Standard package templates (scaffold with `inscript --new`)
- [ ] Package submission CI (auto-test + publish on PR merge)
- [ ] Featured packages program
- [ ] Package quality badges (tested, documented, maintained)
- [ ] Community registry moderation tools

### v3.9.6.99 — Community infrastructure
- [ ] Discord server (chat, help, showcase)
- [ ] GitHub issue templates + triage workflow
- [ ] Community showcase page (games made with InScript)
- [ ] Monthly release cadence (predictable schedule)
- [ ] Security vulnerability reporting process (HackerOne / self-hosted)

---

## .ins Test Coverage Roadmap

`.ins` tests are the only place real InScript code is exercised end-to-end (lexer → parser → analyzer → interpreter). They serve as the primary examples for anyone learning the language. Currently, ~80% of `.py` tests fundamentally cannot be `.ins` (Python internals, DAP framing, benchmarks), but every feature exposed in the InScript runtime should have `.ins` coverage.

### Progress

| Area | Version | Feature | .ins tests | Status |
|------|---------|---------|-----------|--------|
| **Language** | v3.9.6.1 | MatchStmt | 14 | ✅ Done |
| **Language** | v3.9.6.2 | F-strings | 12 | ✅ Done |
| **Language** | v3.9.6.3 | Lambdas | 15 | ✅ Done |
| **Language** | v3.9.6.4 | Comprehensions | 14 | ✅ Done |
| **Language** | v3.9.6.5 | Method calls + named args | 16 | ✅ Done |
| **Physics** | v3.9.6.20 | PhysicsWorld, Body, Shape basics | 20 | ✅ Done |
| **Physics** | v3.9.6.21 | Collision events + callbacks | 9 | ✅ Done |
| **Physics** | v3.9.6.22 | Joints + constraints | 10 | ✅ Done |
| **Physics** | v3.9.6.23 | Triggers + sensors | 8 | ✅ Good |
| **Physics** | v3.9.6.24 | Scene integration | 10 | ✅ Good |
| **Physics** | v3.9.6.25 | Character controller | 11 | ✅ Good |
| **Physics** | v3.9.6.26 | World queries | 9 | ✅ Good |
| **Physics** | v3.9.6.27 | CCD | 6 | ✅ Good |
| **Physics** | v3.9.6.28 | Collision filtering | 5 | ✅ Good |
| **Physics** | v3.9.6.29 | Sleeping + broadphase | 5 | ✅ Good |
| **Debugger** | v3.9.6.10 | Breakpoints | 11 | ✅ Done |
| **Debugger** | v3.9.6.11 | Stepping | 9 | ✅ Done |
| **Debugger** | v3.9.6.12 | Variable inspection | 9 | ✅ Done |
| **Debugger** | v3.9.6.13 | DAP + hit/condition bps | 22 | ✅ Good |
| **Debugger** | v3.9.6.14 | Game loop debugging | 20 | ✅ Good |
| **Debugger** | v3.9.6.15 | Watch + REPL | 20 | ✅ Good |
| **Debugger** | v3.9.6.16 | Multi-file breakpoints | 7 | ✅ Done |
| **Debugger** | v3.9.6.17 | Exception breakpoints | 7 | ✅ Done |
| **Debugger** | v3.9.6.18 | Data breakpoints | 8 | ✅ Done |
| **Debugger** | v3.9.6.19 | REPL polish | 9 | ✅ Done |

### Priority Plan

**P0 — Language features** (v3.9.6.1–5): ✅ Done (71 tests across all 5 versions).

**P1 — Physics backfill** (v3.9.6.20–22): ✅ Done (39 tests — gravity, bodies, shapes, collision callbacks, all 5 joint types).

**P2 — Debugger backfill** (v3.9.6.10–12, 16–19): ✅ Done (60 tests — dbg loops, closures, imports, try/catch, struct mutation, REPL expressions).

---

## v3.10.0 — Production 1.0 Release Candidate

- [ ] All P0 gaps closed: debugger ✓, physics ✓, GUI ✓, visual editor ✓, ECS ✓
- [ ] All P1 gaps closed: particles ✓, animation ✓, mobile/web export ✓, docs ✓
- [ ] All P2 gaps substantially addressed
- [ ] Performance targets met:
  - [ ] 60fps minimum on 5-year-old hardware with 2D scenes
  - [ ] 30fps minimum on mid-range mobile
  - [ ] 1000+ sprites at 60fps with batching
  - [ ] <1ms per frame for physics + game logic (non-rendering)
- [ ] Production game shipped (reference title demonstrating all features)
- [ ] 100+ community packages
- [ ] 50+ stars on GitHub
- [ ] 10+ active contributors

---

## Post-v3.10.0 — Platform Expansion

### v3.10.1 — Console support
- [ ] Nintendo Switch SDK integration
- [ ] PlayStation (PS4/PS5) SDK integration
- [ ] Xbox SDK integration
- [ ] Console-specific input (controllers, vibration, lightbar)
- [ ] Certification checklist compliance

### v3.10.2 — Cloud + backend services
- [ ] InScript Cloud: hosted multiplayer relay
- [ ] Leaderboard service (REST API)
- [ ] Player authentication (OAuth, Steam, Epic, Apple, Google)
- [ ] Cloud save synchronization
- [ ] Analytics / telemetry SDK

### v3.10.3 — AI + machine learning
- [ ] `ai` namespace: neural network inference
- [ ] ONNX model import (trained in PyTorch/TF → run in InScript)
- [ ] Behavior tree editor (visual AI state machine)
- [ ] Pathfinding: A*, navmesh, flow fields
- [ ] ML-agent integration (training → exported policy)
