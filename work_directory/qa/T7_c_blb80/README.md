# T7 classical scaler comparison

- Inputs: `work_directory/extracted/video/c.blb/80/frames/frame_01.png` and `frame_02.png` (320x200, paletted PNG). Byte-identical, SHA-256 `d668f6501596a1c02fe60618e06eafda0adbfab5844e51de3a7d60b779c75e51`; this is a static sample, so temporal conclusions do not generalize.
- Reproduce from project root:
  `python work_directory/tools/compare_classical_scalers.py --input-dir work_directory/extracted/video/c.blb/80/frames --output-dir work_directory/qa/T7_c_blb80 --ffmpeg C:\Users\User\tools\ffmpeg\bin\ffmpeg.exe`
- Ran with local FFmpeg `2026-10-22-git-bf0e831606` (full build). Outputs per frame: 3x 960x600 PNG from FFmpeg nearest, Lanczos, HQx, xBR and EPX; contact sheets `comparison_frame_01.jpg` and `_02.jpg`.
- Visual check: nearest is block-preserving; Lanczos slightly smooths; HQx/xBR impose stronger edge shaping; EPX is block-oriented. Contact-sheet display is reduced and only supports screening, not final selection. Prefer no aggressive filter; compare full-size motion clips before selection.
- No numeric perceptual metric, AI restoration, frame-rate conversion, HDR conversion, or game-file modification was performed.
