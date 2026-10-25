# Resolution options

## 2026-10-23 - T6: HD output and replacement-asset compatibility

### Findings
- **Original executable/display:** the supplied `readme.txt` says the game automatically switches to **640x400** during play, requires at least 256 colors, warns against changing monitor resolution, and cites a `SetDisplayMode`/DirectX video-driver error. That is evidence of a fixed legacy display-mode path, but does not itself establish 8-bit DirectDraw internals. ScummVM's reimplementation instead explicitly initializes a **640x480** game canvas and a CLUT8 (8-bit indexed) backbuffer. Treat these as different claims (possibly original output mode vs. ScummVM logical canvas); the original executable was not disassembled or run. No supported original setting for 1080p+ rendering was found. A DirectDraw wrapper/virtual machine may scale its output, but that does not increase internal scene/asset resolution or provide HD-asset hooks.
- **ScummVM:** the Neverhood engine remains 640x480 CLUT8; bitmap drawing, clip bounds and the normal Smacker surface are game-coordinate sized. The SDL Surface backend offers software scaler factors (normal 1x to 4x, HQ2x/HQ3x, SaI/SuperSaI/SuperEagle and others depending on build), then aspect/stretches to the window. OpenGL mode can scale the original game image to the display by nearest-neighbour or bilinear filtering; it does not load larger Neverhood sprites. Official scaler code/docs reviewed contain HQx and related filters, not xBRZ. Shader features depend on backend/build and are not a Neverhood HD-asset-replacement feature.
- **Blaizer/Neverhood:** this is an explicitly incomplete Perl/SDL2 reimplementation, substantially based on ScummVM, not a high-resolution original-engine fork. `App.c` creates a resizable window but retains a 640x480 SDL logical size and linear renderer scaling. `MoviePlayer.pm` optionally (default true) creates 2x movie surfaces. This is output/movie presentation scaling, not general N-times bitmap/animation or UHD rendering. No other inspected fork established high-resolution asset support.

### Resolution targets (preserve the 4:3 game image)
Uniform scale of the ScummVM 640x480 canvas; 16:9 panels use pillarboxing rather than cropping or distortion:

| Panel class | 16:9 output | 4:3 image area | Scale | 4:3 panel target | Scale |
|---|---:|---:|---:|---:|---:|
| 1080p | 1920x1080 | 1440x1080 (240 px bars each side) | 2.25x | 1440x1080 | 2.25x |
| 1440p | 2560x1440 | 1920x1440 (320 px bars each side) | 3x | 1920x1440 | 3x |
| 2160p | 3840x2160 | 2880x2160 (480 px bars each side) | 4.5x | 2880x2160 | 4.5x |

Integer 4:3 candidates: **3x = 1920x1440**, **4x = 2560x1920**. In particular, 4x is not the 4:3 area of a 2160p panel; that is 4.5x. Fractional scales are valid for GPU output but cannot preserve integer pixel blocks. Avoid non-uniform stretching to fill 16:9 unless deliberately accepting geometric distortion.

### What a true HD-asset engine would need
A fork must separate the logical 640x480 world from output pixels. Keep mouse/hit-test/collision coordinates and animation anchors in logical units (inverse-transform pointer input), but draw high-res backgrounds/sprites to a larger RGB surface using explicit per-asset scale/registration metadata. Change bitmap loading and cached-surface allocation/strides/clipping; transform sprite destination rectangles, offsets, dirty regions, UI/text and screen copies consistently. For CLUT8 sources, expand each index through the *current* 256-color palette at draw time (or implement dynamic palette changes in true-color textures); do not merely reinterpret indices or assume one static palette. Preserve animation frame geometry/collision data. For Smacker, retain container/timing/audio integrity and size the decoded-frame surface/destination correctly; existing doubled-video code is a special case, not a general 4K path. Original 320x240/448x240/320x200 videos also need an explicit letterbox/scale policy. Resource encoders and BLB index/offset consistency remain separate, unvalidated work.

This is a substantial, engine-wide fork with content-specific QA and much more risk than presentation scaling. Upscaled PNGs inserted into current BLBs will not make either original game or stock ScummVM render high-resolution sprites; larger bitmaps may clip, collide incorrectly, or fail assumed bounds/palette handling.

### Recommendation for this project
1. **Immediate playable high-resolution option:** use ScummVM at its unchanged 640x480 logical resolution and enable correct 4:3 aspect/fit on 16:9 displays. Use nearest/normal scaling for crisp blocks or a supported HQ scaler for a smoothed look; output scaling reaches 1080p/1440p/2160p, but is post-process and cannot reveal newly upscaled asset detail. Keep bars; don't stretch/crop.
2. **For the project's upscaled assets:** do not replace production BLB resources yet. Keep source archives pristine and retain upscaled assets as companion/reference assets until a custom renderer/fork can load them. Prototype a high-res renderer against a small static scene, then one animated sprite and one SMK. Maintain logical 640x480 coordinates, exact palette behavior and metadata.
3. Start with **3x 1920x1440** for a 4:3 integer-scale prototype (also maps neatly to 1440p panel height); then assess **4x 2560x1920** for extra detail. For a 2160p 4:3 viewport, use 4.5x 2880x2160 only if fractional scaling and its QA cost are acceptable. These are target asset/output budgets, not settings the original executable accepts.

### Sources
See `sources.md` T6 links. Primary evidence: local original `readme.txt`; ScummVM Neverhood initialization/screen/bitmap/Smacker code and graphics-mode documentation; Blaizer `App.c`, `MoviePlayer.pm`, and project README.

## 2026-10-24 - RULES: output resolution tiers (user-set, binding)

Naming: **2160p = 3840x2160, 1440p = 2560x1440, 1080p = 1920x1080** (16:9 display modes). These names refer ONLY to the display. Asset sizes are never called "1080p" etc.; call them "content size @ tier".

The game image is 4:3, so the content is smaller than the display; the engine fills the rest.

| Display tier | Display size | 4:3 content size (asset) | Scale vs 640x480 |
|--------------|--------------|--------------------------|------------------|
| 2160p | 3840x2160 | 2880x2160 | 4.5x |
| 1440p | 2560x1440 | 1920x1440 | 3x |
| 1080p | 1920x1080 | 1440x1080 | 2.25x |

Rules:
1. **Keep aspect ratio.** Never stretch/crop to 16:9; uniform scale factor for width and height (round to even numbers for video).
2. **No black bars in assets.** Do not generate, upscale or encode letterbox/pillarbox padding; spend no compute on it. The engine adds bars/background at display time. If a source frame has baked-in black borders, crop them, record the crop in the manifest, and scale only the active picture.
3. **Fit by display height**: content height = 2160 / 1440 / 1080. Sprites/partial images use the same factor as the full frame (4.5x / 3x / 2.25x) so they stay aligned.
4. **Master once, derive the rest.** Produce the 2160p content master (2880x2160) and Lanczos-downscale to the 1440p and 1080p content sizes; do not run the expensive upscaler three times. Record rounding of non-integer factors per asset.
5. API outputs with another size (e.g. Gemini 4800x3584) must be cropped/resized to the exact content size with aspect preserved, never padded.
6. Never exceed the content size of the tier (earlier T11 3840x2880 tests were exploratory only).
