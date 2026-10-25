r"""Assemble upscaled frames back into video with local ffmpeg (inverse of extraction).

Reads  work_directory\upscaled\video\<blb>\<entry>\frames\frame_NNN.png  (+ state.json)
       work_directory\extracted\video\<blb>\<entry>\metadata.json         (fps_rational)
Writes work_directory\upscaled\video_encoded\<blb>\<entry>.<mkv|mp4>

Finishing steps (display versions only; frames/ stay the untouched masters):
  * held/duplicate frames get a tiny deterministic sub-pixel drift (--drift px, 0 = off)
  * film grain via ffmpeg temporal noise (--grain strength, 0 = off)
  * optional canvas (e.g. --canvas 3840x2160) centres the content on black (pillarbox)
Timing: source fps and frame count are preserved exactly.

Examples:
  python tools\scripts\assemble_video.py --list
  python tools\scripts\assemble_video.py --blb c.blb --scene 0
  python tools\scripts\assemble_video.py --auto --codec hevc --canvas 3840x2160 --grain 4
Codecs: ffv1 (lossless master, .mkv, default), h264 / hevc (.mp4, crf 12, yuv420p10 for hevc).
"""
import argparse
import hashlib
import io
import json
import math
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
UP = ROOT / "work_directory/upscaled/video"
SRC = ROOT / "work_directory/extracted/video"
OUT = ROOT / "work_directory/upscaled/video_encoded"


def find_ffmpeg(explicit=None):
    if explicit:
        if not explicit.is_file():
            sys.exit(f"ffmpeg executable not found: {explicit}")
        return str(explicit.resolve())
    p = shutil.which("ffmpeg")
    if p:
        return p
    sys.exit("ffmpeg not found; add it to PATH")


def codec_args(codec):
    return {"ffv1": (["-c:v", "ffv1", "-level", "3", "-pix_fmt", "bgr0"], "mkv"),
            "h264": (["-c:v", "libx264", "-crf", "12", "-preset", "slow", "-pix_fmt", "yuv420p"], "mp4"),
            "hevc": (["-c:v", "libx265", "-crf", "12", "-preset", "slow", "-pix_fmt", "yuv420p10le",
                      "-tag:v", "hvc1"], "mp4")}[codec]


def drift(img, k, run_pos, amp, seed):
    """Smooth deterministic wander (sub-pixel) for the k-th frame of a held run."""
    if amp <= 0:
        return img
    rnd = random.Random(f"{seed}:{run_pos}")
    px, py = rnd.uniform(0, 6.28), rnd.uniform(0, 6.28)
    dx = amp * math.sin(0.9 * k + px)
    dy = amp * math.sin(0.7 * k + py)
    return img.transform(img.size, Image.AFFINE, (1, 0, dx, 0, 1, dy), Image.BICUBIC)


def assemble(blb, entry, a, ffmpeg):
    up = UP / blb / entry
    frames = sorted((up / "frames").glob("frame_*.png"))
    meta = json.loads((SRC / blb / entry / "metadata.json").read_text())
    st = json.loads((up / "state.json").read_text()) if (up / "state.json").exists() else {"failed": {}}
    src_frames = sorted((SRC / blb / entry / "frames").glob("frame_*.png"))
    if not frames or len(frames) != len(src_frames):
        print(f"[{blb}/{entry}] incomplete ({len(frames)}/{len(src_frames)} frames) - skipped")
        return False
    if st.get("failed"):
        print(f"[{blb}/{entry}] has failed/quarantined frames - skipped")
        return False
    fps = meta.get("fps_rational") or f"{meta['fps']:.5f}"
    cargs, ext = codec_args(a.codec)
    OUT.joinpath(blb).mkdir(parents=True, exist_ok=True)
    dest = OUT / blb / f"{entry}.{ext}"
    vf = []
    if a.grain > 0:
        vf.append(f"noise=alls={a.grain}:allf=t")
    if a.canvas:
        w, h = a.canvas.split("x")
        vf.append(f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black")
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "png", "-i", "-"]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += cargs + ["-r", str(fps), str(dest)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    prev, k, run_pos = None, 0, 0
    for i, f in enumerate(frames):
        h = hashlib.sha256(src_frames[i].read_bytes()).hexdigest()
        if h == prev:
            k += 1
        else:
            k, run_pos, prev = 0, i, h
        img = Image.open(f).convert("RGB")
        if k > 0:  # held frame: drift grows with hold length
            img = drift(img, k, run_pos, a.drift, f"{blb}/{entry}")
        buf = io.BytesIO()
        img.save(buf, "PNG", compress_level=1)
        proc.stdin.write(buf.getvalue())
    proc.stdin.close()
    if proc.wait() != 0:
        print(f"[{blb}/{entry}] ffmpeg failed")
        return False
    print(f"[{blb}/{entry}] -> {dest} ({len(frames)} frames @ {fps})")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--blb", nargs="*")
    ap.add_argument("--scene", nargs="*")
    ap.add_argument("--codec", choices=["ffv1", "h264", "hevc"], default="ffv1")
    ap.add_argument("--ffmpeg", type=Path, help="ffmpeg executable (default: find ffmpeg on PATH)")
    ap.add_argument("--grain", type=float, default=3.0, help="temporal noise strength (0 off)")
    ap.add_argument("--drift", type=float, default=0.6, help="held-frame wander amplitude in output px (0 off)")
    ap.add_argument("--canvas", help="pad to WxH, e.g. 3840x2160")
    a = ap.parse_args()
    clips = [(b.name, e.name) for b in sorted(UP.glob("*")) if b.is_dir() and (not a.blb or b.name in a.blb)
             for e in sorted(b.iterdir(), key=lambda d: (len(d.name), d.name))
             if e.is_dir() and (not a.scene or e.name in a.scene)]
    if a.list or not (a.auto or a.blb or a.scene):
        for b, e in clips:
            n = len(list((UP / b / e / "frames").glob("*.png")))
            print(f"{b}/{e}: {n} upscaled frames")
        return
    ff = find_ffmpeg(a.ffmpeg)
    for b, e in clips:
        assemble(b, e, a, ff)


if __name__ == "__main__":
    main()
