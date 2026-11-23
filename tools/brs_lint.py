#!/usr/bin/env python3
"""Offline BrightScript/SceneGraph lint (no Roku SDK needed).

Checks:
  * XML components are well-formed and every <script uri> exists
  * block balance: sub/function, if/else/end if, for/end for, while/end while
  * reserved words used as variable names (e.g. `pos`, `box`, `step`)
  * duplicate function names within one component scope (a runtime error on Roku)
  * calls to undefined functions (component scope + BrightScript built-ins)
  * lockstep: every sub/function in roku/components/X.brs has a twin in web/js/x.js
"""
import os, re, sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROKU = os.path.join(ROOT, "roku")
WEB_TWIN = {"Ui.brs": "ui.js", "Home.brs": "home.js", "Recipe.brs": "recipe.js", "Cook.brs": "cook.js",
            "Menu.brs": "menu.js", "MainScene.brs": "app.js"}
RESERVED = {"and", "box", "createobject", "dim", "each", "else", "elseif", "end", "endfunction", "endif",
            "endsub", "endwhile", "eval", "exit", "exitwhile", "false", "for", "function", "getglobalaa",
            "getlastruncompileerror", "getlastrunruntimeerror", "goto", "if", "invalid", "let", "line_num",
            "m", "next", "not", "objfun", "or", "pos", "print", "rem", "return", "run", "step", "stop", "sub",
            "tab", "then", "to", "true", "type", "while", "mod"}
BUILTINS = {"createobject", "parsejson", "formatjson", "readasciifile", "writeasciifile", "int", "len", "str",
            "stri", "mid", "left", "right", "ucase", "lcase", "abs", "val", "chr", "asc", "instr", "wait", "type",
            "sleep", "uptime", "getglobalaa", "box", "fix", "cint", "sgn", "rnd", "string", "substitute",
            "tr", "strtoi", "listdir", "matchfiles", "copyfile", "deletefile", "getinterface", "rebootsystem"}
errors = []


def err(where, msg):
    errors.append("%s: %s" % (where, msg))


def code_lines(path):
    """Yield (lineno, code) with comments and string contents removed."""
    for n, raw in enumerate(open(path, encoding="utf-8"), 1):
        out, in_str = [], False
        i = 0
        while i < len(raw):
            c = raw[i]
            if c == '"':
                in_str = not in_str
                out.append('""' if not in_str else "")
            elif not in_str:
                if c == "'":
                    break
                if raw[i:i + 4].lower() == "rem " and raw[:i].strip() == "":
                    break
                out.append(c)
            i += 1
        yield n, "".join(out).rstrip()


def lint_file(path, defs):
    rel = os.path.relpath(path, ROOT)
    stack = []
    calls = []
    for n, line in code_lines(path):
        s = line.strip()
        low = s.lower()
        where = "%s:%d" % (rel, n)
        if not s:
            continue
        mdef = re.match(r"(sub|function)\s+([a-z_][a-z0-9_]*)\s*\(", low)
        if mdef:
            if stack:
                err(where, "%s %s opened inside %s" % (mdef.group(1), mdef.group(2), stack[-1][0]))
            stack.append((mdef.group(1), n))
            defs.setdefault(mdef.group(2), []).append(where)
            continue
        mend = re.match(r"end\s*(sub|function|if|for|while)\b", low)
        if mend:
            kind = mend.group(1)
            if not stack:
                err(where, "end %s without opener" % kind)
            elif stack[-1][0] != kind:
                err(where, "end %s closes %s opened at line %d" % (kind, stack[-1][0], stack[-1][1]))
                stack.pop()
            else:
                stack.pop()
            continue
        if low == "next" or low.startswith("next "):
            if stack and stack[-1][0] == "for":
                stack.pop()
            else:
                err(where, "next without for")
            continue
        if re.match(r"if\b", low):
            mthen = re.search(r"\bthen\b(.*)$", low)
            if not (mthen and mthen.group(1).strip()):
                stack.append(("if", n))
        elif re.match(r"else\s*if\b|elseif\b|else\b", low):
            if not stack or stack[-1][0] != "if":
                err(where, "else outside if block")
        elif re.match(r"for\b", low):
            stack.append(("for", n))
        elif re.match(r"while\b", low):
            stack.append(("while", n))
        massign = re.match(r"([a-z_][a-z0-9_]*)\s*=(?!=)", low)
        if massign and massign.group(1) in RESERVED:
            err(where, "reserved word %r used as a variable" % massign.group(1))
        for mp in re.finditer(r"\b(sub|function)\s+[a-z_]\w*\s*\(([^)]*)\)", low):
            for p in mp.group(2).split(","):
                pn = p.strip().split(" ")[0]
                if pn in RESERVED:
                    err(where, "reserved word %r used as a parameter" % pn)
        for mc in re.finditer(r"(?<![\.\w])([a-z_][a-z0-9_]*)\s*\(", low):
            name = mc.group(1)
            if name not in RESERVED:
                calls.append((name, where))
        for mf in re.finditer(r"\bfor\s+(each\s+)?([a-z_]\w*)", low):
            if mf.group(2) in RESERVED:
                err(where, "reserved word %r used as loop variable" % mf.group(2))
    for kind, n in stack:
        err(rel, "%s opened at line %d is never closed" % (kind, n))
    return calls


