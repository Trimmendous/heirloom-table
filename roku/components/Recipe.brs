' Recipe.brs: the recipe card (dish, title parchment + meta strip, ingredients with checkboxes,
' and scrollable numbered directions). Mirrors web/js/recipe.js.

sub recipeBuild()
    rl = m.L.recipe
    cc = m.L.colors
    m.recG = mkGroup(m.root, 0, 0)
    m.recG.visible = false
    m.recipeBg = mkPoster(m.recG, rl.bg, 0, 0, 1920, 1080)
    m.rDish = mkPoster(m.recG, "", rl.dish.x, rl.dish.y, rl.dish.w, rl.dish.h)
    cw = rl.cookware
    m.rCookware = mkGroup(m.recG, cw.x, cw.y)
    mkRect(m.rCookware, "0x160F0AEC", 0, 0, cw.w, cw.h)
    m.rCookwareLabel = mkLabel(m.rCookware, "", "serif", cw.size, cc.goldLight, 14, 3, cw.w - 28, "center", 2)
    mkLabel(m.recG, "Culinote", "script", rl.header.size, cc.gold, rl.header.x, rl.header.y, rl.header.w, "center", 0)

    ' title parchment
    m.rTitle = mkLabel(m.recG, "", "script", rl.title.size, cc.ink, rl.title.x, rl.title.y, rl.title.w, "center", 0)
    m.rTitle.height = rl.title.h
    m.rTitle.vertAlign = "center"
    m.rDesc = mkLabel(m.recG, "", "serif", rl.desc.size, cc.ink, rl.desc.x, rl.desc.y, rl.desc.w, "center", 2)
    icons = ["clock", "pot", "utensils", "hat"]
    names = ["Prep", "Cook", "Serves", "Difficulty"]
    mt = rl.meta
    m.rMeta = []
    for k = 0 to 3
        cx = mt.x + k * mt.colW
        mkPoster(m.recG, "images/ui/icon_" + icons[k] + ".png", cx + (mt.colW - 12 - mt.icon) / 2, mt.y, mt.icon, mt.icon)
        mkLabel(m.recG, names[k], "serifBold", mt.size, cc.ink, cx, mt.y + mt.icon, mt.colW - 12, "center", 0)
        valueLabel = invalid
        if k <> 2 then valueLabel = mkLabel(m.recG, "", "serif", mt.size, cc.ink, cx, mt.y + mt.icon + 30, mt.colW - 12, "center", 0)
        m.rMeta.Push(valueLabel)
    end for
    m.rGarnish = mkPoster(m.recG, "", rl.garnish.x, rl.garnish.y, rl.garnish.s, rl.garnish.s)

    ' section headers
    m.rGarnishSmall = mkPoster(m.recG, "", rl.garnishSmall.x, rl.garnishSmall.y, rl.garnishSmall.s, rl.garnishSmall.s)
    mkLabel(m.recG, "Ingredients", "script", rl.ingHeader.size, cc.ink, rl.ingHeader.x, rl.ingHeader.y, rl.ingHeader.w, "left", 0)
    mkLabel(m.recG, "Directions", "script", rl.dirHeader.size, cc.gold, rl.dirHeader.x, rl.dirHeader.y, rl.dirHeader.w, "left", 0)
    m.rStepCount = mkLabel(m.recG, "", "serif", 26, cc.goldLight, rl.steps.x + rl.steps.w - 420, rl.dirHeader.y + 28, 400, "right", 0)

    ' focus layer sits under the lists
    m.rHi = mkRect(m.recG, "0xB8862E33", 0, 0, 10, 10)
    m.rFocus = mkPoster(m.recG, "images/ui/focus.9.png", 0, 0, 10, 10)
    nv = rl.nutrition
    m.rNutrition = mkGroup(m.recG, nv.x, nv.y)
    mkPoster(m.rNutrition, "images/ui/parchment.9.png", 0, 0, nv.w, nv.h)
    mkLabel(m.rNutrition, "Nutrition", "serifBold", nv.size, cc.ink, 0, 6, nv.w, "center", 0)
    sv = rl.servings
    spinner = mkGroup(m.recG, sv.x, sv.y)
    mkRect(spinner, "0x9B714CFF", 0, 0, sv.w, sv.h)
    mkRect(spinner, "0xF3DFC0FF", 2, 2, sv.w - 4, sv.h - 4)
    m.rServingsLabel = mkLabel(spinner, "", "serif", sv.size, cc.ink, 2, 0, 69, "center", 0)
    m.rServingsLabel.height = sv.h
    m.rServingsLabel.vertAlign = "center"
    m.rServingsUp = mkPoster(spinner, "images/ui/chev_up_ink.png", sv.w - 34, 4, 22, 13)
    m.rServingsDown = mkPoster(spinner, "images/ui/chev_down_ink.png", sv.w - 34, sv.h - 17, 22, 13)
    m.serveCounts = {}
    m.rIngG = mkGroup(m.recG, rl.ingList.x, rl.ingList.y)
    m.rStepG = mkGroup(m.recG, rl.steps.x, rl.steps.y)
    il = rl.ingList
    st = rl.steps
    m.rIngUp = mkPoster(m.recG, "images/ui/chev_up_ink.png", il.x + il.w - 30, il.y + 2, 30, 20)
    m.rIngDown = mkPoster(m.recG, "images/ui/chev_down_ink.png", il.x + il.w - 30, il.y + il.h - 20, 30, 20)
    m.rStepUp = mkPoster(m.recG, "images/ui/chev_up.png", st.x + st.w - 30, st.y + 2, 30, 20)
    ft = rl.stepFooter
    footer = mkGroup(m.recG, st.x, ft.y)
    mkRect(footer, "0x140D09DD", 0, 0, st.w, ft.h)
    mkRect(footer, "0xB8862E80", 0, 0, st.w, 2)
    m.rStepRange = mkLabel(footer, "", "serif", ft.size, cc.goldLight, 16, 4, st.w - ft.actionW - 30, "left", 0)
    m.rStepMore = mkGroup(footer, st.w - ft.actionW, 0)
    mkRect(m.rStepMore, "0xB8862E4D", 0, 2, ft.actionW, ft.h - 2)
    m.rStepMoreArrow = mkPoster(m.rStepMore, "", 18, 11, 31, 22)
    m.rStepMoreLabel = mkLabel(m.rStepMore, "", "serifBold", ft.size, cc.goldLight, 62, 4, ft.actionW - 76, "left", 0)
    m.rs = { rpos: 0, zone: "steps", ing: 0, ingTop: 0, sIdx: 0, stepTop: 0 }
