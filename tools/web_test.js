#!/usr/bin/env node
/* Headless test of the web clone: loads web/*.js into a tiny fake DOM and drives it with remote keys.
 * The screen logic mirrors the BrightScript, so this also exercises the Roku state machine's design
 * (it does not execute BrightScript). Run: node tools/web_test.js */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ROOT = path.join(__dirname, '..');

/* ---------------------------------------------------------------- fake DOM */
function El(tag) {
  this.tagName = tag; this.children = []; this.parentNode = null; this.style = {}; this.className = '';
  this._text = ''; this._html = ''; this.hidden = false; this.listeners = {};
  const self = this;
  this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
  Object.defineProperty(this, 'textContent', { get() { return self._text; }, set(v) { self._text = String(v); self._html = ''; } });
  Object.defineProperty(this, 'innerHTML', { get() { return self._html; }, set(v) { self._html = String(v); self._text = String(v).replace(/<[^>]*>/g, ''); } });
}
El.prototype.appendChild = function (c) { c.parentNode = this; this.children.push(c); return c; };
El.prototype.remove = function () { if (this.parentNode) { const k = this.parentNode.children; k.splice(k.indexOf(this), 1); this.parentNode = null; } };
El.prototype.addEventListener = function (t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); };
El.prototype.setAttribute = function () {}; El.prototype.getAttribute = function () { return null; };
Object.defineProperty(El.prototype, 'offsetHeight', {
  get() { // estimate wrapped text height like the Roku fallback does
    const size = parseFloat(this.style.fontSize) || 0;
    if (!size || !this._text) return 0;
    const w = parseFloat(this.style.width) || 4000;
    const perLine = Math.max(1, Math.floor(w / (size * 0.48)));
    let lines = Math.ceil(this._text.length / perLine);
    if (this.style.webkitLineClamp && this.style.webkitLineClamp !== 'none') lines = Math.min(lines, +this.style.webkitLineClamp);
    if (this.style.whiteSpace === 'nowrap') lines = 1;
    return Math.round(lines * size * 1.22);
  }
});
Object.defineProperty(El.prototype, 'offsetWidth', {
  get() { const size = parseFloat(this.style.fontSize) || 0; return Math.round(this._text.length * size * 0.42); }
});
const ids = { stage: new El('div'), exit: new El('div'), 'remote-toggle': new El('button') };
ids['preview-controls'] = new El('header');
ids['remote-dock'] = new El('aside');
ids.screen = new El('main');
ids.screen.clientWidth = 1920;
ids.screen.clientHeight = 1080;
ids.exit.hidden = true;
const document = {
  readyState: 'complete',
  createElement: (t) => new El(t),
  getElementById: (id) => ids[id] || null,
  querySelector: () => null,
  querySelectorAll: () => [],
  addEventListener() {},
  body: new El('body')
};
const store = {};
const requests = [];
const downloads = [];
function ReleaseRequest() { requests.push(this); }
ReleaseRequest.prototype.open = function (method, url) { this.method = method; this.url = url; };
ReleaseRequest.prototype.send = function () {};
ReleaseRequest.prototype.respond = function (status, data) {
  this.status = status;
  this.responseText = JSON.stringify(data);
  this.onload();
};
const ctx = {
  document, console, URLSearchParams, XMLHttpRequest: ReleaseRequest, open: (url) => downloads.push(url), setTimeout: (fn) => { ctx.__timers.push(fn); return ctx.__timers.length; },
  clearTimeout() {}, setInterval: () => 1, clearInterval() {}, __timers: [], innerWidth: 1920, innerHeight: 1080, location: { search: '' },
  addEventListener() {},
  localStorage: { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } }
};
ctx.window = ctx;
vm.createContext(ctx);
for (const f of ['recipes.js', 'js/ui.js', 'js/home.js', 'js/recipe.js', 'js/cook.js', 'js/menu.js', 'js/app.js']) {
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web', f), 'utf8'), ctx, { filename: 'web/' + f });
}

/* ---------------------------------------------------------------- helpers */
let passed = 0;
const fails = [];
function ok(cond, msg) { if (cond) passed++; else fails.push(msg); }
const run = (code) => vm.runInContext(code, ctx);
const press = (...keys) => keys.forEach((k) => run(`pressKey(${JSON.stringify(k)})`));
const M = () => run('m');
const S = (x) => JSON.parse(JSON.stringify(x));
function onStage(n) {
  const [x, y] = n.translation; return x >= 0 && y >= 0 && x + n.width <= 1920 && y + n.height <= 1080;
}
function focusVisible(label) {
  const m = M();
  if (m.menuOpen) {
    const lv = m.mstack[m.mstack.length - 1];
    ok(lv.sel === -1 ? m.mBackFocus.visible && !m.mFocus.visible : lv.sel >= 0 && lv.sel < lv.items.length,
      label + ': menu focus off-list');
    return;
  }
  if (m.screen === 'recipe') {
    const rs = m.rs;
    const node = rs.zone === 'steps' ? m.stepNodes[rs.sIdx] : rs.zone === 'ing' ? m.ingNodes[rs.ing] : m.rFocus;
    ok(node && node.visible, label + ': focused recipe item hidden');
    ok(rs.zone !== 'ing' || !m.rec.ingredients[rs.ing].header, label + ': focus on a group heading');
    ok(onStage(m.rFocus), label + ': focus ring off screen ' + JSON.stringify(m.rFocus.translation));
    const vis = m.ingNodes.map((nd, i) => (nd.visible ? i : -1)).filter((i) => i >= 0);
    ok(!m.rec.ingredients[vis[vis.length - 1]].header, label + ': group heading orphaned at the bottom');
  } else if (m.screen === 'home') {
    const hs = m.hs;
    if (hs.filter) {
      ok(m.homeFilterFocus.visible, label + ': filter focus is visible');
      return;
    }
    ok(hs.row >= hs.top && hs.row < hs.top + 2, label + ': focused row not visible');
    ok(hs.cols[hs.row] < m.rows[hs.row].items.length, label + ': focused column past row end');
  } else if (m.screen === 'cook') {
    ok(m.cs.sIdx >= 0 && m.cs.sIdx < m.rec.steps.length, label + ': cook step out of range');
  }
}

