"""Compose: script JSON + timeline.json -> HyperFrames project (index.html + scenes).

Usage: python compose.py <script.json> <build_dir> <channel.json>
Run voice.py first (it writes build_dir/timeline.json and assets/voice.wav).
"""
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SFX_DIR = ROOT / "assets" / "sfx"


def esc(s):
    return html.escape(str(s), quote=True)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def rich(text, sid, k):
    """*word* -> highlighted span. Returns HTML."""
    parts = re.split(r"(\*[^*]+\*)", text)
    out = []
    for p in parts:
        if p.startswith("*") and p.endswith("*"):
            out.append(f'<span class="hl">{esc(p[1:-1])}</span>')
        else:
            out.append(esc(p))
    return "".join(out)


def words_html(text, sid, key):
    """Split a line into word spans (keeps *highlight*). Returns (html, count)."""
    tokens = re.findall(r"\*[^*]+\*[^\s*]*|\S+", text)
    spans = []
    n = 0
    for t in tokens:
        m = re.fullmatch(r"\*([^*]+)\*([^\s*]*)", t)
        if m:
            ws = m.group(1).split()
            for j, w in enumerate(ws):
                tail = esc(m.group(2)) if j == len(ws) - 1 else ""
                spans.append(f'<span class="w" id="{sid}-{key}-w{n}"><span class="hl">{esc(w)}</span>{tail}</span>')
                n += 1
        else:
            spans.append(f'<span class="w" id="{sid}-{key}-w{n}">{esc(t)}</span>')
            n += 1
    return " ".join(spans), n


class Scene:
    def __init__(self, sid, spec, tl_scene, W, H, theme):
        self.sid = sid
        self.spec = spec
        self.d = spec.get("data", {})
        self.words = tl_scene["words"]
        self.dur = tl_scene["duration"]
        self.W, self.H = W, H
        self.portrait = H > W
        self.theme = theme
        self.narr_end = self.words[-1]["end"] if self.words else self.dur - 0.4
        self.first = False
        self.pops = []      # scene-local times for "pop" sfx
        self.impacts = []

    def cue(self, needle, fallback):
        if needle:
            n = norm(needle)
            for w in self.words:
                wn = norm(w["text"])
                if wn and (wn.startswith(n) or n in wn):
                    return round(max(0.12, min(w["start"] - 0.06, self.dur - 0.7)), 3)
        return round(max(0.12, min(fallback, self.dur - 0.7)), 3)

    def spread(self, i, n, start=0.2, span=0.7):
        if n <= 1:
            return start
        return start + (self.narr_end * span) * i / (n - 1)

    def s(self, landscape_px, portrait_px=None):
        return portrait_px if (self.portrait and portrait_px is not None) else landscape_px


# ---------------------------------------------------------------- templates
# Each returns (markup, css, js_lines). `S` is the Scene. Ids are prefixed.

def t_chapter(S):
    sid, d = S.sid, S.d
    markup = f'''
    <div id="{sid}-wipe"></div>
    <div class="center">
      <div id="{sid}-num" class="chap-num">{esc(d.get("num", ""))}</div>
      <div id="{sid}-title" class="chap-title">{rich(d.get("title", ""), sid, "t")}</div>
    </div>'''
    css = f'''
    #{sid}-wipe {{ position:absolute; inset:0; background: var(--accent); }}
    #root .chap-num {{ font-family:'PL Mono',monospace; font-size:{S.s(64, 72)}px; color: var(--bg); opacity:.75; margin-bottom: 24px; letter-spacing:.1em; }}
    #root .chap-title {{ font-family:'PL Display',sans-serif; font-size:{S.s(96, 104)}px; line-height:1.02; color: var(--bg); text-align:center; max-width:{S.s(1500, 900)}px; letter-spacing:-.02em; }}
    #root .chap-title .hl {{ color: var(--paper); }}'''
    js = [
        f'tl.fromTo("#{sid}-wipe", {{scaleX:0, transformOrigin:"0% 50%"}}, {{scaleX:1, duration:.55, ease:"power3.inOut"}}, 0)',
        f'tl.fromTo("#{sid}-num", {{opacity:0, y:50}}, {{opacity:.75, y:0, duration:.5, ease:"power3.out"}}, .35)',
        f'tl.fromTo("#{sid}-title", {{opacity:0, y:60}}, {{opacity:1, y:0, duration:.7, ease:"power4.out"}}, .5)',
    ]
    return markup, css, js


def fmt_js():
    return ('function fmtN(v, dec, comma){ var s = v.toFixed(dec); if(comma){ var p = s.split("."); '
            'p[0] = p[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g, ","); s = p.join("."); } return s; }')


def t_counter(S):
    sid, d = S.sid, S.d
    at = S.cue(d.get("cue"), 0.5)
    static = d.get("display")
    markup = f'''
    <div class="center">
      <div id="{sid}-kick" class="kicker">{esc(d.get("kicker", ""))}</div>
      <div class="bignum-wrap"><div id="{sid}-num" class="bignum">{esc(static or "")}</div></div>
      <div id="{sid}-label" class="label">{rich(d.get("label", ""), sid, "l")}</div>
    </div>
    <div id="{sid}-src" class="src">{esc(d.get("source", ""))}</div>'''
    css = f'''
    #root .bignum {{ font-family:'PL Display',sans-serif; font-size:{S.s(230, 190)}px; line-height:1; color: var(--gold); font-variant-numeric: tabular-nums; letter-spacing:-.03em; text-align:center; }}'''
    js = []
    if d.get("kicker"):
        js.append(f'tl.fromTo("#{sid}-kick", {{opacity:0, y:20}}, {{opacity:1, y:0, duration:.4, ease:"power2.out"}}, {max(0.1, at - 0.5)})')
    if static:
        js.append(f'tl.fromTo("#{sid}-num", {{opacity:0, scale:1.25}}, {{opacity:1, scale:1, duration:.45, ease:"power4.out"}}, {at})')
        S.pops.append(at + 0.05)
    else:
        val = float(d["value"])
        dec = int(d.get("decimals", 0))
        pre, suf = d.get("prefix", ""), d.get("suffix", "")
        comma = "true" if d.get("comma") else "false"
        js.append(fmt_js())
        js.append(f'var {sid}o = {{v:0}}; var {sid}el = document.getElementById("{sid}-num");')
        js.append(f'{sid}el.textContent = {json.dumps(pre)} + fmtN(0, {dec}, {comma}) + {json.dumps(suf)};')
        js.append(f'tl.fromTo("#{sid}-num", {{opacity:0}}, {{opacity:1, duration:.2}}, {at})')
        js.append(f'tl.fromTo({sid}o, {{v:0}}, {{v:{val}, duration:1.4, ease:"power2.out", onUpdate: function(){{ {sid}el.textContent = {json.dumps(pre)} + fmtN({sid}o.v, {dec}, {comma}) + {json.dumps(suf)}; }} }}, {at})')
        js.append(f'tl.fromTo("#{sid}-num", {{scale:1}}, {{scale:1.06, duration:.12, yoyo:true, repeat:1, ease:"power2.out"}}, {at + 1.4})')
        S.pops.append(at + 1.42)
    js.append(f'tl.fromTo("#{sid}-label", {{opacity:0, y:24}}, {{opacity:1, y:0, duration:.5, ease:"power3.out"}}, {at + 0.35})')
    js.append(f'tl.fromTo("#{sid}-src", {{opacity:0}}, {{opacity:.6, duration:.4}}, {at + 0.6})')
    return markup, css, js


