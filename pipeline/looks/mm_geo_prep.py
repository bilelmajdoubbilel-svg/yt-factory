"""Build assets/mapminutes/geo/na.json from public-domain sources (run once; needs network + shapely).

    pip install shapely
    python pipeline/looks/mm_geo_prep.py [cache_dir]

Sources (all public domain; see assets/mapminutes/geo/LICENSES.md):
  Natural Earth 1:50m vectors, GitHub mirror nvkelso/natural-earth-vector (naturalearthdata.com)
  US Census Bureau cartographic boundary files 2017, states, as TopoJSON in the us-atlas npm package
Derived layers are computed here: the land within 100 km of the southern Canada-US border (the area
Statistics Canada measures), the southern border line, label points.
"""
import io
import json
import math
import sys
import tarfile
from pathlib import Path

import requests
from shapely.geometry import LineString, MultiPolygon, Polygon, mapping, shape
from shapely.ops import transform, unary_union

sys.path.insert(0, str(Path(__file__).parent))
import mm_geo  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "assets" / "mapminutes" / "geo" / "na.json"
NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/{}.geojson"
US_ATLAS = "https://registry.npmjs.org/us-atlas/-/us-atlas-3.0.1.tgz"
BBOX = (-180.0, 14.0, -40.0, 85.0)


def fetch(name, cache):
    p = cache / f"{name}.geojson"
    if not p.exists():
        r = requests.get(NE.format(name), timeout=120)
        r.raise_for_status()
        p.write_bytes(r.content)
    return json.loads(p.read_text())


def us_states(cache):
    p = cache / "states-10m.json"
    if not p.exists():
        r = requests.get(US_ATLAS, timeout=120)
        r.raise_for_status()
        with tarfile.open(fileobj=io.BytesIO(r.content)) as t:
            p.write_bytes(t.extractfile("package/states-10m.json").read())
    topo = json.loads(p.read_text())
    sc, tr = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
        arcs.append(pts)

    def ring(ids):
        pts = []
        for i in ids:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts += a if not pts else a[1:]
        return pts
    out = []
    for g in topo["objects"]["states"]["geometries"]:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        geom = MultiPolygon([Polygon(ring(p[0]), [ring(h) for h in p[1:]]) for p in polys])
        out.append({"name": g["properties"]["name"], "fips": g["id"], "geom": geom.buffer(0)})
    return out


def clip(g):
    from shapely.geometry import box
    return g.intersection(box(*BBOX))


def keep_big(g, min_km2=60.0):
    polys = list(g.geoms) if isinstance(g, MultiPolygon) else [g] if isinstance(g, Polygon) else []
    def km2(p):
        c = p.centroid
        return p.area * 111.2 ** 2 * max(0.05, math.cos(math.radians(c.y)))
    return MultiPolygon([p for p in polys if not p.is_empty and km2(p) >= min_km2])


def mp_coords(g, tol=0.01, nd=3):
    g = keep_big(g.simplify(tol, preserve_topology=True))
    return [[[[round(x, nd), round(y, nd)] for x, y in r.coords] for r in [p.exterior, *p.interiors]] for p in g.geoms]


def lines_coords(g, tol=0.01, nd=3):
    gs = list(getattr(g, "geoms", [g]))
    out = []
    for ln in gs:
        if isinstance(ln, LineString) and ln.length > 0:
            out.append([[round(x, nd), round(y, nd)] for x, y in ln.simplify(tol).coords])
    return out


