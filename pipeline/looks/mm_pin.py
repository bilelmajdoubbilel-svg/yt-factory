"""Pin, the Map Minutes host, as an animatable rig.

Same drawing as brand_art.pin_host (the canonical Pin, decided with the owner on 6 Nov 2026): every shape uses
pin_host's formulas, only split into groups with ids so assets/mapminutes/mm.js can act with it.
Added for acting, never a redesign: expressions (neutral, happy, surprised, thinking, worried), mouth shapes
(smile, talk-a, talk-b, o, flat, grin), eye and brow moves, and the compass needle as a reaction (it swings,
trembles, spins and points; it always points where the story goes).

Local units: head radius R = 100, the pin's tip (ground contact) at (0, 0), head centre (0, -185).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from brand_art import MM  # noqa: E402

R = 100.0
CX, CY = 0.0, -1.85 * R          # head centre
NM = CY - R - 0.2 * R            # needle pivot (y)
VB = (-175, -372, 350, 400)      # viewBox: needle top -347, shadow +10
EXPRS = ("neutral", "happy", "surprised", "thinking", "worried")
MOUTHS = ("smile", "talka", "talkb", "o", "flat", "grin", "wobble")


def _f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def face_geom():
    """pin_host -> _face(cx, cy, r * 0.95, eye_dx=0.23, eye_y=-0.1, eye=0.075). Returns the numbers."""
    r = R * 0.95
    ex, ey = 0.23 * r, CY - 0.1 * r
    rx, ry = 0.075 * r, 0.075 * 1.3 * r
    sw = max(2.0, 0.045 * r)
    brow_y = ey - ry - 0.09 * r
    lift = 0.03 * r
    my = ey + ry + 0.1 * r
    return dict(r=r, ex=ex, ey=ey, rx=rx, ry=ry, sw=sw, brow_y=brow_y, lift=lift, my=my)


def pin_svg(pid, scale=1.0, mouth="smile", expr="neutral", shadow=True, extra_style=""):
    """The rig as an <svg>. Its root <g id="{pid}-rig"> has the tip at (0, 0) in the svg's own space."""
    c = MM
    r = R
    g = face_geom()
    tip = CY + 1.85 * r
    body = (f"M{_f(CX)} {_f(tip)} C{_f(CX - 0.35 * r)} {_f(CY + 1.35 * r)} {_f(CX - r)} {_f(CY + 0.75 * r)} {_f(CX - r)} {_f(CY)} "
            f"A{_f(r)} {_f(r)} 0 1 1 {_f(CX + r)} {_f(CY)} C{_f(CX + r)} {_f(CY + 0.75 * r)} {_f(CX + 0.35 * r)} {_f(CY + 1.35 * r)} "
            f"{_f(CX)} {_f(tip)}Z")
    ny0, ny1 = CY - r - 0.62 * r, CY - r + 0.2 * r
    w = 0.13 * r
    ink = c["ink"]
    p = []
    if shadow:
        p.append(f'<g id="{pid}-shadow"><ellipse cx="{_f(CX)}" cy="{_f(tip + 0.03 * r)}" rx="{_f(0.42 * r)}" ry="{_f(0.07 * r)}" fill="{ink}" opacity="0.22"/></g>')
    p.append(f'<g id="{pid}-lean"><g id="{pid}-squash"><g id="{pid}-body">')
    p.append(f'<g id="{pid}-needle">'
             f'<path d="M{_f(CX)} {_f(ny0)} L{_f(CX + w)} {_f(NM)} L{_f(CX - w)} {_f(NM)}Z" fill="{c["coral"]}"/>'
             f'<path d="M{_f(CX - w)} {_f(NM)} L{_f(CX + w)} {_f(NM)} L{_f(CX)} {_f(ny1)}Z" fill="{ink}"/>'
             f'<circle cx="{_f(CX)}" cy="{_f(NM)}" r="{_f(0.065 * r)}" fill="#F2C14E" stroke="{ink}" stroke-width="{_f(0.025 * r)}"/></g>')
    p.append(f'<path d="{body}" fill="{c["ocean"]}" stroke="{c["ocean2"]}" stroke-width="{_f(0.05 * r)}" stroke-linejoin="round"/>')
    p.append(f'<path d="M{_f(CX - 0.78 * r)} {_f(CY - 0.25 * r)} A{_f(0.82 * r)} {_f(0.82 * r)} 0 0 1 {_f(CX - 0.2 * r)} {_f(CY - 0.8 * r)}" '
             f'stroke="#fff" stroke-opacity="0.28" stroke-width="{_f(0.07 * r)}" fill="none" stroke-linecap="round"/>')
    p.append(f'<circle cx="{_f(CX)}" cy="{_f(CY)}" r="{_f(0.64 * r)}" fill="{c["cream"]}" stroke="{c["ocean2"]}" stroke-width="{_f(0.04 * r)}"/>')
    # face: same geometry as brand_art._face; groups for acting
    ex, ey, rx, ry, sw = g["ex"], g["ey"], g["rx"], g["ry"], g["sw"]
    rr, brow_y, lift, my = g["r"], g["brow_y"], g["lift"], g["my"]
    p.append(f'<g id="{pid}-face">')
    for s, side in ((-1, "l"), (1, "r")):
        x = CX + s * ex
        p.append(f'<ellipse cx="{_f(CX + s * (ex + 0.13 * rr))}" cy="{_f(ey + ry + 0.1 * rr)}" rx="{_f(0.08 * rr)}" ry="{_f(0.05 * rr)}" '
                 f'fill="{c["coral"]}" opacity="0.35" id="{pid}-cheek{side}"/>')
    for s, side in ((-1, "l"), (1, "r")):
        x = CX + s * ex
        p.append(f'<g id="{pid}-eye{side}"><g id="{pid}-lid{side}">'
                 f'<ellipse cx="{_f(x)}" cy="{_f(ey)}" rx="{_f(rx)}" ry="{_f(ry)}" fill="{ink}"/>'
                 f'<circle cx="{_f(x - rx * 0.35)}" cy="{_f(ey - ry * 0.4)}" r="{_f(rx * 0.38)}" fill="#fff"/></g></g>')
        p.append(f'<g id="{pid}-brow{side}"><path d="M{_f(x - rx * 1.2)} {_f(brow_y)} Q{_f(x)} {_f(brow_y - lift - 0.035 * rr)} '
                 f'{_f(x + rx * 1.2)} {_f(brow_y)}" stroke="{ink}" stroke-width="{_f(sw * 0.8)}" fill="none" stroke-linecap="round"/></g>')
    m = {
        "smile": f'<path d="M{_f(CX - 0.15 * rr)} {_f(my)} Q{_f(CX)} {_f(my + 0.15 * rr)} {_f(CX + 0.15 * rr)} {_f(my)}" stroke="{ink}" stroke-width="{_f(sw)}" fill="none" stroke-linecap="round"/>',
        "talka": f'<path d="M{_f(CX - 0.14 * rr)} {_f(my - 0.01 * rr)} Q{_f(CX)} {_f(my + 0.26 * rr)} {_f(CX + 0.14 * rr)} {_f(my - 0.01 * rr)}Z" fill="{ink}" stroke="{ink}" stroke-width="{_f(sw * 0.6)}" stroke-linejoin="round"/>'
                 f'<ellipse cx="{_f(CX)}" cy="{_f(my + 0.085 * rr)}" rx="{_f(0.06 * rr)}" ry="{_f(0.03 * rr)}" fill="{c["coral"]}"/>',
        "talkb": f'<ellipse cx="{_f(CX)}" cy="{_f(my + 0.045 * rr)}" rx="{_f(0.075 * rr)}" ry="{_f(0.05 * rr)}" fill="{ink}"/>',
        "o": f'<ellipse cx="{_f(CX)}" cy="{_f(my + 0.06 * rr)}" rx="{_f(0.065 * rr)}" ry="{_f(0.085 * rr)}" fill="{ink}"/>',
        "flat": f'<path d="M{_f(CX - 0.1 * rr)} {_f(my + 0.05 * rr)} L{_f(CX + 0.09 * rr)} {_f(my + 0.02 * rr)}" stroke="{ink}" stroke-width="{_f(sw)}" stroke-linecap="round"/>',
        "grin": f'<path d="M{_f(CX - 0.19 * rr)} {_f(my - 0.02 * rr)} Q{_f(CX)} {_f(my + 0.3 * rr)} {_f(CX + 0.19 * rr)} {_f(my - 0.02 * rr)}Z" fill="{ink}" stroke="{ink}" stroke-width="{_f(sw * 0.6)}" stroke-linejoin="round"/>'
                f'<ellipse cx="{_f(CX)}" cy="{_f(my + 0.12 * rr)}" rx="{_f(0.08 * rr)}" ry="{_f(0.04 * rr)}" fill="{c["coral"]}"/>',
        "wobble": f'<path d="M{_f(CX - 0.13 * rr)} {_f(my + 0.06 * rr)} q{_f(0.043 * rr)} {_f(-0.05 * rr)} {_f(0.087 * rr)} 0 t{_f(0.087 * rr)} 0 t{_f(0.087 * rr)} 0" stroke="{ink}" stroke-width="{_f(sw * 0.9)}" fill="none" stroke-linecap="round"/>',
    }
    p.append(f'<g id="{pid}-mouth">' + "".join(
        f'<g id="{pid}-m-{k}" opacity="{1 if k == mouth else 0}">{v}</g>' for k, v in m.items()) + "</g>")
    p.append("</g>")   # face
    p.append("</g></g></g>")   # body, squash, lean
    x0, y0, w0, h0 = VB
    W, H = w0 * scale, h0 * scale
    return (f'<svg id="{pid}-svg" xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {w0} {h0}" width="{_f(W)}" height="{_f(H)}" '
            f'overflow="visible" style="display:block;overflow:visible;{extra_style}"><g id="{pid}-rig" data-expr="{expr}">{"".join(p)}</g></svg>')


def pin_box(pid, x, y, r_px, mouth="smile", expr="neutral", flip=False, z=5):
    """A positioned Pin: tip at screen (x, y), head radius r_px. The wrapper div is what moves (hops, slides);
    the svg inside is never transformed by CSS (GSAP animates the groups)."""
    s = r_px / R
    x0, y0, w0, h0 = VB
    left, top = x + x0 * s, y + y0 * s
    inner = pin_svg(pid, s, mouth, expr)
    flip_css = "transform:scaleX(-1);" if flip else ""
    return (f'<div id="{pid}" class="pin" data-r="{_f(r_px)}" style="position:absolute;left:{_f(left)}px;top:{_f(top)}px;'
            f'width:{_f(w0 * s)}px;height:{_f(h0 * s)}px;z-index:{z}"><div id="{pid}-flip" style="{flip_css}">{inner}</div></div>')
