"""Worlds for cinematic scenes. Each returns {far, mid, near, fore} HTML in world coordinates:
x is relative to the frame centre (0), y from the top. Designed at floor line F=790 (landscape)
and shifted down by oy = F - 790 for taller frames. Backgrounds extend far past the frame so
camera moves and 9:16 framing never show an edge."""
from cinema import world_street_night


def _shift(html, oy):
    return f'<div style="position:absolute;left:0;top:{oy}px">{html}</div>' if oy else html


def _bokeh(spots):
    return "".join(
        f'<div style="position:absolute;left:{x}px;top:{y}px;width:{r * 2}px;height:{r * 2}px;border-radius:50%;'
        f'background:radial-gradient(circle,rgba({c},1) 0%,rgba({c},0) 70%);opacity:{op}"></div>'
        for x, y, r, c, op in spots)


def street(F, H, sign="FOOD COURT"):
    oy = F - 790
    w = world_street_night("w", sign_text=sign)
    sky_fix = (f'<div style="position:absolute;left:-1800px;top:{-1400}px;width:3600px;height:1500px;'
               f'background:linear-gradient(#070912,#0A0D19)"></div>')
    ground_fix = (f'<div style="position:absolute;left:-1800px;top:{1150}px;width:3600px;height:{max(0, H - F + 400)}px;background:#120F16"></div>')
    return {"far": sky_fix + _shift(w["far"], oy), "mid": _shift(w["mid"], oy),
            "near": _shift(w["near"] + ground_fix, oy), "fore": _shift(w["fore"], oy)}


