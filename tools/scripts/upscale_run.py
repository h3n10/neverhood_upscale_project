r"""Resumable animation upscaler (Gemini API, prompt v3 method).

Per clip (= extracted/video/<blb>/<entry>/frames/frame_NNN.png):
  1. ANCHOR   first frame upscaled alone with prompt v3 (upscale_v3.txt + colour lock).
  2. APPROVAL anchors need human approval depending on --approval (all | sample | none).
              Unapproved clips stop after the anchor. Approve: --approve-anchor or file ANCHOR_APPROVED.
  3. FRAMES   other frames are sent as [current anchor, (previous output), low-res frame]
              with upscale_v3_anim.txt so the anchor's fine detail carries over.
  4. RE-ANCHOR when a source frame differs from the current anchor's source frame by more than
              --reanchor-threshold (mean abs diff, 0-255), that frame becomes the new anchor
              (schedule is computed from source frames only, so resume is deterministic).
  5. AUTO-QA  every output is checked (colour shift, structure correlation, static-region
              flicker vs anchor). Failures are re-rolled (--rerolls), then quarantined.
  6. DUPLICATES identical source frames reuse the earlier output (no API call).
Size: output = source size x --scale (default 9 => 320x240 -> 2880x2160, i.e. 2160p content;
      sprites/odd sizes scale proportionally). Sources whose aspect is not supported by the API are
      padded with black bars for the request and the bars are cropped away afterwards.
Rules: knowledge/animation_upscaling_rules.md   Key: GEMINI_API_KEY (environment only).

Examples:
  python tools\scripts\upscale_run.py --list
  python tools\scripts\upscale_run.py --auto --anchors-only
  python tools\scripts\upscale_run.py --auto --max-calls 200
  python tools\scripts\upscale_run.py --blb c.blb --scene 0 80 --frames 0-9 --max-frames 20
  python tools\scripts\upscale_run.py --blb c.blb --scene 0 --approve-anchor
  python tools\scripts\upscale_run.py --auto --dry-run
Resume: state.json per clip; finished frames (same input sha + config) are skipped, failed retried.
Output: work_directory\upscaled\video\<blb>\<entry>\{raw,frames,quarantine,state.json,run.log}
"""
import argparse
import base64
import hashlib
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "work_directory/extracted/video"
OUT_ROOT = ROOT / "work_directory/upscaled/video"
PROMPTS = Path(__file__).resolve().parent / "prompts"
DEFAULT_MODEL = "gemini-3-pro-image-preview"
ASPECTS = {"1:1": 1.0, "2:3": 2 / 3, "3:2": 1.5, "3:4": 0.75, "4:3": 4 / 3,
           "4:5": 0.8, "5:4": 1.25, "9:16": 9 / 16, "16:9": 16 / 9, "21:9": 21 / 9}
GENERIC_COLOR_LOCK = (
    "COLOR LOCK: keep every hue, saturation, brightness and the lighting exactly as in the "
    "source image; a color cast of any kind is a failure. Keep the same dark shadow regions.")
BARS_NOTE = ("NOTE: black bars were added to the CURRENT image only to fit the aspect ratio. "
             "Keep them pure black and unchanged; do not draw anything into them.")
REF_MAX_SIDE = 1920  # reference images are downscaled for the request only
QA_DEFAULTS = {"max_rgb_shift": 6.0, "min_corr": 0.985, "max_static_diff": 6.0}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def parse_ranges(spec):
    parts = []
    for tok in spec.split(","):
        tok = tok.strip()
        if not tok:
            continue
        m = re.fullmatch(r"(\d*)-(\d*)", tok)
        parts.append((int(m[1] or 0), int(m[2]) if m[2] else 10**9) if m else (int(tok), int(tok)))
    return lambda i: any(lo <= i <= hi for lo, hi in parts)


