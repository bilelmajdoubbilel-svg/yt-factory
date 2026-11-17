"""Hidden Systems: the sewer world ("system": "sewer"), for "follow" scenes that ride one flush from the toilet
to the river. Kept in its own file so the power world (hs_art.power_strip) cannot change; hs_art.sewer_strip()
and look_hidden.py call into here.

The cutaway, left to right (world px, ground at hs_art.GY):
  bathroom (toilet) -> lateral under the yard (cleanout) -> sewer main under the street (two manholes, the
  "800,000 MILES" plate) -> lift station (wet well, pump, force main, kiosk) -> treatment plant (screens,
  aeration, clarifier, UV) -> outfall -> river.
Marks (distance along the traveller path) for waypoints: toilet, drain, lateral, cleanout, main, manhole,
sign, manhole2, lift, pump, force, plant, screen, aeration, clarifier, uv, outfall, river.

The traveller is a drop (not the power world's spark); its trail is bubbles, the trace behind it is water, and
the arrival in the river makes ripples instead of lighting a bulb.
"""
import json
import math
import random
import subprocess

import hs_art as A

C, INK, OL, GY = A.C, A.INK, A.OL, A.GY
L = 6000          # world width
SEWAGE = "#3F3B29"  # murky sewage (dark olive; dark enough that orange captions keep 3:1 contrast over it)

SIGN_SOURCE = "US PUBLIC SEWERS · ASCE 2021"


def tube(pts, w, body, bore=None, stripe=None, cls="", dash="46 40"):
    """A pipe drawn along a polyline, cut open so the traveller can be seen inside it."""
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    out = (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{w + 10}" stroke-linejoin="round" stroke-linecap="butt"/>'
           f'<path d="{d}" fill="none" stroke="{body}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="butt"/>')
    if bore:
        out += f'<path d="{d}" fill="none" stroke="{bore}" stroke-width="{w * .62:.0f}" stroke-linejoin="round" stroke-linecap="butt"/>'
    if stripe:
        out += (f'<path class="{cls}" d="{d}" fill="none" stroke="{stripe}" stroke-width="{max(5, w * .16):.0f}" '
                f'stroke-dasharray="{dash}" stroke-linecap="round" opacity=".9"/>')
    return out


def collar(x, y, w, ang=0):
    """A joint collar on a pipe at (x, y), rotated to the pipe's angle (degrees)."""
    return (f'<rect x="{x - 9}" y="{y - w / 2 - 9}" width="18" height="{w + 18}" rx="4" fill="{C["steel2"]}" '
            f'stroke="{INK}" stroke-width="3" transform="rotate({ang:.1f} {x} {y})"/>')


# ------------------------------------------------------------------ parts

