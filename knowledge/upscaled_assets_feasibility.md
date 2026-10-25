# Feasibility of upscaled assets in ScummVM Neverhood (T23)

## Executive recommendation

**Do not place the current 9x/upscaled outputs into production BLBs or NHC overrides.** Stock ScummVM's Neverhood implementation initializes a 640x480 screen and CLUT8 backbuffer; it composites sprites and regular Smacker frames in those coordinates. A larger decoded frame can be accepted by parts of the parser/surface setup, but this does not scale game-space positions, UI, hit/collision rectangles, or the final backbuffer. Use stock ScummVM's presentation scaling for now, and keep enlarged replacements outside runtime data until an engine fork with an explicit logical-to-pixel model exists. For actual source-detail recovery, the recommended next technical route is a narrowly scoped high-resolution renderer fork, preserving the 640x480 gameplay coordinate system.

This is a source feasibility assessment only. There is no patched build, asset round-trip, or runtime validation; recommendation is verified/inferred as labelled below.

## Options, constraints and failure modes

### 1. Stock engine presentation scaling (recommended interim)

Retain original 640x480 resources and let the ScummVM backend scale the game output to the display. **Verified:** this Neverhood engine feeds its 640x480 game screen to the system; its source does not decode larger replacement art and scale it into that game screen. This is the least risky compatibility path and keeps object positions, menus, palettes, video cadence and hit regions intact. **Trade-off:** the enlarged display is filtered/repeated original pixels, not new resolution/detail from 9x replacements. Backend scaler behavior depends on the ScummVM graphics backend/settings and is outside the Neverhood engine source reviewed here.

### 2. Replace BLB resources with larger bitmap/animation/video frames, without engine changes

**Technically parseable in some paths, but not an HD-assets solution; reject for production.** `parseBitmapResource()` accepts encoded dimensions; standalone `StaticSprite::loadSprite()` can allocate a surface from parsed dimensions. But its positions remain source/game coordinates and `Screen` still clips to 640x480. `BaseSurface::drawSpriteResourceEx()` draws only if resource dimensions fit its surface; animations use the dimensions returned by `AnimResource::loadSpriteDimensions()` while frame `drawOffset`, `deltaX/Y`, `collisionBoundsOffset`, counters, and frame data remain separate. Larger images can therefore occupy too much of the old scene, hit adjacent objects, clip, or fail surface-fit conditions; a visually expanded object does not expand `DataResource`/static-data hit regions or gameplay geometry. This is an inference about likely outcomes from the verified call paths; no enlarged resource was run.

Video is especially unsafe as a blanket substitution: normal Smacker surfaces use decoded source dimensions and clip into the 640x480 screen, so oversized content would be cropped. The special double-surface path writes each pixel as a 2x2 block directly into the backbuffer without bounds clipping. Replacing its expected-sized streams with larger frames risks out-of-bounds writes. It is not a safe generic upscale route.

Even when a replacement stays within the raster area, indexed pixels/palette matter: type-2 images carry palette indexes, optional 1,024-byte palettes, and normal/RLE forms; palette changes are dynamic. RGB-only artwork or a regenerated palette can recolor shared indices, transparency (index 0 / configured transparent key), or Smacker frames. Animation record metadata must stay consistent with every frame.

### 3. External-file override layer

There is a limited existing resource override mechanism: ScummVM can load a configured `.nhc` archive. `NhcArchiveEntry::isNormal()` defines types 0-10 as same-hash resource replacements; other special entries are for subtitles/font/messages. This is **not** a general loose PNG/JPEG replacement layer, does not create a draw scale factor, and still feeds replacements into the same type-specific parsers, palette rules, geometry, and 640x480 compositor. It may be useful for controlled, same-format replacement experiments after a valid NHC writer/runtime test, not as a high-resolution solution. The `.nhc` behavior is verified in source; file creation/round-trip and use for high-resolution imagery were not tested.

### 4. Patch the engine with a high-resolution render path

This is the feasible way to display genuinely enlarged assets while retaining gameplay logic, but it is a nontrivial fork, not a data-only change. Define a fixed scale factor `S` for render pixels and preserve all game logic in 640x480 coordinates. Every resource must declare/map logical geometry independently of its pixel dimensions. Render sprites and video at `S` pixels per logical coordinate, while keeping entity positions, mouse input, collision rectangles, hit tests, navigation, module/puzzle data, and timing in logical units. A 9x output for a 320x240 source is 2880x2160 (4:3); choose a consistent mapping for original 640x480 content as well, avoid treating a 9x asset as 9x logical size, and pillarbox 4:3 presentation as the selected display mode requires.

