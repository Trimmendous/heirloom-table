/* app.js: mirrors roku/components/MainScene.brs (init, showScreen, onKeyEvent),
 * plus web-only glue: stage scaling, keyboard map, on-screen remote, mouse/touch, exit overlay. */
'use strict';

function init() {
  uiInit();
  m.top = { exitApp: false };
  m.root = new Group('Group', null);
  document.getElementById('stage').appendChild(m.root.el);
  m.checks = loadChecks();
  m.screen = '';
  m.rec = m.D.recipes[0];
  homeBuild();
  recipeBuild();
  cookBuild();
  menuBuild();
  m.toast = mkGroup(m.root, 0, 0);
  m.toast.visible = false;
  mkPoster(m.toast, 'images/ui/parchment.9.png', 660, 936, 600, 76);
  m.toastLabel = mkLabel(m.toast, '', 'serifBold', 30, m.L.colors.ink, 660, 956, 600, 'center', 0);
  m.toastTimer = new Timer('Timer', null);
  m.toastTimer.duration = 2.2;
  m.toastTimer.observeField('fire', 'onToastTimer');
  showScreen('home');
}

function showScreen(name) {
  m.screen = name;
  m.homeG.visible = (name === 'home');
  m.recG.visible = (name === 'recipe');
  m.cookG.visible = (name === 'cook');
  if (name === 'home') homeRender();
}

function onKeyEvent(key, press) {
  if (!press) return false;
  if (m.menuOpen) return menuKey(key);
  if (key === 'options') {
    menuShow();
    return true;
  }
  if (m.screen === 'home') return homeKey(key);
  if (m.screen === 'recipe') return recipeKey(key);
  if (m.screen === 'cook') return cookKey(key);
  return false;
}

/* ------------------------------------------------------------------ web-only glue */
var KEYMAP = {
  ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right',
  Enter: 'OK', Backspace: 'back', Escape: 'back', ' ': 'play', '[': 'rewind', ']': 'fastforward',
  '*': 'options', o: 'options', O: 'options'
};

function pressKey(key) {
  if (m.top.exitApp) {            // "channel closed" overlay: any key reopens
    m.top.exitApp = false;
    document.getElementById('exit').hidden = true;
    return true;
  }
  var handled = onKeyEvent(key, true);
  if (m.top.exitApp) document.getElementById('exit').hidden = false;
  flashRemote(key);
  return handled;
}

/* invisible hit area so mouse/touch can drive any focusable item */
function webHit(node, w, h, fn) {
  var d = document.createElement('div');
  d.className = 'hit';
  d.style.width = w + 'px';
  d.style.height = h + 'px';
  d.addEventListener('click', function (e) { e.stopPropagation(); fn(); });
  node.el.appendChild(d);
}

/* scale the 1920x1080 stage to the window, leaving room for the on-screen remote when it is shown */
function fitStage() {
  var side = document.body.classList.contains('no-remote') ? 0 : 196;
  var w = Math.max(320, window.innerWidth - side);
  var s = Math.min(w / 1920, window.innerHeight / 1080);
  var st = document.getElementById('stage');
  st.style.left = (w / 2) + 'px';
  st.style.transform = 'translate(-50%, -50%) scale(' + s + ')';
}

function flashRemote(key) {
  var b = document.querySelector('#remote [data-key="' + key + '"]');
  if (!b) return;
  b.classList.add('pressed');
  setTimeout(function () { b.classList.remove('pressed'); }, 140);
}

/* Re-measure wrapped text once web fonts are ready (Roku measures synchronously). */
function relayout() {
  if (m.screen === 'recipe') {
    var rs = m.rs;
    recipeShow(rs.rpos);
    m.rs.zone = rs.zone; m.rs.ing = rs.ing; m.rs.sIdx = rs.sIdx;
    recipeLayout();
  } else if (m.screen === 'home') {
    homeRender();
  }
  var hw = m.rHeartLabel.boundingRect().width;
  m.rHeart.translation = [m.L.recipe.noteHeader.x + (hw < 50 ? 300 : hw) + 12, m.L.recipe.noteHeader.y + 14];
}

/* ?screen=recipe&id=<id>&zone=steps&step=2&menu=1 (&timer=1 starts a cook timer) — deep links used by tools/screenshot.py */
function applyQuery() {
  var q = new URLSearchParams(location.search);
  var id = q.get('id');
  var rpos = 0;
  if (id) m.D.recipes.forEach(function (r, i) { if (r.id === id) rpos = i; });
  if (q.get('screen') === 'recipe' || q.get('screen') === 'cook') {
    recipeOpen(rpos);
    if (q.get('zone') === 'steps') recipeFocusStep(+q.get('step') || 0);
    if (q.get('ing')) { m.rs.ing = +q.get('ing'); recipeLayout(); }
    if (q.get('screen') === 'cook') cookOpen(+q.get('step') || 0);
    if (q.get('timer')) { cookKey('OK'); m.toast.visible = false; }
  }
  if (q.get('row')) { m.hs.row = +q.get('row'); homeRender(); }
  if (q.get('menu')) menuShow();
  if (q.get('remote') === '0') document.body.classList.add('no-remote');
  fitStage();
}

function boot() {
  init();
  applyQuery();
  fitStage();
  window.addEventListener('resize', fitStage);
  document.addEventListener('keydown', function (e) {
    var k = KEYMAP[e.key];
    if (!k) return;
    e.preventDefault();
    pressKey(k);
  });
  document.querySelectorAll('#remote [data-key]').forEach(function (b) {
    b.addEventListener('click', function () { pressKey(b.getAttribute('data-key')); });
  });
  document.getElementById('remote-toggle').addEventListener('click', function () {
    document.body.classList.toggle('no-remote');
    fitStage();
  });
  document.getElementById('stage').addEventListener('wheel', function (e) {
    e.preventDefault();
    pressKey(e.deltaY > 0 ? 'down' : 'up');
  }, { passive: false });
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () { relayout(); document.body.classList.add('fonts-ready'); });
  } else {
    document.body.classList.add('fonts-ready');
  }
}

if (typeof document !== 'undefined' && document.readyState !== 'loading') boot();
else if (typeof document !== 'undefined') document.addEventListener('DOMContentLoaded', boot);
