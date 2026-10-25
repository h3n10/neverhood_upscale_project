#!/usr/bin/env python3
"""Read-only structural inspector for Neverhood BLB archives (no resource extraction)."""
from __future__ import annotations
import argparse, collections, json, pathlib, struct, sys

MAGIC = 0x02004940
TYPE_NAMES = {2: "bitmap", 3: "palette", 4: "animation", 5: "data", 6: "text", 7: "sound", 8: "music", 10: "video"}

def inspect(path: pathlib.Path) -> dict:
    data = path.read_bytes()
    if len(data) < 16:
        raise ValueError("shorter than BLB header")
    sig, version, ext_size, declared_size, count = struct.unpack_from("<IHHII", data, 0)
    if sig != MAGIC or version != 7:
        raise ValueError(f"unexpected signature/version: 0x{sig:08X}/{version}")
    if declared_size != len(data):
        raise ValueError(f"declared file size {declared_size} != actual {len(data)}")
    hash_start = 16
    rec_start = hash_start + count * 4
    ext_start = rec_start + count * 20
    data_start = ext_start + ext_size
    if data_start > len(data):
        raise ValueError("header, hash table, records, and extended data exceed archive length")
    hashes = struct.unpack_from(f"<{count}I", data, hash_start) if count else ()
    hash_to_id = {h: i for i, h in enumerate(hashes)}
    entries = []
    invalid_ranges = []
    for i in range(count):
        p = rec_start + i * 20
        rtype, comp, ext_off, stamp, offset, disk_size, size = struct.unpack_from("<BBHIIII", data, p)
        # In s.blb, type-4/compression-101 zero-sized rows are aliases: disk_size holds a resource hash, not a byte count.
        alias_candidate = rtype == 4 and comp == 101 and offset == 0 and size == 0
        alias_target_id = hash_to_id.get(disk_size) if alias_candidate else None
        valid = (alias_target_id is not None) if alias_candidate else (offset <= len(data) and disk_size <= len(data) - offset)
        if not valid:
            invalid_ranges.append(i)
        extra = {}
        if alias_candidate:
            extra["dummy_alias_resolved"] = alias_target_id is not None
            extra["dummy_alias_target_id"] = alias_target_id
            extra["dummy_alias_target_hash"] = f"{disk_size:08X}"
        if ext_off and ext_off <= ext_size:
            extra["extdata_first_byte_hex"] = f"{data[ext_start + ext_off - 1]:02X}"
        if rtype == 10 and comp == 1 and disk_size >= 20:
            head = data[offset:offset + 20]
            if head[:4] in (b"SMK2", b"SMK4"):
                width, height, frames, rate_raw = struct.unpack_from("<IIIi", head, 4)
                extra["video_header"] = {"format": head[:4].decode("ascii"), "width": width,
                                         "height": height, "frame_count": frames, "frame_rate_raw": rate_raw}
        entries.append({"id": i, "hash": f"{hashes[i]:08X}", "type": rtype,
                        "type_name": TYPE_NAMES.get(rtype, "unknown"), "compression": comp,
                        "extdata_offset_1based": ext_off, "timestamp": stamp,
                        "offset": offset, "disk_size": disk_size, "size": size,
                        "extdata_valid": ext_off == 0 or ext_off <= ext_size, **extra})
    by_type = collections.Counter(e["type"] for e in entries)
    by_comp = collections.Counter(e["compression"] for e in entries)
    groups = {}
    for t in sorted(by_type):
        items = [e for e in entries if e["type"] == t]
        groups[str(t)] = {"name": TYPE_NAMES.get(t, "unknown"), "count": len(items),
                          "compressed_bytes": sum(e["disk_size"] for e in items if not e.get("dummy_alias_resolved", False)),
                          "uncompressed_bytes": sum(e["size"] for e in items),
                          "dummy_alias_count": sum(1 for e in items if e.get("dummy_alias_resolved", False)),
                          "size_min": min((e["size"] for e in items), default=0),
                          "size_max": max((e["size"] for e in items), default=0),
                          "compression_counts": dict(sorted(collections.Counter(e["compression"] for e in items).items()))}
    bad_ext = [e["id"] for e in entries if not e["extdata_valid"]]
    ranges = sorted((e["offset"], e["offset"] + e["disk_size"], e["id"]) for e in entries if e["disk_size"] and not e.get("dummy_alias_resolved", False))
    overlaps = []
    for prev, cur in zip(ranges, ranges[1:]):
        if cur[0] < prev[1]: overlaps.append([prev[2], cur[2]])
    return {"archive": path.name, "path": str(path), "file_bytes": len(data),
            "signature": f"0x{sig:08X}", "version": version, "extended_data_bytes": ext_size,
            "entry_count": count, "hash_table_offset": hash_start, "records_offset": rec_start,
            "extended_data_offset": ext_start, "payload_area_offset": data_start,
            "resource_type_counts": {str(k): {"name": TYPE_NAMES.get(k,"unknown"), "count": v} for k,v in sorted(by_type.items())},
            "compression_counts": dict(sorted(by_comp.items())), "type_details": groups,
            "entries_with_invalid_extended_data_offsets": bad_ext, "invalid_payload_range_entry_ids": invalid_ranges, "overlapping_payload_ranges": overlaps,
            "dummy_alias_entry_ids": [e["id"] for e in entries if e.get("dummy_alias_resolved")],
            "unresolved_dummy_alias_entry_ids": [e["id"] for e in entries if e.get("dummy_alias_resolved") is False],
            "entries": entries}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archives", nargs="+", type=pathlib.Path)
    ap.add_argument("--json", type=pathlib.Path, help="write full manifest JSON (use work_directory)")
    args = ap.parse_args()
    results = [inspect(p) for p in args.archives]
    for r in results:
        print(f"{r['archive']}: {r['file_bytes']:,} B, {r['entry_count']} entries; types " +
              ", ".join(f"{k} {v['name']}={v['count']}" for k,v in r['resource_type_counts'].items()))
        print(f"  compressed-bytes by type: " + ", ".join(f"{k}={v['compressed_bytes']:,}" for k,v in r['type_details'].items()))
        print(f"  compression IDs: {r['compression_counts']}; payload start={r['payload_area_offset']}; "
              f"bad ext refs={len(r['entries_with_invalid_extended_data_offsets'])}; invalid ranges={len(r['invalid_payload_range_entry_ids'])}; overlaps={len(r['overlapping_payload_ranges'])}")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"Manifest: {args.json}")

if __name__ == "__main__":
    try: main()
    except (OSError, ValueError, struct.error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); sys.exit(2)