def t_compare(S):
    """Vertical columns that grow to their values."""
    sid, d = S.sid, S.d
    items = d["items"]
    vmax = max(float(i["value"]) for i in items)
    hmax = S.s(500, 420)
    cols = []
    js = [f'tl.fromTo("#{sid}-base", {{scaleX:0, transformOrigin:"50% 50%"}}, {{scaleX:1, duration:.5, ease:"power3.out"}}, .1)']
    for k, it in enumerate(items):
        h = max(8, int(hmax * float(it["value"]) / vmax))
        color = "var(--accent)" if it.get("highlight") else "var(--paper)"
        cols.append(f'''
        <div class="col">
          <div id="{sid}-v{k}" class="col-val" style="color:{color}">{esc(it.get("display", it["value"]))}</div>
          <div id="{sid}-b{k}" class="col-bar" style="height:{h}px;background:{color}"></div>
          <div id="{sid}-l{k}" class="col-lab">{esc(it["label"])}</div>
        </div>''')
        at = S.cue(it.get("cue"), S.spread(k, len(items), 0.4, 0.55))
        js.append(f'tl.fromTo("#{sid}-b{k}", {{scaleY:0, transformOrigin:"50% 100%"}}, {{scaleY:1, duration:.9, ease:"power3.out"}}, {at})')
        js.append(f'tl.fromTo("#{sid}-l{k}", {{opacity:0, y:16}}, {{opacity:1, y:0, duration:.4}}, {at})')
        js.append(f'tl.fromTo("#{sid}-v{k}", {{opacity:0, y:20}}, {{opacity:1, y:0, duration:.4, ease:"back.out(2)"}}, {at + 0.35})')
        S.pops.append(at + 0.37)
    title = d.get("title", "")
    markup = f'''
    <div id="{sid}-title" class="title">{rich(title, sid, "t")}</div>
    <div id="{sid}-chart" class="cols">{"".join(cols)}</div>
    <div id="{sid}-base" class="baseline"></div>
    <div id="{sid}-src" class="src">{esc(d.get("source", ""))}</div>'''
    colw = S.s(300, 300)
    css = f'''
    #root .cols {{ position:absolute; left:0; right:0; bottom:{S.s(210, 880)}px; display:flex; justify-content:center; align-items:flex-end; gap:{S.s(160, 110)}px; }}
    #root .col {{ width:{colw}px; display:flex; flex-direction:column; align-items:center; }}
    #root .col-val {{ font-family:'PL Display',sans-serif; font-size:{S.s(76, 72)}px; margin-bottom:18px; font-variant-numeric: tabular-nums; }}
    #root .col-bar {{ width:{colw - 60}px; border-radius:10px 10px 0 0; }}
    #root .col-lab {{ position:absolute; top:100%; margin-top:24px; left:0; width:{colw}px; text-align:center; font-size:{S.s(32, 34)}px; line-height:1.15; font-weight:700; color: var(--muted); }}
    #root .col {{ position:relative; }}
    #{sid}-base {{ position:absolute; left:{S.s(360, 90)}px; right:{S.s(360, 90)}px; bottom:{S.s(208, 878)}px; height:4px; background: var(--muted); }}'''
    if title:
        js.insert(0, f'tl.fromTo("#{sid}-title", {{opacity:0, y:-20}}, {{opacity:1, y:0, duration:.5, ease:"power3.out"}}, .05)')
    js.append(f'tl.fromTo("#{sid}-src", {{opacity:0}}, {{opacity:.6, duration:.4}}, .8)')
    return markup, css, js


def t_bars(S):
    """Horizontal bars."""
    sid, d = S.sid, S.d
    items = d["items"]
    vmax = max(float(i["value"]) for i in items)
    wmax = S.s(780 if getattr(S, "hosted", False) else 1050, 820)
    rows, js = [], []
    for k, it in enumerate(items):
        w = max(10, int(wmax * float(it["value"]) / vmax))
        color = "var(--accent)" if it.get("highlight") else "var(--paper)"
        rows.append(f'''
        <div class="row">
          <div id="{sid}-l{k}" class="row-lab">{esc(it["label"])}</div>
          <div class="row-track"><div id="{sid}-b{k}" class="row-bar" style="width:{w}px;background:{color}"></div>
          <div id="{sid}-v{k}" class="row-val" style="color:{color}">{esc(it.get("display", it["value"]))}</div></div>
        </div>''')
        at = S.cue(it.get("cue"), S.spread(k, len(items), 0.4, 0.6))
        js.append(f'tl.fromTo("#{sid}-l{k}", {{opacity:0, x:-20}}, {{opacity:1, x:0, duration:.4}}, {at})')
        js.append(f'tl.fromTo("#{sid}-b{k}", {{scaleX:0, transformOrigin:"0% 50%"}}, {{scaleX:1, duration:1.0, ease:"power3.out"}}, {at + 0.1})')
        js.append(f'tl.fromTo("#{sid}-v{k}", {{opacity:0, x:-10}}, {{opacity:1, x:0, duration:.35}}, {at + 0.9})')
        S.pops.append(at + 0.92)
    markup = f'''
    <div id="{sid}-title" class="title">{rich(d.get("title", ""), sid, "t")}</div>
    <div class="rows">{"".join(rows)}</div>
    <div id="{sid}-src" class="src">{esc(d.get("source", ""))}</div>'''
    css = f'''
    #root .rows {{ position:absolute; left:{S.s(220, 100)}px; right:{S.s(220, 100)}px; top:{S.s(330, 560)}px; display:flex; flex-direction:column; gap:{S.s(70, 80)}px; }}
    #root .row {{ display:flex; flex-direction:{S.s("row", "column")}; align-items:{S.s("center", "flex-start")}; gap:{S.s(40, 18)}px; }}
    #root .row-lab {{ flex-shrink:0; width:{S.s(360, 880)}px; font-size:{S.s(38, 40)}px; font-weight:700; color: var(--paper); text-align:{S.s("right", "left")}; }}
    #root .row-track {{ display:flex; align-items:center; gap:28px; }}
    #root .row-bar {{ height:{S.s(84, 90)}px; border-radius:0 12px 12px 0; }}
    #root .row-val {{ font-family:'PL Display',sans-serif; font-size:{S.s(64, 64)}px; font-variant-numeric: tabular-nums; }}'''
    js.insert(0, f'tl.fromTo("#{sid}-title", {{opacity:0, y:-20}}, {{opacity:1, y:0, duration:.5, ease:"power3.out"}}, .05)')
    js.append(f'tl.fromTo("#{sid}-src", {{opacity:0}}, {{opacity:.6, duration:.4}}, .8)')
    return markup, css, js


