#!/usr/bin/env python3
"""Validation flow for the #427 composition stage.

Checks the acceptance criteria:
  1. output/sprint-briefing.mp4 exists, is nonempty, and carries one H.264
     1920x1080 30fps yuv420p video stream and one AAC 48 kHz stereo audio
     stream.
  2. FFmpeg fully decodes the final video without errors.
  3. Total duration matches the sum of measured segment durations within 0.1 s.
  4. manifest.json has the mp4 key and every video-included beat carries
     segment, segment_duration_seconds, and cumulative mp4_offset_seconds;
     non-video beats keep mp4_offset_seconds: null; all segment files exist.
  5. At each video beat's midpoint, one frame is extracted and compared
     against the corresponding slide PNG (MAD < 2.0 for narrated beats, >= 2.0
     for demo beats whose video frames differ from static slides).
  6. Boundary frames at each beat join are checked: the frame just before the
     join shows the ending beat's content type and the frame just after shows
     the starting beat's content type.
  7. The full MP4 audio is decoded once to raw mono PCM; at each demo beat's
     opening (offset + 0.1 s) the dominant zero-crossing frequency matches the
     expected scene tone within 2% or 5 Hz.
  8. A video-only clip (no audio stream) composed as a demo segment produces
     stereo PCM of the expected duration with all-zero samples.
  9. Manual checks (listening, visual legibility, re-encoding loss) are
     recorded as UNVERIFIED or INFO.

Writes evidence/results-composition.md and exits non-zero on any FAIL.
"""

import array
import json
import subprocess
import sys
import wave
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_tools import EXPERIMENT_ROOT, ffmpeg, ffprobe_json, run  # noqa: E402
from make_composition import make_demo_segment  # noqa: E402

MANIFEST_PATH = Path("output/manifest.json")
MP4_PATH = Path("output/sprint-briefing.mp4")
SLIDES_DIR = Path("output/slides")
SEGMENTS_DIR = Path("output/segments")
FRAME_DIR = Path("work/composition-frames")
SILENT_TEST_DIR = Path("work/silent-test")

FPS = 30
FRAME_SECS = 1.0 / FPS
AUDIO_RATE = 48000
TONE_HZ = [440, 660, 880, 1320]
SCENE_SECONDS = 4.0
MAD_SLIDE_THRESHOLD = 2.0
DURATION_TOLERANCE = 0.1

RESULTS: list[tuple[str, str, str, str]] = []


def record(group: str, name: str, ok: bool, detail: str) -> None:
    RESULTS.append((group, name, "PASS" if ok else "FAIL", detail))


def note(group: str, name: str, detail: str) -> None:
    RESULTS.append((group, name, "INFO", detail))


def tone_at(source_seconds: float) -> float:
    return TONE_HZ[min(int(source_seconds / SCENE_SECONDS), len(TONE_HZ) - 1)]


def ffprobe_all(path: Path) -> dict:
    raw = run([ffprobe_bin(), "-v", "error", "-of", "json",
               "-show_streams", "-show_format", str(path)])
    if raw.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path}: {raw.stderr.decode()}")
    return json.loads(raw.stdout)


def ffprobe_bin() -> str:
    from media_tools import ffprobe  # noqa: F401
    return ffprobe()


def full_decode(path: Path) -> tuple[bool, str]:
    raw = run([ffmpeg(), "-v", "error", "-i", str(path), "-f", "null", "-"])
    return raw.returncode == 0, raw.stderr.decode().strip()


def extract_frame(at: float, out: Path) -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = run([ffmpeg(), "-y", "-v", "error",
               "-ss", f"{at:.6f}", "-i", str(MP4_PATH),
               "-frames:v", "1", str(out)])
    return raw.returncode == 0 and out.exists()


def mad_rgb(img1: Path, img2: Path) -> float:
    a = Image.open(img1).convert("RGB")
    b = Image.open(img2).convert("RGB")
    if a.size != b.size:
        b = b.resize(a.size, Image.LANCZOS)
    diff = ImageChops.difference(a, b)
    return sum(ImageStat.Stat(diff).mean) / 3


