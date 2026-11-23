' Cook.brs: full-screen, one-step-at-a-time directions with step timers. Mirrors web/js/cook.js.
' A step whose text mentions a duration ("simmer 3–4 minutes") gets a timer (steps[].timer, in seconds,
' worked out by tools/build_data.py). OK starts or stops it; it keeps running on other steps and screens.

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
    m.cTimerG = mkGroup(m.cookG, 0, kl.timer.y)
    m.cTimerIcon = mkPoster(m.cTimerG, "images/ui/icon_clock.png", 0, 0, kl.timer.icon, kl.timer.icon)
    m.cTimerLabel = mkLabel(m.cTimerG, "", "serifBold", kl.timer.size, cc.rust, 0, -4, 0, "left", 0)
    m.cDots = mkGroup(m.cookG, 0, kl.dots.y)
    m.cHint = mkLabel(m.cookG, "", "serif", kl.hint.size, cc.inkSoft, kl.hint.x, kl.hint.y, kl.hint.w, "center", 0)
    m.cs = { sIdx: 0 }
    m.timer = { on: false, done: false, endMs: 0, left: 0, rid: "", step: -1, lead: "" }
    m.wakeN = 0
    m.cTick = m.top.createChild("Timer")
    m.cTick.duration = 1
    m.cTick.repeat = true
    m.cTick.observeField("fire", "cookTick")
end sub

sub cookOpen(stepIdx as integer)
    m.cs = { sIdx: stepIdx }
    showScreen("cook")
    cookRender()
    m.cTick.control = "start"
    cookKeepAwake()
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
    if s.timer > 0 and i = n - 1
        m.cHint.text = "Last step   ·   OK: start or stop the timer   ·   Left: previous   ·   Play or Back: recipe"
    else if s.timer > 0
        m.cHint.text = "OK: start or stop the timer   ·   Right: next step   ·   Left: previous   ·   Play or Back: recipe"
    else if i = n - 1
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
    cookTimerRender()
end sub

' The clock line above the progress dots: an offer, a live countdown, or "time's up".
sub cookTimerRender()
    kl = m.L.cook.timer
    s = m.rec.steps[m.cs.sIdx]
    t = m.timer
    txt = ""
    if t.on and t.rid = m.rec.id and t.step = m.cs.sIdx
        txt = cookClock(t.left) + " left   ·   OK: stop the timer"
    else if t.on
        txt = t.lead + ": " + cookClock(t.left) + " left"
    else if t.done
        txt = "Time's up: " + t.lead + "   ·   OK: dismiss"
    else if s.timer > 0
        txt = "OK: start a " + s.timerText + " timer"
    end if
    m.cTimerG.visible = (txt <> "")
    m.cTimerLabel.text = txt
    w = m.cTimerLabel.boundingRect().width
    if w < 10 then w = Len(txt) * kl.size * 0.45
    x0 = (1920 - (kl.icon + kl.gap + w)) / 2
    m.cTimerIcon.translation = [x0, 0]
    m.cTimerLabel.translation = [x0 + kl.icon + kl.gap, -4]
end sub

' 75 -> "1:15", 3725 -> "1:02:05"
function cookClock(sec as integer) as string
    h = Int(sec / 3600)
    mn = Int((sec - h * 3600) / 60)
    sc = sec - h * 3600 - mn * 60
    ss = sc.ToStr()
    if sc < 10 then ss = "0" + ss
    if h = 0 then return mn.ToStr() + ":" + ss
    ms = mn.ToStr()
    if mn < 10 then ms = "0" + ms
    return h.ToStr() + ":" + ms + ":" + ss
end function

sub cookTimerToggle()
    s = m.rec.steps[m.cs.sIdx]
    t = m.timer
    if s.timer = 0
        t.done = false
    else if t.on and t.rid = m.rec.id and t.step = m.cs.sIdx
        t.on = false
        showToast("Timer stopped")
    else
        lead = s.lead
        if Right(lead, 1) = "." then lead = Left(lead, Len(lead) - 1)
        m.timer = { on: true, done: false, endMs: nowMs() + s.timer * 1000, left: s.timer, rid: m.rec.id, step: m.cs.sIdx, lead: lead }
        m.cTick.control = "start"
        showToast(s.timerText + " timer started")
    end if
end sub

' Fires every second while cook mode is open or a timer is running.
sub cookTick()
    t = m.timer
    if t.on
        t.left = Int((t.endMs - nowMs() + 999) / 1000)
        if t.left <= 0
            t.on = false
            t.done = true
            t.left = 0
            showToast("Time's up: " + t.lead)
        end if
    end if
    if m.screen = "cook"
        cookTimerRender()
        m.wakeN = m.wakeN + 1
        if m.wakeN >= 30
            m.wakeN = 0
            cookKeepAwake()
        end if
    else if not t.on
        m.cTick.control = "stop"
    end if
end sub

' Long simmering steps shouldn't trip the screensaver: count cook mode as activity.
sub cookKeepAwake()
    am = CreateObject("roAppManager")
    if am <> invalid then am.UpdateLastKeyPressTime()
end sub

function cookKey(key as string) as boolean
    n = m.rec.steps.Count()
    if key = "left" or key = "rewind" or key = "up"
        if m.cs.sIdx > 0 then m.cs.sIdx = m.cs.sIdx - 1
    else if key = "OK" and (m.rec.steps[m.cs.sIdx].timer > 0 or m.timer.done)
        cookTimerToggle()
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
