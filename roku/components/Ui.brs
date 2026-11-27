' Ui.brs: node helpers shared by every screen. Mirrors web/js/ui.js function-for-function.

sub uiInit()
    m.L = ParseJson(ReadAsciiFile("pkg:/data/layout.json"))
    m.D = ParseJson(ReadAsciiFile("pkg:/data/recipes.json"))
    m.fonts = {}
end sub

function uiFont(kind as string, size as integer) as object
    key = kind + size.ToStr()
    f = m.fonts[key]
    if f = invalid
        f = CreateObject("roSGNode", "Font")
        f.uri = "pkg:/fonts/" + m.L.fonts[kind]
        f.size = size
        m.fonts[key] = f
    end if
    return f
end function

function mkGroup(parent as object, x as float, y as float) as object
    g = parent.createChild("Group")
    g.translation = [x, y]
    return g
end function

function mkPoster(parent as object, uri as string, x as float, y as float, w as float, h as float) as object
    p = parent.createChild("Poster")
    p.setFields({ translation: [x, y], width: w, height: h, loadDisplayMode: "scaleToFit" })
    if uri <> "" then p.uri = "pkg:/" + uri
    return p
end function

' Dish thumbnails: decode at display size (saves texture memory) and crop to fill.
function mkThumb(parent as object, uri as string, x as float, y as float, w as float, h as float) as object
    p = parent.createChild("Poster")
    p.setFields({ translation: [x, y], width: w, height: h, loadWidth: w, loadHeight: h, loadDisplayMode: "scaleToZoom" })
    p.uri = "pkg:/" + uri
    return p
end function

function mkRect(parent as object, color as string, x as float, y as float, w as float, h as float) as object
    r = parent.createChild("Rectangle")
    r.setFields({ translation: [x, y], width: w, height: h, color: color })
    return r
end function

' align: "left" | "center" | "right". w = 0 means natural width. maxLines = 0 means single line (no wrap).
function mkLabel(parent as object, text as string, kind as string, size as integer, color as string, x as float, y as float, w as float, align as string, maxLines as integer) as object
    lb = parent.createChild("Label")
    lb.setFields({ translation: [x, y], text: text, font: uiFont(kind, size), color: color, horizAlign: align })
    if w > 0 then lb.width = w
    if maxLines > 0
        lb.wrap = true
        lb.maxLines = maxLines
    end if
    return lb
end function

' Rich text: "<b>Lead.</b> rest". Bold runs use the bold serif, the rest the regular serif.
function mkRich(parent as object, text as string, size as integer, color as string, boldColor as string, x as float, y as float, w as float) as object
    lb = parent.createChild("MultiStyleLabel")
    ' drawingStyles take "#RRGGBBAA" colours
    lb.drawingStyles = {
        "b": { "fontUri": "pkg:/fonts/" + m.L.fonts.serifBold, "fontSize": size, "color": "#" + Mid(boldColor, 3) }
        "default": { "fontUri": "pkg:/fonts/" + m.L.fonts.serif, "fontSize": size, "color": "#" + Mid(color, 3) }
    }
    lb.setFields({ translation: [x, y], width: w, wrap: true, text: text })
    return lb
end function

' Height of a wrapped label. Falls back to an estimate if the renderer has not measured it yet.
function textHeight(lb as object, size as integer, chars as integer, w as float) as float
    h = lb.boundingRect().height
    if h < size
        perLine = Int(w / (size * 0.48))
        if perLine < 1 then perLine = 1
        lines = Int((chars + perLine - 1) / perLine)
        if lines < 1 then lines = 1
        h = lines * size * 1.22
    end if
    return h
end function

' First index >= top so that items top..focus fit in `area` pixels (shared list-window rule).
function fitTop(heights as object, gap as float, area as float, top as integer, focus as integer) as integer
    if focus < top then top = focus
    while top < focus
        y = 0
        for i = top to focus
            y = y + heights[i]
            if i > top then y = y + gap
        end for
        if y <= area then exit while
        top = top + 1
    end while
    return top
end function

' Position items from `top`; hide what does not fit. Returns the index of the last visible item.
function placeItems(nodes as object, heights as object, gap as float, area as float, top as integer) as integer
    y = 0
    last = top - 1
    for i = 0 to nodes.Count() - 1
        n = nodes[i]
        if i < top
            n.visible = false
        else if y + heights[i] <= area or i = top
            n.visible = true
            n.translation = [0, y]
            y = y + heights[i] + gap
            last = i
        else
            n.visible = false
            y = area + 1
        end if
    end for
    return last
end function

sub removeKids(g as object)
    g.removeChildrenIndex(g.getChildCount(), 0)
end sub

function recipeAt(rpos as integer) as object
    return m.D.recipes[rpos]
end function

function loadChecks() as object
    sec = CreateObject("roRegistrySection", "heirloom")
    if sec.Exists("checks")
        v = ParseJson(sec.Read("checks"))
        if v <> invalid then return v
    end if
    return {}
end function

sub saveChecks()
    sec = CreateObject("roRegistrySection", "heirloom")
    sec.Write("checks", FormatJson(m.checks))
    sec.Flush()
end sub

function isChecked(rid as string, idx as integer) as boolean
    c = m.checks[rid]
    if c = invalid then return false
    return c[idx.ToStr()] <> invalid
end function

sub setChecked(rid as string, idx as integer, isOn as boolean)
    if m.checks[rid] = invalid then m.checks[rid] = {}
    if isOn
        m.checks[rid][idx.ToStr()] = true
    else
        m.checks[rid].Delete(idx.ToStr())
    end if
    saveChecks()
end sub

sub showToast(text as string)
    m.toastLabel.text = text
    m.toast.visible = true
    m.toastTimer.control = "stop"
    m.toastTimer.control = "start"
end sub

' Milliseconds since the channel started, for timers (end time is stored, so a late tick never drifts).
function nowMs() as integer
    if m.clock = invalid then m.clock = CreateObject("roTimespan")
    return m.clock.TotalMilliseconds()
end function

sub onToastTimer()
    m.toast.visible = false
end sub

function loadTheme() as string
    sec = CreateObject("roRegistrySection", "heirloom")
    if sec.Read("theme") = "midnight" then return "midnight"
    return "classic"
end function

sub applyTheme(themeName as string)
    m.themeName = themeName
    bgKey = "bg"
    if themeName = "midnight" then bgKey = "nightBg"
    m.homeBg.uri = "pkg:/" + m.L.home[bgKey]
    m.recipeBg.uri = "pkg:/" + m.L.recipe[bgKey]
    m.cookBg.uri = "pkg:/" + m.L.cook[bgKey]
end sub

sub saveTheme(themeName as string)
    sec = CreateObject("roRegistrySection", "heirloom")
    sec.Write("theme", themeName)
    sec.Flush()
end sub

function loadIngredientExclusions() as object
    sec = CreateObject("roRegistrySection", "heirloom")
    avoid = {}
    if not sec.Exists("ingredientExclusions") then return avoid
    saved = ParseJson(sec.Read("ingredientExclusions"))
    if Type(saved) <> "roAssociativeArray" then return avoid
    for each name in m.D.ingredientFilters
        if saved.DoesExist(name) then avoid[name] = true
    end for
    return avoid
end function

sub saveIngredientExclusions(avoid as object)
    sec = CreateObject("roRegistrySection", "heirloom")
    sec.Write("ingredientExclusions", FormatJson(avoid))
    sec.Flush()
end sub