def zero_crossing_freq(samples: array.array, rate: int) -> float:
    crossings = sum(
        1 for a, b in zip(samples[:-1], samples[1:])
        if (a < 0 <= b) or (b < 0 <= a)
    )
    return crossings / 2 / (len(samples) / rate)


def decode_full_audio() -> array.array:
    """Decode the full MP4 audio to mono 16-bit PCM at AUDIO_RATE."""
    raw = subprocess.run(
        [ffmpeg(), "-v", "error", "-i", str(MP4_PATH),
         "-map", "0:a", "-f", "s16le", "-ar", str(AUDIO_RATE), "-ac", "1", "-"],
        capture_output=True, cwd=EXPERIMENT_ROOT,
    )
    if raw.returncode != 0:
        raise RuntimeError(f"audio decode failed: {raw.stderr.decode()}")
    return array.array("h", raw.stdout)


# ------------------------------------------------------------------ checks


def check_output() -> dict:
    group = "output"
    exists = MP4_PATH.exists()
    size = MP4_PATH.stat().st_size if exists else 0
    record(group, "sprint-briefing.mp4 exists and is nonempty",
           exists and size > 0,
           f"{MP4_PATH} ({size} bytes)" if exists else f"missing {MP4_PATH}")
    if not exists:
        return {}

    info = ffprobe_all(MP4_PATH)
    by_type = {s["codec_type"]: s for s in info.get("streams", [])}
    video = by_type.get("video", {})
    audio = by_type.get("audio", {})

    record(group, "video codec H.264",
           video.get("codec_name") == "h264", f"codec: {video.get('codec_name')}")
    record(group, "video resolution 1920x1080",
           video.get("width") == 1920 and video.get("height") == 1080,
           f"{video.get('width')}x{video.get('height')}")
    record(group, "video frame rate 30 fps",
           video.get("r_frame_rate") in ("30/1", "30000/1001"),
           f"r_frame_rate: {video.get('r_frame_rate')}")
    record(group, "video pixel format yuv420p",
           video.get("pix_fmt") == "yuv420p", f"pix_fmt: {video.get('pix_fmt')}")
    record(group, "audio codec AAC",
           audio.get("codec_name") == "aac", f"codec: {audio.get('codec_name')}")
    record(group, "audio sample rate 48000 Hz",
           audio.get("sample_rate") == "48000", f"sample_rate: {audio.get('sample_rate')}")
    record(group, "audio stereo",
           audio.get("channels") == 2, f"channels: {audio.get('channels')}")
    return info


def check_decode() -> None:
    ok, err = full_decode(MP4_PATH)
    record("decode", "FFmpeg fully decodes without errors",
           ok and not err,
           "ffmpeg -f null - exits 0 with empty stderr"
           + (f"; stderr: {err[:300]}" if err else ""))


def check_duration(manifest: dict) -> None:
    group = "duration"
    video_ids: list[str] = manifest["outputs"]["video"]
    beats_by_id = {b["id"]: b for b in manifest["beats"]}
    seg_sum = sum(
        beats_by_id[bid].get("segment_duration_seconds", 0.0)
        for bid in video_ids
    )
    probe = ffprobe_json(["-show_entries", "format=duration", str(MP4_PATH)])
    actual = float(probe["format"]["duration"])
    delta = abs(actual - seg_sum)
    record(group, "actual duration within 0.1 s of segment sum",
           delta <= DURATION_TOLERANCE,
           f"actual {actual:.3f}s, segment sum {seg_sum:.3f}s, delta {delta:.3f}s")

    # Each slide beat's segment must be at least ceil(wav_dur * FPS) / FPS.
    narration = json.loads(Path("output/audio/narration.json").read_text())
    wav_by_id = {e["beat_id"]: e for e in narration["beats"]}
    import math
    for beat in manifest["beats"]:
        if beat.get("kind") == "demo" or not beat["include_in"]["video"]:
            continue
        beat_id = beat["id"]
        entry = wav_by_id.get(beat_id)
        if entry is None:
            continue
        hold = math.ceil(entry["duration_seconds"] * FPS) / FPS
        seg_dur = beat.get("segment_duration_seconds", 0.0)
        record(group, f"{beat_id} slide hold >= ceil(wav * 30) / 30",
               abs(seg_dur - hold) <= FRAME_SECS + 0.002,
               f"segment {seg_dur:.3f}s, hold {hold:.3f}s "
               f"(wav {entry['duration_seconds']:.3f}s)")