def k_bathroom(x=60, w=800):
    """Cut-open house with a bathroom: toilet on the floor, its drain through the slab, a vent up the roof."""
    y_wall = 980
    out = [f'<path d="M{x - 40} {y_wall} L{x + w / 2} {y_wall - 170} L{x + w + 40} {y_wall}Z" fill="{C["line"]}" stroke="{INK}" '
           f'stroke-width="{OL}" stroke-linejoin="round"/>',
           f'<rect x="{x}" y="{y_wall}" width="{w}" height="{GY - y_wall}" fill="{C["wall"]}" stroke="{INK}" stroke-width="{OL}"/>',
           f'<rect x="{x + 50}" y="{y_wall + 40}" width="{w - 100}" height="{GY - y_wall - 46}" fill="{C["room"]}" stroke="{INK}" stroke-width="4"/>']
    # tiles on the lower wall
    ty0 = 1190
    out.append(f'<rect x="{x + 52}" y="{ty0}" width="{w - 104}" height="{GY - 6 - ty0}" fill="{C["concrete2"]}"/>')
    for yy in range(ty0, GY - 6, 52):
        out.append(f'<line x1="{x + 52}" y1="{yy}" x2="{x + w - 52}" y2="{yy}" stroke="{C["line"]}" stroke-width="3"/>')
    for xx in range(x + 52, x + w - 52, 52):
        out.append(f'<line x1="{xx}" y1="{ty0}" x2="{xx}" y2="{GY - 6}" stroke="{C["line"]}" stroke-width="3"/>')
    # small window with a sliver of sky
    out.append(f'<rect x="{x + 520}" y="{y_wall + 80}" width="160" height="110" rx="6" fill="{C["water2"]}" stroke="{INK}" stroke-width="4"/>'
               f'<line x1="{x + 600}" y1="{y_wall + 80}" x2="{x + 600}" y2="{y_wall + 190}" stroke="{INK}" stroke-width="4"/>')
    # vent stack: from the drain up through the roof
    vx = x + 430
    out.append(tube([(vx, GY + 40), (vx, y_wall - 120)], 26, C["steel"]))
    out.append(f'<rect x="{vx - 22}" y="{y_wall - 134}" width="44" height="18" rx="4" fill="{C["steel2"]}" stroke="{INK}" stroke-width="3"/>')
    # toilet: tank, lid, lever, bowl, seat, pedestal
    tx = x + 290
    out.append(f'<rect x="{tx - 70}" y="1180" width="130" height="110" rx="12" fill="{C["cream"]}" stroke="{INK}" stroke-width="{OL}"/>'
               f'<rect x="{tx - 80}" y="1168" width="150" height="22" rx="8" fill="{C["cream"]}" stroke="{INK}" stroke-width="4"/>'
               f'<rect x="{tx + 30}" y="1204" width="44" height="12" rx="5" fill="{C["steel2"]}" stroke="{INK}" stroke-width="3"/>')
    out.append(f'<path d="M{tx - 120} 1300 L{tx + 110} 1300 Q{tx + 108} 1352 {tx + 40} 1362 L{tx + 30} {GY - 6} '
               f'L{tx - 40} {GY - 6} L{tx - 50} 1362 Q{tx - 118} 1352 {tx - 120} 1300Z" fill="{C["cream"]}" stroke="{INK}" '
               f'stroke-width="{OL}" stroke-linejoin="round"/>')
    out.append(f'<rect x="{tx - 128}" y="1290" width="246" height="16" rx="7" fill="{C["steel"]}" stroke="{INK}" stroke-width="4"/>')
    # the bowl's water, seen in section
    out.append(f'<path d="M{tx - 90} 1312 L{tx + 80} 1312 Q{tx + 70} 1346 {tx + 10} 1350 L{tx - 20} 1350 Q{tx - 80} 1346 {tx - 90} 1312Z" fill="{C["water"]}" opacity=".9"/>')
    # floor slab
    out.append(f'<rect x="{x}" y="{GY - 8}" width="{w}" height="22" fill="{C["line"]}" stroke="{INK}" stroke-width="4"/>')
    return "".join(out), {"bowl": (tx - 5, 1330), "drain_top": (tx - 5, GY - 6), "vent": (vx, GY + 40)}


def k_cleanout(x, y_pipe):
    return (tube([(x, y_pipe), (x, GY - 18)], 24, C["pipe"]) +
            f'<rect x="{x - 22}" y="{GY - 30}" width="44" height="20" rx="5" fill="{C["steel"]}" stroke="{INK}" stroke-width="3"/>')


def k_street(x0, x1):
    """Asphalt on the surface, a curb and lane dashes (the street the main runs under)."""
    out = [f'<rect x="{x0}" y="{GY - 10}" width="{x1 - x0}" height="30" fill="{C["deep"]}" stroke="{INK}" stroke-width="4"/>',
           f'<rect x="{x0 - 30}" y="{GY - 34}" width="40" height="40" fill="{C["concrete2"]}" stroke="{INK}" stroke-width="4"/>']
    for xx in range(int(x0) + 120, int(x1) - 80, 260):
        out.append(f'<rect x="{xx}" y="{GY - 2}" width="120" height="8" fill="{C["cream"]}" opacity=".8"/>')
    return "".join(out)


def k_grass(x0, x1, seed=5):
    r = random.Random(seed)
    out = []
    for xx in range(int(x0), int(x1), 34):
        h = r.randint(10, 24)
        out.append(f'<path d="M{xx} {GY - 4} L{xx + 6} {GY - 4 - h} L{xx + 12} {GY - 4}Z" fill="{C["pipe"]}"/>')
    return "".join(out)


