# BLB container format

## 2026-10-23 - T5: independent implementation corroborates compression-101 aliases

Blaizer's `ResourceMan.pm` resolves `compr_type == 0x65` by treating `disk_size` as the next resource key and redirecting the alias to that entry; `Archive.c` confirms the 20-byte directory record layout and DCL handling for compression 3. This explicitly corroborates our s.blb alias interpretation and is the clearest inspected implementation of the redirect workflow. Its project README says it is an incomplete reimplementation based substantially on ScummVM, so it is corroborating implementation evidence, not independent proof of the original executable's behavior. ScummVM `blbarchive.cpp` still handles only compression 1/3. Preserve the 84 aliases/hash links exactly; runtime compatibility remains a test requirement.

## 2026-10-23 - T4: s.blb dummy-alias records resolved (ANL)

The apparent `s.blb` corruption is a parser interpretation error for 84 **type-4/compression-101 dummy aliases**, not 84 payloads. In these rows `offset=0` and `size=0`; `disk_size` is a 32-bit **resource hash**, not a byte count. The independent community pyBLB `extract()` implementation explicitly handles compression 101 by calling `getFile(file.diskSize)`. Local hash-lookup testing confirms all 84 references resolve to existing hashes in `s.blb`, each target is a normal type-4/compression-3 payload, with no self-links or alias cycles. The other 274 type-4 records are compression 3. After teaching `blb_inspect.py` this alias rule, `s.blb` has zero invalid payload ranges and zero payload overlaps; its actual type-4 payload bytes total 16,608,413 B.

**Runtime caveat:** ScummVM `blbarchive.cpp` only handles outer compression 1 and 3; it errors for other IDs, including 101. The community reader's hash-alias behavior is empirically supported for this archive, but how the original runtime reaches/avoids these alias rows remains uncertain. Preserve the alias rows and their hash links; do not rewrite them as payloads or drop them during repacking. References: `sources.md` (ScummVM `blbarchive.cpp`; pyBLB `pyBLB.py`).


## 2026-10-23 - ANL read-only header/directory audit

ScummVM's `BlbArchive` and the independent pyBLB reader agree on this little-endian structure:

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | signature `0x02004940` (`40 49 00 02`) |
| 0x04 | 2 | version/ID `7` |
| 0x06 | 2 | extended-data byte count |
| 0x08 | 4 | total file length; must match archive length |
| 0x0C | 4 | entry count |
| 0x10 | count * 4 | ordered resource hashes (`uint32`) |
| following | count * 20 | ordered records described below |
| following | ext-data size | shared extended-data block |
| later | variable | payload regions at each record's offset |

Each 20-byte record is `type:u8`, `compression:u8`, `extDataOffset:u16`, `timestamp:u32`, `offset:u32`, `diskSize:u32`, `size:u32`. The hash at index *i* belongs to record *i*. `extDataOffset` is one-based into the shared extended-data block; zero means absent. For example, sound resources use the first referenced byte as a codec shift value.

Engine-supported outer compression IDs: **1 = stored/uncompressed**, **3 = DCL-compressed**. For ID 3, payload expands to the record's `size`; for ID 1, data is read directly. Resource types are in `graphics_formats.md`, `video_formats.md`, and `audio_formats.md`. Type 10 Smacker streams are passed as bounded raw streams; do not apply BLB DCL a second time to those entries.

### Structural validation and current exception
`work_directory/tools/blb_inspect.py` validates signature/version/declared length, reads hashes and records, records offsets/sizes, checks extended-data references, payload bounds and overlaps, and samples SMK headers. Full output is `work_directory/scratch/blb_manifest.json`.

For `a`, `c`, `hd`, `i`, `m`, `s`, and `t`, the alias-aware inspector finds no out-of-range payloads, invalid ext-data references, or payload overlaps. For `s.blb`, see the T4 note above: compression-101 dummy rows store resource hashes in `disk_size`, not ranges.

### Repacking invariants
Preserve entry order and hash-to-record association, all timestamps unless intentionally changed, extended-data byte layout and one-based offsets, type/compression semantics, stored/expanded sizes for real payloads, hash-linked dummy-alias semantics, and valid offsets. Rebuild file size and all dependent offsets; validate with a parser and, ultimately, the game/ScummVM. Never append an image file into an archive without updating the directory. Keep source archives read-only.

### Sources
- ScummVM BLB parser: `https://github.com/scummvm/scummvm/blob/master/engines/neverhood/blbarchive.cpp`
- Header/entry structures: `https://github.com/scummvm/scummvm/blob/master/engines/neverhood/blbarchive.h`
- Independent pyBLB implementation/docs: `https://github.com/michal4132/pyBLB`
