"""Map Minutes look: US and Canada geography and history told on animated maps, hosted by Pin.

Selected by "look": "mapminutes" in channels/history.json: make_video.sh runs pipeline/look_mapminutes.py (which calls
main() here) and thumbnail.py calls its thumbnail(); channels without a look (Price Logic) keep their own path. Built from:
  mm_geo.py   projections + public-domain map data (Natural Earth; US Census cartographic boundaries)
  mm_pin.py   Pin's rig (the canonical brand_art.pin_host, split into groups)
  assets/mapminutes/mm.js   map camera, map moves, Pin's acting (deterministic)

Scene types (script JSON "type"):
  map   the map is the world: camera keys (fit a region or a lon/lat + span), borders drawing on, region fills
        sweeping in, labels landing, the coral route travelling, a measuring bracket; Pin reacts in a corner
  data  a data beat on a parchment sheet over the blurred map (bars with counted-up values, a source line)
  pin   Pin close-up over the blurred map (rack focus to the map at the end if "rack": true)
  end   end card for long videos (space for YouTube's end-screen video + subscribe elements)
Transitions ("transition" on the incoming scene): "zoom" (the camera carries on from the last frame: a map
move across the cut), "route" (a coral route line sweeps a fresh parchment over the frame), "dip" (dip to paper),
"cut". Default: zoom between map scenes, route into a data beat, dip elsewhere.
"""
import hashlib
import html
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import compose as C  # noqa: E402  (only its caption/srt/Scene helpers; nothing here changes compose)
import mm_geo as G  # noqa: E402
from mm_pin import pin_box  # noqa: E402

ROOT = HERE.parent.parent
A = ROOT / "assets" / "mapminutes"
SFX = ROOT / "assets" / "sfx-cc0"
CATALOG = {s["id"]: s for s in json.loads((SFX / "catalog.json").read_text())["sounds"]}

PAL = dict(parchment="#F3E6C4", parchment2="#E6D3A6", grid="#CDB987", ocean="#1F5F8B", ocean2="#154766",
           ink="#142B3D", cream="#FFF7E3", coral="#D65A3A", sea="#A9CBD9", sea2="#8FB5C8", gold="#F2C14E", coral2="#B8442A",
           land="#E4D2A4", us="#E8D8AC", ca="#F7ECCD", strip="#D65A3A")
TERRITORIES = ("YT", "NT", "NU")
esc = C.esc


def fmt(portrait):
    """Screen layout per format. Shorts keep words and faces inside 168-1330 px and off the right-hand rail."""
    if portrait:
        return dict(W=1080, H=1920, anchor=(540, 650), fw=1000, fh=860, pin=(172, 1330, 102),
                    cap=dict(left=318, right=104, bottom=626, fs=78), src_y=186, card=(66, 200, 1014, 978))
    return dict(W=1920, H=1080, anchor=(1150, 540), fw=1450, fh=900, pin=(300, 1010, 165),
                cap=None, src_y=1012, card=(560, 120, 1840, 900))


# ------------------------------------------------------------------ easing (mirrors GSAP, for planning)
def ease(name, x):
    x = min(1.0, max(0.0, x))
    if name in ("none", "linear"):
        return x
    if name.startswith("sine.inOut"):
        return -(math.cos(math.pi * x) - 1) / 2
    if name.startswith("power3.out"):
        return 1 - (1 - x) ** 3
    if name.startswith("expo.out"):
        return 1.0 if x == 1 else 1 - 2 ** (-10 * x)
    if name.startswith("power4.out"):
        return 1 - (1 - x) ** 5
    return 2 * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 2 / 2  # power2.inOut


# ------------------------------------------------------------------ geography helpers (cached per projection)
_BB = {}


def bbox_of(P, pname, what):
    key = (pname, json.dumps(what))
    if key in _BB:
        return _BB[key]
    d = G.data()
    if what == "canada":
        rings = G.project_rings(d["countries"]["CAN"] if "CAN" in d["countries"] else d["countries"]["CA"], P, eps=20)
    elif what == "us48":
        rings = [r for s in d["states"] if s["name"] not in ("Alaska", "Hawaii", "Puerto Rico", "United States Virgin Islands")
                 for r in G.project_rings(s["geom"], P, eps=20)]
    elif what == "north":
        rings = [r for p in d["provinces"] if p["code"] in TERRITORIES for r in G.project_rings(p["geom"], P, eps=20)]
    elif what == "strip":
        rings = G.project_rings(d["derived"]["ca_strip_100km"], P, eps=10)
    elif isinstance(what, str):
        rings = [r for p in d["provinces"] + d["states"] if p.get("code") == what or p["name"] == what
                 for r in G.project_rings(p["geom"], P, eps=10)]
    else:  # [lon0, lat0, lon1, lat1]
        lo0, la0, lo1, la1 = what
        import numpy as np
        lons = np.concatenate([np.linspace(lo0, lo1, 20), np.full(20, lo1), np.linspace(lo1, lo0, 20), np.full(20, lo0)])
        lats = np.concatenate([np.full(20, la0), np.linspace(la0, la1, 20), np.full(20, la1), np.linspace(la1, la0, 20)])
        x, y = P.fwd(lons, lats)
        rings = [np.stack([x, y], 1)]
    xs = [v for r in rings for v in r[:, 0]]
    ys = [v for r in rings for v in r[:, 1]]
    _BB[key] = (min(xs), min(ys), max(xs), max(ys))
    return _BB[key]


def resolve_key(k, P, pname, F, prev=None):
    """{"fit": region|bbox, "pad": .08} or {"at": [lon, lat], "span": km}; "zoom" multiplies the span."""
    if k.get("from") == "prev" and prev:
        out = dict(prev)
    elif "fit" in k:
        x0, y0, x1, y1 = bbox_of(P, pname, k["fit"])
        pad = 1 + k.get("pad", 0.08)
        span = max(x1 - x0, (y1 - y0) * F["fw"] / F["fh"]) * pad
        out = {"cx": (x0 + x1) / 2, "cy": (y0 + y1) / 2, "span": span}
    elif "at" in k:
        cx, cy = G.pt(P, *k["at"])
        out = {"cx": cx, "cy": cy, "span": float(k.get("span", 1500))}
    else:
        out = dict(prev) if prev else {"cx": 0.0, "cy": 0.0, "span": 6000.0}
    if "zoom" in k:
        out["span"] /= float(k["zoom"])
    if "nudge" in k:  # screen-fraction offset: [dx, dy] of the focus width
        out["cx"] += k["nudge"][0] * out["span"]
        out["cy"] += k["nudge"][1] * out["span"]
    return out


def cam_at(keys, t):
    if t <= keys[0]["t"]:
        return keys[0]
    for a, b in zip(keys, keys[1:]):
        if t <= b["t"]:
            u = ease(b.get("ease", "power2.inOut"), (t - a["t"]) / max(1e-6, b["t"] - a["t"]))
            return {k: a[k] + (b[k] - a[k]) * u for k in ("cx", "cy", "span")}
    return keys[-1]


def to_screen(F, cam, wx, wy):
    k = F["fw"] / cam["span"]
    return F["anchor"][0] + (wx - cam["cx"]) * k, F["anchor"][1] + (wy - cam["cy"]) * k


# ------------------------------------------------------------------ the map (world units = km)
def stroke(px, dash=None, extra=""):
    s = f"stroke-width:calc({px}px / var(--k, 1));"
    if dash:
        s += "stroke-dasharray:" + " ".join(f"calc({d}px / var(--k, 1))" for d in dash) + ";"
    return s + extra


