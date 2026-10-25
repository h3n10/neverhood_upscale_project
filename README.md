# Neverhood Upscale Project

Upscaling graphics and video of *The Neverhood* (1996) using a small team of AI agents.

## Folders
| Path | Purpose |
|---|---|
| `DATA_source/` | Original game data (.blb) â€” **read-only** |
| `DATA_upscaled/` | Final new game files |
| `work_directory/` | All intermediates (extracted, upscaled, qa, tools, scratch) |
| `knowledge/` | Lessons learned and format/game documentation |
| `comms_center/` | Agent messaging (see `PROTOCOL.md`) |
| `setup/`, root files | Original CD installer files (reference only) |
| `.github/` | Rules, agents, skills |

## Agents
`Neverhood_manager` (the only user-facing one) â†’ `Neverhood_analyst` (structure, extraction, repacking) and `Neverhood_video_champion` (decode, upscale, QA).

## Rules
See [.github/copilot-instructions.md](.github/copilot-instructions.md). Docs: newest entries on top.

## Tools and prerequisites
- **Python 3.10+** to run the project scripts; `pip` is used to install their Python dependencies.
- **FFmpeg** is an external tool required for SMK frame/audio decoding, video QA, and video assembly. Add `ffmpeg.exe` to `PATH` (check with `ffmpeg -version`); raw BLB inspection/extraction and built-in audio decoding do not require it.
- Python packages are pinned in `requirements.txt`; FFmpeg is not a Python package and is not bundled in this repository.

## Python setup (Windows PowerShell)
Create and install the project environment:
```powershell
python -m venv work_directory\.venv
.\work_directory\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```
The virtual environment inherits the system `PATH`. Video tools resolve FFmpeg there by default; use `--ffmpeg PATH` only to override that executable.

## Current technical baseline (2026-10-24)
- BLB header/directory, archive counts, resource formats, engine behavior, compatibility limits and citations are indexed in [knowledge/README.md](knowledge/README.md).
- `work_directory/tools/blb_inspect.py` creates a read-only per-entry audit at `work_directory/scratch/blb_manifest.json`; no bulk extraction or repack has been done.
- `s.blb` compression-101 rows are hash-linked aliases (all 84 resolve); preserve alias semantics and note ScummVM compatibility caveat. Two bounded SMK samples are extracted and FFmpeg-decoded: c.blb#80 (3 frames) and motion-verified c.blb#0 (85 frames, 320x240). PNG frame checks and checksums are documented in their metadata; no repack has been done.
- `work_directory/tools/extract_smk_motion_frames.py` reproducibly extracts three spread frames and verifies pixel motion. The `neverhood-omnibus` skill is at [.github/skills/neverhood-omnibus/SKILL.md](.github/skills/neverhood-omnibus/SKILL.md).
- Cloud-image APIs are research-only: no assets uploaded; explicit rights/privacy/user authorization is required. See `knowledge/cloud_api_options.md` and `knowledge/qa_process.md` (templates in `work_directory/qa/templates/`). Video conversion/upscaling/HDR research and the source-faithful SDR recommendation are recorded in `knowledge/upscaling.md`, `knowledge/video_conversion.md` and `knowledge/uhd_hdr.md` (T7).
- Every VID batch now has a documented QA gate before analyst handoff; the manager triggers an isolated second-agent review for generative or changed pipelines, failed/uncertain checks, or critical sample findings. See `comms_center/PROTOCOL.md` and `knowledge/qa_process.md`.

## Engine feasibility (2026-10-25)
- T23 source-traced ScummVM engine behavior and upscaled-asset feasibility are documented in [knowledge/engine_source.md](knowledge/engine_source.md) and [knowledge/upscaled_assets_feasibility.md](knowledge/upscaled_assets_feasibility.md); larger replacements remain on hold pending a custom high-resolution renderer.
- [T24 engine update plan](docs/engine_update_plan.md) - plan-only resolution/render/resource design, source evidence, estimates and open questions; no ScummVM tree changes.

## Docs and extraction (2026-10-25)
- [docs/game_tree.md](docs/game_tree.md) - game files/archives/videos/audio/engine tree (generated + ScummVM note).
- [docs/upscaling_plan.md](docs/upscaling_plan.md) - `[x]/[ ]` plan per asset group + per-video tracker; update marks by hand or `python work_directory/tools/gen_docs.py --mark ...` (regenerates both docs, keeps marks).
- `work_directory/tools/extract_all.py` - extract from `DATA_source/*.blb` (read-only) to `work_directory/extracted/{video,audio,graphics,data}/<blb>.blb/<id>/` with `metadata.json`:
```powershell
python work_directory/tools/extract_all.py --list                              # dry-run, all archives
python work_directory/tools/extract_all.py --blb c --type video --ids 0,80 --decode-frames 3 --video-audio
python work_directory/tools/extract_all.py --blb a --type audio                # all 329 sounds -> WAV 22050 Hz mono
python work_directory/tools/extract_all.py --blb i hd --type graphics --ids 0-50   # bitmaps -> indexed PNG, palettes
python work_directory/tools/extract_all.py --type all --out D:\nh_out --force      # everything (large)
```
Options: `--blb` (a c hd i m s t | all), `--type video|audio|graphics|data|all`, `--ids/--index` (`0,5,10-20,300-`), `--out`, `--list`, `--manifest file.json`, `--force` (default skips dirs that have metadata.json), `--decode-frames N|all` and `--video-audio` (need FFmpeg), `--ffmpeg PATH` (optional override; defaults to `ffmpeg` on `PATH`). Install FFmpeg separately and add it to `PATH`, or pass its executable path explicitly.

## Status
See [progress_docs.md](progress_docs.md).