/* ---------------------------------------------------------------- scenarios */
let m = M();
const n = m.D.recipes.length;
ok(m.screen === 'home', 'starts on Home');
ok(JSON.stringify(m.rows.map((row) => row.title)) === JSON.stringify(m.D.categories), 'Home has one row per category');
press('up');
ok(M().hs.filter && M().homeFilterFocus.visible, 'Up from the first row focuses Filter');
press('OK');
ok(M().mTitle.text === 'Filter Recipes' && M().mstack[0].items[0].label === 'All Categories', 'Filter opens from the remote');
press('up', 'up');
ok(M().mstack[0].sel === -1 && M().mBackFocus.visible && !M().mFocus.visible, 'Up selects the visible Back button');
press('OK');
ok(!M().menuOpen && M().screen === 'home', 'selecting visible Back closes the filter menu');
press('OK', 'up', 'down');
ok(M().mstack[0].sel === 0 && !M().mBackFocus.visible, 'Down from Back returns to the first filter choice');
press('fastforward');
ok(M().mstack[0].items[M().mstack[0].sel].label === 'Drinks', 'Drinks is available in the category filter');
press('OK');
ok(M().rows.length === 1 && M().rows[0].title === 'Drinks' && M().rows[0].items.length === 3,
  'Drinks filter shows exactly the three lemonade recipes');
ok(M().rows[0].items.every((index) => {
  const drink = M().D.recipes[index];
  return drink.serves === 8 && drink.steps.some((step) => step.text.includes('8 cups'));
}), 'all lemonade recipes give directions for a full eight-cup pitcher');
press('OK', 'rewind');
ok(M().screen === 'recipe' && M().rec.id === 'strawberry-lemonade', 'rewind wraps within the selected category');
press('fastforward');
ok(M().rec.id === 'bitters-heavy-lemonade', 'fast-forward wraps within the selected category');
press('back', 'up', 'OK', 'back');
ok(!M().menuOpen && M().homeCategory === 'Drinks' && M().hs.filter, 'Back closes Filter and keeps the selection');
press('OK', 'rewind', 'OK');
ok(M().rows.length === m.D.categories.length && !M().homeCategory && !M().hs.filter,
  'All Categories restores the category rows and focuses a card');

function selectMenuItem(label) {
  const level = M().mstack[M().mstack.length - 1];
  const target = level.items.findIndex((item) => item.label === label);
  if (target < 0) throw new Error('Missing menu item: ' + label);
  const distance = target - level.sel;
  for (let i = 0; i < Math.abs(distance); i++) press(distance < 0 ? 'up' : 'down');
  press('OK');
}
press('up', 'OK');
selectMenuItem('Ingredients to Avoid');
ok(M().mTitle.text === 'Ingredients to Avoid' && M().mNote.text.includes('cross-contact'),
  'ingredient picker shows its scope for allergies');
ok(!M().mstack[1].items.some(item => item.label === 'Apply Exclusions'), 'ingredient picker has no Apply button');
selectMenuItem('Milk & Dairy');
ok(M().menuOpen && M().homeAvoid['Milk & Dairy'] && M().homeMatches.length < n,
  'selecting an exclusion filters immediately while the picker stays open');
selectMenuItem('Eggs');
press('back');
ok(!M().menuOpen && M().homeAvoid['Milk & Dairy'] && M().homeAvoid.Eggs && M().homeFilterNote.visible,
  'Back closes the picker with both exclusions still active');
ok(M().homeFilterLabel.text === 'Filter · Active' && M().homeFilterTint.visible &&
  M().homeFilterNote.text === 'Avoiding Milk & Dairy, Eggs', 'Home visibly names the exclusions');
ok(M().homeMatches.every((index) => M().D.recipes[index].ingredientFilters
  .every((ingredient) => ingredient !== 'Milk & Dairy' && ingredient !== 'Eggs')),
  'matching recipes are excluded');
ok(run('loadIngredientExclusions().Eggs'), 'exclusions are persisted');
press('OK');
selectMenuItem('Ingredients to Avoid (2)');
selectMenuItem('Eggs');
ok(!M().homeAvoid.Eggs && !run('loadIngredientExclusions().Eggs'), 'selecting a checked ingredient removes it immediately');
selectMenuItem('Fish');
ok(M().homeAvoid.Fish, 'fish can be excluded independently');
ok(!M().homeMatches.some((index) => M().D.recipes[index].id === 'steak-seasoned-skillet-pork-chops'),
  'the fish exclusion accounts for Worcestershire sauce');