class MapBuilder:
    def __init__(self, S, P, pname, F, view, eps):
        self.S, self.P, self.pname, self.F, self.view, self.eps = S, P, pname, F, view, eps
        self.defs, self.layers, self.labels, self.js, self.sfx = [], [], [], [], []
        self.n = 0

    def rings(self, mp, eps=None, min_area=None):
        return G.project_rings(mp, self.P, eps=eps or self.eps, min_area=min_area or max(30.0, self.eps ** 2 * 6), bbox=self.view)

    def uid(self, tag):
        self.n += 1
        return f"{self.S.sid}-{tag}{self.n}"

    def base(self, d):
        """Sea, graticule, land, the US (Census states), Canada (provinces), lakes, coasts."""
        x0, y0, x1, y1 = self.view
        geo = G.data()
        L = self.layers
        L.append(f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}" fill="{PAL["sea"]}"/>')
        L.append(f'<path d="{G.d_lines(G.graticule(self.P, 5))}" fill="none" stroke="{PAL["sea2"]}" style="{stroke(1.4)}" opacity=".55"/>')
        for k in ("MEX", "GRL"):
            if k in geo["countries"]:
                L.append(f'<path d="{G.d_rings(self.rings(geo["countries"][k]))}" fill="{PAL["land"]}" stroke="{PAL["ocean2"]}" '
                         f'style="{stroke(1.2)}" stroke-opacity=".35" fill-rule="evenodd"/>')
        st = [s for s in geo["states"] if s["name"] not in ("Hawaii", "Puerto Rico", "United States Virgin Islands")]
        us_d = "".join(G.d_rings(self.rings(s["geom"])) for s in st)
        L.append(f'<path id="{self.S.sid}-us" d="{us_d}" fill="{PAL["us"]}" stroke="{PAL["grid"]}" style="{stroke(1.1)}" fill-rule="evenodd"/>')
        prov = {p["code"]: G.d_rings(self.rings(p["geom"])) for p in geo["provinces"]}
        L.append(f'<g id="{self.S.sid}-ca">' + "".join(
            f'<path id="{self.S.sid}-pv-{c}" d="{dd}" fill="{PAL["ca"]}" fill-rule="evenodd"/>' for c, dd in prov.items()) + "</g>")
        return prov

    def overlays_after_fill(self, d, prov):
        geo = G.data()
        L = self.layers
        sid = self.S.sid
        # graticule ghost over land: a printed-map feel
        L.append(f'<path d="{G.d_lines(G.graticule(self.P, 5))}" fill="none" stroke="{PAL["grid"]}" style="{stroke(1.0)}" opacity=".55"/>')
        # province lines: dashed ink
        L.append(f'<g fill="none" stroke="{PAL["ink"]}" opacity=".38" style="{stroke(1.4, (7, 5))}">' +
                 "".join(f'<path d="{dd}"/>' for dd in prov.values()) + "</g>")
        lakes = "".join(G.d_rings(self.rings(lk["geom"], min_area=200)) for lk in geo["lakes"])
        L.append(f'<path d="{lakes}" fill="{PAL["sea"]}" stroke="{PAL["ocean2"]}" stroke-opacity=".55" style="{stroke(1.1)}" fill-rule="evenodd"/>')
        coast = "".join(G.d_rings(self.rings(geo["countries"][k])) for k in ("CAN", "USA") if k in geo["countries"])
        L.append(f'<path d="{coast}" fill="none" stroke="{PAL["ocean2"]}" stroke-opacity=".8" style="{stroke(1.6)}"/>')

    # ---- features
    def strip(self, spec):
        """Canada within 100 km of the lower-48 border, swept in west to east (or already lit at frame 0)."""
        sid = self.S.sid
        rings = self.rings(G.data()["derived"]["ca_strip_100km"], eps=min(self.eps, 4), min_area=20)
        x0, y0, x1, y1 = (min(r[:, 0].min() for r in rings), min(r[:, 1].min() for r in rings),
                          max(r[:, 0].max() for r in rings), max(r[:, 1].max() for r in rings))
        cid = f"{sid}-stripclip"
        self.defs.append(f'<clipPath id="{cid}" clipPathUnits="userSpaceOnUse"><rect id="{cid}-r" x="{x0 - 20:.0f}" y="{y0 - 20:.0f}" '
                         f'width="{x1 - x0 + 40:.0f}" height="{y1 - y0 + 40:.0f}"/></clipPath>')
        op = spec.get("opacity", 0.82)
        self.layers.append(f'<g clip-path="url(#{cid})"><path id="{sid}-strip" d="{G.d_rings(rings)}" fill="{PAL["strip"]}" '
                           f'fill-opacity="{op}" stroke="{PAL["coral"]}" style="{stroke(1.5)}" fill-rule="evenodd"/></g>')
        if spec.get("lit"):
            if spec.get("pulse"):
                self.js.append(f'tl.fromTo("#{sid}-strip", {{attr:{{"fill-opacity":{op * .55:.2f}}}}}, {{attr:{{"fill-opacity":{op}}}, '
                               f'duration:.5, yoyo:true, repeat:{int(spec["pulse"]) * 2 - 1}, ease:"sine.inOut"}}, .05)')
        else:
            t = self.S.cue(spec.get("cue"), spec.get("t", .3))
            self.js.append(f'MM.sweep(tl, "#{cid}-r", "#{sid}-strip", {x1 - x0 + 40:.0f}, {t:.3f}, {spec.get("dur", 1.4)})')
            self.sfx.append(("sweep-long", t, 20))

    def territories(self, spec):
        sid = self.S.sid
        geo = G.data()
        t = self.S.cue(spec.get("cue"), spec.get("t", .4))
        parts = []
        for k, p in enumerate([p for p in geo["provinces"] if p["code"] in TERRITORIES]):
            rings = self.rings(p["geom"])
            if not rings:
                continue
            big = max(rings, key=G.ring_area)
            parts.append(f'<path class="{sid}-terr" d="{G.d_rings(rings)}" fill="{PAL["ocean"]}" fill-opacity="0" fill-rule="evenodd"/>')
            parts.append(f'<path class="{sid}-terrline" d="{G.d_rings([big])}" pathLength="1" stroke-dasharray="1 2" stroke-dashoffset="1" '
                         f'fill="none" stroke="{PAL["ocean2"]}" style="{stroke(3.2)}" stroke-linejoin="round"/>')
        self.layers.append("".join(parts))
        self.js.append(f'MM.draw(tl, ".{sid}-terrline", {t:.3f}, 1.3, .18)')
        self.js.append(f'tl.to(".{sid}-terr", {{attr:{{"fill-opacity":{spec.get("opacity", .3)}}}, duration:.7, stagger:.15, ease:"power2.out"}}, {t + .5:.3f})')
        self.sfx.append(("pencil-write", t, 20))

    def regions(self, spec):
        """Physical regions (Natural Earth) as an ink hatch: the Canadian Shield, the Barren Grounds..."""
        sid = self.S.sid
        names = spec.get("names", ["Canadian Shield", "Barren Grounds"])
        hid = f"{sid}-hatch"
        gap, w = spec.get("gap", 46), spec.get("w", 10)
        self.defs.append(f'<pattern id="{hid}" patternUnits="userSpaceOnUse" width="{gap}" height="{gap}" patternTransform="rotate(38)">'
                         f'<rect width="{w}" height="{gap}" fill="{PAL["ocean2"]}"/></pattern>')
        rings = [r for rg in G.data()["regions"] if rg["name"] in names for r in self.rings(rg["geom"], eps=self.eps * 1.5)]
        north = spec.get("north_of")
        dd = G.d_rings(rings)
        if north is not None:  # optional: also hatch everything north of a latitude inside Canada
            pass
        t = self.S.cue(spec.get("cue"), spec.get("t", .3))
        self.layers.append(f'<path id="{sid}-reg" d="{dd}" fill="url(#{hid})" opacity="0" fill-rule="evenodd"/>')
        op = spec.get("opacity", .32)
        if spec.get("lit"):
            self.js.append(f'tl.set("#{sid}-reg", {{opacity:{op}}}, 0)')
        else:
            self.js.append(f'tl.to("#{sid}-reg", {{opacity:{op}, duration:.9, ease:"power2.out"}}, {t:.3f})')

    def border(self, spec):
        """The southern Canada-US border, drawing itself on (pencil sound), plus the dotted 49th parallel."""
        sid = self.S.sid
        lines = G.project_lines(G.data()["derived"]["border_ca_us48"], self.P, eps=min(self.eps, 3))
        draw = spec.get("draw", True)
        t = self.S.cue(spec.get("cue"), spec.get("t", .3))
        segs = "".join(f'<path class="{sid}-bd" d="{G.d_lines([ln])}" pathLength="1" stroke-dasharray="1 2" '
                       f'stroke-dashoffset="{1 if draw else 0}"/>' for ln in sorted(lines, key=lambda a: a[:, 0].min()))
        self.layers.append(f'<g fill="none" stroke="{PAL["ink"]}" style="{stroke(3.0)}" stroke-linecap="round" stroke-linejoin="round">{segs}</g>')
        if draw:
            self.js.append(f'MM.draw(tl, ".{sid}-bd", {t:.3f}, {spec.get("dur", 1.6)}, .12)')
            self.sfx.append(("pencil-write", t, 18))

    def parallel49(self, spec):
        sid = self.S.sid
        ln = G.parallel(self.P, 49.0, -140, -52, 0.5)
        cid = f"{sid}-p49clip"
        x0, x1 = float(ln[:, 0].min()), float(ln[:, 0].max())
        y0, y1 = float(ln[:, 1].min()), float(ln[:, 1].max())
        lit = spec.get("lit", True)
        self.defs.append(f'<clipPath id="{cid}" clipPathUnits="userSpaceOnUse"><rect id="{cid}-r" x="{x0 - 50:.0f}" y="{y0 - 400:.0f}" '
                         f'width="{(x1 - x0 + 100) if lit else 0:.0f}" height="{y1 - y0 + 800:.0f}"/></clipPath>')
        self.layers.append(f'<g clip-path="url(#{cid})"><path d="{G.d_lines([ln])}" fill="none" stroke="{PAL["ocean2"]}" stroke-linecap="round" '
                           f'style="{stroke(spec.get("w", 5), (0.1, 15))}" opacity=".9"/></g>')
        if not lit:
            t = self.S.cue(spec.get("cue"), spec.get("t", .3))
            self.js.append(f'tl.fromTo("#{cid}-r", {{attr:{{width:0}}}}, {{attr:{{width:{x1 - x0 + 100:.0f}}}, duration:{spec.get("dur", 1.4)}, ease:"power2.inOut"}}, {t:.3f})')
        if spec.get("label", True):
            lon = spec.get("label_lon", -106.0)
            self.label({"text": "49°N", "at": [lon, 49.0], "style": "tag", "anchor": "s", "lit": lit, "cue": spec.get("cue"), "t": spec.get("t", .3) + .6})

    def route(self, spec):
        """The coral route line: a dashed path revealed by a mask, with a head dot riding its tip."""
        sid = self.S.sid
        rid = self.uid("rt")
        pts = G.route(self.P, [tuple(w) if isinstance(w, (list, tuple)) else (G.place(w)["lon"], G.place(w)["lat"]) for w in spec["via"]])
        dd = G.d_lines([pts])
        x0, y0, x1, y1 = self.view
        self.defs.append(f'<mask id="{rid}-m" maskUnits="userSpaceOnUse" x="{x0:.0f}" y="{y0:.0f}" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}">'
                         f'<path id="{rid}-mp" d="{dd}" pathLength="1" stroke-dasharray="1 2" stroke-dashoffset="1" fill="none" '
                         f'stroke="#fff" style="{stroke(16)}" stroke-linecap="round" stroke-linejoin="round"/></mask>')
        self.layers.append(f'<g mask="url(#{rid}-m)"><path d="{dd}" fill="none" stroke="{PAL["cream"]}" style="{stroke(10)}" stroke-linecap="round" stroke-linejoin="round" opacity=".9"/>'
                           f'<path d="{dd}" fill="none" stroke="{PAL["coral"]}" style="{stroke(6.5, (16, 11))}" stroke-linecap="round" stroke-linejoin="round"/></g>'
                           f'<circle id="{rid}-h" r="0" style="r:calc(9px / var(--k, 1));{stroke(3.5)}" fill="{PAL["coral"]}" stroke="{PAL["cream"]}" opacity="0"/>')
        t = self.S.cue(spec.get("cue"), spec.get("t", .3))
        dur = spec.get("dur") or max(1.2, (self.S.narr_end - t) * .9)
        self.js.append(f'MM.route(tl, "#{rid}-mp", "#{rid}-h", {t:.3f}, {dur:.2f}, "{spec.get("ease", "sine.inOut")}")')
        self.sfx.append(("whoosh-long-2s", t, 22))
        for k, c in enumerate(spec.get("beads", [])):
            # each city lands as the route reaches it (by order along the route)
            frac = c["at"] if isinstance(c.get("at"), (int, float)) else (k + 1) / (len(spec["beads"]) + 1)
            cc = {kk: v for kk, v in c.items() if not (kk == "at" and isinstance(v, (int, float)))}
            self.label(dict(cc, style=c.get("style", "city"), t=t + dur * frac, sound="pop-2"))

    def bracket(self, spec):
        """A measuring bracket: from a point on the border, north by N km."""
        sid = self.S.sid
        lon, lat = spec["at"]
        km = float(spec.get("km", 100))
        ax, ay = G.pt(self.P, lon, lat)
        bx, by = G.pt(self.P, lon, lat + km / 111.2)
        nx, ny = (bx - ax), (by - ay)
        L = math.hypot(nx, ny)
        ux, uy = -ny / L, nx / L  # perpendicular, for the end ticks
        tick = spec.get("tick", 18)
        dd = (f"M{ax:.1f},{ay:.1f} L{bx:.1f},{by:.1f} M{ax - ux * tick:.1f},{ay - uy * tick:.1f} L{ax + ux * tick:.1f},{ay + uy * tick:.1f} "
              f"M{bx - ux * tick:.1f},{by - uy * tick:.1f} L{bx + ux * tick:.1f},{by + uy * tick:.1f}")
        bid = self.uid("br")
        self.layers.append(f'<path id="{bid}h" d="{dd}" pathLength="1" stroke-dasharray="1 2" stroke-dashoffset="1" fill="none" '
                           f'stroke="{PAL["cream"]}" style="{stroke(11)}" stroke-linecap="round"/>'
                           f'<path id="{bid}" d="{dd}" pathLength="1" stroke-dasharray="1 2" stroke-dashoffset="1" fill="none" '
                           f'stroke="{PAL["ink"]}" style="{stroke(5)}" stroke-linecap="round"/>')
        t = self.S.cue(spec.get("cue"), spec.get("t", .5))
        self.js.append(f'MM.draw(tl, "#{bid}h, #{bid}", {t:.3f}, .7, 0, "power2.out")')
        self.label({"text": spec.get("text", f"{int(km)} km"), "at": [lon + spec.get("label_dlon", 0.0), lat + km / 111.2 / 2],
                    "style": "measure", "anchor": spec.get("anchor", "e"), "t": t + .45, "sound": "tick-soft"})

    # ---- labels ride on the map in screen space (crisp, constant size)
    def label(self, spec):
        sid = self.S.sid
        lid = self.uid("lb")
        if "place" in spec or (spec.get("style") == "city" and "at" not in spec):
            p = G.place(spec.get("place") or spec["text"])
            spec = dict(spec, at=[p["lon"], p["lat"]])
        wx, wy = G.pt(self.P, *spec["at"])
        style = spec.get("style", "region")
        anchor = spec.get("anchor", {"city": "e", "region": "c", "tag": "s", "callout": "n", "measure": "e", "big": "c"}.get(style, "c"))
        text = esc(spec["text"])
        dot = '<div class="dot"></div>' if style in ("city", "callout") else ""
        self.labels.append(f'<div class="lab" id="{lid}" data-wx="{wx:.2f}" data-wy="{wy:.2f}">{dot}'
                           f'<div class="lab-in"><div class="lab-c a-{anchor} s-{style}">{text}</div></div></div>')
        if spec.get("lit"):
            return
        t = spec.get("t") if spec.get("t") is not None and not spec.get("cue") else self.S.cue(spec.get("cue"), spec.get("t", .5))
        t = round(t + spec.get("dt", 0), 3)
        self.js.append(f'MM.land(tl, "#{lid}", {t:.3f}, {"true" if style in ("big", "callout") else "false"})')
        snd = spec.get("sound", {"big": "impact-wood-light", "callout": "impact-wood-light", "city": "pop-2"}.get(style, "tick-soft"))
        if snd:
            self.sfx.append((snd, t + .05, 17))


