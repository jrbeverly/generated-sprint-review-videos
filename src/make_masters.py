#!/usr/bin/env python3
"""Generate the synthetic master recordings for the #430 media-path spike.

Outputs:
  input/frames/frame-%04d.png   numbered 1920x1080 frames, 30 fps, 4 scenes
  input/sprint-demo.mp4         H.264 video + per-scene sine tones
  input/silent-demo.mp4         same video + digital silence

Every frame carries a human-readable "FRAME nnnn" label, a per-scene
background/label, a moving marker, and a 12-bit binary strip in the top-left
corner so scripts can read the frame index back without OCR. The GOP is forced
to 250 frames so declared clip boundaries are provably not keyframe-aligned.

Scene layout (16 s total, scene k covers [4k, 4k+4) seconds):
  scene 0: 440 Hz,  scene 1: 660 Hz,  scene 2: 880 Hz,  scene 3: 1320 Hz
All tone frequencies are multiples of 0.25 Hz and scenes start at integer
second multiples of 4, so tone phase is continuous at scene boundaries
(sin(2*pi*f*t) is 0 at every boundary) and no clicks are introduced.
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_tools import ffmpeg, run  # noqa: E402

FPS = 30
WIDTH, HEIGHT = 1920, 1080
SCENES = 4
SCENE_SECONDS = 4.0
TOTAL_SECONDS = SCENES * SCENE_SECONDS
TOTAL_FRAMES = int(TOTAL_SECONDS * FPS)

# 12-bit strip: supports frame indices up to 4095 (TOTAL_FRAMES = 480).
STRIP_BITS = 12
STRIP_SQUARE = 48
STRIP_X0, STRIP_Y0 = 40, 40

SCENE_COLORS = [(27, 58, 107), (43, 107, 27), (107, 27, 58), (107, 90, 27)]
SCENE_NAMES = ["SCENE 0", "SCENE 1", "SCENE 2", "SCENE 3"]
TONE_HZ = [440, 660, 880, 1320]
GOP_FRAMES = 250

FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


def scene_of_frame(n: int) -> int:
    return int(n / FPS / SCENE_SECONDS)


def render_frame(n: int, out_path: Path, font: ImageFont.FreeTypeFont) -> None:
    scene = scene_of_frame(n)
    img = Image.new("RGB", (WIDTH, HEIGHT), SCENE_COLORS[scene])
    draw = ImageDraw.Draw(img)

    # Neutral band behind the binary strip for contrast after lossy encoding.
    strip_w = STRIP_X0 * 2 + STRIP_BITS * (STRIP_SQUARE + 22) - 22
    draw.rectangle(
        [STRIP_X0 - 10, STRIP_Y0 - 10, STRIP_X0 - 10 + strip_w, STRIP_Y0 + STRIP_SQUARE + 10],
        fill=(90, 90, 90),
    )
    for i in range(STRIP_BITS):
        bit = (n >> (STRIP_BITS - 1 - i)) & 1
        x = STRIP_X0 + i * (STRIP_SQUARE + 22)
        draw.rectangle([x, STRIP_Y0, x + STRIP_SQUARE, STRIP_Y0 + STRIP_SQUARE],
                       fill=(255, 255, 255) if bit else (0, 0, 0))

    draw.text((520, 70), f"FRAME {n:04d}", font=font, fill=(255, 255, 255))
    draw.text((520, 260), f"{SCENE_NAMES[scene]}  tone {TONE_HZ[scene]} Hz  t={n / FPS:.3f}s",
              font=font, fill=(255, 255, 255))

    # Moving marker so adjacent frames differ beyond the digits themselves.
    x = 200 + (n * 23) % (WIDTH - 400)
    draw.ellipse([x, 620, x + 90, 710], fill=(255, 255, 255))

    img.save(out_path)


def build_frames(frames_dir: Path) -> None:
    frames_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(str(FONT_PATH), 130)
    for n in range(TOTAL_FRAMES):
        render_frame(n, frames_dir / f"frame-{n:04d}.png", font)
    print(f"rendered {TOTAL_FRAMES} frames to {frames_dir}")


def tone_filter() -> str:
    """Piecewise per-scene sine tones; phase is continuous at scene edges."""
    terms = []
    for k, hz in enumerate(TONE_HZ):
        lower = f"lt(t\\,{(k + 1) * SCENE_SECONDS:.0f})"
        expr = f"if({lower}\\,0.5*sin(2*PI*{hz}*t)\\,"
        terms.append(expr)
    terms.append("0.5*sin(2*PI*1320*t)")
    terms.append(")" * SCENES)
    return f"aevalsrc=exprs={''.join(terms)}:s=48000:d={TOTAL_SECONDS:.0f}"


def encode_master(frames_dir: Path, audio: str, out_path: Path) -> None:
    cmd = [
        ffmpeg(), "-y", "-v", "error",
        "-framerate", str(FPS), "-i", str(frames_dir / "frame-%04d.png"),
        "-f", "lavfi", "-i", audio,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-x264-params", f"keyint={GOP_FRAMES}:min-keyint={GOP_FRAMES}:scenecut=0",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart",
        str(out_path),
    ]
    result = run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg encode failed for {out_path}: {result.stderr}")
    print(f"encoded {out_path}")


def main() -> None:
    input_dir = Path("input")
    frames_dir = input_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # Regenerate frames only when missing; they are deterministic.
    if not (frames_dir / f"frame-{TOTAL_FRAMES - 1:04d}.png").exists():
        build_frames(frames_dir)
    else:
        print(f"frames already present in {frames_dir}")

    encode_master(frames_dir, tone_filter(), input_dir / "sprint-demo.mp4")
    encode_master(
        frames_dir,
        f"anullsrc=r=48000:cl=stereo:d={TOTAL_SECONDS:.0f}",
        input_dir / "silent-demo.mp4",
    )


if __name__ == "__main__":
    main()
