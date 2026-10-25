# Animation upscaling rules (generative, prompt v3 method)

Status: v2 (2026-10-25), user decisions applied. Scripts: `tools/scripts/upscale_run.py` (upscale), `tools/scripts/assemble_video.py` (frames -> video, local ffmpeg).
Prompts: `tools/scripts/prompts/upscale_v3.txt` (anchor), `upscale_v3_anim.txt` (other frames), `color_locks/<blb>_<entry>.txt` (per-clip colour paragraph, generic fallback).

## Resolution rule
4K = **3840x2160** (16:9 display canvas). 4:3 content is processed at **2880x2160** (source x 9) and only pillarboxed at the display/encode stage (`assemble_video.py --canvas 3840x2160`). Black bars are never sent to the model as content. Sprites and non-4:3 clips use the same proportional factor (x9, e.g. 320x200 -> 2880x1800). If the API lacks that aspect, the source is padded for the request and the bars are cropped from the result.

## Process
1. **Anchor** – first frame upscaled alone (`gemini-3-pro-image-preview`, 4K, prompt v3), resized to the target size.
2. **Approval** – `--approval sample` (default): every 10th clip needs a human OK (`ANCHOR_APPROVED` / `--approve-anchor`); others proceed automatically. `all`/`none` available. A regenerated anchor revokes approval.
3. **Frames** – request = `[current anchor (<=1920 px), current low-res frame]` (+ previous output with `--ref-mode first+prev`). Anchor = detail/style reference only.
4. **Re-anchor** – schedule computed from source frames: a frame whose mean abs diff (80x60) to the current anchor's source exceeds `--reanchor-threshold` (12) is generated with the old anchor as reference and then becomes the anchor. Deterministic, so resume is safe. Threshold is a guess – tune on a real pan/scene change.
5. **Auto-QA + re-roll** – per output: |mean RGB shift| ≤ 6, structure corr ≥ 0.985 (160 px grey), static-region diff vs anchor ≤ 6 (pixels unchanged vs anchor's source). Fail → re-roll up to 2×, each failed try saved to `quarantine/`; still failing → frame marked failed, clip not assembled. Thresholds are initial values (T11 api3: shift ≈ 3, corr 0.996) – calibrate on first real runs.
6. **Duplicates** – identical source frames reuse the earlier output (no call).
7. **Colour lock** – per clip; without it v1 shifted hues.
8. Generative output remains under PROTOCOL rules 6/7 (VID QA gate, independent review for new prompt/pipeline) before handoff to ANL.

## Assembly (answer to "how to get video back")
Local ffmpeg, inverse of extraction: `assemble_video.py` reads `frames/` + source `metadata.json` (fps_rational, frame count preserved), pipes PNGs to ffmpeg. Master = lossless FFV1 `.mkv`; `--codec h264|hevc` for review/delivery. Finishing, applied to display versions only (masters untouched): temporal film grain (`--grain 3`) and deterministic sub-pixel drift on held frames (`--drift 0.6` px) so holds don't look frozen. Audio is muxed later by ANL. Whether the game/ScummVM can play such files (it expects SMK at 640x480) is the repacking question for ANL – the HD files are reference/upscaled assets until an engine path exists.

## Not yet implemented / ideas
- Fades: upscale endpoints only and cross-fade mathematically (needs a fade detector).
- Cost: unknown until a trial; use `--max-calls`, `--anchors-only` first. If too expensive: lower `--image-size` (2K), Batch API (~50 %), or local model for static/boring clips.
- Transparent sprites/overlays need an alpha strategy (upscale on matte, scale alpha classically).
- Live API path (`call_api`) unchanged from the proven v3 test, but this script has only been run against a mocked API.

## Open questions
1. Cost ceiling per clip / total once we know clip counts (T20 extraction)?
2. Which clips get a hand-written colour lock (scene palettes)?
3. Should the sample-review rate stay 1 in 10?
