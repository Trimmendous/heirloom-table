#!/usr/bin/env python3
"""Generate every image the app uses. Nothing here is third-party art.

  python3 tools/make_art.py            # build everything that is missing
  python3 tools/make_art.py --force    # rebuild everything
  python3 tools/make_art.py dishes     # rebuild one group (ui, icons, garnish, photos, dishes, channel, ninepatch)

Vector art is written as SVG, rasterised by tools/render.swift (WebKit, macOS system
frameworks), and JPGs are encoded with macOS `sips`. The two 9-patch images are drawn
pixel-by-pixel in pure Python (zlib + struct) because Roku needs the 1px marker border.
Coordinates for baked panels come from data/layout.json so the art always matches the UI.
"""
import json, math, os, random, struct, subprocess, sys, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "roku", "images")
BUILD = os.path.join(ROOT, "tools", ".build")
BIN = os.path.join(ROOT, "tools", ".bin", "render")
L = json.load(open(os.path.join(ROOT, "data", "layout.json")))

GARNISHES = ["lemon", "berries", "chili", "herbs", "apple", "wheat", "spice"]
PHOTOS = ["villa", "farmhouse", "cottage", "bazaar"]
DISH_W, DISH_H = L["recipe"]["dish"]["w"], L["recipe"]["dish"]["h"]
TABLE = "#160f0a"
GS = L["recipe"]["garnish"]["s"]  # garnish art is drawn on a 256 grid and rendered at its largest on-screen size  # colour the dish images fade into; baked under the dish slot too

# ------------------------------------------------------------------ svg helpers
GOLD = """
<linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="#7d5419"/><stop offset=".3" stop-color="#f2d592"/>
  <stop offset=".55" stop-color="#c38e36"/><stop offset=".8" stop-color="#f0cf84"/><stop offset="1" stop-color="#7a5017"/>
</linearGradient>
<linearGradient id="goldH" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#c38e36" stop-opacity="0"/><stop offset=".15" stop-color="#d9a94a"/>
  <stop offset=".5" stop-color="#f2d592"/><stop offset=".85" stop-color="#d9a94a"/><stop offset="1" stop-color="#c38e36" stop-opacity="0"/>
</linearGradient>
<filter id="shadow" x="-10%" y="-10%" width="120%" height="125%">
  <feDropShadow dx="0" dy="8" stdDeviation="9" flood-color="#000" flood-opacity=".65"/>
</filter>
<filter id="soft" x="-20%" y="-20%" width="140%" height="140%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="6"/></filter>
<filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
  <feGaussianBlur in="SourceAlpha" stdDeviation="2.5" result="b"/>
  <feFlood flood-color="#f5c96a" flood-opacity=".45"/><feComposite in2="b" operator="in" result="g"/>
  <feMerge><feMergeNode in="g"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<filter id="mottle" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency=".012" numOctaves="4" seed="7"/>
  <feColorMatrix values="0 0 0 0 .52  0 0 0 0 .33  0 0 0 0 .13  1.5 0 0 0 -.62"/>
</filter>
<filter id="grain" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency=".75" numOctaves="2" seed="11"/>
  <feColorMatrix values="0 0 0 0 .3  0 0 0 0 .2  0 0 0 0 .1  0 0 0 .9 -.32"/>
</filter>
<filter id="crust" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency=".09" numOctaves="3" seed="4"/>
  <feColorMatrix values="0 0 0 0 .45  0 0 0 0 .22  0 0 0 0 .05  1.6 0 0 0 -.7"/>
</filter>
<radialGradient id="parch" cx=".5" cy=".45" r=".75">
  <stop offset="0" stop-color="#f7ebcb"/><stop offset=".6" stop-color="#ecd7a6"/><stop offset="1" stop-color="#d4b06f"/>
</radialGradient>
<radialGradient id="burn" cx=".5" cy=".5" r=".72">
  <stop offset=".62" stop-color="#6e3d14" stop-opacity="0"/><stop offset=".92" stop-color="#6e3d14" stop-opacity=".38"/>
  <stop offset="1" stop-color="#4a250a" stop-opacity=".7"/>
</radialGradient>
<radialGradient id="vign" cx=".5" cy=".5" r=".7">
  <stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".55"/>
</radialGradient>
"""

_uid = [0]


def uid(p="u"):
    _uid[0] += 1
    return "%s%d" % (p, _uid[0])


def svg(w, h, body, defs="", style=""):
    fonts = "".join(
        "@font-face{font-family:'%s';src:url('file://%s/roku/fonts/%s');}" % (n, ROOT, f)
        for n, f in (("Script", L["fonts"]["script"]), ("Serif", L["fonts"]["serif"]),
                     ("SerifBold", L["fonts"]["serifBold"]), ("Hand", L["fonts"]["hand"])))
    return ("<!doctype html><html><head><meta charset='utf-8'><style>%s html,body{margin:0;padding:0;"
            "background:transparent;overflow:hidden}svg{display:block}%s</style></head><body>"
            "<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' viewBox='0 0 %d %d'>"
            "<defs>%s%s</defs>%s</svg></body></html>") % (fonts, style, w, h, w, h, GOLD, defs, body)


def torn_path(x, y, w, h, rnd, amp=3.5, step=9, nick=0.06):
    pts = []

    def jit():
        j = rnd.uniform(-amp, amp)
        if rnd.random() < nick:
            j += amp * rnd.uniform(1.2, 2.4)
        return j

    n = max(2, int(w / step))
    for i in range(n + 1):
        pts.append((x + w * i / n, y + jit()))
    m = max(2, int(h / step))
    for i in range(1, m + 1):
        pts.append((x + w - jit(), y + h * i / m))
    for i in range(n - 1, -1, -1):
        pts.append((x + w * i / n, y + h - jit()))
    for i in range(m - 1, 0, -1):
        pts.append((x + jit(), y + h * i / m))
    return "M" + " L".join("%.1f,%.1f" % p for p in pts) + "Z"


def parchment(x, y, w, h, seed, shadow=True, grain=.55):
    rnd = random.Random(seed)
    d = torn_path(x, y, w, h, rnd)
    cid = uid("clip")
    return f"""
<clipPath id="{cid}"><path d="{d}"/></clipPath>
<path d="{d}" fill="#e7d09c" {'filter="url(#shadow)"' if shadow else ''}/>
<g clip-path="url(#{cid})">
  <rect x="{x-6}" y="{y-6}" width="{w+12}" height="{h+12}" fill="url(#parch)"/>
  <rect x="{x-6}" y="{y-6}" width="{w+12}" height="{h+12}" filter="url(#mottle)" opacity=".5"/>
  <rect x="{x-6}" y="{y-6}" width="{w+12}" height="{h+12}" filter="url(#grain)" opacity="{grain}"/>
  <rect x="{x-6}" y="{y-6}" width="{w+12}" height="{h+12}" fill="url(#burn)"/>
</g>
<path d="{d}" fill="none" stroke="#8c5f2c" stroke-opacity=".55" stroke-width="1.4"/>"""


FLOURISH = """
<g fill="none" stroke="url(#gold)" stroke-linecap="round">
  <path d="M14 196 C14 96 58 36 158 20" stroke-width="3"/>
  <path d="M158 20 C184 16 196 34 186 48 C177 60 159 55 162 41 C164 33 173 32 176 38" stroke-width="2.4"/>
  <path d="M14 196 C10 222 30 232 42 222 C52 213 45 198 34 202 C28 205 29 213 34 214" stroke-width="2.4"/>
  <path d="M42 128 C44 82 74 52 116 48 C138 46 146 64 134 74 C124 82 110 74 116 64" stroke-width="2"/>
  <path d="M30 30 L70 30 M30 30 L30 70" stroke-width="2"/>
  <path d="M66 108 C82 98 92 86 96 70" stroke-width="1.6"/>
</g>
<g fill="url(#gold)">
  <ellipse cx="86" cy="58" rx="12" ry="4.5" transform="rotate(-38 86 58)"/>
  <ellipse cx="58" cy="88" rx="12" ry="4.5" transform="rotate(-52 58 88)"/>
  <ellipse cx="112" cy="30" rx="10" ry="4" transform="rotate(-18 112 30)"/>
  <ellipse cx="22" cy="140" rx="10" ry="4" transform="rotate(-78 22 140)"/>
  <circle cx="30" cy="30" r="5"/><circle cx="96" cy="96" r="3.2"/>
</g>"""


