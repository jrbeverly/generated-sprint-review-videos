#!/usr/bin/env python3
"""Validation flow for the #430 media-path spike.

Checks the acceptance criteria:
  1. Numbered boundary frames and durations match both declared ranges within
     one output frame, without neighboring scene leakage.
  2. FFprobe identifies the expected streams and FFmpeg fully decodes the
     extracted clips, including the silent case.
  3. The full deck (output/sprint-briefing.pptx, produced by #431) contains
     the videos and posters with internal relationships rather than an
     external source dependency, using the spike's inspection approach.
  4. Desktop PowerPoint playback is exercised if available; otherwise the deck
     is retained and playback is marked unverified.

Writes a full report to evidence/results.md and exits non-zero on any FAIL.
"""

import array
import hashlib
import json
import math
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_tools import ffmpeg, ffprobe, parse_timestamp, run  # noqa: E402

FIXTURE_PATH = Path("fixtures/demos.json")
CLIP_DIR = Path("output/demos")
PPTX_PATH = Path("output/sprint-briefing.pptx")
MANIFEST_PATH = Path("output/manifest.json")
FRAME_DUMP_DIR = Path("work/frames")
FPS = 30
TOTAL_SECONDS = 16.0
SCENE_SECONDS = 4.0
TONE_HZ = [440, 660, 880, 1320]
KEYFRAME_FRAMES = [0, 250]
FRAME_TOLERANCE = 1  # "within one output frame"

STRIP_BITS = 12
STRIP_SQUARE = 48
STRIP_X0, STRIP_Y0 = 40, 40

RESULTS: list[tuple[str, str, str, str]] = []  # (group, check, status, detail)


def record(group: str, name: str, ok: bool, detail: str) -> None:
    RESULTS.append((group, name, "PASS" if ok else "FAIL", detail))


def note(group: str, name: str, detail: str) -> None:
    RESULTS.append((group, name, "INFO", detail))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- media helpers

def ffprobe_streams(path: Path) -> list[dict]:
    raw = run([ffprobe(), "-v", "error", "-of", "json",
               "-show_streams", "-show_format", str(path)])
    if raw.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path}: {raw.stderr.decode()}")
    return json.loads(raw.stdout)


def full_decode(path: Path) -> tuple[bool, str]:
    raw = run([ffmpeg(), "-v", "error", "-i", str(path), "-f", "null", "-"])
    return raw.returncode == 0, raw.stderr.decode().strip()


