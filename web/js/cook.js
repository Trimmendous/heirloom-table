/* cook.js: mirrors roku/components/Cook.brs (cook mode + step timers). */
'use strict';

function cookBuild() {
  var kl = m.L.cook, cc = m.L.colors;
  m.cookG = mkGroup(m.root, 0, 0);
  m.cookG.visible = false;
  m.cookBg = mkPoster(m.cookG, kl.bg, 0, 0, 1920, 1080);
  m.cTitle = mkLabel(m.cookG, '', 'script', kl.title.size, cc.ink, kl.title.x, kl.title.y, kl.title.w, 'center', 0);
  m.cCounter = mkLabel(m.cookG, '', 'serifBold', kl.counter.size, cc.rust, kl.counter.x, kl.counter.y, kl.counter.w, 'center', 0);
  mkPoster(m.cookG, 'images/ui/ring_lg.png', kl.ring.x, kl.ring.y, kl.ring.s, kl.ring.s);
  m.cNum = mkLabel(m.cookG, '', 'serifBold', kl.ring.size, cc.goldLight, kl.ring.x, kl.ring.y + 14, kl.ring.s, 'center', 0);
  m.cLead = mkLabel(m.cookG, '', 'serifBold', kl.lead.size, cc.ink, kl.lead.x, kl.lead.y, kl.lead.w, 'center', 0);
  m.cText = mkLabel(m.cookG, '', 'serif', kl.text.size, cc.ink, kl.text.x, kl.text.y, kl.text.w, 'center', kl.text.maxLines);
  m.cTimerG = mkGroup(m.cookG, 0, kl.timer.y);
  m.cTimerIcon = mkPoster(m.cTimerG, 'images/ui/icon_clock.png', 0, 0, kl.timer.icon, kl.timer.icon);
  m.cTimerLabel = mkLabel(m.cTimerG, '', 'serifBold', kl.timer.size, cc.rust, 0, -4, 0, 'left', 0);
  m.cDots = mkGroup(m.cookG, 0, kl.dots.y);
  m.cHint = mkLabel(m.cookG, '', 'serif', kl.hint.size, cc.inkSoft, kl.hint.x, kl.hint.y, kl.hint.w, 'center', 0);
  m.cs = { sIdx: 0 };
  m.timer = { on: false, done: false, endMs: 0, left: 0, rid: '', step: -1, lead: '' };
  m.wakeN = 0;
  m.cTick = new Timer('Timer', null);
  m.cTick.duration = 1;
  m.cTick.repeat = true;
  m.cTick.observeField('fire', 'cookTick');
}

function cookOpen(stepIdx) {
  m.cs = { sIdx: stepIdx };
  showScreen('cook');
  cookRender();
  m.cTick.control = 'start';
  cookKeepAwake();
}

function cookRender() {
  var kl = m.L.cook, r = m.rec, n = r.steps.length, i = m.cs.sIdx, s = r.steps[i];
  m.cTitle.text = r.title;
  m.cCounter.text = 'Step ' + (i + 1) + ' of ' + n;
  m.cNum.text = String(i + 1);
  m.cLead.text = s.lead;
  m.cText.text = s.text;
  if (s.timer > 0 && i === n - 1) {
    m.cHint.text = 'Last step   ·   OK: start or stop the timer   ·   Left: previous   ·   Play or Back: recipe';
  } else if (s.timer > 0) {
    m.cHint.text = 'OK: start or stop the timer   ·   Right: next step   ·   Left: previous   ·   Play or Back: recipe';
  } else if (i === n - 1) {
    m.cHint.text = 'Last step. Enjoy your meal!   ·   Left: previous   ·   Play or Back: return to the recipe';
  } else {
    m.cHint.text = 'Right or OK: next step   ·   Left: previous   ·   Play or Back: return to the recipe';
  }
  removeKids(m.cDots);
  var total = n * kl.dots.s + (n - 1) * kl.dots.gap;
  var x0 = (1920 - total) / 2;
  for (var d = 0; d < n; d++) {
    var uri = 'images/ui/dot_off.png';
    if (d <= i) uri = 'images/ui/dot_on.png';
    mkPoster(m.cDots, uri, x0 + d * (kl.dots.s + kl.dots.gap), 0, kl.dots.s, kl.dots.s);
  }
  cookTimerRender();
}

