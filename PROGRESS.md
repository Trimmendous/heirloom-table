# Progress

The scheduled build job reads this first and updates it last. Roadmap is from `SPEC.md`; log lines are newest last.

**FOUNDATION: DONE** (2026-11-22). From now on, runs are GROWTH runs: add 4 recipes, then make one improvement from the roadmap below.

## Foundation checklist

- [x] Repo layout from SPEC: `data/`, `roku/`, `web/`, `tools/`, `scripts/`, `design/`
- [x] `data/recipes.json` as the single source of truth, plus `tools/build_data.py`, which:
  - validates the schema, duplicates, length limits, poultry at 165°F, and glyph coverage per font
  - writes `roku/data/*.json`, `web/recipes.js`, `RECIPES.md` and `web/assets/`
- [x] Shared layout `data/layout.json`, read by the Roku app, the web clone and the art generator
- [x] Roku SceneGraph app (`roku/`): manifest (FHD, icons, splash) and `main.brs`
  - Home: script title, tagline, an "Every Recipe" row plus one row per category
  - Recipe: dish, title parchment with meta strip, ingredient checkboxes, gold-ringed directions with bold leads, kitchen note and vintage photo, per-recipe garnish
  - Cook mode: one step at a time with progress dots
  - Options menu: reset ticks, browse all recipes, jump to a category, back to home
  - Full remote mapping, including Back to exit from Home
  - Ticks persist in the registry
- [x] Web clone (`web/`): plain HTML/CSS/JS, works from `file://`
  - Same layout via a SceneGraph look-alike (`web/js/ui.js`)
  - Keyboard map, toggleable on-screen remote, mouse/touch/wheel
  - Ticks persist in `localStorage`
  - Deep links for screenshots
- [x] Generated art pipeline in `tools/`:
  - `make_art.py` writes SVG, `render.swift` rasterises it with WebKit, and `sips` encodes the JPGs
  - The 9-patch images are drawn in pure Python
- [x] Bundled OFL fonts with licence files: Pinyon Script, Crimson Text (Regular and Bold), Kalam. Listed in `CREDITS.md`
- [x] `scripts/check.sh` runs art, data, assets/manifest, BrightScript lint (incl. Roku↔web twin check), `node --check`, the headless web test and the package build
- [x] `scripts/package.sh` builds `dist/heirloom-table-roku.zip`
- [x] README: Roku developer-mode sideload steps, how to open the web clone, remote map
- [x] Seed recipes: 7, one per category (Breakfast, Mains, Soups, Sides, Breads, Desserts, Drinks), across 7 cuisines
- [ ] **On-device test on a real Roku.** Blocked: no device attached to the build machine. Needs a human to sideload `dist/heirloom-table-roku.zip` and report back. Highest-risk items to check are listed below.

## On-device risks to verify (never run on a Roku yet)

- `MultiStyleLabel` with `drawingStyles` using `fontUri` for the bold step leads. If it misbehaves, fall back to a bold `Label` plus a regular `Label`.
- `Label.boundingRect()` height for wrapped text, which the list windowing uses. There is an estimate fallback in `textHeight()`.
- 9-patch posters (`focus.9.png`, `parchment.9.png`).
- Custom fonts in `Font` nodes.
- `roArray.SortBy`.
- The Back key on Home exiting through the `exitApp` field.
- Home re-creates its card nodes on every key press. This is fine on the web; it should be measured on a low-end stick.
- Cook-mode timers (added 2026-11-23):
  - `CreateObject("roAppManager")` and `UpdateLastKeyPressTime()` from the render thread. The code guards against `invalid`, but it's unconfirmed that the call stops the screensaver.
  - The repeating `Timer` node (`repeat = true`, 1 s) firing `cookTick` while cook mode is open.
  - The width of an auto-sized `Label` from `boundingRect()`, used to centre the clock icon and text. There is an estimate fallback.

## Growth roadmap (pick one improvement per run)

### Content
- [ ] Recipes: fill the thinnest areas first (ongoing, 4 per run).
  - Soups, Sides and Drinks still have only 1 recipe each; fill them next.
  - Only 1 Hard recipe (the dumplings).
  - No Middle Eastern or Latin American *main* yet; no Japanese, Korean or West African dishes at all.
  - Gluten-free is 5 of 11.

### Visual fidelity to the reference
- [ ] Richer dish illustrations: the piccata asparagus reads as a flat block, and plates could use rim highlights and steam.
- [ ] Leafy vine decoration down the right edge, plus a small gold house crest above the title, as in the reference.
- [ ] Home: show that more cards exist off-screen (a peeking 5th card or a fade), and a gentle focus scale.

