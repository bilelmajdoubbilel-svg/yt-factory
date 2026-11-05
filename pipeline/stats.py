"""Weekly numbers for every channel, so Claude's Monday run can learn from results.

Public numbers (subscribers, views, likes, comments) come from the YouTube Data API with the upload tokens.
Private numbers (watch time, average % viewed, subscribers gained, the audience-retention curve of each
video, watch hours over 365 days) come from the YouTube Analytics API and need tokens made with the extra
scope https://www.googleapis.com/auth/yt-analytics.readonly; without it they are skipped with a note.

Private numbers never go into the public repo: each channel's report replaces the content of its own
file in Google Drive (config/stats.json), written by the service account (GDRIVE_SA_JSON) which the owner
shared that folder with as Editor. Each report keeps a weekly history of the channel totals.

Usage: python pipeline/stats.py [--channel money] [--local out/]   (--local: write files here, not Drive)
Env: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN_1/2/3, GDRIVE_SA_JSON.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import drive_auth  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = "https://www.googleapis.com/youtube/v3"
ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"


def yt_token(refresh):
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": refresh, "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def iso_seconds(d):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return None
    days, h, mi, s = (int(x or 0) for x in m.groups())
    return days * 86400 + h * 3600 + mi * 60 + s


def analytics(h, **params):
    """One Analytics API report as a list of row dicts; raises PermissionError when the scope is missing."""
    r = requests.get(ANALYTICS, headers=h, timeout=60, params={"ids": "channel==MINE", **params})
    if r.status_code in (401, 403):
        raise PermissionError(r.text[:200])
    r.raise_for_status()
    js = r.json()
    cols = [c["name"] for c in js.get("columnHeaders", [])]
    return [dict(zip(cols, row)) for row in js.get("rows", [])]


def channel_report(cfg, published, today):
    h = {"Authorization": f"Bearer {yt_token(os.environ[cfg['youtube_token_secret']])}"}
    ch = requests.get(f"{DATA}/channels", headers=h, timeout=30,
                      params={"part": "statistics,snippet", "id": cfg["youtube_channel_id"]}).json()["items"][0]
    st = ch["statistics"]
    out = {"channel": cfg["id"], "name": cfg.get("name"), "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "subscribers": int(st.get("subscriberCount", 0)), "views": int(st.get("viewCount", 0)),
           "videos": int(st.get("videoCount", 0)), "analytics": "ok", "items": []}
    mine = [p for p in published if p.get("channel") == cfg["id"] and p.get("video_id")]
    by_id = {p["video_id"]: p for p in mine}
    ids = list(by_id)
    for i in range(0, len(ids), 50):
        r = requests.get(f"{DATA}/videos", headers=h, timeout=30,
                         params={"part": "statistics,snippet,contentDetails", "id": ",".join(ids[i:i + 50])}).json()
        for v in r.get("items", []):
            p, s = by_id[v["id"]], v.get("statistics", {})
            out["items"].append({"video_id": v["id"], "script_id": p["id"], "kind": p["kind"], "date": p["date"],
                                 "title": v["snippet"]["title"], "seconds": iso_seconds(v["contentDetails"].get("duration")),
                                 "views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                                 "comments": int(s.get("commentCount", 0))})
    start = cfg.get("analytics_start", "2026-11-01")
    end = today.isoformat()
    try:
        tot = analytics(h, startDate=(today - dt.timedelta(days=365)).isoformat(), endDate=end,
                        metrics="views,estimatedMinutesWatched,subscribersGained,subscribersLost")
        if tot:
            out["watch_hours_365d"] = round(tot[0]["estimatedMinutesWatched"] / 60, 1)
            out["subscribers_net_365d"] = tot[0]["subscribersGained"] - tot[0]["subscribersLost"]
        if ids:
            rows = analytics(h, startDate=start, endDate=end, dimensions="video", sort="-views", maxResults=200,
                             filters="video==" + ",".join(ids[:200]),
                             metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained")
            per = {r["video"]: r for r in rows}
            for it in out["items"]:
                r = per.get(it["video_id"])
                if r:
                    it.update(minutes_watched=r["estimatedMinutesWatched"], avg_view_seconds=r["averageViewDuration"],
                              avg_view_pct=r["averageViewPercentage"], subs_gained=r["subscribersGained"])
                curve = analytics(h, startDate=start, endDate=end, dimensions="elapsedVideoTimeRatio",
                                  filters=f"video=={it['video_id']}", metrics="audienceWatchRatio,relativeRetentionPerformance")
                if curve:
                    it["retention"] = [[c["elapsedVideoTimeRatio"], round(c["audienceWatchRatio"], 4),
                                        round(c["relativeRetentionPerformance"], 3)] for c in curve]
                    secs = it.get("seconds") or 0
                    if secs:  # share of starting viewers still watching ~30 s in (3 s for Shorts)
                        mark = (3 if it["kind"] == "short" else 30) / secs
                        near = min(it["retention"], key=lambda c: abs(c[0] - mark))
                        it["hook_hold"] = near[1]
    except PermissionError:
        out["analytics"] = "missing: the token needs scope yt-analytics.readonly (and the YouTube Analytics API enabled)"
    return out


def save(report, file_id, local):
    if local:
        Path(local).mkdir(parents=True, exist_ok=True)
        Path(local, f"stats-{report['channel']}.json").write_text(json.dumps(report, indent=1))
        return "local"
    tok = drive_auth.access_token(drive_auth.WRITE_SCOPE)
    h = {"Authorization": f"Bearer {tok}"}
    old = requests.get(f"https://www.googleapis.com/drive/v3/files/{file_id}", params={"alt": "media"}, headers=h, timeout=60)
    history = []
    if old.ok:
        try:
            history = old.json().get("history", [])
        except ValueError:
            pass
    snap = {k: report.get(k) for k in ("generated_at", "subscribers", "views", "videos", "watch_hours_365d")}
    report["history"] = (history + [snap])[-104:]
    r = requests.patch(f"https://www.googleapis.com/upload/drive/v3/files/{file_id}", params={"uploadType": "media"},
                       headers={**h, "Content-Type": "application/json"}, data=json.dumps(report, indent=1), timeout=60)
    r.raise_for_status()
    return "drive"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel")
    ap.add_argument("--local", help="write reports to this folder instead of Drive")
    a = ap.parse_args()
    files = json.loads((ROOT / "config" / "stats.json").read_text())["files"]
    sp = ROOT / "state" / "published.json"
    published = json.loads(sp.read_text()) if sp.exists() else []
    today = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)
    lines, bad = [], 0
    for f in sorted((ROOT / "channels").glob("*.json")):
        cfg = json.loads(f.read_text())
        if a.channel and cfg["id"] != a.channel:
            continue
        if not cfg.get("youtube_channel_id") or not os.environ.get(cfg.get("youtube_token_secret", ""), ""):
            continue
        try:
            rep = channel_report(cfg, published, today)
            where = save(rep, files.get(cfg["id"]), a.local)
            # public numbers only in the log (the repo and its logs are public)
            lines.append(f"OK    {cfg['name']}: {rep['subscribers']} subscribers, {rep['views']} views, "
                         f"{len(rep['items'])} tracked videos, analytics {rep['analytics'].split(':')[0]}, saved to {where}")
        except Exception as e:  # noqa: BLE001
            bad += 1
            lines.append(f"FAIL  {cfg.get('name', f.stem)}: {str(e)[:200]}")
    report = "\n".join(lines) or "no channel with a token"
    print(report)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a").write("### Weekly stats (public numbers)\n```\n" + report + "\n```\n")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
