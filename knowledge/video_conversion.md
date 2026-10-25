# Video conversion and preservation

## 2026-10-23 - T7: SMK, lossless working formats, cadence, and QA

### Source/decode policy
Project videos are complete raw type-10 SMK2 streams. Preserve the entire input container (including palette/audio/timing/keyframes) and checksum; never edit an SMK header, rate, frame count or palette independently. FFmpeg here decodes the authorized `c.blb#80` sample (320x200, 3 frames, raw rate -8300 = 1000/83 fps, about 12.0482) successfully. See `knowledge/video_formats.md` for established signed-rate convention. Use `-fps_mode passthrough` when extracting frames; do not silently force constant 24/30/60 fps. Store frame PTS/durations/rate in the manifest because a numbered PNG sequence alone does not preserve timing.

### Working and delivery formats
- **PNG sequence:** lossless pixel masters, easy per-frame QA and palette inspection. Keep original indexed PNG/palette where available; record if FFmpeg expanded palette to RGB. Pair with timestamps/manifest.
- **FFV1 in Matroska:** preferred lossless video working/master container for decoded frames; specify a suitable RGB/4:4:4 pixel format and verify round-trip decoded frame pixels, count and timestamps. It is not a Neverhood SMK replacement and does not itself retain original SMK container metadata/codec semantics. Keep the untouched SMK alongside it. FFV1 is standardized in RFC 9043.
- **H.264/H.265/AV1 delivery:** lossy convenience copies only after a lossless master; test encodes and keep original frame rate. `yuv420p` can discard color/chroma detail, and inter-frame codecs may soften texture. HEVC Main 10 improves precision but **10-bit is not HDR**. Record codec/profile, pixel format, bitrate/quality, chroma subsampling, frame rate and color metadata.
- No video encoder/re-encoder into valid Neverhood SMK and no archive integration path was validated by T7. Do not substitute MP4/MKV for SMK inside a BLB.

### Frame rates and temporal feel
Default: retain source FPS, exact frame count and per-frame holds/duration. Do not interpolate intentional clay stop motion; RIFE/optical-flow methods can ghost, warp boundaries/occlusions, invent clay motion, alter rhythm and flicker across independently generated frames. A display-rate conversion may duplicate frames only with durations adjusted to preserve each original hold; use it only as a separate deliverable and confirm duration. Interpolation is a separately approved optional sidecar, never the source-faithful master. De-flicker also changes designed exposure/light variations; use only to address measured unintended instability and A/B visually.

### Color and indexed palette handling
SMK carries indexed/color palette content; the palette lookup is not evidence of a specific camera transfer function or scene luminance. Preserve palette bytes and decoded RGB values. The resource is not a BT.601 YCbCr image merely because it is SD resolution; do not apply a guessed BT.601 matrix to palette RGB. For display/exports, make an explicit documented SDR working-space assumption (e.g., sRGB/BT.709-like) only where no source color profile is available; do not silently reinterpret or transform the palette. If color conversion is needed, use an explicit input/output profile and range with FFmpeg `zscale`, preserve source lookup as reference, compare decoded colors, and tag the actual output transform. Never assign HDR tags without converting the signal correctly. Guidance for UHD/HDR is in `knowledge/uhd_hdr.md`.

### Evaluation plan
- Validate decode exit code, frame count, size, original and output SHA-256, timestamps, frame rate, stream mapping, audio presence, palette colors, output pixel format and color tags. Check PNG/FFV1 lossless pixel round-trip on representative frames.
- Compare side by side and at native/target viewing size; inspect movement, clay texture, fine edges, dark/bright regions, palette transitions and transitions/cadence. Build contact sheets and watch/flicker-check full clips; include unchanged/source and edited frames in comparisons.
- PSNR and SSIM detect pixel/signal change only; LPIPS is a learned natural-image feature metric and can mis-score stylized clay; VMAF targets perceived video coding quality, not historical/artistic fidelity or invented detail. Use them against a valid reference only as secondary evidence. No single metric establishes restoration correctness. With no true high-resolution reference, visual and temporal review plus exact decode/round-trip checks are primary.

### Sources
- FFmpeg formats/demuxers and Smacker decoder: https://ffmpeg.org/ffmpeg-formats.html ; https://github.com/FFmpeg/FFmpeg/blob/master/libavformat/smacker.c
- FFmpeg filters and timing/color/metrics tools: https://ffmpeg.org/ffmpeg-filters.html ; https://github.com/FFmpeg/FFmpeg/blob/master/doc/filters.texi
- FFV1 standard: RFC 9043, https://www.rfc-editor.org/rfc/rfc9043.html ; x265 CLI: https://x265.readthedocs.io/en/master/cli.html
- RIFE NCNN (one example interpolation implementation): https://github.com/nihui/rife-ncnn-vulkan
- Local observed sample/decoder evidence: `knowledge/video_formats.md`; local FFmpeg path: `C:\Users\User\tools\ffmpeg\bin\ffmpeg.exe`.
