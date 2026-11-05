"""Write the next script with Gemini (free tier) when the queue is empty.

Primary path: Claude researches and writes scripts into content/<channel>/<slug>/{long,short}.json.
This is the fallback so the channel never stalls. Output is validated before it is used.

Env: GEMINI_API_KEY, optional GEMINI_MODEL (tried first, then gemini-2.5-flash, then gemini-flash-latest).
Every model is called WITH Google Search grounding; if none answers, the script fails (a red run that emails
the owner) rather than writing numbers it cannot source.
Usage: python write.py --channel money
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from compose import TEMPLATES  # noqa: E402

REQUIRED = {
    "chapter": ["num", "title"], "counter": ["label"], "compare": ["items"], "bars": ["items"],
    "share": ["pct"], "dots": ["n", "big", "label"], "statement": ["lines"], "quote": ["quote", "who"],
    "flow": ["steps"], "years": ["from", "to", "price"], "lines": ["series"], "cards": ["cards"],
    "pricetag": ["price"], "end": ["lines"], "cta": ["cue"], "shot": [],
}
WORLD_BY_TYPE = {"statement": ["street", "foodcourt"], "end": ["street"], "cta": ["street"], "quote": ["stage"],
                 "pricetag": ["foodcourt"], "flow": ["stage", "foodcourt"]}


def cinematize(s):
    """Give every scene a world (the stage for data, real places for words) and mark the style."""
    s["style"] = "cinematic"
    n = 0
    for sc in s["scenes"]:
        if "world" not in sc:
            opts = WORLD_BY_TYPE.get(sc["type"], ["stage"])
            sc["world"] = opts[n % len(opts)]
            n += 1
    return s


DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def queue_add(channel, items):
    """Append scripts to content/<channel>/queue.json: the long video on the channel's next free long day
    (channels/<id>.json schedule.long_days), Shorts one a day after it."""
    import datetime as dt
    cfg = json.loads((ROOT / "channels" / f"{channel}.json").read_text())
    long_days = {DAYS.index(x) for x in cfg.get("schedule", {}).get("long_days", ["Thu"])}
    qp = ROOT / "content" / channel / "queue.json"
    q = json.loads(qp.read_text()) if qp.exists() else []
    today = dt.date.today()
    last_long = max([dt.date.fromisoformat(x["date"]) for x in q if x["kind"] == "long"] or [today])
    last_short = max([dt.date.fromisoformat(x["date"]) for x in q if x["kind"] == "short"] or [today])
    d = last_long + dt.timedelta(days=1)
    while d.weekday() not in long_days or d <= today:
        d += dt.timedelta(days=1)
    sd = max(last_short + dt.timedelta(days=1), d + dt.timedelta(days=1))
    for path, kind in items:
        if kind == "long":
            q.append({"script": path, "kind": "long", "date": d.isoformat()})
        else:
            q.append({"script": path, "kind": "short", "date": sd.isoformat()})
            sd += dt.timedelta(days=1)
    q.sort(key=lambda x: x["date"])
    qp.write_text(json.dumps(q, indent=1) + "\n")


MODELS = [m for m in dict.fromkeys([os.environ.get("GEMINI_MODEL"), "gemini-2.5-flash", "gemini-flash-latest"]) if m]


def ask_gemini(prompt):
    last = None
    for model in MODELS:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"},
            json={"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                  "tools": [{"google_search": {}}],
                  "generationConfig": {"temperature": 0.7}},
            timeout=240)
        if r.ok:
            break
        last = f"{model}: {r.status_code} {r.text[:200]}"
        print("gemini", last, file=sys.stderr)
    else:
        raise RuntimeError(f"no Gemini model answered with search grounding ({last})")
    parts = r.json()["candidates"][0]["content"]["parts"]
    text = "".join(p.get("text", "") for p in parts)
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in reply")
    return json.loads(m.group(0))


def validate(s, kind):
    errs = []
    if s.get("format") != kind:
        errs.append("format")
    words = 0
    for i, sc in enumerate(s.get("scenes", [])):
        t = sc.get("type")
        if t not in TEMPLATES:
            errs.append(f"scene {i}: unknown type {t}")
            continue
        for k in REQUIRED[t]:
            if k not in sc.get("data", {}):
                errs.append(f"scene {i} ({t}): missing data.{k}")
        if t == "counter" and "value" not in sc["data"] and "display" not in sc["data"]:
            errs.append(f"scene {i}: counter needs value or display")
        n = len(re.sub(r"\{[^|}]+\|([^}]+)\}", r"\1", sc.get("narration", "")).split())
        if n > 48:
            errs.append(f"scene {i}: narration too long ({n} words)")
        words += n
    lo, hi = (560, 760) if kind == "long" else (40, 70)
    if not lo <= words <= hi:
        errs.append(f"total words {words}, want {lo}-{hi}")
    if len([u for u in s.get("sources", []) if "http" in u]) < 2:
        errs.append("needs at least 2 source URLs")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    a = ap.parse_args()
    channel = json.loads((ROOT / "channels" / f"{a.channel}.json").read_text())
    done = sorted(p.parent.name for p in (ROOT / "content" / a.channel).glob("*/long.json"))
    example = (ROOT / "content" / "money" / "costco-hotdog" / "long.json").read_text()
    if len(example) > 30000:
        example = example[:30000]
    base = f"""You write scripts for the YouTube channel "{channel['name']}". Niche: {channel['niche']}
