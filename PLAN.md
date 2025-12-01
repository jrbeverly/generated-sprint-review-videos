# Implementation plan

Target: `jira/generated-sprint-review-videos/` (issue #402).

Build a local command that takes `sprint-analysis.json` and `sprint-demo.mp4`
and produces the artifacts in `VISION.md`. This ticket proposes the work;
the pipeline is not implemented yet. Keep every script, fixture, dependency
declaration, and asset inside this experiment. No Jira connection or deployment
is needed to prove the behavior.

## 1. Prove the media path first

Create a short synthetic master recording with visibly numbered frames,
distinct scenes, and audible tones. Declare two non-keyframe-aligned ranges in
a small JSON fixture. Use FFmpeg to extract clips by explicit start/end times
and generate one poster per clip. Re-encode for accurate boundaries rather
than relying on keyframe-aligned stream copying. Preserve source audio when
present; exercise a silent source as a second case.

Before building the full story, make a one-slide PPTX containing one local clip
and its poster. Inspect its ZIP contents for embedded media and internal
relationships. Open it in an available desktop PowerPoint installation to
check playback after moving the PPTX away from the input files. If that viewer
is unavailable, record playback as unverified and retain the file for manual
review. Package inspection alone cannot establish player compatibility.

## 2. Define one small presentation plan

Use JSON array order as narrative order. Require unique filename-safe demo IDs,
titles, and timestamps with `0 <= start < end <= source duration`. Assume one
local master recording and trusted local assets. Check these few constraints
because incorrect ranges or colliding IDs would invalidate the experiment.

Carry `epic`, `release`, and `business_value` through when supplied. Default
`include_in_pptx` and `include_in_video` to true. Propose that PDF follows PPTX
inclusion, since the vision defines no separate PDF switch. Record this
assumption in the fixture. Extract each included demo once, even when both
outputs use it; omit demos excluded from both.

Allow optional literal `intro` and `outro` text on each demo. Create separate
intro, demo, and outcome beats; omit absent intro/outro beats. Use fixed opening
and closing text for the initial fixture. Save the ordered narration text in
`script.json`. Do not infer business outcomes or discover video ranges.

Use one ordered list of beats for all outputs, filtered by inclusion flags.
Record IDs, source ranges, artifact paths, measured durations, and final MP4
segment offsets in `manifest.json`. Keep this as ordinary JSON, not a new
presentation framework.

## 3. Generate static presentation assets and documents

Use a small Node script with PptxGenJS for PPTX and a fixed HTML/CSS layout
rendered by a local headless browser for PNG slides and PDF. Both renderers
consume the same beat data and local posters. Use a fixed 16:9 canvas and one
local font; no animation, transitions, template engine, or slide editor.

PPTX demo beats embed the MP4 and show its poster. PDF demo beats show the
poster, title, epic when present, and measured duration. PDF is rendered from
the static layout, so generating it does not require PowerPoint or a service
that converts embedded video. Narrated PNG slides use the same static layout.
Check that text and ordering agree across renderers; pixel identity is not a
requirement.

PptxGenJS documents local video embedding in its
[media API](https://gitbrent.github.io/PptxGenJS/docs/api-media/).
Verify the selected version's poster behavior in the first spike before
committing to it. If embedding fails, retain poster-only output for diagnosis
and mark the embedding criterion incomplete; do not call it a successful demo.

## 4. Add local narration and compose MP4

Use a small Python script with local Kokoro inference for the literal narration
in `script.json`, producing one WAV per narrated beat. Start with one English
voice and CPU execution. Obtain and pin the chosen package, model, voice, and
phonemizer assets during setup; prove that a subsequent run needs no network.
The upstream [Kokoro project](https://github.com/hexgrad/kokoro) is the reference
for its inference and language dependencies. Confirm these on the actual host
before promising offline execution or a runtime budget.

Hold each static slide for its measured WAV duration. Insert extracted clips
directly between narrated segments. Keep demo audio and place no TTS over it.
Overlaid narration is outside the initial slice; do not accept an overlay
option until its behavior is implemented and checked.

Normalize composition segments to fixed 1920x1080, 30 fps, H.264/yuv420p and
48 kHz stereo audio. Preserve aspect ratio with padding. Add silence for clips
without audio, reset timestamps, then concatenate with FFmpeg. Inspect text
legibility after encoding; direct clip insertion avoids screen capture but
does not promise lossless encoding. FFmpeg's
[filter documentation](https://ffmpeg.org/ffmpeg-filters.html) describes the
trim, timestamp, scaling, audio, and concat operations to verify in this spike.

Write `output/sprint-briefing.{pptx,pdf,mp4}`, `demos/`, `audio/`, `slides/`,
`script.json`, and `manifest.json` as described by the vision. Use a fresh output
directory for each validation run so stale artifacts cannot mask missing work.

## 5. Validate the local end-to-end flow

Implement one fixture runner alongside the pipeline, only for these checks:

| Behavior | Evidence required |
| --- | --- |
| Explicit clipping | Check numbered boundary frames and duration against each declared range, within one output frame; no neighboring scene leakage. |
| Playable media | FFprobe reports expected streams; FFmpeg fully decodes every clip and the final MP4 without errors. |
| Shared narrative | Compare expected beat IDs and titles with PPTX XML, extracted PDF text, and manifest order. Exercise both inclusion flags independently. |
| Embedded PPTX | Inspect embedded bytes and media relationships; manually play the moved, standalone deck in PowerPoint. |
| Static PDF | Inspect rendered pages for posters, readable titles, epic and duration; check no blank demo cards or clipped text. |
| Local TTS | Generate nonempty decodable WAVs using real Kokoro with network disabled after setup; listen to a short sample for intelligibility. |
| Timeline and audio | Check final duration against the sum of measured segments within 0.1 seconds; inspect frames around joins and listen for preserved demo tones, no overlapping narration, and no truncated speech. |
| Silent source | A silent demo composes successfully with a silent audio segment of matching duration. |
| Invalid fixture | Reversed/out-of-range timestamps and duplicate IDs fail before producing a claimed completed briefing. |

Run the fixture from this directory with no dependencies on sibling experiments.
Keep commands explicit in the eventual small README. Do not introduce repository
CI, a general validation framework, cloud infrastructure, or hosted TTS.

## Execution limits and completion

An agent can implement scripts, synthesize inputs, inspect ZIP/XML and media
metadata, decode output, and compare frames when the required tools are present.
Those checks do not establish narration quality or PowerPoint playback in every
viewer; retain manual visual/listening review and name the viewer actually tested.

This planning pass found Node and Python on PATH, but not FFmpeg, FFprobe,
LibreOffice, or eSpeak NG. Browser and Kokoro availability have not been tested.
Provision media tools, a browser, and Kokoro assets locally in the implementation
ticket. LibreOffice is not required by the proposed rendering route. If installs,
model downloads, or desktop access are unavailable, report the specific stage
as blocked or unverified; synthetic audio can isolate composition during
development but cannot satisfy the real Kokoro check.

Completion requires the two-demo fixture to produce all three documents and
independent clips without manual editing, with the checks above recorded as
passed, failed, or unverified. Run it again with prepared local assets and the
network disabled. No deployment is required. For this documentation-only ticket,
review coverage against `VISION.md`, check local links, and run `git diff --check`.
