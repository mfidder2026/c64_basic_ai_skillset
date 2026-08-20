---
name: c64-basic
description: Complete instruction manual for writing correct Commodore 64 BASIC V2 code — syntax, tokenizer, PETSCII, screen, color, sprites, SID sound, joystick, files, performance and verification. Always use this document whenever code is written, reviewed or debugged for a real C64 or a C64 emulator (VICE).
---

# C64 BASIC V2 — Skill for the AI Developer

This document is the **single source of truth** for Commodore 64 BASIC V2 code.
Do not deviate from it. Do not invent statements. Do not use knowledge from
other BASIC dialects.

Target platform: **real Commodore 64 / VICE, Commodore BASIC V2, PAL.**

---

## 0. Work order — follow this on EVERY assignment

1. Read §1 (the hard rules) before you write a single line of code.
2. Write the code according to the patterns in §4 through §11.
3. Run through the checklist in §13.
4. Run the syntax checker (§2.2). Zero ERRORs is mandatory.
5. Compile with `invert_case=True` (§2.3). This is **not optional**.
6. Deliver code + a brief explanation. No assumptions, no "approximately".

If something cannot be done in BASIC V2, **say so explicitly** and offer `poke`,
`peek` or `sys` with a concrete address. Never invent a command.

---

## 1. The hard rules

These twelve rules together cause ~90% of all errors. Never break them.

| # | Rule | Why |
|---|---|---|
| 1 | **Write source code in lowercase** | The conversion tool flips the case. Lowercase letters in the source become normal, readable letters on the C64. Uppercase letters become PETSCII graphics characters. |
| 2 | **Every line has a line number**, in steps of 10 | BASIC V2 has no labels. Steps of 10 leave room to insert lines. |
| 3 | **Line numbers strictly ascending** in the source file | The PRG is a linked list. Sorted incorrectly = corrupt list = `?syntax error`. |
| 4 | **Only the first 2 characters of a variable name count** | `score` and `scene` are both `sc` — the same variable. |
| 5 | **No BASIC keyword anywhere inside a variable name** | The tokenizer matches keywords at any position: `total` → `to`+`tal`. |
| 6 | **Lines maximum 80 characters** (2 screen lines of 40) | Longer cannot be typed or edited on a real C64. |
| 7 | **No `else`, `while`, `wend`, `do`, `loop`, `repeat`, `until`, `select`, `case`, `cls`, `locate`, `color`, `sound`, `sprite`, `sub`, `function`** | Do not exist in BASIC V2. |
| 8 | **No abbreviations** (`?`, `pO`, `gO`) in the source | Those are input shortcuts of the C64 editor, not file syntax. The tokenizer does not recognize them. |
| 9 | **`print` uses PETSCII codes, `poke` to screen memory uses screen codes** | Two different tables. `print chr$(65)` = "a", `poke 1024,65` = a graphics character. |
| 10 | **Every `for` has exactly one `next`; every `gosub` has a `return`** | Otherwise `?next without for` / stack corruption. |
| 11 | **Every `goto`/`gosub` target must exist** | Otherwise `?undef'd statement error`. |
| 12 | **`poke` values are 0–255, addresses 0–65535** | Out of range = `?illegal quantity error`. |

Reserved system variables you never use as your own name:
`st`, `ti`, `ti$`.

---

## 2. Toolchain and verification

### 2.1 File format

Plain text, one BASIC line per text line, UTF-8/ASCII, lowercase,
extension `.bas`. No tabs. No blank lines between code (allowed, skipped,
but keep it clean).

### 2.2 Syntax checker — mandatory before delivery

```bash
python c64_syntax_checker.py program.bas
C64_NO_REACH=1 python c64_syntax_checker.py program.bas   # without reachability noise
python c64_syntax_checker.py program.bas --json           # machine-readable
```

The checker validates: line numbers (0–63999, unique, ascending), quotes,
parentheses, unknown keywords, `if` without `then`, `for`/`next` pairing,
`goto`/`gosub` targets, `on ... goto/gosub` lists, expressions,
keywords in variable names and reachability.

**Requirement: 0 ERRORs.** Assess WARNINGs with judgment — see below.

#### Known false positives of the checker

These warnings are incorrect. **Do not rewrite working code for them.**

| Warning | When | Why incorrect |
|---|---|---|
| `Unreachable line` on `data` lines | `data` is after `end` | `data` is read by `read`, not executed. This is the correct location. |
| `Unreachable line` after `if ... then <linenum>` | always | The checker sees the `if` as an unconditional jump and loses the fall-through path. |
| `Unreachable line` after `if ... then ... : end` | always | Same: the `end` on the conditional branch makes the whole line "terminating". |
| `Unreachable line` on the 2nd through last target line of `on ... goto` | always | The checker only traces a path to the first target in the list. |

In those cases set `C64_NO_REACH=1` and assess the rest.

> **Tool bug:** the CLI flags `--no-reach` and `--reach=` are read in `main()`
> but never passed to `check_file()`. Only the environment variables
> `C64_NO_REACH` and `C64_REACH_MODE` work.

#### Warnings you ALWAYS resolve

- `Variable 'x' contains embedded keyword 'y'` → rename the variable. Always.
- `NEXT variable ... does not match FOR variable ...` → make them match.
- `GOTO/GOSUB target line N does not exist` → add or correct the target line.

### 2.3 Compiling to PRG — `invert_case` is mandatory

```python
from bas2prg import Bas2Prg

source = open('program.bas', 'r').read()
prg = Bas2Prg(invert_case=True).convert(source)   # <-- mandatory with lowercase
open('program.prg', 'wb').write(prg)
```

CLI equivalent:

```bash
python bas2prg.py program.bas -o program.prg -i
```

**Why this is mandatory.** The token table in `bas2prg.py` is in
uppercase and the comparison is case-sensitive. Without `-i` a lowercase
source is **not tokenized at all**:

```text
without -i:  10 print chr$(147)  ->  20 70 72 69 6e 74 ...   (literal "print")
with    -i:  10 print chr$(147)  ->  20 99 20 c7 28 ...     ([PRINT] [CHR$] ( )
```

The result without `-i` is a PRG that gives `?syntax error` on the C64
or appears as graphical gibberish on screen. This is one of the most
common causes of "the AI writes good code but it doesn't work".

> The code example in `SKILLS_BASIC.md` (`Bas2Prg().convert(source)`)
> is missing this flag and produces broken PRGs. Always use the form above.

### 2.4 Open bug in `bas2prg.py` — operators

The patch against keywords-in-variable-names also blocks tokenization of
operators when the previous character is alphanumeric:

```text
10 a=5        ->  A  =(raw $3d)  5      WRONG, C64 expects token $b2
10 a = 5      ->  A  [=tok]      5      good (thanks to the spaces)
10 i=i+1      ->  I  =  I  +  1         WRONG, two broken operators
```

C64 BASIC requires the token bytes `$aa`–`$b3` for `+ - * / ^ and or > = <`.
Raw ASCII gives `?syntax error` on execution.

**Fix in `_tokenize_line()`** — add just before the existing
`if token_val is not None and not in_var_name:`:

```python
# Operator tokens (+ - * / ^ > = <) must ALWAYS be tokenized,
# even directly after a variable name.
if token_val is not None and not TOKENS[token_val - 128][0].isalpha():
    in_var_name = False
```

Verified: after this patch operators are tokenized correctly and
the protection against keywords in variable names remains intact
(`total` stays untokenized, `=` becomes `$b2`).

**As long as this patch is not applied:** put spaces around every operator
(`10 a = 5`, `10 i = i + 1`). That costs line length, so patching is
strongly preferred.

### 2.5 Testing

```bash
x64sc program.prg          # VICE
```

