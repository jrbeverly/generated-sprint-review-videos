#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

rm -rf work output
./.venv/bin/python src/make_masters.py
mkdir -p work/narration-hf-home
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME="$PWD/work/narration-hf-home"
export http_proxy=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9
export HTTP_PROXY=$http_proxy HTTPS_PROXY=$https_proxy
export all_proxy=$http_proxy ALL_PROXY=$http_proxy no_proxy= NO_PROXY=
for invalid in fixtures/plan-cases/invalid-*.json; do
  if ./briefing.sh "$invalid" input/sprint-demo.mp4 > work/invalid-briefing.log 2>&1; then
    echo "Invalid plan unexpectedly completed: $invalid" >&2
    exit 1
  fi
  test ! -e output/manifest.json
  test ! -e output/sprint-briefing.mp4
  rm -rf output
done
if PLAYWRIGHT_BROWSERS_PATH="$PWD/work/missing-browser" \
    ./briefing.sh fixtures/sprint-analysis.json input/sprint-demo.mp4 > work/failed-stage.log 2>&1; then
  echo "Missing browser unexpectedly completed" >&2
  exit 1
fi
test -s output/sprint-briefing.pptx
test ! -e output/sprint-briefing.mp4
./.venv/bin/python -c 'import json; assert "mp4" not in json.load(open("output/manifest.json"))'
if grep -q 'Completed briefing:' work/failed-stage.log; then
  echo "Failed stage reported completion" >&2
  exit 1
fi
rm -rf output
./briefing.sh fixtures/sprint-analysis.json input/sprint-demo.mp4 | tee work/briefing.log
./.venv/bin/python src/validate_briefing.py
if ./briefing.sh fixtures/sprint-analysis.json input/sprint-demo.mp4 > work/reused-output.log 2>&1; then
  echo "Existing output unexpectedly accepted" >&2
  exit 1
fi

# The silent-source fixture is separate from the two-demo briefing.
./.venv/bin/python src/extract_clips.py silent-demo
./.venv/bin/python src/validate.py
./.venv/bin/python src/validate_plan.py
./.venv/bin/python src/validate_narration.py
./.venv/bin/python src/validate_static.py
./.venv/bin/python src/validate_composition.py

