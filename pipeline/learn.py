"""Learning loop: public views at 48 h and 7 days against each channel's own median.

Reads state/published.json and the robot's snapshots in state/views-<channel>.json (pipeline/views.py), plus
optional extra snapshots a session took itself (--extra file.json: [{"video_id", "at", "views"}], e.g. from vidIQ).
Prints, per channel and format, each video's views at 48 h and 7 days, its multiple of the median, and a verdict:
  WIN  = 2x the median or more    LOW = a quarter of the median or less    young = not 48 h old yet
  WIN* / LOW* = no snapshot near 48 h, so current views against the current-views median (videos 48 h+ old)
Medians compare a channel with itself (Shorts with Shorts, longs with longs), never with a universal number.
Ends with the Price Logic watch: Price Logic's Shorts median at 48 h against the other two channels.

  python pipeline/learn.py [--extra counts.json] [--json out.json]
"""
import argparse
import datetime as dt
import json
import statistics
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
MARKS = {"48h": 48, "7d": 168}


def parse(ts):
    t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def publish_time(cfg, kind, day, published_at=None):
    if published_at:
        return parse(published_at)
    loc = cfg.get("publish_local") or {}
    hh, mm = map(int, loc.get(kind, "15:00" if kind == "long" else "13:00").split(":"))
    t = dt.datetime.combine(dt.date.fromisoformat(day), dt.time(hh, mm), tzinfo=ZoneInfo(loc.get("tz", "America/Toronto")))
    return t.astimezone(dt.timezone.utc)


def at_age(snaps, start, hours):
    """Views at `hours` after `start`: linear between the snapshots around it; a snapshot up to 24 h later
    stands in when there is none before (marked approximate). None if not measured yet."""
    pts = sorted(((parse(a) - start).total_seconds() / 3600, v) for a, v in snaps)
    pts = [(h, v) for h, v in pts if h >= 0]
    before = [p for p in pts if p[0] <= hours]
    after = [p for p in pts if p[0] >= hours]
    if before and after:
        (h0, v0), (h1, v1) = before[-1], after[0]
        return (round(v0 + (v1 - v0) * (hours - h0) / (h1 - h0)) if h1 > h0 else v0), False
    if after and after[0][0] <= hours + 24:
        return after[0][1], True
    return None, False


def load(extra=None):
    pub = json.loads((STATE / "published.json").read_text())
    snaps, meta = {}, {}
    for f in STATE.glob("views-*.json"):
        for vid, e in json.loads(f.read_text()).items():
            snaps.setdefault(vid, []).extend((s[0], s[1]) for s in e.get("snaps", []))
            if e.get("published_at"):
                meta[vid] = e["published_at"]
    for x in (json.loads(Path(extra).read_text()) if extra else []):
        snaps.setdefault(x["video_id"], []).append((x["at"], int(x["views"])))
        if x.get("published_at"):
            meta[x["video_id"]] = x["published_at"]
    return pub, snaps, meta


def report(pub, snaps, meta, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    cfgs, rows = {}, []
    for p in pub:
        ch = p["channel"]
        cfg = cfgs.setdefault(ch, json.loads((ROOT / "channels" / f"{ch}.json").read_text()))
        start = publish_time(cfg, p["kind"], p["date"], meta.get(p.get("video_id")))
        if start > now:
            continue
        s = snaps.get(p.get("video_id"), [])
        r = {"channel": ch, "kind": p["kind"], "id": p["id"], "video_id": p.get("video_id"),
             "age_h": round((now - start).total_seconds() / 3600), "latest": max((v for _, v in s), default=None)}
        for k, h in MARKS.items():
            r[k], r[k + "_approx"] = at_age(s, start, h)
        rows.append(r)
    groups = {}
    for r in rows:
        groups.setdefault((r["channel"], r["kind"]), []).append(r)
    med = {}
    for key, rs in groups.items():
        vals = [r["48h"] for r in rs if r["48h"] is not None]
        med[key] = statistics.median(vals) if vals else None
        old_now = [r["latest"] for r in rs if r["age_h"] >= 48 and r["latest"] is not None]
        mnow = statistics.median(old_now) if old_now else None
        med[key + ("now",)] = mnow
        for r in rs:
            m, v = med[key], r["48h"]
            r["median_48h"] = m
            if v is None and r["age_h"] >= 48 and r["latest"] is not None and mnow:
                # no snapshot around 48 h (e.g. before the robot took snapshots): judge current views
                # against the current-views median of the group's videos older than 48 h, marked *
                r["x_median"] = round(r["latest"] / mnow, 2)
                r["verdict"] = ("WIN*" if r["latest"] >= 2 * mnow else "LOW*" if r["latest"] <= mnow / 4 else "*")
            elif v is None:
                r["verdict"] = "young" if r["age_h"] < 48 else "no data"
            elif not m:
                r["verdict"] = ""
            else:
                r["x_median"] = round(v / m, 2)
                r["verdict"] = "WIN" if v >= 2 * m else "LOW" if v <= m / 4 else ""
    return rows, med


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra", help="extra snapshots: [{video_id, at, views}] (e.g. vidIQ counts)")
    ap.add_argument("--json", help="also write the rows to this file (keep it out of the repo)")
    a = ap.parse_args()
    rows, med = report(*load(a.extra))
    for (ch, kind) in sorted({(r["channel"], r["kind"]) for r in rows}):
        m = med.get((ch, kind))
        mn = med.get((ch, kind, "now"))
        print(f"\n{ch} {kind}s  (median at 48 h: {m if m is not None else 'n/a'}; current-views median, 48 h+: {mn if mn is not None else 'n/a'})")
        print(f"  {'id':28} {'age':>5} {'48h':>7} {'7d':>7} {'now':>7}  x  verdict")
        for r in sorted((r for r in rows if r["channel"] == ch and r["kind"] == kind), key=lambda r: -r["age_h"]):
            f = lambda k: "-" if r[k] is None else f"{r[k]}{'~' if r.get(k + '_approx') else ''}"
            print(f"  {r['id']:28} {r['age_h']:>4}h {f('48h'):>7} {f('7d'):>7} {str(r['latest'] if r['latest'] is not None else '-'):>7}"
                  f"  {r.get('x_median', ''):>4} {r['verdict']}")
    pl, others = med.get(("money", "short")), [med.get((c, "short")) for c in ("history", "hidden")]
    others = [o for o in others if o]
    if pl is not None and others:
        o = statistics.median(others)
        n = sum(1 for r in rows if r["channel"] == "money" and r["kind"] == "short" and r["48h"] is not None)
        print(f"\nPrice Logic watch: Shorts median at 48 h {pl} vs the other channels' {o} "
              f"({'under' if pl < o / 10 else 'at or above'} a tenth; {n} Price Logic Shorts measured)")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