press('back', 'OK');
selectMenuItem('Fish');
ok(M().rows.length === 0 && M().homeEmpty.visible && M().hs.filter &&
  M().homeFilterCategory.text === 'Fish · 0 recipes' && M().homeFilterNote.text.includes('Fish'),
  'category and ingredient filters combine and are both visible when there are no matches');
press('OK');
selectMenuItem('All Categories');
ok(!M().homeCategory && M().homeAvoid.Fish, 'clearing the category retains ingredient exclusions');
press('up', 'OK');
selectMenuItem('Ingredients to Avoid (2)');
selectMenuItem('Clear Exclusions');
ok(Object.keys(M().homeAvoid).length === 0 && M().homeMatches.length === n && !M().homeFilterTint.visible,
  'Clear Exclusions restores the full catalog immediately and clears the active indicator');
press('back', 'down');

press('down');
run('homeOpenFilter()');
press('back', 'up');
ok(M().hs.filter && M().hs.row === 1, 'Up stays on Filter when opened from a lower row');
press('down', 'up');
focusVisible('home start');

press('right', 'right');
ok(M().hs.cols[0] === 2, 'right moves along the row');
press('left');
ok(M().hs.cols[0] === 1, 'left moves back');
press('OK');
m = M();
ok(m.screen === 'recipe' && m.rec === m.D.recipes[1], 'OK opens the focused recipe');
ok(m.rs.zone === 'steps' && m.rs.sIdx === 0, 'opening a recipe highlights Direction 1');
focusVisible('recipe open');
const rid = m.rec.id;
const firstIng = m.rs.ing;
press('left', 'OK');
ok(run(`isChecked(${JSON.stringify(rid)}, ${firstIng})`) === true, 'OK ticks an ingredient');
ok(m.ingBoxes[firstIng].uri.endsWith('check_on.png'), 'tick shows the checked box');
ok(JSON.parse(store['heirloom.checks'])[rid], 'ticks persist to storage');
press('OK');
ok(run(`isChecked(${JSON.stringify(rid)}, ${firstIng})`) === false, 'OK again unticks');

press('right', 'down');
ok(M().rs.zone === 'steps' && M().rs.sIdx === 1, 'right enters directions, down moves step');
press('play');
ok(M().screen === 'cook' && M().cs.sIdx === 1, 'Play opens cook mode at the focused step');
press('right', 'fastforward');
const advancedStep = Math.min(3, M().rec.steps.length - 1);
ok(M().cs.sIdx === advancedStep, 'right / FF advance the cook step');
press('rewind');
ok(M().cs.sIdx === advancedStep - 1, 'rewind goes back a step');
press('back');
ok(M().screen === 'recipe' && M().rs.zone === 'steps' && M().rs.sIdx === advancedStep - 1, 'Back returns to the recipe on the same step');
press('play', 'play');
ok(M().screen === 'recipe', 'Play toggles cook mode off again');

press('fastforward');
ok(M().rec === M().D.recipes[2], 'FF goes to the next recipe');
press('rewind', 'rewind', 'rewind');
ok(M().rec === M().D.recipes[(1 + n - 2) % n], 'rewind wraps to previous recipes');

// grouped ingredients: headings are never focused
const gi = M().D.recipes.findIndex((r) => r.ingredients.some((i) => i.header));
run(`recipeOpen(${gi})`);
press('left');
ok(!M().rec.ingredients[M().rs.ing].header, 'first focus skips a group heading');
for (let i = 0; i < 30; i++) { press('down'); focusVisible('ing down ' + i); }
for (let i = 0; i < 30; i++) { press('up'); focusVisible('ing up ' + i); }
ok(M().rs.ingTop === 0, 'scrolling back up reveals the first heading');
ok(M().rs.zone === 'servings', 'Up from the first ingredient reaches Serves');
press('down');

// options menu: update, theme, reset
press('OK');
ok(run(`Object.keys(m.checks[m.rec.id] || {}).length`) === 1, 'tick before reset');
press('options');
ok(M().menuOpen, 'Options opens the menu');
const settingsItems = ['Update Now', 'Theme', 'Reset Checkboxes'];
ok(JSON.stringify(M().mstack[0].items.map((item) => item.label)) === JSON.stringify(settingsItems),
  'recipe settings exposes exactly update, theme and reset');
const published = { tag_name: 'v2.0.0', assets: [{ name: 'culinote-roku.zip' }, { name: 'culinote-fire-tv.apk' }] };
press('OK');
const latest = requests[requests.length - 1];
ok(latest.url === M().D.app.latestRelease && downloads.length === 0, 'Update Now checks the release before downloading');
latest.respond(200, published);
ok(M().mTitle.text === 'Confirm Update' && M().mNote.text.includes('v2.0.0') && downloads.length === 0,
  'a newer release shows the exact version before downloading');
