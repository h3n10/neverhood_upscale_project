# Tools and workflow

## 2026-10-25 - T25: FFmpeg external dependency

- FFmpeg is optional for BLB inspection, raw extraction, and audio decoding; it is required for SMK frame/audio decoding, motion/scaler checks, and video assembly.
- Scripts now look for `ffmpeg` on `PATH`; extraction, assembly, and video QA tools accept `--ffmpeg PATH` as an override. No FFmpeg binary or imageio-ffmpeg package is needed in the repository.

## 2026-10-25 - T26: Python environment

- Create the Windows virtual environment at `work_directory/.venv` and install pinned Python dependencies with `python -m pip install -r requirements.txt`.
- Python dependencies are NumPy, Pillow, and SciPy. FFmpeg is not a pip dependency; the virtual environment retains system `PATH`, so `ffmpeg` resolves to the installed executable unless overridden with `--ffmpeg`.

## 2026-10-25 - T18-T20: extract_all.py, gen_docs.py (ANL)

- `extract_all.py` (usage in README.md) reuses `blb_inspect.inspect()` for the directory, then extracts per type. **LESSON: no DCL library needed** - a ~60-line pure-Python PKWARE-DCL decoder (blast.c algorithm: 2 header bytes lit/dict, canonical Huffman with inverted bits, length base/extra tables, 519 = end) decodes all 1,821 compression-3 payloads in a,c,hd,i,s,t to exactly the directory `size` (a few minutes for everything; `limit=` argument allows cheap header peeks). pyBLB needs the C `pklib`, which we do not have.
- Bitmap decode (flags 1 RLE/2 dims/4 pos/8 palette/16 image) verified visually (`i#1` 640x480 normal, `hd#0` RLE). Many bitmaps (i: 900/1183, all of t) have no embedded palette - PNGs of those use a grayscale ramp; the true palette comes from a type-3 entry/scene (open mapping task).
- Audio: ext-data byte = shift; 0xFF raw s16, else delta s8 accumulated then `<< shift`; WAV 22,050 Hz mono (matches ScummVM; not yet compared against an in-game recording).
- Video: raw SMK written as `video.smk`; `--decode-frames N` uses FFmpeg `select=eq(n,..)` with `-fps_mode passthrough`; `--video-audio` pulls the SMK audio track to `audio.wav`. These optional operations require FFmpeg on `PATH` or an explicit `--ffmpeg` path.
- Skip-existing is keyed on `metadata.json` in the entry folder; older samples (`sample.smk`) are therefore skipped unless `--force`.
- `gen_docs.py` generates `docs/game_tree.md` and `docs/upscaling_plan.md` (header cache `work_directory/scratch/docs_cache.json`, `--refresh` to rebuild) and preserves plan marks (`--mark`).
- Windows PowerShell: pipe-to-`python -` run order; stdout from piped Python only appears on exit - be patient with the DCL full scan.

## 2026-10-24 - T9: frame extraction and motion validation

`work_directory/tools/extract_smk_motion_frames.py` uses local FFmpeg with passthrough timing to extract frames 0/middle/last from a selected SMK. It stores the three PNGs and augments the sample metadata with PNG and decoded-RGB SHA-256 hashes plus pairwise changed-pixel/mean-difference measures; it fails if the selected frames are pixel-identical. Validated on `c.blb#0` (85 frames; frame indices 0/42/84 all differ).

## 2026-10-23 - T5: tool suitability checked against source

- YAL Neverhood Image Tools (browser UI/source) handles standalone NHI/NHP plus PNG/BMP. Its format-26 PNG/BMP encoder creates a frequency-ranked palette and nearest-color quantization; it is not a palette-preserving type-2 encoder and cannot extract/repack BLBs. Suitable as a visual/reference converter only.
- Blaizer/Neverhood provides useful source-level examples for BLB parsing, compression-101 resource-hash redirection, bitmap palette/RLE decode and a renderer, but it is an incomplete game reimplementation, not a command-line asset extractor or archive writer. Its parser supports outer compression 1 and 3 only.
- No newly inspected source establishes a complete, verified palette-preserving type-2 encode + archive repack path. Keep pyBLB's pack support as an unverified lead; validate on copies before use.

