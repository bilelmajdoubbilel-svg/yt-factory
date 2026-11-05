"""Hosts and channel art for Map Minutes (Pin, a living map pin) and Hidden Systems (Drip, a water drop
in a hard hat). Original characters, drawn as SVG so the video looks, avatars and banners share one source.

    python pipeline/brand_art.py avatars <outdir>    # 3 avatar options per channel (800x800 PNG + SVG)

The host functions (pin_host, drip_host) are the canonical drawings: reuse them in the channel looks.
Fonts (OFL, in assets/<channel>/fonts): Map Minutes = Fraunces 800 + IBM Plex Mono 600;
Hidden Systems = Barlow Condensed 800 + JetBrains Mono 700.
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MM = {  # Map Minutes palette: parchment and ocean
    "parchment": "#F3E6C4", "parchment2": "#E6D3A6", "grid": "#CDB987", "ocean": "#1F5F8B",
    "ocean2": "#154766", "ink": "#142B3D", "cream": "#FFF7E3", "coral": "#D65A3A", "sea": "#A9CBD9",
}
HS = {  # Hidden Systems palette: concrete, safety orange, pipe green
    "concrete": "#2E3338", "concrete2": "#3B4248", "pipe": "#3E8E5E", "pipe2": "#2C6A45", "bolt": "#A3ADB5",
    "water": "#7CCBEA", "water2": "#2F7FA6", "hat": "#F26B1D", "hat2": "#C24F0E", "ink": "#1B1F23",
    "cream": "#FFF6E8", "line": "#4A535B",
}


def _face(cx, cy, r, ink, eye_dx=0.22, eye_y=-0.05, eye=0.085, cheek="#D65A3A", mood="happy"):
    """Shared face: eyes with catchlights, brows, smile, cheeks. r = size unit."""
    ex = eye_dx * r
    ey = cy + eye_y * r
    rx, ry = eye * r, eye * 1.3 * r
    sw = max(2.0, 0.045 * r)
    brow_y = ey - ry - 0.09 * r
    lift = 0.03 * r if mood == "happy" else -0.02 * r
    out = []
    for s in (-1, 1):
        x = cx + s * ex
        out.append(f'<ellipse cx="{x:.1f}" cy="{ey:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{ink}"/>')
        out.append(f'<circle cx="{x - rx * 0.35:.1f}" cy="{ey - ry * 0.4:.1f}" r="{rx * 0.38:.1f}" fill="#fff"/>')
        out.append(f'<path d="M{x - rx * 1.2:.1f} {brow_y + lift * s * 0:.1f} Q{x:.1f} {brow_y - lift - 0.035 * r:.1f} '
                   f'{x + rx * 1.2:.1f} {brow_y:.1f}" stroke="{ink}" stroke-width="{sw * 0.8:.1f}" fill="none" stroke-linecap="round"/>')
        out.append(f'<ellipse cx="{cx + s * (ex + 0.13 * r):.1f}" cy="{ey + ry + 0.1 * r:.1f}" rx="{0.08 * r:.1f}" '
                   f'ry="{0.05 * r:.1f}" fill="{cheek}" opacity="0.35"/>')
    my = ey + ry + 0.1 * r
    out.append(f'<path d="M{cx - 0.15 * r:.1f} {my:.1f} Q{cx:.1f} {my + 0.15 * r:.1f} {cx + 0.15 * r:.1f} {my:.1f}" '
               f'stroke="{ink}" stroke-width="{sw:.1f}" fill="none" stroke-linecap="round"/>')
    return "".join(out)


def pin_host(cx, cy, r, face=True, shadow=True):
    """Pin: an original living map pin. Head circle centre (cx, cy), radius r, tip at cy + 1.85 r.
    A compass needle stands up from the head (its motif: it always points where the story goes)."""
    c = MM
    tip = cy + 1.85 * r
    body = (f"M{cx:.1f} {tip:.1f} C{cx - 0.35 * r:.1f} {cy + 1.35 * r:.1f} {cx - r:.1f} {cy + 0.75 * r:.1f} {cx - r:.1f} {cy:.1f} "
            f"A{r:.1f} {r:.1f} 0 1 1 {cx + r:.1f} {cy:.1f} C{cx + r:.1f} {cy + 0.75 * r:.1f} {cx + 0.35 * r:.1f} {cy + 1.35 * r:.1f} "
            f"{cx:.1f} {tip:.1f}Z")
    ny0, ny1 = cy - r - 0.62 * r, cy - r + 0.2 * r   # compass needle: coral north half, ink south half
    nm = cy - r - 0.2 * r
    w = 0.13 * r
    parts = []
    if shadow:
        parts.append(f'<ellipse cx="{cx:.1f}" cy="{tip + 0.03 * r:.1f}" rx="{0.42 * r:.1f}" ry="{0.07 * r:.1f}" fill="{c["ink"]}" opacity="0.22"/>')
    parts.append(f'<path d="M{cx:.1f} {ny0:.1f} L{cx + w:.1f} {nm:.1f} L{cx - w:.1f} {nm:.1f}Z" fill="{c["coral"]}"/>')
    parts.append(f'<path d="M{cx - w:.1f} {nm:.1f} L{cx + w:.1f} {nm:.1f} L{cx:.1f} {ny1:.1f}Z" fill="{c["ink"]}"/>')
    parts.append(f'<circle cx="{cx:.1f}" cy="{nm:.1f}" r="{0.065 * r:.1f}" fill="#F2C14E" stroke="{c["ink"]}" stroke-width="{0.025 * r:.1f}"/>')
    parts.append(f'<path d="{body}" fill="{c["ocean"]}" stroke="{c["ocean2"]}" stroke-width="{0.05 * r:.1f}" stroke-linejoin="round"/>')
    parts.append(f'<path d="M{cx - 0.78 * r:.1f} {cy - 0.25 * r:.1f} A{0.82 * r:.1f} {0.82 * r:.1f} 0 0 1 {cx - 0.2 * r:.1f} {cy - 0.8 * r:.1f}" '
                 f'stroke="#fff" stroke-opacity="0.28" stroke-width="{0.07 * r:.1f}" fill="none" stroke-linecap="round"/>')
    parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{0.64 * r:.1f}" fill="{c["cream"]}" stroke="{c["ocean2"]}" stroke-width="{0.04 * r:.1f}"/>')
    if face:
        parts.append(_face(cx, cy, r * 0.95, c["ink"], eye_dx=0.23, eye_y=-0.1, eye=0.075, cheek=c["coral"]))
    return "".join(parts)


def drip_host(cx, cy, r, face=True, shadow=True):
    """Drip: an original water drop in a safety-orange hard hat. Body circle centre (cx, cy), radius r,
    the drop's tip pokes out above the hat at cy - 1.6 r (its motif: it travels through every system)."""
    c = HS
    body = (f"M{cx:.1f} {cy - 1.6 * r:.1f} C{cx + 0.15 * r:.1f} {cy - 1.25 * r:.1f} {cx + r:.1f} {cy - 0.55 * r:.1f} {cx + r:.1f} {cy:.1f} "
            f"A{r:.1f} {r:.1f} 0 1 1 {cx - r:.1f} {cy:.1f} C{cx - r:.1f} {cy - 0.55 * r:.1f} {cx - 0.15 * r:.1f} {cy - 1.25 * r:.1f} "
            f"{cx:.1f} {cy - 1.6 * r:.1f}Z")
    parts = []
    if shadow:
        parts.append(f'<ellipse cx="{cx:.1f}" cy="{cy + 1.02 * r:.1f}" rx="{0.62 * r:.1f}" ry="{0.08 * r:.1f}" fill="#000" opacity="0.25"/>')
    parts.append(f'<path d="{body}" fill="{c["water"]}" stroke="{c["water2"]}" stroke-width="{0.05 * r:.1f}" stroke-linejoin="round"/>')
    parts.append(f'<ellipse cx="{cx - 0.55 * r:.1f}" cy="{cy + 0.05 * r:.1f}" rx="{0.13 * r:.1f}" ry="{0.3 * r:.1f}" fill="#fff" opacity="0.5" transform="rotate(12 {cx - 0.55 * r:.1f} {cy:.1f})"/>')
    hy = cy - 0.55 * r
    parts.append(f'<path d="M{cx - 0.66 * r:.1f} {hy:.1f} Q{cx - 0.64 * r:.1f} {hy - 0.66 * r:.1f} {cx:.1f} {hy - 0.7 * r:.1f} '
                 f'Q{cx + 0.64 * r:.1f} {hy - 0.66 * r:.1f} {cx + 0.66 * r:.1f} {hy:.1f}Z" fill="{c["hat"]}" stroke="{c["hat2"]}" stroke-width="{0.04 * r:.1f}"/>')
    parts.append(f'<rect x="{cx - 0.09 * r:.1f}" y="{hy - 0.69 * r:.1f}" width="{0.18 * r:.1f}" height="{0.69 * r:.1f}" rx="{0.05 * r:.1f}" fill="{c["hat2"]}" opacity="0.55"/>')
    parts.append(f'<rect x="{cx - 0.86 * r:.1f}" y="{hy - 0.04 * r:.1f}" width="{1.72 * r:.1f}" height="{0.15 * r:.1f}" rx="{0.075 * r:.1f}" fill="{c["hat"]}" stroke="{c["hat2"]}" stroke-width="{0.04 * r:.1f}"/>')
    if face:
        parts.append(_face(cx, cy + 0.05 * r, r * 1.05, c["ink"], eye_dx=0.26, eye_y=-0.05, eye=0.085, cheek=c["hat"]))
    return "".join(parts)


