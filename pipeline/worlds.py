"""Worlds for cinematic scenes (v2, "lit"). Each returns {far, mid, near, fore} HTML in world coordinates:
x is relative to the frame centre (0), y from the top. Designed at floor line F=790 (landscape) and
shifted down by oy = F - 790 for taller frames. Backgrounds extend far past the frame so camera moves
and 9:16 framing never show an edge.

v2 changes (owner feedback "the background is mostly black"):
- golden-hour / daylight palettes, mid-tone walls, light floors; nothing near-black behind the host
- a lit "studio" for data scenes (stage = studio), with a screen panel the charts sit on
- live ambient motion that is cheap to render (transforms and opacity only): passers-by, rising
  coins, steam, sign flicker, drifting bokeh. Returned as world["live"][layer] + world["anim"].
The old night worlds stay in worlds_night.py.
"""
from cinema import _windows

DEPTHS = {"far": 3.0, "mid": 1.5, "content": 1.0, "near": 1.0, "fore": 0.55}


def _shift(html, oy):
    return f'<div style="position:absolute;left:0;top:{oy}px">{html}</div>' if oy else html


def _bokeh(spots, cls=""):
    return "".join(
        f'<div class="{cls}" style="position:absolute;left:{x}px;top:{y}px;width:{r * 2}px;height:{r * 2}px;border-radius:50%;'
        f'background:radial-gradient(circle,rgba({c},1) 0%,rgba({c},0) 70%);opacity:{op}"></div>'
        for x, y, r, c, op in spots)


def _walkers(specs, y, scale=1.0, cls="amb-walk"):
    """Soft silhouettes of passers-by (secondary characters). specs: (x, colour, height, speed px/s)."""
    out = []
    for i, (x, col, h, v) in enumerate(specs):
        hh = h * scale
        head = hh * .2
        out.append(
            f'<div class="{cls}" data-v="{v}" style="position:absolute;left:{x}px;top:{y - hh}px;width:{hh * .42:.0f}px;height:{hh:.0f}px">'
            f'<div style="position:absolute;left:{hh * .21 - head / 2:.0f}px;top:0;width:{head:.0f}px;height:{head:.0f}px;border-radius:50%;background:{col}"></div>'
            f'<div style="position:absolute;left:0;top:{head * 1.05:.0f}px;width:{hh * .42:.0f}px;height:{hh * .5:.0f}px;border-radius:{hh * .2:.0f}px {hh * .2:.0f}px 12px 12px;background:{col}"></div>'
            f'<div style="position:absolute;left:{hh * .08:.0f}px;top:{head * 1.05 + hh * .46:.0f}px;width:{hh * .1:.0f}px;height:{hh * .34:.0f}px;border-radius:8px;background:{col}"></div>'
            f'<div style="position:absolute;left:{hh * .24:.0f}px;top:{head * 1.05 + hh * .46:.0f}px;width:{hh * .1:.0f}px;height:{hh * .34:.0f}px;border-radius:8px;background:{col}"></div>'
            f'</div>')
    return "".join(out)


def _coins(spots, cls="amb-coin"):
    return "".join(
        f'<div class="{cls}" data-dy="{dy}" style="position:absolute;left:{x}px;top:{y}px;width:{r * 2}px;height:{r * 2}px;border-radius:50%;'
        f'background:radial-gradient(circle at 35% 35%,#FFE9A8,#F2B53A 60%,#C98516);opacity:{op};filter:blur({b}px);'
        f'box-shadow:0 0 30px rgba(255,200,90,.6);display:flex;align-items:center;justify-content:center;'
        f'font-family:PL Display;font-size:{int(r * 1.1)}px;color:#B9770F">$</div>'
        for x, y, r, op, b, dy in spots)


# ------------------------------------------------------------------ street at golden hour

