# C64 BASIC V2 Skill & Toolchain

A complete toolkit for writing, validating, and compiling
**Commodore 64 BASIC V2** programs — the way the real hardware expects them.

This repository contains:

| File | Description |
|---|---|
| [`c64_basic_skill.md`](c64_basic_skill.md) | The authoritative skill document (English) — all rules, patterns, and reference tables |
| [`c64_basic_skill_nl.md`](c64_basic_skill_nl.md) | The skill document in Dutch (original version) |
| [`bas2prg.py`](bas2prg.py) | Compiles a `.bas` text file into a C64 `.prg` executable |
| [`c64_syntax_checker.py`](c64_syntax_checker.py) | Syntax checker for BASIC V2 source code (English output) |
| [`c64_syntax_checker_nl.py`](c64_syntax_checker_nl.py) | Syntax checker for BASIC V2 source code (Dutch output) |

---

## Why this exists

Commodore 64 BASIC V2 is a minimal dialect. It has no `else`, no `while`,
no `cls`, no `locate`, no sprite commands, no `sound`. Modern AI assistants
and developers routinely invent statements that don't exist, use variable
names that collide with keywords (`score` contains `or`, `total` contains
`to`), or forget that the C64 uses two different character sets (PETSCII
vs. screen codes).

This project provides:

1. **A strict rulebook** — [`c64_basic_skill.md`](c64_basic_skill.md)
   documents everything that exists in BASIC V2 and everything that does
   not, with concrete workaround patterns for every missing feature.
2. **A syntax checker** — catches line-number errors, unbalanced quotes,
   keywords hidden in variable names, missing `then`, broken `for`/`next`
   pairing, non-existent `goto` targets, and more — *before* you run the
   code on a C64.