Or on the C64 itself: `load "program",8,1` followed by `run`.

### 2.6 Pitfall — apply_diff and the equals-sign separator

The apply_diff tool (search/replace) uses a line of six
equals signs as the separator marker between the SEARCH block and the
REPLACE block. If the content of a SEARCH or REPLACE block itself
contains a line consisting solely of six (or more) equals signs, or a
line that starts with them, the parser thinks the section ends there.
The result is an error message pointing to a special
marker in the diff content.

This happens in practice when you try to edit BASIC source code with a
`rem` comment containing a row of equals signs (for example a separator
bar in a `rem` line), or when a Python function contains a comment with
six equals signs. A text string containing six or more equals signs can
also mislead the parser, because the marker is a substring.

Solutions, in order of preference:

1. Escape the marker. Place a backslash before the problem line in
   the SEARCH block. This only works in the SEARCH section; in the
   REPLACE section the literal text may stand as long as it is not
   read as a section separator.
2. Rewrite the source so the problem line is no longer a bare row
   of equals signs. Replace a `rem` separator bar of
   equals signs with dashes: `rem dashes title dashes` instead
   of a bar of equals signs. This is consistent with the
   style in this document and prevents the conflicts entirely.
3. Rewrite the entire file with write-to-file instead of
   apply-diff, when the patch is too complex or contains multiple
   problem lines. That is slower but always safe.

Preference: use dashes instead of
equals signs as a separator bar in `rem` comments. That avoids the
apply-diff conflicts and remains readable on the C64.

---

## 3. Language reference

### 3.1 Complete token table (this is BASIC V2, nothing else exists)

Statements and functions, with their token byte:

| Byte | Keyword | Byte | Keyword | Byte | Keyword | Byte | Keyword |
|---|---|---|---|---|---|---|---|
| $80 | `end` | $92 | `wait` | $a4 | `to` | $b6 | `abs` |
| $81 | `for` | $93 | `load` | $a5 | `fn` | $b7 | `usr` |
| $82 | `next` | $94 | `save` | $a6 | `spc(` | $b8 | `fre` |
| $83 | `data` | $95 | `verify` | $a7 | `then` | $b9 | `pos` |
| $84 | `input#` | $96 | `def` | $a8 | `not` | $ba | `sqr` |
| $85 | `input` | $97 | `poke` | $a9 | `step` | $bb | `rnd` |
| $86 | `dim` | $98 | `print#` | $aa | `+` | $bc | `log` |
| $87 | `read` | $99 | `print` | $ab | `-` | $bd | `exp` |
| $88 | `let` | $9a | `cont` | $ac | `*` | $be | `cos` |
| $89 | `goto` | $9b | `list` | $ad | `/` | $bf | `sin` |
| $8a | `run` | $9c | `clr` | $ae | `^` | $c0 | `tan` |
| $8b | `if` | $9d | `cmd` | $af | `and` | $c1 | `atn` |
| $8c | `restore` | $9e | `sys` | $b0 | `or` | $c2 | `peek` |
| $8d | `gosub` | $9f | `open` | $b1 | `>` | $c3 | `len` |
| $8e | `return` | $a0 | `close` | $b2 | `=` | $c4 | `str$` |
| $8f | `rem` | $a1 | `get` | $b3 | `<` | $c5 | `val` |
| $90 | `stop` | $a2 | `new` | $b4 | `sgn` | $c6 | `asc` |
| $91 | `on` | $a3 | `tab(` | $b5 | `int` | $c7 | `chr$` |
| $c8 | `left$` | $c9 | `right$` | $ca | `mid$` | $cb | `go` |
| $ff | `pi` | | | | | | |

Also available: `get#` (= `get` + `#`), and the system variables
`st`, `ti`, `ti$` (no tokens, but reserved names).

`$cc`–`$fe` are unused. Anything not listed above does not exist.

### 3.2 Forbidden — does NOT exist in BASIC V2

Never use, in any form:

```text
else      elseif    while     wend      do        loop
repeat    until     select    case      sub       end sub
function  end function        procedure local     const
cls       locate    color     sound     play      vol
draw      circle    box       paint     char      graphic
sprite    movspr    sshape    gshape    scnclr    window
trap      resume    begin     bend      key       fast/slow
bank      bload     bsave     dload     dsave     dopen/dclose
directory header    scratch   rename    collect   copy
concat    append    record    getkey    instr     string$
mod       hex$      dec       bin$      print using          pudef
auto      renumber  delete    help      tron      troff      rreg
```

Much of this comes from **BASIC 3.5 / 7.0 (C16, Plus/4, C128)**, QuickBASIC or
GW-BASIC. On a C64 they give `?syntax error`.

Missing language constructs and their BASIC V2 solution:

| What you want | Solution in V2 |
|---|---|
| `if ... else ...` | Two separate `if` lines with complementary conditions |
| `while c ... wend` | `100 if not c then 200` … `190 goto 100` … `200 rem` |
| `do ... loop until c` | `100 rem` … `190 if not c then 100` |
| named subroutine | `gosub <linenum>` + `rem` header above the routine |
| local variables | Do not exist. Reserve names per module (see §3.4) |
| `cls` | `print chr$(147)` |
| `locate x,y` | `poke 781,y:poke 782,x:poke 783,0:sys 65520` (kernal plot) |
| exception handling | Does not exist. Validate input yourself |
| integer division | `int(a/b)` |
| modulo | `a-int(a/b)*b` |

### 3.3 Lines, line numbers and statements

- Line number range: **0 through 63999**. Use steps of 10.
- Multiple statements per line separated by `:` — allowed and often faster.
- Line maximum **80 characters** including the line number.
- A `?syntax error` on a line with colons is rarely caused by the
  colons. Check in this order:
  1. variable name with a keyword inside;
  2. variables colliding on the first 2 characters;
  3. missing parenthesis or comma;
  4. function with the wrong number of arguments;
  5. construct from another BASIC dialect;
  6. `=`/operator not tokenized (see §2.4).

`rem` makes the rest of the line a comment — also after a `:`. So always
put `rem` as the last statement on a line.

### 3.4 Variables

**Two-character rule.** Only the first two significant characters
distinguish variables. More characters are allowed but do not count.

```basic
10 rem wrong: score and scene are the same variable "sc"
20 score=10
30 scene=20
40 print score
```

Therefore work with a **name register** at the top of the program:

```basic
10 rem -- variables --
20 rem v =vic base    sm=screen memory   cm=color memory
30 rem sc=score       lv=lives            px,py=player
40 rem jp=joystick port  i,n,d=loops      a$,k$=text
```

**Keywords in names.** The tokenizer tries to match a keyword at *every*
position in the line. These names are broken:

| Name | Contains | Becomes |
|---|---|---|
| `total` | `to` | `to`+`tal` |
| `score` | `or` | `sc`+`or`+`e` |
| `color` | `or` | same |
| `contact` | `cont` | `cont`+`act` |
| `freq` | `fre` | `fre`+`q` |
| `estep` | `step` | `e`+`step` |
| `before` | `for`,`or` | broken |
| `victory` | `to`,`or` | broken |
| `duration` | `on` | broken |
| `sword` / `password` | `or` | broken |

Safe approach: **one or two letters, optionally followed by a digit**
(`a`, `x1`, `sm`, `p9`). Check every new name against §3.1.

**Types**

| Form | Type | Range | Note |
|---|---|---|---|
| `a` | floating point | ±2.9E-39 … ±1.7E38, ~9 digits | default, fastest in expressions |
| `a%` | integer | −32768 … 32767 | only saves memory in arrays; slower in expressions |
| `a$` | string | 0 … 255 characters | `$` is part of the name |

`a`, `a%` and `a$` are **three different variables**. That is allowed.

**Arrays**