def street(F, H, sign="FOOD COURT"):
    oy = F - 790
    sky = ('<div style="position:absolute;left:-1800px;top:-1400px;width:3600px;height:2200px;'
           'background:linear-gradient(#3B4F95 0%,#5E62A8 45%,#C9788A 70%,#F2A06A 86%,#F8C98A 100%)"></div>')
    sun = ('<div style="position:absolute;left:250px;top:120px;width:520px;height:520px;border-radius:50%;'
           'background:radial-gradient(circle,rgba(255,236,190,.95) 0%,rgba(255,200,130,.55) 30%,rgba(255,170,110,0) 70%)"></div>')
    city = "".join(
        f'<rect x="{-2200 + i * 150}" y="{380 - (37 * i * 7919 % 230)}" width="{110 + (i * 53 % 60)}" height="900" fill="{"#6E5C93" if i % 2 else "#7D6AA0"}"/>'
        for i in range(30))
    city += "".join(f'<rect x="{-2160 + (i * 97 % 4200)}" y="{230 + (i * 61 % 300)}" width="12" height="16" fill="#FFE1A6" opacity=".75"/>'
                    for i in range(90))
    far = sky + sun + f'<svg style="position:absolute;left:-2240px;top:0" width="4480" height="1080" viewBox="-2240 0 4480 1080">{city}</svg>'

    stripes = "".join(f'<path d="M{-1500 + i * 120},300 h120 v70 q-60,26 -120,0z" fill="{"#E0574E" if i % 2 == 0 else "#FFF4E0"}"/>'
                      for i in range(25))
    mid = (f'<svg style="position:absolute;left:-1700px;top:0" width="3400" height="1080" viewBox="-1700 0 3400 1080">'
           f'<defs><linearGradient id="win" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFE3A8"/><stop offset="1" stop-color="#F09A55"/></linearGradient>'
           f'<radialGradient id="glowS" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#FFE7B8" stop-opacity=".7"/><stop offset="1" stop-color="#FFE7B8" stop-opacity="0"/></radialGradient></defs>'
           f'<rect x="-1600" y="150" width="3200" height="640" fill="#8E5E6E"/>'
           f'<rect x="-1600" y="150" width="3200" height="640" fill="#000" opacity=".06"/>'
           f'<rect x="-1600" y="140" width="3200" height="22" fill="#6D4656"/>'
           f'<rect x="-360" y="176" width="720" height="104" rx="14" fill="#3B2638" stroke="#F2C35A" stroke-width="5"/>'
           f'<ellipse cx="0" cy="228" rx="460" ry="120" fill="url(#glowS)"/>'
           f'<text x="0" y="252" text-anchor="middle" font-family="PL Display" font-size="64" fill="#FFE9BD">{sign}</text>'
           f'{stripes}{_windows(7, -1490, 330, 90, 400, 330, "#FFE3A8", "#F09A55")}'
           f'<rect x="-1600" y="760" width="3200" height="30" fill="#6D4656"/></svg>')
    near = (f'<div style="position:absolute;left:-1800px;top:780px;width:3600px;height:{max(560, H - F + 400)}px;'
            f'background:linear-gradient(#B4889A 0%,#9A7486 30%,#7C5E70 100%)"></div>'
            f'<div style="position:absolute;left:-1800px;top:780px;width:3600px;height:16px;background:#D9B1B9"></div>'
            + "".join(f'<div style="position:absolute;left:{-1490 + i * 420 + 40}px;top:800px;width:250px;height:190px;border-radius:50%;'
                      f'background:radial-gradient(ellipse at 50% 20%,rgba(255,214,150,.45),rgba(255,214,150,0) 70%)"></div>' for i in range(7)) +
            f'<svg style="position:absolute;left:820px;top:120px" width="160" height="900" viewBox="0 0 160 900">'
            f'<rect x="70" y="60" width="16" height="840" fill="#4A3346"/><rect x="40" y="40" width="80" height="28" rx="10" fill="#4A3346"/>'
            f'<circle cx="80" cy="80" r="70" fill="#FFE2A6" opacity=".35"/><circle cx="80" cy="74" r="14" fill="#FFF3D6"/></svg>')
    fore = _bokeh([(-1150, 120, 90, "255,214,150", .55), (1010, 90, 110, "255,236,200", .4),
                   (-1300, 700, 130, "255,200,140", .45), (1250, 760, 120, "255,190,130", .45)], "amb-bokeh")
    sign_glow = ('<div class="amb-flick" style="position:absolute;left:-420px;top:150px;width:840px;height:160px;border-radius:50%;'
                 'background:radial-gradient(ellipse,rgba(255,236,190,.55),rgba(255,236,190,0) 70%)"></div>')
    live = {"mid": sign_glow + _walkers([(-1500, "rgba(74,52,84,.55)", 260, 70), (-300, "rgba(90,60,90,.5)", 240, -55),
                                         (900, "rgba(70,50,80,.55)", 270, 62)], 770, 1.0)}
    anim = [("mid", ".amb-walk", "walk"), ("mid", ".amb-flick", "flicker"), ("fore", ".amb-bokeh", "drift")]
    w = {"far": _shift(far, oy), "mid": _shift(mid, oy), "near": _shift(near, oy), "fore": _shift(fore, oy)}
    w["live"] = {k: _shift(v, oy) for k, v in live.items()}
    w["anim"] = anim
    return w


