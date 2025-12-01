"""Shared helpers for the #430 media-path spike.

Resolves the pinned ffmpeg/ffprobe binaries from the npm-installed static
packages so every script in this experiment uses the same pinned versions.
"""

import json
import subprocess
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_bin(module: str, out: str) -> str:
    result = subprocess.run(
        ["node", "-e", f"import('{module}').then(m=>process.stdout.write(m.{out}))"],
        cwd=EXPERIMENT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    path = result.stdout.strip()
    if not Path(path).exists():
        raise RuntimeError(f"resolved {module} binary does not exist: {path}")
    return path


def ffmpeg() -> str:
    return _resolve_bin("ffmpeg-static", "default")


def ffprobe() -> str:
    return _resolve_bin("ffprobe-static", "default.path")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a command from the experiment root (bytes capture), returning the completed process."""
    return subprocess.run(cmd, cwd=EXPERIMENT_ROOT, capture_output=True)


def ffprobe_json(args: list[str]) -> dict:
    result = run([ffprobe(), "-v", "error", "-of", "json", *args])
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return json.loads(result.stdout)


def parse_timestamp(ts: str) -> float:
    """Parse HH:MM:SS.mmm into seconds."""
    hours, minutes, seconds = ts.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
