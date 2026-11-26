/* menu.js: mirrors roku/components/Menu.brs. */
'use strict';

function menuBuild() {
  var ml = m.L.menu, cc = m.L.colors;
  m.menuG = mkGroup(m.root, 0, 0);
  m.menuG.visible = false;
  mkRect(m.menuG, cc.dim, 0, 0, 1920, 1080);
  m.mPanel = mkPoster(m.menuG, 'images/ui/parchment.9.png', ml.panel.x, ml.panel.y, ml.panel.w, ml.panel.h);
  m.mTitle = mkLabel(m.menuG, '', 'script', ml.title.size, cc.ink, ml.title.x, ml.title.y, ml.title.w, 'center', 0);
  m.mHi = mkRect(m.menuG, '0xB8862E40', ml.list.x, ml.list.y, ml.list.w, ml.list.itemH);
  m.mFocus = mkPoster(m.menuG, 'images/ui/focus.9.png', 0, 0, 10, 10);
  m.mList = mkGroup(m.menuG, ml.list.x, ml.list.y);
  m.mUp = mkPoster(m.menuG, 'images/ui/chev_up_ink.png', ml.list.x + ml.list.w / 2 - 15, ml.list.y - 26, 30, 20);
  m.mDown = mkPoster(m.menuG, 'images/ui/chev_down_ink.png', ml.list.x + ml.list.w / 2 - 15, ml.list.y + ml.list.visible * ml.list.itemH + 4, 30, 20);
  m.mNote = mkLabel(m.menuG, '', 'serif', ml.note.size, cc.inkSoft, ml.note.x, 0, ml.note.w, 'left', 7);
  m.mNote.el.style.whiteSpace = 'pre-line';
  m.mNote.el.style.overflowWrap = 'break-word';
  m.menuOpen = false;
  m.mstack = [];
}

function menuShow() {
  var items = [
    { label: 'Update Now', act: 'updates' },
    { label: 'Theme', act: 'themes' }
  ];
  if (m.screen === 'home') {
    items.push({ label: 'Reset all checkboxes', act: 'resetAll', arg: '' });
  } else {
    items.push({ label: 'Reset checkboxes', act: 'reset', arg: '' });
  }
  items.push({ label: 'Browse all recipes', act: 'list', arg: '' });
  m.D.categories.forEach(function (c) { items.push({ label: 'Jump to ' + c, act: 'cat', arg: c }); });
  if (m.screen !== 'home') items.push({ label: 'Back to home', act: 'home', arg: '' });
  m.mstack = [{ title: 'Options', note: '', items: items, sel: 0, top: 0 }];
  m.menuOpen = true;
  m.menuG.visible = true;
  menuRender();
}

function menuClose() {
  m.menuOpen = false;
  m.menuG.visible = false;
  m.mstack = [];
}

function menuRender() {
  var ml = m.L.menu, cc = m.L.colors, lv = m.mstack[m.mstack.length - 1];
  var n = lv.items.length, vis = ml.list.visible;
  if (lv.sel < lv.top) lv.top = lv.sel;
  if (lv.sel >= lv.top + vis) lv.top = lv.sel - vis + 1;
  m.mTitle.text = lv.title;
  m.mNote.text = lv.note || '';
  m.mNote.visible = Boolean(lv.note);
  m.mPanel.height = lv.note ? ml.note.panelH : ml.panel.h;
  if (lv.note) m.mNote.translation = [ml.note.x, ml.list.y + n * ml.list.itemH + ml.note.gap];
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
  } else if (key === 'back' || key === 'options' || key === 'left') {
    menuClose();
    return true;
  }
  menuRender();
  return true;
}

function menuActivate(it) {
  if (it.act === 'updates') {
    menuCheckRelease();
  } else if (it.act === 'download') {
    menuClose();
    if (m.nativeFireTv) {
      location.assign(it.arg);
    } else {
      window.open(it.arg, '_blank', 'noopener');
    }
  } else if (it.act === 'close') {
    menuClose();
  } else if (it.act === 'themes') {
    m.mstack.push({ title: 'Theme', note: 'Choose the background for the cookbook.', top: 0,
      sel: m.themeName === 'midnight' ? 1 : 0, items: [
        { label: 'Classic', act: 'theme', arg: 'classic' },
        { label: 'Midnight', act: 'theme', arg: 'midnight' }
      ] });
    menuRender();
  } else if (it.act === 'theme') {
    applyTheme(it.arg);
    saveTheme(it.arg);
    menuClose();
    showToast(it.arg === 'midnight' ? 'Midnight theme applied' : 'Classic theme applied');
  } else if (it.act === 'reset') {
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

function menuCheckRelease() {
  var level = { title: 'App Update', note: 'Checking GitHub for a newer release...', sel: 0, top: 0,
    items: [{ label: 'Cancel', act: 'close' }] };
  m.mstack.push(level);
  menuRender();

  var request = new XMLHttpRequest();
  request.open('GET', m.D.app.latestRelease);
  request.timeout = 12000;
  request.onload = function () {
    var release;
    try { release = JSON.parse(request.responseText); } catch (e) { /* handled as an unavailable release */ }
    menuReleaseResult(level, request.status, release);
  };
  request.onerror = request.ontimeout = function () { menuReleaseResult(level, 0); };
  request.send();
}

function menuReleaseResult(level, status, release) {
  if (!m.menuOpen || m.mstack[m.mstack.length - 1] !== level) return;

  var app = m.D.app;
  var version = release && /^v?([0-9]{1,3})[.]([0-9]{1,3})[.]([0-9]{1,3})$/.exec(release.tag_name);
  var assetName = m.fireTv ? 'heirloom-table-fire-tv.apk' : 'heirloom-table-roku.zip';
  level.items = [{ label: 'Close', act: 'close' }];
  if (status === 404) {
    level.note = 'GitHub has no public release available. Installed version v' + app.version + '.';
  } else if (status !== 200 || !version) {
    level.note = 'Could not check for updates. Try again later.';
  } else if (Number(version[1]) * 1000000 + Number(version[2]) * 1000 + Number(version[3]) <= app.versionCode) {
    level.note = 'Version v' + app.version + ' is up to date.';
  } else if (!Array.isArray(release.assets) || !release.assets.some(function (asset) { return asset.name === assetName; })) {
    level.note = 'GitHub release ' + release.tag_name + ' is missing the ' + (m.fireTv ? 'Fire TV APK.' : 'Roku ZIP.');
  } else {
    level.title = 'Confirm Update';
    level.note = 'Installed v' + app.version + '\nGitHub release v' + version.slice(1).join('.') +
      '\n\n' + (m.fireTv ? 'Download the APK, then confirm in the Fire TV installer.' : 'Download the ZIP for Roku’s developer installer.');
    level.items = [
      { label: 'Download v' + version.slice(1).join('.'), act: 'download', arg: app.releases + '/download/' + release.tag_name + '/' + assetName },
      { label: 'Cancel', act: 'close' }
    ];
  }
  menuRender();
}

/* web only */
function menuClick(i) {
  var lv = m.mstack[m.mstack.length - 1];
  lv.sel = i;
  pressKey('OK');
}
