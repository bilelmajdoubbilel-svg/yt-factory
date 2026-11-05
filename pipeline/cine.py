"""Cinematic composer: every scene is a world (multiplane layers) + the channel host + the scene's
content, with a moving camera, depth of field, transitions, a ducked music bed and CC0 effects.
Used when the script has "style": "cinematic". Entry: compose.py calls cine.main()."""
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import compose as C
from cinema import char_box, prop_svg
from worlds import WORLDS, DEPTHS, get_world

ROOT = Path(__file__).resolve().parent.parent
SFX = ROOT / "assets" / "sfx-cc0"
CATALOG = {s["id"]: s for s in json.loads((SFX / "catalog.json").read_text())["sounds"]}


# ------------------------------------------------------------------ host direction

def _first_cue(items, key="cue"):
    for it in reversed(items or []):
        if isinstance(it, dict) and it.get(key):
            return it[key]
    return None


def host_spec(S):
    t, d = S.spec["type"], S.d
    h = S.spec.get("host", {})
    if h is False or t == "chapter" or (isinstance(h, dict) and h.get("hidden")):
        return None
    p = S.portrait
    right = getattr(S, "idx", 0) % 2 == 1
    spec = {"x": (300 if right else -300) if p else (650 if right else -650), "y": 1520 if p else 1000,
            "scale": .74 if p else .95, "flip": right,
            "prop": None, "pose": "idle", "expr": "neutral", "acts": [], "outfit": S.theme.get("outfit", "money")}
    last = lambda k: _first_cue(d.get(k))
    acts = {
        "counter": [{"t": .25, "pose": "present", "look": 14}, {"cue": d.get("cue"), "dt": 1.45, "expr": "surprised"},
                    {"cue": d.get("cue"), "dt": 2.4, "expr": "happy"}],
        "compare": [{"t": .3, "pose": "chin", "expr": "thinking", "look": 14}, {"cue": last("items"), "dt": .45, "expr": "surprised", "pose": "present"}],
        "bars": [{"t": .3, "pose": "present", "look": 14}, {"cue": last("items"), "dt": .95, "expr": "surprised"}],
        "share": [{"t": .3, "pose": "chin", "expr": "thinking", "look": 14}, {"cue": d.get("cue"), "dt": 1.45, "expr": "proud", "pose": "point"}],
        "dots": [{"t": .3, "pose": "present", "look": 14}, {"cue": d.get("cue"), "dt": 1.3, "expr": "happy", "hop": True}],
        "statement": [{"t": .3, "expr": "thinking", "pose": "chin"}, {"cue": last("lines"), "expr": "proud", "pose": "point", "look": 14}],
        "end": [{"t": .3, "expr": "thinking", "pose": "chin"}, {"cue": last("lines"), "expr": "happy", "pose": "wave"}],
        "quote": [{"t": .3, "look": 14}, {"cue": d.get("cue"), "dt": 1.0, "expr": "surprised", "pose": "shrug"},
                  {"t": max(1.0, S.narr_end - .5), "expr": "worried", "pose": "idle"}],
        "flow": [{"t": .3, "pose": "point", "look": 14}, {"cue": last("steps"), "expr": "proud", "pose": "present"}],
        "cards": [{"t": .3, "pose": "present", "look": 14}, {"cue": last("cards"), "dt": .4, "expr": "happy"}],
        "pricetag": [{"t": .2, "pose": "present", "look": 14}, {"cue": d.get("cue"), "dt": .6, "expr": "happy"}],
        "years": [{"t": .3, "expr": "neutral", "look": 14}, {"cue": d.get("cue_end"), "dt": .8, "expr": "happy"}],
        "lines": [{"t": .3, "expr": "worried", "look": 14}, {"cue": _first_cue([s for s in d.get("series", []) if s.get("highlight")]), "dt": .9, "expr": "happy", "pose": "point"}],
        "cta": [{"t": .15, "pose": "wave", "expr": "happy"}, {"cue": d.get("cue"), "dt": .2, "hop": True}],
        "shot": [],
    }.get(t, [])
    spec["acts"] = acts
    if isinstance(h, dict):
        spec.update({k: v for k, v in h.items() if k != "acts"})
        if "acts" in h:
            spec["acts"] = h["acts"]
    return spec


def host_js(S, hid, spec):
    js = [f'CIN.setPose(tl, "{hid}", "{spec["pose"]}", 0)', f'CIN.blinks(tl, "{hid}", {S.dur:.2f}, {int(S.sid[1:]) * 7 + 3})',
          f'CIN.breathe(tl, "{hid}", {S.dur:.2f})']
    enter = spec.get("enter")
    if enter:
        js.append(f'CIN.walk(tl, "{hid}", {enter["dx"]}, {enter.get("t", 0)}, {enter.get("dur", 2.4)}, {"false" if spec.get("prop") else "true"})')
    for a in spec["acts"]:
        base = S.cue(a.get("cue"), a.get("t", .3)) if a.get("cue") else a.get("t", .3)
        t = round(min(S.dur - .3, base + a.get("dt", 0)), 3)
        if a.get("expr"):
            js.append(f'CIN.face(tl, "{hid}", "{a["expr"]}", {t})')
        if a.get("pose"):
            js.append(f'CIN.pose(tl, "{hid}", "{a["pose"]}", {t + .05})')
        if a.get("look") is not None:
            js.append(f'CIN.look(tl, "{hid}", {a["look"]}, {t})')
        if a.get("hop"):
            js.append(f'CIN.hop(tl, "{hid}", {t + .1})')
        if a.get("walk"):
            js.append(f'CIN.walk(tl, "{hid}", {a["walk"]}, {t}, {a.get("walk_dur", 1.6)}, true)')
    return js


