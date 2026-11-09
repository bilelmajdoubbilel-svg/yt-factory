"""Thumbnail: script JSON "thumbnail" block -> 1280x720 PNG.

"thumbnail": {"tag": "$1.50", "top": "SAME PRICE", "bottom": "SINCE 1985", "badge": "40 YEARS"}
Usage: python thumbnail.py <script.json> <channel.json> <out.png>
"""
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "node_modules" / "@fontsource" / "archivo-black" / "files" / "archivo-black-latin-400-normal.woff2"


def page(t, theme):
    e = lambda s: html.escape(str(s))
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family: 'AB'; src: url('{FONT.as_uri()}') format('woff2'); }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:1280px; height:720px; overflow:hidden; background:{theme['bg']}; font-family:'AB',sans-serif; position:relative; }}
.grid {{ position:absolute; inset:0; background-image: linear-gradient(rgba(243,238,227,.05) 2px, transparent 2px),
  linear-gradient(90deg, rgba(243,238,227,.05) 2px, transparent 2px); background-size:64px 64px; }}
.glow {{ position:absolute; left:-120px; top:60px; width:760px; height:760px; border-radius:50%;
  background: radial-gradient(circle, rgba(255,197,49,.28), rgba(255,197,49,0) 65%); }}
.tag {{ position:absolute; left:70px; top:200px; transform: rotate(-9deg); background:{theme['gold']}; color:{theme['bg']};
  border-radius:34px; padding:34px 70px 34px 108px; font-size:168px; line-height:1; letter-spacing:-.03em;
  box-shadow: 0 30px 60px rgba(0,0,0,.55); }}
