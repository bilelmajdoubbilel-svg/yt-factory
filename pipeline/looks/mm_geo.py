"""Map Minutes geography: projections, simplification and SVG paths from public-domain data.

Data: assets/mapminutes/geo/na.json, built once by mm_geo_prep.py from
  - Natural Earth 1:50m (public domain): land, countries, Canadian provinces, lakes, physical regions, places
  - US Census Bureau cartographic boundary files 2017 (public domain, via the us-atlas package): US states
World units are kilometres in the chosen projection (x east, y south), so "100 km" is 100 units.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
GEO = ROOT / "assets" / "mapminutes" / "geo" / "na.json"
R_EARTH = 6371.0

# Lambert conformal conic presets (standard parallels, origin). "canada" matches Statistics Canada's
# LCC (49N, 77N); "us" is the Census Albers-like framing for the lower 48; "na" fits both countries.
PROJECTIONS = {
    "canada": {"lat1": 49.0, "lat2": 77.0, "lat0": 62.0, "lon0": -95.0},
    "na": {"lat1": 37.0, "lat2": 65.0, "lat0": 50.0, "lon0": -96.0},
    "us": {"lat1": 29.5, "lat2": 45.5, "lat0": 38.0, "lon0": -96.0},
}


class LCC:
    def __init__(self, lat1, lat2, lat0, lon0):
        p1, p2, p0 = map(math.radians, (lat1, lat2, lat0))
        self.lon0 = math.radians(lon0)
        t = lambda p: math.tan(math.pi / 4 + p / 2)
        self.n = math.log(math.cos(p1) / math.cos(p2)) / math.log(t(p2) / t(p1))
        self.F = math.cos(p1) * t(p1) ** self.n / self.n
        self.rho0 = R_EARTH * self.F / t(p0) ** self.n

    def fwd(self, lon, lat):
        lon = np.radians(np.asarray(lon, dtype=float))
        lat = np.radians(np.clip(np.asarray(lat, dtype=float), -89.9, 89.9))
        rho = R_EARTH * self.F / np.tan(np.pi / 4 + lat / 2) ** self.n
        th = self.n * (lon - self.lon0)
        x = rho * np.sin(th)
        y = self.rho0 - rho * np.cos(th)
        return x, -y  # SVG: y grows downwards

    def inv(self, x, y):
        x = np.asarray(x, dtype=float)
        y = -np.asarray(y, dtype=float)
        rho = np.sign(self.n) * np.sqrt(x ** 2 + (self.rho0 - y) ** 2)
        th = np.arctan2(x, self.rho0 - y)
        lat = 2 * np.arctan((R_EARTH * self.F / rho) ** (1 / self.n)) - np.pi / 2
        lon = self.lon0 + th / self.n
        return np.degrees(lon), np.degrees(lat)


@lru_cache(maxsize=None)
def proj(name="canada"):
    return LCC(**PROJECTIONS[name])


@lru_cache(maxsize=1)
def data():
    return json.loads(GEO.read_text())


def rdp(pts, eps):
    """Ramer-Douglas-Peucker on an (n, 2) array; iterative, keeps the endpoints."""
    n = len(pts)
    if n < 3 or eps <= 0:
        return pts
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        p, q = pts[a], pts[b]
        seg = q - p
        L = math.hypot(*seg)
        sub = pts[a + 1:b]
        if L == 0:
            d = np.hypot(*(sub - p).T)
        else:
            d = np.abs(seg[0] * (sub[:, 1] - p[1]) - seg[1] * (sub[:, 0] - p[0])) / L
        i = int(np.argmax(d))
        if d[i] > eps:
            m = a + 1 + i
            keep[m] = True
            stack += [(a, m), (m, b)]
    return pts[keep]


def ring_area(pts):
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def densify(a, max_deg=0.4):
    """Split long lon/lat segments before projecting: a run along a parallel (the 49th) is an arc in a conic
    projection, not the chord between its two vertices."""
    if len(a) < 2:
        return a
    seg = np.diff(a, axis=0)
    n = np.maximum(1, np.ceil(np.abs(seg).max(axis=1) / max_deg).astype(int))
    if n.max() == 1:
        return a
    out = [a[:1]]
    for i in range(len(seg)):
        f = (np.arange(1, n[i] + 1) / n[i])[:, None]
        out.append(a[i] + seg[i] * f)
    return np.vstack(out)


def project_rings(mp, P, eps=2.5, min_area=120.0, bbox=None):
    """MultiPolygon (lon/lat) -> list of projected rings (numpy arrays). Tiny islands dropped."""
    out = []
    for poly in mp:
        for k, ring in enumerate(poly):
            a = densify(np.asarray(ring, dtype=float))
            x, y = P.fwd(a[:, 0], a[:, 1])
            pts = np.stack([x, y], 1)
            if ring_area(pts) < (min_area if k == 0 else min_area * 2):
                continue
            if bbox is not None:
                x0, y0, x1, y1 = bbox
                if pts[:, 0].max() < x0 or pts[:, 0].min() > x1 or pts[:, 1].max() < y0 or pts[:, 1].min() > y1:
                    continue
            s = rdp(pts, eps)
            if len(s) >= 4:
                out.append(s)
    return out


def project_lines(lines, P, eps=2.0):
    out = []
    for ln in lines:
        a = densify(np.asarray(ln, dtype=float))
        x, y = P.fwd(a[:, 0], a[:, 1])
        s = rdp(np.stack([x, y], 1), eps)
        if len(s) >= 2:
            out.append(s)
    return out


def d_rings(rings, closed=True):
    parts = []
    for r in rings:
        parts.append("M" + " ".join(f"{x:.1f},{y:.1f}" for x, y in r) + ("Z" if closed else ""))
    return "".join(parts)


def d_lines(lines):
    return d_rings(lines, closed=False)


def path_len(pts):
    return float(np.sum(np.hypot(*np.diff(pts, axis=0).T)))


def pt(P, lon, lat):
    x, y = P.fwd(lon, lat)
    return float(x), float(y)


def parallel(P, lat, lon0=-141.0, lon1=-52.0, step=0.5):
    lons = np.arange(lon0, lon1 + 1e-9, step)
    x, y = P.fwd(lons, np.full_like(lons, lat))
    return np.stack([x, y], 1)


def meridian(P, lon, lat0=24.0, lat1=84.0, step=0.5):
    lats = np.arange(lat0, lat1 + 1e-9, step)
    x, y = P.fwd(np.full_like(lats, lon), lats)
    return np.stack([x, y], 1)


def graticule(P, every=10):
    lines = [parallel(P, la, -180, -40, 1.0) for la in range(20, 90, every)]
    lines += [meridian(P, lo, 16, 86, 1.0) for lo in range(-180, -30, every)]
    return lines


def route(P, lonlats, step_km=20.0):
    """A route through lon/lat waypoints, densified along great-circle-ish straight segments in the
    projection and gently smoothed (Chaikin), so the coral line reads as a drawn path."""
    pts = np.array([pt(P, lo, la) for lo, la in lonlats])
    for _ in range(3):
        if len(pts) < 3:
            break
        q = 0.75 * pts[:-1] + 0.25 * pts[1:]
        r = 0.25 * pts[:-1] + 0.75 * pts[1:]
        mid = np.empty((2 * len(q), 2))
        mid[0::2], mid[1::2] = q, r
        pts = np.vstack([pts[:1], mid, pts[-1:]])
    return pts


def place(name):
    for p in data()["places"]:
        if p["name"].lower() == name.lower():
            return p
    raise KeyError(f"place not in na.json: {name}")