def _font(path):
    import base64
    return "data:font/woff2;base64," + base64.b64encode((ROOT / path).read_bytes()).decode()


def _fonts():
    """Fonts embedded as data URIs so the SVG renders the same anywhere (a page set from a string cannot load file://)."""
    faces = {"MMDisplay": "assets/mapminutes/fonts/mm-display.woff2", "MMMono": "assets/mapminutes/fonts/mm-mono.woff2",
             "HSDisplay": "assets/hidden/fonts/hs-display.woff2", "HSMono": "assets/hidden/fonts/hs-mono.woff2"}
    return "<style>" + "".join(f"@font-face{{font-family:{k};src:url({_font(v)})}}" for k, v in faces.items()) + "</style>"


def _svg(inner, w=800, h=800):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{_fonts()}{inner}</svg>'


def graticule(w, h, color, opacity=1.0, step=110):
    """Curved latitude/longitude lines, like an old map projection."""
    out = [f'<g stroke="{color}" stroke-width="3" fill="none" opacity="{opacity}">']
    for i in range(-2, int(h / step) + 3):
        y = i * step
        out.append(f'<path d="M-20 {y + 40} Q{w / 2} {y - 40} {w + 20} {y + 40}"/>')
    for j in range(-3, int(w / step) + 4):
        x = j * step
        out.append(f'<path d="M{x} -20 Q{x + (x - w / 2) * 0.12} {h / 2} {x} {h + 20}"/>')
    out.append("</g>")
    return "".join(out)