# ------------------------------------------------------------------ extra scene kinds

def t_chapter_cine(S):
    sid, d = S.sid, S.d
    inner, nw = C.words_html(d.get("title", ""), sid, "t")
    markup = f'''
    <div class="center" style="padding-bottom:0">
      <div id="{sid}-num" class="kicker" style="color:var(--gold)">PART {C.esc(d.get("num", ""))}</div>
      <div id="{sid}-title" class="chap-title-c">{inner}</div>
      <div id="{sid}-rule" class="chap-rule"></div>
    </div>'''
    css = f'''
    #root .chap-title-c {{ font-family:'PL Display',sans-serif; font-size:{S.s(104, 96)}px; line-height:1.04; text-align:center; max-width:{S.s(1500, 900)}px; color: var(--paper); }}
    #root .chap-title-c .w {{ display:inline-block; }}
    #root .chap-title-c .hl {{ color: var(--gold); }}
    #root .chap-rule {{ width:180px; height:6px; background: var(--accent); margin-top:40px; border-radius:3px; }}'''
    ids = ",".join(f'"#{sid}-t-w{i}"' for i in range(nw))
    js = [f'tl.fromTo("#{sid}-num", {{opacity:0, y:-24}}, {{opacity:1, y:0, duration:.6, ease:"power3.out"}}, .25)',
          f'tl.fromTo([{ids}], {{opacity:0, filter:"blur(10px)"}}, {{opacity:1, filter:"blur(0px)", duration:.22, stagger:.08, ease:"power2.out"}}, .45)',
          f'tl.fromTo("#{sid}-rule", {{scaleX:0}}, {{scaleX:1, duration:.6, ease:"expo.out"}}, .9)']
    return markup, css, js


def t_cta(S):
    sid, d = S.sid, S.d
    at = S.cue(d.get("cue"), S.narr_end * .4)
    markup = f'''
    <div class="center">
      <div id="{sid}-btn" class="sub-btn"><span class="sub-play"></span><span id="{sid}-txt">SUBSCRIBE</span></div>
      <div id="{sid}-label" class="label">{C.rich(d.get("label", ""), sid, "l")}</div>
    </div>'''
    css = f'''
    #root .sub-btn {{ display:flex; align-items:center; gap:22px; background:#E5372B; color:#fff; font-family:'PL Display',sans-serif;
      font-size:{S.s(64, 70)}px; padding:26px 54px; border-radius:22px; }}
    #root .sub-play {{ width:0; height:0; border-left:34px solid #fff; border-top:22px solid transparent; border-bottom:22px solid transparent; }}'''
    js = [f'tl.fromTo("#{sid}-btn", {{opacity:0, y:60, scale:.9}}, {{opacity:1, y:0, scale:1, duration:.6, ease:"expo.out"}}, .3)',
          f'tl.to("#{sid}-btn", {{scale:.9, duration:.08, ease:"power2.in"}}, {at})',
          f'tl.to("#{sid}-btn", {{scale:1, backgroundColor:"#3A3D46", duration:.35, ease:"back.out(2.5)"}}, {at + .08})',
          f'tl.fromTo("#{sid}-label", {{opacity:0}}, {{opacity:1, duration:.4}}, {at + .4})']
    S.clicks = [at]
    return markup, css, js


