/* app.js: mirrors roku/components/MainScene.brs (init, showScreen, onKeyEvent),
 * plus web-only glue: stage scaling, keyboard map, on-screen remote, mouse/touch, exit overlay. */
'use strict';

function init() {
  uiInit();
  m.nativeFireTv = location.hostname === 'cookbook.heirloom.invalid';
  m.fireTv = m.nativeFireTv || new URLSearchParams(location.search).get('platform') === 'fire-tv';
  m.top = { exitApp: false };
  m.root = new Group('Group', null);
  document.getElementById('stage').appendChild(m.root.el);
  m.checks = loadChecks();
  m.screen = '';
  m.rec = m.D.recipes[0];
  homeBuild();
  recipeBuild();
  cookBuild();
  applyTheme(loadTheme());
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

/* Scale the TV canvas to the space left by the browser controls. */
function fitStage() {
  var screen = document.getElementById('screen');
  var s = Math.min(screen.clientWidth / 1920, screen.clientHeight / 1080);
  var st = document.getElementById('stage');
  st.style.transform = 'translate(-50%, -50%) scale(' + s + ')';
}

function flashRemote(key) {
  var platform = m.fireTv ? 'fire-tv' : 'roku';
  var b = document.querySelector('[data-remote="' + platform + '"] [data-key="' + key + '"]');
  if (!b) return;
  b.classList.add('pressed');
  setTimeout(function () { b.classList.remove('pressed'); }, 140);
}

function setPreviewPlatform(platform) {
  var fireTv = platform === 'fire-tv';
  if (fireTv !== m.fireTv && m.menuOpen) menuClose();
  m.fireTv = fireTv;
  m.homeVersion.text = 'v' + m.D.app.version + (fireTv ? '  ·  Menu' : '  ·  * Options');
  document.querySelectorAll('[data-platform]').forEach(function (button) {
    button.setAttribute('aria-pressed', String(button.getAttribute('data-platform') === platform));
  });
  document.querySelectorAll('[data-remote]').forEach(function (remote) {
    remote.hidden = remote.getAttribute('data-remote') !== platform;
  });
}

function setRemoteVisible(visible) {
  var toggle = document.getElementById('remote-toggle');
  document.getElementById('remote-dock').hidden = !visible;
  toggle.setAttribute('aria-expanded', String(visible));
  toggle.textContent = visible ? 'Hide remote' : 'Show remote';
  fitStage();
}

/* Re-measure wrapped text once web fonts are ready (Roku measures synchronously). */
function relayout() {
  if (m.screen === 'recipe') {
    var rs = m.rs;
    recipeShow(rs.rpos, rs);
  } else if (m.screen === 'cook') {
    cookFitText();
  } else if (m.screen === 'home') {
    homeRender();
  }
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
    if (q.get('ing')) {
      m.rs.ing = +q.get('ing');
      if (q.get('zone') !== 'steps') m.rs.zone = 'ing';
      recipeLayout();
    }
    if (q.get('screen') === 'cook') cookOpen(+q.get('step') || 0);
    if (q.get('timer')) { cookKey('OK'); m.toast.visible = false; }
  }
  var row = parseInt(q.get('row'), 10);
  var col = parseInt(q.get('col'), 10);
  if (row >= 0 && row < m.rows.length) m.hs.row = row;
  if (col >= 0 && col < m.rows[m.hs.row].items.length) m.hs.cols[m.hs.row] = col;
  if (q.has('row') || q.has('col')) homeRender();
  if (q.get('menu')) menuShow();
  if (q.get('updates') === '1') {
    menuShow();
    menuActivate(m.mstack[0].items[0]);
  }
}

function boot() {
  init();
  document.getElementById('preview-controls').hidden = m.nativeFireTv;
  setPreviewPlatform(m.fireTv ? 'fire-tv' : 'roku');
  setRemoteVisible(!m.nativeFireTv && new URLSearchParams(location.search).get('remote') !== '0');
  applyQuery();
  window.addEventListener('resize', fitStage);
  document.addEventListener('keydown', function (e) {
    if (e.target === m.rServingsInput && m.rs.zone === 'servingsEdit' && !m.nativeFireTv && !m.menuOpen &&
        !['Enter', 'Escape', 'ArrowUp', 'ArrowDown'].includes(e.key)) return;
    if ((e.key === 'Enter' || e.key === ' ') && e.target.tagName === 'BUTTON') return;
    var k = KEYMAP[e.key];
    if (!k) return;
    e.preventDefault();
    pressKey(k);
  });
  document.querySelectorAll('[data-platform]').forEach(function (button) {
    button.addEventListener('click', function (e) {
      setPreviewPlatform(button.getAttribute('data-platform'));
      if (e.detail) button.blur();
    });
  });
  document.querySelectorAll('[data-key]').forEach(function (button) {
    button.addEventListener('click', function (e) {
      pressKey(button.getAttribute('data-key'));
      if (e.detail) button.blur();
    });
  });
  document.getElementById('remote-toggle').addEventListener('click', function (e) {
    setRemoteVisible(document.getElementById('remote-dock').hidden);
    if (e.detail) e.currentTarget.blur();
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
