/* home.js: mirrors roku/components/Home.brs. */
'use strict';

function homeBuild() {
  var hl = m.L.home, cc = m.L.colors;
  m.homeG = mkGroup(m.root, 0, 0);
  m.homeG.visible = false;
  m.homeBg = mkPoster(m.homeG, hl.bg, 0, 0, 1920, 1080);
  mkLabel(m.homeG, 'Culinote', 'script', hl.title.size, cc.gold, hl.title.x, hl.title.y, hl.title.w, 'center', 0);
  mkLabel(m.homeG, 'A COLLECTION OF FAMILY RECIPES, KITCHEN FAVORITES, AND NEW TRADITIONS.', 'serif', hl.tagline.size, cc.goldLight, hl.tagline.x, hl.tagline.y, hl.tagline.w, 'center', 0);
  var f = hl.filter;
  var filter = mkGroup(m.homeG, f.x, f.y);
  m.homeFilterFocus = mkPoster(filter, 'images/ui/focus.9.png', -14, -14, f.w + 28, f.h + 28);
  mkPoster(filter, 'images/ui/parchment.9.png', 0, 0, f.w, f.h);
  m.homeFilterTint = mkRect(filter, '0xEAB95466', 5, 5, f.w - 10, f.h - 10);
  m.homeFilterLabel = mkLabel(filter, '', 'serifBold', f.size, cc.ink, 12, 10, f.w - 24, 'center', 0);
  var button = document.createElement('button');
  button.type = 'button';
  button.className = 'hit home-filter-hit';
  button.style.width = f.w + 'px';
  button.style.height = f.h + 'px';
  button.setAttribute('aria-label', 'Filter recipes');
  button.setAttribute('aria-haspopup', 'true');
  button.addEventListener('click', function () { button.blur(); homeOpenFilter(); });
  filter.el.appendChild(button);
  var v = hl.version;
  m.homeVersion = mkLabel(m.homeG, '', 'serif', v.size, cc.goldLight, v.x, v.y, v.w, 'right', 0);
  webHit(m.homeVersion, v.w, 40, function () { menuShow(); menuActivate(m.mstack[0].items[0]); });
  m.homeRows = mkGroup(m.homeG, hl.rows.x, hl.rows.y);
  // Clip the rows at the right title-safe edge, so the card after the last visible one peeks in under a fade.
  m.homeClipR = m.L.screen.safe[2] - hl.rows.x;
  m.homeRows.clippingRect = [-48, -60, m.homeClipR + 48, hl.rows.h + 100];
  m.homeUp = mkPoster(m.homeG, 'images/ui/chev_up.png', 1770, hl.rows.y + 18, 30, 20);
  m.homeDown = mkPoster(m.homeG, 'images/ui/chev_down.png', 1770, hl.rows.y + hl.rows.h - 24, 30, 20);
  m.homeMore = mkLabel(m.homeG, '', 'serif', hl.card.metaSize, cc.goldLight, 1424, hl.rows.y + 14, 330, 'right', 0);
  var fn = hl.filterNote;
  m.homeFilterCategory = mkLabel(m.homeG, '', 'serifBold', fn.size, cc.goldLight, fn.x, fn.y, fn.w, 'left', 0);
  m.homeFilterNote = mkLabel(m.homeG, '', 'serif', fn.size, cc.goldLight, fn.x, fn.y + 30, fn.w, 'left', 2);
  m.homeEmpty = mkLabel(m.homeG, 'No recipes match these filters.', 'serif', 34, cc.goldLight, hl.rows.x, hl.rows.y + 26, 950, 'left', 0);

  m.homeCategories = m.D.categories.map(function (c) {
    var row = { title: c, items: [] };
    for (var i = 0; i < m.D.recipes.length; i++) if (m.D.recipes[i].category === c) row.items.push(i);
    return row;
  });
  m.homeAvoid = loadIngredientExclusions();
  homeApplyFilter('');
}

function homeApplyFilter(category) {
  m.homeCategory = category;
  m.rows = [];
  m.homeMatches = [];
  m.homeCategories.forEach(function (row) {
    if (category && row.title !== category) return;
    var items = row.items.filter(function (index) {
      return !m.D.recipes[index].ingredientFilters.some(function (ingredient) { return m.homeAvoid[ingredient]; });
    });
    if (!items.length) return;
    m.rows.push({ title: row.title, items: items });
    m.homeMatches = m.homeMatches.concat(items);
  });
  m.hs = { row: 0, top: 0, cols: [], lefts: [], filter: m.menuOpen || m.rows.length === 0 };
  m.rows.forEach(function () { m.hs.cols.push(0); m.hs.lefts.push(0); });
  var names = m.D.ingredientFilters.filter(function (name) { return m.homeAvoid[name]; });
  var active = Boolean(category || names.length);
  m.homeFilterTint.visible = active;
  m.homeFilterLabel.text = active ? 'Filter · Active' : 'Filter';
  m.homeFilterCategory.visible = active;
  m.homeFilterCategory.text = (category || 'All Categories') + ' · ' + m.homeMatches.length + ' recipes';
  m.homeFilterNote.visible = names.length > 0;
  m.homeFilterNote.text = 'Avoiding ' + (names.length > 2 ? names[0] + ' +' + (names.length - 1) + ' more' : names.join(', '));
  m.homeEmpty.visible = !m.rows.length;
  homeRender();
}

function homeOpenFilter() {
  if (m.menuOpen) return;
  m.hs.filter = true;
  homeRender();
  menuShowFilter();
}

