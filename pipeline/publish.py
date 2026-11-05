"""Publish what is due for a channel: read content/<channel>/queue.json, render each due item,
make its thumbnail, upload it scheduled for its slot, and log it in state/published.json.

Usage: python publish.py --channel money [--dry-run] [--privacy private] [--only long|short]
Queue items: {"script": path, "kind": "long"|"short", "date": "YYYY-MM-DD"}.
Slots (UTC) come from channels/<id>.json "publish_hour_utc" (default long 15:00, short 18:00).
Items are uploaded one day ahead and scheduled for their slot, so a failed run can retry the next day.
If the queue fell behind (the first unpublished item is in the past), every unpublished date slides
forward by the same number of days, so the spacing (weekly long, Shorts every 2 days) is kept.
If nothing is queued for the next 7 days and GEMINI_API_KEY is set, write.py drafts a new topic.
--check only prints "due=true|false" (for the workflow, to skip installs on quiet days).
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "published.json"


def run(*cmd):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, cwd=ROOT)


LOOKAHEAD = 1  # days: upload this far ahead of the publish date


def slot(cfg, kind, day):
    """Publish time for this item; if its slot is already (nearly) past, the same hour the next day."""
    hour = cfg.get("publish_hour_utc", {}).get(kind, 15 if kind == "long" else 18)
    t = dt.datetime.combine(day, dt.time(hour, 0), tzinfo=dt.timezone.utc)
    now = dt.datetime.now(dt.timezone.utc)
    while t < now + dt.timedelta(minutes=45):
        t += dt.timedelta(days=1)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def script_id(q):
    return json.loads((ROOT / q["script"]).read_text())["id"]


def slide(queue, done, today, qpath):
    """Keep the plan's spacing when the robot started late or missed days."""
    pending = [q for q in queue if script_id(q) not in done]
    if not pending:
        return
    first = min(dt.date.fromisoformat(q["date"]) for q in pending)
    lag = (today - first).days
    if lag <= 0:
        return
    for q in pending:
        q["date"] = (dt.date.fromisoformat(q["date"]) + dt.timedelta(days=lag)).isoformat()
    qpath.write_text(json.dumps(queue, indent=1) + "\n")
    print(f"queue was {lag} day(s) behind: moved {len(pending)} unpublished items forward")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--privacy", default=None, help="upload now with this privacy instead of scheduling")
    ap.add_argument("--only", choices=["long", "short"])
    ap.add_argument("--check", action="store_true", help="print due=true/false and exit")
    a = ap.parse_args()
    cfg = json.loads((ROOT / "channels" / f"{a.channel}.json").read_text())
    qpath = ROOT / "content" / a.channel / "queue.json"
    queue = json.loads(qpath.read_text()) if qpath.exists() else []
    state = json.loads(STATE.read_text()) if STATE.exists() else []
    done = {x["id"] for x in state}
    today = dt.datetime.now(dt.timezone.utc).date()
    horizon = today + dt.timedelta(days=LOOKAHEAD)

    if a.check:
        pend = [q for q in queue if script_id(q) not in done]
        soon = [q for q in pend if dt.date.fromisoformat(q["date"]) <= horizon]
        week = [q for q in pend if dt.date.fromisoformat(q["date"]) <= today + dt.timedelta(days=7)]
        need_writer = not week and bool(os.environ.get("GEMINI_API_KEY"))
        print("due=" + ("true" if soon or need_writer else "false"))
        return

    if not a.dry_run:
        slide(queue, done, today, qpath)

    upcoming = [q for q in queue if dt.date.fromisoformat(q["date"]) <= today + dt.timedelta(days=7)
                and json.loads((ROOT / q["script"]).read_text())["id"] not in done]
    if not upcoming and os.environ.get("GEMINI_API_KEY"):
        run(sys.executable, "pipeline/write.py", "--channel", a.channel)
        queue = json.loads(qpath.read_text())

    due = [q for q in queue if dt.date.fromisoformat(q["date"]) <= horizon and (not a.only or q["kind"] == a.only)]
    due = [q for q in due if json.loads((ROOT / q["script"]).read_text())["id"] not in done]
    if not due:
        print("nothing due by", horizon)
        return
    for q in due[:2]:
        script = ROOT / q["script"]
        sid = json.loads(script.read_text())["id"]
        run("bash", "pipeline/make_video.sh", script, "--render")
        out = ROOT / "out"
        up = [sys.executable, "pipeline/upload.py", "--channel", a.channel, "--video", out / f"{sid}.mp4", "--script", script,
              "--srt", out / f"{sid}.srt", "--timeline", ROOT / "build" / sid / "timeline.json"]
        if q["kind"] == "long":
            run(sys.executable, "pipeline/thumbnail.py", script, ROOT / "channels" / f"{a.channel}.json", out / f"{sid}.png")
            up += ["--thumb", out / f"{sid}.png"]
        when = None if a.privacy else slot(cfg, q["kind"], dt.date.fromisoformat(q["date"]))
        up += ["--publish-at", when] if when else ["--privacy", a.privacy or "public"]
        if a.dry_run:
            up.append("--dry-run")
        res = subprocess.run([str(c) for c in up], cwd=ROOT, capture_output=True, text=True)
        print(res.stdout, res.stderr)
        res.check_returncode()
        vid = next((ln.split()[1] for ln in res.stdout.splitlines() if ln.startswith("uploaded ")), None)
        if vid:
            state.append({"id": sid, "channel": a.channel, "kind": q["kind"], "video_id": vid, "date": q["date"],
                          "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
            STATE.parent.mkdir(exist_ok=True)
            STATE.write_text(json.dumps(state, indent=1))
            print("logged", sid, vid)


if __name__ == "__main__":
    main()
