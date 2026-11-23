' MainScene.brs: builds every screen once, routes remote keys, owns the toast. Mirrors web/js/app.js.

sub init()
    uiInit()
    m.top.backgroundUri = ""
    m.top.backgroundColor = "0x160F0AFF"
    m.root = m.top.findNode("root")
    m.checks = loadChecks()
    m.screen = ""
    m.rec = m.D.recipes[0]
    homeBuild()
    recipeBuild()
    cookBuild()
    menuBuild()
    m.toast = mkGroup(m.root, 0, 0)
    m.toast.visible = false
    mkPoster(m.toast, "images/ui/parchment.9.png", 660, 936, 600, 76)
    m.toastLabel = mkLabel(m.toast, "", "serifBold", 30, m.L.colors.ink, 660, 956, 600, "center", 0)
    m.toastTimer = m.top.createChild("Timer")
    m.toastTimer.duration = 2.2
    m.toastTimer.observeField("fire", "onToastTimer")
    showScreen("home")
    m.top.setFocus(true)
end sub

sub showScreen(name as string)
    m.screen = name
    m.homeG.visible = (name = "home")
    m.recG.visible = (name = "recipe")
    m.cookG.visible = (name = "cook")
    if name = "home" then homeRender()
end sub

function onKeyEvent(key as string, press as boolean) as boolean
    if not press then return false
    if m.menuOpen then return menuKey(key)
    if key = "options"
        menuShow()
        return true
    end if
    if m.screen = "home" then return homeKey(key)
    if m.screen = "recipe" then return recipeKey(key)
    if m.screen = "cook" then return cookKey(key)
    return false
end function
