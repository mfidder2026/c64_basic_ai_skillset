#!/usr/bin/env python3
"""c64_syntax_checker.py - Syntax checker voor C64 BASIC V2 broncode.

Volgt de controles uit C64_BASIC_SKILL.md §2.2:
  - regelnummers 0-63999, uniek, oplopend
  - haakjes balans, quotes balans
  - onbekende keywords
  - if zonder then
  - for/next paring
  - goto/gosub doelen
  - on ... goto/gosub lijsten
  - keywords in variabelenamen (rem-commentaar wordt overgeslagen)
  - bereikbaarheid (optioneel, uit met C64_NO_REACH=1)

Gebruik:
  python c64_syntax_checker.py programma.bas
  C64_NO_REACH=1 python c64_syntax_checker.py programma.bas
"""
import os
import re
import sys

KEYWORDS = {
    "end", "for", "next", "data", "input#", "input", "dim", "read", "let",
    "goto", "run", "if", "restore", "gosub", "return", "rem", "stop", "on",
    "wait", "load", "save", "verify", "def", "poke", "print#", "print",
    "cont", "list", "clr", "cmd", "sys", "open", "close", "get", "new",
    "tab(", "spc(", "to", "fn", "then", "not", "step", "and", "or", "sgn",
    "int", "abs", "usr", "fre", "pos", "sqr", "rnd", "log", "exp", "cos",
    "sin", "tan", "atn", "peek", "len", "str$", "val", "asc", "chr$",
    "left$", "right$", "mid$", "go", "pi",
}
VAR_BREAKERS = {
    "end", "for", "next", "data", "input", "dim", "read", "let", "goto",
    "run", "if", "restore", "gosub", "return", "rem", "stop", "on", "wait",
    "load", "save", "verify", "def", "poke", "print", "cont", "list", "clr",
    "cmd", "sys", "open", "close", "get", "new", "to", "then", "step", "and",
    "or", "go",
}
FUNCS = {
    "tab(", "spc(", "sgn", "int", "abs", "usr", "fre", "pos", "sqr", "rnd",
    "log", "exp", "cos", "sin", "tan", "atn", "peek", "len", "str$", "val",
    "asc", "chr$", "left$", "right$", "mid$", "fn", "pi",
}
SYMBOLS = {"+", "-", "*", "/", "^", ">", "=", "<"}
SYS_VARS = {"st", "ti", "ti$"}


def tokenize(line):
    """Return lijst van (type, text): 'str', 'num', 'kw', 'id', 'sym', 'punct'."""
    toks = []
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch.isspace():
            i += 1
            continue
        if ch == '"':
            j = i + 1
            while j < n and line[j] != '"':
                j += 1
            toks.append(("str", line[i:j + 1]))
            i = j + 1
            continue
        if ch.isdigit() or (ch == "." and i + 1 < n and line[i + 1].isdigit()):
            j = i
            while j < n and (line[j].isdigit() or line[j] == "."):
                j += 1
            if j < n and line[j] in "eE":
                j += 1
                if j < n and line[j] in "+-":
                    j += 1
                while j < n and line[j].isdigit():
                    j += 1
            toks.append(("num", line[i:j]))
            i = j
            continue
        if ch.isalpha():
            j = i
            while j < n and (line[j].isalnum() or line[j] == "$" or line[j] == "%"):
                j += 1
            word = line[i:j].lower()
            matched = None
            for kw in ("tab(", "spc(", "left$", "right$", "mid$", "chr$", "str$",
                       "input#", "print#"):
                low = kw.lower()
                if line[i:].lower().startswith(low):
                    matched = kw.lower()
                    j = i + len(low)
                    break
            if matched:
                toks.append(("kw", matched))
                i = j
                continue
            if word in KEYWORDS:
                toks.append(("kw", word))
                i = j
                continue
            toks.append(("id", word))
            i = j
            continue
        if ch in "+-*/^><=":
            toks.append(("sym", ch))
            i += 1
            continue
        if ch in "(),;:":
            toks.append(("punct", ch))
            i += 1
            continue
        toks.append(("sym", ch))
        i += 1
    return toks