def t_share(S):
    sid, d = S.sid, S.d
    pct = float(d["pct"])
    at = S.cue(d.get("cue"), 0.5)
    bw = S.s(1300, 880)
    markup = f'''
    <div id="{sid}-title" class="title">{rich(d.get("title", ""), sid, "t")}</div>
    <div class="center">
      <div class="bignum-wrap"><div id="{sid}-pct" class="bignum">0%</div></div>
      <div class="share-wrap">
        <div id="{sid}-whole" class="share-whole"></div>
        <div id="{sid}-part" class="share-part"></div>
        <div id="{sid}-pl" class="share-lab" style="left:0;color:var(--accent)">{esc(d.get("part_label", ""))}</div>
        <div id="{sid}-wl" class="share-lab" style="right:0;text-align:right">{esc(d.get("whole_label", ""))}</div>
      </div>
    </div>
    <div id="{sid}-src" class="src">{esc(d.get("source", ""))}</div>'''
    css = f'''
    #root .bignum {{ font-family:'PL Display',sans-serif; font-size:{S.s(200, 200)}px; line-height:1; color: var(--accent); font-variant-numeric: tabular-nums; }}
    #root .share-wrap {{ position:relative; width:{bw}px; height:{S.s(90, 96)}px; margin-top:{S.s(60, 80)}px; }}
    #root .share-whole {{ position:absolute; inset:0; border:4px solid var(--paper); border-radius:14px; }}
    #root .share-part {{ position:absolute; left:0; top:0; bottom:0; width:{pct}%; background: var(--accent); border-radius:14px 0 0 14px; }}
    #root .share-lab {{ position:absolute; top:{S.s(112, 120)}px; font-size:{S.s(34, 36)}px; font-weight:700; color: var(--paper); width:{S.s(600, 440)}px; }}'''
    js = [
        f'tl.fromTo("#{sid}-title", {{opacity:0, y:-20}}, {{opacity:1, y:0, duration:.5, ease:"power3.out"}}, .05)',
        f'tl.fromTo("#{sid}-whole", {{opacity:0}}, {{opacity:1, duration:.4}}, .3)',
        f'tl.fromTo("#{sid}-wl", {{opacity:0}}, {{opacity:1, duration:.4}}, .45)',
        fmt_js(),
        f'var {sid}o = {{v:0}}; var {sid}el = document.getElementById("{sid}-pct");',
        f'tl.fromTo("#{sid}-part", {{scaleX:0, transformOrigin:"0% 50%"}}, {{scaleX:1, duration:1.4, ease:"power2.inOut"}}, {at})',
        f'tl.fromTo({sid}o, {{v:0}}, {{v:{pct}, duration:1.4, ease:"power2.inOut", onUpdate:function(){{ {sid}el.textContent = fmtN({sid}o.v, 0, false) + "%"; }} }}, {at})',
        f'tl.fromTo("#{sid}-pl", {{opacity:0, y:10}}, {{opacity:1, y:0, duration:.4}}, {at + 1.2})',
        f'tl.fromTo("#{sid}-src", {{opacity:0}}, {{opacity:.6, duration:.4}}, {at + 1.0})',
    ]
    S.pops.append(at + 1.42)
    return markup, css, js


def t_dots(S):
    sid, d = S.sid, S.d
    n = int(d["n"])
    at = S.cue(d.get("cue"), 0.6)
    size, gap = S.s(34, 32), S.s(14, 12)
    dots = "".join(f'<div class="dot" id="{sid}-d{i}"></div>' for i in range(100))
    markup = f'''
    <div class="dots-layout">
      <div id="{sid}-grid" class="grid">{dots}</div>
      <div class="dots-text">
        <div id="{sid}-big" class="bignum2">{esc(d.get("big", ""))}</div>
        <div id="{sid}-label" class="label left">{rich(d.get("label", ""), sid, "l")}</div>
        <div id="{sid}-sub" class="sub">{rich(d.get("sub", ""), sid, "s")}</div>
      </div>
    </div>
    <div id="{sid}-src" class="src">{esc(d.get("source", ""))}</div>'''
    css = f'''
    #root .dots-layout {{ position:absolute; inset:0; display:flex; flex-direction:{S.s("row", "column")}; align-items:center; justify-content:center; gap:{S.s(120, 70)}px; padding-bottom:{S.s(0, 560)}px; }}
    #root .grid {{ display:grid; grid-template-columns: repeat(10, {size}px); gap:{gap}px; }}
    #root .dot {{ width:{size}px; height:{size}px; border-radius:50%; background: {lt(S, 'rgba(243,238,227,.14)', 'rgba(30,36,48,.13)')}; }}
    #root .dots-text {{ display:flex; flex-direction:column; align-items:{S.s("flex-start", "center")}; max-width:{S.s(700, 900)}px; }}
    #root .bignum2 {{ font-family:'PL Display',sans-serif; font-size:{S.s(170, 150)}px; line-height:1; color: var(--accent); }}
    #root .label.left {{ text-align:{S.s("left", "center")}; margin-top:20px; }}
    #root .sub {{ font-size:{S.s(36, 38)}px; color: var(--muted); margin-top:24px; font-weight:700; }}'''
    first = getattr(S, "first", False) and S.portrait
    js = [f'tl.fromTo("#{sid}-grid .dot", {{opacity:{1 if first else 0}, scale:{1 if first else .3}}}, {{opacity:1, scale:1, duration:.3, stagger:{{each:.006, from:"start"}}, ease:"back.out(2)"}}, {0 if first else .15})']
    js.append(f'tl.fromTo([' + ",".join(f'"#{sid}-d{i}"' for i in range(n)) +
              f'], {{backgroundColor:"{lt(S, 'rgba(243,238,227,.14)', 'rgba(30,36,48,.13)')}"}}, {{backgroundColor:"#FF5B36", duration:.25, stagger:{1.3 / max(n, 1):.4f}}}, {at})')
    js.append(f'tl.fromTo("#{sid}-big", {{opacity:{1 if first else 0}, y:{0 if first else 30}}}, {{opacity:1, y:0, duration:.5, ease:"power3.out"}}, {0 if first else at + 0.2})')
    js.append(f'tl.fromTo("#{sid}-label", {{opacity:0}}, {{opacity:1, duration:.4}}, {at + 0.5})')
    sub_at = S.cue(d.get("sub_cue"), at + 1.6)
    js.append(f'tl.fromTo("#{sid}-sub", {{opacity:0, y:12}}, {{opacity:1, y:0, duration:.4}}, {sub_at})')
    js.append(f'tl.fromTo("#{sid}-src", {{opacity:0}}, {{opacity:.6, duration:.4}}, {at + 0.8})')
    S.pops.append(at + 1.55)
    return markup, css, js