def label_css(S, F):
    p = S.portrait
    fs = {"region": 34 if p else 30, "city": 34 if p else 28, "tag": 30 if p else 26, "measure": 40 if p else 34,
          "callout": 56 if p else 54, "big": 92 if p else 96}
    return f'''
    #root .lab {{ position:absolute; left:0; top:0; width:0; height:0; z-index:3; }}
    #root .lab .dot {{ position:absolute; left:-9px; top:-9px; width:18px; height:18px; border-radius:50%; background:{PAL["coral"]};
      border:4px solid {PAL["cream"]}; box-shadow:0 2px 6px rgba(20,43,61,.35); }}
    #root .lab-in {{ position:absolute; left:0; top:0; }}
    #root .lab-c {{ position:absolute; white-space:nowrap; font-family:'MM Mono',monospace; font-weight:600; color:{PAL["ink"]}; }}
    #root .a-c {{ transform:translate(-50%,-50%); }} #root .a-e {{ transform:translate(22px,-50%); }}
    #root .a-w {{ transform:translate(calc(-100% - 22px),-50%); }} #root .a-n {{ transform:translate(-50%,calc(-100% - 26px)); }}
    #root .a-s {{ transform:translate(-50%,18px); }}
    #root .s-region {{ font-size:{fs["region"]}px; letter-spacing:.16em; text-transform:uppercase; color:{PAL["ocean2"]};
      text-shadow:0 0 6px {PAL["ca"]}, 0 0 12px {PAL["ca"]}; }}
    #root .s-city {{ font-size:{fs["city"]}px; padding:4px 12px; border-radius:10px; background:rgba(255,247,227,.92); color:{PAL["ink"]};
      box-shadow:0 2px 8px rgba(20,43,61,.18); }}
    #root .s-tag {{ font-size:{fs["tag"]}px; color:{PAL["ocean2"]}; letter-spacing:.06em; padding:2px 10px; border-radius:8px; background:rgba(243,230,196,.85); }}
    #root .s-measure {{ font-size:{fs["measure"]}px; color:{PAL["cream"]}; background:{PAL["ink"]}; padding:6px 16px; border-radius:12px; }}
    #root .s-callout {{ font-family:'MM Display',serif; font-weight:800; font-size:{fs["callout"]}px; color:{PAL["cream"]}; background:{PAL["coral"]};
      padding:8px 26px 12px; border-radius:18px; box-shadow:0 10px 24px rgba(20,43,61,.28); letter-spacing:-.01em; }}
    #root .s-big {{ font-family:'MM Display',serif; font-weight:800; font-size:{fs["big"]}px; color:{PAL["ink"]}; letter-spacing:-.02em;
      text-shadow:0 0 18px {PAL["ca"]}, 0 0 4px {PAL["ca"]}; }}'''