## Minimal patch list (planning estimate; not applied)

1. Add explicit logical-size / scale metadata and a resource mapping for high-resolution replacements (including static type-2 bitmaps, animation frames, and optional Smacker assets). Do not infer logical size by dividing dimensions without a defined rule.
2. Separate source pixel dimensions from logical `NDrawRect`/sprite geometry in `SpriteResource`, `AnimResource`, `BaseSurface`, `StaticSprite`, and `AnimatedSprite`. Preserve original offsets, movement deltas, collision bounds and frame counters as logical values; rasterize the replacement at `S`.
3. Replace or extend `Screen`'s fixed 640x480 backbuffer, dirty-tile tracker, clip rectangles, render queue, copy/presentation path to support scaled pixel surfaces; use overflow-safe clipping. Alternatively use a high-res render target and a well-defined final compositor. Ensure transparency, alpha-key, palette conversion and dirty rectangles operate at the appropriate resolution.
4. Keep event coordinates in logical space (or explicitly inverse-map high-res output coordinates before the existing `GameModule`/scene hit tests). Audit UI/menu constants, fonts, subtitle placement, mouse cursor, clips, scene Y offsets and all hard-coded 320/240/640/480 values.
5. Implement the distinct Smacker path deliberately: dimension-aware placement, high-resolution frame draw/composition, palette updates, subtitle sizing/coordinates, and remove or bounds-check the current raw 2x `drawDoubleSurface2()` route for high-resolution inputs. Keep SMK timing/audio synchronization intact.
6. Add tests for parser round-trip (palette/index/RLE/animation metadata), clipping and source/destination bounds, mouse/collision alignment, dynamic palette changes, normal and double-surface SMK playback, menu/subtitles, scene transitions/save-load, and 4:3 output/pillarboxing. Run QA on a representative static sprite, animated character and video before broad adoption.

## Evidence ledger

**Verified in inspected ScummVM source:** `NeverhoodEngine::run()` calls `initGraphics(640,480)`; `Screen::Screen()` creates a 640x480 CLUT8 backbuffer and dirty tile array; `BaseSurface` defaults to a 640x480 clip; resource pixels use indexed 8-bit palette data; animation records carry draw/motion/collision/timing fields; `GameModule` passes mouse event coordinates unchanged; regular `Screen::drawSurface2()` clips/composites without scaling; NHC override is hash-based and type-specific; Smacker double drawing is a 2x2 write into the fixed backbuffer.

**Inferred from these verified paths:** larger source resources alone are not a general high-res feature; old-coordinate hitboxes and geometry become misaligned when the artwork is actually rendered larger; replacing high-resolution streams on the double-surface path may write outside the backbuffer; a custom rendering/coordinate split is needed for a robust scalable-asset system. These have not been demonstrated by running a modified build.

## Source citations

- `C:\Users\User\git\scummvm\engines\neverhood\neverhood.cpp`: `NeverhoodEngine::run`, `mainLoop`
- `...\screen.cpp`: `Screen::Screen`, `drawSurface2`, `drawDoubleSurface2`, `update`, `updatePalette`
- `...\graphics.cpp`: `BaseSurface::BaseSurface`, `drawSpriteResourceEx`, `parseBitmapResource`, `unpackSpriteNormal`, `unpackSpriteRle`
- `...\resource.cpp`: `SpriteResource::load`, `AnimResource::load`, `AnimResource::draw`, `DataResource::getMessageListAtPos`
- `...\sprite.cpp`: `StaticSprite::loadSprite`, `StaticSprite::updatePosition`, `Sprite::updateBounds`, `AnimatedSprite::createSurface1`, `updateFrameInfo`, `updatePosition`
- `...\gamemodule.cpp`: `handleMouseMove`, `handleMouseDown`, `handleMouseUp`
- `...\resourceman.cpp`, `nhcarchive.h/.cpp`: `addNhcArchive`, `loadResource`, `NhcArchiveEntry::isNormal`
- `...\smackerplayer.cpp`: `SmackerPlayer::open`, `updateFrame`, `SmackerSurface::setSmackerFrame/draw`, `SmackerDoubleSurface::draw`
