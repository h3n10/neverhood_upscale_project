# Game structure

## 2026-10-23 - T3/T4 update: verified sample and s.blb aliases

The shortest inspected video sample was extracted and decoded: `c.blb` entry 80, 320x200, 3 frames, raw rate -8300, playable SMK2 (details in `video_formats.md`). The old s.blb invalid-range reports were compression-101 hash aliases: 84/84 resolve to compression-3 type-4 records in the same archive; the alias-aware parser now reports zero out-of-range payloads/overlaps. The ScummVM runtime's lack of compression-101 handling remains a compatibility caveat.


## 2026-10-23 - ANL archive inventory

### Archive summary (local source files; byte sizes)
| Archive | Bytes | Entries | Directory types / observed contents |
|---|---:|---:|---|
| `a.blb` | 50,571,893 | 329 | type 7 sound 295; type 8 music 34 |
| `c.blb` | 241,856,188 | 83 | type 2 bitmap 1; type 10 video 82 |
| `hd.blb` | 4,279,716 | 74 | type 2 bitmap 73; type 10 video 1 |
| `i.blb` | 42,015,045 | 1,316 | type 2 bitmap 1,183; type 3 palette 54; type 4 animation 13; type 5 data 54; type 6 text 12 |
| `m.blb` | 53,797,472 | 13 | type 10 video 13 (making-of grouping supported by pyBLB docs) |
| `s.blb` | 16,622,792 | 358 | type 4; 274 compression-3 payloads plus 84 compression-101 hash aliases targeting those payloads; runtime caveat documented in `blb_format.md` |
| `t.blb` | 228,979,468 | 577 | type 2 bitmap 122; type 10 video 455 |

Across all headers, 2,750 directory rows are declared. The 84 `s.blb` compression-101 rows are hash aliases (all 84 resolve locally); preserve them as aliases, not payload ranges. The other six archives have in-range, non-overlapping payloads under the inspected layout.

### Engine and archive roles
ScummVM's Neverhood resource manager loads archives in this order: `a.blb`, `c.blb`, `hd.blb`, `i.blb`, optional `m.blb` (omitted for Japanese language), `s.blb`, `t.blb`. Demo mode uses `a.blb` and `nevdemo.blb`. Archive entries are indexed by 32-bit resource hash. If the same hash occurs more than once, the manager keeps the entry with the newer timestamp. This makes archive ordering, hash identity, and timestamps significant for replacement/repacking.

Observed roles align with pyBLB's public documentation: `a` audio; `c` cutscene videos; `i` sprites/background resources; `m` making-of videos; `hd` radio-spin/UI resources; `t` first-person videos. pyBLB labels `s` level/animation data but marks that role uncertain; its compression-101 hash aliases are resolved structurally, with a ScummVM compatibility caveat.

### Video header sample audit
All 551 type-10 entries in `c`, `hd`, `m`, and `t` start with `SMK2` in the sampled 20-byte headers and expose a little-endian width, height, frame count, and signed raw frame-rate field. Dimensions/frame-count ranges by archive:
- `c.blb`: 82 videos; 43 at 320x240, 15 at 448x240, 24 at 320x200; 3-3,350 frames.
- `hd.blb`: 1 at 320x240; 91 frames.
- `m.blb`: 13 at 320x240; 338-1,642 frames.
- `t.blb`: 455 at 320x240; 2-180 frames.

Raw frame-rate fields were retained in the manifest; they have not been converted to playback rates. SMK header reads are metadata inspection only, not bulk extraction.

### Root/installer observations
`readme.txt` identifies the Windows 95 release and minimum-era requirements (Pentium 75 MHz, 8 MB RAM / 16 MB recommended, SVGA, 1 MB VRAM, quad-speed CD-ROM). It also states that at least 256 display colors are required and warns against changing monitor resolution during play; it notes legacy accelerated-video-driver problems and an ESS1888/DirectX 3 sound-driver issue. `AUTORUN.INF` launches `SETUP95.EXE` and points to `nhood.ico`; files were inspected as metadata/text only, never executed. Sizes: `SETUP.EXE` 5,904 B; `setup95.exe` 202,240 B; `nhood.ico` 7,590 B; `AUTORUN.INF` 213 B; `readme.txt` 10,955 B. Non-DirectX setup subfolder names present: `3dlabs`, `aztech`, `creative`, `crystal`, `ess`; no files were listed in those folders. `setup/directx` was deliberately skipped.

### Sources
See `sources.md` for engine source URLs and community references. Key primary sources: ScummVM `neverhood.cpp`, `resourceman.cpp`, and `blbarchive.cpp`.
