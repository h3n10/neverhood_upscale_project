# T10 frame_000 upscale QA report
Date: 2026-10-24. Frame: c.blb video 0, frame_000.

Source: `work_directory/extracted/video/c.blb/0/frames/frame_000.png` (320x240). Metrics via `work_directory/tools/image_qa_metrics.py` (candidate Lanczos-downscaled to source size). Screening only; artistic-intent approval is NOT implied by scores.

| Method | Type | Size | Scale | PSNR dB | SSIM | mean dE | p95 dE | Edge F1 (prec/rec) | Sharpness (lap std) |
|---|---|---|---|---|---|---|---|---|---|
| nearest | classical | 960x720 | 3.00x | 40.297 | 0.998327 | 1.894 | 4.076 | 0.87034 (0.95478/0.79962) | 57.69 |
| lanczos | classical | 960x720 | 3.00x | 40.43 | 0.998552 | 1.925 | 4.057 | 0.85233 (0.90669/0.80411) | 54.39 |
| hqx | pixel-art (3x) | 960x720 | 3.00x | 39.725 | 0.99907 | 1.248 | 3.441 | 0.8077 (0.95627/0.69908) | 16.83 |
| xbr | pixel-art (3x) | 960x720 | 3.00x | 37.91 | 0.99855 | 1.342 | 4.514 | 0.79599 (0.92659/0.69766) | 14.56 |
| epx | pixel-art (3x)| 960x720 | 3.00x | 39.276 | 0.999149 | 1.18 | 3.69 | 0.82477 (0.93406/0.73837) | 20.22 |
| gemini | generative AI (Gemini web) | 2390x1792 | 7.47x | 29.776 | 0.988146 | 6.101 | 12.39 | 0.66097 (0.74107/0.59649) | 8.88 |

Montage: `comparison_frame_000.jpg`. Per-method JSON: `<method>.json`. Gemini source: `work_directory/upscaled/sample_frames/frame_000_gamini_web-upscaled.jfif` (converted to PNG for analysis). Sharpness is Laplacian std at each candidate's own size, so not strictly comparable across sizes.

## Summary
- **Classical (nearest, Lanczos)**: highest PSNR/edge-F1 (~40 dB, F1 0.85-0.87), no content change, but no new detail; nearest keeps blocky/compression artefacts, Lanczos is slightly soft. Safe, faithful baselines.
- **Pixel-art scalers (hqx, xbr, epx)**: best SSIM/dE (dE 1.2-1.3) but smooth the clay texture (sharpness drops ~3x vs nearest, edge recall ~0.70) - "plastic/painted" look that violates clay-texture intent. xbr is worst of these (PSNR 37.9, p95 dE 4.5). Not suited to photographic clay footage.
- **Gemini web (2390x1792, 7.47x, not exactly 3x/4x)**: lowest fidelity: PSNR 29.8 dB, mean dE 6.1 (p95 12.4), edge F1 0.66, mean luminance -2.7 and colour drift (dE 6) and visibly smoothed/repainted, with re-drawn micro-detail. Fails the strict artistic-intent gate in `knowledge/qa_process.md` as-is (colour/texture drift, hallucinated detail; output is also non-integer-scale and 2390 px width needs a crop/resize to a fixed grid). Higher resolution does not equal higher fidelity.
- **Ranking for fidelity**: lanczos ≈ nearest > epx ≈ hqx > xbr >> gemini. No method recovers true detail; none is approved yet. Visual review by a human is required for sign-off.
- Recommendation: use Lanczos 3x as baseline; try a local ML SR model (e.g. Real-ESRGAN/SwinIR with low strength) and a colour-matched/blended Gemini variant before reconsidering generative output.


> **SUPERSEDED by work_directory/qa/T11_frame000_4k/qa_report.md** - the fidelity-to-source metrics here penalise added detail; visually Gemini is best.