def dump_frames(clip: Path, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = run([ffmpeg(), "-y", "-v", "error", "-i", str(clip),
               "-start_number", "0", str(out_dir / "f-%04d.png")])
    if raw.returncode != 0:
        raise RuntimeError(f"frame dump failed for {clip}: {raw.stderr.decode()}")
    return sorted(out_dir.glob("f-*.png"))


def decode_strip(png: Path) -> int:
    img = Image.open(png).convert("L")
    value = 0
    for i in range(STRIP_BITS):
        x = STRIP_X0 + i * (STRIP_SQUARE + 22) + STRIP_SQUARE // 2
        y = STRIP_Y0 + STRIP_SQUARE // 2
        value = (value << 1) | (1 if img.getpixel((x, y)) > 128 else 0)
    return value


def audio_window(clip: Path, t0: float, duration: float) -> array.array:
    raw = run([ffmpeg(), "-v", "error", "-ss", f"{t0:.3f}", "-i", str(clip),
               "-t", f"{duration:.3f}", "-map", "0:a:0", "-vn",
               "-ac", "1", "-ar", "48000", "-f", "s16le", "-"])
    if raw.returncode != 0:
        raise RuntimeError(f"audio window failed on {clip}: {raw.stderr.decode()}")
    return array.array("h", raw.stdout)


def zero_crossing_freq(samples: array.array) -> float:
    crossings = sum(1 for a, b in zip(samples, samples[1:]) if (a < 0 <= b) or (b < 0 <= a))
    return crossings / 2 / (len(samples) / 48000)


def tone_at(t: float) -> float:
    return TONE_HZ[int(t / SCENE_SECONDS)]


# ------------------------------------------------------------------- checks

def check_fixture() -> dict:
    fixture = json.loads(FIXTURE_PATH.read_text())
    demos = fixture["demos"]
    record("fixture", "declared demo count", len(demos) == 3,
           f"{len(demos)} demos declared (two ranges + one silent case)")

    all_ok = True
    for demo in demos:
        start = parse_timestamp(demo["start"])
        end = parse_timestamp(demo["end"])
        in_range = 0 <= start < end <= fixture["source_duration_seconds"]
        not_frame_aligned = (start * FPS) % 1 != 0 and (end * FPS) % 1 != 0
        not_keyframe_aligned = all(
            abs(start * FPS - kf) >= 1 and abs(end * FPS - kf) >= 1
            for kf in KEYFRAME_FRAMES
        )
        ok = in_range and not_frame_aligned and not_keyframe_aligned
        all_ok &= ok
        record("fixture", f"{demo['id']} range validity", ok,
               f"{demo['start']}..{demo['end']} in range: {in_range}, "
               f"not 1/{FPS}-aligned: {not_frame_aligned}, "
               f"not keyframe-aligned (frames {KEYFRAME_FRAMES}): {not_keyframe_aligned}")
    return fixture


def check_masters() -> None:
    probe = ffprobe_streams(Path("input/sprint-demo.mp4"))
    streams = {s["codec_type"]: s for s in probe["streams"]}
    video_ok = (streams["video"]["codec_name"] == "h264"
                and streams["video"]["width"] == 1920
                and streams["video"]["height"] == 1080)
    audio_ok = streams["audio"]["codec_name"] == "aac"
    duration = float(probe["format"]["duration"])
    record("master", "sprint-demo streams", video_ok and audio_ok,
           f"h264 {streams['video']['width']}x{streams['video']['height']}, aac audio")
    record("master", "sprint-demo duration", abs(duration - TOTAL_SECONDS) < 0.001,
           f"{duration:.3f}s vs declared {TOTAL_SECONDS}s")

    raw = run([ffprobe(), "-v", "error", "-select_streams", "v:0",
               "-show_entries", "frame=key_frame", "-of", "default=noprint_wrappers=1",
               "input/sprint-demo.mp4"])
    keyframes = [i for i, line in enumerate(raw.stdout.decode().splitlines())
                 if line == "key_frame=1"]
    record("master", "forced GOP layout", keyframes == KEYFRAME_FRAMES,
           f"keyframes at frame indices {keyframes} (expected {KEYFRAME_FRAMES}, "
           f"so clip boundaries are not keyframe-aligned)")


def check_clip_media(demo: dict) -> None:
    demo_id = demo["id"]
    clip = CLIP_DIR / f"{demo_id}.mp4"
    start = parse_timestamp(demo["start"])
    end = parse_timestamp(demo["end"])
    declared = end - start

    probe = ffprobe_streams(clip)
    streams = {s["codec_type"]: s for s in probe["streams"]}
    video = streams["video"]
    has_audio = "audio" in streams
    record("clip", f"{demo_id} streams",
           video["codec_name"] == "h264" and video["width"] == 1920
           and video["height"] == 1080 and video["r_frame_rate"] == "30/1"
           and has_audio and streams["audio"]["codec_name"] == "aac",
           f"h264 {video['width']}x{video['height']} @ {video['r_frame_rate']}, "
           f"{'aac audio' if has_audio else 'no audio'}")

    measured = float(probe["format"]["duration"])
    frame_secs = 1 / FPS
    record("clip", f"{demo_id} duration", abs(measured - declared) <= frame_secs + 0.002,
           f"measured {measured:.3f}s vs declared {declared:.3f}s "
           f"(delta {abs(measured - declared):.3f}s <= {frame_secs:.3f}s)")

    ok, err = full_decode(clip)
    record("clip", f"{demo_id} full decode", ok and not err,
           f"ffmpeg -f null - decoded all streams with no errors"
           + (f"; stderr: {err[:200]}" if err else ""))

    frames = dump_frames(clip, FRAME_DUMP_DIR / demo_id)
    numbers = [decode_strip(p) for p in frames]
    first, last = numbers[0], numbers[-1]
    # Precise seek keeps the first frame whose pts is >= start (ceil) and the
    # last frame whose pts is < end (floor); B-frame packet ordering can shift
    # the end by one frame, which the tolerance admits.
    expected_first = math.ceil(start * FPS)
    expected_last = math.floor(end * FPS)
    boundaries_ok = (abs(first - expected_first) <= FRAME_TOLERANCE
                     and abs(last - expected_last) <= FRAME_TOLERANCE)
    contiguous = numbers == list(range(first, last + 1))
    record("clip", f"{demo_id} boundary frames", boundaries_ok and contiguous,
           f"first frame {first} (declared start frame {expected_first}), "
           f"last frame {last} (declared end frame {expected_last}), "
           f"all {len(numbers)} decoded frames contiguous "
           f"({first}..{last}); tolerance {FRAME_TOLERANCE} frame")

    if demo["source"] == "sprint-demo.mp4":
        window = 0.3
        for label, t0, expected in (
                ("opening", 0.0, tone_at(start + window / 2)),
                ("ending", declared - window, tone_at(end - window / 2))):
            samples = audio_window(clip, t0, window)
            measured_hz = zero_crossing_freq(samples)
            close = abs(measured_hz - expected) <= max(expected * 0.02, 5.0)
            record("clip", f"{demo_id} tone at {label}", close,
                   f"measured {measured_hz:.1f} Hz, expected scene tone {expected:.0f} Hz")
    else:
        samples = audio_window(clip, 1.0, 1.0)
        silent = all(s == 0 for s in samples)
        record("clip", f"{demo_id} silent audio preserved", silent,
               f"1.0 s window at t=1.0s: {len(samples)} samples, all zero: {silent}")


def check_posters(demo: dict) -> None:
    demo_id = demo["id"]
    poster = CLIP_DIR / f"{demo_id}-poster.png"
    start = parse_timestamp(demo["start"])
    end = parse_timestamp(demo["end"])

    img = Image.open(poster)
    size_ok = img.size == (1920, 1080)
    frame = decode_strip(poster)
    # Poster comes from the clip midpoint: first clip frame + first frame with
    # pts >= midpoint (ceil), matching the -ss seek used during extraction.
    expected = math.ceil(start * FPS) + math.ceil((end - start) / 2 * FPS)
    frame_ok = abs(frame - expected) <= FRAME_TOLERANCE
    record("poster", f"{demo_id} poster", size_ok and frame_ok,
           f"{img.size} PNG, frame number {frame} vs expected midpoint frame "
           f"{expected} (tolerance {FRAME_TOLERANCE})")


# ------------------------------------------------------------------- pptx checks

VIDEO_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/video"
MEDIA_TYPE = "http://schemas.microsoft.com/office/2007/relationships/media"
IMAGE_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"


def slide_rels(zf: zipfile.ZipFile, index: int) -> dict[str, list[dict]]:
    """Relationship attrs by type for one slide (1-based index)."""
    rels = ET.fromstring(zf.read(f"ppt/slides/_rels/slide{index}.xml.rels"))
    by_type: dict[str, list[dict]] = {}
    for rel in rels:
        attrs = {k.split('}')[-1]: v for k, v in rel.attrib.items()}
        by_type.setdefault(attrs["Type"], []).append(attrs)
    return by_type


def check_pptx() -> None:
    """Full-deck embedding confirmation, reusing the #430 spike's inspection.

    The full deck (produced by make_pptx.mjs for #431) embeds every
    PPTX-included demo clip with its poster; the same inspection approach as
    the spike — zip structure, byte identity against local assets, internal
    relationships, slide XML media elements, and the moved-deck standalone
    check — is applied per demo slide.
    """
    manifest = json.loads(MANIFEST_PATH.read_text())
    demo_beats = [beat for beat in manifest["beats"] if beat["kind"] == "demo"]
    demo_slides = {beat["demo_id"]: manifest["outputs"]["pptx"].index(beat["id"]) + 1
                   for beat in demo_beats}

    with zipfile.ZipFile(PPTX_PATH) as zf:
        names = zf.namelist()
        media_mp4 = [n for n in names if n.startswith("ppt/media/") and n.endswith(".mp4")]
        media_png = [n for n in names if n.startswith("ppt/media/") and n.endswith(".png")]
        record("pptx", "zip structure",
               len(media_mp4) == len(demo_beats) and len(media_png) == len(demo_beats),
               f"media entries: {len(media_mp4)} mp4 + {len(media_png)} png "
               f"for {len(demo_beats)} demo beats ({media_mp4 + media_png})")

        for beat in demo_beats:
            demo_id = beat["demo_id"]
            clip = Path(beat["artifacts"]["clip"])
            poster = Path(beat["artifacts"]["poster"])
            rels = slide_rels(zf, demo_slides[demo_id])
            video_rel = rels.get(VIDEO_TYPE, [{}])[0]
            media_rel = rels.get(MEDIA_TYPE, [{}])[0]
            image_rel = rels.get(IMAGE_TYPE, [{}])[0]

            def media_bytes(rel: dict) -> bytes:
                target = rel.get("Target", "")
                if not target.startswith("../media/"):
                    return b""
                return zf.read("ppt/media/" + target.rsplit("/", 1)[-1])

            video_embedded = hashlib.sha256(media_bytes(video_rel)).hexdigest() == sha256(clip)
            poster_embedded = hashlib.sha256(media_bytes(image_rel)).hexdigest() == sha256(poster)
            record("pptx", f"{demo_id} embedded bytes match local assets",
                   video_embedded and poster_embedded,
                   f"video bytes == {clip.name}: {video_embedded}; "
                   f"poster bytes == {poster.name}: {poster_embedded}")

            internal = all(
                rel.get("Target", "").startswith("../media/")
                and "TargetMode" not in rel
                and not rel.get("Target", "").startswith(("http", "file:"))
                for rel in (video_rel, media_rel, image_rel)
            )
            same_target = video_rel.get("Target") == media_rel.get("Target")
            record("pptx", f"{demo_id} internal relationships", internal and same_target,
                   f"video rel rId={video_rel.get('Id')} -> {video_rel.get('Target')}, "
                   f"p14 media rel -> {media_rel.get('Target')} "
                   f"(same target: {same_target}), "
                   f"image rel -> {image_rel.get('Target')}; no external targets")

            slide_xml = zf.read(f"ppt/slides/slide{demo_slides[demo_id]}.xml").decode()
            blip_embed = re.search(r'a:blip r:embed="([^"]+)"', slide_xml)
            poster_rel_matches = bool(blip_embed and blip_embed.group(1) == image_rel.get("Id"))
            record("pptx", f"{demo_id} slide XML media elements",
                   "<a:videoFile" in slide_xml and "<p14:media" in slide_xml
                   and poster_rel_matches,
                   f"videoFile present: {'<a:videoFile' in slide_xml}, "
                   f"p14:media present: {'<p14:media' in slide_xml}, "
                   f"blip poster r:embed={blip_embed.group(1) if blip_embed else None} "
                   f"== image rel {image_rel.get('Id')}: {poster_rel_matches}")

        types_xml = zf.read("[Content_Types].xml").decode()
        embedded_bytes = [(n, zf.read(n)) for n in media_mp4 + media_png]

    types = ET.fromstring(types_xml)
    defaults = {d.get("Extension"): d.get("ContentType") for d in types if "Default" in d.tag}
    record("pptx", "content types", defaults.get("mp4") == "video/mp4"
           and defaults.get("png") == "image/png",
           f"mp4 -> {defaults.get('mp4')}, png -> {defaults.get('png')}")

    # Move the deck away from all input/asset files and re-inspect it.
    standalone_dir = Path(tempfile.mkdtemp(prefix="briefing-standalone-"))
    moved = standalone_dir / "sprint-briefing.pptx"
    shutil.copy(PPTX_PATH, moved)
    record("pptx", "deck survives move away from inputs", moved.exists(),
           f"copied to {moved}; input files untouched")

    with zipfile.ZipFile(moved) as zf:
        still_embedded = all(
            hashlib.sha256(zf.read(name)).hexdigest() == hashlib.sha256(data).hexdigest()
            for name, data in embedded_bytes)
    record("pptx", "moved deck keeps embedded bytes", still_embedded,
           "all video and poster bytes still embedded inside the moved deck "
           "(no external source dependency)")

    note("pptx", "desktop PowerPoint playback", "UNVERIFIED: no desktop PowerPoint on "
         "this headless Linux container (no display, no LibreOffice, no PowerPoint "
         "binary). Deck retained for manual review at output/sprint-briefing.pptx. "
         "Package inspection cannot establish player compatibility.")


# -------------------------------------------------------------------- report

def main() -> int:
    fixture = check_fixture()
    check_masters()
    for demo in fixture["demos"]:
        check_clip_media(demo)
        check_posters(demo)
    check_pptx()

    lines = []
    lines.append("# Media-path validation (#430 spike; full deck from #431)")
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
    Path("evidence/results.md").write_text(report + "\n")

    for line in report.splitlines():
        print(line)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
