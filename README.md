# Generated sprint review videos

> [!WARNING]
> **AI-authored:** This change was autonomously planned and implemented by an AI software factory from a human-authored specification, with possible subsequent human review or modification.

> [!WARNING]
> This experiment is effectively abandoned. The generated material is retained primarily as a research artifact.

Generate a local sprint briefing with embedded PowerPoint demos, static PDF cards, and narrated MP4 playback from explicit demo ranges.

```sh
./setup.sh
./briefing.sh /path/to/sprint-analysis.json /path/to/sprint-demo.mp4
./validate.sh
```

## Notes

- experiment; generate sprint reports entirely through AI flows
- outputs could include presentations, summaries, potentially full sprint demo recordings
- broader idea; improve status reporting by making work more granularly reportable
- granular work units could roll up through multiple layers of AI summarization
- potential benefit; easier understanding of where work is, what changed, what matters
- current implementation/direction does not feel right
- likely leave this dormant for now
- revisit if a better reporting/roll-up model emerges
