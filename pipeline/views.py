"""Public view snapshots for the learning loop (read by pipeline/learn.py).

After each real publish run, publish.py calls snapshot(<channel>): the public views, likes and comments of the
channel's videos from the last 30 days are appended to state/views-<channel>.json (one file per channel, so the
parallel channel jobs never edit the same file). Public numbers only: watch time and retention stay in the
private Drive stats files. A failure here never fails a publish run.

  python pipeline/views.py --channel money      # take one snapshot by hand (needs the robot's env)
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
DATA = "https://www.googleapis.com/youtube/v3"
KEEP_DAYS = 30


def path(channel):
    return STATE / f"views-{channel}.json"


def _fetch(cfg, ids):
    """{video_id: (views, likes, comments, publishedAt)} from the Data API with the channel's own token."""
    import requests
    from upload import access_token
    h = {"Authorization": f"Bearer {access_token(os.environ[cfg['youtube_token_secret']])}"}
    out = {}
    for i in range(0, len(ids), 50):
        r = requests.get(f"{DATA}/videos", headers=h, timeout=30,
                         params={"part": "statistics,snippet", "id": ",".join(ids[i:i + 50])})
        r.raise_for_status()
        for v in r.json().get("items", []):
            s = v.get("statistics", {})
            out[v["id"]] = (int(s.get("viewCount", 0)), int(s.get("likeCount", 0)), int(s.get("commentCount", 0)),
                            v.get("snippet", {}).get("publishedAt"))
    return out


def snapshot(channel, fetch=None, now=None):
    cfg = json.loads((ROOT / "channels" / f"{channel}.json").read_text())
    if not cfg.get("ready"):
        return 0
    now = now or dt.datetime.now(dt.timezone.utc)
    pub = json.loads((STATE / "published.json").read_text()) if (STATE / "published.json").exists() else []
    recent = {p["video_id"]: p for p in pub if p.get("channel") == channel and p.get("video_id")
              and dt.date.fromisoformat(p["date"]) <= now.date()
              and (now.date() - dt.date.fromisoformat(p["date"])).days <= KEEP_DAYS}
    if not recent:
        return 0
    got = (fetch or (lambda ids: _fetch(cfg, ids)))(sorted(recent))
    f = path(channel)
    book = json.loads(f.read_text()) if f.exists() else {}
    at = now.isoformat(timespec="minutes")
    for vid, (views, likes, comments, published_at) in got.items():
        p = recent[vid]
        e = book.setdefault(vid, {"id": p["id"], "kind": p["kind"], "date": p["date"], "snaps": []})
        if published_at:
            e["published_at"] = published_at
        e["snaps"].append([at, views, likes, comments])
    STATE.mkdir(exist_ok=True)
    f.write_text(json.dumps(book, indent=1))
    return len(got)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    print("snapshots:", snapshot(ap.parse_args().channel))
