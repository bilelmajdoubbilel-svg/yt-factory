"""Cinematic building blocks: an original host character rig and layered worlds (SVG/HTML).

Every part has a stable id ({cid}-part) so assets/cinema.js can pose and animate it.
Rig coordinates: feet at y=0, shoulders at y=-326, neck pivot at y=-345, head centre y=-420.
"""

OUTFITS = {
    # channel 1 (v3 brand): "Tag", a living price tag. Replaces the round-headed host, which read
    # like another channel (Ifverse). Ink outlines, mustard tag, coral string, white gloves.
    "money": {"rig": "tag", "tag": "#F6C453", "tag_dark": "#E0A630", "ink": "#2B2230", "string": "#E46C55",
              "glove": "#FFF8EC", "shoe": "#E46C55", "sticker": "#2F7F95", "accent": "#E46C55", "cream": "#2B2230"},
    # the old channel-1 host, kept for reference only
    "money_v2": {"skin": "#1C1F2B", "hoodie": "#F2B63C", "hoodie_dark": "#C98E22", "pants": "#2B2F3D",
              "shoe": "#111319", "rim": "#FFB27A", "cream": "#F6EFE2", "accent": "#FF5B36", "badge": "coin"},
    # channel 2: history — olive field jacket, scarf
    "history": {"skin": "#1E1C1A", "hoodie": "#7C8C4A", "hoodie_dark": "#5D6A35", "pants": "#3A3226",
                "shoe": "#1A1512", "rim": "#FFC98A", "cream": "#F3EBDB", "accent": "#C8553D", "badge": "scarf"},
    # channel 3: science by scale — teal jacket, goggles on the head
    "scale": {"skin": "#171B2A", "hoodie": "#3FB7B0", "hoodie_dark": "#2A8984", "pants": "#252B3E",
              "shoe": "#0F121B", "rim": "#9CC7FF", "cream": "#EEF2FA", "accent": "#FFD166", "badge": "goggles"},
}

POSES = {  # [shoulder, elbow] degrees for left and right arm (0 = hanging down)
    "idle": [[6, -4], [-6, 4]], "hold": [[6, -4], [-24, -86]], "point": [[6, -4], [-96, -4]],
    "shrug": [[38, 96], [-38, -96]], "chin": [[6, -4], [-34, -138]], "wave": [[6, -4], [-158, -24]],
    "present": [[30, 40], [-60, -30]], "hips": [[24, 70], [-24, -70]],
}


def face_parts(cid, o, expr):
    c = o["cream"]
    st = f'stroke="{c}" stroke-width="7" stroke-linecap="round" fill="none"'
    eyes = {
        "neutral": f'<ellipse cx="-28" cy="-432" rx="8" ry="11" fill="{c}"/><ellipse cx="24" cy="-432" rx="8" ry="11" fill="{c}"/>',
        "happy": f'<path d="M-42,-428 Q-28,-446 -14,-428" {st}/><path d="M10,-428 Q24,-446 38,-428" {st}/>',
        "surprised": f'<circle cx="-28" cy="-434" r="12" fill="{c}"/><circle cx="24" cy="-434" r="12" fill="{c}"/>'
                     f'<path d="M-42,-462 Q-28,-472 -14,-462" {st}/><path d="M10,-462 Q24,-472 38,-462" {st}/>',
        "worried": f'<ellipse cx="-28" cy="-430" rx="7" ry="10" fill="{c}"/><ellipse cx="24" cy="-430" rx="7" ry="10" fill="{c}"/>'
                   f'<path d="M-42,-452 L-16,-461" {st}/><path d="M10,-461 L36,-452" {st}/>',
        "thinking": f'<ellipse cx="-20" cy="-438" rx="7" ry="10" fill="{c}"/><ellipse cx="30" cy="-438" rx="7" ry="10" fill="{c}"/>'
                    f'<path d="M16,-464 Q28,-474 40,-464" {st}/>',
        "proud": f'<path d="M-42,-430 Q-28,-422 -14,-430" {st}/><path d="M10,-430 Q24,-422 38,-430" {st}/>',
    }
    mouth = {
        "neutral": f'<path d="M-14,-392 Q0,-384 14,-392" {st}/>',
        "happy": f'<path d="M-22,-398 Q0,-370 24,-398" {st}/><ellipse cx="-44" cy="-402" rx="12" ry="7" fill="{o["accent"]}" opacity=".35"/><ellipse cx="46" cy="-402" rx="12" ry="7" fill="{o["accent"]}" opacity=".35"/>',
        "surprised": f'<ellipse cx="2" cy="-388" rx="11" ry="15" fill="{c}"/>',
        "worried": f'<path d="M-18,-388 Q-9,-396 0,-388 Q9,-380 18,-388" {st}/>',
        "thinking": f'<path d="M-8,-390 L16,-395" {st}/>',
        "proud": f'<path d="M-14,-394 Q8,-380 26,-400" {st}/>',
    }
    e = "".join(f'<g id="{cid}-fe-{k}" opacity="{1 if k == expr else 0}">{v}</g>' for k, v in eyes.items())
    m = "".join(f'<g id="{cid}-fm-{k}" opacity="{1 if k == expr else 0}">{v}</g>' for k, v in mouth.items())
    return f'<g id="{cid}-eyes">{e}</g><g id="{cid}-mouths">{m}</g>'


