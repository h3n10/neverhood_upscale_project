# ScummVM Neverhood engine source review (T23)

Reviewed read-only from `C:\Users\User\git\scummvm\engines\neverhood` at ScummVM revision `8ab1cfafb42` on 2026-10-25. This documents the inspected ScummVM implementation, not the original 1996 executable. The ScummVM tree and `DATA_source/` were not modified. No build, runtime patch, or replacement-asset test was performed.

## Runtime lifecycle and fixed logical screen

- `NeverhoodEngine::run()` in `neverhood.cpp` calls `initGraphics(640, 480)`, constructs `Screen`, `ResourceMan`, `SoundMan`, and `GameModule`, then starts the game. Full game mode registers `a.blb`, `c.blb`, `hd.blb`, `i.blb`, optional `m.blb` (optional for Japanese), `s.blb`, and `t.blb`; demo mode instead uses `a.blb` and `nevdemo.blb`.
- `NeverhoodEngine::mainLoop()` polls input and sends mouse event x/y directly to `GameModule`; on each frame it checks module requests, updates, draws, updates `Screen`, services sound, and presents. There is no Neverhood-engine level coordinate-scale conversion in this path.
- `GameModule::createModule()` selects concrete modules; modules own scene/entity flow. `Scene` sets a 24 FPS default, owns/sorts entities and surfaces by priority, and `Scene::draw()` draws the active Smacker surface or all registered surfaces. `Entity::handleUpdate()` and `Entity::receiveMessage()` dispatch the callback-driven update/message handlers. Sources: `neverhood.cpp` (`run`, `mainLoop`), `gamemodule.cpp` (`handleMouseMove`, `handleMouseDown`, `createModule`, `checkRequests`), `scene.cpp` (`Scene`, `draw`, `addEntity`, `addSurface`), `entity.cpp` (`handleUpdate`, `receiveMessage`).

## Screen, surfaces, clipping, and coordinates

- `Screen::Screen()` creates a 640x480 CLUT8 `_backScreen` and 640x480 dirty-tile tracker. `Screen::update()` copies changed rectangles to the system screen, or copies the full 640x480 buffer on `_fullRefresh`. The engine screen is not a larger hidden canvas.
- `BaseSurface::BaseSurface()` makes a CLUT8 surface sized from its supplied width/height (horizontal pitch aligned to 4) and defaults its clip rect to `(0,0)-(640,480)`. `BaseSurface::draw()` routes through `Screen::drawSurface2`, `drawUnk`, or clip-list drawing. `Screen::drawSurface2/3`, `queueBlit`, and `blitRenderItem` clip/composite at pixel coordinates; no general scale factor is applied.
- `Screen::updatePalette()` converts 256 entries from four-byte palette records to 768 RGB bytes and installs the palette. In `blitRenderItem()`, transparent index 0 is skipped (or a configured alpha color); surfaces are indexed pixels, not RGBA.
- `StaticSprite::loadSprite()` reads resource dimensions/position, creates its surface from those dimensions when needed, and uses them as draw-offset dimensions. `Sprite::updateBounds()` computes collision bounds from `_x/_y` and collision offsets; `Sprite::isPointInside()` tests these coordinate-space bounds. `AnimatedSprite::createSurface1()` sizes its surface from `AnimResource::loadSpriteDimensions()`; `AnimatedSprite::updateFrameInfo()` applies per-frame draw offsets, deltas, collision bounds, and timing; `updatePosition()` places the surface in the same screen coordinate space. `filterY` only subtracts the current screen Y offset (`Sprite::defFilterY`).
- `DataResource::getMessageListAtPos()` tests Klaymen and mouse coordinates against stored rectangles; `Scene`/sprite collision and mouse code therefore consume game-space coordinates. `GameModule::handleMouseMove/down/up()` passes the event positions through unchanged.

Sources: `screen.cpp` (`Screen`, `update`, `updatePalette`, `drawSurface2`, `drawSurface3`, `queueBlit`, `blitRenderItem`); `graphics.cpp` (`BaseSurface`, `parseBitmapResource`); `sprite.cpp` (`StaticSprite::loadSprite`, `StaticSprite::updatePosition`, `Sprite::updateBounds`, `AnimatedSprite::createSurface1`, `AnimatedSprite::updateFrameInfo`, `AnimatedSprite::updatePosition`); `resource.cpp` (`DataResource::getMessageListAtPos`).

## Resource lookup and parsed layouts