```basic
10 dim a(20)          : rem indices 0..20, so 21 elements
20 dim b$(9),c%(4,4)  : rem multiple arrays in one dim
```

- Without `dim` an array automatically gets indices 0..10.
- Dimensioning an array twice gives `?redim'd array error`.
- `clr` clears all variables and arrays; the program remains in memory.

**User-defined functions**

```basic
10 def fn r(x)=int(rnd(1)*x)+1
20 print fn r(6)
```

One numeric argument, one expression, no strings. The function name also
falls under the two-character rule.

### 3.5 Numbers and expressions

- Operator precedence: `^` → unary `-` → `*` `/` → `+` `-` → comparisons →
  `not` → `and` → `or`. Use parentheses when in doubt.
- Comparisons yield **−1 (true)** or **0 (false)**. That is useful:
  `x=x+(k=1)-(k=2)` moves `x` without `if`.
- `and`/`or`/`not` are **bitwise** on 16-bit integers, not purely logical.
  Therefore they work both for conditions and for bitmasks.
- Scientific notation: `1.5e3`.
- `pi` is a constant (on the C64 the π symbol; in text files you write `pi`).

### 3.6 Built-in functions

| Function | Returns | Note |
|---|---|---|
| `abs(x)` | absolute value | |
| `int(x)` | round down | `int(-3.2)` = −4 |
| `sgn(x)` | −1, 0 or 1 | |
| `sqr(x)` | square root | `x>=0` |
| `rnd(x)` | 0 ≤ r < 1 | `rnd(1)` sequence, `rnd(0)` from timer, `rnd(-n)` seed |
| `sin/cos/tan/atn(x)` | radians | |
| `exp(x)` / `log(x)` | e-power / natural log | `log(x)` requires `x>0` |
| `len(a$)` | length | |
| `left$(a$,n)` / `right$(a$,n)` | substring | |
| `mid$(a$,p,n)` | substring from position `p` (1-based) | `n` optional |
| `asc(a$)` | PETSCII code of first character | empty string = `?illegal quantity` |
| `chr$(n)` | character for PETSCII code | |
| `str$(x)` | number → string | gets a leading space or `-` |
| `val(a$)` | string → number | non-numeric = 0 |
| `peek(a)` | byte at address | |
| `pos(0)` | current cursor column | |
| `fre(0)` | free BASIC memory | above 32767 negative: `fre(0)-65536*(fre(0)<0)` |
| `usr(x)` | machine code routine via vector 785/786 | |
| `tab(n)` / `spc(n)` | only inside `print` | |

### 3.7 print — formatting

```basic
10 print "a";"b"        : rem concatenated
20 print "a","b"        : rem b starts in the next column of 10
30 print "no newline";: rem trailing ; suppresses the line break
40 print                : rem blank line
50 print "value:";x    : rem numbers get a space before and after
```

Printing numbers with a leading space (room for the minus sign) and a
trailing space. If you do not want that, use
`a$=str$(x):print right$(a$,len(a$)-1)`.

---

## 4. Control flow — the fixed patterns

### 4.1 if / then

```basic
10 input "number";x
20 if x>10 then print "greater than 10"
30 if x<=10 then print "10 or less"
40 end
```

- `then <linenum>` is a jump; `then goto <n>` is the same but longer.
- Everything after `then` on the same line belongs to the true branch:
  `if a=1 then b=2:c=3` — `c=3` is executed **only** if `a=1`.
  This is the main pitfall when reconstructing `else`.
- There is no `else`. Write two `if` lines with complementary conditions.

### 4.2 Loops

```basic
10 for i=1 to 10:print i:next i
20 for i=10 to 1 step -1:print i:next i
30 for j=0 to 7:for k=0 to 7:print j,k:next k:next j
```

- `next` without a variable is slightly faster, but `next i` is more readable
  and is checked by the checker. Use `next i`.
- `next i,j` closes two loops at once (innermost first).
- A `for` loop **always runs at least once** — the test is at `next`.
- Never jump into or out of a `for` loop with `goto`: the stack fills up
  (`?out of memory error`).

Conditional loop (replaces `while`):

```basic
100 if a>=10 then 200
110 a=a+1
120 goto 100
200 rem continue
```

### 4.3 gosub / return

```basic
10 gosub 1000
20 print "back"
30 end
1000 rem subroutine
1010 return
```

- Always end the main program with `end` before the subroutine block,
  otherwise execution falls into the subroutine and
  `?return without gosub error` follows.
- Nesting is limited by the stack (~23 levels). Keep it shallow.
- Give subroutines fixed blocks: 1000, 2000, 3000, …

### 4.4 on ... goto / gosub

```basic
10 input "choose 1, 2 or 3";k
20 on k goto 100,200,300
30 goto 10
100 print "one":goto 10
200 print "two":goto 10
300 print "three":end
```

At `k=0` or `k>` number of targets, execution falls through to the next
line. Always catch that (line 30 above).

### 4.5 data / read / restore

```basic
10 for i=1 to 3:read n$,w:print n$;w:next i
20 end
100 data "red",2,"green",5,"blue",6
```

- `data` may be anywhere; conventionally at the end, after `end`.
- **Always put text in `data` between double quotes.** Without quotes
  BASIC tokenizes keywords inside the text: `data one` becomes `data` + token(`on`) + `e`.
- `restore` resets the read pointer to the first `data` line. BASIC V2
  **cannot** restore to a specific line.
- Reading too many times gives `?out of data error`. End with a sentinel
  (for example `-1`) or count exactly.

### 4.5a RESTORE to a specific line — workaround

BASIC V2 only has `restore` (without a line number). If you need to read
the same `data` block multiple times (for example a melody at the
intro and at winning), load the `data` into arrays once and
play from the arrays:

```basic
10 dim mh(6),ml(6)
20 for i = 1 to 6:read mh(i),ml(i):next i
30 end
100 data 17,103,19,137,21,237,23,59,26,19,34,206
200 rem -- play melody --
210 for q = 1 to 6
220 poke s+1,mh(q):poke s,ml(q)
230 poke s+4,17
240 for d = 1 to 120:next d
250 poke s+4,16
260 next q
270 return
```

Advantages: no `restore` needed, no `?out of data error` on repeated
playing, and the melody can be called unlimited times.

### 4.6 end, stop, cont, clr, new

| Command | Effect |
|---|---|
| `end` | Clean stop, no message |
| `stop` | Break with `break in <line>`; resume with `cont` |
| `cont` | Resumes after `stop` or run/stop, provided the program was not modified |
| `clr` | Clears all variables, arrays and the gosub/for stack; program remains |
| `new` | Erases the program from memory |
| `run` | Starts; implicitly does a `clr` |

---

## 5. PETSCII, screen codes and control codes

### 5.1 Two different tables

This is a classic source of errors:

- **`print` and `chr$()` use PETSCII codes.**
- **`poke` to screen memory (1024–2023) uses screen codes.**

`print chr$(65)` shows the letter A. `poke 1024,65` shows a graphics character.
The letter A in screen memory is code **1**.

Conversion PETSCII → screen code:

| PETSCII | Screen code |
|---|---|
| 0–31 | not printable (control codes) |
| 32–63 | same value |
| 64–95 | PETSCII − 64 |
| 96–127 | PETSCII − 32 |
| 128–159 | not printable (control codes) |
| 160–191 | PETSCII − 64 |
| 192–223 | PETSCII − 128 |
| 224–254 | PETSCII − 128 |
| 255 | 94 |

Reverse video: **screen code + 128**.

Commonly used screen codes:

