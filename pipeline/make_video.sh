#!/usr/bin/env bash
# Usage: pipeline/make_video.sh <script.json> [--render]
# Builds build/<id>/ (voice, scenes, captions), lints it, and optionally renders the MP4.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
if [ -z "${HYPERFRAMES_BROWSER_PATH:-}" ] && [ -x /usr/bin/google-chrome ]; then export HYPERFRAMES_BROWSER_PATH=/usr/bin/google-chrome; fi
SCRIPT="$1"; shift || true
ID=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['id'])" "$SCRIPT")
CH=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['channel'])" "$SCRIPT")
B="$HERE/build/$ID"
rm -rf "$B"; mkdir -p "$B"
python3 "$HERE/pipeline/voice.py" "$SCRIPT" "$B"
# a channel with its own look ("look": "<name>" in channels/<id>.json) composes with pipeline/look_<name>.py
LOOK=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('look',''))" "$HERE/channels/$CH.json")
if [ -n "$LOOK" ]; then
  python3 "$HERE/pipeline/look_$LOOK.py" "$SCRIPT" "$B" "$HERE/channels/$CH.json"
else
  python3 "$HERE/pipeline/compose.py" "$SCRIPT" "$B" "$HERE/channels/$CH.json"
fi
cd "$B"
npx --prefix "$HERE" hyperframes check --json > check.json 2>/dev/null || true
python3 "$HERE/pipeline/lint_report.py" check.json
if [[ "${1:-}" == "--render" ]]; then
  mkdir -p "$HERE/out"
  npx --prefix "$HERE" hyperframes render --quality looks --output "$HERE/out/$ID.raw.mp4" --quiet
  # loudness to about -14 LUFS, true peak -1.5 dB (YouTube/Shorts friendly)
  ffmpeg -y -loglevel error -i "$HERE/out/$ID.raw.mp4" -c:v copy -af loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.8:level=false -ar 48000 -c:a aac -b:a 192k "$HERE/out/$ID.mp4"
  rm -f "$HERE/out/$ID.raw.mp4"
  cp captions.srt "$HERE/out/$ID.srt"
  echo "rendered $HERE/out/$ID.mp4"
fi