def frame(w, h):
    out = [f'<rect x="22" y="22" width="{w-44}" height="{h-44}" fill="none" stroke="url(#gold)" stroke-width="3" rx="6"/>',
           f'<rect x="33" y="33" width="{w-66}" height="{h-66}" fill="none" stroke="#c9963f" stroke-opacity=".55" stroke-width="1.2" rx="4"/>']
    for sx, sy, tx, ty in ((1, 1, 6, 6), (-1, 1, w - 6, 6), (1, -1, 6, h - 6), (-1, -1, w - 6, h - 6)):
        out.append(f'<g transform="translate({tx} {ty}) scale({sx} {sy})" filter="url(#glow)">{FLOURISH}</g>')
    return "\n".join(out)


def background(w, h, seed=1):
    return f"""
<radialGradient id="bgg" cx=".42" cy=".38" r=".8"><stop offset="0" stop-color="#36241a"/><stop offset=".55" stop-color="#211510"/><stop offset="1" stop-color="#0f0906"/></radialGradient>
<filter id="bgn" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".006 .009" numOctaves="4" seed="{seed}"/>
<feColorMatrix values="0 0 0 0 .05  0 0 0 0 .03  0 0 0 0 .02  1.8 0 0 0 -.8"/></filter>
<filter id="bgw" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".012" numOctaves="2" seed="{seed+5}"/>
<feColorMatrix values="0 0 0 0 .55  0 0 0 0 .34  0 0 0 0 .16  1.2 0 0 0 -.62"/></filter>
<pattern id="damask" width="120" height="120" patternUnits="userSpaceOnUse">
  <g fill="none" stroke="#c9963f" stroke-width="1.2" opacity=".09">
   <path d="M60 10 C80 30 80 50 60 60 C40 50 40 30 60 10 Z M60 60 C80 70 80 90 60 110 C40 90 40 70 60 60Z M10 60 C30 40 50 40 60 60 C50 80 30 80 10 60Z M110 60 C90 40 70 40 60 60 C70 80 90 80 110 60Z"/>
  </g>
</pattern>""", f"""
<rect width="{w}" height="{h}" fill="url(#bgg)"/>
<rect width="{w}" height="{h}" filter="url(#bgw)" opacity=".22"/>
<rect width="{w}" height="{h}" fill="url(#damask)"/>
<rect width="{w}" height="{h}" filter="url(#bgn)"/>
<rect width="{w}" height="{h}" fill="url(#vign)"/>"""


def ornament_rule(x1, x2, y, color="url(#goldH)", diamond="#b8862e", width=2):
    cx = (x1 + x2) / 2
    return (f'<rect x="{x1}" y="{y-width/2}" width="{x2-x1}" height="{width}" fill="{color}"/>'
            f'<path d="M{cx-9} {y} L{cx} {y-6} L{cx+9} {y} L{cx} {y+6}Z" fill="{diamond}"/>'
            f'<circle cx="{cx-18}" cy="{y}" r="2.4" fill="{diamond}"/><circle cx="{cx+18}" cy="{y}" r="2.4" fill="{diamond}"/>')


# ------------------------------------------------------------------ screens
def ui_jobs():
    W, H = 1920, 1080
    jobs = []
    d, b = background(W, H, 3)
    R = L["recipe"]
    dish = R["dish"]
    slot = (f'<filter id="feather" x="-30%" y="-30%" width="160%" height="160%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="22"/></filter>'
            f'<rect x="{dish["x"]-34}" y="{dish["y"]-30}" width="{dish["w"]+68}" height="{dish["h"]+60}" rx="60" fill="{TABLE}" filter="url(#feather)"/>'
            f'<rect x="{dish["x"]-4}" y="{dish["y"]-4}" width="{dish["w"]+8}" height="{dish["h"]+8}" rx="20" fill="{TABLE}" filter="url(#soft)"/>')
    tc, ic, nc = R["titleCard"], R["ingCard"], R["noteCard"]
    meta = R["meta"]
    divs = "".join(f'<line x1="{meta["x"]+meta["colW"]*k-6}" y1="{meta["y"]+6}" x2="{meta["x"]+meta["colW"]*k-6}" '
                   f'y2="{meta["y"]+96}" stroke="#8c5f2c" stroke-opacity=".5" stroke-width="1.5"/>' for k in (1, 2, 3))
    st = R["steps"]
    body = b + slot + frame(W, H) + parchment(tc["x"], tc["y"], tc["w"], tc["h"], 21) \
        + parchment(ic["x"], ic["y"], ic["w"], ic["h"], 22) + parchment(nc["x"], nc["y"], nc["w"], nc["h"], 23) \
        + ornament_rule(tc["x"] + 140, tc["x"] + tc["w"] - 140, meta["y"] - 10, "#9c6f37", "#9c6f37", 1.4) \
        + divs \
        + ornament_rule(R["ingHeader"]["x"] - 10, ic["x"] + ic["w"] - 34, R["ingList"]["y"] - 14, "#9c6f37", "#9c6f37", 1.4) \
        + ornament_rule(st["x"] + 4, st["x"] + st["w"] - 20, st["y"] - 14) \
        + ornament_rule(R["noteHeader"]["x"], nc["x"] + nc["w"] - 40, R["note"]["y"] - 4, "#9c6f37", "#9c6f37", 1.2)
    jobs.append(("ui/recipe_bg.jpg", svg(W, H, body, d), W, H, 66))

    d, b = background(W, H, 5)
    T = L["home"]["title"]
    body = b + frame(W, H) + ornament_rule(560, 1360, L["home"]["tagline"]["y"] + 50)
    jobs.append(("ui/home_bg.jpg", svg(W, H, body, d), W, H, 72))

    d, b = background(W, H, 9)
    s = L["cook"]["sheet"]
    body = b + frame(W, H) + parchment(s["x"], s["y"], s["w"], s["h"], 31, grain=.3) \
        + ornament_rule(s["x"] + 300, s["x"] + s["w"] - 300, L["cook"]["counter"]["y"] + 56, "#9c6f37", "#9c6f37", 1.6)
    jobs.append(("ui/cook_bg.jpg", svg(W, H, body, d), W, H, 58))
    return jobs


# ------------------------------------------------------------------ icons
INK = "#3a2414"