| Code | Character |
|---|---|
| 0 | `@` |
| 1–26 | letters a–z |
| 27–31 | `[` `£` `]` `↑` `←` |
| 32 | space |
| 33–47 | `!` `"` `#` `$` `%` `&` `'` `(` `)` `*` `+` `,` `-` `.` `/` |
| 48–57 | digits 0–9 |
| 58–63 | `:` `;` `<` `=` `>` `?` |
| 64–127 | graphics characters |
| 81 | filled circle (classic "ball") |
| 87 | filled block variant |
| 160 | reverse space (fully filled block) |

Not sure of a screen code? Print the character and read it back:

```basic
10 print chr$(147);"x";
20 print peek(1024)
```

### 5.2 PETSCII control codes for print

| Code | Effect | | Code | Effect |
|---:|---|---|---:|---|
| 5 | white | | 144 | black |
| 8 | shift+commodore off | | 145 | cursor up |
| 9 | shift+commodore on | | 146 | reverse off |
| 13 | return | | 147 | clear screen |
| 14 | lowercase set | | 148 | insert |
| 17 | cursor down | | 149 | brown |
| 18 | reverse on | | 150 | light red |
| 19 | home (cursor top-left) | | 151 | dark gray |
| 20 | delete | | 152 | gray |
| 28 | red | | 153 | light green |
| 29 | cursor right | | 154 | light blue |
| 30 | green | | 155 | light gray |
| 31 | blue | | 156 | purple |
| 129 | orange | | 157 | cursor left |
| 142 | uppercase/graphics set | | 158 | yellow |
| | | | 159 | cyan |

Usage:

```basic
10 print chr$(147);              : rem clear
20 print chr$(19);               : rem home, without clearing
30 print chr$(18);"reverse";chr$(146)
40 print chr$(28);"red text"
50 print chr$(14)                : rem enable lowercase
```

`chr$(19)` (home) instead of `chr$(147)` (clear) is the way to refresh a
score line without flicker.

---

## 6. Screen and color

### 6.1 Core addresses

```text
1024 – 2023    screen memory, 40 x 25 characters (screen codes)
55296 – 56295  color ram, same layout (only bits 0-3)
2040 – 2047    sprite pointers
53280          border color
53281          background color
646            color of newly printed characters
53272          memory setup: character and screen memory
198            keyboard buffer length
650            key repeat (128 = all keys repeat)
```

Position calculation:

```text
screen address = 1024  + x + y*40      with x = 0..39, y = 0..24
color address  = 55296 + x + y*40
```

The offset is identical — calculate it once:

```basic
10 sm=1024:cm=55296
20 o=x+y*40
30 poke sm+o,81:poke cm+o,1
```

### 6.2 Color codes

| Code | Color | Code | Color |
|---:|---|---:|---|
| 0 | black | 8 | orange |
| 1 | white | 9 | brown |
| 2 | red | 10 | light red |
| 3 | cyan | 11 | dark gray |
| 4 | purple | 12 | gray |
| 5 | green | 13 | light green |
| 6 | blue | 14 | light blue |
| 7 | yellow | 15 | light gray |

Startup colors: border 14, background 6, text 14.

```basic
10 poke 53280,0:poke 53281,0:poke 646,1   : rem black with white text
20 print chr$(147)
```

Note the order: `print chr$(147)` fills color ram with the **current**
text color (646). So set 646 before clearing.

### 6.3 Switching character set

```basic
10 print chr$(14)   : rem lowercase + uppercase
20 print chr$(142)  : rem uppercase + graphics characters (default)
30 poke 53272,23    : rem via vic (21=graphics, 23=lowercase)
40 poke 657,128     : rem block shift+commodore
```

### 6.4 Borderless screen and screen shifting

```basic
10 poke 53265,peek(53265) and 247  : rem 24 rows instead of 25
20 poke 53270,peek(53270) and 247  : rem 38 columns
30 poke 53265,peek(53265) or 8     : rem back to 25 rows
```

### 6.5 Fixed screen layout (no scroll)

Text adventures and menus often have a fixed layout: title at the top,
inventory at the bottom, response area in the middle. If you use `print`
on the bottom rows, the screen scrolls and the top
text disappears. Solution: position the cursor explicitly with the KERNAL
PLOT routine before each `print`, so no new lines are added.

```basic
10 rem -- cursor to row r, column 0 --
20 poke 781,r:poke 782,0:poke 783,0:sys 65520
30 print "text on fixed row";
```

| PEEK/POKE address | Function |
|---:|---|
| 781 | row (0–24) |
| 782 | column (0–39) |
| 783 | 0 = absolute position, 1 = relative |

Clearing an area without scrolling — position the cursor on each row
and print spaces with `;` (no return):

```basic
10 for cl = 12 to 19
20 poke 781,cl:poke 782,0:poke 783,0:sys 65520
30 print "                                       ";
40 next cl
```

Example layout for a text adventure:

```text
row  0:   room: <name>              (cyan, chr$(159))
row  2:   <room description>
row  6:   exits: north south
row 10:   command?                  (fixed prompt line)
row 12-19: <response text>           (cleared per command)
row 20:   carrying: lamp key        (green, chr$(30))
row 21:   press a key...            (wait prompt)
```

Setting a color for a line and restoring it:

```basic
10 print chr$(159);"cyan text";chr$(158)
```

`chr$(159)` = cyan, `chr$(158)` = yellow (restore default color).

---

## 7. Sprites

BASIC V2 has **no** sprite commands. Everything goes through `poke`/`peek`
on the VIC-II. Always work with a base address:

```basic
10 v=53248
```

### 7.1 Register overview (offsets from v=53248)

| Offset | Decimal | Function |
|---:|---:|---|
| v+0 … v+15 | 53248–53263 | X and Y position of sprite 0..7 (pairs: `v+2*n`, `v+2*n+1`) |
| v+16 | 53264 | X-coordinate bit 8 per sprite (for X > 255) |
| v+21 | 53269 | Sprite on/off (1 bit per sprite) |
| v+23 | 53271 | Y-expand (double height) |
| v+27 | 53275 | Priority: 1 = sprite behind screen text |
| v+28 | 53276 | Multicolor on/off |
| v+29 | 53277 | X-expand (double width) |
| v+30 | 53278 | Sprite–sprite collision (**reading clears the register**) |
| v+31 | 53279 | Sprite–background collision (**reading clears the register**) |
| v+37 | 53285 | Multicolor 1 (shared by all sprites) |
| v+38 | 53286 | Multicolor 2 (shared by all sprites) |
| v+39 … v+46 | 53287–53294 | Color of sprite 0..7 |

Sprite pointers: **2040 + n** for sprite n (with the standard screen at 1024).

### 7.2 Shape of the sprite data

A sprite is **24 x 21 pixels** = 3 bytes per row x 21 rows = **63 bytes**,
stored in a block of 64 bytes. The pointer value is the block number:

```text
block number = address / 64        address = block number * 64
```

Safe blocks in BASIC **without** relocating memory:

| Block | Address | Note |
|---:|---:|---|
| 11 | 704 | free area 679–767 |
| 13 | 832 | datasette buffer — safe as long as you do not use tape |
| 14 | 896 | same |
| 15 | 960 | same |

Block 12 (768–831) contains system vectors. **Never use.**

More than four sprites? Lower the BASIC upper limit and put the data at 12288:

```basic
10 poke 52,48:poke 56,48:clr   : rem basic-top to $3000 = 12288
20 rem sprite n data at 12288+n*64, pointer value 192+n
```

### 7.3 Creating sprite data

Each row is 3 bytes; each byte is 8 pixels, bit 7 leftmost.

```text
row:   ...####...  ..######..  ..######..
byte:  00111100    00111111    11000000  ...
       = 60        = 63        = 192
```

Standard pattern with `data` + `read` + `poke`:

```basic
10 v=53248:sb=832              : rem sb = sprite base, block 13
20 for i=0 to 62:read d:poke sb+i,d:next i
30 poke 2040,sb/64             : rem pointer = 13
...
900 data 0,127,0,   1,255,192, 3,255,224, 3,231,224
910 data 7,217,240, 7,223,240, 7,217,240, 3,231,224
920 data 3,255,224, 3,255,224, 2,255,160, 1,127,64
930 data 1,62,64,   0,156,128, 0,156,128, 0,73,0
940 data 0,73,0,    0,62,0,    0,62,0,    0,62,0
950 data 0,28,0
```

Count the bytes: **exactly 63**, otherwise the shape shifts or you get
`?out of data error`.

### 7.4 Activating a sprite

```basic
10 v=53248
20 n=0                          : rem sprite number 0..7
30 b=2^n                        : rem bitmask for this sprite
40 poke 2040+n,13               : rem pointer -> block 13 (address 832)
50 poke v+21,peek(v+21) or b    : rem turn on
60 poke v+39+n,1                : rem color white
70 poke v+2*n,160:poke v+2*n+1,120 : rem x=160, y=120
```

**Always preserve existing bits.** To turn off one sprite without
affecting the others:

```basic
100 poke v+21,peek(v+21) and (255-b)
```

The same pattern applies to v+16, v+23, v+27, v+28 and v+29.

### 7.5 Positioning and X > 255

Visible area for a non-expanded sprite:

```text
x: 24 .. 320   (fully visible; 24 = left edge of the screen)
y: 50 .. 229   (fully visible; 50 = top edge)
```

X goes up to 320 and therefore does not fit in one byte. Use the MSB register:

```basic
100 poke v+2*n,x and 255
110 if x>255 then poke v+16,peek(v+16) or b
120 if x<256 then poke v+16,peek(v+16) and (255-b)
130 poke v+2*n+1,y
```

Do not forget line 120 — without the "off" branch the sprite stays stuck
on the right once it has gone past 255 once.

### 7.6 Expand, multicolor, priority

```basic
200 poke v+29,peek(v+29) or b   : rem double width
210 poke v+23,peek(v+23) or b   : rem double height
220 poke v+27,peek(v+27) or b   : rem behind screen text
230 poke v+28,peek(v+28) or b   : rem multicolor on
240 poke v+37,2:poke v+38,7     : rem multicolor 1 = red, 2 = yellow
```

In multicolor mode the bits are read **in pairs**; the sprite is then
12 pixels wide with double-width dots:

| Bit pair | Color |
|---|---|
| 00 | transparent |
| 01 | multicolor 1 (v+37) |
| 10 | own sprite color (v+39+n) |
| 11 | multicolor 2 (v+38) |

### 7.7 Collision detection

The registers v+30 and v+31 **clear themselves on read**. So read them
exactly once per loop into a variable:

```basic
300 c=peek(v+30)                : rem sprite-sprite
310 if (c and 1)<>0 then gosub 900 : rem sprite 0 hit something
320 cb=peek(v+31)               : rem sprite-background
330 if (cb and 1)<>0 then gosub 950
```

In BASIC the loop is so slow that fast sprites can miss collisions.
For games: compare coordinates yourself, that is more reliable:

```basic
400 if abs(x1-x2)<20 and abs(y1-y2)<18 then gosub 900
```

### 7.8 Turning everything off (cleanup)

```basic
500 poke v+21,0:poke v+16,0:poke v+23,0:poke v+29,0
510 poke v+27,0:poke v+28,0
```

---

## 8. Sound — the SID (6581/8580)

BASIC V2 has **no** `sound`, `play` or `vol`. Everything via `poke`.
The SID registers are **write-only** and are **not cleared** on power-up.
So always start by setting all 25 registers to 0.

```basic
10 s=54272
20 for i=0 to 24:poke s+i,0:next i
```

### 8.1 Register overview (offsets from s=54272)

| Offset | Voice 1 | Voice 2 | Voice 3 | Function |
|---:|---:|---:|---:|---|
| +0 / +1 | 0,1 | 7,8 | 14,15 | frequency lo, hi |
| +2 / +3 | 2,3 | 9,10 | 16,17 | pulse width lo, hi (0–4095) |
| +4 | 4 | 11 | 18 | control register (waveform + gate) |
| +5 | 5 | 12 | 19 | attack (bits 4–7) + decay (bits 0–3) |
| +6 | 6 | 13 | 20 | sustain (bits 4–7) + release (bits 0–3) |

Global:

| Offset | Decimal | Function |
|---:|---:|---|
| s+21 | 54293 | filter frequency low (bits 0–2) |
| s+22 | 54294 | filter frequency high (bits 3–10) |
| s+23 | 54295 | filter routing (bits 0–2) + resonance (bits 4–7) |
| s+24 | 54296 | **volume (bits 0–3)** + filter mode (16=lowpass, 32=bandpass, 64=highpass, 128=voice 3 off) |

### 8.2 Control register (waveform + gate)

| Bit | Value | Meaning |
|---:|---:|---|
| 0 | 1 | **gate**: 1 = start attack/decay/sustain, 0 = start release |
| 1 | 2 | sync with voice n−1 |
| 2 | 4 | ring modulation |
| 3 | 8 | test / reset generator |
| 4 | 16 | triangle |
| 5 | 32 | sawtooth |
| 6 | 64 | pulse (requires pulse width!) |
| 7 | 128 | noise |

Practical values:

| Waveform | Note on | Note off |
|---|---:|---:|
| triangle | 17 | 16 |
| sawtooth | 33 | 32 |
| pulse | 65 | 64 |
| noise | 129 | 128 |

Playing a note is always: **gate on → wait → gate off**. Without turning
the gate off again the next note does not retrigger.

### 8.3 ADSR

```text
attack/decay byte  = attack * 16 + decay
sustain/release    = sustain volume * 16 + release
```

Values 0–15. Rough times (attack / decay & release):

| Value | Attack | Decay & Release |
|---:|---|---|
| 0 | 2 ms | 6 ms |
| 1 | 8 ms | 24 ms |
| 2 | 16 ms | 48 ms |
| 4 | 38 ms | 114 ms |
| 6 | 68 ms | 204 ms |
| 8 | 100 ms | 300 ms |
| 9 | 250 ms | 750 ms |
| 11 | 800 ms | 2.4 s |
| 13 | 3 s | 9 s |
| 15 | 8 s | 24 s |

Usable starting values: `poke s+5,9:poke s+6,0` (short pluck),
`poke s+5,0:poke s+6,240` (organ: instant on, full sustain).

### 8.4 Frequency table (PAL)

Formula: `frequency value = hertz * 16777216 / 985248 ≈ hertz * 17.028`
(NTSC: `* 16.405`). Split: `hi = int(w/256)` , `lo = w - hi*256`.

The table below gives **hi,lo** per note and octave. Octave 4 is the
middle octave (a4 = 440 Hz).

| Note | o1 | o2 | o3 | o4 | o5 | o6 |
|---|---|---|---|---|---|---|
| c | 2,45 | 4,90 | 8,180 | 17,103 | 34,206 | 69,156 |
| c# | 2,78 | 4,156 | 9,56 | 18,112 | 36,224 | 73,192 |
| d | 2,113 | 4,226 | 9,196 | 19,137 | 39,17 | 78,35 |
| d# | 2,150 | 5,45 | 10,89 | 20,178 | 41,100 | 82,200 |
| e | 2,190 | 5,123 | 10,247 | 21,237 | 43,218 | 87,180 |
| f | 2,231 | 5,207 | 11,157 | 23,59 | 46,118 | 92,235 |
| f# | 3,20 | 6,39 | 12,78 | 24,156 | 49,57 | 98,114 |
| g | 3,66 | 6,133 | 13,10 | 26,19 | 52,38 | 104,76 |
| g# | 3,116 | 6,232 | 13,208 | 27,160 | 55,64 | 110,128 |
| a | 3,169 | 7,81 | 14,162 | 29,69 | 58,137 | 117,18 |
| a# | 3,224 | 7,193 | 15,129 | 31,2 | 62,4 | 124,8 |
| b | 4,27 | 8,55 | 16,109 | 32,218 | 65,180 | 131,104 |