FS_STMT = {"l": {False: 92, True: 96}, "m": {False: 72, True: 80}, "xl": {False: 120, True: 112}}


def t_statement(S):
    sid, d = S.sid, S.d
    lines = d["lines"]
    blocks, js = [], []
    for k, ln in enumerate(lines):
        if isinstance(ln, str):
            ln = {"text": ln}
        inner, nw = words_html(ln["text"], sid, f"l{k}")
        color = {"plus": "var(--mint)", "minus": "var(--accent)"}.get(ln.get("tone"), "var(--paper)")
        plain = re.sub(r"[*]", "", ln["text"])
        maxw = S.s(1600, 940)
        lfs = min(FS_STMT[d.get("size", "l")][S.portrait], int(maxw / (0.64 * max(len(plain), 1))))
        nowrap = "white-space:nowrap;" if not S.portrait or lfs >= 64 else ""
        blocks.append(f'<div id="{sid}-l{k}" class="stmt" style="color:{color};font-size:{max(lfs, 56)}px;{nowrap}">{inner}</div>')
        at = S.cue(ln.get("cue"), S.spread(k, len(lines), 0.25, 0.6))
        ids = ",".join(f'"#{sid}-l{k}-w{i}"' for i in range(nw))
        if k == 0 and getattr(S, "first", False) and S.portrait:
            js.append(f'tl.fromTo([{ids}], {{opacity:1, scale:1.08}}, {{opacity:1, scale:1, duration:.6, ease:"power3.out"}}, 0)')
        else:
            js.append(f'tl.fromTo([{ids}], {{opacity:0, y:40}}, {{opacity:1, y:0, duration:.45, stagger:.06, ease:"power3.out"}}, {at})')
    markup = f'''
    <div class="center">{"".join(blocks)}</div>'''
    size = d.get("size", "l")
    fs = {"l": S.s(92, 96), "m": S.s(72, 80), "xl": S.s(120, 112)}[size]
    css = f'''
    #root .center {{ padding-bottom:{S.s(0, 300)}px; }}
    #root .stmt {{ font-family:'PL Display',sans-serif; font-size:{fs}px; line-height:1.12; text-align:center; max-width:{S.s(1560, 920)}px; letter-spacing:-.015em; margin: 14px 0; }}
    #root .stmt .w {{ display:inline-block; }}
    #root .stmt .hl {{ color: var(--gold); }}
    #root .stmt .w .hl {{ display:inline; }}'''
    return markup, css, js


def t_quote(S):
    sid, d = S.sid, S.d
    inner, nw = words_html(d["quote"], sid, "q")
    at = S.cue(d.get("cue"), S.narr_end * 0.45)
    end = max(at + 0.8, S.narr_end - 0.3)
    each = (end - at) / max(nw, 1)
    markup = f'''
    <div class="center">
      <div id="{sid}-mark" class="qmark">&ldquo;</div>
      <div id="{sid}-q" class="quote">{inner}</div>
      <div id="{sid}-who" class="who">{esc(d.get("who", ""))}</div>
      <div id="{sid}-note" class="note">{esc(d.get("note", ""))}</div>
    </div>'''
    css = f'''
    #root .center {{ padding-bottom:{S.s(0, 300)}px; }}
    #root .qmark {{ font-family:'Playfair Display',serif; font-size:{S.s(260, 260)}px; line-height:.6; color: var(--accent); height:{S.s(130, 130)}px; }}
    #root .quote {{ font-family:'Playfair Display',serif; font-style:italic; font-weight:700; font-size:{S.s(84, 82)}px; line-height:1.18; text-align:center; max-width:{S.s(1500, 920)}px; }}
    #root .quote .w {{ display:inline-block; }}
    #root .quote .hl {{ color: var(--gold); }}
    #root .who {{ margin-top:48px; font-size:{S.s(44, 40)}px; font-weight:700; color: var(--paper); }}
    #root .note {{ margin-top:10px; font-size:{S.s(38, 34)}px; color: var(--muted); }}'''
    ids = ",".join(f'"#{sid}-q-w{i}"' for i in range(nw))
    js = [
        f'tl.fromTo("#{sid}-mark", {{opacity:0, scale:.6}}, {{opacity:1, scale:1, duration:.5, ease:"back.out(2)"}}, .15)',
        f'tl.fromTo("#{sid}-who", {{opacity:0}}, {{opacity:1, duration:.4}}, .4)',
        f'tl.fromTo("#{sid}-note", {{opacity:0}}, {{opacity:1, duration:.4}}, .6)',
        f'tl.fromTo([{ids}], {{opacity:0, y:24}}, {{opacity:1, y:0, duration:.3, stagger:{each:.3f}, ease:"power2.out"}}, {at})',
    ]
    S.impacts.append(end + 0.2)
    return markup, css, js