def icon_jobs():
    j = []
    s = 46
    ico = {
        "clock": f'<circle cx="23" cy="23" r="18" fill="none" stroke="{INK}" stroke-width="3"/><path d="M23 12 V23 L31 28" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/><circle cx="23" cy="23" r="2.2" fill="{INK}"/>',
        "pot": f'<path d="M8 18 H38 V34 Q38 40 32 40 H14 Q8 40 8 34Z" fill="none" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/><path d="M4 20 H8 M38 20 H42 M6 15 H40" stroke="{INK}" stroke-width="3" stroke-linecap="round"/><path d="M19 15 Q23 9 27 15" fill="none" stroke="{INK}" stroke-width="3"/><path d="M17 6 q2 -2 0 -4 M23 7 q2 -2 0 -4 M29 6 q2 -2 0 -4" fill="none" stroke="{INK}" stroke-width="1.8" stroke-linecap="round"/>',
        "utensils": f'<path d="M12 5 V17 Q12 22 16 22 Q20 22 20 17 V5 M16 5 V41" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/><path d="M31 41 V5 Q38 9 38 21 Q38 25 31 25" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',
        "hat": f'<path d="M12 30 Q4 28 5 19 Q7 11 15 13 Q17 5 23 5 Q30 5 31 13 Q39 11 41 19 Q42 28 34 30Z" fill="none" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/><path d="M12 30 V40 H34 V30 M12 35 H34" fill="none" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>',
        "heart": f'<path d="M23 40 C10 30 4 23 6 15 C8 8 18 7 23 15 C28 7 38 8 40 15 C42 23 36 30 23 40Z" fill="none" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>',
    }
    for k, v in ico.items():
        j.append(("ui/icon_%s.png" % k, svg(s, s, v), s, s, None))
    bx = L["recipe"]["ingList"]["box"]
    box = f'<rect x="3" y="3" width="{bx-6}" height="{bx-6}" rx="3" fill="#fbf3dc" fill-opacity=".5" stroke="{INK}" stroke-width="2.4"/>'
    j.append(("ui/check_off.png", svg(bx, bx, box), bx, bx, None))
    j.append(("ui/check_on.png", svg(bx, bx, box + '<path d="M7 14 L12 20 L23 6" fill="none" stroke="#7a2e14" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/>'), bx, bx, None))
    for name, s in (("ring", L["recipe"]["steps"]["ring"]), ("ring_lg", L["cook"]["ring"]["s"])):
        r = s / 2
        ring = (f'<radialGradient id="rf"><stop offset="0" stop-color="#4a2c15"/><stop offset="1" stop-color="#1e110a"/></radialGradient>'
                f'<circle cx="{r}" cy="{r}" r="{r-3}" fill="url(#rf)" stroke="url(#gold)" stroke-width="{s/16:.1f}"/>'
                f'<circle cx="{r}" cy="{r}" r="{r-3-s/10:.1f}" fill="none" stroke="#d9a94a" stroke-opacity=".6" stroke-width="1.2"/>')
        j.append(("ui/%s.png" % name, svg(s, s, ring), s, s, None))
    j.append(("ui/chev_up.png", svg(30, 20, '<path d="M4 16 L15 5 L26 16" fill="none" stroke="#d9a94a" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>'), 30, 20, None))
    j.append(("ui/chev_down.png", svg(30, 20, '<path d="M4 4 L15 15 L26 4" fill="none" stroke="#d9a94a" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>'), 30, 20, None))
    j.append(("ui/chev_up_ink.png", svg(30, 20, f'<path d="M4 16 L15 5 L26 16" fill="none" stroke="{INK}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>'), 30, 20, None))
    j.append(("ui/chev_down_ink.png", svg(30, 20, f'<path d="M4 4 L15 15 L26 4" fill="none" stroke="{INK}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>'), 30, 20, None))
    ds = L["cook"]["dots"]["s"]
    j.append(("ui/dot_on.png", svg(ds, ds, f'<circle cx="{ds/2}" cy="{ds/2}" r="{ds/2-2}" fill="#9c6420" stroke="#6b3e12" stroke-width="1.5"/>'), ds, ds, None))
    j.append(("ui/dot_off.png", svg(ds, ds, f'<circle cx="{ds/2}" cy="{ds/2}" r="{ds/2-3}" fill="none" stroke="#9c6f37" stroke-width="2"/>'), ds, ds, None))
    return j


# ------------------------------------------------------------------ garnish
def leaf(cx, cy, ln, wd, ang, c1="#5f7f2e", c2="#3b5a1c", vein="#a9c27a"):
    g = uid("lf")
    return (f'<linearGradient id="{g}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient>'
            f'<g transform="translate({cx} {cy}) rotate({ang})"><path d="M0 0 Q{wd} {-ln*.45} 0 {-ln} Q{-wd} {-ln*.45} 0 0Z" fill="url(#{g})"/>'
            f'<path d="M0 0 L0 {-ln*.92}" stroke="{vein}" stroke-width="1.3" opacity=".7"/></g>')


def lemon(cx, cy, rx, ry, ang):
    g = uid("lm")
    return (f'<radialGradient id="{g}" cx=".38" cy=".35" r=".7"><stop offset="0" stop-color="#fff5a8"/><stop offset=".45" stop-color="#f5cf22"/><stop offset="1" stop-color="#c98f0c"/></radialGradient>'
            f'<g transform="translate({cx} {cy}) rotate({ang})"><path d="M{-rx} 0 Q{-rx} {-ry} 0 {-ry} Q{rx} {-ry} {rx} 0 Q{rx} {ry} 0 {ry} Q{-rx} {ry} {-rx} 0Z M{rx} 0 l8 -2 l0 4Z M{-rx} 0 l-7 -2 l0 4Z" fill="url(#{g})" stroke="#a87408" stroke-width="1"/>'
            f'<ellipse cx="{-rx*.3}" cy="{-ry*.45}" rx="{rx*.3}" ry="{ry*.18}" fill="#fff" opacity=".35"/></g>')


def lemon_slice(cx, cy, r, half=False):
    segs = "".join(f'<line x1="0" y1="0" x2="{r*.82*math.cos(a):.1f}" y2="{r*.82*math.sin(a):.1f}" stroke="#fbf3c4" stroke-width="2.2"/>'
                   for a in [i * math.pi / 5 for i in range(10)])
    g = uid("ls")
    clip = f'<clipPath id="{g}c"><rect x="{-r-2}" y="{-r-2}" width="{2*r+4}" height="{r+2}"/></clipPath>' if half else ""
    return (f'{clip}<radialGradient id="{g}"><stop offset="0" stop-color="#fff6b0"/><stop offset="1" stop-color="#f2cc2c"/></radialGradient>'
            f'<g transform="translate({cx} {cy})" {"clip-path=url(#%sc)" % g if half else ""}><circle r="{r}" fill="#f0c419" stroke="#c9960c" stroke-width="1.5"/>'
            f'<circle r="{r*.88}" fill="#fdf8dc"/><circle r="{r*.82}" fill="url(#{g})"/>{segs}<circle r="{r*.1}" fill="#fbf3c4"/></g>')


def blossom(cx, cy, r):
    pet = "".join(f'<ellipse cx="0" cy="{-r*.55}" rx="{r*.32}" ry="{r*.55}" fill="#fbf8f0" stroke="#d8d0bc" stroke-width=".8" transform="rotate({a})"/>' for a in range(0, 360, 72))
    return f'<g transform="translate({cx} {cy})">{pet}<circle r="{r*.22}" fill="#e7b33a"/></g>'


def berry(cx, cy, r):
    g = uid("bb")
    return (f'<radialGradient id="{g}" cx=".35" cy=".3" r=".75"><stop offset="0" stop-color="#8f9ad6"/><stop offset=".5" stop-color="#3e4a96"/><stop offset="1" stop-color="#1b2050"/></radialGradient>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#{g})"/><path d="M{cx-r*.28} {cy-r*.28} l{r*.28} {r*.12} l{r*.28} {-r*.12}" stroke="#1b1f45" stroke-width="1.6" fill="none"/>'
            f'<circle cx="{cx-r*.35}" cy="{cy-r*.4}" r="{r*.18}" fill="#fff" opacity=".35"/>')


def raspberry(cx, cy, r, rnd):
    out = []
    for i in range(16):
        a = rnd.uniform(0, math.tau)
        d = rnd.uniform(0, r * .7)
        out.append(f'<circle cx="{cx+d*math.cos(a):.1f}" cy="{cy+d*math.sin(a):.1f}" r="{r*.32:.1f}" fill="#c4213c" stroke="#7d0f22" stroke-width=".8"/>'
                   f'<circle cx="{cx+d*math.cos(a)-r*.08:.1f}" cy="{cy+d*math.sin(a)-r*.1:.1f}" r="{r*.08:.1f}" fill="#ffb3c0" opacity=".7"/>')
    return "".join(out)


def chili(x, y, ln, ang, c="#c4221a"):
    g = uid("ch")
    return (f'<linearGradient id="{g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff6a4a"/><stop offset=".4" stop-color="{c}"/><stop offset="1" stop-color="#6e0a08"/></linearGradient>'
            f'<g transform="translate({x} {y}) rotate({ang})"><path d="M0 -9 C{ln*.4} -14 {ln*.8} -6 {ln} 10 C{ln*.75} 2 {ln*.4} 8 0 9Z" fill="url(#{g})"/>'
            f'<path d="M4 -5 C{ln*.4} -9 {ln*.7} -4 {ln*.85} 4" stroke="#fff" stroke-opacity=".35" stroke-width="2" fill="none"/>'
            f'<path d="M2 -8 Q-8 -10 -12 -2 Q-8 4 2 8Z" fill="#4f7a22"/><path d="M-10 -2 Q-20 -4 -24 -14" stroke="#4f7a22" stroke-width="4" fill="none" stroke-linecap="round"/></g>')