end sub

sub recipeOpen(rpos as integer)
    showScreen("recipe")
    recipeShow(rpos)
end sub

sub recipeShow(rpos as integer, previous = invalid as dynamic)
    rl = m.L.recipe
    cc = m.L.colors
    r = recipeAt(rpos)
    m.rec = r
    m.rs = { rpos: rpos, zone: "steps", ing: 0, ingTop: 0, sIdx: 0, stepTop: 0 }
    m.rServes = m.serveCounts[r.id]
    if m.rServes = invalid then m.rServes = r.serves
    m.servingVariant = r.servingVariants[m.rServes - 1]
    m.rNutrition.visible = m.servingVariant.DoesExist("nutritionText")
    m.rDish.uri = "pkg:/" + r.image
    m.rCookware.visible = r.cookwareText <> ""
    if m.rCookware.visible then m.rCookwareLabel.text = "Cookware · " + r.cookwareText
    size = rl.title.size
    if Len(r.title) > rl.title.longAt then size = rl.title.sizeLong
    m.rTitle.font = uiFont("script", size)
    m.rTitle.text = r.title
    m.rDesc.text = r.description
    m.rMeta[0].text = m.servingVariant.prepText
    m.rMeta[1].text = m.servingVariant.cookText
    m.rMeta[3].text = r.difficulty
    m.rGarnish.uri = "pkg:/" + r.garnish
    m.rGarnishSmall.uri = "pkg:/" + r.garnish

    ' ingredients: build every row once, measure, then window them
    il = rl.ingList
    tw = il.w - il.textX - 40
    removeKids(m.rIngG)
    m.ingNodes = []
    m.ingH = []
    m.ingBoxes = []
    first = -1
    for i = 0 to r.ingredients.Count() - 1
        it = r.ingredients[i]
        g = m.rIngG.createChild("Group")
        if it.header
            lb = mkLabel(g, it.text, "serifBold", il.size, cc.rust, 0, 2, il.w - 40, "left", 2)
            m.ingBoxes.Push(invalid)
            h = textHeight(lb, il.size, Len(it.text), il.w - 40) + 2
        else
            if first < 0 then first = i
            cb = mkPoster(g, checkUri(r.id, i), 0, 5, il["box"], il["box"])
            m.ingBoxes.Push(cb)
            ingredient = recipeScaledText("ingredients", i, it.text)
            lb = mkLabel(g, ingredient, "serif", il.size, cc.ink, il.textX, 0, tw, "left", 3)
            h = textHeight(lb, il.size, Len(ingredient), tw)
            if h < il["box"] + 6 then h = il["box"] + 6
        end if
        m.ingNodes.Push(g)
        m.ingH.Push(h)
    end for
    if first < 0 then first = 0
    m.rs.ing = first

    ' steps
    st = rl.steps
    sw = st.w - st.textX - 40
    removeKids(m.rStepG)
    m.stepNodes = []
    m.stepH = []
    for i = 0 to r.steps.Count() - 1
        s = r.steps[i]
        g = m.rStepG.createChild("Group")
        mkPoster(g, "images/ui/ring.png", 0, 0, st.ring, st.ring)
        mkLabel(g, (i + 1).ToStr(), "serifBold", 32, cc.goldLight, 0, 6, st.ring, "center", 0)
        stepText = recipeStepText(i)
        lb = mkRich(g, "<b>" + s.lead + "</b> " + stepText, st.size, "0xF0E2C4FF", cc.goldLight, st.textX, 2, sw)
        h = textHeight(lb, st.size, Len(s.lead) + Len(stepText) + 1, sw) + 4
        if h < st.ring then h = st.ring
        m.stepNodes.Push(g)
        m.stepH.Push(h)
    end for
    if previous <> invalid then m.rs = previous
    recipeLayout()