press('back');
ok(!M().menuOpen && M().screen === 'recipe' && downloads.length === 0, 'Back exits update confirmation and preserves the underlying screen');
press('options', 'OK');
requests[requests.length - 1].respond(200, published);
press('OK');
ok(downloads[0] === M().D.app.releases + '/download/v2.0.0/culinote-roku.zip', 'Confirm opens the versioned download directly');
run('m.fireTv = true');
press('options', 'OK');
requests[requests.length - 1].respond(200, published);
press('OK');
ok(downloads[1] === M().D.app.releases + '/download/v2.0.0/culinote-fire-tv.apk', 'Fire TV selects the APK');
run('m.fireTv = false');
press('options', 'OK');
requests[requests.length - 1].respond(404, {});
ok(M().mNote.text.includes('no public release') && downloads.length === 2, 'a missing release never starts a download');
press('back', 'options', 'OK', 'back');
requests[requests.length - 1].respond(200, published);
ok(!M().menuOpen && downloads.length === 2, 'a response after Back cannot reopen the menu');
press('options', 'down', 'OK');
ok(M().mTitle.text === 'Theme', 'Theme opens the picker');
press('down', 'OK');
ok(!M().menuOpen && M().themeName === 'midnight' && run('loadTheme()') === 'midnight'
  && M().homeBg.uri === M().L.home.nightBg && M().recipeBg.uri === M().L.recipe.nightBg && M().cookBg.uri === M().L.cook.nightBg,
  'Midnight updates all three backgrounds and persists the choice');
press('options', 'down', 'OK');
ok(M().mstack[1].sel === 1, 'theme menu selects the saved theme');
press('up', 'OK');
ok(M().themeName === 'classic' && run('loadTheme()') === 'classic', 'Classic restores the original appearance');
press('options', 'down', 'down', 'OK');
ok(!M().menuOpen && run(`Object.keys(m.checks[m.rec.id] || {}).length`) === 0, 'Reset checkboxes clears this recipe');
ok(M().toast.visible, 'toast confirms the reset');
press('OK', 'play', 'options');
ok(M().screen === 'cook' && JSON.stringify(M().mstack[0].items.map((item) => item.label)) === JSON.stringify(settingsItems),
  'cook mode exposes the same three settings');
press('back', 'back', 'back', 'options');
ok(M().screen === 'home' && JSON.stringify(M().mstack[0].items.map((item) => item.label)) === JSON.stringify(settingsItems),
  'home exposes the same three settings');
press('down', 'down', 'down');
ok(M().mstack[0].sel === 2, 'menu selection stops at Reset Checkboxes');
press('OK');
ok(!M().menuOpen && Object.keys(JSON.parse(store['heirloom.checks'])).length === 0,
  'Reset Checkboxes from home clears all checklists');
press('options', 'options');
ok(!M().menuOpen, 'Options again closes the menu');
press('options', 'back');
ok(!M().menuOpen, 'Back closes the root menu');

// home back = exit, any key reopens (web)
press('back');
ok(M().top.exitApp === true && ids.exit.hidden === false, 'Back on Home exits the channel');
press('OK');
ok(M().top.exitApp === false && ids.exit.hidden === true, 'web: a key reopens after exit');

