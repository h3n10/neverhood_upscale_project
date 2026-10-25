# ScummVM Neverhood high-resolution renderer update plan (T24)

**Status: PLAN ONLY.** This is a proposed fork/update plan; no files in `C:\Users\User\git\scummvm` were changed, and no code was built or runtime-tested. Source statements below are marked **Verified** (observed in ScummVM source revision `8ab1cfafb42`) or **Inferred/proposed** (design guidance requiring implementation and validation). This plan does not establish original-game high-resolution support.

## Goal and recommended design

Add a game-specific ScummVM display/render option that presents Neverhood's 640x480 game world using a selected render/output target, and uses matching high-resolution resources where available. Keep scripts, scenes, sprite positions, input, hit/collision rectangles and save state in the unchanged 640x480 logical coordinate system. Fit the 4:3 game image to the selected display with centered pillar/letterboxing. Preserve the stock resource and render path as the fallback.

**Verified baseline:** `NeverhoodEngine::run()` calls `initGraphics(640, 480)`; `Screen::Screen()` creates a 640x480 CLUT8 buffer and dirty-tile tracker; `GameModule::handleMouseMove/Down/Up()` forwards coordinates; sprite/animation metadata and collision logic use game-space values. Source map: `knowledge/engine_source.md` and `knowledge/upscaled_assets_feasibility.md`, with file/function citations below.

**Recommendation (proposed):** retain a fixed 640x480 *logical* world and introduce a resolution-aware compositor/output surface. Do not merely change `initGraphics()` to a larger number and let resources interpret that as game coordinates. The selected dimensions should configure a high-resolution render target/active viewport; ScummVM's backend may separately choose or scale to the physical display. Verify the relevant OSystem/backend contract on desktop and Android before finalizing this boundary. Keep every existing logical draw/input API stable where possible, and add explicit logical-to-output and output-to-logical transforms.

## User-selectable targets and geometry

In the Neverhood game options provide a **Render resolution** popup with:

| Choice | Requested display canvas | 4:3 active viewport / resource tier example |
|---|---:|---:|
| Original | 640x480 | 640x480; use original resources |
| 1080p | 1920x1080 | 1440x1080; 4.5x 320x240 = 1440x1080 |
| 1440p | 2560x1440 | 1920x1440; 6x 320x240 = 1920x1440 |
| 4K | 3840x2160 | 2880x2160; 9x 320x240 = 2880x2160 |
| Device preset | e.g. OnePlus 11 3216x1440 | centered 1920x1440 4:3 viewport (648-pixel side bars) |
| Custom | user width x height | fit the 4:3 viewport to the canvas, centered; validate dimensions and aspect |

The 16:9 sizes are *display canvases*, not the dimensions of the 4:3 game image. For an arbitrary canvas, set `viewportScale = min(canvasWidth / 640, canvasHeight / 480)`, center the resulting 4:3 viewport, and keep bars outside game content. On devices that cannot set a physical mode, treat the choice as the requested render canvas and let the backend scale/composite it to the actual display; report/fallback cleanly rather than pretending the device switched modes. Android rotation, insets, display changes and safe areas need device testing.

Map pointer coordinates from display space through the viewport offset/scale back to the 640x480 logical space *before* the existing game-module handlers. Clamp/reject touches in the bars. Do not change scene scripts, puzzle constants, Klaymen hit tests, or animation timing to match target pixel size.

## Resource tiers, manifest and fallback

Use a sidecar hi-res resource package rather than replacing production BLB resources. The existing NHC mechanism is a hash/type replacement overlay, not a loose-image scale layer; it still enters current parsers. A new indexed archive (working name `.nhres`; extension/version are open to implementation) can coexist with unchanged BLBs and NHC files. Index each variant by resource hash, original type, tier and checksum. Look up a compatible hi-res record first; if absent, malformed, too large, or rejected by a format/palette check, load the exact original resource. Preserve existing alias/hash resolution semantics.

Manifest fields required per variant:

