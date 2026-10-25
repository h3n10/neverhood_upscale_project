# Audio formats

## 2026-10-23 - engine stream analysis

`a.blb` has 295 type-7 sound effects and 34 type-8 music resources. The engine reads the first referenced extended-data byte as `shiftValue` and plays resources through `NeverhoodAudioStream` at **22,050 Hz, mono**.

- `shiftValue == 0xFF`: raw signed 16-bit little-endian PCM samples.
- Otherwise: signed 8-bit differential samples are accumulated from the previous value, then left-shifted by `shiftValue` to produce 16-bit samples.
- The BLB compression layer (IDs 1/3) is separate from this audio sample encoding. The local audit finds a nonzero extended-data reference for all 329 `a.blb` entries.

Do not confuse type 7/8 with the audio tracks multiplexed inside SMK videos. Encoding replacements must keep duration/sample count, loop behavior, and the per-resource extended-data shift semantics compatible; no audio extraction/re-encoding was done in this task.

### Sources
- Engine audio decoder/player: `https://github.com/scummvm/scummvm/blob/master/engines/neverhood/sound.cpp`
- BLB extended-data mapping: `https://github.com/scummvm/scummvm/blob/master/engines/neverhood/blbarchive.cpp`
