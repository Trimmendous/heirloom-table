/* recipe.js: mirrors roku/components/Recipe.brs. */
'use strict';

function recipeBuild() {
  var rl = m.L.recipe, cc = m.L.colors;
  m.recG = mkGroup(m.root, 0, 0);
  m.recG.visible = false;
  m.recipeBg = mkPoster(m.recG, rl.bg, 0, 0, 1920, 1080);
  m.rDish = mkPoster(m.recG, '', rl.dish.x, rl.dish.y, rl.dish.w, rl.dish.h);
  mkLabel(m.recG, 'The Heirloom Table', 'script', rl.header.size, cc.gold, rl.header.x, rl.header.y, rl.header.w, 'center', 0);

  m.rTitle = mkLabel(m.recG, '', 'script', rl.title.size, cc.ink, rl.title.x, rl.title.y, rl.title.w, 'center', 0);
  m.rTitle.height = rl.title.h;
  m.rTitle.vertAlign = 'center';
  m.rDesc = mkLabel(m.recG, '', 'serif', rl.desc.size, cc.ink, rl.desc.x, rl.desc.y, rl.desc.w, 'center', 2);
  var icons = ['clock', 'pot', 'utensils', 'hat'];
  var names = ['Prep', 'Cook', 'Serves', 'Difficulty'];
  var mt = rl.meta;
  m.rMeta = [];
  for (var k = 0; k <= 3; k++) {
    var cx = mt.x + k * mt.colW;
    mkPoster(m.recG, 'images/ui/icon_' + icons[k] + '.png', cx + (mt.colW - 12 - mt.icon) / 2, mt.y, mt.icon, mt.icon);
    mkLabel(m.recG, names[k], 'serifBold', mt.size, cc.ink, cx, mt.y + mt.icon, mt.colW - 12, 'center', 0);
    m.rMeta.push(mkLabel(m.recG, '', 'serif', mt.size, cc.ink, cx, mt.y + mt.icon + 30, mt.colW - 12, 'center', 0));
  }
  m.rGarnish = mkPoster(m.recG, '', rl.garnish.x, rl.garnish.y, rl.garnish.s, rl.garnish.s);

  m.rGarnishSmall = mkPoster(m.recG, '', rl.garnishSmall.x, rl.garnishSmall.y, rl.garnishSmall.s, rl.garnishSmall.s);
  mkLabel(m.recG, 'Ingredients', 'script', rl.ingHeader.size, cc.ink, rl.ingHeader.x, rl.ingHeader.y, rl.ingHeader.w, 'left', 0);
  mkLabel(m.recG, 'Directions', 'script', rl.dirHeader.size, cc.gold, rl.dirHeader.x, rl.dirHeader.y, rl.dirHeader.w, 'left', 0);
  m.rStepCount = mkLabel(m.recG, '', 'serif', 26, cc.goldLight, rl.steps.x + rl.steps.w - 420, rl.dirHeader.y + 28, 400, 'right', 0);

  var nh = mkLabel(m.recG, 'From My Kitchen', 'script', rl.noteHeader.size, cc.ink, rl.noteHeader.x, rl.noteHeader.y, 0, 'left', 0);
  var hw = nh.boundingRect().width;
  if (hw < 50) hw = 300;
  m.rHeart = mkPoster(m.recG, 'images/ui/icon_heart.png', rl.noteHeader.x + hw + 12, rl.noteHeader.y + 14, 34, 34);
  m.rHeartLabel = nh;
  m.rNote = mkLabel(m.recG, '', 'hand', rl.note.size, cc.ink, rl.note.x, rl.note.y, rl.note.w, 'left', rl.note.maxLines);
  m.rPhoto = mkPoster(m.recG, '', rl.photo.x, rl.photo.y, rl.photo.w, rl.photo.h);

  m.rHi = mkRect(m.recG, '0xB8862E33', 0, 0, 10, 10);
  m.rFocus = mkPoster(m.recG, 'images/ui/focus.9.png', 0, 0, 10, 10);
  m.rIngG = mkGroup(m.recG, rl.ingList.x, rl.ingList.y);
  m.rStepG = mkGroup(m.recG, rl.steps.x, rl.steps.y);
  var il = rl.ingList, st = rl.steps;
  m.rIngUp = mkPoster(m.recG, 'images/ui/chev_up_ink.png', il.x + il.w - 30, il.y + 2, 30, 20);
  m.rIngDown = mkPoster(m.recG, 'images/ui/chev_down_ink.png', il.x + il.w - 30, il.y + il.h - 20, 30, 20);
  m.rStepUp = mkPoster(m.recG, 'images/ui/chev_up.png', st.x + st.w - 30, st.y + 2, 30, 20);
  m.rStepDown = mkPoster(m.recG, 'images/ui/chev_down.png', st.x + st.w - 30, st.y + st.h - 20, 30, 20);
  m.rs = { rpos: 0, zone: 'ing', ing: 0, ingTop: 0, sIdx: 0, stepTop: 0 };
}

