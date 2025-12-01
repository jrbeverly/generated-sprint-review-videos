#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# 1. Experiment-local tooling (npm pins: ffmpeg/ffprobe static, pptxgenjs,
#    playwright, the Roboto font; venv pins: Pillow, the #429 Kokoro stack,
#    pypdf). Everything stays inside this directory. This host has no system
#    ensurepip, so bootstrap pip into the venv when it is missing.
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv 2>/dev/null || python3 -m venv --without-pip .venv
fi
if ! ./.venv/bin/python -m pip --version >/dev/null 2>&1; then
  curl -sS https://bootstrap.pypa.io/get-pip.py | ./.venv/bin/python
fi
if [ ! -x node_modules/ffmpeg-static/ffmpeg ] || [ ! -d node_modules/pptxgenjs ] \
    || [ ! -d node_modules/playwright ] || [ ! -d node_modules/@fontsource/roboto ]; then
  npm install --no-fund --no-audit
fi
if ! ./.venv/bin/python -c "import PIL, kokoro, pypdf" 2>/dev/null; then
  ./.venv/bin/pip install --quiet -r requirements.txt
fi

# 1c. Playwright browser: the pinned playwright version downloads its own
#     pinned Chromium build into experiment-local assets/browsers (gitignored).
#     PLAYWRIGHT_BROWSERS_PATH keeps it inside this directory at install and
#     render time. Chromium's OS-level runtime libraries (libnss3 etc.) are a
#     host prerequisite, like Node and Python themselves; see the README.
export PLAYWRIGHT_BROWSERS_PATH="$PWD/assets/browsers"
if [ ! -d "$PLAYWRIGHT_BROWSERS_PATH" ]; then
  npx playwright install chromium
fi
if ! ./.venv/bin/python -c "import spacy; spacy.util.is_package('en_core_web_sm') or exit(1)" 2>/dev/null; then
  ./.venv/bin/python -m spacy download en_core_web_sm
fi

# 1b. Kokoro model/voice assets: one pinned English voice (af_heart) plus the
#     model and config from hexgrad/Kokoro-82M, sha256-pinned here and kept
#     experiment-local under assets/ (gitignored). Downloaded once; the
#     narration stage then runs with network disabled.
fetch_asset() {
  local url=$1 out=$2 sha=$3
  if [ ! -f "$out" ]; then
    echo "downloading $out"
    curl -sSL -f -o "$out.part" "$url"
    printf '%s  %s\n' "$sha" "$out.part" | sha256sum -c --status -
    mv "$out.part" "$out"
  else
    printf '%s  %s\n' "$sha" "$out" | sha256sum -c --status - \
      || { echo "sha256 mismatch for $out"; exit 1; }
  fi
}
mkdir -p assets/kokoro/voices
fetch_asset "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/config.json" \
  assets/kokoro/config.json \
  5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f
fetch_asset "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/kokoro-v1_0.pth" \
  assets/kokoro/kokoro-v1_0.pth \
  496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4
fetch_asset "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/voices/af_heart.pt" \
  assets/kokoro/voices/af_heart.pt \
  0ab5709b8ffab19bfd849cd11d98f75b60af7733253ad0d67b12382a102cb4ff