def mm_avatar(option):
    c = MM
    if option == "A":  # close-up, parchment map behind
        bg = f'<rect width="800" height="800" fill="{c["parchment"]}"/>' + graticule(800, 800, c["grid"], 0.8)
        return _svg(bg + pin_host(400, 395, 225, shadow=False))
    if option == "B":  # full pin on its route, 49th parallel motif
        bg = (f'<rect width="800" height="800" fill="{c["parchment"]}"/>' + graticule(800, 800, c["grid"], 0.6)
              + f'<path d="M110 430 Q400 395 690 430" stroke="{c["ocean2"]}" stroke-width="5" stroke-dasharray="2 14" stroke-linecap="round" fill="none"/>'
              + f'<text x="640" y="415" font-family="MMMono" font-size="34" fill="{c["ocean2"]}" text-anchor="middle">49°N</text>'
              + f'<path d="M150 640 C250 560 300 690 400 600" stroke="{c["coral"]}" stroke-width="10" stroke-dasharray="26 18" stroke-linecap="round" fill="none"/>')
        return _svg(bg + pin_host(400, 330, 150))
    if option == "C":  # bold icon for small sizes
        bg = (f'<rect width="800" height="800" fill="{c["ink"]}"/>'
              + f'<circle cx="400" cy="400" r="340" fill="{c["parchment"]}"/>'
              + f'<circle cx="400" cy="400" r="340" fill="none" stroke="{c["coral"]}" stroke-width="14" stroke-dasharray="40 22"/>')
        return _svg(bg + pin_host(400, 330, 175, shadow=False))
    raise ValueError(option)


