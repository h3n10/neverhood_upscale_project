---
name: neverhood-omnibus
description: Distilled Neverhood game, BLB, graphics, video, audio, engine, extraction, and repacking reference for the analyst.
---

# Neverhood Omnibus

## T6 resolution research (2026-10-23)
- Do not conflate the original local manual's documented 640x400 display-mode switch/256-color requirement with ScummVM's 640x480 CLUT8 canvas. Original exe was not disassembled; no native HD mode/assets hook was established. DirectDraw output wrappers cannot by themselves create engine-resolution detail.
- Stock ScummVM scales the fixed game image at presentation (software scalers include factors and HQ filters depending on backend/build; OpenGL uses nearest/bilinear output scaling). This does not load HD replacements. Blaizer's incomplete SDL2 port keeps a 640x480 logical canvas; default 2x movie surface is a special video option, not a general hi-res pipeline.
- HD assets require a custom renderer/engine that separates logical coordinates from high-res surfaces, maps mouse input back, transforms draw/clip/UI/animation geometry, handles dynamic CLUT8 palettes and full-resolution Smacker outputs. Preserve 4:3 content with pillarboxing on 16:9.
- Candidate 4:3 integer targets are 3x 1920x1440 and 4x 2560x1920; 2160p 4:3 is 2880x2160 (4.5x). The recommended interim solution is ScummVM presentation scaling; keep upscaled replacements out of production BLBs pending a renderer and runtime validation. Full analysis/citations: `knowledge/resolution_options.md` and `knowledge/sources.md`.

Use this skill for Neverhood archive analysis and safe asset-pipeline work. Follow the project-level instructions and `comms_center/PROTOCOL.md`; originals in `DATA_source/` are read-only. Keep intermediate output under `work_directory/`; final game files only under `DATA_upscaled/`.

## T5 source research (2026-10-23)
- Blaizer/Neverhood's `ResourceMan.pm` explicitly redirects compression `0x65` aliases via the `disk_size` resource hash. This corroborates s.blb semantics, but the reimplementation is based substantially on ScummVM; it does not prove original executable behavior. Its archive parser handles only compression 1/3.
- YAL Neverhood Image Tools reads/writes standalone NHI/NHP. Format-26 export creates a new frequency-ranked palette and quantizes >256 colors; it does not preserve an existing palette/index mapping or pack BLBs. No validated type-2 image/repack path is established.
- ScummVM `gamevars.h` describes gameplay-state hashes only, not asset metadata or scaling. ScummVM stays 640x480 CLUT8. Blaizer's separate SDL port scales a 640x480 logical canvas to a resizable output and can double movie frames; this is port-level presentation scaling, not proof that original runtime/assets have high-resolution hooks.
- The requested ScummVM wiki page is anti-bot/500 blocked from this environment; do not infer fresh facts from it. See `knowledge/sources.md`, `knowledge/game_vars.md`, `knowledge/graphics_formats.md`, and `knowledge/engine_tech.md`.

## Fast facts
- Seven BLBs: `a` audio (295 sounds, 34 music), `c` (82 videos + 1 bitmap), `hd` (73 bitmaps + 1 video), `i` (1,183 bitmaps, 54 palettes, 13 animations, 54 data, 12 text), `m` (13 videos), `s` (358 type-4 records; 84 hash aliases, runtime caveat in BLB notes), and `t` (122 bitmaps + 455 videos).
- BLB header signature `0x02004940`, version 7, extended-data length, archive length, entry count; then ordered `uint32` hashes, 20-byte ordered records, shared extended-data block, payloads. Record = type, outer compression, 1-based extended-data offset, timestamp, payload offset, stored size, expanded size. Outer compression 1 is raw, 3 DCL.
- Resource types: 2 bitmap, 3 palette, 4 animation, 5 data, 6 text, 7 sound, 8 music, 10 video.
- Graphics: 640x480 CLUT8 canvas, palette-index pixels, dynamic 256-color palettes; type-2 bitmap can use RLE and optional dimensions/position/1,024-byte palette. Type-4 animations carry frame geometry, offsets, timing and collision data.
- Videos are raw type-10 `SMK2` streams, 551 total; typical 320x240, with `c.blb` also 448x240 and 320x200. Signed frame rate: negative raw fields are 1/100000-second frame intervals; positive fields are milliseconds. A 3-frame `c.blb` sample (entry 80) decodes in ffmpeg 7.1.
- Audio type 7/8 plays at 22,050 Hz mono. Extended-data byte selects signed 8-bit differential samples + left shift; `0xFF` selects raw signed 16-bit LE samples.
- `s.blb`: 84 type-4/compression-101 rows are dummy aliases; their `disk_size` is a resource hash (not bytes), all 84 resolve to type-4/compression-3 entries. ScummVM itself only handles IDs 1/3, so preserve aliases and test runtime expectations.
- Engine hash lookup chooses newer timestamp for duplicate hashes. Preserve hash/record index alignment, timestamps, ext-data offsets, compression and file size.

