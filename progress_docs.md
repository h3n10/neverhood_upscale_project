## 2026-10-25 - T23 completed (ENG)
- Read-only source review of ScummVM Neverhood at `8ab1cfafb42`. Documented startup, fixed 640x480 CLUT8 screen, resource/hash/NHC behavior, bitmap/animation geometry, scene/entity/input flow, palettes, Smacker and audio paths in `knowledge/engine_source.md`.
- Assessed replacement and patch options in `knowledge/upscaled_assets_feasibility.md`. Recommendation: keep high-resolution replacements out of runtime data pending a custom logical-coordinate/high-resolution render path; use stock presentation scaling in the interim. Claims are marked verified vs inferred; no build/patch/runtime test was run.
- Updated `knowledge/engine_tech.md`, the knowledge index, project README and task board. ScummVM source and `DATA_source/` were not modified.
## 2026-10-25 - T18/T19/T20 completed (ANL)
- **T20** `work_directory/tools/extract_all.py`: CLI extractor (video/audio/graphics/data) with `--blb`, `--type`, `--ids/--index`, `--out`, `--list`, `--manifest`, `--force`, `--decode-frames N|all`, `--video-audio`. Output `work_directory/extracted/<group>/<blb>.blb/<id>/` + `metadata.json`. Includes a pure-Python PKWARE-DCL decoder (verified: all 1,821 compression-3 payloads decode to exact stored sizes), ScummVM-style audio decode to 22,050 Hz WAV, and type-2 bitmap (normal+RLE) to indexed PNG. `--list` on all archives = 2,750 entries; real extraction tested on c#0/#80 (frames+SMK audio), a#0/1/300, i#0-6, hd/t bitmaps, s#0-3 (test output purged). Full bulk extraction not yet run.
- **T18** `docs/game_tree.md`: generated tree of root files/archives/types with counts, sizes, resolutions, frame counts, per-video and per-audio tables, engine-element tree and ScummVM note.
- **T19** `docs/upscaling_plan.md`: `[x]/[~]/[ ]` checklist per archive/video/graphics/palette/audio/engine/QA/tier + 551-row per-video stage tracker (E/F/U/Q/R). Both docs come from `work_directory/tools/gen_docs.py` (marks preserved on regeneration; `--mark` helper).
- No `DATA_source/` or `DATA_upscaled/` changes.

## 2026-10-24 - MGR: T17 independent QA disposition
- Independent reviewer passed the provisional layout/color screens but could not verify reconstructed microdetail or approved variation range. Temporal consistency was not assessed (only frame 000 candidate available).
- Keep the generative frame_000 candidate on hold: no handoff, repack, or production. Resolve with explicit art/style review and required rights/privacy/method approvals; if intended for video, review consecutive generated frames for temporal consistency.
- Report: `work_directory/qa/T17_independent_frame000/independent_report.md`.

## 2026-10-24 - MGR: QA gate operationalized
- Added a required per-batch QA report, automated checks and tier-based human review before VID-to-ANL handoff; failed or uncertain outputs stay quarantined pending manager resolution.
- Defined when MGR must request a fresh, isolated, read-only second-agent review: generative output, changed pipeline, failed/uncertain gates, or critical sample findings. Routine deterministic batches retain existing review rates without extra-agent overhead.
- Updated `comms_center/PROTOCOL.md`, `knowledge/qa_process.md` and README. No assets or game data changed.

## 2026-10-24 - T9 completed (ANL)
- Extracted `c.blb` entry 0 as a second SMK2 sample: 320x240, 85 frames, 15.0015 fps, 5.6661 s, 541,428 B; archive SHA-256 is in its metadata. Full FFmpeg decode succeeded.
- Sampled frames 0/42/84 show clear clay-character movement. Their decoded RGB hashes are all distinct; pairwise comparisons changed 35,744, 42,334, and 23,260 pixels (of 76,800). Three PNGs and detailed hashes/diffs are beside the sample.
- Handed off to VID as H2. Added repeatable `work_directory/tools/extract_smk_motion_frames.py`; no `DATA_source/` or `DATA_upscaled/` files changed.