# ------------------------------------------------------------------ Pin direction
BASE_MOUTH = {"neutral": "smile", "happy": "smile", "surprised": "o", "thinking": "flat", "worried": "wobble"}


def pin_plan(S, F, spec, keys, pin_xyr):
    """Pin's acting for a scene -> (html, js). Acts: {"t"|"cue", "dt", "expr", "look": [dx, dy], "point": [lon, lat] |
    {"deg": a}, "hold": s, "hop": true, "needle": "swing|spin|tremble|waver|wiggle"}; "enter": "drop"|"slide"."""
    if spec is False:
        return "", []
    spec = spec or {}
    sid = S.sid
    pid = f"{sid}-pin"
    x, y, r = spec.get("x", pin_xyr[0]), spec.get("y", pin_xyr[1]), spec.get("r", pin_xyr[2])
    flip = bool(spec.get("flip"))
    expr0 = spec.get("expr", "neutral")
    js = [f'MM.pin.setFace(tl, "{pid}", "{expr0}")', f'MM.pin.breathe(tl, "{pid}", {S.dur:.2f})',
          f'MM.pin.blinks(tl, "{pid}", {S.dur:.2f}, {int(sid[1:]) * 11 + 5})']
    if spec.get("enter") == "drop":
        js.append(f'MM.pin.drop(tl, "{pid}", {spec.get("enter_t", .05)})')
    elif spec.get("enter") == "slide":
        js.append(f'MM.pin.slide(tl, "{pid}", {-500 if x < F["W"] / 2 else 500}, {spec.get("enter_t", .05)})')
    exprs = [(0.0, expr0)]
    s = r / 100.0
    piv = (x, y - 305 * s)
    for a in spec.get("acts", []):
        t = (S.cue(a["cue"], a.get("t", .3)) if a.get("cue") else a.get("t", .3)) + a.get("dt", 0)
        t = round(max(0.0, min(S.dur - .25, t)), 3)
        if a.get("expr"):
            js.append(f'MM.pin.face(tl, "{pid}", "{a["expr"]}", {t}, {"false" if a.get("needle") or a.get("point") else "true"})')
            exprs.append((t, a["expr"]))
        if a.get("look") is not None:
            dx, dy = a["look"]
            js.append(f'MM.pin.look(tl, "{pid}", {-dx if flip else dx}, {dy}, {t + .02:.3f})')
        if a.get("point") is not None:
            pt_ = a["point"]
            if isinstance(pt_, dict):
                ang = pt_["deg"]
            else:
                P = G.proj(S.pname)
                wx, wy = G.pt(P, *pt_)
                sx, sy = to_screen(F, cam_at(keys, t + .5), wx, wy)
                ang = math.degrees(math.atan2(sx - piv[0], -(sy - piv[1])))
            ang = -ang if flip else ang
            js.append(f'MM.pin.point(tl, "{pid}", {ang:.1f}, {t:.3f}, {a.get("hold", 0) or 0})')
        if a.get("hop"):
            js.append(f'MM.pin.hop(tl, "{pid}", {t + .05:.3f})')
        if a.get("needle"):
            js.append(f'MM.pin.needle(tl, "{pid}", "{a["needle"]}", {t + .12:.3f}, {a.get("amt", 1)})')
    track = mouth_track(S, exprs, spec.get("talk", True))
    js.append(f'MM.pin.mouths(tl, "{pid}", {json.dumps(track)})')
    return pin_box(pid, x, y, r, mouth=BASE_MOUTH.get(expr0, "smile"), expr=expr0, flip=flip), js


def mouth_track(S, exprs, talk):
    def base(t):
        e = "neutral"
        for te, ex in exprs:
            if te <= t + 1e-6:
                e = ex
        return BASE_MOUTH.get(e, "smile")
    keys = [(0.0, base(0.0))] + [(t, BASE_MOUTH.get(e, "smile")) for t, e in exprs[1:]]
    if talk:
        ws = S.words
        for i, w in enumerate(ws):
            st, en = w["start"], w["end"]
            nxt = ws[i + 1]["start"] if i + 1 < len(ws) else en + .3
            if en - st < .07:
                continue
            n = len(re.sub(r"[^A-Za-z0-9]", "", w["text"]))
            keys.append((st, "talka" if (i + n) % 2 == 0 else "talkb"))
            if en - st > .32:
                keys.append(((st + en) / 2, "talkb" if (i + n) % 2 == 0 else "talka"))
            close = min(en, nxt) - .015
            if nxt - en > .06 or i == len(ws) - 1:
                keys.append((close, base(close)))
    keys.sort(key=lambda k: k[0])
    out = []
    for t, m in keys:
        t = round(max(0.0, min(S.dur - .05, t)), 3)
        if out and abs(out[-1][0] - t) < 1e-3:
            out[-1] = [t, m]
        elif not out or out[-1][1] != m:
            out.append([t, m])
    return out


# ------------------------------------------------------------------ data beat on parchment
def data_card(S, F, d):
    sid = S.sid
    x0, y0, x1, y1 = F["card"]
    p = S.portrait
    rows, js, pops = [], [], []
    for k, it in enumerate(d.get("rows", [])):
        v = float(it["value"])
        color = PAL["coral"] if it.get("highlight") else PAL["ocean"]
        at = S.cue(it.get("cue"), .4 + k * .8)
        rows.append(f'''
        <div class="drow">
          <div class="dhead"><div class="dlab">{esc(it["label"])}</div>
            <div id="{sid}-val{k}" class="dval" style="color:{PAL["coral2"] if it.get("highlight") else PAL["ocean"]}">{esc(it.get("display", it["value"]))}</div></div>
          <div class="dtrack"><div id="{sid}-bar{k}" class="dbar" style="width:{max(1.0, v):.2f}%;background:{color}"></div></div>
        </div>''')
        js.append(f'tl.fromTo("#{sid}-bar{k}", {{scaleX:0}}, {{scaleX:1, duration:1.1, ease:"power3.out"}}, {at:.3f})')
        dec = int(it.get("decimals", 0))
        suf = it.get("suffix", "%")
        js.append(f'MM.roll(tl, "#{sid}-val{k}", 0, {v}, {at:.3f}, 1.1, {dec}, "", {json.dumps(suf)})')
        pops.append(at + 1.1)
    kicker = d.get("kicker", "")
    html_ = f'''
    <div id="{sid}-card" class="card" style="left:{x0}px;top:{y0}px;width:{x1 - x0}px;height:{y1 - y0}px">
      <div class="card-in">
        <div class="ckick">{esc(kicker)}</div>
        <div class="ctitle">{C.rich(d.get("title", ""), sid, "t")}</div>
        <div class="crule"></div>
        <div class="rows">{"".join(rows)}</div>
        <div class="csrc">{esc(d.get("source", ""))}</div>
      </div>
    </div>'''
    css = f'''
    #root .card {{ position:absolute; z-index:4; }}
    #root .card-in {{ position:absolute; inset:0; border-radius:26px; background:{PAL["parchment"]} url(assets/paper.png); background-blend-mode:multiply;
      border:4px solid {PAL["ink"]}; box-shadow:0 26px 70px rgba(20,43,61,.38), inset 0 0 0 10px {PAL["parchment"]}, inset 0 0 0 13px {PAL["grid"]};
      padding:{"54px 56px 44px" if p else "52px 70px 40px"}; display:flex; flex-direction:column; }}
    #root .ckick {{ font-family:'MM Mono',monospace; font-weight:600; font-size:{32 if p else 30}px; letter-spacing:.2em; color:{PAL["ocean"]}; text-transform:uppercase; }}
    #root .ctitle {{ font-family:'MM Display',serif; font-weight:800; font-size:{70 if p else 66}px; line-height:1.02; color:{PAL["ink"]}; margin-top:18px; letter-spacing:-.015em; }}
    #root .ctitle .hl {{ color:{PAL["coral"]}; }}
    #root .crule {{ height:6px; margin:{26 if p else 24}px 0 {34 if p else 30}px; background:radial-gradient(circle, {PAL["ocean2"]} 2.6px, transparent 3px) 0 50%/18px 6px repeat-x; }}
    #root .rows {{ display:flex; flex-direction:column; gap:{40 if p else 34}px; }}
    #root .dhead {{ display:flex; align-items:baseline; justify-content:space-between; margin-bottom:12px; }}
    #root .dlab {{ font-family:'MM Mono',monospace; font-weight:600; font-size:{38 if p else 34}px; letter-spacing:.14em; color:{PAL["ink"]}; }}
    #root .dval {{ font-family:'MM Display',serif; font-weight:800; font-size:{104 if p else 92}px; line-height:.9; font-variant-numeric:tabular-nums; letter-spacing:-.02em; }}
    #root .dtrack {{ position:relative; height:{62 if p else 56}px; border-radius:14px; border:4px dashed {PAL["ink"]}; background:rgba(255,247,227,.6); }}
    #root .dbar {{ position:absolute; left:-4px; top:-4px; bottom:-4px; border-radius:14px; transform-origin:0 50%; min-width:16px; }}
    #root .csrc {{ margin-top:auto; font-family:'MM Mono',monospace; font-weight:600; font-size:{28 if p else 26}px; color:#4A5A66; }}'''
    js.insert(0, f'tl.fromTo("#{sid}-card", {{y:{F["H"]}, rotation:-4}}, {{y:0, rotation:-1.2, duration:.75, ease:"expo.out"}}, .02)')
    return html_, css, js, pops


