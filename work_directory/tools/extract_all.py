#!/usr/bin/env python3
"""Parametric extractor for Neverhood BLB archives (READ-ONLY on DATA_source).

Output: <out>/{video,audio,graphics,data}/<blb-name>/<entry-id>/ with metadata.json
  video    type 10  -> video.smk (raw SMK2 stream) [+ frames/*.png, audio.wav via ffmpeg]
  audio    type 7/8 -> audio.wav (22050 Hz mono s16, decoded like ScummVM) + audio.raw (BLB-decompressed)
  graphics type 2   -> bitmap.bin (decompressed) + bitmap.png (indexed, embedded palette if present)
           type 3   -> palette.bin (1024 B, 256x4) + palette.pal (768 B RGB)
  data     types 4,5,6 (animation / data / text) -> raw.bin (decompressed)
Entry ids are the directory index (same IDs as blb_inspect.py manifest).

Examples:
  python extract_all.py --list                          # dry-run, all archives, all types
  python extract_all.py --blb c --type video --ids 0,80 --decode-frames 3
  python extract_all.py --blb a --type audio --ids 0-9
  python extract_all.py --blb i --type graphics --ids 0-20
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, struct, subprocess, sys, tempfile, wave, shutil

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import blb_inspect  # noqa: E402

SRC = ROOT / "DATA_source"
DEFAULT_OUT = ROOT / "work_directory" / "extracted"
ALL_BLB = ["a", "c", "hd", "i", "m", "s", "t"]
GROUPS = {"video": {10}, "audio": {7, 8}, "graphics": {2, 3}, "data": {4, 5, 6}}
TYPE_GROUP = {t: g for g, ts in GROUPS.items() for t in ts}
SAMPLE_RATE = 22050


# ---------------------------------------------------------------- DCL (PKWARE implode) decoder
_LITLEN = bytes([11, 124, 8, 7, 28, 7, 188, 13, 76, 4, 10, 8, 12, 10, 12, 10, 8, 23, 8, 9, 7, 6, 7, 8, 7, 6, 55, 8,
                 23, 24, 12, 11, 7, 9, 11, 12, 6, 7, 22, 5, 7, 24, 6, 11, 9, 6, 7, 22, 7, 11, 38, 7, 9, 8, 25, 11,
                 8, 11, 9, 12, 8, 12, 5, 38, 5, 38, 5, 11, 7, 5, 6, 21, 6, 10, 53, 8, 7, 24, 10, 27, 44, 253, 253,
                 253, 252, 252, 252, 13, 12, 45, 12, 45, 12, 61, 12, 45, 44, 173])
_LENLEN = bytes([2, 35, 36, 53, 38, 23])
_DISTLEN = bytes([2, 20, 53, 230, 247, 151, 248])
_BASE = [3, 2, 4, 5, 6, 7, 8, 9, 10, 12, 16, 24, 40, 72, 136, 264]
_EXTRA = [0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8]


def _huff(rep: bytes, n: int):
    lens = []
    for b in rep:
        lens += [b & 15] * ((b >> 4) + 1)
    assert len(lens) == n
    count = [0] * 16
    for l in lens:
        count[l] += 1
    offs = [0] * 16
    for l in range(1, 15):
        offs[l + 1] = offs[l] + count[l]
    symbol = [0] * n
    for s, l in enumerate(lens):
        if l:
            symbol[offs[l]] = s
            offs[l] += 1
    return count, symbol


_LIT, _LEN, _DIST = _huff(_LITLEN, 256), _huff(_LENLEN, 16), _huff(_DISTLEN, 64)


def dcl_decompress(src: bytes, expected: int, limit: int | None = None) -> bytes:
    """Decode a PKWARE DCL stream. With `limit`, stop early after that many output bytes (header peeks)."""
    pos = 0
    bitbuf = 0
    bitcnt = 0

    def bits(n):
        nonlocal pos, bitbuf, bitcnt
        while bitcnt < n:
            if pos >= len(src):
                raise ValueError("DCL: input exhausted")
            bitbuf |= src[pos] << bitcnt
            pos += 1
            bitcnt += 8
        v = bitbuf & ((1 << n) - 1)
        bitbuf >>= n
        bitcnt -= n
        return v

    def decode(h):
        count, symbol = h
        code = first = index = 0
        for l in range(1, 16):
            code |= bits(1) ^ 1
            c = count[l]
            if code - c < first:
                return symbol[index + (code - first)]
            index += c
            first += c
            first <<= 1
            code <<= 1
        raise ValueError("DCL: bad huffman code")

    lit = bits(8)
    dbits = bits(8)
    if lit > 1 or not 4 <= dbits <= 6:
        raise ValueError("DCL: bad header")
    out = bytearray()
    while True:
        if bits(1):
            s = decode(_LEN)
            ln = _BASE[s] + bits(_EXTRA[s])
            if ln == 519:
                break
            sh = 2 if ln == 2 else dbits
            dist = (decode(_DIST) << sh) + bits(sh) + 1
            if dist > len(out):
                raise ValueError("DCL: distance too far")
            for _ in range(ln):
                out.append(out[-dist])
        else:
            out.append(decode(_LIT) if lit else bits(8))
        if limit is not None and len(out) >= limit:
            return bytes(out[:limit])
        if len(out) > expected + 600:
            raise ValueError("DCL: output overrun")
    return bytes(out)


# ---------------------------------------------------------------- helpers
def fps_of(raw: int):
    if raw < 0:
        return 100000.0 / -raw
    if raw > 0:
        return 1000.0 / raw
    return None


def ffmpeg_exe(explicit: pathlib.Path | None = None) -> str | None:
    if explicit:
        return str(explicit.resolve()) if explicit.is_file() else None
    return shutil.which("ffmpeg")


def parse_ids(spec: str | None, count: int):
    if not spec:
        return None
    ids = set()
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            a = int(a) if a else 0
            b = int(b) if b else count - 1
            ids.update(range(a, b + 1))
        else:
            ids.add(int(part))
    return sorted(i for i in ids if 0 <= i < count)


def payload(fh, e, archive, limit: int | None = None) -> bytes:
    """Return the BLB-level decoded payload of entry e (decompresses compression 3); `limit` = header peek."""
    fh.seek(e["offset"])
    raw = fh.read(e["disk_size"])
    if e["compression"] == 1:
        return raw[:limit] if limit else raw
    if e["compression"] == 3:
        out = dcl_decompress(raw, e["size"], limit)
        if limit is None and len(out) != e["size"]:
            raise ValueError(f"DCL size mismatch {len(out)} != {e['size']}")
        return out
    raise ValueError(f"unsupported compression {e['compression']}")


def decode_audio(data: bytes, shift: int) -> bytes:
    if shift == 0xFF:
        n = len(data) // 2
        return data[: n * 2]
    out = bytearray()
    v = 0
    for b in data:
        v += b - 256 if b > 127 else b
        s = (v << shift) if shift < 16 else 0
        s = max(-32768, min(32767, s))
        out += struct.pack("<h", s)
    return bytes(out)


def parse_bitmap(d: bytes, size_hint=None):
    flags = struct.unpack_from("<H", d, 0)[0]
    p = 2
    w = h = 1
    x = y = 0
    pal = None
    if flags & 2:
        w, h = struct.unpack_from("<HH", d, p); p += 4
    if flags & 4:
        x, y = struct.unpack_from("<HH", d, p); p += 4
    if flags & 8:
        pal = d[p:p + 1024]; p += 1024
    pix = None
    if flags & 16:
        src = d[p:]
        if flags & 1:  # RLE
            buf = bytearray(w * h)
            q = 0
            row = 0
            rows, chunks = struct.unpack_from("<HH", src, q); q += 4
            while True:
                if chunks == 0:
                    row += rows
                else:
                    for _ in range(rows):
                        for _c in range(chunks):
                            skip, copy = struct.unpack_from("<HH", src, q); q += 4
                            if row < h:
                                buf[row * w + skip: row * w + skip + copy] = src[q:q + copy][: max(0, w - skip)]
                            q += copy
                        row += 1
                rows, chunks = struct.unpack_from("<HH", src, q); q += 4
                if rows <= 0 or rows > 0x7FFF:
                    break
            pix = bytes(buf)
        else:
            pitch = (w + 3) & ~3
            pix = b"".join(src[r * pitch: r * pitch + w] for r in range(h))
    return {"flags": flags, "width": w, "height": h, "x": x, "y": y, "palette": pal, "pixels": pix}


def write_json(path: pathlib.Path, obj):
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- per-type extraction
def do_video(fh, e, d: pathlib.Path, meta, args):
    raw = payload(fh, e, None)
    (d / "video.smk").write_bytes(raw)
    meta["files"] = ["video.smk"]
    meta["sha256"] = hashlib.sha256(raw).hexdigest()
    if raw[:4] in (b"SMK2", b"SMK4"):
        w, h, n, r = struct.unpack_from("<IIIi", raw, 4)
        f = fps_of(r)
        meta.update(format=raw[:4].decode(), width=w, height=h, frames=n, frame_rate_raw=r,
                    fps=f, duration_s=(n / f if f else None))
    ff = args.ffmpeg_executable
    if args.decode_frames and ff:
        n = meta.get("frames", 0)
        sel = list(range(n)) if args.decode_frames == "all" else sorted(
            {round(i * (n - 1) / max(int(args.decode_frames) - 1, 1)) for i in range(int(args.decode_frames))})
        fd = d / "frames"
        fd.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            cmd = [ff, "-v", "error", "-y", "-i", str(d / "video.smk")]
            if len(sel) < n:
                cmd += ["-vf", "select='" + "+".join(f"eq(n\\,{i})" for i in sel) + "'"]
            cmd += ["-fps_mode", "passthrough", str(pathlib.Path(tmp) / "f_%06d.png")]
            subprocess.run(cmd, check=True)
            got = sorted(pathlib.Path(tmp).glob("f_*.png"))
            names = []
            for idx, g in zip(sel, got):
                shutil.move(str(g), fd / f"frame_{idx:05d}.png")
                names.append(f"frames/frame_{idx:05d}.png")
        meta["decoded_frames"] = names
    if args.video_audio and ff:
        r = subprocess.run([ff, "-v", "error", "-y", "-i", str(d / "video.smk"), "-vn", "-c:a", "pcm_s16le",
                            str(d / "audio.wav")], capture_output=True)
        if r.returncode == 0 and (d / "audio.wav").exists():
            meta["files"].append("audio.wav")
        else:
            meta["smk_audio"] = "none/failed"


def do_audio(fh, e, d: pathlib.Path, meta, args):
    raw = payload(fh, e, None)
    shift = int(e.get("extdata_first_byte_hex", "FF"), 16) if "extdata_first_byte_hex" in e else 0xFF
    pcm = decode_audio(raw, shift)
    (d / "audio.raw").write_bytes(raw)
    with wave.open(str(d / "audio.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    meta.update(files=["audio.raw", "audio.wav"], shift_value=shift, sample_rate=SAMPLE_RATE, channels=1,
                bits=16, samples=len(pcm) // 2, duration_s=len(pcm) / 2 / SAMPLE_RATE,
                kind="music" if e["type"] == 8 else "sound", sha256=hashlib.sha256(raw).hexdigest())


def do_graphics(fh, e, d: pathlib.Path, meta, args):
    raw = payload(fh, e, None)
    meta["sha256"] = hashlib.sha256(raw).hexdigest()
    if e["type"] == 3:
        (d / "palette.bin").write_bytes(raw)
        rgb = b"".join(raw[i * 4:i * 4 + 3] for i in range(min(256, len(raw) // 4)))
        (d / "palette.pal").write_bytes(rgb)
        meta["files"] = ["palette.bin", "palette.pal"]
        return
    (d / "bitmap.bin").write_bytes(raw)
    meta["files"] = ["bitmap.bin"]
    try:
        b = parse_bitmap(raw)
    except Exception as ex:  # keep raw, record the failure
        meta["decode_error"] = str(ex)
        return
    meta.update(bitmap_flags=b["flags"], rle=bool(b["flags"] & 1), width=b["width"], height=b["height"],
                pos_x=b["x"], pos_y=b["y"], has_palette=b["palette"] is not None,
                has_image=b["pixels"] is not None)
    if b["pixels"] is None:
        return
    try:
        from PIL import Image
        im = Image.frombytes("P", (b["width"], b["height"]), b["pixels"])
        if b["palette"]:
            im.putpalette(b"".join(b["palette"][i * 4:i * 4 + 3] for i in range(256)))
            (d / "bitmap.pal").write_bytes(b["palette"])
            meta["files"].append("bitmap.pal")
        else:
            meta["palette_note"] = "no embedded palette; PNG uses grayscale ramp (palette comes from a type-3 entry/scene)"
            im.putpalette(bytes(v for i in range(256) for v in (i, i, i)))
        im.save(d / "bitmap.png")
        meta["files"].append("bitmap.png")
    except ImportError:
        meta["png"] = "Pillow missing"


def do_data(fh, e, d: pathlib.Path, meta, args):
    raw = payload(fh, e, None)
    (d / "raw.bin").write_bytes(raw)
    meta["files"] = ["raw.bin"]
    meta["sha256"] = hashlib.sha256(raw).hexdigest()


HANDLERS = {"video": do_video, "audio": do_audio, "graphics": do_graphics, "data": do_data}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blb", nargs="+", default=["all"], help="archive names (a c hd i m s t, with/without .blb) or 'all'")
    ap.add_argument("--type", default="all", choices=["video", "audio", "graphics", "data", "all"],
                    help="resource group; 'all' = video+audio+graphics+data")
    ap.add_argument("--ids", "--index", dest="ids", help="entry ids: e.g. 0,5,10-20,300- (applies to each archive)")
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT, help="output root (default work_directory/extracted)")
    ap.add_argument("--src", type=pathlib.Path, default=SRC, help="archive folder (default DATA_source)")
    ap.add_argument("--list", action="store_true", help="dry-run: list matching entries, write nothing")
    ap.add_argument("--manifest", type=pathlib.Path, help="write JSON list of matching entries (works with --list)")
    ap.add_argument("--force", action="store_true", help="overwrite existing (default: skip dirs with metadata.json)")
    ap.add_argument("--decode-frames", metavar="N|all", help="video: decode N evenly spaced frames (or 'all') to PNG via ffmpeg")
    ap.add_argument("--video-audio", action="store_true", help="video: also extract SMK audio track to audio.wav via ffmpeg")
    ap.add_argument("--ffmpeg", type=pathlib.Path, help="ffmpeg executable (default: find ffmpeg on PATH)")
    args = ap.parse_args()
    ffmpeg = ffmpeg_exe(args.ffmpeg)
    if args.ffmpeg and not ffmpeg:
        ap.error(f"ffmpeg executable not found: {args.ffmpeg}")
    if (args.decode_frames or args.video_audio) and not ffmpeg:
        ap.error("video decoding/audio extraction requires ffmpeg on PATH or --ffmpeg <path>")
    args.ffmpeg_executable = ffmpeg

    names = ALL_BLB if "all" in args.blb else [b.lower().removesuffix(".blb") for b in args.blb]
    groups = list(GROUPS) if args.type == "all" else [args.type]
    wanted = set().union(*(GROUPS[g] for g in groups))
    todo_total = done = skipped = failed = 0
    manifest = []
    for name in names:
        path = args.src / f"{name}.blb"
        if not path.exists():
            print(f"!! missing {path}", file=sys.stderr); continue
        arc = blb_inspect.inspect(path)
        ids = parse_ids(args.ids, arc["entry_count"])
        sel = [e for e in arc["entries"] if e["type"] in wanted and (ids is None or e["id"] in ids)]
        print(f"== {path.name}: {len(sel)} matching of {arc['entry_count']} entries")
        with path.open("rb") as fh:
            for e in sel:
                grp = TYPE_GROUP[e["type"]]
                vh = e.get("video_header", {})
                row = {"archive": path.name, "id": e["id"], "hash": e["hash"], "type": e["type"],
                       "group": grp, "compression": e["compression"], "disk_size": e["disk_size"], "size": e["size"]}
                row.update({k: vh[k] for k in ("width", "height", "frame_count") if k in vh})
                if e.get("dummy_alias_resolved"):
                    row["alias_of_id"] = e["dummy_alias_target_id"]
                manifest.append(row)
                todo_total += 1
                d = args.out / grp / path.name / str(e["id"])
                if args.list:
                    extra = f" {vh['width']}x{vh['height']} {vh['frame_count']}f" if vh else ""
                    extra += f" ->alias#{row['alias_of_id']}" if "alias_of_id" in row else ""
                    print(f"  {grp:8s} #{e['id']:<5d} {e['hash']} t{e['type']} c{e['compression']:<3d} "
                          f"{e['disk_size']:>10,} -> {e['size']:>10,}{extra}")
                    continue
                if (d / "metadata.json").exists() and not args.force:
                    skipped += 1; continue
                d.mkdir(parents=True, exist_ok=True)
                meta = dict(row, type_name=e["type_name"], timestamp=e["timestamp"], offset=e["offset"],
                            extdata_first_byte_hex=e.get("extdata_first_byte_hex"))
                try:
                    if e.get("dummy_alias_resolved"):
                        meta["note"] = f"compression-101 hash alias of entry #{e['dummy_alias_target_id']}; no payload"
                    else:
                        HANDLERS[grp](fh, e, d, meta, args)
                    write_json(d / "metadata.json", meta)
                    done += 1
                except Exception as ex:
                    failed += 1
                    print(f"  FAIL {path.name}#{e['id']}: {ex}", file=sys.stderr)
                    if d.exists() and not any(d.iterdir()):
                        d.rmdir()
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.manifest, manifest)
    print(f"matched {todo_total}; extracted {done}; skipped(existing) {skipped}; failed {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