def foodcourt(F, H):
    oy = F - 790
    tiles = "".join(f'<rect x="{-1700 + i * 64}" y="-600" width="2" height="1400" fill="#000" opacity=".12"/>' for i in range(54))
    tiles += "".join(f'<rect x="-1700" y="{-600 + j * 64}" width="3400" height="2" fill="#000" opacity=".12"/>' for j in range(22))
    lamps = "".join(
        f'<g><rect x="{x - 2}" y="-600" width="4" height="{690}" fill="#1A1214"/>'
        f'<path d="M{x - 60},{100} Q{x},{40} {x + 60},{100} Z" fill="#2A1C1E"/>'
        f'<ellipse cx="{x}" cy="104" rx="46" ry="10" fill="#FFE2A6"/>'
        f'<path d="M{x - 46},104 L{x - 320},720 L{x + 320},720 L{x + 46},104 Z" fill="url(#cone)"/></g>'
        for x in (-900, 0, 900))
    far = (f'<div style="position:absolute;left:-1800px;top:-1400px;width:3600px;height:2400px;'
           f'background:linear-gradient(#1E1517 0%,#3A2628 55%,#2A1C1E 100%)"></div>'
           f'<svg style="position:absolute;left:-1700px;top:0" width="3400" height="800" viewBox="-1700 -600 3400 1400" overflow="visible">'
           f'<defs><linearGradient id="cone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFD58F" stop-opacity=".22"/>'
           f'<stop offset="1" stop-color="#FFD58F" stop-opacity="0"/></linearGradient></defs>{tiles}'
           f'<rect x="-760" y="140" width="1520" height="420" rx="18" fill="#141012" stroke="#5A3E30" stroke-width="10"/>'
           f'<rect x="-760" y="140" width="1520" height="420" rx="18" fill="none" stroke="#FFB45A" stroke-width="3" opacity=".35"/>'
           f'<rect x="-1500" y="140" width="560" height="420" rx="14" fill="#201618"/>'
           f'<rect x="940" y="140" width="560" height="420" rx="14" fill="#201618"/>{lamps}</svg>')
    dogs = "".join(f'<rect x="{560 + i * 46}" y="574" width="36" height="22" rx="11" fill="#C9472F"/>' for i in range(6))
    mid = (f'<svg style="position:absolute;left:-1700px;top:0" width="3400" height="1000" viewBox="-1700 0 3400 1000">'
           f'<rect x="-1700" y="640" width="3400" height="26" fill="#C9CDD4"/>'
           f'<rect x="-1700" y="666" width="3400" height="130" fill="#7A2E2A"/>'
           f'<rect x="-1700" y="666" width="3400" height="8" fill="#000" opacity=".25"/>'
           f'<rect x="540" y="560" width="300" height="80" rx="10" fill="#9EA3AB"/><rect x="548" y="568" width="284" height="40" fill="#2B2224"/>{dogs}'
           f'<rect x="-860" y="440" width="220" height="200" rx="14" fill="#5B5F68"/><rect x="-840" y="460" width="180" height="70" rx="8" fill="#1F2733"/>'
           + "".join(f'<rect x="{-836 + k * 60}" y="540" width="16" height="40" fill="#C9CDD4"/>' for k in range(3)) +
           f'<path d="M-560,600 h70 l-6,40 h-58z" fill="#F4EEE4"/><path d="M-570,560 h90 l-6,40 h-78z" fill="#E9E2D6"/>'
           f'</svg>')
    near = (f'<div style="position:absolute;left:-1800px;top:796px;width:3600px;height:{max(500, H - F + 300)}px;'
            f'background:linear-gradient(#3A2A26 0%,#2A1F1D 40%,#1C1514 100%)"></div>'
            + "".join(f'<div style="position:absolute;left:{x}px;top:820px;width:420px;height:160px;border-radius:50%;'
                      f'background:radial-gradient(ellipse,rgba(255,200,130,.22),rgba(255,200,130,0) 70%);filter:blur(4px)"></div>' for x in (-1110, -210, 690)))
    fore = _bokeh([(-1250, 80, 110, "255,200,130", .45), (1120, 140, 90, "255,180,110", .4),
                   (-1300, 780, 150, "255,190,120", .35), (1180, 820, 140, "255,210,150", .3)])
    fore += ('<svg style="position:absolute;left:820px;top:760px" width="320" height="360" viewBox="0 0 320 360">'
             '<rect x="20" y="150" width="120" height="210" rx="16" fill="#C9CDD4"/><rect x="34" y="120" width="92" height="40" rx="10" fill="#9EA3AB"/>'
             '<rect x="180" y="90" width="70" height="270" rx="30" fill="#D63A2C"/><rect x="198" y="40" width="34" height="60" rx="10" fill="#E8E1D6"/></svg>')
    return {"far": _shift(far, oy), "mid": _shift(mid, oy), "near": _shift(near, oy), "fore": _shift(fore, oy)}