def prop_svg(kind, x=0, y=0, s=1.0):
    """Props drawn around (0,0); placed at (x,y) with scale s."""
    body = {
        "hotdog": '<path d="M-62,-6 Q-66,-30 -40,-30 L40,-30 Q66,-30 62,-6 Q60,14 40,14 L-40,14 Q-60,14 -62,-6Z" fill="#E7A65B"/>'
                  '<rect x="-70" y="-26" width="140" height="22" rx="11" fill="#C9472F"/>'
                  '<path d="M-56,-16 q8,-8 16,0 t16,0 t16,0 t16,0 t16,0 t16,0 t16,0" stroke="#FFC531" stroke-width="5" fill="none" stroke-linecap="round"/>'
                  '<path d="M-60,-2 Q0,10 60,-2" stroke="#C88A43" stroke-width="4" fill="none"/>',
        "soda": '<path d="M-30,-70 L30,-70 L22,40 L-22,40Z" fill="#F4EEE4"/><rect x="-30" y="-40" width="60" height="26" fill="#D9452F"/>'
                '<rect x="-34" y="-82" width="68" height="14" rx="6" fill="#E5DED2"/><rect x="6" y="-128" width="7" height="50" rx="3" fill="#D9452F" transform="rotate(12 9 -80)"/>',
        "tag": '<rect x="-150" y="-60" width="300" height="120" rx="22" fill="#FFC531"/><circle cx="-112" cy="0" r="14" fill="#1C1F2B"/>'
               '<text x="18" y="22" text-anchor="middle" font-family="PL Display" font-size="66" fill="#1C1F2B">$1.50</text>',
        "card": '<rect x="-120" y="-76" width="240" height="152" rx="16" fill="#20242F" stroke="#F2B63C" stroke-width="5"/>'
                '<rect x="-120" y="-50" width="240" height="22" fill="#F2B63C"/><rect x="-96" y="20" width="90" height="12" rx="6" fill="#8A8F98"/>',
        "popcorn": '<path d="M-48,-40 L48,-40 L36,70 L-36,70Z" fill="#F4EEE4"/>'
                   '<path d="M-40,-40 L-30,70 M-14,-40 L-10,70 M14,-40 L10,70 M40,-40 L30,70" stroke="#D63A2C" stroke-width="12"/>'
                   + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#FFF3D6"/>' for x, y, r in
                             ((-34, -48, 16), (-12, -58, 18), (12, -54, 17), (34, -46, 15), (-22, -70, 14), (4, -76, 15), (24, -68, 13))),
        "coin": '<circle r="26" fill="#FFC531" stroke="#C98E22" stroke-width="5"/><text y="10" text-anchor="middle" font-family="PL Display" font-size="28" fill="#C98E22">$</text>',
    }[kind]
    return f'<g transform="translate({x} {y}) scale({s})">{body}</g>'