def apple(cx, cy, r, c1="#e0473a", c2="#8e1a18"):
    g = uid("ap")
    return (f'<radialGradient id="{g}" cx=".35" cy=".35" r=".8"><stop offset="0" stop-color="#ff9a7a"/><stop offset=".35" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></radialGradient>'
            f'<g transform="translate({cx} {cy})"><path d="M0 {-r*.7} C{r*.5} {-r*1.1} {r*1.1} {-r*.8} {r} 0 C{r*.95} {r*.75} {r*.45} {r} 0 {r*.85} C{-r*.45} {r} {-r*.95} {r*.75} {-r} 0 C{-r*1.1} {-r*.8} {-r*.5} {-r*1.1} 0 {-r*.7}Z" fill="url(#{g})"/>'
            f'<path d="M0 {-r*.7} Q{r*.05} {-r*1.05} {r*.18} {-r*1.25}" stroke="#5a3a1a" stroke-width="{r*.09:.1f}" fill="none" stroke-linecap="round"/>'
            f'<ellipse cx="{-r*.45}" cy="{-r*.3}" rx="{r*.18}" ry="{r*.3}" fill="#fff" opacity=".28" transform="rotate(20 {-r*.45} {-r*.3})"/></g>')


def wheat(x, y, ln, ang):
    grains = []
    for i in range(9):
        t = 0.38 + i * 0.07
        gy = -ln * t
        grains.append(f'<ellipse cx="-6" cy="{gy:.1f}" rx="5" ry="10" transform="rotate(-28 -6 {gy:.1f})" fill="#d9a548" stroke="#8a5e1c" stroke-width=".8"/>'
                      f'<ellipse cx="6" cy="{gy-4:.1f}" rx="5" ry="10" transform="rotate(28 6 {gy-4:.1f})" fill="#e6b85c" stroke="#8a5e1c" stroke-width=".8"/>'
                      f'<line x1="-8" y1="{gy-8:.1f}" x2="-16" y2="{gy-26:.1f}" stroke="#c99a48" stroke-width="1"/>'
                      f'<line x1="8" y1="{gy-12:.1f}" x2="16" y2="{gy-30:.1f}" stroke="#c99a48" stroke-width="1"/>')
    return (f'<g transform="translate({x} {y}) rotate({ang})"><path d="M0 0 L0 {-ln*1.05}" stroke="#b88a3c" stroke-width="3"/>'
            + "".join(grains) + f'<ellipse cx="0" cy="{-ln*1.04:.1f}" rx="4.5" ry="10" fill="#e6b85c" stroke="#8a5e1c" stroke-width=".8"/></g>')


def cinnamon(x, y, ln, ang):
    return (f'<g transform="translate({x} {y}) rotate({ang})"><rect x="0" y="-9" width="{ln}" height="18" rx="5" fill="#8a4b22"/>'
            f'<rect x="0" y="-9" width="{ln}" height="7" rx="3" fill="#a8622e"/><path d="M6 -2 H{ln-6} M10 4 H{ln-12}" stroke="#5e2f12" stroke-width="1.5"/>'
            f'<ellipse cx="{ln}" cy="0" rx="5" ry="9" fill="#6e3615"/><path d="M{ln-2} -5 a5 5 0 1 0 4 5" stroke="#c48552" stroke-width="1.5" fill="none"/></g>')


def star_anise(cx, cy, r):
    pts = "".join(f'<g transform="rotate({a})"><path d="M0 0 Q{r*.22} {-r*.5} 0 {-r} Q{-r*.22} {-r*.5} 0 0Z" fill="#7a3a16" stroke="#3e1a08" stroke-width="1"/>'
                  f'<ellipse cx="0" cy="{-r*.5}" rx="{r*.07}" ry="{r*.16}" fill="#c9883a"/></g>' for a in range(0, 360, 45))
    return f'<g transform="translate({cx} {cy})">{pts}<circle r="{r*.12}" fill="#4a200a"/></g>'


def cardamom(cx, cy, ang):
    return (f'<g transform="translate({cx} {cy}) rotate({ang})"><ellipse rx="13" ry="7.5" fill="#9bb25a" stroke="#5f7430" stroke-width="1.2"/>'
            f'<path d="M-11 0 H11 M-9 -3 Q0 -6 9 -3" stroke="#6f8a35" stroke-width="1" fill="none"/></g>')


def basil(cx, cy, s, ang):
    return leaf(cx, cy, 46 * s, 22 * s, ang, "#4f8a2a", "#2d5e16", "#9fd07a")


def thyme(x, y, ln, ang):
    lv = "".join(f'<ellipse cx="{(-5 if i % 2 else 5)}" cy="{-ln*i/12:.1f}" rx="4.5" ry="2.4" fill="#6c8a3c" transform="rotate({-30 if i % 2 else 30} {(-5 if i % 2 else 5)} {-ln*i/12:.1f})"/>' for i in range(1, 12))
    return f'<g transform="translate({x} {y}) rotate({ang})"><path d="M0 0 Q3 {-ln/2} 0 {-ln}" stroke="#6b5233" stroke-width="2" fill="none"/>{lv}</g>'


def garnish_svg(name):
    rnd = random.Random(name)
    S = 256
    if name == "lemon":
        b = (leaf(66, 150, 84, 26, -60) + leaf(140, 74, 80, 24, 20) + leaf(186, 160, 62, 20, 110, "#6b8f34") +
             lemon(122, 142, 62, 46, -24) + lemon_slice(70, 198, 40) + blossom(166, 86, 24) + blossom(84, 98, 17))
    elif name == "berries":
        b = leaf(70, 120, 80, 26, -50, "#5d8a36") + leaf(176, 96, 78, 24, 40, "#5d8a36") + raspberry(176, 168, 26, rnd) + raspberry(100, 186, 22, rnd)
        for (x, y, r) in ((122, 132, 22), (150, 120, 18), (140, 158, 20), (104, 150, 17), (162, 200, 16), (130, 192, 18), (82, 124, 14)):
            b += berry(x, y, r)
    elif name == "chili":
        b = (leaf(80, 130, 96, 22, -40, "#4d6f2a", "#2f4c18") + leaf(176, 122, 90, 20, 50, "#4d6f2a", "#2f4c18") +
             chili(60, 150, 150, -18) + chili(78, 188, 136, -38, "#d5361c") + chili(110, 92, 118, 24, "#a8180f"))
    elif name == "herbs":
        b = thyme(86, 230, 170, -22) + thyme(170, 232, 150, 26)
        for (x, y, s, a) in ((128, 200, 1.5, 0), (128, 200, 1.3, -55), (128, 200, 1.3, 55), (128, 150, 1.0, -35), (128, 150, 1.0, 35), (128, 112, .8, 0)):
            b += basil(x, y, s, a)
        b += '<path d="M128 236 L128 110" stroke="#3f6b20" stroke-width="4"/>'
    elif name == "apple":
        b = (leaf(150, 70, 70, 24, 40) + apple(118, 150, 70) +
             '<g transform="translate(188 196) rotate(-18)"><path d="M-46 0 A46 40 0 0 1 46 0Z" fill="#f6ecd0" stroke="#c43a2c" stroke-width="5"/>'
             '<ellipse cx="-8" cy="-14" rx="4" ry="7" fill="#5a3a1a"/><ellipse cx="8" cy="-14" rx="4" ry="7" fill="#5a3a1a"/></g>')
    elif name == "wheat":
        b = wheat(96, 238, 190, -24) + wheat(128, 240, 200, -4) + wheat(160, 238, 186, 18) + \
            '<path d="M96 210 Q128 200 162 212" stroke="#8a5e1c" stroke-width="5" fill="none"/>'
    elif name == "spice":
        b = (cinnamon(40, 150, 170, -24) + cinnamon(54, 182, 160, -12) + star_anise(170, 90, 48) + star_anise(96, 214, 32) +
             cardamom(176, 186, 30) + cardamom(200, 160, -40) + cardamom(150, 214, 70))
    else:
        raise KeyError(name)
    k = GS / S
    return svg(GS, GS, f'<g transform="scale({k:.4f})" filter="url(#shadow)">{b}</g>')


