"""Channel 1 branding (brand v3, "Tag"): profile picture (800x800) and banner (2560x1440, text inside the
1546x423 safe area that every device shows). Bright teal, cream receipt, Tag the mascot; nothing dark."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from cinema import tag_character  # noqa: E402

DISPLAY = (ROOT / "assets/fonts/pl-display.woff2").as_uri()
MONO = (ROOT / "assets/fonts/pl-mono.woff2").as_uri()
FONTS = (f"@font-face{{font-family:'PL Display';src:url('{DISPLAY}')}}"
         f"@font-face{{font-family:'PL Mono';src:url('{MONO}')}}")
INK, TEAL, MUSTARD, CORAL, CREAM = "#2B2230", "#2F7F95", "#F6C453", "#E46C55", "#FFF8EC"
name = sys.argv[1] if len(sys.argv) > 1 else "Price Logic"

# profile picture: Tag's face filling a teal circle (YouTube crops to a circle)
avatar = f'''<!doctype html><html><head><meta charset="utf-8"><style>{FONTS}
*{{margin:0;padding:0}} body{{width:800px;height:800px;overflow:hidden;
background:radial-gradient(circle at 50% 38%,#4FA7B5 0%,{TEAL} 55%,#1F5E70 100%)}}</style></head>
<body><svg width="800" height="800" viewBox="-200 -600 400 400">{tag_character("av", expr="happy", pose="wave")}</svg></body></html>'''

# banner: cream receipt strip with the name, Tag waving beside it, coins on teal
zig = "".join(f"{i * 40},{0 if i % 2 == 0 else 26} " for i in range(0, 41))
coins = "".join(
    f'<div style="position:absolute;left:{x}px;top:{y}px;width:{r * 2}px;height:{r * 2}px;border-radius:50%;'
    f'background:radial-gradient(circle at 35% 35%,#FFE9A8,{MUSTARD} 60%,#C98516);opacity:{op};filter:blur({b}px)"></div>'
    for x, y, r, op, b in ((260, 300, 40, .55, 4), (2200, 260, 52, .5, 6), (380, 1050, 60, .4, 8), (2280, 1000, 36, .6, 3),
                           (1900, 420, 22, .5, 2), (640, 520, 18, .45, 2)))
banner = f'''<!doctype html><html><head><meta charset="utf-8"><style>{FONTS}
*{{margin:0;padding:0}} body{{width:2560px;height:1440px;overflow:hidden;position:relative;
background:radial-gradient(ellipse at 50% 45%,#5DB2BE 0%,{TEAL} 50%,#1F5E70 100%)}}</style></head><body>
{coins}
<div style="position:absolute;left:507px;top:508px;width:1546px;height:423px;display:flex;align-items:center;gap:30px">
  <svg width="330" height="430" viewBox="-200 -640 400 650" style="flex:none">{tag_character("bn", expr="happy", pose="wave")}</svg>
  <div style="transform:rotate(-2deg);filter:drop-shadow(0 20px 30px rgba(10,30,40,.35))">
    <div style="background:{CREAM};border-radius:16px 16px 0 0;padding:26px 52px 20px">
      <div style="font-family:'PL Mono';font-size:30px;letter-spacing:.2em;color:#7A7480">RECEIPT · EVERY TUESDAY & FRIDAY</div>
      <div style="font-family:'PL Display';font-size:150px;line-height:1;color:{INK};letter-spacing:-.03em;margin-top:6px">{name}</div>
      <div style="font-family:'PL Display';font-size:52px;color:{CORAL};margin-top:4px">The receipts behind everyday prices</div>
    </div>
    <svg width="100%" height="26" viewBox="0 0 1600 26" preserveAspectRatio="none" style="display:block"><polygon points="0,0 {zig} 1600,0" fill="{CREAM}"/></svg>
  </div>
</div></body></html>'''

if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    out = ROOT / "out" / "branding"
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        for fname, html, (W, H) in (("profile_picture.png", avatar, (800, 800)), ("banner.png", banner, (2560, 1440))):
            f = out / (fname + ".html")
            f.write_text(html)
            pg = b.new_page(viewport={"width": W, "height": H})
            pg.goto(f.as_uri())
            pg.wait_for_timeout(500)
            pg.screenshot(path=str(out / fname))
            f.unlink()
            print("wrote", out / fname)
        b.close()
