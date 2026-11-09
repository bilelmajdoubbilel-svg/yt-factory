"""Hidden Systems look: script + timeline -> HyperFrames project. Selected by "look": "hidden" in
channels/hidden.json (make_video.sh and thumbnail.py dispatch here), so Price Logic's compose.py/cine.py path is
untouched. Usage (after voice.py): python pipeline/look_hidden.py <script.json> <build_dir> <channel.json>

What makes it Hidden Systems and not Price Logic or Map Minutes:
- host Drip (hs_art.drip_rig, the canonical drip_host drawing) driven by assets/hidden/drip.js: idle breath and
  blinks, takes where the hard hat pops and lands last, tendril arms that grow only to point or flip a switch,
  lip-sync from the voice track;
- flat cutaway worlds with ink outlines in concrete / pipe green / safety orange / water, no bokeh, no warm grade;
- "follow the drop": one traveller (drop, spark, parcel, call) moves along the system's real path and the camera
  rides with it, on global time, so the move runs unbroken across scene cuts;
- data beats stencil-sprayed on board-formed concrete, sources on riveted plates, gauges for rates;
- transitions with a cause: pipe iris (fly into a pipe), match on motion, bulb flash, whip;
- Barlow Condensed 800 + JetBrains Mono 700, captions in caps with the live word in safety orange.

Scene types: host, follow, data, chapter, endcard. Reused read-only from the shared code: compose.Scene,
compose.caption_groups/srt/esc, cine.build_music/lufs/CATALOG.
"""
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np

import compose as C
import cine
import hs_art as A
from brand_art import pipe_ring

ROOT = Path(__file__).resolve().parent.parent
HSD = ROOT / "assets" / "hidden"
SFX = ROOT / "assets" / "sfx-cc0"
PAL = A.C
FPS_LIPS = 15

# music beds for this channel (CC0 library): calmer, more mechanical than Price Logic's playful Shorts
HS_MOODS = {
    "short": ["music-lofi-chill-loop.mp3", "music-calm-loop.mp3"],
    "open": ["music-tension-soft.mp3"],
    "body": ["music-contemplation.mp3", "music-lofi-lobby.mp3", "music-ambient-piano.mp3"],
    "payoff": ["music-inspiring-orchestral.mp3"],
}


# ------------------------------------------------------------------ helpers

def fonts_css(prefix="assets/fonts/"):
    return (f"@font-face {{ font-family:'HS Display'; src:url('{prefix}hs-display.woff2') format('woff2'); font-weight:100 900; }}"
            f"@font-face {{ font-family:'HS Mono'; src:url('{prefix}hs-mono.woff2') format('woff2'); font-weight:100 900; }}")


def svg_layer(inner, x0, y0, w, h, extra=""):
    return (f'<svg style="position:absolute;left:{x0}px;top:{y0}px" width="{w}" height="{h}" viewBox="{x0} {y0} {w} {h}" '
            f'overflow="visible" data-layout-ignore>{A.SVG_DEFS}{inner}{extra}</svg>')


