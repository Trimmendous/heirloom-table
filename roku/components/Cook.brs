' Cook.brs: full-screen, one-step-at-a-time directions. Mirrors web/js/cook.js.

sub cookBuild()
    kl = m.L.cook
    cc = m.L.colors
    m.cookG = mkGroup(m.root, 0, 0)
    m.cookG.visible = false
    mkPoster(m.cookG, kl.bg, 0, 0, 1920, 1080)
    m.cTitle = mkLabel(m.cookG, "", "script", kl.title.size, cc.ink, kl.title.x, kl.title.y, kl.title.w, "center", 0)
    m.cCounter = mkLabel(m.cookG, "", "serifBold", kl.counter.size, cc.rust, kl.counter.x, kl.counter.y, kl.counter.w, "center", 0)
    mkPoster(m.cookG, "images/ui/ring_lg.png", kl.ring.x, kl.ring.y, kl.ring.s, kl.ring.s)
    m.cNum = mkLabel(m.cookG, "", "serifBold", kl.ring.size, cc.goldLight, kl.ring.x, kl.ring.y + 14, kl.ring.s, "center", 0)
    m.cLead = mkLabel(m.cookG, "", "serifBold", kl.lead.size, cc.ink, kl.lead.x, kl.lead.y, kl.lead.w, "center", 0)
    m.cText = mkLabel(m.cookG, "", "serif", kl.text.size, cc.ink, kl.text.x, kl.text.y, kl.text.w, "center", kl.text.maxLines)
    m.cDots = mkGroup(m.cookG, 0, kl.dots.y)
    m.cHint = mkLabel(m.cookG, "", "serif", kl.hint.size, cc.inkSoft, kl.hint.x, kl.hint.y, kl.hint.w, "center", 0)
    m.cs = { sIdx: 0 }
end sub

sub cookOpen(stepIdx as integer)
    m.cs = { sIdx: stepIdx }
    showScreen("cook")
    cookRender()
end sub

sub cookRender()
    kl = m.L.cook
    r = m.rec
    n = r.steps.Count()
    i = m.cs.sIdx
    s = r.steps[i]
    m.cTitle.text = r.title
    m.cCounter.text = "Step " + (i + 1).ToStr() + " of " + n.ToStr()
    m.cNum.text = (i + 1).ToStr()
    m.cLead.text = s.lead
    m.cText.text = s.text
    if i = n - 1
        m.cHint.text = "Last step. Enjoy your meal!   ·   Left: previous   ·   Play or Back: return to the recipe"
    else
        m.cHint.text = "Right or OK: next step   ·   Left: previous   ·   Play or Back: return to the recipe"
    end if
    removeKids(m.cDots)
    total = n * kl.dots.s + (n - 1) * kl.dots.gap
    x0 = (1920 - total) / 2
    for d = 0 to n - 1
        uri = "images/ui/dot_off.png"
        if d <= i then uri = "images/ui/dot_on.png"
        mkPoster(m.cDots, uri, x0 + d * (kl.dots.s + kl.dots.gap), 0, kl.dots.s, kl.dots.s)
    end for
end sub

function cookKey(key as string) as boolean
    n = m.rec.steps.Count()
    if key = "left" or key = "rewind" or key = "up"
        if m.cs.sIdx > 0 then m.cs.sIdx = m.cs.sIdx - 1
    else if key = "right" or key = "fastforward" or key = "down" or key = "OK"
        if m.cs.sIdx < n - 1
            m.cs.sIdx = m.cs.sIdx + 1
        else if key = "OK"
            showToast("Bon appétit!")
        end if
    else if key = "play" or key = "back"
        showScreen("recipe")
        recipeFocusStep(m.cs.sIdx)
        return true
    else
        return false
    end if
    cookRender()
    return true
end function
