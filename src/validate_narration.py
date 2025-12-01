#!/usr/bin/env python3
"""Validation flow for the #429 local-Kokoro narration stage.

Checks the acceptance criteria:
  1. output/audio/narration.json exists with the one English voice, sample
     rate, asset paths, and the measured wall time of the generation run.
  2. Exactly the narrated video beats get a WAV: a beat is narrated iff it
     carries text and include_in.video is true (demo beats have no text, so
     TTS is never placed over demo audio). Beat order follows script.json.
  3. Every WAV is nonempty, ffprobe-readable (24 kHz mono PCM), fully decodes
     with ffmpeg, and its recorded duration matches ffprobe.
  4. No WAV exists beyond the narrated set and every recorded path exists.
  5. The generation ran with no network: the HF_HOME scratch directory set by
     validate.sh is empty (no HuggingFace downloads) and the narration run
     itself was executed under HF_HUB_OFFLINE=1 with all proxies pointing at
     a dead local port (recorded as INFO, enforced by validate.sh).
  6. The video-inclusion filter is exercised against the pptx-only case
     fixture with --dry-run: its video-excluded intro/outro beats are not
     selected and the demo beat is never narrated.
  7. Listening: recorded as UNVERIFIED on this headless host (no audio
     device); the opening WAV is retained for manual review.

Writes a full report to evidence/results-narration.md and exits non-zero on
any FAIL.
"""

import json
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_tools import EXPERIMENT_ROOT, ffmpeg, ffprobe_json  # noqa: E402
from make_narration import SAMPLE_RATE, VOICE  # noqa: E402

SCRIPT_PATH = Path("output/script.json")
MANIFEST_PATH = Path("output/manifest.json")
NARRATION_PATH = Path("output/audio/narration.json")
AUDIO_DIR = Path("output/audio")
HF_SCRATCH = Path("work/narration-hf-home")

# The pptx-only case fixture declares one video-excluded demo with intro and
# outro text: its beats must not be narrated, while the opening, the
# video-included demo beat (no text), and the closing behave normally.
PPTX_ONLY_CASE = {
    "name": "pptx-only",
    "fixture": "fixtures/plan-cases/pptx-only.json",
    "expected_selected": ["opening", "closing"],
}

RESULTS: list[tuple[str, str, str, str]] = []


def record(group: str, name: str, ok: bool, detail: str) -> None:
    RESULTS.append((group, name, "PASS" if ok else "FAIL", detail))


def note(group: str, name: str, detail: str) -> None:
    RESULTS.append((group, name, "INFO", detail))


def expected_narrated_beats() -> list[str]:
    """Beat ids that must be narrated: text present and video-included."""
    script = json.loads(SCRIPT_PATH.read_text())
    manifest = json.loads(MANIFEST_PATH.read_text())
    include_in = {beat["id"]: beat["include_in"] for beat in manifest["beats"]}
    return [beat["id"] for beat in script["beats"]
            if "text" in beat and include_in[beat["id"]].get("video", False)]


def wav_stream_info(path: Path) -> dict:
    probe = ffprobe_json(["-show_streams", "-select_streams", "a", str(path)])
    streams = probe["streams"]
    return streams[0] if len(streams) == 1 else {}


def ffmpeg_decodes(path: Path) -> bool:
    result = subprocess.run(
        [ffmpeg(), "-v", "error", "-i", str(path), "-f", "null", "-"],
        cwd=EXPERIMENT_ROOT, capture_output=True,
    )
    return result.returncode == 0 and not result.stderr


def has_nonzero_samples(path: Path) -> bool:
    with wave.open(str(path), "rb") as wav:
        frames = wav.readframes(wav.getnframes())
    return any(frames)


