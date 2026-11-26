' Home.brs: title + rows of recipe cards ("Every Recipe" first, then one row per category).
' Mirrors web/js/home.js.

sub homeBuild()
    hl = m.L.home
    cc = m.L.colors
    m.homeG = mkGroup(m.root, 0, 0)
    m.homeG.visible = false
    m.homeBg = mkPoster(m.homeG, hl.bg, 0, 0, 1920, 1080)
    mkLabel(m.homeG, "The Heirloom Table", "script", hl.title.size, cc.gold, hl.title.x, hl.title.y, hl.title.w, "center", 0)
    mkLabel(m.homeG, "A COLLECTION OF FAMILY RECIPES, KITCHEN FAVORITES, AND NEW TRADITIONS.", "serif", hl.tagline.size, cc.goldLight, hl.tagline.x, hl.tagline.y, hl.tagline.w, "center", 0)
    v = hl.version
    mkLabel(m.homeG, "v" + m.D.app.version + "  ·  * Options", "serif", v.size, cc.goldLight, v.x, v.y, v.w, "right", 0)
    m.homeRows = mkGroup(m.homeG, hl.rows.x, hl.rows.y)
    ' Clip the rows at the right title-safe edge, so the card after the last visible one peeks in under a fade.
    m.homeClipR = m.L.screen.safe[2] - hl.rows.x
    m.homeRows.clippingRect = [-48, -60, m.homeClipR + 48, hl.rows.h + 100]
    m.homeUp = mkPoster(m.homeG, "images/ui/chev_up.png", 1770, hl.rows.y + 18, 30, 20)
    m.homeDown = mkPoster(m.homeG, "images/ui/chev_down.png", 1770, hl.rows.y + hl.rows.h - 24, 30, 20)
    m.homeMore = mkLabel(m.homeG, "", "serif", hl.card.metaSize, cc.goldLight, 1424, hl.rows.y + 14, 330, "right", 0)

    m.rows = [{ title: "Every Recipe", items: [] }]
    for i = 0 to m.D.recipes.Count() - 1
        m.rows[0].items.Push(i)
    end for
    for each c in m.D.categories
        row = { title: c, items: [] }
        for i = 0 to m.D.recipes.Count() - 1
            if m.D.recipes[i].category = c then row.items.Push(i)
        end for
        m.rows.Push(row)
    end for
    m.hs = { row: 0, top: 0, cols: [], lefts: [] }
    for each r in m.rows
        m.hs.cols.Push(0)
        m.hs.lefts.Push(0)
    end for
end sub

sub homeRender()
    hl = m.L.home
    cc = m.L.colors
    hs = m.hs
    vis = Int(hl.rows.h / hl.rows.rowH)
    if hs.row < hs.top then hs.top = hs.row
    if hs.row >= hs.top + vis then hs.top = hs.row - vis + 1
    removeKids(m.homeRows)
    cw = hl.card.w
    ch = hl.card.h
    th = hl.card.thumbH
    for r = hs.top to hs.top + vis - 1
        if r >= m.rows.Count() then exit for
        row = m.rows[r]
        y = (r - hs.top) * hl.rows.rowH
        mkLabel(m.homeRows, row.title, "script", hl.rows.labelSize, cc.gold, 0, y - 6, 1100, "left", 0)
        col = hs.cols[r]
        lft = hs.lefts[r]
        if col < lft then lft = col
        if col >= lft + hl.card.visible then lft = col - hl.card.visible + 1
        hs.lefts[r] = lft
        n = row.items.Count()
        ' one card past the visible ones: it peeks in from the right edge (clipped) to show the row goes on
        for c = lft to lft + hl.card.visible
            if c >= n then exit for
            rec = m.D.recipes[row.items[c]]
            g = mkGroup(m.homeRows, (c - lft) * (cw + hl.card.gap), y + hl.rows.labelH)
            if r = hs.row and c = col
                g.scaleRotateCenter = [cw / 2, ch / 2]
                g.scale = [hl.card.focusScale, hl.card.focusScale]
                mkPoster(g, "images/ui/focus.9.png", -22, -22, cw + 44, ch + 44)
            end if
            mkThumb(g, rec.thumb, 0, 0, cw, th)
            mkPoster(g, "images/ui/parchment.9.png", -4, th - 8, cw + 8, ch - th + 12)
            mkLabel(g, rec.title, "serifBold", hl.card.titleSize, cc.ink, 16, th + 4, cw - 32, "left", 2)
            mkLabel(g, rec.cuisine + " · " + rec.totalText, "serif", hl.card.metaSize, cc.inkSoft, 16, th + 74, cw - 32, "left", 0)
        end for
        if lft + hl.card.visible < n
            mkPoster(m.homeRows, hl.peek.fade, hl.card.visible * (cw + hl.card.gap) + hl.peek.fadeX, y + hl.rows.labelH - 8, hl.peek.fadeW, ch + 16)
        end if
        if r = hs.row and n > hl.card.visible
            m.homeMore.translation = [1424, hl.rows.y + y + 14]
            m.homeMore.text = (col + 1).ToStr() + " of " + n.ToStr()
        end if
    end for
    m.homeMore.visible = m.rows[hs.row].items.Count() > hl.card.visible
    m.homeUp.visible = hs.top > 0
    m.homeDown.visible = hs.top + vis < m.rows.Count()
end sub

' Put focus on a recipe's card in the current row (used when returning from a recipe).
sub homeFocusRecipe(rpos as integer)
    items = m.rows[m.hs.row].items
    for c = 0 to items.Count() - 1
        if items[c] = rpos then m.hs.cols[m.hs.row] = c
    end for
end sub

sub homeJump(cat as string)
    for r = 0 to m.rows.Count() - 1
        if m.rows[r].title = cat
            m.hs.row = r
            m.hs.cols[r] = 0
        end if
    end for
    showScreen("home")
end sub

function homeKey(key as string) as boolean
    hs = m.hs
    n = m.rows[hs.row].items.Count()
    if key = "up"
        if hs.row > 0 then hs.row = hs.row - 1
    else if key = "down"
        if hs.row < m.rows.Count() - 1 then hs.row = hs.row + 1
    else if key = "left" or key = "rewind"
        if hs.cols[hs.row] > 0 then hs.cols[hs.row] = hs.cols[hs.row] - 1
    else if key = "right" or key = "fastforward"
        if hs.cols[hs.row] < n - 1 then hs.cols[hs.row] = hs.cols[hs.row] + 1
    else if key = "OK"
        recipeOpen(m.rows[hs.row].items[hs.cols[hs.row]])
        return true
    else if key = "play"
        recipeOpen(m.rows[hs.row].items[hs.cols[hs.row]])
        cookOpen(0)
        return true
    else if key = "back"
        m.top.exitApp = true
        return true
    else
        return false
    end if
    homeRender()
    return true
end function