def shot_elements(S):
    """In-world elements for story shots. Returns ({layer: html}, css, js)."""
    sid, d = S.sid, S.d
    per, css, js = {}, "", []
    for k, el in enumerate(d.get("elements", [])):
        eid = f"{sid}-e{k}"
        layer = el.get("layer", "mid")
        x, y = el.get("x", 0), el.get("y", 300) + (S.F - 790)
        at = S.cue(el.get("cue"), el.get("t", .4))
        kind = el["kind"]
        if kind == "hangtag":
            sc = el.get("scale", 1.0)
            html_ = (f'<div id="{eid}" style="position:absolute;left:{x - 210 * sc:.0f}px;top:{y}px;width:{420 * sc:.0f}px;height:{330 * sc:.0f}px;">'
                     f'<svg viewBox="-210 0 420 330" width="{420 * sc:.0f}" height="{330 * sc:.0f}" overflow="visible">'
                     f'<path d="M-100,0 L-100,112 M100,0 L100,112" stroke="#1A1420" stroke-width="5"/>'
                     f'<g transform="translate(0 170)">{prop_svg("tag", 0, 0, 1.0).replace("$1.50", C.esc(el.get("text", "$1.50")))}</g></svg></div>')
            js += [f'tl.fromTo("#{eid}", {{rotation:-28, y:-260, opacity:0, transformOrigin:"50% 0%"}}, {{rotation:0, y:0, opacity:1, duration:1.5, ease:"elastic.out(1, 0.38)"}}, {at})']
            if el.get("cue2"):
                t2 = S.cue(el["cue2"], at + 3)
                js.append(f'tl.to("#{eid}", {{rotation:7, duration:.18, yoyo:true, repeat:3, ease:"sine.inOut"}}, {t2})')
            S.pops.append(at + .3)
        elif kind == "yearboard":
            html_ = (f'<div id="{eid}" class="yearboard" style="position:absolute;left:{x - 190}px;top:{y}px;">'
                     f'<div class="yb-cap">{C.esc(el.get("caption", "YEAR"))}</div><div id="{eid}-n" class="yb-n">{C.esc(el["from"])}</div></div>')
            css += f'''
    #root .yearboard {{ width:380px; padding:16px 0 22px; border-radius:20px; background:#141016; border:5px solid #5A3E30; text-align:center; box-shadow:0 0 60px rgba(255,180,90,.25); }}
    #root .yb-cap {{ font-family:'PL Mono',monospace; font-size:30px; letter-spacing:.3em; color:#B99A7A; }}
    #root .yb-n {{ font-family:'PL Display',sans-serif; font-size:120px; line-height:1; color:#FFD58F; font-variant-numeric:tabular-nums; }}'''
            js += [f'tl.fromTo("#{eid}", {{opacity:0, y:-30}}, {{opacity:1, y:0, duration:.6, ease:"power3.out"}}, {max(.1, el.get("t", .2))})',
                   f'CIN.roll(tl, "#{eid}-n", {int(el["from"])}, {int(el["to"])}, {at}, {el.get("dur", 1.6)}, 0, "", "", false)']
            S.pops.append(at + el.get("dur", 1.6))
        else:
            continue
        per[layer] = per.get(layer, "") + html_
    return per, css, js


# ------------------------------------------------------------------ baked backgrounds (speed)

BAKE_PAD = 0.25   # extra canvas around the frame so camera moves never reveal an edge
BAKED = {}        # (world spec, layer, focus) -> served path


def bake_backgrounds(build, jobs, W, H, F):
    """Render each world's far/mid/fore layer once, blurred for its focus, to a PNG.
    jobs: set of (world_spec, focus). Fills BAKED. Frames then only move bitmaps."""
    from playwright.sync_api import sync_playwright
    font = (ROOT / "assets/fonts/pl-display.woff2").as_uri()
    out = (build / "assets" / "bg").resolve()
    out.mkdir(parents=True, exist_ok=True)
    pw_, ph_ = int(W * (1 + 2 * BAKE_PAD)), int(H * (1 + 2 * BAKE_PAD))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": pw_, "height": ph_})
        for spec, focus in sorted(jobs):
            world = get_world(spec, F, H)
            for layer in ("far", "mid", "fore"):
                d = DEPTHS[layer]
                blur = min(16, 13 * abs(1 / d - 1 / focus))
                name = f"{spec.replace(':', '_').lower()}-{layer}-f{focus:.2f}.png"
                html_ = (f'<!doctype html><html><head><meta charset="utf-8"><style>@font-face{{font-family:"PL Display";src:url("{font}");font-weight:100 900}}'
                         f'*{{margin:0;padding:0}} html,body{{width:{pw_}px;height:{ph_}px;overflow:hidden;background:transparent}}</style></head><body>'
                         f'<div style="position:absolute;left:{int(W * BAKE_PAD)}px;top:{int(H * BAKE_PAD)}px;width:{W}px;height:{H}px;'
                         f'filter:{"blur(%.2fpx)" % blur if blur > .4 else "none"}">'
                         f'<div style="position:absolute;left:{W // 2}px;top:0">{world[layer]}</div></div></body></html>')
                tmp = out / (name + ".html")
                tmp.write_text(html_)
                pg.goto(tmp.as_uri())
                pg.wait_for_timeout(150)
                pg.screenshot(path=str(out / name), omit_background=(layer != "far"))
                tmp.unlink()
                BAKED[(spec, layer, round(focus, 2))] = f"assets/bg/{name}"
        b.close()


# ------------------------------------------------------------------ camera + transitions

CAM_MOVES = [  # (start, end) as (x, y, z); varied by scene index
    ((-30, 10, 1.00), (40, -10, 1.07)),   # push in
    ((-90, 0, 1.04), (90, 0, 1.05)),      # truck right
    ((0, 0, 1.11), (0, 10, 1.02)),        # pull out
    ((90, -10, 1.05), (-80, 0, 1.06)),    # truck left
    ((0, 50, 1.05), (20, -40, 1.08)),     # crane up
]


