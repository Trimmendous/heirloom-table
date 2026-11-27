' Menu.brs: updates, theme and checklist reset. Mirrors web/js/menu.js.

sub menuBuild()
    ml = m.L.menu
    cc = m.L.colors
    m.menuG = mkGroup(m.root, 0, 0)
    m.menuG.visible = false
    mkRect(m.menuG, cc.dim, 0, 0, 1920, 1080)
    m.mPanel = mkPoster(m.menuG, "images/ui/parchment.9.png", ml.panel.x, ml.panel.y, ml.panel.w, ml.panel.h)
    m.mTitle = mkLabel(m.menuG, "", "script", ml.title.size, cc.ink, ml.title.x, ml.title.y, ml.title.w, "center", 0)
    b = ml.back
    backGroup = mkGroup(m.menuG, b.x, b.y)
    mkRect(backGroup, "0xB8862E26", 0, 0, b.w, b.h)
    m.mBackFocus = mkPoster(backGroup, "images/ui/focus.9.png", -9, -9, b.w + 18, b.h + 18)
    mkLabel(backGroup, "‹ Back", "serifBold", b.size, cc.ink, 0, 5, b.w, "center", 0)
    m.mHi = mkRect(m.menuG, "0xB8862E40", ml.list.x, ml.list.y, ml.list.w, ml.list.itemH)
    m.mFocus = mkPoster(m.menuG, "images/ui/focus.9.png", 0, 0, 10, 10)
    m.mList = mkGroup(m.menuG, ml.list.x, ml.list.y)
    m.mNote = mkLabel(m.menuG, "", "serif", ml.note.size, cc.inkSoft, ml.note.x, 0, ml.note.w, "left", 7)
    m.mNutrition = mkGroup(m.menuG, ml.note.x, ml.list.y)
    m.mUp = mkPoster(m.menuG, "images/ui/chev_up_ink.png", 945, ml.list.y - 25, 30, 20)
    m.mDown = mkPoster(m.menuG, "images/ui/chev_down_ink.png", 945, ml.list.y + ml.filterVisible * ml.list.itemH + 8, 30, 20)
    m.mQR = m.menuG.createChild("QRCode")
    m.mQR.setFields({ translation: [825, 524], width: 270, height: 270, visible: false })
    m.menuOpen = false
    m.mstack = []
end sub

sub menuShow()
    reset = "reset"
    if m.screen = "home" then reset = "resetAll"
    items = [
        { label: "Update Now", act: "updates" },
        { label: "Theme", act: "themes" },
        { label: "Reset Checkboxes", act: reset }
    ]
    menuOpenLevel({ title: "Options", items: items, sel: 0 })
end sub

sub menuShowFilter()
    label = "Ingredients to Avoid"
    excluded = m.homeAvoid.Count()
    if excluded > 0 then label = label + " (" + excluded.ToStr() + ")"
    items = [
        { label: "All Categories", act: "filter", arg: "" },
        { label: label, act: "avoid" }
    ]
    selected = 0
    for each category in m.D.categories
        if category = m.homeCategory then selected = items.Count()
        items.Push({ label: category, act: "filter", arg: category })
    end for
    menuOpenLevel({ title: "Filter Recipes", items: items, sel: selected, top: 0 })
end sub

sub menuShowIngredients()
    items = [{ label: "Clear Exclusions", act: "avoidClear" }]
    for each ingredient in m.D.ingredientFilters
        items.Push({ label: ingredient, act: "avoidToggle", arg: ingredient })
    end for
    m.mstack.Push({ title: "Ingredients to Avoid", items: items, sel: 1, top: 0, ingredientPicker: true,
        note: "Selections apply immediately. For allergies, check package labels and cross-contact." })
    menuRender()
end sub

sub menuShowNutrition()
    menuOpenLevel({ title: "Nutrition Estimate", items: [], sel: -1, nutrition: m.servingVariant.nutritionText })
end sub

sub menuRenderNutrition(content as string)
    ml = m.L.menu
    cc = m.L.colors
    removeKids(m.mNutrition)
    newline = Chr(10)
    sections = content.Split(newline + newline)
    for section = 0 to 1
        lines = sections[section].Split(newline)
        y = section * 162
        mkLabel(m.mNutrition, lines[0], "serifBold", 33, cc.rust, 0, y, ml.note.w, "left", 0)
        for line = 1 to lines.Count() - 1
            mkLabel(m.mNutrition, lines[line], "serif", 29, cc.ink, 0, y + 6 + line * 35, ml.note.w, "left", 0)
        end for
    end for
    mkLabel(m.mNutrition, sections[2], "serif", 25, cc.inkSoft, 0, 334, ml.note.w, "left", 2)
