#!/usr/bin/env python3
"""Generate docs/game_tree.md and docs/upscaling_plan.md from the real archives (read-only).

  python gen_docs.py                 # regenerate both docs (checklist marks in the plan are PRESERVED)
  python gen_docs.py --mark video:c.blb:0-84 --stage E --state x     # tick a stage for videos by id range
  python gen_docs.py --mark item:graphics.palette-map --state x      # tick a checklist item by key

Plan marks: `x` done, `~` partial, ` ` open. Per-video stages: E=extracted, F=frames decoded,
U=upscaled, Q=QA pass, R=repacked/playable. Row ids are `<archive>#<entry id>` = extract_all.py ids.
"""
from __future__ import annotations
import argparse, collections, json, pathlib, re, struct, sys, datetime

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import blb_inspect, extract_all as xa  # noqa: E402

DOCS = ROOT / "docs"
CACHE = ROOT / "work_directory" / "scratch" / "docs_cache.json"
ARCS = ["a", "c", "hd", "i", "m", "s", "t"]
ROLE = {"a": "audio: 295 sound effects + 34 music", "c": "cutscene videos (+1 bitmap)", "hd": "UI / radio-spin bitmaps (+1 video)",
        "i": "backgrounds, sprites, palettes, animation lists, data, text", "m": "making-of videos",
        "s": "type-4 records incl. 84 compression-101 hash aliases (role uncertain: level/animation/static data)",
        "t": "first-person transition videos (455) + bitmaps (122)"}


def collect():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    out = {}
    for n in ARCS:
        p = ROOT / "DATA_source" / f"{n}.blb"
        a = blb_inspect.inspect(p)
        with p.open("rb") as fh:
            for e in a["entries"]:
                if e["type"] == 2:
                    try:
                        d = xa.payload(fh, e, None, limit=16)
                        f = struct.unpack_from("<H", d, 0)[0]
                        w = h = 1
                        q = 2
                        if f & 2:
                            w, h = struct.unpack_from("<HH", d, q)
                        e["bmp"] = {"flags": f, "w": w, "h": h, "rle": bool(f & 1), "pal": bool(f & 8)}
                    except Exception as ex:
                        e["bmp"] = {"error": str(ex)}
        a.pop("path", None)
        out[n] = a
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(out), encoding="utf-8")
    return out


def fps(raw):
    return xa.fps_of(raw)


def mb(n):
    return f"{n / 1048576:,.1f} MB"


def vids(a):
    return [e for e in a["entries"] if e["type"] == 10 and "video_header" in e]


def auds(a):
    r = []
    for e in a["entries"]:
        if e["type"] in (7, 8):
            sh = int(e.get("extdata_first_byte_hex", "FF"), 16)
            samples = e["size"] // 2 if sh == 0xFF else e["size"]
            r.append((e, sh, samples / xa.SAMPLE_RATE))
    return r