# ------------------------------------------------------------------ vintage photos
def photo_svg(name):
    W, H = L["recipe"]["photo"]["w"], L["recipe"]["photo"]["h"]
    rnd = random.Random(name)
    iw, ih = 170, 128
    sky = (f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e9d4a6"/><stop offset="1" stop-color="#c9a46c"/></linearGradient>'
           f'<rect width="{iw}" height="{ih}" fill="url(#sky)"/>')
    D, M, Lt = "#3d2a17", "#7a5a36", "#a8855a"
    if name == "villa":
        sc = (f'<path d="M0 82 Q40 60 90 72 T170 64 V128 H0Z" fill="{Lt}"/><path d="M0 100 Q60 84 170 96 V128 H0Z" fill="{M}"/>'
              f'<rect x="70" y="52" width="46" height="30" fill="#d6bb8a"/><path d="M66 54 L93 40 L120 54Z" fill="{M}"/>'
              f'<rect x="78" y="62" width="6" height="8" fill="{D}"/><rect x="92" y="62" width="6" height="8" fill="{D}"/><rect x="104" y="62" width="6" height="8" fill="{D}"/>'
              + "".join(f'<ellipse cx="{x}" cy="{y}" rx="5" ry="{h}" fill="{D}"/>' for x, y, h in ((30, 64, 22), (44, 70, 18), (140, 60, 24), (152, 68, 18), (60, 76, 12)))
              + "".join(f'<path d="M{x} 128 L{x+22} 100" stroke="{D}" stroke-width="1" opacity=".5"/>' for x in range(-20, 170, 14)))
    elif name == "farmhouse":
        sc = (f'<path d="M0 90 Q80 78 170 88 V128 H0Z" fill="{Lt}"/><rect x="34" y="56" width="58" height="40" fill="{M}"/>'
              f'<path d="M28 58 L63 30 L98 58Z" fill="{D}"/><rect x="56" y="74" width="14" height="22" fill="{D}"/>'
              f'<rect x="100" y="66" width="30" height="30" fill="#c9a876"/><path d="M96 68 L115 52 L134 68Z" fill="{M}"/>'
              f'<circle cx="150" cy="54" r="20" fill="{D}"/><rect x="148" y="60" width="4" height="34" fill="{D}"/>'
              + "".join(f'<path d="M0 {100+i*7} Q85 {94+i*7} 170 {100+i*7}" stroke="{M}" stroke-width="1.5" fill="none"/>' for i in range(4)))
    elif name == "cottage":
        sc = (f'<path d="M0 86 Q70 70 170 84 V128 H0Z" fill="{Lt}"/><rect x="50" y="58" width="70" height="38" fill="#b7976a"/>'
              f'<path d="M44 62 Q85 26 126 62Z" fill="{D}"/><rect x="100" y="34" width="9" height="20" fill="{M}"/>'
              f'<path d="M104 30 q8 -8 2 -14 q-6 -6 4 -14" stroke="#efe2c4" stroke-width="5" fill="none" opacity=".7"/>'
              f'<rect x="78" y="74" width="14" height="22" fill="{D}"/><rect x="58" y="70" width="12" height="10" fill="{D}"/><rect x="100" y="70" width="12" height="10" fill="{D}"/>'
              + "".join(f'<ellipse cx="{x}" cy="104" rx="9" ry="5" fill="{M}" stroke="{D}" stroke-width=".8"/>' for x in range(0, 180, 16)))
    elif name == "bazaar":
        sc = (f'<rect x="0" y="40" width="170" height="88" fill="#b8956a"/>'
              + "".join(f'<path d="M{x} 128 V74 Q{x} 50 {x+17} 50 Q{x+34} 50 {x+34} 74 V128Z" fill="{D}"/>' for x in (6, 66, 126))
              + f'<path d="M60 40 Q85 6 110 40Z" fill="{M}"/><rect x="83" y="2" width="3" height="10" fill="{M}"/>'
              + "".join(f'<line x1="{x}" y1="50" x2="{x}" y2="{62+rnd.randint(0,8)}" stroke="{D}" stroke-width="1"/><ellipse cx="{x}" cy="{66+rnd.randint(0,6)}" rx="4" ry="6" fill="#e0b860"/>' for x in (44, 56, 104, 118))
              + f'<rect x="0" y="112" width="170" height="16" fill="{M}"/>')
    else:
        raise KeyError(name)
    body = f"""
<filter id="sep"><feColorMatrix type="matrix" values=".45 .8 .2 0 .04  .36 .68 .16 0 .02  .24 .46 .1 0 0  0 0 0 1 0"/></filter>
<g transform="translate({W/2} {H/2+4}) rotate(-5) translate({-W/2+18} {-H/2+12})" filter="url(#shadow)">
  <rect x="0" y="0" width="{iw+16}" height="{ih+16}" fill="#efe4cb"/>
  <g transform="translate(8 8)"><clipPath id="pc"><rect width="{iw}" height="{ih}"/></clipPath>
   <g clip-path="url(#pc)"><g filter="url(#sep)">{sky}{sc}
    <rect width="{iw}" height="{ih}" filter="url(#grain)" opacity=".9"/></g><rect width="{iw}" height="{ih}" fill="url(#vign)"/></g></g>
  <rect x="0" y="0" width="{iw+16}" height="{ih+16}" fill="url(#burn)" opacity=".6"/>
</g>
<rect x="{W/2-34}" y="2" width="68" height="22" fill="#e9dcb4" opacity=".75" transform="rotate(4 {W/2} 12)"/>"""
    return svg(W, H, body)


# ------------------------------------------------------------------ dishes
def table_bg(seed):
    W, H = DISH_W, DISH_H
    return f"""
<filter id="wood" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".004 .06" numOctaves="3" seed="{seed}"/>
<feColorMatrix values="0 0 0 0 .32  0 0 0 0 .2  0 0 0 0 .12  1.6 0 0 0 -.55"/></filter>
<radialGradient id="tv" cx=".5" cy=".5" r=".6"><stop offset=".5" stop-color="{TABLE}" stop-opacity="0"/><stop offset=".78" stop-color="{TABLE}" stop-opacity=".8"/><stop offset=".9" stop-color="{TABLE}"/></radialGradient>
<linearGradient id="edgeL" x1="0" x2="1"><stop offset="0" stop-color="{TABLE}"/><stop offset="1" stop-color="{TABLE}" stop-opacity="0"/></linearGradient>
""", f'<rect width="{W}" height="{H}" fill="#2a1a10"/><rect width="{W}" height="{H}" filter="url(#wood)"/>'


def table_fg():
    W, H = DISH_W, DISH_H
    return (f'<linearGradient id="edgeT" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{TABLE}"/><stop offset="1" stop-color="{TABLE}" stop-opacity="0"/></linearGradient>'
            f'<rect width="{W}" height="{H}" fill="url(#tv)"/>'
            f'<rect width="60" height="{H}" fill="url(#edgeL)"/><rect width="60" height="{H}" fill="url(#edgeL)" transform="translate({W} 0) scale(-1 1)"/>'
            f'<rect width="{W}" height="44" fill="url(#edgeT)"/><rect width="{W}" height="44" fill="url(#edgeT)" transform="translate(0 {H}) scale(1 -1)"/>')


