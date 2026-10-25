from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib
import shutil
import subprocess
import wave
from fractions import Fraction

import numpy as np
from PIL import Image
from scipy.signal import resample_poly, stft, welch

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXTRACTED = ROOT / "work_directory" / "extracted" / "audio" / "a.blb"
UPSCALED = ROOT / "work_directory" / "upscaled" / "audio" / "a.blb"
QA = ROOT / "work_directory" / "qa" / "audio" / "T28"
SFX_IDS = [0, 2, 3, 10, 11, 16, 71, 182, 294, 319]
MUSIC_IDS = [126, 128, 131]
SAMPLE_IDS = SFX_IDS + MUSIC_IDS


def read_wav(path: pathlib.Path):
    with wave.open(str(path), "rb") as f:
        channels, width, rate, count = f.getnchannels(), f.getsampwidth(), f.getframerate(), f.getnframes()
        raw = f.readframes(count)
    if channels != 1 or width != 2:
        raise ValueError(f"Expected mono s16 WAV: {path} ({channels} ch/{width * 8} bit)")
    return np.frombuffer(raw, dtype="<i2").astype(np.int32), rate


def write_wav(path: pathlib.Path, samples: np.ndarray, rate: int):
    pcm = np.clip(np.rint(samples), -32768, 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(pcm.tobytes())


def sha256(path: pathlib.Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def metrics(path: pathlib.Path, shift: int | None, reference=None):
    x, rate = read_wav(path)
    xf = x.astype(np.float64)
    n = len(x)
    peak = int(np.max(np.abs(x))) if n else 0
    rms = float(np.sqrt(np.mean(xf * xf))) if n else 0.0
    delta = np.diff(xf)
    seg = min(4096, n)
    freq, power = welch(xf, fs=rate, nperseg=max(16, seg)) if n >= 16 else (np.array([]), np.array([]))
    total = float(np.sum(power)) if len(power) else 0.0
    bw99 = float(freq[min(np.searchsorted(np.cumsum(power), total * 0.99), len(freq) - 1)]) if total else 0.0
    high = float(np.sum(power[freq >= min(8000, rate / 2)])) if len(power) else 0.0
    noise = float(np.median(power[(freq >= min(8000, rate / 2)) & (freq <= min(10000, rate / 2))])) if len(power) and np.any((freq >= min(8000, rate / 2)) & (freq <= min(10000, rate / 2))) else 0.0
    row = {
        "file": str(path.relative_to(ROOT)), "sha256": sha256(path), "sample_rate_hz": rate,
        "bits": 16, "channels": 1, "samples": n, "duration_s": n / rate,
        "shift_value": shift, "reconstruction_grid_step": (2 ** shift if shift is not None and shift != 255 else 1),
        "grid_aligned_fraction": (float(np.mean(np.remainder(x, 2 ** shift) == 0)) if shift is not None and shift not in (255, 0) else (1.0 if shift in (255, 0) else None)),
        "rms_dbfs": (20 * math.log10(max(rms, 1e-12) / 32768)), "peak_dbfs": (20 * math.log10(max(peak, 1) / 32768)),
        "peak_sample": peak, "clipped_samples": int(np.count_nonzero((x <= -32768) | (x >= 32767))),
        "dc_offset": float(np.mean(xf)) if n else 0.0,
        "bandwidth_99_percent_hz": bw99,
        "power_fraction_above_8khz": high / total if total else 0.0,
        "median_spectral_level_8_10khz_dbfs_per_bin": (10 * math.log10(max(noise, 1e-30) / (32768 ** 2)) if noise else None),
        "max_adjacent_step": float(np.max(np.abs(delta))) if len(delta) else 0.0,
        "p99_9_adjacent_step": float(np.percentile(np.abs(delta), 99.9)) if len(delta) else 0.0,
        "loop_end_to_start_step": float(abs(x[0] - x[-1])) if n else 0.0,
        "loop_slope_mismatch": float(abs((x[1] - x[0]) - (x[-1] - x[-2]))) if n > 2 else 0.0,
    }
    if reference is not None:
        original, original_rate = reference
        y = xf
        if rate != original_rate:
            ratio = Fraction(original_rate, rate)
            y = resample_poly(y, ratio.numerator, ratio.denominator)
        count = min(len(original), len(y))
        err = y[:count] - original[:count]
        signal_power = float(np.mean(original[:count].astype(np.float64) ** 2)) if count else 0.0
        error_power = float(np.mean(err ** 2)) if count else 0.0
        row["change_snr_db_vs_source"] = 10 * math.log10(max(signal_power, 1e-30) / max(error_power, 1e-30))
        row["correlation_vs_source"] = float(np.corrcoef(original[:count], y[:count])[0, 1]) if count > 1 else None
    return row


def spectrogram(path: pathlib.Path, out: pathlib.Path):
    x, rate = read_wav(path)
    x = x[: min(len(x), rate * 8)].astype(np.float32)
    if not len(x):
        return
    nperseg = min(2048, len(x))
    if nperseg < 16:
        return
    _, _, z = stft(x, fs=rate, nperseg=nperseg, noverlap=nperseg * 3 // 4, boundary=None)
    db = 20 * np.log10(np.maximum(np.abs(z), 1e-8) / 32768)
    img = np.clip((db + 90) * (255 / 90), 0, 255).astype(np.uint8)
    image = Image.fromarray(np.flipud(img), mode="L").resize((768, 384), Image.Resampling.NEAREST)
    image.save(out)


def main():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg not found on PATH")
    QA.mkdir(parents=True, exist_ok=True)
    rows = []
    originals = {}
    for entry_id in SAMPLE_IDS:
        source = EXTRACTED / str(entry_id) / "audio.wav"
        meta = json.loads((EXTRACTED / str(entry_id) / "metadata.json").read_text(encoding="utf-8"))
        originals[entry_id] = read_wav(source)
        shift = meta["shift_value"]
        row = metrics(source, shift)
        row["asset_id"] = entry_id
        row["kind"] = meta["kind"]
        rows.append(row)
        spectrogram(source, QA / f"{entry_id}_source_spectrogram.png")

    candidates = []

    def ffmpeg_candidate(asset_id: int, label: str, audio_filter: str, out_rate: int | None = None):
        src = EXTRACTED / str(asset_id) / "audio.wav"
        dest = UPSCALED / str(asset_id) / f"{label}.wav"
        dest.parent.mkdir(parents=True, exist_ok=True)
        cmd = [ffmpeg, "-v", "error", "-y", "-i", str(src), "-af", audio_filter]
        if out_rate:
            cmd += ["-ar", str(out_rate)]
        cmd += ["-c:a", "pcm_s16le", str(dest)]
        subprocess.run(cmd, check=True, capture_output=True)
        shift = json.loads((EXTRACTED / str(asset_id) / "metadata.json").read_text(encoding="utf-8"))["shift_value"]
        row = metrics(dest, shift, originals[asset_id])
        row.update(asset_id=asset_id, kind="experiment", method=label, parameters=audio_filter)
        rows.append(row)
        candidates.append({"asset_id": asset_id, "path": str(dest.relative_to(ROOT)), "method": label, "parameters": audio_filter,
                           "sha256": row["sha256"], "sample_rate_hz": row["sample_rate_hz"], "samples": row["samples"],
                           "duration_s": row["duration_s"], "disposition": "diagnostic only; not approved for replacement"})
        spectrogram(dest, QA / f"{asset_id}_{label}_spectrogram.png")

    ffmpeg_candidate(128, "afftdn_nr6_nfminus45", "afftdn=nr=6:nf=-45")
    ffmpeg_candidate(294, "adeclick_default", "adeclick")
    ffmpeg_candidate(128, "resampled_44100", "aresample=44100", 44100)
    ffmpeg_candidate(128, "resampled_48000", "aresample=48000", 48000)

    # This diagnostic adds TPDF noise at one reconstructed code step; it is not a restoration.
    asset_id = 128
    src = EXTRACTED / str(asset_id) / "audio.wav"
    dest = UPSCALED / str(asset_id) / "tpdf_one_code_step_diagnostic.wav"
    x, rate = originals[asset_id]
    shift = json.loads((EXTRACTED / str(asset_id) / "metadata.json").read_text(encoding="utf-8"))["shift_value"]
    step = 2 ** shift
    rng = np.random.default_rng(2801)
    noise = (rng.random(len(x)) - rng.random(len(x))) * step
    write_wav(dest, x.astype(np.float64) + noise, rate)
    row = metrics(dest, shift, originals[asset_id])
    row.update(asset_id=asset_id, kind="experiment", method="tpdf_one_code_step_diagnostic", parameters=f"seed=2801; TPDF peak about {step} PCM counts")
    rows.append(row)
    candidates.append({"asset_id": asset_id, "path": str(dest.relative_to(ROOT)), "method": "TPDF diagnostic", "parameters": f"seed=2801; one code-step scale={step}",
                       "sha256": row["sha256"], "sample_rate_hz": rate, "samples": len(x), "duration_s": len(x) / rate,
                       "disposition": "rejected for replacement; adds noise, not recovered detail"})
    spectrogram(dest, QA / f"{asset_id}_tpdf_diagnostic_spectrogram.png")

    fieldnames = sorted({key for row in rows for key in row})
    with (QA / "metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    report = {
        "task": "T28", "date": "2026-10-25", "source": "DATA_source/a.blb (read-only)",
        "sample_ids": {"sfx": SFX_IDS, "music": MUSIC_IDS},
        "decoder": "work_directory/tools/extract_all.py; mono s16le WAV at 22050 Hz; ext-data shift FF=raw s16le, otherwise signed delta accumulation then << shift",
        "experiments": candidates,
        "spectrograms": "first 8 seconds, log magnitude, linear frequency bins to Nyquist, normalized -90..0 dBFS",
        "limitations": ["high-band level is a spectral proxy, not calibrated noise-floor measurement", "loop boundary values are diagnostic; game loop behavior was not audio-loopback tested", "no listening session was recorded", "resampling adds no source bandwidth"],
    }
    (QA / "analysis.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} metric rows, {len(candidates)} candidates, and spectrograms to {QA.relative_to(ROOT)}")
    for c in candidates:
        print(f"candidate {c['asset_id']} {c['method']}: {c['path']}")


if __name__ == "__main__":
    main()