# ------------------------------------------------------------------ game_tree.md
def game_tree(D):
    L = []
    w = L.append
    w("# Neverhood game tree\n")
    w(f"_Generated {datetime.date.today()} by `work_directory/tools/gen_docs.py` from the real archives in `DATA_source/` (read-only). "
      "Counts, sizes, resolutions and frame counts are measured, not estimated. Hand-written sections are marked._\n")
    w("## 1. Top level\n")
    w("```")
    w("The Neverhood (CD, Win95 release)")
    root = ROOT
    for f in sorted(root.iterdir()):
        if f.name in ("AUTORUN.INF", "SETUP.EXE", "nhood.ico", "readme.txt", "setup95.exe"):
            w(f"├── {f.name:<14} {f.stat().st_size:>9,} B")
    w("├── setup/            installer vendor folders (3dlabs, aztech, creative, crystal, ess; directx skipped) - reference only")
    w("└── DATA/ (here: DATA_source/)   all game content, 7 BLB archives")
    tot = 0
    for i, n in enumerate(ARCS):
        a = D[n]
        tot += a["file_bytes"]
        br = "└──" if i == len(ARCS) - 1 else "├──"
        pad = "    " if i == len(ARCS) - 1 else "│   "
        w(f"    {br} {n}.blb  {a['file_bytes']:>12,} B  {a['entry_count']:>5} entries  - {ROLE[n]}")
        types = a["type_details"]
        tl = list(types.items())
        for j, (t, v) in enumerate(tl):
            b2 = "└──" if j == len(tl) - 1 else "├──"
            extra = ""
            if t == "10":
                vs = vids(a)
                res = collections.Counter(f"{e['video_header']['width']}x{e['video_header']['height']}" for e in vs)
                fr = [e["video_header"]["frame_count"] for e in vs]
                extra = f"; {', '.join(f'{k} x{c}' for k, c in res.most_common())}; frames {min(fr)}-{max(fr)} (sum {sum(fr):,})"
            elif t in ("7", "8"):
                al = [x for x in auds(a) if x[0]["type"] == int(t)]
                extra = f"; {sum(x[2] for x in al) / 60:.1f} min total @22.05 kHz mono"
            elif t == "2":
                bm = [e["bmp"] for e in a["entries"] if e["type"] == 2 and "w" in e["bmp"]]
                dims = collections.Counter(f"{b['w']}x{b['h']}" for b in bm)
                big = dims.get("640x480", 0)
                extra = f"; {big} full-screen 640x480, {len(bm) - big} sprites/partials; {sum(b['rle'] for b in bm)} RLE; {sum(b['pal'] for b in bm)} with embedded palette"
            w(f"    {pad}{b2} type {t:>2} {v['name']:<9} x{v['count']:<5} {v['uncompressed_bytes']:>12,} B expanded{extra}")
    w(f"```\n\nTotal: {tot:,} B ({mb(tot)}) in 7 archives, {sum(D[n]['entry_count'] for n in ARCS):,} directory entries.\n")

    w("## 2. BLB structure and resource types (hand-written; see `knowledge/blb_format.md`)\n")
    w("""```
BLB: header(16 B: sig 0x02004940, ver 7, extDataSize, fileSize, count)
     | count x u32 resource hash | count x 20-byte record | ext-data block | payloads
record = type:u8 comp:u8 extOff:u16 timestamp:u32 offset:u32 diskSize:u32 size:u32
comp   = 1 stored | 3 PKWARE-DCL | 101 (s.blb only) alias: diskSize holds another entry's hash
engine = hash lookup over a,c,hd,i,m,s,t in that order; duplicate hash -> newest timestamp wins
```
| type | name | content | engine handling |
|---:|---|---|---|
| 2 | bitmap | flags(u16: 1 RLE, 2 dims, 4 pos, 8 palette, 16 image) [w,h][x,y][1024 B palette][pixels] | 8-bit indexed sprite/background; RLE = rows/chunks of (skip,copy) |
| 3 | palette | 256 x 4 B (RGB used) | dynamic palette, loaded into 640x480 CLUT8 screen |
| 4 | animation | frame list: hash, ticks, draw rect, delta, collision rect, sprite offset | sprites with timing and hit boxes |
| 5 | data | structured tables (hint/rect/message/track lists) | static data |
| 6 | text | string tables | text |
| 7 | sound | 8-bit delta (shift in ext data) or raw s16 (shift 0xFF), 22050 Hz mono | one-shot SFX |
| 8 | music | same codec as 7 | looped/streamed music |
| 10 | video | raw Smacker SMK2 stream (never DCL) | SmackerPlayer, 640x480 surface |
""")

    w("## 3. Archives -> entries by type\n")
    w("| archive | type | count | stored B | expanded B | size min..max (expanded) | compression |\n|---|---|---:|---:|---:|---|---|")
    for n in ARCS:
        for t, v in D[n]["type_details"].items():
            w(f"| {n}.blb | {t} {v['name']} | {v['count']} | {v['compressed_bytes']:,} | {v['uncompressed_bytes']:,} | "
              f"{v['size_min']:,}..{v['size_max']:,} | {v['compression_counts']} |")
    w("")

    w("## 4. Videos (SMK) by archive\n")
    w("Scene -> video mapping: BLB entries are identified only by a 32-bit hash; names/scenes are bound in ScummVM module code "
      "(`Module####` classes call `SmackerScene`/`playVideo` with hash constants). That table is **not** in the data files, so videos are "
      "listed under their archive/role below; scene attribution is TODO (extract hash constants from the ScummVM sources).\n")
    for n in ["c", "hd", "m", "t"]:
        vs = vids(D[n])
        if not vs:
            continue
        res = collections.Counter(f"{e['video_header']['width']}x{e['video_header']['height']}" for e in vs)
        fr = sum(e["video_header"]["frame_count"] for e in vs)
        dur = sum(e["video_header"]["frame_count"] / fps(e["video_header"]["frame_rate_raw"]) for e in vs if fps(e["video_header"]["frame_rate_raw"]))
        rates = collections.Counter(e["video_header"]["frame_rate_raw"] for e in vs)
        w(f"### {n}.blb - {len(vs)} videos, {fr:,} frames, {dur / 60:.1f} min, {mb(sum(e['disk_size'] for e in vs))}")
        w(f"Resolutions: {dict(res)}. Raw rate fields: {dict(rates)}.\n")
        w("<details><summary>per-video list</summary>\n")
        w("| id | hash | WxH | frames | fps | s | bytes |\n|---:|---|---|---:|---:|---:|---:|")
        for e in vs:
            h = e["video_header"]
            f = fps(h["frame_rate_raw"])
            w(f"| {e['id']} | {e['hash']} | {h['width']}x{h['height']} | {h['frame_count']} | {f:.2f} | {h['frame_count'] / f:.1f} | {e['disk_size']:,} |")
        w("\n</details>\n")

    w("## 5. Audio\n")
    a = D["a"]
    al = auds(a)
    w(f"`a.blb` holds all stand-alone audio: {sum(1 for x in al if x[0]['type'] == 7)} sounds (type 7) and {sum(1 for x in al if x[0]['type'] == 8)} music tracks (type 8), "
      f"{sum(x[2] for x in al) / 60:.1f} min total, 22,050 Hz mono. Shift-value (ext data byte) histogram: "
      f"{dict(collections.Counter(f'0x{x[1]:02X}' for x in al).most_common())}. SMK videos also carry their own audio tracks (extract with `extract_all.py --video-audio`).\n")
    w("Longest music/sound entries:\n")
    w("| id | hash | kind | shift | comp | seconds | stored B |\n|---:|---|---|---:|---:|---:|---:|")
    for e, sh, d in sorted(al, key=lambda x: -x[2])[:20]:
        w(f"| {e['id']} | {e['hash']} | {e['type_name']} | {sh} | {e['compression']} | {d:.1f} | {e['disk_size']:,} |")
    w("\n<details><summary>all 329 audio entries</summary>\n")
    w("| id | hash | kind | shift | seconds |\n|---:|---|---|---:|---:|")
    for e, sh, d in al:
        w(f"| {e['id']} | {e['hash']} | {e['type_name']} | {sh} | {d:.2f} |")
    w("\n</details>\n")

    w("## 6. Graphics, palettes, animations, data\n")
    for n in ["i", "hd", "t", "c"]:
        bm = [e for e in D[n]["entries"] if e["type"] == 2 and "w" in e["bmp"]]
        if not bm:
            continue
        dims = collections.Counter(f"{e['bmp']['w']}x{e['bmp']['h']}" for e in bm)
        w(f"- **{n}.blb**: {len(bm)} bitmaps; {sum(e['bmp']['rle'] for e in bm)} RLE, {sum(e['bmp']['pal'] for e in bm)} with embedded palette "
          f"(the rest use a palette set by scene/type-3 entry). Top sizes: " + ", ".join(f"{k} x{c}" for k, c in dims.most_common(8)) + ".")
    ti = D["i"]["type_details"]
    w(f"- **i.blb** also: {ti['3']['count']} palettes (type 3, 1,024 B each), {ti['4']['count']} animation lists (type 4), {ti['5']['count']} data tables (type 5), {ti['6']['count']} text tables (type 6).")
    ts = D["s"]["type_details"]["4"]
    w(f"- **s.blb**: {ts['count']} type-4 records = {ts['count'] - ts.get('dummy_alias_count', 0)} real payloads + {ts.get('dummy_alias_count', 0)} compression-101 hash aliases (preserve on repack).")
    w("- Canvas: 640x480 CLUT8. Sprites carry (x,y) position inside the scene; animations add per-frame deltas and collision rects. Palettes are swapped at runtime.\n")

    w("## 7. Engine elements (hand-written; from ScummVM `engines/neverhood`, names may drift between versions)\n")
    w("""```
NeverhoodEngine (neverhood.cpp)            main loop, 640x480 CLUT8 screen, archives a,c,hd,i,m,s,t
├── ResourceMan (resourceman.cpp)          hash -> newest-timestamp BLB entry; BlbArchive (blbarchive.cpp)
├── Screen / Palette (screen.cpp, palette.cpp)  backbuffer + dynamic palette fades, microtiles dirty rects
├── GameModule (gamemodule.cpp) -> Module  scene manager; current module/scene ids kept in GameVars
│   ├── Module1000 .. Module3000           world/level modules ("Module1000" = start area, 1100..1900, 2100..2800, 3000 ...)
│   │   └── Scene subclasses (Scene####)   each Scene owns Backgrounds, Sprites, Klaymen, hit rects, music
│   ├── MenuModule, CreditsScene, DiskplayerScene, RadioMusicScene ...  UI / mini-games
│   └── SmackerScene / SmackerPlayer       plays type-10 SMK (smackerplayer.cpp), optional 2x surface
├── Entity -> Sprite / AnimatedSprite / Klaymen (entity.cpp, sprite.cpp, klaymen.cpp)
├── Background (background.cpp)            full-screen bitmap + palette
├── AudioResourceMan / Sound (audiores.cpp, sound.cpp)  type 7/8 -> 22.05 kHz mono streams
├── StaticData (staticdata.cpp)            hint/rect/message/track lists (type-5 style data)
└── GameVars (gamevars.h)                  hashed global/sub variables (puzzle flags, inventory, counters); see knowledge/game_vars.md
```
Hash note: all game objects are addressed by u32 hashes (calcHash of upper-cased names such as `"s1000"`-like strings, plus numeric file hashes). Mapping scene->archive entries needs those constants from the engine source (open item in `docs/upscaling_plan.md`).
""")

    w("## 8. ScummVM note (hand-written)\n")
    w("""The Neverhood runs on ScummVM's `engines/neverhood` (supports the 1996 CD release, demo, Japanese). It is our reference implementation: it documents
the BLB layout (`blbarchive.cpp/.h`), resource hashing/override rules (`resourceman.cpp`), bitmap/RLE and palette parsing (`graphics.cpp`),
animation lists (`resource.cpp/.h`), audio codec (`sound.cpp`), SMK playback (`smackerplayer.cpp`), the fixed 640x480 CLUT8 screen (`screen.cpp`, `neverhood.cpp`),
module/scene logic (`module*.cpp`, `scene.cpp`, `gamemodule.cpp`) and game state (`gamevars.h`). Implications for us:
(1) assets are replaceable in the BLB only if hash, type, compression, ext data and sizes stay valid; (2) stock ScummVM cannot draw >640x480 sprites, so HD assets
need a modified renderer (logical 640x480 coordinates, RGB output surface) or must be kept as companions; (3) s.blb compression-101 aliases are not handled by
ScummVM's `BlbArchive::load` (only 1 and 3); (4) 8-bit palette semantics must be mirrored if bitmaps are re-encoded.
URLs: see `knowledge/sources.md`.
""")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ upscaling_plan.md
STAGES = ["E", "F", "U", "Q", "R"]
DEFAULT_VIDEO = {("c", 0): "x x ~ . .", ("c", 80): "x x . . ."}