def k_lift_station(x=3080, w=420):
    """Wet well below ground, a submersible pump with a spinning impeller, the force main going up, a kiosk on top."""
    x0, x1, yb = x + 20, x + w, 2080
    out = [f'<rect x="{x0}" y="{GY - 4}" width="{x1 - x0}" height="{yb - GY + 4}" fill="{C["concrete2"]}" stroke="{INK}" stroke-width="{OL}"/>',
           f'<rect x="{x0 + 28}" y="{GY + 20}" width="{x1 - x0 - 56}" height="{yb - GY - 48}" fill="{C["deep"]}"/>']
    # sewage in the well
    out.append(f'<rect x="{x0 + 28}" y="1880" width="{x1 - x0 - 56}" height="{yb - 28 - 1880}" fill="{SEWAGE}"/>'
               f'<path class="hs-flow2" d="M{x0 + 28} 1882 L{x1 - 28} 1882" stroke="{C["water"]}" stroke-width="6" stroke-dasharray="30 26" opacity=".7"/>')
    # level float switches on a cable
    out.append(f'<line x1="{x1 - 70}" y1="{GY + 20}" x2="{x1 - 70}" y2="1860" stroke="{C["steel"]}" stroke-width="4"/>'
               f'<ellipse cx="{x1 - 70}" cy="1760" rx="16" ry="11" fill="{C["hat"]}" stroke="{INK}" stroke-width="3"/>'
               f'<ellipse cx="{x1 - 70}" cy="1870" rx="16" ry="11" fill="{C["hat"]}" stroke="{INK}" stroke-width="3"/>')
    # guide rails + pump
    px, py = x + 210, 1985
    out.append(f'<line x1="{px - 40}" y1="{GY + 20}" x2="{px - 40}" y2="{py}" stroke="{C["steel2"]}" stroke-width="8"/>'
               f'<line x1="{px + 40}" y1="{GY + 20}" x2="{px + 40}" y2="{py}" stroke="{C["steel2"]}" stroke-width="8"/>')
    out.append(f'<rect x="{px - 64}" y="{py - 10}" width="128" height="80" rx="16" fill="{C["pipe"]}" stroke="{INK}" stroke-width="{OL}"/>'
               f'<circle cx="{px}" cy="{py + 30}" r="40" fill="{C["deep"]}" stroke="{INK}" stroke-width="4"/>')
    vanes = "".join(f'<path d="M0 0 Q{22 * math.cos(a + .5):.1f} {22 * math.sin(a + .5):.1f} {34 * math.cos(a):.1f} {34 * math.sin(a):.1f}" '
                    f'stroke="{C["water"]}" stroke-width="7" fill="none" stroke-linecap="round"/>' for a in [k * math.pi / 3 for k in range(6)])
    out.append(f'<g transform="translate({px} {py + 30})"><g class="hs-spin">{vanes}<circle r="9" fill="{C["cream"]}" stroke="{INK}" stroke-width="3"/></g></g>')
    # kiosk (control panel) on top + hatch
    kx0, kx1, ky = x + 60, x + w - 40, 1190
    out.append(f'<rect x="{kx0}" y="{ky}" width="{kx1 - kx0}" height="{GY - ky}" fill="{C["wall"]}" stroke="{INK}" stroke-width="{OL}"/>'
               f'<path d="M{kx0 - 24} {ky} L{(kx0 + kx1) / 2} {ky - 60} L{kx1 + 24} {ky}Z" fill="{C["line"]}" stroke="{INK}" stroke-width="{OL}" stroke-linejoin="round"/>'
               f'<rect x="{kx0 + 30}" y="{ky + 110}" width="110" height="140" rx="8" fill="{C["concrete2"]}" stroke="{INK}" stroke-width="4"/>'
               f'<circle cx="{kx0 + 62}" cy="{ky + 150}" r="12" fill="{C["pipe"]}" stroke="{INK}" stroke-width="3"/>'
               f'<circle cx="{kx0 + 108}" cy="{ky + 150}" r="12" fill="{C["hat"]}" stroke="{INK}" stroke-width="3"/>'
               f'<rect x="{kx0 + 48}" y="{ky + 190}" width="74" height="34" rx="4" fill="{C["deep"]}" stroke="{INK}" stroke-width="3"/>')
    out.append(A.stencil((kx0 + kx1) / 2, ky + 80, "LIFT STATION", 50, C["cream"], spray=False, ls=3))
    return "".join(out), {"inlet": (x0 + 10, 1772), "pump": (px, py + 30), "rise": (px, 1500), "exit": (x1 + 6, 1500)}