- archive/resource hash and type; original BLB identity/index for traceability; original payload checksum;
- logical size and logical draw/collision rectangle (640x480 coordinate units); source raster size, replacement raster size and explicit X/Y scale; anchor/pivot and any frame/offset mapping;
- tier (4.5x, 6x, 9x or declared custom), pixel format, alpha/transparency convention, palette behavior/version, codec/container for video;
- frame count, cadence/timing, animation frame ids and source mapping; audio/subtitle linkage where applicable;
- replacement checksum, encoder/upscaler provenance and QA disposition.

Resource tiers are per resource, not an assumption that every input is 320x240. The specified example maps a 320x240 source to 1440x1080, 1920x1440 or 2880x2160 for the three tiers. Preserve the declared logical footprint independently of replacement pixels; never derive collision geometry by dividing a replacement's raster dimensions. For 640x480 sources and smaller sprites, use the same tier factor proportionally only when the artist/manifest explicitly confirms correspondence. Select the lowest tier that meets the active viewport's sampling demand; allow a higher tier to be downsampled when supported, but do not enlarge low-tier/replacement assets past the approved fallback path. If only originals exist, keep their behavior and scale the final composition.

**Package proposal:** a versioned header plus manifest and independently seekable resource blobs, keyed by hash/type/tier; validate bounds, dimensions, hash uniqueness, CRC/SHA and declared sizes at load. Keep the package external under `DATA_upscaled/` (mirror the game-data structure) while the engine format is experimental. Do not put MKV/PNG files directly into legacy BLBs. ANL should propose archive writer/reader feasibility and a concrete schema before engine coding.

## Render pipeline: sprites, animations, palette, alpha and video

1. **Static resources and sprites:** decode source type-2 indexed graphics as today. For high-resolution variants, retain raster size separately from their logical draw rectangle/position. Apply the logical-to-output transform at composition, with overflow-safe clipping. Verify static sprite offsets, layer priority, Y filtering and drawing of resource surfaces larger than their logical footprint.
2. **Animations:** keep frame IDs, counters, delays, draw offsets, deltaX/Y and collision bounds as logical metadata. The manifest maps each original frame to its high-resolution counterpart; scale only pixel sampling and any explicitly-raster-space effect. Missing frames fall back individually. Never scale animation collision or movement data.
3. **CLUT8 to true color:** retain the indexed 640x480 compatibility path. For the new path, resolve each index through the *current* 256-entry palette during conversion/composition into an RGB(A) target. Palette changes must invalidate dependent cached colors/dirty tiles. Alpha is explicit and independent of index 0; preserve original transparent-index/alpha-key rules, and use premultiplied or straight alpha consistently. True-colour replacements need an explicit palette policy: either an index-corresponding variant for resources with dynamic palette changes, or approved baked RGB(A) with tested palette-transition behavior. Do not silently discard palette transitions or infer transparency from black. Original CLUT8 resources remain the guaranteed fallback.
4. **Smacker video:** current Neverhood playback uses `NeverhoodSmackerDecoder`, `SmackerPlayer::updateFrame()` and `SmackerSurface::setSmackerFrame()`; normal video submits the decoded frame to the 640x480 screen, and the special doubled path writes 2x2 pixels directly. A high-resolution path must use dimension-aware safe composition, dynamic palette handling, preserved exact frame timing/count and original audio sync; remove/guard the double-surface shortcut for enlarged input. Subtitle/caption placement must stay logical and scale only at output.

**Video format proposal:** keep untouched original SMK streams as fallback and decode them with ScummVM's existing `Video::SmackerDecoder`. Keep a lossless FFV1/Matroska master in project working storage (per `knowledge/video_conversion.md`), but do **not** assume ScummVM can play that master. ScummVM has an MKV decoder guarded by `USE_VPX` (`video/mkv_decoder.h` identifies VPX video and Vorbis audio tracks); the candidate runtime sidecar is VP9/WebM-in-MKV only after confirming codec/profile/build availability and syncing it through a generic decoder path. **Verified scope:** the Neverhood player currently hardcodes its Smacker decoder; the MKV decoder is conditional and VPX-based. **Not verified:** FFV1 runtime support, a Neverhood MKV integration, high-resolution decode limits, VP9 alpha, or mobile performance. Do not place an MKV in a resource slot expected to contain SMK. VID should deliver a source-faithful, timed, reviewed runtime candidate plus lossless master and metadata; ANL must preserve original audio/cadence or document and test a replacement audio link. If a compatible ScummVM codec/build is unavailable, fall back to original SMK at the higher output scale.

