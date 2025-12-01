#!/usr/bin/env python3
"""Build the #428 presentation plan: ordered beats + artifact metadata.

Reads a presentation-plan fixture (default fixtures/sprint-analysis.json) and
the one local master recording (input/sprint-demo.mp4):

  1. Validates the whole plan first: unique filename-safe demo IDs, non-empty
     titles, and explicit timestamps with 0 <= start < end <= source duration
     (measured from the master). Any violation exits non-zero before any
     output is written, so an invalid plan can never be claimed complete.
  2. Builds one ordered beat list in fixture array order: a fixed opening,
     then for each demo an optional literal intro, the demo beat, and an
     optional literal outcome/outro, then a fixed closing. Demos excluded
     from both outputs are omitted entirely.
  3. Extracts each demo included in either output exactly once, reusing the
     #430 extraction path, and measures clip durations with ffprobe. Posters
     are extracted only for PPTX-included demos (PDF follows PPTX).
  4. Writes output/script.json (ordered literal narration; demo beats carry
     no text) and output/manifest.json (beat/demo IDs, source ranges,
     artifact paths, measured durations; mp4_offset_seconds stays null until
     the composition stage fills it).

Ordinary JSON only: nothing is inferred, no ranges are discovered, and no
narration-overlay option exists.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_clips import extract_clip, extract_poster  # noqa: E402
from media_tools import EXPERIMENT_ROOT, ffprobe_json, parse_timestamp  # noqa: E402

MASTER = Path("input/sprint-demo.mp4")
OPENING_TEXT = "Welcome to this sprint review."
CLOSING_TEXT = "That concludes this sprint review. Thank you."
FILENAME_SAFE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
OUTPUTS = ("pptx", "pdf", "video")
METADATA_KEYS = ("epic", "release", "business_value")
TEXT_KEYS = ("intro", "outro")


def probe_duration(path: Path) -> float:
    probe = ffprobe_json(["-show_entries", "format=duration", str(path)])
    return float(probe["format"]["duration"])


def load_demos(fixture: dict, source_duration: float) -> list[dict]:
    """Validate the fixture and return parsed demos with defaults applied.

    Raises ValueError on any invalid plan, before any output exists.
    """
    if fixture.get("pdf_follows_pptx", True) is not True:
        raise ValueError("unsupported plan: pdf_follows_pptx must be true "
                         "(the vision defines no separate PDF switch)")
    demos = fixture.get("demos")
    if not isinstance(demos, list) or not demos:
        raise ValueError("fixture must declare a non-empty 'demos' array")

    seen: set[str] = set()
    parsed: list[dict] = []
    for demo in demos:
        if not isinstance(demo, dict):
            raise ValueError("each demo must be an object")
        demo_id = demo.get("id")
        if not isinstance(demo_id, str) or not FILENAME_SAFE.match(demo_id):
            raise ValueError(f"demo id {demo_id!r} is not filename-safe "
                             "(expected lowercase letters, digits, hyphens)")
        if demo_id in seen:
            raise ValueError(f"duplicate demo id {demo_id!r}")
        seen.add(demo_id)

        title = demo.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"demo {demo_id!r} must declare a non-empty title")
        try:
            start = parse_timestamp(demo["start"])
            end = parse_timestamp(demo["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"demo {demo_id!r} timestamps must be HH:MM:SS.mmm: {exc}")
        if not (0 <= start < end <= source_duration):
            raise ValueError(f"demo {demo_id!r} range {demo['start']}..{demo['end']} "
                             f"violates 0 <= start < end <= {source_duration:.3f}")

        include_in_pptx = demo.get("include_in_pptx", True)
        include_in_video = demo.get("include_in_video", True)
        if not isinstance(include_in_pptx, bool) or not isinstance(include_in_video, bool):
            raise ValueError(f"demo {demo_id!r} inclusion flags must be booleans")

        entry = {
            "id": demo_id,
            "title": title.strip(),
            "start": demo["start"],
            "end": demo["end"],
            "start_seconds": start,
            "end_seconds": end,
            "include_in_pptx": include_in_pptx,
            "include_in_video": include_in_video,
        }
        for key in METADATA_KEYS + TEXT_KEYS:
            value = demo.get(key)
            if value is None:
                continue
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"demo {demo_id!r} {key} must be non-empty text when supplied")
            entry[key] = value
        parsed.append(entry)
    return parsed


def build_beats(demos: list[dict]) -> list[dict]:
    """One ordered beat list in fixture order; both-excluded demos are omitted."""
    beats = [{
        "id": "opening", "kind": "opening", "text": OPENING_TEXT,
        "include_in": {"pptx": True, "video": True},
    }]
    for demo in demos:
        if not (demo["include_in_pptx"] or demo["include_in_video"]):
            continue
        include = {"pptx": demo["include_in_pptx"], "video": demo["include_in_video"]}
        if "intro" in demo:
            beats.append({"id": f"{demo['id']}-intro", "kind": "intro",
                          "demo_id": demo["id"], "text": demo["intro"],
                          "include_in": dict(include)})
        beats.append({"id": demo["id"], "kind": "demo", "demo_id": demo["id"],
                      "title": demo["title"], "include_in": dict(include)})
        if "outro" in demo:
            beats.append({"id": f"{demo['id']}-outro", "kind": "outro",
                          "demo_id": demo["id"], "text": demo["outro"],
                          "include_in": dict(include)})
    beats.append({
        "id": "closing", "kind": "closing", "text": CLOSING_TEXT,
        "include_in": {"pptx": True, "video": True},
    })
    return beats


def output_beats(beats: list[dict], output: str) -> list[str]:
    """Ordered beat IDs for one output; PDF follows PPTX inclusion."""
    key = "pptx" if output == "pdf" else output
    return [beat["id"] for beat in beats if beat["include_in"][key]]


def rel_path(path: Path) -> str:
    """Path string relative to the experiment root when possible."""
    try:
        return str(path.resolve().relative_to(EXPERIMENT_ROOT))
    except ValueError:
        return str(path)


def extract_and_measure(demos: list[dict], out_dir: Path) -> None:
    """Extract each included demo once and measure its clip duration.

    A poster is extracted only for PPTX-included demos (the PDF card and the
    PPTX cover share it; a video-only demo has no deck representation).
    """
    clip_dir = out_dir / "demos"
    clip_dir.mkdir(parents=True, exist_ok=True)
    for demo in demos:
        if not (demo["include_in_pptx"] or demo["include_in_video"]):
            continue
        demo_id = demo["id"]
        clip = clip_dir / f"{demo_id}.mp4"
        extract_clip(MASTER, demo["start_seconds"], demo["end_seconds"], clip)
        artifacts = {"clip": rel_path(clip)}
        if demo["include_in_pptx"]:
            poster = clip_dir / f"{demo_id}-poster.png"
            midpoint = (demo["end_seconds"] - demo["start_seconds"]) / 2
            extract_poster(clip, midpoint, poster)
            artifacts["poster"] = rel_path(poster)
        demo["artifacts"] = artifacts
        demo["duration_seconds"] = probe_duration(clip)
        print(f"  extracted {demo_id}: {demo['start']}..{demo['end']} -> "
              f"{rel_path(clip)} ({demo['duration_seconds']:.3f}s)")


def script_beat(beat: dict) -> dict:
    entry = {"id": beat["id"], "kind": beat["kind"]}
    if "demo_id" in beat:
        entry["demo_id"] = beat["demo_id"]
    if beat["kind"] == "demo":
        entry["title"] = beat["title"]
    else:
        entry["text"] = beat["text"]
    return entry


def write_script(beats: list[dict], out_dir: Path) -> None:
    script = {"beats": [script_beat(beat) for beat in beats]}
    (out_dir / "script.json").write_text(json.dumps(script, indent=2) + "\n")


def manifest_beat(beat: dict, demos: dict) -> dict:
    entry = {"id": beat["id"], "kind": beat["kind"]}
    if "demo_id" in beat:
        entry["demo_id"] = beat["demo_id"]
    if beat["kind"] == "demo":
        demo = demos[beat["demo_id"]]
        entry["title"] = demo["title"]
        for key in METADATA_KEYS:
            if key in demo:
                entry[key] = demo[key]
        entry["source_range"] = {
            "start": demo["start"], "start_seconds": demo["start_seconds"],
            "end": demo["end"], "end_seconds": demo["end_seconds"],
        }
        entry["artifacts"] = demo["artifacts"]
        entry["duration_seconds"] = demo["duration_seconds"]
    else:
        entry["text"] = beat["text"]
    entry["include_in"] = beat["include_in"]
    entry["mp4_offset_seconds"] = None  # filled by the composition stage
    return entry


def write_manifest(beats: list[dict], demos: dict, source_duration: float,
                   out_dir: Path) -> None:
    manifest = {
        "source": {"master": str(MASTER), "duration_seconds": source_duration},
        "pdf_follows_pptx": True,
        "outputs": {output: output_beats(beats, output) for output in OUTPUTS},
        "beats": [manifest_beat(beat, demos) for beat in beats],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main(argv: list[str]) -> int:
    global MASTER
    if len(argv) > 3:
        MASTER = Path(rel_path(Path(argv[3])))
    fixture_path = Path(argv[1]) if len(argv) > 1 else Path("fixtures/sprint-analysis.json")
    out_dir = Path(argv[2]) if len(argv) > 2 else Path("output")

    # A failed run must not leave a previous run's claim behind.
    for name in ("script.json", "manifest.json"):
        (out_dir / name).unlink(missing_ok=True)

    if not MASTER.exists():
        print(f"error: master recording not found: {MASTER}", file=sys.stderr)
        return 1
    source_duration = probe_duration(MASTER)
    fixture = json.loads(fixture_path.read_text())
    try:
        demos = load_demos(fixture, source_duration)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    beats = build_beats(demos)
    print(f"plan: {fixture_path} -> {len(demos)} demos, {len(beats)} beats")
    out_dir.mkdir(parents=True, exist_ok=True)
    extract_and_measure(demos, out_dir)
    write_script(beats, out_dir)
    write_manifest(beats, {demo["id"]: demo for demo in demos}, source_duration, out_dir)
    for output in OUTPUTS:
        print(f"  {output}: {' -> '.join(output_beats(beats, output))}")
    print(f"wrote {out_dir / 'script.json'} and {out_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