# ------------------------------------------------------------------ food court, daytime

def foodcourt(F, H):
    oy = F - 790
    tiles = "".join(f'<rect x="{-1700 + i * 64}" y="-600" width="2" height="1400" fill="#8A6A48" opacity=".10"/>' for i in range(54))
    lamps = "".join(
        f'<g><rect x="{x - 2}" y="-600" width="4" height="{690}" fill="#6A4A3A"/>'
        f'<path d="M{x - 60},{100} Q{x},{40} {x + 60},{100} Z" fill="#C9472F"/>'
        f'<ellipse cx="{x}" cy="104" rx="46" ry="10" fill="#FFF0C8"/>'
        f'<path d="M{x - 46},104 L{x - 320},720 L{x + 320},720 L{x + 46},104 Z" fill="url(#cone)"/></g>'
        for x in (-900, 0, 900))
    menu = "".join(
        f'<rect x="{x}" y="160" width="460" height="300" rx="16" fill="#2E2A33"/>'
        f'<rect x="{x}" y="160" width="460" height="56" rx="16" fill="#C9472F"/>'
        + "".join(f'<rect x="{x + 30}" y="{240 + r * 52}" width="{220 + (r * 37 % 90)}" height="18" rx="9" fill="#F3E7D2" opacity=".75"/>'
                  f'<rect x="{x + 360}" y="{240 + r * 52}" width="70" height="18" rx="9" fill="#F6C453"/>' for r in range(4))
        for x in (-1180, -230, 720))
    far = (f'<div style="position:absolute;left:-1800px;top:-1400px;width:3600px;height:2400px;'
           f'background:linear-gradient(#F4E6CC 0%,#EBD3AE 55%,#D9B88C 100%)"></div>'
           f'<svg style="position:absolute;left:-1700px;top:0" width="3400" height="800" viewBox="-1700 -600 3400 1400" overflow="visible">'
           f'<defs><linearGradient id="cone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFF4D6" stop-opacity=".55"/>'
           f'<stop offset="1" stop-color="#FFF4D6" stop-opacity="0"/></linearGradient></defs>{tiles}{menu}{lamps}</svg>')
    dogs = "".join(f'<rect x="{560 + i * 46}" y="574" width="36" height="22" rx="11" fill="#C9472F"/>' for i in range(6))
    mid = (f'<svg style="position:absolute;left:-1700px;top:0" width="3400" height="1000" viewBox="-1700 0 3400 1000">'
           f'<rect x="-1700" y="640" width="3400" height="26" fill="#E8ECF1"/>'
           f'<rect x="-1700" y="666" width="3400" height="130" fill="#C9472F"/>'
           f'<rect x="-1700" y="666" width="3400" height="8" fill="#000" opacity=".15"/>'
           + "".join(f'<rect x="{-1700 + i * 170}" y="700" width="90" height="10" rx="5" fill="#F6C453" opacity=".8"/>' for i in range(20)) +
           f'<rect x="540" y="560" width="300" height="80" rx="10" fill="#B9BEC6"/><rect x="548" y="568" width="284" height="40" fill="#4A3F42"/>{dogs}'
           f'<rect x="-860" y="440" width="220" height="200" rx="14" fill="#8E949E"/><rect x="-840" y="460" width="180" height="70" rx="8" fill="#2F3B4D"/>'
           + "".join(f'<rect x="{-836 + k * 60}" y="540" width="16" height="40" fill="#E8ECF1"/>' for k in range(3)) +
           f'<path d="M-560,600 h70 l-6,40 h-58z" fill="#FFFFFF"/><path d="M-570,560 h90 l-6,40 h-78z" fill="#F4EEE4"/>'
           f'</svg>')
    steam = "".join(f'<div class="amb-steam" data-dy="{110 + k * 25}" style="position:absolute;left:{600 + k * 70}px;top:520px;width:70px;height:70px;border-radius:50%;'
                    f'background:radial-gradient(circle,rgba(255,255,255,.55),rgba(255,255,255,0) 70%)"></div>' for k in range(3))
    near = (f'<div style="position:absolute;left:-1800px;top:796px;width:3600px;height:{max(560, H - F + 400)}px;'
            f'background:linear-gradient(#C98A64 0%,#B67552 40%,#9A5F43 100%)"></div>'
            + "".join(f'<div style="position:absolute;left:{-1800 + i * 160}px;top:796px;width:2px;height:{max(560, H - F + 400)}px;background:rgba(80,40,25,.18)"></div>' for i in range(23))
            + "".join(f'<div style="position:absolute;left:{x}px;top:820px;width:420px;height:160px;border-radius:50%;'
                      f'background:radial-gradient(ellipse,rgba(255,236,190,.35),rgba(255,236,190,0) 70%)"></div>' for x in (-1110, -210, 690)))
    fore = _bokeh([(-1250, 80, 110, "255,236,190", .45), (1120, 140, 90, "255,220,160", .4),
                   (-1300, 780, 150, "255,214,150", .35), (1180, 820, 140, "255,230,180", .3)], "amb-bokeh")
    live = {"far": _walkers([(-1400, "rgba(150,110,90,.45)", 230, 50), (200, "rgba(140,100,85,.45)", 220, -45),
                             (1100, "rgba(160,120,95,.45)", 240, 40)], 640, 1.0),
            "mid": steam}
    anim = [("far", ".amb-walk", "walk"), ("mid", ".amb-steam", "rise"), ("fore", ".amb-bokeh", "drift")]
    w = {"far": _shift(far, oy), "mid": _shift(mid, oy), "near": _shift(near, oy), "fore": _shift(fore, oy)}
    w["live"] = {k: _shift(v, oy) for k, v in live.items()}
    w["anim"] = anim
    return w