# ------------------------------------------------------------------ end card (long videos)
def end_card(S, F, d, pin_xy=None):
    """Landscape end card: Pin hops on the 49th parallel, the wordmark, a dotted slot for YouTube's end-screen video
    (left free for the element) and a route line that leads the eye from Pin to it."""
    sid = S.sid
    W, H = F["W"], F["H"]
    p = S.portrait
    if p:
        slot = (90, 420, 990, 926)
    else:
        slot = (1010, 210, 1780, 643)  # 16:9 video element area
    sx0, sy0, sx1, sy1 = slot
    px, py = pin_xy or F["pin"][:2]
    html_ = f'''
    <div id="{sid}-wm" class="wm">Map Minutes</div>
    <div id="{sid}-tag" class="tagl">{esc(d.get("tagline", "The US and Canada, explained on the map"))}</div>
    <div id="{sid}-slot" class="slot" style="left:{sx0}px;top:{sy0}px;width:{sx1 - sx0}px;height:{sy1 - sy0}px"><div class="slot-in">{esc(d.get("slot", "WATCH NEXT"))}</div></div>
    <div id="{sid}-next" class="nextp">{esc(d.get("next", "New map every Wednesday"))}</div>
    <svg class="endroute" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><path id="{sid}-er" d="M{px + 150},{py - 380} C{px + 380},{py - 560} {sx0 - 300},{sy1 + 120} {sx0 - 26},{(sy0 + sy1) / 2:.0f}"
      fill="none" stroke="{PAL["coral"]}" stroke-width="9" stroke-dasharray="18 13" stroke-linecap="round"/></svg>'''
    css = f'''
    #root .wm {{ position:absolute; left:{110 if not p else 90}px; top:{110 if not p else 200}px; font-family:'MM Display',serif; font-weight:800; font-size:{132 if not p else 120}px;
      color:{PAL["ink"]}; letter-spacing:-.025em; z-index:4; }}
    #root .tagl {{ position:absolute; left:{118 if not p else 96}px; top:{270 if not p else 350}px; font-family:'MM Mono',monospace; font-weight:600; font-size:{34 if not p else 32}px; color:{PAL["ocean2"]}; z-index:4; }}
    #root .slot {{ position:absolute; z-index:4; border-radius:22px; border:5px dashed {PAL["ink"]}; background:rgba(255,247,227,.45); }}
    #root .slot-in {{ position:absolute; left:0; right:0; bottom:-64px; text-align:center; font-family:'MM Mono',monospace; font-weight:600; font-size:30px; letter-spacing:.22em; color:{PAL["ocean2"]}; }}
    #root .nextp {{ position:absolute; left:{sx0}px; width:{sx1 - sx0}px; top:{sy1 + 110}px; text-align:center; z-index:4; font-family:'MM Mono',monospace; font-weight:600;
      font-size:34px; color:{PAL["cream"]}; }}
    #root .nextp {{ background:{PAL["ocean"]}; border-radius:40px; padding:14px 0; }}
    #root .endroute {{ position:absolute; left:0; top:0; z-index:3; overflow:visible; }}'''
    js = [f'tl.fromTo("#{sid}-wm", {{opacity:0, y:-30}}, {{opacity:1, y:0, duration:.6, ease:"expo.out"}}, .2)',
          f'tl.fromTo("#{sid}-tag", {{opacity:0}}, {{opacity:1, duration:.5}}, .55)',
          f'tl.fromTo("#{sid}-slot", {{opacity:0, scale:.94}}, {{opacity:1, scale:1, duration:.6, ease:"back.out(1.6)"}}, .8)',
          f'tl.fromTo("#{sid}-next", {{opacity:0, y:20}}, {{opacity:1, y:0, duration:.5, ease:"power3.out"}}, 1.2)',
          f'tl.fromTo("#{sid}-er", {{opacity:0}}, {{opacity:1, duration:.4}}, 1.0)']
    return html_, css, js