// Check all 12 serving sizes for every recipe across the recipe card and cook mode.
run('m.serveCounts = Object.create(null)');
{
  const pork = M().D.recipes.findIndex((recipe) => recipe.id === 'steak-seasoned-skillet-pork-chops');
  run(`recipeOpen(${pork})`);
  const ri = 'm.rs.ing';
  press('left', 'OK', 'up', 'up');
  ok(M().rs.zone === 'servings' && M().rServes === 4 && M().rServingsInput.readOnly && M().rServingsUp.disabled,
    'highlighting Serves leaves it locked and Up does not change the count');
  press('OK');
  for (let i = 4; i < 8; i++) press('up');
  ok(M().rs.zone === 'servingsEdit' && M().rServingsInput.value === '8' && M().rServes === 4 &&
    run('recipeStepText(0)').includes('2 tablespoons Worcestershire'),
    'remote changes the draft while directions keep the confirmed quantity');
  press('OK');
  ok(M().rServes === 8 && run('recipeStepText(0)').includes('4 tablespoons Worcestershire'),
    'OK confirms the count and scales the marinade');
  ok(M().rs.zone === 'ing' && run(`isChecked(m.rec.id, ${ri})`), 'confirming servings preserves checks and restores ingredient focus');
  press('OK', 'right', 'up', 'OK');
  ok(M().rs.zone === 'servingsEdit', 'Up from first direction reaches Serves and OK unlocks it');
  run('m.rServingsDown.listeners.click[0]()');
  ok(M().rServingsInput.value === '7' && M().rServes === 8, 'serving arrow click decreases only the draft');
  press('back');
  ok(M().screen === 'recipe' && M().rs.zone === 'servings' && M().rServingsInput.value === '8',
    'Back cancels editing and restores the confirmed count');
  press('OK');
  M().rServingsInput.value = '99';
  press('OK');
  ok(M().rServes === 12 && M().rs.zone === 'steps' && M().rs.sIdx === 0, 'typed confirmation caps at 12 and restores directions');
  press('up', 'OK');
  M().rServingsInput.value = '0';
  press('OK');
  ok(M().rServes === 1 && M().rServingsDown.disabled, 'typed confirmation stops at 1');
  press('back');
  run(`recipeOpen(${pork})`);
  ok(M().rServes === 1 && M().rs.zone === 'steps' && M().rs.sIdx === 0, 'reopening returns to Direction 1 with the saved serving count');
  run('delete m.serveCounts[m.rec.id]');
}
const portionDirections = {
  'argentine-beef-empanadas': [2, '1/6 lb beef', '2 lb beef'],
  'baked-cod-with-tomatoes': [1, '1 cod fillet', '12 cod fillets'],
  'bitters-heavy-lemonade': [3, 'holds 1 cup', 'holds 12 cups'],
  'blueberry-buttermilk-pancakes': [1, '½ cup buttermilk, ½ egg', '6 cups buttermilk, 6 eggs'],
  'chicken-broccoli-rice-bake': [4, '½ cup cooked rice, 1/3 cup shredded cooked chicken', '6 cups cooked rice, 4 cups shredded cooked chicken'],
  'creamy-chicken-and-wild-rice': [1, '1/8 cup wild rice and 1 cup broth', '1½ cups wild rice and 12 cups broth'],
  'crusty-french-baguettes': [0, '2/3 cup bread flour', '8 cups bread flour'],
  'garlic-butter-baked-salmon': [1, '¾ Tbsp melted butter', '9 Tbsp melted butter'],
  'grandmas-apple-crumble': [1, '5/12 lb apples', '5 lb apples'],
  'huevos-rancheros': [4, '2 eggs across 1 batch', '24 eggs across 6 batches'],
  'irish-soda-bread': [1, '½ cup flour', '6 cups flour'],
  'italian-beef-rigatoni-skillet': [2, '1/5 lb beef', '2 2/5 lb beef'],
  'jamaican-rice-and-peas': [0, '¼ cup rice', '3 cups rice'],
  'lemon-chicken-and-rice': [3, '7/16 cup broth', '5¼ cups broth'],
  'midwest-lemonade-shake-up': [4, 'pitcher to 1 cup', 'pitcher to 12 cups'],
  'pan-seared-trout-almondine': [0, '1 trout fillet', '12 trout fillets'],
  'parmesan-mushroom-risotto': [3, '3/8 cup Arborio rice', '4½ cups Arborio rice'],
  'penne-alla-vodka': [0, '3 oz penne', '36 oz penne'],
  'provencal-ratatouille': [0, '1/6 lb cubed eggplant', '2 lb cubed eggplant'],
  'steak-seasoned-skillet-pork-chops': [0, '½ tablespoon Worcestershire sauce', '6 tablespoons Worcestershire sauce'],
  'strawberry-lemonade': [5, 'measures 1 cup', 'measures 12 cups'],
  'tuscan-lemon-chicken-piccata': [0, 'make 2 thin cutlets', 'make 24 thin cutlets'],
  'vanilla-cream-cheese-cupcakes': [0, '1 standard muffin cup', '12 standard muffin cups'],
};
for (let r = 0; r < n; r++) {
  run(`recipeOpen(${r})`);
  const rec = M().rec;
  ok(M().rServes === rec.serves && rec.serves <= 12 && rec.servingVariants.length === 12, rec.id + ': recipe starts at its default and supports 12');
  const portionExample = portionDirections[rec.id];
  const renderedPortions = new Set();
  for (let count = 1; count <= 12; count++) {
    run(`recipeSetServings(${count})`);
    const variant = rec.servingVariants[count - 1];
    ok(M().rServingsInput.value === String(count), rec.id + ': serving count ' + count);
    ok(M().rMeta[0].text === variant.prepText && M().rMeta[1].text === variant.cookText,
      rec.id + ': time estimates at ' + count);
    if (portionExample) {
      const [stepIndex, single, dozen] = portionExample;
      const directions = run(`recipeStepText(${stepIndex})`);
      if (count === 1) ok(directions.includes(single), rec.id + ': directions give the quantity for one serving');
      if (count === 12) ok(directions.includes(dozen), rec.id + ': directions give the quantity for twelve servings');
      renderedPortions.add(directions);
    }
    rec.ingredients.forEach((item, i) => {
      const label = M().ingNodes[i].kids.find((node) => node.type === 'Label');
      ok(label.text === (variant.ingredients[i] || item.text), rec.id + ': ingredient ' + i + ' at ' + count);
    });
    rec.steps.forEach((step, i) => {
      const label = M().stepNodes[i].kids.find((node) => node.type === 'MultiStyleLabel');
      const expected = variant.steps[i] || step.text;
      ok(label.text === step.lead + ' ' + expected, rec.id + ': direction ' + i + ' at ' + count);
      run(`m.cs = { sIdx: ${i} }; cookRender()`);
      ok(M().cText.text === expected && M().cText.boundingRect().height <= M().L.cook.text.h, rec.id + ': cook text ' + i + ' at ' + count);
      const timing = variant.timers[i] || step;
      ok(M().cTimerLabel.text === (timing.timer > 0 ? 'OK: start a ' + timing.timerText + ' timer' : ''),
        rec.id + ': timer offer matches the selected size for step ' + i + ' at ' + count);
    });
  }
  if (portionExample) ok(renderedPortions.size === 12, rec.id + ': directions change for all 12 serving sizes');
  run('delete m.serveCounts[m.rec.id]');
}