## 2026-10-24 - T8 completed (VID)
- Researched Google Gemini/Nano Banana, OpenAI GPT Image, Stability, Replicate ESRGAN, Topaz and Magnific current capabilities/pricing/limits, reproducibility, data practices and processing-rights considerations. Wrote `knowledge/cloud_api_options.md` and `knowledge/qa_process.md`.
- Recommendation: no cloud uploads now; local/classical for bulk and, only after explicit rights/privacy/style approval, a tiny hero-still generative study. Per-frame generation of 100k-500k frames is estimated at roughly $3,360-$120,000 per pass depending on API/model/resolution (before retries/input costs); details and local ESRGAN comparison documented.
- Designed frozen golden set, per-asset spec, automated/human gates, VLM advisory rubric, tiered review, regression, rejection/rework and signoff. Added QA checklist/report/rejection templates and referenced the process in the VID agent file.
- Added Pillow-only `work_directory/tools/image_qa_metrics.py`; ran it against five T7 scaler outputs locally, reports in `work_directory/qa/T8_metrics/`. No asset or key was sent to a third party. No DATA_source/DATA_upscaled files changed.

## 2026-10-23 - T7 completed (VID)
- Researched SMK decode, PNG/FFV1 working masters, classical and learned scalers, frame-rate/interpolation risks, palette/color handling, QA metrics, hardware and UHD/HDR delivery. Sources and recommendations are in `knowledge/upscaling.md`, `knowledge/video_conversion.md` and `knowledge/uhd_hdr.md`.
- Recommendation: source-faithful SDR, exact source cadence, lossless masters, aspect-correct classical scaler comparison; no AI restoration, HDR conversion or SMK/archive replacement without authorization and runtime validation.
- PowerShell GPU check: Intel UHD Graphics 620 (1 GB reported adapter memory); FFmpeg has zscale/libplacebo/libx265/VMAF; no PyTorch/OpenCV and no heavy AI tools installed. Vulkan acceleration remains unverified.
- Ran a small FFmpeg comparison (nearest, Lanczos, HQx, xBR, EPX; 3x) on two identical 320x200 paletted sample frames; outputs/contact sheets are in `work_directory/qa/T7_c_blb80/`; tool: `work_directory/tools/compare_classical_scalers.py`. Static frames do not establish motion quality. No DATA_source/DATA_upscaled files changed.

# Progress (newest on top)

## 2026-10-23 - T6 completed (ANL)
- Researched resolution behavior in the local manual, ScummVM Neverhood and graphics-backend source/docs, and Blaizer's SDL2 port. Important distinction: local original-game manual says 640x400 display-mode switch and 256-color minimum; ScummVM's implementation is fixed 640x480 CLUT8. Original executable was not disassembled/run, so do not claim verified high-res support or unsupported beyond available evidence.
- ScummVM can scale the logical screen to larger output via software filters or GPU nearest/bilinear scaling; that is presentation upscaling, not HD asset replacement. Blaizer keeps 640x480 logical rendering and only offers a special 2x movie path.
- Documented 1080p/1440p/2160p, 4:3 fit/pillarbox dimensions, engine work for high-res sprites/animations/palettes/SMK, and recommended staged strategy in `knowledge/resolution_options.md`; updated `sources.md`, index and omnibus skill. No game archives changed.

