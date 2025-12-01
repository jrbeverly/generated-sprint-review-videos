# Complete local briefing (#434)

- `./setup.sh` completed separately; Chromium host runtime libraries were installed before validation.
- `sudo -n unshare -n sudo -u node ./validate.sh` passed with no network interfaces available beyond the inactive loopback interface. No Jira access, deployment, or sibling experiment was used.
- The same `./briefing.sh fixtures/sprint-analysis.json input/sprint-demo.mp4` command produced PPTX, PDF, a 27.567-second MP4, two demo clips/posters, five WAVs, five slide PNGs, script, manifest, and seven inspectable composition segments.
- Every generated artifact path recorded in the manifest resolved to a nonempty file under `output/`; the successful command logged exactly two demo extractions.
- Four invalid plans exited nonzero without a script/manifest completion claim or MP4. Each attempt used a fresh output directory.
- A deliberately missing browser failed after PPTX generation, with no MP4, no manifest MP4 reference, and no success message. The following successful run used a fresh output directory.
- A repeated invocation refused the existing output directory.
- Existing validations passed: media 38/38, plan 77/77, narration 39/39, static rendering 62/62, composition 84/84.
- Desktop PowerPoint playback and human listening remain unverified; generated media is retained under `output/`.