def plate(cx, cy, r, rnd, ry=None, rim="#efe6d4"):
    ry = ry or r
    specks = "".join(f'<circle cx="{cx + (r*.93)*math.cos(a):.1f}" cy="{cy + (ry*.93)*math.sin(a):.1f}" r="{rnd.uniform(.8,1.8):.1f}" fill="#8a6a46" opacity=".6"/>'
                     for a in [rnd.uniform(0, math.tau) for _ in range(120)])
    return (f'<ellipse cx="{cx+6}" cy="{cy+14}" rx="{r}" ry="{ry}" fill="#000" opacity=".6" filter="url(#soft)"/>'
            f'<radialGradient id="pl"><stop offset="0" stop-color="#f6f0e2"/><stop offset=".75" stop-color="{rim}"/><stop offset="1" stop-color="#c8b796"/></radialGradient>'
            f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{ry}" fill="url(#pl)" stroke="#8c6a44" stroke-width="3"/>{specks}'
            f'<ellipse cx="{cx}" cy="{cy}" rx="{r*.74}" ry="{ry*.74}" fill="#f3ecdf" stroke="#d9ccb2" stroke-width="3"/>')


def flecks(cx, cy, rx, ry, n, rnd, colors=("#3f7a24", "#5c9a33"), size=(1.5, 3.5)):
    out = []
    for _ in range(n):
        a = rnd.uniform(0, math.tau)
        d = math.sqrt(rnd.random())
        out.append(f'<circle cx="{cx+rx*d*math.cos(a):.1f}" cy="{cy+ry*d*math.sin(a):.1f}" r="{rnd.uniform(*size):.1f}" fill="{rnd.choice(colors)}"/>')
    return "".join(out)


def dish_piccata(rnd):
    b = plate(304, 205, 186, rnd)
    b += f'<ellipse cx="300" cy="230" rx="120" ry="80" fill="#d9a63a" opacity=".55"/>'
    for i in range(7):  # asparagus
        x0, y0 = 120 + i * 10, 300 - i * 6
        b += (f'<line x1="{x0}" y1="{y0}" x2="{x0+120}" y2="{y0-170}" stroke="#4d7a26" stroke-width="13" stroke-linecap="round"/>'
              f'<line x1="{x0+2}" y1="{y0-4}" x2="{x0+118}" y2="{y0-170}" stroke="#86b04a" stroke-width="4" stroke-linecap="round" opacity=".7"/>'
              f'<ellipse cx="{x0+120}" cy="{y0-172}" rx="8" ry="12" transform="rotate(35 {x0+120} {y0-172})" fill="#3b5e1c"/>')
    pasta = "".join(f'<path d="M{380+rnd.uniform(-50,50):.0f} {120+rnd.uniform(-34,34):.0f} q{rnd.uniform(-60,60):.0f} {rnd.uniform(-40,40):.0f} {rnd.uniform(-70,70):.0f} {rnd.uniform(-20,20):.0f}" stroke="{rnd.choice(["#f2dc9e","#e8c97a","#fbe9b8"])}" stroke-width="2" fill="none"/>' for _ in range(160))
    b += f'<ellipse cx="380" cy="122" rx="78" ry="52" fill="#e3c27a"/>{pasta}'
    for (x, y, a) in ((246, 236, -20), (330, 260, 12), (380, 214, -8)):
        g = uid("ct")
        b += (f'<radialGradient id="{g}" cx=".45" cy=".4" r=".7"><stop offset="0" stop-color="#f0bf66"/><stop offset=".7" stop-color="#cf8a34"/><stop offset="1" stop-color="#9a5a1c"/></radialGradient>'
              f'<g transform="rotate({a} {x} {y})"><ellipse cx="{x}" cy="{y}" rx="82" ry="48" fill="url(#{g})" filter="url(#shadow)"/>'
              f'<ellipse cx="{x}" cy="{y}" rx="80" ry="46" filter="url(#crust)" opacity=".8"/></g>')
    b += flecks(310, 240, 140, 70, 140, rnd)
    for _ in range(22):
        x, y = 310 + rnd.uniform(-140, 140), 240 + rnd.uniform(-70, 70)
        b += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rnd.uniform(4,6.5):.1f}" fill="#4a5a1e" stroke="#2c3610" stroke-width="1"/><circle cx="{x-1.5:.0f}" cy="{y-1.5:.0f}" r="1.6" fill="#a8b86a"/>'
    b += lemon_slice(400, 196, 40)
    return b


def dish_pancakes(rnd):
    b = plate(300, 262, 236, rnd, ry=118)
    for i in range(4):
        y = 262 - i * 24
        g = uid("pc")
        b += (f'<path d="M160 {y} A140 58 0 0 0 440 {y} L440 {y-18} A140 58 0 0 1 160 {y-18}Z" fill="#b06d2c"/>'
              f'<path d="M160 {y} A140 58 0 0 0 440 {y}" stroke="#7d4a1a" stroke-width="2" fill="none"/>'
              f'<radialGradient id="{g}" cx=".5" cy=".5" r=".6"><stop offset="0" stop-color="#d8913e"/><stop offset=".8" stop-color="#c47c30"/><stop offset="1" stop-color="#e6bb72"/></radialGradient>'
              f'<ellipse cx="300" cy="{y-18}" rx="140" ry="58" fill="url(#{g})"/>')
    top = 262 - 3 * 24 - 18
    b += f'<ellipse cx="300" cy="{top}" rx="136" ry="55" filter="url(#crust)" opacity=".55"/>'
    b += (f'<path d="M210 {top-10} Q240 {top-40} 300 {top-36} Q380 {top-30} 392 {top+6} Q400 {top+30} 420 {top+40} L424 {top+92} Q418 {top+100} 412 {top+90} L408 {top+44} Q360 {top+40} 300 {top+38} Q236 {top+30} 196 {top+50} L192 {top+76} Q186 {top+84} 182 {top+74} L184 {top+34} Q190 {top+6} 210 {top-10}Z" fill="#7a3a0c" opacity=".82"/>'
          f'<path d="M240 {top-22} Q300 {top-34} 360 {top-18}" stroke="#ffd79a" stroke-width="3" opacity=".5" fill="none"/>'
          f'<rect x="272" y="{top-26}" width="54" height="36" rx="6" fill="#f8e6a2" stroke="#d9bd6c" transform="rotate(-8 299 {top-8})"/>'
          f'<rect x="278" y="{top-24}" width="22" height="10" rx="3" fill="#fff8d8" transform="rotate(-8 299 {top-8})"/>')
    for (x, y) in ((250, top - 4), (350, top - 6), (330, top + 16), (224, top + 14), (372, top + 18), (110, 300), (126, 320), (480, 300), (498, 280), (466, 326), (92, 278)):
        b += berry(x, y, 11)
    b += leaf(520, 230, 40, 14, 60, "#5d8a36") + leaf(100, 250, 36, 12, -70, "#5d8a36")
    return b


def dish_lentil(rnd):
    b = (f'<ellipse cx="300" cy="216" rx="172" ry="172" fill="#000" opacity=".6" filter="url(#soft)"/>'
         f'<circle cx="294" cy="202" r="170" fill="#2f5d7c" stroke="#1d3a4f" stroke-width="3"/>')
    b += "".join(f'<circle cx="{294+156*math.cos(a):.1f}" cy="{202+156*math.sin(a):.1f}" r="4" fill="#e8dcc0"/>' for a in [i * math.tau / 36 for i in range(36)])
    b += (f'<circle cx="294" cy="202" r="142" fill="#e9e0cc"/><radialGradient id="sp"><stop offset="0" stop-color="#f0a248"/><stop offset=".8" stop-color="#d27322"/><stop offset="1" stop-color="#a85316"/></radialGradient>'
          f'<circle cx="294" cy="202" r="130" fill="url(#sp)"/><circle cx="294" cy="202" r="128" filter="url(#crust)" opacity=".35"/>')
    sp = " ".join("%s%.1f,%.1f" % ("M" if i == 0 else "L", 294 + (8 + i * 1.6) * math.cos(i * .32), 202 + (8 + i * 1.6) * math.sin(i * .32)) for i in range(60))
    b += f'<path d="{sp}" stroke="#a8240f" stroke-width="8" fill="none" opacity=".85" stroke-linecap="round"/>'
    b += flecks(294, 202, 100, 100, 70, rnd, ("#8a1a08", "#b8321e"), (1.2, 2.6)) + flecks(294, 202, 90, 90, 40, rnd, ("#4f6a2a", "#6c8a3c"), (1.2, 2.4))
    b += lemon_slice(520, 330, 46, half=True)
    b += f'<g transform="translate(520 92) rotate(30)"><ellipse rx="50" ry="22" fill="#d9a356"/><ellipse rx="44" ry="17" filter="url(#crust)" opacity=".7"/></g>'
    b += leaf(70, 330, 60, 20, -40, "#4f7a28") + leaf(96, 352, 50, 18, 10, "#5f8a32")
    return b


def dish_ratatouille(rnd):
    b = (f'<ellipse cx="300" cy="216" rx="186" ry="180" fill="#000" opacity=".65" filter="url(#soft)"/>'
         f'<rect x="460" y="186" width="150" height="34" rx="14" fill="#262220"/>'
         f'<circle cx="300" cy="202" r="182" fill="#2b2826" stroke="#151312" stroke-width="4"/><circle cx="300" cy="202" r="162" fill="#a8301a"/>'
         f'<circle cx="300" cy="202" r="160" filter="url(#crust)" opacity=".5"/>')
    pieces = []
    for _ in range(70):
        a = rnd.uniform(0, math.tau)
        d = 150 * math.sqrt(rnd.random())
        x, y = 300 + d * math.cos(a), 202 + d * math.sin(a)
        if d > 140:
            continue
        k = rnd.choice(["egg", "egg", "zuc", "zuc", "red", "yel", "tom"])
        rot = rnd.uniform(0, 180)
        if k == "egg":
            pieces.append(f'<g transform="translate({x:.0f} {y:.0f}) rotate({rot:.0f})"><rect x="-14" y="-12" width="28" height="24" rx="5" fill="#e3c98e"/><rect x="-14" y="-12" width="28" height="7" rx="3" fill="#3d1a36"/></g>')
        elif k == "zuc":
            pieces.append(f'<g transform="translate({x:.0f} {y:.0f}) rotate({rot:.0f})"><path d="M-17 0 A17 15 0 0 1 17 0Z" fill="#e7e3a6" stroke="#2f5e1e" stroke-width="5"/></g>')
        elif k in ("red", "yel"):
            pieces.append(f'<g transform="translate({x:.0f} {y:.0f}) rotate({rot:.0f})"><rect x="-18" y="-8" width="36" height="16" rx="6" fill="{"#c8261b" if k == "red" else "#e9b81e"}"/><rect x="-16" y="-7" width="30" height="4" rx="2" fill="#fff" opacity=".3"/></g>')
        else:
            pieces.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="10" fill="#d23a22" stroke="#8a1a0c"/>')
    b += "".join(pieces)
    for (x, y, a) in ((250, 160, -30), (350, 230, 40), (300, 200, 160), (220, 260, 100)):
        b += basil(x, y, .8, a)
    b += thyme(470, 380, 90, -60) + thyme(120, 60, 80, 120)
    return b


