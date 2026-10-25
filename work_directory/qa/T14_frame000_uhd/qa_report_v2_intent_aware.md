# T15 frame_000 - intent-aware QA (supersedes the scoring in T10/T11/T14 reports; images/sizes from T14 unchanged)
Change requested by user: **added fine detail that matches the artistic intent (clay fingerprints, tool marks, grain, cracks) must not be penalised.** Full-reference PSNR/SSIM/edge-F1 against the 320x240 source are therefore no longer used to rank candidates.

## New method (script `work_directory/tools/uhd_qa_v2.py`, results `qa_v2_metrics.json`)
1. **Gates (automatic, pass/fail)** - only check what must NOT change:
   - G1 layout: band-limited (blur sigma 2 at 320x240, i.e. below half source Nyquist), per-channel colour-matched SSIM vs source >= 0.95 (shape, position, composition; fine detail excluded by the blur).
   - G2 colour: 32x24 block-mean Lab dE vs source: mean <= 6 and max channel shift <= 8 levels (hue/exposure/lighting).
2. **Detail rubric (visual, only for candidates that pass the gates)**, 0-3 on 4K crops: 0 none/artefacts (blocks, posterisation, ringing), 1 sharper edges only, 2 plausible clay surface detail, 3 rich clay detail (fingerprints, tool marks, cracks, grain) consistent with the material and lighting. Deduct only for **intent violations**: new objects/features with no support in the source, changed expression/pose, stylised/plastic/airbrushed look, recolouring. An automatic detail metric was tried and dropped: stair-step and ringing artefacts of classical scalers score as "detail", so it cannot separate real texture from artefacts.

## Results
| Method | G1 SSIM | G2 dE mean / p95 | RGB shift | Gates | Detail (0-3, my visual rating) | Verdict |
|---|---|---|---|---|---|---|
| nearest | 0.999 | 0.6 / 1.3 | -0.5 | pass | 0 (blocks) | faithful, no new detail |
| lanczos | 0.999 | 0.6 / 1.3 | -0.5 | pass | 0-1 (soft, noise amplified) | baseline |
| hqx | 1.000 | 0.2 / 0.7 | ~0 | pass | 0 (stair-steps) | no |
| xbr | 1.000 | 0.3 / 0.8 | ~0 | pass | 0 (posterised, clay lost) | no |
| epx | 1.000 | 0.2 / 0.7 | ~0 | pass | 0 (flat) | no |
| gemini web | 0.988 | 4.5 / 7.4 | -4.4/-2.9/+2.6 | pass | 3 | **good** |
| gemapi v1 | 0.955 | 21.2 / 39.9 | -20.8/-10.3/+21.9 | **FAIL colour** | 3 | rejected (blue walls) |
| gemapi v2 | 0.981 | 4.9 / 8.0 | -1.8/-3.5/+3.1 | pass | 2-3 | good |
| **gemapi v3** | 0.981 | 4.9 / 8.0 | -1.9/-3.4/+3.3 | pass | 3 | **best candidate** (v1 texture + colour lock) |

## Notes
- Classical/pixel-art methods trivially pass the gates because they add nothing; passing gates is necessary, not sufficient. Ranking among gate-passers is by detail rubric, then by smallest colour drift.
- Correction: the mouth/teeth in the Gemini results were previously called "invented". The 320x240 source contains the dark mouth outline in the same place (`crop_mouth_source_vs_v3.png`), so these are plausible reconstructions of existing content, not additions.
- Remaining checks before sign-off: confirm the detail ratings visually yourself (ratings above are the analyst's), ~+3 blue tint -> colour-match post step, multi-frame temporal stability, and watch for features with no source support (the gates cannot detect small local hallucinations; crops review does).
- Thresholds (0.95 / 6 / 8) are provisional, set from this one frame after visually confirming layout equality; recalibrate on more frames.
