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
const ctx = {
  document, console, URLSearchParams, setTimeout: (fn) => { ctx.__timers.push(fn); return ctx.__timers.length; },
  clearTimeout() {}, __timers: [], innerWidth: 1920, innerHeight: 1080, location: { search: '' },
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
    ok(lv.sel >= lv.top && lv.sel < lv.top + m.L.menu.list.visible, label + ': menu focus off-list');
    return;
  }
  if (m.screen === 'recipe') {
    const rs = m.rs;
    const node = rs.zone === 'ing' ? m.ingNodes[rs.ing] : m.stepNodes[rs.sIdx];
    ok(node && node.visible, label + ': focused recipe item hidden');
    ok(rs.zone !== 'ing' || !m.rec.ingredients[rs.ing].header, label + ': focus on a group heading');
    ok(onStage(m.rFocus), label + ': focus ring off screen ' + JSON.stringify(m.rFocus.translation));
    const vis = m.ingNodes.map((nd, i) => (nd.visible ? i : -1)).filter((i) => i >= 0);
    ok(!m.rec.ingredients[vis[vis.length - 1]].header, label + ': group heading orphaned at the bottom');
  } else if (m.screen === 'home') {
    const hs = m.hs;
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
ok(m.rows.length === m.D.categories.length + 1, 'one row per category + Every Recipe');
focusVisible('home start');

press('right', 'right');
ok(M().hs.cols[0] === 2, 'right moves along the row');
press('left');
ok(M().hs.cols[0] === 1, 'left moves back');
press('OK');
m = M();
ok(m.screen === 'recipe' && m.rec === m.D.recipes[1], 'OK opens the focused recipe');
focusVisible('recipe open');
const rid = m.rec.id;
const firstIng = m.rs.ing;
press('OK');
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
ok(M().cs.sIdx === 3, 'right / FF advance the cook step');
press('rewind');
ok(M().cs.sIdx === 2, 'rewind goes back a step');
press('back');
ok(M().screen === 'recipe' && M().rs.zone === 'steps' && M().rs.sIdx === 2, 'Back returns to the recipe on the same step');
press('play', 'play');
ok(M().screen === 'recipe', 'Play toggles cook mode off again');

press('fastforward');
ok(M().rec === M().D.recipes[2], 'FF goes to the next recipe');
press('rewind', 'rewind', 'rewind');
ok(M().rec === M().D.recipes[(1 + n - 2) % n], 'rewind wraps to previous recipes');

// grouped ingredients: headings are never focused
const gi = M().D.recipes.findIndex((r) => r.ingredients.some((i) => i.header));
run(`recipeOpen(${gi})`);
ok(!M().rec.ingredients[M().rs.ing].header, 'first focus skips a group heading');
for (let i = 0; i < 30; i++) { press('down'); focusVisible('ing down ' + i); }
for (let i = 0; i < 30; i++) { press('up'); focusVisible('ing up ' + i); }
ok(M().rs.ingTop === 0, 'scrolling back up reveals the first heading');

// options menu: reset, browse, jump
press('OK');
ok(run(`Object.keys(m.checks[m.rec.id] || {}).length`) === 1, 'tick before reset');
press('options');
ok(M().menuOpen, 'Options opens the menu');
press('OK');
ok(!M().menuOpen && run(`Object.keys(m.checks[m.rec.id] || {}).length`) === 0, 'Reset checkboxes clears this recipe');
ok(M().toast.visible, 'toast confirms the reset');
press('options', 'down', 'OK');
ok(M().mstack.length === 2 && M().mstack[1].title === 'All Recipes', 'Browse all recipes opens the list');
const titles = M().mstack[1].items.map((i) => i.label);
ok(JSON.stringify(titles) === JSON.stringify([...titles].sort()), 'recipe list is alphabetical');
press('back');
ok(M().menuOpen && M().mstack.length === 1, 'Back pops one menu level');
ok(M().mstack[0].sel === 1, 'menu keeps its selection after Back');
press('OK', 'down', 'OK');
ok(!M().menuOpen && M().screen === 'recipe' && M().rec.title === titles[1], 'choosing a recipe opens it');
press('options');
const cats = M().D.categories;
for (let i = 0; i < 3; i++) press('down');      // reset, browse, jump to cats[0], cats[1]
press('OK');
ok(M().screen === 'home' && M().rows[M().hs.row].title === cats[1], 'Jump to category lands on that row');
press('options', 'options');
ok(!M().menuOpen, 'Options again closes the menu');
press('options', 'back');
ok(!M().menuOpen, 'Back closes the root menu');

// home back = exit, any key reopens (web)
press('back');
ok(M().top.exitApp === true && ids.exit.hidden === false, 'Back on Home exits the channel');
press('OK');
ok(M().top.exitApp === false && ids.exit.hidden === true, 'web: a key reopens after exit');

// exhaustive walk: every recipe, every ingredient and step, cook mode to the end
for (let r = 0; r < n; r++) {
  run(`recipeOpen(${r})`);
  const rec = M().rec;
  focusVisible(rec.id + ' open');
  for (let i = 0; i < rec.ingredients.length + 2; i++) { press('down'); focusVisible(rec.id + ' ing'); }
  press('right');
  for (let i = 0; i < rec.steps.length + 2; i++) { press('down'); focusVisible(rec.id + ' step'); }
  ok(M().rs.sIdx === rec.steps.length - 1, rec.id + ': can reach the last step');
  press('up', 'up', 'left', 'right');
  focusVisible(rec.id + ' zones');
  run('cookOpen(0)');
  for (let i = 0; i < rec.steps.length + 1; i++) { press('OK'); focusVisible(rec.id + ' cook'); }
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
// home Play goes straight to cook mode
press('play');
ok(M().screen === 'cook' && M().cs.sIdx === 0, 'Play on Home opens cook mode');
press('back', 'back');
ok(M().screen === 'home', 'two Backs return Home from cook mode');
// unknown keys are not swallowed
ok(run(`onKeyEvent('info', true)`) === false, 'unmapped keys are not handled');
ok(run(`onKeyEvent('OK', false)`) === false, 'key releases are ignored');

if (fails.length) {
  console.log(`web test FAILED: ${fails.length} of ${passed + fails.length} assertions`);
  fails.slice(0, 40).forEach((f) => console.log('  - ' + f));
  process.exit(1);
}
console.log(`web test OK (${passed} assertions: navigation, ticks, cook mode, options menu, focus never lost)`);
