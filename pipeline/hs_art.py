"""Hidden Systems art kit: Drip's animation rig and the flat cutaway worlds (power, water, recycling).

Drip is drawn from the same formulas as brand_art.drip_host() (body circle r=100 at the origin, tip at
y=-160, hat brim at y=-55); in his base state ("happy", no take) the rig is the canonical drawing.
New here: expressions, mouth shapes for lip-sync, and two water "tendril" arms that only grow out of the
body when he points or flips a switch (at rest the silhouette is exactly the canonical one).

Every part has a stable id ({cid}-part) so assets/hidden/drip.js can drive it from timeline time.
Cutaways are flat: ink outlines, the channel palette, no gradients except the glow of the traveller.
"""
import math

from brand_art import HS, _face  # canonical palette + face (single source of truth)

C = dict(HS)
C.update({
    "deep": "#23282C", "soil": "#262B2F", "steel": "#A3ADB5", "steel2": "#7E8A93", "wall": "#3B4248",
    "room": "#2A2F34", "glass": "#FFF6E8", "wood": "#5E4B3C", "wood2": "#46372C", "grid": "#353C42",
    "glow": "#FFD9A8",
})
INK = C["ink"]
OL = 5  # outline width of world parts


# ------------------------------------------------------------------ Drip rig

R = 100.0          # body radius in rig units
FR = R * 1.05      # face unit used by drip_host (_face(..., r * 1.05))
FCY = 0.05 * R     # face centre y
EX = 0.26 * FR     # eye x offset
EY = FCY - 0.05 * FR
ERX, ERY = 0.085 * FR, 0.085 * 1.3 * FR
SW = max(2.0, 0.045 * FR)
BROW_Y = EY - ERY - 0.09 * FR
MY = EY + ERY + 0.1 * FR   # mouth line

EXPRS = {  # expression -> (eye set, mouth)
    "happy": ("base", "smile"), "neutral": ("neutral", "rest"), "surprised": ("wide", "o"),
    "thinking": ("think", "flat"), "worried": ("worried", "frown"), "proud": ("squint", "smile"),
}
MOUTHS = ["smile", "rest", "o", "flat", "frown", "a", "e", "wide"]
EYESETS = ["base", "neutral", "wide", "think", "worried", "squint"]


def drop_path(r=R):
    return (f"M0 {-1.6 * r:.1f} C{0.15 * r:.1f} {-1.25 * r:.1f} {r:.1f} {-0.55 * r:.1f} {r:.1f} 0 "
            f"A{r:.1f} {r:.1f} 0 1 1 {-r:.1f} 0 C{-r:.1f} {-0.55 * r:.1f} {-0.15 * r:.1f} {-1.25 * r:.1f} 0 {-1.6 * r:.1f}Z")


def _eyes(name):
    """Eyes (+catchlights) and brows of one eye set."""
    ink = C["ink"]
    eyes, brows = [], []
    for s in (-1, 1):
        x = s * EX
        rx, ry, ey = ERX, ERY, EY
        if name == "wide":
            rx, ry = ERX * 1.22, ERY * 1.28
        if name == "think":
            x, ey = x + 3.5, ey - 3.0
        if name == "squint":
            eyes.append(f'<path d="M{x - rx * 1.25:.1f} {ey + 3:.1f} Q{x:.1f} {ey - ry * 1.2:.1f} {x + rx * 1.25:.1f} {ey + 3:.1f}" '
                        f'stroke="{ink}" stroke-width="{SW * 1.15:.1f}" fill="none" stroke-linecap="round"/>')
        else:
            eyes.append(f'<ellipse cx="{x:.1f}" cy="{ey:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{ink}"/>')
            eyes.append(f'<circle cx="{x - rx * 0.35:.1f}" cy="{ey - ry * 0.4:.1f}" r="{rx * 0.38:.1f}" fill="#fff"/>')
        bx = s * EX
        by = BROW_Y
        if name == "base":       # canonical happy brow (lift .03)
            d = f"M{bx - ERX * 1.2:.1f} {by:.1f} Q{bx:.1f} {by - 0.03 * FR - 0.035 * FR:.1f} {bx + ERX * 1.2:.1f} {by:.1f}"
        elif name == "neutral":
            d = f"M{bx - ERX * 1.2:.1f} {by:.1f} Q{bx:.1f} {by + 0.02 * FR - 0.035 * FR:.1f} {bx + ERX * 1.2:.1f} {by:.1f}"
        elif name == "wide":
            by -= 9
            d = f"M{bx - ERX * 1.3:.1f} {by:.1f} Q{bx:.1f} {by - 13:.1f} {bx + ERX * 1.3:.1f} {by:.1f}"
        elif name == "think":
            if s < 0:
                d = f"M{bx - ERX * 1.2:.1f} {by + 3:.1f} L{bx + ERX * 1.2:.1f} {by + 1:.1f}"
            else:
                by -= 10
                d = f"M{bx - ERX * 1.2:.1f} {by + 2:.1f} Q{bx:.1f} {by - 12:.1f} {bx + ERX * 1.3:.1f} {by + 2:.1f}"
        elif name == "worried":   # inner ends raised
            d = f"M{bx - s * ERX * 1.2:.1f} {by - 9:.1f} L{bx + s * ERX * 1.2:.1f} {by + 1:.1f}"
        else:  # squint / proud
            d = f"M{bx - ERX * 1.2:.1f} {by - 4:.1f} Q{bx:.1f} {by - 11:.1f} {bx + ERX * 1.2:.1f} {by - 4:.1f}"
        brows.append(f'<path d="{d}" stroke="{ink}" stroke-width="{SW * 0.8:.1f}" fill="none" stroke-linecap="round"/>')
    return "".join(eyes), "".join(brows)


