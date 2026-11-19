"""Hidden Systems thumbnail heroes: one simple, bold object per system, drawn between Drip and the word slab.

Each hero returns (svg, glow_xy, glow_colors): the object for the 1280x720 thumbnail (Drip sits on the left third,
the word slab on the right third, the floor line at y=600), the point that glows, and the glow's (mid, edge) colours.
look_hidden.thumbnail_page() uses a hero when the script's "system" is listed in HEROES; power and sewer keep their
own cutaway slices. A new system = one small function here + one line in HEROES. Keep heroes readable at 120 px wide:
one object, thick ink outlines, flat palette colours, no text.
"""
import hs_art as A

C, INK = A.C, A.INK
WATER, WATER2, BLUE, BLUE2 = "#7CCBEA", "#2F7FA6", "#2F6FB3", "#24548A"
ORANGE, PIPE, CREAM, STEEL, STEEL2 = C["hat"], "#3E8E5E", C["cream"], C["steel"], C["steel2"]
WATER_GLOW = ("#7CCBEA", "#2F7FA6")
ORANGE_GLOW = ("#FFD9A8", "#F26B1D")


def water():
    """Tap water: a chrome faucet on a green supply pipe, a clear stream falling into a full glass."""
    o = [
        # supply pipe from the wall behind the slab, elbow down to the faucet body
        f'<path d="M800 250 L690 250 L690 300" fill="none" stroke="{INK}" stroke-width="58" stroke-linejoin="round"/>',
        f'<path d="M800 250 L690 250 L690 300" fill="none" stroke="{PIPE}" stroke-width="46" stroke-linejoin="round"/>',
        f'<rect x="652" y="292" width="78" height="40" rx="8" fill="{STEEL}" stroke="{INK}" stroke-width="7"/>',
        # handle
        f'<rect x="676" y="252" width="30" height="44" rx="6" fill="{STEEL2}" stroke="{INK}" stroke-width="6"/>',
        f'<rect x="646" y="236" width="90" height="24" rx="10" fill="{ORANGE}" stroke="{INK}" stroke-width="6"/>',
        # spout curving left and down
        f'<path d="M662 312 L648 312 Q624 312 624 336 L624 352" fill="none" stroke="{INK}" stroke-width="44" stroke-linecap="butt"/>',
        f'<path d="M662 312 L648 312 Q624 312 624 336 L624 352" fill="none" stroke="{STEEL}" stroke-width="32" stroke-linecap="butt"/>',
        # stream
        f'<rect x="613" y="354" width="22" height="150" fill="{WATER}" stroke="{INK}" stroke-width="4"/>',
        # glass: a tall tumbler, full of water, standing on the floor line clear of Drip's body
        f'<path d="M550 422 L702 422 L688 598 L564 598 Z" fill="{C["glass"]}" fill-opacity=".35" stroke="{INK}" stroke-width="8" stroke-linejoin="round"/>',
        f'<path d="M556 480 L696 480 L688 590 L564 590 Z" fill="{WATER}"/>',
        f'<path d="M556 480 Q591 468 626 480 Q661 492 696 480" fill="none" stroke="{CREAM}" stroke-width="5"/>',
        f'<path d="M672 500 L666 576" stroke="{CREAM}" stroke-width="8" stroke-linecap="round" opacity=".8"/>',
        f'<path d="M550 422 L702 422 L688 598 L564 598 Z" fill="none" stroke="{INK}" stroke-width="8" stroke-linejoin="round"/>',
    ]
    return "".join(o), (624, 356), WATER_GLOW


