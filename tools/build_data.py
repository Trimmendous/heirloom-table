#!/usr/bin/env python3
"""Validate data/recipes.json + data/layout.json and generate every derived file.

Writes:
  roku/data/recipes.json   normalised recipes (+ ordered categories)
  roku/data/layout.json    shared layout
  web/recipes.js           window.HEIRLOOM = {recipes, layout} (no fetch, works from file://)
  web/assets/...           byte-for-byte copy of roku/images + roku/fonts (so web works from disk)
  RECIPES.md               human index of every recipe

Validation covers schema, duplicates, plausibility rules, text length limits that keep
cards readable on a TV, and glyph coverage of every string in the font that will draw it.
Pure stdlib. Exit code 1 on any error.
"""
import json, os, re, shutil, struct, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "recipes.json")
LAYOUT = os.path.join(ROOT, "data", "layout.json")

REQUIRED = {
    "id": str, "title": str, "category": str, "cuisine": str, "description": str,
    "prepMin": int, "cookMin": int, "serves": int, "difficulty": str,
    "ingredients": list, "steps": list, "kitchenNote": str, "accent": dict,
    "image": str, "photo": str, "tags": list,
}
DIFFICULTIES = ["Easy", "Medium", "Hard"]
GARNISHES = None  # filled from tools/make_art.py's list via art manifest below
LIMITS = {"title": 34, "description": 150, "kitchenNote": 190, "ingredient": 80,
          "lead": 34, "stepText": 300}

errors = []


def err(msg):
    errors.append(msg)


# ---------------------------------------------------------------- font cmap
def font_codepoints(path):
    """Return the set of codepoints mapped by a TrueType font (cmap formats 4 and 12)."""
    with open(path, "rb") as f:
        data = f.read()
    num_tables = struct.unpack(">H", data[4:6])[0]
    cmap_off = None
    for i in range(num_tables):
        tag, _, off, _ = struct.unpack(">4sIII", data[12 + 16 * i: 28 + 16 * i])
        if tag == b"cmap":
            cmap_off = off
    if cmap_off is None:
        raise ValueError("no cmap in " + path)
    n = struct.unpack(">H", data[cmap_off + 2: cmap_off + 4])[0]
    cps = set()
    for i in range(n):
        pid, eid, off = struct.unpack(">HHI", data[cmap_off + 4 + 8 * i: cmap_off + 12 + 8 * i])
        sub = cmap_off + off
        fmt = struct.unpack(">H", data[sub: sub + 2])[0]
        if fmt == 4:
            segx2 = struct.unpack(">H", data[sub + 6: sub + 8])[0]
            seg = segx2 // 2
            ends = struct.unpack(">%dH" % seg, data[sub + 14: sub + 14 + segx2])
            starts = struct.unpack(">%dH" % seg, data[sub + 16 + segx2: sub + 16 + 2 * segx2])
            deltas = struct.unpack(">%dh" % seg, data[sub + 16 + 2 * segx2: sub + 16 + 3 * segx2])
            ro_pos = sub + 16 + 3 * segx2
            ranges = struct.unpack(">%dH" % seg, data[ro_pos: ro_pos + segx2])
            for s in range(seg):
                for c in range(starts[s], ends[s] + 1):
                    if c == 0xFFFF:
                        continue
                    if ranges[s] == 0:
                        g = (c + deltas[s]) & 0xFFFF
                    else:
                        p = ro_pos + 2 * s + ranges[s] + 2 * (c - starts[s])
                        g = struct.unpack(">H", data[p: p + 2])[0]
                        if g:
                            g = (g + deltas[s]) & 0xFFFF
                    if g:
                        cps.add(c)
        elif fmt == 12:
            ngroups = struct.unpack(">I", data[sub + 12: sub + 16])[0]
            for g in range(ngroups):
                a, b, _ = struct.unpack(">III", data[sub + 16 + 12 * g: sub + 28 + 12 * g])
                cps.update(range(a, b + 1))
    return cps