# ------------------------------------------------------------------ warehouse aisle, bright

def aisle(F, H):
    oy = F - 790
    racks = ""
    palette = ["#E7A86A", "#D98C55", "#A9B8C8", "#F1DDB8", "#D2705E", "#86B39A", "#F6E6C6"]
    for i, x in enumerate(range(-1700, 1700, 420)):
        racks += f'<rect x="{x}" y="-300" width="22" height="1090" fill="#F08A35"/><rect x="{x + 398}" y="-300" width="22" height="1090" fill="#F08A35"/>'
        for lvl, y in enumerate((60, 300, 540)):
            racks += f'<rect x="{x}" y="{y + 180}" width="420" height="18" fill="#3D72C4"/>'
            bx, k = x + 30, 0
            while bx < x + 380:
                bw = 70 + ((i * 7 + lvl * 13 + k * 31) % 60)
                bh = 90 + ((i * 11 + lvl * 5 + k * 17) % 80)
                if bx + bw > x + 395:
                    break
                racks += f'<rect x="{bx}" y="{y + 180 - bh}" width="{bw}" height="{bh}" rx="4" fill="{palette[(i + lvl + k) % len(palette)]}"/>'
                bx += bw + 8
                k += 1
    far = (f'<div style="position:absolute;left:-1800px;top:-1400px;width:3600px;height:2400px;background:linear-gradient(#DCE4EE,#C3CEDB 60%,#AEBBCB)"></div>'
           + "".join(f'<div style="position:absolute;left:-1500px;top:{y}px;width:3000px;height:12px;border-radius:6px;background:#FFFFFF;'
                     f'box-shadow:0 0 40px 14px rgba(255,255,255,.7);opacity:{op}"></div>' for y, op in ((-120, .7), (0, .85), (80, 1))))
    mid = (f'<svg style="position:absolute;left:-1700px;top:0" width="3400" height="800" viewBox="-1700 0 3400 800" overflow="visible">{racks}'
           f'<rect x="-1700" y="760" width="3400" height="40" fill="#5E6672" opacity=".35"/></svg>')
    near = (f'<div style="position:absolute;left:-1800px;top:790px;width:3600px;height:{max(560, H - F + 400)}px;'
            f'background:linear-gradient(#C9CED6 0%,#AEB5BF 35%,#8F97A3 100%)"></div>'
            f'<div style="position:absolute;left:-1800px;top:800px;width:3600px;height:140px;background:linear-gradient(rgba(255,255,255,.45),rgba(255,255,255,0));"></div>')
    fore = ('<svg style="position:absolute;left:-1340px;top:700px" width="520" height="420" viewBox="0 0 520 420">'
            '<path d="M40,60 L480,60 L440,260 L90,260 Z" fill="none" stroke="#7D8796" stroke-width="12"/>'
            + "".join(f'<path d="M{70 + i * 46},60 L{100 + i * 40},260" stroke="#7D8796" stroke-width="6"/>' for i in range(9))
            + '<path d="M40,60 L10,10" stroke="#7D8796" stroke-width="12"/><circle cx="120" cy="330" r="34" fill="#3A3F48"/><circle cx="410" cy="330" r="34" fill="#3A3F48"/>'
            '<rect x="80" y="270" width="380" height="14" fill="#7D8796"/></svg>')
    fore += _bokeh([(1050, 60, 120, "255,255,255", .45), (1200, 700, 140, "255,214,150", .3)], "amb-bokeh")
    live = {"mid": _walkers([(-1300, "rgba(70,90,120,.4)", 300, 55), (1000, "rgba(90,80,110,.4)", 290, -48)], 785, 1.0)}
    anim = [("mid", ".amb-walk", "walk"), ("fore", ".amb-bokeh", "drift")]
    w = {"far": _shift(far, oy), "mid": _shift(mid, oy), "near": _shift(near, oy), "fore": _shift(fore, oy)}
    w["live"] = {k: _shift(v, oy) for k, v in live.items()}
    w["anim"] = anim
    return w


