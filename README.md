# The Heirloom Table

A family cookbook for **Roku**, **Fire TV Stick running Fire OS**, and the **browser**. The same recipes, ingredient checklists, and cook-mode timers are available on all three.
Dark espresso backgrounds with a gold filigree frame, deckled parchment cards, script titles, and a handwritten "From My Kitchen" note on every recipe.

![Recipe screen](docs/screens/recipe-piccata.jpg)

## Start here

- **Browser.** Open [`web/index.html`](web/index.html). Choose **Roku** or **Fire TV Stick** at the top. Use the matching remote on the right and click **Hide remote** to give the cookbook more room.
- **Roku.** Install `dist/heirloom-table-roku.zip` using the [Roku developer installer](#sideload-on-a-roku-developer-mode). Select **The Heirloom Table** from Roku Home after installation.
- **Fire TV Stick.** Install `dist/heirloom-table-fire-tv.apk` using the [Fire TV steps below](#sideload-on-a-fire-tv-stick). Open **The Heirloom Table** from **Your Apps & Channels**.

## Browser controls

The browser version works from disk. The keyboard controls work in both modes and when the remote is hidden.

| Remote | Keyboard |
|---|---|
| D-pad | Arrow keys |
| OK | Enter |
| Back | Backspace or Esc |
| ▶︎/⏸ Play | Space |
| ◀◀ / ▶▶ | `[` / `]` |
| Roku Options / Fire TV Menu | `*` or `O` |

You can also click or tap recipe cards. The first click focuses a card and the second opens it. The mouse wheel works like Up and Down.

Deep links (handy for screenshots): `web/index.html?screen=recipe&id=lemon-chicken-and-rice`, `?screen=cook&id=irish-soda-bread&step=2`, `?menu=1`, `?remote=0`, `?screen=cook&id=penne-alla-vodka&step=1&timer=1` (starts that step's timer).

### Preview Fire TV in the browser

Open [`web/fire-tv.html`](web/fire-tv.html) to start with the Fire TV Stick remote selected. You can switch to Roku from the same page.

### App version and releases

The version appears on the cookbook home. Select **Update Now** from **Menu** on Fire TV or **Options** on Roku. The app checks GitHub for a newer public release and shows its version before you choose **Download**. Fire TV downloads the APK and opens the system installer for the matching, signed update. If your Fire TV blocks installation from the app, you can use `adb install -r`. Roku shows a QR code for the confirmed ZIP. Scan it on a phone, then use **Replace** in the Roku Development Application Installer from a computer. Back closes the menu from any screen.

Choose **Theme** in the same menu to switch between **Classic** and **Midnight**. Each device remembers its selection.

Publish a public, stable tag such as `v1.0.0` on [GitHub Releases](https://github.com/Trimmendous/heirloom-table/releases). Attach `heirloom-table-fire-tv.apk` and `heirloom-table-roku.zip` using those exact filenames. Set the matching version in `roku/manifest` before rebuilding. The web and Android builds use the same version, and the Fire TV APK must be signed with the same key as the installed APK.

## Sideload on a Fire TV Stick

The offline APK supports Android-based **Fire OS 6 and later**. Vega OS models, including the Fire TV Stick 4K Select, use a separate app format. Check your model in [Amazon's Fire OS device list](https://developer.amazon.com/docs/fire-tv/fire-os-overview).

1. Use the built `dist/heirloom-table-fire-tv.apk`, or run `scripts/package-fire-tv.sh` to rebuild. The build needs a JDK (17 or newer), Python 3, `zip`, and the Android SDK with `platforms;android-35` and `build-tools;35.0.0`. Set `ANDROID_HOME` to the SDK directory. Keep the local `dist/heirloom-fire-tv-debug.p12` signing key to install later builds as updates.
2. On the Stick, open **Settings → My Fire TV → Developer Options** and enable **ADB Debugging**. If Developer Options is hidden, open **About** and select the device name seven times. Find the IP address under **About → Network**. See [Amazon's ADB setup instructions](https://developer.amazon.com/docs/fire-tv/connecting-adb-to-device).
3. From a computer on the same network with Android SDK Platform Tools installed, connect and accept the authorization prompt on the TV. Then install the APK.

   ```sh
   adb connect FIRE_TV_IP:5555
   adb install -r dist/heirloom-table-fire-tv.apk
   ```

4. Open **The Heirloom Table** from **Your Apps & Channels**. Use the D-pad and Select to navigate, the **Menu** button for Options, and **Play/Pause** to enter or leave cook mode. Select a direction step to start cook mode on remotes without Play/Pause. Back leaves the current screen or exits from the cookbook home.

## Sideload on a Roku (developer mode)

1. **Enable developer mode.** On the Roku remote press **Home ×3, Up ×2, Right, Left, Right, Left, Right**. Write down the IP address the screen shows, accept the developer agreement, set a password, and let the device reboot.
2. **Get the package.** Use `dist/heirloom-table-roku.zip`. Run `scripts/check.sh` if you need to rebuild it.
3. **Install it.** Browse to `http://<roku-ip>` on the same network and sign in as `rokudev` with the password you set. Under *Development Application Installer*, choose `dist/heirloom-table-roku.zip` and press **Install** (or **Replace**).
4. The channel launches straight away. It also appears on the Home screen as the dev channel ("The Heirloom Table").

> Note: the channel has not been run on a physical Roku yet (none was attached to the build machine). The checks below are static and headless; see `PROGRESS.md` for what has been verified.

## Remote map (same on both)

| Key | Home | Recipe | Cook mode | Options menu |
|---|---|---|---|---|
| D-pad | move between cards and rows | up/down within a list, left/right between Ingredients and Directions | left/right (also up/down) change step | move |
| OK | open the recipe | tick an ingredient; on a step, start cook mode there | start/stop the step's timer on a timed step, otherwise next step | choose |
| Back | exit the channel | Home | back to the recipe | close menu |
| Play | cook mode for the focused card | cook mode (from the focused step) | back to the recipe | |
| ◀◀ / ▶▶ | previous/next card | previous/next recipe | previous/next step | page up/down |
| ✱ | Options: update, theme, reset all ticks, browse, jump to a category | Options: update, theme, reset recipe ticks, browse, jump, home | same | close |

Ticked ingredients are remembered: in the Roku registry on the device, and in `localStorage` in the browser.

**Cook-mode timers.** Any step that names a time ("simmer 3–4 minutes") gets a timer; `tools/build_data.py` picks the longest duration in the step (the low end of a range). On that step, OK starts or stops it. One timer runs at a time; it keeps counting on other steps and on the recipe card, and a toast says when time is up (the next OK dismisses it). While cook mode is open the Roku is told the viewer is active (`roAppManager.UpdateLastKeyPressTime`), and the browser asks for a screen wake lock where it can.

## Repository layout

```
data/recipes.json      single source of truth for recipes (edit this)
data/layout.json       shared 1920x1080 layout: Roku, web and the art generator all read it
roku/                  SceneGraph app: manifest, source/main.brs, components/*.brs|xml, fonts/, images/, data/ (generated)
web/                   browser clone: index.html, css/, js/ (one file per Roku .brs twin), recipes.js + assets/ (generated)
fire-tv/               Android launcher and remote input for the shared web cookbook
tools/build_data.py    validate recipes (schema, glyph coverage, food-safety sanity), write generated files and RECIPES.md
tools/add_recipe.py    add a recipe interactively and refresh the shared catalog
tools/make_art.py      generate every image (SVG -> WebKit via tools/render.swift -> PNG/JPG with sips)
tools/brs_lint.py      offline BrightScript lint and Roku↔web lockstep check
tools/check_assets.py  asset, size, manifest, credit and package checks
tools/web_test.js      headless behaviour test of the web clone (Node, no dependencies)
tools/screenshot.py    screenshots of the web clone (WebKit)
scripts/check.sh       run checks and build the Roku ZIP (add --fire-tv to build both)
scripts/package.sh     build dist/heirloom-table-roku.zip
scripts/package-fire-tv.sh  build dist/heirloom-table-fire-tv.apk
```

How Roku and web stay in lockstep:
- Each `roku/components/X.brs` has a twin `web/js/x.js` with the same functions and logic.
- `web/js/ui.js` is a tiny SceneGraph look-alike, with `Group`, `Poster`, `Label`, `MultiStyleLabel`, `Rectangle` and `Timer` nodes.
- `tools/brs_lint.py` fails if a BrightScript function has no web twin.

## Adding a recipe

1. Run `python3 tools/add_recipe.py` from the repo root. Enter the ingredients and directions one per line. Leave a blank line to finish each list. A direction such as `Simmer | Cook for 10 minutes.` adds a step heading and a timer.
2. Open `web/index.html` to try the recipe. The wizard validates it, uses a shared recipe-card illustration, and refreshes the browser catalog, Roku data, and `RECIPES.md`.
3. Run `scripts/check.sh --fire-tv` to verify the catalog and rebuild both TV packages. Run `scripts/check.sh` for Roku alone.

Use `python3 tools/add_recipe.py --dry-run` to validate an entry before saving. You can also edit `data/recipes.json` directly. For custom artwork, set the image to `images/dishes/<id>.jpg` and add the illustration to `DISHES` in `tools/make_art.py`.

The wizard needs Python 3.8 or later. Checks and the Roku build use Node and `zip`. Regenerating custom artwork uses the macOS Xcode command-line tools and `sips`. The Fire TV build uses the Android SDK and JDK listed above.