ITEMS = [  # (section, key, text, default state)
    ("0. Foundations (done so far)", None, None, None),
    ("0. Foundations (done so far)", "found.blb-parse", "BLB header/directory parser + validation (`blb_inspect.py`), all 7 archives, manifest `work_directory/scratch/blb_manifest.json`", "x"),
    ("0. Foundations (done so far)", "found.alias", "s.blb compression-101 hash aliases resolved (84/84)", "x"),
    ("0. Foundations (done so far)", "found.smk-sample", "T3/T9: SMK samples c.blb#80 and c.blb#0 extracted, ffmpeg-decoded, frames 0/42/84 PNG verified", "x"),
    ("0. Foundations (done so far)", "found.frame000", "T10-T15, T17: frame_000 upscaling experiments (classical, pixel-art, Gemini 4K/UHD, QA); generative candidate ON HOLD (T17)", "x"),
    ("0. Foundations (done so far)", "found.tiers", "Resolution tiers decided (2880x2160 master, 1920x1440, 1440x1080; `knowledge/resolution_options.md`)", "x"),
    ("0. Foundations (done so far)", "found.qa-process", "QA process + templates (`knowledge/qa_process.md`, protocol gate T16)", "x"),
    ("0. Foundations (done so far)", "found.extract-all", "T20: `extract_all.py` (audio/video/graphics/data, DCL decoder verified on all 1,821 compressed payloads)", "x"),
    ("0. Foundations (done so far)", "found.docs", "T18/T19: `docs/game_tree.md`, this plan", "x"),
    ("1. Decisions to make (blockers)", "dec.engine", "Choose delivery path: (a) ScummVM output scaling only, (b) HD-asset fork with logical 640x480 coords, (c) companion assets only", " "),
    ("1. Decisions to make (blockers)", "dec.generative", "Art/style + rights approval for any generative upscaler (T17 hold)", " "),
    ("1. Decisions to make (blockers)", "dec.video-format", "Replacement video container/codec (SMK cannot be encoded locally; engine only plays SMK)", " "),
    ("1. Decisions to make (blockers)", "dec.video-scale", "Policy for 448x240 and 320x200 cutscenes (aspect/fit to tier)", " "),
    ("2. Per-archive checklist", None, None, None),
]
for _n, _txt in [("a", "audio (no upscaling; keep/verify only)"), ("c", "cutscenes"), ("hd", "UI bitmaps + 1 video"), ("i", "backgrounds/sprites/palettes/anims"),
                 ("m", "making-of videos"), ("s", "type-4 records (data; alias-preserving)"), ("t", "first-person videos + bitmaps")]:
    ITEMS += [("2. Per-archive checklist", f"arc.{_n}.extract", f"`{_n}.blb` {_txt}: full extraction to `work_directory/extracted/` + metadata.json", " "),
              ("2. Per-archive checklist", f"arc.{_n}.upscale", f"`{_n}.blb`: upscaled assets produced (tier master 2880x2160 basis)", " "),
              ("2. Per-archive checklist", f"arc.{_n}.qa", f"`{_n}.blb`: QA gate passed + report in `work_directory/qa/`", " "),
              ("2. Per-archive checklist", f"arc.{_n}.repack", f"`{_n}.blb`: rebuilt into `DATA_upscaled/{_n}.blb` + re-parse OK", " ")]
