# The Heirloom Table: build brief

A cookbook app for a **Roku stick**, used only with the Roku remote, plus a **browser clone** that looks and behaves the same (keyboard or an on-screen remote). This file is the source of truth for the scheduled build job. Read it at the start of every run.

## Look and feel (match `design/reference-recipe-card.png`)

Open the reference image and study it before doing any visual work. Every recipe screen should feel like that card:

- A dark, warm background: charcoal and espresso with a subtle texture and a gold filigree frame and corner flourishes.
- Aged parchment panels with torn or deckled edges and soft shadows: the title card, the ingredients card, and the "From My Kitchen" note.
- Type:
  - Gold or ink script for titles (e.g. *Great Vibes* or *Pinyon Script*).
  - A classic serif for body text (e.g. *Cormorant Garamond* or *EB Garamond*).
  - A handwritten face for the kitchen note (e.g. *Kalam* or *Caveat*).
  - Use OFL-licensed fonts only, bundled in the repo with their licence files. Roku loads them via `Font { uri: "pkg:/fonts/…" }`.
- Layout of one recipe:
  - The dish image goes top left.
  - The title parchment goes top right, with a one-line description and a meta strip of 4 icons: Prep, Cook, Serves, Difficulty.
  - The Ingredients card goes on the left, with checkboxes.
  - Numbered Directions go on the right, in gold-ringed numerals with a bold lead-in phrase per step.
  - The handwritten "From My Kitchen ♡" note goes at the bottom, next to a small vintage photo.
- Each recipe gets its own accent garnish (lemons for piccata, chilies for a curry, herbs, berries…) so the cards don't all look identical.
- Build at 1920×1080 (FHD) and keep it readable from a couch: the body text is at least 26px on the TV, and nothing sits outside the 5% title-safe margin.

## Images

- Roku `Poster` nodes need PNG or JPG, not SVG.
- Generate textures, frames, parchment and garnish art with a script that is checked into `tools/`. No third-party Python packages are installed. Pure-stdlib PNG writing (zlib + struct) works, and so does macOS `sips`/`qlmanage` for rasterising SVG.
- For dish images you have 2 options:
  - Openly licensed photos (CC0 / CC-BY, e.g. Wikimedia Commons). Record every one in `CREDITS.md`, with its source URL, author and licence.
  - Tasteful generated illustrations.
- Never use an image whose licence you can't confirm.
- Keep each image ≤ 400 KB and the Roku package ≤ 4 MB total.

## Roku app (`roku/`)

- Use SceneGraph + BrightScript, with a `manifest` that includes the title, version, FHD `ui_resolutions` and splash/focus icons.
- Screens:
  1. **Home**: the script title "The Heirloom Table" with its tagline, and a browsable grid or rows of recipe cards grouped by category (Breakfast, Mains, Soups, Sides, Desserts, Breads, Drinks…).
  2. **Recipe**: the card layout described above.
  3. **Cook mode**: big, full-screen, one-step-at-a-time directions, for following along while cooking.
- Remote mapping. Everything works with the remote alone:
  - D-pad: move focus.
  - OK: open, or tick an ingredient.
  - Back: go up one level, and exit from Home.
  - ▶︎/⏸ (Play): enter or leave cook mode.
  - ◀◀ / ▶▶: previous/next recipe, or previous/next step in cook mode.
  - ✱ (Options): a menu to reset checkboxes, show the recipe list, and jump to a category.
  - Focus must always be visible (a gold glow or outline) and must never get lost.
- Recipes come from `roku/data/recipes.json` (generated, see below).
- Package with `scripts/package.sh` → `dist/heirloom-table-roku.zip`, which sideloads at `http://<roku-ip>` in developer mode.

## Browser clone (`web/`)

- Plain HTML/CSS/JS with no build step and no frameworks. Opening `web/index.html` from disk must work, so load recipe data via a generated `web/recipes.js` rather than `fetch`.
- It shares the same assets, and its layout is pixel-faithful to the Roku version, scaled to fit the window at 16:9.
- Keyboard maps to the remote: arrows, Enter=OK, Backspace/Escape=Back, Space=Play, `[`/`]`=◀◀/▶▶, `*` or `o`=Options.
- There is also a toggleable on-screen Roku-style remote, and mouse/touch works too.

## Recipe data (`data/recipes.json`, single source of truth)

Each recipe has:

- id
- title
- category
- cuisine
- description
- prepMin
- cookMin
- serves
- difficulty
- ingredients[]: text, optionally grouped
- steps[]: lead + text
- kitchenNote
- garnish/accent theme
- image path
- tags

Rules for the data:

- Recipes must be real and cookable: accurate quantities, safe temperatures (poultry 165°F, etc.) and sensible timings, written in a warm voice.
- Aim for variety across cuisines, meal types, diets (vegetarian, gluten-free) and difficulty.
- No duplicate dishes. Check `RECIPES.md`, the index of every recipe, before adding.
- `tools/build_data` (or similar) validates the schema and writes `roku/data/recipes.json` and `web/recipes.js`.

## Checks (`scripts/check.sh` must pass before every commit)

- `scripts/check.sh` must run:
  - recipe schema validation
  - an asset existence and size check
  - a manifest sanity check
  - a BrightScript lint, if one is available offline, or at least a balanced `sub`/`function`/`end` check
  - the web clone, loaded headlessly if possible (e.g. `node` + a tiny DOM check), or at least JS-parsed with `node --check`
  - the package build
- No Roku device is attached, so state clearly what was verified and what wasn't.

## Progress

`PROGRESS.md` holds the roadmap checklist and a dated log line per run. Read it first, and update it last.