{
  const open = (id) => run(`recipeOpen(m.D.recipes.findIndex((r) => r.id === '${id}'))`);
  open('chicken-broccoli-rice-bake');
  ok(run('recipeStepText(0)').includes('2 cups shredded cooked chicken, 1½ cups milk and ½ cup chicken broth'),
    'six servings show chicken, milk and broth in the opening direction');
  ok(run('recipeStepText(3)').includes('1½ cups milk and ½ cup chicken broth'), 'six servings give the default sauce amounts');
  run('recipeSetServings(12)');
  ok(run('recipeStepText(0)').includes('two baking dishes') &&
    run('recipeStepText(0)').includes('4 cups shredded cooked chicken, 3 cups milk and 1 cup chicken broth') &&
    run('recipeStepText(1)').includes('6 cups broccoli florets in 2 batches') &&
    run('recipeStepText(2)').includes('4 Tbsp flour') &&
    run('recipeStepText(3)').includes('3 cups milk and 1 cup chicken broth') &&
    run('recipeStepText(4)').includes('1 cup crushed crackers'), 'double rice bake scales each cooking stage');
  run('recipeSetServings(1); cookOpen(5)');
  ok(M().cText.text.includes('17 minutes') && M().cText.text.includes('165°F'), 'small rice bake checks earlier at the same doneness temperature');
  open('steak-seasoned-skillet-pork-chops');
  ok(M().rMeta[0].text === '25 min' && M().rMeta[1].text === '35 min', 'pork keeps its default time estimates');
  run('recipeSetServings(12); cookOpen(4)');
  ok(M().rMeta[0].text === '43 min' && M().rMeta[1].text === '58 min' && M().cText.text.includes('3 batches'),
    '12 pork servings add prep work and two skillet batches to the estimate');
  ok(M().cTimerLabel.text === 'OK: start a 3 min timer', 'pork searing timer covers one batch');
  open('irish-soda-bread');
  run('recipeSetServings(4); cookOpen(5)');
  ok(M().cText.text.includes('20 minutes') && M().cTimerLabel.text === 'OK: start a 20 min timer',
    'a smaller soda bread has an earlier check-in in directions and cook mode');
  press('OK');
  ok(M().timer.left === 1200, 'a smaller loaf starts a 20-minute countdown');
  press('OK');
  run('recipeSetServings(8); cookOpen(5)');
  ok(M().cText.text.includes('35 minutes') && M().cTimerLabel.text === 'OK: start a 35 min timer',
    'the default soda bread retains the original check-in');
  open('midwest-lemonade-shake-up');
  run('recipeSetServings(12)');
  ok(M().rMeta[1].text === 'None' && run('recipeStepText(2)').includes('6 batches'),
    '12 servings of lemonade change shaking batches while keeping cook time at None');
  run('m.serveCounts = Object.create(null); m.toast.visible = false');
}

// Nutrition is based on one serving and separately totals the selected batch.
{
  run("recipeOpen(m.D.recipes.findIndex((r) => r.id === 'chicken-broccoli-rice-bake')); recipeSetServings(1)");
  press('left', 'left', 'OK');
  const one = M().mstack[0].nutrition;
  ok(M().mTitle.text === 'Nutrition Estimate' && one.includes('Per serving') && one.includes('Batch total · 1 serving') && M().mNutrition.kids[0].text === 'Per serving',
    'remote opens the nutrition estimate for the selected serving count');
  press('back');
  run('recipeSetServings(12)');
  press('OK');
  const twelve = M().mstack[0].nutrition;
  const perServing = one.split('\n\n')[0];
  const kcal = Number(perServing.match(/(\d+) kcal/)[1]);
  const batchKcal = Number(twelve.split('Batch total · 12 servings\n')[1].match(/^(\d+) kcal/)[1]);
  ok(twelve.startsWith(perServing) && kcal > 250 && kcal < 600 && Math.abs(batchKcal - kcal * 12) <= 6,
    'the per-serving estimate is constant and the batch estimate scales without compounded rounding');
  press('back');
  run('m.serveCounts = Object.create(null)');
}
ok(M().D.recipes.every(recipe => recipe.servingVariants.every(v => /protein.*carbs/.test(v.nutritionText))),
  'all 23 recipes have nutrition estimates at every serving size');

{
  run("recipeOpen(m.D.recipes.findIndex((r) => r.id === 'steak-seasoned-skillet-pork-chops'))");
  ok(M().rStepCount.text === 'Step 1 of 9', 'recipe highlights the first direction');
  const visibleSteps = M().stepNodes.filter(node => node.visible).length;
  ok(M().rStepMore.visible && M().rStepMoreLabel.text === 'Scroll down for more' &&
    visibleSteps >= 3 && M().rStepRange.text === 'Showing 1–' + visibleSteps + ' of 9 steps',
    'long recipe shows more steps and names the hidden remainder');
  press('right');
  for (let i = 0; i < M().rec.steps.length; i++) press('down');
  ok(M().stepNodes[M().rec.steps.length - 1].visible && M().rStepMoreLabel.text === 'Scroll up for earlier steps',
    'the final step is reachable by remote and the cue points back up');
  run("recipeOpen(m.D.recipes.findIndex((r) => r.id === 'garlic-butter-baked-salmon'))");
  ok(!M().rStepMore.visible && M().rStepRange.text === 'Showing 1–3 of 3 steps',
    'the scroll cue stays hidden when every step fits');
}