## Config and GUI integration (proposal)

Use `NeverhoodOptionsWidget` as the game-specific UI hook: it already builds controls, defines a layout, and reads/writes target-scoped `ConfMan` values. Add a popup for `Original / 1080p / 1440p / 4K / Device / Custom`, plus numeric width/height controls enabled only for Custom. Add validation/help text, preview current effective output, and an Apply/restart notice if the backend cannot switch safely while running.

Proposed config keys (new; not existing):

- `nh_render_resolution` = `original|1080p|1440p|4k|device|custom`;
- `nh_custom_width`, `nh_custom_height` (bounded positive dimensions; avoid allocation overflow);
- `nh_asset_tier` = `auto|original|4.5x|6x|9x` (default `auto`); optional `nh_resource_pack` path/identifier;
- optionally `nh_render_backend` only if multiple renderer implementations remain exposed; avoid duplicating ScummVM global scaler settings.

Store target options via `ConfMan`; specify stable defaults and migrate missing/unknown values to `original`/`auto`. Set up UI with the existing options container/layout/load/save pattern; whether resolution changes require engine restart or can request a backend mode transaction is a test decision. Check default config generation and localization for the GUI labels.

## Backend, dirty rectangles, mobile and memory

- **Backend boundary:** `NeverhoodEngine::run()` currently calls `initGraphics(640,480)` and calls `copyRectToScreen()` from `Screen::update()`. Determine whether to keep that logical API and submit a high-res compositor surface, or set an output-sized engine surface and inverse-map input explicitly. Prefer backend-neutral ScummVM graphics/surface facilities over direct platform APIs. Treat physical mode selection as best-effort; `initGraphics()` size alone must not be assumed to change a phone's native resolution. Desktop and Android implementations may differ.
- **Dirty rectangles/performance:** keep dirty tracking in logical tiles; transform dirty rect edges to the output target, expand for filtering, coalesce adjacent rects, and force a full refresh for palette-wide invalidation, viewport changes and video frames as needed. Avoid resampling the entire 4K canvas for each small sprite update. Benchmark scenes, cursor, scrolling, palette transitions and full-motion video. Enable fast paths for unchanged/original assets and nearest/bilinear sampling selected to preserve clay texture; avoid smoothing transparent edges.
- **Approximate RGBA working memory (uncompressed):** a 3840x2160 surface is 31.6 MiB; two are 63.3 MiB. A 2880x2160 4:3 target is 23.7 MiB; two are 47.5 MiB. A 3216x1440 target is 17.7 MiB; two are 35.3 MiB. Add video decode frames, textures, cache and backend copies to these values. Proposed initial budgets: cap extra decoded-resource cache at 32 MiB on mobile / 128 MiB desktop, keep output surfaces to two buffers where possible, decode video incrementally, and evict with an LRU. Treat the total as a starting budget to profile, not guaranteed device capacity. On allocation failure or sustained frame drops, reduce cache/tier or fall back to original assets without changing gameplay.
- **Mobile:** query actual drawable resolution and orientation, keep 4:3 content centered in ultra-wide displays, ensure touch transforms account for system insets, and provide a low-memory mode (original/6x tier, small cache, no extra frame queue). Avoid forcing 4K decode on a 1440-pixel-high device. Record temperature/frame-time and battery impact in performance tests.

## Save compatibility

Keep save-game serialization exclusively in logical/game state. Do not write render resolution, resource tier, physical viewport or high-resolution pixel data into save slots. Store preferences in target config. Preserve the existing save header, game-state serialization and thumbnail compatibility; if thumbnails are ever rendered high-resolution, downsample or retain the legacy size on save and continue accepting existing saves. Test old saves at every new render target and new saves at `Original`; resolution changes must not affect gameplay state or module transitions.

## Testing and acceptance plan