def aisle(F, H):
    oy = F - 790
    racks = ""
    palette = ["#C98E5A", "#B9784A", "#8E9AA8", "#D6C3A0", "#A8574A", "#6E8C7A", "#E2D1B3"]
    for i, x in enumerate(range(-1700, 1700, 420)):
        racks += f'<rect x="{x}" y="-300" width="22" height="1090" fill="#E07B2C"/><rect x="{x + 398}" y="-300" width="22" height="1090" fill="#E07B2C"/>'
        for lvl, y in enumerate((60, 300, 540)):
            racks += f'<rect x="{x}" y="{y + 180}" width="420" height="18" fill="#2F5DA8"/>'
            bx = x + 30
            k = 0
            while bx < x + 380:
                bw = 70 + ((i * 7 + lvl * 13 + k * 31) % 60)
                bh = 90 + ((i * 11 + lvl * 5 + k * 17) % 80)
                if bx + bw > x + 395:
                    break
                racks += f'<rect x="{bx}" y="{y + 180 - bh}" width="{bw}" height="{bh}" rx="4" fill="{palette[(i + lvl + k) % len(palette)]}"/>'
                bx += bw + 8
                k += 1
    far = (f'<div style="position:absolute;left:-1800px;top:-1400px;width:3600px;height:2400px;background:linear-gradient(#0F1218,#1B2029 60%,#232832)"></div>'
           + "".join(f'<div style="position:absolute;left:-1500px;top:{y}px;width:3000px;height:10px;border-radius:5px;background:#EAF2FF;'
                     f'box-shadow:0 0 40px 12px rgba(200,220,255,.35);opacity:{op}"></div>' for y, op in ((-120, .5), (0, .7), (80, .9))))
    mid = (f'<svg style="position:absolute;left:-1700px;top:0" width="3400" height="800" viewBox="-1700 0 3400 800" overflow="visible">{racks}'
           f'<rect x="-1700" y="760" width="3400" height="40" fill="#11141A" opacity=".6"/></svg>')
    near = (f'<div style="position:absolute;left:-1800px;top:790px;width:3600px;height:{max(500, H - F + 300)}px;'
            f'background:linear-gradient(#5A606B 0%,#3B4049 35%,#262A31 100%)"></div>'
            f'<div style="position:absolute;left:-1800px;top:800px;width:3600px;height:120px;background:linear-gradient(rgba(234,242,255,.18),rgba(234,242,255,0));"></div>')
    fore = ('<svg style="position:absolute;left:-1340px;top:700px" width="520" height="420" viewBox="0 0 520 420">'
            '<path d="M40,60 L480,60 L440,260 L90,260 Z" fill="none" stroke="#B9C0CC" stroke-width="12"/>'
            + "".join(f'<path d="M{70 + i * 46},60 L{100 + i * 40},260" stroke="#B9C0CC" stroke-width="6"/>' for i in range(9))
            + '<path d="M40,60 L10,10" stroke="#B9C0CC" stroke-width="12"/><circle cx="120" cy="330" r="34" fill="#1A1C22"/><circle cx="410" cy="330" r="34" fill="#1A1C22"/>'
            '<rect x="80" y="270" width="380" height="14" fill="#B9C0CC"/></svg>')
    fore += _bokeh([(1050, 60, 120, "200,220,255", .35), (1200, 700, 140, "255,190,120", .3)])
    return {"far": _shift(far, oy), "mid": _shift(mid, oy), "near": _shift(near, oy), "fore": _shift(fore, oy)}


def stage(F, H, warm="255,190,110"):
    oy = F - 790
    far = (f'<div style="position:absolute;left:-1800px;top:-1400px;width:3600px;height:2600px;'
           f'background:radial-gradient(ellipse at 50% 62%,#2A2433 0%,#15141C 45%,#0A0A0F 80%)"></div>'
           + "".join(f'<div style="position:absolute;left:{-1700 + i * 120}px;top:-600px;width:2px;height:1400px;background:rgba(243,238,227,.03)"></div>' for i in range(29)))
    mid = (f'<div style="position:absolute;left:-620px;top:-200px;width:1240px;height:1000px;'
           f'background:linear-gradient(rgba({warm},.16),rgba({warm},0) 85%);clip-path:polygon(42% 0,58% 0,100% 100%,0 100%)"></div>'
           f'<div style="position:absolute;left:-90px;top:-230px;width:180px;height:40px;border-radius:50%;background:rgba({warm},.6);filter:blur(10px)"></div>')
    near = (f'<div style="position:absolute;left:-1800px;top:790px;width:3600px;height:{max(500, H - F + 300)}px;'
            f'background:linear-gradient(#1A1820 0%,#100F15 60%,#0A0A0E 100%)"></div>'
            f'<div style="position:absolute;left:-700px;top:770px;width:1400px;height:200px;border-radius:50%;'
            f'background:radial-gradient(ellipse,rgba({warm},.20),rgba({warm},0) 70%)"></div>')
    fore = _bokeh([(-1200, 120, 100, f"{warm}", .30), (1100, 60, 80, "150,180,255", .25),
                   (-1250, 800, 140, f"{warm}", .25), (1150, 840, 130, f"{warm}", .22)])
    return {"far": _shift(far, oy), "mid": _shift(mid, oy), "near": _shift(near, oy), "fore": _shift(fore, oy)}


