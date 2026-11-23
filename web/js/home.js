/* home.js: mirrors roku/components/Home.brs. */
'use strict';

function homeBuild() {
  var hl = m.L.home, cc = m.L.colors;
  m.homeG = mkGroup(m.root, 0, 0);
  m.homeG.visible = false;
  mkPoster(m.homeG, hl.bg, 0, 0, 1920, 1080);
  mkLabel(m.homeG, 'The Heirloom Table', 'script', hl.title.size, cc.gold, hl.title.x, hl.title.y, hl.title.w, 'center', 0);
  mkLabel(m.homeG, 'A COLLECTION OF FAMILY RECIPES, KITCHEN FAVORITES, AND NEW TRADITIONS.', 'serif', hl.tagline.size, cc.goldLight, hl.tagline.x, hl.tagline.y, hl.tagline.w, 'center', 0);
  m.homeRows = mkGroup(m.homeG, hl.rows.x, hl.rows.y);
  m.homeUp = mkPoster(m.homeG, 'images/ui/chev_up.png', 1770, hl.rows.y + 18, 30, 20);
  m.homeDown = mkPoster(m.homeG, 'images/ui/chev_down.png', 1770, hl.rows.y + hl.rows.h - 24, 30, 20);
  m.homeMore = mkLabel(m.homeG, '', 'serif', hl.card.metaSize, cc.goldLight, 1424, hl.rows.y + 14, 330, 'right', 0);

  m.rows = [{ title: 'Every Recipe', items: [] }];
  for (var i = 0; i < m.D.recipes.length; i++) m.rows[0].items.push(i);
  m.D.categories.forEach(function (c) {
    var row = { title: c, items: [] };
    for (var i = 0; i < m.D.recipes.length; i++) if (m.D.recipes[i].category === c) row.items.push(i);
    m.rows.push(row);
  });
  m.hs = { row: 0, top: 0, cols: [], lefts: [] };
  m.rows.forEach(function () { m.hs.cols.push(0); m.hs.lefts.push(0); });
}

function homeRender() {
  var hl = m.L.home, cc = m.L.colors, hs = m.hs;
  var vis = Math.floor(hl.rows.h / hl.rows.rowH);
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
    for (var c = lft; c <= lft + hl.card.visible - 1; c++) {
      if (c >= n) break;
      var rec = m.D.recipes[row.items[c]];
      var g = mkGroup(m.homeRows, (c - lft) * (cw + hl.card.gap), y + hl.rows.labelH);
      if (r === hs.row && c === col) {
        mkPoster(g, 'images/ui/focus.9.png', -22, -22, cw + 44, ch + 44);
      }
      mkThumb(g, rec.thumb, 0, 0, cw, th);
      mkPoster(g, 'images/ui/parchment.9.png', -4, th - 8, cw + 8, ch - th + 12);
      mkLabel(g, rec.title, 'serifBold', hl.card.titleSize, cc.ink, 16, th + 4, cw - 32, 'left', 2);
      mkLabel(g, rec.cuisine + ' · ' + rec.totalText, 'serif', hl.card.metaSize, cc.inkSoft, 16, th + 74, cw - 32, 'left', 0);
      webHit(g, cw, ch, homeClick.bind(null, r, c));
    }
    if (r === hs.row && n > hl.card.visible) {
      m.homeMore.translation = [1424, hl.rows.y + y + 14];
      m.homeMore.text = (col + 1) + ' of ' + n;
    }
  }
  m.homeMore.visible = m.rows[hs.row].items.length > hl.card.visible;
  m.homeUp.visible = hs.top > 0;
  m.homeDown.visible = hs.top + vis < m.rows.length;
}

function homeFocusRecipe(rpos) {
  var items = m.rows[m.hs.row].items;
  for (var c = 0; c < items.length; c++) if (items[c] === rpos) m.hs.cols[m.hs.row] = c;
}

function homeJump(cat) {
  for (var r = 0; r < m.rows.length; r++) {
    if (m.rows[r].title === cat) {
      m.hs.row = r;
      m.hs.cols[r] = 0;
    }
  }
  showScreen('home');
}

function homeKey(key) {
  var hs = m.hs, n = m.rows[hs.row].items.length;
  if (key === 'up') {
    if (hs.row > 0) hs.row = hs.row - 1;
  } else if (key === 'down') {
    if (hs.row < m.rows.length - 1) hs.row = hs.row + 1;
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
  if (m.hs.row === r && m.hs.cols[r] === c) { pressKey('OK'); return; }
  m.hs.row = r; m.hs.cols[r] = c; homeRender();
}