1. **Resource/parser tests:** validate package manifest/version, malformed/truncated entries, unknown tiers, duplicate hashes, hash aliases, exact original fallback, CRC mismatch, per-resource absence, and safe size/overflow limits. Compare legacy BLB/NHC behavior unchanged.
2. **Geometry tests:** fixed 640x480 logical assertions; transforms at 640x480, 1080p, 1440p, 4K, 3216x1440 and odd custom dimensions; bars reject clicks; content pixel maps to the correct original coordinate; hitboxes, navigation, collision, UI, cursor, subtitles and scene Y-offsets remain aligned.
3. **Graphics tests:** static background/sprite and animated Klaymen across all tiers; animation frame/offset/movement/collision/timing parity; palette swaps and transparency; edge clipping; source/high-res/original fallback comparison; full refresh after palette update.
4. **Video tests:** original SMK and candidate sidecar with frame count, cadence, palette/colour, audio sync, seek/rewind and subtitles; compare consecutive frames; test 320x200/320x240/448x240 originals and target high-res sizes; assert bounds for the prior double path. Fail or disable sidecar if codec support is absent.
5. **Backend/mobile tests:** software and supported accelerated desktop backends; Android native 3216x1440/device viewport, rotation, insets, suspend/resume and external display where available. Measure FPS/frame time, allocations, cache peak and thermal behavior in representative static, scrolling, animation and full-video scenes.
6. **Save/regression:** load pre-change saves, play/save/load at each resolution, return to Original and compare state; verify unchanged input, startup, menus, scene transitions and screenshots against the 640x480 baseline.

Acceptance: zero logical-coordinate or save regressions; exact fallback to current original resources when hi-res data/codec is unavailable; stable frame timing; no out-of-bounds writes; palette/transparency checks pass; requested output fits with no distortion; performance/memory meet agreed platform thresholds.

## Milestones and effort (engineering estimate)

| Milestone | Scope / exit | Effort |
|---|---|---:|
| M0 — architecture and backend spike | Confirm OSystem/backend sizing and input mapping on desktop + Android; prototype 4:3 output viewport; decide output-surface API | 2–4 engineer-days |
| M1 — logical/render separation | Output transform, input inverse transform, clipping, high-resolution composition and dirty-region tests; original path unchanged | 5–8 days |
| M2 — manifest/package + static resources | Agree schema with ANL; loader/cache/fallback; static backgrounds/sprites; validation tests | 4–7 days |
| M3 — animation and palette | Frame mappings, palette-to-RGBA, alpha and palette invalidation; representative character tests | 4–7 days |
| M4 — video and GUI | Resolution options/config, generic video selection or a tested supported format, subtitles/audio/cadence | 4–7 days |
| M5 — device/performance/save QA | Android/desktop test matrix, memory/perf tuning, regression and documentation/sign-off | 4–8 days |

**Total preliminary engineering estimate: 23–41 engineer-days**, not including asset production/review, upstream review time, platform porting surprises or a new decoder. M0 is a go/no-go milestone; if backend constraints undermine mobile support, reduce scope to presentation scaling plus optional desktop render targets.

## Risks and cheaper route

- **High risk:** extensive hidden fixed-size assumptions beyond the sampled engine paths; high-res buffer/OOM cost; 9x-upscaled art or palette conversion may change intentional texture/color; video decoder availability differs by build; Android backend may not permit arbitrary mode changes; large cache/CPU scaling can throttle mobile. Mitigate with M0 prototype, original fallback, per-resource tiers, low-memory mode, and no broad rollout before scene-level QA.
- **Asset risk:** existing NHC does not express independent logical size/scale. Keep new replacements in an opt-in package until parser/schema and runtime round-trip tests pass. Do not alter `DATA_source/` or ship unreviewed outputs.
- **Cheaper alternative:** no engine renderer fork. Keep the 640x480 CLUT8 engine and original assets; expose/recommend ScummVM's existing backend scaler/aspect controls (or add a simple preset selector that only selects presentation scaling). This achieves larger display output and preserves saves/input/palettes/video at low cost, but it only enlarges existing pixels and does not use the 9x assets. A slightly larger step is to add only a high-resolution static-image overlay path while retaining original animations/video, but it still incurs the package and palette/geometry risks and is not recommended as the first implementation.

## Required ANL / VID deliverables before implementation

**ANL:** propose and document `.nhres` (or alternate) package/index schema; resource hash/type mapping; per-resource logical footprint vs raster size; original payload checksum and fallback rule; frame/offset/timing/collision metadata association; palette/alpha semantics; runtime lookup order; reader/writer and validation test plan; representative original fallback fixtures. Do not edit `DATA_source/`.