# ------------------------------------------------------------------ studio (data scenes)

def studio(F, H, warm="255,214,140"):
    """A lit explainer set: teal wall, warm key light, wooden floor, plants. Charts sit on a screen
    panel that cine.py puts behind the content, so the frame is bright but numbers stay readable."""
    oy = F - 790
    slats = "".join(f'<rect x="{x}" y="-700" width="46" height="1500" rx="6" fill="#C98E5A" opacity=".9"/>'
                    for x in list(range(-1700, -1060, 70)) + list(range(1080, 1720, 70)))
    shelves = "".join(
        f'<rect x="{x}" y="{y}" width="300" height="14" rx="7" fill="#8E5A36"/>'
        f'<rect x="{x + 30}" y="{y - 70}" width="50" height="70" rx="8" fill="#F2E3C4"/>'
        f'<rect x="{x + 100}" y="{y - 90}" width="36" height="90" rx="6" fill="#E46C55"/>'
        f'<circle cx="{x + 220}" cy="{y - 40}" r="40" fill="#4C9A6A"/><rect x="{x + 200}" y="{y - 20}" width="40" height="20" rx="4" fill="#D98C55"/>'
        for x, y in ((-1000, 300), (-1000, 520), (700, 260), (700, 480)))
    far = (f'<div style="position:absolute;left:-1800px;top:-1400px;width:3600px;height:2400px;'
           f'background:linear-gradient(#245F78 0%,#2F7F95 55%,#5AA8B5 100%)"></div>'
           f'<div style="position:absolute;left:-1100px;top:-300px;width:2200px;height:1300px;border-radius:50%;'
           f'background:radial-gradient(ellipse,rgba({warm},.55) 0%,rgba({warm},.18) 40%,rgba({warm},0) 70%)"></div>'
           f'<svg style="position:absolute;left:-1700px;top:0" width="3400" height="800" viewBox="-1700 0 3400 800" overflow="visible">{slats}{shelves}'
           f'<text x="-1350" y="170" font-family="PL Display" font-size="150" fill="#F6C453" opacity=".9">$</text>'
           f'<text x="1300" y="200" font-family="PL Display" font-size="130" fill="#FF8A5B" opacity=".85">%</text></svg>')
    mid = (f'<svg style="position:absolute;left:-1700px;top:0" width="3400" height="900" viewBox="-1700 0 3400 900">'
           f'<path d="M-1450,790 l40,-170 h150 l40,170z" fill="#E46C55"/><circle cx="-1335" cy="560" r="110" fill="#3E8A5C"/><circle cx="-1260" cy="500" r="80" fill="#4FA56E"/>'
           f'<path d="M1250,790 l30,-150 h130 l30,150z" fill="#F6C453"/><circle cx="1345" cy="560" r="100" fill="#3E8A5C"/><circle cx="1290" cy="500" r="70" fill="#5DB37A"/>'
           f'</svg>')
    near = (f'<div style="position:absolute;left:-1800px;top:790px;width:3600px;height:{max(560, H - F + 400)}px;'
            f'background:linear-gradient(#D9A06C 0%,#C2875A 35%,#A36B44 100%)"></div>'
            + "".join(f'<div style="position:absolute;left:{-1800 + i * 210}px;top:790px;width:3px;height:{max(560, H - F + 400)}px;background:rgba(90,50,25,.18)"></div>' for i in range(18))
            + f'<div style="position:absolute;left:-760px;top:810px;width:1520px;height:200px;border-radius:50%;background:radial-gradient(ellipse,rgba(255,236,190,.45),rgba(255,236,190,0) 70%)"></div>')
    fore = ('<svg style="position:absolute;left:-1500px;top:520px" width="600" height="700" viewBox="0 0 600 700">'
            '<path d="M80,700 C60,520 140,380 300,300 C220,420 200,560 210,700Z" fill="#2F6E4A" opacity=".9"/>'
            '<path d="M150,700 C180,520 300,430 470,410 C340,480 270,580 260,700Z" fill="#3E8A5C" opacity=".9"/></svg>')
    fore += _bokeh([(1050, 60, 120, "255,236,190", .45), (-1200, 120, 100, f"{warm}", .35),
                    (1150, 840, 130, f"{warm}", .3)], "amb-bokeh")
    live = {"far": _coins([(-700, 520, 26, .55, 4, 260), (-420, 700, 20, .45, 5, 320), (520, 600, 24, .5, 4, 280),
                           (780, 380, 18, .4, 6, 240), (-80, 760, 16, .35, 6, 300)])}
    anim = [("far", ".amb-coin", "rise"), ("fore", ".amb-bokeh", "drift")]
    w = {"far": _shift(far, oy), "mid": _shift(mid, oy), "near": _shift(near, oy), "fore": _shift(fore, oy)}
    w["live"] = {k: _shift(v, oy) for k, v in live.items()}
    w["anim"] = anim
    w["panel"] = True
    return w


