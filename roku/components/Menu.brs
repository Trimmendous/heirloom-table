' Menu.brs: the Options (*) overlay: reset checkboxes, browse all recipes, jump to a category.
' Levels stack, so "Browse all recipes" opens a list and Back returns to the options. Mirrors web/js/menu.js.

sub menuBuild()
    ml = m.L.menu
    cc = m.L.colors
    m.menuG = mkGroup(m.root, 0, 0)
    m.menuG.visible = false
    mkRect(m.menuG, cc.dim, 0, 0, 1920, 1080)
    m.mPanel = mkPoster(m.menuG, "images/ui/parchment.9.png", ml.panel.x, ml.panel.y, ml.panel.w, ml.panel.h)
    m.mTitle = mkLabel(m.menuG, "", "script", ml.title.size, cc.ink, ml.title.x, ml.title.y, ml.title.w, "center", 0)
    m.mHi = mkRect(m.menuG, "0xB8862E40", ml.list.x, ml.list.y, ml.list.w, ml.list.itemH)
    m.mFocus = mkPoster(m.menuG, "images/ui/focus.9.png", 0, 0, 10, 10)
    m.mList = mkGroup(m.menuG, ml.list.x, ml.list.y)
    m.mUp = mkPoster(m.menuG, "images/ui/chev_up_ink.png", ml.list.x + ml.list.w / 2 - 15, ml.list.y - 26, 30, 20)
    m.mDown = mkPoster(m.menuG, "images/ui/chev_down_ink.png", ml.list.x + ml.list.w / 2 - 15, ml.list.y + ml.list.visible * ml.list.itemH + 4, 30, 20)
    m.mNote = mkLabel(m.menuG, "", "serif", ml.note.size, cc.inkSoft, ml.note.x, 0, ml.note.w, "left", 7)
    m.mQR = m.menuG.createChild("QRCode")
    m.mQR.setFields({ translation: [825, 524], width: 270, height: 270, visible: false })
    m.menuOpen = false
    m.mstack = []
end sub

sub menuShow()
    items = [
        { label: "Update Now", act: "updates" },
        { label: "Theme", act: "themes" }
    ]
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
    m.mstack = []
    m.mQR.visible = false
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
    m.mQR.visible = lv.DoesExist("qr")
    if m.mQR.visible then m.mQR.text = lv.qr
    m.mNote.visible = lv.DoesExist("note")
    if m.mNote.visible
        m.mNote.text = lv.note
        m.mNote.translation = [ml.note.x, ml.list.y + n * ml.list.itemH + ml.note.gap]
        m.mPanel.height = ml.note.panelH
    else
        m.mPanel.height = ml.panel.h
    end if
    if m.mQR.visible then m.mPanel.height = ml.panel.h
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
    else if key = "back" or key = "options" or key = "left"
        menuClose()
        return true
    end if
    ' the menu is modal: every other key is swallowed
    menuRender()
    return true
end function

sub menuActivate(it as object)
    if it.act = "updates"
        menuCheckRelease()
    else if it.act = "download"
        note = "Scan to download the Roku ZIP. On a computer, upload it with Replace in Roku Development Application Installer."
        m.mstack.Push({ title: "Download " + it.version, sel: 0, top: 0, note: note, qr: it.arg,
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
        m.mstack.Push({ title: "Theme", sel: selected, top: 0, items: items, note: "Choose the background for the cookbook." })
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

sub menuCheckRelease()
    items = [{ label: "Cancel", act: "close" }]
    m.mstack.Push({ title: "App Update", sel: 0, top: 0, items: items, checking: true,
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
                        if asset.name = "heirloom-table-roku.zip" then hasZip = true
                    end for
                end if
                if publishedCode <= app.versionCode
                    lv.note = "Version v" + app.version + " is up to date."
                else if not hasZip
                    lv.note = "GitHub release " + release.tag_name + " is missing the Roku ZIP."
                else
                    versionLabel = "v" + matches[1] + "." + matches[2] + "." + matches[3]
                    url = app.releases + "/download/" + release.tag_name + "/heirloom-table-roku.zip"
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