**VID:** opt-in high-resolution static backgrounds/sprites/animation frames and video candidates; source-to-output mapping with measured dimensions and tier; transparent alpha separate from RGB, palette mapping/transition behavior (or explicit baked-color limitation); animation frame correspondence and unchanged cadence; lossless FFV1/Matroska masters plus any proposed ScummVM-playable VP9/WebM runtime sidecar; audio/subtitle/timing metadata; checksums and QA disposition/report. A runtime codec candidate is not approved until built-in decoder/build availability and frame/audio sync are verified. Follow `knowledge/qa_process.md` and its independent-review triggers.

## Open questions for the user / manager

1. Should the first release target Desktop only, or must Android be an acceptance platform from day one?
2. Is the custom renderer/fork acceptable at the estimated 23–41 engineering days, or is presentation scaling the preferred near-term deliverable?
3. For “4K,” should the selector mean 3840x2160 display canvas with 2880x2160 4:3 image (recommended), or a 2880x2160 4:3 render target reported as the mode?
4. Should device presets be manually listed (e.g. OnePlus 11), detected from actual drawable dimensions, or both? Should custom dimensions be editable in the in-game options UI or only configuration?
5. Which Android mobile memory/FPS/thermal thresholds and minimum supported devices should gate release?
6. Can any runtime video sidecar use VP9 lossy compression, or must cutscenes remain original SMK until a proven compatible lossless format is available?
7. Who approves artistically reconstructed detail and palette behavior before ANL receives VID assets?
8. Should resource variants live only in external `DATA_upscaled/` development data initially, or is a versioned optional package intended for end users after QA?

## Source references (verified scope)

All paths below are within ScummVM revision `8ab1cfafb42`; source tree not modified.

- `engines/neverhood/neverhood.cpp`: `NeverhoodEngine::run` (`initGraphics(640, 480)` and resource setup), `mainLoop` (input/update/present flow).
- `engines/neverhood/screen.cpp`: `Screen::Screen` (640x480 CLUT8/dirty tiles), `Screen::update`, `updatePalette`, `drawSurface2`, `drawDoubleSurface2`.
- `engines/neverhood/graphics.cpp`: `BaseSurface::BaseSurface`, `BaseSurface::draw`, `parseBitmapResource`, `unpackSpriteNormal`, `unpackSpriteRle`.
- `engines/neverhood/resource.cpp`: `SpriteResource::load`, `AnimResource::load/draw`, `DataResource::getMessageListAtPos`.
- `engines/neverhood/sprite.cpp`: `StaticSprite::loadSprite`, `Sprite::updateBounds/isPointInside`, `AnimatedSprite::createSurface1/updateFrameInfo/updatePosition`.
- `engines/neverhood/gamemodule.cpp`: `GameModule::handleMouseMove/handleMouseDown/handleMouseUp`.
- `engines/neverhood/resourceman.cpp`, `blbarchive.cpp`, `nhcarchive.h/.cpp`: hash lookup, alias/BLB and NHC replacement behavior.
- `engines/neverhood/dialogs.cpp`: `NeverhoodOptionsWidget` constructor, `defineLayout`, `load`, `save` (existing config/GUI extension pattern); `engines/neverhood/metaengine.cpp`: `buildEngineOptionsWidget` hook.
- `engines/neverhood/smackerplayer.cpp`: `SmackerPlayer::open/updateFrame`, `SmackerSurface::setSmackerFrame/draw`, `SmackerDoubleSurface::draw`; `video/smk_decoder.cpp` and `engines/neverhood/smackerplayer.h`: Smacker decoder types.
- `video/mkv_decoder.h`: `Video::MKVDecoder` is guarded by `USE_VPX` and declares VPX video/Vorbis audio tracks. `common/system.h`: OSystem graphics mode/features; backend physical-resolution behavior remains to be established for each target.
- Project evidence/docs: `knowledge/engine_source.md`, `knowledge/upscaled_assets_feasibility.md`, `knowledge/animation_upscaling_rules.md`, `knowledge/video_conversion.md`, `knowledge/qa_process.md`.