def lipsync(wav, t0, dur, words):
    """Mouth keys [[t, shape]] (scene-local) from the voice's loudness and brightness, 15 per second.
    Closed between words, then e/a/wide by level, o on dark (low zero-crossing) loud frames."""
    import soundfile as sf
    x, sr = sf.read(str(wav), dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    hop = sr // FPS_LIPS
    a, b = int(t0 * sr), int((t0 + dur) * sr)
    seg = x[a:b]
    if len(seg) < hop:
        return []
    ref = np.percentile(np.abs(x[x != 0]) if np.any(x) else [1], 97) or 1.0
    frames = []
    spoken = [(w["start"], w["end"]) for w in words]
    for i in range(0, len(seg) - hop, hop):
        fr = seg[i:i + hop]
        t = i / sr
        lvl = float(np.sqrt(np.mean(fr ** 2))) / (ref * .5)
        zcr = float(np.mean(np.abs(np.diff(np.sign(fr))) > 0))
        talking = any(s - .05 <= t <= e + .05 for s, e in spoken)
        if not talking or lvl < .12:
            shape = ""
        elif lvl > .62:
            shape = "o" if zcr < .045 else "wide"
        elif lvl > .3:
            shape = "o" if zcr < .03 else "a"
        else:
            shape = "e"
        frames.append([round(t, 3), shape])
    # runs; a one-frame run joins the run before it (no flicker)
    runs = []
    for t, sh in frames:
        if runs and runs[-1][1] == sh:
            runs[-1][2] += 1
        else:
            runs.append([t, sh, 1])
    out = []
    for r in runs:
        if out and r[2] == 1:
            out[-1][2] += 1
            continue
        if out and out[-1][1] == r[1]:
            out[-1][2] += r[2]
            continue
        out.append(r)
    return [[r[0], r[1]] for r in out]


def cue(S, needle, fallback):
    return S.cue(needle, fallback) if needle else fallback


def ring_svg(pid, W, H, mode):
    """Pipe iris overlay (see DRIP.iris)."""
    flange = pipe_ring(0, 0, 100, 26, 10).replace('stroke-width="6"', 'stroke-width="5"')
    if mode == "close":
        return (f'<svg id="{pid}" width="{W}" height="{H}" style="position:absolute;left:0;top:0" data-layout-ignore>'
                f'<circle id="{pid}-dark" cx="0" cy="0" r="1" fill="#14181B" opacity="0"/>'
                f'<g id="{pid}-ring2" opacity="0">{pipe_ring(0, 0, 100, 14, 8)}</g>'
                f'<g id="{pid}-ring" opacity="0">{flange}</g><circle id="{pid}-hole" r="0"/></svg>')
    return (f'<svg id="{pid}" width="{W}" height="{H}" style="position:absolute;left:0;top:0" data-layout-ignore>'
            f'<defs><mask id="{pid}-m"><rect width="{W}" height="{H}" fill="#fff"/><circle id="{pid}-hole" cx="{W / 2}" cy="{H / 2}" r="0.1" fill="#000"/></mask></defs>'
            f'<rect id="{pid}-dark" width="{W}" height="{H}" fill="#14181B" mask="url(#{pid}-m)"/>'
            f'<g id="{pid}-ring2">{pipe_ring(0, 0, 100, 14, 8)}</g><g id="{pid}-ring">{flange}</g></svg>')


def porthole(sid, cx, cy, r, scale):
    """Drip watching from a pipe porthole (the avatar's flange ring): a fixed overlay over the cutaway."""
    did = f"{sid}-pd"
    return (f'<div style="position:absolute;left:{cx - r - 40}px;top:{cy - r - 40}px;width:{2 * r + 80}px;height:{2 * r + 80}px" data-layout-ignore>'
            f'<svg width="{2 * r + 80}" height="{2 * r + 80}" viewBox="{-r - 40} {-r - 40} {2 * r + 80} {2 * r + 80}" overflow="visible">'
            f'<defs><clipPath id="{sid}-pclip"><circle r="{r}"/></clipPath></defs>'
            f'<circle r="{r}" fill="{PAL["concrete"]}"/>'
            + "".join(f'<circle r="{rr}" fill="none" stroke="{PAL["line"]}" stroke-width="3" opacity=".6"/>' for rr in (r * .45, r * .7))
            + f'<g clip-path="url(#{sid}-pclip)"><g transform="translate(0 {r * .38:.1f}) scale({scale})">{A.drip_rig(did)}</g></g>'
            + pipe_ring(0, 0, r + 12, 34, 10) + '</svg></div>'), did


# ------------------------------------------------------------------ sets (host scenes)

def room_set(S, lit_at=None, start_lit=False, off_at=None):
    """Drip's room: concrete wall, an end-on conduit stub (the pipe we fly into), a pendant bulb and a switch."""
    W, H = S.W, S.H
    p = S.portrait
    fl = 1285 if p else 860                      # floor line
    stub = (230, 760) if p else (380, 330)       # conduit opening (end-on)
    bulb = (720, 560) if p else (1180, 300)
    sw = (900, 1110) if p else (1430, 690)
    sid = S.sid
    parts = [f'<img src="assets/bg/concrete-{W}x{H}.png" alt="" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px" data-layout-ignore>']
    g = []
    g.append(f'<rect x="0" y="{fl}" width="{W}" height="{H - fl}" fill="#24292D"/>'
             f'<rect x="0" y="{fl - 8}" width="{W}" height="16" fill="{PAL["line"]}" stroke="{A.INK}" stroke-width="4"/>')
    # conduit run: from the stub along the wall to the switch box
    run = f"M{stub[0]} {stub[1]} L{stub[0]} 170 L{sw[0]} 170 L{sw[0]} {sw[1] - 50}" if p else \
          f"M{stub[0]} {stub[1]} L{stub[0]} 120 L{sw[0]} 120 L{sw[0]} {sw[1] - 50}"
    g.append(f'<path d="{run}" stroke="{A.INK}" stroke-width="40" fill="none" stroke-linejoin="round"/>'
             f'<path d="{run}" stroke="{PAL["pipe"]}" stroke-width="30" fill="none" stroke-linejoin="round"/>'
             f'<path d="{run}" stroke="#fff" stroke-opacity=".12" stroke-width="8" fill="none" stroke-linejoin="round" transform="translate(-6 0)"/>')
    # end-on stub: dark bore inside a flange ring
    g.append(f'<circle cx="{stub[0]}" cy="{stub[1]}" r="78" fill="#14181B"/>'
             + pipe_ring(stub[0], stub[1], 92, 30, 8)
             + "".join(f'<circle cx="{stub[0]}" cy="{stub[1]}" r="{r}" fill="none" stroke="{PAL["line"]}" stroke-width="3" opacity=".7"/>' for r in (28, 52)))
    # pendant bulb
    g.append(f'<line x1="{bulb[0]}" y1="0" x2="{bulb[0]}" y2="{bulb[1] - 60}" stroke="{A.INK}" stroke-width="6"/>'
             f'<rect x="{bulb[0] - 22}" y="{bulb[1] - 72}" width="44" height="40" rx="6" fill="{PAL["steel2"]}" stroke="{A.INK}" stroke-width="4"/>')
    glow = (f'<div id="{sid}-glow" style="position:absolute;left:{bulb[0] - 420}px;top:{bulb[1] - 420}px;width:840px;height:840px;border-radius:50%;'
            f'background:radial-gradient(circle, rgba(255,217,168,.55) 0%, rgba(255,217,168,.18) 32%, rgba(255,217,168,0) 70%);opacity:{1 if start_lit else 0}" data-layout-ignore></div>')
    g2 = (f'<circle cx="{bulb[0]}" cy="{bulb[1]}" r="44" fill="#5B6168" stroke="{A.INK}" stroke-width="5"/>'
          f'<circle id="{sid}-bulbon" cx="{bulb[0]}" cy="{bulb[1]}" r="44" fill="{PAL["glow"]}" stroke="{A.INK}" stroke-width="5" opacity="{1 if start_lit else 0}"/>'
          f'<path d="M{bulb[0] - 16} {bulb[1] + 6} L{bulb[0] - 8} {bulb[1] - 8} L{bulb[0]} {bulb[1] + 6} L{bulb[0] + 8} {bulb[1] - 8} L{bulb[0] + 16} {bulb[1] + 6}" '
          f'stroke="{PAL["hat2"]}" stroke-width="4" fill="none" stroke-linejoin="round"/>')
    # switch plate (the toggle flips by rotation)
    g3 = (f'<rect x="{sw[0] - 46}" y="{sw[1] - 66}" width="92" height="132" rx="12" fill="{PAL["cream"]}" stroke="{A.INK}" stroke-width="5"/>'
          f'<g id="{sid}-tog-up" opacity="{1 if start_lit else 0}"><rect x="{sw[0] - 13}" y="{sw[1] - 40}" width="26" height="42" rx="6" fill="{PAL["steel2"]}" stroke="{A.INK}" stroke-width="4"/></g>'
          f'<g id="{sid}-tog-dn" opacity="{0 if start_lit else 1}"><rect x="{sw[0] - 13}" y="{sw[1] - 2}" width="26" height="42" rx="6" fill="{PAL["steel2"]}" stroke="{A.INK}" stroke-width="4"/></g>')
    parts.append(svg_layer("".join(g), 0, 0, W, H))
    parts.append(glow)
    parts.append(svg_layer(g2 + g3, 0, 0, W, H))
    dim = f'<div id="{sid}-dim" style="position:absolute;inset:0;background:#0B0E10;opacity:0" data-layout-ignore></div>'   # set by the timeline at 0
    return "".join(parts), dim, {"stub": stub, "bulb": bulb, "switch": sw, "floor": fl}


# ------------------------------------------------------------------ scene builders

def drip_events(S, acts, lips):
    """acts from the script ({t|cue, dt, take|expr|look|point|unpoint|hop|lean}) -> DRIP.rig cfg."""
    cfg = {"seed": int(S.sid[1:]) * 7 + 3, "expr": "happy", "takes": [], "exprs": [], "look": [], "lean": [], "arms": {"R": [], "L": []},
           "hops": [], "mouth": lips}
    for a in acts:
        t = (S.cue(a["cue"], a.get("t", .3)) if a.get("cue") else a.get("t", .3)) + a.get("dt", 0)
        t = round(min(S.dur - .2, t), 3) if t < 0 else round(max(0, min(S.dur - .2, t)), 3)   # t < 0: already done at frame 0
        if a.get("take"):
            cfg["takes"].append([t, a["take"], a.get("amp", 1)])
        if a.get("expr"):
            cfg["exprs"].append([t, a["expr"]])
        if "look" in a:
            lk = a["look"]
            cfg["look"].append([t, lk[0], lk[1]] if isinstance(lk, list) else [t, lk, 0])
        if a.get("point"):
            cfg["arms"][a["point"]].append([t, a.get("reach", 1), a.get("angle", -20)])
        if a.get("unpoint"):
            cfg["arms"][a["unpoint"]].append([t, 0, None])
        if a.get("hop"):
            cfg["hops"].append(t)
        if "lean" in a:
            cfg["lean"].append([t, a["lean"]])
    if not cfg["takes"] and not cfg["exprs"]:
        cfg["expr"] = "happy"
    return cfg


def scene_host(S, ctx):
    """Drip close-up in his room: stencil hook on the wall, light switch, the pipe stub we fly into."""
    sid, d, W, H = S.sid, S.d, S.W, S.H
    p = S.portrait
    first = S.first
    start_lit = d.get("start_lit", False)
    world, dim, pts = room_set(S, start_lit=start_lit)
    js, css = [], ""
    # Drip
    dx, dy, sc = (540, 1065, 2.1) if p else (820, 690, 1.45)
    dripbox = A.drip_box(f"{sid}-d", dx, dy, sc)
    origin = f'{pts["stub"][0]}px {pts["stub"][1]}px' if S.spec.get("transition_out") == "iris" else f"{W // 2}px {H // 2}px"
    acts = list(S.spec.get("drip", {}).get("acts", []))
    lips = lipsync(ctx["voice"], S.start, S.dur, S.words) if d.get("talk", True) else []
    cfg = drip_events(S, acts, lips)
    js.append(f'DRIP.rig(tl, "{sid}-d", {S.dur:.3f}, {json.dumps(cfg)})')
    # stencil hook on the wall (frame 0 when first)
    sten = d.get("stencil")
    over = ""
    if sten:
        sx, sy = (W // 2, 345) if p else (W // 2, 170)
        size = 132 if p else 120
        over += (f'<div id="{sid}-sten" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px" data-layout-ignore>'
                 + svg_layer(A.stencil(sx, sy, C.esc(sten), size, PAL["hat"], ls=6), 0, 0, W, H) + '</div>')
        if first:
            js.append(f'tl.set("#{sid}-sten", {{opacity:1}}, 0)')
        else:
            at = cue(S, d.get("stencil_cue"), .3)
            js.append(f'tl.fromTo("#{sid}-sten", {{opacity:0, clipPath:"inset(0 100% 0 0)"}}, {{opacity:1, clipPath:"inset(0 0% 0 0)", duration:.45, ease:"power2.out"}}, {at})')
            S.sfx.append(("stamp-thud", at + .1, 15))
        if d.get("stencil_out"):
            t_out = cue(S, d["stencil_out"], S.dur * .6)
            js.append(f'tl.to("#{sid}-sten", {{opacity:0, duration:.25}}, {t_out})')
    # the switch: flips at cue words -> light on/off
    for fl in d.get("flips", []):
        t = cue(S, fl.get("cue"), fl.get("t", .3)) + fl.get("dt", 0)
        on = fl.get("on", True)
        js.append(f'tl.set("#{sid}-tog-up", {{opacity:{1 if on else 0}}}, {t + .05:.3f})')
        js.append(f'tl.set("#{sid}-tog-dn", {{opacity:{0 if on else 1}}}, {t + .05:.3f})')
        if on:
            js += [f'tl.to("#{sid}-dim", {{opacity:.18, duration:.05}}, {t + .08:.3f})',
                   f'tl.to("#{sid}-dim", {{opacity:.4, duration:.05}}, {t + .14:.3f})',
                   f'tl.to("#{sid}-dim", {{opacity:0, duration:.12}}, {t + .2:.3f})',
                   f'tl.to(["#{sid}-glow", "#{sid}-bulbon"], {{opacity:1, duration:.06}}, {t + .08:.3f})']
        else:
            js += [f'tl.to("#{sid}-dim", {{opacity:.5, duration:.1}}, {t + .08:.3f})',
                   f'tl.to(["#{sid}-glow", "#{sid}-bulbon"], {{opacity:0, duration:.08}}, {t + .08:.3f})']
        S.sfx.append(("switch-1", t, 10))
    js.append(f'tl.fromTo("#{sid}-dim", {{opacity:{0 if start_lit else .5}}}, {{opacity:{0 if start_lit else .5}, duration:.02}}, 0)')
    # leave through the pipe stub
    tail = ""
    if S.spec.get("transition_out") == "iris":
        pid = f"{sid}-iris"
        tail = ring_svg(pid, W, H, "close")
        d0 = .62
        js.append(f'DRIP.iris(tl, "{pid}", {S.dur - d0:.3f}, {d0}, "close", {W}, {H}, {pts["stub"][0]}, {pts["stub"][1]}, 92)')
        js.append(f'tl.to("#{sid}-cam", {{scale:1.18, duration:{d0}, ease:"power2.in"}}, {S.dur - d0:.3f})')
        S.sfx.append(("whoosh-long-2s", S.dur - d0 - .2, 14))
    if S.spec.get("transition_out") == "whip":
        js.append(f'tl.to("#{sid}-cam", {{x:{-int(W * .3)}, filter:"blur(16px)", duration:.22, ease:"power3.in"}}, {max(.2, S.dur - .22):.3f})')
    if S.spec.get("transition_in") == "whip":
        js.append(f'tl.fromTo("#{sid}-cam", {{x:{int(W * .3)}, filter:"blur(16px)"}}, {{x:0, filter:"blur(0px)", duration:.3, ease:"power3.out"}}, 0)')
    # a slow push keeps the close-up alive
    push = d.get("push", .04)
    js.append(f'tl.fromTo("#{sid}-push", {{scale:1}}, {{scale:{1 + push}, duration:{S.dur:.3f}, ease:"sine.inOut"}}, 0)')
    # camera and push scale about the pipe stub when we leave through it, so the iris starts exactly on it
    markup = (f'<div id="{sid}-cam" class="full" style="transform-origin:{origin}"><div id="{sid}-push" class="full" style="transform-origin:{origin}">'
              f'{world}{dripbox}{dim}{over}</div></div>{tail}')
    return markup, css, js


def follow_keys(S_list, strip, ctx):
    """Global distance keys for every follow scene: each waypoint {mark, cue, dt} pins where the traveller is
    when that word is spoken. Linear in between; ease in at the start of the run, ease out at its end."""
    keys = []
    for S in S_list:
        for wp in S.d.get("waypoints", []):
            t0 = S.dur if wp.get("t") == "end" else wp.get("t", 0)
            t = S.start + (S.cue(wp["cue"], t0) if wp.get("cue") else t0) + wp.get("dt", 0)
            d = strip["marks"][wp["mark"]] + wp.get("off", 0)
            keys.append([round(t, 3), round(d, 1), wp.get("ease", "linear")])
    keys.sort(key=lambda k: k[0])
    if keys:
        keys[1:2] = [[k[0], k[1], k[2] if k[2] != "linear" else "in"] for k in keys[1:2]]
        keys[-1][2] = keys[-1][2] if keys[-1][2] != "linear" else "out"
    return keys


def scene_follow(S, ctx):
    sid, d, W, H = S.sid, S.d, S.W, S.H
    p = S.portrait
    strip = ctx["strip"]
    keys = ctx["fkeys"]
    js, css = [], ""
    path_d = "M" + " L".join(f"{x},{y}" for x, y in strip["path"])
    # spark (traveller) + trail; the lit conductor segment behind it
    spark = (f'<div id="{sid}-spark" style="position:absolute;left:0;top:0;width:0;height:0" data-layout-ignore>'
             f'<div style="position:absolute;left:-90px;top:-90px;width:180px;height:180px;border-radius:50%;'
             f'background:radial-gradient(circle, rgba(255,246,232,1) 0%, rgba(255,217,168,.95) 14%, rgba(242,107,29,.55) 30%, rgba(242,107,29,0) 68%)"></div>'
             f'<svg style="position:absolute;left:-60px;top:-60px" width="120" height="120" viewBox="-60 -60 120 120" overflow="visible">'
             + "".join(f'<path d="M0 0 L{18 * math.cos(a):.1f} {18 * math.sin(a):.1f} L{30 * math.cos(a + .25):.1f} {30 * math.sin(a + .25):.1f} L{46 * math.cos(a):.1f} {46 * math.sin(a):.1f}" '
                       f'stroke="{PAL["cream"]}" stroke-width="4" fill="none" stroke-linecap="round" class="zap"/>' for a in (0.4, 2.3, 4.2))
             + '</svg></div>')
    trail = "".join(f'<div id="{sid}-tr{k}" style="position:absolute;left:-{12 - k}px;top:-{12 - k}px;width:{24 - 2 * k}px;height:{24 - 2 * k}px;'
                    f'border-radius:50%;background:{PAL["glow"]};opacity:0" data-layout-ignore></div>' for k in range(5))
    lit = (f'<path id="{sid}-lit" d="{path_d}" fill="none" stroke="{PAL["hat"]}" stroke-width="14" stroke-linecap="round" '
           f'stroke-linejoin="round" opacity=".85" stroke-dasharray="0 99999"/>')
    bulb = strip["bulb"]
    bglow = (f'<div id="{sid}-bglow" style="position:absolute;left:{bulb[0] - 260}px;top:{bulb[1] - 260}px;width:520px;height:520px;border-radius:50%;'
             f'background:radial-gradient(circle, rgba(255,246,232,.95) 0%, rgba(255,217,168,.6) 18%, rgba(255,217,168,0) 70%);opacity:0" data-layout-ignore></div>')
    sign = strip["sign"]
    mid = (svg_layer(strip["near"] + strip["mid"] + sign + lit, -800, -200, strip["width"] + 1600, 2400) + bglow + trail + spark)
    far = svg_layer(strip["far"], -800, -400, int(strip["width"] * .45) + 3400, 2800)
    fore = svg_layer(strip["fore"], -800, 1300, int(strip["width"] * 1.6) + 2000, 1100)
    world = (f'<div id="{sid}-Lfar" class="L">{far}</div><div id="{sid}-Lmid" class="L">{mid}</div>'
             f'<div id="{sid}-Lfore" class="L">{fore}</div>')
    anchor = [W / 2, 760] if p else [W / 2, H * .5]
    zoom = [[S.start + (S.cue(z[0], 0) if isinstance(z[0], str) else z[0]), z[1]] for z in d.get("zoom", [[0, d.get("z", 1.0)]])]
    lead = [[S.start + (S.cue(l[0], 0) if isinstance(l[0], str) else l[0]), l[1], l[2]] for l in d.get("lead", [[0, 0, 0]])]
    cfg = {"W": W, "H": H, "g0": S.start, "path": strip["path"], "keys": keys, "lag": .22, "mix": .5, "anchor": anchor, "c0": [0, 1000],
           "zoom": ctx["zoom_hist"] + zoom, "lead": ctx["lead_hist"] + lead,
           "layers": [{"sel": f"#{sid}-Lfar", "p": .35}, {"sel": f"#{sid}-Lmid", "p": 1}, {"sel": f"#{sid}-Lfore", "p": 1.6}],
           "spark": f"#{sid}-spark", "trail": [f"#{sid}-tr{k}" for k in range(5)], "lit": f"#{sid}-lit", "litLen": 900,
           "spin": [[f"#{sid}-Lmid .hs-spin", 3.0]], "flow": [[f"#{sid}-Lmid .hs-flow", 90], [f"#{sid}-Lmid .hs-flow2", 45]]}
    ctx["zoom_hist"] += zoom
    ctx["lead_hist"] += lead
    js.append(f'DRIP.follow(tl, "{sid}", {json.dumps(cfg)}, {S.dur:.3f})')
    # the spark is born at its first waypoint (zap) / hidden before the run starts
    t_first = keys[0][0] - S.start if keys else 0
    if 0 <= t_first < S.dur:
        js.append(f'tl.fromTo("#{sid}-spark", {{opacity:0}}, {{opacity:1, duration:.12}}, {max(0, t_first - .3):.3f})')
        S.sfx.append(("glitch-soft-1", max(0, t_first - .3), 12))
    elif t_first >= S.dur:
        js.append(f'tl.set("#{sid}-spark", {{opacity:0}}, 0)')
    # arrival at the bulb: it lights and blooms (cause of the flash transition)
    t_bulb = None
    for k in keys:
        if abs(k[1] - strip["marks"]["bulb"]) < 1:
            t_bulb = k[0] - S.start
    if t_bulb is not None and 0 <= t_bulb <= S.dur + .01:
        js.append(f'tl.to("#{sid}-bglow", {{opacity:1, duration:.15}}, {max(0, t_bulb - .1):.3f})')
        gone = json.dumps([f"#{sid}-spark"] + [f"#{sid}-tr{k}" for k in range(5)])
        js.append(f'tl.to("#{sid}-spark", {{opacity:0, duration:.12}}, {t_bulb + .05:.3f})')
        S.sfx.append(("pop-1", max(0, t_bulb - .05), 14))
    # zap sounds where the traveller passes a transformer
    for m in d.get("zaps", []):
        for i in range(1, len(keys)):
            if keys[i - 1][1] <= strip["marks"][m] <= keys[i][1] and keys[i][1] > keys[i - 1][1]:
                f = (strip["marks"][m] - keys[i - 1][1]) / (keys[i][1] - keys[i - 1][1])
                tz = keys[i - 1][0] + f * (keys[i][0] - keys[i - 1][0]) - S.start
                if 0 <= tz < S.dur:
                    S.sfx.append(("glitch-soft-2", tz, 14))
    # Drip in the porthole, reacting + lip-sync
    ph = ""
    if d.get("porthole", True):
        r = 150 if p else 130
        pc = (60 + r + 30, 250 + r) if p else (60 + r + 30, 60 + r + 30)
        ph, did = porthole(sid, pc[0], pc[1], r, .95)
        lips = lipsync(ctx["voice"], S.start, S.dur, S.words)
        cfg2 = drip_events(S, S.spec.get("drip", {}).get("acts", []), lips)
        js.append(f'DRIP.rig(tl, "{did}", {S.dur:.3f}, {json.dumps(cfg2)})')
    tin = S.spec.get("transition_in")
    tail = ""
    if tin == "iris":
        pid = f"{sid}-iris"
        tail += ring_svg(pid, W, H, "open")
        js.append(f'DRIP.iris(tl, "{pid}", 0, .55, "open", {W}, {H}, {W / 2}, {H / 2}, 92)')
    if S.spec.get("transition_out") == "flash":
        tail += f'<div id="{sid}-flash" style="position:absolute;inset:0;background:{PAL["cream"]};opacity:0" data-layout-ignore></div>'
        js.append(f'tl.fromTo("#{sid}-flash", {{opacity:0}}, {{opacity:1, duration:.22, ease:"power2.in"}}, {S.dur - .22:.3f})')
        S.sfx.append(("swell-soft-3s", max(0, S.dur - 1.6), 16))
    markup = f'<div id="{sid}-cam" class="full">{world}</div>{ph}{tail}'
    return markup, css, js


def gauge_svg(sid, cx, cy, r, vmin, vmax, labels, unit):
    a0, a1 = -120, 120
    ticks = []
    for k in range(41):
        f = k / 40
        a = math.radians(a0 + (a1 - a0) * f - 90)
        big = k % 10 == 0
        r1 = r * (.78 if big else .86)
        ticks.append(f'<line x1="{cx + r1 * math.cos(a):.1f}" y1="{cy + r1 * math.sin(a):.1f}" x2="{cx + r * .93 * math.cos(a):.1f}" '
                     f'y2="{cy + r * .93 * math.sin(a):.1f}" stroke="{A.INK}" stroke-width="{7 if big else 3}"/>')
    labs = []
    for v, txt in labels:
        f = (v - vmin) / (vmax - vmin)
        a = math.radians(a0 + (a1 - a0) * f - 90)
        labs.append(f'<text x="{cx + r * .6 * math.cos(a):.1f}" y="{cy + r * .6 * math.sin(a) + 14:.1f}" font-family="HS Mono" font-weight="700" '
                    f'font-size="{int(r * .13)}" fill="{A.INK}" text-anchor="middle">{txt}</text>')
    # green band around the setpoint
    def arc(f0, f1, rr):
        p0 = math.radians(a0 + (a1 - a0) * f0 - 90)
        p1 = math.radians(a0 + (a1 - a0) * f1 - 90)
        return f"M{cx + rr * math.cos(p0):.1f} {cy + rr * math.sin(p0):.1f} A{rr} {rr} 0 0 1 {cx + rr * math.cos(p1):.1f} {cy + rr * math.sin(p1):.1f}"
    out = (f'<circle cx="{cx}" cy="{cy}" r="{r + 36}" fill="{PAL["steel2"]}" stroke="{A.INK}" stroke-width="8"/>'
           + "".join(f'<circle cx="{cx + (r + 18) * math.cos(a):.1f}" cy="{cy + (r + 18) * math.sin(a):.1f}" r="9" fill="{PAL["steel"]}" stroke="{A.INK}" stroke-width="3"/>'
                     for a in [k * math.pi / 4 + math.pi / 8 for k in range(8)])
           + f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{PAL["cream"]}" stroke="{A.INK}" stroke-width="6"/>'
           + f'<path d="{arc(.42, .58, r * .9)}" stroke="{PAL["pipe"]}" stroke-width="{r * .1:.0f}" fill="none"/>'
           + f'<path d="{arc(0, .2, r * .9)}" stroke="{PAL["hat"]}" stroke-width="{r * .1:.0f}" fill="none"/>'
           + f'<path d="{arc(.8, 1, r * .9)}" stroke="{PAL["hat"]}" stroke-width="{r * .1:.0f}" fill="none"/>'
           + "".join(ticks) + "".join(labs)
           + f'<text x="{cx}" y="{cy + r * .42:.1f}" font-family="HS Mono" font-weight="700" font-size="{int(r * .12)}" fill="{PAL["steel2"]}" text-anchor="middle">{unit}</text>'
           + f'<g transform="translate({cx} {cy})"><g id="{sid}-needle" transform="rotate(0)">'
           f'<path d="M-9 20 L0 {-r * .86:.1f} L9 20Z" fill="{PAL["hat"]}" stroke="{A.INK}" stroke-width="4" stroke-linejoin="round"/></g>'
           f'<circle r="{r * .09:.1f}" fill="{A.INK}"/><circle r="{r * .04:.1f}" fill="{PAL["steel"]}"/></g>')
    return out, a0, a1


def scene_data(S, ctx):
    """A number on concrete: stencil-sprayed value, a label, the source on a riveted plate, optional gauge."""
    sid, d, W, H = S.sid, S.d, S.W, S.H
    p = S.portrait
    js, css = [], ""
    g = []
    over = []
    top = d.get("top")            # e.g. [["SUPPLY", cue], ["=", cue], ["DEMAND", cue]]
    if top:
        y = 420 if p else 190
        xs = [W * .24, W * .5, W * .76] if len(top) == 3 else [W * (k + 1) / (len(top) + 1) for k in range(len(top))]
        for k, (word, cw) in enumerate(top):
            col = PAL["hat"] if word.strip() in ("=", "≠") else PAL["cream"]
            over.append(f'<g id="{sid}-top{k}" opacity="0">{A.stencil(xs[k], y, C.esc(word), 96 if p else 84, col, ls=4)}</g>')
            at = cue(S, cw, .3 + .4 * k)
            js.append(f'tl.fromTo("#{sid}-top{k}", {{opacity:0}}, {{opacity:1, duration:.18}}, {at})')
            S.sfx.append(("tap", at, 16))
    gauge = d.get("gauge")
    if gauge:
        gx, gy, gr = (W / 2, 735, 245) if p else (W * .38, H * .55, 250)
        gsvg, a0, a1 = gauge_svg(sid, gx, gy, gr, gauge["min"], gauge["max"], [(v, t) for v, t in gauge["labels"]], gauge.get("unit", ""))
        g.append(gsvg)
        keys = [[0, gauge.get("start", gauge["value"])]]
        for k in gauge.get("moves", []):
            keys.append([cue(S, k.get("cue"), k.get("t", .5)), k["value"]])
        js.append(f'DRIP.gauge(tl, "#{sid}-needle", {S.dur:.3f}, {json.dumps({"keys": keys, "min": gauge["min"], "max": gauge["max"], "a0": a0, "a1": a1, "wobble": gauge.get("wobble", 0)})})')
    big = d.get("big")
    if big:
        bx, by = (W / 2, 1180) if p else (W * .72, H * .6)
        at = cue(S, d.get("cue"), .5)
        over.append(f'<g id="{sid}-big">{A.stencil(bx, by, C.esc(big), 168 if p else 190, PAL["hat"], ls=6)}</g>')
        js.append(f'tl.fromTo("#{sid}-big", {{opacity:0, scale:1.3, svgOrigin:"{bx} {by - 60}"}}, {{opacity:1, scale:1, svgOrigin:"{bx} {by - 60}", duration:.35, ease:"power4.out"}}, {at})')
        S.sfx.append(("stamp-thud", at + .05, 13))
        if d.get("label"):
            over.append(f'<g id="{sid}-lab">{A.stencil(bx, by + (70 if p else 80), C.esc(d["label"]), 56, PAL["cream"], spray=False, ls=8)}</g>')
            js.append(f'tl.fromTo("#{sid}-lab", {{opacity:0}}, {{opacity:1, duration:.3}}, {at + .3})')
    src = d.get("source")
    if src:
        tw = min(W - 120, 30 + 16.5 * len(src))
        sx, sy = ((W - tw) / 2, 226) if p else (W - tw - 70, 70)
        over.append(f'<g id="{sid}-src">{A.plate(sx, sy, tw, 64, fill=PAL["concrete2"], bolts=False)}{A.mono(sx + tw / 2, sy + 42, C.esc(src), 27, PAL["steel"], "middle")}</g>')
        js.append(f'tl.fromTo("#{sid}-src", {{opacity:0}}, {{opacity:1, duration:.3}}, {cue(S, d.get("source_cue"), .6)})')
    # Drip at the side, reacting
    dx, dy, sc = (165, 1190, .8) if p else (W * .86, H * .78, .9)
    dripbox = A.drip_box(f"{sid}-d", dx, dy, sc)
    lips = lipsync(ctx["voice"], S.start, S.dur, S.words)
    cfg = drip_events(S, S.spec.get("drip", {}).get("acts", [{"t": .2, "look": [12, -6]}]), lips)
    js.append(f'DRIP.rig(tl, "{sid}-d", {S.dur:.3f}, {json.dumps(cfg)})')
    bg = f'<img src="assets/bg/concrete-{W}x{H}.png" alt="" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px" data-layout-ignore>'
    tin, tout, tail = S.spec.get("transition_in"), S.spec.get("transition_out"), ""
    if tin == "flash":
        tail += f'<div id="{sid}-flash" style="position:absolute;inset:0;background:{PAL["cream"]}" data-layout-ignore></div>'
        js.append(f'tl.fromTo("#{sid}-flash", {{opacity:1}}, {{opacity:0, duration:.4, ease:"power2.out"}}, 0)')
    if tout == "whip":
        js.append(f'tl.to("#{sid}-cam", {{x:{-int(W * .3)}, filter:"blur(16px)", duration:.22, ease:"power3.in"}}, {max(.2, S.dur - .22):.3f})')
        S.sfx.append(("whoosh-short", max(0, S.dur - .25), 15))
    js.append(f'tl.fromTo("#{sid}-push", {{scale:1.0}}, {{scale:1.035, duration:{S.dur:.3f}, ease:"sine.inOut"}}, 0)')
    markup = (f'<div id="{sid}-cam" class="full"><div id="{sid}-push" class="full">{bg}'
              f'{svg_layer("".join(g) + "".join(over), 0, 0, W, H)}{dripbox}</div></div>{tail}')
    return markup, css, js


def scene_chapter(S, ctx):
    sid, d, W, H = S.sid, S.d, S.W, S.H
    bg = f'<img src="assets/bg/concrete-{W}x{H}.png" alt="" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px" data-layout-ignore>'
    y = H * .48
    inner = (A.stencil(W / 2, y - 120, f'PART {C.esc(d.get("num", ""))}', 64, PAL["cream"], spray=False, ls=12)
             + A.stencil(W / 2, y + 40, C.esc(d.get("title", "").upper()), 150 if S.portrait else 170, PAL["hat"], ls=5))
    js = [f'tl.fromTo("#{sid}-ch", {{opacity:0, clipPath:"inset(0 100% 0 0)"}}, {{opacity:1, clipPath:"inset(0 0% 0 0)", duration:.5, ease:"power2.out"}}, .2)']
    S.sfx.append(("stamp-thud", .45, 14))
    return (f'<div id="{sid}-cam" class="full">{bg}<div id="{sid}-ch" class="full">{svg_layer(inner, 0, 0, W, H)}</div></div>', "", js)


def endcard_svg(W=1920, H=1080):
    """Long-video end card: a pipe junction. Centre flange = subscribe circle; two pipes lead to two video hatches
    (YouTube end-screen elements sit on the hatches: 16:9 slots at the positions below)."""
    slots = [(150, 330, 640, 360), (W - 150 - 640, 330, 640, 360)]
    g = [f'<rect x="0" y="{H - 150}" width="{W}" height="150" fill="#24292D"/><rect x="0" y="{H - 158}" width="{W}" height="16" fill="{PAL["line"]}" stroke="{A.INK}" stroke-width="4"/>']
    cx, cy = W / 2, 300
    ty_ = slots[0][1] + slots[0][3] / 2
    run = f"M{slots[0][0] + slots[0][2]} {ty_} L{slots[1][0]} {ty_} M{cx} {cy} L{cx} {ty_}"
    g.append(f'<path d="{run}" stroke="{A.INK}" stroke-width="56" fill="none" stroke-linejoin="round"/>'
             f'<path d="{run}" stroke="{PAL["pipe"]}" stroke-width="44" fill="none" stroke-linejoin="round"/>'
             f'<rect x="{cx - 40}" y="{ty_ - 40}" width="80" height="80" rx="12" fill="{PAL["pipe2"]}" stroke="{A.INK}" stroke-width="5"/>')
    for (x, y, w, h) in slots:
        g.append(f'<rect x="{x - 22}" y="{y - 22}" width="{w + 44}" height="{h + 44}" rx="22" fill="{PAL["pipe2"]}" stroke="{A.INK}" stroke-width="6"/>'
                 f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#14181B"/>')
        for bx, by in ((x - 8, y - 8), (x + w + 8, y - 8), (x - 8, y + h + 8), (x + w + 8, y + h + 8)):
            g.append(f'<circle cx="{bx}" cy="{by}" r="10" fill="{PAL["steel"]}" stroke="{A.INK}" stroke-width="3"/>')
    g.append(f'<circle cx="{cx}" cy="{cy}" r="96" fill="#14181B"/>' + pipe_ring(cx, cy, 112, 34, 10))
    g.append(A.stencil(cx, 150, "NEXT SYSTEM", 92, PAL["hat"], ls=8))
    g.append(A.mono(cx, 640, "PICK A PIPE", 30, PAL["steel"], "middle"))
    return "".join(g), slots, (cx, cy)


def scene_endcard(S, ctx):
    sid, W, H = S.sid, S.W, S.H
    inner, slots, sub = endcard_svg(W, H)
    bg = f'<img src="assets/bg/concrete-{W}x{H}.png" alt="" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px" data-layout-ignore>'
    dripbox = A.drip_box(f"{sid}-d", W / 2, H - 230, 1.2)
    lips = lipsync(ctx["voice"], S.start, S.dur, S.words)
    cfg = drip_events(S, S.spec.get("drip", {}).get("acts", [{"t": .3, "take": "happy"}, {"t": .9, "point": "R", "angle": -35}]), lips)
    js = [f'DRIP.rig(tl, "{sid}-d", {S.dur:.3f}, {json.dumps(cfg)})']
    return f'<div id="{sid}-cam" class="full">{bg}{svg_layer(inner, 0, 0, W, H)}{dripbox}</div>', "", js


BUILDERS = {"host": scene_host, "follow": scene_follow, "data": scene_data, "chapter": scene_chapter, "endcard": scene_endcard}


def scene_file(S, ctx):
    markup, css, js = BUILDERS[S.spec["type"]](S, ctx)
    sid, W, H = S.sid, S.W, S.H
    js.append(f'window.__timelines["{sid}"] = tl;')
    body = "\n    ".join(["const tl = gsap.timeline({ paused: true });"] + [ln if ln.rstrip().endswith((";", "}")) else ln + ";" for ln in js])
    return f'''<template>
  <style>
    #root {{ position:absolute; inset:0; overflow:hidden; background:{PAL["concrete"]}; font-family:'HS Display',sans-serif; }}
    #root .full {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; transform-origin:{W // 2}px {H // 2}px; }}
    #root .L {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; }}
    #root .drip svg {{ overflow:visible; }}{css}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="{W}" data-height="{H}" data-layout-allow-overflow>
    {markup}
  </div>
  <script>
    {body}
  </script>
</template>
'''


# ------------------------------------------------------------------ captions, fx, audio

def captions_file(groups, W, H, total):
    portrait = H > W
    blocks, js = [], []
    for g, grp in enumerate(groups):
        spans = " ".join(f'<span class="cw" id="cap-g{g}-w{i}">{C.esc(w["text"].upper())}</span>' for i, w in enumerate(grp["words"]))
        blocks.append(f'<div class="cg" id="cap-g{g}">{spans}</div>')
        st, en = grp["start"], grp["end"]
        js.append(f'tl.fromTo("#cap-g{g}", {{opacity:0, y:14}}, {{opacity:1, y:0, duration:.09, ease:"power2.out"}}, {st:.3f});')
        for i, w in enumerate(grp["words"]):
            js.append(f'tl.fromTo("#cap-g{g}-w{i}", {{color:"{PAL["cream"]}"}}, {{color:"{PAL["hat"]}", duration:.05}}, {w["start"]:.3f});')
            if i + 1 < len(grp["words"]):
                js.append(f'tl.to("#cap-g{g}-w{i}", {{color:"{PAL["cream"]}", duration:.05}}, {grp["words"][i + 1]["start"]:.3f});')
        js.append(f'tl.to("#cap-g{g}", {{opacity:0, duration:.07, ease:"power2.in"}}, {max(st + .1, en - .07):.3f});')
        js.append(f'tl.set("#cap-g{g}", {{opacity:0, visibility:"hidden"}}, {en:.3f});')
    fs, bottom = (92, 505) if portrait else (62, 70)
    return f'''<template>
  <style>
    #root {{ position:absolute; inset:0; pointer-events:none; }}
    #root .cg {{ position:absolute; left:0; right:0; bottom:{bottom}px; text-align:center; padding:0 {120 if portrait else 220}px;
      font-family:'HS Display',sans-serif; font-weight:800; font-size:{fs}px; line-height:1.0; letter-spacing:.02em; color:{PAL["cream"]}; opacity:0;
      -webkit-text-stroke:{11 if portrait else 8}px {A.INK}; paint-order:stroke fill; }}
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


def fx_file(W, H, total):
    grain = ("url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E"
             "%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E"
             "%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")")
    return f'''<template>
  <style>
    #root {{ position:absolute; inset:0; pointer-events:none; }}
    #fx-vig {{ position:absolute; inset:0; background:radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 62%, rgba(0,0,0,.22) 100%); }}
    #fx-grain {{ position:absolute; inset:-10px; opacity:.045; background-image:{grain}; }}
  </style>
  <div id="root" data-composition-id="fx" data-width="{W}" data-height="{H}" data-layout-ignore>
    <div id="fx-vig"></div><div id="fx-grain"></div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    CIN.grain(tl, "#fx-grain", {total:.3f});
    window.__timelines["fx"] = tl;
  </script>
</template>
'''


def hum_wav(path, dur):
    """Transformer hum (120 Hz and harmonics, slow beat), generated here: no licence questions."""
    expr = "0.5*sin(2*PI*120*t)+0.22*sin(2*PI*240*t+1)+0.12*sin(2*PI*360*t+2)"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"aevalsrc='{expr}':s=44100:d={dur:.2f}",
                    "-af", f"tremolo=f=0.7:d=0.25,volume=0.5,afade=t=in:d=0.6,afade=t=out:st={max(0, dur - .8):.2f}:d=0.8", "-ac", "2", str(path)], check=True)


def score_for(script, tl):
    if script.get("score"):
        return script["score"]
    pick = lambda opts: opts[sum(map(ord, script["id"])) % len(opts)]
    if script.get("format") == "short":
        return [{"scene": 0, "track": script.get("music") or pick(HS_MOODS["short"])}]
    types = [s["type"] for s in script["scenes"]]
    cues = [{"scene": 0, "track": pick(HS_MOODS["open"])}]
    k = 0
    for i, t in enumerate(types):
        if t == "chapter":
            cues.append({"scene": i, "track": HS_MOODS["body"][(k + sum(map(ord, script["id"]))) % len(HS_MOODS["body"])]})
            k += 1
    if len(types) > 6:
        cues.append({"scene": len(types) - 2, "track": pick(HS_MOODS["payoff"])})
    return cues


# ------------------------------------------------------------------ assemble

def main(script, channel, build, tl):
    portrait = script.get("format") == "short"
    W, H = (1080, 1920) if portrait else (1920, 1080)
    comp = build / "compositions"
    comp.mkdir(parents=True, exist_ok=True)
    assets = build / "assets"
    for sub in ("sfx", "fonts", "bg"):
        (assets / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "node_modules" / "gsap" / "dist" / "gsap.min.js", assets / "gsap.min.js")
    shutil.copy(ROOT / "assets" / "cinema.js", assets / "cinema.js")
    shutil.copy(HSD / "drip.js", assets / "drip.js")
    for f in ("hs-display.woff2", "hs-mono.woff2"):
        shutil.copy(HSD / "fonts" / f, assets / "fonts" / f)
    A.concrete_png(assets / "bg" / f"concrete-{W}x{H}.png", W, H, seed=sum(map(ord, script["id"])) % 97)
    total = round(tl["total"] + .6, 3)
    voice_lufs = cine.lufs(assets / "voice.wav")

    scenes = list(zip(script["scenes"], tl["scenes"]))
    S_all = []
    for i, (sp, tsc) in enumerate(scenes):
        if i == len(scenes) - 1:
            tsc = dict(tsc, duration=round(total - tsc["start"], 3))
        S = C.Scene(tsc["id"], sp, tsc, W, H, channel["theme"])
        S.first, S.idx, S.start, S.sfx = i == 0, i, tsc["start"], []
        S_all.append(S)
    ctx = {"voice": assets / "voice.wav", "zoom_hist": [], "lead_hist": []}
    follows = [S for S in S_all if S.spec["type"] == "follow"]
    if follows:
        ctx["strip"] = A.power_strip() if script.get("system", "power") == "power" else A.power_strip()
        ctx["fkeys"] = follow_keys(follows, ctx["strip"], ctx)
    hosts, sfx = [], []
    for S in S_all:
        (comp / f"{S.sid}.html").write_text(scene_file(S, ctx))
        hosts.append(f'<div id="{S.sid}" data-composition-id="{S.sid}" data-composition-src="compositions/{S.sid}.html" '
                     f'data-start="{S.start}" data-duration="{S.dur}" data-track-index="1" data-track-kind="graphics" '
                     f'data-width="{W}" data-height="{H}" style="z-index:1"></div>')
        for name, t, under in S.sfx:
            if name in cine.CATALOG and 0 <= S.start + t < total - .1:
                sfx.append(cine.sfx_clip(name, S.start + t, total, voice_lufs, under))

    (comp / "fx.html").write_text(fx_file(W, H, total))
    hosts.append(f'<div id="fx" data-composition-id="fx" data-composition-src="compositions/fx.html" data-start="0" '
                 f'data-duration="{total}" data-track-index="6" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:40"></div>')
    if portrait:
        groups = C.caption_groups(tl, 3, 18)
        (comp / "captions.html").write_text(captions_file(groups, W, H, total))
        hosts.append(f'<div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" '
                     f'data-start="0" data-duration="{total}" data-track-index="2" data-track-kind="captions" '
                     f'data-width="{W}" data-height="{H}" style="z-index:50"></div>')
    (build / "captions.srt").write_text(C.srt(C.caption_groups(tl, 8, 46)))

    audio = [f'<audio id="vo" class="clip" data-start="0" data-duration="{tl["total"]}" data-track-index="3" data-volume="1" src="assets/voice.wav"></audio>']
    music = cine.build_music(dict(script, score=score_for(script, tl)), assets, total, tl)
    if music:
        audio.append(f'<audio id="bed" class="clip" data-start="0" data-duration="{total}" data-track-index="4" data-volume="1" src="assets/music.wav"></audio>')
    if follows:   # transformer hum under the cutaway travel, ~30 dB under the voice
        f0, f1 = follows[0].start, follows[-1].start + follows[-1].dur
        hum_wav(assets / "hum.wav", f1 - f0)
        g = round(min(1.0, 10 ** ((voice_lufs - 30 - cine.lufs(assets / "hum.wav")) / 20)), 3)
        audio.append(f'<audio id="hum" class="clip" data-start="{f0:.3f}" data-duration="{f1 - f0:.3f}" data-track-index="9" data-volume="{g}" src="assets/hum.wav"></audio>')
    last_end = {}
    for k, (name, st, dur, gain) in enumerate(sorted(sfx, key=lambda x: x[1])):
        trk = 5 if name.startswith(("whoosh", "swell")) else 7 if name.startswith(("stamp", "switch")) else 8
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
    <script src="assets/cinema.js"></script>
    <script src="assets/drip.js"></script>
    <style>
      {fonts_css()}
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      html, body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:{PAL["concrete"]}; }}
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
    print(f"hidden look: {len(S_all)} scenes, {len(audio)} audio clips, {total:.1f}s, music={music}, voice {voice_lufs:.1f} LUFS")


# ------------------------------------------------------------------ thumbnail + stills

def thumbnail_page(t):
    """1280x720: Drip big with a clear emotion (hat mid-pop), the system behind him in cutaway,
    at most 3 words on a concrete slab on the other third. Never repeats the title's words."""
    W, H = 1280, 720
    big, small = C.esc(t.get("big", "")), C.esc(t.get("small", ""))
    expr = t.get("expr", "surprised")
    # a slice of the system: a whole tower behind Drip, the lit conductor, the spark at the insulator
    tower, att = A.k_lattice_tower(0, top=560)
    ts = .42
    tx, ty = 640, 600 - A.GY * ts
    ax, ay = tx + att[1][0] * ts, ty + att[1][1] * ts
    world = (f'<g transform="translate({tx} {ty:.1f}) scale({ts})">{tower}</g>'
             f'<path d="M-40 250 Q{(ax - 40) / 2:.0f} {ay + 120:.0f} {ax:.0f} {ay:.0f} Q{ax + 120:.0f} {ay + 60:.0f} {ax + 260:.0f} {ay + 20:.0f}" stroke="{A.INK}" stroke-width="12" fill="none"/>'
             f'<path d="M-40 250 Q{(ax - 40) / 2:.0f} {ay + 120:.0f} {ax:.0f} {ay:.0f}" stroke="{PAL["hat"]}" stroke-width="7" fill="none"/>'
             f'<path d="M{ax:.0f} {ay:.0f} Q{ax + 120:.0f} {ay + 60:.0f} {ax + 260:.0f} {ay + 20:.0f}" stroke="{PAL["steel"]}" stroke-width="6" fill="none"/>')
    spark_xy = (ax, ay)
    rig = A.drip_rig("th", expr)
    # hat mid-pop: lift + tilt (same as a take's peak), squash/stretch
    rig = rig.replace('<g id="th-hat">', '<g id="th-hat" transform="translate(-6 -30) rotate(-9 0 -52)">')
    rig = rig.replace('<g id="th-bod">', '<g id="th-bod" transform="translate(0 100) scale(.95 1.06) translate(0 -100)">')
    rig = rig.replace('<g id="th-armR" transform="translate(80 28) scale(0)">', '<g id="th-armR" transform="translate(80 28) rotate(-38) scale(1.1)">')
    grid = "".join(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="{PAL["grid"]}" stroke-width="2"/>' for x in range(0, W, 64)) + \
           "".join(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="{PAL["grid"]}" stroke-width="2"/>' for y in range(0, H, 64))
    spark = (f'<circle cx="{spark_xy[0]:.0f}" cy="{spark_xy[1]:.0f}" r="120" fill="url(#thg)"/><circle cx="{spark_xy[0]:.0f}" cy="{spark_xy[1]:.0f}" r="22" fill="{PAL["cream"]}"/>')
    slab = (f'<g transform="rotate(-3 1000 360)"><rect x="760" y="170" width="470" height="{330 if small else 230}" rx="14" fill="{PAL["concrete2"]}" stroke="{A.INK}" stroke-width="8"/>'
            f'<clipPath id="thz"><rect x="764" y="174" width="462" height="30"/></clipPath><g clip-path="url(#thz)"><rect x="760" y="170" width="470" height="34" fill="{PAL["hat"]}"/>'
            + "".join(f'<path d="M{760 + k * 44} 204 L{782 + k * 44} 170 L{804 + k * 44} 170 L{782 + k * 44} 204Z" fill="{A.INK}"/>' for k in range(-1, 12)) + '</g>'
            + f'<text x="995" y="{372 if small else 352}" font-family="HS Display" font-weight="800" font-size="{190 if len(t.get("big", "")) <= 4 else 140}" '
              f'fill="{PAL["hat"]}" text-anchor="middle" letter-spacing="2">{big}</text>'
            + (f'<text x="995" y="458" font-family="HS Display" font-weight="800" font-size="78" fill="{PAL["cream"]}" text-anchor="middle" letter-spacing="4">{small}</text>' if small else "")
            + "</g>")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<defs><radialGradient id="thg"><stop offset="0" stop-color="#FFF6E8" stop-opacity="1"/><stop offset=".25" stop-color="#FFD9A8" stop-opacity=".8"/>'
           f'<stop offset="1" stop-color="#F26B1D" stop-opacity="0"/></radialGradient></defs>'
           f'<rect width="{W}" height="{H}" fill="{PAL["concrete"]}"/>{grid}'
           f'<rect x="0" y="600" width="{W}" height="120" fill="#24292D"/><rect x="0" y="594" width="{W}" height="14" fill="{PAL["line"]}"/>'
           f'{world}{spark}<g transform="translate(330 470) scale(2.05)">{rig}</g>{slab}</svg>')
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{fonts_css((HSD / "fonts").as_uri() + "/")}'
            f'*{{margin:0;padding:0}} body{{width:{W}px;height:{H}px;overflow:hidden}}</style></head><body>{svg}</body></html>')


def thumbnail(script_path, channel_path, out_png):
    from playwright.sync_api import sync_playwright
    script = json.loads(Path(script_path).read_text())
    t = script.get("thumbnail") or {"big": "?", "small": ""}
    tmp = Path(out_png).with_suffix(".html")
    tmp.write_text(thumbnail_page(t))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        pg.goto(tmp.resolve().as_uri())
        pg.evaluate("document.fonts.ready.then(() => 1)")
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(out_png))
        b.close()
    tmp.unlink()
    print("thumbnail", out_png)


def endcard_page():
    W, H = 1920, 1080
    inner, slots, sub = endcard_svg(W, H)
    rig = A.drip_rig("ec", "happy").replace('<g id="ec-armR" transform="translate(80 28) scale(0)">',
                                            '<g id="ec-armR" transform="translate(80 28) rotate(-40) scale(1)">')
    return inner + f'<g transform="translate({W / 2} {H - 230}) scale(1.2)">{rig}</g>', slots


if __name__ == "__main__":
    import sys
    _script = json.loads(Path(sys.argv[1]).read_text())
    _build = Path(sys.argv[2])
    main(_script, json.loads(Path(sys.argv[3]).read_text()), _build, json.loads((_build / "timeline.json").read_text()))