def t_flow(S):
    sid, d = S.sid, S.d
    steps = d["steps"]
    parts, js = [], []
    for k, st in enumerate(steps):
        if isinstance(st, str):
            st = {"label": st}
        hl = " hlbox" if st.get("highlight") or k == len(steps) - 1 else ""
        parts.append(f'<div id="{sid}-s{k}" class="step{hl}"><div class="step-n">{k + 1:02d}</div><div class="step-t">{esc(st["label"])}</div></div>')
        if k < len(steps) - 1:
            parts.append(f'<div id="{sid}-a{k}" class="arrow"></div>')
        at = S.cue(st.get("cue"), S.spread(k, len(steps), 0.3, 0.75))
        if k > 0:
            js.append(f'tl.fromTo("#{sid}-a{k - 1}", {{scaleX:0, scaleY:0, transformOrigin:"0% 0%"}}, {{scaleX:1, scaleY:1, duration:.35, ease:"power2.out"}}, {max(0.1, at - 0.25)})')
        js.append(f'tl.fromTo("#{sid}-s{k}", {{opacity:0, y:40, scale:.92}}, {{opacity:1, y:0, scale:1, duration:.5, ease:"back.out(1.6)"}}, {at})')
        S.pops.append(at + 0.05)
    markup = f'''
    <div id="{sid}-title" class="title">{rich(d.get("title", ""), sid, "t")}</div>
    <div class="flow">{"".join(parts)}</div>'''
    css = f'''
    #root .flow {{ position:absolute; inset:0; display:flex; flex-direction:{S.s("row", "column")}; align-items:center; justify-content:center; gap:{S.s(26, 22)}px; padding: 0 80px {S.s(0, 380)}px; }}
    #root .step {{ background: var(--panel); border:3px solid {lt(S, 'rgba(243,238,227,.18)', 'rgba(30,36,48,.16)')}; border-radius:22px; padding:{S.s("34px 30px", "30px 40px")}; width:{S.s(420 if len(steps) <= 3 else 350, 720)}px; min-height:{S.s(220, 0)}px; }}
    #root .step.hlbox {{ border-color: var(--gold); }}
    #root .step-n {{ font-family:'PL Mono',monospace; font-size:28px; color: var(--muted); margin-bottom:14px; }}
    #root .step-t {{ font-family:'PL Display',sans-serif; font-size:{S.s(46, 52)}px; line-height:1.1; }}
    #root .step.hlbox .step-t {{ color: var(--gold); }}
    #root .arrow {{ width:{S.s(60, 6)}px; height:{S.s(6, 50)}px; background: var(--accent); border-radius:3px; }}'''
    if d.get("title"):
        js.insert(0, f'tl.fromTo("#{sid}-title", {{opacity:0, y:-20}}, {{opacity:1, y:0, duration:.5}}, .05)')
    return markup, css, js


def t_years(S):
    sid, d = S.sid, S.d
    y0, y1 = int(d["from"]), int(d["to"])
    ticks = list(range(y0, y1 + 1, 5))
    lw = S.s(1400, 860)
    tick_html = "".join(
        f'<div class="tick" id="{sid}-t{i}" style="left:{(y - y0) / (y1 - y0) * lw:.0f}px"><span>{y if y in (y0, y1) or not S.portrait else ""}</span></div>'
        for i, y in enumerate(ticks))
    at1 = S.cue(d.get("cue_end"), S.narr_end * 0.6)
    markup = f'''
    <div id="{sid}-label" class="title">{rich(d.get("label", ""), sid, "t")}</div>
    <div class="yr-wrap">
      <div id="{sid}-line" class="yr-line"></div>
      {tick_html}
      <div id="{sid}-p0" class="chip" style="left:0">{esc(d["price"])}</div>
      <div id="{sid}-flat" class="flat"></div>
      <div id="{sid}-p1" class="chip" style="left:{lw}px">{esc(d["price"])}</div>
    </div>
    <div id="{sid}-src" class="src">{esc(d.get("source", ""))}</div>'''
    css = f'''
    #root .yr-wrap {{ position:absolute; left:{(S.W - lw) // 2}px; width:{lw}px; top:{S.s(640, 900)}px; height:10px; }}
    #root .yr-line {{ position:absolute; left:0; right:0; top:0; height:6px; background: var(--paper); border-radius:3px; }}
    #root .tick {{ position:absolute; top:-14px; width:4px; height:34px; background: var(--paper); margin-left:-2px; }}
    #root .tick span {{ position:absolute; top:52px; left:-60px; width:124px; text-align:center; font-family:'PL Mono',monospace; font-size:{S.s(34, 40)}px; color: var(--muted); }}
    #root .chip {{ position:absolute; z-index:2; top:{S.s(-180, -200)}px; margin-left:-130px; width:260px; text-align:center; font-family:'PL Display',sans-serif; font-size:{S.s(80, 84)}px; color: var(--bg); background: var(--gold); border-radius:16px; padding:12px 0; }}
    #root .flat {{ position:absolute; z-index:1; left:0; width:{lw}px; top:{S.s(-120, -136)}px; height:0; border-top:5px dashed var(--gold); }}'''
    tick_ids = ",".join(f'"#{sid}-t{i}"' for i in range(len(ticks)))
    js = [
        (f'tl.fromTo("#{sid}-label", {{opacity:1}}, {{opacity:1, duration:.1}}, 0)' if S.first else
         f'tl.fromTo("#{sid}-label", {{opacity:0, y:-20}}, {{opacity:1, y:0, duration:.5}}, .05)'),
        f'tl.fromTo("#{sid}-line", {{scaleX:0, transformOrigin:"0% 50%"}}, {{scaleX:1, duration:{max(1.0, at1 - 0.6):.2f}, ease:"power1.inOut"}}, .3)',
        f'tl.fromTo([{tick_ids}], {{opacity:0, y:10}}, {{opacity:1, y:0, duration:.25, stagger:{max(1.0, at1 - 0.6) / len(ticks):.3f}}}, .3)',
        (f'tl.fromTo("#{sid}-p0", {{opacity:1, scale:1.1}}, {{opacity:1, scale:1, duration:.5, ease:"power2.out"}}, 0)' if S.first else
         f'tl.fromTo("#{sid}-p0", {{opacity:0, y:30, scale:.8}}, {{opacity:1, y:0, scale:1, duration:.45, ease:"back.out(2)"}}, {S.cue(d.get("cue_price"), 1.2)})'),
        f'tl.fromTo("#{sid}-flat", {{scaleX:0, transformOrigin:"0% 50%"}}, {{scaleX:1, duration:.9, ease:"power2.inOut"}}, {at1})',
        f'tl.fromTo("#{sid}-p1", {{opacity:0, y:30, scale:.8}}, {{opacity:1, y:0, scale:1, duration:.45, ease:"back.out(2)"}}, {at1 + 0.8})',
        f'tl.fromTo("#{sid}-src", {{opacity:0}}, {{opacity:.6, duration:.4}}, 1)',
    ]
    S.pops += [S.cue(d.get("cue_price"), 1.2) + 0.05, at1 + 0.85]
    return markup, css, js