def k_screens(x, w=230):
    """Headworks: an open channel at grade with a slanted bar screen."""
    out = [f'<rect x="{x}" y="{GY - 150}" width="{w}" height="170" fill="{C["concrete2"]}" stroke="{INK}" stroke-width="{OL}"/>',
           f'<rect x="{x + 18}" y="{GY - 110}" width="{w - 36}" height="112" fill="{SEWAGE}"/>']
    for k in range(7):
        bx = x + 90 + k * 14
        out.append(f'<line x1="{bx}" y1="{GY - 2}" x2="{bx + 40}" y2="{GY - 170}" stroke="{C["steel"]}" stroke-width="6" stroke-linecap="round"/>')
    out.append(A.stencil(x + w / 2, GY - 196, "SCREENS", 46, C["cream"], spray=False))
    return "".join(out)


def k_uv(x, w=240):
    """Disinfection: a channel with UV lamp racks; the water leaving it is clean."""
    out = [f'<rect x="{x}" y="{GY - 130}" width="{w}" height="150" fill="{C["concrete2"]}" stroke="{INK}" stroke-width="{OL}"/>',
           f'<rect x="{x + 18}" y="{GY - 104}" width="{w - 36}" height="106" fill="{C["water2"]}"/>']
    for k in range(5):
        lx = x + 44 + k * 38
        out.append(f'<rect x="{lx - 7}" y="{GY - 150}" width="14" height="130" rx="7" fill="{C["glass"]}" stroke="{INK}" stroke-width="3"/>')
    out.append(f'<rect x="{x + 20}" y="{GY - 160}" width="{w - 40}" height="14" fill="{C["hat"]}" stroke="{INK}" stroke-width="3"/>')
    out.append(A.stencil(x + w / 2, GY - 186, "UV LIGHT", 46, C["cream"], spray=False))
    return "".join(out)


def k_river(x0, x1):
    """The river the plant discharges to: banks cut into the ground, water with a moving surface."""
    bed = GY + 270
    out = [f'<path d="M{x0} {GY + 14} L{x0 + 90} {bed} L{x1 - 90} {bed} L{x1} {GY + 14}Z" fill="{C["water2"]}" stroke="{INK}" stroke-width="{OL}" stroke-linejoin="round"/>',
           f'<path d="M{x0 + 90} {bed} L{x1 - 90} {bed} L{x1 - 60} {bed + 40} L{x0 + 60} {bed + 40}Z" fill="{C["soil"]}"/>',
           f'<path d="M{x0 + 20} {GY + 40} L{x1 - 20} {GY + 40}" stroke="{C["water"]}" stroke-width="10" fill="none"/>',
           f'<path class="hs-flow" d="M{x0 + 30} {GY + 70} L{x1 - 30} {GY + 70}" stroke="{C["water"]}" stroke-width="6" stroke-dasharray="70 60" opacity=".7"/>',
           f'<path class="hs-flow" d="M{x0 + 60} {GY + 150} L{x1 - 60} {GY + 150}" stroke="{C["water"]}" stroke-width="5" stroke-dasharray="40 80" opacity=".5"/>']
    for k in range(5):     # reeds on the far bank
        rx = x1 - 20 + k * 16
        out.append(f'<path d="M{rx} {GY - 4} Q{rx + 4} {GY - 60} {rx + 10} {GY - 90}" stroke="{C["pipe"]}" stroke-width="6" fill="none"/>')
    out.append(A.stencil((x0 + x1) / 2, GY - 40, "RIVER", 60, C["water"], spray=False, ls=10))
    return "".join(out)


def k_far():
    """Far layer (parallax ~.35): blueprint grid and a low row of house roofs (power has towers; this is a street)."""
    far = []
    xmax = int(L * .45) + 2400
    for x in range(-400, xmax, 80):
        far.append(f'<line x1="{x}" y1="-400" x2="{x}" y2="2400" stroke="{C["grid"]}" stroke-width="2"/>')
    for y in range(-400, 2400, 80):
        far.append(f'<line x1="-400" y1="{y}" x2="{xmax}" y2="{y}" stroke="{C["grid"]}" stroke-width="2"/>')
    r = random.Random(23)
    x = -300
    while x < xmax - 200:
        w = r.randint(140, 240)
        h = r.randint(90, 170)
        far.append(f'<path d="M{x} {1240 - h} L{x + w / 2} {1240 - h - r.randint(50, 90)} L{x + w} {1240 - h} L{x + w} 1640 L{x} 1640Z" fill="#353B41"/>')
        x += w + r.randint(20, 90)
    far.append('<path d="M1500 1240 L1500 1010 Q1500 960 1560 960 L1620 960 Q1680 960 1680 1010 L1680 1240Z" fill="#383E44"/>'
               '<rect x="1585" y="1240" width="10" height="400" fill="#383E44"/>')  # distant water tower
    return "".join(far)