def ambient_js(sid, anim, dur):
    """Cheap background life: transforms and opacity only, on live elements (never on baked pictures)."""
    js = []
    D = max(1.0, dur)
    for layer, sel, kind in anim:
        q = f"#{sid}-L{layer} {sel}"
        if kind == "walk":
            js.append(f'tl.fromTo("{q}", {{x:0}}, {{x:(i, el) => parseFloat(el.dataset.v) * {D:.2f}, duration:{D:.2f}, ease:"none"}}, 0)')
            n = max(1, int(D / .34))
            js.append(f'tl.fromTo("{q}", {{y:0}}, {{y:-7, duration:.17, yoyo:true, repeat:{2 * n - 1}, ease:"sine.inOut"}}, 0)')
        elif kind == "glide":
            js.append(f'tl.fromTo("{q}", {{x:0}}, {{x:(i, el) => parseFloat(el.dataset.v) * {D:.2f}, duration:{D:.2f}, ease:"none"}}, 0)')
        elif kind == "rise":
            n = max(0, int(D / 2.4) - 1)
            js.append(f'tl.fromTo("{q}", {{y:0, scale:.7}}, {{y:(i, el) => -parseFloat(el.dataset.dy), scale:1.25, duration:2.4, ease:"none", repeat:{n}, stagger:.8}}, 0)')
            js.append(f'tl.fromTo("{q}", {{opacity:0}}, {{opacity:.85, duration:1.2, yoyo:true, repeat:{2 * n + 1}, ease:"sine.inOut", stagger:.8}}, 0)')
        elif kind == "drift":
            js.append(f'tl.fromTo("{q}", {{x:0, y:0}}, {{x:(i) => (i % 2 ? -1 : 1) * 46, y:(i) => (i % 3 - 1) * 24, duration:{D:.2f}, ease:"sine.inOut"}}, 0)')
        elif kind == "flicker":
            js.append(f'tl.set("{q}", {{opacity:1}}, 0)')
            for t0 in (D * .23, D * .71):
                js.append(f'tl.to("{q}", {{opacity:.35, duration:.07, yoyo:true, repeat:3, ease:"none"}}, {t0:.2f})')
        elif kind == "flicker_soft":
            n = max(1, int(D / 1.4))
            js.append(f'tl.fromTo("{q}", {{opacity:.35}}, {{opacity:1, duration:.7, yoyo:true, repeat:{2 * n - 1}, ease:"sine.inOut"}}, 0)')
    return js