// exhaustive walk: every recipe, every ingredient and step, cook mode to the end
for (let r = 0; r < n; r++) {
  run(`recipeOpen(${r})`);
  const rec = M().rec;
  ok(M().rCookware.visible && M().rCookwareLabel.text === 'Cookware · ' + rec.cookwareText,
    rec.id + ': cookware is visible on the recipe card');
  focusVisible(rec.id + ' open');
  ok(M().rs.zone === 'steps' && M().rs.sIdx === 0, rec.id + ': opens on the first direction');
  press('left');
  for (let i = 0; i < rec.ingredients.length + 2; i++) { press('down'); focusVisible(rec.id + ' ing'); }
  press('right');
  for (let i = 0; i < rec.steps.length + 2; i++) { press('down'); focusVisible(rec.id + ' step'); }
  ok(M().rs.sIdx === rec.steps.length - 1, rec.id + ': can reach the last step');
  press('up', 'up', 'left', 'right');
  focusVisible(rec.id + ' zones');
  run('cookOpen(0)');
  for (let i = 0; i < rec.steps.length + 1; i++) {
    const before = M().cs.sIdx;
    const hasTimer = rec.steps[before].timer > 0;
    press(hasTimer ? 'right' : 'OK');
    focusVisible(rec.id + ' cook');
    const now = M().rec.steps[M().cs.sIdx];
    ok(M().cText.boundingRect().height <= M().L.cook.text.h, rec.id + ': full cook directions fit above the timer');
    ok(M().cTimerG.visible === (now.timer > 0 || M().timer.on || M().timer.done), rec.id + ': timer line shown only for timed steps');
  }
  if (rec.steps[rec.steps.length - 1].timer === 0) press('OK');
  else run(`showToast('x')`);
  ok(M().cs.sIdx === rec.steps.length - 1 && M().toast.visible, rec.id + ': cook mode reaches the end');
  ok(M().cText.text === rec.steps[rec.steps.length - 1].text, rec.id + ': cook text shows the step');
  press('back');
  ok(M().rs.sIdx === rec.steps.length - 1, rec.id + ': returns to last step');
  press('back');
  ok(M().screen === 'home', rec.id + ': back to Home');
}
// home grid navigation never loses focus
for (const k of ['down', 'down', 'down', 'right', 'right', 'down', 'down', 'down', 'down', 'down', 'up', 'up', 'left', 'up', 'up', 'up', 'up', 'up', 'fastforward', 'rewind']) {
  press(k); focusVisible('home ' + k);
}
// home rows: the next card peeks in under a fade, clipped at the title-safe edge; focused card is scaled
{
  const L = M().L, hl = L.home;
  const rowCards = (r) => M().homeRows.kids.filter((k) => k.type === 'Group' && k.translation[1] === (r - M().hs.top) * hl.rows.rowH + hl.rows.labelH);
  const fades = () => M().homeRows.kids.filter((k) => k.type === 'Poster' && k.uri === 'pkg:/' + hl.peek.fade);
  run('m.hs.row = 0; m.hs.top = 0; m.hs.cols[0] = 0; m.hs.lefts[0] = 0; homeRender()');
  // Give the first category a longer row to exercise peeking even with a small catalog.
  run('m.rows = m.homeCategories.slice(); m.rows[0] = { title: m.rows[0].title, items: [0, 1, 2, 3, 4, 5] }; m.hs.filter = false; homeRender()');
  const clip = M().homeRows.clippingRect;
  ok(hl.rows.x + clip[0] + clip[2] === L.screen.safe[2], 'home rows clip at the right title-safe edge');
  ok(hl.rows.x + clip[0] >= 0 && hl.rows.y + clip[1] + clip[3] <= 1080, 'home clip stays on screen');
  let cards = rowCards(0);
  const pitch = hl.card.w + hl.card.gap;
  ok(cards.length === hl.card.visible + 1, 'a long row renders one peeking card past the visible ones: ' + cards.length);
  const px = cards[hl.card.visible].translation[0];
  ok(px === hl.card.visible * pitch && px < M().homeClipR && px + hl.card.w > M().homeClipR, 'the peeking card straddles the clip edge');
  ok(M().homeClipR - px >= 80, 'at least 80px of the peeking card shows: ' + (M().homeClipR - px));
  ok(cards[hl.card.visible - 1].translation[0] + hl.card.w + 22 * hl.card.focusScale < px + hl.peek.fadeX, 'the fade never covers the last fully visible card (incl. focus glow)');
  ok(fades().length >= 1, 'a fade sits over the peeking card');
  ok(cards[0].scale[0] === hl.card.focusScale && cards[1].scale[0] === 1, 'only the focused card is scaled up');
  ok(cards[0].scaleRotateCenter[0] === hl.card.w / 2, 'focus scale is centred on the card');
  const n0 = M().rows[0].items.length;
  run(`m.hs.cols[0] = ${n0 - 1}; homeRender()`);
  cards = rowCards(0);
  ok(cards.length === hl.card.visible && cards[hl.card.visible - 1].scale[0] === hl.card.focusScale, 'at the end of a row there is no peeking card and the last card has focus');
  const shortRow = M().rows.findIndex((r) => r.items.length <= hl.card.visible);
  run(`m.hs.cols[0] = 0; m.hs.row = ${shortRow}; homeRender()`);
  ok(rowCards(shortRow).length === M().rows[shortRow].items.length, 'a short row renders exactly its cards');
  const rowsShown = [M().hs.top, M().hs.top + 1].filter((r) => r < M().rows.length);
  const longShown = rowsShown.filter((r) => M().rows[r].items.length - M().hs.lefts[r] > hl.card.visible).length;
  ok(fades().length === longShown, 'one fade per row that continues off-screen');
  run('homeApplyFilter("")');
}
// home Play goes straight to cook mode
press('play');
ok(M().screen === 'cook' && M().cs.sIdx === 0, 'Play on Home opens cook mode');
press('back', 'back');
ok(M().screen === 'home', 'two Backs return Home from cook mode');
// unknown keys are not swallowed
ok(run(`onKeyEvent('info', true)`) === false, 'unmapped keys are not handled');
ok(run(`onKeyEvent('OK', false)`) === false, 'key releases are ignored');

