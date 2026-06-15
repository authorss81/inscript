# InScript Roadmap — Production-Grade Microversion Plan

> **Current:** v3.9.6.12 — Debugger: variable inspection. All 22 debugger tests pass.
>
> **Version scheme:** MAJOR.MINOR.PATCH.MICRO — each micro targets a discrete production feature.
> After v3.9.6.99, roll to v3.9.7.0 for the next feature cluster.

---

## Phase 8 — py_compiler Stability (v3.9.6.1–v3.9.6.9)

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

## Phase 9 — Debugger (v3.9.6.10–v3.9.6.15)

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

### v3.9.6.13 — Debugger: DAP protocol for VS Code
- [ ] Debug Adapter Protocol (DAP) server
- [ ] VS Code launch config integration
- [ ] Hit-count breakpoints
- [ ] Conditional breakpoints (break when `x > 5`)

### v3.9.6.13.1 — Rust lexer synchronization
Fixes 6 pre-existing Rust lexer tests by bringing the Rust lexer into parity with the Python lexer. Parallel microversion to v3.9.6.13.
- [ ] `keyword_or_ident()` emits `OnStart`, `OnUpdate`, `OnDraw`, `OnExit`, `IntType`, `FloatType`, `BoolType`, `StringType`, `VoidType` token variants (not `Identifier`)
- [ ] `scan_operator()` emits `PlusEq`, `MinusEq`, `StarEq`, `SlashEq` for compound assignment (not plain `Assign`)
- [ ] PyO3 bridge wraps Rust lexer errors as `LexerError` (not `SyntaxError`)
- [ ] Rebuild `inscript_parser.pyd` and verify `test_lexer.py` 25/25 pass

### v3.9.6.14 — Debugger: game loop debugging
- [ ] Break in `on_update` / `on_draw` / `on_start`
- [ ] Frame advance (step one game frame)
- [ ] Pause game loop at specific frame count
- [ ] Inspect scene state mid-frame

### v3.9.6.15 — Debugger: watch window + REPL integration
- [ ] Expression evaluation in debug REPL
- [ ] Persistent watch list across steps
- [ ] Type display for all values
- [ ] Pretty-print for structs, arrays, enums

---

## Phase 10 — Physics Engine (v3.9.6.20–v3.9.6.29)

**P0 gap:** No physics engine — only primitive AABB/circle overlap.

### v3.9.6.20 — Physics: Box2D binding (native extension)
- [ ] Create `physics` namespace module
- [ ] `PhysicsWorld` — world creation, step, gravity
- [ ] `Body` types: static, dynamic, kinematic
- [ ] Shape types: rectangle, circle, polygon

### v3.9.6.21 — Physics: collision events + callbacks
- [ ] `on_begin_contact(a, b)` — collision start callback
- [ ] `on_end_contact(a, b)` — collision separation
- [ ] `on_pre_solve(a, b)` — allow/disallow collision
- [ ] Contact info: point, normal, impulse

### v3.9.6.22 — Physics: joints + constraints
- [ ] Distance joint (spring)
- [ ] Revolute joint (hinge/pivot)
- [ ] Prismatic joint (sliding)
- [ ] Weld joint (rigid connection)
- [ ] Mouse joint (click-drag bodies)

### v3.9.6.23 — Physics: triggers + sensors
- [ ] Sensor bodies (detect overlap without collision response)
- [ ] `on_trigger_enter(other)`, `on_trigger_exit(other)`
- [ ] Area detection queries
- [ ] Ray-cast and shape-cast queries

### v3.9.6.24 — Physics: scene integration
- [ ] `on_physics_update(dt)` lifecycle hook (fixed timestep)
- [ ] Physics debug draw (show shapes, contacts, joints)
- [ ] Body + shape serialization to `.inscene` files
- [ ] Restitution, friction, density parameters

### v3.9.6.25 — Physics: character controller
- [ ] `CharacterBody` — move_and_slide, move_and_collide
- [ ] Slope handling, stair stepping
- [ ] Platform collision (one-way platforms)
- [ ] Knockback / impulse API

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