def check_main() -> None:
    if not NARRATION_PATH.exists():
        record("main", "narration outputs exist", False,
               f"missing {NARRATION_PATH}; run src/make_narration.py first")
        return
    if not HF_SCRATCH.is_dir():
        record("main", "offline HF scratch dir exists", False,
               f"missing {HF_SCRATCH}; validate.sh sets HF_HOME there")
    else:
        scratch_files = [p for p in HF_SCRATCH.rglob("*") if p.is_file()]
        record("main", "no HuggingFace downloads during the run",
               not scratch_files,
               f"{HF_SCRATCH} contains {len(scratch_files)} files"
               + (f": {[str(p) for p in scratch_files]}" if scratch_files else ""))

    narration = json.loads(NARRATION_PATH.read_text())
    record("main", "one English voice recorded",
           narration.get("voice") == VOICE, f"voice: {narration.get('voice')}")
    record("main", "sample rate recorded",
           narration.get("sample_rate") == SAMPLE_RATE,
           f"{narration.get('sample_rate')} Hz")
    record("main", "asset paths recorded",
           narration.get("model_asset") == "assets/kokoro/kokoro-v1_0.pth"
           and narration.get("voice_asset") == f"assets/kokoro/voices/{VOICE}.pt"
           and Path(narration.get("model_asset", "")).exists()
           and Path(narration.get("voice_asset", "")).exists(),
           f"{narration.get('model_asset')} / {narration.get('voice_asset')}")
    record("main", "generation wall time recorded",
           isinstance(narration.get("wall_seconds"), (int, float))
           and narration["wall_seconds"] > 0,
           f"{narration.get('wall_seconds', 0):.1f}s for "
           f"{len(narration.get('beats', []))} beats")

    expected = expected_narrated_beats()
    script = json.loads(SCRIPT_PATH.read_text())
    texts = {beat["id"]: beat["text"] for beat in script["beats"] if "text" in beat}
    entries = narration.get("beats", [])
    got = [entry["beat_id"] for entry in entries]
    record("main", "narration covers exactly the narrated video beats",
           got == expected, f"got {got}, want {expected}")
    record("main", "no narration over demo beats",
           all("text" in beat or beat["id"] not in got for beat in script["beats"]),
           "demo beats have no narration entries")
    record("main", "literal narration text preserved",
           all(entry["text"] == texts[entry["beat_id"]] for entry in entries),
           "every narrated text matches script.json verbatim")

    for entry in entries:
        beat_id = entry["beat_id"]
        wav = Path(entry["wav"])
        record("main", f"{beat_id} wav exists and is nonempty",
               wav.exists() and wav.stat().st_size > 0,
               f"{wav} ({wav.stat().st_size} bytes)" if wav.exists() else f"missing {wav}")
        if not wav.exists():
            continue

        stream = wav_stream_info(wav)
        record("main", f"{beat_id} 24 kHz mono PCM stream",
               stream.get("sample_rate") == str(SAMPLE_RATE)
               and stream.get("channels") == 1
               and "pcm" in stream.get("codec_name", ""),
               f"{stream.get('codec_name')} {stream.get('sample_rate')} Hz "
               f"{stream.get('channels')}ch")

        measured = float(ffprobe_json(
            ["-show_entries", "format=duration", str(wav)])["format"]["duration"])
        recorded = entry["duration_seconds"]
        record("main", f"{beat_id} measured duration recorded",
               measured > 0 and abs(measured - recorded) < 0.005,
               f"recorded {recorded:.3f}s, ffprobe {measured:.3f}s")

        record("main", f"{beat_id} fully decodes with ffmpeg",
               ffmpeg_decodes(wav),
               "ffmpeg -v error -i wav -f null - exits 0 with empty stderr")
        record("main", f"{beat_id} contains nonzero samples",
               has_nonzero_samples(wav),
               f"{wav} has audible (nonzero) PCM data")

    stray = sorted(p.name for p in AUDIO_DIR.glob("*.wav")
                   if p.name != "narration.json"
                   and p.name not in {f"{i:03d}-{e['beat_id']}.wav"
                                      for i, e in enumerate(entries, start=1)})
    record("main", "no WAVs beyond the narrated set",
           not stray and len(list(AUDIO_DIR.glob("*.wav"))) == len(entries),
           f"stray: {stray}" if stray else f"{len(entries)} WAVs, all listed")

    note("main", "network disabled during generation",
         "validate.sh runs make_narration.py with HF_HUB_OFFLINE=1, "
         "TRANSFORMERS_OFFLINE=1, HF_HOME=work/narration-hf-home, and all "
         "http(s)_proxy variables pointed at a dead local port, so any "
         "network attempt fails; the scratch-dir check above proves no "
         "HuggingFace download happened")

    note("main", "listening",
         "UNVERIFIED: this headless host has no audio device (no aplay/"
         "paplay/ffplay), so intelligibility was not listened to; "
         "output/audio/001-opening.wav is retained for manual review")


def run_pptx_only_dry_run() -> None:
    name = PPTX_ONLY_CASE["name"]
    out_dir = Path("work/plan-cases") / name
    # validate_plan.py builds this case; build it here if it has not run yet.
    if not (out_dir / "script.json").exists():
        subprocess.run(
            [sys.executable, "src/build_plan.py", PPTX_ONLY_CASE["fixture"],
             str(out_dir)],
            cwd=EXPERIMENT_ROOT, capture_output=True, check=True,
        )
    result = subprocess.run(
        [sys.executable, "src/make_narration.py", "--dry-run",
         str(out_dir / "script.json"), str(out_dir / "manifest.json"),
         str(out_dir)],
        cwd=EXPERIMENT_ROOT, capture_output=True, text=True,
    )
    selected = [line.removeprefix("would narrate: ")
                for line in result.stdout.splitlines()
                if line.startswith("would narrate: ")]
    expected = PPTX_ONLY_CASE["expected_selected"]
    record(name, "dry-run selects only video-included narrated beats",
           result.returncode == 0 and selected == expected,
           f"selected {selected}, want {expected}")
    record(name, "video-excluded intro/outro beats not narrated",
           "deck-only-intro" not in selected and "deck-only-outro" not in selected,
           "the pptx-only demo's intro/outro are excluded from the video")
    record(name, "demo beat never narrated",
           "deck-only" not in selected and "both-demo" not in selected,
           "demo beats carry no narration text")


def main() -> int:
    check_main()
    run_pptx_only_dry_run()

    lines = []
    lines.append("# Local Kokoro narration validation (#429)")
    lines.append("")
    lines.append(f"Run date: {__import__('datetime').datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("| Group | Check | Status | Detail |")
    lines.append("|---|---|---|---|")
    fails = 0
    for group, name, status, detail in RESULTS:
        lines.append(f"| {group} | {name} | {status} | {detail} |")
        if status == "FAIL":
            fails += 1
    lines.append("")
    lines.append(f"Result: {len(RESULTS)} checks, {fails} failed")
    report = "\n".join(lines)
    Path("evidence").mkdir(exist_ok=True)
    Path("evidence/results-narration.md").write_text(report + "\n")

    for line in report.splitlines():
        print(line)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
