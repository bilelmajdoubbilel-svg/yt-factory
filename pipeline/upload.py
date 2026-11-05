"""Upload a rendered video to YouTube with the Data API (no extra libraries).

Needs env: YT_CLIENT_ID, YT_CLIENT_SECRET and the channel's refresh token
(env var named in channels/<id>.json -> "youtube_token_secret").

Usage:
  python upload.py --channel money --video out/x.mp4 --script content/.../long.json
                   [--thumb out/x.png] [--srt out/x.srt] [--timeline build/x/timeline.json]
                   [--publish-at 2026-11-06T15:00:00Z] [--privacy private|unlisted|public] [--dry-run]
"""
import argparse
import json
import os
import sys
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com"


def access_token(refresh_token):
    r = requests.post(TOKEN_URL, data={
        "client_id": os.environ["YT_CLIENT_ID"],
        "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def fmt_ts(sec):
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}" if sec < 3600 else f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def description(script, timeline=None):
    lines = [script.get("summary", script["title"]), ""]
    if timeline and script.get("format") != "short":
        chapters = [(0.0, script.get("intro_chapter", "Intro"))]
        for spec, sc in zip(script["scenes"], timeline["scenes"]):
            if spec["type"] == "chapter":
                title = spec["data"]["title"].replace("*", "")
                chapters.append((sc["start"], title))
        if len(chapters) >= 3:
            lines.append("Chapters")
            lines += [f"{fmt_ts(t)} {name}" for t, name in chapters]
            lines.append("")
    lines.append("Sources")
    lines += [f"- {s}" for s in script.get("sources", [])]
    lines += ["", "Narration uses a synthetic (AI) voice. The script is researched from the sources above; "
                  "estimates are labelled on screen."]
    if script.get("format") == "short":
        state = ROOT / "state" / "published.json"
        if script.get("long_video") and state.exists():
            vid = next((x["video_id"] for x in json.loads(state.read_text()) if x["id"] == script["long_video"]), None)
            if vid:
                lines += ["", f"Full video: https://youtu.be/{vid}"]
        lines += ["", "#shorts"]
    return "\n".join(lines)[:4900]


def upload(args):
    channel = json.loads((ROOT / "channels" / f"{args.channel}.json").read_text())
    script = json.loads(Path(args.script).read_text())
    timeline = json.loads(Path(args.timeline).read_text()) if args.timeline else None
    title = script["title"][:100]
    body = {
        "snippet": {
            "title": title,
            "description": description(script, timeline),
            "tags": (script.get("tags") or []) + channel.get("default_tags", []),
            "categoryId": channel.get("category_id", "27"),
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": "private" if args.publish_at else args.privacy,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": bool(script.get("contains_synthetic_media", False)),
        },
    }
    if args.publish_at:
        body["status"]["publishAt"] = args.publish_at
    if args.dry_run:
        print(json.dumps(body, indent=1))
        return None

    token = access_token(os.environ[channel["youtube_token_secret"]])
    h = {"Authorization": f"Bearer {token}"}
    size = Path(args.video).stat().st_size
    r = requests.post(f"{API}/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                      headers={**h, "Content-Type": "application/json; charset=UTF-8",
                               "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
                      data=json.dumps(body), timeout=60)
    r.raise_for_status()
    with open(args.video, "rb") as f:
        r = requests.put(r.headers["Location"], headers={**h, "Content-Type": "video/mp4"}, data=f, timeout=3600)
    r.raise_for_status()
    vid = r.json()["id"]
    print("uploaded", vid)

    if args.thumb and Path(args.thumb).exists():
        with open(args.thumb, "rb") as f:
            t = requests.post(f"{API}/upload/youtube/v3/thumbnails/set?videoId={vid}",
                              headers={**h, "Content-Type": "image/png"}, data=f, timeout=120)
        print("thumbnail", t.status_code, "" if t.ok else t.text[:300])  # needs a phone-verified channel

    if args.srt and Path(args.srt).exists():
        boundary = uuid.uuid4().hex
        meta = json.dumps({"snippet": {"videoId": vid, "language": "en", "name": "English", "isDraft": False}})
        payload = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n"
                   f"--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n").encode() + \
            Path(args.srt).read_bytes() + f"\r\n--{boundary}--".encode()
        c = requests.post(f"{API}/upload/youtube/v3/captions?uploadType=multipart&part=snippet",
                          headers={**h, "Content-Type": f"multipart/related; boundary={boundary}"}, data=payload, timeout=120)
        print("captions", c.status_code, "" if c.ok else c.text[:300])
    return vid


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--script", required=True)
    ap.add_argument("--thumb")
    ap.add_argument("--srt")
    ap.add_argument("--timeline")
    ap.add_argument("--publish-at")
    ap.add_argument("--privacy", default="private")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    v = upload(a)
    if v:
        Path(os.environ.get("GITHUB_OUTPUT", "/dev/null")).open("a").write(f"video_id={v}\n")
    sys.exit(0)
