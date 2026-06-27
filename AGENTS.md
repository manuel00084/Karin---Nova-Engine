# Karin VTuber Renderer

## Current State
Nova backend (pygfx + wgpu D3D12) with PBR/toon/cel/taimanin/vtuber shading, CPU morph combining, GPU skinning, springbone physics, cloth simulation, virtual morphs, VMC tracking, OSC output, configurable expression hotkeys, model hot-switching, screenshot, virtual keyboard/mouse overlay, walking locomotion, hand IK (mouse + webcam), transparent window (Win32 layered), GPU particle system (sparkles/hearts/stars), procedural face idle (mouth/brow/head micro), voice expression triggers, interactive mouse/audio-reactive backgrounds, **window crop (circle/rounded square)**, **setting presets (save/load named configs)**, **XInput gamepad (expressions + body lean)**, **keyboard/mouse-reactive avatar motion (typing arms + mouse head tracking)**, **3D model accessories (.glb/.vrm attached to bones)**, **Spout output (OBS/TouchDesigner texture sharing)**, **NDI output (network texture sharing)**, **WebSocket receiver (Stream Deck/bot integration)**, **hand gesture mapping (MediaPipe landmarks → actions)**, **MMD .vmd motion loading**, **stretch bones (distance-based deformation)**, **pendulum chain physics (parameter-driven bone chains)**, **AudioLink-style audio-reactive frequency analysis**, **liquid/slime physics (particle-based fluids)**, **plugin system (custom post-processing/behavior extensions)**, **throwable items + head pats + confetti + screen effects + health bar** (VTuber Plus interactions), **emote overlays** (PNG above avatar), **room/background system** (switchable scenes with transitions), and **ragdoll mode** (spring-physics bone fallback). Architecture from `@pixiv/three-vrm`: VrmParser → Humanoid + BlendShapeProxy + SpringBoneManager. All Python files clean (no comments).

## Architecture
- `render/backends/nova.py` — main engine: window, input, GPU pipelines, VRM loading, morphs, cloth, physics
- `render/skeleton.py` — `SkeletonSystem` — bone hierarchy, world/local matrices, joint texture
- `render/tracking_server.py` — UDP VMC protocol server → `TrackingState` → Humanoid + BlendShapeProxy
- `render/osc_output.py` — OSC sender (raw UDP, no deps) — blend shapes + bone poses to external apps
- `render/spout_output.py` — SpoutSender (ctypes SpoutLibrary.dll) — GPU texture sharing to OBS/TouchDesigner
- `render/vrm/parser.py` — wraps pygltflib, extracts VRM extension data
- `render/vrm/humanoid.py` — 54 VRM bone mapping → skeleton, `set_bone_rotation()`, `apply_vmc_pose()`
- `render/vrm/blendshape.py` — `BlendShapeProxy` — 14+ presets, morph combining, auto-blink
- `render/vrm/springbone.py` — `SpringBoneManager` — verlet physics on bone tails
- `render/vrm/cloth.py` — `ClothManager` — PBD cloth simulation
- `render/vrm/virtual_morphs.py` — `VirtualMorphGenerator` — procedural morphs for missing presets
- `render/vrm/pmx_loader.py` — `parse_pmx()` — native PMX/PMD model converter
- `render/vrm/model.py` — `VrmModel` — composes Humanoid + BlendShapeProxy + SpringBoneManager
- `render/vrm/device_overlay.py` — `DeviceOverlay` — virtual keyboard/mouse overlay
- `render/vrm/particles.py` — `ParticleEmitter` + `ExpressionParticleTrigger` — GPU-instanced sparkles/hearts/stars
- `render/vrm/ik.py` — `ProceduralLocomotion` — hip sway, bob, foot CCD, arm swing for walking
- `render/vrm/procedural.py` — `ProceduralFaceIdle` + `VoiceExpressionTriggers` — mouth/brow/head micro, laughter/surprise/anger/sadness detection from audio
- `render/vrm/gamepad.py` — `GamepadInput` — XInput gamepad polling, button→expression mapping, stick→body lean
- `render/vrm/desktop_motion.py` — `DesktopMotion` — keyboard typing arm motion + mouse head/eye tracking
- `render/vrm/stretch_bones.py` — `StretchBoneSystem` — distance-based bone deformation (muscle flex, jiggle control)
- `render/vrm/pendulum_chain.py` — `PendulumChainSystem` — parameter-driven pendulum bone chains (wobbly eyes, ear twitches, tail sway)
- `render/vrm/gesture_mapper.py` — `GestureMapper` — MediaPipe hand landmarks → gesture detection → actions
- `render/vrm/vmd_loader.py` — `VmdAnimation` — MMD .vmd motion file parser and sampler
- `render/vrm/audiolink.py` — `AudioLinkSystem` — audio-reactive frequency analysis (4 bass + 4 mid + 4 treble + volume)
- `render/vrm/liquid_physics.py` — `LiquidSystem` — particle-based liquid with SPH density, surface tension, colliders
- `render/ndi_output.py` — `NdiSender` — NDI texture sharing (alternative to Spout)
- `render/websocket_receiver.py` — `WebSocketReceiver` — WebSocket server for Stream Deck/Streamer.bot/bots
- `render/plugins.py` — `PluginManager` + `PluginBase` — custom post-processing and behavior extensions
- `render/vrm/interactions.py` — `InteractionSystem` — throwable items, head pats, confetti, screen effects, health bar
- `render/vrm/emotes.py` — `EmoteSystem` — PNG emote overlays above avatar head
- `render/vrm/rooms.py` — `RoomSystem` — switchable rooms with transitions
- `render/vrm/ragdoll.py` — `RagdollSystem` — spring-physics ragdoll bone fallback
- `render/vrm/pose_extractor.py` — `WebcamFaceTracker` — webcam tracking + hand landmarks (21 per hand) for gesture mapper
- `render/config.py` — `RendererConfig` dataclass with JSON load/save
- `render/shaders_wgsl/` — all WGSL shaders (pbr, cel, taimanin, vtuber, outline, post-process, compute, crop)