def character(cid, outfit="money", expr="neutral", pose="idle", prop=None, flip=False, animated=False):
    o = OUTFITS[outfit]
    pl, pr = POSES[pose]
    rim_clip = f'{cid}-rimclip'
    badge = {
        "coin": f'<circle cx="34" cy="-282" r="15" fill="{o["accent"]}" stroke="#7A2A1A" stroke-width="3"/>'
                f'<text x="34" y="-275" text-anchor="middle" font-family="PL Display" font-size="18" fill="#FFE7C2">$</text>',
        "scarf": f'<path d="M-46,-336 Q0,-312 46,-336 L40,-318 Q0,-298 -40,-318Z" fill="{o["accent"]}"/><rect x="18" y="-322" width="18" height="70" rx="6" fill="{o["accent"]}"/>',
        "goggles": '',
    }[o["badge"]]
    head_extra = ""
    if o["badge"] == "goggles":
        head_extra = (f'<rect x="-82" y="-486" width="164" height="22" rx="11" fill="#2A3045"/>'
                      f'<circle cx="-30" cy="-476" r="22" fill="#9CE4E0" stroke="#2A3045" stroke-width="7"/>'
                      f'<circle cx="30" cy="-476" r="22" fill="#9CE4E0" stroke="#2A3045" stroke-width="7"/>')
    if o["badge"] == "scarf":
        head_extra = (f'<path d="M-84,-452 Q-80,-520 0,-522 Q80,-520 84,-452 Q40,-470 0,-470 Q-40,-470 -84,-452Z" fill="#6B5A3E"/>'
                      f'<rect x="-104" y="-462" width="208" height="16" rx="8" fill="#6B5A3E"/>')
    prop_html = prop_svg(prop, -2, 16, 0.8) if prop else ""
    if prop == "popcorn":  # keep the bucket upright in the "hold" pose
        prop_html = f'<g transform="rotate(110)">{prop_html}</g>'
    arm = lambda side, sh, el, color, front: (
        (f'<g id="{cid}-arm{side}">' if animated else f'<g id="{cid}-arm{side}" transform="rotate({sh} {(-68 if side == "l" else 68)} -326)">') +
        f'<rect x="{-84 if side == "l" else 52}" y="-338" width="32" height="104" rx="16" fill="{color}"/>' +
        (f'<g id="{cid}-fore{side}">' if animated else f'<g id="{cid}-fore{side}" transform="rotate({el} {(-68 if side == "l" else 68)} -234)">') +
        f'<rect x="{-82 if side == "l" else 54}" y="-250" width="28" height="94" rx="14" fill="{color}"/>'
        f'<circle cx="{-68 if side == "l" else 68}" cy="-150" r="19" fill="{o["skin"]}"/>'
        + (f'<g id="{cid}-prop" transform="translate({-68 if side == "l" else 68} -150)">{prop_html}</g>' if front else "")
        + '</g></g>')
    legs = (f'<g id="{cid}-legl"><path d="M-46,-180 h38 v166 q0,12 -12,12 h-14 q-12,0 -12,-12z" fill="{o["pants"]}"/>'
            f'<ellipse cx="-24" cy="-6" rx="36" ry="14" fill="{o["shoe"]}"/></g>'
            f'<g id="{cid}-legr"><path d="M8,-180 h38 v166 q0,12 -12,12 h-14 q-12,0 -12,-12z" fill="{o["pants"]}"/>'
            f'<ellipse cx="30" cy="-6" rx="36" ry="14" fill="{o["shoe"]}"/></g>')
    torso_path = "M-70,-172 C-78,-232 -86,-300 -60,-332 Q0,-352 60,-332 C86,-300 78,-232 70,-172 Q0,-156 -70,-172 Z"
    torso = (f'<g id="{cid}-torso"><path d="{torso_path}" fill="{o["hoodie"]}"/>'
             f'<path d="M-70,-186 Q0,-170 70,-186 L70,-172 Q0,-156 -70,-172Z" fill="{o["hoodie_dark"]}"/>'
             f'<path d="M-40,-240 Q0,-230 40,-240 L44,-200 Q0,-192 -44,-200Z" fill="{o["hoodie_dark"]}" opacity=".55"/>'
             f'<path d="M-14,-330 L-18,-280 M14,-330 L18,-282" stroke="{o["cream"]}" stroke-width="4" stroke-linecap="round" opacity=".8"/>'
             f'{badge}'
             f'<path d="{torso_path}" fill="none" stroke="{o["rim"]}" stroke-width="7" clip-path="url(#{rim_clip})" opacity=".85"/></g>')
    head = (f'<g id="{cid}-head"><ellipse cx="0" cy="-338" rx="76" ry="30" fill="{o["hoodie_dark"]}"/>'
            f'<circle cx="0" cy="-420" r="80" fill="{o["skin"]}"/>'
            f'<circle cx="0" cy="-420" r="80" fill="none" stroke="{o["rim"]}" stroke-width="8" clip-path="url(#{rim_clip})" opacity=".9"/>'
            f'{head_extra}<g id="{cid}-face" transform="translate(12 0)">{face_parts(cid, o, expr)}</g></g>')
    flipattr = ' transform="scale(-1 1)"' if flip else ""
    return (f'<g id="{cid}-root"{flipattr}><defs><clipPath id="{rim_clip}"><rect x="-200" y="-620" width="150" height="640"/></clipPath></defs>'
            f'<ellipse cx="0" cy="2" rx="100" ry="16" fill="rgba(0,0,0,.38)"/>{legs}'
            f'<g id="{cid}-upper">{arm("l", pl[0], pl[1], o["hoodie_dark"], False)}{torso}{head}'
            f'{arm("r", pr[0], pr[1], o["hoodie"], True)}</g></g>')


