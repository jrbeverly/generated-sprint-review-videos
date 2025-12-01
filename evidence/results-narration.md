# Local Kokoro narration validation (#429)

Run date: 2026-09-14T09:49:50

| Group | Check | Status | Detail |
|---|---|---|---|
| main | no HuggingFace downloads during the run | PASS | work/narration-hf-home contains 0 files |
| main | one English voice recorded | PASS | voice: af_heart |
| main | sample rate recorded | PASS | 24000 Hz |
| main | asset paths recorded | PASS | assets/kokoro/kokoro-v1_0.pth / assets/kokoro/voices/af_heart.pt |
| main | generation wall time recorded | PASS | 9.7s for 5 beats |
| main | narration covers exactly the narrated video beats | PASS | got ['opening', 'new-checkout-intro', 'new-checkout-outro', 'admin-controls-intro', 'closing'], want ['opening', 'new-checkout-intro', 'new-checkout-outro', 'admin-controls-intro', 'closing'] |
| main | no narration over demo beats | PASS | demo beats have no narration entries |
| main | literal narration text preserved | PASS | every narrated text matches script.json verbatim |
| main | opening wav exists and is nonempty | PASS | output/audio/001-opening.wav (105644 bytes) |
| main | opening 24 kHz mono PCM stream | PASS | pcm_s16le 24000 Hz 1ch |
| main | opening measured duration recorded | PASS | recorded 2.200s, ffprobe 2.200s |
| main | opening fully decodes with ffmpeg | PASS | ffmpeg -v error -i wav -f null - exits 0 with empty stderr |
| main | opening contains nonzero samples | PASS | output/audio/001-opening.wav has audible (nonzero) PCM data |
| main | new-checkout-intro wav exists and is nonempty | PASS | output/audio/002-new-checkout-intro.wav (214844 bytes) |
| main | new-checkout-intro 24 kHz mono PCM stream | PASS | pcm_s16le 24000 Hz 1ch |
| main | new-checkout-intro measured duration recorded | PASS | recorded 4.475s, ffprobe 4.475s |
| main | new-checkout-intro fully decodes with ffmpeg | PASS | ffmpeg -v error -i wav -f null - exits 0 with empty stderr |
| main | new-checkout-intro contains nonzero samples | PASS | output/audio/002-new-checkout-intro.wav has audible (nonzero) PCM data |
| main | new-checkout-outro wav exists and is nonempty | PASS | output/audio/003-new-checkout-outro.wav (175244 bytes) |
| main | new-checkout-outro 24 kHz mono PCM stream | PASS | pcm_s16le 24000 Hz 1ch |
| main | new-checkout-outro measured duration recorded | PASS | recorded 3.650s, ffprobe 3.650s |
| main | new-checkout-outro fully decodes with ffmpeg | PASS | ffmpeg -v error -i wav -f null - exits 0 with empty stderr |
| main | new-checkout-outro contains nonzero samples | PASS | output/audio/003-new-checkout-outro.wav has audible (nonzero) PCM data |
| main | admin-controls-intro wav exists and is nonempty | PASS | output/audio/004-admin-controls-intro.wav (205244 bytes) |
| main | admin-controls-intro 24 kHz mono PCM stream | PASS | pcm_s16le 24000 Hz 1ch |
| main | admin-controls-intro measured duration recorded | PASS | recorded 4.275s, ffprobe 4.275s |
| main | admin-controls-intro fully decodes with ffmpeg | PASS | ffmpeg -v error -i wav -f null - exits 0 with empty stderr |
| main | admin-controls-intro contains nonzero samples | PASS | output/audio/004-admin-controls-intro.wav has audible (nonzero) PCM data |
| main | closing wav exists and is nonempty | PASS | output/audio/005-closing.wav (148844 bytes) |
| main | closing 24 kHz mono PCM stream | PASS | pcm_s16le 24000 Hz 1ch |
| main | closing measured duration recorded | PASS | recorded 3.100s, ffprobe 3.100s |
| main | closing fully decodes with ffmpeg | PASS | ffmpeg -v error -i wav -f null - exits 0 with empty stderr |
| main | closing contains nonzero samples | PASS | output/audio/005-closing.wav has audible (nonzero) PCM data |
| main | no WAVs beyond the narrated set | PASS | 5 WAVs, all listed |
| main | network disabled during generation | INFO | validate.sh runs make_narration.py with HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1, HF_HOME=work/narration-hf-home, and all http(s)_proxy variables pointed at a dead local port, so any network attempt fails; the scratch-dir check above proves no HuggingFace download happened |
| main | listening | INFO | UNVERIFIED: this headless host has no audio device (no aplay/paplay/ffplay), so intelligibility was not listened to; output/audio/001-opening.wav is retained for manual review |
| pptx-only | dry-run selects only video-included narrated beats | PASS | selected ['opening', 'closing'], want ['opening', 'closing'] |
| pptx-only | video-excluded intro/outro beats not narrated | PASS | the pptx-only demo's intro/outro are excluded from the video |
| pptx-only | demo beat never narrated | PASS | demo beats carry no narration text |

Result: 39 checks, 0 failed
