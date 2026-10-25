from pathlib import Path
import argparse
import subprocess
from PIL import Image, ImageDraw, ImageFont

SCALERS = {
    'nearest': 'scale=960:600:flags=neighbor',
    'lanczos': 'scale=960:600:flags=lanczos',
    'hqx': 'hqx=n=3',
    'xbr': 'xbr=n=3',
    'epx': 'epx',
}

def main():
    ap = argparse.ArgumentParser(description='Compare FFmpeg classical 3x scalers on extracted PNG frames.')
    ap.add_argument('--input-dir', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    ap.add_argument('--ffmpeg', type=Path, required=True)
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    inputs = sorted(args.input_dir.glob('frame_*.png'))
    if not inputs:
        ap.error(f'no frame_*.png in {args.input_dir}')
    for src in inputs:
        tag = src.stem.removeprefix('frame_')
        for name, vf in SCALERS.items():
            out = args.output_dir / f'frame_{tag}_{name}.png'
            cmd = [str(args.ffmpeg), '-hide_banner', '-loglevel', 'error', '-y', '-i', str(src), '-vf', vf, '-frames:v', '1', str(out)]
            subprocess.run(cmd, check=True)
            with Image.open(out) as im:
                if im.size != (960, 600):
                    raise RuntimeError(f'{out} size {im.size} != (960, 600)')
        labels = list(SCALERS)
        tile = (480, 300)
        canvas = Image.new('RGB', (tile[0] * len(labels), 330), '#222222')
        draw = ImageDraw.Draw(canvas)
        for n, label in enumerate(labels):
            with Image.open(args.output_dir / f'frame_{tag}_{label}.png') as im:
                thumb = im.convert('RGB').resize(tile, Image.Resampling.LANCZOS)
                canvas.paste(thumb, (n * tile[0], 25))
            draw.text((n * tile[0] + 8, 6), label, fill='white', font=ImageFont.load_default())
        canvas.save(args.output_dir / f'comparison_frame_{tag}.jpg', quality=92)
    print(f'Compared {len(inputs)} input frame(s) x {len(SCALERS)} scalers at 3x; output={args.output_dir}')

if __name__ == '__main__':
    main()
