# Sources and references

## 2026-10-23 - T6: display modes, scaler capability, and HD asset feasibility

- Local original game manual: `readme.txt` in project root, 'A few things Willie wants you to know' / display-driver troubleshooting. It says the game automatically changes display to 640x400, requires 256 colors, warns not to change monitor resolution, and mentions `SetDisplayMode`/DirectX driver errors. This is manual evidence, not a direct original-executable disassembly.
- ScummVM Neverhood engine: [`neverhood.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/neverhood/neverhood.cpp) (`initGraphics(640, 480)`); [`screen.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/neverhood/screen.cpp) (640x480 CLUT8 backbuffer/palette); [`graphics.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/neverhood/graphics.cpp) (indexed sprite and fixed clip/draw logic); [`smackerplayer.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/neverhood/smackerplayer.cpp) (normal/doubled movie surfaces).
- ScummVM official graphics behavior: [`understand_graphics.rst`](https://github.com/scummvm/scummvm/blob/master/doc/docportal/advanced_topics/understand_graphics.rst) and [`graphics.rst`](https://github.com/scummvm/scummvm/blob/master/doc/docportal/settings/graphics.rst). SDL Surface mode applies a software scaler before aspect/stretch; OpenGL mode scales the original game image to output with nearest/bilinear filtering. HQ2x/HQ3x and other software factors are backend/build dependent. Checked current source `graphics/scaler/hq.cpp`, `graphics/scalerplugin.cpp`, `backends/graphics/opengl/opengl-graphics.cpp`; no xBRZ support identified. Shader availability is backend/build dependent and does not add Neverhood high-resolution asset loading.
- Blaizer SDL2 Perl reimplementation: [`README`](https://github.com/Blaizer/Neverhood/blob/master/README) calls it incomplete and based substantially on ScummVM; [`src/App.c`](https://github.com/Blaizer/Neverhood/blob/master/src/App.c) creates a resizable SDL window with 640x480 logical size; [`lib/Neverhood/MoviePlayer.pm`](https://github.com/Blaizer/Neverhood/blob/master/lib/Neverhood/MoviePlayer.pm) has optional default-on 2x movie surfaces. This is port presentation behavior, not original-executable capability.
- Other project checked: [The Neverhood Restoration Project](https://github.com/pyroneous/TheNeverhoodRestorationProject); no inspected source/documentation established a verified hi-res engine/fork. No original binaries were executed; the original executable was not disassembled for this research.

## 2026-10-23 - T5: aliases, image tools, and engine references

- ScummVM game-variable identifiers and declarations: https://github.com/scummvm/scummvm/blob/master/engines/neverhood/gamevars.h (game-state hashes/arrays, not BLB metadata or scaling controls).
- Blaizer/Neverhood reimplementation: https://github.com/Blaizer/Neverhood; README, `src/Archive.c`/`.h`, `src/Sprite.c`, `src/App.c`, `lib/Neverhood/ResourceMan.pm`, `lib/Neverhood/Options.pm`, and `lib/Neverhood/MoviePlayer.pm` inspected. It expressly redirects compression `0x65` entries through their `disk_size` resource hash; its archive parser decodes only 1/3. The project says its engine is based substantially on ScummVM.
- Neverhood Image Tools: https://yal-game-tools.github.io/neverhood-image-tools/ and source https://github.com/YellowAfterlife/neverhood-image-tools (README, `NhiReader.hx`, `NhiWriter.hx`, `NhiWeb.hx` inspected). Standalone NHI/NHP and PNG/BMP conversion; format-26 writer generates/quantizes its own palette.
- ScummVM wiki requested URL: https://wiki.scummvm.org/index.php/Neverhood (and `?title=The_Neverhood`/raw/API variants attempted 2026-10-23; access returned anti-bot challenge/HTTP 500, so no new claims derived from it).

## 2026-10-23 - T4: alias, timing and palette-source details

- FFmpeg Smacker demuxer timing logic: https://github.com/FFmpeg/FFmpeg/blob/master/libavformat/smacker.c (signed `pts_inc`; negative absolute value vs. positive ?100, internal time base 100000).
- pyBLB README and implementation: https://github.com/michal4132/pyBLB and https://github.com/michal4132/pyBLB/blob/master/pyBLB.py (community `comprType == 101` path calls `getFile(file.diskSize)`; `getFile` matches resource hashes).
- ScummVM bitmap parser: https://github.com/scummvm/scummvm/blob/master/engines/neverhood/graphics.cpp (bitmap flags, optional dimensions/position/palette and index pixels); BLB reader handles only compression IDs 1 and 3 in `blbarchive.cpp`.


## 2026-10-23 - ANL research references

### Primary engine/format source
ScummVM Neverhood engine source (public, source-derived factual references; upstream `master` URLs may change):
- Engine archive load order: https://github.com/scummvm/scummvm/blob/master/engines/neverhood/neverhood.cpp
- BLB headers, directory records, DCL loading, stream bounds: https://github.com/scummvm/scummvm/blob/master/engines/neverhood/blbarchive.cpp
- BLB entry structures: https://github.com/scummvm/scummvm/blob/master/engines/neverhood/blbarchive.h
- Resource type IDs, bitmap/animation/text structures: https://github.com/scummvm/scummvm/blob/master/engines/neverhood/resource.h and https://github.com/scummvm/scummvm/blob/master/engines/neverhood/resource.cpp
- Bitmap format/RLE and indexed drawing: https://github.com/scummvm/scummvm/blob/master/engines/neverhood/graphics.cpp
- Palette and 640x480 CLUT8 screen: https://github.com/scummvm/scummvm/blob/master/engines/neverhood/screen.cpp
- Hash lookup, duplicate timestamp choice, archive registration: https://github.com/scummvm/scummvm/blob/master/engines/neverhood/resourceman.cpp
- Smacker playback: https://github.com/scummvm/scummvm/blob/master/engines/neverhood/smackerplayer.cpp
- Audio codec/playback: https://github.com/scummvm/scummvm/blob/master/engines/neverhood/sound.cpp
- ScummVM engine directory: https://github.com/scummvm/scummvm/tree/master/engines/neverhood

### Community references
- pyBLB extractor/packer and its stated codec/encoding coverage: https://github.com/michal4132/pyBLB and https://raw.githubusercontent.com/michal4132/pyBLB/master/README.md
- Neverhood Restoration Project: https://github.com/pyroneous/TheNeverhoodRestorationProject
- ScummVM Neverhood wiki page (may apply anti-bot protections): https://wiki.scummvm.org/index.php?title=The_Neverhood

### Local inputs
`DATA_source/*.blb`, root `readme.txt`, `AUTORUN.INF`, `nhood.ico`, `SETUP.EXE`, `setup95.exe`; names under `setup/` outside `setup/directx`. Root installer binaries were not executed. `setup/directx` was not inspected.