ITEMS += [
    ("3. Video (SMK) - 551 clips: c 82, hd 1, m 13, t 455", "vid.extract-all", "Extract all videos raw (`extract_all.py --type video`)", " "),
    ("3. Video (SMK) - 551 clips: c 82, hd 1, m 13, t 455", "vid.frames-all", "Decode all frames to lossless PNG/FFV1 masters (`--decode-frames all`; ~100k+ frames - disk budget first)", " "),
    ("3. Video (SMK) - 551 clips: c 82, hd 1, m 13, t 455", "vid.audio", "SMK audio tracks extracted and kept bit-identical", " "),
    ("3. Video (SMK) - 551 clips: c 82, hd 1, m 13, t 455", "vid.timing", "Frame-rate/time-base preserved per clip (no interpolation without approval)", " "),
    ("3. Video (SMK) - 551 clips: c 82, hd 1, m 13, t 455", "vid.pipeline", "Select upscaler + temporal-consistency method for clay video (classical baseline vs learned)", " "),
    ("3. Video (SMK) - 551 clips: c 82, hd 1, m 13, t 455", "vid.reencode", "Re-encode to playable target + audio re-mux", " "),
    ("4. Graphics / sprites", "gfx.extract-bmp", "All type-2 bitmaps -> indexed PNG + raw + palette (`--type graphics`)", " "),
    ("4. Graphics / sprites", "gfx.sample", "Sample extraction verified (backgrounds `i.blb#1`, RLE `hd.blb#0`, partial sprites)", "x"),
    ("4. Graphics / sprites", "gfx.roundtrip", "Lossless decode -> index encode -> decode round trip on a copied bitmap (RLE + normal)", " "),
    ("4. Graphics / sprites", "gfx.backgrounds", "Upscale full-screen 640x480 backgrounds (i, hd, t) to 2880x2160 master", " "),
    ("4. Graphics / sprites", "gfx.sprites", "Upscale sprites/partials with same 4.5x factor, preserving registration (x,y) metadata and alpha/transparent index", " "),
    ("4. Graphics / sprites", "gfx.anim", "Animation lists (type 4): frame geometry, deltas, collision rects scaled/validated", " "),
    ("4. Graphics / sprites", "gfx.golden", "Frozen golden set of representative backgrounds/sprites/video frames", " "),
    ("5. Palettes", "pal.extract", "Type-3 palettes + embedded bitmap palettes extracted", " "),
    ("5. Palettes", "pal.map", "Bitmap -> palette association map (which scene palette each palette-less bitmap uses)", " "),
    ("5. Palettes", "pal.strategy", "Strategy: keep indexed + palette (needs requantisation) vs RGB path through new renderer", " "),
    ("5. Palettes", "pal.color-lock", "Colour lock / hue checks vs original palette", " "),
    ("6. Audio handling", "aud.extract-all", "Extract all 329 `a.blb` entries to WAV (22,050 Hz mono) + raw (`--type audio`)", " "),
    ("6. Audio handling", "aud.verify", "WAV decode verified against ScummVM codec (shift bytes, delta/raw)", "~"),
    ("6. Audio handling", "aud.policy", "Policy: audio is NOT upscaled; originals kept byte-identical in the rebuilt BLB (optional lossless clean-up only with approval)", " "),
    ("6. Audio handling", "aud.video-tracks", "SMK embedded audio retained in re-encoded video", " "),
    ("7. Engine / repack / testing", "eng.writer", "BLB writer preserving order, hashes, timestamps, ext data, aliases, offsets", " "),
    ("7. Engine / repack / testing", "eng.reparse", "Repacked archive re-parses with `blb_inspect.py`; byte-identical when nothing changed", " "),
    ("7. Engine / repack / testing", "eng.hd-loader", "Engine hook for larger bitmaps/videos (logical 640x480 + scaled draw) if path (b) chosen", " "),
    ("7. Engine / repack / testing", "eng.scummvm-test", "Smoke test in ScummVM (boot, one scene, one cutscene)", " "),
    ("7. Engine / repack / testing", "eng.original-test", "Compatibility check on original executable (only if replacement files are in-format)", " "),
    ("7. Engine / repack / testing", "eng.full-playthrough", "Full playthrough / scene sweep with captured evidence", " "),
    ("8. QA gates (see `knowledge/qa_process.md`)", "qa.auto", "100% automated checks per batch (size, aspect, palette, hashes, layout/colour)", " "),
    ("8. QA gates (see `knowledge/qa_process.md`)", "qa.human", "Tiered human sampling with report in `work_directory/qa/<batch>/`", " "),
    ("8. QA gates (see `knowledge/qa_process.md`)", "qa.independent", "Independent review for generative/changed pipelines (T17 pending)", " "),
    ("8. QA gates (see `knowledge/qa_process.md`)", "qa.temporal", "Temporal-consistency review for every upscaled video", " "),
    ("9. Output tiers (display / content size; 4:3, no baked bars)", "tier.2160", "2160p display 3840x2160 -> content master 2880x2160 (4.5x, video 9x from 320x240)", "~"),
    ("9. Output tiers (display / content size; 4:3, no baked bars)", "tier.1440", "1440p display 2560x1440 -> content 1920x1440 (3x), Lanczos-derived from master", " "),
    ("9. Output tiers (display / content size; 4:3, no baked bars)", "tier.1080", "1080p display 1920x1080 -> content 1440x1080 (2.25x), derived from master", " "),
]