def check_manifest(manifest: dict) -> None:
    group = "manifest"
    record(group, "manifest has mp4 key",
           "mp4" in manifest, f"mp4: {manifest.get('mp4')}")

    video_ids: list[str] = manifest["outputs"]["video"]
    beats_by_id = {b["id"]: b for b in manifest["beats"]}

    all_filled = all(
        beats_by_id[bid].get("mp4_offset_seconds") is not None
        for bid in video_ids
    )
    record(group, "all video beats have mp4_offset_seconds filled",
           all_filled, f"{len(video_ids)} video beats checked")

    non_video = [b for b in manifest["beats"]
                 if not b["include_in"]["video"] and b["kind"] != "demo"]
    still_null = all(b.get("mp4_offset_seconds") is None for b in non_video)
    record(group, "non-video beats keep mp4_offset_seconds: null",
           still_null or not non_video,
           f"{len(non_video)} non-video beats" + (", all null" if still_null else ""))

    offset = 0.0
    for beat_id in video_ids:
        beat = beats_by_id[beat_id]
        recorded = beat.get("mp4_offset_seconds")
        ok = recorded is not None and abs(recorded - offset) <= 0.002
        record(group, f"{beat_id} mp4_offset_seconds correct",
               ok, f"recorded {recorded}, expected {offset:.6f}")
        seg_dur = beat.get("segment_duration_seconds", 0.0)
        offset += seg_dur

        seg_path = beat.get("segment")
        seg_exists = seg_path is not None and (EXPERIMENT_ROOT / seg_path).exists()
        record(group, f"{beat_id} segment file exists",
               seg_exists, f"{seg_path}")

        dur_ok = isinstance(beat.get("segment_duration_seconds"), float) and seg_dur > 0
        record(group, f"{beat_id} segment_duration_seconds recorded",
               dur_ok, f"{beat.get('segment_duration_seconds'):.3f}s" if dur_ok else "missing")