def pipe_ring(cx, cy, r, width, n_bolts=8):
    c = HS
    out = [f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c["pipe"]}" stroke-width="{width}"/>',
           f'<circle cx="{cx}" cy="{cy}" r="{r - width / 2}" fill="none" stroke="{c["pipe2"]}" stroke-width="6"/>']
    for i in range(n_bolts):
        a = 2 * math.pi * i / n_bolts + math.pi / n_bolts
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{width * 0.22:.1f}" fill="{c["bolt"]}" stroke="{c["pipe2"]}" stroke-width="4"/>')
    return "".join(out)


def hs_avatar(option):
    c = HS
    if option == "A":  # looking into a pipe: flange ring frames Drip
        rings = "".join(f'<circle cx="400" cy="400" r="{r}" fill="none" stroke="{c["line"]}" stroke-width="3" opacity="0.6"/>' for r in (120, 190, 260))
        bg = f'<rect width="800" height="800" fill="{c["concrete"]}"/>' + rings + pipe_ring(400, 400, 345, 70, 10)
        return _svg(bg + drip_host(400, 470, 175))
    if option == "B":  # cutaway pipe with flow, blueprint grid
        grid = "".join(f'<path d="M{x} 0V800" stroke="{c["line"]}" stroke-width="2"/>' for x in range(0, 801, 50)) + \
               "".join(f'<path d="M0 {y}H800" stroke="{c["line"]}" stroke-width="2"/>' for y in range(0, 801, 50))
        pipe = (f'<rect x="-10" y="470" width="820" height="150" fill="{c["concrete2"]}" stroke="{c["pipe"]}" stroke-width="22"/>'
                + "".join(f'<path d="M{x} 545 h60" stroke="{c["water"]}" stroke-width="8" stroke-linecap="round" opacity="0.7"/>' for x in (60, 560, 680))
                + f'<path d="M100 300 v80 h120" stroke="{c["hat"]}" stroke-width="10" fill="none" stroke-linecap="round"/>'
                + f'<text x="640" y="230" font-family="HSMono" font-size="34" fill="{c["bolt"]}" text-anchor="middle">PIPE 01</text>')
        return _svg(f'<rect width="800" height="800" fill="{c["concrete"]}"/>' + grid + pipe + drip_host(400, 480, 150))
    if option == "C":  # bold icon for small sizes
        bg = (f'<rect width="800" height="800" fill="{c["concrete"]}"/>'
              + f'<circle cx="400" cy="400" r="340" fill="{c["pipe"]}"/>'
              + f'<circle cx="400" cy="400" r="300" fill="none" stroke="{c["pipe2"]}" stroke-width="8"/>')
        return _svg(bg + drip_host(400, 470, 185, shadow=False))
    raise ValueError(option)


CHOSEN = {"mapminutes": "A", "hidden": "A"}  # owner picked on 6 Nov 2026