// cook-mode step timers
{
  const recs = M().D.recipes;
  ok(recs.every((r) => r.steps.every((st) => /\d+(\s*[–-]\s*\d+)?[\s-]*(second|minute|hour)/i.test(st.text) === (st.timer > 0))),
    'every step that names a duration has a timer, and only those');
  const penne = recs.findIndex((r) => r.id === 'penne-alla-vodka');
  ok(recs[penne].steps[1].timer === 180 && recs[penne].steps[1].timerText === '3 min', 'a 3–4 minute range gives a 3 min timer');
  ok(run('cookClock(75)') === '1:15' && run('cookClock(3725)') === '1:02:05' && run('cookClock(5)') === '0:05', 'cookClock formats m:ss and h:mm:ss');
  let T = 1000000;
  run('nowMs = function () { return __T; }');
  ctx.__T = T;
  run(`recipeOpen(${penne})`);
  run('cookOpen(1)');
  ok(M().cTimerG.visible && M().cTimerLabel.text === 'OK: start a 3 min timer', 'a timed step offers its timer');
  ok(M().cTimerIcon.translation[0] > 0 && M().cTimerIcon.translation[0] < 960, 'timer line is centred on screen');
  press('OK');
  ok(M().cs.sIdx === 1 && M().timer.on && M().timer.step === 1, 'OK on a timed step starts the timer instead of advancing');
  ok(M().toast.visible && M().toastLabel.text === '3 min timer started', 'a toast confirms the timer');
  ok(M().cTimerLabel.text.indexOf('3:00 left') === 0, 'countdown shows the full time at start');
  ctx.__T = T + 61500; run('cookTick()');
  ok(M().cTimerLabel.text.indexOf('1:59 left') === 0, 'countdown follows the clock, not the tick count: ' + M().cTimerLabel.text);
  press('right');
  ok(M().cs.sIdx === 2 && M().cTimerLabel.text === 'Cook the tomato paste: 1:59 left', 'the running timer stays visible on other steps');
  press('back');
  ok(M().screen === 'recipe' && M().timer.on, 'the timer keeps running outside cook mode');
  ctx.__T = T + 180000; run('cookTick()');
  ok(!M().timer.on && M().timer.done && M().toastLabel.text === "Time's up: Cook the tomato paste", 'time up raises a toast even on the recipe card');
  press('play');
  ok(M().screen === 'cook' && M().cTimerLabel.text.indexOf("Time's up") === 0, 'cook mode shows the finished timer');
  const plain = M().rec.steps.findIndex((st) => st.timer === 0);
  run(`m.cs.sIdx = ${plain}; cookRender()`);
  press('OK');
  ok(M().cs.sIdx === plain && !M().timer.done && !M().cTimerG.visible, 'OK dismisses a finished timer without skipping a step');
  press('OK');
  ok(M().cs.sIdx === plain + 1 || plain === M().rec.steps.length - 1, 'then OK advances again');
  run('cookOpen(1)');
  press('OK', 'OK');
  ok(!M().timer.on && M().toastLabel.text === 'Timer stopped', 'OK twice stops the timer');
  press('OK'); run('cookOpen(2)'); press('OK');
  ok(M().timer.on && M().timer.step === 2 && M().cTimerLabel.text.indexOf('2:00 left') === 0, 'starting another step\'s timer replaces the old one');
  press('OK');
  ok(!M().timer.on, 'and OK stops it');
}

// Longer directions can shrink without affecting the font size of the following step.
run(`m.cText.width = 950; m.cText.text = 'Check the thicker pieces before removing them from the skillet. '.repeat(4);
  cookFitText();`);
ok(parseFloat(M().cText.el.style.fontSize) < M().L.cook.text.size
  && M().cText.boundingRect().height <= M().L.cook.text.h, 'cook text shrinks when necessary to fit');
run(`m.cText.width = m.L.cook.text.w; m.cText.text = 'Stir and serve.'; cookFitText();`);
ok(parseFloat(M().cText.el.style.fontSize) === M().L.cook.text.size, 'short directions use the normal type size again');

if (fails.length) {
  console.log(`web test FAILED: ${fails.length} of ${passed + fails.length} assertions`);
  fails.slice(0, 40).forEach((f) => console.log('  - ' + f));
  process.exit(1);
}
console.log(`web test OK (${passed} assertions: navigation, ticks, cook mode, options menu, focus never lost)`);