def tag_face(cid, o, expr):
    """Tag's face: white eyes with ink pupils, ink brows and mouth (no cream line-art on a dark head)."""
    ink, w = o["ink"], "#FFFFFF"
    st = f'stroke="{ink}" stroke-width="7" stroke-linecap="round" fill="none"'
    eye = lambda cx, r=17, px=0, py=0, pr=8: (f'<circle cx="{cx}" cy="-432" r="{r}" fill="{w}" stroke="{ink}" stroke-width="5"/>'
                                               f'<circle cx="{cx + px}" cy="{-432 + py}" r="{pr}" fill="{ink}"/>')
    eyes = {
        "neutral": eye(-30) + eye(28),
        "happy": f'<path d="M-46,-428 Q-30,-450 -14,-428" {st}/><path d="M12,-428 Q28,-450 44,-428" {st}/>',
        "surprised": eye(-30, 21, 0, 0, 7) + eye(28, 21, 0, 0, 7) + f'<path d="M-50,-468 Q-30,-480 -12,-470" {st}/><path d="M10,-470 Q28,-480 48,-468" {st}/>',
        "worried": eye(-30, 16, 0, 3) + eye(28, 16, 0, 3) + f'<path d="M-48,-452 L-16,-462" {st}/><path d="M12,-462 L44,-452" {st}/>',
        "thinking": eye(-30, 16, 6, -6) + eye(28, 16, 6, -6) + f'<path d="M12,-466 Q28,-478 44,-466" {st}/>',
        "proud": f'<path d="M-46,-432 Q-30,-422 -14,-432" {st}/><path d="M12,-432 Q28,-422 44,-432" {st}/>' + f'<path d="M-48,-456 L-14,-452" {st}/><path d="M12,-452 L46,-456" {st}/>',
    }
    mouth = {
        "neutral": f'<path d="M-14,-386 Q0,-378 14,-386" {st}/>',
        "happy": f'<path d="M-24,-392 Q0,-356 26,-392 Z" fill="{ink}"/><path d="M-10,-372 Q2,-364 12,-372" stroke="{o["string"]}" stroke-width="7" stroke-linecap="round" fill="none"/>',
        "surprised": f'<ellipse cx="0" cy="-380" rx="12" ry="16" fill="{ink}"/>',
        "worried": f'<path d="M-20,-382 Q-10,-390 0,-382 Q10,-374 20,-382" {st}/>',
        "thinking": f'<path d="M-8,-384 L18,-390" {st}/>',
        "proud": f'<path d="M-16,-390 Q6,-374 28,-394" {st}/>',
    }
    e = "".join(f'<g id="{cid}-fe-{k}" opacity="{1 if k == expr else 0}">{v}</g>' for k, v in eyes.items())
    m = "".join(f'<g id="{cid}-fm-{k}" opacity="{1 if k == expr else 0}">{v}</g>' for k, v in mouth.items())
    return f'<g id="{cid}-eyes">{e}</g><g id="{cid}-mouths">{m}</g>'


TAG_SX = 100   # Tag's shoulders sit on the tag's edges (the old host's were at 68)


