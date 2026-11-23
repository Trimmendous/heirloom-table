#!/usr/bin/env python3
"""Screenshot the web clone at 1920x1080 with WebKit (tools/render.swift).

  python3 tools/screenshot.py                 # default set -> tools/.build/shots/*.png
  python3 tools/screenshot.py --docs          # also refresh docs/screens/*.jpg (committed previews)
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import make_art  # noqa: E402

OUT = os.path.join(ROOT, "tools", ".build", "shots")
SHOTS = [
    ("home", "remote=0"),
    ("recipe-piccata", "remote=0&screen=recipe&id=tuscan-lemon-chicken-piccata"),
    ("recipe-lentil-steps", "remote=0&screen=recipe&id=turkish-red-lentil-soup&zone=steps&step=4"),
    ("cook-chai", "remote=0&screen=cook&id=masala-chai&step=1"),
    ("menu", "remote=0&screen=recipe&id=irish-soda-bread&menu=1"),
    ("recipe-dumplings", "remote=0&screen=recipe&id=pork-and-chive-dumplings"),
    ("recipe-huevos", "remote=0&screen=recipe&id=huevos-rancheros"),
    ("recipe-manakish", "remote=0&screen=recipe&id=zaatar-manakish"),
    ("recipe-mango", "remote=0&screen=recipe&id=mango-sticky-rice"),
    ("cook-timer", "remote=0&screen=cook&id=pork-and-chive-dumplings&step=5&timer=1"),
]


def main():
    make_art.ensure_renderer()
    os.makedirs(OUT, exist_ok=True)
    index = os.path.join(ROOT, "web", "index.html")
    jobs = [{"html": index + "?" + q, "out": os.path.join(OUT, n + ".png"), "w": 1920, "h": 1080,
             "opaque": True, "wait": 1.2} for n, q in SHOTS]
    jf = os.path.join(OUT, "jobs.json")
    json.dump(jobs, open(jf, "w"))
    subprocess.check_call([make_art.BIN, jf, ROOT])
    for j in jobs:
        print("  shot", os.path.relpath(j["out"], ROOT))
    if "--docs" in sys.argv:
        docs = os.path.join(ROOT, "docs", "screens")
        os.makedirs(docs, exist_ok=True)
        for n, _ in SHOTS:
            subprocess.check_call(["sips", "-Z", "1280", "-s", "format", "jpeg", "-s", "formatOptions", "70",
                                   os.path.join(OUT, n + ".png"), "--out", os.path.join(docs, n + ".jpg")],
                                  stdout=subprocess.DEVNULL)
            print("  docs/screens/%s.jpg" % n)


if __name__ == "__main__":
    main()