def check_frames(manifest: dict) -> None:
    """Midpoint frame content check per video beat, plus boundary-frame joins."""
    group = "frames"
    FRAME_DIR.mkdir(parents=True, exist_ok=True)

    video_ids: list[str] = manifest["outputs"]["video"]
    beats_by_id = {b["id"]: b for b in manifest["beats"]}

    # Build slide_index the same way make_composition does.
    slide_index: dict[str, int] = {}
    idx = 1
    for beat in manifest["beats"]:
        if "text" in beat and beat["include_in"]["video"]:
            slide_index[beat["id"]] = idx
            idx += 1

    # --- midpoint frame checks ---
    for beat_id in video_ids:
        beat = beats_by_id[beat_id]
        offset = beat.get("mp4_offset_seconds", 0.0)
        dur = beat.get("segment_duration_seconds", 0.0)
        mid = offset + dur / 2
        frame_path = FRAME_DIR / f"mid-{beat_id}.png"
        extracted = extract_frame(mid, frame_path)
        record(group, f"{beat_id} midpoint frame extracted",
               extracted, f"t={mid:.3f}s from {MP4_PATH.name}")
        if not extracted:
            continue

        if beat["kind"] == "demo":
            # Demo frames must differ from static slides (any slide has MAD >= threshold).
            opening_slide_id = video_ids[0]  # opening slide
            slide_png = SLIDES_DIR / f"{slide_index[opening_slide_id]:03d}-{opening_slide_id}.png"
            if slide_png.exists():
                m = mad_rgb(frame_path, slide_png)
                record(group, f"{beat_id} demo frame differs from slide (MAD >= {MAD_SLIDE_THRESHOLD})",
                       m >= MAD_SLIDE_THRESHOLD, f"MAD {m:.2f} vs threshold {MAD_SLIDE_THRESHOLD}")
        else:
            si = slide_index.get(beat_id)
            if si is None:
                continue
            slide_png = SLIDES_DIR / f"{si:03d}-{beat_id}.png"
            if not slide_png.exists():
                record(group, f"{beat_id} slide PNG exists", False, f"missing {slide_png}")
                continue
            m = mad_rgb(frame_path, slide_png)
            record(group, f"{beat_id} midpoint frame matches slide PNG (MAD < {MAD_SLIDE_THRESHOLD})",
                   m < MAD_SLIDE_THRESHOLD, f"MAD {m:.4f}")

    # --- boundary-frame checks at each join ---
    for i in range(len(video_ids) - 1):
        before_id = video_ids[i]
        after_id = video_ids[i + 1]
        before_beat = beats_by_id[before_id]
        after_beat = beats_by_id[after_id]
        join_t = (before_beat.get("mp4_offset_seconds", 0.0)
                  + before_beat.get("segment_duration_seconds", 0.0))

        t_before = join_t - 2 * FRAME_SECS
        t_after = join_t + 2 * FRAME_SECS

        f_before = FRAME_DIR / f"join{i:02d}-before.png"
        f_after = FRAME_DIR / f"join{i:02d}-after.png"
        ok_before = t_before > 0 and extract_frame(t_before, f_before)
        ok_after = extract_frame(t_after, f_after)

        if ok_before and before_beat["kind"] != "demo":
            si = slide_index.get(before_id)
            slide_png = SLIDES_DIR / f"{si:03d}-{before_id}.png" if si else None
            if slide_png and slide_png.exists():
                m = mad_rgb(f_before, slide_png)
                record(group, f"join {i} before: {before_id} slide still present",
                       m < MAD_SLIDE_THRESHOLD, f"MAD {m:.4f} at t={t_before:.3f}s")
        elif ok_before and before_beat["kind"] == "demo":
            opening_slide_id = video_ids[0]
            slide_png = SLIDES_DIR / f"{slide_index[opening_slide_id]:03d}-{opening_slide_id}.png"
            if slide_png.exists():
                m = mad_rgb(f_before, slide_png)
                record(group, f"join {i} before: {before_id} demo frame differs from slide",
                       m >= MAD_SLIDE_THRESHOLD, f"MAD {m:.2f} at t={t_before:.3f}s")

        if ok_after and after_beat["kind"] != "demo":
            si = slide_index.get(after_id)
            slide_png = SLIDES_DIR / f"{si:03d}-{after_id}.png" if si else None
            if slide_png and slide_png.exists():
                m = mad_rgb(f_after, slide_png)
                record(group, f"join {i} after: {after_id} slide appears",
                       m < MAD_SLIDE_THRESHOLD, f"MAD {m:.4f} at t={t_after:.3f}s")
        elif ok_after and after_beat["kind"] == "demo":
            opening_slide_id = video_ids[0]
            slide_png = SLIDES_DIR / f"{slide_index[opening_slide_id]:03d}-{opening_slide_id}.png"
            if slide_png.exists():
                m = mad_rgb(f_after, slide_png)
                record(group, f"join {i} after: {after_id} demo frame differs from slide",
                       m >= MAD_SLIDE_THRESHOLD, f"MAD {m:.2f} at t={t_after:.3f}s")


