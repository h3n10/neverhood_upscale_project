# T11 frame_000 - 4K UHD (3840x2880, 4:3) comparison incl. Gemini web
Source: c.blb video 0 frame_000 (320x240). All candidates on one 3840x2880 grid (Gemini 2390x1792 Lanczos-resized to it). 3840x2160 UHD at 4:3 would be 2880x2160 pillarboxed; the same images downscale cleanly to that.
Files: `frame_000_<method>_3840x2880.png`, `crops_robot.png`, `crops_wall.png` (same 800x600 crop, 4K px), `uhd_metrics.json`, script `work_directory/tools/uhd_compare.py`.

## Correction of T10
T10 ranked Gemini last. That was a **metric artefact**: PSNR/SSIM/edge-F1 against the 320x240 source reward reproducing the source's blur and blocks and penalise any added detail. They measure "closeness to the low-res source", not perceived quality. Visual inspection at 4K contradicts the T10 ranking, so T10 ranking should not be used for quality.

## Visual result (crops, 4K)
| Method | Detail | Sharpness | Artefacts |
|---|---|---|---|
| nearest | none new | blocky | visible 12x12 pixel blocks |
| lanczos | none new | soft/blurred | ringing, mushy clay |
| hqx (3x/Lanczos) | none new | stair-stepped | blocky edges, flat patches |
| xbr (4x/Lanczos) | none new | smooth shapes | posterised "cartoon/camo" look, clay texture destroyed |
| **gemini** | **best**: clay fingerprints, cracks, teeth, spring/neck, surface grain recovered | **clearly best** | slight colour drift, invented micro-detail |

## No-reference numbers (uhd_metrics.json)
Laplacian variance and gradient are dominated by block/stair edges (nearest "scores" highest) so they are unreliable for sharpness; ignore them. Fidelity at low frequency (<=160x120, below source Nyquist, aligned, no shift found): classical/pixel-art 42-49 dB; Gemini 31.4 dB with mean RGB shift (-3.6, -2.9, +2.8) i.e. slightly cooler/bluer, and no geometric shift (0,0), correlation 0.995. So Gemini keeps composition and layout; remaining difference is small colour tint and the re-synthesised detail.

## Conclusion
- For single-frame visual quality Gemini is the best by a large margin; classical and pixel-art methods only enlarge, they do not add detail.
- Risks to manage (not visible in one still): (1) detail is *inferred* (e.g. the mouth/teeth and neck mechanism are drawn, not recovered) - check against artistic intent per `knowledge/qa_process.md`; (2) ~3-4 level colour tint - fixable by colour-matching Gemini output to the source (per-channel mean/std or low-frequency transfer); (3) temporal flicker/inconsistency across frames for video, and Gemini output is 2390x1792, not native 3840 - a final Lanczos resize to 3840x2880 (or 2880x2160) is needed; (4) cost/volume for thousands of frames (see `knowledge/cloud_api_options.md`).
- Next steps proposed: colour-match Gemini to source; test 3-5 consecutive frames for temporal stability; try a local ML SR (Real-ESRGAN) as a cheaper, more consistent video option and compare against Gemini with human review.

## T12 - Gemini API run (gemini-3-pro-image-preview, imageSize 4K, aspect 4:3), frame_000
Native output 4800x3584 (not exactly 4:3; resized to 3840x2880 for QA, ~0.4% aspect squeeze - crop or pad is needed in production). Files: `frame_000_gemapi_*` (prompt v1), `frame_000_gemapi2_*` (prompt v2), `api_full.png`, `api_crops_*.png`, `api2_crops_*.png`, `api_metrics.json`. Raw outputs and meta (prompt, usage) in `work_directory/upscaled/gemini_test/`.
- **v1** (`tools/scripts/prompts/upscale_v1.txt`): finest detail, but **hue shifted** - green walls became blue (mean RGB shift -20/-11/+24, low-freq PSNR 20.5 dB), plus invented comb-like striations on walls. **Rejected.**
- **v2** (adds explicit COLOR LOCK naming the object hues, bans striped surface patterns): green walls, warm light and composition restored; see metrics line above. Detail comparable to web Gemini; teeth/neck mechanism still drawn by the model (inferred, as in web result).
- Lesson: negative "do not change colours" is not enough; state the expected hues per region. Next: colour-match post-step, multi-frame stability test, human sign-off.

## T12b - prompt v3 = v1 + COLOR LOCK only (`tools/scripts/prompts/upscale_v3.txt`)
Per user request (v1 wording was good, only add colour lock). Result `frame_000_gemapi3_*`, raw `work_directory/upscaled/gemini_test/frame_000_gemini_v3_4800x3584.png` (+ `_v2_`, `_v1_` raws/meta). Comparison: `api3_full.png`, `api3_crops_*.png`, `api3_metrics.json`.
- Hue fixed: walls green, orange-red shapes, warm light; mean RGB shift (-0.8, -3.4, +3.3) vs v1 (-20.5, -10.5, +24.2); low-freq PSNR 31.9 dB vs 20.5.
- v1 detail character retained (clay striation texture kept, since v1 wording kept); v3 ~ v2 in colour accuracy. Residual small blue-ish tint (+3) -> colour-match post-step.
- **v3 is the current best prompt.**

> **Resolutions superseded by work_directory/qa/T14_frame000_uhd/qa_report.md** (3840x2880 squeeze was wrong; correct: 2880x2160 / 3840x2160 pillarbox).
