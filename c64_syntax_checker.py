#!/usr/bin/env python3
"""c64_syntax_checker_en.py - Syntax checker for C64 BASIC V2 source code.

Follows the checks from C64_BASIC_SKILL.md §2.2:
  - line numbers 0-63999, unique, ascending
  - parenthesis balance, quote balance
  - unknown keywords
  - if without then
  - for/next pairing
  - goto/gosub targets
  - on ... goto/gosub lists
  - keywords embedded in variable names (rem comments are skipped)
  - forbidden keywords from other dialects (§3.2: else, while, mod, cls, ...)
  - uppercase letters in code (§1 rule 1: bas2prg -i would break the keywords)
  - reachability (optional, disabled with C64_NO_REACH=1)

Usage:
  python c64_syntax_checker_en.py program.bas
  python c64_syntax_checker_en.py program.bas --json
  C64_NO_REACH=1 python c64_syntax_checker_en.py program.bas

Exit codes: 0 = no errors, 1 = errors found, 2 = usage error / file unreadable.
"""
import json
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
# §3.2: keywords from BASIC 3.5/7.0, QuickBASIC etc. that do not exist in V2
FORBIDDEN = {
    "else", "elseif", "while", "wend", "do", "loop", "repeat", "until",
    "select", "case", "sub", "function", "procedure", "local", "const",
    "cls", "locate", "color", "sound", "play", "vol", "draw", "circle",
    "box", "paint", "char", "graphic", "sprite", "movspr", "sshape",
    "gshape", "scnclr", "window", "trap", "resume", "begin", "bend", "key",
    "fast", "slow", "bank", "bload", "bsave", "dload", "dsave", "dopen",
    "dclose", "directory", "header", "scratch", "rename", "collect", "copy",
    "concat", "append", "record", "getkey", "instr", "string$", "mod",
    "hex$", "dec", "bin$", "using", "pudef", "auto", "renumber", "delete",
    "help", "tron", "troff", "rreg", "sqrt",
}
OPERAND_TYPES = {"num", "id", "str"}
# Forbidden words that are functions elsewhere; others followed by "(" are arrays
FORBIDDEN_FUNCS = {"instr", "dec", "hex$", "bin$", "string$", "sqrt"}


def forbidden_keywords(st):
    """Return the §3.2 keywords used as keywords in one statement.

    Most of these words are legal V2 variable names (do=5, key(3)=1), so a
    word only counts when it is used the way the other dialect uses it.
    """
    for k, t in enumerate(st):
        if t == ("kw", "rem"):
            st = st[:k]
            break
    found = []
    for k, (ty, tx) in enumerate(st):
        if ty != "id" or tx not in FORBIDDEN:
            continue
        prev = st[k - 1] if k > 0 else None
        nxt = st[k + 1] if k + 1 < len(st) else None
        if nxt == ("sym", "="):
            continue  # assignment to (or comparison with) a variable of that name
        at_head = prev is None or prev == ("kw", "then")
        if tx == "else":
            found.append(tx)
        elif tx == "mod":
            if prev and (prev[0] in OPERAND_TYPES or prev == ("punct", ")")) and \
                    nxt and (nxt[0] in OPERAND_TYPES or nxt == ("punct", "(")):
                found.append(tx)
        elif tx in ("sub", "function") and prev == ("kw", "end"):
            found.append("end " + tx)
        elif tx == "using" and prev == ("kw", "print"):
            found.append("print using")
        elif nxt == ("punct", "("):
            if tx in FORBIDDEN_FUNCS and not at_head:
                found.append(tx)  # function call such as instr(...), hex$(...)
        elif at_head and nxt != ("punct", "("):
            found.append(tx)  # statement such as cls, color 0,2, do, loop
    return found


def if_jump_targets(st):
    """Line numbers an if statement can jump to: 'then 100', 'then goto 100', 'goto 100'."""
    targets = []
    for k in range(len(st) - 1):
        if st[k] in (("kw", "then"), ("kw", "goto")) and st[k + 1][0] == "num":
            targets.append(int(st[k + 1][1]))
    return targets


def case_problems(body):
    """Return (uppercase in code, uppercase inside a string) for one line body.

    Text after rem is ignored: it is stored literally and never executed.
    """
    in_string = False
    upper_code = upper_string = False
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == '"':
            in_string = not in_string
        elif not in_string and body[i:i + 3].lower() == "rem":
            break
        elif "A" <= ch <= "Z":
            if in_string:
                upper_string = True
            else:
                upper_code = True
        i += 1
    return upper_code, upper_string