# ------------------------------------------------------------------ cinema auditorium (lifted)

def cinema(F, H):
    """Auditorium seen from the aisle: a glowing screen, a projector beam, rows of seats and an audience."""
    oy = F - 790
    far = (f'<div style="position:absolute;left:-1800px;top:-1400px;width:3600px;height:2600px;background:linear-gradient(#2A2440,#3A2E52 60%,#4A3558)"></div>'
           f'<div style="position:absolute;left:-900px;top:40px;width:1800px;height:560px;border-radius:10px;'
           f'background:linear-gradient(160deg,#F3F7FF,#BCD0F4 55%,#8EA6DC);box-shadow:0 0 220px 80px rgba(170,195,255,.45)"></div>'
           f'<div style="position:absolute;left:-1700px;top:620px;width:3400px;height:240px;background:radial-gradient(ellipse at 50% 0%,rgba(170,195,255,.4),rgba(0,0,0,0) 70%)"></div>')
    beam = (f'<div style="position:absolute;left:-1500px;top:-300px;width:2400px;height:900px;'
            f'background:linear-gradient(200deg,rgba(230,238,255,.0) 20%,rgba(230,238,255,.16) 50%,rgba(230,238,255,0) 80%);'
            f'clip-path:polygon(100% 0,96% 0,10% 100%,40% 100%)"></div>')
    rows = ""
    for r, (y, h, sc) in enumerate(((560, 70, .7), (640, 90, .85), (740, 120, 1.0))):
        w_ = int(120 * sc)
        rows += "".join(f'<rect x="{-1700 + i * (w_ + 14) + (r * 37) % 60}" y="{y}" width="{w_}" height="{h}" rx="{int(22 * sc)}" fill="{"#A13A44" if r < 2 else "#B5424D"}"/>'
                        + (f'<circle cx="{-1700 + i * (w_ + 14) + (r * 37) % 60 + w_ / 2}" cy="{y - 6}" r="{int(26 * sc)}" fill="#3A2E52"/>' if (i * 7 + r * 3) % 3 else "")
                        for i in range(int(3400 / (w_ + 14)) + 1))
    mid = beam + (f'<svg style="position:absolute;left:-1700px;top:0" width="3400" height="900" viewBox="-1700 0 3400 900">{rows}'
                  f'<rect x="-1700" y="860" width="3400" height="40" fill="#2A2032"/></svg>')
    near = (f'<div style="position:absolute;left:-1800px;top:800px;width:3600px;height:{max(560, H - F + 400)}px;'
            f'background:linear-gradient(#5A3A52,#46304A 50%,#36263C)"></div>'
            + "".join(f'<div style="position:absolute;left:{x}px;top:{810 + k * 70}px;width:16px;height:8px;border-radius:4px;background:#FFC86A;'
                      f'box-shadow:0 0 14px 4px rgba(255,190,90,.45)"></div>' for k, x in enumerate((-360, -330, -300))))
    fore = ('<svg style="position:absolute;left:-1500px;top:820px" width="3000" height="400" viewBox="0 0 3000 400">'
            '<rect x="0" y="40" width="520" height="360" rx="60" fill="#7A2A34"/><rect x="2480" y="20" width="520" height="380" rx="60" fill="#7A2A34"/></svg>')
    fore += _bokeh([(-1150, 120, 90, "190,210,255", .35), (1050, 90, 110, "190,210,255", .3)], "amb-bokeh")
    w = {"far": _shift(far, oy), "mid": _shift(mid, oy), "near": _shift(near, oy), "fore": _shift(fore, oy)}
    screen_light = ('<div class="amb-flick" style="position:absolute;left:-900px;top:40px;width:1800px;height:560px;border-radius:10px;'
                    'background:linear-gradient(120deg,rgba(255,255,255,.35),rgba(255,214,160,.25),rgba(160,200,255,.35))"></div>')
    w["live"] = {"far": _shift(screen_light, oy)}
    w["anim"] = [("far", ".amb-flick", "flicker_soft"), ("fore", ".amb-bokeh", "drift")]
    return w