function recipeOpen(rpos) {
  showScreen('recipe');
  recipeShow(rpos);
}

function recipeShow(rpos) {
  var rl = m.L.recipe, cc = m.L.colors, r = recipeAt(rpos);
  m.rec = r;
  m.rs = { rpos: rpos, zone: 'ing', ing: 0, ingTop: 0, sIdx: 0, stepTop: 0 };
  m.rDish.uri = 'pkg:/' + r.image;
  var size = rl.title.size;
  if (r.title.length > rl.title.longAt) size = rl.title.sizeLong;
  m.rTitle.font = uiFont('script', size);
  m.rTitle.text = r.title;
  m.rDesc.text = r.description;
  m.rMeta[0].text = r.prepText;
  m.rMeta[1].text = r.cookText;
  m.rMeta[2].text = String(r.serves);
  m.rMeta[3].text = r.difficulty;
  m.rGarnish.uri = 'pkg:/' + r.garnish;
  m.rGarnishSmall.uri = 'pkg:/' + r.garnish;
  m.rPhoto.uri = 'pkg:/' + r.photo;
  m.rNote.text = r.kitchenNote;

  var il = rl.ingList, tw = il.w - il.textX - 40;
  removeKids(m.rIngG);
  m.ingNodes = []; m.ingH = []; m.ingBoxes = [];
  var first = -1, g, lb, h, i;
  for (i = 0; i < r.ingredients.length; i++) {
    var it = r.ingredients[i];
    g = m.rIngG.createChild('Group');
    if (it.header) {
      lb = mkLabel(g, it.text, 'serifBold', il.size, cc.rust, 0, 2, il.w - 40, 'left', 2);
      m.ingBoxes.push(null);
      h = textHeight(lb, il.size, it.text.length, il.w - 40) + 2;
    } else {
      if (first < 0) first = i;
      var cb = mkPoster(g, checkUri(r.id, i), 0, 5, il.box, il.box);
      m.ingBoxes.push(cb);
      lb = mkLabel(g, it.text, 'serif', il.size, cc.ink, il.textX, 0, tw, 'left', 3);
      h = textHeight(lb, il.size, it.text.length, tw);
      if (h < il.box + 6) h = il.box + 6;
      webHit(g, il.w - 40, h, recipeClick.bind(null, 'ing', i));
    }
    m.ingNodes.push(g);
    m.ingH.push(h);
  }
  if (first < 0) first = 0;
  m.rs.ing = first;

  var st = rl.steps, sw = st.w - st.textX - 40;
  removeKids(m.rStepG);
  m.stepNodes = []; m.stepH = [];
  for (i = 0; i < r.steps.length; i++) {
    var s = r.steps[i];
    g = m.rStepG.createChild('Group');
    mkPoster(g, 'images/ui/ring.png', 0, 0, st.ring, st.ring);
    mkLabel(g, String(i + 1), 'serifBold', 32, cc.goldLight, 0, 6, st.ring, 'center', 0);
    lb = mkRich(g, '<b>' + s.lead + '</b> ' + s.text, st.size, '0xF0E2C4FF', cc.goldLight, st.textX, 2, sw);
    h = textHeight(lb, st.size, s.lead.length + s.text.length + 1, sw) + 4;
    if (h < st.ring) h = st.ring;
    webHit(g, st.w - 40, h, recipeClick.bind(null, 'steps', i));
    m.stepNodes.push(g);
    m.stepH.push(h);
  }
  recipeLayout();
}

function checkUri(rid, i) {
  if (isChecked(rid, i)) return 'images/ui/check_on.png';
  return 'images/ui/check_off.png';
}

function recipeRefreshChecks() {
  for (var i = 0; i < m.ingBoxes.length; i++) {
    if (m.ingBoxes[i]) m.ingBoxes[i].uri = 'pkg:/' + checkUri(m.rec.id, i);
  }
}