3. **A PRG compiler** — converts your lowercase `.bas` source into a
   tokenized `.prg` file that loads and runs on a real Commodore 64 or
   in the [VICE](https://vice-emu.sourceforge.io/) emulator.

---

## Requirements

- **[Python 3](https://www.python.org/downloads/)** (3.6 or newer)
  - No third-party packages needed — both tools use only the Python
    standard library (`re`, `sys`, `os`).
- **[VICE emulator](https://vice-emu.sourceforge.io/)** (optional, for
  testing the compiled `.prg` files)
  - The `x64sc` command is used in the examples below.
- **A real Commodore 64** (optional, for the ultimate test)

Check your Python version:

```bash
python --version
```

---

## Quick start

### 1. Write a BASIC program

Create a `.bas` file in **lowercase**, one statement per line, with line
numbers in steps of 10:

```basic
10 rem -- hello world --
20 print chr$(147)
30 print "hello commodore 64"
40 end
```

Save it as `hello.bas`.

> **Why lowercase?** The C64 displays uppercase letters as PETSCII
> graphics characters. The compiler flips the case so that lowercase
> source becomes readable text on the C64. See
> [§1 rule 1](c64_basic_skill.md) and
> [§2.3](c64_basic_skill.md) in the skill document.

### 2. Run the syntax checker

```bash
python c64_syntax_checker.py hello.bas
```

Output:

```text
=== c64 syntax checker ===
file: hello.bas
errors: 0
warnings: 0
ok: 0 errors
```

**Requirement: 0 errors.** Warnings should be reviewed — some are known
false positives (documented in
[§2.2](c64_basic_skill.md)). To suppress
reachability warnings:

```bash
# Windows (PowerShell)
$env:C64_NO_REACH=1; python c64_syntax_checker.py hello.bas

# Linux / macOS
C64_NO_REACH=1 python c64_syntax_checker.py hello.bas
```

### 3. Compile to PRG

```bash
python bas2prg.py hello.bas -o hello.prg -i
```

The `-i` flag (`invert_case=True`) is **mandatory** for lowercase source
files. Without it, the tokenizer does not recognize any keywords and the
output PRG will give `?syntax error` on the C64. See
[§2.3](c64_basic_skill.md).

Output:

```text
geschreven: hello.prg (XX bytes, invert=True)
```

> The message is in Dutch ("geschreven" = "written"). The compiler
> itself works identically regardless of language.

### 4. Run in VICE

```bash
x64sc hello.prg
```

Or on a real C64 with a SD2IEC / Ultimate64 / Pi1541:

```text
load "hello.prg",8,1
run
```

---

## The toolchain in detail

### `bas2prg.py` — BASIC to PRG compiler

Converts a plain-text `.bas` file into a tokenized Commodore 64 `.prg`
file. The PRG format is a linked list of lines with a 2-byte load address
header (default `$0801` = 2049, the standard BASIC start).

**CLI usage:**

```bash
python bas2prg.py <source.bas> [-o <output.prg>] [-i]
```

| Flag | Description |
|---|---|
| `<source.bas>` | Input file (required) |
| `-o <output.prg>` | Output path (optional; defaults to same name with `.prg` extension) |
| `-i` | Invert case — **mandatory** for lowercase source files |

**Python API usage:**

```python
from bas2prg import Bas2Prg

source = open('program.bas', 'r').read()
prg = Bas2Prg(invert_case=True).convert(source)
open('program.prg', 'wb').write(prg)
```

**Known bug — operator tokenization** (see
[§2.4](c64_basic_skill.md)):

The patch that prevents keywords from being matched inside variable
names also blocks operator tokenization when the previous character is
alphanumeric. This means `a=5` (without spaces) produces a raw `=` byte
instead of the `=` token (`$b2`), causing `?syntax error` on the C64.

**Workaround:** always put spaces around operators: `a = 5`, `i = i + 1`.

**Fix:** apply the patch described in
[§2.4](c64_basic_skill.md) of the skill
document (a 3-line addition to `_tokenize_line()`).

---

### `c64_syntax_checker.py` — Syntax checker

Validates a `.bas` file against BASIC V2 rules *before* compilation. This
catches errors that would otherwise only surface as cryptic `?syntax
error` messages on the C64.

**CLI usage:**

```bash
python c64_syntax_checker.py <source.bas>
python c64_syntax_checker.py <source.bas> --json   # machine-readable, same schema as the C128 checker
```

The checker validates:

- Line numbers: present, in range 0–63999, unique, ascending
- Quotes: balanced (even count per line)
- Parentheses: balanced
- `if` followed by `then`
- `for` / `next` variable pairing
- `goto` / `gosub` / `then <n>` targets exist
- `on ... goto/gosub` target lists
- Keywords embedded in variable names (e.g. `score` contains `or`)
- Keywords from other dialects that do not exist in V2 (skill §3.2: `else`,
  `while`, `mod`, `cls`, `color`, `instr(`, …). Plain variables with such a
  name (`do=5`, `key(3)`) are still allowed
- Uppercase letters in code (error: `bas2prg -i` would break the keywords)
  and in strings (warning: they show up as PETSCII graphics characters)
- Expression validity
- Reachability (lines that can never be executed)

**Environment variables:**

| Variable | Effect |
|---|---|
| `C64_NO_REACH=1` | Disables reachability checking (suppresses known false positives) |
| `C64_REACH_MODE=...` | Reachability mode (see source) |

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | No errors |
| 1 | One or more errors found |
| 2 | Usage error (no file argument) or file unreadable |

> **Note:** `c64_syntax_checker.py` has English output messages;
> `c64_syntax_checker_nl.py` has Dutch output messages. Both produce
> identical results — only the language of the messages differs.

---

## How to use the skill document

[`c64_basic_skill.md`](c64_basic_skill.md) is the **single source of
truth** for writing correct C64 BASIC V2 code. It is structured as a
reference manual:

| Section | Content |
|---|---|
| §0 | Work order — the 6-step process to follow on every task |
| §1 | The 12 hard rules that cause 90% of all errors |
| §2 | Toolchain: file format, syntax checker, PRG compilation, known bugs |
| §3 | Language reference: complete token table, forbidden keywords, variables, expressions, built-in functions, `print` formatting |
| §4 | Control flow patterns: `if`/`then`, loops, `gosub`/`return`, `on ... goto`, `data`/`read`/`restore` (including the RESTORE workaround) |
| §5 | PETSCII vs. screen codes — the two character tables |
| §6 | Screen and color: memory addresses, color codes, character sets, fixed screen layout (no-scroll pattern) |
| §7 | Sprites: VIC-II registers, data format, activation, positioning, X>255, multicolor, collision detection |
| §8 | SID sound: registers, waveforms, ADSR, frequency table (PAL), melody player, sound effects |
| §9 | Input and timing: keyboard, `get`, joystick, `ti`/`ti$`, wait loops, "press a key" pause pattern |
| §10 | Files and peripherals: disk, printer, datassette, status variable |
| §11 | Performance optimization tips |
| §12 | Error messages and diagnosis route |
| §13 | Verification checklist (run before every delivery) |
| §14 | Ready-made templates: skeleton, menu, joystick sprite, SID melody, game shell |
| Appendix A | Memory map — all addresses you need in BASIC |
| Appendix B | Quick correction table — common mistakes and fixes |

### Recommended workflow

1. **Read §1** (the hard rules) before writing any code.
2. **Write the code** following the patterns in §4–§11.
3. **Run the checklist** in §13.
4. **Run the syntax checker** — 0 errors is mandatory.
5. **Compile with `-i`** — this is not optional.
6. **Test in VICE** or on real hardware.

---

## Project structure

```text
.
├── c64_basic_skill.md          # Skill document (English)
├── c64_basic_skill_nl.md       # Skill document (Dutch)
├── bas2prg.py                  # .bas → .prg compiler
├── c64_syntax_checker.py       # Syntax checker (English output)
├── c64_syntax_checker_nl.py    # Syntax checker (Dutch output)
├── .gitignore                  # Excludes .bas/.prg from git
└── README.md                   # This file
```

---

## Key takeaways

1. **Always write source in lowercase** — the compiler flips case so
   lowercase becomes readable text on the C64.
2. **Always use `-i` when compiling** — without it, keywords are not
   tokenized and the PRG is broken.
3. **Always run the syntax checker** — it catches errors before they
   become cryptic `?syntax error` messages on the hardware.
4. **Never invent statements** — BASIC V2 has no `else`, `while`, `cls`,
   `locate`, `sprite`, `sound`, etc. Use the workarounds in §3.2 and §4.
5. **Check variable names against the token table** — `score` contains
   `or`, `total` contains `to`, `freq` contains `fre`. Use 1–2 character
   names.
6. **PETSCII ≠ screen codes** — `print chr$(65)` shows "a", but
   `poke 1024,65` shows a graphics character. See §5.

---

## License

This project is provided as-is for educational and hobbyist use.

## Sources

- [C64-Wiki](https://www.c64-wiki.de/) — BASIC V2.0, C64-Commands, Color
- Commodore 64 Programmer's Reference Guide
- Commodore 64 memory map
- [VICE emulator](https://vice-emu.sourceforge.io/)