#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 sprint-analysis.json sprint-demo.mp4" >&2
  exit 1
fi
analysis=$(realpath "$1")
master=$(realpath "$2")
cd "$(dirname "$0")"
if [ -e output ]; then
  echo "output/ already exists; move it aside before starting a fresh briefing." >&2
  exit 1
fi
mkdir output
trap 'echo "Briefing failed; output/ contains incomplete artifacts." >&2' ERR
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
./.venv/bin/python src/build_plan.py "$analysis" output "$master"
node src/make_pptx.mjs
node src/make_static.mjs
./.venv/bin/python src/make_narration.py
./.venv/bin/python src/make_composition.py
echo "Completed briefing: output/sprint-briefing.{pptx,pdf,mp4}"