def mm_banner():
    """2560x1440; everything that matters inside YouTube's safe area (1546x423, centred)."""
    c = MM
    sx, sy, sw, sh = 507, 508, 1546, 423
    bg = (f'<rect width="2560" height="1440" fill="{c["parchment"]}"/>' + graticule(2560, 1440, c["grid"], 0.7, step=150)
          + f'<path d="M0 {sy + 393} H2560" stroke="{c["ocean2"]}" stroke-width="7" stroke-dasharray="3 20" stroke-linecap="round" fill="none"/>'
          + f'<text x="{sx + 1430}" y="{sy + 378}" font-family="MMMono" font-size="34" fill="{c["ocean2"]}">49°N</text>')
    title = (f'<text x="{sx + 40}" y="{sy + 190}" font-family="MMDisplay" font-size="150" fill="{c["ink"]}">Map Minutes</text>'
             f'<text x="{sx + 44}" y="{sy + 262}" font-family="MMMono" font-size="40" fill="{c["ocean2"]}">The US and Canada, explained on the map</text>'
             f'<rect x="{sx + 44}" y="{sy + 300}" width="520" height="62" rx="31" fill="{c["ocean"]}"/>'
             f'<text x="{sx + 304}" y="{sy + 342}" font-family="MMMono" font-size="32" fill="{c["cream"]}" text-anchor="middle">New video every Wednesday</text>')
    return _svg(bg + title + pin_host(sx + 1300, sy + 190, 108), 2560, 1440)  # Pin stands on the 49th parallel


def hs_banner():
    c = HS
    sx, sy, sw, sh = 507, 508, 1546, 423
    grid = "".join(f'<path d="M{x} 0V1440" stroke="{c["line"]}" stroke-width="2"/>' for x in range(0, 2561, 80)) + \
           "".join(f'<path d="M0 {y}H2560" stroke="{c["line"]}" stroke-width="2"/>' for y in range(0, 1441, 80))
    pipe_y = sy + 330
    pipe = (f'<rect x="-10" y="{pipe_y}" width="2580" height="90" fill="{c["pipe"]}"/>'
            f'<rect x="-10" y="{pipe_y + 12}" width="2580" height="12" fill="#fff" opacity="0.12"/>'
            + "".join(f'<rect x="{x}" y="{pipe_y - 14}" width="34" height="118" rx="6" fill="{c["pipe2"]}"/>' for x in range(120, 2560, 420)))
    title = (f'<text x="{sx + 40}" y="{sy + 170}" font-family="HSDisplay" font-size="168" fill="{c["cream"]}" letter-spacing="4">HIDDEN <tspan fill="{c["hat"]}">SYSTEMS</tspan></text>'
             f'<text x="{sx + 46}" y="{sy + 240}" font-family="HSMono" font-size="38" fill="{c["bolt"]}">How water, power, trash, mail and 911 really work</text>'
             f'<rect x="{sx + 46}" y="{sy + 262}" width="470" height="56" rx="8" fill="{c["hat"]}"/>'
             f'<text x="{sx + 281}" y="{sy + 300}" font-family="HSMono" font-size="30" fill="{c["ink"]}" text-anchor="middle">NEW VIDEO EVERY SUNDAY</text>')
    return _svg(f'<rect width="2560" height="1440" fill="{c["concrete"]}"/>' + grid + pipe + title
                + drip_host(sx + 1340, sy + 230, 105), 2560, 1440)


def render(svgs, outdir):
    from playwright.sync_api import sync_playwright
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 2560, "height": 1440})
        for name, svg in svgs.items():
            (outdir / f"{name}.svg").write_text(svg)
            pg.set_content(f'<html><body style="margin:0">{svg}</body></html>')
            pg.wait_for_timeout(150)
            pg.locator("svg").first.screenshot(path=str(outdir / f"{name}.png"))
        b.close()


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "avatars":
        svgs = {f"mapminutes-avatar-{o}": mm_avatar(o) for o in "ABC"}
        svgs.update({f"hidden-avatar-{o}": hs_avatar(o) for o in "ABC"})
        render(svgs, sys.argv[2])
        print("wrote", len(svgs), "avatars to", sys.argv[2])
    elif len(sys.argv) >= 2 and sys.argv[1] == "channel-art":
        # the chosen avatars + banners, into assets/<channel>/
        render({"avatar": mm_avatar(CHOSEN["mapminutes"]), "banner": mm_banner()}, ROOT / "assets/mapminutes/art")
        render({"avatar": hs_avatar(CHOSEN["hidden"]), "banner": hs_banner()}, ROOT / "assets/hidden/art")
        print("wrote assets/mapminutes/art and assets/hidden/art")
    else:
        print(__doc__)