def _mouth(name):
    ink, my = C["ink"], MY
    st = f'stroke="{ink}" stroke-width="{SW:.1f}" fill="none" stroke-linecap="round"'
    tongue = C["hat2"]
    return {
        "smile": f'<path d="M{-0.15 * FR:.1f} {my:.1f} Q0 {my + 0.15 * FR:.1f} {0.15 * FR:.1f} {my:.1f}" {st}/>',  # canonical
        "rest": f'<path d="M-10 {my + 2:.1f} Q0 {my + 8:.1f} 10 {my + 2:.1f}" {st}/>',
        "o": f'<ellipse cx="0" cy="{my + 8:.1f}" rx="9" ry="12" fill="{ink}"/>',
        "flat": f'<path d="M-9 {my + 5:.1f} L11 {my + 2:.1f}" {st}/>',
        "frown": f'<path d="M-12 {my + 9:.1f} Q0 {my:.1f} 12 {my + 9:.1f}" {st}/>',
        "a": (f'<path d="M-13 {my:.1f} Q0 {my - 3:.1f} 13 {my:.1f} Q11 {my + 16:.1f} 0 {my + 17:.1f} Q-11 {my + 16:.1f} -13 {my:.1f}Z" fill="{ink}"/>'
              f'<ellipse cx="0" cy="{my + 12:.1f}" rx="6" ry="3.5" fill="{tongue}" opacity=".8"/>'),
        "e": f'<path d="M-16 {my + 1:.1f} Q0 {my - 1:.1f} 16 {my + 1:.1f} Q14 {my + 10:.1f} 0 {my + 11:.1f} Q-14 {my + 10:.1f} -16 {my + 1:.1f}Z" fill="{ink}"/>',
        "wide": (f'<path d="M-17 {my - 2:.1f} Q0 {my - 6:.1f} 17 {my - 2:.1f} Q15 {my + 22:.1f} 0 {my + 24:.1f} Q-15 {my + 22:.1f} -17 {my - 2:.1f}Z" fill="{ink}"/>'
                 f'<ellipse cx="0" cy="{my + 17:.1f}" rx="8" ry="4.5" fill="{tongue}" opacity=".8"/>'),
    }[name]


def _arm(cid, side):
    """A water tendril that grows out of the body (scale 0 at rest). Root on the body edge, pointing outward."""
    s = 1 if side == "R" else -1
    d = (f"M0 -14 Q{s * 50} -12 {s * 82} -9 A16 16 0 1 {1 if s > 0 else 0} {s * 82} 9 Q{s * 50} 12 0 14Z")
    return (f'<g id="{cid}-arm{side}" transform="translate({s * 80} 28) scale(0)">'
            f'<path d="{d}" fill="{C["water"]}" stroke="{C["water2"]}" stroke-width="5" stroke-linejoin="round"/>'
            f'<path d="M{s * 14} -6 Q{s * 50} -6 {s * 76} -4" stroke="#fff" stroke-opacity=".45" stroke-width="4" fill="none" stroke-linecap="round"/></g>')


def drip_rig(cid, expr="happy", shadow=True):
    """Drip as an SVG group in rig units (origin = body centre). Ids: root, shadow, bod, armL/R, face, eyes,
    eyes-<set>, brows-<set>, m-<mouth>, hat. Opacity switches choose the expression and mouth."""
    eset, mouth = EXPRS.get(expr, EXPRS["happy"])
    c = C
    parts = [f'<g id="{cid}-root">']
    if shadow:
        parts.append(f'<ellipse id="{cid}-shadow" cx="0" cy="{1.02 * R:.1f}" rx="{0.62 * R:.1f}" ry="{0.08 * R:.1f}" fill="#000" opacity="0.25"/>')
    parts.append(f'<g id="{cid}-bod">')
    parts.append(_arm(cid, "L") + _arm(cid, "R"))
    parts.append(f'<path d="{drop_path()}" fill="{c["water"]}" stroke="{c["water2"]}" stroke-width="{0.05 * R:.1f}" stroke-linejoin="round"/>')
    parts.append(f'<ellipse cx="{-0.55 * R:.1f}" cy="{0.05 * R:.1f}" rx="{0.13 * R:.1f}" ry="{0.3 * R:.1f}" fill="#fff" opacity="0.5" '
                 f'transform="rotate(12 {-0.55 * R:.1f} 0.0)"/>')
    parts.append(f'<g id="{cid}-face">')
    eyes_html, brows_html = [], []
    for name in EYESETS:
        e, b = _eyes(name)
        op = 1 if name == eset else 0
        eyes_html.append(f'<g id="{cid}-eyes-{name}" opacity="{op}">{e}</g>')
        brows_html.append(f'<g id="{cid}-brows-{name}" opacity="{op}">{b}</g>')
    parts.append(f'<g id="{cid}-eyes">{"".join(eyes_html)}</g>{"".join(brows_html)}')
    for s in (-1, 1):  # cheeks (canonical)
        parts.append(f'<ellipse cx="{s * (EX + 0.13 * FR):.1f}" cy="{EY + ERY + 0.1 * FR:.1f}" rx="{0.08 * FR:.1f}" ry="{0.05 * FR:.1f}" '
                     f'fill="{c["hat"]}" opacity="0.35"/>')
    parts.append("".join(f'<g id="{cid}-m-{m}" opacity="{1 if m == mouth else 0}">{_mouth(m)}</g>' for m in MOUTHS))
    parts.append("</g>")  # face
    hy = -0.55 * R
    parts.append(f'<g id="{cid}-hat">'
                 f'<path d="M{-0.66 * R:.1f} {hy:.1f} Q{-0.64 * R:.1f} {hy - 0.66 * R:.1f} 0 {hy - 0.7 * R:.1f} '
                 f'Q{0.64 * R:.1f} {hy - 0.66 * R:.1f} {0.66 * R:.1f} {hy:.1f}Z" fill="{c["hat"]}" stroke="{c["hat2"]}" stroke-width="{0.04 * R:.1f}"/>'
                 f'<rect x="{-0.09 * R:.1f}" y="{hy - 0.69 * R:.1f}" width="{0.18 * R:.1f}" height="{0.69 * R:.1f}" rx="{0.05 * R:.1f}" fill="{c["hat2"]}" opacity="0.55"/>'
                 f'<rect x="{-0.86 * R:.1f}" y="{hy - 0.04 * R:.1f}" width="{1.72 * R:.1f}" height="{0.15 * R:.1f}" rx="{0.075 * R:.1f}" fill="{c["hat"]}" '
                 f'stroke="{c["hat2"]}" stroke-width="{0.04 * R:.1f}"/></g>')
    parts.append("</g></g>")
    return "".join(parts)


def drip_box(cid, x, y, scale=1.0, expr="happy", shadow=True):
    """Drip placed with his body centre at (x, y) in the parent's px, `scale` px per rig unit / 1."""
    return (f'<div id="{cid}" class="drip" style="position:absolute;left:{x - 270 * scale:.1f}px;top:{y - 320 * scale:.1f}px;'
            f'width:{540 * scale:.1f}px;height:{480 * scale:.1f}px" data-layout-ignore>'
            f'<svg viewBox="-270 -320 540 480" width="{540 * scale:.1f}" height="{480 * scale:.1f}" overflow="visible">'
            f'{drip_rig(cid, expr, shadow)}</svg></div>')