# ------------------------------------------------------------------ airport gate, daylight

def _plane(x, y, s, cls, v, tail="#2F7F95"):
    return (f'<div class="{cls}" data-v="{v}" style="position:absolute;left:{x}px;top:{y}px;width:{int(420 * s)}px;height:{int(120 * s)}px">'
            f'<svg viewBox="0 0 420 120" width="100%" height="100%">'
            f'<path d="M20,70 Q20,52 60,50 L350,50 Q400,50 410,66 Q400,82 350,82 L60,82 Q20,82 20,70Z" fill="#FFFFFF"/>'
            f'<path d="M40,50 L20,8 L58,8 L96,50Z" fill="{tail}"/>'
            f'<path d="M170,66 L250,66 L210,112 L180,112Z" fill="#D9E2EA"/>'
            + "".join(f'<circle cx="{120 + i * 22}" cy="62" r="4" fill="#5C7A8C"/>' for i in range(10)) +
            f'<path d="M378,58 Q398,60 404,66 L378,66Z" fill="#5C7A8C"/></svg></div>')


def airport(F, H):
    oy = F - 790
    far = ('<div style="position:absolute;left:-1800px;top:-1400px;width:3600px;height:2100px;'
           'background:linear-gradient(#7EC3EA 0%,#B5DDF2 55%,#E8F4FA 100%)"></div>'
           '<div style="position:absolute;left:-1800px;top:560px;width:3600px;height:400px;background:linear-gradient(#9AA6AE,#7E8A92)"></div>'
           '<div style="position:absolute;left:-1800px;top:640px;width:3600px;height:10px;background:repeating-linear-gradient(90deg,#FFF 0 80px,transparent 80px 160px)"></div>'
           + _plane(-700, 470, 1.1, "parked", 0, "#E46C55"))
    mullions = "".join(f'<rect x="{x}" y="-120" width="34" height="780" fill="#23505E"/>' for x in range(-1700, 1720, 330))
    board = ('<rect x="-1480" y="150" width="520" height="330" rx="16" fill="#1E2A33"/>'
             '<rect x="-1480" y="150" width="520" height="56" rx="16" fill="#F6C453"/>'
             + "".join(f'<rect x="-1450" y="{232 + r * 46}" width="{180 + (r * 53 % 90)}" height="18" rx="4" fill="#F3E7D2" opacity=".8"/>'
                       f'<rect x="-1080" y="{232 + r * 46}" width="90" height="18" rx="4" fill="{"#4FC3A1" if r % 3 else "#E46C55"}"/>' for r in range(5)))
    gate = ('<rect x="780" y="120" width="300" height="120" rx="16" fill="#F6C453" stroke="#2B2230" stroke-width="6"/>'
            '<text x="930" y="200" text-anchor="middle" font-family="PL Display" font-size="64" fill="#2B2230">GATE 12</text>'
            '<rect x="925" y="-120" width="10" height="240" fill="#2B2230"/>')
    mid = (f'<svg style="position:absolute;left:-1700px;top:0" width="3400" height="900" viewBox="-1700 0 3400 900" overflow="visible">'
           f'<rect x="-1700" y="-120" width="3400" height="40" fill="#23505E"/>{mullions}'
           f'<rect x="-1700" y="640" width="3400" height="26" fill="#23505E"/>{board}{gate}'
           f'<rect x="-300" y="560" width="600" height="230" rx="12" fill="#E8ECF1" stroke="#2B2230" stroke-width="5"/>'
           f'<rect x="-300" y="560" width="600" height="40" rx="12" fill="#2F7F95"/></svg>')
    near = (f'<div style="position:absolute;left:-1800px;top:790px;width:3600px;height:{max(560, H - F + 400)}px;'
            f'background:#3E6E8C;background-image:radial-gradient(circle,rgba(255,255,255,.12) 3px,transparent 4px);background-size:48px 48px"></div>'
            f'<div style="position:absolute;left:-900px;top:800px;width:1800px;height:200px;border-radius:50%;background:radial-gradient(ellipse,rgba(255,255,255,.25),rgba(255,255,255,0) 70%)"></div>')
    fore = ('<svg style="position:absolute;left:-1560px;top:760px" width="3120" height="420" viewBox="0 0 3120 420">'
            + "".join(f'<rect x="{x}" y="60" width="150" height="190" rx="26" fill="#5D6B78"/><rect x="{x}" y="230" width="150" height="40" rx="12" fill="#46525E"/>'
                      for x in (0, 170, 2800, 2970)) + '</svg>')
    fore += _bokeh([(-1150, 60, 110, "255,255,255", .45), (1100, 80, 100, "255,236,190", .35)], "amb-bokeh")
    live = {"far": _plane(-2600, 430, .8, "amb-glide", 180) + _plane(1900, 380, .55, "amb-glide", -140, "#F6C453"),
            "mid": _walkers([(-1450, "rgba(40,60,80,.45)", 270, 60), (1150, "rgba(60,50,80,.45)", 260, -52)], 785, 1.0)}
    anim = [("far", ".amb-glide", "glide"), ("mid", ".amb-walk", "walk"), ("fore", ".amb-bokeh", "drift")]
    w = {"far": _shift(far, oy), "mid": _shift(mid, oy), "near": _shift(near, oy), "fore": _shift(fore, oy)}
    w["live"] = {k: _shift(v, oy) for k, v in live.items()}
    w["anim"] = anim
    return w


WORLDS = {"street": street, "foodcourt": foodcourt, "aisle": aisle, "stage": studio, "studio": studio, "cinema": cinema, "airport": airport}


def _live_bokeh(w, F):
    """Bokeh drifts, so it must stay live (baked layers are pictures): move it out of the fore layer."""
    import re
    found = re.findall(r'<div class="amb-bokeh"[^>]*></div>', w["fore"])
    if found:
        for f in found:
            w["fore"] = w["fore"].replace(f, "", 1)
        w.setdefault("live", {})
        w["live"]["fore"] = w["live"].get("fore", "") + _shift("".join(found), F - 790)
    return w


def get_world(spec, F, H):
    """'street' or 'street:CINEMA' (the part after ':' is the street sign)."""
    name, _, arg = (spec or "stage").partition(":")
    if name == "street" and arg:
        return _live_bokeh(street(F, H, sign=arg), F)
    return _live_bokeh(WORLDS[name](F, H), F)
