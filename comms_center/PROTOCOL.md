# COMMS PROTOCOL v1 (machine-terse)

Transport: append-only files. One message = one line in `comms_center/bus.log` AND (if payload large) a file in recipient inbox `comms_center/inbox/<agent>/<id>.md`.

Agents: `MGR` (manager) `ANL` (analyst) `VID` (video_champion) `ENG` (engine_champion). `ALL` = broadcast.

## Line format (bus.log)
`<UTC ISO>|<FROM>><TO>|<TYPE>|<ID>|<STATUS>|<payload ≤200ch>|<ref path optional>`

TYPE: `TASK` `RESULT` `QUERY` `ANSWER` `BLOCK` `HANDOFF` `LESSON` `ALERT` `ACK`
STATUS: `NEW` `WIP` `DONE` `FAIL` `BLOCKED`
ID: `T<n>` task, `H<n>` handoff, `Q<n>` query (monotonic; see `tasks.tsv`).

## Examples
```
2026-10-23T14:00Z|MGR>ANL|TASK|T1|NEW|map a.blb entries; list types+counts|work_directory/extracted/
2026-10-23T15:10Z|ANL>VID|HANDOFF|H1|NEW|120 sprites 8bpp pal ready|work_directory/extracted/graphics/a.blb/
2026-10-23T16:30Z|VID>ANL|HANDOFF|H2|DONE|4x upscaled PNG+pal-map|work_directory/upscaled/graphics/a.blb/
2026-10-23T16:31Z|VID>ALL|LESSON|L7|DONE|ESRGAN anime model best for flat clay art|knowledge/upscaling.md
```

## Files
- `bus.log` — append-only message log (never edit old lines).
- `tasks.tsv` — task board: `id<TAB>owner<TAB>status<TAB>title<TAB>updated`. Manager owns; others update own rows.
- `inbox/<agent>/` — large payloads; delete/move to `archive/` after ACK.

## Rules
1. Read own inbox + tail of `bus.log` at start; write RESULT/BLOCK at end of every task.
2. Handoffs must list: paths, formats, counts, color/palette/size info, checksums if cheap.
3. ANL↔VID talk directly for handoffs but CC `MGR` in bus.log.
4. Any `LESSON` must also be written into `knowledge/`.
5. Keep payload terse; details go in referenced file.
6. **QA gate before handoff:** VID runs the applicable 100% automated checks and tier-based human review in `knowledge/qa_process.md` for every batch. Save a report under `work_directory/qa/<task-or-batch>/` with candidate/source identifiers and hashes, checks performed, sampling/reviewer, pass/fail per candidate, exceptions, and evidence paths. A failed or unresolved item is quarantined in `work_directory/qa/`; pause affected work and report `BLOCK` to MGR. Do not hand failed or unreviewed output to ANL or mark the batch complete.
7. **Independent-review trigger:** MGR obtains a second, isolated QA review before handoff or further batch work if the batch uses generative output, a new/changed model/prompt/scale/color pipeline, any automated gate fails, or a reviewer reports a possible content/layout/color/timing violation or uncertainty. Also trigger it if a critical issue is found in a human sample. MGR launches a fresh agent instance with a QA-only, read-only scope (prefer a dedicated QA agent if configured; otherwise use a fresh `Neverhood_video_champion` instance or an available independent reviewer). Give it the source/candidate evidence, rubric, and report, but not the generation context or desired outcome. It returns a cited pass/fail/uncertain report to MGR; uncertainty or disagreement keeps the batch on hold. Routine deterministic batches with passed gates follow the existing tier-based sample rates and do not need an extra agent.
