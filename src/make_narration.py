#!/usr/bin/env python3
"""Generate local Kokoro narration for the #429 stage.

Reads output/script.json (ordered literal narration from build_plan.py) and
output/manifest.json (per-beat output inclusion) and produces one WAV per
narrated beat that participates in the video: any beat with text whose
include_in.video is true. Demo beats carry no text and video-excluded beats
are skipped, so TTS is never placed over demo audio.

Inference uses real Kokoro on CPU with one English voice (af_heart, American
English). The model, config, and voice load from experiment-local files in
assets/kokoro/ — downloaded once and sha256-pinned by validate.sh during
setup — so generation needs no network. Output is 24 kHz mono 16-bit PCM
WAVs, one per beat, numbered in script order.

Each WAV duration is measured with ffprobe and written with its path to
output/audio/narration.json for the composition stage.

With --dry-run, only the beat selection is printed (no kokoro import, no
output), which is how the video-inclusion filter is exercised against case
fixtures without running the model.
"""

import json
import sys
import time
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_tools import EXPERIMENT_ROOT, ffprobe_json  # noqa: E402

VOICE = "af_heart"  # one English voice (American English)
LANG_CODE = "a"
SAMPLE_RATE = 24000
ASSET_DIR = EXPERIMENT_ROOT / "assets" / "kokoro"
MODEL_FILE = ASSET_DIR / "kokoro-v1_0.pth"
CONFIG_FILE = ASSET_DIR / "config.json"
VOICE_FILE = ASSET_DIR / "voices" / f"{VOICE}.pt"
REPO_ID = "hexgrad/Kokoro-82M"


def probe_duration(path: Path) -> float:
    probe = ffprobe_json(["-show_entries", "format=duration", str(path)])
    return float(probe["format"]["duration"])


def rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(EXPERIMENT_ROOT))
    except ValueError:
        return str(path)


def load_plan(script_path: Path, manifest_path: Path) -> tuple[list[dict], dict]:
    script = json.loads(script_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    include_in = {beat["id"]: beat["include_in"] for beat in manifest["beats"]}
    return script["beats"], include_in


def select_beats(beats: list[dict], include_in: dict) -> list[dict]:
    """Narrated video beats only: text present and include_in.video true."""
    selected = []
    for beat in beats:
        if "text" not in beat:
            continue
        if not include_in.get(beat["id"], {}).get("video", False):
            continue
        selected.append(beat)
    return selected


def check_assets() -> None:
    missing = [path for path in (MODEL_FILE, CONFIG_FILE, VOICE_FILE)
               if not path.exists()]
    if missing:
        print(f"error: Kokoro assets missing: {', '.join(map(str, missing))}",
              file=sys.stderr)
        print("run ./validate.sh to provision the pinned assets", file=sys.stderr)
        sys.exit(1)


def build_pipeline():
    from kokoro import KModel, KPipeline

    model = KModel(repo_id=REPO_ID, config=str(CONFIG_FILE),
                   model=str(MODEL_FILE)).eval()
    return KPipeline(lang_code=LANG_CODE, repo_id=REPO_ID, model=model,
                     device="cpu"), model


def write_wav(path: Path, audio: np.ndarray) -> None:
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())


def synthesize(pipeline, beat: dict) -> np.ndarray:
    """One beat -> one audio array; chunks are concatenated in order."""
    import torch

    chunks = [result.audio for result in
              pipeline(text=beat["text"], voice=str(VOICE_FILE), speed=1,
                       split_pattern=r"\n+")
              if result.audio is not None]
    if not chunks:
        raise RuntimeError(f"no audio generated for beat {beat['id']!r}")
    return torch.cat(chunks).numpy()


def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv
    args = [arg for arg in argv[1:] if arg != "--dry-run"]
    script_path = Path(args[0]) if len(args) > 0 else Path("output/script.json")
    manifest_path = Path(args[1]) if len(args) > 1 else Path("output/manifest.json")
    out_dir = Path(args[2]) if len(args) > 2 else Path("output")
    audio_dir = out_dir / "audio"

    beats, include_in = load_plan(script_path, manifest_path)
    selected = select_beats(beats, include_in)

    if dry_run:
        for beat in selected:
            print(f"would narrate: {beat['id']}")
        print(f"dry run: {len(selected)} of {len(beats)} beats selected")
        return 0

    check_assets()

    # A failed run must not leave a previous run's claim behind.
    if audio_dir.exists():
        for wav in audio_dir.glob("*.wav"):
            wav.unlink()
    narration_path = audio_dir / "narration.json"
    narration_path.unlink(missing_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    pipeline, _ = build_pipeline()
    entries = []
    total_audio = 0.0
    for index, beat in enumerate(selected, start=1):
        beat_started = time.monotonic()
        audio = synthesize(pipeline, beat)
        wav_path = audio_dir / f"{index:03d}-{beat['id']}.wav"
        write_wav(wav_path, audio)
        duration = probe_duration(wav_path)
        total_audio += duration
        beat_wall = time.monotonic() - beat_started
        entries.append({
            "beat_id": beat["id"],
            "wav": rel_path(wav_path),
            "duration_seconds": duration,
            "text": beat["text"],
        })
        print(f"  {beat['id']}: {duration:.3f}s audio in {beat_wall:.1f}s wall "
              f"({beat_wall / duration:.1f}x realtime) -> {rel_path(wav_path)}")

    wall = time.monotonic() - started
    narration_path.write_text(json.dumps({
        "voice": VOICE,
        "sample_rate": SAMPLE_RATE,
        "model_asset": rel_path(MODEL_FILE),
        "voice_asset": rel_path(VOICE_FILE),
        "wall_seconds": round(wall, 3),
        "beats": entries,
    }, indent=2) + "\n")
    print(f"narration: {len(entries)} WAVs, {total_audio:.3f}s audio in "
          f"{wall:.1f}s wall ({wall / total_audio:.1f}x realtime)")
    print(f"wrote {narration_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
