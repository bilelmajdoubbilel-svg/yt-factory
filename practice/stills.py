"""Practice stills (no video): character sheet, channel hosts, one cinematic style frame."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from cinema import character, char_box, world_street_night, frame_page, prop_svg  # noqa: E402

FONT = (ROOT / "node_modules/@fontsource/archivo-black/files/archivo-black-latin-400-normal.woff2").as_uri()
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "out" / "practice")
OUT.mkdir(parents=True, exist_ok=True)


def sheet_page(body, title):
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family:'Archivo Black'; src:url('{FONT}'); }}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1920px;height:1080px;overflow:hidden;background:radial-gradient(ellipse at 50% 30%,#2A2438,#0E0C14);font-family:'Archivo Black',sans-serif;color:#F3EEE3;position:relative}}
h1{{position:absolute;left:60px;top:36px;font-size:40px;letter-spacing:.02em}}
.lab{{position:absolute;font-size:22px;color:#9A97A6;text-align:center;width:300px;font-family:monospace}}
</style></head><body><h1>{title}</h1>{body}</body></html>'''


def svg_at(x, y, w, h, vb, inner):
    return f'<svg style="position:absolute;left:{x}px;top:{y}px" width="{w}" height="{h}" viewBox="{vb}" overflow="visible">{inner}</svg>'


pages = {}

# 1) expressions + poses, channel 1 host
body = ""
exprs = ["neutral", "happy", "surprised", "worried", "thinking", "proud"]
for i, e in enumerate(exprs):
    x = 70 + i * 300
    body += f'<div style="position:absolute;left:{x}px;top:110px;width:260px;height:290px;overflow:hidden;border-radius:24px;background:rgba(255,255,255,.04)">' + svg_at(0, 0, 260, 290, "-130 -520 260 290", character(f"e{i}", "money", expr=e)) + '</div>'
    body += f'<div class="lab" style="left:{x - 20}px;top:410px">{e}</div>'
poses = [("idle", None, "neutral"), ("hold", "hotdog", "happy"), ("point", None, "proud"),
         ("shrug", None, "worried"), ("chin", None, "thinking"), ("wave", None, "happy")]
for i, (p, prop, e) in enumerate(poses):
    x = 70 + i * 300
    body += svg_at(x, 470, 260, 520, "-210 -640 420 660", character(f"p{i}", "money", expr=e, pose=p, prop=prop))
    body += f'<div class="lab" style="left:{x - 20}px;top:1000px">{p}</div>'
pages["01_character_sheet"] = sheet_page(body, "Channel 1 host · expressions and poses")

# 2) three channel hosts
body = ""
for i, (o, e, p, label) in enumerate([("money", "happy", "hold", "Business & money"),
                                       ("history", "proud", "point", "History on maps"),
                                       ("scale", "surprised", "wave", "Science by scale")]):
    x = 210 + i * 560
    body += svg_at(x, 170, 420, 760, "-220 -640 440 660", character(f"h{i}", o, expr=e, pose=p, prop="hotdog" if o == "money" else None))
    body += f'<div class="lab" style="left:{x + 60}px;top:960px;font-size:28px;color:#F3EEE3;width:300px">{label}</div>'
pages["02_channel_hosts"] = sheet_page(body, "One recurring host per channel")

# 3) cinematic style frame: night storefront, shallow focus on the host
w = world_street_night("sf")
tag = ('<svg style="position:absolute;left:-40px;top:300px" width="420" height="320" viewBox="-210 -40 420 320" overflow="visible">'
       '<g transform="rotate(-5 0 0)"><path d="M-100,0 L-100,112 M100,0 L100,112" stroke="#1A1420" stroke-width="5"/>'
       f'<g transform="translate(0 170)">{prop_svg("tag", 0, 0, 1.0)}</g></g></svg>')
w["mid"] += tag
w["near"] += char_box("host", -260, 1000, 1.0, outfit="money", expr="happy", pose="hold", prop="hotdog")
html = frame_page([("far", w["far"]), ("mid", w["mid"]), ("near", w["near"]), ("fore", w["fore"])],
                  {"far": 3.2, "mid": 1.5, "near": 1.0, "fore": 0.55}, focus=1.0, cam=(-120, 40, 1.08))
pages["03_style_frame"] = html.replace("ARCHIVO", FONT)

if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        for name, html in pages.items():
            f = OUT / f"{name}.html"
            f.write_text(html)
            pg.goto(f.resolve().as_uri())
            pg.wait_for_timeout(400)
            pg.screenshot(path=str(OUT / f"{name}.png"))
            print("wrote", OUT / f"{name}.png")
        b.close()