def tag_character(cid, outfit="money", expr="neutral", pose="idle", prop=None, flip=False, animated=False, mirror=False):
    """'Tag', a price tag with a face. Same part ids as character(), so cinema.js animates it unchanged."""
    o = OUTFITS[outfit]
    ink = o["ink"]
    pl, pr = POSES[pose]
    sx = TAG_SX
    prop_html = prop_svg(prop, -2, 16, 0.8) if prop else ""
    if prop == "popcorn":
        prop_html = f'<g transform="rotate(110)">{prop_html}</g>'

    def arm(side, sh, el, front):
        x = -sx if side == "l" else sx
        g0 = f'<g id="{cid}-arm{side}">' if animated else f'<g id="{cid}-arm{side}" transform="rotate({sh} {x} -326)">'
        g1 = f'<g id="{cid}-fore{side}">' if animated else f'<g id="{cid}-fore{side}" transform="rotate({el} {x} -234)">'
        return (g0 + f'<rect x="{x - 8}" y="-334" width="16" height="104" rx="8" fill="{ink}"/>' + g1 +
                f'<rect x="{x - 7}" y="-244" width="14" height="92" rx="7" fill="{ink}"/>'
                f'<circle cx="{x}" cy="-150" r="18" fill="{o["glove"]}" stroke="{ink}" stroke-width="5"/>'
                + (f'<g id="{cid}-prop" transform="translate({x} -150)">{prop_html}</g>' if front else "") + '</g></g>')

    legs = (f'<g id="{cid}-legl"><rect x="-38" y="-186" width="16" height="176" rx="8" fill="{ink}"/>'
            f'<ellipse cx="-38" cy="-8" rx="30" ry="13" fill="{o["shoe"]}" stroke="{ink}" stroke-width="4"/></g>'
            f'<g id="{cid}-legr"><rect x="22" y="-186" width="16" height="176" rx="8" fill="{ink}"/>'
            f'<ellipse cx="38" cy="-8" rx="30" ry="13" fill="{o["shoe"]}" stroke="{ink}" stroke-width="4"/></g>')
    body_path = "M-100,-206 L-100,-468 L-48,-546 L48,-546 L100,-468 L100,-206 Q100,-182 76,-182 L-76,-182 Q-100,-182 -100,-206 Z"
    bars = "".join(f'<rect x="{-52 + x}" y="-296" width="{w}" height="58" fill="{ink}"/>'
                   for x, w in ((0, 6), (10, 3), (17, 8), (29, 3), (36, 5), (45, 9), (58, 3), (65, 6), (75, 3), (82, 8), (94, 4)))
    torso = (f'<g id="{cid}-torso"><rect x="-64" y="-306" width="128" height="88" rx="10" fill="#FFF8EC" stroke="{ink}" stroke-width="4"/>'
             f'{bars}<text x="0" y="-226" text-anchor="middle" font-family="PL Mono" font-size="14" font-weight="700" fill="{ink}"'
             f'{" transform=\"scale(-1 1)\"" if mirror else ""}>PRICE LOGIC</text></g>')
    string = (f'<path d="M0,-506 C-46,-596 74,-650 52,-578 C40,-546 14,-560 8,-520" stroke="{o["string"]}" stroke-width="7" '
              f'stroke-linecap="round" fill="none"/>')
    head = (f'<g id="{cid}-head">{string}'
            f'<path d="{body_path}" fill="{o["tag"]}" stroke="{ink}" stroke-width="7" stroke-linejoin="round"/>'
            f'<path d="M-84,-460 L-38,-530 L-20,-530 L-70,-456 Z" fill="#FFFFFF" opacity=".35"/>'
            f'<circle cx="0" cy="-506" r="14" fill="{ink}"/><circle cx="0" cy="-506" r="14" fill="none" stroke="{o["tag_dark"]}" stroke-width="4"/>'
            f'<circle cx="66" cy="-346" r="20" fill="{o["sticker"]}" stroke="{ink}" stroke-width="4"/>'
            f'<g transform="translate(66 -339){" scale(-1 1)" if mirror else ""}"><text x="0" y="0" text-anchor="middle" font-family="PL Display" font-weight="800" font-size="20" fill="#FFF8EC">%</text></g>'
            f'<g id="{cid}-face">{tag_face(cid, o, expr)}</g></g>')
    flipattr = ' transform="scale(-1 1)"' if flip else ""
    return (f'<g id="{cid}-root" data-sx="{sx}"{flipattr}><ellipse cx="0" cy="2" rx="110" ry="16" fill="rgba(0,0,0,.25)"/>{legs}'
            f'<g id="{cid}-upper">{arm("l", pl[0], pl[1], False)}{head}{torso}{arm("r", pr[0], pr[1], True)}</g></g>')