def main(cache):
    cache.mkdir(parents=True, exist_ok=True)
    countries = fetch("ne_50m_admin_0_countries", cache)
    adm1 = fetch("ne_50m_admin_1_states_provinces", cache)
    land = fetch("ne_50m_land", cache)
    lakes = fetch("ne_50m_lakes", cache)
    regions = fetch("ne_50m_geography_regions_polys", cache)
    places = fetch("ne_50m_populated_places_simple", cache)

    cty = {}
    for f in countries["features"]:
        a3 = f["properties"]["ADM0_A3"]
        if a3 in ("CAN", "USA", "MEX", "GRL"):
            cty[a3] = clip(shape(f["geometry"]).buffer(0))
    land_g = clip(unary_union([shape(f["geometry"]) for f in land["features"]]))

    provinces = []
    for f in adm1["features"]:
        p = f["properties"]
        if p["admin"] != "Canada":
            continue
        provinces.append({"name": p["name"], "code": p["postal"], "label": [p["longitude"], p["latitude"]],
                          "geom": mp_coords(shape(f["geometry"]).buffer(0))})

    states = []
    for s in us_states(cache):
        if clip(s["geom"]).is_empty:
            continue
        rp = s["geom"].representative_point()
        states.append({"name": s["name"], "fips": s["fips"], "label": [round(rp.x, 3), round(rp.y, 3)],
                       "geom": mp_coords(clip(s["geom"]))})

    lake_list = []
    for f in lakes["features"]:
        g = shape(f["geometry"])
        c = g.centroid
        if -170 < c.x < -50 and 30 < c.y < 80 and g.area > 0.15:
            lake_list.append({"name": f["properties"].get("name") or "", "geom": mp_coords(g.buffer(0), 0.01)})

    reg = []
    for f in regions["features"]:
        p = f["properties"]
        if p["NAME"] in ("CANADIAN SHIELD", "ROCKY MOUNTAINS", "GREAT PLAINS", "BARREN GROUNDS", "ARCTIC ARCHIPELAGO",
                         "APPALACHIAN MTS.", "COAST MOUNTAINS", "MACKENZIE MTS.", "YUKON PLATEAU", "GREAT BASIN"):
            g = clip(shape(f["geometry"]).buffer(0))
            reg.append({"name": p["NAME"].title().replace("Mts.", "Mountains"), "kind": p["FEATURECLA"],
                        "geom": mp_coords(g, 0.02)})

    pl = []
    for f in places["features"]:
        p = f["properties"]
        if p["adm0_a3"] in ("CAN", "USA"):
            pl.append({"name": p["name"], "lon": round(p["longitude"], 3), "lat": round(p["latitude"], 3),
                       "pop": int(p.get("pop_max") or 0), "rank": p.get("scalerank"), "country": p["adm0_a3"],
                       "capital": p.get("featurecla", "").startswith("Admin-0 capital")})

    # derived: Canada within 100 km of the southern border with the lower 48 (StatCan's "southern border")
    P = mm_geo.proj("canada")
    fwd = lambda x, y, z=None: P.fwd(x, y)
    inv = lambda x, y, z=None: P.inv(x, y)
    us48 = MultiPolygon([p for p in cty["USA"].geoms if p.centroid.x > -130 and p.centroid.y < 50])
    ca_p = transform(fwd, cty["CAN"])
    us48_p = transform(fwd, us48)
    strip_p = ca_p.intersection(us48_p.buffer(100.0, 64))
    strip = transform(inv, strip_p)
    border = transform(inv, ca_p.boundary.intersection(us48_p.buffer(2.0)))
    ca_km2 = ca_p.area
    lakes_p = transform(fwd, unary_union([shape(f["geometry"]) for f in lakes["features"]]).buffer(0))
    strip_land_km2 = strip_p.difference(lakes_p).area
    ca_land_km2 = ca_p.difference(lakes_p).area

    out = {
        "meta": {
            "sources": [
                "Natural Earth 1:50m vectors (public domain), https://www.naturalearthdata.com, mirror https://github.com/nvkelso/natural-earth-vector",
                "US Census Bureau cartographic boundary files 2017, states (public domain), https://www2.census.gov/geo/tiger/GENZ2017/shp/, via us-atlas 3.0.1 (ISC)",
            ],
            "derived": "ca_strip_100km = Canada within 100 km of the lower-48 border, computed in LCC 49N/77N with shapely",
            "areas_km2_ne50m_approx": {"canada_incl_lakes": round(ca_km2), "canada_land": round(ca_land_km2),
                                       "strip_land": round(strip_land_km2),
                                       "strip_share_of_land_pct": round(100 * strip_land_km2 / ca_land_km2, 1)},
        },
        "land": mp_coords(land_g, 0.01),
        "countries": {k: mp_coords(v, 0.01) for k, v in cty.items()},
        "provinces": provinces,
        "states": states,
        "lakes": lake_list,
        "regions": reg,
        "places": pl,
        "derived": {"ca_strip_100km": mp_coords(strip, 0.01), "border_ca_us48": lines_coords(border, 0.005)},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print("wrote", OUT, f"{OUT.stat().st_size / 1e6:.2f} MB", json.dumps(out["meta"]["areas_km2_ne50m_approx"]))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/mm-geo-cache"))