end sub

function recipeScaledText(section as string, index as integer, fallback as string) as string
    value = m.servingVariant[section][index.ToStr()]
    if value = invalid then return fallback
    return value
end function

function recipeStepTiming(index as integer) as object
    timing = m.servingVariant.timers[index.ToStr()]
    if timing = invalid then return m.rec.steps[index]
    return timing
end function

function recipeStepText(index as integer) as string
    return recipeScaledText("steps", index, m.rec.steps[index].text)
end function

sub recipeFocusServings()
    m.rs.returnZone = m.rs.zone
    m.rs.zone = "servings"
end sub

sub recipeSetServings(count as integer)
    if count < 1 then count = 1
    if count > m.D.maxServings then count = m.D.maxServings
    if count = m.rServes
        recipeLayout()
        return
    end if
    m.serveCounts[m.rec.id] = count
    recipeShow(m.rs.rpos, m.rs)
end sub

function checkUri(rid as string, i as integer) as string
    if isChecked(rid, i) then return "images/ui/check_on.png"
    return "images/ui/check_off.png"
end function

sub recipeRefreshChecks()
    for i = 0 to m.ingBoxes.Count() - 1
        if m.ingBoxes[i] <> invalid then m.ingBoxes[i].uri = "pkg:/" + checkUri(m.rec.id, i)
    end for
end sub

sub recipeLayout()
    rl = m.L.recipe
    rs = m.rs
    il = rl.ingList
    st = rl.steps
    ings = m.rec.ingredients
    editing = rs.zone = "servingsEdit"
    shownServes = m.rServes
    if editing then shownServes = rs.draftServes
    m.rServingsLabel.text = shownServes.ToStr()
    m.rServingsUp.opacity = 0.35
    m.rServingsDown.opacity = 0.35
    if editing and shownServes < m.D.maxServings then m.rServingsUp.opacity = 1
    if editing and shownServes > 1 then m.rServingsDown.opacity = 1
    rs.ingTop = fitTop(m.ingH, il.gap, il.h, rs.ingTop, rs.ing)
    ' keep a group heading visible together with its first ingredient
    if rs.ingTop > 0 and rs.ingTop = rs.ing
        if ings[rs.ingTop - 1].header and m.ingH[rs.ingTop - 1] + il.gap + m.ingH[rs.ingTop] <= il.h then rs.ingTop = rs.ingTop - 1
    end if
    lastI = placeItems(m.ingNodes, m.ingH, il.gap, il.h, rs.ingTop)
    ' never leave a group heading orphaned at the bottom of the card
    if lastI > rs.ingTop and ings[lastI].header
        m.ingNodes[lastI].visible = false
        lastI = lastI - 1
    end if
    m.rIngUp.visible = rs.ingTop > 0
    m.rIngDown.visible = lastI < m.ingNodes.Count() - 1
    rs.stepTop = fitTop(m.stepH, st.gap, st.h, rs.stepTop, rs.sIdx)
    lastS = placeItems(m.stepNodes, m.stepH, st.gap, st.h, rs.stepTop)
    m.rStepUp.visible = rs.stepTop > 0
    n = m.stepNodes.Count()
    moreBelow = lastS < n - 1
    m.rStepMore.visible = moreBelow or rs.stepTop > 0
    if moreBelow
        m.rStepMoreLabel.text = "Scroll down for more"
        m.rStepMoreArrow.uri = "pkg:/images/ui/chev_down.png"
    else
        m.rStepMoreLabel.text = "Scroll up for earlier steps"
        m.rStepMoreArrow.uri = "pkg:/images/ui/chev_up.png"
    end if
    shown = (rs.stepTop + 1).ToStr()
    if lastS > rs.stepTop then shown = shown + "–" + (lastS + 1).ToStr()
    m.rStepRange.text = "Showing " + shown + " of " + n.ToStr() + " steps"
    if rs.zone = "ing"
        node = m.ingNodes[rs.ing]
        x = il.x - 12
        y = il.y + node.translation[1] - 6
        w = il.w - 22
        h = m.ingH[rs.ing] + 12
        m.rHi.color = "0xB8862E38"
        m.rStepCount.text = "Right to select directions"
    else if rs.zone = "servings" or editing
        sv = rl.servings
        x = sv.x - 3
        y = sv.y - 3
        w = sv.w + 6
        h = sv.h + 6
        m.rHi.color = "0xB8862E38"
        m.rStepCount.text = "OK to edit servings"
        if editing then m.rStepCount.text = "Up / Down · OK to confirm"
    else if rs.zone = "nutrition"
        nv = rl.nutrition
        x = nv.x
        y = nv.y
        w = nv.w
        h = nv.h
        m.rHi.color = "0xB8862E38"
        m.rStepCount.text = "OK to view nutrition"
    else
        node = m.stepNodes[rs.sIdx]
        x = st.x - 10
        y = st.y + node.translation[1] - 6
        w = st.w - 26
        h = m.stepH[rs.sIdx] + 12
        m.rHi.color = "0xD9A94A24"
        m.rStepCount.text = "Step " + (rs.sIdx + 1).ToStr() + " of " + n.ToStr()
    end if
    m.rHi.setFields({ translation: [x, y], width: w, height: h })
    m.rFocus.setFields({ translation: [x - 14, y - 14], width: w + 28, height: h + 28 })
