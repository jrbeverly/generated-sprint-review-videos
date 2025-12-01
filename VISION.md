# Demo Video Integration

The sprint briefing should support embedded demo videos as first-class presentation content.

A source sprint demo recording may contain several demonstrations in one continuous video.

For development, this may be a synthetic or mock recording.

The system receives:

```text
sprint-demo.mp4
+
sprint-analysis.json
```

The JSON contains the locations of meaningful demo segments.

For example:

```json
{
  "demos": [
    {
      "id": "new-checkout",
      "title": "New Checkout Experience",
      "start": "00:02:14.000",
      "end": "00:03:01.500",
      "epic": "Checkout Modernization"
    },
    {
      "id": "admin-controls",
      "title": "Administrative Controls",
      "start": "00:05:42.000",
      "end": "00:06:31.000",
      "epic": "Enterprise Administration"
    }
  ]
}
```

The generator should not analyze the source recording to discover these ranges.

The ranges are provided explicitly.

This keeps video processing deterministic and simple.

---

## Clip Extraction

FFmpeg extracts each declared segment into an independent artifact.

Conceptually:

```text
input/
  sprint-demo.mp4

        ↓ FFmpeg

work/
  demos/
    new-checkout.mp4
    admin-controls.mp4
```

Each clip corresponds directly to one structured demo entry.

The clipping stage performs only:

```text
source video
+
start timestamp
+
end timestamp
=
demo clip
```

No computer vision, transcription, scene detection, or semantic video analysis is required.

---

# PowerPoint Integration

Where supported, the generated PowerPoint should embed the corresponding demo clip directly into the relevant slide.

For example:

```text
Slide 6
┌──────────────────────────────────────────┐
│ Checkout Modernization                  │
│                                          │
│  [ embedded demo video ]                │
│                                          │
│  Released this sprint                   │
│  Reduced checkout flow from 5 → 3 steps │
└──────────────────────────────────────────┘
```

The demo video should be treated as part of the slide rather than as an external presentation dependency where practical.

A poster frame or thumbnail may be generated from the clip for use as its visible PowerPoint preview.

FFmpeg may extract that image as part of the same preprocessing step.

Conceptually:

```text
demo clip
   ↓
FFmpeg
   ↓
poster.png
```

The PowerPoint generator then receives:

```text
demo.mp4
poster.png
```

and places both according to the presentation template.

---

# Video Briefing Integration

The generated MP4 should not attempt to simulate playback of an embedded PowerPoint video.

Instead, it should use the extracted demo clip directly.

The video timeline may therefore contain two kinds of segments:

```text
narrated slide

demo clip
```

For example:

```text
Slide 1 + narration
        ↓
Slide 2 + narration
        ↓
Slide 3 + narration
        ↓
Checkout demo clip
        ↓
Slide 4 + narration
        ↓
Admin demo clip
        ↓
Closing slide + narration
```

This creates a cleaner final video than screen-recording PowerPoint playback.

---

# Narration Around Demos

Each demo may have narration associated with its introduction and conclusion.

For example:

```json
{
  "id": "new-checkout",
  "intro": "The first release this sprint was the redesigned checkout experience.",
  "clip": "new-checkout.mp4",
  "outro": "This removes two steps from the most common purchase path."
}
```

The timeline becomes:

```text
intro slide + TTS
        ↓
demo clip
        ↓
outcome slide + TTS
```

The demo itself may preserve its original audio.

The system should not automatically place TTS narration over demo audio unless explicitly requested by the input configuration.

---

# Demo Slides as Narrative Beats

The no-animation principle still applies.

Instead of one complicated slide that changes state around a video, generate separate narrative beats.

For example:

```text
Slide 7
"Checkout Modernization"

        ↓

Demo Clip
"New Checkout Experience"

        ↓

Slide 8
"Outcome: Checkout reduced from 5 steps to 3"
```

This maps naturally into both PowerPoint and MP4.

---

# Demo Metadata

Each demo entry may carry presentation metadata such as:

```json
{
  "id": "checkout-demo",
  "title": "New Checkout Experience",
  "epic": "Checkout Modernization",
  "release": "2026.08",
  "business_value": "Reduced purchase friction",
  "start": "00:02:14.000",
  "end": "00:03:01.500",
  "include_in_pptx": true,
  "include_in_video": true
}
```

This allows the same source demo to participate differently in different outputs.

For example:

```text
PPTX:
embedded video

PDF:
poster image + demo title

MP4:
actual extracted clip
```

---

# PDF Behavior

PDF cannot contain the playable demo in the same way as PowerPoint or MP4.

For the PDF representation, the video should degrade gracefully into a static demo card.

For example:

```text
┌──────────────────────────────────────────┐
│ [ Demo poster frame ]                   │
│                                          │
│ New Checkout Experience                 │
│ Checkout Modernization                  │
│ Demo duration: 47 seconds               │
└──────────────────────────────────────────┘
```

The PDF therefore remains useful without pretending to support video playback.

---

# Expanded Artifact Pipeline

The complete briefing pipeline becomes:

```text
sprint-analysis.json
sprint-demo.mp4
presentation assets
        ↓
parse presentation plan
        ↓
extract demo clips
        ↓
extract poster frames
        ↓
generate PPTX
        ↓
generate narration
        ↓
generate local Kokoro TTS
        ↓
render static slides
        ↓
combine:
  slides + narration
  demo clips
        ↓
FFmpeg
        ↓
sprint-briefing.mp4
```

The PPTX and MP4 share source assets but are produced independently.

---

# Artifact Layout

A run may produce:

```text
output/
  sprint-briefing.pptx
  sprint-briefing.pdf
  sprint-briefing.mp4

  demos/
    checkout.mp4
    checkout-poster.png
    admin-controls.mp4
    admin-controls-poster.png

  audio/
    001-introduction.wav
    002-health.wav
    003-checkout-intro.wav
    004-checkout-outcome.wav

  slides/
    001.png
    002.png
    003.png
    004.png

  script.json
  manifest.json
```

Intermediate artifacts should be ordinary files.

This keeps the pipeline inspectable and easy to debug.

---

# Updated Design Principle

The generated PowerPoint and generated video should tell the same sprint story, but they do not need to render that story in exactly the same technical way.

For PowerPoint:

```text
embed demo clips
```

For MP4:

```text
insert demo clips directly into the timeline
```

For PDF:

```text
represent demo clips with poster frames
```

The presentation model is shared.

The rendering implementation is allowed to differ by output format.

---

# Success Criterion for Demo Integration

The system should be able to take:

```text
one master sprint demo recording
+
structured clip definitions
```

and automatically produce:

```text
independent demo clips

embedded demonstrations in PPTX

static demo representations in PDF

full-fidelity demo playback in MP4
```

without requiring manual video editing.