# ------------------------------------------------------------------ scene assembly
def scene_file(S, F, ctx, tin, tout):
    sid, W, H = S.sid, F["W"], F["H"]
    t = S.spec["type"]
    d = S.d
    P = G.proj(S.pname)
    # camera
    keys_spec = S.spec.get("cam") or [{"from": "prev"}]
    keys, prev = [], ctx.get("cam")
    for k in keys_spec:
        kk = resolve_key(k, P, S.pname, F, keys[-1] if keys else prev)
        tk = k.get("t", 0)
        tk = S.dur if tk == "end" else (S.cue(k["cue"], 0) if k.get("cue") else float(tk))
        kk.update(t=round(min(S.dur, tk), 3), ease=k.get("ease", "power2.inOut"))
        keys.append(kk)
    if not keys:
        keys = [dict(resolve_key({"fit": "canada"}, P, S.pname, F), t=0, ease="none")]
    if keys[-1]["t"] < S.dur and len(keys) == 1:
        keys.append(dict(keys[0], t=S.dur, span=keys[0]["span"] * (1 - S.spec.get("push", .035)), ease="sine.inOut"))
    ctx["cam"] = {k: keys[-1][k] for k in ("cx", "cy", "span")}
    # visible world (union of views, padded) and simplification for the closest zoom
    spans = [k["span"] for k in keys]
    xs = [k["cx"] for k in keys]
    ys = [k["cy"] for k in keys]
    smax = max(spans)
    ax, ay = F["anchor"]
    view = (min(xs) - smax * (ax / F["fw"]) * 1.35, min(ys) - smax * (ay / F["fw"]) * 1.35,
            max(xs) + smax * ((W - ax) / F["fw"]) * 1.35, max(ys) + smax * ((H - ay) / F["fw"]) * 1.35)
    eps = max(0.8, min(spans) / F["fw"] * 0.7)
    M = MapBuilder(S, P, S.pname, F, view, eps)
    prov = M.base(d)
    lay = d.get("layers", {})
    if lay.get("regions"):
        M.regions(lay["regions"])
    if lay.get("territories"):
        M.territories(lay["territories"])
    if lay.get("strip"):
        M.strip(lay["strip"])
    M.overlays_after_fill(d, prov)
    if lay.get("parallel49") is not None and lay.get("parallel49") is not False:
        M.parallel49(lay["parallel49"] if isinstance(lay["parallel49"], dict) else {})
    if lay.get("border"):
        M.border(lay["border"] if isinstance(lay["border"], dict) else {})
    for rt in lay.get("routes", []):
        M.route(rt)
    if lay.get("bracket"):
        M.bracket(lay["bracket"])
    for lb in d.get("labels", []):
        M.label(lb)
    # depth of field on the map (data beats, close-ups): a rack focus is a change of blur over time
    blur = S.spec.get("blur")
    if blur is None:
        blur = {"data": [{"t": 0, "b": 0}, {"t": .1, "b": 7, "dur": .6}], "pin": [{"t": 0, "b": 9}], "end": [{"t": 0, "b": 0}]}.get(t, [{"t": 0, "b": 0}])
    blur = [dict(b, t=round(S.cue(b["cue"], b.get("t", 0)), 3)) if b.get("cue") else b for b in blur]
    if S.spec.get("rack"):
        blur = blur + [{"t": round(S.dur - .9, 3), "b": 0, "dur": .8}]
    # host
    pin_default = F["pin"]
    if t == "pin":
        pin_default = (330, F["pin"][1], 236) if S.portrait else (520, 1040, 360)
    if t == "end" and not S.portrait:
        pin_default = (400, 975, 190)
    extra_html, extra_css, extra_js = "", "", []
    pops = []
    if t == "data":
        extra_html, extra_css, extra_js, pops = data_card(S, F, d)
    elif t == "end":
        pp = S.spec.get("pin") or {}
        extra_html, extra_css, extra_js = end_card(S, F, d, (pp.get("x", pin_default[0]), pp.get("y", pin_default[1])))
    pin_html, pin_js = pin_plan(S, F, S.spec.get("pin"), keys, pin_default)
    # source pill
    src = d.get("source") if t != "data" else None
    src_html = (f'<div id="{sid}-src" class="srcpill" style="top:{F["src_y"]}px">{esc(src)}</div>' if src else "")
    js = [f'MM.mapcam(tl, {json.dumps(dict(world=f"#{sid}-world", wrap=f"#{sid}-mapwrap", map=f"#{sid}-map", far=f"#{sid}-far", labels=f"#{sid}-ov .lab", anchor=list(F["anchor"]), fw=F["fw"], keys=[{k: (round(v, 3) if isinstance(v, float) else v) for k, v in kk.items()} for kk in keys], blur=blur, dur=round(S.dur, 3), drift=S.spec.get("drift", .8 if t != "data" else .35)))})']
    js += M.js + extra_js + pin_js
    if src:
        js.append(f'tl.fromTo("#{sid}-src", {{opacity:0, y:12}}, {{opacity:1, y:0, duration:.4}}, {S.cue(d.get("source_cue"), .7):.3f})')
    # transitions: the incoming half here, the outgoing half on the previous scene
    if tin == "route":
        js.append(f'tl.fromTo("#{sid}-wipe", {{x:0}}, {{x:{-int(W * 1.6)}, duration:.5, ease:"power3.inOut"}}, 0)')
    if tout == "route":
        js.append(f'tl.fromTo("#{sid}-wipe", {{x:{int(W * 1.6)}}}, {{x:0, duration:.32, ease:"power3.in"}}, {max(.1, S.dur - .32):.3f})')
    if tin == "dip":
        js.append(f'tl.fromTo("#{sid}-dip", {{opacity:1}}, {{opacity:0, duration:.35, ease:"power2.out"}}, 0)')
    if tout == "dip":
        js.append(f'tl.fromTo("#{sid}-dip", {{opacity:0}}, {{opacity:1, duration:.16, ease:"power2.in"}}, {max(.1, S.dur - .16):.3f})')
    js.append(f'window.__timelines["{sid}"] = tl;')
    S.sfx = M.sfx + [("pop-1", p_, 16) for p_ in pops[:2]]
    defs = "".join(M.defs)
    wipe_w = int(W * 1.6)
    xt, xb = int(wipe_w * .42), int(wipe_w * .12)   # the wipe's slanted leading edge (matches its clip-path)
    wipe = (f'<div id="{sid}-wipe" class="wipe" style="width:{wipe_w}px;transform:translateX({wipe_w}px)">'
            f'<svg width="{wipe_w}" height="{H}" viewBox="0 0 {wipe_w} {H}" style="position:absolute;left:0;top:0;overflow:visible">'
            f'<path d="M{xt + 34},{-40} L{xb + 34},{H + 40}" stroke="{PAL["coral"]}" stroke-width="18" stroke-dasharray="40 24" stroke-linecap="round"/>'
            f'<path d="M{xt + 92},{-40} L{xb + 92},{H + 40}" stroke="{PAL["ocean2"]}" stroke-width="6" stroke-dasharray="1 20" stroke-linecap="round"/></svg></div>'
            if "route" in (tin, tout) else "")
    js_text = "\n    ".join(["const tl = gsap.timeline({ paused: true });"] + [ln if ln.rstrip().endswith((";", "}")) else ln + ";" for ln in js])
    return f'''<template>
  <style>
    #root {{ position:absolute; inset:0; overflow:hidden; background:{PAL["parchment"]}; }}
    #root .L {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; }}
    #{sid}-far {{ left:-120px; top:-120px; width:{W + 240}px; height:{H + 240}px; background:{PAL["sea"]}; }}
    #{sid}-paper {{ position:absolute; inset:0; background:url(assets/paper.png); mix-blend-mode:multiply; opacity:.9; pointer-events:none; }}
    #root .srcpill {{ position:absolute; left:0; right:0; margin:0 auto; width:fit-content; z-index:6; font-family:'MM Mono',monospace; font-weight:600;
      font-size:{29 if S.portrait else 26}px; color:{PAL["cream"]}; background:rgba(20,43,61,.86); padding:8px 20px; border-radius:12px; }}
    #root .wipe {{ position:absolute; top:0; height:{H}px; left:{-int(W * .3)}px; z-index:30; background:{PAL["parchment"]} url(assets/paper.png); background-blend-mode:multiply;
      clip-path:polygon(42% 0, 100% 0, 100% 100%, 12% 100%); }}
    #{sid}-dip {{ position:absolute; inset:0; z-index:29; background:{PAL["parchment"]}; opacity:0; pointer-events:none; }}
    {label_css(S, F)}
    {extra_css}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="{W}" data-height="{H}" data-layout-allow-overflow data-layout-allow-overlap>
    <div id="{sid}-far" class="L"></div>
    <div id="{sid}-mapwrap" class="L"><div id="{sid}-map" class="L"><svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" style="display:block">
      <defs>{defs}</defs><g id="{sid}-world">{"".join(M.layers)}</g></svg></div></div>
    <div id="{sid}-paper"></div>
    <div id="{sid}-ov" class="L" data-layout-ignore>{"".join(M.labels)}</div>
    <div id="{sid}-ui" class="L">{extra_html}{src_html}</div>
    <div id="{sid}-host" class="L">{pin_html}</div>
    {wipe}
    <div id="{sid}-dip"></div>
  </div>
  <script>
    {js_text}
  </script>
</template>
'''


# ------------------------------------------------------------------ captions, fx, sound
def captions_file(groups, F, total):
    W, H = F["W"], F["H"]
    cp = F["cap"]
    blocks, js = [], []
    for g_, grp in enumerate(groups):
        spans = [f'<span class="cw" id="cap-g{g_}-w{i}">{esc(w["text"])}</span>' for i, w in enumerate(grp["words"])]
        blocks.append(f'<div class="cg" id="cap-g{g_}">{" ".join(spans)}</div>')
        st, en = grp["start"], grp["end"]
        js.append(f'tl.fromTo("#cap-g{g_}", {{opacity:0, y:14}}, {{opacity:1, y:0, duration:.12, ease:"power2.out"}}, {st:.3f});')
        for i, w in enumerate(grp["words"]):
            js.append(f'tl.fromTo("#cap-g{g_}-w{i}", {{color:"{PAL["cream"]}"}}, {{color:"{PAL["gold"]}", duration:.06}}, {w["start"]:.3f});')
        js.append(f'tl.to("#cap-g{g_}", {{opacity:0, duration:.08, ease:"power2.in"}}, {max(st + .1, en - .08):.3f});')
        js.append(f'tl.set("#cap-g{g_}", {{opacity:0, visibility:"hidden"}}, {en:.3f});')
    return f'''<template>
  <style>
    #root {{ position:absolute; inset:0; pointer-events:none; }}
    #root .cg {{ position:absolute; left:{cp["left"]}px; right:{cp["right"]}px; bottom:{cp["bottom"]}px; text-align:center;
      font-family:'MM Display',serif; font-weight:800; font-size:{cp["fs"]}px; line-height:1.06; color:{PAL["cream"]}; opacity:0;
      -webkit-text-stroke:11px {PAL["ink"]}; paint-order:stroke fill; letter-spacing:-.01em; }}
  </style>
  <div id="root" data-composition-id="captions" data-width="{W}" data-height="{H}" data-layout-allow-caption-zone>
    {"".join(blocks)}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {chr(10).join("    " + j for j in js)}
    window.__timelines["captions"] = tl;
  </script>
</template>
'''


def fx_file(F, total):
    W, H = F["W"], F["H"]
    grain = ("url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E"
             "%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E"
             "%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")")
    return f'''<template>
  <style>
    #root {{ position:absolute; inset:0; pointer-events:none; }}
    #fx-vig {{ position:absolute; inset:0; background:radial-gradient(ellipse at 50% 42%, rgba(60,40,10,0) 55%, rgba(60,40,10,.26) 100%); }}
    #fx-warm {{ position:absolute; inset:0; background:linear-gradient(165deg, rgba(255,200,120,.07), rgba(31,95,139,.06)); }}
    #fx-grain {{ position:absolute; inset:-10px; opacity:.06; background-image:{grain}; }}
  </style>
  <div id="root" data-composition-id="fx" data-width="{W}" data-height="{H}" data-layout-ignore>
    <div id="fx-warm"></div><div id="fx-vig"></div><div id="fx-grain"></div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    MM.grain(tl, "#fx-grain", {total:.3f});
    window.__timelines["fx"] = tl;
  </script>
</template>
'''


