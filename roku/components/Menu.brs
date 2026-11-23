' Menu.brs: the Options (*) overlay: reset checkboxes, browse all recipes, jump to a category.
' Levels stack, so "Browse all recipes" opens a list and Back returns to the options. Mirrors web/js/menu.js.

sub menuBuild()
    ml = m.L.menu
    cc = m.L.colors
    m.menuG = mkGroup(m.root, 0, 0)
    m.menuG.visible = false
    mkRect(m.menuG, cc.dim, 0, 0, 1920, 1080)
    mkPoster(m.menuG, "images/ui/parchment.9.png", ml.panel.x, ml.panel.y, ml.panel.w, ml.panel.h)
    m.mTitle = mkLabel(m.menuG, "", "script", ml.title.size, cc.ink, ml.title.x, ml.title.y, ml.title.w, "center", 0)
    m.mHi = mkRect(m.menuG, "0xB8862E40", ml.list.x, ml.list.y, ml.list.w, ml.list.itemH)
    m.mFocus = mkPoster(m.menuG, "images/ui/focus.9.png", 0, 0, 10, 10)
    m.mList = mkGroup(m.menuG, ml.list.x, ml.list.y)
    m.mUp = mkPoster(m.menuG, "images/ui/chev_up_ink.png", ml.list.x + ml.list.w / 2 - 15, ml.list.y - 26, 30, 20)
    m.mDown = mkPoster(m.menuG, "images/ui/chev_down_ink.png", ml.list.x + ml.list.w / 2 - 15, ml.list.y + ml.list.visible * ml.list.itemH + 4, 30, 20)
    m.menuOpen = false
    m.mstack = []
end sub

sub menuShow()
    items = []
    if m.screen = "home"
        items.Push({ label: "Reset all checkboxes", act: "resetAll", arg: "" })
    else
        items.Push({ label: "Reset checkboxes", act: "reset", arg: "" })
    end if
    items.Push({ label: "Browse all recipes", act: "list", arg: "" })
    for each c in m.D.categories
        items.Push({ label: "Jump to " + c, act: "cat", arg: c })
    end for
    if m.screen <> "home" then items.Push({ label: "Back to home", act: "home", arg: "" })
    m.mstack = [{ title: "Options", items: items, sel: 0, top: 0 }]
    m.menuOpen = true
    m.menuG.visible = true
    menuRender()
end sub

sub menuClose()
    m.menuOpen = false
    m.menuG.visible = false
end sub

sub menuRender()
    ml = m.L.menu
    cc = m.L.colors
    lv = m.mstack.Peek()
    n = lv.items.Count()
    vis = ml.list.visible
    if lv.sel < lv.top then lv.top = lv.sel
    if lv.sel >= lv.top + vis then lv.top = lv.sel - vis + 1
    m.mTitle.text = lv.title
    removeKids(m.mList)
    for i = lv.top to lv.top + vis - 1
        if i >= n then exit for
        mkLabel(m.mList, lv.items[i].label, "serif", ml.list.size, cc.ink, 24, (i - lv.top) * ml.list.itemH + 10, ml.list.w - 48, "left", 0)
    end for
    y = ml.list.y + (lv.sel - lv.top) * ml.list.itemH
    m.mHi.translation = [ml.list.x, y]
    m.mFocus.setFields({ translation: [ml.list.x - 14, y - 14], width: ml.list.w + 28, height: ml.list.itemH + 28 })
    m.mUp.visible = lv.top > 0
    m.mDown.visible = lv.top + vis < n
end sub

function menuKey(key as string) as boolean
    lv = m.mstack.Peek()
    if key = "up"
        if lv.sel > 0 then lv.sel = lv.sel - 1
    else if key = "down"
        if lv.sel < lv.items.Count() - 1 then lv.sel = lv.sel + 1
    else if key = "rewind"
        lv.sel = lv.sel - m.L.menu.list.visible
        if lv.sel < 0 then lv.sel = 0
    else if key = "fastforward"
        lv.sel = lv.sel + m.L.menu.list.visible
        if lv.sel > lv.items.Count() - 1 then lv.sel = lv.items.Count() - 1
    else if key = "OK"
        menuActivate(lv.items[lv.sel])
        return true
    else if key = "back" or key = "left"
        if m.mstack.Count() > 1
            m.mstack.Pop()
        else
            menuClose()
            return true
        end if
    else if key = "options"
        menuClose()
        return true
    end if
    ' the menu is modal: every other key is swallowed
    menuRender()
    return true
end function

sub menuActivate(it as object)
    if it.act = "reset"
        m.checks.Delete(m.rec.id)
        saveChecks()
        recipeRefreshChecks()
        menuClose()
        showToast("Checkboxes cleared")
    else if it.act = "resetAll"
        m.checks = {}
        saveChecks()
        menuClose()
        showToast("All checkboxes cleared")
    else if it.act = "list"
        items = []
        for i = 0 to m.D.recipes.Count() - 1
            items.Push({ label: m.D.recipes[i].title, act: "open", arg: i })
        end for
        items.SortBy("label")
        m.mstack.Push({ title: "All Recipes", items: items, sel: 0, top: 0 })
        menuRender()
    else if it.act = "open"
        menuClose()
        recipeOpen(it.arg)
    else if it.act = "cat"
        menuClose()
        homeJump(it.arg)
    else if it.act = "home"
        menuClose()
        showScreen("home")
    end if
end sub
