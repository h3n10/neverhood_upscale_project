## 2026-10-24 - T9: motion-verified animated sample

Extracted `c.blb` entry 0 (different from the earlier static/3-frame entry 80) to `work_directory/extracted/video/c.blb/0/`. It is raw SMK2, 320x240, 85 frames, 541,428 bytes, raw rate -6666 (`50000/3333` = 15.0015 fps), 5.6661 s per FFprobe, SHA-256 `6e9413a1330d3ca5bef086bfe12bd311be5aaa2a660b0f539e82e72e06f5ef17`. FFmpeg decoded all 85 frames with exit code 0.

Frames 0, 42, and 84 were saved as PNGs. Their decoded RGB hashes are distinct; pairwise differences are 35,744, 42,334, and 23,260 changed pixels out of 76,800, confirming substantial real clay-character motion rather than a static clip. `metadata.json` records the source frame indices, PNG/RGB hashes, and difference statistics. `work_directory/tools/extract_smk_motion_frames.py` reproduces this check.

# Video formats

## 2026-10-23 - T3/T4: SMK sample verified and signed rate decoded (ANL)

Extracted BLB `c.blb`, entry 80 to `work_directory/extracted/video/c.blb/80/sample.smk` (31,568 B, exact raw type-10 payload, SHA-256 `9a329d76824941c57fb6a0d5085c0f8dabee571463355dc6f13bd064e80cb676`). Metadata is beside it in `metadata.json`: SMK2, 320x200, 3 frames, raw signed rate -8300. Local ffmpeg 7.1 decoded successfully to a null muxer with exit code 0 and exactly 3 output frames; it reports 12.05 fps and 0.25 s duration.

FFmpeg `libavformat/smacker.c` resolves the signed field as a frame-time increment. A negative raw value is its absolute value in 1/100,000-second units; positive values are multiplied by 100 and thus are milliseconds in the same time base. Therefore `fps = 100000/abs(raw)` for negative fields (e.g. -8300 = 1000/83, approximately 12.0482 fps), and `fps = 1000/raw` for positive fields. No zero-valued rate field was observed, so its interpretation is not asserted here. This matches ffmpeg's stream reports. Keep the raw signed field when auditing and do not rewrite it independently of frames/timestamps.


## 2026-10-23 - SMK header audit

Type **10** resources in `c.blb`, `hd.blb`, `m.blb`, and `t.blb` are bounded raw streams. The sampled/all 551 entries start with `SMK2`; the first 20 bytes provide little-endian width, height, frame count, and a signed raw rate field. ScummVM uses its Smacker decoder and a palette-aware surface. They are not BLB DCL payloads: every observed type-10 entry uses outer compression ID 1.

| Archive | Videos | Resolution distribution | Frames |
|---|---:|---|---:|
| c | 82 | 320x240 (43), 448x240 (15), 320x200 (24) | 3-3,350 |
| hd | 1 | 320x240 (1) | 91 |
| m | 13 | 320x240 (13) | 338-1,642 |
| t | 455 | 320x240 (455) | 2-180 |

Known raw signed frame-rate values include -6666, -6700, -7100, -8300, and -8333. Their signed units are now described in the T4 note above; the archive audit retains raw values alongside any derived fps. Other tracks (audio, palette, keyframe data) are part of the SMK container; preserve full stream consistency when encoding/replacing video. Do not edit headers or frame counts independently of the media stream.

Engine code uses 640x480 coordinates and provides a double-surface Smacker presentation path for certain scenes; that is not evidence of a general engine-wide high-resolution scaling hook. The 448x240 and 320x200 cutscenes are expected variants rather than parsing errors.

During the initial T1 header-only audit, no video data was extracted or re-encoded. `work_directory/tools/blb_inspect.py` reads only each type-10 header to record format, dimensions, frame count, and raw rate.

### Sources
- ScummVM playback: `https://github.com/scummvm/scummvm/blob/master/engines/neverhood/smackerplayer.cpp`
- ScummVM screen and palette path: `https://github.com/scummvm/scummvm/blob/master/engines/neverhood/screen.cpp`
- Public extractor capability notes (community, not a codec specification): `https://github.com/michal4132/pyBLB`
