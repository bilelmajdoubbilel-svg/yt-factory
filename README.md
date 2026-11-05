# yt-factory

Free, automated pipeline for animated explainer channels: a researched script becomes a cinematic
video with a recurring host character, moving camera, depth of field, a music bed and sound effects,
then uploads itself to YouTube on schedule.

```
content/<channel>/queue.json         what publishes when (long: Tue + Fri 15:00 UTC, Shorts: daily 18:00 UTC)
content/<channel>/<topic>/*.json     scripts: scenes with narration, world, host acting, data
        │
pipeline/voice.py      Kokoro TTS (free, offline) -> voice.wav + word timings
pipeline/compose.py    -> cine.py (style "cinematic"): worlds + host + camera + transitions + fx + audio mix
pipeline/cinema.py     host rig (SVG), props        assets/cinema.js   camera, poses, faces, walk, grain
pipeline/worlds.py     street, foodcourt, aisle, studio, cinema, airport (multiplane layers, live motion)
HyperFrames render     HTML -> MP4, then loudness to -14 LUFS
pipeline/thumbnail.py  brand thumbnail: Tag + receipt with one number and <=3 words
pipeline/upload.py     YouTube Data API: scheduled publish, thumbnail, captions, chapters, sources
pipeline/publish.py    runs daily from .github/workflows/publish.yml, publishes whatever is due
pipeline/write.py      backup writer (Gemini free tier) when the queue runs dry; Claude is the main writer
```

## Channels

| id | channel | niche | host |
|----|---------|-------|------|
| `money` | channel 1 "Price Logic" | why things cost what they cost, how companies make money | Tag, a living price tag (brand v3) |
| `history` | channel 2 (to create) | history on animated maps and timelines | olive jacket, explorer hat |
| `scale` | channel 3 (to create) | science and space by scale | teal jacket, goggles |

## Audio

Music: `music/shared/` (15 CC0 tracks). Effects: `assets/sfx-cc0/` (113 CC0 sounds) and `assets/sfx/`
(Pixabay licence). All free for monetized videos, no attribution needed; licences in each folder.
The music is ducked under the voice automatically; the master is normalised to -14 LUFS.

## Run locally

```bash
npm ci && pip install -r requirements.txt
mkdir -p models && cd models
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
cd ..
bash pipeline/make_video.sh content/money/costco-hotdog/costco-s1-hotdog.json --render
```

Render speed (2 cores, backgrounds baked): a 25 s Short takes ~3 min, a 4-minute video ~30-40 min.
The robot uploads each item one day before its publish date, scheduled for its slot; if it starts late,
the whole queue slides forward so the spacing stays the same.

## GitHub setup (once)

Settings → Secrets and variables → Actions → New repository secret:
`YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN_1`, `GEMINI_API_KEY`
(later `YT_REFRESH_TOKEN_2`, `YT_REFRESH_TOKEN_3` for the new channels).

Test: Actions → publish → Run workflow → tick **test**: it renders the next Short and uploads it private with a
[TEST] title. After that the robot runs every day at 12:17 UTC and uploads what `queue.json` says is due
(one day ahead, scheduled for its slot).