### Remote and focus
- [ ] Animate row and list scrolling (Roku `Animation` nodes and CSS transitions in lockstep).
- [ ] An Info (`*` long-press / `info`) panel with tags and diet badges.

### Cook mode
- [x] Step timers: detect "3–4 minutes" in a step and let OK start a countdown, with a toast when it's done. (2026-11-23)
- [ ] An ingredients side panel in cook mode.
- [x] Investigate the Roku screensaver kicking in during long cook-mode sessions. Cook mode now calls `roAppManager.UpdateLastKeyPressTime()` every 30 s, and the web asks for a Screen Wake Lock. **Not verified on a device.** (2026-11-23)
- [ ] Optional: a chime when a timer ends (Roku `roAudioResource` / a web `Audio`), with a setting to mute it.

### Performance
- [ ] Reuse Home card nodes instead of rebuilding them on each key.
- [ ] Keep the package budget in check.
  - It is 2.42 MB of 4 MB now (11 recipes). Each new recipe adds a dish JPG of about 50 KB, plus about 45 KB if it needs a new garnish, plus about 60 KB for a new vintage photo.
  - If it gets tight, swap Kalam (427 KB) for a lighter handwriting face, or shrink the dish JPGs.

### Accessibility
- [ ] Web: an `aria-live` region announcing the focused item.
- [ ] Roku: use `roAudioGuide` to speak the focused item when Audio Guide is on.
- [ ] Check contrast of the gold-on-espresso small text.

### Web
- [ ] Verify in Chrome and Firefox from `file://`. Only WebKit has been exercised so far, and Firefox's strict file-origin policy may matter for fonts.

## Log

- 2026-11-22: **Foundation built.**
  - Added the full repo:
    - data pipeline and validator
    - Roku SceneGraph app (Home, Recipe, Cook mode, Options menu, full remote map)
    - web clone with keyboard, on-screen remote and mouse
    - generated art (backgrounds, parchment, frame, icons, 7 dish illustrations, 7 garnishes, 4 vintage photos, channel icons and splash)
    - OFL fonts, check/package scripts, README, CREDITS
  - Seeded 7 recipes:
    - Blueberry Buttermilk Pancakes
    - Tuscan Lemon Chicken Piccata
    - Turkish Red Lentil Soup
    - Provençal Ratatouille
    - Irish Soda Bread
    - Grandma's Apple Crumble
    - Masala Chai
  - Verified:
    - `scripts/check.sh` passes, including the 1,058-assertion headless web test
    - the package is 1.97 MB
    - WebKit screenshots of Home, Recipe, Cook and Menu were compared against the reference: same palette, parchment cards, script titles, gold-ringed numerals and garnish accents, but a landscape TV layout with scrolling lists instead of the reference's tall single card
  - **Not** verified on a Roku device.
  - Next: start GROWTH. Add 4 recipes into thin areas (e.g. a Hard main, gluten-free, East Asian / Latin American), then improve the dish illustrations or add step timers.
- 2026-11-23: **Growth run 1.**
  - Added 4 recipes, each with its own dish illustration and garnish:
    - Pork and Chive Dumplings (Mains, Chinese, **Hard**; new `scallion` garnish, new `teahouse` photo)
    - Huevos Rancheros (Breakfast, Mexican, gluten-free; new `lime` garnish, new `hacienda` photo)
    - Za'atar Manakish (Breads, Lebanese; new `olive` garnish)
    - Mango Sticky Rice (Desserts, Thai, vegan, gluten-free; new `mango` garnish)
  - Improvement: **cook-mode step timers**, the same on Roku and web.
    - `build_data.py` derives `steps[].timer`/`timerText` from the step text.
    - In cook mode, a clock line offers the timer; OK starts or stops it; it counts down from a stored end time; a toast says "Time's up". The web `Timer` shim gained `repeat`.
    - Cook mode also keeps the screen awake (see the on-device risks above).
  - Fixed: the new garnishes are kept out of the bottom-left of their art box so they don't cover the title card's description.
  - Verified:
    - `scripts/check.sh` passes, including 1,640 headless web assertions (19 new timer checks)
    - the package is 2.42 MB
    - WebKit screenshots of the 4 new recipe cards and the cook timer were checked by eye: no text overlap, and each garnish and dish looks distinct
  - **Not** verified on a Roku device.
  - Next: add recipes for Soups, Sides and Drinks (e.g. a Japanese or Korean soup, a Latin American side, a Middle Eastern drink). Then make the Home card nodes reusable, or add the leafy vine and crest decoration from the reference.
