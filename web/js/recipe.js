/* recipe.js: mirrors roku/components/Recipe.brs. */
'use strict';

function recipeBuild() {
  var rl = m.L.recipe, cc = m.L.colors;
  m.recG = mkGroup(m.root, 0, 0);
  m.recG.visible = false;
  m.recipeBg = mkPoster(m.recG, rl.bg, 0, 0, 1920, 1080);
  m.rDish = mkPoster(m.recG, '', rl.dish.x, rl.dish.y, rl.dish.w, rl.dish.h);
  var cw = rl.cookware;
  m.rCookware = mkGroup(m.recG, cw.x, cw.y);
  mkRect(m.rCookware, '0x160F0AEC', 0, 0, cw.w, cw.h);
  m.rCookwareLabel = mkLabel(m.rCookware, '', 'serif', cw.size, cc.goldLight, 14, 3, cw.w - 28, 'center', 2);
  mkLabel(m.recG, 'Culinote', 'script', rl.header.size, cc.gold, rl.header.x, rl.header.y, rl.header.w, 'center', 0);

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
    m.rMeta.push(k === 2 ? null : mkLabel(m.recG, '', 'serif', mt.size, cc.ink, cx, mt.y + mt.icon + 30, mt.colW - 12, 'center', 0));
  }
  m.rGarnish = mkPoster(m.recG, '', rl.garnish.x, rl.garnish.y, rl.garnish.s, rl.garnish.s);

  m.rGarnishSmall = mkPoster(m.recG, '', rl.garnishSmall.x, rl.garnishSmall.y, rl.garnishSmall.s, rl.garnishSmall.s);
  mkLabel(m.recG, 'Ingredients', 'script', rl.ingHeader.size, cc.ink, rl.ingHeader.x, rl.ingHeader.y, rl.ingHeader.w, 'left', 0);
  mkLabel(m.recG, 'Directions', 'script', rl.dirHeader.size, cc.gold, rl.dirHeader.x, rl.dirHeader.y, rl.dirHeader.w, 'left', 0);
  m.rStepCount = mkLabel(m.recG, '', 'serif', 26, cc.goldLight, rl.steps.x + rl.steps.w - 420, rl.dirHeader.y + 28, 400, 'right', 0);
  m.rServingsConfirm = mkGroup(m.recG, rl.steps.x + rl.steps.w - 420, rl.dirHeader.y + 28);
  webHit(m.rServingsConfirm, 400, 35, function () { pressKey('OK'); });

  m.rHi = mkRect(m.recG, '0xB8862E33', 0, 0, 10, 10);
  m.rFocus = mkPoster(m.recG, 'images/ui/focus.9.png', 0, 0, 10, 10);
  var nv = rl.nutrition;
  m.rNutrition = mkGroup(m.recG, nv.x, nv.y);
  mkPoster(m.rNutrition, 'images/ui/parchment.9.png', 0, 0, nv.w, nv.h);
  mkLabel(m.rNutrition, 'Nutrition', 'serifBold', nv.size, cc.ink, 0, 6, nv.w, 'center', 0);
  webHit(m.rNutrition, nv.w, nv.h, function () {
    if (m.rs.zone !== 'servingsEdit') menuShowNutrition();
  });
  var sv = rl.servings;
  var spinner = mkGroup(m.recG, sv.x, sv.y);
  spinner.width = sv.w;
  spinner.height = sv.h;
  mkRect(spinner, '0x9B714CFF', 0, 0, sv.w, sv.h);
  mkRect(spinner, '0xF3DFC0FF', 2, 2, sv.w - 4, sv.h - 4);
  m.serveCounts = Object.create(null);
  m.rServingsInput = document.createElement('input');
  m.rServingsInput.className = 'servings-input';
  m.rServingsInput.type = 'number';
  m.rServingsInput.min = '1';
  m.rServingsInput.max = String(m.D.maxServings);
  m.rServingsInput.style.fontSize = sv.size + 'px';
  m.rServingsInput.setAttribute('aria-label', 'Servings');
  m.rServingsInput.readOnly = true;
  if (m.nativeFireTv) m.rServingsInput.tabIndex = -1;
  m.rServingsInput.addEventListener('focus', recipeFocusServings);
  m.rServingsInput.addEventListener('click', function () {
    if (m.rs.zone === 'servingsEdit') return;
    recipeFocusServings();
    pressKey('OK');
    if (!m.nativeFireTv) m.rServingsInput.select();
  });
  spinner.el.appendChild(m.rServingsInput);
  [1, -1].forEach(function (delta) {
    var up = delta > 0;
    var button = document.createElement('button');
    button.className = 'servings-arrow ' + (up ? 'servings-up' : 'servings-down');
    button.setAttribute('aria-label', up ? 'Increase servings' : 'Decrease servings');
    if (m.nativeFireTv) button.tabIndex = -1;
    button.addEventListener('click', function (e) {
      if (m.rs.zone !== 'servingsEdit') return;
      recipeAdjustServings(delta);
      if (e && e.detail) button.blur();
    });
    spinner.el.appendChild(button);
    if (up) m.rServingsUp = button; else m.rServingsDown = button;
  });
  m.rIngG = mkGroup(m.recG, rl.ingList.x, rl.ingList.y);
  m.rStepG = mkGroup(m.recG, rl.steps.x, rl.steps.y);
  var il = rl.ingList, st = rl.steps;
  m.rIngUp = mkPoster(m.recG, 'images/ui/chev_up_ink.png', il.x + il.w - 30, il.y + 2, 30, 20);
  m.rIngDown = mkPoster(m.recG, 'images/ui/chev_down_ink.png', il.x + il.w - 30, il.y + il.h - 20, 30, 20);
  m.rStepUp = mkPoster(m.recG, 'images/ui/chev_up.png', st.x + st.w - 30, st.y + 2, 30, 20);
  var ft = rl.stepFooter;
  var footer = mkGroup(m.recG, st.x, ft.y);
  mkRect(footer, '0x140D09DD', 0, 0, st.w, ft.h);
  mkRect(footer, '0xB8862E80', 0, 0, st.w, 2);
  m.rStepRange = mkLabel(footer, '', 'serif', ft.size, cc.goldLight, 16, 4, st.w - ft.actionW - 30, 'left', 0);
  m.rStepMore = mkGroup(footer, st.w - ft.actionW, 0);
  mkRect(m.rStepMore, '0xB8862E4D', 0, 2, ft.actionW, ft.h - 2);
  m.rStepMoreArrow = mkPoster(m.rStepMore, '', 18, 11, 31, 22);
  m.rStepMoreLabel = mkLabel(m.rStepMore, '', 'serifBold', ft.size, cc.goldLight, 62, 4, ft.actionW - 76, 'left', 0);
  webHit(m.rStepMore, ft.actionW, ft.h, function () {
    if (m.rs.zone !== 'servingsEdit') recipeFocusStep(m.rNextHiddenStep);
  });
  m.rStepG.width = st.w;
  m.rStepG.height = st.h;
  m.rStepG.el.addEventListener('wheel', function (event) {
    if (m.menuOpen || !event.deltaY) return;
    event.preventDefault();
    event.stopPropagation();
    if (m.rs.zone === 'servingsEdit') return;
    m.rs.zone = 'steps';
    pressKey(event.deltaY > 0 ? 'down' : 'up');
  }, { passive: false });
  m.rs = { rpos: 0, zone: 'steps', ing: 0, ingTop: 0, sIdx: 0, stepTop: 0 };
}