def canonical_check_svg(expr_rig=True):
    """Side-by-side test: brand_art.drip_host at r=100 vs the rig at rest (must match)."""
    from brand_art import drip_host
    a = drip_host(0, 0, 100)
    b = drip_rig("chk")
    return a, b


# ------------------------------------------------------------------ type helpers

def stencil(x, y, text, size, color=None, anchor="middle", spray=True, ls=4):
    """Spray-stencilled word on concrete: Barlow Condensed 800 with a soft overspray."""
    color = color or C["hat"]
    t = (f'font-family="HS Display" font-weight="800" font-size="{size}" letter-spacing="{ls}" text-anchor="{anchor}"')
    out = ""
    if spray:
        out += f'<text x="{x}" y="{y}" {t} fill="{color}" opacity=".22" filter="url(#hs-spray)">{text}</text>'
    out += f'<text x="{x}" y="{y}" {t} fill="{color}">{text}</text>'
    return out


def mono(x, y, text, size=30, color=None, anchor="start"):
    color = color or C["cream"]
    return (f'<text x="{x}" y="{y}" font-family="HS Mono" font-weight="700" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" letter-spacing="1">{text}</text>')


def plate(x, y, w, h, fill=None, bolts=True):
    """A riveted metal plate."""
    fill = fill or C["concrete2"]
    out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{INK}" stroke-width="{OL}"/>'
    if bolts:
        for bx, by in ((x + 18, y + 18), (x + w - 18, y + 18), (x + 18, y + h - 18), (x + w - 18, y + h - 18)):
            out += f'<circle cx="{bx}" cy="{by}" r="7" fill="{C["steel"]}" stroke="{INK}" stroke-width="3"/>'
    return out


SVG_DEFS = ('<defs><filter id="hs-spray" x="-20%" y="-40%" width="140%" height="180%">'
            '<feGaussianBlur stdDeviation="7"/></filter></defs>')


# ------------------------------------------------------------------ concrete wall texture (PNG, numpy)

