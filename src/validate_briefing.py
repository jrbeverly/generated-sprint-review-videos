import json
from pathlib import Path

root = Path("output")
manifest = json.loads((root / "manifest.json").read_text())
for name in ("demos", "audio", "slides", "segments"):
    assert (root / name).is_dir(), name
paths = list(manifest["artifacts"].values())
for beat in manifest["beats"]:
    paths.extend(beat.get("artifacts", {}).values())
    if beat["include_in"]["video"]:
        paths.append(beat["segment"])
        assert beat["mp4_offset_seconds"] is not None
for name in paths:
    path = Path(name)
    assert path.is_file() and path.stat().st_size > 0, name
    assert path.resolve().is_relative_to(root.resolve()), name
assert len(list((root / "demos").glob("*.mp4"))) == 2
assert len(list((root / "demos").glob("*-poster.png"))) == 2
log = Path("work/briefing.log").read_text()
assert log.count("  extracted ") == 2
assert "Completed briefing:" in log
print("Briefing: all manifest artifact paths resolve; two demos extracted once.")