def t_lines(S):
    """Illustrative trend lines: several rise, one stays flat (highlighted)."""
    sid, d = S.sid, S.d
    cw, ch = S.s(1300, 900), S.s(560, 760)
    series = d["series"]
    paths, labels, js = [], [], []
    for k, se in enumerate(series):
        pts = se["points"]
        n = len(pts)
        coords = [(i / (n - 1) * cw, ch - p * ch) for i, p in enumerate(pts)]
        dpath = "M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in coords)
        color = "#FFC531" if se.get("highlight") else ["#8A8F98", "#B9BCC2", "#6B7079", "#A3A7AE"][k % 4]
        width = 10 if se.get("highlight") else 6
        paths.append(f'<path id="{sid}-p{k}" d="{dpath}" pathLength="1" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1" stroke-dashoffset="1" opacity="0"/>')
        lx, ly = coords[-1]
        labels.append(f'<div id="{sid}-lb{k}" class="ln-lab" style="left:{lx + 24:.0f}px;top:{ly - 24:.0f}px;color:{color}">{esc(se["label"])}</div>')
        at = S.cue(se.get("cue"), S.spread(k, len(series), 0.3, 0.6))
        js.append(f'tl.fromTo("#{sid}-p{k}", {{opacity:0}}, {{opacity:1, duration:.05}}, {at})')
        js.append(f'tl.fromTo("#{sid}-p{k}", {{attr:{{"stroke-dashoffset":1}}}}, {{attr:{{"stroke-dashoffset":0}}, duration:1.3, ease:"power2.inOut"}}, {at})')
        js.append(f'tl.fromTo("#{sid}-lb{k}", {{opacity:0, x:-10}}, {{opacity:1, x:0, duration:.35}}, {at + 0.7})')
    markup = f'''
    <div id="{sid}-title" class="title">{rich(d.get("title", ""), sid, "t")}</div>
    <div class="ln-wrap" data-layout-allow-overflow>
      <div id="{sid}-axis" class="ln-axis"></div>
      <svg width="{cw}" height="{ch}" viewBox="0 0 {cw} {ch}" style="overflow:visible">{"".join(paths)}</svg>
      {"".join(labels)}
    </div>
    <div id="{sid}-tag" class="src">{esc(d.get("note", "Illustrative"))}</div>'''
    css = f'''
    #root .ln-wrap {{ position:absolute; left:{S.s(220, 70)}px; top:{S.s(260, 470)}px; width:{cw}px; height:{ch}px; }}
    #root .ln-axis {{ position:absolute; left:0; bottom:0; width:{cw}px; height:{ch}px; border-left:3px solid {lt(S, 'rgba(243,238,227,.3)', 'rgba(30,36,48,.35)')}; border-bottom:3px solid {lt(S, 'rgba(243,238,227,.3)', 'rgba(30,36,48,.35)')}; }}
    #root .ln-lab {{ position:absolute; font-weight:800; font-size:{S.s(34, 32)}px; white-space:nowrap; }}'''
    js.insert(0, f'tl.fromTo("#{sid}-title", {{opacity:0, y:-20}}, {{opacity:1, y:0, duration:.5}}, .05)')
    js.insert(1, f'tl.fromTo("#{sid}-axis", {{opacity:0}}, {{opacity:1, duration:.4}}, .1)')
    js.append(f'tl.fromTo("#{sid}-tag", {{opacity:0}}, {{opacity:.6, duration:.4}}, .6)')
    return markup, css, js


def t_cards(S):
    sid, d = S.sid, S.d
    cards, js = [], []
    for k, c in enumerate(d["cards"]):
        tone = "var(--gold)" if k == 0 else "var(--paper)"
        cards.append(f'''
        <div id="{sid}-c{k}" class="card">
          <div class="card-stripe" style="background:{tone}"></div>
          <div class="card-name">{esc(c["name"])}</div>
          <div class="card-price" style="color:{tone}">{esc(c["price"])}</div>
          <div class="card-sub">{esc(c.get("sub", ""))}</div>
        </div>''')
        at = S.cue(c.get("cue"), S.spread(k, len(d["cards"]), 0.5, 0.6))
        rot = -4 if k == 0 else 4
        js.append(f'tl.fromTo("#{sid}-c{k}", {{opacity:0, y:220, rotation:{rot * 3}}}, {{opacity:1, y:0, rotation:{rot}, duration:.7, ease:"power4.out"}}, {at})')
        S.pops.append(at + 0.4)
    markup = f'''
    <div id="{sid}-title" class="title">{rich(d.get("title", ""), sid, "t")}</div>
    <div class="cards">{"".join(cards)}</div>
    <div id="{sid}-src" class="src">{esc(d.get("source", ""))}</div>'''
    css = f'''
    #root .cards {{ position:absolute; inset:0; display:flex; flex-direction:{S.s("row", "column")}; align-items:center; justify-content:center; gap:{S.s(90, 70)}px; padding-bottom:{S.s(0, 330)}px; }}
    #root .card {{ width:{S.s(560, 700)}px; height:{S.s(350, 400)}px; border-radius:30px; background: var(--panel); border:3px solid {lt(S, 'rgba(243,238,227,.15)', 'rgba(30,36,48,.15)')}; position:relative; overflow:hidden; padding:44px 48px; }}
    #root .card-stripe {{ position:absolute; left:0; right:0; top:0; height:22px; }}
    #root .card-name {{ font-size:{S.s(38, 42)}px; font-weight:800; color: var(--muted); margin-top:20px; }}
    #root .card-price {{ font-family:'PL Display',sans-serif; font-size:{S.s(140, 150)}px; line-height:1.05; margin-top:12px; }}
    #root .card-sub {{ font-size:{S.s(32, 36)}px; color: var(--muted); }}'''
    js.insert(0, f'tl.fromTo("#{sid}-title", {{opacity:0, y:-20}}, {{opacity:1, y:0, duration:.5}}, .05)')
    js.append(f'tl.fromTo("#{sid}-src", {{opacity:0}}, {{opacity:.6, duration:.4}}, 1)')
    return markup, css, js


def t_pricetag(S):
    sid, d = S.sid, S.d
    at = S.cue(d.get("cue"), 0.35)
    markup = f'''
    <div class="center">
      <div id="{sid}-kick" class="kicker">{esc(d.get("kicker", ""))}</div>
      <div id="{sid}-swing" class="tag-swing">
        <div class="tag-string"></div>
        <div class="tag"><div class="tag-hole"></div><div class="tag-price">{esc(d["price"])}</div></div>
      </div>
      <div id="{sid}-label" class="label">{rich(d.get("label", ""), sid, "l")}</div>
    </div>'''
    css = f'''
    #root .tag-swing {{ display:flex; flex-direction:column; align-items:center; }}
    #root .tag-string {{ width:4px; height:{S.s(90, 120)}px; background: var(--muted); }}
    #root .tag {{ position:relative; background: var(--gold); color: var(--bg); border-radius:28px; padding:{S.s("40px 90px 40px 120px", "48px 90px 48px 120px")}; }}
    #root .tag-hole {{ position:absolute; left:42px; top:50%; width:38px; height:38px; margin-top:-19px; border-radius:50%; background: var(--bg); }}
    #root .tag-price {{ font-family:'PL Display',sans-serif; font-size:{S.s(200, 210)}px; line-height:1; letter-spacing:-.03em; }}'''
    js = [
        (f'tl.fromTo("#{sid}-kick", {{opacity:1, y:0}}, {{opacity:1, y:0, duration:.1}}, 0)' if S.first else
         f'tl.fromTo("#{sid}-kick", {{opacity:0, y:20}}, {{opacity:1, y:0, duration:.4}}, {max(0.1, at - 0.25)})'),
        (f'tl.fromTo("#{sid}-swing", {{opacity:1, y:0, rotation:-14, transformOrigin:"50% 0%"}}, {{opacity:1, y:0, rotation:0, duration:1.6, ease:"elastic.out(1, 0.35)"}}, 0)' if S.first else
         f'tl.fromTo("#{sid}-swing", {{opacity:0, y:-120, rotation:-16, transformOrigin:"50% 0%"}}, {{opacity:1, y:0, rotation:0, duration:1.4, ease:"elastic.out(1, 0.45)"}}, {at})'),
        f'tl.fromTo("#{sid}-label", {{opacity:0, y:24}}, {{opacity:1, y:0, duration:.5}}, {S.cue(d.get("label_cue"), at + 0.9)})',
    ]
    S.pops.append(at + 0.35)
    return markup, css, js