def lufs(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else -20.0


# Map Minutes scores with acoustic, piano and gentle lo-fi: exploring, not selling (Price Logic is playful/funky)
MOODS = {
    "explore": ["music-cozy-acoustic.mp3", "music-lofi-tea.mp3", "music-calm-loop.mp3"],
    "wonder": ["music-ambient-piano.mp3", "music-contemplation.mp3"],
    "tension": ["music-tension-soft.mp3"],
    "payoff": ["music-inspiring-orchestral.mp3"],
    "sad": ["music-emotional-piano-loop.mp3"],
}


def build_music(script, assets, total, tl):
    lib = ROOT / "music" / "shared"
    starts = [s["start"] for s in tl["scenes"]]
    cues = script.get("score") or ([{"scene": 0, "mood": script.get("mood", "explore")}] if script.get("format") == "short" else
                                   [{"scene": 0, "mood": script.get("open_mood", "wonder")}] +
                                   [{"scene": i, "mood": script.get("body_mood", "explore")} for i, s in enumerate(script["scenes"]) if s["type"] == "chapter"])
    segs, used = [], {}
    h = int(hashlib.md5(script["id"].encode()).hexdigest(), 16)
    for k, c in enumerate(cues):
        t0 = starts[min(c["scene"], len(starts) - 1)] if k else 0.0
        t1 = starts[min(cues[k + 1]["scene"], len(starts) - 1)] if k + 1 < len(cues) else total
        if t1 - t0 < 3:
            continue
        opts = MOODS.get(c.get("mood"), MOODS["explore"])
        n = used.get(c.get("mood"), 0)
        used[c.get("mood")] = n + 1
        segs.append((t0, t1, c.get("track") or opts[(n + h) % len(opts)]))
    parts = []
    for k, (t0, t1, name) in enumerate(segs):
        seg = assets / f"music_seg{k}.wav"
        dur = (t1 - t0) + (1.6 if k + 1 < len(segs) else 0)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(lib / name), "-t", f"{dur:.2f}",
                        "-af", "loudnorm=I=-27:TP=-3:LRA=11", "-ar", "44100", "-ac", "2", str(seg)], check=True)
        parts.append(seg)
    raw, out = assets / "music_raw.wav", assets / "music.wav"
    if len(parts) == 1:
        chain = f"[0:a]afade=t=in:d=0.6,afade=t=out:st={max(0, total - 3):.2f}:d=3,apad[m]"
    else:
        chain, last = "", "[0:a]"
        for k in range(1, len(parts)):
            chain += f"{last}[{k}:a]acrossfade=d=1.6:c1=tri:c2=tri[x{k}];"
            last = f"[x{k}]"
        chain += f"{last}afade=t=in:d=0.6,afade=t=out:st={max(0, total - 3):.2f}:d=3,apad[m]"
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for p_ in parts:
        cmd += ["-i", str(p_)]
    subprocess.run(cmd + ["-filter_complex", chain, "-map", "[m]", "-t", f"{total:.2f}", str(raw)], check=True)
    for p_ in parts:
        p_.unlink()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-i", str(assets / "voice.wav"), "-filter_complex",
                    "[1:a]aresample=44100,aformat=channel_layouts=stereo,volume=3,apad[sc];"
                    "[0:a][sc]sidechaincompress=threshold=0.02:ratio=5:attack=30:release=500:makeup=1[m]",
                    "-map", "[m]", "-t", f"{total:.2f}", str(out)], check=True)
    raw.unlink()
    return " > ".join(f"{n} ({t0:.0f}s)" for t0, _, n in segs)


def sfx_clip(name, t, total, voice_lufs, under=16.0):
    info = CATALOG[name]
    gain = min(1.0, 10 ** ((voice_lufs - under - info.get("lufs", -22)) / 20))
    return name, round(t, 3), min(info["duration_s"], total - t - .05), round(gain, 3)


def fonts_css(prefix="assets/fonts/"):
    return (f"@font-face {{ font-family:'MM Display'; src:url('{prefix}mm-display.woff2') format('woff2'); font-weight:100 900; }}"
            f"@font-face {{ font-family:'MM Mono'; src:url('{prefix}mm-mono.woff2') format('woff2'); font-weight:100 900; }}")


def transitions(script):
    types = [s["type"] for s in script["scenes"]]
    out = []
    for i, sp in enumerate(script["scenes"]):
        if i == 0:
            out.append("cut")
        elif sp.get("transition"):
            out.append(sp["transition"])
        elif types[i] == "data":
            out.append("zoom")
        elif types[i - 1] == "data":
            out.append("route")
        elif types[i] == "map" and types[i - 1] == "map":
            out.append("zoom")
        else:
            out.append("dip")
    return out


def main(script, channel, build, tl):
    portrait = script.get("format") == "short"
    F = fmt(portrait)
    W, H = F["W"], F["H"]
    comp = build / "compositions"
    comp.mkdir(parents=True, exist_ok=True)
    assets = build / "assets"
    (assets / "sfx").mkdir(parents=True, exist_ok=True)
    (assets / "fonts").mkdir(exist_ok=True)
    shutil.copy(ROOT / "node_modules" / "gsap" / "dist" / "gsap.min.js", assets / "gsap.min.js")
    shutil.copy(A / "mm.js", assets / "mm.js")
    shutil.copy(A / "paper.png", assets / "paper.png")
    for f in ("mm-display.woff2", "mm-mono.woff2"):
        shutil.copy(A / "fonts" / f, assets / "fonts" / f)
    total = round(tl["total"] + .6, 3)
    voice_lufs = lufs(assets / "voice.wav")
    pname = script.get("projection", "canada")
    scenes = list(zip(script["scenes"], tl["scenes"]))
    trans = transitions(script)
    ctx = {"cam": None}
    hosts, sfx = [], []
    for i, (sp, tsc) in enumerate(scenes):
        if i == len(scenes) - 1:
            tsc = dict(tsc, duration=round(total - tsc["start"], 3))
        S = C.Scene(tsc["id"], sp, tsc, W, H, channel["theme"])
        S.first, S.idx, S.pname = i == 0, i, pname
        tin, tout = trans[i], (trans[i + 1] if i + 1 < len(trans) else None)
        (comp / f"{S.sid}.html").write_text(scene_file(S, F, ctx, tin, tout))
        hosts.append(f'<div id="{S.sid}" data-composition-id="{S.sid}" data-composition-src="compositions/{S.sid}.html" '
                     f'data-start="{tsc["start"]}" data-duration="{S.dur}" data-track-index="1" data-track-kind="graphics" '
                     f'data-width="{W}" data-height="{H}" style="z-index:1"></div>')
        st = tsc["start"]
        if tin == "route":
            sfx.append(sfx_clip("page-turn", max(0, st - .3), total, voice_lufs, 13))
        elif tin == "dip":
            sfx.append(sfx_clip("paper-handle-1", max(0, st - .15), total, voice_lufs, 16))
        elif tin == "zoom":
            sfx.append(sfx_clip("whoosh-soft", max(0, st - .1), total, voice_lufs, 19))
        for name, t_, under in getattr(S, "sfx", []):
            sfx.append(sfx_clip(name, st + t_, total, voice_lufs, under))
        pin = sp.get("pin") or {}
        if pin and pin.get("enter") == "drop":
            sfx.append(sfx_clip("dry-thud", st + pin.get("enter_t", .05) + .42, total, voice_lufs, 15))
    (comp / "fx.html").write_text(fx_file(F, total))
    hosts.append(f'<div id="fx" data-composition-id="fx" data-composition-src="compositions/fx.html" data-start="0" '
                 f'data-duration="{total}" data-track-index="6" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:40"></div>')
    if portrait:
        (comp / "captions.html").write_text(captions_file(C.caption_groups(tl, 3, 18), F, total))
        hosts.append(f'<div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" '
                     f'data-start="0" data-duration="{total}" data-track-index="2" data-track-kind="captions" '
                     f'data-width="{W}" data-height="{H}" style="z-index:50"></div>')
    (build / "captions.srt").write_text(C.srt(C.caption_groups(tl, 8, 46)))
    audio = [f'<audio id="vo" class="clip" data-start="0" data-duration="{tl["total"]}" data-track-index="3" data-volume="1" src="assets/voice.wav"></audio>']
    music = build_music(script, assets, total, tl)
    audio.append(f'<audio id="bed" class="clip" data-start="0" data-duration="{total}" data-track-index="4" data-volume="1" src="assets/music.wav"></audio>')
    last_end = {}
    for k, (name, st, dur, gain) in enumerate(sorted(sfx, key=lambda x: x[1])):
        trk = 5 if name.startswith(("whoosh", "page", "paper", "sweep")) else 7 if name.startswith(("pencil", "dry", "impact")) else 8
        if st < last_end.get(trk, -1) or dur < .05:
            continue
        last_end[trk] = st + dur
        shutil.copy(SFX / f"{name}.wav", assets / "sfx" / f"{name}.wav")
        audio.append(f'<audio id="sfx{k}" class="clip" data-start="{st:.3f}" data-duration="{dur:.3f}" data-track-index="{trk}" '
                     f'data-volume="{gain}" src="assets/sfx/{name}.wav"></audio>')
    index = f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="assets/gsap.min.js"></script>
    <script src="assets/mm.js"></script>
    <style>
      {fonts_css()}
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      html, body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:{PAL["parchment"]}; }}
      #root {{ position:relative; width:100%; height:100%; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
      {chr(10).join("      " + h for h in hosts)}
      {chr(10).join("      " + a for a in audio)}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