## Model Compatibility
All 7 .glb files parse via pygltflib; 5 load fully in renderer:

| Model | Meshes | Prims | Joints | Morphs | Bones | Blends | Springs | Loads? |
|---|---|---|---|---|---|---|---|---|
| Miku V4X | 3 | 23 | 750 (3×250) | 7 | 54 | 14 | 28 (50 bones) | ✅ |
| Asaba Seine | 3 | 20 | 747 (3×249) | 7 | 54 | 14 | 25 | ✅ |
| Pyra | 3 | 14 | 339 (3×113) | 8 | 54 | 14 | 15 | ✅ |
| hoochan | 3 | 15 | 411 (3×137) | 5 | 54 | 14 | 14 | ✅ |
| 白金ちどり | 3 | 21 | 699 (3×233) | 7 | 54 | 14 | 25 | ✅ |
| Carlotta (WuWa) | 3 | 32 | 1869 (3×623) | 10 | 53 | 17 | 3 | ✅ |
| Changli (WuWa) | 3 | 34 | 2532 (3×844) | 10 | 53 | 19 | 5 | ❌ |

## Key Technical Details

### FSR 1.0 Spatial Upscaling (Nova backend)
- Two compute shader passes: EASU (Edge-Adaptive Spatial Upsampling) + RCAS (Robust Contrast-Adaptive Sharpening)
- `render/shaders_wgsl/fsr_easu.wgsl` — compute shader, 9-tap edge-aware filter, detects edge direction via luma gradients
- `render/shaders_wgsl/fsr_rcas.wgsl` — compute shader, contrast-adaptive sharpening with luminance-based weight
- Blit pipeline (`BLIT_SRC` inline in `nova.py`) copies rgba16float intermediate → bgra8unorm swap chain (fullscreen triangle, no vertex buffer)
- FSR modes: off (1x), quality (1.3x), balanced (1.5x), performance (2x), ultra performance (3x)
- Render pipeline targets bgra8unorm FSR input texture → EASU → intermediate (rgba16float) → RCAS → output (rgba16float) → blit → swap chain
- UI: combo box "FSR" (Off/Ultra Performance/Performance/Balanced/Quality) + "Output" (720p/1080p)
- Keyboard: Y cycles FSR modes at runtime
- `_FRAME_UBO_SIZE = 672` — shared FrameUBO with rim_light (power, intensity, color) + outline_color

