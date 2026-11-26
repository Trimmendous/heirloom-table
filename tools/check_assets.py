#!/usr/bin/env python3
"""Asset, manifest and package checks.

  python3 tools/check_assets.py                       # assets + manifest + UI glyphs + web sync + credits
  python3 tools/check_assets.py --package dist/x.zip  # package contents and size budget
"""
import json, os, re, struct, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROKU = os.path.join(ROOT, "roku")
MAX_IMAGE = 400 * 1024
MAX_PACKAGE = 4 * 1024 * 1024
errors = []
sys.path.insert(0, os.path.join(ROOT, "tools"))
from build_data import font_codepoints  # noqa: E402


def err(msg):
    errors.append(msg)


def image_size(path):
    with open(path, "rb") as f:
        head = f.read(26)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", head[16:24])
        f.seek(2)
        while True:
            marker = f.read(2)
            if len(marker) < 2 or marker[0] != 0xFF:
                return None
            if marker[1] in (0xC0, 0xC1, 0xC2):
                f.read(3)
                h, w = struct.unpack(">HH", f.read(4))
                return w, h
            seg = struct.unpack(">H", f.read(2))[0]
            f.seek(seg - 2, 1)


def check_ref(uri, where):
    rel = uri.replace("pkg:/", "")
    p = os.path.join(ROKU, rel)
    if not os.path.isfile(p):
        err("%s: missing asset %s" % (where, rel))
        return None
    return p