def cinema(F, H):
    """Auditorium seen from the aisle: a glowing screen, a projector beam, rows of seats."""
    oy = F - 790
    far = (f'<div style="position:absolute;left:-1800px;top:-1400px;width:3600px;height:2600px;background:linear-gradient(#07080D,#0E0F16 60%,#14121A)"></div>'
           f'<div style="position:absolute;left:-900px;top:40px;width:1800px;height:560px;border-radius:10px;'
           f'background:linear-gradient(160deg,#DCE8FF,#9DB6E8 55%,#6E86C4);box-shadow:0 0 160px 50px rgba(150,180,255,.35)"></div>'
           f'<div style="position:absolute;left:-1700px;top:620px;width:3400px;height:200px;background:radial-gradient(ellipse at 50% 0%,rgba(150,180,255,.25),rgba(0,0,0,0) 70%)"></div>')
    beam = (f'<div style="position:absolute;left:-1500px;top:-300px;width:2400px;height:900px;'
            f'background:linear-gradient(200deg,rgba(220,230,255,.0) 20%,rgba(220,230,255,.10) 50%,rgba(220,230,255,0) 80%);'
            f'clip-path:polygon(100% 0,96% 0,10% 100%,40% 100%)"></div>')
    rows = ""
    for r, (y, h, sc) in enumerate(((560, 70, .7), (640, 90, .85), (740, 120, 1.0))):
        w = int(120 * sc)
        rows += "".join(f'<rect x="{-1700 + i * (w + 14) + (r * 37) % 60}" y="{y}" width="{w}" height="{h}" rx="{int(22 * sc)}" fill="{"#5E1F24" if r < 2 else "#73252B"}"/>'
                        for i in range(int(3400 / (w + 14)) + 1))
    mid = beam + (f'<svg style="position:absolute;left:-1700px;top:0" width="3400" height="900" viewBox="-1700 0 3400 900">{rows}'
                  f'<rect x="-1700" y="860" width="3400" height="40" fill="#0C0A10"/></svg>')
    near = (f'<div style="position:absolute;left:-1800px;top:800px;width:3600px;height:{max(500, H - F + 300)}px;'
            f'background:linear-gradient(#241A22,#140F15 50%,#0B090D)"></div>'
            + "".join(f'<div style="position:absolute;left:{x}px;top:{810 + k * 70}px;width:16px;height:8px;border-radius:4px;background:#FFC86A;'
                      f'box-shadow:0 0 14px 4px rgba(255,190,90,.45)"></div>' for k, x in enumerate((-360, -330, -300)))
            )
    fore = ('<svg style="position:absolute;left:-1500px;top:820px" width="3000" height="400" viewBox="0 0 3000 400">'
            '<rect x="0" y="40" width="520" height="360" rx="60" fill="#3A1216"/><rect x="2480" y="20" width="520" height="380" rx="60" fill="#3A1216"/></svg>')
    fore += _bokeh([(-1150, 120, 90, "160,190,255", .25), (1050, 90, 110, "160,190,255", .22)])
    return {"far": _shift(far, oy), "mid": _shift(mid, oy), "near": _shift(near, oy), "fore": _shift(fore, oy)}


WORLDS = {"street": street, "foodcourt": foodcourt, "aisle": aisle, "stage": stage, "cinema": cinema}


def get_world(spec, F, H):
    """'street' or 'street:CINEMA' (the part after ':' is the street sign)."""
    name, _, arg = (spec or "stage").partition(":")
    if name == "street" and arg:
        return street(F, H, sign=arg)
    return WORLDS[name](F, H)
DEPTHS = {"far": 3.0, "mid": 1.5, "content": 1.0, "near": 1.0, "fore": 0.55}