def recycling():
    """Recycling: a blue curbside cart, lid open, a bottle and a box poking out."""
    o = [
        # bottle (behind the lid line)
        f'<path d="M598 300 L598 252 L590 240 L590 214 L618 214 L618 240 L610 252 L610 300 Z" fill="{WATER}" fill-opacity=".9" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>',
        f'<rect x="588" y="200" width="32" height="18" rx="4" fill="{ORANGE}" stroke="{INK}" stroke-width="5"/>',
        # cardboard box
        f'<path d="M626 312 L640 236 L724 250 L712 324 Z" fill="#C89A5B" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>',
        f'<path d="M660 241 L652 318" stroke="#8C6A3A" stroke-width="6"/>',
        # cart body (tapered) with wheels
        f'<path d="M530 300 L740 300 L722 584 L548 584 Z" fill="{BLUE}" stroke="{INK}" stroke-width="8" stroke-linejoin="round"/>',
        f'<rect x="522" y="290" width="226" height="30" rx="8" fill="{BLUE2}" stroke="{INK}" stroke-width="7"/>',
        # open lid flipped back
        f'<path d="M742 296 L790 150 L812 156 L766 302 Z" fill="{BLUE2}" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>',
        # three chasing arrows (simple triangle of arrows) on the front
        f'<g transform="translate(635 450)" fill="none" stroke="{CREAM}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M-44 30 L-8 -34"/><path d="M8 -34 L44 30"/><path d="M34 46 L-34 46"/>'
        f'<path d="M-22 -30 L-8 -34 L-4 -20"/><path d="M38 12 L44 30 L28 34"/><path d="M-20 34 L-34 46 L-20 58"/></g>',
        f'<circle cx="566" cy="596" r="18" fill="{INK}"/><circle cx="566" cy="596" r="8" fill="{STEEL}"/>',
        f'<circle cx="704" cy="596" r="18" fill="{INK}"/><circle cx="704" cy="596" r="8" fill="{STEEL}"/>',
    ]
    return "".join(o), (604, 250), WATER_GLOW


def nine11():
    """911: a building cutaway, one floor lit, a phone glowing on it, signal rings above."""
    floors = 6
    x0, x1, top, bot = 540, 740, 200, 598
    fh = (bot - top) / floors
    o = [f'<rect x="{x0}" y="{top}" width="{x1 - x0}" height="{bot - top}" fill="{C["wall"]}" stroke="{INK}" stroke-width="8"/>']
    lit = 3  # floor index from the top that holds the caller
    for k in range(floors):
        y = top + k * fh
        if k == lit:
            o.append(f'<rect x="{x0 + 4}" y="{y + 4:.0f}" width="{x1 - x0 - 8}" height="{fh - 8:.0f}" fill="{C["glow"]}"/>')
        else:
            for wx in range(x0 + 22, x1 - 30, 46):
                o.append(f'<rect x="{wx}" y="{y + 16:.0f}" width="26" height="{fh - 34:.0f}" fill="{C["room"]}" stroke="{INK}" stroke-width="3"/>')
        if k:
            o.append(f'<line x1="{x0}" y1="{y:.0f}" x2="{x1}" y2="{y:.0f}" stroke="{INK}" stroke-width="6"/>')
    py = top + lit * fh + fh / 2
    o += [  # the phone on the lit floor
        f'<rect x="616" y="{py - 30:.0f}" width="34" height="58" rx="7" fill="{INK}"/>',
        f'<rect x="621" y="{py - 24:.0f}" width="24" height="42" rx="3" fill="{ORANGE}"/>',
        # roof and antenna with signal rings
        f'<rect x="{x0 - 10}" y="{top - 18}" width="{x1 - x0 + 20}" height="22" fill="{C["concrete2"]}" stroke="{INK}" stroke-width="7"/>',
        f'<line x1="700" y1="{top - 18}" x2="700" y2="{top - 92}" stroke="{INK}" stroke-width="8"/>',
        f'<circle cx="700" cy="{top - 96}" r="10" fill="{ORANGE}" stroke="{INK}" stroke-width="5"/>',
    ]
    for r in (30, 54):
        o.append(f'<path d="M{700 - r} {top - 96 - r * .2:.0f} A{r} {r} 0 0 1 {700 + r} {top - 96 - r * .2:.0f}" fill="none" stroke="{ORANGE}" stroke-width="7" stroke-linecap="round"/>')
    return "".join(o), (633, py), ORANGE_GLOW


HEROES = {"water": water, "recycling": recycling, "911": nine11}