def lint_scope(name, files):
    defs, calls = {}, []
    for f in files:
        calls += lint_file(f, defs)
    for fn, wh in defs.items():
        if len(wh) > 1:
            err(name, "function %s defined more than once: %s" % (fn, ", ".join(wh)))
    for fn, wh in calls:
        if fn not in defs and fn not in BUILTINS:
            err(wh, "call to undefined function %s()" % fn)
    return defs


def twin_check(brs, defs_in_file):
    js = os.path.join(ROOT, "web", "js", WEB_TWIN.get(os.path.basename(brs), ""))
    if not os.path.isfile(js):
        err(os.path.relpath(brs, ROOT), "no web twin %s" % os.path.relpath(js, ROOT))
        return
    src = open(js, encoding="utf-8").read()
    jsdefs = {m.lower() for m in re.findall(r"function\s+([A-Za-z_]\w*)\s*\(", src)}
    for fn in defs_in_file:
        if fn not in jsdefs:
            err(os.path.relpath(brs, ROOT), "%s() has no twin in %s (keep Roku and web in lockstep)" % (fn, os.path.relpath(js, ROOT)))


def main():
    comp_dir = os.path.join(ROKU, "components")
    n_files = 0
    for fn in sorted(os.listdir(comp_dir)):
        if not fn.endswith(".xml"):
            continue
        path = os.path.join(comp_dir, fn)
        try:
            tree = ET.parse(path)
        except ET.ParseError as e:
            err(fn, "XML parse error: %s" % e)
            continue
        comp = tree.getroot()
        scripts = []
        for s in comp.iter("script"):
            uri = s.get("uri", "")
            p = os.path.join(ROKU, uri.replace("pkg:/", ""))
            if not os.path.isfile(p):
                err(fn, "script %s missing" % uri)
            else:
                scripts.append(p)
        lint_scope(comp.get("name"), scripts)
        for sp in scripts:
            d = {}
            lint_file(sp, d)
            twin_check(sp, d)
            n_files += 1
        src = "\n".join(open(p).read() for p in scripts).lower()
        if comp.get("extends") == "Scene" and "function onkeyevent(" not in src:
            err(fn, "Scene has no onKeyEvent()")
    src_files = [os.path.join(ROKU, "source", f) for f in os.listdir(os.path.join(ROKU, "source")) if f.endswith(".brs")]
    defs = lint_scope("source", src_files)
    n_files += len(src_files)
    if "main" not in defs:
        err("source", "no Main() entry point")
    main_src = "".join(open(p).read() for p in src_files)
    for scene in re.findall(r'CreateScene\("(\w+)"\)', main_src):
        if not os.path.isfile(os.path.join(comp_dir, scene + ".xml")):
            err("source", "CreateScene(%s) has no component" % scene)
    if errors:
        print("BrightScript lint FAILED:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("BrightScript lint OK (%d files, blocks balanced, web twins present)" % n_files)


if __name__ == "__main__":
    main()