- `BlbArchive::open()` checks signature `0x02004940`, version 7, and declared length; it loads ordered hashes, records and shared extended data. `BlbArchive::load()` handles outer compression 1 (stored) and 3 (DCL), and errors on other compression identifiers. `createStream()` returns a bounded stream over stored bytes.
- `ResourceMan::addArchive()` indexes resources by 32-bit hash; on a duplicate hash it selects a record with newer timestamp. `findEntry()` follows compression `0x65` aliases by treating `diskSize` as the next hash. `queryResource()` preserves the first alias record's ext-data pointer. `loadResource()` loads NHC normal overrides where present, otherwise the selected BLB payload; resource bytes are cached/refcounted.
- An NHC file is an existing optional overlay, not an arbitrary loose-PNG search path. `NeverhoodEngine::run()` conditionally loads the configured `<nhc_file>.nhc`. `NhcArchiveEntry::isNormal()` treats types 0-10 as replacements keyed by matching resource hash; custom types 11/12 serve font/messages and type 13 attaches subtitles to a video. Replacement resources still enter existing resource parsers and draw code.
- `parseBitmapResource()` reads flags, optional uint16 width/height, optional position, optional 1,024-byte palette, and pixel pointer. `SpriteResource::load()` loads type 2; `unpackSpriteNormal()` expects rows padded to 4 bytes and `unpackSpriteRle()` decodes row/chunk commands. It does not scale image pixels.
- `AnimResource::load()` parses animation frame records: frame hash, counter, draw rect, movement deltas, collision rect, and sprite-data offset. `AnimResource::draw()` unpacks frame RLE pixels. Altering frame dimensions alone does not rewrite associated placement, movement, timing, or collision values.

Sources: `blbarchive.cpp` (`open`, `load`, `createStream`); `resourceman.cpp` (`addArchive`, `addNhcArchive`, `findEntry`, `queryResource`, `loadResource`); `nhcarchive.h` (`NhcArchiveEntry::isNormal`), `nhcarchive.cpp` (`open`); `graphics.cpp` (`parseBitmapResource`, `unpackSpriteNormal`, `unpackSpriteRle`); `resource.cpp` (`SpriteResource::load`, `AnimResource::load`, `AnimResource::draw`).

## Smacker and sound paths

- `SmackerPlayer::open()` obtains a resource-hash stream and loads it with `NeverhoodSmackerDecoder`; `updateFrame()` uses the decoder's frame and palette. `SmackerSurface::setSmackerFrame()` adopts the decoded frame width/height and normal drawing submits those dimensions to `Screen::drawSurface2`, whose clipping canvas is 640x480. Default placement centers relative to 640x480.
- `SmackerDoubleSurface::draw()` uses `Screen::drawDoubleSurface2()`. That function writes each decoded source pixel into a 2x2 block in the 640x480 backbuffer, without clipping/guard logic. `SmackerPlayer::updateFrame()` positions this path relative to 320x240. This special path is not a general high-resolution video renderer and is unsafe to assume for larger frames.
- Video palettes are copied from the Smacker decoder into the current palette. Subtitle positions/widths also contain 320/640/480-oriented constants (`SmackerPlayer::open`, `SmackerSurface::draw`).
- `AudioResourceManSoundItem::playSound()` makes a stream at 22,050 Hz, using resource ext-data for differential 8-bit shift or raw 16-bit samples; this audio path is independent of graphics scaling.

Sources: `smackerplayer.cpp` (`SmackerPlayer::open`, `updateFrame`, `updatePalette`, `SmackerSurface::setSmackerFrame`, `SmackerSurface::draw`, `SmackerDoubleSurface::draw`); `screen.cpp` (`drawDoubleSurface2`); `sound.cpp` (`NeverhoodAudioStream::readBuffer`, `AudioResourceManSoundItem::playSound`).

## Evidence boundaries

**Verified from inspected source:** the ScummVM game/backbuffer/dirty-tile size and default clip are 640x480; bitmap and animation pixels are indexed; palette updates are dynamic; game geometry, collision and mouse messages use the existing coordinate values; regular video submission clips into that same screen; doubled Smacker drawing writes 2x pixels; hashes and NHC/BLB override behavior are as described above.

**Inference, not runtime proof:** replacing dimensions with 9x art while retaining old positions/hit rects would likely produce oversized/clipped or misaligned objects; changing only resources cannot turn the fixed screen into a high-res scene. NHC can carry compatible same-type replacement payloads, but no evidence here says it can handle an arbitrary image format or scale factor. No modified engine or candidate high-resolution asset was compiled or played.

## Primary source references

- `C:\Users\User\git\scummvm\engines\neverhood\neverhood.cpp`: `NeverhoodEngine::run`, `mainLoop`
- `...\screen.cpp`: `Screen::Screen`, `update`, `updatePalette`, `drawSurface2`, `drawDoubleSurface2`
- `...\graphics.cpp`: `BaseSurface`, `parseBitmapResource`, `unpackSpriteNormal`, `unpackSpriteRle`
- `...\resource.cpp`: `SpriteResource::load`, `AnimResource::load/draw`, `DataResource::getMessageListAtPos`
- `...\resourceman.cpp`, `blbarchive.cpp`, `nhcarchive.h/.cpp`: lookup, formats, overlay handling
- `...\sprite.cpp`, `scene.cpp`, `gamemodule.cpp`, `entity.cpp`: scene, sprite, collision, input and update flow
- `...\smackerplayer.cpp`, `sound.cpp`: video and audio playback
