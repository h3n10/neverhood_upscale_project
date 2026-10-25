# Graphics formats

## 2026-10-23 - T5: public image encoder is not a palette-preserving BLB pipeline

YellowAfterlife's web tool reads/writes standalone NHI format 26 and reads NHP palette files. Its writer takes RGBA input, ranks colors by frequency, assigns/reorders indices, and quantizes colors beyond 256 to nearest palette colors; it does not retain an existing 1,024-byte palette or pixel-index mapping. The NHP path affects reader display of formats without embedded palettes; the writer does not use it to preserve a supplied palette. Therefore it is useful for preview/conversion experiments, not a validated palette-preserving encoder or BLB packer. Do not assume NHI format-26 bytes can replace a ScummVM type-2 bitmap resource: the tool has no BLB/type-2 flag, offset, or archive repack support, and no type-2 round-trip was demonstrated.

Blaizer's renderer (a reimplementation based substantially on ScummVM) mirrors type-2 flags, dimensions/position, 1,024-byte embedded palette, uncompressed 8-bit rows padded to 4-byte width, and row/chunk RLE. This helps corroborate the decoded layout but includes no bitmap encoder. A true palette-preserving route still requires writing indexed pixels directly and preserving the exact palette and resource metadata, followed by round-trip and runtime tests.

## 2026-10-23 - T4: palette-preserving encode/repack feasibility

A palette-preserving path is technically viable for compatible type-2 bitmaps: keep pixels as 8-bit palette indices, retain the exact 256-entry x 4-byte (1,024-byte) palette and bitmap flags/position/dimensions, and encode either the normal index plane or a valid row/chunk RLE stream. ScummVM `parseBitmapResource()` consumes these fields directly and sprite drawing writes index bytes into a CLUT8 surface. An RGB-only PNG pipeline is not sufficient; if colors change, a palette remap must update every pixel index consistently, including the transparency convention and shared/dynamic palette users.

This is **not yet a proven end-to-end encoder/repacker**. pyBLB advertises image encoding only for "Format 26", with palette auto-matching and animation encoding incomplete. No round-trip of a representative resource or game/ScummVM runtime test was performed. First implement/validate a lossless decode-to-indexed-encode-to-decode round-trip on a copied bitmap, then verify archive metadata/offsets. Upscaled dimensions remain risky under the fixed 640x480 canvas and animation/collision geometry; visual upscaling does not itself add engine scaling support.


## 2026-10-23 - ANL format mapping

### Resource type IDs (ScummVM Neverhood engine)
- **2 bitmap**: two-byte flags followed by optional fields: dimensions (two `u16`), position (two `u16`), 1,024-byte palette, then image pixels. Flags identify RLE, dimensions, position, palette, and image presence. Sprites are drawn by 8-bit normal or RLE unpackers.
- **3 palette**: palette resources contain 1,024 bytes (256 entries x 4 bytes in the resource representation). The engine transfers the first three bytes per entry as RGB; a palette may also be embedded in a bitmap resource.
- **4 animation**: animation index lists reference frame records and sprite/palette data by offsets. ScummVM reads a frame count, per-frame hash/timing counter, draw rectangle, movement deltas, collision rectangle, and sprite-data offset. Replacing only the visual pixels while ignoring offsets/collision/timing can break animation and interaction.
- **5 data / 6 text**: structured game data and string tables; do not treat these as image assets.

The engine canvas and backbuffer use 640x480 CLUT8 (8-bit indexed) pixels. Palettes are dynamic, so RGB PNG conversion alone is insufficient: retain/reconstruct the exact index-to-color mapping. RLE pixel streams and palettes are tied to resource flags/layout; do not alter image dimensions without updating the record and dependent animation positions/bounds.

### Upscale implications
The original coordinate system remains 640x480. Upscaled replacement bitmaps at 2x/4x dimensions can be clipped, overlap neighboring objects, exceed expected bounds, and desynchronize collision rectangles unless the engine's drawing/scaling path is changed consistently. Nearest-neighbor or other resampling can introduce index/color changes; reserve palette entries and transparency semantics. Keep original indexed assets/metadata as a rollback copy and test a few representative sprites/animations before any archive-wide pass.

### Sources
- Resource types / animation parser: `https://github.com/scummvm/scummvm/blob/master/engines/neverhood/resource.h` and `resource.cpp`
- Bitmap flags and parser: `https://github.com/scummvm/scummvm/blob/master/engines/neverhood/graphics.cpp`
- Indexed screen/palette conversion: `https://github.com/scummvm/scummvm/blob/master/engines/neverhood/screen.cpp`