### MToon-style Toon Shading
- Gated by `#define TOON_SHADING` (compile-time), toggled via `app._toon_mode = True/False`
- **3-tone diffuse**: `smoothstep(cutoff ± smoothness, ndl)` produces lit/shade/shade-shade bands
- **Toon specular**: `pow(ndh, shininess)` with cutoff, colored via `toonSpecColor`
- **Rim light**: `pow(1-ndv, rimPower) * rimIntensity * rimTint`
- Uniforms: `toonCutoff`, `toonSmoothness`, `toonShadeShift`, `toonShadeColor`, `rimPower`, `rimIntensity`, `rimTint`, `toonSpecIntensity`, `toonSpecShininess`, `toonSpecCutoff`, `toonSpecColor`
- Defaults: cutoff=0.45, smooth=0.08, shade=(0.3,0.3,0.4), rimPower=3, rimIntensity=0.8, specIntensity=0.5, specShininess=50

### MToon Official Algorithm (Nova backend)
- Ported from UniVRM official HLSL implementation
- `toon_mode == 2u` in `pbr.wgsl`: half-lambert → shading_grade_rate → toon threshold mapping → shade/lit mix → light_color_attenuation → indirect_light(tooned GI) → rim(fresnel_power + lift + lighting_mix) → matcap → SSS
- Per-material MToon properties extracted from VRM `materialProperties` extension
- MeshUBO expanded to 128 bytes with MToon fields (vec4f-first layout for alignment)
- Properties: shade_color, rim_color, shade_toony, shade_shift, light_color_attenuation, indirect_light_intensity, rim_fresnel_power, rim_lift, rim_lighting_mix, outline_width, shading_grade_rate, receive_shadow_rate

### ACES Tone Mapping + Gamma Correction (Nova backend)
- `aces_tonemap()` function in fragment shader: `a = color * (color * 2.51 + 0.03); b = color * (2.43 * color + 0.59) + 0.14`
- `linear_to_srgb()` function: piecewise sRGB conversion
- Applied to all 5 shader modes (PBR, Toon-GG, MToon, Unlit, PS1)
- Unlit/PS1 modes skip ACES, just apply sRGB conversion

### FXAA Anti-Aliasing (Nova backend)
- Fullscreen post-process pass using `fxaa.wgsl` shader
- Luminance-based edge detection with subpixel quality blending
- Reads from scene texture (intermediate when FXAA on without FSR, or FSR RCAS output when FSR+FXAA)
- 32-byte FXAAUBO: screen_size, redu_min(0.04), redu_mul(0.125), span_max(8.0), edge_threshold(0.0625), edge_threshold_min(0.03125)

### LookAt System (Nova backend)
- `Humanoid.apply_look_at(camera_world_pos)` — rotates left/right eye bones to follow camera
- Uses VRM `firstPerson.firstPersonBone` (head) to compute look direction in head-local space
- Extracts yaw/pitch from direction, creates quaternion rotation, applies to eye bones
- Called each frame with actual orbit camera position

### VRM materialProperties Extraction (Nova backend)
- `VrmParser` extracts `materialProperties` from VRM extension
- In `load_model()`, matches VRM material names to glTF materials
- Applies MToon parameters per-mesh: shade_color, shade_toony, rim_color, etc.
- Supports both name-based and index-based matching

