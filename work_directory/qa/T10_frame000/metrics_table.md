# T10 frame_000 upscale QA report

Source: `work_directory/extracted/video/c.blb/0/frames/frame_000.png` (320x240). Metrics via `work_directory/tools/image_qa_metrics.py` (candidate Lanczos-downscaled to source size). Screening only; artistic-intent approval is NOT implied by scores.

| Method | Type | Size | Scale | PSNR dB | SSIM | mean dE | p95 dE | Edge F1 (prec/rec) | Sharpness (lap std) |
|---|---|---|---|---|---|---|---|---|---|
| nearest | classical | 960x720 | 3.00x | 40.297 | 0.998327 | 1.894 | 4.076 | 0.87034 (0.95478/0.79962) | 57.69 |
| lanczos | classical | 960x720 | 3.00x | 40.43 | 0.998552 | 1.925 | 4.057 | 0.85233 (0.90669/0.80411) | 54.39 |
| hqx | pixel-art (3x) | 960x720 | 3.00x | 39.725 | 0.99907 | 1.248 | 3.441 | 0.8077 (0.95627/0.69908) | 16.83 |
| xbr | pixel-art (3x) | 960x720 | 3.00x | 37.91 | 0.99855 | 1.342 | 4.514 | 0.79599 (0.92659/0.69766) | 14.56 |
| epx | pixel-art (2x) | 960x720 | 3.00x | 39.276 | 0.999149 | 1.18 | 3.69 | 0.82477 (0.93406/0.73837) | 20.22 |
| gemini | generative AI (Gemini web) | 2390x1792 | 7.47x | 29.776 | 0.988146 | 6.101 | 12.39 | 0.66097 (0.74107/0.59649) | 8.88 |