def read_marks(path):
    items, vids_ = {}, {}
    if path.exists():
        for ln in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"- \[(.)\] .*<!--k:(\S+)-->", ln)
            if m:
                items[m.group(2)] = m.group(1)
            m = re.match(r"\| (\S+#\d+) \|.*\|((?: \[.\] \|){5})\s*$", ln)
            if m:
                vids_[m.group(1)] = re.findall(r"\[(.)\]", m.group(2))
    return items, vids_


def plan(D, marks):
    items, vm = marks
    L = []
    w = L.append
    w("# Upscaling plan\n")
    w(f"_Generated {datetime.date.today()} by `work_directory/tools/gen_docs.py`; checklist marks are preserved on regeneration._\n")
    w("Targets: 4:3 content masters per `knowledge/resolution_options.md`: **2880x2160** (2160p display), 1920x1440 (1440p), 1440x1080 (1080p). Master once at 2880x2160, derive the others (Lanczos). No baked-in bars. "
      "Native canvas is 640x480 (4.5x / 3x / 2.25x); 320x240 videos are 9x / 6x / 4.5x.\n")
    w("## How to update marks\n")
    w("- Legend: `[x]` done, `[~]` partial/on hold, `[ ]` open. Edit this file by hand (change the character inside the brackets; keep the `<!--k:...-->` comment), or use the helper:\n"
      "  - `python work_directory/tools/gen_docs.py --mark item:arc.c.extract --state x`\n"
      "  - `python work_directory/tools/gen_docs.py --mark video:c.blb:0-84 --stage U --state x` (stages E F U Q R; ranges `a-b`, lists `1,5,9`, `*` = all)\n"
      "- Re-running `python work_directory/tools/gen_docs.py` regenerates `docs/game_tree.md` and this file from the archives and keeps your marks.\n"
      "- Video stages: **E** extracted (raw SMK + metadata), **F** frames decoded, **U** upscaled, **Q** QA gate passed, **R** repacked/playable in game.\n"
      "- Same IDs as `extract_all.py` (`<archive>#<entry id>`).\n")
    sec = None
    for s, k, t, d in ITEMS:
        if s != sec:
            sec = s
            w(f"\n## {s}\n")
        if k is None:
            continue
        st = items.get(k, d)
        w(f"- [{st}] {t} <!--k:{k}-->")
    w("\n## 10. Per-video tracker\n")
    w("`2160 fit` = size when scaled to 2160 px height keeping aspect (448x240 exceeds 3840 wide -> needs fit policy `dec.video-scale`).\n")
    for n in ["c", "hd", "m", "t"]:
        vs = vids(D[n])
        w(f"\n### {n}.blb ({len(vs)} videos)\n")
        w("| id | hash | src WxH | frames | fps | 2160 fit | E | F | U | Q | R |")
        w("|---|---|---|---:|---:|---|---|---|---|---|---|")
        for e in vs:
            h = e["video_header"]
            key = f"{n}.blb#{e['id']}"
            if key in vm:
                st = vm[key]
            else:
                dv = DEFAULT_VIDEO.get((n, e["id"]), ". . . . .").replace(".", " ").split(" ")
                st = [c if c else " " for c in DEFAULT_VIDEO.get((n, e["id"]), "     ").split(" ")] if (n, e["id"]) in DEFAULT_VIDEO else [" "] * 5
                if (n, e["id"]) in DEFAULT_VIDEO:
                    st = [{"x": "x", "~": "~"}.get(c, " ") for c in DEFAULT_VIDEO[(n, e["id"])].split(" ")]
            f = fps(h["frame_rate_raw"])
            fit = f"{round(h['width'] * 2160 / h['height'])}x2160"
            w(f"| {key} | {e['hash']} | {h['width']}x{h['height']} | {h['frame_count']} | {f:.2f} | {fit} | " + " | ".join(f"[{c}]" for c in st) + " |")
    return "\n".join(L) + "\n"


