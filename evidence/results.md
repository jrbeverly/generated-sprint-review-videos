# Media-path validation (#430 spike; full deck from #431)

Run date: 2026-09-14T09:49:40

| Group | Check | Status | Detail |
|---|---|---|---|
| fixture | declared demo count | PASS | 3 demos declared (two ranges + one silent case) |
| fixture | new-checkout range validity | PASS | 00:00:02.317..00:00:07.484 in range: True, not 1/30-aligned: True, not keyframe-aligned (frames [0, 250]): True |
| fixture | admin-controls range validity | PASS | 00:00:09.623..00:00:14.202 in range: True, not 1/30-aligned: True, not keyframe-aligned (frames [0, 250]): True |
| fixture | silent-demo range validity | PASS | 00:00:01.417..00:00:06.929 in range: True, not 1/30-aligned: True, not keyframe-aligned (frames [0, 250]): True |
| master | sprint-demo streams | PASS | h264 1920x1080, aac audio |
| master | sprint-demo duration | PASS | 16.000s vs declared 16.0s |
| master | forced GOP layout | PASS | keyframes at frame indices [0, 250] (expected [0, 250], so clip boundaries are not keyframe-aligned) |
| clip | new-checkout streams | PASS | h264 1920x1080 @ 30/1, aac audio |
| clip | new-checkout duration | PASS | measured 5.200s vs declared 5.167s (delta 0.033s <= 0.033s) |
| clip | new-checkout full decode | PASS | ffmpeg -f null - decoded all streams with no errors |
| clip | new-checkout boundary frames | PASS | first frame 70 (declared start frame 70), last frame 225 (declared end frame 224), all 156 decoded frames contiguous (70..225); tolerance 1 frame |
| clip | new-checkout tone at opening | PASS | measured 440.0 Hz, expected scene tone 440 Hz |
| clip | new-checkout tone at ending | PASS | measured 660.0 Hz, expected scene tone 660 Hz |
| poster | new-checkout poster | PASS | (1920, 1080) PNG, frame number 148 vs expected midpoint frame 148 (tolerance 1) |
| clip | admin-controls streams | PASS | h264 1920x1080 @ 30/1, aac audio |
| clip | admin-controls duration | PASS | measured 4.600s vs declared 4.579s (delta 0.021s <= 0.033s) |
| clip | admin-controls full decode | PASS | ffmpeg -f null - decoded all streams with no errors |
| clip | admin-controls boundary frames | PASS | first frame 289 (declared start frame 289), last frame 426 (declared end frame 426), all 138 decoded frames contiguous (289..426); tolerance 1 frame |
| clip | admin-controls tone at opening | PASS | measured 880.0 Hz, expected scene tone 880 Hz |
| clip | admin-controls tone at ending | PASS | measured 1320.0 Hz, expected scene tone 1320 Hz |
| poster | admin-controls poster | PASS | (1920, 1080) PNG, frame number 358 vs expected midpoint frame 358 (tolerance 1) |
| clip | silent-demo streams | PASS | h264 1920x1080 @ 30/1, aac audio |
| clip | silent-demo duration | PASS | measured 5.534s vs declared 5.512s (delta 0.022s <= 0.033s) |
| clip | silent-demo full decode | PASS | ffmpeg -f null - decoded all streams with no errors |
| clip | silent-demo boundary frames | PASS | first frame 43 (declared start frame 43), last frame 208 (declared end frame 207), all 166 decoded frames contiguous (43..208); tolerance 1 frame |
| clip | silent-demo silent audio preserved | PASS | 1.0 s window at t=1.0s: 48000 samples, all zero: True |
| poster | silent-demo poster | PASS | (1920, 1080) PNG, frame number 126 vs expected midpoint frame 126 (tolerance 1) |
| pptx | zip structure | PASS | media entries: 2 mp4 + 2 png for 2 demo beats (['ppt/media/media-3-1.mp4', 'ppt/media/media-6-1.mp4', 'ppt/media/image-3-3.png', 'ppt/media/image-6-3.png']) |
| pptx | new-checkout embedded bytes match local assets | PASS | video bytes == new-checkout.mp4: True; poster bytes == new-checkout-poster.png: True |
| pptx | new-checkout internal relationships | PASS | video rel rId=rId1 -> ../media/media-3-1.mp4, p14 media rel -> ../media/media-3-1.mp4 (same target: True), image rel -> ../media/image-3-3.png; no external targets |
| pptx | new-checkout slide XML media elements | PASS | videoFile present: True, p14:media present: True, blip poster r:embed=rId3 == image rel rId3: True |
| pptx | admin-controls embedded bytes match local assets | PASS | video bytes == admin-controls.mp4: True; poster bytes == admin-controls-poster.png: True |
| pptx | admin-controls internal relationships | PASS | video rel rId=rId1 -> ../media/media-6-1.mp4, p14 media rel -> ../media/media-6-1.mp4 (same target: True), image rel -> ../media/image-6-3.png; no external targets |
| pptx | admin-controls slide XML media elements | PASS | videoFile present: True, p14:media present: True, blip poster r:embed=rId3 == image rel rId3: True |
| pptx | content types | PASS | mp4 -> video/mp4, png -> image/png |
| pptx | deck survives move away from inputs | PASS | copied to /tmp/briefing-standalone-nu4ad4tk/sprint-briefing.pptx; input files untouched |
| pptx | moved deck keeps embedded bytes | PASS | all video and poster bytes still embedded inside the moved deck (no external source dependency) |
| pptx | desktop PowerPoint playback | INFO | UNVERIFIED: no desktop PowerPoint on this headless Linux container (no display, no LibreOffice, no PowerPoint binary). Deck retained for manual review at output/sprint-briefing.pptx. Package inspection cannot establish player compatibility. |

Result: 38 checks, 0 failed