def dish_soda_bread(rnd):
    b = (f'<ellipse cx="300" cy="216" rx="250" ry="174" fill="#000" opacity=".6" filter="url(#soft)"/>'
         f'<rect x="56" y="34" width="490" height="340" rx="26" fill="#8b5a2b"/><rect x="56" y="34" width="490" height="340" rx="26" filter="url(#wood)" opacity=".9"/>'
         f'<rect x="56" y="34" width="490" height="340" rx="26" fill="none" stroke="#5a3616" stroke-width="4"/>')
    b += flecks(300, 204, 230, 160, 260, rnd, ("#f6f0e2", "#ffffff", "#ece4d2"), (.8, 2.2)).replace("/>", ' opacity=".55"/>')
    g = uid("lf")
    b += (f'<radialGradient id="{g}" cx=".45" cy=".4" r=".65"><stop offset="0" stop-color="#e8b86a"/><stop offset=".65" stop-color="#c0812f"/><stop offset="1" stop-color="#7e4a17"/></radialGradient>'
          f'<circle cx="300" cy="200" r="142" fill="url(#{g})" filter="url(#shadow)"/><circle cx="300" cy="200" r="140" filter="url(#crust)" opacity=".9"/>'
          f'<path d="M300 72 L300 328 M172 200 L428 200" stroke="#6e3a12" stroke-width="22" stroke-linecap="round"/>'
          f'<path d="M300 76 L300 324 M176 200 L424 200" stroke="#f2dfb2" stroke-width="10" stroke-linecap="round"/>'
          f'<path d="M300 80 L300 320 M180 200 L420 200" stroke="#d9a860" stroke-width="4" stroke-linecap="round"/>')
    b += flecks(300, 200, 120, 120, 120, rnd, ("#fbf6ea", "#ffffff"), (.8, 2)).replace("/>", ' opacity=".7"/>')
    b += f'<g transform="translate(500 318) rotate(-12)"><rect x="-40" y="-24" width="80" height="48" rx="8" fill="#f7e6a2" stroke="#d9bd6c"/></g>'
    b += wheat(560, 380, 130, -40)
    return b


def dish_crumble(rnd):
    b = (f'<ellipse cx="300" cy="216" rx="250" ry="168" fill="#000" opacity=".6" filter="url(#soft)"/>'
         f'<ellipse cx="292" cy="200" rx="246" ry="162" fill="#f2ece0" stroke="#bfb19a" stroke-width="3"/>'
         f'<ellipse cx="292" cy="200" rx="214" ry="134" fill="#7a2a14"/>')
    crumbs = []
    for _ in range(520):
        a = rnd.uniform(0, math.tau)
        d = math.sqrt(rnd.random()) * .93
        x, y = 292 + 210 * d * math.cos(a), 200 + 130 * d * math.sin(a)
        c = rnd.choice(["#e6b56a", "#d39a4c", "#b77a32", "#8a5420", "#f0c97e", "#c98a3c"])
        crumbs.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rnd.uniform(3,9):.1f}" fill="{c}"/>')
    b += "".join(crumbs) + f'<ellipse cx="292" cy="200" rx="200" ry="122" filter="url(#crust)" opacity=".45"/>'
    b += "".join(f'<circle cx="{292+206*math.cos(a):.0f}" cy="{200+128*math.sin(a):.0f}" r="{rnd.uniform(3,7):.0f}" fill="#8e2a16" opacity=".9"/>' for a in [rnd.uniform(0, math.tau) for _ in range(40)])
    b += (f'<radialGradient id="ic" cx=".4" cy=".35"><stop offset="0" stop-color="#fffdf4"/><stop offset=".8" stop-color="#f3e7c6"/><stop offset="1" stop-color="#dccb9c"/></radialGradient>'
          f'<path d="M330 150 q10 -30 44 -34 q30 -6 46 18 q16 22 0 44 q-14 20 -46 18 q-34 -2 -44 -22 q-6 -12 0 -24Z" fill="url(#ic)" filter="url(#shadow)"/>'
          f'<path d="M346 176 q20 12 46 4" stroke="#e8d6a6" stroke-width="3" fill="none"/>')
    b += apple(546, 340, 42) + leaf(100, 360, 50, 18, -50)
    return b


def dish_chai(rnd):
    b = ""
    for (cx, cy) in ((210, 210), (420, 180)):
        b += (f'<ellipse cx="{cx+6}" cy="{cy+12}" rx="112" ry="112" fill="#000" opacity=".55" filter="url(#soft)"/>'
              f'<circle cx="{cx}" cy="{cy}" r="108" fill="#e9e0cf" stroke="#b8a888" stroke-width="2"/>'
              f'<circle cx="{cx}" cy="{cy}" r="88" fill="#d9cdb6"/>'
              f'<rect x="{cx+60}" y="{cy-14}" width="50" height="28" rx="14" fill="none" stroke="#f4efe6" stroke-width="10"/>'
              f'<circle cx="{cx}" cy="{cy}" r="76" fill="#f7f2e8" stroke="#c9bb9e" stroke-width="2" filter="url(#shadow)"/>'
              f'<radialGradient id="ch{cx}"><stop offset="0" stop-color="#d9ac74"/><stop offset=".85" stop-color="#b47a42"/><stop offset="1" stop-color="#8a5428"/></radialGradient>'
              f'<circle cx="{cx}" cy="{cy}" r="64" fill="url(#ch{cx})"/>'
              f'<circle cx="{cx}" cy="{cy}" r="58" fill="none" stroke="#e8cfa6" stroke-width="5" opacity=".7"/>')
        b += flecks(cx, cy, 56, 56, 26, rnd, ("#f2e2c4", "#e8d2a8"), (1, 3)).replace("/>", ' opacity=".7"/>')
    b += cinnamon(80, 360, 150, -10) + cinnamon(96, 380, 140, -4) + star_anise(330, 330, 34) + star_anise(520, 330, 26)
    b += cardamom(400, 360, 20) + cardamom(430, 372, -30) + cardamom(250, 360, 60) + cardamom(560, 60, 10)
    b += f'<g transform="translate(70 70) rotate(-20)"><ellipse rx="34" ry="22" fill="#d6b07a" stroke="#9c7440" stroke-width="2"/><path d="M-26 -4 q10 8 22 0 q12 -8 24 2" stroke="#9c7440" fill="none"/></g>'
    return b


DISHES = {
    "tuscan-lemon-chicken-piccata": dish_piccata,
    "blueberry-buttermilk-pancakes": dish_pancakes,
    "turkish-red-lentil-soup": dish_lentil,
    "provencal-ratatouille": dish_ratatouille,
    "irish-soda-bread": dish_soda_bread,
    "grandmas-apple-crumble": dish_crumble,
    "masala-chai": dish_chai,
}


def dish_svg(rid):
    rnd = random.Random(rid)
    d, b = table_bg(sum(map(ord, rid)) % 50)
    return svg(DISH_W, DISH_H, b + DISHES[rid](rnd) + table_fg(), d)