end sub

sub menuOpenLevel(level as object)
    m.mstack = [level]
    m.menuOpen = true
    m.menuG.visible = true
    menuRender()
end sub

sub menuClose()
    m.menuOpen = false
    m.menuG.visible = false
    m.mstack = []
    m.mQR.visible = false
end sub

sub menuRender()
    ml = m.L.menu
    cc = m.L.colors
    lv = m.mstack.Peek()
    n = lv.items.Count()
    firstItem = 0
    endItem = n
    m.mTitle.text = lv.title
    m.mQR.visible = lv.DoesExist("qr")
    if m.mQR.visible then m.mQR.text = lv.qr
    m.mNote.visible = lv.DoesExist("note")
    if m.mNote.visible
        m.mNote.text = lv.note
        m.mPanel.height = ml.note.panelH
    else
        m.mPanel.height = ml.panel.h
    end if
    m.mNutrition.visible = lv.DoesExist("nutrition")
    if m.mNutrition.visible
        m.mPanel.height = ml.nutritionPanelH
        menuRenderNutrition(lv.nutrition)
    end if
    if lv.DoesExist("top")
        shown = n
        limit = ml.filterVisible
        if lv.DoesExist("ingredientPicker") then limit = ml.ingredientVisible
        if shown > limit then shown = limit
        if lv.sel < 0
            lv.top = 0
        else if lv.sel < lv.top
            lv.top = lv.sel
        else if lv.sel >= lv.top + shown
            lv.top = lv.sel - shown + 1
        end if
        firstItem = lv.top
        endItem = firstItem + shown
        bottomSpace = 46
        if m.mNote.visible then bottomSpace = 132
        m.mPanel.height = ml.list.y - ml.panel.y + shown * ml.list.itemH + bottomSpace
        m.mDown.translation = [945, ml.list.y + shown * ml.list.itemH + 8]
    end if
    if m.mNote.visible then m.mNote.translation = [ml.note.x, ml.list.y + (endItem - firstItem) * ml.list.itemH + ml.note.gap]
    m.mUp.visible = firstItem > 0
    m.mDown.visible = endItem < n
    if m.mQR.visible then m.mPanel.height = ml.qrPanelH
    removeKids(m.mList)
    for i = firstItem to endItem - 1
        it = lv.items[i]
        row = mkGroup(m.mList, 0, (i - firstItem) * ml.list.itemH)
        labelX = 24
        if it.act = "avoidToggle"
            uri = "images/ui/check_off.png"
            if m.homeAvoid.DoesExist(it.arg) then uri = "images/ui/check_on.png"
            mkPoster(row, uri, 24, 15, 28, 28)
            labelX = 68
        end if
        mkLabel(row, it.label, "serif", ml.list.size, cc.ink, labelX, 10, ml.list.w - labelX - 24, "left", 0)
    end for
    y = ml.list.y + (lv.sel - firstItem) * ml.list.itemH
    m.mBackFocus.visible = lv.sel < 0
    m.mHi.visible = lv.sel >= 0
    m.mFocus.visible = lv.sel >= 0
    m.mHi.translation = [ml.list.x, y]
    m.mFocus.setFields({ translation: [ml.list.x - 14, y - 14], width: ml.list.w + 28, height: ml.list.itemH + 28 })
end sub

function menuKey(key as string) as boolean
    lv = m.mstack.Peek()
    if key = "up"
        if lv.sel >= 0 then lv.sel = lv.sel - 1
    else if key = "down"
        if lv.sel < lv.items.Count() - 1 then lv.sel = lv.sel + 1
    else if key = "rewind"
        lv.sel = 0
    else if key = "fastforward"
        lv.sel = lv.items.Count() - 1
    else if key = "OK"
        if lv.sel < 0
            menuClose()
        else
            menuActivate(lv.items[lv.sel])
        end if
        return true
    else if key = "back" or key = "options" or key = "left"
        menuClose()
        return true
    end if
    ' the menu is modal: every other key is swallowed
    menuRender()
    return true