Topics already made (do not repeat): {', '.join(done) or 'none'}.

Pick ONE new, specific, evergreen topic in this niche that a curious adult would click. Research it with Google Search.
Rules: every number must come from a source you list (URL); round numbers the same way everywhere; label estimates as estimates
on screen; no investment advice; no claims you cannot source. Write narration that explains, with one concrete example worked
through. Use the markup {{display|spoken}} for numbers and symbols (e.g. {{$1.50|a dollar fifty}}). Max ~40 words per scene.
Scene types and their data fields must match this example exactly (same JSON shape). Return ONLY JSON.

EXAMPLE:
{example}
"""
    out = {}
    for kind, extra in (("long", "Write the LONG version: format \"long\", 26-32 scenes, 600-720 words total, 3 chapter scenes, a \"cta\" scene near 1:00 (data: {\"cue\": \"subscribe\"}), end scene last that teases next week. Add \"thumbnail\": {\"tag\": a short price or number, \"top\": at most 2 words}, a \"title\" under 45 characters that does not repeat the thumbnail words, \"summary\" (2 sentences) and \"hooks\" (5 hooks from different formulas)."),
                        ("short", "Now write ONE SHORT on a different angle of the same topic: format \"short\", 4-5 scenes, 45-60 words, the first scene is the hook and is readable on frame 0 (pricetag, statement or dots), the last scene is \"end\"."),
                        ("short2", "Write ANOTHER SHORT on a third angle of the same topic, same rules as the previous Short."),
                        ("short3", "Write ANOTHER SHORT on a fourth angle of the same topic, same rules.")):
        prompt = base + "\n" + extra
        if kind.startswith("short"):
            prompt += "\nThe long script you wrote:\n" + json.dumps(out["long"])
        for attempt in range(3):
            s = ask_gemini(prompt)
            errs = validate(s, "short" if kind.startswith("short") else kind)
            if not errs:
                out[kind] = s
                break
            prompt += "\n\nYour last answer failed validation: " + "; ".join(errs[:12]) + ". Fix these and return the full JSON again."
        else:
            sys.exit(f"{kind}: could not get a valid script: {errs}")
    slug = re.sub(r"[^a-z0-9]+", "-", out["long"]["title"].lower()).strip("-")[:48]
    d = ROOT / "content" / a.channel / slug
    d.mkdir(parents=True, exist_ok=True)
    items = []
    for kind, s in out.items():
        s = cinematize(s)
        s["id"], s["channel"] = f"{slug}-{kind}", a.channel
        s["voice"] = channel.get("voice", "af_heart")
        s["speed"] = 0.95 if kind == "long" else 1.05
        if kind != "long":
            s["long_video"] = f"{slug}-long"
        name = "long.json" if kind == "long" else f"{kind}.json"
        (d / name).write_text(json.dumps(s, indent=1))
        items.append((str((d / name).relative_to(ROOT)), "long" if kind == "long" else "short"))
    queue_add(a.channel, items)
    print("wrote and queued", d)


if __name__ == "__main__":
    main()