/* The clock line above the progress dots: an offer, a live countdown, or "time's up". */
function cookTimerRender() {
  var kl = m.L.cook.timer, s = m.rec.steps[m.cs.sIdx], t = m.timer, txt = '';
  if (t.on && t.rid === m.rec.id && t.step === m.cs.sIdx) {
    txt = cookClock(t.left) + ' left   ·   OK: stop the timer';
  } else if (t.on) {
    txt = t.lead + ': ' + cookClock(t.left) + ' left';
  } else if (t.done) {
    txt = "Time's up: " + t.lead + '   ·   OK: dismiss';
  } else if (s.timer > 0) {
    txt = 'OK: start a ' + s.timerText + ' timer';
  }
  m.cTimerG.visible = (txt !== '');
  m.cTimerLabel.text = txt;
  var w = m.cTimerLabel.boundingRect().width;
  if (w < 10) w = txt.length * kl.size * 0.45;
  var x0 = (1920 - (kl.icon + kl.gap + w)) / 2;
  m.cTimerIcon.translation = [x0, 0];
  m.cTimerLabel.translation = [x0 + kl.icon + kl.gap, -4];
}

/* 75 -> "1:15", 3725 -> "1:02:05" */
function cookClock(sec) {
  var h = Math.floor(sec / 3600);
  var mn = Math.floor((sec - h * 3600) / 60);
  var sc = sec - h * 3600 - mn * 60;
  var ss = String(sc);
  if (sc < 10) ss = '0' + ss;
  if (h === 0) return mn + ':' + ss;
  var ms = String(mn);
  if (mn < 10) ms = '0' + ms;
  return h + ':' + ms + ':' + ss;
}

function cookTimerToggle() {
  var s = m.rec.steps[m.cs.sIdx], t = m.timer;
  if (s.timer === 0) {
    t.done = false;
  } else if (t.on && t.rid === m.rec.id && t.step === m.cs.sIdx) {
    t.on = false;
    showToast('Timer stopped');
  } else {
    var lead = s.lead;
    if (lead.slice(-1) === '.') lead = lead.slice(0, -1);
    m.timer = { on: true, done: false, endMs: nowMs() + s.timer * 1000, left: s.timer, rid: m.rec.id, step: m.cs.sIdx, lead: lead };
    m.cTick.control = 'start';
    showToast(s.timerText + ' timer started');
  }
}

/* Fires every second while cook mode is open or a timer is running. */
function cookTick() {
  var t = m.timer;
  if (t.on) {
    t.left = Math.floor((t.endMs - nowMs() + 999) / 1000);
    if (t.left <= 0) {
      t.on = false;
      t.done = true;
      t.left = 0;
      showToast("Time's up: " + t.lead);
    }
  }
  if (m.screen === 'cook') {
    cookTimerRender();
    m.wakeN = m.wakeN + 1;
    if (m.wakeN >= 30) {
      m.wakeN = 0;
      cookKeepAwake();
    }
  } else if (!t.on) {
    m.cTick.control = 'stop';
    if (m.wakeLock) { m.wakeLock.release(); m.wakeLock = null; }   // web only: let the screen sleep again
  }
}

/* Long simmering steps shouldn't let the screen sleep. Roku: roAppManager.UpdateLastKeyPressTime();
 * web: the Screen Wake Lock API where the browser has it (re-requested every 30 s, as it drops when hidden). */
function cookKeepAwake() {
  if (m.wakeLock || typeof navigator === 'undefined' || !navigator.wakeLock) return;
  navigator.wakeLock.request('screen').then(function (l) {
    m.wakeLock = l;
    l.addEventListener('release', function () { m.wakeLock = null; });
  }).catch(function () { /* not allowed (e.g. file:// or hidden tab): fine */ });
}

function cookKey(key) {
  var n = m.rec.steps.length;
  if (key === 'left' || key === 'rewind' || key === 'up') {
    if (m.cs.sIdx > 0) m.cs.sIdx = m.cs.sIdx - 1;
  } else if (key === 'OK' && (m.rec.steps[m.cs.sIdx].timer > 0 || m.timer.done)) {
    cookTimerToggle();
  } else if (key === 'right' || key === 'fastforward' || key === 'down' || key === 'OK') {
    if (m.cs.sIdx < n - 1) {
      m.cs.sIdx = m.cs.sIdx + 1;
    } else if (key === 'OK') {
      showToast('Bon appétit!');
    }
  } else if (key === 'play' || key === 'back') {
    showScreen('recipe');
    recipeFocusStep(m.cs.sIdx);
    return true;
  } else {
    return false;
  }
  cookRender();
  return true;
}
