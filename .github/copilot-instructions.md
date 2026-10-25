# Neverhood Upscale Project — Global Rules (all agents)

Goal: upscale The Neverhood (graphics + video) and rebuild game data in `DATA_upscaled/`.

## Hard rules
1. **NEVER modify, move, rename or delete anything in `DATA_source/`** (original, read-only). Also never touch `setup/`, `*.exe`, `readme.txt` originals.
2. All new/modified game files go ONLY to `DATA_upscaled/` (mirror `DATA_source/` structure).
3. ALL intermediate files go in `work_directory/` using the logical structure below. No stray files in the project root.
4. Always keep learning: write every valuable lesson (formats, tool flags, pitfalls, what failed) to `knowledge/` (see `knowledge/README.md`).
5. Communicate between agents ONLY via `comms_center/` (see `comms_center/PROTOCOL.md`).
6. Documentation style: human-readable, concise; **newest entries on top** (reverse-chronological, dated). Keep `README.md` (project overview/how-to) and `progress_docs.md` (dated progress log) current after every meaningful step.
7. Destructive/irreversible ops need manager approval; prefer copy over move.
9. Secrets live only in `.secrets/secrets.json` (git-ignored). Never copy keys into docs, logs, comms, scripts or `work_directory`; read them at runtime. Never send any asset to a third-party API without explicit user approval (see `knowledge/cloud_api_options.md`).
8. Be reproducible: every pipeline step is a script in `work_directory/tools/` + logged.

## Layout
```
DATA_source/        ORIGINAL (read-only)
DATA_upscaled/      FINAL new game files
work_directory/
  extracted/{graphics,video,audio}/   analyst output (raw from .blb)
  upscaled/{graphics,video}/          video_champion output
  qa/                                 quality reports, comparisons
  tools/                              scripts, converters
  scratch/                            temp (safe to purge)
knowledge/          lessons learned, format specs, tool notes
comms_center/       agent messaging (inbox/, log, tasks, archive/)
.github/agents/     agent definitions
```
Use sub-folders per asset source, e.g. `work_directory/extracted/video/a.blb/<asset_id>/`.

## Agents
- `Neverhood_manager` — orchestrates, assigns tasks, maintains comms/knowledge.
- `Neverhood_analyst` — game structure, extraction, repacking into `DATA_upscaled/`.
- `Neverhood_video_champion` — decode/upscale/clean/QA of images & video.
- `Neverhood_engine_champion` (ENG) — ScummVM engine source analysis (`C:\Users\User\git\scummvm\engines\neverhood`), upscaled-asset feasibility.