## 2026-10-23 - T5 completed (ANL)
- Read requested upstream sources: ScummVM `gamevars.h`; Blaizer archive/resource/sprite/app/movie code; YAL image-tool docs and encoder/decoder source. The ScummVM wiki was attempted at page/raw/API variants but returned anti-bot/HTTP 500.
- Blaizer explicitly redirects compression-101 aliases through the target resource hash, corroborating s.blb's 84 aliases. Since its reimplementation is substantially based on ScummVM and ScummVM itself only handles outer compression 1/3, original-runtime behavior remains unproven.
- YAL can convert standalone format-26 NHI from PNG/BMP, but regenerates/reorders palette indices and quantizes >256 colors; no palette-preserving type-2 or BLB repack path. Blaizer offers source reference for type-2 parsing, not an extraction/repack utility.
- Scaling conclusion clarified: ScummVM logical output is still 640x480 CLUT8; Blaizer's separate SDL port has a 640x480 logical canvas with resizable renderer output and optional 2x movie frames. This is port-level scaling, not original-runtime asset scaling support. Game variable hashes are unrelated.
- Updated `knowledge/` and omnibus skill. No DATA_source/DATA_upscaled files changed.

## 2026-10-23 - T3/T4 completed (ANL)
- T3: Extracted only `c.blb` entry 80 to `work_directory/extracted/video/c.blb/80/sample.smk` (SMK2, 320x200, 3 frames, 31,568 B, SHA-256 recorded in metadata). Bundled local ffmpeg 7.1 identified and decoded all 3 frames to null with exit 0; metadata includes archive, entry, offset, size, dimensions, frames, raw/derived rate. Added repeatable extractor; handed sample metadata/path to VID.
- T4(a): Resolved s.blb's 84 compression-101 rows as hash aliases: `disk_size` holds a resource hash, all references match a compression-3 type-4 entry. Alias-aware inspector now validates all real ranges and reports zero overlaps. ScummVM still rejects compression IDs other than 1/3, so runtime alias expectations remain a caveat.
- T4(b): FFmpeg `smacker.c` establishes signed-rate units: negative values encode frame intervals in 1/100,000 s; positive values are milliseconds. Sample raw -8300 = 1000/83 fps, approximately 12.0482; ffmpeg reports 12.05.
- T4(c): Palette-preserving type-2 encoding is technically viable with indexed pixels + exact 1,024-byte palette/resource metadata, but no complete encode/repack/engine round-trip was verified. pyBLB only claims Format-26 image encoding; palette remapping and animation/screen geometry remain risks.
- Updated knowledge and omnibus skill. DATA_source unchanged; DATA_upscaled unchanged.


## 2026-10-23 - T1/T2 completed
- Audited all seven DATA_source BLBs read-only: 2,750 declared directory rows; 551 SMK2 headers inspected without extracting bulk assets. Root readme confirms 256-color display requirements and legacy hardware-driver caveats. Documented archive map, BLB records/compression, graphics/palettes/animation, video, audio, engine loading/resolution, tools, and citations in knowledge/.
- Added work_directory/tools/blb_inspect.py and work_directory/scratch/blb_manifest.json. Parser checks header/directory, sizes/offsets, extended data, overlap/bounds and SMK metadata; validated 7 archives and 551 video headers.
- At T1, s.blb appeared to contain 84 unsupported compression IDs and invalid ranges; T4 resolved these as hash aliases. Preserve them and heed the documented runtime caveat.
- Created .github/skills/neverhood-omnibus/SKILL.md, linked it from the analyst agent definition, and updated the root README with the technical baseline. At the end of T1/T2, no bulk extraction, handoff, repack, or DATA_upscaled changes had occurred.
- Open questions: identify s.blb variant/corruption; confirm signed SMK rate units; validate a palette-preserving image encode/repack path and game compatibility.

## 2026-10-23 - Knowledge gathering started
- Rule added: docs newest-on-top; README + progress_docs maintained.
- Analyst tasked: analyze DATA_source, setup/ (skip directX), root files; web research; write `knowledge/`; create "neverhood omnibus" skill.

## 2026-10-23 - Project init
- Agents created (manager visible; analyst, video champion hidden), rules, comms_center, folder layout.

