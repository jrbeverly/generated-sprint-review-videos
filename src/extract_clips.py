#!/usr/bin/env python3
"""Extract declared demo clips and one poster per clip (#430 media-path spike).

Reads fixtures/demos.json and, for every entry:
  - trims input/<source> with explicit -ss/-t times and re-encodes
    (input-side -ss after -i gives frame-accurate boundaries regardless of
    keyframe position; re-encoding keeps the boundary exact),
  - preserves the source audio track when present,
  - writes output/demos/<id>.mp4,
  - extracts one poster PNG from the clip midpoint into output/demos/.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_tools import ffmpeg, parse_timestamp, run  # noqa: E402


def extract_clip(source: Path, start: float, end: float, clip: Path) -> None:
    duration = end - start
    cmd = [
        ffmpeg(), "-y", "-v", "error",
        "-i", str(source),
        "-ss", f"{start:.3f}",
        "-t", f"{duration:.3f}",
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(clip),
    ]
    result = run(cmd)
    if result.returncode != 0 or not clip.exists():
        raise RuntimeError(f"clip extraction failed for {clip}: {result.stderr.decode()}")


def extract_poster(clip: Path, at_seconds: float, poster: Path) -> None:
    cmd = [
        ffmpeg(), "-y", "-v", "error",
        "-i", str(clip),
        "-ss", f"{at_seconds:.3f}",
        "-frames:v", "1",
        "-q:v", "2",
        str(poster),
    ]
    result = run(cmd)
    if result.returncode != 0 or not poster.exists():
        raise RuntimeError(f"poster extraction failed for {poster}: {result.stderr.decode()}")


def main() -> None:
    fixture = json.loads(Path("fixtures/demos.json").read_text())
    out_dir = Path("output/demos")
    out_dir.mkdir(parents=True, exist_ok=True)

    for demo in fixture["demos"]:
        demo_id = demo["id"]
        if len(sys.argv) > 1 and demo_id != sys.argv[1]:
            continue
        source = Path("input") / demo.get("source", "sprint-demo.mp4")
        start = parse_timestamp(demo["start"])
        end = parse_timestamp(demo["end"])
        if not (0 <= start < end <= fixture["source_duration_seconds"]):
            raise ValueError(f"bad range for {demo_id}: {start}..{end}")

        clip = out_dir / f"{demo_id}.mp4"
        extract_clip(source, start, end, clip)

        poster_at = (end - start) / 2
        extract_poster(clip, poster_at, out_dir / f"{demo_id}-poster.png")
        print(f"{demo_id}: {start:.3f}-{end:.3f} -> {clip} (+ poster at {poster_at:.3f}s)")


if __name__ == "__main__":
    main()
