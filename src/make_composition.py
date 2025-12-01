#!/usr/bin/env python3
"""Compose sprint-briefing.mp4 from narrated slides and demo clips (#427).

Reads output/manifest.json (video-beat order, demo artifact paths) and
output/audio/narration.json (per-beat WAV paths and measured durations).
Writes one normalized PCM segment per video beat to output/segments/, then
concatenates them into output/sprint-briefing.mp4 with one H.264/AAC pass.

Narrated beats: the slide PNG is held for ceil(WAV_dur * 30) / 30 seconds
(frame-aligned so speech is never cut) with the WAV apad'd to that length.
Demo beats: the extracted clip is normalized to 1920x1080 / 30 fps / H.264 /
yuv420p / 48 kHz stereo PCM; anullsrc silence is added when no audio stream
is present. All intermediate segments use PCM audio to avoid AAC join
artifacts in the concat filter; AAC is only written in the final pass.

Updates manifest.json in-place: adds segment, segment_duration_seconds, and
cumulative mp4_offset_seconds to each video-included beat. Non-video beats
keep mp4_offset_seconds: null. Adds mp4 to the manifest top level.
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_tools import EXPERIMENT_ROOT, ffmpeg, ffprobe_json, run  # noqa: E402

MANIFEST_PATH = Path("output/manifest.json")
NARRATION_PATH = Path("output/audio/narration.json")
SLIDES_DIR = Path("output/slides")
MP4_PATH = Path("output/sprint-briefing.mp4")
SEGMENTS_DIR = Path("output/segments")
FPS = 30
AUDIO_RATE = 48000

_VFILTER = (
    "scale=1920:1080:force_original_aspect_ratio=decrease,"
    "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
    "setpts=PTS-STARTPTS"
)


def probe_duration(path: Path) -> float:
    probe = ffprobe_json(["-show_entries", "format=duration", str(path)])
    return float(probe["format"]["duration"])


def has_audio(path: Path) -> bool:
    probe = ffprobe_json(["-show_streams", "-select_streams", "a", str(path)])
    return bool(probe.get("streams"))


def rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(EXPERIMENT_ROOT))
    except ValueError:
        return str(path)


def make_slide_segment(slide_png: Path, wav: Path, hold: float, out: Path) -> None:
    """Static slide held for `hold` seconds (frame-aligned) with apad'd WAV.

    Input-side -t on the looped PNG prevents ffmpeg from producing a non-frame-
    aligned duration; apad=whole_dur pads the mono WAV to the same hold length.
    -ac 2 upmixes mono WAV to stereo PCM for consistency with demo segments.
    """
    cmd = [
        ffmpeg(), "-y", "-v", "error",
        "-loop", "1", "-framerate", str(FPS), "-t", f"{hold:.6f}", "-i", str(slide_png),
        "-i", str(wav),
        "-vf", _VFILTER,
        "-af", (f"aresample={AUDIO_RATE},"
                f"apad=whole_dur={hold:.6f},"
                f"asetpts=PTS-STARTPTS"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "pcm_s16le", "-ac", "2",
        "-t", f"{hold:.6f}",
        str(out),
    ]
    result = run(cmd)
    if result.returncode != 0:
        raise RuntimeError(
            f"slide segment failed for {out.name}: {result.stderr.decode()}")


def make_demo_segment(clip: Path, out: Path) -> None:
    """Normalize a demo clip to 1920x1080 / 30 fps / H.264 / PCM stereo.

    When no audio stream is present, anullsrc generates matching silence for
    the clip's duration.
    """
    if has_audio(clip):
        cmd = [
            ffmpeg(), "-y", "-v", "error",
            "-i", str(clip),
            "-vf", _VFILTER,
            "-af", f"aresample={AUDIO_RATE},asetpts=PTS-STARTPTS",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "pcm_s16le", "-ac", "2",
            str(out),
        ]
    else:
        dur = probe_duration(clip)
        cmd = [
            ffmpeg(), "-y", "-v", "error",
            "-i", str(clip),
            "-f", "lavfi", "-i", f"anullsrc=r={AUDIO_RATE}:cl=stereo",
            "-vf", _VFILTER,
            "-af", f"atrim=0:{dur:.6f},asetpts=PTS-STARTPTS",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "pcm_s16le", "-ac", "2",
            "-shortest",
            str(out),
        ]
    result = run(cmd)
    if result.returncode != 0:
        raise RuntimeError(
            f"demo segment failed for {clip.name}: {result.stderr.decode()}")


def concat_segments(segments: list[Path], out: Path) -> None:
    inputs: list[str] = []
    for seg in segments:
        inputs += ["-i", str(seg)]
    n = len(segments)
    links = "".join(f"[{i}:v][{i}:a]" for i in range(n))
    fc = f"{links}concat=n={n}:v=1:a=1[outv][outa]"
    cmd = [
        ffmpeg(), "-y", "-v", "error",
        *inputs,
        "-filter_complex", fc,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(out),
    ]
    result = run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"concat failed: {result.stderr.decode()}")


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text())
    narration = json.loads(NARRATION_PATH.read_text())
    wav_by_id = {e["beat_id"]: e for e in narration["beats"]}

    # Slide PNG numbering matches make_static.mjs: beats with text that are
    # video-included, numbered 1-based in manifest order.
    slide_index: dict[str, int] = {}
    idx = 1
    for beat in manifest["beats"]:
        if "text" in beat and beat["include_in"]["video"]:
            slide_index[beat["id"]] = idx
            idx += 1

    video_ids: list[str] = manifest["outputs"]["video"]
    beats_by_id = {beat["id"]: beat for beat in manifest["beats"]}

    SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)
    MP4_PATH.parent.mkdir(parents=True, exist_ok=True)
    MP4_PATH.unlink(missing_ok=True)

    segments: list[Path] = []
    durations: list[float] = []

    for beat_id in video_ids:
        beat = beats_by_id[beat_id]
        seg = SEGMENTS_DIR / f"{beat_id}.mp4"

        if beat["kind"] == "demo":
            clip = EXPERIMENT_ROOT / beat["artifacts"]["clip"]
            print(f"  demo  {beat_id}: {beat['artifacts']['clip']}")
            make_demo_segment(clip, seg)
        else:
            entry = wav_by_id[beat_id]
            wav = EXPERIMENT_ROOT / entry["wav"]
            hold = math.ceil(entry["duration_seconds"] * FPS) / FPS
            png = SLIDES_DIR / f"{slide_index[beat_id]:03d}-{beat_id}.png"
            print(f"  slide {beat_id}: hold {hold:.3f}s (wav {entry['duration_seconds']:.3f}s)")
            make_slide_segment(png, wav, hold, seg)
            beat["artifacts"] = {"slide": rel_path(png), "audio": rel_path(wav)}

        dur = probe_duration(seg)
        segments.append(seg)
        durations.append(dur)
        print(f"    -> {seg.name} ({dur:.3f}s)")

    print(f"concat: {len(segments)} segments -> {MP4_PATH}")
    concat_segments(segments, MP4_PATH)

    offset = 0.0
    for beat_id, seg, dur in zip(video_ids, segments, durations):
        beat = beats_by_id[beat_id]
        beat["segment"] = rel_path(seg)
        beat["segment_duration_seconds"] = round(dur, 6)
        beat["mp4_offset_seconds"] = round(offset, 6)
        offset += dur

    manifest["mp4"] = rel_path(MP4_PATH)
    manifest["artifacts"] = {
        "pptx": "output/sprint-briefing.pptx",
        "pdf": "output/sprint-briefing.pdf",
        "mp4": rel_path(MP4_PATH),
        "script": "output/script.json",
        "narration": rel_path(NARRATION_PATH),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"total: {sum(durations):.3f}s; wrote {MP4_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
