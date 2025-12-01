# Composition validation (#427)

Run date: 2026-09-14T09:50:00

| Group | Check | Status | Detail |
|---|---|---|---|
| output | sprint-briefing.mp4 exists and is nonempty | PASS | output/sprint-briefing.mp4 (897913 bytes) |
| output | video codec H.264 | PASS | codec: h264 |
| output | video resolution 1920x1080 | PASS | 1920x1080 |
| output | video frame rate 30 fps | PASS | r_frame_rate: 30/1 |
| output | video pixel format yuv420p | PASS | pix_fmt: yuv420p |
| output | audio codec AAC | PASS | codec: aac |
| output | audio sample rate 48000 Hz | PASS | sample_rate: 48000 |
| output | audio stereo | PASS | channels: 2 |
| decode | FFmpeg fully decodes without errors | PASS | ffmpeg -f null - exits 0 with empty stderr |
| duration | actual duration within 0.1 s of segment sum | PASS | actual 27.567s, segment sum 27.567s, delta 0.000s |
| duration | opening slide hold >= ceil(wav * 30) / 30 | PASS | segment 2.200s, hold 2.200s (wav 2.200s) |
| duration | new-checkout-intro slide hold >= ceil(wav * 30) / 30 | PASS | segment 4.500s, hold 4.500s (wav 4.475s) |
| duration | new-checkout-outro slide hold >= ceil(wav * 30) / 30 | PASS | segment 3.667s, hold 3.667s (wav 3.650s) |
| duration | admin-controls-intro slide hold >= ceil(wav * 30) / 30 | PASS | segment 4.300s, hold 4.300s (wav 4.275s) |
| duration | closing slide hold >= ceil(wav * 30) / 30 | PASS | segment 3.100s, hold 3.100s (wav 3.100s) |
| manifest | manifest has mp4 key | PASS | mp4: output/sprint-briefing.mp4 |
| manifest | all video beats have mp4_offset_seconds filled | PASS | 7 video beats checked |
| manifest | non-video beats keep mp4_offset_seconds: null | PASS | 0 non-video beats, all null |
| manifest | opening mp4_offset_seconds correct | PASS | recorded 0.0, expected 0.000000 |
| manifest | opening segment file exists | PASS | output/segments/opening.mp4 |
| manifest | opening segment_duration_seconds recorded | PASS | 2.200s |
| manifest | new-checkout-intro mp4_offset_seconds correct | PASS | recorded 2.2, expected 2.200000 |
| manifest | new-checkout-intro segment file exists | PASS | output/segments/new-checkout-intro.mp4 |
| manifest | new-checkout-intro segment_duration_seconds recorded | PASS | 4.500s |
| manifest | new-checkout mp4_offset_seconds correct | PASS | recorded 6.7, expected 6.700000 |
| manifest | new-checkout segment file exists | PASS | output/segments/new-checkout.mp4 |
| manifest | new-checkout segment_duration_seconds recorded | PASS | 5.200s |
| manifest | new-checkout-outro mp4_offset_seconds correct | PASS | recorded 11.9, expected 11.900000 |
| manifest | new-checkout-outro segment file exists | PASS | output/segments/new-checkout-outro.mp4 |
| manifest | new-checkout-outro segment_duration_seconds recorded | PASS | 3.667s |
| manifest | admin-controls-intro mp4_offset_seconds correct | PASS | recorded 15.567, expected 15.567000 |
| manifest | admin-controls-intro segment file exists | PASS | output/segments/admin-controls-intro.mp4 |
| manifest | admin-controls-intro segment_duration_seconds recorded | PASS | 4.300s |
| manifest | admin-controls mp4_offset_seconds correct | PASS | recorded 19.867, expected 19.867000 |
| manifest | admin-controls segment file exists | PASS | output/segments/admin-controls.mp4 |
| manifest | admin-controls segment_duration_seconds recorded | PASS | 4.600s |
| manifest | closing mp4_offset_seconds correct | PASS | recorded 24.467, expected 24.467000 |
| manifest | closing segment file exists | PASS | output/segments/closing.mp4 |
| manifest | closing segment_duration_seconds recorded | PASS | 3.100s |
| frames | opening midpoint frame extracted | PASS | t=1.100s from sprint-briefing.mp4 |
| frames | opening midpoint frame matches slide PNG (MAD < 2.0) | PASS | MAD 0.0420 |
| frames | new-checkout-intro midpoint frame extracted | PASS | t=4.450s from sprint-briefing.mp4 |
| frames | new-checkout-intro midpoint frame matches slide PNG (MAD < 2.0) | PASS | MAD 0.0958 |
| frames | new-checkout midpoint frame extracted | PASS | t=9.300s from sprint-briefing.mp4 |
| frames | new-checkout demo frame differs from slide (MAD >= 2.0) | PASS | MAD 185.27 vs threshold 2.0 |
| frames | new-checkout-outro midpoint frame extracted | PASS | t=13.733s from sprint-briefing.mp4 |
| frames | new-checkout-outro midpoint frame matches slide PNG (MAD < 2.0) | PASS | MAD 0.0882 |
| frames | admin-controls-intro midpoint frame extracted | PASS | t=17.717s from sprint-briefing.mp4 |
| frames | admin-controls-intro midpoint frame matches slide PNG (MAD < 2.0) | PASS | MAD 0.0902 |
| frames | admin-controls midpoint frame extracted | PASS | t=22.167s from sprint-briefing.mp4 |
| frames | admin-controls demo frame differs from slide (MAD >= 2.0) | PASS | MAD 179.65 vs threshold 2.0 |
| frames | closing midpoint frame extracted | PASS | t=26.017s from sprint-briefing.mp4 |
| frames | closing midpoint frame matches slide PNG (MAD < 2.0) | PASS | MAD 0.0599 |
| frames | join 0 before: opening slide still present | PASS | MAD 0.0420 at t=2.133s |
| frames | join 0 after: new-checkout-intro slide appears | PASS | MAD 0.0957 at t=2.267s |
| frames | join 1 before: new-checkout-intro slide still present | PASS | MAD 0.0958 at t=6.633s |
| frames | join 1 after: new-checkout demo frame differs from slide | PASS | MAD 181.52 at t=6.767s |
| frames | join 2 before: new-checkout demo frame differs from slide | PASS | MAD 185.31 at t=11.833s |
| frames | join 2 after: new-checkout-outro slide appears | PASS | MAD 0.0881 at t=11.967s |
| frames | join 3 before: new-checkout-outro slide still present | PASS | MAD 0.0882 at t=15.500s |
| frames | join 3 after: admin-controls-intro slide appears | PASS | MAD 0.0904 at t=15.634s |
| frames | join 4 before: admin-controls-intro slide still present | PASS | MAD 0.0907 at t=19.800s |
| frames | join 4 after: admin-controls demo frame differs from slide | PASS | MAD 180.57 at t=19.934s |
| frames | join 5 before: admin-controls demo frame differs from slide | PASS | MAD 171.02 at t=24.400s |
| frames | join 5 after: closing slide appears | PASS | MAD 0.0599 at t=24.534s |
| audio | full audio decode to PCM | PASS | 1324032 samples (27.584s at 48000 Hz mono) |
| audio | new-checkout audio window available | PASS | 14400 samples at t=6.800s |
| audio | new-checkout demo tone preserved at opening | PASS | measured 440.0 Hz, expected 440 Hz (source scene at 2.417s) |
| audio | admin-controls audio window available | PASS | 14400 samples at t=19.967s |
| audio | admin-controls demo tone preserved at opening | PASS | measured 880.0 Hz, expected 880 Hz (source scene at 9.723s) |
| audio | no TTS over demo audio | INFO | demo beats carry no narration text (build_plan.py design); tone checks above confirm demo audio is audible at each demo offset |
| audio | listening | INFO | UNVERIFIED: this headless host has no audio device; output/sprint-briefing.mp4 is retained for manual listening review |
| audio | text legibility | INFO | UNVERIFIED: static slide frames are rendered at 1920x1080 by Playwright (confirmed in validate_static.py); H.264 re-encoding at CRF 18 is high quality but lossy — manual visual review of the MP4 is needed |
| silent-source | video-only test clip created | PASS | work/silent-test/noaudio-clip.mp4 (no audio map) |
| silent-source | test clip has no audio stream | PASS | streams: [] |
| silent-source | make_demo_segment succeeds for no-audio clip | PASS | work/silent-test/noaudio-seg.mp4 |
| silent-source | segment has audio stream (PCM / ipcm) | PASS | codec_name: '', codec_tag: 'ipcm', rate: 48000, ch: 2 |
| silent-source | segment stereo 48 kHz | PASS | 48000 Hz, 2 ch |
| silent-source | segment duration matches clip | PASS | segment 2.067s, clip 2.067s |
| silent-source | silent segment has all-zero audio | PASS | 98304 samples, all zero: True |
| silent-source | re-encoding | INFO | segment re-encodes to H.264/PCM (intermediate) and then to AAC in the final concat pass; this is not lossless and is not claimed as lossless |
| manual | visual legibility in player | INFO | UNVERIFIED: frame extraction and MAD checks confirm the expected slide appears at each narrated beat; legibility in a real video player with scaled rendering is left for manual review |
| manual | narration intelligibility | INFO | UNVERIFIED: Kokoro WAV intelligibility is recorded in evidence/results-narration.md; the composition preserves the WAVs verbatim as PCM segments (no re-synthesis, no pitch shift) |
| manual | speech not truncated | INFO | slide hold is ceil(wav_dur * 30) / 30 (frame-aligned ceiling), so the last speech frame always completes before the slide ends; check the results-narration.md measured durations for evidence |

Result: 84 checks, 0 failed