### SpringBoneManager
- Read bone positions from `SkeletonSystem._bones[bi].local_matrix[0:3,3]`
- Bone direction from first child (child's local position = direction/length); fallback to local rotation Z axis
- Verlet integration on tail position; `compute_rotation()` aligns rest direction → current tail direction
- Applies rotation to skeleton via `set_bone_rotation()` every frame
- Miku: 50 bones initialized (was 0), quaternions non-identity
- **Collision detection**: VRM sphere colliders parsed from `colliderGroups`, transformed to world space via `SkeletonSystem._world_matrices`, linked per spring bone group via `colliderGroups` indices. Each spring bone's tail position is pushed outside collider spheres after verlet integration. Asaba Seine: 51 bones, 28 colliders.

### VMC Tracking Pipeline
- `VMCUDPHandler` receives UDP packets (port 18081), parses VMC binary protocol
- Packet type 0x0001 → bone transforms (name + pos/rot), stored in `TrackingState.bone_transforms`
- Packet type 0x0010 → blend shape weights (name + float), stored in `TrackingState.blend_shape_weights`
- Thread-safe access via `consume_bone_transforms()` / `consume_blend_shape_weights()` (lock-protected)
- Every frame: `_update_task` reads tracking state → `humanoid.set_bone_rotation()` + `blendshape.set_weight()`
- VRM bone names map directly (VMC uses same `leftUpperArm`, `head`, etc.)

### Humanoid Reverse Mapping
- `SkeletonSystem._index_to_name: dict[int, str]` added (index → glTF node name)
- `Humanoid.set_bone_rotation()` now uses `self._skeleton._index_to_name.get(joint_idx)` — clean reverse lookup
- `set_bone_axis_angle()` also fixed

### GPU Skinning (SkeletonSystem)
- Reads glTF skeleton via pygltflib (supports 113-844 joints per skin)
- **Critical**: glTF matrices column-major → `.transpose(0,2,1)` for inverse bind matrices
- **Y-up to Z-up**: `R = [[1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,1]]`, apply `R * M * R`
- Skinning matrix = `current_world * inv_bind`, packed into RGBA32 float texture (texel per row)
- Vertex shader: `texelFetch(jointData, ivec2(ji, row), 0)` for up to 4 joint influences
- API: `set_bone_rotation(name, qx, qy, qz, qw)` modifies LOCAL matrix; world propagated from hierarchy

### BlendShapeProxy
- Morph column count from `floats.shape[1] // 3` (n_vec3_cols)
- 0 morphs handled gracefully (don't set blink)
- Smoothing: exponential damp `1-exp(-s*dt)` with per-preset smoothing factor

### Outline Pass (Nova)
- Outline pass renders back faces with vertex expansion along normals, weighted by `outlineWidth`
- Solid color output via `outlineColor` uniform
- Defaults: width=0.04, color=black (0,0,0,1)

### Bug Fixes
- **.vrm binary loading**: pygltflib only recognizes `.glb`/`.bin` as binary; `.vrm` falls through to `load_json()` → `UnicodeDecodeError`. Fix: check extension in `skeleton.py`, `vrm/parser.py` and call `load_binary()` for `.vrm`
- **Empty morph targets**: `repair_glb.py` strips `targets: []` from WuWa primitives; auto-repair in `_load_model()`
- **Humanoid lookups**: `set_bone_rotation` used broken inline reverse map; now uses `_index_to_name`
- **WGSL joint texture transpose**: WGSL `texelFetch` returns rows of joint data; `mat4x4f(r0,r1,r2,r3)` constructs column-major from rows → need `transpose()` to get correct skinning matrix. Upload data transposed to `(4,N,4)` layout.
- **WGSL VP matrix transpose**: `view_proj` uniform stored as `view_proj.T` (transpose) because WGSL `mat4x4f` expects column-major memory layout
- **wgpu import order**: `logging.getLogger('wgpu')` must NOT be called before `import wgpu`, or wgpu's `assert isinstance(logger, WGPULogger)` fails because Python caches a generic `Logger` instead of wgpu's custom `WGPULogger`
- **Joint indices as float32**: Pipeline vertex format uses `float32x4` (not `uint32x4`) for joint indices. `.astype(np.float32)` stores uint16 index values as float32 values correctly on GPU (e.g., `1 → 1.0f`). Do NOT use `.view(np.float32)` which reinterprets raw bits.
- **First-frame degenerate triangle**: The first 3 indices `[2,1,0]` in Miku's index buffer form a nearly-zero-area triangle; offscreen pixel readback with full mesh indices confirmed 13,310 non-background pixels rendering correctly

## Backend Architecture
- `render/backends/__init__.py` — `RendererBase` ABC + `@register_backend(name)` decorator + `create_backend()`, auto-imports all `.py` files in directory
- `render/launcher.py` — CLI entry point: `python -m render.launcher --render nova model.glb`
- Shared: `TrackerServer`/`TrackingState`, `SkeletonSystem`, VRM components (`VrmParser`, `Humanoid`, `BlendShapeProxy`, `SpringBoneManager`), `ClothManager`, `VirtualMorphGenerator`

| Backend | Engine | Status | Description |
|---|---|---|---|---|
| `nova` | pygfx + wgpu (D3D12/Vulkan/Metal) | ✅ Primary (sole backend) | pygfx scene graph + wgpu GPU. VRM skeleton, blendshape, springbone, cloth, VMC tracking, MToon official, LookAt, FSR, FXAA, ACES tonemap, 5 shader modes (pbr/cel/taimanin/vtuber/unlit), BVH animation, 6 post-process effects |

## UI Launcher
- `render/launcher_ui.py` — Tkinter GUI wrapper around `launcher.py`
- Tabs: Modelo, Voz/Cam, **Gráficos**, Controles, Expresiones, Optimizar VRM
- Dropdown para seleccionar backend (nova)
- Botón Examinar para buscar modelo .glb/.vrm
- Selector de resolución, checkbox modo Toon
- Lista de modelos recientes (guardados en `.recent_models.txt`)
- Lanza el renderer en un subproceso

### Gráficos Tab
- **Sombreado**: shader mode, toon on/off, cutoff, smoothness, shade shift/toony/color, MToon properties (light attenuation, indirect light, rim fresnel/lift/mix, grade rate)
- **Iluminación**: ambient RGB, main/fill/rim light HPR, IBL intensity/specular/diffuse, hemi sky/ground color + intensity
- **Post-Process**: FXAA, Bloom (threshold/intensity/radius), Color Grading (brightness/contrast/saturation/temperature), TAA, DOF, Motion Blur, SSR, Edge Detect
- **FSR/Upscaling**: FSR mode (Off/Ultra Perf/Perf/Balanced/Quality), sharpness, output resolution, texture quality
- **Outline**: width, color RGBA, min/max distance, normal/depth strength
- **PBR/Avanzado**: rim power/intensity/color, shadow strength/bias, volumetric density/scattering/intensity
- All settings passed via JSON config to launcher.py

## Tools (`render/tools/`)
All tools available via UI (Tools tab in launcher) or CLI.

### `dedup.py` — Deduplicación de vértices
- Preserva morph targets (aplica old2new mapping a cada delta)
- Usa `np.unique` para compactar morph data eficientemente
- Lee datos morph del blob original (`orig`), no del blob modificado
- Blob final: vertex data + morph data + image data
- Limpia buffer views y accessors huérfanos al final

### `copy_blendshapes.py` — Copiar blend shapes entre modelos
- Copia blend shape groups del source al target
- Estrategias de mapeo (en orden): nombre de mesh → fallback índice → fallback primer mesh con morphs
- Soporta VRM 0.x y VRM 1.0 como source
- Los morph targets se mapean por nombre, fallback al mismo índice

### `vrm_convert_to_1.py` — Conversión VRM 0.x → 1.0 vía Blender
- Requiere Blender 5.0+ con VRM Add-on instalado
- Importa VRM 0.x, cambia spec_version a 1.0, exporta VRM 1.0
- Uso: `blender --background --python render/tools/vrm_convert_to_1.py -- input.vrm output.vrm`

## Keyboard Shortcuts (Nova backend)
| Key | Function |
|-----|----------|
| Arrows | Orbit camera |
| Shift+Arrows | Seek motion ±2s |
| Ctrl+Arrows | Seek motion ±1 frame |
| +/- | Zoom in/out |
| Q | Toggle walking mode |
| W/A/S/D | Move model / Walk (when walking mode ON) |
| R | Reset camera |
| G | Chroma key toggle |
| E | Edge detect toggle |
| Z/X | Light heading ±10° |
| C/V | Light pitch ±10° |
| Shift+C | Window crop toggle (circle/rounded square) |
| B | Cycle light intensity (0.5→0.8→1.0→1.3→1.5→2.0) |
| T | Keyboard/mouse overlay |
| Y | Cycle FSR modes |
| F | Cycle FPS (15/30/60) |
| N | Webcam face tracking |
| H | Help overlay (in-HUD shortcuts) |
| [ | Mic lip sync toggle |
| P | Load audio file + lip sync |
| Shift+D | Dance mode toggle |
| M | Load video dance |
| Shift+M | Stop dance + clear motion |
| , | Hide static meshes |
| L | Demand-load remaining textures |
| F1 | Debug overlay |
| F2 | Background toggle |
| F3 | Add accessory PNG |
| F4 | Toggle accessories |
| F5 | Reload current model |
| Shift+F5 | Switch model (dialog) |
| F12 | Screenshot (PNG) |
| I | Load motion file (BVH/JSON/VMC/VMD) |
| U | Play/Pause motion |
| J | Stop motion |
| K | Cycle motion speed (0.25x/0.5x/1x/1.5x/2x) |
| O | OSC output toggle |
| Shift+O | Spout output toggle |
| F6 | Toggle ragdoll mode |
| F7 | Throw item (Shift+F7: cycle item type) |
| F8 | Play emote (Shift+F8: cycle emote) |
| F9 | Cycle room |
| Click-on-head | Head pat |
| 0 | Reset all expressions |
| 1-9 | Expression hotkeys (configurable) |

## Commands
```bash
# UI Launcher (recomendado)
python render/launcher_ui.py

# CLI Launcher
python -m render.launcher --render nova "D:\Vtuber\MODELOS VRM\2859557972043991571.vrm"
python -m render.launcher --list-backends
python render/test_windowed.py "D:\Vtuber\MODELOS VRM\2859557972043991571.vrm"
python render/test_windowed.py --config render_config.json
python render/test_all_models.py
python render/repair_glb.py "D:\Vtuber\MODELOS VRM\4976500629603652360.vrm"

# Standalone tools
python -m render.tools.copy_blendshapes source.vrm target.glb output.glb
blender --background --python render/tools/vrm_convert_to_1.py -- input.vrm output.vrm
```

## Shaders (Nova backend)
| Mode | WGSL file | Description | Status |
|---|---|---|---|
| original | `pbr.wgsl` | PBR Cook-Torrance + toon optional | ✅ |
| cel | `cel.wgsl` | 2-tone cel: `lit=col`, smoothstep cutoff, shade_color shadows | ✅ Working |
| taimanin | `taimanin.wgsl` | 3-tone ramp + SSS + Kajiya-Kay hair + env eye + dual rim + color grading | ✅ Clean rewrite (Jun 16) |
| vtuber | `vtuber.wgsl` | MToon-style toon ramp, hair anisotropic, eye fresnel, rim glow, filmic tone map | ✅ Clean rewrite (Jun 16) |
| unlit | `pbr.wgsl` | Unlit passthrough | ✅ |

### Shader Rules (from cel.wgsl proven pattern)
- **Main diffuse**: `lit = base_color * shade` — NEVER multiply by `frame.light_color.rgb` (darkens 30%)
- **Shadow**: `shade = mix(mesh.shade_color.rgb, vec3f(1.0), cel)` — per-material shade_color tints shadows
- **Transition**: smoothstep(threshold - blur, threshold + blur, half_ndl) — clean anime-style band
- **Specular**: tiny white dot, `pow(NdotH, 40+)`, cutoff at ~0.2-0.3, intensity ~0.18-0.20
- **Rim**: dual layer (pow 2+5), intensity ~0.15+0.35
- **Ambient**: `base_color * frame.ambient * 0.25 * mesh.indirect_light_intensity`
- **Tone mapping**: filmic (ACES-like), slight saturation bump (1.05-1.15x), gamma ~0.92-0.96

### BVH Animation System (Jun 21)
- `BvhAnimation` in `render/vrm/bvh.py`: parses `.bvh` files, samples quaternions + hip position at time `t`
- `VRM_BONE_MAP`: maps 22 standard BVH bone names to VRM bone names (Hips→hips, LeftArm→leftUpperArm, etc.)
- `BvhAnimation.sample(t, [])` returns `{vrm_bone: np.ndarray quat}` + `{@vrm_bone_pos: np.ndarray vec3}` for bones with position channels
- Root motion: hip position channels (Xposition/Yposition/Zposition) now captured and returned as `@hips_pos` — applied via `Humanoid.set_bone_position()`
- `MotionPlayer` in `render/vrm/motion.py`: unified playback for BVH, JSON keyframe, VMC recordings. Now stores VMC position data as `@bone_name_pos` and applies root motion via `apply_to_humanoid`
- Dance mode (M key): `_apply_dance()` uses `_bvh` loaded from config (`dance_path`) if available, falls back to procedural keyframe dance
- Speed: BVH plays at 50% speed (`_dance_time * 0.5`) — adjustable
- No Y-up↔Z-up conversion needed: BVH uses same coordinate system as glTF/VRM (Y-up)
- Hierarchy parser fixed: removed dead JOINT path in `_parse_hierarchy` that assigned parent incorrectly (was always using `self.joints[-2]`)
- `MotionPlayer.apply_to_humanoid` fixed: used `isinstance(val, (list, tuple))` but `BvhAnimation.sample()` returns numpy arrays → now uses `hasattr(val, '__len__')` to handle both types

### Known Issues
- Repeated `_draw first frame` log — `_frame_count` reset each second for FPS counter. Fixed: separate `_first_frame_logged` flag.

### Bugs Found & Fixed (Jun 21)
- **`pbr.wgsl` fragment shader had NO lighting code** — the entire diffuse/specular/rim/tone-mapping was missing. Fragment shader was just sampling base color + matcap + shadows. Added full toon lighting (cel-style), specular (PBR GGX blend with metalness/roughness), rim, ambient, emissive, ACES tonemap, and sRGB gamma correction.
- **`taimanin.wgsl` / `vtuber.wgsl` early return on `toon_mode == 0`** — debug mode `dbg == 0` returned unlit color (early exit), but Python sends `toon_mode = 0` for normal rendering (default). So these shaders were rendering unlit by default. Fixed: early returns only trigger at `toon_mode >= 100` for debug use.
- **Repeated `_draw first frame` log** — `_frame_count` was reset each second for FPS counting, so `if self._frame_count == 0` triggered every second. Fixed: separate `_first_frame_logged` boolean flag.

## Shader Developments (Jun 16)
- Both `taimanin.wgsl` and `vtuber.wgsl` completely rewritten from scratch following cel pattern
- No `light_color` multiplication on diffuse (was darkening everything 30%)
- VTuber: MToon-inspired using `mesh.shade_shift + 0.5` threshold, `shade_toony` controls blur
- Taimanin: 3-tone ramp with `remap_tone()`, SSS wrap, dual Kajiya-Kay hair highlights, dual rim layers
- Both keep hair anisotropic (Kajiya-Kay), eye reflection (env texture), rim glow
- Both use filmic tone mapping + saturation boost at the end

## Next Steps
- [ ] **Test visual** — correr con modelo real para verificar BVH dance + shader fixes

## Skills
Skills provide specialized instructions and workflows for specific tasks.
Use the skill tool to load a skill when a task matches its description.
<available_skills>
  <skill>
    <name>customize-opencode</name>
    <description>Use ONLY when the user is editing or creating opencode's own configuration: opencode.json, opencode.jsonc, files under .opencode/, or files under ~/.config/opencode/. Also use when creating or fixing opencode agents, subagents, skills, plugins, MCP servers, or permission rules. Do not use for the user's own application code, or for any project that is not configuring opencode itself.</description>
    <location>file:///C:/Users/Brad%20Wong/%3Cbuilt-in%3E</location>
  </skill>
</available_skills>