function recipeOpen(rpos) {
  showScreen('recipe');
  recipeShow(rpos);
}

function recipeShow(rpos, previous) {
  var rl = m.L.recipe, cc = m.L.colors, r = recipeAt(rpos);
  m.rec = r;
  m.rs = { rpos: rpos, zone: 'steps', ing: 0, ingTop: 0, sIdx: 0, stepTop: 0 };
  m.rServes = m.serveCounts[r.id] || r.serves;
  m.servingVariant = r.servingVariants[m.rServes - 1];
  m.rNutrition.visible = Boolean(m.servingVariant.nutritionText);
  m.rDish.uri = 'pkg:/' + r.image;
  m.rCookware.visible = Boolean(r.cookwareText);
  m.rCookwareLabel.text = r.cookwareText ? 'Cookware · ' + r.cookwareText : '';
  var size = rl.title.size;
  if (r.title.length > rl.title.longAt) size = rl.title.sizeLong;
  m.rTitle.font = uiFont('script', size);
  m.rTitle.text = r.title;
  m.rDesc.text = r.description;
  m.rMeta[0].text = m.servingVariant.prepText;
  m.rMeta[1].text = m.servingVariant.cookText;
  m.rMeta[3].text = r.difficulty;
  m.rGarnish.uri = 'pkg:/' + r.garnish;
  m.rGarnishSmall.uri = 'pkg:/' + r.garnish;

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
      var ingredient = recipeScaledText('ingredients', i, it.text);
      lb = mkLabel(g, ingredient, 'serif', il.size, cc.ink, il.textX, 0, tw, 'left', 3);
      h = textHeight(lb, il.size, ingredient.length, tw);
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
    var step = recipeStepText(i);
    lb = mkRich(g, '<b>' + s.lead + '</b> ' + step, st.size, '0xF0E2C4FF', cc.goldLight, st.textX, 2, sw);
    h = textHeight(lb, st.size, s.lead.length + step.length + 1, sw) + 4;
    if (h < st.ring) h = st.ring;
    webHit(g, st.w - 40, h, recipeClick.bind(null, 'steps', i));
    m.stepNodes.push(g);
    m.stepH.push(h);
  }
  if (previous) m.rs = previous;
  recipeLayout();
}

