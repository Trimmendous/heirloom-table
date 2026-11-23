/* menu.js: mirrors roku/components/Menu.brs. */
'use strict';

function menuBuild() {
  var ml = m.L.menu, cc = m.L.colors;
  m.menuG = mkGroup(m.root, 0, 0);
  m.menuG.visible = false;
  mkRect(m.menuG, cc.dim, 0, 0, 1920, 1080);
  mkPoster(m.menuG, 'images/ui/parchment.9.png', ml.panel.x, ml.panel.y, ml.panel.w, ml.panel.h);
  m.mTitle = mkLabel(m.menuG, '', 'script', ml.title.size, cc.ink, ml.title.x, ml.title.y, ml.title.w, 'center', 0);
  m.mHi = mkRect(m.menuG, '0xB8862E40', ml.list.x, ml.list.y, ml.list.w, ml.list.itemH);
  m.mFocus = mkPoster(m.menuG, 'images/ui/focus.9.png', 0, 0, 10, 10);
  m.mList = mkGroup(m.menuG, ml.list.x, ml.list.y);
  m.mUp = mkPoster(m.menuG, 'images/ui/chev_up_ink.png', ml.list.x + ml.list.w / 2 - 15, ml.list.y - 26, 30, 20);
  m.mDown = mkPoster(m.menuG, 'images/ui/chev_down_ink.png', ml.list.x + ml.list.w / 2 - 15, ml.list.y + ml.list.visible * ml.list.itemH + 4, 30, 20);
  m.menuOpen = false;
  m.mstack = [];
}

function menuShow() {
  var items = [];
  if (m.screen === 'home') {
    items.push({ label: 'Reset all checkboxes', act: 'resetAll', arg: '' });
  } else {
    items.push({ label: 'Reset checkboxes', act: 'reset', arg: '' });
  }
  items.push({ label: 'Browse all recipes', act: 'list', arg: '' });
  m.D.categories.forEach(function (c) { items.push({ label: 'Jump to ' + c, act: 'cat', arg: c }); });
  if (m.screen !== 'home') items.push({ label: 'Back to home', act: 'home', arg: '' });
  m.mstack = [{ title: 'Options', items: items, sel: 0, top: 0 }];
  m.menuOpen = true;
  m.menuG.visible = true;
  menuRender();
}

function menuClose() {
  m.menuOpen = false;
  m.menuG.visible = false;
}

function menuRender() {
  var ml = m.L.menu, cc = m.L.colors, lv = m.mstack[m.mstack.length - 1];
  var n = lv.items.length, vis = ml.list.visible;
  if (lv.sel < lv.top) lv.top = lv.sel;
  if (lv.sel >= lv.top + vis) lv.top = lv.sel - vis + 1;
  m.mTitle.text = lv.title;
  removeKids(m.mList);
  for (var i = lv.top; i <= lv.top + vis - 1; i++) {
    if (i >= n) break;
    var lb = mkLabel(m.mList, lv.items[i].label, 'serif', ml.list.size, cc.ink, 24, (i - lv.top) * ml.list.itemH + 10, ml.list.w - 48, 'left', 0);
    webHit(lb, ml.list.w - 48, ml.list.itemH, menuClick.bind(null, i));
  }
  var y = ml.list.y + (lv.sel - lv.top) * ml.list.itemH;
  m.mHi.translation = [ml.list.x, y];
  m.mFocus.setFields({ translation: [ml.list.x - 14, y - 14], width: ml.list.w + 28, height: ml.list.itemH + 28 });
  m.mUp.visible = lv.top > 0;
  m.mDown.visible = lv.top + vis < n;
}

function menuKey(key) {
  var lv = m.mstack[m.mstack.length - 1];
  if (key === 'up') {
    if (lv.sel > 0) lv.sel = lv.sel - 1;
  } else if (key === 'down') {
    if (lv.sel < lv.items.length - 1) lv.sel = lv.sel + 1;
  } else if (key === 'rewind') {
    lv.sel = lv.sel - m.L.menu.list.visible;
    if (lv.sel < 0) lv.sel = 0;
  } else if (key === 'fastforward') {
    lv.sel = lv.sel + m.L.menu.list.visible;
    if (lv.sel > lv.items.length - 1) lv.sel = lv.items.length - 1;
  } else if (key === 'OK') {
    menuActivate(lv.items[lv.sel]);
    return true;
  } else if (key === 'back' || key === 'left') {
    if (m.mstack.length > 1) {
      m.mstack.pop();
    } else {
      menuClose();
      return true;
    }
  } else if (key === 'options') {
    menuClose();
    return true;
  }
  menuRender();
  return true;
}

function menuActivate(it) {
  if (it.act === 'reset') {
    delete m.checks[m.rec.id];
    saveChecks();
    recipeRefreshChecks();
    menuClose();
    showToast('Checkboxes cleared');
  } else if (it.act === 'resetAll') {
    m.checks = {};
    saveChecks();
    menuClose();
    showToast('All checkboxes cleared');
  } else if (it.act === 'list') {
    var items = [];
    for (var i = 0; i < m.D.recipes.length; i++) items.push({ label: m.D.recipes[i].title, act: 'open', arg: i });
    items.sort(function (a, b) { return a.label < b.label ? -1 : a.label > b.label ? 1 : 0; });
    m.mstack.push({ title: 'All Recipes', items: items, sel: 0, top: 0 });
    menuRender();
  } else if (it.act === 'open') {
    menuClose();
    recipeOpen(it.arg);
  } else if (it.act === 'cat') {
    menuClose();
    homeJump(it.arg);
  } else if (it.act === 'home') {
    menuClose();
    showScreen('home');
  }
}

/* web only */
function menuClick(i) {
  var lv = m.mstack[m.mstack.length - 1];
  if (lv.sel === i) { pressKey('OK'); return; }
  lv.sel = i; menuRender();
}
