r"""Upscale a single frame with the Gemini image model (REST, stdlib only).

Usage:
  set GEMINI_API_KEY=...            (key is never stored in the repo)
  python tools\scripts\gemini_upscale_frame.py [--input PNG] [--out DIR] [--model NAME] [--prompt-file TXT]

Default input: work_directory\extracted\video\c.blb\0\frames\frame_000.png
Outputs go to work_directory\upscaled\gemini_test\ (response image + request metadata).
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IN = ROOT / "work_directory/extracted/video/c.blb/0/frames/frame_000.png"
DEFAULT_OUT = ROOT / "work_directory/upscaled/gemini_test"
DEFAULT_MODEL = "gemini-2.5-flash-image"

PROMPT = (
    "This is a frame from the 1996 claymation adventure game The Neverhood, "
    "low resolution with a limited palette. Upscale it to 4x resolution "
    "(preserve the aspect ratio). Keep the composition, every object, colors and "
    "clay-sculpt look exactly as in the source: do not add, remove, move or "
    "redesign anything, do not add text, borders or new details. Only restore "
    "sharp edges, clean clay texture and remove palette dithering/compression "
    "artifacts. Return only the image."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--prompt-file", type=Path)
    ap.add_argument("--image-size", default="", help="1K/2K/4K (Gemini 3 image models only)")
    ap.add_argument("--aspect", default="", help="e.g. 4:3")
    a = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        sys.exit("Set GEMINI_API_KEY (or GOOGLE_API_KEY) in the environment.")
    prompt = a.prompt_file.read_text(encoding="utf-8") if a.prompt_file else PROMPT
    src = a.input.read_bytes()

    body = {
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/png",
                             "data": base64.b64encode(src).decode()}},
        ]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    img_cfg = {k: v for k, v in (("imageSize", a.image_size), ("aspectRatio", a.aspect)) if v}
    if img_cfg:
        body["generationConfig"]["imageConfig"] = img_cfg
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{a.model}:generateContent")
    req = urllib.request.Request(
        url, json.dumps(body).encode(),
        {"Content-Type": "application/json", "x-goog-api-key": key})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode(errors='replace')[:2000]}")

    a.out.mkdir(parents=True, exist_ok=True)
    stem = a.input.stem
    saved = []
    for cand in resp.get("candidates", []):
        for p in cand.get("content", {}).get("parts", []):
            d = p.get("inlineData") or p.get("inline_data")
            if d:
                f = a.out / f"{stem}_gemini_{len(saved)}.png"
                f.write_bytes(base64.b64decode(d["data"]))
                saved.append(f)
            elif "text" in p:
                print("model text:", p["text"])
    meta = {"model": a.model, "image_config": img_cfg, "prompt": prompt, "input": str(a.input),
            "seconds": round(time.time() - t0, 1),
            "usage": resp.get("usageMetadata"), "outputs": [str(s) for s in saved]}
    (a.out / f"{stem}_gemini_meta.json").write_text(json.dumps(meta, indent=2))
    if not saved:
        sys.exit("No image returned: " + json.dumps(resp)[:1500])
    try:
        from PIL import Image
        print("input size:", Image.open(a.input).size)
        for s in saved:
            print(s, Image.open(s).size)
    except ImportError:
        print("saved:", *saved)


if __name__ == "__main__":
    main()