### 8.5 Working example — melody player

```basic
10 rem sid melody
20 s=54272
30 for i=0 to 24:poke s+i,0:next i
40 poke s+24,15                : rem volume maximum
50 poke s+5,9:poke s+6,0       : rem attack 250ms, decay 6ms
60 read hi,lo,du
70 if hi<0 then poke s+4,0:poke s+24,0:end
80 poke s+1,hi:poke s,lo
90 poke s+4,17                 : rem triangle, gate on
100 for d=1 to du*40:next d
110 poke s+4,16                : rem gate off -> release
120 for d=1 to 40:next d
130 goto 60
900 data 17,103,4, 19,137,4, 21,237,4, 23,59,4
910 data 26,19,4,  29,69,4,  32,218,4, 34,206,8
920 data -1,-1,-1
```

### 8.6 Sound effects

```basic
1000 rem explosion: noise with fast decay
1010 poke s+5,0:poke s+6,9
1020 poke s+1,20:poke s,0
1030 poke s+4,129:for d=1 to 200:next d:poke s+4,128
1040 return
1100 rem siren: sweep frequency up
1110 poke s+5,0:poke s+6,240:poke s+4,33
1120 for f=30 to 80:poke s+1,f:for d=1 to 10:next d:next f
1130 poke s+4,32:return
```

### 8.7 Pitfalls

- Volume (s+24) not set → no sound. Always set it first.
- Pulse waveform without pulse width (s+2/s+3) → silence. Set e.g.
  `poke s+3,8` (= 2048, 50% square wave).
- Registers not cleared at program start → random beeps.
- Gate not turned off → next note does not retrigger.
- At program end: `poke s+24,0` and all gates to 0, otherwise a tone
  keeps sounding.
- BASIC is too slow for tight timing. For real music under a game
  a machine code player via raster interrupt is needed.

---

## 9. Input and timing

### 9.1 Keyboard

```basic
10 input "what is your name";n$      : rem blocks, waits for return
20 get a$                          : rem reads 1 character, does NOT block
30 if a$="" then 20                : rem wait for a key
```

- `input` does not accept commas in the input (they split fields).
  For free text with commas: build your own input routine with `get`.
- `input a,b` reads two values separated by a comma or return.
- `get a$` yields `""` if no key is in the buffer.
- `get a` (numeric) gives `?syntax error` on a non-digit key;
  always use `get a$` and convert with `val()`.

Useful addresses:

| Address | Function |
|---:|---|
| 198 | number of characters in the keyboard buffer; `poke 198,0` clears it |
| 631–640 | the buffer itself |
| 197 | matrix code of the currently pressed key (64 = none) |
| 653 | modifier keys: bit 0 = shift, bit 1 = commodore, bit 2 = ctrl |
| 650 | key repeat: 128 = all keys repeat, 64 = none |
| 808 | stop routine; 239 blocks run/stop and list, 237 restores |

```basic
10 poke 650,128                    : rem all keys repeat
20 poke 198,0                      : rem clear buffer for a clean start
30 print "press a key"
40 wait 198,15                     : rem wait until something is in the buffer
50 get a$
```

Reading multiple keys simultaneously is not possible with `get`. For that
use `peek(197)` (one key) or the joystick.

### 9.1a "Press a key" — pause without scroll

In a game with a fixed screen layout (§6.5) you must not use `print` without
cursor positioning on the bottom rows, because that causes
scroll. Combine KERNAL PLOT with a `get` wait loop:

```basic
10 rem -- wait for key --
20 poke 781,21:poke 782,0:poke 783,0:sys 65520
30 print "press a key...";
40 get a$:if a$ = "" then 40
50 return
```

Important: use `print "...";` with a semicolon (no return) to
prevent the cursor from jumping to the next row and triggering scroll.

This pattern is also suitable for an intro screen that waits until the
player is ready to read:

```basic
10 print "treasure of the ghost castle"
20 print:print "press a key to start"
30 get a$:if a$ = "" then 30
```

### 9.2 Joystick

| Port | Address | Note |
|---:|---:|---|
| 2 | 56320 | **use this** in BASIC |
| 1 | 56321 | shares hardware with the keyboard scan; gives false values |

Bits are **active low**: a 0-bit means pressed.

| Bit | Value | Direction |
|---:|---:|---|
| 0 | 1 | up |
| 1 | 2 | down |
| 2 | 4 | left |
| 3 | 8 | right |
| 4 | 16 | fire button |

```basic
100 j=peek(56320)
110 if (j and 1)=0 then y=y-1
120 if (j and 2)=0 then y=y+1
130 if (j and 4)=0 then x=x-1
140 if (j and 8)=0 then x=x+1
150 if (j and 16)=0 then gosub 500
```

Read `peek(56320)` **once** per loop into a variable — otherwise you get
inconsistent diagonals and the loop is unnecessarily slow.

### 9.3 Timing

```basic
10 print ti$          : rem "hhmmss" since power-on
20 print ti           : rem jiffies, approximately 1/60 second
30 ti$="000000"       : rem reset clock (ti$ is writable, ti is not)
```

Waiting for a fixed time — more accurate than a count loop:

```basic
100 t=ti
110 if ti-t<30 then 110    : rem wait half a second
```

Simple delay (rule of thumb: ~1000 iterations ≈ 1 second):

```basic
200 for d=1 to 500:next d
```

Frame synchronization against flicker during animation:

```basic
300 wait 53265,128         : rem wait until the raster beam is below line 256
```

`wait address,mask1[,mask2]` keeps waiting until
`(peek(address) xor mask2) and mask1 <> 0`. Note: if that condition
is never met, the program hangs and only run/stop+restore helps.

---

## 10. Files and peripherals

```basic
10 open 1,8,2,"data,s,w"    : rem write to disk (seq)
20 print#1,"line 1"
30 close 1
40 open 1,8,2,"data,s,r"    : rem read
50 input#1,a$
60 close 1
```

| Device | Number |
|---|---:|
| datassette | 1 |
| printer | 4 (or 5) |
| disk drive | 8 through 11 |

File types: `s` = sequential, `p` = program, `u` = user, `r` = relative.
Mode: `r` = read, `w` = write, `a` = append.

**Status variable `st`** after every I/O operation:

| Value | Meaning |
|---:|---|
| 0 | ok |
| 64 | end of file reached |
| −128 | device not present |

Reading character by character until the end:

```basic
10 open 1,8,2,"data,s,r"
20 get#1,a$
30 if st<>0 then 60
40 print a$;
50 goto 20
60 close 1:end
```

Reading the drive error channel (always do this after a failed operation):

```basic
10 open 15,8,15
20 input#15,en,em$,et,es
30 print en;em$;et;es
40 close 15
```

Printer:

```basic
10 open 4,4:print#4,"hello printer":close 4
20 open 4,4:cmd 4:list:print#4:close 4   : rem listing to the printer
```

**Always** close every file with `close`. An unclosed file
loses data and blocks the device.

Programs:

```text
save "name",8      load "name",8      verify "name",8
load "name",8,1    (load at the original address, for machine code/data)
```

---

## 11. Performance

BASIC V2 is slow. These measures give the most gain, in order
of effect:

1. **Put variables you use often as the first in the program.**
   BASIC searches variables linearly in order of first assignment.
   ```basic
   10 x=0:y=0:j=0:o=0:v=53248:sm=1024
   ```
