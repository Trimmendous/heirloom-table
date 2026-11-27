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

GARNISHES = ["lemon", "berries", "chili", "herbs", "apple", "wheat", "spice", "scallion", "lime", "olive", "mango", "peanut", "cucumber", "mint", "pepper", "tofu", "bonnet", "tomato", "butter"]
PHOTOS = ["villa", "farmhouse", "cottage", "bazaar", "teahouse", "hacienda", "village", "seaside", "boulangerie"]
DISH_W, DISH_H = L["recipe"]["dish"]["w"], L["recipe"]["dish"]["h"]
PHOTO_W, PHOTO_H = 224, 190
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


def background(w, h, seed=1, night=False):
    light, middle, dark, grain = (
        ("#20384a", "#132533", "#080f1a", ".12 0 0 0 .34  0 0 0 0 .53")
        if night else ("#36241a", "#211510", "#0f0906", ".55 0 0 0 .34  0 0 0 0 .16")
    )
    return f"""
<radialGradient id="bgg" cx=".42" cy=".38" r=".8"><stop offset="0" stop-color="{light}"/><stop offset=".55" stop-color="{middle}"/><stop offset="1" stop-color="{dark}"/></radialGradient>
<filter id="bgn" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".006 .009" numOctaves="4" seed="{seed}"/>
<feColorMatrix values="0 0 0 0 .05  0 0 0 0 .03  0 0 0 0 .02  1.8 0 0 0 -.8"/></filter>
<filter id="bgw" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".012" numOctaves="2" seed="{seed+5}"/>
<feColorMatrix values="0 0 0 0 {grain}  1.2 0 0 0 -.62"/></filter>
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


def crest(cx, cy=30):
    """Small gold farmhouse crest with laurel sprigs, sitting on the top frame line (as in the reference)."""
    hide = (f'<radialGradient id="crh" cx=".5" cy=".5" r=".5"><stop offset=".55" stop-color="#1a110b"/><stop offset="1" stop-color="#1a110b" stop-opacity="0"/></radialGradient>'
            f'<ellipse cx="{cx}" cy="{cy}" rx="150" ry="30" fill="url(#crh)"/>')
    house = (f'<g transform="translate({cx} {cy})" fill="none" stroke="url(#gold)" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round">'
             f'<path d="M-24 -2 L0 -20 L24 -2"/><path d="M-19 -5 V16 H19 V-5"/><path d="M11 -14 V-22 H16 V-10"/>'
             f'<path d="M-4 16 V5 H4 V16"/><rect x="-14" y="1" width="6" height="6"/><rect x="8" y="1" width="6" height="6"/>'
             f'<path d="M-34 18 H34" stroke-width="1.6"/></g>')
    sprigs = ""
    for side in (-1, 1):
        sx = cx + side * 34
        sprigs += f'<path d="M{sx} {cy+14} Q{sx+side*48} {cy+12} {sx+side*104} {cy-6}" stroke="url(#gold)" stroke-width="2" fill="none" stroke-linecap="round"/>'
        for i in range(6):
            t = (i + .6) / 6.4
            x = sx + side * (104 * t)
            y = cy + 14 - 20 * t * t
            for up in (-1, 1):
                ang = side * (60 if up < 0 else 125) - (0 if side > 0 else 0)
                ln = 15 - i * 1.2
                sprigs += (f'<ellipse cx="0" cy="{-ln/2:.1f}" rx="{ln*.24:.1f}" ry="{ln/2:.1f}" fill="url(#gold)" '
                           f'transform="translate({x:.1f} {y:.1f}) rotate({ang + up * 8 * side:.0f})"/>')
        sprigs += f'<circle cx="{sx+side*108}" cy="{cy-8}" r="2.6" fill="#e9c77a"/>'
    return hide + f'<g filter="url(#glow)">{house}{sprigs}</g>'


def vine(x, y1, y2, seed=13):
    """Leafy vine trailing down the right edge of the recipe screen, outside the title-safe area."""
    rnd = random.Random(seed)
    pts = []
    n = 40
    for i in range(n + 1):
        t = i / n
        pts.append((x + 9 * math.sin(t * math.tau * 2.2) + 4 * math.sin(t * 17), y1 + (y2 - y1) * t))
    d = "M%.1f %.1f " % pts[0] + " ".join("L%.1f %.1f" % p for p in pts[1:])
    out = [f'<path d="{d}" stroke="#6b5a2a" stroke-width="3.2" fill="none" stroke-linecap="round"/>',
           f'<path d="{d}" stroke="url(#gold)" stroke-width="1.2" fill="none" opacity=".7"/>']
    i = 2
    side = 1
    while i < n - 1:
        px, py = pts[i]
        ln = rnd.uniform(26, 38) * (1 - .35 * (i / n))
        ang = side * rnd.uniform(48, 70) + 180
        out.append(leaf(round(px, 1), round(py, 1), round(ln, 1), round(ln * .3, 1), round(ang),
                        "#8aa04a", "#4a5e22", "#d8d08a"))
        if rnd.random() < .45:
            out.append(leaf(round(px, 1), round(py, 1), round(ln * .7, 1), round(ln * .22, 1), round(ang + side * 30),
                            "#7a9440", "#3e5020", "#d8d08a"))
        if rnd.random() < .22:
            bx, by = px - side * 12, py + 6
            out.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="3.6" fill="#e9c77a"/><circle cx="{bx-1:.1f}" cy="{by-1:.1f}" r="1.2" fill="#fff4d0"/>')
        side = -side
        i += rnd.choice((2, 3))
    out.append(leaf(round(pts[-1][0], 1), round(pts[-1][1], 1), 22, 7, 170, "#8aa04a", "#4a5e22", "#d8d08a"))
    return f'<g filter="url(#shadow)">' + "".join(out) + "</g>"


# ------------------------------------------------------------------ screens
def ui_jobs(night=False):
    W, H = 1920, 1080
    jobs = []
    suffix = "night" if night else "bg"
    d, b = background(W, H, 3, night)
    R = L["recipe"]
    dish = R["dish"]
    slot = (f'<filter id="feather" x="-30%" y="-30%" width="160%" height="160%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="22"/></filter>'
            f'<rect x="{dish["x"]-34}" y="{dish["y"]-30}" width="{dish["w"]+68}" height="{dish["h"]+60}" rx="60" fill="{TABLE}" filter="url(#feather)"/>'
            f'<rect x="{dish["x"]-4}" y="{dish["y"]-4}" width="{dish["w"]+8}" height="{dish["h"]+8}" rx="20" fill="{TABLE}" filter="url(#soft)"/>')
    tc, ic = R["titleCard"], R["ingCard"]
    meta = R["meta"]
    divs = "".join(f'<line x1="{meta["x"]+meta["colW"]*k-6}" y1="{meta["y"]+6}" x2="{meta["x"]+meta["colW"]*k-6}" '
                   f'y2="{meta["y"]+96}" stroke="#8c5f2c" stroke-opacity=".5" stroke-width="1.5"/>' for k in (1, 2, 3))
    st = R["steps"]
    body = b + slot + frame(W, H) + parchment(tc["x"], tc["y"], tc["w"], tc["h"], 21) \
        + parchment(ic["x"], ic["y"], ic["w"], ic["h"], 22) \
        + ornament_rule(tc["x"] + 140, tc["x"] + tc["w"] - 140, meta["y"] - 10, "#9c6f37", "#9c6f37", 1.4) \
        + divs \
        + ornament_rule(R["ingHeader"]["x"] - 10, ic["x"] + ic["w"] - 34, R["ingList"]["y"] - 14, "#9c6f37", "#9c6f37", 1.4) \
        + ornament_rule(st["x"] + 4, st["x"] + st["w"] - 20, st["y"] - 14) \
        + crest(W / 2) + vine(1858, tc["y"] + tc["h"] - 40, R["stepFooter"]["y"] - 16)
    jobs.append((f"ui/recipe_{suffix}.jpg", svg(W, H, body, d), W, H, 66))

    d, b = background(W, H, 5, night)
    T = L["home"]["title"]
    body = b + frame(W, H) + crest(W / 2) + ornament_rule(560, 1360, L["home"]["tagline"]["y"] + 50)
    jobs.append((f"ui/home_{suffix}.jpg", svg(W, H, body, d), W, H, 72))

    d, b = background(W, H, 9, night)
    s = L["cook"]["sheet"]
    body = b + frame(W, H) + crest(W / 2) + parchment(s["x"], s["y"], s["w"], s["h"], 31, grain=.3) \
        + ornament_rule(s["x"] + 300, s["x"] + s["w"] - 300, L["cook"]["counter"]["y"] + 56, "#9c6f37", "#9c6f37", 1.6)
    jobs.append((f"ui/cook_{suffix}.jpg", svg(W, H, body, d), W, H, 58))
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


LEMON = ("#fff5a8", "#f5cf22", "#c98f0c", "#a87408")
LIME = ("#e4f4a0", "#79b52e", "#2f6a12", "#2a5410")
LEMON_SLICE = ("#f0c419", "#c9960c", "#fdf8dc", "#fff6b0", "#f2cc2c", "#fbf3c4")
LIME_SLICE = ("#4f8a1e", "#2f5e12", "#f1f7d8", "#e8f7b0", "#a6d046", "#f2fad0")


def lemon(cx, cy, rx, ry, ang, c=LEMON):
    g = uid("lm")
    return (f'<radialGradient id="{g}" cx=".38" cy=".35" r=".7"><stop offset="0" stop-color="{c[0]}"/><stop offset=".45" stop-color="{c[1]}"/><stop offset="1" stop-color="{c[2]}"/></radialGradient>'
            f'<g transform="translate({cx} {cy}) rotate({ang})"><path d="M{-rx} 0 Q{-rx} {-ry} 0 {-ry} Q{rx} {-ry} {rx} 0 Q{rx} {ry} 0 {ry} Q{-rx} {ry} {-rx} 0Z M{rx} 0 l8 -2 l0 4Z M{-rx} 0 l-7 -2 l0 4Z" fill="url(#{g})" stroke="{c[3]}" stroke-width="1"/>'
            f'<ellipse cx="{-rx*.3}" cy="{-ry*.45}" rx="{rx*.3}" ry="{ry*.18}" fill="#fff" opacity=".35"/></g>')


def lemon_slice(cx, cy, r, half=False, c=LEMON_SLICE):
    segs = "".join(f'<line x1="0" y1="0" x2="{r*.82*math.cos(a):.1f}" y2="{r*.82*math.sin(a):.1f}" stroke="{c[5]}" stroke-width="2.2"/>'
                   for a in [i * math.pi / 5 for i in range(10)])
    g = uid("ls")
    clip = f'<clipPath id="{g}c"><rect x="{-r-2}" y="{-r-2}" width="{2*r+4}" height="{r+2}"/></clipPath>' if half else ""
    return (f'{clip}<radialGradient id="{g}"><stop offset="0" stop-color="{c[3]}"/><stop offset="1" stop-color="{c[4]}"/></radialGradient>'
            f'<g transform="translate({cx} {cy})" {"clip-path=url(#%sc)" % g if half else ""}><circle r="{r}" fill="{c[0]}" stroke="{c[1]}" stroke-width="1.5"/>'
            f'<circle r="{r*.88}" fill="{c[2]}"/><circle r="{r*.82}" fill="url(#{g})"/>{segs}<circle r="{r*.1}" fill="{c[5]}"/></g>')


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


def scallion(x, y, ln, ang):
    g = uid("sc")
    roots = "".join(f'<path d="M0 0 q{rnd_x} 10 {rnd_x*1.6:.1f} 18" stroke="#d8cfae" stroke-width="1.2" fill="none"/>' for rnd_x in (-6, -3, 0, 3, 6))
    return (f'<linearGradient id="{g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3f7f22"/><stop offset=".55" stop-color="#7fb446"/><stop offset=".72" stop-color="#e3eccb"/><stop offset="1" stop-color="#fbf8ec"/></linearGradient>'
            f'<g transform="translate({x} {y}) rotate({ang})">{roots}'
            f'<path d="M-7 0 Q-9 {-ln*.25} -6 {-ln*.42} L-12 {-ln} Q-6 {-ln*1.02} -2 {-ln*.96} L0 {-ln*.45} L4 {-ln*.98} Q9 {-ln*1.02} 12 {-ln*.94} L6 {-ln*.42} Q9 {-ln*.25} 7 0Z" fill="url(#{g})" stroke="#2f5e16" stroke-width=".8"/>'
            f'<path d="M-3 {-ln*.3} L-7 {-ln*.9} M3 {-ln*.32} L7 {-ln*.88}" stroke="#fff" stroke-opacity=".35" stroke-width="1.5"/></g>')


def scallion_rings(cx, cy, rx, ry, n, rnd, r=(5, 8)):
    out = []
    for _ in range(n):
        a = rnd.uniform(0, math.tau)
        d = math.sqrt(rnd.random())
        rr = rnd.uniform(*r)
        out.append(f'<circle cx="{cx+rx*d*math.cos(a):.1f}" cy="{cy+ry*d*math.sin(a):.1f}" r="{rr:.1f}" fill="#d9ebb0" stroke="{rnd.choice(("#3f8a22", "#5ea232"))}" stroke-width="{rr*.45:.1f}"/>')
    return "".join(out)


def ginger(cx, cy, s, ang):
    g = uid("gi")
    lobes = ((0, 0, 30, 20), (-30, -10, 20, 15), (26, -18, 18, 13), (34, 12, 16, 12))
    body = "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="url(#{g})" stroke="#9a7038" stroke-width="1.3"/>' for x, y, rx, ry in lobes)
    rings = "".join(f'<path d="M{x-rx*.5} {y-ry*.2} q{rx*.5} {ry*.4} {rx} 0" stroke="#a87a3e" stroke-width="1.2" fill="none"/>' for x, y, rx, ry in lobes)
    return (f'<radialGradient id="{g}" cx=".4" cy=".35"><stop offset="0" stop-color="#f0d39a"/><stop offset="1" stop-color="#c79a58"/></radialGradient>'
            f'<g transform="translate({cx} {cy}) rotate({ang}) scale({s})">{body}{rings}'
            f'<ellipse cx="0" cy="0" rx="14" ry="10" fill="#f6e6a8" stroke="#d7b766" stroke-width="2"/></g>')


def cilantro(x, y, ln, ang, k=1.0):
    out = [f'<path d="M0 0 Q{ln*.1} {-ln*.5} 0 {-ln}" stroke="#4f7f2a" stroke-width="{2*k:.1f}" fill="none"/>']
    for t, side in ((.45, -1), (.62, 1), (.8, -1), (1.0, 0)):
        lx, ly = side * 16 * k, -ln * t - (6 * k if side == 0 else 0)
        out.append(f'<path d="M0 {-ln*t:.1f} L{lx:.1f} {ly:.1f}" stroke="#4f7f2a" stroke-width="{1.4*k:.1f}"/>')
        for da in (-50, 0, 50):
            a = math.radians(da + (90 if side == 0 else (0 if side > 0 else 180)) - 90 * (side == 0) * 2)
            px, py = lx + 9 * k * math.cos(a), ly + 9 * k * math.sin(a)
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{8*k:.1f}" fill="#4e9a2c" stroke="#2f6a18" stroke-width=".8"/>'
                       f'<path d="M{px-4*k:.1f} {py:.1f} l{3*k:.1f} {-3*k:.1f} l{3*k:.1f} {3*k:.1f}" stroke="#2f6a18" stroke-width=".8" fill="none"/>')
    return f'<g transform="translate({x} {y}) rotate({ang})">' + "".join(out) + "</g>"


def olive(cx, cy, rx, ry, ang, dark=True):
    g = uid("ol")
    c = ("#8a6a8a", "#4a2a44", "#1e1018") if dark else ("#d8dc86", "#8a9a2a", "#4a5a12")
    return (f'<radialGradient id="{g}" cx=".35" cy=".32" r=".75"><stop offset="0" stop-color="{c[0]}"/><stop offset=".5" stop-color="{c[1]}"/><stop offset="1" stop-color="{c[2]}"/></radialGradient>'
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" transform="rotate({ang} {cx} {cy})" fill="url(#{g})"/>'
            f'<ellipse cx="{cx-rx*.3:.1f}" cy="{cy-ry*.35:.1f}" rx="{rx*.25:.1f}" ry="{ry*.15:.1f}" transform="rotate({ang} {cx} {cy})" fill="#fff" opacity=".4"/>')


def olive_leaf(cx, cy, ln, ang):
    return leaf(cx, cy, ln, ln * .17, ang, "#93a37a", "#55643f", "#d2dcb6")


def mango(cx, cy, s, ang):
    g, h = uid("mg"), uid("mh")
    return (f'<radialGradient id="{g}" cx=".3" cy=".72" r=".95"><stop offset="0" stop-color="#ffd84a"/><stop offset=".45" stop-color="#f59a1e"/><stop offset=".85" stop-color="#d9502a"/><stop offset="1" stop-color="#a83418"/></radialGradient>'
            f'<linearGradient id="{h}" x1="1" y1="0" x2=".4" y2=".6"><stop offset="0" stop-color="#7aa02a" stop-opacity=".9"/><stop offset="1" stop-color="#7aa02a" stop-opacity="0"/></linearGradient>'
            f'<g transform="translate({cx} {cy}) rotate({ang}) scale({s})">'
            f'<path d="M0 -62 C52 -72 74 -12 52 38 C36 76 -22 80 -46 50 C-72 18 -52 -52 0 -62Z" fill="url(#{g})" stroke="#9a3a12" stroke-width="1.2"/>'
            f'<path d="M0 -62 C52 -72 74 -12 52 38 C36 76 -22 80 -46 50 C-72 18 -52 -52 0 -62Z" fill="url(#{h})"/>'
            f'<ellipse cx="-24" cy="-26" rx="12" ry="22" transform="rotate(20 -24 -26)" fill="#fff" opacity=".25"/>'
            f'<path d="M4 -62 q2 -10 -2 -16" stroke="#5a3a1a" stroke-width="4" fill="none" stroke-linecap="round"/></g>')


def mango_slice(x, y, ln, ang, wd=30):
    g = uid("ms")
    fib = "".join(f'<path d="M{ln*t:.1f} {-wd*.55*math.sin(math.pi*t):.1f} L{ln*(t+.06):.1f} {wd*.3*math.sin(math.pi*t):.1f}" stroke="#ffe08a" stroke-width="1.2" opacity=".6"/>' for t in (.15, .3, .45, .6, .75))
    return (f'<linearGradient id="{g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffd34a"/><stop offset=".6" stop-color="#f7a21c"/><stop offset="1" stop-color="#e07a14"/></linearGradient>'
            f'<g transform="translate({x} {y}) rotate({ang})"><path d="M0 0 C{ln*.3} {-wd} {ln*.75} {-wd} {ln} {-wd*.15} C{ln*.75} {wd*.35} {ln*.3} {wd*.4} 0 0Z" fill="url(#{g})" stroke="#c8661a" stroke-width="1"/>{fib}'
            f'<path d="M{ln*.2} {-wd*.55} C{ln*.45} {-wd*.8} {ln*.7} {-wd*.75} {ln*.85} {-wd*.4}" stroke="#fff6c8" stroke-width="2.5" opacity=".5" fill="none"/></g>')


def sesame(cx, cy, rx, ry, n, rnd, colors=("#f4e6c0", "#e8d4a0")):
    out = []
    for _ in range(n):
        a = rnd.uniform(0, math.tau)
        d = math.sqrt(rnd.random())
        x, y = cx + rx * d * math.cos(a), cy + ry * d * math.sin(a)
        out.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="3.2" ry="1.9" transform="rotate({rnd.uniform(0,180):.0f} {x:.1f} {y:.1f})" fill="{rnd.choice(colors)}" stroke="#a88a52" stroke-width=".4"/>')
    return "".join(out)


def blob(cx, cy, r, rnd, jitter=.12, n=18):
    """Irregular closed shape (egg whites, sauce pools)."""
    pts = []
    for i in range(n):
        a = i * math.tau / n
        rr = r * (1 + rnd.uniform(-jitter, jitter))
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d = "M%.1f %.1f" % ((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2)
    for i, p in enumerate(pts):
        q = pts[(i + 1) % n]
        d += " Q%.1f %.1f %.1f %.1f" % (p[0], p[1], (p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    return d + "Z"


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
    elif name == "scallion":
        # garnish art keeps clear of the bottom-left of its 256 grid (x < 170, y > 210): the title card's description runs there
        b = (scallion(74, 196, 180, 36) + scallion(100, 206, 168, 52) + scallion(58, 180, 160, 24) +
             ginger(190, 178, 1.0, -14) + scallion_rings(160, 98, 32, 22, 7, rnd, (6, 9)) + chili(178, 226, 64, -24))
    elif name == "lime":
        b = (cilantro(196, 236, 120, -28, 1.1) + cilantro(214, 226, 100, 34, 1.0) + cilantro(66, 196, 96, -62, 1.0) +
             lemon(120, 96, 58, 46, -20, LIME) + leaf(176, 62, 60, 20, 50, "#4f8a2a", "#2d5e16") +
             lemon_slice(176, 150, 40, c=LIME_SLICE) + lemon_slice(96, 162, 30, c=LIME_SLICE))
    elif name == "olive":
        b = '<path d="M62 196 C100 166 140 126 230 36" stroke="#6b5233" stroke-width="5" fill="none" stroke-linecap="round"/>'
        for t, side, ln in ((.12, 1, 70), (.25, -1, 76), (.38, 1, 74), (.5, -1, 72), (.62, 1, 68), (.74, -1, 62), (.86, 1, 56), (.98, 0, 48)):
            x, y = 62 + 168 * t, 196 - 160 * t ** .9
            b += olive_leaf(x, y, ln, 45 + side * 55)
        for (x, y, dk) in ((96, 196, True), (120, 176, True), (150, 150, False), (172, 128, True), (78, 172, False)):
            b += olive(x + 30, y - 4, 15, 21, -30, dk)
    elif name == "mango":
        b = (leaf(70, 120, 120, 24, -56, "#3f6a26", "#22451a", "#8fb070") + leaf(186, 100, 110, 22, 48, "#3f6a26", "#22451a", "#8fb070") +
             mango(112, 108, 1.1, -18) + mango_slice(140, 176, 110, -14, 28) + mango_slice(132, 198, 100, -4, 24) + sesame(206, 214, 22, 16, 12, rnd))
    elif name == "peanut":
        b = (leaf(70, 110, 96, 24, -50, "#3f6e26", "#24481a") + leaf(190, 92, 84, 22, 46, "#3f6e26", "#24481a") +
             peanut(110, 120, -30, 1.7) + peanut(160, 150, 24, 1.6) + peanut(196, 196, -60, 1.4) +
             chili(132, 70, 96, 18, "#e0681a") + peanut(200, 120, 10, 1.3, True) + peanut(214, 140, 70, 1.3, True) + peanut(186, 226, 30, 1.2, True))
    elif name == "cucumber":
        b = (leaf(178, 64, 76, 26, 40, "#3f7a22", "#24501a") + cucumber(128, 118, 190, -32, 44) +
             cucumber_slice(176, 178, 40, 10) + cucumber_slice(210, 132, 34, -20) + chili(96, 172, 92, -12) +
             sesame(196, 214, 30, 16, 14, rnd))
    elif name == "mint":
        b = (mint_sprig(118, 220, 170, -18, 1.1) + mint_sprig(152, 228, 150, 22, 1.0) + mint_sprig(96, 190, 110, -48, .8) +
             sugar_cube(196, 196, 30, 14) + sugar_cube(222, 168, 26, -10))
    elif name == "pepper":
        b = (cilantro(196, 236, 110, -20, 1.0) + bell_pepper(124, 118, 1.25, -14) + bell_pepper(194, 150, .85, 22, ("#ffd86a", "#f0a01a", "#8a4a08")) +
             pepper_strip(150, 196, 70, -8) + pepper_strip(176, 214, 60, 10, "#f0a01a"))
    elif name == "tofu":
        b = (wakame(96, 70, 120, 24, 16) + wakame(120, 120, 110, -8, 14) + scallion(214, 210, 150, -24) +
             tofu_cube(150, 160, 46, -8) + tofu_cube(196, 120, 38, 12) + tofu_cube(120, 100, 34, -18) + scallion_rings(180, 190, 30, 22, 7, rnd, (5, 7)))
    elif name == "bonnet":
        b = (thyme(70, 150, 120, -60) + thyme(200, 220, 150, 10) + leaf(170, 74, 80, 24, 30, "#4d7a2a", "#2f5418") +
             scotch_bonnet(120, 110, 1.3, -14) + scotch_bonnet(188, 160, 1.0, 22, ("#fff09a", "#f2c21a", "#9a6a06")) +
             allspice(150, 196, 9) + allspice(170, 210, 8) + allspice(206, 206, 8) + allspice(228, 186, 7))
    elif name == "tomato":
        b = (leaf(70, 110, 80, 24, -60, "#4d7a2a", "#2f5418") + '<path d="M60 52 Q130 30 210 60" stroke="#4f7a22" stroke-width="5" fill="none" stroke-linecap="round"/>' +
             '<path d="M100 44 L102 70 M150 40 L154 88 M196 56 L198 110" stroke="#4f7a22" stroke-width="4" fill="none"/>' +
             tomato(104, 100, 34) + tomato(156, 132, 42) + tomato(204, 150, 32) + garlic_clove(200, 208, 1.1, 20) + cilantro(150, 236, 80, 30, .8))
    elif name == "butter":
        b = (wheat(80, 200, 150, -28) + wheat(110, 210, 140, -8) + baguette(160, 110, 190, -38, 40, slashes=3) +
             butter_pat(176, 182, 1.2, -8) + '<path d="M150 222 L236 196" stroke="#8a8c92" stroke-width="7" stroke-linecap="round"/><path d="M208 204 L246 192" stroke="#4a3a2a" stroke-width="10" stroke-linecap="round"/>')
    else:
        raise KeyError(name)
    k = GS / S
    return svg(GS, GS, f'<g transform="scale({k:.4f})" filter="url(#shadow)">{b}</g>')


# ------------------------------------------------------------------ vintage photos
def photo_svg(name):
    W, H = PHOTO_W, PHOTO_H
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
    elif name == "teahouse":
        sc = (f'<path d="M0 70 Q40 50 80 62 Q120 40 170 58 V128 H0Z" fill="{Lt}"/><rect x="0" y="96" width="170" height="32" fill="#cdb187"/>'
              f'<rect x="58" y="62" width="54" height="30" fill="#c9a876"/><path d="M40 64 Q85 54 130 64 Q120 56 112 52 H58 Q50 56 40 64Z" fill="{D}"/>'
              f'<path d="M52 50 Q85 40 118 50 Q110 42 104 38 H66 Q60 42 52 50Z" fill="{D}"/><rect x="82" y="30" width="6" height="9" fill="{D}"/>'
              f'<rect x="64" y="66" width="4" height="26" fill="{D}"/><rect x="102" y="66" width="4" height="26" fill="{D}"/><rect x="76" y="70" width="18" height="22" fill="{M}"/>'
              + "".join(f'<ellipse cx="{x}" cy="72" rx="3" ry="4" fill="#e0b860"/><line x1="{x}" y1="64" x2="{x}" y2="68" stroke="{D}"/>' for x in (54, 116))
              + f'<path d="M150 30 Q140 60 146 96" stroke="{D}" stroke-width="3" fill="none"/>'
              + "".join(f'<path d="M{146+rnd.randint(-6,4)} {34+i*6} q{-8-rnd.randint(0,6)} 14 {-6-rnd.randint(0,4)} 30" stroke="{M}" stroke-width="1.4" fill="none"/>' for i in range(8))
              + "".join(f'<path d="M{x} {104+rnd.randint(0,16)} h{rnd.randint(10,22)}" stroke="#efe2c4" stroke-width="1" opacity=".7"/>' for x in range(0, 170, 18))
              + f'<path d="M30 96 Q85 82 140 96" stroke="{D}" stroke-width="3" fill="none"/>')
    elif name == "hacienda":
        sc = (f'<path d="M0 74 Q30 54 70 66 Q110 48 170 62 V128 H0Z" fill="{Lt}"/><rect x="0" y="100" width="170" height="28" fill="{M}"/>'
              f'<rect x="20" y="62" width="112" height="40" fill="#d6bb8a"/><path d="M16 64 L136 64 L132 56 L20 56Z" fill="{M}"/>'
              + "".join(f'<path d="M{x} 102 V86 Q{x} 74 {x+9} 74 Q{x+18} 74 {x+18} 86 V102Z" fill="{D}"/>' for x in (28, 54, 80, 106))
              + "".join(f'<path d="M{x} 59 q2 -3 4 0" stroke="{D}" stroke-width="1" fill="none"/>' for x in range(22, 132, 6))
              + f'<path d="M150 104 V64 Q150 58 154 58 Q158 58 158 64 V104Z" fill="{D}"/>'
              + f'<path d="M150 84 H144 Q142 84 142 80 V72 Q142 68 145 68 Q147 68 147 72 V78 H150Z M158 80 H163 Q165 80 165 76 V68 Q165 64 162 64 Q160 64 160 68 V74 H158Z" fill="{D}"/>'
              + "".join(f'<circle cx="{x}" cy="{108+rnd.randint(0,10)}" r="{rnd.uniform(1.5,3):.1f}" fill="{D}" opacity=".6"/>' for x in range(4, 170, 11)))
    elif name == "village":
        sc = (f'<path d="M0 78 Q50 62 100 72 T170 66 V128 H0Z" fill="{Lt}"/><rect x="0" y="100" width="170" height="28" fill="#c9a876"/>'
              + "".join(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#b7976a"/><path d="M{x-8} {y+2} L{x+w/2} {y-h*.9:.0f} L{x+w+8} {y+2}Z" fill="{D}"/>'
                        f'<rect x="{x+w/2-4}" y="{y+h-14}" width="8" height="14" fill="{D}"/>' for x, y, w, h in ((18, 76, 34, 26), (70, 70, 40, 30), (124, 80, 30, 22)))
              + f'<path d="M160 104 V40" stroke="{D}" stroke-width="4"/>'
              + "".join(f'<path d="M160 42 q{dx} {dy} {dx*1.6:.0f} {dy+14}" stroke="{D}" stroke-width="3" fill="none"/>' for dx, dy in ((-22, -6), (22, -6), (-18, 4), (18, 4), (0, -12)))
              + f'<circle cx="40" cy="30" r="14" fill="#f2e2b8" opacity=".8"/>'
              + "".join(f'<ellipse cx="{x}" cy="{112+rnd.randint(0,8)}" rx="{rnd.randint(4,8)}" ry="3" fill="{M}" opacity=".7"/>' for x in range(6, 170, 17)))
    elif name == "seaside":
        sc = (f'<rect y="56" width="170" height="40" fill="{M}"/>' + "".join(f'<path d="M{x} {62+i*7} h{14+(i*7)%10}" stroke="#efe2c4" stroke-width="1" opacity=".6"/>' for i, x in enumerate(range(6, 160, 22)))
              + f'<path d="M0 92 Q60 82 120 90 T170 88 V128 H0Z" fill="#d8c08a"/><circle cx="120" cy="34" r="12" fill="#f2e2b8" opacity=".85"/>'
              + f'<rect x="80" y="70" width="40" height="24" fill="#c9a876"/><path d="M74 72 L100 54 L126 72Z" fill="{D}"/><rect x="96" y="80" width="8" height="14" fill="{D}"/>'
              + f'<path d="M36 124 Q30 80 44 44" stroke="{D}" stroke-width="4" fill="none"/>'
              + "".join(f'<path d="M44 44 q{dx} {dy} {dx*1.7:.0f} {dy+16}" stroke="{D}" stroke-width="3.4" fill="none"/>' for dx, dy in ((-24, -8), (24, -8), (-18, 4), (20, 4), (2, -14)))
              + f'<path d="M136 128 Q140 104 150 92" stroke="{D}" stroke-width="3" fill="none"/>'
              + "".join(f'<path d="M150 92 q{dx} {dy} {dx*1.5:.0f} {dy+12}" stroke="{D}" stroke-width="2.6" fill="none"/>' for dx, dy in ((-16, -6), (16, -6), (-12, 4), (14, 4)))
              + "".join(f'<ellipse cx="{x}" cy="{110+rnd.randint(0,10)}" rx="{rnd.randint(3,6)}" ry="2" fill="{M}" opacity=".6"/>' for x in range(4, 170, 19)))
    elif name == "boulangerie":
        sc = (f'<rect x="0" y="0" width="170" height="128" fill="#b8956a"/><rect x="14" y="10" width="142" height="100" fill="#c9a876"/>'
              f'<rect x="24" y="16" width="122" height="16" fill="{D}"/><path d="M40 24 h90" stroke="#efe2c4" stroke-width="3" stroke-dasharray="7 4"/>'
              + "".join(f'<path d="M{x} 36 h14 l-3 14 h-8Z" fill="{D if i % 2 else M}"/>' for i, x in enumerate(range(14, 156, 14)))
              + f'<rect x="22" y="56" width="70" height="42" fill="{D}"/><rect x="104" y="56" width="40" height="54" fill="{M}"/><rect x="108" y="60" width="32" height="24" fill="{D}"/>'
              + "".join(f'<path d="M{28+i*14} 94 L{38+i*14} 64" stroke="#d6bb8a" stroke-width="5" stroke-linecap="round"/>' for i in range(5))
              + f'<path d="M22 76 h70" stroke="#a8855a" stroke-width="2"/><circle cx="136" cy="96" r="2" fill="#efe2c4"/>'
              + f'<rect x="0" y="110" width="170" height="18" fill="{M}"/>' + "".join(f'<path d="M{x} 110 v18 M{x+9} 119 h-18" stroke="{D}" stroke-width=".8" opacity=".6"/>' for x in range(9, 170, 18))
              + f'<path d="M156 30 V100" stroke="{D}" stroke-width="2"/><circle cx="160" cy="46" r="8" fill="{D}"/>')
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


def dumpling(cx, cy, ang, s, rnd):
    g = uid("dp")
    pleats = "".join(f'<path d="M{x} {-27+abs(x)*.12:.1f} q4 7 {2+x*.04:.1f} 14" stroke="#c9b48a" stroke-width="2" fill="none"/>' for x in range(-28, 30, 9))
    return (f'<radialGradient id="{g}" cx=".45" cy=".35" r=".7"><stop offset="0" stop-color="#fbf4e2"/><stop offset=".7" stop-color="#ead9b4"/><stop offset="1" stop-color="#d4bb88"/></radialGradient>'
            f'<g transform="translate({cx} {cy}) rotate({ang}) scale({s})">'
            f'<path d="M-50 10 Q-46 -32 0 -36 Q46 -32 50 10 Q0 30 -50 10Z" fill="url(#{g})" stroke="#b8935a" stroke-width="1.5"/>'
            + flecks(0, -4, 34, 14, 14, rnd, ("#6a9a3a", "#88b050"), (1.2, 2.6)).replace("/>", ' opacity=".35"/>')
            + f'<path d="M-47 12 Q0 30 47 12" stroke="#c07a2c" stroke-width="6" fill="none" stroke-linecap="round" opacity=".85"/>'
            f'<path d="M-42 13 Q0 27 42 13" stroke="#ecc074" stroke-width="2" fill="none" stroke-linecap="round" opacity=".8"/>'
            f'<path d="M-36 -24 Q0 -38 36 -24" stroke="#d4bd8e" stroke-width="5" fill="none"/>{pleats}'
            f'<ellipse cx="-14" cy="-14" rx="16" ry="6" fill="#fff" opacity=".45"/></g>')


def dish_dumplings(rnd):
    b = plate(286, 214, 184, rnd, rim="#dfe6e8")
    b += '<circle cx="286" cy="214" r="128" fill="none" stroke="#3b6e8f" stroke-width="3" opacity=".7"/><circle cx="286" cy="214" r="120" fill="none" stroke="#3b6e8f" stroke-width="1.2" opacity=".6"/>'
    for i in range(6):
        a = i * math.tau / 6 + .3
        b += dumpling(286 + 84 * math.cos(a), 214 + 84 * math.sin(a), math.degrees(a) - 90, .92, rnd)
    b += dumpling(286, 210, -10, .9, rnd)
    b += scallion_rings(286, 214, 104, 104, 9, rnd, (2.5, 4))
    b += (f'<ellipse cx="528" cy="104" rx="66" ry="66" fill="#000" opacity=".55" filter="url(#soft)"/>'
          f'<circle cx="522" cy="96" r="62" fill="#e9eef0" stroke="#7c95a6" stroke-width="3"/><circle cx="522" cy="96" r="54" fill="#2c1a0e"/>'
          f'<circle cx="522" cy="96" r="54" fill="none" stroke="#5a3a1e" stroke-width="3"/>')
    b += "".join(f'<circle cx="{522+rnd.uniform(-38,38):.0f}" cy="{96+rnd.uniform(-34,34):.0f}" r="{rnd.uniform(2.5,6):.1f}" fill="#d0461c" opacity=".8"/>' for _ in range(14))
    b += "".join(f'<path d="M{522+rnd.uniform(-30,20):.0f} {96+rnd.uniform(-26,26):.0f} l{rnd.uniform(10,22):.0f} {rnd.uniform(-6,6):.0f}" stroke="#f2d48a" stroke-width="2"/>' for _ in range(8))
    b += ('<g filter="url(#shadow)"><path d="M420 396 L606 224" stroke="#2a1a12" stroke-width="11" stroke-linecap="round"/><path d="M444 400 L610 246" stroke="#2a1a12" stroke-width="11" stroke-linecap="round"/>'
          '<path d="M424 390 L600 228 M448 394 L604 250" stroke="#8a6a4a" stroke-width="2" opacity=".6"/></g>')
    b += scallion(54, 380, 150, 58) + ginger(70, 70, .8, 30)
    return b


def dish_huevos(rnd):
    b = plate(300, 206, 188, rnd, rim="#e3c9a2")
    for (x, y) in ((262, 194), (340, 216)):
        b += f'<circle cx="{x}" cy="{y}" r="104" fill="#e6c584" stroke="#c49a56" stroke-width="2"/>'
        b += flecks(x, y, 98, 98, 40, rnd, ("#8a5a2a", "#6b3e1a", "#a8743a"), (1.5, 5)).replace("/>", ' opacity=".55"/>')
    b += f'<path d="{blob(300, 210, 112, rnd, .2, 14)}" fill="#b02c18" opacity=".92"/><path d="{blob(300, 210, 108, rnd, .2, 14)}" filter="url(#crust)" opacity=".3"/>'
    b += flecks(300, 210, 100, 100, 50, rnd, ("#d9482a", "#e8603a", "#7a1a0c"), (2, 5))
    for _ in range(22):
        x, y = 210 + rnd.uniform(-30, 30), 280 + rnd.uniform(-16, 18)
        b += f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="7" ry="4.5" transform="rotate({rnd.uniform(0,180):.0f} {x:.0f} {y:.0f})" fill="{rnd.choice(("#1c1214", "#2a1c20", "#33242a"))}" stroke="#4a3a3e" stroke-width=".6"/>'
    for (x, y) in ((252, 172), (352, 196)):
        g = uid("yk")
        b += (f'<path d="{blob(x, y, 60, rnd, .14)}" fill="#c48a4a"/><path d="{blob(x, y, 55, rnd, .1)}" fill="#fbf8f0"/>'
              f'<radialGradient id="{g}" cx=".38" cy=".35" r=".7"><stop offset="0" stop-color="#ffe27a"/><stop offset=".6" stop-color="#f6a81a"/><stop offset="1" stop-color="#d9800c"/></radialGradient>'
              f'<circle cx="{x+6}" cy="{y+6}" r="23" fill="#8a5a1a" opacity=".35"/><circle cx="{x+4}" cy="{y+2}" r="23" fill="url(#{g})"/><ellipse cx="{x-4}" cy="{y-6}" rx="7" ry="4" fill="#fff" opacity=".6"/>')
    for i in range(4):
        g = uid("av")
        b += (f'<linearGradient id="{g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e4ec9a"/><stop offset=".7" stop-color="#9ac04a"/><stop offset="1" stop-color="#2f4a12"/></linearGradient>'
              f'<g transform="translate(372 286) rotate({-62 + i * 16})"><path d="M0 0 C20 -14 70 -14 92 -2 C70 10 20 10 0 0Z" fill="url(#{g})" stroke="#2a3a10" stroke-width="2"/></g>')
    b += flecks(300, 200, 120, 110, 40, rnd, ("#fbf8ee", "#efe9da"), (2.5, 5))
    for (x, y, a) in ((200, 150, -30), (300, 120, 20), (410, 240, 60), (260, 260, -70)):
        b += cilantro(x, y, 34, a, .55)
    b += lemon_slice(530, 336, 44, half=True, c=LIME_SLICE) + lemon(70, 70, 40, 32, 30, LIME) + cilantro(80, 390, 90, 20, .8)
    return b


def dish_manakish(rnd):
    b = (f'<ellipse cx="300" cy="216" rx="250" ry="174" fill="#000" opacity=".6" filter="url(#soft)"/>'
         f'<rect x="60" y="30" width="460" height="350" rx="30" fill="#9a6a38"/><rect x="60" y="30" width="460" height="350" rx="30" filter="url(#wood)" opacity=".85"/>'
         f'<rect x="60" y="30" width="460" height="350" rx="30" fill="none" stroke="#5a3616" stroke-width="4"/>'
         f'<rect x="490" y="180" width="80" height="40" rx="18" fill="#9a6a38" stroke="#5a3616" stroke-width="3"/>')
    g, z = uid("fb"), uid("za")
    b += (f'<radialGradient id="{g}" cx=".45" cy=".4" r=".65"><stop offset="0" stop-color="#e8bb70"/><stop offset=".75" stop-color="#d09444"/><stop offset="1" stop-color="#8a5418"/></radialGradient>'
          f'<path d="{blob(290, 204, 150, rnd, .04, 24)}" fill="url(#{g})" filter="url(#shadow)"/>'
          f'<radialGradient id="{z}" cx=".42" cy=".38" r=".7"><stop offset="0" stop-color="#8a8434"/><stop offset=".7" stop-color="#5e5a20"/><stop offset="1" stop-color="#4a4416"/></radialGradient>'
          f'<path d="{blob(290, 204, 124, rnd, .05, 22)}" fill="url(#{z})"/><circle cx="290" cy="204" r="122" filter="url(#crust)" opacity=".35"/>')
    b += flecks(290, 204, 118, 118, 260, rnd, ("#2e2e0c", "#3e3e12", "#6c6a22", "#7a2a14"), (1, 2.6))
    b += sesame(290, 204, 116, 116, 70, rnd)
    b += "".join(f'<circle cx="{290+rnd.uniform(-90,90):.0f}" cy="{204+rnd.uniform(-90,90):.0f}" r="{rnd.uniform(5,9):.0f}" fill="#2a2808" opacity=".25"/>' for _ in range(18))
    b += '<ellipse cx="250" cy="160" rx="60" ry="26" fill="#fff6c0" opacity=".12" transform="rotate(-25 250 160)"/>'
    b += '<path d="M290 204 L290 56 M290 204 L418 278 M290 204 L162 278" stroke="#3a2a0c" stroke-width="3" opacity=".55"/>'
    b += (f'<ellipse cx="536" cy="78" rx="50" ry="50" fill="#000" opacity=".5" filter="url(#soft)"/><circle cx="530" cy="72" r="46" fill="#efe6d4" stroke="#8c6a44" stroke-width="3"/>'
          f'<circle cx="530" cy="72" r="38" fill="#b7a228"/><circle cx="530" cy="72" r="38" fill="#e8d04a" opacity=".35"/><ellipse cx="518" cy="60" rx="14" ry="7" fill="#fff" opacity=".35"/>')
    for (x, y) in ((540, 330), (500, 360), (560, 380)):
        b += (f'<circle cx="{x}" cy="{y}" r="28" fill="#3f6a1e"/><circle cx="{x}" cy="{y}" r="24" fill="#cfe2a0"/><circle cx="{x}" cy="{y}" r="14" fill="#b6d080"/>'
              + "".join(f'<ellipse cx="{x+8*math.cos(a):.1f}" cy="{y+8*math.sin(a):.1f}" rx="2.6" ry="1.6" fill="#f2f6d8" transform="rotate({math.degrees(a):.0f} {x+8*math.cos(a):.1f} {y+8*math.sin(a):.1f})"/>' for a in [k * math.tau / 6 for k in range(6)]))
    b += leaf(80, 380, 54, 22, -30, "#5aa03a", "#2f6a1e", "#b4e08a") + leaf(100, 384, 46, 20, 20, "#5aa03a", "#2f6a1e", "#b4e08a") + leaf(560, 260, 44, 18, 70, "#5aa03a", "#2f6a1e", "#b4e08a")
    b += olive(40, 120, 12, 17, 20) + olive(52, 146, 12, 17, -10, False)
    return b


def dish_mango(rnd):
    b = plate(300, 206, 188, rnd)
    b += ('<g transform="translate(296 206) rotate(-30)"><path d="M-130 -70 L130 -70 L130 70 L-130 70Z" fill="#3f7a2a" stroke="#2a5a1a" stroke-width="2"/>'
          + "".join(f'<path d="M{x} -70 L{x+16} 70" stroke="#5f9a3a" stroke-width="1.5" opacity=".7"/>' for x in range(-126, 126, 14))
          + '<path d="M-130 0 L130 0" stroke="#8ab85a" stroke-width="4"/></g>')
    g = uid("ri")
    b += (f'<radialGradient id="{g}" cx=".42" cy=".35" r=".7"><stop offset="0" stop-color="#ffffff"/><stop offset=".7" stop-color="#f2ecdc"/><stop offset="1" stop-color="#cfc4a4"/></radialGradient>'
          f'<path d="{blob(232, 204, 90, rnd, .06)}" fill="url(#{g})" filter="url(#shadow)"/>')
    for _ in range(240):
        a, d = rnd.uniform(0, math.tau), 84 * math.sqrt(rnd.random())
        x, y = 232 + d * math.cos(a), 204 + d * math.sin(a)
        b += f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="5.5" ry="2.4" transform="rotate({rnd.uniform(0,180):.0f} {x:.0f} {y:.0f})" fill="{rnd.choice(("#ffffff", "#f6f1e2", "#e6dcc2"))}" opacity=".9"/>'
    b += f'<path d="{blob(226, 192, 52, rnd, .25, 12)}" fill="#fff8e2" opacity=".88"/><ellipse cx="212" cy="180" rx="20" ry="8" fill="#fff" opacity=".6"/>'
    b += sesame(228, 196, 60, 50, 26, rnd, ("#f6ead0", "#2a2018", "#e8d4a0"))
    for i in range(5):
        b += mango_slice(318, 268 - i * 4, 150, -58 + i * 15, 30)
    b += leaf(212, 132, 40, 16, -20, "#5aa03a", "#2f6a1e", "#b4e08a") + leaf(226, 130, 36, 14, 30, "#5aa03a", "#2f6a1e", "#b4e08a")
    b += mango(540, 88, .7, 30) + mango_slice(470, 372, 100, -20, 24)
    return b


# ------------------------------------------------------------------ growth run 2 ingredients
def peanut(cx, cy, ang, s=1.0, shelled=False):
    """A peanut in its shell (two lobes, waist, criss-cross texture) or a shelled half."""
    g = uid("pn")
    if shelled:
        return (f'<radialGradient id="{g}" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#f2d39a"/><stop offset=".7" stop-color="#d9a85c"/><stop offset="1" stop-color="#a8702e"/></radialGradient>'
                f'<g transform="translate({cx} {cy}) rotate({ang}) scale({s})"><ellipse rx="9" ry="6.5" fill="url(#{g})" stroke="#8a5a24" stroke-width=".8"/>'
                f'<path d="M-6 0 Q0 -2 6 0" stroke="#8a5a24" stroke-width=".7" fill="none" opacity=".6"/></g>')
    tex = "".join(f'<path d="M{x} -12 L{x+6} 12" stroke="#a8803e" stroke-width=".8" opacity=".5"/>' for x in range(-30, 30, 7))
    return (f'<radialGradient id="{g}" cx=".4" cy=".3" r=".8"><stop offset="0" stop-color="#ecd2a0"/><stop offset=".7" stop-color="#cfa766"/><stop offset="1" stop-color="#9a7238"/></radialGradient>'
            f'<g transform="translate({cx} {cy}) rotate({ang}) scale({s})">'
            f'<path d="M-30 0 C-30 -16 -12 -17 -6 -9 Q0 -5 6 -9 C12 -17 30 -16 30 0 C30 16 12 17 6 9 Q0 5 -6 9 C-12 17 -30 16 -30 0Z" fill="url(#{g})" stroke="#8a6230" stroke-width="1.2"/>'
            f'{tex}<ellipse cx="-16" cy="-6" rx="8" ry="3" fill="#fff" opacity=".3"/></g>')


def cucumber_slice(cx, cy, r, ang=0, ry=None):
    ry = ry or r
    seeds = "".join(f'<ellipse cx="{r*.32*math.cos(a):.1f}" cy="{ry*.32*math.sin(a):.1f}" rx="{r*.08:.1f}" ry="{r*.045:.1f}" '
                    f'transform="rotate({math.degrees(a):.0f} {r*.32*math.cos(a):.1f} {ry*.32*math.sin(a):.1f})" fill="#f4f8dc" opacity=".9"/>'
                    for a in [k * math.tau / 7 for k in range(7)])
    return (f'<g transform="translate({cx} {cy}) rotate({ang})"><ellipse rx="{r}" ry="{ry}" fill="#2f5a1a"/><ellipse rx="{r*.9:.1f}" ry="{ry*.9:.1f}" fill="#9fc55a"/>'
            f'<ellipse rx="{r*.8:.1f}" ry="{ry*.8:.1f}" fill="#d4e8a0"/><ellipse rx="{r*.45:.1f}" ry="{ry*.45:.1f}" fill="#bcd884"/>{seeds}'
            f'<ellipse cx="{-r*.3:.1f}" cy="{-ry*.35:.1f}" rx="{r*.25:.1f}" ry="{ry*.12:.1f}" fill="#fff" opacity=".35"/></g>')


def cucumber(cx, cy, ln, ang, wd=34):
    g = uid("cu")
    bumps = "".join(f'<circle cx="{x}" cy="{(-1)**i * wd*.25:.1f}" r="1.6" fill="#c8e090" opacity=".7"/>' for i, x in enumerate(range(int(-ln/2) + 14, int(ln/2) - 10, 11)))
    return (f'<linearGradient id="{g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5e9a34"/><stop offset=".45" stop-color="#2f6a1c"/><stop offset="1" stop-color="#173d0c"/></linearGradient>'
            f'<g transform="translate({cx} {cy}) rotate({ang})"><rect x="{-ln/2}" y="{-wd/2}" width="{ln}" height="{wd}" rx="{wd/2}" fill="url(#{g})"/>'
            f'<path d="M{-ln/2+14} {-wd*.22:.1f} L{ln/2-14} {-wd*.22:.1f}" stroke="#b8d888" stroke-width="3" opacity=".35" stroke-linecap="round"/>{bumps}'
            f'<ellipse cx="{ln/2-3}" cy="0" rx="5" ry="{wd*.32:.1f}" fill="#c8a85a"/></g>')


def mint_sprig(x, y, ln, ang, k=1.0):
    out = [f'<path d="M0 0 Q{ln*.08} {-ln*.5} 0 {-ln}" stroke="#4a6a2a" stroke-width="{2.6*k:.1f}" fill="none"/>']
    for i, t in enumerate((.35, .55, .75, .92)):
        s = (1.15 - t * .55) * k
        for side in (-1, 1):
            g = uid("mt")
            out.append(f'<linearGradient id="{g}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7ac25a"/><stop offset="1" stop-color="#2f7a32"/></linearGradient>'
                       f'<g transform="translate(0 {-ln*t:.1f}) rotate({side*(62 - i*8)}) scale({s:.2f})">'
                       f'<path d="M0 0 C12 -6 16 -26 0 -40 C-16 -26 -12 -6 0 0Z" fill="url(#{g})" stroke="#24602a" stroke-width="1"/>'
                       f'<path d="M0 -2 L0 -36" stroke="#b8e0a0" stroke-width="1" opacity=".7"/>'
                       + "".join(f'<path d="M0 {-v} l{6*sd} -5" stroke="#b8e0a0" stroke-width=".7" opacity=".6"/>' for v in (10, 18, 26) for sd in (-1, 1))
                       + '</g>')
    out.append(f'<g transform="translate(0 {-ln})"><path d="M0 0 C9 -5 11 -20 0 -30 C-11 -20 -9 -5 0 0Z" fill="#6ab04a" stroke="#24602a" stroke-width="1" transform="scale({k:.2f})"/></g>')
    return f'<g transform="translate({x} {y}) rotate({ang})">' + "".join(out) + "</g>"


def sugar_cube(cx, cy, s, ang):
    return (f'<g transform="translate({cx} {cy}) rotate({ang})"><rect x="{-s/2}" y="{-s/2}" width="{s}" height="{s}" rx="2" fill="#fbf8f0" stroke="#d8d0bc" stroke-width="1"/>'
            f'<path d="M{-s/2} {-s/2} l{s*.25} {-s*.2} h{s} l{-s*.25} {s*.2}Z" fill="#ffffff" stroke="#d8d0bc" stroke-width=".8"/>'
            f'<path d="M{s/2} {-s/2} l{s*.25} {-s*.2} v{s} l{-s*.25} {s*.2}Z" fill="#e8e2d0" stroke="#d8d0bc" stroke-width=".8"/></g>')


def bell_pepper(cx, cy, s, ang, c=("#ff7a5a", "#d8281a", "#7a0c08")):
    g = uid("bp")
    return (f'<radialGradient id="{g}" cx=".35" cy=".35" r=".8"><stop offset="0" stop-color="{c[0]}"/><stop offset=".5" stop-color="{c[1]}"/><stop offset="1" stop-color="{c[2]}"/></radialGradient>'
            f'<g transform="translate({cx} {cy}) rotate({ang}) scale({s})">'
            f'<path d="M-44 -30 C-58 0 -50 44 -24 52 C-12 56 -4 48 0 44 C4 48 12 56 24 52 C50 44 58 0 44 -30 C34 -46 12 -44 0 -38 C-12 -44 -34 -46 -44 -30Z" fill="url(#{g})" stroke="#6a0c08" stroke-width="1.5"/>'
            f'<path d="M0 -36 C-4 0 -4 30 0 44" stroke="#7a0c08" stroke-width="2" opacity=".45" fill="none"/>'
            f'<ellipse cx="-24" cy="-12" rx="7" ry="22" fill="#fff" opacity=".3" transform="rotate(8 -24 -12)"/>'
            f'<path d="M-16 -40 Q0 -50 16 -40 Q8 -34 0 -36 Q-8 -34 -16 -40Z" fill="#3f6a1e"/>'
            f'<path d="M0 -40 Q2 -56 12 -64" stroke="#4f7a22" stroke-width="7" fill="none" stroke-linecap="round"/></g>')


def pepper_strip(x, y, ln, ang, c="#d8281a"):
    return (f'<g transform="translate({x} {y}) rotate({ang})"><path d="M0 0 Q{ln*.5} -10 {ln} 0 Q{ln*.5} -2 0 8Z" fill="{c}" stroke="#7a0c08" stroke-width="1"/>'
            f'<path d="M{ln*.15} 1 Q{ln*.5} -6 {ln*.85} 0" stroke="#fff" stroke-width="1.5" opacity=".35" fill="none"/></g>')


def empanada(cx, cy, ang, s, rnd):
    g = uid("em")
    rope = "".join(f'<ellipse cx="{82*math.cos(a):.1f}" cy="{6 + 50*math.sin(a):.1f}" rx="9" ry="5.5" transform="rotate({math.degrees(a)+60:.0f} {82*math.cos(a):.1f} {6 + 50*math.sin(a):.1f})" fill="#c9852e" stroke="#8a4e14" stroke-width="1"/>'
                   for a in [math.pi + k * math.pi / 13 for k in range(14)])
    return (f'<radialGradient id="{g}" cx=".45" cy=".3" r=".85"><stop offset="0" stop-color="#f6c66e"/><stop offset=".55" stop-color="#d9913a"/><stop offset="1" stop-color="#9a5818"/></radialGradient>'
            f'<g transform="translate({cx} {cy}) rotate({ang}) scale({s})" filter="url(#shadow)">'
            f'<path d="M-82 6 A82 62 0 0 1 82 6 Q0 20 -82 6Z" fill="url(#{g})" stroke="#8a4e14" stroke-width="1.5"/>'
            f'<path d="M-82 6 A82 62 0 0 1 82 6" fill="none" stroke="#7a4210" stroke-width="1" opacity=".5" filter="url(#crust)"/>{rope}'
            + flecks(0, -24, 52, 18, 14, rnd, ("#fbe0a0", "#e8b060"), (1.5, 3.5)).replace("/>", ' opacity=".6"/>')
            + f'<ellipse cx="-20" cy="-30" rx="30" ry="9" fill="#fff6d0" opacity=".35"/></g>')


def tea_glass(cx, cy, s, tint="#c8862a"):
    g = uid("tg")
    pattern = "".join(f'<path d="M{x} -10 q5 8 0 16 q-5 8 0 16" stroke="#e8c060" stroke-width="2" fill="none" opacity=".8"/>' for x in (-22, -8, 6, 20))
    return (f'<linearGradient id="{g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e8c06a" stop-opacity=".9"/><stop offset=".25" stop-color="{tint}"/><stop offset="1" stop-color="#6a3a0c"/></linearGradient>'
            f'<g transform="translate({cx} {cy}) scale({s})">'
            f'<ellipse cx="4" cy="44" rx="36" ry="12" fill="#000" opacity=".45" filter="url(#soft)"/>'
            f'<path d="M-30 -40 L30 -40 L24 40 Q0 48 -24 40Z" fill="url(#{g})" stroke="#f4e8c8" stroke-width="2" opacity=".95"/>'
            f'<ellipse cx="0" cy="-34" rx="29" ry="6" fill="#f6ecd0" opacity=".85"/>{pattern}'
            f'<path d="M-24 -36 L-19 36" stroke="#fff" stroke-width="4" opacity=".35"/><ellipse cx="0" cy="-40" rx="30" ry="6" fill="none" stroke="#f4e8c8" stroke-width="2"/></g>')


def dish_peanut_soup(rnd):
    b = (f'<ellipse cx="300" cy="216" rx="176" ry="176" fill="#000" opacity=".6" filter="url(#soft)"/>'
         f'<circle cx="294" cy="202" r="172" fill="#8a4a22" stroke="#4a2410" stroke-width="3"/><circle cx="294" cy="202" r="172" filter="url(#crust)" opacity=".5"/>'
         f'<circle cx="294" cy="202" r="150" fill="#e4d2b0" stroke="#6a3a1a" stroke-width="2"/>')
    b += ('<radialGradient id="pns"><stop offset="0" stop-color="#e09a4a"/><stop offset=".75" stop-color="#c46a26"/><stop offset="1" stop-color="#8e4414"/></radialGradient>'
          '<circle cx="294" cy="202" r="136" fill="url(#pns)"/><circle cx="294" cy="202" r="134" filter="url(#crust)" opacity=".3"/>')
    for _ in range(9):  # sweet potato cubes
        x, y = 294 + rnd.uniform(-90, 90), 202 + rnd.uniform(-90, 90)
        if (x - 294) ** 2 + (y - 202) ** 2 < 100 ** 2:
            b += f'<rect x="{x:.0f}" y="{y:.0f}" width="22" height="20" rx="4" transform="rotate({rnd.uniform(0,90):.0f} {x:.0f} {y:.0f})" fill="#f09a3a" stroke="#b0581a" stroke-width="1"/>'
    for _ in range(16):  # kale
        x, y = 294 + rnd.uniform(-100, 100), 202 + rnd.uniform(-100, 100)
        if (x - 294) ** 2 + (y - 202) ** 2 < 110 ** 2:
            b += f'<path d="{blob(x, y, rnd.uniform(9, 15), rnd, .35, 9)}" fill="{rnd.choice(("#2f5a1e", "#3f6e26", "#24481a"))}" opacity=".9"/>'
    b += '<path d="M220 150 q40 -20 80 0 q40 20 80 -4" stroke="#f0c890" stroke-width="5" fill="none" opacity=".45" stroke-linecap="round"/>'
    for _ in range(26):
        a, d = rnd.uniform(0, math.tau), 60 * math.sqrt(rnd.random())
        b += peanut(294 + d * math.cos(a) - 10, 196 + d * math.sin(a) * .7, rnd.uniform(0, 180), .9, shelled=True)
    for (x, y, a) in ((250, 190, -30), (330, 220, 40), (300, 160, 0)):
        b += cilantro(x, y, 30, a, .5)
    b += flecks(294, 202, 120, 120, 24, rnd, ("#a8240f", "#c43a1a"), (1.2, 2.4))
    b += peanut(500, 320, -30, 1.4) + peanut(530, 280, 20, 1.2) + peanut(470, 356, 60, 1.1)
    b += chili(470, 70, 90, 20, "#e0681a") + leaf(80, 350, 60, 22, -30, "#3f6e26") + leaf(104, 372, 50, 18, 20, "#2f5a1e")
    return b


def dish_cucumber(rnd):
    b = (f'<ellipse cx="300" cy="220" rx="190" ry="160" fill="#000" opacity=".6" filter="url(#soft)"/>'
         f'<ellipse cx="294" cy="206" rx="188" ry="156" fill="#d8d4c8" stroke="#6a7a8a" stroke-width="3"/>'
         f'<ellipse cx="294" cy="206" rx="168" ry="138" fill="#eef0ea" stroke="#b8c0c4" stroke-width="2"/>'
         f'<ellipse cx="294" cy="206" rx="178" ry="146" fill="none" stroke="#3a5a7a" stroke-width="2" opacity=".6"/>')
    sl = []
    for _ in range(30):
        a, d = rnd.uniform(0, math.tau), math.sqrt(rnd.random())
        sl.append((294 + 120 * d * math.cos(a), 206 + 96 * d * math.sin(a)))
    sl.sort(key=lambda p: p[1])
    for (x, y) in sl:
        b += cucumber_slice(x, y, rnd.uniform(22, 28), rnd.uniform(0, 180), rnd.uniform(17, 22))
    b += flecks(294, 206, 130, 104, 120, rnd, ("#c8281a", "#e0401a", "#9a1a0a"), (1, 2.4))
    b += sesame(294, 206, 120, 96, 40, rnd)
    for _ in range(14):
        x, y = 294 + rnd.uniform(-110, 110), 206 + rnd.uniform(-80, 80)
        b += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="5" fill="none" stroke="#5aa03a" stroke-width="2.4"/>'
    b += '<ellipse cx="240" cy="150" rx="60" ry="18" fill="#fff" opacity=".18" transform="rotate(-20 240 150)"/>'
    b += cucumber(470, 340, 170, -20) + cucumber_slice(80, 80, 30, 0) + cucumber_slice(110, 120, 26, 40, 20)
    b += (f'<ellipse cx="540" cy="90" rx="46" ry="46" fill="#000" opacity=".5" filter="url(#soft)"/><circle cx="534" cy="84" r="42" fill="#efe6d4" stroke="#6a7a8a" stroke-width="3"/>'
          f'<circle cx="534" cy="84" r="34" fill="#b8281a"/>') + flecks(534, 84, 30, 30, 60, rnd, ("#e0401a", "#7a1a0a", "#f06a3a"), (1, 2.2))
    return b


def dish_mint_tea(rnd):
    b = ('<ellipse cx="300" cy="222" rx="236" ry="164" fill="#000" opacity=".6" filter="url(#soft)"/>'
         '<radialGradient id="tray" cx=".4" cy=".35" r=".8"><stop offset="0" stop-color="#f4dc98"/><stop offset=".6" stop-color="#c9a048"/><stop offset="1" stop-color="#7a5418"/></radialGradient>'
         '<ellipse cx="294" cy="208" rx="232" ry="160" fill="url(#tray)" stroke="#6a4810" stroke-width="3"/>'
         '<ellipse cx="294" cy="208" rx="212" ry="142" fill="none" stroke="#8a6420" stroke-width="2"/>')
    b += "".join(f'<path d="M{294+186*math.cos(a):.1f} {208+124*math.sin(a):.1f} l{6*math.cos(a+1):.1f} {6*math.sin(a+1):.1f}" stroke="#7a5418" stroke-width="2"/>' for a in [i * math.tau / 48 for i in range(48)])
    # teapot
    b += ('<g transform="translate(300 170)" filter="url(#shadow)">'
          '<radialGradient id="pot" cx=".35" cy=".35" r=".8"><stop offset="0" stop-color="#ffffff"/><stop offset=".4" stop-color="#d8dade"/><stop offset="1" stop-color="#7a7c82"/></radialGradient>'
          '<path d="M60 10 C110 0 130 -40 150 -70 L156 -66 C140 -30 120 20 64 34Z" fill="url(#pot)" stroke="#5a5c62" stroke-width="1.5"/>'
          '<path d="M-62 -4 C-110 -10 -110 50 -66 46" stroke="#8a8c92" stroke-width="10" fill="none"/>'
          '<ellipse cx="0" cy="12" rx="74" ry="56" fill="url(#pot)" stroke="#5a5c62" stroke-width="2"/>'
          '<ellipse cx="0" cy="56" rx="46" ry="10" fill="#9a9ca2"/>'
          '<path d="M-44 -30 Q0 -52 44 -30 L36 -40 Q0 -58 -36 -40Z" fill="#b8bac0" stroke="#5a5c62" stroke-width="1.5"/>'
          '<path d="M-24 -50 Q0 -90 24 -50Z" fill="url(#pot)" stroke="#5a5c62" stroke-width="1.5"/><circle cx="0" cy="-86" r="8" fill="#d8dade" stroke="#5a5c62"/>'
          + "".join(f'<path d="M{x} -10 q10 20 0 40" stroke="#8a6420" stroke-width="2" fill="none" opacity=".55"/>' for x in (-40, -14, 12, 38))
          + '<ellipse cx="-30" cy="-6" rx="14" ry="26" fill="#fff" opacity=".55" transform="rotate(20 -30 -6)"/></g>')
    b += tea_glass(140, 270, 1.0) + tea_glass(420, 300, 1.0) + tea_glass(220, 330, .9, "#b8781e")
    b += mint_sprig(142, 236, 46, -10, .5) + mint_sprig(420, 266, 46, 12, .5)
    b += mint_sprig(470, 170, 110, 30, .8) + mint_sprig(500, 190, 100, 52, .7)
    for (x, y, a) in ((90, 90, 10), (120, 70, -14), (104, 118, 30)):
        b += sugar_cube(x, y, 22, a)
    b += ('<path d="M300 90 q-12 -26 4 -46 q14 -18 0 -40" stroke="#fff" stroke-width="8" fill="none" opacity=".18" stroke-linecap="round" filter="url(#soft)"/>')
    return b


def dish_empanadas(rnd):
    b = (f'<ellipse cx="300" cy="216" rx="250" ry="174" fill="#000" opacity=".6" filter="url(#soft)"/>'
         f'<rect x="56" y="34" width="480" height="340" rx="22" fill="#a8743e"/><rect x="56" y="34" width="480" height="340" rx="22" filter="url(#wood)" opacity=".85"/>'
         f'<rect x="56" y="34" width="480" height="340" rx="22" fill="none" stroke="#5a3616" stroke-width="4"/>'
         f'<path d="M80 60 L520 60 L520 350 L80 350Z" fill="#efe2c4" opacity=".85" transform="rotate(-3 300 204)"/>')
    b += empanada(200, 140, -12, .95, rnd) + empanada(380, 120, 10, .95, rnd) + empanada(190, 280, 8, 1.0, rnd) + empanada(386, 268, -6, 1.0, rnd)
    b += (f'<ellipse cx="540" cy="340" rx="50" ry="50" fill="#000" opacity=".5" filter="url(#soft)"/><circle cx="534" cy="334" r="46" fill="#efe6d4" stroke="#8c6a44" stroke-width="3"/>'
          f'<circle cx="534" cy="334" r="38" fill="#4f6a1e"/>') + flecks(534, 334, 34, 34, 80, rnd, ("#7aa02a", "#2f4a12", "#c43a1a", "#a8c050"), (1.2, 3))
    b += bell_pepper(500, 96, .7, 20) + pepper_strip(446, 52, 50, 30) + cilantro(60, 380, 90, 20, .8) + olive(40, 110, 12, 17, 20, False)
    return b


# ------------------------------------------------------------------ growth run 3 ingredients
def tofu_cube(cx, cy, s, ang):
    return (f'<g transform="translate({cx} {cy}) rotate({ang})"><rect x="{-s/2}" y="{-s/2}" width="{s}" height="{s}" rx="{s*.12:.1f}" fill="#f4ecd4" stroke="#cfc29c" stroke-width="1"/>'
            f'<path d="M{-s/2} {-s/2} l{s*.22:.1f} {-s*.18:.1f} h{s} l{-s*.22:.1f} {s*.18:.1f}Z" fill="#fffaea" stroke="#d8ccaa" stroke-width=".8"/>'
            f'<path d="M{s/2} {-s/2} l{s*.22:.1f} {-s*.18:.1f} v{s} l{-s*.22:.1f} {s*.18:.1f}Z" fill="#e2d6b4" stroke="#cfc29c" stroke-width=".8"/>'
            f'<ellipse cx="{-s*.18:.1f}" cy="{-s*.15:.1f}" rx="{s*.2:.1f}" ry="{s*.08:.1f}" fill="#fff" opacity=".5"/></g>')


def wakame(x, y, ln, ang, wd=14):
    g = uid("wk")
    n = 6
    top = " ".join("Q%.1f %.1f %.1f %.1f" % (ln * (i + .5) / n, -wd * (1.4 if i % 2 else .6), ln * (i + 1) / n, -wd * .9) for i in range(n))
    bot = " ".join("Q%.1f %.1f %.1f %.1f" % (ln * (n - i - .5) / n, wd * (1.3 if i % 2 else .5), ln * (n - i - 1) / n, wd * .8) for i in range(n))
    return (f'<linearGradient id="{g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4f7a2e"/><stop offset=".5" stop-color="#2e5a1c"/><stop offset="1" stop-color="#1a3a10"/></linearGradient>'
            f'<g transform="translate({x} {y}) rotate({ang})"><path d="M0 {-wd*.9:.1f} {top} L{ln} {wd*.8:.1f} {bot}Z" fill="url(#{g})" opacity=".95"/>'
            f'<path d="M4 0 Q{ln*.5} -4 {ln-4} 0" stroke="#8ab85a" stroke-width="1.6" fill="none" opacity=".55"/></g>')


def scotch_bonnet(cx, cy, s, ang, c=("#ffd27a", "#f07a12", "#9a3a06")):
    g = uid("sb")
    return (f'<radialGradient id="{g}" cx=".35" cy=".3" r=".85"><stop offset="0" stop-color="{c[0]}"/><stop offset=".5" stop-color="{c[1]}"/><stop offset="1" stop-color="{c[2]}"/></radialGradient>'
            f'<g transform="translate({cx} {cy}) rotate({ang}) scale({s})">'
            f'<path d="M-34 -14 C-44 6 -36 30 -18 34 C-10 40 -4 32 0 28 C6 36 14 40 22 32 C40 26 44 2 34 -14 C26 -28 12 -26 0 -22 C-12 -28 -26 -28 -34 -14Z" fill="url(#{g})" stroke="{c[2]}" stroke-width="1.4"/>'
            f'<path d="M-14 -20 C-18 4 -14 24 -10 32 M14 -20 C18 4 16 24 12 32" stroke="{c[2]}" stroke-width="1.6" opacity=".45" fill="none"/>'
            f'<ellipse cx="-18" cy="-6" rx="6" ry="13" fill="#fff" opacity=".35" transform="rotate(10 -18 -6)"/>'
            f'<path d="M-14 -24 Q0 -32 14 -24 Q6 -20 0 -22 Q-6 -20 -14 -24Z" fill="#3f6a1e"/>'
            f'<path d="M0 -26 Q-2 -40 6 -48" stroke="#4f7a22" stroke-width="6" fill="none" stroke-linecap="round"/></g>')


def allspice(cx, cy, r=7):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#5a2e14" stroke="#2e160a" stroke-width="1"/>'
            f'<circle cx="{cx-r*.3:.1f}" cy="{cy-r*.35:.1f}" r="{r*.3:.1f}" fill="#9a6036" opacity=".7"/><circle cx="{cx+r*.2:.1f}" cy="{cy-r*.8:.1f}" r="{r*.22:.1f}" fill="#2e160a"/>')


def kidney_bean(cx, cy, ang, s=1.0):
    return (f'<g transform="translate({cx:.1f} {cy:.1f}) rotate({ang:.0f}) scale({s})"><path d="M-10 -3 C-10 -9 -2 -8 0 -5 C2 -8 10 -9 10 -3 C10 6 -10 6 -10 -3Z" fill="#7a1a1e" stroke="#4a0a10" stroke-width=".8"/>'
            f'<ellipse cx="-4" cy="-3" rx="3" ry="1.4" fill="#c86a6a" opacity=".6"/></g>')


def tomato(cx, cy, r, c=("#ff8a6a", "#d8301a", "#7a0c08")):
    g = uid("tm")
    cal = "".join(f'<path d="M0 0 Q{r*.12*math.cos(a+.5):.1f} {r*.12*math.sin(a+.5):.1f} {r*.5*math.cos(a):.1f} {r*.5*math.sin(a):.1f} Q{r*.12*math.cos(a-.5):.1f} {r*.12*math.sin(a-.5):.1f} 0 0Z" fill="#3f6a1e"/>'
                  for a in [k * math.tau / 5 - math.pi / 2 for k in range(5)])
    return (f'<radialGradient id="{g}" cx=".35" cy=".35" r=".8"><stop offset="0" stop-color="{c[0]}"/><stop offset=".55" stop-color="{c[1]}"/><stop offset="1" stop-color="{c[2]}"/></radialGradient>'
            f'<g transform="translate({cx} {cy})"><ellipse rx="{r}" ry="{r*.88:.1f}" fill="url(#{g})" stroke="{c[2]}" stroke-width="1"/>'
            f'<ellipse cx="{-r*.38:.1f}" cy="{-r*.3:.1f}" rx="{r*.22:.1f}" ry="{r*.13:.1f}" fill="#fff" opacity=".45" transform="rotate(-30 {-r*.38:.1f} {-r*.3:.1f})"/>'
            f'<g transform="translate(0 {-r*.62:.1f})">{cal}<path d="M0 0 q2 -6 -2 -12" stroke="#4f7a22" stroke-width="3" fill="none"/></g></g>')


def garlic_clove(cx, cy, s, ang):
    return (f'<g transform="translate({cx} {cy}) rotate({ang}) scale({s})"><path d="M-16 10 C-20 -6 -6 -20 4 -26 C2 -14 18 -4 14 10 C10 16 -12 16 -16 10Z" fill="#f6efe0" stroke="#c8b898" stroke-width="1.2"/>'
            f'<path d="M-8 8 C-8 -6 0 -16 4 -24" stroke="#d8ccb0" stroke-width="1.4" fill="none"/><path d="M4 -26 l2 -5" stroke="#b8a888" stroke-width="2"/></g>')


def baguette(x, y, ln, ang, wd=44, rnd=None, slashes=4):
    g = uid("bg")
    cuts = ""
    for i in range(slashes):
        t = (i + .7) / (slashes + .4)
        cx = -ln / 2 + ln * t
        cuts += (f'<path d="M{cx-ln*.09:.1f} {wd*.12:.1f} Q{cx:.1f} {-wd*.32:.1f} {cx+ln*.1:.1f} {-wd*.18:.1f} Q{cx:.1f} {-wd*.02:.1f} {cx-ln*.09:.1f} {wd*.12:.1f}Z" fill="#f2d79a" stroke="#8a5418" stroke-width="1"/>'
                 f'<path d="M{cx-ln*.07:.1f} {wd*.02:.1f} Q{cx:.1f} {-wd*.28:.1f} {cx+ln*.09:.1f} {-wd*.2:.1f}" stroke="#7a3e0c" stroke-width="2.4" fill="none"/>')
    return (f'<linearGradient id="{g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e6a650"/><stop offset=".45" stop-color="#c4782a"/><stop offset="1" stop-color="#7a4210"/></linearGradient>'
            f'<g transform="translate({x} {y}) rotate({ang})" filter="url(#shadow)"><path d="M{-ln/2} 0 C{-ln/2} {-wd*.6:.1f} {-ln/2+wd*.6:.1f} {-wd/2} {-ln/2+wd} {-wd/2} H{ln/2-wd} C{ln/2-wd*.6:.1f} {-wd/2} {ln/2} {-wd*.6:.1f} {ln/2} 0 C{ln/2} {wd*.55:.1f} {ln/2-wd*.6:.1f} {wd/2} {ln/2-wd} {wd/2} H{-ln/2+wd} C{-ln/2+wd*.6:.1f} {wd/2} {-ln/2} {wd*.55:.1f} {-ln/2} 0Z" fill="url(#{g})" stroke="#6a3608" stroke-width="1.4"/>'
            f'<path d="M{-ln/2} 0 C{-ln/2} {-wd*.6:.1f} {-ln/2+wd*.6:.1f} {-wd/2} {-ln/2+wd} {-wd/2} H{ln/2-wd} C{ln/2-wd*.6:.1f} {-wd/2} {ln/2} {-wd*.6:.1f} {ln/2} 0Z" filter="url(#crust)" opacity=".6"/>'
            f'{cuts}<path d="M{-ln/2+wd*.8:.1f} {-wd*.36:.1f} H{ln/2-wd*.8:.1f}" stroke="#fff4d0" stroke-width="3" opacity=".25" stroke-linecap="round"/></g>')


def bread_slice(cx, cy, r, ang, rnd):
    g = uid("bs")
    holes = "".join(f'<ellipse cx="{rnd.uniform(-r*.55, r*.55):.1f}" cy="{rnd.uniform(-r*.4, r*.4):.1f}" rx="{rnd.uniform(1.5, 4.5):.1f}" ry="{rnd.uniform(1, 3):.1f}" fill="#d8b878" opacity=".8"/>' for _ in range(18))
    return (f'<radialGradient id="{g}"><stop offset="0" stop-color="#f8e4b4"/><stop offset=".8" stop-color="#ecd096"/><stop offset="1" stop-color="#d8b06a"/></radialGradient>'
            f'<g transform="translate({cx} {cy}) rotate({ang})" filter="url(#shadow)"><ellipse rx="{r}" ry="{r*.72:.1f}" fill="#a8641e" stroke="#6a3608" stroke-width="1.2"/>'
            f'<ellipse rx="{r*.88:.1f}" ry="{r*.62:.1f}" fill="url(#{g})"/>{holes}</g>')


def butter_pat(cx, cy, s, ang):
    return (f'<g transform="translate({cx} {cy}) rotate({ang}) scale({s})"><path d="M-30 -10 L20 -18 L36 -4 L-14 4Z" fill="#fff4b8" stroke="#d8c070" stroke-width="1"/>'
            f'<path d="M-30 -10 L-14 4 L-14 22 L-30 8Z" fill="#f2dc84" stroke="#d8c070" stroke-width="1"/><path d="M-14 4 L36 -4 L36 14 L-14 22Z" fill="#f8e698" stroke="#d8c070" stroke-width="1"/>'
            f'<path d="M-20 -8 Q4 -16 26 -10" stroke="#fffbe0" stroke-width="2.4" fill="none" opacity=".8"/></g>')


def egg_in_sauce(x, y, r, rnd):
    g = uid("yk")
    return (f'<path d="{blob(x, y, r, rnd, .16)}" fill="#fbf8f0" stroke="#e8dcc0" stroke-width="1"/>'
            f'<radialGradient id="{g}" cx=".38" cy=".35" r=".7"><stop offset="0" stop-color="#ffe27a"/><stop offset=".6" stop-color="#f6a81a"/><stop offset="1" stop-color="#d9800c"/></radialGradient>'
            f'<circle cx="{x+3}" cy="{y+3}" r="{r*.42:.1f}" fill="#8a5a1a" opacity=".3"/><circle cx="{x+1}" cy="{y}" r="{r*.42:.1f}" fill="url(#{g})"/>'
            f'<ellipse cx="{x-r*.12:.1f}" cy="{y-r*.16:.1f}" rx="{r*.13:.1f}" ry="{r*.07:.1f}" fill="#fff" opacity=".6"/>')


def steam(x, y, h, n=3, gap=26):
    return "".join(f'<path d="M{x+i*gap} {y} q-12 {-h*.25:.0f} 2 {-h*.5:.0f} q14 {-h*.25:.0f} 0 {-h*.5:.0f}" stroke="#fff" stroke-width="7" fill="none" opacity=".16" stroke-linecap="round" filter="url(#soft)"/>'
                   for i in range(n))


def dish_miso(rnd):
    cx, cy = 286, 206
    b = (f'<ellipse cx="{cx+6}" cy="{cy+16}" rx="176" ry="176" fill="#000" opacity=".65" filter="url(#soft)"/>'
         '<radialGradient id="lac" cx=".4" cy=".35" r=".75"><stop offset="0" stop-color="#4a1410"/><stop offset=".7" stop-color="#2a0a08"/><stop offset="1" stop-color="#120404"/></radialGradient>'
         f'<circle cx="{cx}" cy="{cy}" r="172" fill="url(#lac)" stroke="#0a0202" stroke-width="3"/>'
         f'<circle cx="{cx}" cy="{cy}" r="160" fill="none" stroke="#a8241a" stroke-width="8"/>'
         f'<path d="M{cx-120} {cy-110} A164 164 0 0 1 {cx+60} {cy-156}" stroke="#fff" stroke-width="6" opacity=".18" fill="none" stroke-linecap="round"/>'
         '<radialGradient id="miso" cx=".45" cy=".42" r=".6"><stop offset="0" stop-color="#e8c27a"/><stop offset=".7" stop-color="#c8963e"/><stop offset="1" stop-color="#9a6a24"/></radialGradient>'
         f'<circle cx="{cx}" cy="{cy}" r="150" fill="url(#miso)"/>')
    for _ in range(9):  # miso clouds
        b += f'<path d="{blob(cx + rnd.uniform(-80, 80), cy + rnd.uniform(-80, 80), rnd.uniform(22, 42), rnd, .3, 10)}" fill="#f2dca8" opacity=".35" filter="url(#soft)"/>'
    for _ in range(7):
        a, d = rnd.uniform(0, math.tau), rnd.uniform(20, 105)
        b += wakame(cx + d * math.cos(a) - 30, cy + d * math.sin(a), rnd.uniform(56, 80), rnd.uniform(0, 180), rnd.uniform(9, 13))
    cubes = [(cx + rnd.uniform(-95, 95), cy + rnd.uniform(-95, 95)) for _ in range(14)]
    for (x, y) in sorted([p for p in cubes if (p[0] - cx) ** 2 + (p[1] - cy) ** 2 < 112 ** 2], key=lambda p: p[1]):
        b += tofu_cube(x, y, rnd.uniform(24, 30), rnd.uniform(-20, 20))
    b += scallion_rings(cx, cy, 110, 110, 22, rnd, (3, 5.5))
    b += f'<ellipse cx="{cx-50}" cy="{cy-60}" rx="60" ry="16" fill="#fff" opacity=".14" transform="rotate(-25 {cx-50} {cy-60})"/>'
    b += steam(cx - 30, 70, 120)
    b += ('<g filter="url(#shadow)"><rect x="478" y="92" width="30" height="16" rx="6" fill="#d8c8a0"/>'
          '<path d="M470 386 L560 40" stroke="#2a1a12" stroke-width="10" stroke-linecap="round"/><path d="M494 390 L574 50" stroke="#2a1a12" stroke-width="10" stroke-linecap="round"/>'
          '<path d="M546 96 L560 40 M562 104 L574 50" stroke="#a8241a" stroke-width="10" stroke-linecap="round"/></g>')
    b += scallion(60, 380, 140, 50) + tofu_cube(88, 76, 54, -12)
    return b


def dish_rice_peas(rnd):
    cx, cy = 290, 208
    b = plate(cx, cy, 186, rnd, rim="#e8dcc4")
    b += '<circle cx="290" cy="208" r="134" fill="none" stroke="#2a7a8a" stroke-width="4" opacity=".55"/><circle cx="290" cy="208" r="126" fill="none" stroke="#e8a020" stroke-width="2" opacity=".6"/>'
    g = uid("ri")
    b += (f'<radialGradient id="{g}" cx=".42" cy=".35" r=".7"><stop offset="0" stop-color="#fffaf0"/><stop offset=".7" stop-color="#f0e4ca"/><stop offset="1" stop-color="#cfbf98"/></radialGradient>'
          f'<path d="{blob(cx, cy, 116, rnd, .07, 20)}" fill="url(#{g})" filter="url(#shadow)"/>')
    items = []
    for _ in range(380):
        a, d = rnd.uniform(0, math.tau), 108 * math.sqrt(rnd.random())
        items.append(("r", cx + d * math.cos(a), cy + d * math.sin(a)))
    for _ in range(46):
        a, d = rnd.uniform(0, math.tau), 100 * math.sqrt(rnd.random())
        items.append(("b", cx + d * math.cos(a), cy + d * math.sin(a)))
    rnd.shuffle(items)
    for k, x, y in items:
        if k == "r":
            b += f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="6" ry="2.4" transform="rotate({rnd.uniform(0,180):.0f} {x:.0f} {y:.0f})" fill="{rnd.choice(("#ffffff", "#f8f0de", "#ecdcbc", "#f2e6cc"))}" opacity=".95"/>'
        else:
            b += kidney_bean(x, y, rnd.uniform(0, 180), rnd.uniform(.9, 1.15))
    b += thyme(250, 250, 110, -60) + thyme(330, 180, 80, 40)
    b += scotch_bonnet(318, 176, .9, 18)
    b += f'<ellipse cx="250" cy="150" rx="46" ry="12" fill="#fff" opacity=".2" transform="rotate(-20 250 150)"/>'
    # coconut half, allspice, spare pepper
    b += ('<g filter="url(#shadow)"><circle cx="494" cy="318" r="50" fill="#6a3e1c"/><circle cx="494" cy="318" r="50" filter="url(#crust)" opacity=".8"/>'
          '<circle cx="494" cy="318" r="41" fill="#fffdf6"/><circle cx="494" cy="318" r="34" fill="#f6f0e2"/><ellipse cx="480" cy="304" rx="12" ry="6" fill="#fff" opacity=".8"/></g>')
    for (x, y) in ((70, 70), (88, 84), (64, 96), (98, 62), (110, 92)):
        b += allspice(x, y, 8)
    b += scotch_bonnet(540, 84, .95, -20, ("#fff09a", "#f2c21a", "#9a6a06")) + leaf(80, 380, 70, 22, -30, "#4f7a28") + leaf(110, 384, 54, 18, 24, "#5f8a32")
    return b


def dish_shakshuka(rnd):
    cx, cy = 280, 208
    b = (f'<ellipse cx="{cx+8}" cy="{cy+16}" rx="184" ry="184" fill="#000" opacity=".65" filter="url(#soft)"/>'
         f'<rect x="{cx+160}" y="{cy-22}" width="150" height="40" rx="16" fill="#1e1c1a" stroke="#0e0c0a" stroke-width="2" transform="rotate(-10 {cx} {cy})"/>'
         '<radialGradient id="iron" cx=".4" cy=".35" r=".8"><stop offset="0" stop-color="#4a4642"/><stop offset=".8" stop-color="#232120"/><stop offset="1" stop-color="#121110"/></radialGradient>'
         f'<circle cx="{cx}" cy="{cy}" r="180" fill="url(#iron)" stroke="#0a0908" stroke-width="4"/>'
         f'<path d="M{cx-140} {cy-100} A172 172 0 0 1 {cx+40} {cy-170}" stroke="#8a8680" stroke-width="4" opacity=".35" fill="none" stroke-linecap="round"/>'
         '<radialGradient id="shk" cx=".45" cy=".42" r=".65"><stop offset="0" stop-color="#d8442a"/><stop offset=".75" stop-color="#b02a16"/><stop offset="1" stop-color="#7a160a"/></radialGradient>'
         f'<circle cx="{cx}" cy="{cy}" r="160" fill="url(#shk)"/><circle cx="{cx}" cy="{cy}" r="158" filter="url(#crust)" opacity=".45"/>')
    b += flecks(cx, cy, 150, 150, 90, rnd, ("#e8603a", "#7a1a0c", "#f07a4a", "#c8321e"), (2, 6))
    for _ in range(14):  # pepper bits
        x, y = cx + rnd.uniform(-130, 130), cy + rnd.uniform(-130, 130)
        if (x - cx) ** 2 + (y - cy) ** 2 < 140 ** 2:
            b += f'<rect x="{x:.0f}" y="{y:.0f}" width="16" height="10" rx="4" transform="rotate({rnd.uniform(0,180):.0f} {x:.0f} {y:.0f})" fill="#e8301a" stroke="#8a1208" stroke-width="1"/>'
    for i in range(6):
        a = i * math.tau / 6 + .2
        b += egg_in_sauce(cx + 92 * math.cos(a), cy + 92 * math.sin(a), 38, rnd)
    for _ in range(16):  # feta
        x, y = cx + rnd.uniform(-120, 120), cy + rnd.uniform(-120, 120)
        if (x - cx) ** 2 + (y - cy) ** 2 < 135 ** 2:
            b += f'<path d="{blob(x, y, rnd.uniform(5, 9), rnd, .35, 7)}" fill="#fbf8f0" stroke="#e0d8c4" stroke-width=".8"/>'
    for (x, y, a) in ((cx - 10, cy - 10, 20), (cx + 60, cy + 40, -40), (cx - 70, cy + 50, 80), (cx + 20, cy - 80, -10)):
        b += cilantro(x, y, 30, a, .5)
    b += flecks(cx, cy, 140, 140, 40, rnd, ("#3f7a24", "#5c9a33"), (1.5, 3))
    b += steam(cx - 40, 60, 100)
    b += bread_slice(506, 96, 54, 20, rnd) + bread_slice(528, 150, 50, 40, rnd)
    b += tomato(506, 330, 34) + tomato(462, 364, 26) + garlic_clove(70, 80, 1.1, -20) + cilantro(60, 386, 100, 20, .8)
    return b


def dish_baguettes(rnd):
    b = (f'<ellipse cx="300" cy="216" rx="260" ry="176" fill="#000" opacity=".55" filter="url(#soft)"/>'
         '<g transform="rotate(-4 300 206)"><rect x="70" y="52" width="470" height="308" rx="10" fill="#e2d6b8"/>'
         + "".join(f'<rect x="70" y="{y}" width="470" height="9" fill="#a8302a" opacity=".5"/>' for y in (76, 94, 318, 336))
         + '<rect x="70" y="52" width="470" height="308" rx="10" filter="url(#grain)" opacity=".5"/>'
         '<rect x="70" y="52" width="470" height="308" rx="10" fill="none" stroke="#a89878" stroke-width="2"/></g>')
    b += flecks(300, 206, 240, 150, 120, rnd, ("#fbf6ea", "#e8dcc0", "#d8c49a"), (.8, 2)).replace("/>", ' opacity=".6"/>')
    b += baguette(300, 120, 470, -8, 50) + baguette(292, 206, 480, -4, 52) + baguette(304, 292, 440, 3, 50)
    b += bread_slice(492, 350, 40, -20, rnd) + bread_slice(446, 366, 36, 10, rnd)
    b += butter_pat(130, 340, 1.2, -10) + wheat(548, 230, 150, 14) + wheat(560, 236, 130, 30)
    return b


EXTRA_DISHES = {
    "miso-soup-with-tofu-and-wakame": dish_miso,
    "jamaican-rice-and-peas": dish_rice_peas,
    "shakshuka": dish_shakshuka,
    "crusty-french-baguettes": dish_baguettes,
}


def rice_plate(rnd, style):
    cx, cy = 304, 207
    b = plate(cx, cy, 181, rnd, rim="#e4d8bd")
    base, grains = {
        "lemon": ("#e1c28b", ("#f4e4b2", "#d4aa64", "#fff1c8")),
        "soup": ("#bc925d", ("#5b4032", "#e4c18d", "#927154")),
        "bake": ("#bb7233", ("#e8ac57", "#ffd581", "#8b4825")),
        "risotto": ("#bc9d6f", ("#e7cda1", "#d2b68a", "#f2ddb5")),
    }[style]
    b += f'<ellipse cx="{cx}" cy="{cy}" rx="132" ry="129" fill="{base}"/>'
    for _ in range(590):
        a, d = rnd.uniform(0, math.tau), math.sqrt(rnd.random())
        x, y = cx + 125*d*math.cos(a), cy + 121*d*math.sin(a)
        b += (f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rnd.uniform(3, 7):.1f}" ry="2" '
              f'fill="{rnd.choice(grains)}" transform="rotate({rnd.randrange(180)} {x:.1f} {y:.1f})"/>')
    if style == "lemon":
        for x, y, angle in ((250, 200, -26), (339, 250, 17)):
            b += (f'<g transform="translate({x} {y}) rotate({angle})">'
                  '<path d="M-60 -12 Q-52 -49 -4 -49 Q48 -55 67 -19 Q81 18 38 39 Q-24 58 -58 24Z" '
                  'fill="#ca8b45" stroke="#965727" stroke-width="4" filter="url(#shadow)"/>'
                  f'{flecks(0, 0, 54, 32, 120, rnd, ("#ad672d", "#e8b363", "#f1cb82"))}</g>')
        b += lemon_slice(375, 155, 32)
    elif style == "risotto":
        for x, y, angle in ((260, 153, -32), (329, 160, 64), (320, 221, 16), (235, 226, -72), (355, 255, 40), (285, 290, -15)):
            b += (f'<g transform="translate({x} {y}) rotate({angle})">'
                  '<path d="M-24 0 Q-23 -23 0 -25 Q20 -25 25 0 L7 3 L5 19 L-7 19 L-9 3Z" '
                  'fill="#a77751" stroke="#744d36" stroke-width="3"/>'
                  '<path d="M-17 -5 Q0 -28 17 -5" fill="none" stroke="#d1a178" stroke-width="3"/></g>')
    else:
        colors = ("#e5caa2", "#d78b4b", "#769150") if style == "soup" else ("#588345", "#3d6938", "#edc58a")
        b += flecks(cx, cy, 119, 113, 130, rnd, colors, (4, 9))
    return b + flecks(cx, cy, 114, 109, 46, rnd)


def dish_penne(rnd, beef=False):
    b = plate(304, 205, 183, rnd)
    b += '<ellipse cx="304" cy="205" rx="132" ry="129" fill="#a7502d"/>'
    for _ in range(170):
        a, d = rnd.uniform(0, math.tau), math.sqrt(rnd.random())
        x, y = 304 + 115*d*math.cos(a), 205 + 113*d*math.sin(a)
        shade = rnd.choice(("#de884d", "#e89b5e", "#ca6c3f", "#edaa6d"))
        b += f'<g transform="translate({x:.1f} {y:.1f}) rotate({rnd.randrange(360)})">'
        if beef:
            b += (f'<rect x="-13" y="-8" width="28" height="16" rx="3" fill="{shade}" stroke="#a65531"/>'
                  '<path d="M-10 -4 H10 M-10 0 H10 M-10 4 H10" stroke="#f1ad72"/>'
                  '<ellipse cx="12" rx="3" ry="6" fill="#963f24"/>')
        else:
            b += (f'<path d="M-15 -6 L12 -6 L18 6 L-11 6Z" fill="{shade}" stroke="#a65531"/>'
                  '<path d="M-11 -2 H12 M-9 1 H13" stroke="#f1ad72" fill="none"/>')
        b += '</g>'
    if beef:
        b += flecks(304, 205, 115, 107, 90, rnd, ("#622f1d", "#89432a", "#a75832"), (2.5, 5.0))
    b += flecks(304, 205, 117, 115, 65, rnd, ("#f8e4b1", "#fbecce"), (1, 2.5))
    return b + '<path d="M305 223 Q257 196 276 176 Q303 176 305 223 Q324 175 352 187 Q344 215 305 223Z" fill="#40713c"/>'


def fish_plate(rnd, style):
    b = plate(304, 205, 184, rnd, rim="#e2e7df")
    color, detail, sides = {
        "salmon": ("#dd895a", "#f1ae84", ("#657f40", "#9ba452", "#bea367")),
        "cod": ("#eee0bd", "#fff4d6", ("#a93d24", "#d35731", "#625139")),
        "trout": ("#917655", "#c5ab80", ("#be9562", "#e4ba83", "#72824b")),
    }[style]
    b += flecks(304, 213, 128, 123, 87, rnd, sides, (5, 13))
    for x, y, angle in ((260, 170, -24), (343, 238, -23)):
        b += (f'<g transform="translate({x} {y}) rotate({angle})">'
              f'<path d="M-89 -35 Q-12 -49 77 -24 Q95 -18 80 5 Q21 40 -75 29 Q-96 23 -89 -35Z" '
              f'fill="{color}" stroke="#896444" stroke-width="3" filter="url(#shadow)"/>')
        for line in range(-65, 66, 22):
            b += f'<path d="M{line} -23 q13 16 2 42" fill="none" stroke="{detail}" stroke-width="3" opacity=".8"/>'
        b += flecks(-7, 0, 72, 23, 42, rnd, (detail, "#866745"), (1, 2)) + '</g>'
    b += flecks(304, 205, 112, 101, 55, rnd)
    return b + (lemon_slice(377, 150, 31) if style != "cod" else "")


def dish_lemonade(rnd, style):
    bright, dark = {
        "strawberry": ("#e98288", "#ac394d"),
        "shake-up": ("#f8dd7d", "#c99332"),
        "bitters": ("#dc9a50", "#9b492b"),
    }[style]
    body = (f'<linearGradient id="drink" x1="0" x2="1"><stop offset="0" stop-color="{dark}"/>'
            f'<stop offset=".36" stop-color="{bright}"/><stop offset="1" stop-color="{dark}"/></linearGradient>'
            '<ellipse cx="310" cy="330" rx="116" ry="23" fill="#110a06" filter="url(#soft)"/>'
            '<path d="M201 105 L224 313 Q304 349 384 313 L407 105Z" fill="#e2d9bd" fill-opacity=".3" stroke="#eed9ac" stroke-width="3"/>'
            '<path d="M207 146 L229 310 Q304 339 379 310 L401 146Z" fill="url(#drink)"/>'
            f'<ellipse cx="304" cy="146" rx="97" ry="23" fill="{bright}"/>')
    for x, y in ((246, 143), (293, 131), (343, 142), (371, 166), (269, 180), (320, 171), (298, 217)):
        body += (f'<rect x="{x-19}" y="{y-13}" width="38" height="26" rx="6" transform="rotate({rnd.randrange(-33, 34)} {x} {y})" '
                 'fill="#fffbec" fill-opacity=".56" stroke="#fff8e7" stroke-width="2"/>')
    body += ('<path d="M215 129 L235 303 M394 129 L376 301" fill="none" stroke="#fff4d2" stroke-width="5" stroke-opacity=".42"/>'
             '<ellipse cx="304" cy="105" rx="103" ry="30" fill="none" stroke="#fff4d2" stroke-width="4" stroke-opacity=".8"/>'
             '<path d="M233 312 Q304 337 375 312" fill="none" stroke="#fff4d2" stroke-opacity=".55" stroke-width="3"/>')
    if style == "bitters":
        body += '<path d="M311 154 C329 116 373 146 355 170 C340 190 311 168 333 150" fill="none" stroke="#f4cc46" stroke-width="9" stroke-linecap="round"/>'
    else:
        body += lemon_slice(373, 112, 38)
        body += lemon_slice(163, 291, 34)
    if style == "strawberry":
        for x, y, angle in ((426, 291, 25), (460, 315, -19), (152, 238, -29)):
            body += (f'<g transform="translate({x} {y}) rotate({angle})">'
                     '<path d="M-24 -9 Q0 -27 24 -9 Q22 10 0 30 Q-22 10 -24 -9Z" fill="#bd3746" stroke="#853035" stroke-width="2"/>'
                     '<path d="M-22 -10 L-12 -20 L-3 -15 L2 -26 L10 -16 L19 -19 L22 -8 L4 -10 L-9 -4Z" fill="#53803a"/>'
                     + flecks(0, 8, 16, 12, 19, rnd, ("#e98c6a", "#eeac77"), (1, 2)) + '</g>')
    return body


def dish_cupcakes(rnd):
    b = plate(304, 204, 175, rnd, 162, rim="#eadbd1")
    b += ('<radialGradient id="frost"><stop offset="0" stop-color="#fff8e7"/>'
          '<stop offset="1" stop-color="#d8c7a6"/></radialGradient>')
    for x, y, scale, liner in ((352, 151, .77, "#8f594e"), (252, 226, 1, "#724b69"), (370, 260, .65, "#9a734f")):
        b += (f'<g transform="translate({x} {y}) scale({scale})">'
              '<path d="M-61 -19 L-44 50 Q0 68 44 50 L61 -19Z" fill="' + liner + '" stroke="#795041" stroke-width="3"/>')
        for line in range(-45, 51, 11):
            b += f'<path d="M{line} -20 L{line*.72:.1f} 51" stroke="#f1c7a2" stroke-width="2" opacity=".48"/>'
        b += ('<ellipse cy="-18" rx="63" ry="24" fill="#d9a454" stroke="#b7803c" stroke-width="3"/>'
              '<path d="M-62 -24 Q-64 -45 -30 -50 Q-37 -67 -13 -71 Q-9 -85 8 -87 Q11 -75 24 -72 Q38 -64 29 -49 Q60 -46 62 -26 Q32 2 -62 -24Z" '
              'fill="url(#frost)" stroke="#c9b694" stroke-width="2"/>'
              '<path d="M-48 -32 Q-1 -15 46 -33 M-26 -51 Q1 -40 28 -56 M-17 -67 Q1 -60 15 -70" '
              'fill="none" stroke="#fff8e6" stroke-width="5" stroke-linecap="round"/>')
        b += flecks(0, -37, 42, 8, 15, rnd, ("#ba6f64", "#cfa751", "#85647c"), (1.2, 2.7)) + '</g>'
    return b


def dish_pork_chops(rnd):
    b = plate(304, 204, 179, rnd, rim="#e8dfca")
    b += ('<radialGradient id="mash"><stop offset="0" stop-color="#f6e8bd"/><stop offset="1" stop-color="#caa96b"/></radialGradient>'
          '<ellipse cx="358" cy="128" rx="68" ry="48" fill="url(#mash)"/>'
          '<path d="M320 135 Q352 97 384 122 Q398 140 357 144 Q341 139 356 127" fill="none" stroke="#fff1cc" stroke-width="6" stroke-linecap="round"/>')
    for i in range(16):
        x, y = 196 + rnd.uniform(-24, 38), 160 + i * 7
        b += (f'<path d="M{x:.1f} {y} q26 15 62 3" fill="none" stroke="{rnd.choice(("#4c7336", "#648748", "#76934c"))}" '
              'stroke-width="9" stroke-linecap="round"/>')
    b += ('<radialGradient id="sear"><stop offset="0" stop-color="#e0a968"/><stop offset=".72" stop-color="#b6743f"/>'
          '<stop offset="1" stop-color="#743818"/></radialGradient>'
          '<g transform="translate(324 238) rotate(-16)">'
          '<path d="M-80 -21 Q-65 -69 3 -60 Q68 -59 84 -15 Q105 33 52 52 Q11 74 -62 44 Q-96 24 -80 -21Z" '
          'fill="url(#sear)" stroke="#794121" stroke-width="4" filter="url(#shadow)"/>')
    b += flecks(2, -2, 69, 44, 175, rnd, ("#663b26", "#92522e", "#e5b477", "#c08049"), (1.3, 3.6))
    return b + '</g>'


DISHES = {
    "vanilla-cream-cheese-cupcakes": dish_cupcakes,
    "steak-seasoned-skillet-pork-chops": dish_pork_chops,
    "italian-beef-rigatoni-skillet": lambda rnd: dish_penne(rnd, beef=True),
    "strawberry-lemonade": lambda rnd: dish_lemonade(rnd, "strawberry"),
    "midwest-lemonade-shake-up": lambda rnd: dish_lemonade(rnd, "shake-up"),
    "bitters-heavy-lemonade": lambda rnd: dish_lemonade(rnd, "bitters"),
    "lemon-chicken-and-rice": lambda rnd: rice_plate(rnd, "lemon"),
    "creamy-chicken-and-wild-rice": lambda rnd: rice_plate(rnd, "soup"),
    "chicken-broccoli-rice-bake": lambda rnd: rice_plate(rnd, "bake"),
    "parmesan-mushroom-risotto": lambda rnd: rice_plate(rnd, "risotto"),
    "penne-alla-vodka": dish_penne,
    "garlic-butter-baked-salmon": lambda rnd: fish_plate(rnd, "salmon"),
    "baked-cod-with-tomatoes": lambda rnd: fish_plate(rnd, "cod"),
    "pan-seared-trout-almondine": lambda rnd: fish_plate(rnd, "trout"),
    "tuscan-lemon-chicken-piccata": dish_piccata,
    "blueberry-buttermilk-pancakes": dish_pancakes,
    "turkish-red-lentil-soup": dish_lentil,
    "provencal-ratatouille": dish_ratatouille,
    "irish-soda-bread": dish_soda_bread,
    "grandmas-apple-crumble": dish_crumble,
    "masala-chai": dish_chai,
    "pork-and-chive-dumplings": dish_dumplings,
    "huevos-rancheros": dish_huevos,
    "zaatar-manakish": dish_manakish,
    "mango-sticky-rice": dish_mango,
    "west-african-peanut-soup": dish_peanut_soup,
    "korean-cucumber-salad": dish_cucumber,
    "moroccan-mint-tea": dish_mint_tea,
    "argentine-beef-empanadas": dish_empanadas,
    **EXTRA_DISHES,
}


def dish_svg(rid):
    rnd = random.Random(rid)
    d, b = table_bg(sum(map(ord, rid)) % 50)
    return svg(DISH_W, DISH_H, b + DISHES[rid](rnd) + table_fg(), d)


def recipe_card_svg():
    defs, body = table_bg(33)
    body += '<g transform="rotate(-9 304 202)">'
    body += parchment(141, 79, 326, 246, 36)
    body += ornament_rule(177, 431, 134, "#8d643a", "#ac7b46", 1.5)
    for y, width in ((180, 208), (216, 248), (252, 229), (288, 175)):
        body += f'<path d="M180 {y} h{width}" stroke="#a27646" stroke-width="2" opacity=".5"/>'
    body += '</g>'
    return svg(DISH_W, DISH_H, body + table_fg(), defs)


# ------------------------------------------------------------------ channel art
def culinote_mark(x, y, size):
    cream = "#f8edda"
    return (f'<g transform="translate({x} {y}) scale({size / 128})">'
            '<rect width="128" height="128" rx="34" fill="#103c30"/>'
            f'<path d="M93 37 A41 41 0 1 0 94 91" fill="none" stroke="{cream}" '
            'stroke-width="8" stroke-linecap="round"/>'
            f'<path d="M60 33 Q59 33 59 35 L58 52 Q58 57 62 60 Q64 62 63.5 67 '
            'L62.3 86 Q62.3 92 65.5 92 Q68.7 92 68.7 86 L67.5 67 '
            'Q67 62 69 60 Q73 57 73 52 L72 35 Q72 33 71 33 Q70 33 70 35 '
            'V49 Q70 50 69 50 Q68 50 68 49 V35 Q68 33 67 33 Q66 33 66 35 '
            'V49 Q66 50 65 50 Q64 50 64 49 V35 Q64 33 63 33 Q62 33 62 35 '
            f'V49 Q62 50 61 50 Q60 50 60 49 V35 Q60 33 60 33 Z" fill="{cream}"/></g>')


def channel_jobs():
    jobs = [("channel/culinote_mark.png", svg(256, 256, culinote_mark(0, 0, 256)), 256, 256, None)]
    for name, w, h, quality in (
        ("splash_fhd.jpg", 1920, 1080, 78),
        ("icon_focus_fhd.png", 540, 405, None),
        ("icon_focus_hd.png", 290, 218, None),
        ("fire_tv_banner.png", 320, 180, None),
    ):
        size = h * .49
        body = f'<rect width="{w}" height="{h}" fill="#09291f"/>'
        body += culinote_mark((w - size) / 2, h * .12, size)
        body += (f'<text x="{w/2}" y="{h*.82}" text-anchor="middle" font-family="SerifBold" '
                 f'font-size="{h*.18}" fill="#f8edda">Culinote</text>')
        jobs.append((f"channel/{name}", svg(w, h, body), w, h, quality))
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


def fade_job():
    """Home: soft fade over the peeking off-screen card, so the row reads as 'more this way'."""
    # drawn at its exact on-screen size (Posters default to scaleToFit, which would letterbox a stretched strip)
    w, h = L["home"]["peek"]["fadeW"], L["home"]["card"]["h"] + 16
    r, g, b = 0x14, 0x0d, 0x09
    px = []
    for y in range(h):
        for x in range(w):
            t = x / (w - 1)
            px += [r, g, b, int(255 * min(1.0, .25 + .72 * t ** .8))]
    write_png(os.path.join(IMG, "ui", "fade_r.png"), w, h, px)


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
        jobs += ui_jobs() + ui_jobs(night=True)
    if want("icons"):
        jobs += icon_jobs()
    if want("garnish"):
        jobs += [("garnish/%s.png" % g, garnish_svg(g), GS, GS, None) for g in GARNISHES]
    if want("photos"):
        jobs += [("photos/%s.png" % p, photo_svg(p), PHOTO_W, PHOTO_H, None) for p in PHOTOS]
    if want("dishes"):
        jobs.append(("dishes/recipe-card.jpg", recipe_card_svg(), DISH_W, DISH_H, 80))
        for r in data["recipes"]:
            if r["image"] == "images/dishes/recipe-card.jpg":
                continue
            if r["id"] not in DISHES:
                sys.exit("no dish illustration for %s: add one to DISHES in tools/make_art.py" % r["id"])
            jobs.append(("dishes/%s.jpg" % r["id"], dish_svg(r["id"]), DISH_W, DISH_H, 80))
    if want("channel"):
        jobs += channel_jobs()
    run(jobs, force)
    if want("ui") and (force or not os.path.exists(os.path.join(IMG, "ui", "fade_r.png"))):
        fade_job()
        print("  art ui/fade_r.png")
    if want("ninepatch") and (force or not os.path.exists(os.path.join(IMG, "ui", "focus.9.png"))):
        ninepatch_jobs()
        print("  art ui/focus.9.png, ui/parchment.9.png")


if __name__ == "__main__":
    main()
