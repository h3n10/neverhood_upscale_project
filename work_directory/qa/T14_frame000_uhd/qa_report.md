# T14 frame_000 - corrected UHD resolutions (supersedes T10/T11 sizes)
## What was wrong
T11/T12 used 3840x2880 (not a UHD height) and squeezed the API output (4800x3584, 1.339:1) and web Gemini (2390x1792) into 4:3. 
## Correct targets
- Source 320x240 (4:3). UHD height 2160 -> **2880x2160 = exactly 9x** (primary master, no distortion).
- **3840x2160 UHD canvas = 2880x2160 pillarboxed** (480 px black each side; `*_3840x2160_pillarbox.png`). Stretching 4:3 to 16:9 is not used.
- Gemini outputs are centre-cropped to exact 4:3 (API 4800x3584 -> 4776x3582; web 2390x1792 -> 2388x1791; 12 px/1 px lost per side, no squeeze) then Lanczos to 2880x2160. Natural API size is limited by the model (imageSize 4K returns ~4800x3584); it cannot be set to 3840x2160 exactly, so a final resize is required.
## Files (all in this folder)
`frame_000_<method>_2880x2160.png` and `_3840x2160_pillarbox.png` for nearest, bicubic, lanczos, hqx, xbr, epx, gemini (web), gemapi (prompt v1), gemapi2 (v2), gemapi3 (v3 = v1 + color lock). Montages: `full_compare.png`, `crops_robot.png`, `crops_wall.png`. Metrics: `uhd_metrics.json` (script `work_directory/tools/uhd_compare.py`).
## Result (aligned low-frequency fidelity; higher = closer to source colours/layout)
| Method | Low-freq PSNR dB | Mean RGB shift | Visual |
|---|---|---|---|
| nearest | 42.0 | -0.3/-0.4/-0.5 | 9x9 blocks, noisy dither visible |
| lanczos | 42.6 | -0.5/-0.5/-0.5 | soft, dithering noise amplified |
| hqx | 48.7 | ~0 | stair-stepped, flat |
| xbr | 45.9 | ~0 | posterised |
| epx | 47.0 | ~0 | flat, plastic |
| gemini web | 30.6 | -3.7/-2.9/+2.8 | detailed clay, slight tint |
| gemapi v1 | 20.2 | -20.9/-10.6/+24.3 | detailed but **blue walls** |
| gemapi v2 | 29.7 | -0.9/-3.6/+2.9 | detailed, correct hue |
| **gemapi v3** | 29.7 | -1.1/-3.5/+3.3 | detailed, correct hue, v1 texture character |
Note: low-freq PSNR drops ~2 dB vs T11 only because the crop removes a few edge pixels the source still contains; ranking unchanged. Fidelity metrics penalise added detail, so judge visually: classical/pixel-art add no detail; Gemini adds clay detail; v3 is the best prompt (hue-correct). Remaining: ~+3 blue tint (colour-match step), temporal test, human sign-off.

> **Scoring superseded by qa_report_v2_intent_aware.md** (added detail matching artistic intent is not penalised).