.hole {{ position:absolute; left:38px; top:50%; width:40px; height:40px; margin-top:-20px; border-radius:50%; background:{theme['bg']}; }}
.text {{ position:absolute; right:60px; top:150px; width:520px; text-align:right; }}
.top {{ font-size:92px; line-height:.98; color:{theme['paper']}; }}
.bottom {{ font-size:92px; line-height:.98; color:{theme['gold']}; margin-top:10px; }}
.badge {{ display:inline-block; margin-top:34px; background:{theme['accent']}; color:#fff; font-size:44px; padding:10px 26px; border-radius:14px; }}
</style></head><body>
<div class="grid"></div><div class="glow"></div>
<div class="tag"><div class="hole"></div>{e(t['tag'])}</div>
<div class="text"><div class="top">{e(t['top'])}</div><div class="bottom">{e(t['bottom'])}</div>
{f'<div class="badge">{e(t["badge"])}</div>' if t.get('badge') else ''}</div>
</body></html>"""


def main(script_path, channel_path, out_png):
    from playwright.sync_api import sync_playwright
    script = json.loads(Path(script_path).read_text())
    theme = json.loads(Path(channel_path).read_text())["theme"]
    t = script.get("thumbnail") or {"tag": "?", "top": script["title"][:20].upper(), "bottom": ""}
    tmp = Path(out_png).with_suffix(".html")
    tmp.write_text(page(t, theme))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        pg.goto(tmp.resolve().as_uri())
        pg.wait_for_timeout(300)
        pg.screenshot(path=out_png)
        b.close()
    tmp.unlink()
    print("thumbnail", out_png)





BRAND_DISPLAY = ROOT / "assets" / "fonts" / "pl-display.woff2"
BRAND_MONO = ROOT / "assets" / "fonts" / "pl-mono.woff2"


def cinematic_page(t, theme, outfit="money"):
    """Brand v3 thumbnail: bright studio, Tag the mascot big on the left, a cream receipt on the right with
    one number and at most 3 words. Built to look like nothing else in the feed (no dark scene, no outlined caps)."""
    import sys as _s
    _s.path.insert(0, str(Path(__file__).parent))
    from cinema import char_box, frame_page
    from worlds import studio
    w = studio(790, 1080)
    host = char_box("th", -520, 1180, 1.65, outfit=outfit, expr=t.get("expr", "surprised"), pose=t.get("pose", "hold"),
                    prop=t.get("prop", "hotdog"))
    zig = "".join(f"{i * 28},{0 if i % 2 == 0 else 22} " for i in range(0, 25))
    ink, coral = theme.get("ink", "#2B2230"), theme.get("accent", "#E46C55")
    over = (f'<div style="position:absolute;left:930px;top:110px;width:680px;transform:rotate(4deg);filter:drop-shadow(0 24px 40px rgba(20,30,40,.35))">'
            f'<div style="background:#FFF8EC;border-radius:18px 18px 0 0;padding:34px 46px 26px">'
            f'<div style="font-family:PLMono;font-size:30px;letter-spacing:.18em;color:#7A7480">PRICE LOGIC · RECEIPT</div>'
            f'<div style="height:4px;margin:18px 0 10px;background:repeating-linear-gradient(90deg,{ink} 0 14px,transparent 14px 24px)"></div>'
            f'<div id="bignum" style="font-family:PLDisplay;font-size:210px;line-height:1;color:{ink};letter-spacing:-.04em;white-space:nowrap">{html.escape(t["tag"])}</div>'
            f'<div style="font-family:PLDisplay;font-size:96px;line-height:.98;color:{coral};margin-top:8px">{html.escape(t["top"])}</div></div>'
            f'<svg width="680" height="24" viewBox="0 0 672 22" preserveAspectRatio="none" style="display:block"><polygon points="0,0 {zig} 672,0" fill="#FFF8EC"/></svg></div>')
    page = frame_page([("far", w["far"]), ("mid", w["mid"]), ("near", w["near"] + host), ("fore", w["fore"])],
                      {"far": 3.0, "mid": 1.5, "near": 1.0, "fore": .55}, focus=1.0, cam=(0, 30, 1.0), extra=over)
    page = page.replace("ARCHIVO", BRAND_DISPLAY.as_uri())
    page = page.replace("<style>", "<style>@font-face{font-family:PLDisplay;src:url('" + BRAND_DISPLAY.as_uri() + "')}"
                        "@font-face{font-family:PLMono;src:url('" + BRAND_MONO.as_uri() + "')}"
                        "@font-face{font-family:'PL Mono';src:url('" + BRAND_MONO.as_uri() + "')}", 1)
    # thumbnails: no letterbox bars, no dark vignette
    page = page.replace('<div style="position:absolute;left:0;right:0;top:0;height:64px;background:#000"></div>', "")
    page = page.replace('<div style="position:absolute;left:0;right:0;bottom:0;height:64px;background:#000"></div>', "")
    page = page.replace("rgba(0,0,0,0) 50%,rgba(0,0,0,.55) 100%", "rgba(0,0,0,0) 60%,rgba(0,0,0,.18) 100%")
    return page


def main_cinematic(script_path, channel_path, out_png):
    from playwright.sync_api import sync_playwright
    script = json.loads(Path(script_path).read_text())
    ch = json.loads(Path(channel_path).read_text())
    t = script["thumbnail"]
    tmp = Path(out_png).with_suffix(".html")
    tmp.write_text(cinematic_page(t, ch["theme"], ch.get("id", "money")))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=2 / 3)
        pg.goto(tmp.resolve().as_uri())
        pg.evaluate("document.fonts.ready.then(() => 1)")
        # wide numbers ($985M) shrink until they fit the receipt
        pg.evaluate("""() => { const b = document.getElementById('bignum'); if (!b) return;
            let f = 210; while (b.scrollWidth > b.clientWidth && f > 100) { f -= 4; b.style.fontSize = f + 'px'; } }""")
        pg.wait_for_timeout(400)
        pg.screenshot(path=out_png)
        b.close()
    tmp.unlink()
    print("thumbnail", out_png)


if __name__ == "__main__":
    _sp = json.loads(Path(sys.argv[1]).read_text())
    _ch = json.loads(Path(sys.argv[2]).read_text())
    if _ch.get("look"):   # channel look module (channels/<id>.json "look") draws its own thumbnail
        import importlib
        sys.path.insert(0, str(Path(__file__).parent))
        importlib.import_module("look_" + _ch["look"]).thumbnail(*sys.argv[1:4])
    else:
        (main_cinematic if _sp.get("style") == "cinematic" else main)(*sys.argv[1:4])
