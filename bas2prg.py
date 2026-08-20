#!/usr/bin/env python3
"""bas2prg.py - Converteer C64 BASIC V2 broncode naar een .prg bestand.

Volgt de werkwijze uit C64_BASIC_SKILL.md:
  - tokentabel in hoofdletters, hoofdlettergevoelig
  - invert_case=True (CLI: -i) is VERPLICHT bij kleine-letterbron
  - operatoren worden altijd getokeniseerd (§2.4 fix is ingebouwd)
  - rem: rest van de regel is commentaar, letterlijk opgeslagen

Gebruik:
  python bas2prg.py programma.bas -o programma.prg -i
"""
import sys

# (keyword_uppercase, token_byte), volgens §3.1
TOKENS = [
    ("INPUT#", 0x84), ("PRINT#", 0x98), ("TAB(", 0xa3), ("SPC(", 0xa6),
    ("LEFT$", 0xc8), ("RIGHT$", 0xc9), ("MID$", 0xca),
    ("END", 0x80), ("FOR", 0x81), ("NEXT", 0x82), ("DATA", 0x83),
    ("INPUT", 0x85), ("DIM", 0x86), ("READ", 0x87), ("LET", 0x88),
    ("GOTO", 0x89), ("RUN", 0x8a), ("IF", 0x8b), ("RESTORE", 0x8c),
    ("GOSUB", 0x8d), ("RETURN", 0x8e), ("REM", 0x8f), ("STOP", 0x90),
    ("ON", 0x91), ("WAIT", 0x92), ("LOAD", 0x93), ("SAVE", 0x94),
    ("VERIFY", 0x95), ("DEF", 0x96), ("POKE", 0x97), ("PRINT", 0x99),
    ("CONT", 0x9a), ("LIST", 0x9b), ("CLR", 0x9c), ("CMD", 0x9d),
    ("SYS", 0x9e), ("OPEN", 0x9f), ("CLOSE", 0xa0), ("GET", 0xa1),
    ("NEW", 0xa2), ("TO", 0xa4), ("FN", 0xa5), ("THEN", 0xa7),
    ("NOT", 0xa8), ("STEP", 0xa9), ("AND", 0xaf), ("OR", 0xb0),
    ("SGN", 0xb4), ("INT", 0xb5), ("ABS", 0xb6), ("USR", 0xb7),
    ("FRE", 0xb8), ("POS", 0xb9), ("SQR", 0xba), ("RND", 0xbb),
    ("LOG", 0xbc), ("EXP", 0xbd), ("COS", 0xbe), ("SIN", 0xbf),
    ("TAN", 0xc0), ("ATN", 0xc1), ("PEEK", 0xc2), ("LEN", 0xc3),
    ("STR$", 0xc4), ("VAL", 0xc5), ("ASC", 0xc6), ("CHR$", 0xc7),
    ("GO", 0xcb), ("PI", 0xff),
    ("+", 0xaa), ("-", 0xab), ("*", 0xac), ("/", 0xad), ("^", 0xae),
    (">", 0xb1), ("=", 0xb2), ("<", 0xb3),
]
# Sorteer op lengte aflopend voor langste-match
TOKENS.sort(key=lambda t: -len(t[0]))
TOKEN_MAP = {kw: byte for kw, byte in TOKENS}


def swap_case(s):
    out = []
    for ch in s:
        o = ord(ch)
        if 65 <= o <= 90:
            out.append(chr(o + 32))
        elif 97 <= o <= 122:
            out.append(chr(o - 32))
        else:
            out.append(ch)
    return "".join(out)


def is_alnum(ch):
    o = ord(ch)
    return (48 <= o <= 57) or (65 <= o <= 90) or (97 <= o <= 122)


def tokenize_line(line, invert_case):
    if invert_case:
        line = swap_case(line)
    out = bytearray()
    i = 0
    n = len(line)
    in_string = False
    prev_alnum = False
    while i < n:
        ch = line[i]
        if ch == '"':
            in_string = not in_string
            out.append(ord(ch))
            i += 1
            prev_alnum = False
            continue
        if in_string:
            out.append(ord(ch) & 0xFF)
            i += 1
            continue
        # probeer langste keyword match
        matched = False
        for kw, byte in TOKENS:
            if line.startswith(kw, i):
                kw_is_alpha = kw[0].isalpha()
                # §2.4 fix: operatoren (niet-alpha) altijd tokeniseren
                if kw_is_alpha and prev_alnum:
                    continue  # keyword in variabelenaam: niet tokeniseren
                out.append(byte)
                i += len(kw)
                matched = True
                prev_alnum = False
                # rem: rest van de regel is commentaar, letterlijk opslaan
                if kw == "REM":
                    while i < n:
                        out.append(ord(line[i]) & 0xFF)
                        i += 1
                    return bytes(out)
                break
        if matched:
            continue
        out.append(ord(ch) & 0xFF)
        prev_alnum = is_alnum(ch)
        i += 1
    return bytes(out)


def parse_line_number(line):
    i = 0
    n = len(line)
    while i < n and line[i] == " ":
        i += 1
    start = i
    while i < n and line[i].isdigit():
        i += 1
    if i == start:
        return None, line
    num = int(line[start:i])
    rest = line[i:]
    return num, rest


def convert(source, invert_case=False):
    prg = bytearray()
    prg.append(0x01)
    prg.append(0x08)  # load adres 2049
    addr = 2049
    lines = source.splitlines()
    for raw in lines:
        stripped = raw.rstrip("\r")
        if stripped.strip() == "":
            continue
        num, rest = parse_line_number(stripped)
        if num is None:
            continue
        body = tokenize_line(rest, invert_case)
        # line link: next pointer (2) + line number (2) + body + 0
        next_addr = addr + 2 + 2 + len(body) + 1
        prg.append(next_addr & 0xFF)
        prg.append((next_addr >> 8) & 0xFF)
        prg.append(num & 0xFF)
        prg.append((num >> 8) & 0xFF)
        prg.extend(body)
        prg.append(0x00)
        addr = next_addr
    # einde van programma: pointer 0
    prg.append(0x00)
    prg.append(0x00)
    return bytes(prg)


def main():
    args = sys.argv[1:]
    invert = False
    out_path = None
    in_path = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-i":
            invert = True
        elif a == "-o":
            i += 1
            out_path = args[i]
        elif in_path is None:
            in_path = a
        i += 1
    if in_path is None:
        print("gebruik: python bas2prg.py bron.bas -o uit.prg -i")
        sys.exit(1)
    if out_path is None:
        if in_path.lower().endswith(".bas"):
            out_path = in_path[:-4] + ".prg"
        else:
            out_path = in_path + ".prg"
    source = open(in_path, "r", encoding="utf-8").read()
    prg = convert(source, invert_case=invert)
    open(out_path, "wb").write(prg)
    print("geschreven: " + out_path + " (" + str(len(prg)) + " bytes, invert=" + str(invert) + ")")


if __name__ == "__main__":
    main()