# Neverhood game variables

## 2026-10-23 - T5 source review

ScummVM `engines/neverhood/gamevars.h` defines numeric 32-bit hashes for mutable gameplay variables. Named examples group into module/current-scene state, text and counters, Klaymen movement/state, puzzle/door/world flags, inventory, radio/navigation/projector/teleporter state, and array-like puzzle values. `GameVars` exposes clear, save/load, global get/set, sub-variable get/set, and diagnostic dump methods; entries contain a name hash, value, and linked indices for subvariables.

These hashes are game-state identifiers, not BLB resource hashes, archive directory fields, or graphics/display configuration. This header does not describe image encoding, archive compression, resolution, or scaling hooks. For visual compatibility, use the engine/rendering and resource parsers instead (`engine_tech.md`, `graphics_formats.md`).

Source: https://github.com/scummvm/scummvm/blob/master/engines/neverhood/gamevars.h