def split_statements(toks):
    """Splits op ':' maar niet binnen haakjes of strings."""
    stmts = []
    cur = []
    depth = 0
    for t in toks:
        ty, tx = t
        if ty == "punct" and tx == "(":
            depth += 1
            cur.append(t)
        elif ty == "punct" and tx == ")":
            depth -= 1
            cur.append(t)
        elif ty == "punct" and tx == ":" and depth == 0:
            stmts.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        stmts.append(cur)
    return stmts


def check_file(path):
    errors = []
    warnings = []
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            lines.append(raw.rstrip("\n"))

    nums = []
    num_to_idx = {}
    for idx, raw in enumerate(lines):
        if raw.strip() == "":
            continue
        m = re.match(r"\s*(\d+)(.*)", raw)
        if not m:
            errors.append("line " + str(idx + 1) + ": geen regelnummer")
            continue
        num = int(m.group(1))
        if num < 0 or num > 63999:
            errors.append("line " + str(num) + ": regelnummer buiten 0-63999")
        if num in num_to_idx:
            errors.append("line " + str(num) + ": dubbel regelnummer")
        nums.append(num)
        num_to_idx[num] = idx

    for a in range(1, len(nums)):
        if nums[a] <= nums[a - 1]:
            errors.append("line " + str(nums[a]) + ": regelnummer niet oplopend")

    for_raw = {}
    next_raw = {}
    for_targets = set()
    gosub_targets = set()
    for num, raw in zip(nums, [l for l in lines if re.match(r"\s*\d+", l)]):
        m = re.match(r"\s*\d+(.*)", raw)
        if not m:
            continue
        body = m.group(1)
        if len(raw) > 80:
            warnings.append("line " + str(num) + ": langer dan 80 tekens")
        q = body.count('"')
        if q % 2 != 0:
            errors.append("line " + str(num) + ": oneven aantal quotes")
        toks = tokenize(body)
        depth = 0
        for ty, tx in toks:
            if ty == "punct" and tx == "(":
                depth += 1
            elif ty == "punct" and tx == ")":
                depth -= 1
                if depth < 0:
                    errors.append("line " + str(num) + ": haakje sluiten zonder openen")
                    depth = 0
        if depth != 0:
            errors.append("line " + str(num) + ": haakjes niet in balans")

        stmts = split_statements(toks)
        for st in stmts:
            if not st:
                continue
            head = st[0]
            if head[0] != "kw":
                continue
            kw = head[1]
            if kw == "if":
                has_then = any(t[0] == "kw" and t[1] == "then" for t in st)
                if not has_then:
                    errors.append("line " + str(num) + ": if zonder then")
            if kw == "for":
                if len(st) < 2 or st[1][0] != "id":
                    errors.append("line " + str(num) + ": for zonder variabele")
                else:
                    for_raw[st[1][1]] = num
            if kw == "next":
                if len(st) >= 2 and st[1][0] == "id":
                    next_raw[st[1][1]] = num
                else:
                    next_raw[""] = num
            if kw == "goto":
                if len(st) >= 2 and st[1][0] == "num":
                    for_targets.add(int(st[1][1]))
                else:
                    errors.append("line " + str(num) + ": goto zonder doel")
            if kw == "gosub":
                if len(st) >= 2 and st[1][0] == "num":
                    gosub_targets.add(int(st[1][1]))
                else:
                    errors.append("line " + str(num) + ": gosub zonder doel")
            if kw == "on":
                gidx = None
                for gi in range(1, len(st)):
                    if st[gi][0] == "kw" and st[gi][1] in ("goto", "gosub"):
                        gidx = gi
                        break
                if gidx is None:
                    errors.append("line " + str(num) + ": on zonder goto/gosub")
                else:
                    tgtset = for_targets if st[gidx][1] == "goto" else gosub_targets
                    for ti in range(gidx + 1, len(st)):
                        if st[ti][0] == "num":
                            tgtset.add(int(st[ti][1]))
            if kw == "then":
                if len(st) >= 2 and st[1][0] == "num":
                    for_targets.add(int(st[1][1]))

    for v, ln in for_raw.items():
        if v not in next_raw and "" not in next_raw:
            errors.append("line " + str(ln) + ": for zonder next (" + v + ")")
    for v, ln in next_raw.items():
        if v == "":
            continue
        if v not in for_raw:
            errors.append("line " + str(ln) + ": next zonder for (" + v + ")")

    for t in for_targets:
        if t not in num_to_idx:
            errors.append("goto/then doel " + str(t) + " bestaat niet")
    for t in gosub_targets:
        if t not in num_to_idx:
            errors.append("gosub doel " + str(t) + " bestaat niet")

    # keywords in variabelenamen (rem-commentaar wordt overgeslagen)
    id_re = re.compile(r"[a-zA-Z][a-zA-Z0-9$%]*")
    for num in nums:
        raw = lines[num_to_idx[num]]
        m = re.match(r"\s*\d+(.*)", raw)
        if not m:
            continue
        body = m.group(1)
        clean = re.sub(r'"[^"]*"', '""', body)
        rem_pos = clean.lower().find("rem")
        if rem_pos >= 0:
            clean = clean[:rem_pos]
        for mm in id_re.finditer(clean):
            name = mm.group(0).lower()
            if name in KEYWORDS or name in FUNCS or name in SYS_VARS:
                continue
            for kw in VAR_BREAKERS:
                if kw in name and kw != name:
                    pos = name.find(kw)
                    if pos > 0:
                        warnings.append("variable '" + name + "' contains embedded keyword '" + kw + "'")
                        break

    no_reach = os.environ.get("C64_NO_REACH") == "1"
    if not no_reach and nums:
        reachable = set()
        stack = [nums[0]]
        while stack:
            cur = stack.pop()
            if cur in reachable:
                continue
            reachable.add(cur)
            raw = lines[num_to_idx[cur]]
            m = re.match(r"\s*\d+(.*)", raw)
            if not m:
                continue
            body = m.group(1)
            toks = tokenize(body)
            stmts = split_statements(toks)
            jumped = False
            for st in stmts:
                if not st:
                    continue
                head = st[0]
                if head[0] != "kw":
                    continue
                kw = head[1]
                if kw == "goto" and len(st) >= 2 and st[1][0] == "num":
                    stack.append(int(st[1][1]))
                    jumped = True
                if kw == "gosub" and len(st) >= 2 and st[1][0] == "num":
                    stack.append(int(st[1][1]))
                if kw == "then" and len(st) >= 2 and st[1][0] == "num":
                    stack.append(int(st[1][1]))
                    jumped = True
                if kw == "on":
                    for gi in range(1, len(st)):
                        if st[gi][0] == "kw" and st[gi][1] in ("goto", "gosub"):
                            for ti in range(gi + 1, len(st)):
                                if st[ti][0] == "num":
                                    stack.append(int(st[ti][1]))
                            break
            if not jumped:
                idx = nums.index(cur)
                if idx + 1 < len(nums):
                    stack.append(nums[idx + 1])
        for num in nums:
            if num not in reachable:
                warnings.append("line " + str(num) + ": unreachable line")

    print("=== c64 syntax checker ===")
    print("file: " + path)
    print("errors: " + str(len(errors)))
    for e in errors:
        print("  ERROR  " + e)
    print("warnings: " + str(len(warnings)))
    for w in warnings:
        print("  WARN   " + w)
    if errors:
        sys.exit(1)
    print("ok: 0 errors")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("gebruik: python c64_syntax_checker.py bron.bas")
        sys.exit(2)
    check_file(sys.argv[1])