def check_assets():
    layout = json.load(open(os.path.join(ROOT, "data", "layout.json")))
    data = json.load(open(os.path.join(ROKU, "data", "recipes.json")))
    # every image reachable from data
    for r in data["recipes"]:
        for key in ("image", "photo", "garnish", "thumb"):
            p = check_ref(r[key], "recipe %s %s" % (r["id"], key))
            if p and key == "image":
                sz = image_size(p)
                if sz != (layout["recipe"]["dish"]["w"], layout["recipe"]["dish"]["h"]):
                    err("%s: dish image is %s, expected %dx%d" % (r["id"], sz, layout["recipe"]["dish"]["w"], layout["recipe"]["dish"]["h"]))
    check_ref(layout["home"]["peek"]["fade"], "layout home.peek.fade")
    for sec in ("home", "recipe", "cook"):
        for key in ("bg", "nightBg"):
            p = check_ref(layout[sec][key], "layout %s.%s" % (sec, key))
            if p and image_size(p) != (1920, 1080):
                err("%s.%s must be 1920x1080" % (sec, key))
    # every literal image path in code (Roku + web)
    code = []
    for d in (os.path.join(ROKU, "components"), os.path.join(ROKU, "source"), os.path.join(ROOT, "web", "js")):
        for fn in os.listdir(d):
            path = os.path.join(d, fn)
            if os.path.isfile(path):
                code.append((fn, open(path, encoding="utf-8").read()))
    for fn, src in code:
        for uri in set(re.findall(r"""["'](images/[\w/.\-]+\.(?:png|jpg))["']""", src)):
            check_ref(uri, fn)
    for icon in ("clock", "pot", "utensils", "hat", "heart"):
        check_ref("images/ui/icon_%s.png" % icon, "meta icons")
    # sizes
    total_imgs = 0
    for d, _, files in os.walk(os.path.join(ROKU, "images")):
        for fn in files:
            p = os.path.join(d, fn)
            total_imgs += os.path.getsize(p)
            if os.path.getsize(p) > MAX_IMAGE:
                err("%s is %d KB (max 400 KB)" % (os.path.relpath(p, ROOT), os.path.getsize(p) // 1024))
            if fn.endswith((".png", ".jpg")) and image_size(p) is None:
                err("%s: unreadable image header" % os.path.relpath(p, ROOT))
    # fonts + licences + credits
    credits = open(os.path.join(ROOT, "CREDITS.md"), encoding="utf-8").read() if os.path.exists(os.path.join(ROOT, "CREDITS.md")) else ""
    if not credits:
        err("CREDITS.md missing")
    for kind, f in layout["fonts"].items():
        if not os.path.isfile(os.path.join(ROKU, "fonts", f)):
            err("font %s (%s) missing" % (f, kind))
        fam = re.match(r"([A-Za-z]+?)(?:-|$)", f).group(1)
        lic = [x for x in os.listdir(os.path.join(ROKU, "fonts", "licenses")) if x.startswith(fam)]
        if not lic:
            err("font %s has no licence file in roku/fonts/licenses" % f)
        elif "SIL Open Font License" not in open(os.path.join(ROKU, "fonts", "licenses", lic[0]), encoding="utf-8").read():
            err("font %s licence is not OFL" % f)
        if f not in credits:
            err("CREDITS.md does not list font %s" % f)
    # UI string glyphs (non-ASCII characters in code literals must exist in the serif fonts)
    cps = [font_codepoints(os.path.join(ROKU, "fonts", layout["fonts"][k])) for k in ("serif", "serifBold")]
    for fn, src in code:
        for lit in re.findall(r'"([^"\n]*)"' if fn.endswith(".brs") else r"'([^'\n]*)'", src):
            for ch in set(lit):
                if ord(ch) > 127 and not all(ord(ch) in c for c in cps):
                    err("%s: UI string %r uses %r which the serif fonts lack" % (fn, lit, ch))
    # web mirror is byte-identical
    for sub in ("images", "fonts"):
        for d, _, files in os.walk(os.path.join(ROKU, sub)):
            for fn in files:
                if fn.startswith("."):
                    continue
                src = os.path.join(d, fn)
                dst = os.path.join(ROOT, "web", "assets", sub, os.path.relpath(src, os.path.join(ROKU, sub)))
                if not os.path.isfile(dst) or open(src, "rb").read() != open(dst, "rb").read():
                    err("web/assets out of sync for %s (run tools/build_data.py)" % os.path.relpath(src, ROOT))
    # generated data is current
    web = open(os.path.join(ROOT, "web", "recipes.js"), encoding="utf-8").read()
    if json.dumps(data, ensure_ascii=False, separators=(",", ":")) not in web:
        err("web/recipes.js is stale (run tools/build_data.py)")
    return total_imgs


def check_manifest():
    path = os.path.join(ROKU, "manifest")
    kv = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            k, _, v = line.partition("=")
            kv[k.strip()] = v.strip()
    for k in ("title", "major_version", "minor_version", "build_version", "ui_resolutions",
              "mm_icon_focus_fhd", "mm_icon_focus_hd", "splash_screen_fhd"):
        if not kv.get(k):
            err("manifest: missing %s" % k)
    for k in ("major_version", "minor_version", "build_version"):
        if kv.get(k) and not kv[k].isdigit():
            err("manifest: %s must be numeric" % k)
    if kv.get("ui_resolutions") != "fhd":
        err("manifest: ui_resolutions must be fhd")
    want = {"mm_icon_focus_fhd": (540, 405), "mm_icon_focus_hd": (290, 218), "splash_screen_fhd": (1920, 1080)}
    for k, dims in want.items():
        if kv.get(k):
            p = check_ref(kv[k], "manifest " + k)
            if p and image_size(p) != dims:
                err("manifest: %s is %s, expected %dx%d" % (k, image_size(p), dims[0], dims[1]))
    return kv


def check_package(zpath):
    if not os.path.isfile(zpath):
        err("package %s not found" % zpath)
        return
    size = os.path.getsize(zpath)
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        bad = z.testzip()
    if bad:
        err("package: corrupt member %s" % bad)
    for need in ("manifest", "source/main.brs", "components/MainScene.xml", "data/recipes.json", "data/layout.json"):
        if need not in names:
            err("package: %s not at zip root" % need)
    if any(n.startswith("images/web/") or n.endswith(".DS_Store") for n in names):
        err("package: contains web-only or junk files")
    if size > MAX_PACKAGE:
        err("package is %.2f MB (max 4 MB)" % (size / 1048576))
    print("package %s: %d files, %.2f MB of 4 MB budget" % (os.path.relpath(zpath, ROOT), len(names), size / 1048576))


def main():
    if "--package" in sys.argv:
        check_package(os.path.join(ROOT, sys.argv[sys.argv.index("--package") + 1]))
    else:
        total = check_assets()
        kv = check_manifest()
        if not errors:
            print("assets OK (%.2f MB of images), manifest OK (%s v%s.%s.%s)" % (
                total / 1048576, kv["title"], kv["major_version"], kv["minor_version"], kv["build_version"]))
    if errors:
        print("asset/manifest/package check FAILED:")
        for e in errors:
            print("  -", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