def char_box(cid, x, y, scale=1.0, flip=False, **kw):
    """Character as an absolutely positioned HTML box; (x, y) = feet position in the layer.
    #cid moves (walk), #cid-inner hops, #cid-flip mirrors with CSS (never animated)."""
    fl = "transform:scaleX(-1);" if flip else ""
    return (f'<div id="{cid}" style="position:absolute;left:{x - 220 * scale:.0f}px;top:{y - 620 * scale:.0f}px;'
            f'width:{440 * scale:.0f}px;height:{640 * scale:.0f}px;">'
            f'<div id="{cid}-inner" style="position:absolute;inset:0"><div style="position:absolute;inset:0;{fl}">'
            f'<svg viewBox="-220 -620 440 640" width="100%" height="100%" overflow="visible">'
            f'{tag_character(cid, mirror=flip, **kw) if OUTFITS[kw.get("outfit", "money")].get("rig") == "tag" else character(cid, **kw)}</svg></div></div></div>')


# ------------------------------------------------------------------ worlds

def _windows(n, x0, w, gap, y, h, warm1="#F6C27A", warm2="#C86F37"):
    out = []
    for i in range(n):
        x = x0 + i * (w + gap)
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="url(#win)"/>'
                   f'<path d="M{x + w / 2},{y} V{y + h} M{x},{y + h * .55} H{x + w}" stroke="#3B2630" stroke-width="7" opacity=".7"/>'
                   f'<circle cx="{x + w / 2}" cy="{y + 46}" r="40" fill="#FFE2A8" opacity=".35"/>'
                   f'<rect x="{x + w / 2 - 3}" y="{y}" width="6" height="34" fill="#3B2630"/>'
                   f'<circle cx="{x + w / 2}" cy="{y + 40}" r="10" fill="#FFF1CF"/>')
    return "".join(out)