def concrete_png(path, W, H, seed=7, panel=(540, 360)):
    """Board-formed concrete: base colour, soft mottling, panel seams and tie holes. Deterministic."""
    import numpy as np
    from PIL import Image
    rng = np.random.default_rng(seed)
    base = np.array([0x2E, 0x33, 0x38], dtype=np.float32)
    img = np.ones((H, W, 3), dtype=np.float32) * base
    # low-frequency mottling: a few blurred noise octaves
    noise = np.zeros((H, W), dtype=np.float32)
    for k, amp in ((12, 2.2), (48, 2.6), (180, 3.0)):
        small = rng.standard_normal((H // k + 2, W // k + 2)).astype(np.float32)
        up = np.array(Image.fromarray(small).resize((W + 2 * k, H + 2 * k), Image.BICUBIC))[k:k + H, k:k + W]
        noise += amp * up
    noise += rng.standard_normal((H, W)).astype(np.float32) * 1.1   # fine grain
    img += noise[..., None]
    pw, ph = panel
    for x in range(pw // 2 if W > H else 0, W, pw):        # vertical seams
        img[:, max(0, x - 2):x + 2] = base - 9
        img[:, x + 2:x + 4] = base + 5
    for y in range(ph // 2, H, ph):                          # horizontal seams
        img[max(0, y - 2):y + 2, :] = base - 9
        img[y + 2:y + 4, :] = base + 5
    yy, xx = np.mgrid[0:H, 0:W]
    for x0 in range((pw // 2 if W > H else 0) + pw // 4, W, pw // 2):   # tie holes
        for y0 in range(ph // 2 + ph // 4, H, ph // 2):
            d = (xx[max(0, y0 - 12):y0 + 12, max(0, x0 - 12):x0 + 12] - x0) ** 2 + (yy[max(0, y0 - 12):y0 + 12, max(0, x0 - 12):x0 + 12] - y0) ** 2
            sl = img[max(0, y0 - 12):y0 + 12, max(0, x0 - 12):x0 + 12]
            sl[d <= 64] = base - 14
            sl[(d > 64) & (d <= 100)] = base + 6
    Image.fromarray(np.clip(img, 0, 255).astype("uint8")).save(path, optimize=True)
    return path


# ------------------------------------------------------------------ cutaway kit (world coords, ground at GY)

GY = 1400


def k_ground(x0, x1, depth=560, seed=3):
    """Cut-open ground: surface band, soil with strata and stones."""
    import random
    r = random.Random(seed)
    out = [f'<rect x="{x0}" y="{GY}" width="{x1 - x0}" height="{depth}" fill="{C["soil"]}"/>',
           f'<rect x="{x0}" y="{GY - 6}" width="{x1 - x0}" height="30" fill="{C["line"]}" stroke="{INK}" stroke-width="{OL}"/>']
    for k in range(4):
        y = GY + 120 + k * 110
        pts = " ".join(f"{x},{y + r.randint(-14, 14)}" for x in range(x0, x1 + 200, 200))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{C["concrete"]}" stroke-width="6" opacity=".9"/>')
    for _ in range((x1 - x0) // 90):
        x, y = r.randint(x0, x1), r.randint(GY + 60, GY + depth - 20)
        out.append(f'<ellipse cx="{x}" cy="{y}" rx="{r.randint(8, 20)}" ry="{r.randint(5, 11)}" fill="{C["concrete2"]}"/>')
    return "".join(out)


def k_utilities(x0, x1):
    """What runs under every street (the channel's whole beat): gas, water main, fibre, sewer, with manholes.
    Flow stripes carry class hs-flow / hs-flow2 so the composer can run them."""
    out = []
    def pipe(y, d, body, bore, stripe, label, cls, dash="40 60"):
        out.append(f'<rect x="{x0}" y="{y - d / 2}" width="{x1 - x0}" height="{d}" fill="{body}" stroke="{INK}" stroke-width="4"/>')
        if bore:
            out.append(f'<rect x="{x0}" y="{y - d / 2 + 9}" width="{x1 - x0}" height="{d - 18}" fill="{bore}"/>')
        if stripe:
            out.append(f'<line class="{cls}" x1="{x0}" y1="{y + d * .18:.0f}" x2="{x1}" y2="{y + d * .18:.0f}" stroke="{stripe}" '
                       f'stroke-width="{max(5, d * .16):.0f}" stroke-dasharray="{dash}" stroke-linecap="round" opacity=".85"/>')
        for x in range(int(x0) + 300, int(x1), 900):
            out.append(f'<rect x="{x}" y="{y - d / 2 - 8}" width="18" height="{d + 16}" rx="4" fill="{C["steel2"]}" stroke="{INK}" stroke-width="3"/>')
            out.append(mono(x + 60, y + 9, label, 24, C["cream"]))
    pipe(GY + 110, 34, C["steel"], None, C["hat"], "GAS", "", "18 14")
    pipe(GY + 250, 86, C["water2"], C["deep"], C["water"], "WATER", "hs-flow")
    for k in range(3):
        pipe(GY + 365 + k * 26, 22, C["pipe"], None, None, "", "")
    out.append(mono(x0 + 1240, GY + 420, "FIBRE", 24, C["cream"]))
    pipe(GY + 560, 130, C["concrete2"], C["deep"], C["wood2"], "SEWER", "hs-flow2", "60 50")
    for x in range(int(x0) + 900, int(x1), 1800):
        out.append(f'<rect x="{x - 46}" y="{GY + 10}" width="92" height="{560 - 70}" fill="{C["deep"]}" stroke="{INK}" stroke-width="4"/>'
                   + "".join(f'<line x1="{x - 26}" y1="{GY + 50 + k * 54}" x2="{x + 26}" y2="{GY + 50 + k * 54}" stroke="{C["steel"]}" stroke-width="6"/>' for k in range(8))
                   + f'<rect x="{x - 62}" y="{GY - 10}" width="124" height="18" rx="6" fill="{C["steel2"]}" stroke="{INK}" stroke-width="4"/>')
    return "".join(out)


def k_lattice_tower(x, top=560, w_base=300, w_top=90, arm=440):
    """A steel lattice transmission tower standing on the ground at x. Returns (svg, [attach points])."""
    yb, yt = GY, top
    lx0, rx0, lx1, rx1 = x - w_base / 2, x + w_base / 2, x - w_top / 2, x + w_top / 2
    st = f'stroke="{C["steel"]}" stroke-width="9" stroke-linecap="round"'
    out = [f'<g>']
    out.append(f'<rect x="{lx0 - 30}" y="{yb - 26}" width="70" height="40" fill="{C["concrete2"]}" stroke="{INK}" stroke-width="4"/>'
               f'<rect x="{rx0 - 40}" y="{yb - 26}" width="70" height="40" fill="{C["concrete2"]}" stroke="{INK}" stroke-width="4"/>')
    # legs (ink under-stroke for the outline look)
    for a, b in (((lx0, yb), (lx1, yt + 60)), ((rx0, yb), (rx1, yt + 60))):
        out.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="{INK}" stroke-width="17" stroke-linecap="round"/>')
        out.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" {st}/>')
    n = 6
    for i in range(n):
        f0, f1 = i / n, (i + 1) / n
        ya, yb2 = yb + (yt + 60 - yb) * f0, yb + (yt + 60 - yb) * f1
        la, ra = lx0 + (lx1 - lx0) * f0, rx0 + (rx1 - rx0) * f0
        lb, rb = lx0 + (lx1 - lx0) * f1, rx0 + (rx1 - rx0) * f1
        out.append(f'<line x1="{la}" y1="{ya}" x2="{rb}" y2="{yb2}" stroke="{C["steel2"]}" stroke-width="6"/>')
        out.append(f'<line x1="{ra}" y1="{ya}" x2="{lb}" y2="{yb2}" stroke="{C["steel2"]}" stroke-width="6"/>')
        out.append(f'<line x1="{lb}" y1="{yb2}" x2="{rb}" y2="{yb2}" stroke="{C["steel"]}" stroke-width="7"/>')
    # peak + cross arm
    out.append(f'<path d="M{lx1} {yt + 60} L{x} {yt - 40} L{rx1} {yt + 60}" fill="none" stroke="{INK}" stroke-width="15" stroke-linejoin="round"/>'
               f'<path d="M{lx1} {yt + 60} L{x} {yt - 40} L{rx1} {yt + 60}" fill="none" {st} stroke-linejoin="round"/>')
    out.append(f'<rect x="{x - arm / 2}" y="{yt + 40}" width="{arm}" height="26" rx="6" fill="{C["steel"]}" stroke="{INK}" stroke-width="{OL}"/>')
    attach = []
    for ax in (x - arm / 2 + 30, x, x + arm / 2 - 30):
        # insulator string
        out.append(f'<line x1="{ax}" y1="{yt + 66}" x2="{ax}" y2="{yt + 150}" stroke="{INK}" stroke-width="4"/>')
        for k in range(5):
            out.append(f'<ellipse cx="{ax}" cy="{yt + 78 + k * 15}" rx="17" ry="6" fill="{C["cream"]}" stroke="{INK}" stroke-width="3"/>')
        attach.append((ax, yt + 150))
    out.append("</g>")
    return "".join(out), attach


def catenary(a, b, sag, n=24):
    pts = []
    for i in range(n + 1):
        f = i / n
        pts.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f + sag * 4 * f * (1 - f)))
    return pts


def k_transformer(x, w=220, h=280, bushings=3, label="T-1", tall=150):
    """Oil-filled transformer with radiator fins and bushings. Returns (svg, [bushing tops])."""
    y = GY - h
    out = [f'<rect x="{x - 26}" y="{y + 30}" width="26" height="{h - 50}" fill="{C["pipe2"]}" stroke="{INK}" stroke-width="4"/>',
           f'<rect x="{x + w}" y="{y + 30}" width="26" height="{h - 50}" fill="{C["pipe2"]}" stroke="{INK}" stroke-width="4"/>']
    for k in range(5):
        out.append(f'<line x1="{x - 26}" y1="{y + 50 + k * (h - 90) / 4}" x2="{x}" y2="{y + 50 + k * (h - 90) / 4}" stroke="{INK}" stroke-width="3"/>')
        out.append(f'<line x1="{x + w}" y1="{y + 50 + k * (h - 90) / 4}" x2="{x + w + 26}" y2="{y + 50 + k * (h - 90) / 4}" stroke="{INK}" stroke-width="3"/>')
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{C["pipe"]}" stroke="{INK}" stroke-width="{OL}"/>')
    out.append(f'<rect x="{x + 16}" y="{y + 16}" width="{w - 32}" height="10" rx="5" fill="#fff" opacity=".12"/>')
    tops = []
    for k in range(bushings):
        bx = x + w * (k + 1) / (bushings + 1)
        for j in range(5):
            out.append(f'<rect x="{bx - 18 + j * 1.5}" y="{y - (j + 1) * tall / 5}" width="{36 - j * 3}" height="{tall / 5 - 4}" rx="6" '
                       f'fill="{C["cream"] if j % 2 == 0 else C["steel"]}" stroke="{INK}" stroke-width="3"/>')
        tops.append((bx, y - tall))
    out.append(plate(x + w / 2 - 70, y + h / 2 - 34, 140, 68, fill=C["hat"], bolts=False))
    out.append(mono(x + w / 2, y + h / 2 + 11, label, 32, INK, "middle"))
    return "".join(out), tops


def k_plant(x):
    """Power plant cut open: hall, turbine, generator with a spinning rotor, stack. Returns (svg, spark origin)."""
    y0 = 820
    out = [f'<rect x="{x + 560}" y="420" width="90" height="{y0 - 420 + 10}" fill="{C["line"]}" stroke="{INK}" stroke-width="{OL}"/>',
           f'<rect x="{x + 560}" y="440" width="90" height="26" fill="{C["hat"]}"/><rect x="{x + 560}" y="490" width="90" height="26" fill="{C["cream"]}"/>',
           f'<rect x="{x}" y="{y0}" width="720" height="{GY - y0}" fill="{C["wall"]}" stroke="{INK}" stroke-width="{OL}"/>',
           f'<rect x="{x + 30}" y="{y0 + 60}" width="660" height="{GY - y0 - 60}" fill="{C["room"]}" stroke="{INK}" stroke-width="4"/>',
           f'<path d="M{x - 20} {y0} L{x + 360} {y0 - 120} L{x + 740} {y0}Z" fill="{C["line"]}" stroke="{INK}" stroke-width="{OL}" stroke-linejoin="round"/>']
    # crane rail
    out.append(f'<rect x="{x + 30}" y="{y0 + 88}" width="660" height="16" fill="{C["hat"]}" stroke="{INK}" stroke-width="3"/>')
    # turbine (tapered casing)
    ty = 1215
    out.append(f'<path d="M{x + 70} {ty - 60} L{x + 330} {ty - 95} L{x + 330} {ty + 95} L{x + 70} {ty + 60}Z" fill="{C["pipe"]}" stroke="{INK}" stroke-width="{OL}" stroke-linejoin="round"/>')
    for k in range(5):
        xx = x + 110 + k * 48
        hh = 64 + k * 8
        out.append(f'<line x1="{xx}" y1="{ty - hh}" x2="{xx}" y2="{ty + hh}" stroke="{C["pipe2"]}" stroke-width="6"/>')
    out.append(f'<path d="M{x + 140} {ty - 75} L{x + 140} {y0 + 140} L{x + 250} {y0 + 140}" stroke="{C["steel"]}" stroke-width="22" fill="none"/>'
               f'<path d="M{x + 140} {ty - 75} L{x + 140} {y0 + 140} L{x + 250} {y0 + 140}" stroke="{INK}" stroke-width="4" fill="none" stroke-dasharray="1 0"/>')
    # generator
    gx = x + 340
    out.append(f'<rect x="{gx}" y="{ty - 105}" width="250" height="210" rx="30" fill="{C["pipe"]}" stroke="{INK}" stroke-width="{OL}"/>')
    out.append(f'<rect x="{gx + 20}" y="{ty - 18}" width="210" height="36" fill="{C["hat"]}" stroke="{INK}" stroke-width="3"/>')
    out.append(f'<circle cx="{gx + 125}" cy="{ty}" r="70" fill="{C["deep"]}" stroke="{INK}" stroke-width="4"/>')
    spokes = "".join(f'<line x1="0" y1="0" x2="{58 * math.cos(a):.1f}" y2="{58 * math.sin(a):.1f}" stroke="{C["water"]}" stroke-width="10" stroke-linecap="round"/>'
                     for a in [k * math.pi / 3 for k in range(6)])
    out.append(f'<g transform="translate({gx + 125} {ty})"><g class="hs-spin">{spokes}<circle r="16" fill="{C["cream"]}" stroke="{INK}" stroke-width="3"/></g></g>')
    out.append(f'<rect x="{gx + 250}" y="{ty - 30}" width="{x + 720 - gx - 250 + 30}" height="60" fill="{C["steel2"]}" stroke="{INK}" stroke-width="4"/>')
    out.append(stencil(x + 520, y0 + 170, "UNIT 1", 64, C["cream"], spray=False))
    out.append(k_floor_bolts(x + 40, x + 700, GY))
    return "".join(out), (gx + 125, ty)


def k_floor_bolts(x0, x1, y):
    return "".join(f'<rect x="{x}" y="{y - 14}" width="34" height="14" fill="{C["steel2"]}" stroke="{INK}" stroke-width="3"/>' for x in range(int(x0), int(x1), 140))


def k_gantry(x, top=980, w=180):
    out = []
    for xx in (x - w / 2, x + w / 2):
        out.append(f'<rect x="{xx - 12}" y="{top}" width="24" height="{GY - top}" fill="{C["steel"]}" stroke="{INK}" stroke-width="4"/>')
    out.append(f'<rect x="{x - w / 2 - 30}" y="{top}" width="{w + 60}" height="24" fill="{C["steel"]}" stroke="{INK}" stroke-width="4"/>')
    for k in range(4):
        y = top + 40 + k * 90
        out.append(f'<line x1="{x - w / 2}" y1="{y}" x2="{x + w / 2}" y2="{y + 80}" stroke="{C["steel2"]}" stroke-width="5"/>')
        out.append(f'<line x1="{x + w / 2}" y1="{y}" x2="{x - w / 2}" y2="{y + 80}" stroke="{C["steel2"]}" stroke-width="5"/>')
    return "".join(out)


def k_fence(x0, x1, h=150):
    out = [f'<g opacity=".95">']
    out.append(f'<line x1="{x0}" y1="{GY - h}" x2="{x1}" y2="{GY - h}" stroke="{C["steel"]}" stroke-width="6"/>')
    for x in range(int(x0), int(x1) + 1, 180):
        out.append(f'<rect x="{x - 6}" y="{GY - h - 10}" width="12" height="{h + 10}" fill="{C["steel"]}" stroke="{INK}" stroke-width="3"/>')
    for x in range(int(x0), int(x1), 30):
        out.append(f'<line x1="{x}" y1="{GY - h}" x2="{x + 30}" y2="{GY}" stroke="{C["steel2"]}" stroke-width="2" opacity=".7"/>'
                   f'<line x1="{x + 30}" y1="{GY - h}" x2="{x}" y2="{GY}" stroke="{C["steel2"]}" stroke-width="2" opacity=".7"/>')
    out.append("</g>")
    return "".join(out)


def k_breaker(x):
    y = GY - 210
    return (f'<rect x="{x - 8}" y="{y + 90}" width="16" height="120" fill="{C["steel"]}" stroke="{INK}" stroke-width="3"/>'
            f'<rect x="{x - 40}" y="{y}" width="80" height="100" rx="8" fill="{C["steel2"]}" stroke="{INK}" stroke-width="4"/>'
            f'<rect x="{x - 12}" y="{y - 70}" width="24" height="70" rx="5" fill="{C["cream"]}" stroke="{INK}" stroke-width="3"/>')


def k_pole(x, top=940, arm_y=1000):
    out = [f'<rect x="{x - 16}" y="{top}" width="32" height="{GY - top}" fill="{C["wood"]}" stroke="{INK}" stroke-width="4"/>',
           f'<rect x="{x - 140}" y="{arm_y}" width="280" height="22" fill="{C["wood2"]}" stroke="{INK}" stroke-width="4"/>']
    for ax in (x - 120, x + 120):
        out.append(f'<rect x="{ax - 9}" y="{arm_y - 34}" width="18" height="34" rx="4" fill="{C["cream"]}" stroke="{INK}" stroke-width="3"/>')
    # pole-top "can" transformer
    cx, cy = x + 52, arm_y + 110
    out.append(f'<rect x="{x + 14}" y="{cy - 50}" width="18" height="16" fill="{C["steel2"]}"/>')
    out.append(f'<rect x="{cx - 38}" y="{cy - 70}" width="76" height="140" rx="16" fill="{C["steel"]}" stroke="{INK}" stroke-width="{OL}"/>')
    out.append(f'<rect x="{cx - 38}" y="{cy - 40}" width="76" height="10" fill="{C["steel2"]}"/>')
    out.append(f'<rect x="{cx - 9}" y="{cy - 100}" width="18" height="32" rx="5" fill="{C["cream"]}" stroke="{INK}" stroke-width="3"/>')
    return "".join(out), (x - 120, arm_y - 34), (cx, cy - 100), (cx + 38, cy + 20)


def k_house(x, w=760):
    """Cut-open house: roof, outside wall with meter, a room with a conduit to a pendant bulb and a switch."""
    y_roof, y_wall = 860, 980
    out = [f'<path d="M{x - 40} {y_wall} L{x + w / 2} {y_roof - 90} L{x + w + 40} {y_wall}Z" fill="{C["line"]}" stroke="{INK}" stroke-width="{OL}" stroke-linejoin="round"/>',
           f'<rect x="{x}" y="{y_wall}" width="{w}" height="{GY - y_wall}" fill="{C["wall"]}" stroke="{INK}" stroke-width="{OL}"/>',
           f'<rect x="{x + 70}" y="{y_wall + 30}" width="{w - 100}" height="{GY - y_wall - 30}" fill="{C["room"]}" stroke="{INK}" stroke-width="4"/>']
    # meter on the outside wall
    mx, my = x + 34, 1210
    out.append(f'<rect x="{mx - 26}" y="{my - 40}" width="52" height="80" rx="10" fill="{C["steel"]}" stroke="{INK}" stroke-width="4"/>'
               f'<circle cx="{mx}" cy="{my - 6}" r="17" fill="{C["cream"]}" stroke="{INK}" stroke-width="3"/>')
    # weatherhead
    out.append(f'<rect x="{mx - 7}" y="1100" width="14" height="{my - 40 - 1100}" fill="{C["steel2"]}" stroke="{INK}" stroke-width="3"/>'
               f'<path d="M{mx - 16} 1100 Q{mx} 1080 {mx + 16} 1100Z" fill="{C["steel2"]}" stroke="{INK}" stroke-width="3"/>')
    # conduit inside the room: up from the meter, along the ceiling, down to the bulb
    bx, by = x + 380, 1090
    cy_ = y_wall + 70
    cpath = f"M{x + 70} {my} L{x + 120} {my} L{x + 120} {cy_} L{bx} {cy_} L{bx} {by - 40}"
    out.append(f'<path d="{cpath}" stroke="{INK}" stroke-width="30" fill="none" stroke-linejoin="round"/>'
               f'<path d="{cpath}" stroke="{C["pipe"]}" stroke-width="20" fill="none" stroke-linejoin="round"/>')
    # switch box + conduit to it
    sx, sy = x + 560, 1210
    out.append(f'<path d="M{x + 120} {cy_} L{sx} {cy_} L{sx} {sy - 40}" stroke="{INK}" stroke-width="30" fill="none" stroke-linejoin="round"/>'
               f'<path d="M{x + 120} {cy_} L{sx} {cy_} L{sx} {sy - 40}" stroke="{C["pipe"]}" stroke-width="20" fill="none" stroke-linejoin="round"/>')
    out.append(f'<rect x="{sx - 32}" y="{sy - 46}" width="64" height="92" rx="8" fill="{C["cream"]}" stroke="{INK}" stroke-width="4"/>'
               f'<rect x="{sx - 10}" y="{sy - 26}" width="20" height="30" rx="4" fill="{C["steel2"]}" stroke="{INK}" stroke-width="3"/>')
    # bulb (glow is a live element added by the composer)
    out.append(f'<rect x="{bx - 14}" y="{by - 44}" width="28" height="26" fill="{C["steel2"]}" stroke="{INK}" stroke-width="3"/>'
               f'<circle cx="{bx}" cy="{by}" r="30" fill="{C["glass"]}" stroke="{INK}" stroke-width="4" opacity=".9"/>')
    return "".join(out), {"meter": (mx, my), "weather": (mx, 1090), "bulb": (bx, by), "conduit": [(x + 70, my), (x + 120, my), (x + 120, cy_), (bx, cy_), (bx, by - 20)],
                          "switch": (sx, sy)}


def power_strip():
    """The power-grid cutaway: plant -> step-up -> towers -> substation -> pole -> house.
    Returns dict(mid, near, far, fore, path=[(x,y)...], marks={name: distance along path}, width, bulb)."""
    mid, near, far, fore = [], [], [], []
    L = 5400
    near.append(k_ground(-600, L + 600, depth=900))
    near.append(k_utilities(-600, L + 600))
    plant, gen = k_plant(80)
    mid.append(plant)
    xf, xf_tops = k_transformer(930, w=230, h=270, bushings=3, label="STEP-UP", tall=160)
    mid.append(xf)
    t1, a1 = k_lattice_tower(1520)
    t2, a2 = k_lattice_tower(2330)
    t3, a3 = k_lattice_tower(3080)
    # sign on tower 2 (the number lives in the world)
    mid.append(t1 + t2 + t3)
    # substation
    mid.append(k_fence(3260, 3980))
    mid.append(k_gantry(3360, top=980))
    mid.append(k_breaker(3480))
    sx, s_tops = k_transformer(3560, w=200, h=230, bushings=2, label="T-2", tall=120)
    mid.append(sx)
    mid.append(k_gantry(3900, top=1080, w=120))
    pole, p_arm, p_can, p_out = k_pole(4230)
    mid.append(pole)
    house, hp = k_house(4560)
    mid.append(house)

    # conductors (drawn wires) + the traveller path
    wires = []
    def wire(pts, w=6, color=None):
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        wires.append(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{w + 4}" stroke-linecap="round" stroke-linejoin="round"/>'
                     f'<path d="{d}" fill="none" stroke="{color or C["steel"]}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')
    for k in range(3):
        wire([xf_tops[k], (xf_tops[k][0] + 160, xf_tops[k][1] - 80)] + catenary((xf_tops[k][0] + 160, xf_tops[k][1] - 80), a1[k], 40)[1:], 5)
        wire(catenary(a1[k], a2[k], 150), 5)
        wire(catenary(a2[k], a3[k], 150), 5)
        wire(catenary(a3[k], (3360 - 60 + k * 60, 1004), 110), 5)
    wire(catenary((3900 - 50, 1084), p_arm, 70), 5)
    wire(catenary((3900 + 50, 1084), (4230 + 120, 966), 70), 5)
    wire(catenary(p_out, hp["weather"], 60), 4)
    mid.append("".join(wires))

    # traveller path: generator -> bus -> step-up -> centre conductor -> substation -> pole can -> house -> bulb
    path = [gen, (gen[0] + 160, gen[1]), (950, gen[1]), (xf_tops[1][0], gen[1]), xf_tops[1], (xf_tops[1][0] + 160, xf_tops[1][1] - 80)]
    path += catenary((xf_tops[1][0] + 160, xf_tops[1][1] - 80), a1[1], 40)[1:]
    path += catenary(a1[1], a2[1], 150)[1:]
    path += catenary(a2[1], a3[1], 150)[1:]
    path += catenary(a3[1], (3360, 1004), 110)[1:]
    path += [(3360, 1060), (3460, 1100), (s_tops[0][0], s_tops[0][1]), (s_tops[0][0], 1240), (s_tops[1][0], 1240), s_tops[1],
             (3850, 1084)]
    path += catenary((3850, 1084), p_arm, 70)[1:]
    path += [(p_can[0], p_can[1] - 10), (p_can[0], p_can[1] + 60), p_out]
    path += catenary(p_out, hp["weather"], 60)[1:]
    path += [hp["meter"]] + hp["conduit"]
    # sign plate on tower 2
    sign = (plate(2330 - 370, 850, 740, 320, fill=C["concrete"]) +
            stencil(2330, 1030, "160,000", 190, C["hat"]) +
            stencil(2330, 1100, "MILES", 64, C["cream"], spray=False, ls=12) +
            mono(2330, 1144, "US HIGH-VOLTAGE LINES · EIA 2016", 27, C["steel"], "middle"))
    marks = {}
    dists = [0.0]
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        dists.append(dists[-1] + math.hypot(x1 - x0, y1 - y0))
    def near_d(pt):
        best = min(range(len(path)), key=lambda i: (path[i][0] - pt[0]) ** 2 + (path[i][1] - pt[1]) ** 2)
        return round(dists[best], 1)
    marks.update({"gen": 0.0, "stepup": near_d(xf_tops[1]), "tower1": near_d(a1[1]), "tower2": near_d(a2[1]), "tower3": near_d(a3[1]),
                  "substation": near_d((3360, 1004)), "t2": near_d(s_tops[1]), "pole": near_d(p_can), "house": near_d(hp["weather"]),
                  "bulb": round(dists[-1], 1)})
    # far layer (parallax ~.35): blueprint grid + distant skyline, drawn in its own space
    for x in range(-400, int(L * .45) + 2400, 80):
        far.append(f'<line x1="{x}" y1="-400" x2="{x}" y2="2400" stroke="{C["grid"]}" stroke-width="2"/>')
    for y in range(-400, 2400, 80):
        far.append(f'<line x1="-400" y1="{y}" x2="{int(L * .45) + 2400}" y2="{y}" stroke="{C["grid"]}" stroke-width="2"/>')
    import random
    r = random.Random(11)
    x = -300
    while x < L * .45 + 2200:
        w = r.randint(60, 160)
        h = r.randint(120, 380)
        far.append(f'<rect x="{x}" y="{1240 - h}" width="{w}" height="{h + 400}" fill="#353B41"/>')
        if r.random() < .35:
            far.append(f'<rect x="{x + w / 2 - 6}" y="{1240 - h - 60}" width="12" height="60" fill="#353B41"/>')
        x += w + r.randint(10, 70)
    far.append('<path d="M340 1240 Q360 1000 300 860 L520 860 Q470 1000 490 1240Z" fill="#383E44"/>')  # distant cooling tower
    # fore layer (parallax ~1.6): foreground cable reel, fence posts, cones; drawn in fore space
    # (fore layer left empty in v1: foreground props fought the captions)
    return {"mid": "".join(mid), "sign": sign, "near": "".join(near), "far": "".join(far), "fore": "".join(fore),
            "path": [(round(x, 1), round(y, 1)) for x, y in path], "marks": marks, "width": L, "bulb": hp["bulb"],
            "switch": hp["switch"]}


# ------------------------------------------------------------------ other kits (water, sewage, recycling)

def k_pipe_run(x0, x1, y, d=90, color=None, flange_every=320):
    """A horizontal pipe in section with flanges; the bore is drawn so a traveller can move inside."""
    color = color or C["pipe"]
    out = [f'<rect x="{x0}" y="{y - d / 2}" width="{x1 - x0}" height="{d}" fill="{color}" stroke="{INK}" stroke-width="{OL}"/>',
           f'<rect x="{x0}" y="{y - d / 2 + 14}" width="{x1 - x0}" height="{d - 28}" fill="{C["deep"]}"/>',
           f'<rect x="{x0}" y="{y + d / 2 - 30}" width="{x1 - x0}" height="16" fill="{C["water"]}" opacity=".75"/>']
    for x in range(int(x0) + 60, int(x1), flange_every):
        out.append(f'<rect x="{x}" y="{y - d / 2 - 12}" width="22" height="{d + 24}" rx="4" fill="{C["pipe2"]}" stroke="{INK}" stroke-width="4"/>')
    return "".join(out)


def k_manhole(x, depth=420):
    return (f'<rect x="{x - 50}" y="{GY}" width="100" height="{depth}" fill="{C["deep"]}" stroke="{INK}" stroke-width="{OL}"/>'
            + "".join(f'<line x1="{x - 30}" y1="{GY + 40 + k * 60}" x2="{x + 30}" y2="{GY + 40 + k * 60}" stroke="{C["steel"]}" stroke-width="7"/>' for k in range(depth // 60))
            + f'<rect x="{x - 70}" y="{GY - 10}" width="140" height="18" rx="6" fill="{C["steel2"]}" stroke="{INK}" stroke-width="4"/>')


def k_treatment(x):
    """Wastewater / water treatment: a clarifier (circular tank in section) and an aeration basin with bubbles."""
    out = [f'<rect x="{x}" y="{GY - 200}" width="420" height="220" fill="{C["concrete2"]}" stroke="{INK}" stroke-width="{OL}"/>',
           f'<rect x="{x + 20}" y="{GY - 170}" width="380" height="170" fill="{C["water2"]}"/>',
           f'<rect x="{x + 20}" y="{GY - 170}" width="380" height="24" fill="{C["water"]}"/>']
    for k in range(14):
        bx = x + 40 + (k * 53) % 360
        by = GY - 30 - (k * 37) % 120
        out.append(f'<circle class="hs-bubble" cx="{bx}" cy="{by}" r="{6 + k % 3 * 3}" fill="none" stroke="{C["cream"]}" stroke-width="3" opacity=".8"/>')
    cx = x + 700
    out.append(f'<path d="M{cx - 220} {GY - 180} L{cx + 220} {GY - 180} L{cx + 220} {GY - 40} L{cx} {GY + 30} L{cx - 220} {GY - 40}Z" '
               f'fill="{C["concrete2"]}" stroke="{INK}" stroke-width="{OL}" stroke-linejoin="round"/>')
    out.append(f'<path d="M{cx - 200} {GY - 150} L{cx + 200} {GY - 150} L{cx + 200} {GY - 50} L{cx} {GY + 8} L{cx - 200} {GY - 50}Z" fill="{C["water2"]}"/>')
    out.append(f'<path d="M{cx - 200} {GY - 60} L{cx} {GY + 8} L{cx + 200} {GY - 60}Z" fill="{C["wood2"]}" opacity=".9"/>')
    out.append(f'<rect x="{cx - 8}" y="{GY - 260}" width="16" height="250" fill="{C["steel"]}" stroke="{INK}" stroke-width="3"/>'
               f'<rect x="{cx - 230}" y="{GY - 200}" width="460" height="14" fill="{C["hat"]}" stroke="{INK}" stroke-width="3"/>')
    out.append(stencil(x + 210, GY - 230, "AERATION", 46, C["cream"], spray=False))
    out.append(stencil(cx, GY - 290, "CLARIFIER", 46, C["cream"], spray=False))
    return "".join(out)


def k_sorting_line(x, n_items=9):
    """Recycling sorting line: conveyor, overhead magnet, disc screen, bales."""
    y = GY - 260
    out = [f'<rect x="{x}" y="{y}" width="900" height="40" rx="20" fill="{C["concrete2"]}" stroke="{INK}" stroke-width="{OL}"/>']
    for k in range(0, 900, 60):
        out.append(f'<circle cx="{x + 20 + k}" cy="{y + 20}" r="12" fill="{C["steel"]}" stroke="{INK}" stroke-width="3"/>')
    for k in range(4):
        out.append(f'<rect x="{x + 40 + k * 260}" y="{y + 40}" width="22" height="{GY - y - 40}" fill="{C["steel2"]}" stroke="{INK}" stroke-width="3"/>')
    shapes = []
    for k in range(n_items):
        ix = x + 40 + k * 95
        kind = k % 3
        if kind == 0:   # bottle
            shapes.append(f'<rect x="{ix}" y="{y - 70}" width="34" height="70" rx="10" fill="{C["water"]}" stroke="{INK}" stroke-width="3"/>')
        elif kind == 1:  # can
            shapes.append(f'<rect x="{ix}" y="{y - 52}" width="38" height="52" rx="5" fill="{C["steel"]}" stroke="{INK}" stroke-width="3"/>')
        else:            # cardboard
            shapes.append(f'<rect x="{ix}" y="{y - 46}" width="64" height="46" fill="{C["wood"]}" stroke="{INK}" stroke-width="3"/>')
    out.append(f'<g class="hs-belt">{"".join(shapes)}</g>')
    out.append(f'<rect x="{x + 520}" y="{y - 300}" width="220" height="110" rx="12" fill="{C["hat"]}" stroke="{INK}" stroke-width="{OL}"/>'
               f'<rect x="{x + 600}" y="{y - 420}" width="60" height="120" fill="{C["steel2"]}" stroke="{INK}" stroke-width="4"/>')
    out.append(stencil(x + 630, y - 228, "MAGNET", 44, INK, spray=False))
    for k in range(3):   # bales
        out.append(f'<rect x="{x + 980 + k * 130}" y="{GY - 120}" width="120" height="120" fill="{[C["water"], C["steel"], C["wood"]][k]}" stroke="{INK}" stroke-width="{OL}"/>'
                   f'<line x1="{x + 980 + k * 130}" y1="{GY - 80}" x2="{x + 1100 + k * 130}" y2="{GY - 80}" stroke="{INK}" stroke-width="4"/>'
                   f'<line x1="{x + 980 + k * 130}" y1="{GY - 40}" x2="{x + 1100 + k * 130}" y2="{GY - 40}" stroke="{INK}" stroke-width="4"/>')
    return "".join(out)


def kit_sheet_svg(W=1920, H=1080):
    """One sheet that shows the reusable cutaway parts at a glance (review / previews)."""
    inner = [f'<rect width="{W}" height="{H}" fill="{C["concrete"]}"/>']
    for x in range(0, W, 80):
        inner.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="{C["grid"]}" stroke-width="2"/>')
    for y in range(0, H, 80):
        inner.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="{C["grid"]}" stroke-width="2"/>')
    s = .46
    g = [k_ground(-200, 4300, 900), k_utilities(-200, 4300), k_manhole(560, 520)]
    g.append(k_treatment(760))
    g.append(k_sorting_line(1800))
    xf, _ = k_transformer(3240, label="T-3")
    g.append(xf)
    t, _ = k_lattice_tower(3800, top=560)
    g.append(t)
    inner.append(f'<g transform="translate(70 {800 - GY * s:.0f}) scale({s})">{"".join(g)}</g>')
    inner.append(stencil(60, 130, "CUTAWAY KIT", 96, C["hat"], anchor="start"))
    inner.append(mono(64, 180, "under every street: gas · water · fibre · sewer   above: treatment · sorting line · transformer · tower", 26, C["steel"]))
    return "".join(inner)