function recipeLayout() {
  var rl = m.L.recipe, rs = m.rs, il = rl.ingList, st = rl.steps, ings = m.rec.ingredients;
  rs.ingTop = fitTop(m.ingH, il.gap, il.h, rs.ingTop, rs.ing);
  if (rs.ingTop > 0 && rs.ingTop === rs.ing) {
    if (ings[rs.ingTop - 1].header && m.ingH[rs.ingTop - 1] + il.gap + m.ingH[rs.ingTop] <= il.h) rs.ingTop = rs.ingTop - 1;
  }
  var lastI = placeItems(m.ingNodes, m.ingH, il.gap, il.h, rs.ingTop);
  if (lastI > rs.ingTop && ings[lastI].header) {
    m.ingNodes[lastI].visible = false;
    lastI = lastI - 1;
  }
  m.rIngUp.visible = rs.ingTop > 0;
  m.rIngDown.visible = lastI < m.ingNodes.length - 1;
  rs.stepTop = fitTop(m.stepH, st.gap, st.h, rs.stepTop, rs.sIdx);
  var lastS = placeItems(m.stepNodes, m.stepH, st.gap, st.h, rs.stepTop);
  m.rStepUp.visible = rs.stepTop > 0;
  m.rStepDown.visible = lastS < m.stepNodes.length - 1;

  var n = m.stepNodes.length, node, x, y, w, h;
  if (rs.zone === 'ing') {
    node = m.ingNodes[rs.ing];
    x = il.x - 12;
    y = il.y + node.translation[1] - 6;
    w = il.w - 22;
    h = m.ingH[rs.ing] + 12;
    m.rHi.color = '0xB8862E38';
    m.rStepCount.text = n + ' steps';
  } else {
    node = m.stepNodes[rs.sIdx];
    x = st.x - 10;
    y = st.y + node.translation[1] - 6;
    w = st.w - 26;
    h = m.stepH[rs.sIdx] + 12;
    m.rHi.color = '0xD9A94A24';
    m.rStepCount.text = 'Step ' + (rs.sIdx + 1) + ' of ' + n;
  }
  m.rHi.setFields({ translation: [x, y], width: w, height: h });
  m.rFocus.setFields({ translation: [x - 14, y - 14], width: w + 28, height: h + 28 });
}

function recipeKey(key) {
  var rs = m.rs, ings = m.rec.ingredients, count = m.D.recipes.length, i;
  if (key === 'up') {
    if (rs.zone === 'ing') {
      i = rs.ing - 1;
      while (i >= 0 && ings[i].header) i = i - 1;
      if (i >= 0) rs.ing = i;
    } else if (rs.sIdx > 0) {
      rs.sIdx = rs.sIdx - 1;
    }
  } else if (key === 'down') {
    if (rs.zone === 'ing') {
      i = rs.ing + 1;
      while (i < ings.length && ings[i].header) i = i + 1;
      if (i < ings.length) rs.ing = i;
    } else if (rs.sIdx < m.stepNodes.length - 1) {
      rs.sIdx = rs.sIdx + 1;
    }
  } else if (key === 'right') {
    rs.zone = 'steps';
  } else if (key === 'left') {
    rs.zone = 'ing';
  } else if (key === 'OK') {
    if (rs.zone === 'ing') {
      setChecked(m.rec.id, rs.ing, !isChecked(m.rec.id, rs.ing));
      recipeRefreshChecks();
    } else {
      cookOpen(rs.sIdx);
      return true;
    }
  } else if (key === 'play') {
    if (rs.zone === 'steps') cookOpen(rs.sIdx);
    else cookOpen(0);
    return true;
  } else if (key === 'rewind') {
    recipeShow((rs.rpos + count - 1) % count);
    return true;
  } else if (key === 'fastforward') {
    recipeShow((rs.rpos + 1) % count);
    return true;
  } else if (key === 'back') {
    homeFocusRecipe(rs.rpos);
    showScreen('home');
    return true;
  } else {
    return false;
  }
  recipeLayout();
  return true;
}

function recipeFocusStep(stepIdx) {
  m.rs.zone = 'steps';
  m.rs.sIdx = stepIdx;
  recipeLayout();
}

/* web only: click focuses an item; clicking the focused item presses OK */
function recipeClick(zone, i) {
  var rs = m.rs;
  if (rs.zone === zone && (zone === 'ing' ? rs.ing : rs.sIdx) === i) { pressKey('OK'); return; }
  rs.zone = zone;
  if (zone === 'ing') rs.ing = i; else rs.sIdx = i;
  recipeLayout();
}