'''
    (build / "index.html").write_text(index)
    (build / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions", "assets": "assets"}}, indent=1))
    (build / "meta.json").write_text(json.dumps({"id": script["id"], "name": script["title"]}, indent=1))
    print(f"mapminutes: {len(scenes)} scenes, {len(audio)} audio clips, {total:.1f}s, music={music}, voice {voice_lufs:.1f} LUFS, transitions={trans}")


# ------------------------------------------------------------------ thumbnail (1280x720)
def thumbnail_html(script):
    """One focal point: the region lit in coral on the parchment map, Pin big on the left third with the
    video's emotion, at most 3 words on the right (never the title's words). Reads at 120 px wide."""
    t = script.get("thumbnail") or {}
    W, H = 1280, 720
    F = dict(W=W, H=H, anchor=(t.get("ax", 800), t.get("ay", 380)), fw=t.get("fw", 900), fh=640, pin=(250, 690, 150), cap=None, src_y=0, card=(0, 0, 0, 0))
    pname = script.get("projection", "canada")
    P = G.proj(pname)

    class _S:  # a still: one frame, no narration
        sid, d, words, dur, narr_end, portrait = "th", {}, [], 1.0, .5, False
        spec = {"type": "map"}

        def cue(self, n, f):
            return f
    S = _S()
    S.pname = pname
    cam = resolve_key(t.get("cam", {"fit": "canada"}), P, pname, F)
    k = F["fw"] / cam["span"]
    view = (cam["cx"] - F["anchor"][0] / k * 1.2, cam["cy"] - F["anchor"][1] / k * 1.2,
            cam["cx"] + (W - F["anchor"][0]) / k * 1.2, cam["cy"] + (H - F["anchor"][1]) / k * 1.2)
    M = MapBuilder(S, P, pname, F, view, max(1.0, cam["span"] / F["fw"] * .7))
    prov = M.base({})
    lay = t.get("layers", {"strip": {"lit": True}})
    if "regions" in lay:
        M.regions(dict(lay["regions"], lit=True))
    if "strip" in lay:
        M.strip(dict(lay["strip"], lit=True))
    M.overlays_after_fill({}, prov)
    if lay.get("parallel49", True):
        M.parallel49({"lit": True, "label": False, "w": 6})
    tx, ty = F["anchor"][0] - cam["cx"] * k, F["anchor"][1] - cam["cy"] * k
    words = t.get("words", [])
    wcol = [PAL["ink"], PAL["coral"], PAL["ocean"]]
    wl = "".join(f'<div style="color:{wcol[i % 3]}">{esc(w)}</div>' for i, w in enumerate(words[:3]))
    from mm_pin import pin_box as pb
    pin = pb("tp", t.get("pin_x", 250), t.get("pin_y", 700), t.get("pin_r", 165), mouth=BASE_MOUTH.get(t.get("expr", "surprised"), "o"))
    f_ = {"surprised": (1.22, 1.22, (-9, 0), (-9, 0)), "happy": (1, .8, (-3, -4), (-3, 4)), "thinking": (1, 1, (2, 6), (-9, -10))}.get(t.get("expr", "surprised"), (1, 1, (0, 0), (0, 0)))
    face_js = (f'["l","r"].forEach(function(s,i){{var e=document.getElementById("tp-eye"+s),b=document.getElementById("tp-brow"+s);'
               f'var cx=s=="l"?-21.85:21.85; e.setAttribute("transform","translate("+cx+" -194.5) scale({f_[0]} {f_[1]}) translate("+(-cx)+" 194.5)");'
               f'var bb=s=="l"?{list(f_[2])}:{list(f_[3])}; b.setAttribute("transform","translate(0 "+bb[0]+") rotate("+bb[1]+" "+cx+" -194.5)");}});'
               f'document.getElementById("tp-needle").setAttribute("transform","rotate({t.get("needle", 24)} 0 -305)");'
               f'document.getElementById("tp-lean").setAttribute("transform","rotate({t.get("lean", 5)} 0 0)");')
    callout = ""
    if t.get("callout"):
        c = t["callout"]
        wx, wy = G.pt(P, *c["at"])
        cx_, cy_ = wx * k + tx, wy * k + ty
        callout = (f'<div style="position:absolute;left:{cx_ - 16:.0f}px;top:{cy_ - 16:.0f}px;width:32px;height:32px;border-radius:50%;background:{PAL["coral"]};border:7px solid {PAL["cream"]};box-shadow:0 3px 10px rgba(20,43,61,.4);z-index:3"></div>')
        if c.get("arrow_from"):  # a hand-drawn coral arrow from the words to the place
            ax_, ay_ = c["arrow_from"]
            mx, my = (ax_ + cx_) / 2 + c.get("bend", -60), (ay_ + cy_) / 2
            ang = math.atan2(cy_ - my, cx_ - mx)
            ex, ey = cx_ - 30 * math.cos(ang), cy_ - 30 * math.sin(ang)
            hx1, hy1 = ex - 34 * math.cos(ang - .5), ey - 34 * math.sin(ang - .5)
            hx2, hy2 = ex - 34 * math.cos(ang + .5), ey - 34 * math.sin(ang + .5)
            arrow = (f'M{ax_:.0f},{ay_:.0f} Q{mx:.0f},{my:.0f} {ex:.0f},{ey:.0f} M{hx1:.0f},{hy1:.0f} L{ex:.0f},{ey:.0f} L{hx2:.0f},{hy2:.0f}')
            callout += (f'<svg width="{W}" height="{H}" style="position:absolute;left:0;top:0;z-index:2;overflow:visible">'
                        f'<path d="{arrow}" fill="none" stroke="{PAL["cream"]}" stroke-width="22" stroke-linecap="round" stroke-linejoin="round"/>'
                        f'<path d="{arrow}" fill="none" stroke="{PAL["coral"]}" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/></svg>')
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
{fonts_css((A / "fonts").as_uri() + "/")}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:{W}px; height:{H}px; overflow:hidden; background:{PAL["parchment"]}; position:relative; --k:{k}; }}
.paper {{ position:absolute; inset:0; background:url({(A / "paper.png").as_uri()}); mix-blend-mode:multiply; }}
.vig {{ position:absolute; inset:0; background:radial-gradient(ellipse at 60% 45%, rgba(0,0,0,0) 55%, rgba(60,40,10,.28) 100%); }}
.words {{ position:absolute; z-index:4; right:{t.get("words_right", 56)}px; top:{t.get("words_top", 64)}px; text-align:right; font-family:'MM Display',serif; font-weight:800;
  font-size:{t.get("words_fs", 118)}px; line-height:.95; letter-spacing:-.03em; -webkit-text-stroke:14px {PAL["cream"]}; paint-order:stroke fill; }}
</style></head><body>
<svg width="{W}" height="{H}" style="position:absolute;left:0;top:0"><defs>{"".join(M.defs)}</defs>
<g transform="matrix({k} 0 0 {k} {tx} {ty})">{"".join(M.layers)}</g></svg>
<div class="paper"></div><div class="vig"></div>{callout}
<div class="words">{wl}</div>
{pin}
<script>{face_js}</script>
</body></html>'''


def thumbnail(script_path, channel_path, out_png):
    from playwright.sync_api import sync_playwright
    script = json.loads(Path(script_path).read_text())
    tmp = Path(out_png).with_suffix(".html")
    tmp.write_text(thumbnail_html(script))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        pg.goto(tmp.resolve().as_uri())
        pg.evaluate("document.fonts.ready.then(() => 1)")
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(out_png))
        b.close()
    tmp.unlink()
    print("thumbnail", out_png)


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "thumbnail":
        thumbnail(sys.argv[2], ROOT / "channels" / "history.json", sys.argv[3])
    else:
        print(__doc__)
