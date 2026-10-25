## 2026-10-25 - T23: source-traced engine/asset feasibility (ENG)

The ScummVM engine source was re-read at revision `8ab1cfafb42`; detailed function map and verification limits are in `engine_source.md`, with the decision/options/patch plan in `upscaled_assets_feasibility.md`.

- **Verified:** `NeverhoodEngine::run()` requests 640x480; `Screen` owns a 640x480 CLUT8 backbuffer and dirty-tile tracker; `BaseSurface` defaults to that clip. Sprite and animation pixels are indexed, palette updates are dynamic, and render submission does not apply a general scale factor.
- **Verified:** sprites, animation offsets, game hit/collision rectangles, and mouse messages operate in the existing coordinate space. `AnimatedSprite::updateFrameInfo()` loads draw/movement/collision/timing metadata independently of frame pixel bytes. Larger artwork alone does not scale those values.
- **Verified:** resources can be overridden by configured hash-keyed `.nhc` entries for defined types; this is not a loose-image loader or a scale system. Smacker regular surfaces are clipped into the fixed screen; the special double path writes pixels 2x2 directly to the same backbuffer.
- **Recommendation:** use ScummVM backend presentation scaling with original-compatible resources as the interim runtime path. Keep larger replacements out of production BLBs/NHC until a fork separates logical geometry from raster dimensions, implements safe scaled composition and input mapping, handles palettes/video/subtitles, and passes tests. Current research did not build or run a patch.

### Sources
- ScummVM revision: `8ab1cfafb42` (`C:\Users\User\git\scummvm`)
- `engines/neverhood/neverhood.cpp`: `NeverhoodEngine::run`, `mainLoop`
- `engines/neverhood/screen.cpp`: `Screen::Screen`, `drawSurface2`, `drawDoubleSurface2`, `updatePalette`
- `engines/neverhood/graphics.cpp`, `resource.cpp`, `sprite.cpp`, `gamemodule.cpp`: indexed resource, animation, geometry, and mouse paths
- `engines/neverhood/resourceman.cpp`, `nhcarchive.h/.cpp`: resource override paths
- `engines/neverhood/smackerplayer.cpp`: normal/doubled Smacker composition
# Engine technology and compatibility

## 2026-10-23 - T5: game variables and scaling evidence

ScummVM `gamevars.h` enumerates hashed gameplay state (scene/module, puzzle flags, inventory, counters and arrays) plus save/load/get/set APIs. These identifiers describe mutable game state; they are not BLB resource indices, image dimensions, display settings, or documented scaling hooks. See `game_vars.md`.

Resolution evidence is now better differentiated: ScummVM's actual game screen remains 640x480 CLUT8. Blaizer's separate SDL reimplementation creates a resizable window and sets SDL logical size to 640x480, allowing renderer-level output scaling/letterboxing while retaining the game's logical coordinate system; its MoviePlayer also optionally doubles video frames. This demonstrates that a port can add presentation scaling, not that original BLBs or the original runtime support higher-resolution assets. Existing sprite/animation geometry and palette constraints still apply.

## 2026-10-23 - ScummVM source-derived behavior

The Neverhood engine initializes a **640x480** graphics mode and a **640x480 CLUT8** backbuffer; sprite resources use indexed pixel data and dynamic 256-color palettes. Game resources are looked up by 32-bit hash across the BLB archives. Duplicate hashes resolve to the record with the newer timestamp. Normal resource loading applies the outer BLB compression; video playback instead receives a bounded stream of raw type-10 payload bytes.

ScummVM loads `a`, `c`, `hd`, `i`, `m` (optional), `s`, `t`. Language affects whether `m.blb` is optional; demo mode uses different archives. The engine's 640x480 coordinate system, sprite rectangles, hit/collision regions, animation offsets, video dimensions, and palette indexes are compatibility constraints. Replacing 320x240 movies with higher-resolution streams alone will not enlarge the game canvas. A scaling implementation must be deliberate and preserve scene coordinates, UI placement, aspect ratio, palette and frame timing.

The root readme requires a 256-color display and warns against changing monitor resolution during play, supporting the engine-source findings about indexed color and a fixed coordinate canvas. It also documents legacy accelerated-video-driver problems and an ESS1888/DirectX 3 sound-driver issue. Windows installer assets indicate a Windows 95-era target; never execute setup files during format research. The local `setup/` vendor folder names suggest legacy graphics/audio device support, but no driver files were found in the non-DirectX folders. DirectX contents were skipped.

### Sources
- Engine entry point and archive order: `https://github.com/scummvm/scummvm/blob/master/engines/neverhood/neverhood.cpp`
- Resource hash resolution: `https://github.com/scummvm/scummvm/blob/master/engines/neverhood/resourceman.cpp`
- Screen format: `https://github.com/scummvm/scummvm/blob/master/engines/neverhood/screen.cpp`