def t_end(S):
    sid, d = S.sid, S.d
    m, c, js = t_statement(S)
    m += f'<div id="{sid}-foot" class="foot">{esc(d.get("foot", ""))}</div>'
    c += f'''
    #root .foot {{ position:absolute; left:0; right:0; bottom:{S.s(110, 860)}px; text-align:center; font-size:{S.s(40, 40)}px; font-weight:700; color: var(--muted); }}'''
    js.append(f'tl.fromTo("#{sid}-foot", {{opacity:0}}, {{opacity:1, duration:.5}}, {S.cue(d.get("foot_cue"), S.narr_end * 0.45)})')
    return m, c, js


TEMPLATES = {
    "chapter": t_chapter, "counter": t_counter, "compare": t_compare, "bars": t_bars,
    "share": t_share, "dots": t_dots, "statement": t_statement, "quote": t_quote,
    "flow": t_flow, "years": t_years, "lines": t_lines, "cards": t_cards,
    "pricetag": t_pricetag, "end": t_end,
}


def lt(S, dark, light):
    """Colour for the dark look or the light studio panel (cine.py sets S.light)."""
    return light if getattr(S, "light", False) else dark


def base_css(S):
    th = S.theme
    return f'''
    #root {{ position:absolute; inset:0; overflow:hidden; background:{th["bg"]};
      --bg:{th["bg"]}; --panel:{th["panel"]}; --paper:{th["paper"]}; --muted:{th["muted"]};
      --accent:{th["accent"]}; --gold:{th["gold"]}; --mint:{th["mint"]};
      font-family:'Inter',sans-serif; color: var(--paper); }}
    #{S.sid}-bg {{ position:absolute; inset:0;
      background-image: linear-gradient(rgba(243,238,227,.035) 2px, transparent 2px), linear-gradient(90deg, rgba(243,238,227,.035) 2px, transparent 2px);
      background-size: 96px 96px; background-position: center center; }}
    #{S.sid}-vig {{ position:absolute; inset:0; background: radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 45%, rgba(0,0,0,.5) 100%); }}
    #{S.sid}-cam {{ position:absolute; inset:0; }}
    #root .center {{ position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; padding-bottom:{S.s(0, 330)}px; }}
    #root .title {{ position:absolute; left:0; right:0; top:{S.s(110, 380)}px; text-align:center; font-family:'PL Display',sans-serif; font-size:{S.s(60, 64)}px; color: var(--paper); padding:0 80px; line-height:1.1; }}
    #root .title .hl, #root .label .hl {{ color: var(--gold); }}
    #root .kicker {{ font-family:'PL Mono',monospace; font-size:{S.s(38, 44)}px; color: var(--muted); letter-spacing:.12em; text-transform:uppercase; margin-bottom:26px; }}
    #root .label {{ font-size:{S.s(46, 52)}px; font-weight:700; color: var(--paper); margin-top:36px; text-align:center; max-width:{S.s(1400, 900)}px; line-height:1.2; }}
    #root .src {{ position:absolute; left:{S.s(96, 80)}px; bottom:{S.s(52, 600)}px; font-family:'PL Mono',monospace; font-size:{S.s(30, 30)}px; color: var(--muted); }}'''


def scene_file(S):
    fn = TEMPLATES[S.spec["type"]]
    markup, css, js = fn(S)
    sid, dur = S.sid, S.dur
    push = S.spec.get("push", 0.035)
    lines = [
        "const tl = gsap.timeline({ paused: true });",
        *[ln + ";" if not ln.rstrip().endswith(("}", ";")) else ln for ln in js],
        f'tl.fromTo("#{sid}-cam", {{scale:1}}, {{scale:{1 + push:.3f}, duration:{dur:.3f}, ease:"none"}}, 0);',
        f'tl.fromTo("#{sid}-bg", {{backgroundPosition:"50% 50%"}}, {{backgroundPosition:"50% 46%", duration:{dur:.3f}, ease:"none"}}, 0);',
        f'tl.to("#{sid}-fade", {{opacity:0, duration:.22, ease:"power2.in"}}, {max(0.3, dur - 0.24):.3f});',
        f'window.__timelines["{sid}"] = tl;',
    ]
    js_text = "\n    ".join(lines)
    return f'''<template>
  <style>{base_css(S)}{css}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="{S.W}" data-height="{S.H}">
    <div id="{sid}-bg"></div>
    <div id="{sid}-vig"></div>
    <div id="{sid}-cam"><div id="{sid}-fade" style="position:absolute;inset:0;">{markup}
    </div></div>
  </div>
  <script>
    {js_text}
  </script>
</template>
'''


# ---------------------------------------------------------------- captions

def caption_groups(tl, max_words, max_chars):
    groups = []
    for sc in tl["scenes"]:
        cur = []
        for w in sc["words"]:
            cur.append(w)
            text = " ".join(x["text"] for x in cur)
            if len(cur) >= max_words or len(text) >= max_chars or re.search(r"[.!?,;:]$", w["text"]):
                groups.append((sc["start"], cur))
                cur = []
        if cur:
            groups.append((sc["start"], cur))
    out = []
    for base, ws in groups:
        out.append({"start": round(base + ws[0]["start"], 3), "end": round(base + ws[-1]["end"], 3),
                    "words": [{"text": x["text"], "start": round(base + x["start"], 3), "end": round(base + x["end"], 3)} for x in ws]})
    # close each group when the next opens
    for a, b in zip(out, out[1:]):
        a["end"] = min(max(a["end"], a["start"] + 0.4), b["start"])
    return out