class Clip:
    def __init__(self, blb, entry):
        self.blb, self.entry = blb, entry
        self.src = SRC_ROOT / blb / entry
        self.out = OUT_ROOT / blb / entry
        self.key = f"{blb}/{entry}"

    def frames(self):
        fs = sorted((self.src / "frames").glob("frame_*.png"))
        return [(int(re.search(r"(\d+)", f.stem)[1]), f) for f in fs]

    def state(self):
        p = self.out / "state.json"
        return json.loads(p.read_text()) if p.exists() else {"frames": {}, "failed": {}}

    def save(self, st):
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / "state.json").write_text(json.dumps(st, indent=1))

    def log(self, msg):
        self.out.mkdir(parents=True, exist_ok=True)
        with open(self.out / "run.log", "a", encoding="utf-8") as f:
            f.write(f"{now()} {msg}\n")
        print(f"[{self.key}] {msg}", flush=True)

    def outpath(self, idx):
        return self.out / "frames" / f"frame_{idx:03d}.png"

    @property
    def approved(self):
        return (self.out / "ANCHOR_APPROVED").exists()


def discover(blbs, scenes):
    clips = []
    if not SRC_ROOT.exists():
        return clips
    for b in sorted(SRC_ROOT.iterdir()):
        if not b.is_dir() or (blbs and b.name not in blbs):
            continue
        for e in sorted((d for d in b.iterdir() if d.is_dir()), key=lambda d: (len(d.name), d.name)):
            if (not scenes or e.name in scenes) and (e / "frames").is_dir():
                clips.append(Clip(b.name, e.name))
    return clips


# ---------- prompts / geometry ----------
def color_lock(clip, args):
    f = Path(args.color_lock) if args.color_lock else PROMPTS / "color_locks" / f"{clip.blb}_{clip.entry}.txt"
    return f.read_text(encoding="utf-8-sig").strip() if f.exists() else GENERIC_COLOR_LOCK


def build_prompt(clip, args, anchor, padded=False):
    cl = color_lock(clip, args)
    if anchor:
        t = (PROMPTS / "upscale_v3.txt").read_text(encoding="utf-8-sig")
        t = re.sub(r"COLOR LOCK:.*?(?=\n\n|\Z)", lambda _: cl, t, flags=re.S)
    else:
        t = (PROMPTS / "upscale_v3_anim.txt").read_text(encoding="utf-8-sig").replace("{COLOR_LOCK}", cl)
    if padded:
        t = t.replace("Output: one image only", BARS_NOTE + "\n\nOutput: one image only")
    return t


def nearest_aspect(w, h):
    r = w / h
    return min(ASPECTS, key=lambda k: abs(ASPECTS[k] - r))


def pad_to_aspect(img, aspect):
    """Pad with black bars to exactly the API aspect; returns (padded, box of original in padded)."""
    ar = ASPECTS[aspect]
    w, h = img.size
    pw, ph = (max(w, round(h * ar)), h) if w / h < ar else (w, max(h, round(w / ar)))
    if (pw, ph) == (w, h):
        return img, (0, 0, w, h)
    canvas = Image.new("RGB", (pw, ph), (0, 0, 0))
    x, y = (pw - w) // 2, (ph - h) // 2
    canvas.paste(img, (x, y))
    return canvas, (x, y, x + w, y + h)


def png_part(img, max_side=None):
    img = img.convert("RGB")
    if max_side and max(img.size) > max_side:
        s = max_side / max(img.size)
        img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(buf.getvalue()).decode()}}


def finalize(raw_bytes, padded_size, box, target):
    """Drop the added bars (proportionally), resize to target (source size x scale)."""
    im = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    sx, sy = im.width / padded_size[0], im.height / padded_size[1]
    im = im.crop((round(box[0] * sx), round(box[1] * sy), round(box[2] * sx), round(box[3] * sy)))
    return im.resize(target, Image.LANCZOS)


