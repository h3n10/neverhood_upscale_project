# QA release checklist

- [ ] Source is read-only; original hash/palette/timing preserved.
- [ ] Rights-holder/project authority and user method/style approval documented.
- [ ] If external transfer: named provider/region/plan/endpoint and retention/training/subprocessor review explicitly approved. No API secret in code/log.
- [ ] Golden set and per-asset manifest frozen; model/weights/prompts/params versioned.
- [ ] Baseline and candidate side-by-side/blink reviewed; exact dimensions, aspect and color management checked.
- [ ] Every output passes decode, checksum, dimension, palette/color, frame count/PTS/audio and downscale-back checks.
- [ ] Structural/object diff and human review detect no unauthorized added/removed content, pose, silhouette, mood, lighting or palette drift.
- [ ] Video: cadence, scene cuts, neighbor consistency and temporal flicker/warp reviewed at source and delivery speed; no unapproved interpolation.
- [ ] Tier-specific human sampling complete; all automated outliers adjudicated.
- [ ] Golden regressions passed for current model/version and approved examples.
- [ ] All rejects/rework, metrics, contact sheets, costs, exceptions and output hashes logged.
- [ ] Artist + user + manager signoffs complete; analyst handoff only after approval.