2. **Precompute fixed addresses and constants**, outside the loop.
   ```basic
   10 v=53248:se=v+21:sm=1024
   100 poke se,peek(se) or 1
   ```
   instead of `poke 53248+21,peek(53248+21) or 1`.
3. **Put the main loop and frequently used subroutines at low line numbers.**
   A jump back is searched from the beginning of the program.
4. **Multiple statements per line.** Fewer lines = fewer link steps.
5. **No `rem` in a hot loop.** Comment lines cost scan time.
   Put documentation in a header block at the top.
6. **Avoid `a%` integers in calculations.** BASIC always computes internally
   in floating point and converts integers back and forth. Use `%`
   only in large arrays to save memory (2 bytes instead of 5).
7. **Avoid string concatenation in loops.** That causes garbage
   collection and unpredictable pauses.
8. **Use logical expressions instead of `if`** where possible:
   ```basic
   100 x=x+(j and 8)/8-(j and 4)/4
   ```
9. For raster, music and scroll code: **move to 6502 machine code**
   and call with `sys`. Say this explicitly when a requirement in BASIC
   is not feasible.

Checking free memory:

```basic
10 f=fre(0):print f-65536*(f<0)
```

---

## 12. Error messages and diagnosis

| Message | Most common cause |
|---|---|
| `?syntax error` | Keyword in variable name; dialect construct; missing parenthesis/comma; untokenized operator (§2.4); abbreviation like `?` in source; `restore` with line number (§4.5a) |
| `?undef'd statement error` | `goto`/`gosub`/`then <n>` to a non-existent line |
| `?next without for` | `next` without `for`, or jumped out of a loop with `goto` |
| `?return without gosub` | No `end` before the subroutine block |
| `?out of data error` | More `read` than `data`; no end marker |
| `?illegal quantity error` | `poke` value outside 0–255; negative argument to `sqr`/`log`; `mid$` with position 0; `asc("")` |
| `?overflow error` | Number larger than 1.7E38 |
| `?out of memory error` | Program + variables too large; too deep `gosub`/`for` nesting; jumped out of a loop with `goto` |
| `?bad subscript error` | Array index outside the dimensioned size |
| `?redim'd array error` | Same array `dim`'d twice, or used before `dim` |
| `?division by zero error` | Division by 0 |
| `?type mismatch error` | String where a number is expected or vice versa (`a$=5`, `a="x"`) |
| `?string too long error` | String longer than 255 characters |
| `?formula too complex` | Too many nested string expressions; split the line |
| `?can't continue error` | `cont` after a modification or after `end` |
| `?undef'd function error` | `fn` used without `def fn` |
| `?device not present error` | Drive/printer off or wrong device number |
| `?file not found` / `?file open` / `?file not open` | File management; check `open`/`close` |

### Diagnosis route for an unexpected `?syntax error`

1. Look at the **original line**, not a modern rewrite of it.
2. Check every variable name against the token table (§3.1).
3. Check whether two variables collide on the first two characters.
4. Check parentheses and commas.
5. Check that all statements used are in §3.1.
6. Check that the PRG was made with `invert_case=True` (§2.3).
7. Check that operators are tokenized (§2.4).
8. Only then adjust the logic.

Never automatically convert to another BASIC dialect to "bypass" an error.

---

## 13. Verification checklist — run through this before every delivery

**Language**
- [ ] All code in lowercase.
- [ ] Only keywords from the table in §3.1.
- [ ] No `else`, `while`, `do`, `cls`, `locate`, `sprite`, `sound`, etc.
- [ ] No abbreviations (`?`, `pO`) in the source code.

**Lines**
- [ ] Every line has a line number, steps of 10.
- [ ] Line numbers strictly ascending, no duplicates, 0–63999.
- [ ] No line longer than 80 characters.

**Variables**
- [ ] All variables unique in the **first two characters**.
- [ ] No variable name contains a BASIC keyword as a substring.
- [ ] `st`, `ti`, `ti$` not used as your own name.
- [ ] Name register in a `rem` header block at the top.
- [ ] Strings end in `$`, integers in `%`, types not mixed.

**Structure**
- [ ] Every `for` has exactly one matching `next` with the same variable.
- [ ] Never jump into or out of a `for` loop with `goto`.
- [ ] Every `gosub` has a `return`; `end` is before the subroutine block.
- [ ] Every `goto`/`gosub`/`then <n>` target exists.
- [ ] `on ... goto/gosub` has fall-through handling for 0 and too-large values.
- [ ] Number of `read` operations matches the `data`, or there is an end marker.
- [ ] Text in `data` is between double quotes.
- [ ] `restore` has no line number (BASIC V2; §4.5a).
- [ ] Repeatable `data` (melody, maps) is loaded into arrays (§4.5a).
- [ ] `get a$` wait loops use `;` (no return) to prevent scroll (§9.1a).
- [ ] Fixed screen layout uses KERNAL PLOT, no `print` on bottom rows (§6.5).

**Hardware**
- [ ] All `poke` addresses are correct (§14 and the appendix).
- [ ] All `poke` values are between 0 and 255.
- [ ] Bit registers are masked with `or` / `and (255-b)`, existing bits preserved.
- [ ] Sprite data is exactly 63 bytes; pointer = address/64; block 12 not used.
- [ ] X > 255 is handled via register 53264, in both directions.
- [ ] SID: all 25 registers cleared, volume set, gate on and off again.
- [ ] Screen memory gets **screen codes**, `print`/`chr$` gets **PETSCII**.
- [ ] Color ram is set along with poking characters.
- [ ] Collision registers 53278/53279 are read only once per loop.

**Tooling**
- [ ] `c64_syntax_checker.py` gives 0 ERRORs.
- [ ] All WARNINGs are either resolved or a documented false positive (§2.2).
- [ ] PRG built with `invert_case=True` / `-i`.
- [ ] Tested in VICE or on hardware.

**Cleanup**
- [ ] Sprites turned off and SID volume to 0 at program end.
- [ ] All open files closed.

---

## 14. Ready-made templates

All templates below are validated: 0 ERRORs in the syntax checker
and successfully tokenized to PRG.

### 14.1 Basic skeleton

```basic
10 rem ---- title ----
20 rem variables: v=vic sm=screen cm=color
30 gosub 1000
40 gosub 2000
50 end
1000 rem -- initialization --
1010 v=53248:sm=1024:cm=55296
1020 poke 53280,0:poke 53281,0:poke 646,1
1030 print chr$(147)
1040 return
2000 rem -- main logic --
2010 print "hello commodore 64"
2020 return
```

### 14.2 Menu with input validation

```basic
10 rem menu
20 print chr$(147)
30 print "1. start"
40 print "2. settings"
50 print "3. quit"
60 get k$:if k$="" then 60
70 k=val(k$)
80 if k<1 or k>3 then 60
90 on k goto 100,200,300
100 print "start":goto 20
200 print "settings":goto 20
300 print "goodbye":end
```

### 14.3 Sprite controlled by joystick (port 2)

```basic
10 rem sprite with joystick
20 v=53248:sb=832:n=0:b=2^n:jp=56320
30 print chr$(147):poke 53280,0:poke 53281,0
40 for i=0 to 62:read d:poke sb+i,d:next i
50 poke 2040+n,sb/64
60 poke v+21,peek(v+21) or b
70 poke v+39+n,7
80 x=160:y=140
90 j=peek(jp)
100 if (j and 1)=0 then y=y-2
110 if (j and 2)=0 then y=y+2
120 if (j and 4)=0 then x=x-2
130 if (j and 8)=0 then x=x+2
140 if x<24 then x=24
150 if x>320 then x=320
160 if y<50 then y=50
170 if y>229 then y=229
180 poke v+2*n,x and 255
190 if x>255 then poke v+16,peek(v+16) or b
200 if x<256 then poke v+16,peek(v+16) and (255-b)
210 poke v+2*n+1,y
220 if (j and 16)=0 then poke v+21,0:end
230 goto 90
900 data 0,126,0, 1,255,128, 3,255,192, 7,255,224
910 data 7,231,224, 15,255,240, 15,255,240, 15,255,240
920 data 7,255,224, 7,189,224, 3,255,192, 1,255,128
930 data 0,126,0, 0,60,0, 0,60,0, 0,24,0
940 data 0,24,0, 0,24,0, 0,60,0, 0,102,0
950 data 0,195,0
```

