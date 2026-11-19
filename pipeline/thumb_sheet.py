"""Thumbnail contact sheet: every upcoming long video's thumbnail (and any options to try), full size and at 120 px.

Usage:
  python pipeline/thumb_sheet.py --channel hidden [--opts opts.json] [--out out/thumb_sheet_hidden.png] [--all]

--opts: JSON {"content/<ch>/<slug>/long.json": [{"big": "...", "small": "...", "expr": "..."}, ...]} lists options
to compare with the script's own "thumbnail". Each tile is labelled "<id> #n: BIG / SMALL / expr" and shows a 120 px
wide copy in its corner (the size a phone feed shows), so pick the one that still reads there, then copy its block
into the script's "thumbnail". Uses the channel's look (channels/<id>.json "look") or pipeline/thumbnail.py.
Without --all only queue items dated today or later are drawn.
"""
import argparse
import datetime as dt
import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))


def render(script_path, thumb, ch_path, out_png, look):
    s = json.loads(Path(script_path).read_text())
    if thumb is not None:
        s["thumbnail"] = thumb
    tmp = Path(tempfile.mkdtemp()) / "s.json"
    tmp.write_text(json.dumps(s))
    if look:
        importlib.import_module("look_" + look).thumbnail(str(tmp), str(ch_path), str(out_png))
    else:
        subprocess.run([sys.executable, str(ROOT / "pipeline" / "thumbnail.py"), str(tmp), str(ch_path), str(out_png)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    ap.add_argument("--opts")
    ap.add_argument("--out")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    ch_path = ROOT / "channels" / f"{a.channel}.json"
    look = json.loads(ch_path.read_text()).get("look", "")
    today = dt.date.today().isoformat()
    queue = json.loads((ROOT / "content" / a.channel / "queue.json").read_text())
    longs = [q for q in queue if q["kind"] == "long" and (a.all or q["date"] >= today)]
    opts = json.loads(Path(a.opts).read_text()) if a.opts else {}
    work = Path(tempfile.mkdtemp())
    tiles = []
    for q in longs:
        s = json.loads((ROOT / q["script"]).read_text())
        variants = [None] + opts.get(q["script"], [])
        for n, th in enumerate(variants):
            t = th or s.get("thumbnail", {})
            png = work / f"{s['id']}-{n}.png"
            render(ROOT / q["script"], th, ch_path, png, look)
            label = f"{q['date']} {s['id']} #{n}: " + " / ".join(str(t.get(k, "")) for k in ("big", "small", "expr", "tag", "top") if t.get(k))
            tiles.append((png, label, s["title"]))
    if not tiles:
        print("thumb_sheet: nothing to draw")
        return
    tw, th_, cols = 640, 360, 2
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th_ + 46)), "#111")
    d = ImageDraw.Draw(sheet)
    for i, (png, label, title) in enumerate(tiles):
        x, y = (i % cols) * tw, (i // cols) * (th_ + 46)
        im = Image.open(png).convert("RGB")
        sheet.paste(im.resize((tw, th_)), (x, y))
        small = im.resize((120, 68))
        sheet.paste(small, (x + tw - 128, y + th_ - 76))
        d.rectangle([x + tw - 129, y + th_ - 77, x + tw - 7, y + th_ - 7], outline="#fff")
        d.text((x + 6, y + th_ + 4), label[:96], fill="#fff")
        d.text((x + 6, y + th_ + 24), title[:96], fill="#aaa")
    out = Path(a.out) if a.out else ROOT / "out" / f"thumb_sheet_{a.channel}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print("thumb_sheet", out, f"{len(tiles)} tiles")


if __name__ == "__main__":
    main()
