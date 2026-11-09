"""Hidden Systems look review stills: thumbnail, end card, Drip rig sheet, cutaway kit sheet.

    python practice/hidden_stills.py <outdir> [script.json]

Frames from a built Short come from `npx hyperframes snapshot --at ...` in build/<id>/ (see RUNBOOK).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import hs_art as A           # noqa: E402
import look_hidden as LH     # noqa: E402

FONTS = LH.fonts_css((ROOT / "assets/hidden/fonts").as_uri() + "/")


def page(svg_inner, W, H, bg=None):
    bg_img = ""
    if bg:
        bg_img = f'<img src="{bg.as_uri()}" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px">'
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{FONTS}*{{margin:0;padding:0}}'
            f'body{{width:{W}px;height:{H}px;overflow:hidden;position:relative;background:{A.C["concrete"]}}}</style></head><body>{bg_img}'
            f'<svg style="position:absolute;left:0;top:0" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{A.SVG_DEFS}{svg_inner}</svg></body></html>')


def rig_sheet():
    """Expressions, mouth shapes, the take (hat pop) and the tendril arms."""
    W, H = 1920, 1080
    g = [A.stencil(60, 110, "DRIP · RIG SHEET", 84, A.C["hat"], anchor="start"),
         A.mono(64, 156, "canonical drip_host() at rest · new: expressions, mouths, take, tendril arms", 26, A.C["steel"])]
    for i, e in enumerate(A.EXPRS):
        x = 170 + i * 316
        g.append(f'<g transform="translate({x} 420) scale(1.05)">{A.drip_rig(f"x{i}", e)}</g>')
        g.append(A.mono(x, 560, e.upper(), 28, A.C["cream"], "middle"))
    for i, m in enumerate(["rest", "e", "a", "wide", "o"]):
        x = 170 + i * 316
        rig = A.drip_rig(f"m{i}", "neutral")
        for mm in A.MOUTHS:
            rig = rig.replace(f'<g id="m{i}-m-{mm}" opacity="1">', f'<g id="m{i}-m-{mm}" opacity="0">')
        rig = rig.replace(f'<g id="m{i}-m-{m}" opacity="0">', f'<g id="m{i}-m-{m}" opacity="1">')
        g.append(f'<g transform="translate({x} 840) scale(.9)">{rig}</g>')
        g.append(A.mono(x, 960, f"MOUTH {m.upper()}", 26, A.C["steel"], "middle"))
    take = A.drip_rig("tk", "surprised").replace('<g id="tk-hat">', '<g id="tk-hat" transform="translate(-4 -34) rotate(-10 0 -52)">') \
        .replace('<g id="tk-bod">', '<g id="tk-bod" transform="translate(0 100) scale(.93 1.1) translate(0 -100)">') \
        .replace('<g id="tk-armR" transform="translate(80 28) scale(0)">', '<g id="tk-armR" transform="translate(80 28) rotate(-30) scale(1)">') \
        .replace('<g id="tk-armL" transform="translate(-80 28) scale(0)">', '<g id="tk-armL" transform="translate(-80 28) rotate(20) scale(.8)">')
    g.append(f'<g transform="translate({170 + 5 * 316} 840) scale(.9)">{take}</g>')
    g.append(A.mono(170 + 5 * 316, 960, "TAKE + ARMS", 26, A.C["cream"], "middle"))
    return page("".join(g), W, H)


def main(outdir, script_path=None):
    from playwright.sync_api import sync_playwright
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    bg = A.concrete_png(out / "_concrete.png", 1920, 1080, seed=5)
    inner, slots = LH.endcard_page()
    jobs = {
        "endcard.png": (page(inner, 1920, 1080, bg), 1920, 1080),
        "rig-sheet.png": (rig_sheet(), 1920, 1080),
        "kit-sheet.png": (page(A.kit_sheet_svg(), 1920, 1080), 1920, 1080),
    }
    t = {"big": "60×", "small": "A SECOND", "expr": "surprised"}
    if script_path:
        t = json.loads(Path(script_path).read_text()).get("thumbnail", t)
    jobs["thumbnail.png"] = (LH.thumbnail_page(t), 1280, 720)
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, (html_, W, H) in jobs.items():
            pg = b.new_page(viewport={"width": W, "height": H})
            tmp = out / (name + ".html")
            tmp.write_text(html_)
            pg.goto(tmp.resolve().as_uri())
            pg.evaluate("document.fonts.ready.then(() => 1)")
            pg.wait_for_timeout(300)
            pg.screenshot(path=str(out / name))
            tmp.unlink()
            pg.close()
        b.close()
    (out / "_concrete.png").unlink()
    print("end-screen slots (x, y, w, h):", slots)
    print("wrote", ", ".join(jobs), "to", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