# ------------------------------------------------------------------ channel art
def channel_jobs():
    jobs = []
    d = '<radialGradient id="ibg" cx=".5" cy=".5" r=".7"><stop offset="0" stop-color="#36241a"/><stop offset="1" stop-color="#110a06"/></radialGradient>'
    b = '<rect width="1920" height="1080" fill="url(#ibg)"/>'
    title = ('<text x="960" y="560" text-anchor="middle" font-family="Script" font-size="170" fill="url(#gold)" filter="url(#glow)">The Heirloom Table</text>'
             '<text x="960" y="650" text-anchor="middle" font-family="Serif" font-size="34" letter-spacing="6" fill="#e9cf8e">FAMILY RECIPES · KITCHEN FAVORITES · NEW TRADITIONS</text>')
    jobs.append(("channel/splash_fhd.jpg", svg(1920, 1080, b + frame(1920, 1080) + title, d), 1920, 1080, 70))
    for name, w, h, fs in (("channel/icon_focus_fhd.png", 540, 405, 74), ("channel/icon_focus_hd.png", 290, 218, 40)):
        d = ""
        b = f'<rect width="{w}" height="{h}" fill="#1e140d"/>'
        t = (f'<text x="{w/2}" y="{h*.47}" text-anchor="middle" font-family="Script" font-size="{fs}" fill="url(#gold)">The Heirloom</text>'
             f'<text x="{w/2}" y="{h*.47+fs*.95}" text-anchor="middle" font-family="Script" font-size="{fs}" fill="url(#gold)">Table</text>')
        fr = (f'<rect x="{w*.04}" y="{w*.04}" width="{w*.92}" height="{h-w*.08}" fill="none" stroke="url(#gold)" stroke-width="{max(2, w/140):.1f}" rx="6"/>')
        jobs.append((name, svg(w, h, b + fr + t, d), w, h, None))
    return jobs


# ------------------------------------------------------------------ pure-python PNG (9-patch)
def write_png(path, w, h, px):
    raw = b"".join(b"\x00" + bytes(px[y * w * 4:(y + 1) * w * 4]) for y in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(data)


def rr_dist(x, y, w, h, r):
    """Signed distance from (x,y) to a rounded rectangle [0,w]x[0,h] with radius r (negative inside)."""
    qx = abs(x - w / 2) - (w / 2 - r)
    qy = abs(y - h / 2) - (h / 2 - r)
    return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r


def ninepatch(name, size, corner, fn):
    """fn(x, y) -> (r,g,b,a) for the content area; writes <name>.9.png (Roku) and web/<name>.png (no markers)."""
    W = H = size
    content = [0] * (W * H * 4)
    for y in range(H):
        for x in range(W):
            content[(y * W + x) * 4:(y * W + x) * 4 + 4] = fn(x + .5, y + .5)
    os.makedirs(os.path.join(IMG, "web"), exist_ok=True)
    write_png(os.path.join(IMG, "web", name + ".png"), W, H, content)
    W2, H2 = W + 2, H + 2
    px = [0] * (W2 * H2 * 4)
    for y in range(H):
        px[((y + 1) * W2 + 1) * 4:((y + 1) * W2 + 1 + W) * 4] = content[y * W * 4:(y + 1) * W * 4]
    for i in range(corner, size - corner):  # stretch markers (top row, left column)
        px[(0 * W2 + 1 + i) * 4:(0 * W2 + 1 + i) * 4 + 4] = [0, 0, 0, 255]
        px[((1 + i) * W2 + 0) * 4:((1 + i) * W2 + 0) * 4 + 4] = [0, 0, 0, 255]
    write_png(os.path.join(IMG, "ui", name + ".9.png"), W2, H2, px)


def focus_px(x, y, S=72, inset=14, r=12):
    d = rr_dist(x - inset, y - inset, S - 2 * inset, S - 2 * inset, r)
    ring = max(0.0, 1 - abs(d) / 2.2)  # crisp 4px gold ring centred on the rect edge
    glow = math.exp(-max(d, 0) / 5.0) * 0.55 if d > -1 else 0.0
    a = min(1.0, ring + glow * (1 - ring))
    col = (246, 214, 140) if ring > glow else (230, 170, 60)
    return [col[0], col[1], col[2], int(a * 255)]


_noise_cache = {}


def vnoise(x, y, seed=3):
    xi, yi = int(x), int(y)

    def h(i, j):
        k = (i, j)
        if k not in _noise_cache:
            _noise_cache[k] = random.Random(i * 7919 + j * 104729 + seed).random()
        return _noise_cache[k]
    fx, fy = x - xi, y - yi
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = h(xi, yi) + (h(xi + 1, yi) - h(xi, yi)) * fx
    b = h(xi, yi + 1) + (h(xi + 1, yi + 1) - h(xi, yi + 1)) * fx
    return a + (b - a) * fy


def parch_px(x, y, S=120, m=6):
    edge = min(x, y, S - x, S - y)
    jag = (vnoise(x / 3.0, y / 3.0) - .5) * 4
    a = max(0.0, min(1.0, (edge - m + jag) / 1.5))
    n = vnoise(x / 14.0, y / 14.0) * .6 + vnoise(x / 4.0, y / 4.0) * .4
    burn = max(0.0, 1 - (edge - m) / 18.0) if edge > m - 3 else 1
    base = (242, 226, 186)
    dark = (176, 128, 70)
    t = min(1.0, burn * .75 + (n - .5) * .18 + .06)
    c = [int(base[i] * (1 - t) + dark[i] * t) for i in range(3)]
    return c + [int(a * 255)]


def ninepatch_jobs():
    os.makedirs(os.path.join(IMG, "ui"), exist_ok=True)
    ninepatch("focus", 72, 24, focus_px)
    ninepatch("parchment", 120, 30, parch_px)


# ------------------------------------------------------------------ driver
def ensure_renderer():
    src = os.path.join(ROOT, "tools", "render.swift")
    if not os.path.exists(BIN) or os.path.getmtime(BIN) < os.path.getmtime(src):
        os.makedirs(os.path.dirname(BIN), exist_ok=True)
        print("compiling tools/render.swift ...")
        subprocess.check_call(["swiftc", "-O", src, "-o", BIN])


def run(jobs, force):
    todo = [j for j in jobs if force or not os.path.exists(os.path.join(IMG, j[0]))]
    if not todo:
        return
    ensure_renderer()
    os.makedirs(BUILD, exist_ok=True)
    spec = []
    for rel, html, w, h, q in todo:
        hp = os.path.join(BUILD, rel.replace("/", "__") + ".html")
        open(hp, "w", encoding="utf-8").write(html)
        tmp = os.path.join(BUILD, rel.replace("/", "__") + ".png")
        spec.append({"html": hp, "out": tmp if q else os.path.join(IMG, rel), "w": w, "h": h,
                     "opaque": bool(q), "wait": 0.9 if "channel" in rel else 0.3})
        os.makedirs(os.path.dirname(os.path.join(IMG, rel)), exist_ok=True)
    jf = os.path.join(BUILD, "jobs.json")
    json.dump(spec, open(jf, "w"))
    subprocess.check_call([BIN, jf, ROOT])
    for (rel, _, _, _, q), s in zip(todo, spec):
        if q:
            subprocess.check_call(["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(q), s["out"],
                                   "--out", os.path.join(IMG, rel)], stdout=subprocess.DEVNULL)
        print("  art", rel, os.path.getsize(os.path.join(IMG, rel)) // 1024, "KB")


def main():
    force = "--force" in sys.argv
    groups = [a for a in sys.argv[1:] if not a.startswith("-")]
    want = lambda g: not groups or g in groups
    data = json.load(open(os.path.join(ROOT, "data", "recipes.json")))
    jobs = []
    if want("ui"):
        jobs += ui_jobs()
    if want("icons"):
        jobs += icon_jobs()
    if want("garnish"):
        jobs += [("garnish/%s.png" % g, garnish_svg(g), GS, GS, None) for g in GARNISHES]
    if want("photos"):
        jobs += [("photos/%s.png" % p, photo_svg(p), L["recipe"]["photo"]["w"], L["recipe"]["photo"]["h"], None) for p in PHOTOS]
    if want("dishes"):
        for r in data["recipes"]:
            if r["id"] not in DISHES:
                sys.exit("no dish illustration for %s: add one to DISHES in tools/make_art.py" % r["id"])
            jobs.append(("dishes/%s.jpg" % r["id"], dish_svg(r["id"]), DISH_W, DISH_H, 80))
    if want("channel"):
        jobs += channel_jobs()
    run(jobs, force)
    if want("ninepatch") and (force or not os.path.exists(os.path.join(IMG, "ui", "focus.9.png"))):
        ninepatch_jobs()
        print("  art ui/focus.9.png, ui/parchment.9.png")


if __name__ == "__main__":
    main()