# ------------------------------------------------------------------ the strip

def sewer_strip():
    """The sewer cutaway. Same dict shape as hs_art.power_strip() plus the drop-traveller style keys."""
    mid, near, fore = [], [], []
    # ground with a gap for the river; street + yard surface
    near.append(A.k_ground(-600, 5400, depth=900, seed=4))
    near.append(A.k_ground(5900, L + 600, depth=900, seed=9))
    near.append(k_river(5380, 5900))
    near.append(k_grass(880, 1330))
    near.append(k_street(1360, 2980))
    near.append(k_grass(3560, 3620, seed=8))

    house, hp = k_bathroom(60)
    mid.append(house)
    bx, by = hp["bowl"]
    drain = (bx, GY + 70)
    elbow = (bx + 50, GY + 112)
    junction = (1650, 1664)
    main_end = (3110, 1774)
    # manhole shafts first (the main runs through them)
    for mx in (1900, 2650):
        y_main = junction[1] + (main_end[1] - junction[1]) * (mx - junction[0]) / (main_end[0] - junction[0])
        mid.append(A.k_manhole(mx, depth=int(y_main - GY + 40)))
    # lift station (the main and the force main attach to it)
    ls, lp = k_lift_station(3080)
    mid.append(ls)
    # the pipes
    mid.append(tube([(bx, GY - 10), drain, elbow, junction], 40, C["pipe"], C["deep"], SEWAGE, "hs-flow2", "30 28"))
    mid.append(k_cleanout(860, elbow[1] + (junction[1] - elbow[1]) * (860 - elbow[0]) / (junction[0] - elbow[0])))
    ang_main = math.degrees(math.atan2(main_end[1] - junction[1], main_end[0] - junction[0]))
    mid.append(tube([junction, main_end], 104, C["concrete2"], C["deep"], SEWAGE, "hs-flow2", "60 50"))
    for k in range(1, 6):
        cx = junction[0] + (main_end[0] - junction[0]) * k / 6
        cy = junction[1] + (main_end[1] - junction[1]) * k / 6
        mid.append(collar(cx, cy, 104, ang_main))
    # force main: up out of the well, across to the headworks
    rise, exit_, plant_in = lp["rise"], lp["exit"], (3700, 1500)
    mid.append(tube([(lp["pump"][0], lp["pump"][1] - 40), rise, exit_, plant_in, (3700, GY - 60), (3740, GY - 60)],
                    44, C["pipe"], C["deep"], SEWAGE, "hs-flow2", "30 28"))
    mid.append(f'<circle cx="{rise[0]}" cy="1690" r="30" fill="{C["hat"]}" stroke="{INK}" stroke-width="4"/>'
               f'<path d="M{rise[0] - 14} 1700 L{rise[0]} 1676 L{rise[0] + 14} 1700Z" fill="{INK}"/>')   # check valve
    # treatment plant
    mid.append(k_screens(3640))
    mid.append(A.k_treatment(3950))
    mid.append(k_uv(4950))
    # connectors between the tanks (sewage until the UV channel, clean water after)
    mid.append(tube([(3870, GY - 60), (3940, GY - 110)], 30, C["pipe"], C["deep"]))
    mid.append(tube([(4370, GY - 110), (4440, GY - 125)], 30, C["pipe"], C["deep"]))
    mid.append(tube([(4860, GY - 125), (4960, GY - 70)], 30, C["pipe"], C["deep"]))
    outfall_mouth = (5420, GY + 130)
    mid.append(tube([(5190, GY - 70), (5250, GY - 40), (5280, GY + 60), outfall_mouth], 40, C["pipe"], C["deep"], C["water"], "hs-flow", "30 28"))
    mid.append(f'<rect x="{outfall_mouth[0] - 14}" y="{outfall_mouth[1] - 34}" width="22" height="68" rx="4" fill="{C["steel2"]}" stroke="{INK}" stroke-width="4"/>')
    river_pt = (5600, GY + 112)

    # traveller path
    lat = lambda xx: (xx, elbow[1] + (junction[1] - elbow[1]) * (xx - elbow[0]) / (junction[0] - elbow[0]))
    path = [(bx, by), (bx, GY - 10), drain, elbow, lat(860), lat(1250), junction]
    path += [(junction[0] + (main_end[0] - junction[0]) * k / 10, junction[1] + 10 + (main_end[1] - junction[1]) * k / 10) for k in range(1, 11)]
    # falls into the wet well (a short arc), rides down to the pump, is pumped up and across
    for k in range(1, 7):
        u = k / 6
        path.append((main_end[0] + 90 * u, main_end[1] + 10 + (1905 - main_end[1] - 10) * u * u))
    path += [(lp["pump"][0] - 40, 1960), lp["pump"], (lp["pump"][0], lp["pump"][1] - 50), rise, exit_, plant_in, (3700, GY - 60),
             (3870, GY - 60), (3950, GY - 110), (4160, GY - 110), (4360, GY - 110), (4440, GY - 125), (4650, GY - 125), (4860, GY - 125),
             (4960, GY - 70), (5075, GY - 70), (5190, GY - 70), (5250, GY - 40), (5280, GY + 60), outfall_mouth, (5500, GY + 120), river_pt]
    dists = [0.0]
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        dists.append(dists[-1] + math.hypot(x1 - x0, y1 - y0))

    def near_d(pt):
        best = min(range(len(path)), key=lambda i: (path[i][0] - pt[0]) ** 2 + (path[i][1] - pt[1]) ** 2)
        return round(dists[best], 1)
    marks = {"toilet": 0.0, "drain": near_d(drain), "lateral": near_d(elbow), "cleanout": near_d(lat(860)),
             "main": near_d(junction), "manhole": near_d((1900, 1690)), "sign": near_d((2380, 1730)),
             "manhole2": near_d((2650, 1750)), "lift": near_d((main_end[0] + 15, main_end[1])), "pump": near_d(lp["pump"]),
             "force": near_d(rise), "plant": near_d((3700, GY - 60)), "screen": near_d((3870, GY - 60)),
             "aeration": near_d((4160, GY - 110)), "clarifier": near_d((4650, GY - 125)), "uv": near_d((5075, GY - 70)),
             "outfall": near_d(outfall_mouth), "river": round(dists[-1], 1)}
    # the number lives in the world: a plate in the soil under the main
    sign = (A.plate(2080, 1846, 600, 250, fill=C["concrete"]) +
            A.stencil(2380, 1990, "800,000", 150, C["hat"]) +
            A.stencil(2380, 2048, "MILES", 52, C["cream"], spray=False, ls=12) +
            A.mono(2380, 2082, SIGN_SOURCE, 24, C["steel"], "middle"))
    return {"mid": "".join(mid), "sign": sign, "near": "".join(near), "far": k_far(), "fore": "".join(fore),
            "path": [(round(x, 1), round(y, 1)) for x, y in path], "marks": marks, "width": L, "bulb": river_pt,
            "system": "sewer", "traveller": "drop", "end_mark": "river", "lit_len": 700, "ambience": "flow",
            "sfx": {"birth": "whoosh-soft", "pass": "tap", "end": "pop-2"}}


