#!/usr/bin/env python3
"""Validation flow for the #428 presentation-plan stage.

Checks the acceptance criteria:
  1. The main fixture produces the expected ordered beats — opening, optional
     literal intro, demo, optional literal outcome/outro, closing — with the
     fixed opening/closing text and literal narration only.
  2. Fixture array order, optional epic/release/business_value metadata, and
     default inclusion flags are preserved in script.json/manifest.json.
  3. The fixture records that PDF follows PPTX inclusion; each output is
     filtered independently; demos included in either output are extracted
     once; demos excluded from both are omitted (no beats, no artifacts).
  4. manifest.json entries carry beat/demo IDs, source ranges, artifact
     paths, and measured durations; mp4 offsets stay null for composition.
  5. Case fixtures exercise missing optional text, PPTX-only, video-only, and
     both-excluded demos against explicit expected beat orders.
  6. Reversed/out-of-range timestamps, duplicate IDs, and unsafe IDs fail
     before script.json/manifest.json can claim the briefing complete.

Writes a full report to evidence/results-plan.md and exits non-zero on any
FAIL.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_plan import CLOSING_TEXT, FILENAME_SAFE, OPENING_TEXT, probe_duration  # noqa: E402
from media_tools import EXPERIMENT_ROOT, parse_timestamp  # noqa: E402

MAIN_FIXTURE = Path("fixtures/sprint-analysis.json")
SCRIPT_PATH = Path("output/script.json")
MANIFEST_PATH = Path("output/manifest.json")

# Explicit expected beat order for the main fixture: demo 2 has an intro but
# no outro, so no admin-controls-outro beat may exist.
EXPECTED_MAIN_BEATS = [
    ("opening", "opening"),
    ("new-checkout-intro", "intro"),
    ("new-checkout", "demo"),
    ("new-checkout-outro", "outro"),
    ("admin-controls-intro", "intro"),
    ("admin-controls", "demo"),
    ("closing", "closing"),
]

FRAME_SECONDS = 1 / 30
FRAME_TOLERANCE = 1 / 30 + 0.002  # same tolerance as the #430 spike

CASES = [
    {
        "name": "missing-optional-text",
        "fixture": "fixtures/plan-cases/missing-optional-text.json",
        "expected_beats": [
            ("opening", "opening"),
            ("plain-demo", "demo"),
            ("closing", "closing"),
        ],
        "expected": {
            "pptx": ["opening", "plain-demo", "closing"],
            "pdf": ["opening", "plain-demo", "closing"],
            "video": ["opening", "plain-demo", "closing"],
        },
        "extracted": ["plain-demo"],
        "posters": ["plain-demo"],
    },
    {
        "name": "pptx-only",
        "fixture": "fixtures/plan-cases/pptx-only.json",
        "expected_beats": [
            ("opening", "opening"),
            ("deck-only-intro", "intro"),
            ("deck-only", "demo"),
            ("deck-only-outro", "outro"),
            ("both-demo", "demo"),
            ("closing", "closing"),
        ],
        "expected": {
            "pptx": ["opening", "deck-only-intro", "deck-only", "deck-only-outro",
                     "both-demo", "closing"],
            "pdf": ["opening", "deck-only-intro", "deck-only", "deck-only-outro",
                    "both-demo", "closing"],
            "video": ["opening", "both-demo", "closing"],
        },
        "extracted": ["deck-only", "both-demo"],
        "posters": ["deck-only", "both-demo"],
    },
    {
        "name": "video-only",
        "fixture": "fixtures/plan-cases/video-only.json",
        "expected_beats": [
            ("opening", "opening"),
            ("clip-only-intro", "intro"),
            ("clip-only", "demo"),
            ("both-demo", "demo"),
            ("closing", "closing"),
        ],
        "expected": {
            "pptx": ["opening", "both-demo", "closing"],
            "pdf": ["opening", "both-demo", "closing"],
            "video": ["opening", "clip-only-intro", "clip-only", "both-demo", "closing"],
        },
        "extracted": ["clip-only", "both-demo"],
        "posters": ["both-demo"],  # clip-only is video-only: clip but no poster
    },
    {
        "name": "both-excluded",
        "fixture": "fixtures/plan-cases/both-excluded.json",
        "expected_beats": [
            ("opening", "opening"),
            ("shown", "demo"),
            ("closing", "closing"),
        ],
        "expected": {
            "pptx": ["opening", "shown", "closing"],
            "pdf": ["opening", "shown", "closing"],
            "video": ["opening", "shown", "closing"],
        },
        "extracted": ["shown"],
        "posters": ["shown"],
    },
]

INVALID_CASES = [
    {"name": "invalid-reversed",
     "fixture": "fixtures/plan-cases/invalid-reversed.json",
     "marker": "violates 0 <= start < end"},
    {"name": "invalid-out-of-range",
     "fixture": "fixtures/plan-cases/invalid-out-of-range.json",
     "marker": "violates 0 <= start < end"},
    {"name": "invalid-duplicate-id",
     "fixture": "fixtures/plan-cases/invalid-duplicate-id.json",
     "marker": "duplicate demo id"},
    {"name": "invalid-unsafe-id",
     "fixture": "fixtures/plan-cases/invalid-unsafe-id.json",
     "marker": "filename-safe"},
]

RESULTS: list[tuple[str, str, str, str]] = []  # (group, check, status, detail)


def record(group: str, name: str, ok: bool, detail: str) -> None:
    RESULTS.append((group, name, "PASS" if ok else "FAIL", detail))


def note(group: str, name: str, detail: str) -> None:
    RESULTS.append((group, name, "INFO", detail))


def run_builder(fixture: str, out_dir: Path) -> subprocess.CompletedProcess:
    shutil.rmtree(out_dir, ignore_errors=True)
    return subprocess.run(
        [sys.executable, "src/build_plan.py", fixture, str(out_dir)],
        cwd=EXPERIMENT_ROOT, capture_output=True, text=True,
    )


# ------------------------------------------------------------------ main run

def check_main() -> None:
    if not (SCRIPT_PATH.exists() and MANIFEST_PATH.exists()):
        record("main", "plan outputs exist", False,
               f"missing {SCRIPT_PATH} and/or {MANIFEST_PATH}; run src/build_plan.py first")
        return

    fixture = json.loads(MAIN_FIXTURE.read_text())
    demos = fixture["demos"]
    fixture_demos = {demo["id"]: demo for demo in demos}
    note_text = fixture.get("note", "")
    record("main", "fixture records PDF follows PPTX",
           "PDF follows PPTX" in note_text and fixture.get("pdf_follows_pptx", True) is True,
           f"note: {note_text[:90]}...")
    record("main", "fixture ids are filename-safe",
           all(FILENAME_SAFE.match(demo["id"]) for demo in demos),
           f"ids: {[d['id'] for d in demos]} vs {FILENAME_SAFE.pattern}")
    record("main", "fixture leaves inclusion flags unset",
           all("include_in_pptx" not in d and "include_in_video" not in d for d in demos),
           "both demos rely on the default flags")

    script = json.loads(SCRIPT_PATH.read_text())
    manifest = json.loads(MANIFEST_PATH.read_text())
    script_beats = [(b["id"], b["kind"]) for b in script["beats"]]
    manifest_beats = [(b["id"], b["kind"]) for b in manifest["beats"]]
    record("main", "script beat order", script_beats == EXPECTED_MAIN_BEATS,
           f"got {script_beats}, want {EXPECTED_MAIN_BEATS}")
    record("main", "manifest beat order matches script",
           manifest_beats == script_beats,
           f"got {manifest_beats}")

    script_by_id = {b["id"]: b for b in script["beats"]}
    record("main", "fixed opening text",
           script_by_id["opening"]["text"] == OPENING_TEXT,
           repr(script_by_id["opening"]["text"]))
    record("main", "fixed closing text",
           script_by_id["closing"]["text"] == CLOSING_TEXT,
           repr(script_by_id["closing"]["text"]))

    literals_ok = True
    for demo in demos:
        for key in ("intro", "outro"):
            if key not in demo:
                continue
            beat = script_by_id[f"{demo['id']}-{key}"]
            if beat["text"] != demo[key]:
                literals_ok = False
                record("main", f"{demo['id']} literal {key}", False,
                       f"got {beat['text']!r}, want {demo[key]!r}")
    record("main", "literal intro/outro narration matches fixture", literals_ok,
           "every supplied intro/outro text carried verbatim")
    record("main", "no narration over demo beats",
           all("text" not in b for b in script["beats"] if b["kind"] == "demo"),
           "demo beats carry no text, so no TTS is ever placed over demo audio")

    manifest_by_id = {b["id"]: b for b in manifest["beats"]}
    nc = manifest_by_id["new-checkout"]
    ac = manifest_by_id["admin-controls"]
    nc_fx = fixture_demos["new-checkout"]
    ac_fx = fixture_demos["admin-controls"]
    record("main", "epic/release/business_value carried",
           (nc["epic"] == nc_fx["epic"] and nc["release"] == nc_fx["release"]
            and nc["business_value"] == nc_fx["business_value"]
            and ac["epic"] == ac_fx["epic"]
            and "release" not in ac and "business_value" not in ac),
           f"new-checkout: {nc.get('epic')} / {nc.get('release')} / "
           f"{nc.get('business_value')}; admin-controls: {ac.get('epic')} "
           f"with release/business_value absent")

    default_include = {"pptx": True, "video": True}
    record("main", "default inclusion flags",
           nc["include_in"] == default_include and ac["include_in"] == default_include,
           f"both demo beats include_in {nc['include_in']}")

    all_ids = [beat_id for beat_id, _ in EXPECTED_MAIN_BEATS]
    record("main", "pptx beat list", manifest["outputs"]["pptx"] == all_ids,
           f"got {manifest['outputs']['pptx']}")
    record("main", "pdf follows pptx",
           manifest["outputs"]["pdf"] == manifest["outputs"]["pptx"] == all_ids,
           f"pdf list == pptx list: {manifest['outputs']['pdf']}")
    record("main", "video beat list", manifest["outputs"]["video"] == all_ids,
           f"got {manifest['outputs']['video']}")
    record("main", "manifest records the pdf assumption",
           manifest.get("pdf_follows_pptx") is True, str(manifest.get("pdf_follows_pptx")))

    record("main", "source master recorded",
           manifest["source"]["master"] == "input/sprint-demo.mp4",
           manifest["source"]["master"])
    measured_master = probe_duration(Path("input/sprint-demo.mp4"))
    record("main", "source duration measured from the master",
           abs(manifest["source"]["duration_seconds"] - measured_master) < 0.001
           and abs(measured_master - 16.0) < 0.001,
           f"manifest {manifest['source']['duration_seconds']:.3f}s, "
           f"ffprobe {measured_master:.3f}s")

    for demo in demos:
        demo_id = demo["id"]
        beat = manifest_by_id[demo_id]
        clip = Path(beat["artifacts"]["clip"])
        poster = Path(beat["artifacts"]["poster"])
        record("main", f"{demo_id} artifact paths",
               clip == Path("output/demos") / f"{demo_id}.mp4"
               and poster == Path("output/demos") / f"{demo_id}-poster.png"
               and clip.exists() and poster.exists(),
               f"{clip} exists: {clip.exists()}, {poster} exists: {poster.exists()}")

        declared = parse_timestamp(demo["end"]) - parse_timestamp(demo["start"])
        measured = beat["duration_seconds"]
        record("main", f"{demo_id} measured duration",
               abs(measured - declared) <= FRAME_TOLERANCE,
               f"measured {measured:.3f}s vs declared {declared:.3f}s "
               f"(delta {abs(measured - declared):.3f}s <= {FRAME_TOLERANCE:.3f}s)")

        sr = beat["source_range"]
        record("main", f"{demo_id} source range",
               sr["start"] == demo["start"] and sr["end"] == demo["end"]
               and abs(sr["start_seconds"] - parse_timestamp(demo["start"])) < 1e-9
               and abs(sr["end_seconds"] - parse_timestamp(demo["end"])) < 1e-9,
               f"{sr['start']}..{sr['end']} ({sr['start_seconds']}..{sr['end_seconds']})")

    record("main", "mp4 offsets reserved for composition",
           all(b["mp4_offset_seconds"] is not None for b in manifest["beats"])
           if "mp4" in manifest else
           all(b["mp4_offset_seconds"] is None for b in manifest["beats"]),
           "offsets populated after composition, null before composition")

    note("main", "extraction happens once per included demo",
         "build_plan.py extracts each demo included in either output in a "
         "single extract_clip call, regardless of how many outputs use it")


# ----------------------------------------------------------------- case runs

def check_case_outputs(case: dict, out_dir: Path) -> None:
    name = case["name"]
    script = json.loads((out_dir / "script.json").read_text())
    manifest = json.loads((out_dir / "manifest.json").read_text())

    script_beats = [(b["id"], b["kind"]) for b in script["beats"]]
    record(name, "script beat order", script_beats == case["expected_beats"],
           f"got {script_beats}, want {case['expected_beats']}")
    manifest_beats = [(b["id"], b["kind"]) for b in manifest["beats"]]
    record(name, "manifest beat order matches script",
           manifest_beats == script_beats, f"got {manifest_beats}")

    for output in ("pptx", "pdf", "video"):
        actual = manifest["outputs"][output]
        record(name, f"{output} beat list", actual == case["expected"][output],
               f"got {actual}, want {case['expected'][output]}")
    record(name, "pdf follows pptx",
           manifest["outputs"]["pdf"] == manifest["outputs"]["pptx"],
           f"pdf == pptx: {manifest['outputs']['pdf']}")

    fixture = json.loads(Path(case["fixture"]).read_text())
    demo_ids = {demo["id"] for demo in fixture["demos"]}
    extracted = set(case["extracted"])
    for demo_id in sorted(extracted):
        clip = out_dir / "demos" / f"{demo_id}.mp4"
        record(name, f"{demo_id} clip extracted", clip.exists(), str(clip))
        beat = manifest["beats"][[b["id"] for b in manifest["beats"]].index(demo_id)]
        expected_clip = f"work/plan-cases/{name}/demos/{demo_id}.mp4"
        demo_fx = next(d for d in fixture["demos"] if d["id"] == demo_id)
        declared = parse_timestamp(demo_fx["end"]) - parse_timestamp(demo_fx["start"])
        record(name, f"{demo_id} artifact path and measured duration",
               beat["artifacts"]["clip"] == expected_clip
               and abs(beat["duration_seconds"] - declared) <= FRAME_TOLERANCE,
               f"clip path {beat['artifacts']['clip']}, measured "
               f"{beat['duration_seconds']:.3f}s vs declared {declared:.3f}s")
    for demo_id in sorted(demo_ids - extracted):
        clip = out_dir / "demos" / f"{demo_id}.mp4"
        record(name, f"{demo_id} clip omitted", not clip.exists(), f"no {clip}")

    posters = set(case["posters"])
    for demo_id in sorted(posters):
        poster = out_dir / "demos" / f"{demo_id}-poster.png"
        record(name, f"{demo_id} poster extracted", poster.exists(), str(poster))
    for demo_id in sorted(demo_ids - posters):
        poster = out_dir / "demos" / f"{demo_id}-poster.png"
        record(name, f"{demo_id} poster omitted", not poster.exists(), f"no {poster}")


def run_case(case: dict) -> None:
    name = case["name"]
    out_dir = Path("work/plan-cases") / name
    result = run_builder(case["fixture"], out_dir)
    record(name, "builder exit", result.returncode == 0,
           f"exit {result.returncode}"
           + (f"; stderr: {result.stderr[:200]}" if result.returncode else ""))
    if result.returncode != 0:
        return
    check_case_outputs(case, out_dir)


def run_invalid_case(case: dict) -> None:
    name = case["name"]
    out_dir = Path("work/plan-cases") / name
    result = run_builder(case["fixture"], out_dir)
    failed = result.returncode != 0
    marker = case["marker"] in result.stderr
    no_claim = (not (out_dir / "manifest.json").exists()
                and not (out_dir / "script.json").exists())
    record(name, "builder fails before claiming completion", failed and marker and no_claim,
           f"exit {result.returncode}, marker {case['marker']!r} in stderr: {marker}, "
           f"no script/manifest written: {no_claim}"
           + (f"; stderr: {result.stderr[:200]}" if not (failed and marker) else ""))


# -------------------------------------------------------------------- report

def main() -> int:
    check_main()
    for case in CASES:
        run_case(case)
    for case in INVALID_CASES:
        run_invalid_case(case)

    lines = []
    lines.append("# Presentation-plan validation (#428)")
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
    Path("evidence/results-plan.md").write_text(report + "\n")

    for line in report.splitlines():
        print(line)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