function homeRender() {
  var hl = m.L.home, cc = m.L.colors, hs = m.hs;
  var vis = Math.floor(hl.rows.h / hl.rows.rowH);
  m.homeFilterFocus.visible = hs.filter;
  if (hs.row < hs.top) hs.top = hs.row;
  if (hs.row >= hs.top + vis) hs.top = hs.row - vis + 1;
  removeKids(m.homeRows);
  var cw = hl.card.w, ch = hl.card.h, th = hl.card.thumbH;
  for (var r = hs.top; r <= hs.top + vis - 1; r++) {
    if (r >= m.rows.length) break;
    var row = m.rows[r];
    var y = (r - hs.top) * hl.rows.rowH;
    mkLabel(m.homeRows, row.title, 'script', hl.rows.labelSize, cc.gold, 0, y - 6, 1100, 'left', 0);
    var col = hs.cols[r], lft = hs.lefts[r];
    if (col < lft) lft = col;
    if (col >= lft + hl.card.visible) lft = col - hl.card.visible + 1;
    hs.lefts[r] = lft;
    var n = row.items.length;
    // one card past the visible ones: it peeks in from the right edge (clipped) to show the row goes on
    for (var c = lft; c <= lft + hl.card.visible; c++) {
      if (c >= n) break;
      var rec = m.D.recipes[row.items[c]];
      var g = mkGroup(m.homeRows, (c - lft) * (cw + hl.card.gap), y + hl.rows.labelH);
      if (!hs.filter && r === hs.row && c === col) {
        g.scaleRotateCenter = [cw / 2, ch / 2];
        g.scale = [hl.card.focusScale, hl.card.focusScale];
        mkPoster(g, 'images/ui/focus.9.png', -22, -22, cw + 44, ch + 44);
      }
      mkThumb(g, rec.thumb, 0, 0, cw, th);
      mkPoster(g, 'images/ui/parchment.9.png', -4, th - 8, cw + 8, ch - th + 12);
      mkLabel(g, rec.title, 'serifBold', hl.card.titleSize, cc.ink, 16, th + 4, cw - 32, 'left', 2);
      mkLabel(g, rec.cuisine + ' · ' + rec.totalText, 'serif', hl.card.metaSize, cc.inkSoft, 16, th + 74, cw - 32, 'left', 0);
      webHit(g, cw, ch, homeClick.bind(null, r, c));
    }
    if (lft + hl.card.visible < n) {
      mkPoster(m.homeRows, hl.peek.fade, hl.card.visible * (cw + hl.card.gap) + hl.peek.fadeX, y + hl.rows.labelH - 8, hl.peek.fadeW, ch + 16);
    }
    if (r === hs.row && n > hl.card.visible) {
      m.homeMore.translation = [1424, hl.rows.y + y + 14];
      m.homeMore.text = (col + 1) + ' of ' + n;
    }
  }
  m.homeMore.visible = m.rows.length > 0 && m.rows[hs.row].items.length > hl.card.visible;
  m.homeUp.visible = hs.top > 0;
  m.homeDown.visible = hs.top + vis < m.rows.length;
}

function homeFocusRecipe(rpos) {
  for (var r = 0; r < m.rows.length; r++) {
    var col = m.rows[r].items.indexOf(rpos);
    if (col < 0) continue;
    m.hs.row = r;
    m.hs.cols[r] = col;
    m.hs.filter = false;
    return;
  }
}

function homeAdjacentRecipe(rpos, direction) {
  var items = m.homeMatches;
  if (!items.length) return rpos;
  var col = items.indexOf(rpos);
  return col < 0 ? items[0] : items[(col + direction + items.length) % items.length];
}

function homeKey(key) {
  var hs = m.hs, n = m.rows.length ? m.rows[hs.row].items.length : 0;
  if (key === 'up') {
    if (hs.filter) return true;
    if (hs.row > 0) hs.row = hs.row - 1;
    else hs.filter = true;
  } else if (key === 'down') {
    if (hs.filter && n > 0) hs.filter = false;
    else if (hs.row < m.rows.length - 1) hs.row = hs.row + 1;
  } else if (hs.filter && key === 'OK') {
    homeOpenFilter();
    return true;
  } else if (hs.filter && ['left', 'right', 'play', 'rewind', 'fastforward'].indexOf(key) >= 0) {
    return true;
  } else if (key === 'left' || key === 'rewind') {
    if (hs.cols[hs.row] > 0) hs.cols[hs.row] = hs.cols[hs.row] - 1;
  } else if (key === 'right' || key === 'fastforward') {
    if (hs.cols[hs.row] < n - 1) hs.cols[hs.row] = hs.cols[hs.row] + 1;
  } else if (key === 'OK') {
    recipeOpen(m.rows[hs.row].items[hs.cols[hs.row]]);
    return true;
  } else if (key === 'play') {
    recipeOpen(m.rows[hs.row].items[hs.cols[hs.row]]);
    cookOpen(0);
    return true;
  } else if (key === 'back') {
    m.top.exitApp = true;
    return true;
  } else {
    return false;
  }
  homeRender();
  return true;
}

/* web only: mouse/touch focuses a card, a second click opens it */
function homeClick(r, c) {
  if (!m.hs.filter && m.hs.row === r && m.hs.cols[r] === c) { pressKey('OK'); return; }
  m.hs.filter = false; m.hs.row = r; m.hs.cols[r] = c; homeRender();
}