def scene_file_cine(S, idx, tin, tout):
    sid, W, H = S.sid, S.W, S.H
    world = get_world(S.spec.get("world", "stage"), S.F, H)
    t = S.spec["type"]
    # the lit studio puts data on a light screen panel: templates switch to dark ink (compose.lt)
    # light screen panel in the landscape studio; Shorts get a compact dark glass card instead
    S.light = (bool(world.get("panel")) or S.portrait) and t != "shot"
    if t == "chapter":
        markup, css, js = t_chapter_cine(S)
    elif t == "cta":
        markup, css, js = t_cta(S)
    elif t == "shot":
        markup, css, js = "", "", []
    else:
        markup, css, js = C.TEMPLATES[t](S)
    extra, ecss, ejs = shot_elements(S)
    css += ecss
    js += ejs
    host = host_spec(S)
    hid = f"{sid}-host"
    if host:
        world["near"] += char_box(hid, host["x"], host["y"], host["scale"], flip=host.get("flip", False), outfit=host["outfit"],
                                  expr=host["expr"], pose=host["pose"], prop=host.get("prop"), animated=True)
        js += host_js(S, hid, host)
    for layer, html_ in extra.items():
        world[layer] += html_
    if S.portrait:
        wrap = "translate(0px,-300px) scale(.8)"
    elif host and t == "flow" and len(S.d.get("steps", [])) >= 4:
        # a 4-step flow is too wide to sit beside the host at .76: smaller and less offset
        wrap = f"translate({-170 if host.get('flip') else 170}px,-6px) scale(.64)"
    elif host and t not in ("chapter", "shot"):
        wrap = f"translate({-250 if host.get('flip') else 250}px,-6px) scale(.76)"
    else:
        wrap = "scale(.94)"
    cam = S.spec.get("cam")
    if cam:
        keys = [dict(k, t=(S.dur if k.get("t") == "end" else k.get("t", 0))) for k in cam]
    else:
        (a, b) = CAM_MOVES[idx % len(CAM_MOVES)]
        keys = [{"t": 0, "x": a[0], "y": a[1], "z": a[2]}, {"t": S.dur, "x": b[0], "y": b[1], "z": b[2], "ease": "sine.inOut"}]
    focus = S.spec.get("focus") or [{"t": 0, "f": 3.0 if t == "chapter" else 1.0}]
    layers = [{"sel": f"#{sid}-L{n}", "d": DEPTHS[n], **({"blur": False} if n == "content" else {})}
              for n in ("far", "mid", "content", "near", "fore")]
    if t == "chapter":
        layers = [dict(L, d=L["d"]) for L in layers]
    scrim = ""
    panel = ""
    if S.portrait and markup and t != "shot":
        # Shorts layout (screen px): card 140-860, captions 880-1080, host 1100-1520, YouTube UI below
        panel = '<div class="panel" style="left:30px;right:30px;top:310px;height:900px"></div>'
    elif S.light and markup:
        # the lit studio: charts sit on a screen panel, the room around it stays bright
        if S.portrait:
            panel = '<div class="panel" style="left:60px;right:60px;top:300px;height:1240px"></div>'
        else:
            panel = '<div class="panel" style="left:150px;right:150px;top:56px;bottom:30px"></div>'
    elif markup and t != "shot":
        cx, cy = (W // 2, int(H * .3)) if S.portrait else (((710 if host.get("flip") else 1210), 520) if host else (W // 2, 520))
        rx, ry = (620, 520) if S.portrait else (980, 560)
        scrim = (f'<div style="position:absolute;inset:0;background:radial-gradient(ellipse {rx}px {ry}px at {cx}px {cy}px,'
                 f'rgba(14,10,20,.66) 0%,rgba(14,10,20,.42) 55%,rgba(14,10,20,0) 100%)"></div>')
    spec_w = S.spec.get("world", "stage")
    f0 = round(focus[0]["f"], 2)
    baked = {n: BAKED.get((spec_w, n, f0)) for n in ("far", "mid", "fore")} if len(focus) == 1 else {}
    if baked and all(baked.values()):
        # extra elements placed in those layers stay live on top of the baked picture
        for L in layers:
            if L["sel"].endswith(("Lfar", "Lmid", "Lfore")):
                L["blur"] = False

    def layer_inner(n):
        if n == "content":
            return f'{scrim}<div class="cwrap{" lp" if S.light else ""}" style="transform:{wrap}">{panel}{markup}</div>'
        if baked.get(n):
            img = (f'<img src="{baked[n]}" alt="" data-layout-ignore style="position:absolute;left:{-int(W * BAKE_PAD)}px;top:{-int(H * BAKE_PAD)}px;'
                   f'width:{int(W * (1 + 2 * BAKE_PAD))}px;height:{int(H * (1 + 2 * BAKE_PAD))}px">')
            live = world.get("live", {}).get(n, "") + extra.get(n, "")
            return img + (f'<div style="position:absolute;left:{W // 2}px;top:0" data-layout-ignore>{live}</div>' if live else "")
        live = world.get("live", {}).get(n, "")
        return f'<div style="position:absolute;left:{W // 2}px;top:0" data-layout-ignore>{world[n]}{live}</div>'
    # z-order: the floor and host ("near") sit under the content, so chart labels and source lines that
    # reach below the horizon stay readable (the stage floor used to cover them).
    lay_html = "".join(f'<div id="{sid}-L{n}" class="L">{layer_inner(n)}</div>' for n in ("far", "mid", "near", "content", "fore"))
    js.append(f'CIN.camera(tl, "{sid}", {json.dumps(layers)}, {json.dumps(keys)}, {json.dumps(focus)}, {S.dur:.3f}, {S.spec.get("shake", .6)})')
    js += ambient_js(sid, world.get("anim", []), S.dur)
    if tin == "whip":
        js.append(f'tl.fromTo("#{sid}-whip", {{x:{int(W * .28)}, filter:"blur(18px)"}}, {{x:0, filter:"blur(0px)", duration:.34, ease:"power3.out"}}, 0)')
    if tout == "whip":
        js.append(f'tl.to("#{sid}-whip", {{x:{-int(W * .28)}, filter:"blur(18px)", duration:.24, ease:"power3.in"}}, {max(.2, S.dur - .24):.3f})')
    if tout == "dip":
        js.append(f'tl.fromTo("#{sid}-dip", {{opacity:0}}, {{opacity:.5, duration:.1}}, {max(.2, S.dur - .1):.3f})')
    if tin == "fade":
        js.append(f'tl.fromTo("#{sid}-dip", {{opacity:1}}, {{opacity:0, duration:.6, ease:"power2.out"}}, 0)')
    js.append(f'window.__timelines["{sid}"] = tl;')
    js_text = "\n    ".join(["const tl = gsap.timeline({ paused: true });"] +
                             [ln if ln.rstrip().endswith((";", "}")) else ln + ";" for ln in js])
    return f'''<template>
  <style>{C.base_css(S)}{css}
    #root {{ background:#000; }}
    #root .kicker {{ color:#C9C4BA; }}
    #root .src {{ color:#A9A6B0; font-size:{S.s(38, 36)}px; left:0; right:0; text-align:center; }}
    #root .step-n {{ font-size:44px; }}
    #root .note {{ font-size:{S.s(38, 34)}px; }}
    /* content is scaled ~.76-.8 next to the host: keep labels >= 28 px on screen */
    #root .col-lab, #root .ln-lab, #root .card-sub, #root .share-lab {{ font-size:{S.s(40, 38)}px; }}
    #root .col-lab {{ left:-80px; width:460px; }}
    #root .cwrap {{ text-shadow:0 3px 16px rgba(10,8,16,.55); }}
    #root .panel {{ position:absolute; border-radius:40px; background:linear-gradient(160deg,#FFFBF2,#FFF1D6);
      border:7px solid #F6C453; box-shadow:0 30px 90px rgba(10,30,40,.35); }}
    #root .cwrap.lp {{ --paper:#1E2430; --muted:#5B6270; --gold:#B86E00; --accent:#E2492A; --mint:#138A63; --panel:#FFFFFF;
      color:#1E2430; text-shadow:none; }}
    #root .cwrap.lp .kicker {{ color:#6B6F7A; }}
    #root .cwrap.lp .tag {{ background:#F6C453; color:#2B2230; }}
    #root .panel.pglass {{ background:linear-gradient(160deg,rgba(24,22,36,.86),rgba(36,26,44,.86)); border:5px solid rgba(246,196,83,.9); }}
    #root .src {{ bottom:{S.s(52, 712)}px; }}
    #root .cwrap.lp .src {{ color:#7A7F8A; }}
    /* bright worlds: cream bars vanish on beige walls, grey source lines too -> teal bars, source on a dark pill */
    #root .cwrap:not(.lp) {{ --bar:#2F7F95; }}
    #root .cwrap:not(.lp) .src {{ width:fit-content; max-width:{W - 160}px; margin:0 auto; padding:8px 22px; border-radius:14px;
      background:rgba(24,20,32,.62); color:#EDE8DE; text-shadow:none; }}
    #{sid}-whip {{ position:absolute; inset:0; }}
    #root .L {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; transform-origin:{W // 2}px {H // 2}px; }}
    #root .cwrap {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; transform-origin:{W // 2}px {H // 2}px; }}
    #{sid}-dip {{ position:absolute; inset:0; background:#000; opacity:0; pointer-events:none; }}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="{W}" data-height="{H}" data-layout-allow-overflow>
    <div id="{sid}-whip">{lay_html}</div>
    <div id="{sid}-dip"></div>
  </div>
  <script>
    {js_text}
  </script>
</template>
'''


# ------------------------------------------------------------------ fx overlay + audio

def fx_files(W, H, total, leaks, portrait):
    grain = ("url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E"
             "%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E"
             "%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")")
    leak_html = "".join(f'<div id="fx-leak{k}" class="leak"></div>' for k in range(len(leaks)))
    leak_js = "".join(
        f'tl.fromTo("#fx-leak{k}", {{opacity:0, x:-420}}, {{opacity:.9, x:0, duration:.4, ease:"power2.out"}}, {max(0, t - .25):.3f});'
        f'tl.to("#fx-leak{k}", {{opacity:0, x:420, duration:.7, ease:"power2.in"}}, {t + .2:.3f});' for k, t in enumerate(leaks))
    bars = "" if True else ('<div style="position:absolute;left:0;right:0;top:0;height:60px;background:#000"></div>'
                                '<div style="position:absolute;left:0;right:0;bottom:0;height:60px;background:#000"></div>')
    fx = f'''<template>
  <style>
    #root {{ position:absolute; inset:0; pointer-events:none; }}
    #fx-vig {{ position:absolute; inset:0; background:radial-gradient(ellipse at 50% 46%, rgba(0,0,0,0) 58%, rgba(0,0,0,.30) 100%); }}
    #fx-warm {{ position:absolute; inset:0; background:linear-gradient(160deg, rgba(255,160,80,.10), rgba(30,60,130,.12)); }}
    #fx-grain {{ position:absolute; inset:-10px; opacity:.07; background-image:{grain}; }}
    #root .leak {{ position:absolute; left:-20%; top:-20%; width:140%; height:140%; opacity:0;
      background:radial-gradient(ellipse at 30% 40%, rgba(255,190,120,.85), rgba(255,120,60,.35) 35%, rgba(255,120,60,0) 65%); }}
  </style>
  <div id="root" data-composition-id="fx" data-width="{W}" data-height="{H}" data-layout-ignore>
    <div id="fx-warm"></div><div id="fx-vig"></div><div id="fx-grain"></div>{leak_html}{bars}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    CIN.grain(tl, "#fx-grain", {total:.3f});
    {leak_js}
    window.__timelines["fx"] = tl;
  </script>
</template>
'''
    return fx


def lufs(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else -20.0


# Music follows the story (v2): the owner heard one bed that "does not match the speaking topic".
# A video is scored in cues by mood; the bed changes at story turns with a crossfade.
MOODS = {
    "tension": ["music-tension-soft.mp3"],
    "curious": ["music-lofi-tea.mp3", "music-lofi-lobby.mp3", "music-lofi-chill-loop.mp3", "music-calm-loop.mp3"],
    "warm": ["music-cozy-acoustic.mp3"],
    "playful": ["music-energetic-jazz-funk.mp3", "music-funky-house.mp3"],
    "reflective": ["music-contemplation.mp3", "music-ambient-piano.mp3"],
    "sad": ["music-emotional-piano-loop.mp3"],
    "payoff": ["music-inspiring-orchestral.mp3"],
}
XFADE = 1.6


def auto_score(script, tl):
    """Cold open = tension; each chapter = curious (a new track per chapter); the last two scenes = payoff.
    Shorts: one playful bed. A script can set its own: "score": [{"scene": 0, "mood": "tension"}, ...]."""
    if script.get("score"):
        return script["score"]
    if script.get("format") == "short":
        return [{"scene": 0, "mood": script.get("mood", "playful")}]
    types = [s["type"] for s in script["scenes"]]
    cues = [{"scene": 0, "mood": script.get("open_mood", "tension")}]
    for i, t in enumerate(types):
        if t == "chapter":
            cues.append({"scene": i, "mood": script.get("body_mood", "curious")})
    n = len(types)
    if n > 6:
        cues.append({"scene": n - 2, "mood": script.get("end_mood", "payoff")})
    return cues


def build_music(script, assets, total, tl=None):
    lib = ROOT / "music" / "shared"
    if not sorted(lib.glob("*.mp3")):
        return None
    starts = [s["start"] for s in tl["scenes"]] if tl else [0.0]
    cues = auto_score(script, tl) if tl else [{"scene": 0, "mood": "curious"}]
    if script.get("music") and not script.get("score") and script.get("format") == "short":
        cues = [{"scene": 0, "track": script["music"]}]
    used, segs = {}, []
    for k, c in enumerate(cues):
        t0 = starts[min(c["scene"], len(starts) - 1)] if k else 0.0
        t1 = starts[min(cues[k + 1]["scene"], len(starts) - 1)] if k + 1 < len(cues) else total
        if t1 - t0 < 3:
            continue
        if c.get("track"):
            name = c["track"]
        else:
            opts = MOODS.get(c["mood"], MOODS["curious"])
            n = used.get(c["mood"], 0)
            name = opts[(n + int(hashlib.md5(script["id"].encode()).hexdigest(), 16)) % len(opts)]
            used[c["mood"]] = n + 1
        segs.append((t0, t1, name))
    parts = []
    for k, (t0, t1, name) in enumerate(segs):
        seg = assets / f"music_seg{k}.wav"
        dur = (t1 - t0) + (XFADE if k + 1 < len(segs) else 0)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(lib / name), "-t", f"{dur:.2f}",
                        "-af", "loudnorm=I=-27:TP=-3:LRA=11", "-ar", "44100", "-ac", "2", str(seg)], check=True)
        parts.append(seg)
    raw, out = assets / "music_raw.wav", assets / "music.wav"
    if len(parts) == 1:
        chain = f"[0:a]afade=t=in:d=0.6,afade=t=out:st={max(0, total - 3):.2f}:d=3[m]"
    else:
        chain, last = "", "[0:a]"
        for k in range(1, len(parts)):
            lab = f"[x{k}]"
            chain += f"{last}[{k}:a]acrossfade=d={XFADE}:c1=tri:c2=tri{lab};"
            last = lab
        chain += f"{last}afade=t=in:d=0.6,afade=t=out:st={max(0, total - 3):.2f}:d=3[m]"
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for p_ in parts:
        cmd += ["-i", str(p_)]
    cmd += ["-filter_complex", chain, "-map", "[m]", "-t", f"{total:.2f}", str(raw)]
    subprocess.run(cmd, check=True)
    for p_ in parts:
        p_.unlink()
    # duck the bed under the narration (sidechain), so it swells in the gaps
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-i", str(assets / "voice.wav"), "-filter_complex",
                    "[1:a]aresample=44100,aformat=channel_layouts=stereo,volume=3,apad[sc];"
                    "[0:a][sc]sidechaincompress=threshold=0.02:ratio=5:attack=30:release=500:makeup=1[m]",
                    "-map", "[m]", "-t", f"{total:.2f}", str(out)], check=True)
    raw.unlink()
    return " > ".join(f"{n} ({t0:.0f}s)" for t0, _, n in segs)