## 2026-10-23 - T3/T4: repeatable sample extraction and alias-aware audit

Added `work_directory/tools/extract_smk_sample.py`, which extracts one requested in-bounds, uncompressed type-10 SMK payload and writes its JSON metadata and SHA-256. The initial validation used imageio-ffmpeg's bundled FFmpeg 7.1; the vendored binary/package has since been removed in T25. Runtime frame/audio decode now resolves FFmpeg from `PATH` or an explicit `--ffmpeg` path.

Updated `blb_inspect.py` to recognize only type-4/compression-101 rows with offset/size zero as possible dummy aliases, resolve `disk_size` against the archive's hash table, and exclude confirmed references from byte-range/overlap totals. Re-run across all seven archives: all 84 s.blb aliases resolve and the archive has zero invalid real payload ranges or overlaps. Unresolved aliases remain invalid. Do not treat the alias field as payload bytes during repacking.


## 2026-10-23 - local inspector and known tools

### Local tool
`work_directory/tools/blb_inspect.py` is a read-only structural/header inspector; it does not extract or rewrite resources. It validates BLB header fields, maps hashes/20-byte records, checks bounds/ext-data/overlaps, records sizes/types/compression/offsets, and samples type-10 SMK2 headers. Full per-entry JSON manifest: `work_directory/scratch/blb_manifest.json`.

Run in PowerShell (expand paths explicitly; Python does not expand a shell wildcard on Windows):
```powershell
$archives = Get-ChildItem DATA_source -Filter '*.blb' -File | ForEach-Object { $_.FullName }
python work_directory/tools/blb_inspect.py $archives --json work_directory/scratch/blb_manifest.json
```

### Existing community tools
- **pyBLB** (`https://github.com/michal4132/pyBLB`) advertises BLB unpack/pack, directory printing/JSON reconstruction metadata, and image/video/audio/animation decoding. Its README marks image encoding as limited to format 26, video encoding as unavailable/possibly requiring RAD Game Tools, animation encoding unavailable, and audio encoding without compression. Treat it as a research lead, not a verified safe repacker; do not run it against `DATA_source` or assume round-trip fidelity.
- **The Neverhood Restoration Project** (`https://github.com/pyroneous/TheNeverhoodRestorationProject`) is a community project reference; its README is sparse and does not establish a dependable BLB round-trip pipeline.
- **ScummVM** is the strongest public format/engine reference here, not an asset extractor/repacker for this workflow.

### Controlled future workflow
1. Inspect and record checksums/header/directory first. Keep every input read-only.
2. If extraction is authorized, operate on a copy and write only beneath `work_directory/extracted/{graphics,video,audio}/<archive>/`; include archive hash/entry id/type/hash/size/compression/offset/palette/frame count and conversion details in a manifest. Extract only requested assets until pipeline validation.
3. Preserve indexed pixels/palettes for graphics; preserve complete SMK streams and timing for video; preserve extended-data codec bytes for audio. Use a reversible format and keep original raw payloads for audit.
4. Handoff to VID through the protocol with paths, dimensions, palette/index details, frame counts, and checksums. Do not place upscaled work in source or final game data.
5. Repack only validated assets to a copied archive under `DATA_upscaled/`, maintaining ordered hashes, types, timestamps, extended data, compression semantics, payload offsets/sizes and declared file size. Parse the result again; test duplicates, missing hashes, sample playback, then game compatibility.

During the initial T1 audit, no extraction or repacking was performed. T3 later extracted one authorized SMK sample with the bundled local ffmpeg; no bulk extraction, repacking, or `DATA_upscaled/` modification has occurred.