# ------------------------------------------------------------------ look_hidden hooks (drop traveller)

def traveller_markup(sid, strip, path_d):
    """Drop + bubble trail + water trace + river bloom (same element ids the follow runtime drives)."""
    W_ = C["water"]
    drop = A.drop_path(17)
    spark = (f'<div id="{sid}-spark" style="position:absolute;left:0;top:0;width:0;height:0" data-layout-ignore>'
             f'<div style="position:absolute;left:-80px;top:-80px;width:160px;height:160px;border-radius:50%;'
             f'background:radial-gradient(circle, rgba(255,246,232,.85) 0%, rgba(124,203,234,.7) 22%, rgba(124,203,234,0) 66%)"></div>'
             f'<svg style="position:absolute;left:-50px;top:-50px" width="100" height="100" viewBox="-50 -50 100 100" overflow="visible">'
             f'<g transform="translate(0 10)"><path d="{drop}" fill="{W_}" stroke="{INK}" stroke-width="4"/>'
             f'<ellipse cx="-6" cy="-6" rx="4.5" ry="7" fill="{C["cream"]}" opacity=".9"/></g></svg></div>')
    trail = "".join(f'<div id="{sid}-tr{k}" style="position:absolute;left:-{9 - k}px;top:-{9 - k}px;width:{18 - 2 * k}px;height:{18 - 2 * k}px;'
                    f'border-radius:50%;border:3px solid {W_};opacity:0" data-layout-ignore></div>' for k in range(5))
    lit = (f'<path id="{sid}-lit" d="{path_d}" fill="none" stroke="{W_}" stroke-width="9" stroke-linecap="round" '
           f'stroke-linejoin="round" opacity=".55" stroke-dasharray="0 99999"/>')
    b = strip["bulb"]
    bglow = (f'<div id="{sid}-bglow" style="position:absolute;left:{b[0] - 260}px;top:{b[1] - 260}px;width:520px;height:520px;border-radius:50%;'
             f'background:radial-gradient(circle, rgba(255,246,232,.7) 0%, rgba(124,203,234,.55) 20%, rgba(124,203,234,0) 70%);opacity:0" data-layout-ignore></div>'
             + "".join(f'<div id="{sid}-rip{k}" style="position:absolute;left:{b[0] - 60}px;top:{b[1] - 18}px;width:120px;height:36px;border-radius:50%;'
                       f'border:5px solid {C["cream"]};opacity:0" data-layout-ignore></div>' for k in range(3)))
    return spark, trail, lit, bglow