def sfx_clip(name, t, total, voice_lufs, under=15.0):
    info = CATALOG[name]
    gain = min(1.0, 10 ** ((voice_lufs - under - info.get("lufs", -22)) / 20))
    dur = min(info["duration_s"], total - t - .05)
    return name, t, dur, round(gain, 3)


def main(script, channel, build, tl):
    portrait = script.get("format") == "short"
    W, H = (1080, 1920) if portrait else (1920, 1080)
    theme = dict(channel["theme"], outfit=channel.get("id", "money"))
    comp = build / "compositions"
    comp.mkdir(parents=True, exist_ok=True)
    assets = build / "assets"
    (assets / "sfx").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "node_modules" / "gsap" / "dist" / "gsap.min.js", assets / "gsap.min.js")
    shutil.copy(ROOT / "assets" / "cinema.js", assets / "cinema.js")
    (assets / "fonts").mkdir(exist_ok=True)
    for f in ("pl-display.woff2", "pl-mono.woff2"):
        shutil.copy(ROOT / "assets" / "fonts" / f, assets / "fonts" / f)
    total = round(tl["total"] + .6, 3)
    voice_lufs = lufs(assets / "voice.wav")

    scenes = list(zip(script["scenes"], tl["scenes"]))
    worlds = [sp.get("world", "stage") for sp, _ in scenes]
    trans = []
    for i, (sp, _) in enumerate(scenes):
        if i == 0:
            trans.append("cut")  # frame 0 is the hook: never open on black
        elif sp.get("transition"):
            trans.append(sp["transition"])
        elif sp["type"] == "chapter":
            trans.append("leak")
        elif worlds[i] != worlds[i - 1]:
            trans.append("whip")
        else:
            trans.append("dip" if i % 3 == 0 else "cut")
    if script.get("bake", True):
        jobs = set()
        for sp, _ in scenes:
            fo = sp.get("focus") or [{"f": 3.0 if sp["type"] == "chapter" else 1.0}]
            if len(fo) == 1:
                jobs.add((sp.get("world", "stage"), round(fo[0]["f"], 2)))
        bake_backgrounds(build, jobs, W, H, 1300 if portrait else 790)
    hosts, sfx, leaks = [], [], []
    whooshes = ["whoosh-short", "whoosh-medium-1s"]
    for i, (sp, tsc) in enumerate(scenes):
        if i == len(scenes) - 1:
            tsc = dict(tsc, duration=round(total - tsc["start"], 3))
        S = C.Scene(tsc["id"], sp, tsc, W, H, theme)
        S.first = i == 0
        S.idx = i
        S.F = 1300 if portrait else 790
        S.hosted = sp["type"] not in ("chapter",) and sp.get("host") is not False
        S.clicks = []
        tin = trans[i]
        tout = trans[i + 1] if i + 1 < len(trans) else None
        tout = tout if tout in ("whip", "dip") else None
        (comp / f"{S.sid}.html").write_text(scene_file_cine(S, i, tin, tout))
        hosts.append(f'<div id="{S.sid}" data-composition-id="{S.sid}" data-composition-src="compositions/{S.sid}.html" '
                     f'data-start="{tsc["start"]}" data-duration="{S.dur}" data-track-index="1" data-track-kind="graphics" '
                     f'data-width="{W}" data-height="{H}" style="z-index:1"></div>')
        st = tsc["start"]
        if tin == "whip":
            sfx.append(sfx_clip(whooshes[i % 2], max(0, st - .2), total, voice_lufs, 16))
        if tin == "leak":
            leaks.append(st)
            sfx.append(sfx_clip("swell-soft-3s", max(0, st - 1.4), total, voice_lufs, 14))
        for p in S.pops[:2]:
            sfx.append(sfx_clip("coin-drop" if sp["type"] in ("cards", "pricetag") else "pop-1", st + p, total, voice_lufs, 15))
        for p in S.impacts[:1]:
            sfx.append(sfx_clip("stinger-serious-low", st + p - 1.2, total, voice_lufs, 18))
        for p in S.clicks:
            sfx.append(sfx_clip("click-soft", st + p, total, voice_lufs, 12))

    (comp / "fx.html").write_text(fx_files(W, H, total, leaks, portrait))
    hosts.append(f'<div id="fx" data-composition-id="fx" data-composition-src="compositions/fx.html" data-start="0" '
                 f'data-duration="{total}" data-track-index="6" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:40"></div>')
    if portrait:
        groups = C.caption_groups(tl, 3, 18)
        cap = C.captions_file(groups, W, H, total, channel["theme"]).replace("bottom:650px", "bottom:840px")
        (comp / "captions.html").write_text(cap)
        hosts.append(f'<div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" '
                     f'data-start="0" data-duration="{total}" data-track-index="2" data-track-kind="captions" '
                     f'data-width="{W}" data-height="{H}" style="z-index:50"></div>')
    (build / "captions.srt").write_text(C.srt(C.caption_groups(tl, 8, 46)))

    audio = [f'<audio id="vo" class="clip" data-start="0" data-duration="{tl["total"]}" data-track-index="3" data-volume="1" src="assets/voice.wav"></audio>']
    music = build_music(script, assets, total, tl)
    if music:
        audio.append(f'<audio id="bed" class="clip" data-start="0" data-duration="{total}" data-track-index="4" data-volume="1" src="assets/music.wav"></audio>')
    last_end = {}
    for k, (name, st, dur, gain) in enumerate(sorted(sfx, key=lambda x: x[1])):
        trk = 5 if name.startswith(("whoosh", "swell")) else 7 if name.startswith("stinger") else 8
        if st < last_end.get(trk, -1) or dur < .1:
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
    <script src="assets/cinema.js"></script>
    <style>
      @font-face {{ font-family:'PL Display'; src:url('assets/fonts/pl-display.woff2') format('woff2'); font-weight:100 900; }}
      @font-face {{ font-family:'PL Mono'; src:url('assets/fonts/pl-mono.woff2') format('woff2'); font-weight:100 900; }}
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      html, body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:#000; }}
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
    print(f"cinematic: {len(scenes)} scenes, {len(audio)} audio clips, {total:.1f}s, music={music}, voice {voice_lufs:.1f} LUFS, transitions={trans}")