end sub

function recipeKey(key as string) as boolean
    rs = m.rs
    ings = m.rec.ingredients
    if rs.zone = "servingsEdit"
        if key = "up"
            if rs.draftServes < m.D.maxServings then rs.draftServes = rs.draftServes + 1
        else if key = "down"
            if rs.draftServes > 1 then rs.draftServes = rs.draftServes - 1
        else if key = "OK"
            rs.zone = rs.returnZone
            recipeSetServings(rs.draftServes)
            return true
        else if key = "back"
            rs.zone = "servings"
        end if
        recipeLayout()
        return true
    end if
    if rs.zone = "nutrition"
        if key = "OK"
            menuShowNutrition()
            return true
        else if key = "up" or key = "down" or key = "left" or key = "right"
            rs.zone = "ing"
            recipeLayout()
            return true
        end if
    end if
    if rs.zone = "servings" and (key = "up" or key = "down")
        if key = "down" then rs.zone = rs.returnZone
        recipeLayout()
        return true
    end if
    if key = "up"
        if rs.zone = "ing"
            i = rs.ing - 1
            while i >= 0 and ings[i].header
                i = i - 1
            end while
            if i >= 0
                rs.ing = i
            else
                recipeFocusServings()
            end if
        else if rs.sIdx > 0
            rs.sIdx = rs.sIdx - 1
        else
            recipeFocusServings()
        end if
    else if key = "down"
        if rs.zone = "ing"
            i = rs.ing + 1
            while i < ings.Count() and ings[i].header
                i = i + 1
            end while
            if i < ings.Count() then rs.ing = i
        else if rs.sIdx < m.stepNodes.Count() - 1
            rs.sIdx = rs.sIdx + 1
        end if
    else if key = "right"
        rs.zone = "steps"
    else if key = "left"
        if rs.zone = "ing" and m.rNutrition.visible
            rs.zone = "nutrition"
        else
            rs.zone = "ing"
        end if
    else if key = "OK"
        if rs.zone = "servings"
            rs.draftServes = m.rServes
            rs.zone = "servingsEdit"
        else if rs.zone = "ing"
            setChecked(m.rec.id, rs.ing, not isChecked(m.rec.id, rs.ing))
            recipeRefreshChecks()
        else
            cookOpen(rs.sIdx)
            return true
        end if
    else if key = "play"
        if rs.zone = "steps"
            cookOpen(rs.sIdx)
        else
            cookOpen(0)
        end if
        return true
    else if key = "rewind"
        recipeShow(homeAdjacentRecipe(rs.rpos, -1))
        return true
    else if key = "fastforward"
        recipeShow(homeAdjacentRecipe(rs.rpos, 1))
        return true
    else if key = "back"
        homeFocusRecipe(rs.rpos)
        showScreen("home")
        return true
    else
        return false
    end if
    recipeLayout()
    return true
end function

' Return from cook mode with the directions focused on the step the cook reached.
sub recipeFocusStep(stepIdx as integer)
    m.rs.zone = "steps"
    m.rs.sIdx = stepIdx
    recipeLayout()
end sub
