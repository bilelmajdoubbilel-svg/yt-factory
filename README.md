# yt-factory

Free, automated pipeline for animated explainer channels: a researched script becomes a cinematic
video with a recurring host character, moving camera, depth of field, a music bed and sound effects,
then uploads itself to YouTube on schedule.

```
content/<channel>/queue.json         what publishes when (long: Tue + Fri 3 pm ET, Shorts: daily 1 pm ET; see channels/money.json)
content/<channel>/<topic>/*.json     scripts: scenes with narration, world, host acting, data
        │
pipeline/voice.py      Kokoro TTS (free, offline) -> voice.wav + word timings
pipeline/compose.py    -> cine.py (style "cinematic"): worlds + host + camera + transitions + fx + audio mix
pipeline/cinema.py     host rig (SVG), props        assets/cinema.js   camera, poses, faces, walk, grain
pipeline/worlds.py     street, foodcourt, aisle, studio, cinema, airport (multiplane layers, live motion)
HyperFrames render     HTML -> MP4, then loudness to -14 LUFS
pipeline/thumbnail.py  brand thumbnail: Tag + receipt with one number and <=3 words
pipeline/upload.py     YouTube Data API: scheduled publish, thumbnail, captions, chapters, sources
pipeline/publish.py    runs daily from .github/workflows/publish.yml, publishes whatever is due (only channels with "ready": true)
pipeline/inbox.py      first step of the daily run: applies checked update bundles from the Google Drive inbox
pipeline/check_tokens.py  weekly (.github/workflows/check-tokens.yml): each token works and controls the right channel
pipeline/write.py      backup writer (Gemini free tier) when the Price Logic queue runs dry; Claude is the main writer
```

Claude's scheduled sessions (weekly run every Monday + one-off design sessions) follow `RUNBOOK.md`.

## Channels

| id | channel | niche | host |
|----|---------|-------|------|
| `money` | channel 1 "Price Logic" | why things cost what they cost, how companies make money | Tag, a living price tag (brand v3) |
| `history` | channel 2 "Map Minutes" (@MapMinutes19) | US and Canada geography and history on maps; long Wed 3 pm ET, Shorts 10 am ET | a living map pin (look in progress, "ready": false) |
| `hidden` | channel 3 "Hidden Systems" (@HiddenSystems19) | how water, power, trash, mail and 911 work; long Sun 3 pm ET, Shorts 8 pm ET | a living water drop (look in progress, "ready": false) |

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
`YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN_1` (Price Logic), `YT_REFRESH_TOKEN_2` (Map Minutes),
`YT_REFRESH_TOKEN_3` (Hidden Systems), `GEMINI_API_KEY`, and `GDRIVE_REFRESH_TOKEN` (same OAuth client, scope
`https://www.googleapis.com/auth/drive.readonly`, Google Drive API enabled in the Cloud project) for the Drive inbox.
Check them any time: Actions → check-tokens → Run workflow.

Test: Actions → publish → Run workflow → tick **test**: it renders the next Short and uploads it private with a
[TEST] title. After that the robot runs every day at 12:17 UTC and uploads what `queue.json` says is due
(one day ahead, scheduled for its slot).
