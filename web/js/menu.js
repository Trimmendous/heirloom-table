/* menu.js: mirrors roku/components/Menu.brs. */
'use strict';

function menuBuild() {
  var ml = m.L.menu, cc = m.L.colors;
  m.menuG = mkGroup(m.root, 0, 0);
  m.menuG.visible = false;
  mkRect(m.menuG, cc.dim, 0, 0, 1920, 1080);
  m.mPanel = mkPoster(m.menuG, 'images/ui/parchment.9.png', ml.panel.x, ml.panel.y, ml.panel.w, ml.panel.h);
  m.mTitle = mkLabel(m.menuG, '', 'script', ml.title.size, cc.ink, ml.title.x, ml.title.y, ml.title.w, 'center', 0);
  var b = ml.back;
  var back = mkGroup(m.menuG, b.x, b.y);
  mkRect(back, '0xB8862E26', 0, 0, b.w, b.h);
  m.mBackFocus = mkPoster(back, 'images/ui/focus.9.png', -9, -9, b.w + 18, b.h + 18);
  mkLabel(back, '‹ Back', 'serifBold', b.size, cc.ink, 0, 5, b.w, 'center', 0);
  var button = document.createElement('button');
  button.type = 'button';
  button.className = 'hit menu-back-hit';
  button.style.width = b.w + 'px';
  button.style.height = b.h + 'px';
  button.setAttribute('aria-label', 'Back');
  button.addEventListener('click', menuClose);
  back.el.appendChild(button);
  m.mHi = mkRect(m.menuG, '0xB8862E40', ml.list.x, ml.list.y, ml.list.w, ml.list.itemH);
  m.mFocus = mkPoster(m.menuG, 'images/ui/focus.9.png', 0, 0, 10, 10);
  m.mList = mkGroup(m.menuG, ml.list.x, ml.list.y);
  m.mNote = mkLabel(m.menuG, '', 'serif', ml.note.size, cc.inkSoft, ml.note.x, 0, ml.note.w, 'left', 7);
  m.mNote.el.style.whiteSpace = 'pre-line';
  m.mNote.el.style.overflowWrap = 'break-word';
  m.mNutrition = mkGroup(m.menuG, ml.note.x, ml.list.y);
  m.mUp = mkPoster(m.menuG, 'images/ui/chev_up_ink.png', 945, ml.list.y - 25, 30, 20);
  m.mDown = mkPoster(m.menuG, 'images/ui/chev_down_ink.png', 945, ml.list.y + ml.filterVisible * ml.list.itemH + 8, 30, 20);
  m.menuOpen = false;
  m.mstack = [];
}

function menuShow() {
  var reset = m.screen === 'home' ? 'resetAll' : 'reset';
  var items = [
    { label: 'Update Now', act: 'updates' },
    { label: 'Theme', act: 'themes' },
    { label: 'Reset Checkboxes', act: reset }
  ];
  menuOpenLevel({ title: 'Options', items: items, sel: 0 });
}

function menuShowFilter() {
  var excluded = Object.keys(m.homeAvoid).length;
  var items = [
    { label: 'All Categories', act: 'filter', arg: '' },
    { label: 'Ingredients to Avoid' + (excluded ? ' (' + excluded + ')' : ''), act: 'avoid' }
  ];
  m.D.categories.forEach(function (category) {
    items.push({ label: category, act: 'filter', arg: category });
  });
  var category = m.D.categories.indexOf(m.homeCategory);
  menuOpenLevel({ title: 'Filter Recipes', items: items, sel: category < 0 ? 0 : category + 2, top: 0 });
}

function menuShowIngredients() {
  var items = [{ label: 'Clear Exclusions', act: 'avoidClear' }];
  m.D.ingredientFilters.forEach(function (ingredient) {
    items.push({ label: ingredient, act: 'avoidToggle', arg: ingredient });
  });
  m.mstack.push({ title: 'Ingredients to Avoid', items: items, sel: 1, top: 0, ingredientPicker: true,
    note: 'Selections apply immediately. For allergies, check package labels and cross-contact.' });
  menuRender();
}

function menuShowNutrition() {
  menuOpenLevel({ title: 'Nutrition Estimate', items: [], sel: -1,
    nutrition: m.servingVariant.nutritionText });
}