def captions_file(groups, W, H, total, theme):
    portrait = H > W
    blocks, js = [], []
    for g, grp in enumerate(groups):
        spans = []
        for i, w in enumerate(grp["words"]):
            spans.append(f'<span class="cw" id="cap-g{g}-w{i}">{esc(w["text"].upper() if portrait else w["text"])}</span>')
        blocks.append(f'<div class="cg" id="cap-g{g}">{" ".join(spans)}</div>')
        st, en = grp["start"], grp["end"]
        js.append(f'tl.fromTo("#cap-g{g}", {{opacity:0, scale:.92}}, {{opacity:1, scale:1, duration:.1, ease:"power2.out"}}, {st:.3f});')
        for i, w in enumerate(grp["words"]):
            js.append(f'tl.fromTo("#cap-g{g}-w{i}", {{color:"{theme.get("paper", "#FFFFFF")}"}}, {{color:"{theme["gold"]}", duration:.06}}, {w["start"]:.3f});')
        js.append(f'tl.to("#cap-g{g}", {{opacity:0, duration:.08, ease:"power2.in"}}, {max(st + 0.1, en - 0.08):.3f});')
        js.append(f'tl.set("#cap-g{g}", {{opacity:0, visibility:"hidden"}}, {en:.3f});')
    fs = 84 if portrait else 58
    bottom = 650 if portrait else 70
    return f'''<template>
  <style>
    #root {{ position:absolute; inset:0; pointer-events:none; }}
    #root .cg {{ position:absolute; left:0; right:0; bottom:{bottom}px; text-align:center; padding:0 {90 if portrait else 200}px;
      font-family:'PL Display',sans-serif; font-size:{fs}px; line-height:1.08; color:{theme.get("paper", "#FFFFFF")}; opacity:0;
      -webkit-text-stroke: {10 if portrait else 7}px {theme.get("ink", "#000")}; paint-order: stroke fill; overflow:visible; }}
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


def srt(groups):
    def ts(t):
        h, rem = divmod(t, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"
    out = []
    for i, g in enumerate(groups, 1):
        out.append(f"{i}\n{ts(g['start'])} --> {ts(g['end'])}\n{' '.join(w['text'] for w in g['words'])}\n")
    return "\n".join(out)


# ---------------------------------------------------------------- assemble

def build_music(channel, script, out_assets, total):
    lib = ROOT / channel.get("music_dir", "music")
    tracks = sorted(p for p in lib.glob("*") if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg")) if lib.exists() else []
    if not tracks:
        return None
    pick = tracks[int(hashlib.md5(script["id"].encode()).hexdigest(), 16) % len(tracks)]
    dst = out_assets / "music.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(pick), "-t", f"{total:.2f}",
                    "-af", f"afade=t=in:d=1.5,afade=t=out:st={max(0, total - 2.5):.2f}:d=2.5", "-ar", "44100", str(dst)], check=True)
    return pick.name


def main(script_path, build_dir, channel_path):
    script = json.loads(Path(script_path).read_text())
    channel = json.loads(Path(channel_path).read_text())
    build = Path(build_dir)
    tl = json.loads((build / "timeline.json").read_text())
    if script.get("style") == "cinematic":
        import cine
        return cine.main(script, channel, build, tl)
    portrait = script.get("format") == "short"
    W, H = (1080, 1920) if portrait else (1920, 1080)
    theme = channel["theme"]
    comp_dir = build / "compositions"
    comp_dir.mkdir(parents=True, exist_ok=True)
    assets = build / "assets"
    (assets / "sfx").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "node_modules" / "gsap" / "dist" / "gsap.min.js", assets / "gsap.min.js")

    total = round(tl["total"] + 0.6, 3)
    hosts, sfx = [], []
    whooshes = ["whoosh-short.mp3", "whoosh.mp3", "whoosh-short.mp3", "whoosh-cinematic.mp3"]
    for i, (spec, tsc) in enumerate(zip(script["scenes"], tl["scenes"])):
        sid = tsc["id"]
        if i == len(tl["scenes"]) - 1:
            tsc = dict(tsc, duration=round(total - tsc["start"], 3))
        S = Scene(sid, spec, tsc, W, H, theme)
        S.first = i == 0
        (comp_dir / f"{sid}.html").write_text(scene_file(S))
        hosts.append(f'<div id="{sid}" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" '
                     f'data-start="{tsc["start"]}" data-duration="{S.dur}" data-track-index="1" data-track-kind="graphics" '
                     f'data-width="{W}" data-height="{H}" style="z-index:1"></div>')
        if i > 0 and (spec["type"] == "chapter" or i % 2 == 0):
            f = "whoosh-cinematic.mp3" if spec["type"] == "chapter" else whooshes[i % 3]
            sfx.append((f, max(0, tsc["start"] - 0.12), 0.22 if spec["type"] != "chapter" else 0.3))
        for p in S.pops[:2]:
            sfx.append(("pop.mp3", tsc["start"] + p, 0.28))
        for p in S.impacts[:1]:
            sfx.append(("impact-bass-1.mp3", tsc["start"] + p, 0.35))

    manifest = json.loads((SFX_DIR / "manifest.json").read_text())
    durs = {v["file"]: v["duration"] for v in manifest.values()}
    audio = [f'<audio id="vo" class="clip" data-start="0" data-duration="{tl['total']}" data-track-index="3" data-volume="1" src="assets/voice.wav"></audio>']
    music = build_music(channel, script, assets, total)
    if music:
        audio.append(f'<audio id="bed" class="clip" data-start="0" data-duration="{total}" data-track-index="4" data-volume="{channel.get("music_volume", 0.14)}" src="assets/music.wav"></audio>')
    track_of = {"pop.mp3": 6, "impact-bass-1.mp3": 7}
    last_end = {}
    for k, (f, st, vol) in enumerate(sorted(sfx, key=lambda x: x[1])):
        trk = track_of.get(f, 5)
        if st < last_end.get(trk, -1):
            continue
        last_end[trk] = st + durs.get(f, 1.0)
        shutil.copy(SFX_DIR / f, assets / "sfx" / f)
        dd = min(durs.get(f, 1.0), total - st - 0.05)
        if dd <= 0.1:
            continue
        audio.append(f'<audio id="sfx{k}" class="clip" data-start="{st:.3f}" data-duration="{dd:.3f}" data-track-index="{trk}" data-volume="{vol}" src="assets/sfx/{f}"></audio>')

    if portrait:
        groups = caption_groups(tl, 3, 18)
        (comp_dir / "captions.html").write_text(captions_file(groups, W, H, total, theme))
        hosts.append(f'<div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" '
                     f'data-start="0" data-duration="{total}" data-track-index="2" data-track-kind="captions" '
                     f'data-width="{W}" data-height="{H}" style="z-index:50"></div>')
    srt_groups = caption_groups(tl, 8, 46)
    (build / "captions.srt").write_text(srt(srt_groups))

    index = f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="assets/gsap.min.js"></script>
    <style>
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      html, body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:{theme["bg"]}; }}
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
    print(f"composed {len(hosts)} hosts, {len(audio)} audio clips, {total:.1f}s, music={music}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