def parse_range(spec, ids):
    if spec == "*":
        return set(ids)
    r = set()
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            r.update(range(int(a), int(b) + 1))
        else:
            r.add(int(part))
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mark", help="item:<key> or video:<archive.blb>:<ids>")
    ap.add_argument("--stage", choices=STAGES)
    ap.add_argument("--state", choices=["x", "~", " "], default="x")
    ap.add_argument("--refresh", action="store_true", help="ignore the header cache")
    a = ap.parse_args()
    if a.refresh and CACHE.exists():
        CACHE.unlink()
    D = collect()
    DOCS.mkdir(exist_ok=True)
    pp = DOCS / "upscaling_plan.md"
    items, vm = read_marks(pp)
    if a.mark:
        kind, _, rest = a.mark.partition(":")
        if kind == "item":
            if rest not in {k for _, k, _, _ in ITEMS if k}:
                sys.exit(f"unknown item key {rest}")
            items[rest] = a.state
        elif kind == "video":
            arc, _, spec = rest.rpartition(":")
            n = arc.removesuffix(".blb")
            vs = vids(D[n])
            want = parse_range(spec, [e["id"] for e in vs])
            if not a.stage:
                sys.exit("--stage required for videos")
            for e in vs:
                if e["id"] in want:
                    key = f"{n}.blb#{e['id']}"
                    cur = vm.get(key)
                    if cur is None:
                        cur = [{"x": "x", "~": "~"}.get(c, " ") for c in DEFAULT_VIDEO.get((n, e["id"]), "     ").split(" ")] if (n, e["id"]) in DEFAULT_VIDEO else [" "] * 5
                    cur[STAGES.index(a.stage)] = a.state
                    vm[key] = cur
        else:
            sys.exit("bad --mark")
    # when un-marked existing file exists, read_marks keeps its video rows; first generation uses defaults
    (DOCS / "game_tree.md").write_text(game_tree(D), encoding="utf-8")
    pp.write_text(plan(D, (items, vm)), encoding="utf-8")
    print("wrote", DOCS / "game_tree.md", "and", pp)


if __name__ == "__main__":
    main()