end function

sub menuActivate(it as object)
    if it.act = "filter"
        menuClose()
        homeApplyFilter(it.arg)
    else if it.act = "avoid"
        menuShowIngredients()
    else if it.act = "avoidToggle" or it.act = "avoidClear"
        if it.act = "avoidClear"
            m.homeAvoid = {}
        else if m.homeAvoid.DoesExist(it.arg)
            m.homeAvoid.Delete(it.arg)
        else
            m.homeAvoid[it.arg] = true
        end if
        saveIngredientExclusions(m.homeAvoid)
        homeApplyFilter(m.homeCategory)
        menuRender()
    else if it.act = "updates"
        menuCheckRelease()
    else if it.act = "download"
        note = "Scan to download the Roku ZIP. On a computer, upload it with Replace in Roku Development Application Installer."
        m.mstack.Push({ title: "Download " + it.version, sel: 0, note: note, qr: it.arg,
            items: [{ label: "Close", act: "close" }] })
        menuRender()
    else if it.act = "close"
        menuClose()
    else if it.act = "themes"
        items = [
            { label: "Classic", act: "theme", arg: "classic" },
            { label: "Midnight", act: "theme", arg: "midnight" }
        ]
        selected = 0
        if m.themeName = "midnight" then selected = 1
        m.mstack.Push({ title: "Theme", sel: selected, items: items, note: "Choose the background for the cookbook." })
        menuRender()
    else if it.act = "theme"
        applyTheme(it.arg)
        saveTheme(it.arg)
        menuClose()
        if it.arg = "midnight"
            showToast("Midnight theme applied")
        else
            showToast("Classic theme applied")
        end if
    else if it.act = "reset"
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
    end if
end sub

sub menuCheckRelease()
    items = [{ label: "Cancel", act: "close" }]
    m.mstack.Push({ title: "App Update", sel: 0, items: items, checking: true,
        note: "Checking GitHub for a newer release..." })
    menuRender()
    if m.updateTask <> invalid then return
    m.updateTask = CreateObject("roSGNode", "ReleaseLookup")
    m.updateTask.endpoint = m.D.app.latestRelease
    m.updateTask.observeField("result", "menuReleaseResult")
    m.updateTask.control = "RUN"
end sub

sub menuReleaseResult()
    result = m.updateTask.result
    m.updateTask = invalid
    if not m.menuOpen then return
    lv = m.mstack.Peek()
    if not lv.DoesExist("checking") then return
    lv.Delete("checking")
    lv.items = [{ label: "Close", act: "close" }]
    app = m.D.app
    if result.status = 404
        lv.note = "GitHub has no public release available. Installed version v" + app.version + "."
    else if result.status <> 200 or result.release = invalid
        lv.note = "Could not check for updates. Try again later."
    else
        release = result.release
        if release.tag_name = invalid
            lv.note = "Could not check for updates. Try again later."
        else
            matches = CreateObject("roRegex", "^v?([0-9]{1,3})[.]([0-9]{1,3})[.]([0-9]{1,3})$", "").Match(release.tag_name)
            if matches.Count() = 0
                lv.note = "Could not read the version of the GitHub release."
            else
                publishedCode = Val(matches[1]) * 1000000 + Val(matches[2]) * 1000 + Val(matches[3])
                hasZip = false
                if release.assets <> invalid
                    for each asset in release.assets
                        if asset.name = "culinote-roku.zip" then hasZip = true
                    end for
                end if
                if publishedCode <= app.versionCode
                    lv.note = "Version v" + app.version + " is up to date."
                else if not hasZip
                    lv.note = "GitHub release " + release.tag_name + " is missing the Roku ZIP."
                else
                    versionLabel = "v" + matches[1] + "." + matches[2] + "." + matches[3]
                    url = app.releases + "/download/" + release.tag_name + "/culinote-roku.zip"
                    lv.title = "Confirm Update"
                    lv.note = "Installed v" + app.version + Chr(10) + "GitHub release " + versionLabel + Chr(10) + Chr(10) + "Confirm to show the direct download QR code."
                    lv.items = [
                        { label: "Download " + versionLabel, act: "download", version: versionLabel, arg: url },
                        { label: "Cancel", act: "close" }
                    ]
                end if
            end if
        end if
    end if
    menuRender()
end sub