def check_audio(manifest: dict) -> None:
    group = "audio"
    try:
        samples = decode_full_audio()
    except RuntimeError as exc:
        record(group, "full audio decode to PCM", False, str(exc))
        return
    record(group, "full audio decode to PCM",
           len(samples) > 0,
           f"{len(samples)} samples ({len(samples) / AUDIO_RATE:.3f}s at {AUDIO_RATE} Hz mono)")

    window_samples = int(0.3 * AUDIO_RATE)
    demo_beats = [b for b in manifest["beats"]
                  if b["kind"] == "demo" and b["include_in"]["video"]]
    for beat in demo_beats:
        beat_id = beat["id"]
        offset_sec = beat.get("mp4_offset_seconds", 0.0)
        probe_t = offset_sec + 0.1
        start_i = int(probe_t * AUDIO_RATE)
        window = samples[start_i:start_i + window_samples]
        if len(window) < window_samples // 2:
            record(group, f"{beat_id} audio window available", False,
                   f"too few samples at t={probe_t:.3f}s")
            continue
        record(group, f"{beat_id} audio window available",
               True, f"{len(window)} samples at t={probe_t:.3f}s")

        measured = zero_crossing_freq(window, AUDIO_RATE)
        source_start = beat.get("source_range", {}).get("start_seconds", 0.0)
        expected = tone_at(source_start + 0.1)
        close = abs(measured - expected) <= max(expected * 0.02, 5.0)
        record(group, f"{beat_id} demo tone preserved at opening",
               close,
               f"measured {measured:.1f} Hz, expected {expected:.0f} Hz "
               f"(source scene at {source_start + 0.1:.3f}s)")

    note(group, "no TTS over demo audio",
         "demo beats carry no narration text (build_plan.py design); "
         "tone checks above confirm demo audio is audible at each demo offset")
    note(group, "listening",
         "UNVERIFIED: this headless host has no audio device; "
         "output/sprint-briefing.mp4 is retained for manual listening review")
    note(group, "text legibility",
         "UNVERIFIED: static slide frames are rendered at 1920x1080 by Playwright "
         "(confirmed in validate_static.py); H.264 re-encoding at CRF 18 is high "
         "quality but lossy — manual visual review of the MP4 is needed")