def tokenize(line):
    """Return list of (type, text): 'str', 'num', 'kw', 'id', 'sym', 'punct'."""
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
    """Split on ':' but not within parentheses or strings."""
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
            errors.append("line " + str(idx + 1) + ": no line number")
            continue
        num = int(m.group(1))
        if num < 0 or num > 63999:
            errors.append("line " + str(num) + ": line number out of range 0-63999")
        if num in num_to_idx:
            errors.append("line " + str(num) + ": duplicate line number")
        nums.append(num)
        num_to_idx[num] = idx

    for a in range(1, len(nums)):
        if nums[a] <= nums[a - 1]:
            errors.append("line " + str(nums[a]) + ": line number not ascending")

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
            warnings.append("line " + str(num) + ": longer than 80 characters")
        q = body.count('"')
        if q % 2 != 0:
            errors.append("line " + str(num) + ": odd number of quotes")
        toks = tokenize(body)
        depth = 0
        for ty, tx in toks:
            if ty == "punct" and tx == "(":
                depth += 1
            elif ty == "punct" and tx == ")":
                depth -= 1
                if depth < 0:
                    errors.append("line " + str(num) + ": closing parenthesis without opening")
                    depth = 0
        if depth != 0:
            errors.append("line " + str(num) + ": unbalanced parentheses")

        upper_code, upper_string = case_problems(body)
        if upper_code:
            errors.append("line " + str(num) + ": uppercase letters in code - write the source in lowercase "
                          "(bas2prg -i flips the case, keywords would not be tokenized)")
        if upper_string:
            warnings.append("line " + str(num) + ": uppercase letters in a string appear as PETSCII graphics characters")

        stmts = split_statements(toks)
        for st in stmts:
            if not st:
                continue
            for word in forbidden_keywords(st):
                errors.append("line " + str(num) + ": '" + word + "' does not exist in BASIC V2 (skill §3.2)")
            head = st[0]
            if head[0] != "kw":
                continue
            kw = head[1]
            if kw == "if":
                has_then = any(t[0] == "kw" and t[1] == "then" for t in st)
                if not has_then:
                    errors.append("line " + str(num) + ": if without then")
                for target in if_jump_targets(st):
                    for_targets.add(target)
            if kw == "for":
                if len(st) < 2 or st[1][0] != "id":
                    errors.append("line " + str(num) + ": for without variable")
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
                    errors.append("line " + str(num) + ": goto without target")
            if kw == "gosub":
                if len(st) >= 2 and st[1][0] == "num":
                    gosub_targets.add(int(st[1][1]))
                else:
                    errors.append("line " + str(num) + ": gosub without target")
            if kw == "on":
                gidx = None
                for gi in range(1, len(st)):
                    if st[gi][0] == "kw" and st[gi][1] in ("goto", "gosub"):
                        gidx = gi
                        break
                if gidx is None:
                    errors.append("line " + str(num) + ": on without goto/gosub")
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
            errors.append("line " + str(ln) + ": for without next (" + v + ")")
    for v, ln in next_raw.items():
        if v == "":
            continue
        if v not in for_raw:
            errors.append("line " + str(ln) + ": next without for (" + v + ")")

    for t in for_targets:
        if t not in num_to_idx:
            errors.append("goto/then target " + str(t) + " does not exist")
    for t in gosub_targets:
        if t not in num_to_idx:
            errors.append("gosub target " + str(t) + " does not exist")

    # keywords embedded in variable names (rem comments are skipped)
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
            if cur in reachable or cur not in num_to_idx:  # missing targets are reported above
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
            conditional = False  # after an if, the rest of the line may be skipped
            for st in stmts:
                if not st:
                    continue
                head = st[0]
                if head[0] != "kw":
                    continue
                kw = head[1]
                if kw == "if":
                    conditional = True
                    stack.extend(if_jump_targets(st))
                if kw == "goto" and len(st) >= 2 and st[1][0] == "num":
                    stack.append(int(st[1][1]))
                    if not conditional:
                        jumped = True
                if kw == "gosub" and len(st) >= 2 and st[1][0] == "num":
                    stack.append(int(st[1][1]))
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

    return errors, warnings


def to_issue(severity, text):
    m = re.match(r"line (\d+): (.*)", text)
    if m:
        return {"line": int(m.group(1)), "severity": severity, "message": m.group(2)}
    return {"line": None, "severity": severity, "message": text}


def main(argv):
    args = [a for a in argv[1:] if a != "--json"]
    want_json = "--json" in argv[1:]
    if len(args) != 1:
        print("usage: python c64_syntax_checker_en.py source.bas [--json]")
        return 2
    path = args[0]
    try:
        errors, warnings = check_file(path)
    except (OSError, UnicodeDecodeError) as exc:
        print("ERROR: cannot read " + path + ": " + str(exc), file=sys.stderr)
        return 2

    if want_json:
        print(json.dumps({
            "file": path,
            "errors": len(errors),
            "warnings": len(warnings),
            "issues": [to_issue("ERROR", e) for e in errors] + [to_issue("WARN", w) for w in warnings],
        }, indent=2))
        return 1 if errors else 0

    print("=== c64 syntax checker ===")
    print("file: " + path)
    print("errors: " + str(len(errors)))
    for e in errors:
        print("  ERROR  " + e)
    print("warnings: " + str(len(warnings)))
    for w in warnings:
        print("  WARN   " + w)
    if errors:
        return 1
    print("ok: 0 errors")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))