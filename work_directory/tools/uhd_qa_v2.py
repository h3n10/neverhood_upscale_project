"""Intent-aware QA for upscales of a 320x240 source (does NOT penalise added fine detail).

Gates (pass/fail, must hold for any candidate):
  G1 layout    : after per-channel colour matching, band-limited (<= source Nyquist) SSIM vs source
  G2 colour    : 32x24 block-mean Lab dE vs source (hue/exposure drift), plus global RGB shift
Detail is NOT scored automatically (no metric separates real clay texture from stair/ringing artefacts);
  it is rated visually on 4K crops with the rubric in knowledge/qa_process.md, but only for candidates that pass G1+G2.

Usage: python uhd_qa_v2.py DIR SRC.png method1 method2 ...  (files DIR/frame_000_<m>_2880x2160.png)
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

d = Path(sys.argv[1]); src = Image.open(sys.argv[2]).convert('RGB'); names = sys.argv[3:]
SW, SH = src.size
S = np.asarray(src, np.float64)

def rgb2lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = (c @ m.T) / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)

def lab_blocks(im, bw=32, bh=24):
    a = np.asarray(im.convert('RGB').resize((bw, bh), Image.Resampling.BOX), np.float64)
    return rgb2lab(a)

def ssim(a, b, sigma=1.5):
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    g = lambda x: ndi.gaussian_filter(x, sigma)
    ma, mb = g(a), g(b)
    va, vb, cab = g(a * a) - ma ** 2, g(b * b) - mb ** 2, g(a * b) - ma * mb
    return float((((2 * ma * mb + c1) * (2 * cab + c2)) / ((ma ** 2 + mb ** 2 + c1) * (va + vb + c2))).mean())

def colour_match(x, ref):
    out = x.copy()
    for c in range(3):
        out[..., c] = (x[..., c] - x[..., c].mean()) / (x[..., c].std() + 1e-9) * ref[..., c].std() + ref[..., c].mean()
    return out

src_lab = lab_blocks(src)
res = {}
for n in names:
    im = Image.open(next(d.glob(f'frame_000_{n}_2880x2160.png'))).convert('RGB')
    back = np.asarray(im.resize((SW, SH), Image.Resampling.LANCZOS), np.float64)
    lp_s = ndi.gaussian_filter(S, (2, 2, 0)); lp_b = ndi.gaussian_filter(colour_match(back, S), (2, 2, 0))
    g1 = float(np.mean([ssim(lp_s[..., c], lp_b[..., c]) for c in range(3)]))
    de = np.sqrt(((lab_blocks(im) - src_lab) ** 2).sum(-1))
    shift = (back.mean((0, 1)) - S.mean((0, 1)))
    r = {'G1_layout_ssim_bandlimited_colourmatched': round(g1, 4),
         'G2_block_dE_mean': round(float(de.mean()), 2), 'G2_block_dE_p95': round(float(np.percentile(de, 95)), 2),
         'rgb_shift': [round(float(x), 2) for x in shift]}
    r['G1_pass'] = g1 >= 0.95
    r['G2_pass'] = bool(de.mean() <= 6 and np.abs(shift).max() <= 8)
    r['gates_pass'] = bool(r['G1_pass'] and r['G2_pass'])
    res[n] = r
    print(n, r)
(d / 'qa_v2_metrics.json').write_text(json.dumps(res, indent=1))



