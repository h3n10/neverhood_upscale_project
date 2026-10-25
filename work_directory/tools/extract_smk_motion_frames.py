#!/usr/bin/env python3
"""Extract three spread SMK frames and verify decoded-pixel motion locally."""
import argparse, hashlib, json, pathlib, shutil, subprocess, sys
from PIL import Image, ImageChops, ImageStat

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('sample', type=pathlib.Path)
    ap.add_argument('metadata', type=pathlib.Path)
    ap.add_argument('frames_dir', type=pathlib.Path)
    ap.add_argument('--ffmpeg', type=pathlib.Path, help='ffmpeg executable (default: find ffmpeg on PATH)')
    a = ap.parse_args()
    ffmpeg = a.ffmpeg
    if ffmpeg is not None and not ffmpeg.is_file():
        raise SystemExit(f'ffmpeg executable not found: {ffmpeg}')
    if ffmpeg is None:
        found = shutil.which('ffmpeg')
        if not found:
            raise SystemExit('ffmpeg not found; add it to PATH or pass --ffmpeg <path>')
        ffmpeg = pathlib.Path(found)
    meta = json.loads(a.metadata.read_text(encoding='utf-8'))
    count = int(meta['frames'])
    if count < 3:
        raise SystemExit('sample must contain at least three frames')
    indices = sorted({0, count // 2, count - 1})
    if len(indices) != 3:
        raise SystemExit('could not choose three distinct frame indices')
    a.frames_dir.mkdir(parents=True, exist_ok=True)
    pattern = a.frames_dir / 'frame_%03d.png'
    if list(a.frames_dir.glob('frame_*.png')):
        raise SystemExit('refusing to overwrite existing frame PNGs')
    expr = 'select=' + '+'.join(f'eq(n\\,{i})' for i in indices)
    cmd = [str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-i', str(a.sample),
           '-vf', expr, '-fps_mode', 'passthrough', '-start_number', '0', str(pattern)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode:
        raise SystemExit(f'ffmpeg frame extraction failed ({proc.returncode}): {proc.stderr}')
    paths = sorted(a.frames_dir.glob('frame_*.png'))
    if len(paths) != 3:
        raise SystemExit(f'expected 3 PNGs, found {len(paths)}')
    images = [Image.open(p).convert('RGB') for p in paths]
    dimensions = [list(im.size) for im in images]
    if len(set(tuple(d) for d in dimensions)) != 1:
        raise SystemExit(f'frame dimensions disagree: {dimensions}')
    samples = []
    for idx, path, im in zip(indices, paths, images):
        samples.append({'source_frame_index': idx, 'path': str(path),
                        'dimensions': {'width': im.width, 'height': im.height},
                        'png_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'decoded_rgb_sha256': hashlib.sha256(im.tobytes()).hexdigest()})
    diffs = []
    for left in range(3):
        for right in range(left + 1, 3):
            diff = ImageChops.difference(images[left], images[right])
            changed = sum(1 for pix in diff.get_flattened_data() if pix != (0, 0, 0))
            mean = sum(ImageStat.Stat(diff).mean) / 3.0
            diffs.append({'frame_indices': [indices[left], indices[right]],
                          'changed_pixels': changed, 'total_pixels': images[left].width * images[left].height,
                          'mean_absolute_channel_difference_0_255': round(mean, 6)})
    distinct = len({s['decoded_rgb_sha256'] for s in samples}) == 3
    if not distinct or any(d['changed_pixels'] == 0 for d in diffs):
        raise SystemExit('motion check failed: sampled decoded frames are not all distinct')
    meta['sampled_frames'] = samples
    meta['motion_validation'] = {'method': 'decoded RGB pixel hashes and pairwise pixel differences',
                                 'all_three_decoded_frames_distinct': distinct,
                                 'pairwise_differences': diffs}
    a.metadata.write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'indices': indices, 'samples': samples, 'pairwise_differences': diffs}, indent=2))

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(2)