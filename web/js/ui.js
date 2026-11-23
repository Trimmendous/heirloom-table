/* ui.js: a tiny SceneGraph look-alike (Group, Poster, Label, MultiStyleLabel, Rectangle, Timer)
 * rendered as absolutely positioned DOM on a 1920x1080 stage, plus the helpers from roku/components/Ui.brs.
 * Screen files (home.js, recipe.js, cook.js, menu.js) mirror their .brs twins function-for-function. */
'use strict';

var m = {};            // BrightScript's component-scoped `m`
var NINE = { focus: 24, parchment: 30 };   // 9-patch corner sizes (tools/make_art.py ninepatch())
var FONT_FAMILY = { script: 'HT Script', serif: 'HT Serif', serifBold: 'HT SerifBold', hand: 'HT Hand' };

function cssColor(c) {           // "0xRRGGBBAA" -> rgba()
  var v = String(c).replace(/^0x|^#/, '');
  var a = v.length >= 8 ? parseInt(v.slice(6, 8), 16) / 255 : 1;
  return 'rgba(' + parseInt(v.slice(0, 2), 16) + ',' + parseInt(v.slice(2, 4), 16) + ',' + parseInt(v.slice(4, 6), 16) + ',' + a.toFixed(3) + ')';
}
function assetUrl(uri) { return uri ? 'assets/' + String(uri).replace(/^pkg:\//, '') : ''; }

function SGNode(type, parent) {
  this.type = type;
  this.kids = [];
  this.el = document.createElement('div');
  this.el.className = 'sg sg-' + type;
  this._tr = [0, 0];
  this._vis = true;
  if (parent) { parent.el.appendChild(this.el); parent.kids.push(this); }
}
SGNode.prototype = {
  get translation() { return this._tr; },
  set translation(t) { this._tr = [t[0], t[1]]; this.el.style.left = t[0] + 'px'; this.el.style.top = t[1] + 'px'; },
  get visible() { return this._vis; },
  set visible(v) { this._vis = !!v; this.el.style.display = v ? '' : 'none'; },
  set width(w) { this._w = w; this.el.style.width = w + 'px'; this.restyle && this.restyle(); },
  get width() { return this._w || 0; },
  set height(h) { this._h = h; this.el.style.height = h + 'px'; this.restyle && this.restyle(); },
  get height() { return this._h || 0; },
  setFields: function (o) { for (var k in o) this[k] = o[k]; },
  createChild: function (type) { return new TYPES[type](type, this); },
  getChildCount: function () { return this.kids.length; },
  removeChildrenIndex: function (n, i) { this.kids.splice(i, n).forEach(function (k) { k.el.remove(); }); },
  boundingRect: function () { return { x: this._tr[0], y: this._tr[1], width: this.el.offsetWidth, height: this.el.offsetHeight }; },
  findNode: function (id) { return this.ids ? this.ids[id] : null; }
};

function Group(t, p) { SGNode.call(this, t, p); }
Group.prototype = Object.create(SGNode.prototype);

function Rectangle(t, p) { SGNode.call(this, t, p); }
Rectangle.prototype = Object.create(SGNode.prototype);
Object.defineProperty(Rectangle.prototype, 'color', { set: function (c) { this.el.style.background = cssColor(c); } });

function Poster(t, p) { SGNode.call(this, t, p); this.loadDisplayMode = 'scaleToFit'; }
Poster.prototype = Object.create(SGNode.prototype);
Object.defineProperty(Poster.prototype, 'uri', {
  get: function () { return this._uri || ''; },
  set: function (u) {
    this._uri = u;
    var s = this.el.style, m9 = /images\/ui\/(\w+)\.9\.png$/.exec(u || '');
    if (m9) {      // 9-patch: same art without the marker border, drawn with CSS border-image
      var c = NINE[m9[1]];
      s.backgroundImage = 'none';
      s.borderStyle = 'solid';
      s.borderWidth = c + 'px';
      s.boxSizing = 'border-box';
      s.borderImage = 'url("assets/images/web/' + m9[1] + '.png") ' + c + ' fill / ' + c + 'px stretch';
    } else {
      s.borderImage = 'none'; s.borderWidth = '0';
      s.backgroundImage = u ? 'url("' + assetUrl(u) + '")' : 'none';
    }
  }
});
Object.defineProperty(Poster.prototype, 'loadDisplayMode', {
  set: function (v) { this.el.style.backgroundSize = v === 'scaleToZoom' ? 'cover' : v === 'scaleToFill' ? '100% 100%' : 'contain'; }
});
['loadWidth', 'loadHeight', 'opacity'].forEach(function (f) {
  Object.defineProperty(Poster.prototype, f, { set: function (v) { if (f === 'opacity') this.el.style.opacity = v; } });
});

function Label(t, p) {
  SGNode.call(this, t, p);
  this._align = 'left'; this._valign = 'top'; this._wrap = false; this._max = 0;
  this.restyle();
}
Label.prototype = Object.create(SGNode.prototype);
Label.prototype.restyle = function () {
  var s = this.el.style;
  s.textAlign = this._align;
  if (this._wrap) {
    s.whiteSpace = 'normal';
    s.display = this._vis ? '-webkit-box' : 'none';
    s.webkitBoxOrient = 'vertical';
    s.webkitLineClamp = this._max ? String(this._max) : 'none';
    s.overflow = 'hidden';
    s.lineHeight = '';
  } else {
    s.whiteSpace = 'nowrap';
    s.overflow = this._w ? 'hidden' : 'visible';
    s.textOverflow = 'ellipsis';
    s.lineHeight = (this._h && this._valign === 'center') ? this._h + 'px' : '';
  }
};
Object.defineProperty(Label.prototype, 'visible', {
  get: function () { return this._vis; },
  set: function (v) { this._vis = !!v; this.el.style.display = v ? (this._wrap ? '-webkit-box' : '') : 'none'; }
});
Object.defineProperty(Label.prototype, 'text', {
  get: function () { return this.el.textContent; }, set: function (v) { this.el.textContent = v; }
});
Object.defineProperty(Label.prototype, 'font', {
  set: function (f) { this.el.style.fontFamily = '"' + FONT_FAMILY[f.kind] + '"'; this.el.style.fontSize = f.size + 'px'; }
});
Object.defineProperty(Label.prototype, 'color', { set: function (c) { this.el.style.color = cssColor(c); } });
Object.defineProperty(Label.prototype, 'horizAlign', { set: function (a) { this._align = a; this.restyle(); } });
Object.defineProperty(Label.prototype, 'vertAlign', { set: function (a) { this._valign = a; this.restyle(); } });
Object.defineProperty(Label.prototype, 'wrap', { set: function (w) { this._wrap = !!w; this.restyle(); } });
Object.defineProperty(Label.prototype, 'maxLines', { set: function (n) { this._max = n; this.restyle(); } });

function MultiStyleLabel(t, p) { Label.call(this, t, p); this._styles = {}; }
MultiStyleLabel.prototype = Object.create(Label.prototype);
Object.defineProperty(MultiStyleLabel.prototype, 'drawingStyles', {
  set: function (ds) {
    this._styles = ds;
    var d = ds['default'];
    this.el.style.fontFamily = '"' + FONT_FAMILY[fontKindFromUri(d.fontUri)] + '"';
    this.el.style.fontSize = d.fontSize + 'px';
    this.el.style.color = cssColor(d.color);
  }
});
Object.defineProperty(MultiStyleLabel.prototype, 'text', {
  get: function () { return this.el.textContent; },
  set: function (v) {       // "<b>Lead.</b> rest" -> styled spans; everything else is escaped
    var b = this._styles.b, out = '';
    String(v).split(/(<b>|<\/b>)/).reduce(function (bold, part) {
      if (part === '<b>') return true;
      if (part === '</b>') return false;
      var esc = part.replace(/&/g, '&amp;').replace(/</g, '&lt;');
      out += bold && b ? '<span style="font-family:\'' + FONT_FAMILY[fontKindFromUri(b.fontUri)] + '\';color:' + cssColor(b.color) + '">' + esc + '</span>' : esc;
      return bold;
    }, false);
    this.el.innerHTML = out;
  }
});
function fontKindFromUri(u) {
  for (var k in m.L.fonts) if (u.indexOf(m.L.fonts[k]) >= 0) return k;
  return 'serif';
}

function Timer(t, p) { SGNode.call(this, t, null); this.duration = 1; this.repeat = false; this._obs = {}; }
Timer.prototype = Object.create(SGNode.prototype);
Timer.prototype.observeField = function (f, fn) { this._obs[f] = fn; };
Object.defineProperty(Timer.prototype, 'control', {
  set: function (c) {
    var self = this;
    var fire = function () { var fn = self._obs.fire; if (fn) window[fn](); };
    clearTimeout(this._t);
    clearInterval(this._i);
    if (c === 'start' && this.repeat) this._i = setInterval(fire, this.duration * 1000);
    else if (c === 'start') this._t = setTimeout(fire, this.duration * 1000);
  }
});

var TYPES = { Group: Group, Rectangle: Rectangle, Poster: Poster, Label: Label, MultiStyleLabel: MultiStyleLabel, Timer: Timer };

/* ---------------------------------------------------------------- Ui.brs mirror */
function uiInit() {
  m.L = window.HEIRLOOM.layout;
  m.D = window.HEIRLOOM.data;
  m.fonts = {};
}

function uiFont(kind, size) {
  var key = kind + size;
  if (!m.fonts[key]) m.fonts[key] = { kind: kind, size: size };
  return m.fonts[key];
}

function mkGroup(parent, x, y) {
  var g = parent.createChild('Group');
  g.translation = [x, y];
  return g;
}

function mkPoster(parent, uri, x, y, w, h) {
  var p = parent.createChild('Poster');
  p.setFields({ translation: [x, y], width: w, height: h, loadDisplayMode: 'scaleToFit' });
  if (uri !== '') p.uri = 'pkg:/' + uri;
  return p;
}

function mkThumb(parent, uri, x, y, w, h) {
  var p = parent.createChild('Poster');
  p.setFields({ translation: [x, y], width: w, height: h, loadWidth: w, loadHeight: h, loadDisplayMode: 'scaleToZoom' });
  p.uri = 'pkg:/' + uri;
  return p;
}

function mkRect(parent, color, x, y, w, h) {
  var r = parent.createChild('Rectangle');
  r.setFields({ translation: [x, y], width: w, height: h, color: color });
  return r;
}

function mkLabel(parent, text, kind, size, color, x, y, w, align, maxLines) {
  var lb = parent.createChild('Label');
  lb.setFields({ translation: [x, y], text: text, font: uiFont(kind, size), color: color, horizAlign: align });
  if (w > 0) lb.width = w;
  if (maxLines > 0) {
    lb.wrap = true;
    lb.maxLines = maxLines;
  }
  return lb;
}

function mkRich(parent, text, size, color, boldColor, x, y, w) {
  var lb = parent.createChild('MultiStyleLabel');
  // drawingStyles take "#RRGGBBAA" colours
  lb.drawingStyles = {
    b: { fontUri: 'pkg:/fonts/' + m.L.fonts.serifBold, fontSize: size, color: '#' + boldColor.slice(2) },
    'default': { fontUri: 'pkg:/fonts/' + m.L.fonts.serif, fontSize: size, color: '#' + color.slice(2) }
  };
  lb.setFields({ translation: [x, y], width: w, wrap: true, text: text });
  return lb;
}

function textHeight(lb, size, chars, w) {
  var h = lb.boundingRect().height;
  if (h < size) {
    var perLine = Math.floor(w / (size * 0.48));
    if (perLine < 1) perLine = 1;
    var lines = Math.floor((chars + perLine - 1) / perLine);
    if (lines < 1) lines = 1;
    h = lines * size * 1.22;
  }
  return h;
}

function fitTop(heights, gap, area, top, focus) {
  if (focus < top) top = focus;
  while (top < focus) {
    var y = 0;
    for (var i = top; i <= focus; i++) {
      y = y + heights[i];
      if (i > top) y = y + gap;
    }
    if (y <= area) break;
    top = top + 1;
  }
  return top;
}

function placeItems(nodes, heights, gap, area, top) {
  var y = 0, last = top - 1;
  for (var i = 0; i < nodes.length; i++) {
    var n = nodes[i];
    if (i < top) {
      n.visible = false;
    } else if (y + heights[i] <= area || i === top) {
      n.visible = true;
      n.translation = [0, y];
      y = y + heights[i] + gap;
      last = i;
    } else {
      n.visible = false;
      y = area + 1;
    }
  }
  return last;
}

function removeKids(g) { g.removeChildrenIndex(g.getChildCount(), 0); }

function recipeAt(rpos) { return m.D.recipes[rpos]; }

function loadChecks() {
  try {
    var v = JSON.parse(localStorage.getItem('heirloom.checks') || 'null');
    if (v) return v;
  } catch (e) { /* storage unavailable (file:// in some browsers): keep in memory */ }
  return {};
}

function saveChecks() {
  try { localStorage.setItem('heirloom.checks', JSON.stringify(m.checks)); } catch (e) { /* ignore */ }
}

function isChecked(rid, idx) {
  var c = m.checks[rid];
  if (!c) return false;
  return c[String(idx)] !== undefined;
}

function setChecked(rid, idx, isOn) {
  if (!m.checks[rid]) m.checks[rid] = {};
  if (isOn) m.checks[rid][String(idx)] = true;
  else delete m.checks[rid][String(idx)];
  saveChecks();
}

function showToast(text) {
  m.toastLabel.text = text;
  m.toast.visible = true;
  m.toastTimer.control = 'stop';
  m.toastTimer.control = 'start';
}

/* Milliseconds clock for timers (end time is stored, so a late tick never drifts). */
function nowMs() { return Date.now(); }

function onToastTimer() { m.toast.visible = false; }