def call_api(key, model, parts, aspect, size, timeout=300):
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"],
                                 "imageConfig": {"imageSize": size, "aspectRatio": aspect}}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    req = urllib.request.Request(url, json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.load(r)
    for c in resp.get("candidates", []):
        for p in c.get("content", {}).get("parts", []):
            d = p.get("inlineData") or p.get("inline_data")
            if d:
                return base64.b64decode(d["data"]), resp.get("usageMetadata")
    raise RuntimeError("no image in response: " + json.dumps(resp)[:600])


# ---------- QA ----------
def _small(img, size):
    return np.asarray(img.convert("RGB").resize(size, Image.BOX), dtype=np.float32)


def auto_qa(src_img, out_img, anchor_src, anchor_out, is_anchor, args):
    """Gate checks vs the low-res source; thresholds are starting values (see rules doc)."""
    sm = (160, round(160 * src_img.height / src_img.width))
    s, o = _small(src_img, sm), _small(out_img, sm)
    shift = (o.mean((0, 1)) - s.mean((0, 1)))
    corr = float(np.corrcoef(s.mean(2).ravel(), o.mean(2).ravel())[0, 1])
    res = {"rgb_shift": [round(float(x), 2) for x in shift], "corr": round(corr, 4)}
    fails = []
    if np.abs(shift).max() > args.qa_max_rgb_shift:
        fails.append("colour shift")
    if corr < args.qa_min_corr:
        fails.append("structure correlation")
    if not is_anchor and anchor_src is not None and anchor_out is not None:
        a_s = _small(anchor_src, sm)
        static = np.abs(a_s - s).max(2) < 3  # unchanged pixels vs the anchor's source
        if static.mean() > 0.02:
            d = float(np.abs(_small(anchor_out, sm) - o).mean(2)[static].mean())
            res["static_diff"] = round(d, 2)
            res["static_frac"] = round(float(static.mean()), 3)
            if d > args.qa_max_static_diff:
                fails.append("static-region flicker")
    res["pass"] = not fails
    res["fails"] = fails
    return res


def upscale_one(clip, idx, srcpath, args, key, anchor_img, prev_img, anchor, target):
    src_bytes = srcpath.read_bytes()
    src = Image.open(io.BytesIO(src_bytes)).convert("RGB")
    aspect = nearest_aspect(*src.size)
    padded, box = pad_to_aspect(src, aspect)
    prompt = build_prompt(clip, args, anchor, padded.size != src.size)
    parts = [{"text": prompt}]
    if not anchor:
        parts.append(png_part(anchor_img, REF_MAX_SIDE))
        if args.ref_mode == "first+prev" and prev_img is not None:
            parts.append(png_part(prev_img, REF_MAX_SIDE))
    parts.append(png_part(padded))
    last = None
    for attempt in range(1, args.retries + 1):
        try:
            t0 = time.time()
            raw, usage = call_api(key, args.model, parts, aspect, args.image_size)
            fin = finalize(raw, padded.size, box, target)
            return raw, fin, src, {"seconds": round(time.time() - t0, 1), "usage": usage,
                                   "prompt_sha": sha(prompt.encode()), "input_sha": sha(src_bytes)}
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"
            if e.code in (400, 401, 403, 404):
                break
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        clip.log(f"frame {idx} attempt {attempt} failed: {last}")
        time.sleep(args.backoff * attempt)
    raise RuntimeError(last)


def anchor_schedule(frames, thr):
    """Indices that are anchors: first frame + every frame drifting > thr from the current anchor."""
    anchors = [frames[0][0]]
    small = lambda p: _small(Image.open(p), (80, 60))
    ref = small(frames[0][1])
    for idx, p in frames[1:]:
        cur = small(p)
        if thr > 0 and float(np.abs(cur - ref).mean()) > thr:
            anchors.append(idx)
            ref = cur
    return anchors


class Budget:
    def __init__(self, n):
        self.left = n

    def take(self):
        if self.left is None:
            return True
        if self.left <= 0:
            return False
        self.left -= 1
        return True


def needs_approval(clip_pos, args):
    if args.approval == "none":
        return False
    if args.approval == "all":
        return True
    return clip_pos % args.sample_every == 0  # sample: every Nth clip is reviewed


def process_clip(clip, clip_pos, args, key, budget):
    frames = clip.frames()
    if not frames:
        return 0
    want = parse_ranges(args.frames) if args.frames else (lambda i: True)
    st = clip.state()
    cfg_id = f"{args.model}|{args.image_size}|{args.scale}|{args.ref_mode}"
    (clip.out / "frames").mkdir(parents=True, exist_ok=True)
    (clip.out / "raw").mkdir(parents=True, exist_ok=True)
    first_idx = frames[0][0]
    src0 = Image.open(frames[0][1])
    target = (round(src0.width * args.scale), round(src0.height * args.scale))
    anchors = set(anchor_schedule(frames, args.reanchor_threshold))
    st["anchors"] = sorted(anchors)
    shas = {i: sha(p.read_bytes()) for i, p in frames}
    paths = dict(frames)
    calls = 0

    def is_done(idx):
        r = st["frames"].get(str(idx))
        return bool(r and r["input_sha"] == shas[idx] and r["cfg"] == cfg_id and clip.outpath(idx).exists())

    def load_out(idx):
        p = clip.outpath(idx)
        return Image.open(p).convert("RGB") if p.exists() else None

    cur_anchor = {"idx": first_idx, "img": load_out(first_idx)}

    def run(idx, is_anchor, prev_img):
        nonlocal calls
        if args.dry_run:
            clip.log(f"DRY frame {idx} ({'ANCHOR' if is_anchor else 'anim'})")
            return None
        for roll in range(args.rerolls + 1):
            if not budget.take():
                raise StopIteration("max-calls reached")
            try:
                raw, fin, src, meta = upscale_one(clip, idx, paths[idx], args, key, cur_anchor["img"],
                                                  prev_img, is_anchor, target)
            except RuntimeError as e:
                st["failed"][str(idx)] = {"error": str(e), "at": now()}
                st["_consec"] = st.get("_consec", 0) + 1
                clip.save(st)
                raise
            calls += 1
            a_src = None if is_anchor else Image.open(paths[cur_anchor["idx"]]).convert("RGB")
            qa = auto_qa(src, fin, a_src, None if is_anchor else cur_anchor["img"], is_anchor, args)
            meta.update(cfg=cfg_id, done_at=now(), size=list(fin.size), qa=qa, roll=roll,
                        is_anchor=is_anchor, anchor_idx=cur_anchor["idx"])
            if qa["pass"]:
                break
            qdir = clip.out / "quarantine"
            qdir.mkdir(exist_ok=True)
            fin.save(qdir / f"frame_{idx:03d}_roll{roll}.png")
            clip.log(f"frame {idx} QA fail roll {roll}: {qa['fails']} {qa}")
        else:
            st["failed"][str(idx)] = {"error": "QA failed after re-rolls", "qa": qa, "at": now()}
            st["_consec"] = st.get("_consec", 0) + 1
            clip.save(st)
            raise RuntimeError(f"frame {idx} quarantined")
        (clip.out / "raw" / f"frame_{idx:03d}.png").write_bytes(raw)
        fin.save(clip.outpath(idx))
        st["frames"][str(idx)] = meta
        st["failed"].pop(str(idx), None)
        st["_consec"] = 0
        clip.save(st)
        clip.log(f"frame {idx} ok {meta['seconds']}s {fin.size} qa={qa['rgb_shift']}/{qa['corr']}")
        if args.sleep:
            time.sleep(args.sleep)
        return fin

    # --- first anchor
    if (args.force and want(first_idx)) or not is_done(first_idx):
        was = clip.approved
        img = run(first_idx, True, None)
        if img is not None:
            cur_anchor["img"] = img
            if was:
                (clip.out / "ANCHOR_APPROVED").unlink()
    if args.anchors_only:
        return calls
    if args.approve_anchor:
        (clip.out / "ANCHOR_APPROVED").write_text(f"approved {now()}\n")
    elif args.auto_approve or not needs_approval(clip_pos, args):
        if cur_anchor["img"] is not None and not clip.approved:
            (clip.out / "ANCHOR_APPROVED").write_text(f"auto ({args.approval}) {now()}\n")
    if not clip.approved and not args.dry_run:
        clip.log(f"anchor awaiting approval: review {clip.outpath(first_idx)} then --approve-anchor")
        return calls

    # --- remaining frames (sequential: each depends on its anchor and previous output)
    seen = {shas[first_idx]: first_idx}
    n_new = 0
    prev_idx = first_idx
    for idx, _ in frames[1:]:
        selected = want(idx) and idx % args.step == 0
        done = is_done(idx) and not args.force
        if shas[idx] in seen and idx not in anchors:  # identical source frame -> reuse
            if selected and not done and not args.dry_run:
                shutil.copy(clip.outpath(seen[shas[idx]]), clip.outpath(idx))
                st["frames"][str(idx)] = {"input_sha": shas[idx], "cfg": cfg_id,
                                          "reuse_of": seen[shas[idx]], "done_at": now()}
                clip.save(st)
                clip.log(f"frame {idx} reused from {seen[shas[idx]]}")
            prev_idx = idx
            continue
        seen.setdefault(shas[idx], idx)
        if done or not selected:
            if idx in anchors and clip.outpath(idx).exists():
                cur_anchor.update(idx=idx, img=load_out(idx))
            prev_idx = idx
            continue
        if args.max_frames and n_new >= args.max_frames:
            break
        try:
            fin = run(idx, False, load_out(prev_idx))
            n_new += 1
            if idx in anchors and fin is not None:
                cur_anchor.update(idx=idx, img=fin)
                clip.log(f"re-anchored at frame {idx}")
        except RuntimeError:
            if st.get("_consec", 0) >= args.max_consecutive_failures:
                clip.log("too many consecutive failures; aborting clip")
                raise
        prev_idx = idx
    return calls


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auto", action="store_true", help="all clips, resuming where left off")
    ap.add_argument("--list", action="store_true", help="show progress and exit")
    ap.add_argument("--blb", nargs="*", help="archive names, e.g. c.blb")
    ap.add_argument("--scene", nargs="*", help="entry ids (clip folders), e.g. 0 80")
    ap.add_argument("--frames", help="frame indices, e.g. 0-9,20,30-")
    ap.add_argument("--max-frames", type=int, help="max new frames per clip this run")
    ap.add_argument("--max-files", type=int, help="max clips this run")
    ap.add_argument("--max-calls", type=int, help="hard cap on API calls this run (cost guard)")
    ap.add_argument("--step", type=int, default=1, help="only frame indices %% step == 0 (testing)")
    ap.add_argument("--ref-mode", choices=["first", "first+prev"], default="first")
    ap.add_argument("--reanchor-threshold", type=float, default=12.0,
                    help="mean abs source diff (0-255) vs current anchor that triggers re-anchor; 0 = off")
    ap.add_argument("--approval", choices=["all", "sample", "none"], default="sample")
    ap.add_argument("--sample-every", type=int, default=10, help="--approval sample: review every Nth clip")
    ap.add_argument("--anchors-only", action="store_true")
    ap.add_argument("--approve-anchor", action="store_true")
    ap.add_argument("--auto-approve", action="store_true", help="never wait for approval")
    ap.add_argument("--color-lock", help="file with COLOR LOCK paragraph (overrides per-clip file)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--image-size", default="4K", choices=["1K", "2K", "4K"], help="API generation size")
    ap.add_argument("--scale", type=float, default=9.0, help="final = source x scale (9 => 2880x2160 from 320x240)")
    ap.add_argument("--rerolls", type=int, default=2, help="re-generate frames failing auto-QA")
    ap.add_argument("--qa-max-rgb-shift", type=float, default=QA_DEFAULTS["max_rgb_shift"])
    ap.add_argument("--qa-min-corr", type=float, default=QA_DEFAULTS["min_corr"])
    ap.add_argument("--qa-max-static-diff", type=float, default=QA_DEFAULTS["max_static_diff"])
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--backoff", type=float, default=10)
    ap.add_argument("--sleep", type=float, default=0, help="pause between calls (rate limits)")
    ap.add_argument("--max-consecutive-failures", type=int, default=3)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    clips = discover(args.blb, args.scene)
    if args.list or not (args.auto or args.blb or args.scene or args.frames):
        for c in clips:
            st, n = c.state(), len(c.frames())
            print(f"{c.key:16} frames={n:4} done={len(st['frames']):4} failed={len(st['failed'])} "
                  f"anchors={len(st.get('anchors', []))} approved={c.approved}")
        if not args.list:
            print("\nNothing selected: use --auto or --blb/--scene/--frames (or --list).")
        return
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key and not args.dry_run:
        sys.exit("Set GEMINI_API_KEY (or GOOGLE_API_KEY).")
    budget, total, n_clips = Budget(args.max_calls), 0, 0
    for pos, c in enumerate(clips):
        if args.max_files and n_clips >= args.max_files:
            break
        st, fr = c.state(), c.frames()
        if (fr and not args.force and not args.frames and not args.approve_anchor
                and len(st["frames"]) >= len(fr)):
            continue  # complete -> resume goes to the next clip
        n_clips += 1
        try:
            total += process_clip(c, pos, args, key, budget)
        except StopIteration as e:
            print(e)
            break
        except RuntimeError as e:
            c.log(f"clip stopped: {e}")
    print(f"done: {total} API calls this run")


if __name__ == "__main__":
    main()