def world_street_night(sid, sign_text="FOOD COURT"):
    """Night storefront. Returns {layer: html}. World is centred on x=0 (viewport centre), y from top."""
    sky = (f'<div style="position:absolute;left:-1600px;top:-300px;width:5120px;height:1700px;'
           f'background:linear-gradient(#0A0D19 0%,#151B33 45%,#2B2443 75%,#3A2A3F 100%)"></div>')
    city = "".join(
        f'<rect x="{-2200 + i * 150}" y="{430 - (37 * i * 7919 % 230)}" width="{110 + (i * 53 % 60)}" height="900" fill="#141A2E"/>'
        for i in range(30))
    city += "".join(f'<rect x="{-2160 + (i * 97 % 4200)}" y="{260 + (i * 61 % 300)}" width="10" height="14" fill="#F5C77A" opacity=".55"/>'
                    for i in range(90))
    far = sky + f'<svg style="position:absolute;left:-2240px;top:0" width="4480" height="1080" viewBox="-2240 0 4480 1080">{city}</svg>'

    stripes = "".join(f'<path d="M{-1500 + i * 120},300 h120 v70 q-60,26 -120,0z" fill="{"#B9443E" if i % 2 == 0 else "#EFE3CC"}"/>'
                      for i in range(25))
    mid = (f'<svg style="position:absolute;left:-1700px;top:0" width="3400" height="1080" viewBox="-1700 0 3400 1080">'
           f'<defs><linearGradient id="win" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FAD08A"/><stop offset="1" stop-color="#C76A35"/></linearGradient>'
           f'<radialGradient id="glowS" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#FFD99A" stop-opacity=".55"/><stop offset="1" stop-color="#FFD99A" stop-opacity="0"/></radialGradient></defs>'
           f'<rect x="-1600" y="150" width="3200" height="640" fill="#2A2233"/>'
           f'<rect x="-1600" y="140" width="3200" height="22" fill="#1E1826"/>'
           f'<rect x="-360" y="176" width="720" height="104" rx="14" fill="#1A1420" stroke="#4A3A44" stroke-width="4"/>'
           f'<ellipse cx="0" cy="228" rx="460" ry="120" fill="url(#glowS)"/>'
           f'<text x="0" y="252" text-anchor="middle" font-family="PL Display" font-size="64" fill="#FFE3B0">{sign_text}</text>'
           f'{stripes}{_windows(7, -1490, 330, 90, 400, 330)}'
           f'<rect x="-1600" y="760" width="3200" height="30" fill="#1E1826"/></svg>')
    near = (f'<div style="position:absolute;left:-1700px;top:780px;width:3400px;height:420px;'
            f'background:linear-gradient(#2A2030 0%,#1A1620 60%,#141118 100%)"></div>'
            + "".join(f'<div style="position:absolute;left:{-1490 + i * 420 + 40}px;top:800px;width:250px;height:190px;border-radius:50%;'
                      f'background:radial-gradient(ellipse at 50% 20%,rgba(250,190,110,.30),rgba(250,190,110,0) 70%);filter:blur(6px)"></div>' for i in range(7)) +
            f'<div style="position:absolute;left:-1700px;top:1010px;width:3400px;height:10px;background:#0E0C12"></div>'
            f'<svg style="position:absolute;left:820px;top:120px" width="160" height="900" viewBox="0 0 160 900">'
            f'<rect x="70" y="60" width="16" height="840" fill="#0F0D14"/><rect x="40" y="40" width="80" height="28" rx="10" fill="#0F0D14"/>'
            f'<circle cx="80" cy="80" r="70" fill="#FFD99A" opacity=".18"/><circle cx="80" cy="74" r="14" fill="#FFE9C2"/></svg>')
    bokeh = "".join(
        f'<div style="position:absolute;left:{x}px;top:{y}px;width:{r * 2}px;height:{r * 2}px;border-radius:50%;'
        f'background:radial-gradient(circle,{c} 0%,{c.replace(",1)", ",0)")} 70%);opacity:{op}"></div>'
        for x, y, r, c, op in [(-1150, 120, 90, "rgba(255,190,110,1)", .55), (-980, 330, 60, "rgba(255,220,150,1)", .45),
                               (1010, 90, 110, "rgba(120,170,255,1)", .30), (1180, 400, 70, "rgba(255,160,90,1)", .5),
                               (-1300, 700, 130, "rgba(255,200,120,1)", .45), (1250, 760, 120, "rgba(255,180,100,1)", .45),
                               (-820, 860, 150, "rgba(255,210,140,1)", .30), (700, 900, 160, "rgba(255,170,90,1)", .28)])
    fore = bokeh + '<div style="position:absolute;left:-1240px;top:-100px;width:70px;height:1300px;background:#09080C;border-radius:30px"></div>'
    return {"far": far, "mid": mid, "near": near, "fore": fore}


def frame_page(layers, depths, focus=1.0, cam=(0, 0, 1.0), extra="", W=1920, H=1080, grade=True):
    """A still frame: layers rendered with the same maths as cinema.js (parallax + depth blur)."""
    cx, cy, z = cam
    out = []
    for name, html_ in layers:
        d = depths[name]
        p = 1 / d
        s = 1 + (z - 1) * p
        b = min(16, 13 * abs(p - 1 / focus))
        out.append(f'<div class="L" style="transform:translate({-cx * p * s:.1f}px,{-cy * p * s:.1f}px) scale({s:.4f});'
                   f'filter:{"blur(%.2fpx)" % b if b > .4 else "none"}"><div style="position:absolute;left:{W // 2}px;top:0">{html_}</div></div>')
    fx = ""
    if grade:
        fx = ('<div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 45%,rgba(0,0,0,0) 50%,rgba(0,0,0,.55) 100%)"></div>'
              '<div style="position:absolute;inset:0;mix-blend-mode:soft-light;background:linear-gradient(160deg,rgba(255,170,90,.35),rgba(40,70,140,.35))"></div>'
              '<div class="grain"></div>'
              '<div style="position:absolute;left:0;right:0;top:0;height:64px;background:#000"></div>'
              '<div style="position:absolute;left:0;right:0;bottom:0;height:64px;background:#000"></div>')
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family:'PL Display'; src:url('ARCHIVO'); }}
*{{margin:0;padding:0;box-sizing:border-box}} body{{width:{W}px;height:{H}px;overflow:hidden;background:#000;position:relative}}
.L{{position:absolute;left:0;top:0;width:{W}px;height:{H}px;transform-origin:{W / 2}px {H / 2}px}}
.grain{{position:absolute;inset:0;opacity:.12;mix-blend-mode:overlay;background:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}}
</style></head><body>{"".join(out)}{extra}{fx}</body></html>'''
