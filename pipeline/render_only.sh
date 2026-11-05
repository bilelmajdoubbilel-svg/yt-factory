#!/usr/bin/env bash
# Render an already-composed build folder and master the loudness.
# Usage: pipeline/render_only.sh <id>
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ID="$1"
if [ -z "${HYPERFRAMES_BROWSER_PATH:-}" ] && [ -x /usr/bin/google-chrome ]; then export HYPERFRAMES_BROWSER_PATH=/usr/bin/google-chrome; fi
cd "$HERE/build/$ID"
mkdir -p "$HERE/out"
npx --prefix "$HERE" hyperframes render --quality looks --output "$HERE/out/$ID.raw.mp4" --quiet
ffmpeg -y -loglevel error -i "$HERE/out/$ID.raw.mp4" -c:v copy -af loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.8:level=false -ar 48000 -c:a aac -b:a 192k "$HERE/out/$ID.mp4"
rm -f "$HERE/out/$ID.raw.mp4"
cp captions.srt "$HERE/out/$ID.srt"
echo "done $ID"