### 14.4 SID melody player

```basic
10 rem sid melody
20 s=54272
30 for i=0 to 24:poke s+i,0:next i
40 poke s+24,15
50 poke s+5,9:poke s+6,0
60 read hi,lo,du
70 if hi<0 then poke s+4,0:poke s+24,0:end
80 poke s+1,hi:poke s,lo
90 poke s+4,17
100 for d=1 to du*40:next d
110 poke s+4,16
120 for d=1 to 40:next d
130 goto 60
900 data 17,103,4, 19,137,4, 21,237,4, 23,59,4
910 data 26,19,4,  29,69,4,  32,218,4, 34,206,8
920 data -1,-1,-1
```

### 14.5 Game skeleton with screen poking

```basic
10 rem ---- game skeleton ----
20 gosub 1000
30 gosub 2000
40 gosub 3000
50 if lv>0 then 30
60 gosub 4000
70 end
1000 rem init
1010 v=53248:sm=1024:cm=55296:jp=56320
1020 poke 53280,0:poke 53281,0:poke 646,1
1030 print chr$(147)
1040 sc=0:lv=3:px=20:py=12
1050 return
2000 rem draw screen
2010 print chr$(19);"score:";sc;" lives:";lv
2020 return
3000 rem main loop
3010 j=peek(jp)
3020 poke sm+px+py*40,32
3030 if (j and 4)=0 then px=px-1
3040 if (j and 8)=0 then px=px+1
3050 if px<0 then px=0
3060 if px>39 then px=39
3070 poke sm+px+py*40,81:poke cm+px+py*40,1
3080 gosub 2000
3090 return
4000 rem game over
4010 print chr$(147);"game over - score:";sc
4020 return
```

---

## Appendix A — Memory map, only what you need in BASIC

### Zero page and system variables

| Address | Function |
|---:|---|
| 43–44 | Start of BASIC program (default 2049 = $0801) |
| 45–46 | Start of variables |
| 51–52 | Start of string memory (grows downward) |
| 55–56 | End of BASIC memory (default 40960 = $A000) |
| 145 | Stop key: 127 = pressed |
| 197 | Matrix code of the currently pressed key |
| 198 | Keyboard buffer length |
| 199 | Reverse mode: 0 = normal, 18 = inverse |
| 211 | Cursor column (0–39) |
| 214 | Cursor row (0–24) |
| 631–640 | Keyboard buffer |
| 646 | Current text color |
| 648 | High byte of screen memory (default 4 = 1024) |
| 650 | Key repeat (128 = all keys repeat) |
| 653 | Shift/commodore/ctrl status |
| 704 | Free, usable as sprite block 11 |
| 768–819 | System vectors — **do not use** |
| 785–786 | Vector for `usr()` |
| 788–789 | IRQ vector (default $EA31 = 59953) |
| 808–809 | Stop routine (237 = normal, 239 = run/stop disabled) |
| 828–1019 | Datassette buffer — usable as sprite block 13, 14, 15 |
| 1024–2023 | Screen memory (screen codes) |
| 2040–2047 | Sprite pointers |
| 2049 | Start of BASIC program |

### VIC-II (v = 53248)

| Address | Offset | Function |
|---:|---:|---|
| 53248–53263 | v+0…v+15 | Sprite X/Y 0..7 |
| 53264 | v+16 | Sprite X bit 8 |
| 53265 | v+17 | Screen control 1: raster line bit 8, screen on/off, bitmap, 24/25 rows |
| 53266 | v+18 | Current raster line (read) / interrupt line (write) |
| 53269 | v+21 | Sprite on/off |
| 53270 | v+22 | Screen control 2: multicolor text, 38/40 columns |
| 53271 | v+23 | Sprite Y-expand |
| 53272 | v+24 | Memory setup: screen and character memory (21 = graphics, 23 = lowercase) |
| 53273 | v+25 | Interrupt status |
| 53274 | v+26 | Interrupt control |
| 53275 | v+27 | Sprite priority |
| 53276 | v+28 | Sprite multicolor |
| 53277 | v+29 | Sprite X-expand |
| 53278 | v+30 | Sprite–sprite collision (read clears) |
| 53279 | v+31 | Sprite–background collision (read clears) |
| 53280 | v+32 | Border color |
| 53281 | v+33 | Background color |
| 53282–53284 | v+34…v+36 | Extra background colors 1–3 |
| 53285–53286 | v+37, v+38 | Sprite multicolor 1 and 2 |
| 53287–53294 | v+39…v+46 | Color of sprite 0..7 |

### SID (s = 54272)

| Address | Offset | Function |
|---:|---:|---|
| 54272–54278 | s+0…s+6 | Voice 1: freq lo/hi, pulse lo/hi, control, attack/decay, sustain/release |
| 54279–54285 | s+7…s+13 | Voice 2, same layout |
| 54286–54292 | s+14…s+20 | Voice 3, same layout |
| 54293–54295 | s+21…s+23 | Filter: cutoff lo/hi, routing + resonance |
| 54296 | s+24 | Volume (bits 0–3) and filter mode |
| 54299 | s+27 | Waveform output voice 3 (read — usable as random) |

### Other

| Address | Function |
|---:|---|
| 55296–56295 | Color ram (only bits 0–3) |
| 56320 | CIA1 port A — **joystick port 2** |
| 56321 | CIA1 port B — joystick port 1 + keyboard |
| 56333 | CIA1 interrupt control |
| 56576 | VIC bank select (bits 0–1, inverted) |
| 64738 | `sys 64738` = soft reset |

---

## Appendix B — Quick correction table

What the AI often gets wrong, and what it should be:

| Wrong | Right |
|---|---|
| `if a=1 then x=1 else x=2` | `if a=1 then x=1` / `if a<>1 then x=2` |
| `cls` | `print chr$(147)` |
| `while a<10 ... wend` | `100 if a>=10 then 200` … `190 goto 100` |
| `locate 10,5:print "x"` | `poke 781,5:poke 782,10:poke 783,0:sys 65520:print "x"` |
| `sprite 1,1,2` | `poke 53269,peek(53269) or 2:poke 53288,2` |
| `sound 1,440,10` | see §8: poke SID registers |
| `color 0,1` | `poke 53281,0:poke 646,1` |
| `score=0` | `sc=0` (`score` contains `or`) |
| `total=0` | `tt=0` (`total` contains `to`) |
| `? "hello"` | `print "hello"` |
| `poke 1024,65` for the letter a | `poke 1024,1` (screen code) |
| `poke 53248+21,1` in a loop | `v=53248:se=v+21` … `poke se,1` |
| `poke 53269,1` (turns off other sprites) | `poke 53269,peek(53269) or 1` |
| `data one,two` | `data "one","two"` |
| `Bas2Prg().convert(src)` | `Bas2Prg(invert_case=True).convert(src)` |

---

*Sources: C64-Wiki (BASIC V2.0, C64-Commands, Color), Commodore 64
memory map, Commodore 64 Programmer's Reference Guide, and the project
tools `bas2prg.py` and `c64_syntax_checker.py`. All code examples in this
document are verified with the syntax checker and the PRG tokenizer.*