## Knowledge and tools
Read these before deeper work:
- `knowledge/README.md` - index
- `knowledge/game_structure.md`, `knowledge/blb_format.md` - archives and container
- `knowledge/graphics_formats.md`, `knowledge/video_formats.md`, `knowledge/audio_formats.md` - resources
- `knowledge/engine_tech.md`, `knowledge/game_vars.md`, `knowledge/tools.md`, `knowledge/sources.md` - runtime, game-state IDs, workflow and citations
- `work_directory/tools/blb_inspect.py` - read-only structural and SMK-header inspector (including hash-alias resolution)
- `work_directory/tools/extract_smk_sample.py` - extract one bounded raw type-10 SMK plus metadata/checksum
- `work_directory/scratch/blb_manifest.json` - full entry metadata audit

Run the inspector from PowerShell with explicit paths (PowerShell itself expands):
```powershell
$archives = Get-ChildItem DATA_source -Filter '*.blb' -File | ForEach-Object { $_.FullName }
python work_directory/tools/blb_inspect.py $archives --json work_directory/scratch/blb_manifest.json
```
It does not extract or rewrite resources. Do not treat the manifest as a repack recipe for anomalous entries.

## Safe extraction workflow
1. Start by reading global instructions, protocol, analyst inbox, bus tail and `knowledge/`. Review archive hashes/manifest and resolve anomalies before acting.
2. Extract only authorized assets; never bulk extract unless requested. Work on a copy, writing to `work_directory/extracted/{graphics,video,audio}/<archive>/<entry>/`.
3. Include archive, entry index/hash, resource type, stored/expanded sizes, compression, offset, ext-data/palette, image dimensions, animation frame details or SMK frame count, and a checksum in a manifest. For alias rows in s.blb, disk_size is the target hash, not a payload size.
4. Preserve raw payload and palette/index map. Do not convert indexed art to RGB-only and discard its palette. For videos preserve the full SMK container and track/frame timing. For audio retain ext-data codec parameters.
5. Handoff to VID only via `comms_center/bus.log` following protocol; state paths, format, counts, dimensions, palette, frame counts and checksum. Do not claim handoff if no assets were extracted.

## Safe repack workflow
1. Obtain VID output and compare against its handoff manifest; validate dimensions, frame counts, palette mapping, alpha/transparency and checksums.
2. Rebuild a copy while retaining hash/record order, type, timestamp, extended-data bytes/offsets, outer compression, expanded/stored sizes and all unaffected payloads. Recompute payload offsets and declared total size; never edit `DATA_source/`.
3. Save only to `DATA_upscaled/` mirroring source paths. Re-run the inspector, compare every unchanged entry, and test representative playback. Raise compatibility concerns before scaling beyond the fixed 640x480 coordinate/palette assumptions.
4. Record lessons in `knowledge/`, update `progress_docs.md` newest-on-top, task status, and bus RESULT/HANDOFF as appropriate.

## Current known cautions
- Existing community pyBLB advertises pack/unpack but documents limited image encoding, no video encoding, animation encoding TODO, and audio encoding without compression. YAL Image Tools encodes standalone format-26 NHI with a generated palette, not BLB type-2 resources. Both remain unverified for palette-preserving archive round-trip; neither is a trusted repack pipeline.
- Only the authorized 3-frame SMK sample has been extracted; no repack has been performed. `s.blb` aliases are resolved structurally, but ScummVM runtime handling for alias rows remains uncertain. Palette-preserving type-2 re-encoding is possible in principle but has not been round-trip or engine tested.