function recipeScaledText(section, index, fallback) {
  return m.servingVariant[section][index] || fallback;
}

function recipeStepTiming(index) {
  return m.servingVariant.timers[index] || m.rec.steps[index];
}

function recipeStepText(index) {
  return recipeScaledText('steps', index, m.rec.steps[index].text);
}

function recipeFocusServings() {
  if (m.rs.zone === 'servings' || m.rs.zone === 'servingsEdit') return;
  m.rs.returnZone = m.rs.zone;
  m.rs.zone = 'servings';
  recipeLayout();
}

function recipePendingServings() {
  var field = m.rServingsInput;
  return field.value !== '' && Number.isFinite(Number(field.value)) ? Math.round(Number(field.value)) : m.rs.draftServes;
}

function recipeAdjustServings(delta) {
  m.rs.draftServes = Math.min(m.D.maxServings, Math.max(1, recipePendingServings() + delta));
  recipeLayout();
}

function recipeSetServings(count) {
  if (Number.isFinite(count)) count = Math.min(m.D.maxServings, Math.max(1, Math.round(count)));
  else count = m.rServes;
  if (count === m.rServes) {
    recipeLayout();
    return;
  }
  m.serveCounts[m.rec.id] = count;
  recipeShow(m.rs.rpos, m.rs);
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
  var editing = rs.zone === 'servingsEdit';
  var shownServes = editing ? rs.draftServes : m.rServes;
  m.rServingsInput.readOnly = !editing || m.nativeFireTv;
  m.rServingsInput.value = String(shownServes);
  m.rServingsUp.disabled = !editing || shownServes >= m.D.maxServings;
  m.rServingsDown.disabled = !editing || shownServes <= 1;
  m.rServingsConfirm.visible = editing;
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
  var n = m.stepNodes.length, node, x, y, w, h;
  var moreBelow = lastS < n - 1;
  m.rNextHiddenStep = moreBelow ? lastS + 1 : rs.stepTop - 1;
  m.rStepMore.visible = m.rNextHiddenStep >= 0;
  m.rStepMoreLabel.text = moreBelow ? 'Scroll down for more' : 'Scroll up for earlier steps';
  m.rStepMoreArrow.uri = moreBelow ? 'images/ui/chev_down.png' : 'images/ui/chev_up.png';
  var range = String(rs.stepTop + 1);
  if (lastS > rs.stepTop) range += '–' + (lastS + 1);
  m.rStepRange.text = 'Showing ' + range + ' of ' + n + ' steps';
  if (rs.zone === 'ing') {
    node = m.ingNodes[rs.ing];
    x = il.x - 12;
    y = il.y + node.translation[1] - 6;
    w = il.w - 22;
    h = m.ingH[rs.ing] + 12;
    m.rHi.color = '0xB8862E38';
    m.rStepCount.text = 'Right to select directions';
  } else if (rs.zone === 'servings' || editing) {
    var sv = rl.servings;
    x = sv.x - 3;
    y = sv.y - 3;
    w = sv.w + 6;
    h = sv.h + 6;
    m.rHi.color = '0xB8862E38';
    m.rStepCount.text = editing ? 'Up / Down · OK to confirm' : 'OK to edit servings';
  } else if (rs.zone === 'nutrition') {
    var nv = rl.nutrition;
    x = nv.x;
    y = nv.y;
    w = nv.w;
    h = nv.h;
    m.rHi.color = '0xB8862E38';
    m.rStepCount.text = 'OK to view nutrition';
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
  var rs = m.rs, ings = m.rec.ingredients, i;
  if (rs.zone === 'servingsEdit') {
    if (key === 'up' || key === 'down') {
      recipeAdjustServings(key === 'up' ? 1 : -1);
    } else if (key === 'OK' || key === 'back') {
      var count = key === 'OK' ? recipePendingServings() : m.rServes;
      rs.zone = key === 'OK' ? rs.returnZone : 'servings';
      if (document.activeElement === m.rServingsInput) m.rServingsInput.blur();
      recipeSetServings(count);
    }
    return true;
  }
  if (rs.zone === 'nutrition') {
    if (key === 'OK') {
      menuShowNutrition();
      return true;
    }
    if (key === 'up' || key === 'down' || key === 'left' || key === 'right') {
      rs.zone = 'ing';
      recipeLayout();
      return true;
    }
  }
  if (rs.zone === 'servings' && (key === 'up' || key === 'down')) {
    if (key === 'down') rs.zone = rs.returnZone;
    recipeLayout();
    return true;
  }
  if (key === 'up') {
    if (rs.zone === 'ing') {
      i = rs.ing - 1;
      while (i >= 0 && ings[i].header) i = i - 1;
      if (i >= 0) rs.ing = i;
      else recipeFocusServings();
    } else if (rs.sIdx > 0) {
      rs.sIdx = rs.sIdx - 1;
    } else recipeFocusServings();
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
    rs.zone = rs.zone === 'ing' && m.rNutrition.visible ? 'nutrition' : 'ing';
  } else if (key === 'OK') {
    if (rs.zone === 'servings') {
      rs.draftServes = m.rServes;
      rs.zone = 'servingsEdit';
    } else if (rs.zone === 'ing') {
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
    recipeShow(homeAdjacentRecipe(rs.rpos, -1));
    return true;
  } else if (key === 'fastforward') {
    recipeShow(homeAdjacentRecipe(rs.rpos, 1));
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
  if (rs.zone === 'servingsEdit') return;
  if (rs.zone === zone && (zone === 'ing' ? rs.ing : rs.sIdx) === i) { pressKey('OK'); return; }
  rs.zone = zone;
  if (zone === 'ing') rs.ing = i; else rs.sIdx = i;
  recipeLayout();
}
