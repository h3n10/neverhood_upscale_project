"""Compare 4K upscales of one frame: no-reference detail/sharpness plus alignment-aware low-frequency fidelity.
Fidelity is checked only below the source Nyquist, because detail above it cannot be verified from the source."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

d = Path(sys.argv[1]); src_path = sys.argv[2]
names = ['nearest', 'bicubic', 'lanczos', 'epx', 'hqx', 'xbr', 'gemini']
W, H = 3840, 2880
gray = lambda im: np.asarray(im.convert('L'), np.float64)

def hf_fraction(g, cutoff):
    f = np.abs(np.fft.fftshift(np.fft.fft2(g - g.mean()))) ** 2
    fy = np.fft.fftshift(np.fft.fftfreq(g.shape[0]))[:, None]
    fx = np.fft.fftshift(np.fft.fftfreq(g.shape[1]))[None, :]
    r = np.hypot(fx, fy)
    return f[r > cutoff].sum() / f.sum()

def shift_search(a, b, maxs=24):
    # integer pixel shift (at 160x120 grid scaled) maximizing correlation
    best = (-2, 0, 0)
    for dy in range(-maxs, maxs + 1, 2):
        for dx in range(-maxs, maxs + 1, 2):
            bb = np.roll(np.roll(b, dy, 0), dx, 1)
            c = np.corrcoef(a[maxs:-maxs, maxs:-maxs].ravel(), bb[maxs:-maxs, maxs:-maxs].ravel())[0, 1]
            if c > best[0]: best = (c, dy, dx)
    return best

src = Image.open(src_path).convert('RGB')
ref = np.asarray(src.resize((160, 120), Image.Resampling.LANCZOS), np.float64)
nyq = 0.5 * 320 / W  # source Nyquist in cycles/pixel at 4K
res = {}
for n in names:
    im = Image.open(d / f'frame_000_{n}_3840x2880.png').convert('RGB')
    g = gray(im)
    gy, gx = np.gradient(ndi.gaussian_filter(g, 0.7))
    lap = ndi.laplace(g)
    small = np.asarray(im.resize((160, 120), Image.Resampling.LANCZOS), np.float64)
    sg, rg = small.mean(2), ref.mean(2)
    c, dy, dx = shift_search(rg, sg, 8)
    aligned = np.roll(np.roll(small, dy, 0), dx, 1)
    m = 8
    diff = (aligned - ref)[m:-m, m:-m]
    mse = (diff ** 2).mean()
    # per-channel gain-corrected fidelity (removes global colour/exposure shift)
    res[n] = {
        'laplacian_var': round(float(lap.var()), 1),
        'mean_gradient': round(float(np.hypot(gx, gy).mean()), 3),
        'hf_energy_above_source_nyquist_pct': round(100 * hf_fraction(g[::2, ::2], nyq * 2), 3),
        'lowfreq_corr_160x120': round(float(c), 5),
        'best_shift_px_160grid': [int(dy), int(dx)],
        'lowfreq_psnr_aligned_db': round(float(10 * np.log10(255 ** 2 / mse)), 2),
        'mean_rgb_shift_vs_source': [round(float(x), 2) for x in (aligned - ref)[m:-m, m:-m].mean((0, 1))],
    }
Path(d / 'uhd_metrics.json').write_text(json.dumps(res, indent=1))
for n, r in res.items(): print(n, r)