def check_glyphs(font_file, text, where, cache={}):
    path = os.path.join(ROOT, "roku", "fonts", font_file)
    if path not in cache:
        cache[path] = font_codepoints(path)
    missing = sorted({ch for ch in text if ord(ch) not in cache[path] and not ch.isspace()})
    if missing:
        err("%s: font %s lacks glyph(s) %s" % (where, font_file, " ".join(
            "%r(U+%04X)" % (c, ord(c)) for c in missing)))


# ---------------------------------------------------------------- helpers
def fmt_minutes(m):
    if m < 60:
        return "%d min" % m
    h, r = divmod(m, 60)
    return ("%d hr" % h) + (" %d min" % r if r else "")


TIMER_RE = re.compile(r"(\d+)(?:\s*[–-]\s*\d+)?[\s-]*(seconds?|minutes?|hours?)\b", re.I)
TIMER_UNIT = {"s": 1, "m": 60, "h": 3600}


def step_timer(text):
    """Cook-mode timer for a step: the longest duration it mentions (lower bound of a range), in seconds.
    "Cook 3–4 minutes, then stir for 30 seconds" -> 180. Returns (seconds, label) or (0, "")."""
    best = 0
    for mt in TIMER_RE.finditer(text):
        best = max(best, int(mt.group(1)) * TIMER_UNIT[mt.group(2)[0].lower()])
    if not (0 < best <= 12 * 3600):
        return 0, ""
    return best, ("%d sec" % best if best < 60 else fmt_minutes(best // 60))


def norm_title(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\b(the|grandma'?s|my|classic|easy|best|homemade)\b", "", t)
    return re.sub(r"[^a-z]+", "", t)


def load_garnishes():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import make_art  # noqa: E402
    return set(make_art.GARNISHES), set(make_art.PHOTOS)


def validate(doc, layout):
    garnishes, photos = load_garnishes()
    cats = doc.get("categories")
    if not isinstance(cats, list) or not cats:
        err("categories must be a non-empty list")
        cats = []
    recipes = doc.get("recipes")
    if not isinstance(recipes, list) or len(recipes) < 1:
        err("recipes must be a non-empty list")
        return
    seen_ids, seen_titles = set(), {}
    fonts = layout["fonts"]
    for c in cats:
        check_glyphs(fonts["script"], c, "category " + c)
    for i, r in enumerate(recipes):
        where = "recipe[%d] %s" % (i, r.get("id", "?"))
        for k, t in REQUIRED.items():
            if k not in r:
                err("%s: missing %s" % (where, k))
            elif not isinstance(r[k], t) or (t is int and isinstance(r[k], bool)):
                err("%s: %s must be %s" % (where, k, t.__name__))
        extra = set(r) - set(REQUIRED)
        if extra:
            err("%s: unknown keys %s" % (where, sorted(extra)))
        if errors:
            continue
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", r["id"]):
            err("%s: id must be kebab-case" % where)
        if r["id"] in seen_ids:
            err("%s: duplicate id" % where)
        seen_ids.add(r["id"])
        nt = norm_title(r["title"])
        if nt in seen_titles:
            err("%s: duplicate dish of %s" % (where, seen_titles[nt]))
        seen_titles[nt] = r["id"]
        if r["category"] not in cats:
            err("%s: category %r not in categories list" % (where, r["category"]))
        if r["difficulty"] not in DIFFICULTIES:
            err("%s: difficulty must be one of %s" % (where, DIFFICULTIES))
        if not (0 < r["prepMin"] <= 600 and 0 <= r["cookMin"] <= 720 and 0 < r["serves"] <= 24):
            err("%s: implausible prep/cook/serves" % where)
        for key in ("title", "description", "kitchenNote"):
            if len(r[key]) > LIMITS[key]:
                err("%s: %s is %d chars (max %d to fit the card)" % (where, key, len(r[key]), LIMITS[key]))
        items = 0
        for ing in r["ingredients"]:
            if isinstance(ing, str):
                group = [ing]
            elif isinstance(ing, dict) and set(ing) == {"group", "items"} and isinstance(ing["items"], list):
                group = ing["items"]
                check_glyphs(fonts["serifBold"], ing["group"], where + " group")
            else:
                err("%s: ingredient must be string or {group, items}" % where)
                continue
            for s in group:
                if not isinstance(s, str) or not s.strip():
                    err("%s: empty ingredient" % where)
                    continue
                items += 1
                if len(s) > LIMITS["ingredient"]:
                    err("%s: ingredient too long: %s" % (where, s))
                check_glyphs(fonts["serif"], s, where + " ingredient")
        if items < 2:
            err("%s: needs at least 2 ingredients" % where)
        if not (3 <= len(r["steps"]) <= 12):
            err("%s: needs 3..12 steps" % where)
        for j, st in enumerate(r["steps"]):
            if not isinstance(st, dict) or set(st) != {"lead", "text"}:
                err("%s: step %d must be {lead, text}" % (where, j + 1))
                continue
            if len(st["lead"]) > LIMITS["lead"] or len(st["text"]) > LIMITS["stepText"]:
                err("%s: step %d too long" % (where, j + 1))
            check_glyphs(fonts["serifBold"], st["lead"], where + " step lead")
            check_glyphs(fonts["serif"], st["text"], where + " step text")
        text = " ".join([r["title"], r["description"]] + [s["text"] for s in r["steps"]
                                                         if isinstance(s, dict) and "text" in s])
        # food-safety sanity: poultry must state 165°F; any °F must be plausible
        if re.search(r"\b(chicken|turkey|duck)\b", text, re.I) and "chicken broth" not in text.lower():
            if re.search(r"\b(chicken|turkey|duck)\b", r["title"], re.I) and "165°F" not in text:
                err("%s: poultry recipe must state the 165°F safe internal temperature" % where)
        for t in re.findall(r"(\d+)°F", text):
            if not (140 <= int(t) <= 550) and int(t) != 200:
                err("%s: suspicious temperature %s°F" % (where, t))
        check_glyphs(fonts["script"], r["title"], where + " title")
        check_glyphs(fonts["serif"], r["description"] + r["cuisine"], where + " description")
        check_glyphs(fonts["hand"], r["kitchenNote"], where + " kitchenNote")
        acc = r["accent"]
        if set(acc) != {"garnish", "color"} or not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(acc.get("color"))):
            err("%s: accent must be {garnish, color:#RRGGBB}" % where)
        elif acc["garnish"] not in garnishes:
            err("%s: garnish %r has no art in tools/make_art.py (have %s)" % (where, acc["garnish"], sorted(garnishes)))
        if r["image"] != "images/dishes/%s.jpg" % r["id"]:
            err("%s: image must be images/dishes/<id>.jpg" % where)
        if r["photo"] not in ["images/photos/%s.png" % p for p in photos]:
            err("%s: photo must be one of images/photos/{%s}.png" % (where, ",".join(sorted(photos))))
        if not all(isinstance(t, str) and re.fullmatch(r"[a-z0-9-]+", t) for t in r["tags"]):
            err("%s: tags must be lowercase-kebab strings" % where)


def normalise(doc):
    out = []
    for r in doc["recipes"]:
        lst = []
        for ing in r["ingredients"]:
            if isinstance(ing, str):
                lst.append({"text": ing, "header": False})
            else:
                lst.append({"text": ing["group"], "header": True})
                lst.extend({"text": s, "header": False} for s in ing["items"])
        n = dict(r)
        n["ingredients"] = lst
        n["steps"] = []
        for st in r["steps"]:
            sec, label = step_timer(st["text"])
            n["steps"].append({"lead": st["lead"], "text": st["text"], "timer": sec, "timerText": label})
        n["prepText"] = fmt_minutes(r["prepMin"])
        n["cookText"] = fmt_minutes(r["cookMin"]) if r["cookMin"] else "None"
        n["totalText"] = fmt_minutes(r["prepMin"] + r["cookMin"])
        n["garnish"] = "images/garnish/%s.png" % r["accent"]["garnish"]
        n["thumb"] = r["image"]
        out.append(n)
    cats = [c for c in doc["categories"] if any(r["category"] == c for r in out)]
    # stable home order: category order, then title
    out.sort(key=lambda r: (doc["categories"].index(r["category"]), r["title"]))
    return {"version": doc["version"], "categories": cats, "recipes": out}


def write(path, text):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    old = open(full, encoding="utf-8").read() if os.path.exists(full) else None
    if old != text:
        with open(full, "w", encoding="utf-8") as f:
            f.write(text)
        print("  wrote", path)


def sync_assets():
    """Mirror roku/images and roku/fonts into web/assets (byte-identical)."""
    for sub in ("images", "fonts"):
        src_root = os.path.join(ROOT, "roku", sub)
        dst_root = os.path.join(ROOT, "web", "assets", sub)
        want = set()
        for d, _, files in os.walk(src_root):
            for fn in files:
                if fn.startswith("."):
                    continue
                src = os.path.join(d, fn)
                rel = os.path.relpath(src, src_root)
                want.add(rel)
                dst = os.path.join(dst_root, rel)
                if not os.path.exists(dst) or open(src, "rb").read() != open(dst, "rb").read():
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copyfile(src, dst)
                    print("  synced web/assets/%s/%s" % (sub, rel))
        if os.path.isdir(dst_root):
            for d, _, files in os.walk(dst_root):
                for fn in files:
                    rel = os.path.relpath(os.path.join(d, fn), dst_root)
                    if rel not in want:
                        os.remove(os.path.join(d, fn))
                        print("  removed stale web/assets/%s/%s" % (sub, rel))


def recipes_md(norm):
    lines = ["# Recipe index", "",
             "Generated by `tools/build_data.py` from `data/recipes.json`. Check here before adding a dish: no duplicates.", "",
             "| # | Recipe | Category | Cuisine | Difficulty | Time | Serves | Diet / tags | Garnish |",
             "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(norm["recipes"], 1):
        lines.append("| %d | %s | %s | %s | %s | %s | %d | %s | %s |" % (
            i, r["title"], r["category"], r["cuisine"], r["difficulty"], r["totalText"], r["serves"],
            ", ".join(r["tags"]), r["accent"]["garnish"]))
    lines += ["", "## Coverage", ""]
    cats = {}
    cuis = {}
    for r in norm["recipes"]:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
        cuis[r["cuisine"]] = cuis.get(r["cuisine"], 0) + 1
    lines.append("- **By category:** " + ", ".join("%s %d" % (c, cats.get(c, 0)) for c in DOC_CATS))
    lines.append("- **By cuisine:** " + ", ".join("%s %d" % kv for kv in sorted(cuis.items())))
    veg = sum(1 for r in norm["recipes"] if {"vegetarian", "vegan"} & set(r["tags"]))
    gf = sum(1 for r in norm["recipes"] if "gluten-free" in r["tags"])
    lines.append("- **Vegetarian/vegan:** %d of %d; **gluten-free:** %d" % (veg, len(norm["recipes"]), gf))
    return "\n".join(lines) + "\n"


DOC_CATS = []


def main():
    global DOC_CATS
    check_only = "--check" in sys.argv
    with open(DATA, encoding="utf-8") as f:
        doc = json.load(f)
    with open(LAYOUT, encoding="utf-8") as f:
        layout = json.load(f)
    DOC_CATS = doc.get("categories", [])
    validate(doc, layout)
    if errors:
        print("recipe validation FAILED:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    norm = normalise(doc)
    print("validated %d recipes in %d categories" % (len(norm["recipes"]), len(norm["categories"])))
    if check_only:
        return
    write("roku/data/recipes.json", json.dumps(norm, ensure_ascii=False, separators=(",", ":")) + "\n")
    write("roku/data/layout.json", json.dumps(layout, ensure_ascii=False, separators=(",", ":")) + "\n")
    write("web/recipes.js", "/* Generated by tools/build_data.py. Do not edit. */\nwindow.HEIRLOOM = " +
          json.dumps({"data": norm, "layout": layout}, ensure_ascii=False, separators=(",", ":")) + ";\n")
    write("RECIPES.md", recipes_md(norm))
    sync_assets()


if __name__ == "__main__":
    main()