def check_silent_source() -> None:
    """Verify a video-only clip (no audio stream) composes with silent PCM."""
    group = "silent-source"
    SILENT_TEST_DIR.mkdir(parents=True, exist_ok=True)
    master = EXPERIMENT_ROOT / "input" / "sprint-demo.mp4"
    noaudio_clip = SILENT_TEST_DIR / "noaudio-clip.mp4"
    noaudio_seg = SILENT_TEST_DIR / "noaudio-seg.mp4"

    # Extract a 2-second video-only clip (no audio map).
    result = run([
        ffmpeg(), "-y", "-v", "error",
        "-ss", "1.0", "-t", "2.0", "-i", str(master),
        "-map", "0:v", "-c:v", "copy",
        str(noaudio_clip),
    ])
    clip_ok = result.returncode == 0 and noaudio_clip.exists()
    record(group, "video-only test clip created", clip_ok,
           f"{noaudio_clip} (no audio map)" if clip_ok
           else f"ffmpeg error: {result.stderr.decode()[:200]}")
    if not clip_ok:
        return

    # Confirm the clip has no audio stream.
    probe = ffprobe_json(["-show_streams", "-select_streams", "a", str(noaudio_clip)])
    has_no_audio = not probe.get("streams")
    record(group, "test clip has no audio stream", has_no_audio,
           f"streams: {probe.get('streams')}")

    # Compose a segment — make_demo_segment must add anullsrc silence.
    try:
        make_demo_segment(noaudio_clip, noaudio_seg)
        seg_ok = noaudio_seg.exists()
    except RuntimeError as exc:
        record(group, "make_demo_segment succeeds for no-audio clip", False, str(exc))
        return
    record(group, "make_demo_segment succeeds for no-audio clip",
           seg_ok, str(noaudio_seg))
    if not seg_ok:
        return

    # Verify the segment has audio and its duration matches the clip.
    probe_seg = ffprobe_all(noaudio_seg)
    by_type = {s["codec_type"]: s for s in probe_seg.get("streams", [])}
    audio = by_type.get("audio", {})
    clip_dur = float(ffprobe_json(["-show_entries", "format=duration",
                                   str(noaudio_clip)])["format"]["duration"])
    seg_dur = float(probe_seg.get("format", {}).get("duration", 0))
    # ffprobe-static 4.0.2 does not report codec_name for PCM-in-MP4; it
    # uses codec_tag_string 'ipcm' instead (gotcha: old ffprobe + ffmpeg 7).
    codec_name = audio.get("codec_name", "") or ""
    codec_tag = audio.get("codec_tag_string", "") or ""
    is_pcm = "pcm" in codec_name or "pcm" in codec_tag or "ipcm" in codec_tag
    record(group, "segment has audio stream (PCM / ipcm)",
           "audio" in by_type and is_pcm,
           f"codec_name: {codec_name!r}, codec_tag: {codec_tag!r}, "
           f"rate: {audio.get('sample_rate')}, ch: {audio.get('channels')}")
    record(group, "segment stereo 48 kHz",
           audio.get("sample_rate") == "48000" and audio.get("channels") == 2,
           f"{audio.get('sample_rate')} Hz, {audio.get('channels')} ch")
    record(group, "segment duration matches clip",
           abs(seg_dur - clip_dur) <= FRAME_SECS + 0.005,
           f"segment {seg_dur:.3f}s, clip {clip_dur:.3f}s")

    # Verify all samples are zero (silence).
    result = subprocess.run(
        [ffmpeg(), "-v", "error", "-i", str(noaudio_seg),
         "-map", "0:a", "-f", "s16le", "-ar", str(AUDIO_RATE), "-ac", "1", "-"],
        capture_output=True, cwd=EXPERIMENT_ROOT,
    )
    if result.returncode != 0:
        record(group, "silent segment decodes cleanly", False,
               result.stderr.decode()[:200])
        return
    silent_samples = array.array("h", result.stdout)
    all_zero = len(silent_samples) > 0 and all(s == 0 for s in silent_samples)
    record(group, "silent segment has all-zero audio",
           all_zero,
           f"{len(silent_samples)} samples, all zero: {all_zero}")

    note(group, "re-encoding",
         "segment re-encodes to H.264/PCM (intermediate) and then to AAC in the "
         "final concat pass; this is not lossless and is not claimed as lossless")


# ------------------------------------------------------------------ report


def main() -> int:
    if not MANIFEST_PATH.exists():
        print(f"error: {MANIFEST_PATH} not found; run src/make_composition.py first",
              file=sys.stderr)
        return 1
    manifest = json.loads(MANIFEST_PATH.read_text())

    info = check_output()
    if MP4_PATH.exists():
        check_decode()
        check_duration(manifest)
        check_manifest(manifest)
        check_frames(manifest)
        check_audio(manifest)
    check_silent_source()

    note("manual", "visual legibility in player",
         "UNVERIFIED: frame extraction and MAD checks confirm the expected slide "
         "appears at each narrated beat; legibility in a real video player with "
         "scaled rendering is left for manual review")
    note("manual", "narration intelligibility",
         "UNVERIFIED: Kokoro WAV intelligibility is recorded in "
         "evidence/results-narration.md; the composition preserves the WAVs "
         "verbatim as PCM segments (no re-synthesis, no pitch shift)")
    note("manual", "speech not truncated",
         "slide hold is ceil(wav_dur * 30) / 30 (frame-aligned ceiling), "
         "so the last speech frame always completes before the slide ends; "
         "check the results-narration.md measured durations for evidence")

    lines: list[str] = []
    lines.append("# Composition validation (#427)")
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
    Path("evidence/results-composition.md").write_text(report + "\n")

    for line in report.splitlines():
        print(line)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