function menuRenderNutrition(content) {
  var ml = m.L.menu, cc = m.L.colors;
  removeKids(m.mNutrition);
  var sections = content.split('\n\n');
  for (var section = 0; section < 2; section++) {
    var lines = sections[section].split('\n');
    var y = section * 162;
    mkLabel(m.mNutrition, lines[0], 'serifBold', 33, cc.rust, 0, y, ml.note.w, 'left', 0);
    for (var line = 1; line < lines.length; line++) {
      mkLabel(m.mNutrition, lines[line], 'serif', 29, cc.ink, 0, y + 6 + line * 35, ml.note.w, 'left', 0);
    }
  }
  mkLabel(m.mNutrition, sections[2], 'serif', 25, cc.inkSoft, 0, 334, ml.note.w, 'left', 2);
}

function menuOpenLevel(level) {
  m.mstack = [level];
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
  var n = lv.items.length;
  var start = 0, end = n;
  m.mTitle.text = lv.title;
  m.mNote.text = lv.note || '';
  m.mNote.visible = Boolean(lv.note);
  m.mPanel.height = lv.note ? ml.note.panelH : ml.panel.h;
  m.mNutrition.visible = Boolean(lv.nutrition);
  if (lv.nutrition) {
    m.mPanel.height = ml.nutritionPanelH;
    menuRenderNutrition(lv.nutrition);
  }
  if (lv.top !== undefined) {
    var shown = Math.min(n, lv.ingredientPicker ? ml.ingredientVisible : ml.filterVisible);
    lv.top = Math.max(0, Math.min(lv.top, lv.sel), lv.sel - shown + 1);
    start = lv.top;
    end = start + shown;
    m.mPanel.height = ml.list.y - ml.panel.y + shown * ml.list.itemH + (lv.note ? 132 : 46);
    m.mDown.translation = [945, ml.list.y + shown * ml.list.itemH + 8];
  }
  m.mUp.visible = start > 0;
  m.mDown.visible = end < n;
  if (lv.note) m.mNote.translation = [ml.note.x, ml.list.y + (end - start) * ml.list.itemH + ml.note.gap];
  removeKids(m.mList);
  for (var i = start; i < end; i++) {
    var it = lv.items[i], labelX = 24;
    var row = mkGroup(m.mList, 0, (i - start) * ml.list.itemH);
    if (it.act === 'avoidToggle') {
      mkPoster(row, 'images/ui/' + (m.homeAvoid[it.arg] ? 'check_on.png' : 'check_off.png'), 24, 15, 28, 28);
      labelX = 68;
    }
    mkLabel(row, it.label, 'serif', ml.list.size, cc.ink, labelX, 10, ml.list.w - labelX - 24, 'left', 0);
    webHit(row, ml.list.w, ml.list.itemH, menuClick.bind(null, i));
  }
  var y = ml.list.y + (lv.sel - start) * ml.list.itemH;
  m.mBackFocus.visible = lv.sel < 0;
  m.mHi.visible = lv.sel >= 0;
  m.mFocus.visible = lv.sel >= 0;
  m.mHi.translation = [ml.list.x, y];
  m.mFocus.setFields({ translation: [ml.list.x - 14, y - 14], width: ml.list.w + 28, height: ml.list.itemH + 28 });
}

function menuKey(key) {
  var lv = m.mstack[m.mstack.length - 1];
  if (key === 'up') {
    if (lv.sel >= 0) lv.sel = lv.sel - 1;
  } else if (key === 'down') {
    if (lv.sel < lv.items.length - 1) lv.sel = lv.sel + 1;
  } else if (key === 'rewind') {
    lv.sel = 0;
  } else if (key === 'fastforward') {
    lv.sel = lv.items.length - 1;
  } else if (key === 'OK') {
    if (lv.sel < 0) menuClose();
    else menuActivate(lv.items[lv.sel]);
    return true;
  } else if (key === 'back' || key === 'options' || key === 'left') {
    menuClose();
    return true;
  }
  menuRender();
  return true;
}

function menuActivate(it) {
  if (it.act === 'filter') {
    menuClose();
    homeApplyFilter(it.arg);
  } else if (it.act === 'avoid') {
    menuShowIngredients();
  } else if (it.act === 'avoidToggle' || it.act === 'avoidClear') {
    if (it.act === 'avoidClear') m.homeAvoid = {};
    else if (m.homeAvoid[it.arg]) delete m.homeAvoid[it.arg];
    else m.homeAvoid[it.arg] = true;
    saveIngredientExclusions(m.homeAvoid);
    homeApplyFilter(m.homeCategory);
    menuRender();
  } else if (it.act === 'updates') {
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
    m.mstack.push({ title: 'Theme', note: 'Choose the background for the cookbook.',
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
  }
}

function menuCheckRelease() {
  var level = { title: 'App Update', note: 'Checking GitHub for a newer release...', sel: 0,
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
  var assetName = m.fireTv ? 'culinote-fire-tv.apk' : 'culinote-roku.zip';
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