def arrival_js(sid, t_end):
    """Ripples spread on the river when the drop arrives (scene-local time t_end)."""
    return [f'tl.fromTo("#{sid}-rip{k}", {{opacity:.9, scale:.3}}, {{opacity:0, scale:{2.6 + k * .6:.1f}, duration:{1.1 + k * .2:.2f}, ease:"power2.out"}}, {t_end + k * .22:.3f})'
            for k in range(3)]


def flow_wav(path, dur):
    """Low running-water rumble under the cutaway travel (brown noise, low-passed, slow swell). Generated here."""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"anoisesrc=color=brown:amplitude=0.6:d={dur:.2f}:seed=7",
                    "-af", f"lowpass=f=520,highpass=f=60,tremolo=f=0.35:d=0.3,volume=0.9,afade=t=in:d=0.6,"
                           f"afade=t=out:st={max(0, dur - .8):.2f}:d=0.8", "-ac", "2", "-ar", "44100", str(path)], check=True)


# ------------------------------------------------------------------ thumbnail slice

def thumb_world():
    """1280x720 thumbnail backdrop for sewer videos: a cut-open toilet beside Drip's pointing hand, the drop
    glowing in the bowl, its drain running into a pipe under the floor. Returns (svg, glow_xy)."""
    tx = 640                      # toilet centre (between Drip and the word slab)
    out = [tube([(tx, 560), (tx, 650), (tx + 60, 676), (1320, 700)], 46, C["pipe"], C["deep"], SEWAGE, "", "26 22"),
           f'<rect x="{tx - 62}" y="300" width="124" height="104" rx="12" fill="{C["cream"]}" stroke="{INK}" stroke-width="6"/>',
           f'<rect x="{tx - 72}" y="288" width="144" height="22" rx="8" fill="{C["cream"]}" stroke="{INK}" stroke-width="5"/>',
           f'<path d="M{tx - 112} 414 L{tx + 104} 414 Q{tx + 100} 470 {tx + 36} 480 L{tx + 28} 596 L{tx - 36} 596 L{tx - 46} 480 '
           f'Q{tx - 108} 470 {tx - 112} 414Z" fill="{C["cream"]}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>',
           f'<rect x="{tx - 120}" y="404" width="232" height="16" rx="7" fill="{C["steel"]}" stroke="{INK}" stroke-width="5"/>',
           f'<path d="M{tx - 86} 426 L{tx + 78} 426 Q{tx + 68} 458 {tx + 10} 462 L{tx - 18} 462 Q{tx - 76} 458 {tx - 86} 426Z" fill="{C["water"]}"/>']
    return "".join(out), (tx - 4, 442)


if __name__ == "__main__":   # quick check: marks in order along the path
    s = sewer_strip()
    print(json.dumps(s["marks"], indent=1))
    v = list(s["marks"].values())
    assert v == sorted(v), "marks out of order"
