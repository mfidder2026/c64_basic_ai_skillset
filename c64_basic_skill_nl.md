---
name: c64-basic
description: Complete werkinstructie voor het schrijven van correcte Commodore 64 BASIC V2 code — syntax, tokenizer, PETSCII, scherm, kleur, sprites, SID-geluid, joystick, bestanden, performance en verificatie. Gebruik dit document altijd wanneer er code voor een echte C64 of een C64-emulator (VICE) geschreven, gereviewd of gedebugd wordt.
---

# C64 BASIC V2 — Skill voor de AI Developer

Dit document is de **enige waarheid** voor Commodore 64 BASIC V2 code.
Wijk er niet van af. Verzin geen statements. Gebruik geen kennis uit
andere BASIC-dialecten.

Doelplatform: **echte Commodore 64 / VICE, Commodore BASIC V2, PAL.**

---

## 0. Werkvolgorde — hou je hieraan bij ELKE opdracht

1. Lees §1 (de harde regels) voordat je één regel code schrijft.
2. Schrijf de code volgens de patronen in §4 t/m §11.
3. Loop de checklist in §13 af.
4. Draai de syntax checker (§2.2). Nul ERRORs is verplicht.
5. Compileer met `invert_case=True` (§2.3). Dit is **niet optioneel**.
6. Lever code + korte toelichting op. Geen aannames, geen "ongeveer".

Als iets niet kan in BASIC V2, **zeg dat expliciet** en bied `poke`,
`peek` of `sys` aan met een concreet adres. Verzin nooit een commando.

---

## 1. De harde regels

Deze twaalf regels veroorzaken samen ~90% van alle fouten. Overtreed ze nooit.

| # | Regel | Waarom |
|---|---|---|
| 1 | **Schrijf broncode in kleine letters** | De conversietool draait de case om. Kleine letters in de bron worden normale, leesbare letters op de C64. Hoofdletters worden PETSCII-grafiektekens. |
| 2 | **Elke regel heeft een regelnummer**, in stappen van 10 | BASIC V2 kent geen labels. Stappen van 10 laten ruimte om in te voegen. |
| 3 | **Regelnummers strikt oplopend** in het bronbestand | De PRG is een gelinkte lijst. Fout gesorteerd = corrupte lijst = `?syntax error`. |
| 4 | **Alleen de eerste 2 tekens van een variabelenaam tellen** | `score` en `scene` zijn allebei `sc` — dezelfde variabele. |
| 5 | **Geen BASIC-keyword ergens ín een variabelenaam** | De tokenizer matcht keywords op elke positie: `total` → `to`+`tal`. |
| 6 | **Regels maximaal 80 tekens** (2 schermregels van 40) | Langer is niet in te typen of te bewerken op een echte C64. |
| 7 | **Geen `else`, `while`, `wend`, `do`, `loop`, `repeat`, `until`, `select`, `case`, `cls`, `locate`, `color`, `sound`, `sprite`, `sub`, `function`** | Bestaan niet in BASIC V2. |
| 8 | **Geen afkortingen** (`?`, `pO`, `gO`) in de bron | Dat zijn invoersnelkoppelingen van de C64-editor, geen bestandssyntax. De tokenizer herkent ze niet. |
| 9 | **`print` gebruikt PETSCII-codes, `poke` naar schermgeheugen gebruikt schermcodes** | Twee verschillende tabellen. `print chr$(65)` = "a", `poke 1024,65` = een grafisch teken. |
| 10 | **Elke `for` heeft precies één `next`; elke `gosub` heeft een `return`** | Anders `?next without for` / stack-vervuiling. |
| 11 | **Elk `goto`/`gosub`-doel moet bestaan** | Anders `?undef'd statement error`. |
| 12 | **`poke`-waarden zijn 0–255, adressen 0–65535** | Buiten bereik = `?illegal quantity error`. |

Gereserveerde systeemvariabelen die je nooit als eigen naam gebruikt:
`st`, `ti`, `ti$`.

---

## 2. Toolchain en verificatie

### 2.1 Bestandsformaat

Platte tekst, één BASIC-regel per tekstregel, UTF-8/ASCII, kleine letters,
extensie `.bas`. Geen tabs. Geen lege regels tussen code (mag wel, wordt
overgeslagen, maar hou het schoon).

### 2.2 Syntax checker — verplicht vóór oplevering

```bash
python c64_syntax_checker.py programma.bas
C64_NO_REACH=1 python c64_syntax_checker.py programma.bas   # zonder bereikbaarheids-ruis
python c64_syntax_checker.py programma.bas --json           # machineleesbaar
```

De checker controleert: regelnummers (0–63999, uniek, oplopend), quotes,
haakjes, onbekende keywords, `if` zonder `then`, `for`/`next`-paring,
`goto`/`gosub`-doelen, `on ... goto/gosub`-lijsten, expressies,
keywords in variabelenamen en bereikbaarheid.

**Eis: 0 ERRORs.** WARNINGs beoordeel je met verstand — zie hieronder.

#### Bekende false positives van de checker

Deze waarschuwingen zijn onterecht. **Herschrijf werkende code er niet voor.**

| Waarschuwing | Wanneer | Waarom onterecht |
|---|---|---|
| `Unreachable line` op `data`-regels | `data` staat na `end` | `data` wordt gelezen door `read`, niet uitgevoerd. Dit is de correcte plek. |
| `Unreachable line` na `if ... then <regelnr>` | altijd | De checker ziet de `if` als onvoorwaardelijke sprong en verliest het doorval-pad. |
| `Unreachable line` na `if ... then ... : end` | altijd | Idem: de `end` op de conditionele tak maakt de hele regel "terminerend". |
| `Unreachable line` op de 2e t/m laatste doelregel van `on ... goto` | altijd | De checker legt alleen een pad naar het eerste doel in de lijst. |

Zet in die gevallen `C64_NO_REACH=1` en beoordeel de rest.

> **Toolbug:** de CLI-vlaggen `--no-reach` en `--reach=` worden in `main()`
> wél uitgelezen maar nooit doorgegeven aan `check_file()`. Alleen de
> omgevingsvariabelen `C64_NO_REACH` en `C64_REACH_MODE` werken.

#### Waarschuwingen die je WEL altijd oplost

- `Variable 'x' contains embedded keyword 'y'` → hernoem de variabele. Altijd.
- `NEXT variable ... does not match FOR variable ...` → maak ze gelijk.
- `GOTO/GOSUB target line N does not exist` → doelregel toevoegen of corrigeren.

### 2.3 Compileren naar PRG — `invert_case` is verplicht

```python
from bas2prg import Bas2Prg

source = open('programma.bas', 'r').read()
prg = Bas2Prg(invert_case=True).convert(source)   # <-- verplicht bij kleine letters
open('programma.prg', 'wb').write(prg)
```

CLI-equivalent:

```bash
python bas2prg.py programma.bas -o programma.prg -i
```

**Waarom dit verplicht is.** De tokentabel in `bas2prg.py` staat in
hoofdletters en de vergelijking is hoofdlettergevoelig. Zonder `-i` wordt
kleine-letterbron **helemaal niet getokeniseerd**:

```text
zonder -i:  10 print chr$(147)  ->  20 70 72 69 6e 74 ...   (letterlijk "print")
met    -i:  10 print chr$(147)  ->  20 99 20 c7 28 ...      ([PRINT] [CHR$] ( )
```

Het resultaat zonder `-i` is een PRG die op de C64 `?syntax error` geeft
of als grafische wartaal in beeld komt. Dit is een van de meest
voorkomende oorzaken van "de AI schrijft goede code maar hij werkt niet".

> Het codevoorbeeld in `SKILLS_BASIC.md` (`Bas2Prg().convert(source)`)
> mist deze vlag en levert kapotte PRG's op. Gebruik altijd de vorm hierboven.

### 2.4 Openstaande bug in `bas2prg.py` — operatoren

De patch tegen keywords-in-variabelenamen blokkeert óók de tokenisatie van
operatoren wanneer het vorige teken alfanumeriek is:

```text
10 a=5        ->  A  =(raw $3d)  5      FOUT, C64 verwacht token $b2
10 a = 5      ->  A  [=tok]      5      goed (dankzij de spaties)
10 i=i+1      ->  I  =  I  +  1         FOUT, twee kapotte operatoren
```

C64 BASIC vereist de tokenbytes `$aa`–`$b3` voor `+ - * / ^ and or > = <`.
Ruwe ASCII geeft `?syntax error` bij het uitvoeren.

**Fix in `_tokenize_line()`** — voeg vlak vóór de bestaande
`if token_val is not None and not in_var_name:` toe:

```python
# Operatortokens (+ - * / ^ > = <) moeten ALTIJD getokeniseerd worden,
# ook direct na een variabelenaam.
if token_val is not None and not TOKENS[token_val - 128][0].isalpha():
    in_var_name = False
```

Geverifieerd: na deze patch worden operatoren correct getokeniseerd en
blijft de bescherming tegen keywords in variabelenamen intact
(`total` blijft ongetokeniseerd, `=` wordt wel `$b2`).

**Zolang deze patch niet is toegepast:** zet spaties rond elke operator
(`10 a = 5`, `10 i = i + 1`). Dat kost regellengte, dus patchen heeft
sterk de voorkeur.

### 2.5 Testen

```bash
x64sc programma.prg          # VICE
```

Of op de C64 zelf: `load "programma",8,1` gevolgd door `run`.

### 2.6 Valkuil - apply_diff en de gelijkteken-separator

De apply_diff-tool (search/replace) gebruikt een regel van zes
gelijktekens als scheidingsmarkering tussen het SEARCH-blok en het
REPLACE-blok. Als de inhoud van een SEARCH- of REPLACE-blok zelf een
regel bevat die uitsluitend uit zes (of meer) gelijktekens bestaat, of
een regel die daarmee begint, dan denkt de parser dat de sectie daar
eindigt. Het resultaat is een foutmelding die wijst op een special
marker in de diff-inhoud.

Dit gebeurt in de praktijk wanneer je BASIC-broncode met een
rem-commentaar probeert te bewerken dat een rij gelijktekens bevat
(bijvoorbeeld een scheidingsbalk in een rem-regel), of wanneer een
Python-functie een commentaar met zes gelijktekens bevat. Ook een
tekststring die zes of meer gelijktekens bevat kan de parser misleiden,
omdat de marker een deelstring vormt.

Oplossingen, in volgorde van voorkeur:

1. Ontsnap de marker. Plaats een backslash voor de probleemregel in
   het SEARCH-blok. Dit werkt alleen in de SEARCH-sectie; in de
   REPLACE-sectie mag de letterlijke tekst staan zolang deze niet als
   sectie-scheider wordt gelezen.
2. Herschrijf de broncode zodat de probleemregel geen kale rij
   gelijktekens meer is. Vervang een rem-scheidingsbalk van
   gelijktekens door streepjes: rem streepjes titel streepjes in
   plaats van een balk van gelijktekens. Dit is consistent met de
   stijl in dit document en voorkomt de conflicten helemaal.
3. Herschrijf het hele bestand met write-to-file in plaats van
   apply-diff, wanneer de patch te complex is of meerdere
   probleemregels bevat. Dat is trager maar altijd veilig.

Voorkeur: gebruik in rem-commentaar streepjes in plaats van
gelijktekens als scheidingsbalk. Dat vermijdt de apply-diff-conflicten
en blijft leesbaar op de C64.

---

## 3. Taalreferentie

### 3.1 Volledige tokentabel (dit is BASIC V2, niets anders bestaat)

Statements en functies, met hun tokenbyte:

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

Verder bestaan nog: `get#` (= `get` + `#`), en de systeemvariabelen
`st`, `ti`, `ti$` (geen tokens, maar gereserveerde namen).

`$cc`–`$fe` zijn ongebruikt. Alles wat hierboven niet staat, bestaat niet.

### 3.2 Verboden — bestaat NIET in BASIC V2

Gebruik nooit, in geen enkele vorm:

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

Veel hiervan komt uit **BASIC 3.5 / 7.0 (C16, Plus/4, C128)**, QuickBASIC of
GW-BASIC. Op een C64 geven ze `?syntax error`.

Ontbrekende taalconstructies en hun BASIC V2-oplossing:

| Wat je wilt | Oplossing in V2 |
|---|---|
| `if ... else ...` | Twee losse `if`-regels met complementaire condities |
| `while c ... wend` | `100 if not c then 200` … `190 goto 100` … `200 rem` |
| `do ... loop until c` | `100 rem` … `190 if not c then 100` |
| benoemde subroutine | `gosub <regelnummer>` + `rem`-koptekst boven de routine |
| lokale variabelen | Bestaan niet. Reserveer namen per module (zie §3.4) |
| `cls` | `print chr$(147)` |
| `locate x,y` | `poke 781,y:poke 782,x:poke 783,0:sys 65520` (kernal plot) |
| exception handling | Bestaat niet. Valideer invoer zelf |
| integer-deling | `int(a/b)` |
| modulo | `a-int(a/b)*b` |

### 3.3 Regels, regelnummers en statements

- Regelnummerbereik: **0 t/m 63999**. Gebruik stappen van 10.
- Meerdere statements per regel scheiden met `:` — toegestaan en vaak sneller.
- Regel maximaal **80 tekens** inclusief regelnummer.
- Een `?syntax error` op een regel met dubbele punten ligt zelden aan de
  dubbele punten. Controleer in deze volgorde:
  1. variabelenaam met keyword erin;
  2. variabelen die op eerste 2 tekens botsen;
  3. ontbrekend haakje of komma;
  4. functie met verkeerd aantal argumenten;
  5. constructie uit een ander BASIC-dialect;
  6. `=`/operator niet getokeniseerd (zie §2.4).

`rem` maakt de rest van de regel commentaar — ook na een `:`. Zet `rem`
dus altijd als laatste statement op een regel.

### 3.4 Variabelen

**Twee-tekenregel.** Alleen de eerste twee significante tekens
onderscheiden variabelen. Meer tekens mogen, maar tellen niet mee.

```basic
10 rem fout: score en scene zijn dezelfde variabele "sc"
20 score=10
30 scene=20
40 print score
```

Werk daarom met een **naamregister** boven in het programma:

```basic
10 rem -- variabelen --
20 rem v =vic basis   sm=schermgeheugen  cm=kleurgeheugen
30 rem sc=score       lv=levens          px,py=speler
40 rem jp=joystickpoort  i,n,d=lussen    a$,k$=tekst
```

**Keywords in namen.** De tokenizer probeert op *elke* positie in de
regel een keyword te matchen. Deze namen zijn kapot:

| Naam | Bevat | Wordt |
|---|---|---|
| `total` | `to` | `to`+`tal` |
| `score` | `or` | `sc`+`or`+`e` |
| `color` | `or` | idem |
| `contact` | `cont` | `cont`+`act` |
| `freq` | `fre` | `fre`+`q` |
| `estep` | `step` | `e`+`step` |
| `before` | `for`,`or` | kapot |
| `victory` | `to`,`or` | kapot |
| `duration` | `on` | kapot |
| `sword` / `password` | `or` | kapot |

Veilige aanpak: **één of twee letters, eventueel gevolgd door een cijfer**
(`a`, `x1`, `sm`, `p9`). Controleer elke nieuwe naam tegen §3.1.

**Types**

| Vorm | Type | Bereik | Opmerking |
|---|---|---|---|
| `a` | floating point | ±2.9E-39 … ±1.7E38, ~9 cijfers | standaard, snelst in expressies |
| `a%` | integer | −32768 … 32767 | alleen zuinig in arrays; trager in expressies |
| `a$` | string | 0 … 255 tekens | `$` hoort bij de naam |

`a`, `a%` en `a$` zijn **drie verschillende variabelen**. Dat mag.

**Arrays**

```basic
10 dim a(20)          : rem indices 0..20, dus 21 elementen
20 dim b$(9),c%(4,4)  : rem meerdere arrays in één dim
```

- Zonder `dim` krijgt een array automatisch indices 0..10.
- Een array twee keer dimensioneren geeft `?redim'd array error`.
- `clr` wist alle variabelen en arrays; het programma blijft staan.

**Zelfgedefinieerde functies**

```basic
10 def fn r(x)=int(rnd(1)*x)+1
20 print fn r(6)
```

Eén numeriek argument, één expressie, geen strings. De functienaam valt
óók onder de twee-tekenregel.

### 3.5 Getallen en expressies

- Operatorvolgorde: `^` → unair `-` → `*` `/` → `+` `-` → vergelijkingen →
  `not` → `and` → `or`. Gebruik bij twijfel haakjes.
- Vergelijkingen leveren **−1 (waar)** of **0 (onwaar)**. Dat is bruikbaar:
  `x=x+(k=1)-(k=2)` verplaatst `x` zonder `if`.
- `and`/`or`/`not` zijn **bitsgewijs** op 16-bits integers, niet puur logisch.
  Daarom werken ze zowel voor condities als voor bitmaskers.
- Wetenschappelijke notatie: `1.5e3`.
- `pi` is een constante (op de C64 het π-teken; in tekstbestanden schrijf je `pi`).

### 3.6 Ingebouwde functies

| Functie | Levert | Opmerking |
|---|---|---|
| `abs(x)` | absolute waarde | |
| `int(x)` | afronden naar beneden | `int(-3.2)` = −4 |
| `sgn(x)` | −1, 0 of 1 | |
| `sqr(x)` | wortel | `x>=0` |
| `rnd(x)` | 0 ≤ r < 1 | `rnd(1)` reeks, `rnd(0)` uit timer, `rnd(-n)` seed |
| `sin/cos/tan/atn(x)` | radialen | |
| `exp(x)` / `log(x)` | e-macht / natuurlijke log | `log(x)` vereist `x>0` |
| `len(a$)` | lengte | |
| `left$(a$,n)` / `right$(a$,n)` | deelstring | |
| `mid$(a$,p,n)` | deelstring vanaf positie `p` (1-based) | `n` optioneel |
| `asc(a$)` | PETSCII-code eerste teken | lege string = `?illegal quantity` |
| `chr$(n)` | teken bij PETSCII-code | |
| `str$(x)` | getal → string | krijgt een leidende spatie of `-` |
| `val(a$)` | string → getal | niet-numeriek = 0 |
| `peek(a)` | byte op adres | |
| `pos(0)` | huidige cursorkolom | |
| `fre(0)` | vrij BASIC-geheugen | boven 32767 negatief: `fre(0)-65536*(fre(0)<0)` |
| `usr(x)` | machinetaalroutine via vector 785/786 | |
| `tab(n)` / `spc(n)` | alleen binnen `print` | |

### 3.7 print — formattering

```basic
10 print "a";"b"        : rem aaneengesloten
20 print "a","b"        : rem b begint in de volgende kolom van 10
30 print "geen newline";: rem afsluitende ; onderdrukt de regelovergang
40 print                : rem lege regel
50 print "waarde:";x    : rem getallen krijgen een spatie ervoor en erna
```

Getallen printen met een leidende spatie (plaats voor het minteken) en een
afsluitende spatie. Wil je dat niet, gebruik dan
`a$=str$(x):print right$(a$,len(a$)-1)`.

---

## 4. Control flow — de vaste patronen

### 4.1 if / then

```basic
10 input "getal";x
20 if x>10 then print "groter dan 10"
30 if x<=10 then print "10 of kleiner"
40 end
```

- `then <regelnummer>` is een sprong; `then goto <n>` is hetzelfde maar langer.
- Alles achter `then` op dezelfde regel hoort bij de ware tak:
  `if a=1 then b=2:c=3` — `c=3` wordt **alleen** uitgevoerd als `a=1`.
  Dit is de belangrijkste val bij het nabouwen van `else`.
- Er is geen `else`. Schrijf twee `if`-regels met complementaire condities.

### 4.2 Lussen

```basic
10 for i=1 to 10:print i:next i
20 for i=10 to 1 step -1:print i:next i
30 for j=0 to 7:for k=0 to 7:print j,k:next k:next j
```

- `next` zonder variabele is iets sneller, maar `next i` is leesbaarder en
  wordt door de checker gecontroleerd. Gebruik `next i`.
- `next i,j` sluit twee lussen tegelijk (binnenste eerst).
- Een `for`-lus loopt **altijd minstens één keer** — de test staat bij `next`.
- Nooit met `goto` een `for`-lus in- of uitspringen: de stack loopt vol
  (`?out of memory error`).

Voorwaardelijke lus (vervangt `while`):

```basic
100 if a>=10 then 200
110 a=a+1
120 goto 100
200 rem verder
```

### 4.3 gosub / return

```basic
10 gosub 1000
20 print "terug"
30 end
1000 rem subroutine
1010 return
```

- Sluit het hoofdprogramma altijd af met `end` vóór het subroutineblok,
  anders loopt de uitvoering de subroutine in en volgt
  `?return without gosub error`.
- Nesting is beperkt door de stack (~23 niveaus). Hou het ondiep.
- Geef subroutines vaste blokken: 1000, 2000, 3000, …

### 4.4 on ... goto / gosub

```basic
10 input "kies 1, 2 of 3";k
20 on k goto 100,200,300
30 goto 10
100 print "een":goto 10
200 print "twee":goto 10
300 print "drie":end
```

Bij `k=0` of `k>` aantal doelen valt de uitvoering door naar de volgende
regel. Vang dat altijd af (regel 30 hierboven).

### 4.5 data / read / restore

```basic
10 for i=1 to 3:read n$,w:print n$;w:next i
20 end
100 data "rood",2,"groen",5,"blauw",6
```

- `data` mag overal staan; conventioneel achteraan, na `end`.
- **Zet tekst in `data` altijd tussen dubbele quotes.** Zonder quotes
  tokeniseert BASIC keywords ín de tekst: `data one` wordt `data` + token(`on`) + `e`.
- `restore` zet de leespointer terug naar de eerste `data`-regel. BASIC V2
  kan **niet** naar een specifieke regel restoren.
- Te vaak lezen geeft `?out of data error`. Sluit af met een eindmarkering
  (bijvoorbeeld `-1`) of tel precies.

### 4.5a RESTORE naar een specifieke regel — workaround

BASIC V2 kent alleen `restore` (zonder regelnummer). Als je dezelfde
`data`-blok meerdere keren moet lezen (bijvoorbeeld een melodie bij de
intro én bij het winnen), laad de `data` dan één keer in arrays en
speel af vanuit de arrays:

```basic
10 dim mh(6),ml(6)
20 for i = 1 to 6:read mh(i),ml(i):next i
30 end
100 data 17,103,19,137,21,237,23,59,26,19,34,206
200 rem -- speel melodie --
210 for q = 1 to 6
220 poke s+1,mh(q):poke s,ml(q)
230 poke s+4,17
240 for d = 1 to 120:next d
250 poke s+4,16
260 next q
270 return
```

Voordelen: geen `restore` nodig, geen `?out of data error` bij herhaald
spelen, en de melodie kan onbeperkt worden aangeroepen.

### 4.6 end, stop, cont, clr, new

| Commando | Effect |
|---|---|
| `end` | Netjes stoppen, geen melding |
| `stop` | Onderbreken met `break in <regel>`; hervatten met `cont` |
| `cont` | Hervat na `stop` of run/stop, mits het programma niet is gewijzigd |
| `clr` | Wist alle variabelen, arrays en de gosub/for-stack; programma blijft |
| `new` | Wist het programma uit het geheugen |
| `run` | Start; doet impliciet een `clr` |

---

## 5. PETSCII, schermcodes en besturingscodes

### 5.1 Twee verschillende tabellen

Dit is een klassieke foutbron:

- **`print` en `chr$()` gebruiken PETSCII-codes.**
- **`poke` naar schermgeheugen (1024–2023) gebruikt schermcodes.**

`print chr$(65)` toont de letter A. `poke 1024,65` toont een grafisch teken.
De letter A in schermgeheugen is code **1**.

Omrekening PETSCII → schermcode:

| PETSCII | Schermcode |
|---|---|
| 0–31 | niet afdrukbaar (besturingscodes) |
| 32–63 | zelfde waarde |
| 64–95 | PETSCII − 64 |
| 96–127 | PETSCII − 32 |
| 128–159 | niet afdrukbaar (besturingscodes) |
| 160–191 | PETSCII − 64 |
| 192–223 | PETSCII − 128 |
| 224–254 | PETSCII − 128 |
| 255 | 94 |

Omgekeerd videobeeld: **schermcode + 128**.

Veelgebruikte schermcodes:

| Code | Teken |
|---|---|
| 0 | `@` |
| 1–26 | letters a–z |
| 27–31 | `[` `£` `]` `↑` `←` |
| 32 | spatie |
| 33–47 | `!` `"` `#` `$` `%` `&` `'` `(` `)` `*` `+` `,` `-` `.` `/` |
| 48–57 | cijfers 0–9 |
| 58–63 | `:` `;` `<` `=` `>` `?` |
| 64–127 | grafische tekens |
| 81 | gevulde cirkel (klassieke "bal") |
| 87 | gevuld blok-variant |
| 160 | omgekeerde spatie (volledig gevuld blok) |

Weet je een schermcode niet zeker? Print het teken en lees het terug:

```basic
10 print chr$(147);"x";
20 print peek(1024)
```

### 5.2 PETSCII-besturingscodes voor print

| Code | Effect | | Code | Effect |
|---:|---|---|---:|---|
| 5 | wit | | 144 | zwart |
| 8 | shift+commodore uit | | 145 | cursor omhoog |
| 9 | shift+commodore aan | | 146 | reverse uit |
| 13 | return | | 147 | scherm wissen |
| 14 | kleine-letterset | | 148 | insert |
| 17 | cursor omlaag | | 149 | bruin |
| 18 | reverse aan | | 150 | lichtrood |
| 19 | home (cursor linksboven) | | 151 | donkergrijs |
| 20 | delete | | 152 | grijs |
| 28 | rood | | 153 | lichtgroen |
| 29 | cursor rechts | | 154 | lichtblauw |
| 30 | groen | | 155 | lichtgrijs |
| 31 | blauw | | 156 | paars |
| 129 | oranje | | 157 | cursor links |
| 142 | hoofdletter-/grafische set | | 158 | geel |
| | | | 159 | cyaan |

Gebruik:

```basic
10 print chr$(147);              : rem wissen
20 print chr$(19);               : rem home, zonder te wissen
30 print chr$(18);"invers";chr$(146)
40 print chr$(28);"rode tekst"
50 print chr$(14)                : rem kleine letters aanzetten
```

`chr$(19)` (home) in plaats van `chr$(147)` (wissen) is dé manier om een
score-regel te verversen zonder flikkering.

---

## 6. Scherm en kleur

### 6.1 Kernadressen

```text
1024 – 2023    schermgeheugen, 40 x 25 tekens (schermcodes)
55296 – 56295  color ram, zelfde indeling (alleen bits 0-3)
2040 – 2047    sprite pointers
53280          randkleur (border)
53281          achtergrondkleur
646            kleur van nieuw geprinte tekens
53272          geheugenopzet: teken- en schermgeheugen
198            lengte toetsenbordbuffer
650            toetsherhaling (128 = alle toetsen herhalen)
```

Positieberekening:

```text
schermadres = 1024  + x + y*40      met x = 0..39, y = 0..24
kleuradres  = 55296 + x + y*40
```

De offset is identiek — bereken hem één keer:

```basic
10 sm=1024:cm=55296
20 o=x+y*40
30 poke sm+o,81:poke cm+o,1
```

### 6.2 Kleurcodes

| Code | Kleur | Code | Kleur |
|---:|---|---:|---|
| 0 | zwart | 8 | oranje |
| 1 | wit | 9 | bruin |
| 2 | rood | 10 | lichtrood |
| 3 | cyaan | 11 | donkergrijs |
| 4 | paars | 12 | grijs |
| 5 | groen | 13 | lichtgroen |
| 6 | blauw | 14 | lichtblauw |
| 7 | geel | 15 | lichtgrijs |

Opstartkleuren: rand 14, achtergrond 6, tekst 14.

```basic
10 poke 53280,0:poke 53281,0:poke 646,1   : rem zwart met witte tekst
20 print chr$(147)
```

Let op de volgorde: `print chr$(147)` vult color ram met de **huidige**
tekstkleur (646). Zet 646 dus vóór het wissen.

### 6.3 Tekenset omschakelen

```basic
10 print chr$(14)   : rem kleine letters + hoofdletters
20 print chr$(142)  : rem hoofdletters + grafische tekens (standaard)
30 poke 53272,23    : rem via vic (21=grafisch, 23=kleine letters)
40 poke 657,128     : rem shift+commodore blokkeren
```

### 6.4 Randloos scherm en schermverschuiving

```basic
10 poke 53265,peek(53265) and 247  : rem 24 rijen i.p.v. 25
20 poke 53270,peek(53270) and 247  : rem 38 kolommen
30 poke 53265,peek(53265) or 8     : rem terug naar 25 rijen
```

### 6.5 Vaste schermindeling (geen scroll)

Tekst-avonturen en menu's hebben vaak een vaste indeling: titel bovenaan,
inventaris onderaan, reactiegebied in het midden. Als je `print` gebruikt
op de onderste regels, schuift het scherm op en verdwijnt de bovenste
tekst. Oplossing: positioneer de cursor expliciet met de KERNAL PLOT-
routine vóór elke `print`, zodat er geen nieuwe regels worden toegevoegd.

```basic
10 rem -- cursor naar rij r, kolom 0 --
20 poke 781,r:poke 782,0:poke 783,0:sys 65520
30 print "tekst op vaste rij";
```

| PEEK/POKE-adres | Functie |
|---:|---|
| 781 | rij (0–24) |
| 782 | kolom (0–39) |
| 783 | 0 = absolute positie, 1 = relatief |

Een gebied wissen zonder te scrollen — positioneer de cursor op elke rij
en print spaties met `;` (geen return):

```basic
10 for cl = 12 to 19
20 poke 781,cl:poke 782,0:poke 783,0:sys 65520
30 print "                                       ";
40 next cl
```

Voorbeeldindeling voor een tekst-avontuur:

```text
rij  0:   kamer: <naam>            (cyaan, chr$(159))
rij  2:   <kamerbeschrijving>
rij  6:   uitgangen: noord zuid
rij 10:   commando?                (vaste prompt-regel)
rij 12-19: <reactietekst>           (wordt gewist per commando)
rij 20:   bij je: lamp sleutel     (groen, chr$(30))
rij 21:   druk op een toets...    (wacht-prompt)
```

Kleur voor een regel instellen en terugzetten:

```basic
10 print chr$(159);"cyaan tekst";chr$(158)
```

`chr$(159)` = cyaan, `chr$(158)` = geel (standaardkleur herstellen).

---

## 7. Sprites

BASIC V2 heeft **geen** sprite-commando's. Alles gaat via `poke`/`peek` op
de VIC-II. Werk altijd met een basisadres:

```basic
10 v=53248
```

### 7.1 Registeroverzicht (offsets vanaf v=53248)

| Offset | Decimaal | Functie |
|---:|---:|---|
| v+0 … v+15 | 53248–53263 | X- en Y-positie van sprite 0..7 (paren: `v+2*n`, `v+2*n+1`) |
| v+16 | 53264 | X-coördinaat bit 8 per sprite (voor X > 255) |
| v+21 | 53269 | Sprite aan/uit (1 bit per sprite) |
| v+23 | 53271 | Y-vergroting (dubbele hoogte) |
| v+27 | 53275 | Prioriteit: 1 = sprite achter schermtekst |
| v+28 | 53276 | Multicolor aan/uit |
| v+29 | 53277 | X-vergroting (dubbele breedte) |
| v+30 | 53278 | Sprite–sprite botsing (**lezen wist het register**) |
| v+31 | 53279 | Sprite–achtergrond botsing (**lezen wist het register**) |
| v+37 | 53285 | Multicolor 1 (gedeeld door alle sprites) |
| v+38 | 53286 | Multicolor 2 (gedeeld door alle sprites) |
| v+39 … v+46 | 53287–53294 | Kleur van sprite 0..7 |

Sprite pointers: **2040 + n** voor sprite n (bij het standaard scherm op 1024).

### 7.2 Vorm van de spritedata

Een sprite is **24 x 21 pixels** = 3 bytes per rij x 21 rijen = **63 bytes**,
opgeslagen in een blok van 64 bytes. De pointerwaarde is het bloknummer:

```text
bloknummer = adres / 64        adres = bloknummer * 64
```

Veilige blokken in BASIC **zonder** geheugen te verplaatsen:

| Blok | Adres | Opmerking |
|---:|---:|---|
| 11 | 704 | vrij gebied 679–767 |
| 13 | 832 | datasettebuffer — veilig zolang je geen tape gebruikt |
| 14 | 896 | idem |
| 15 | 960 | idem |

Blok 12 (768–831) bevat systeemvectoren. **Nooit gebruiken.**

Meer dan vier sprites? Verlaag de bovengrens van BASIC en zet de data op 12288:

```basic
10 poke 52,48:poke 56,48:clr   : rem basic-top naar $3000 = 12288
20 rem sprite n data op 12288+n*64, pointerwaarde 192+n
```

### 7.3 Spritedata maken

Elke rij is 3 bytes; elke byte is 8 pixels, bit 7 links.

```text
rij:  ...####...  ..######..  ..######..
byte:  00111100    00111111    11000000  ...
       = 60        = 63        = 192
```

Standaardpatroon met `data` + `read` + `poke`:

```basic
10 v=53248:sb=832              : rem sb = spritebasis, blok 13
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

Tel de bytes: **precies 63**, anders schuift de vorm of krijg je
`?out of data error`.

### 7.4 Sprite activeren

```basic
10 v=53248
20 n=0                          : rem spritenummer 0..7
30 b=2^n                        : rem bitmasker voor dit sprite
40 poke 2040+n,13               : rem pointer -> blok 13 (adres 832)
50 poke v+21,peek(v+21) or b    : rem aanzetten
60 poke v+39+n,1                : rem kleur wit
70 poke v+2*n,160:poke v+2*n+1,120 : rem x=160, y=120
```

**Bewaar altijd bestaande bits.** Zo zet je één sprite uit zonder de
andere te raken:

```basic
100 poke v+21,peek(v+21) and (255-b)
```

Ditzelfde patroon geldt voor v+16, v+23, v+27, v+28 en v+29.

### 7.5 Positionering en X > 255

Zichtbaar gebied voor een niet-vergroot sprite:

```text
x: 24 .. 320   (volledig zichtbaar; 24 = linkerrand van het beeld)
y: 50 .. 229   (volledig zichtbaar; 50 = bovenrand)
```

X loopt tot 320 en past dus niet in één byte. Gebruik het MSB-register:

```basic
100 poke v+2*n,x and 255
110 if x>255 then poke v+16,peek(v+16) or b
120 if x<256 then poke v+16,peek(v+16) and (255-b)
130 poke v+2*n+1,y
```

Vergeet regel 120 niet — zonder de "uit"-tak blijft het sprite rechts hangen
zodra het één keer voorbij 255 is geweest.

### 7.6 Vergroten, multicolor, prioriteit

```basic
200 poke v+29,peek(v+29) or b   : rem dubbele breedte
210 poke v+23,peek(v+23) or b   : rem dubbele hoogte
220 poke v+27,peek(v+27) or b   : rem achter de schermtekst
230 poke v+28,peek(v+28) or b   : rem multicolor aan
240 poke v+37,2:poke v+38,7     : rem multicolor 1 = rood, 2 = geel
```

In multicolormodus worden de bits **paarsgewijs** gelezen; de sprite is dan
12 pixels breed met dubbelbrede punten:

| Bitpaar | Kleur |
|---|---|
| 00 | transparant |
| 01 | multicolor 1 (v+37) |
| 10 | eigen spritekleur (v+39+n) |
| 11 | multicolor 2 (v+38) |

### 7.7 Botsingsdetectie

De registers v+30 en v+31 **wissen zichzelf bij het lezen**. Lees ze dus
exact één keer per lus in een variabele:

```basic
300 c=peek(v+30)                : rem sprite-sprite
310 if (c and 1)<>0 then gosub 900 : rem sprite 0 raakte iets
320 cb=peek(v+31)               : rem sprite-achtergrond
330 if (cb and 1)<>0 then gosub 950
```

In BASIC is de lus zo traag dat snelle sprites botsingen kunnen missen.
Voor games: vergelijk zelf de coördinaten, dat is betrouwbaarder:

```basic
400 if abs(x1-x2)<20 and abs(y1-y2)<18 then gosub 900
```

### 7.8 Alles uitzetten (opruimen)

```basic
500 poke v+21,0:poke v+16,0:poke v+23,0:poke v+29,0
510 poke v+27,0:poke v+28,0
```

---

## 8. Geluid — de SID (6581/8580)

BASIC V2 heeft **geen** `sound`, `play` of `vol`. Alles via `poke`.
De SID-registers zijn **write-only** en worden bij het aanzetten **niet
gewist**. Begin daarom altijd met alle 25 registers op 0.

```basic
10 s=54272
20 for i=0 to 24:poke s+i,0:next i
```

### 8.1 Registeroverzicht (offsets vanaf s=54272)

| Offset | Stem 1 | Stem 2 | Stem 3 | Functie |
|---:|---:|---:|---:|---|
| +0 / +1 | 0,1 | 7,8 | 14,15 | frequentie lo, hi |
| +2 / +3 | 2,3 | 9,10 | 16,17 | pulsbreedte lo, hi (0–4095) |
| +4 | 4 | 11 | 18 | controleregister (golfvorm + gate) |
| +5 | 5 | 12 | 19 | attack (bits 4–7) + decay (bits 0–3) |
| +6 | 6 | 13 | 20 | sustain (bits 4–7) + release (bits 0–3) |

Globaal:

| Offset | Decimaal | Functie |
|---:|---:|---|
| s+21 | 54293 | filterfrequentie laag (bits 0–2) |
| s+22 | 54294 | filterfrequentie hoog (bits 3–10) |
| s+23 | 54295 | filterroutering (bits 0–2) + resonantie (bits 4–7) |
| s+24 | 54296 | **volume (bits 0–3)** + filtermodus (16=laagdoorlaat, 32=banddoorlaat, 64=hoogdoorlaat, 128=stem 3 uit) |

### 8.2 Controleregister (golfvorm + gate)

| Bit | Waarde | Betekenis |
|---:|---:|---|
| 0 | 1 | **gate**: 1 = attack/decay/sustain starten, 0 = release starten |
| 1 | 2 | sync met stem n−1 |
| 2 | 4 | ringmodulatie |
| 3 | 8 | test / generator resetten |
| 4 | 16 | driehoek |
| 5 | 32 | zaagtand |
| 6 | 64 | puls (vereist pulsbreedte!) |
| 7 | 128 | ruis |

Praktische waarden:

| Golfvorm | Noot aan | Noot uit |
|---|---:|---:|
| driehoek | 17 | 16 |
| zaagtand | 33 | 32 |
| puls | 65 | 64 |
| ruis | 129 | 128 |

Een noot spelen is altijd: **gate aan → wachten → gate uit**. Zonder de
gate weer uit te zetten start de volgende noot niet opnieuw.

### 8.3 ADSR

```text
attack/decay byte  = attack * 16 + decay
sustain/release    = sustainvolume * 16 + release
```

Waarden 0–15. Ruwe tijden (attack / decay & release):

| Waarde | Attack | Decay & Release |
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

Bruikbare startwaarden: `poke s+5,9:poke s+6,0` (korte pluk),
`poke s+5,0:poke s+6,240` (orgel: direct aan, sustain vol).

### 8.4 Frequentietabel (PAL)

Formule: `frequentiewaarde = hertz * 16777216 / 985248 ≈ hertz * 17.028`
(NTSC: `* 16.405`). Splitsen: `hi = int(w/256)` , `lo = w - hi*256`.

Onderstaande tabel geeft **hi,lo** per noot en octaaf. Octaaf 4 is het
middenoctaaf (a4 = 440 Hz).

| Noot | o1 | o2 | o3 | o4 | o5 | o6 |
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

### 8.5 Werkend voorbeeld — melodiespeler

```basic
10 rem sid melodie
20 s=54272
30 for i=0 to 24:poke s+i,0:next i
40 poke s+24,15                : rem volume maximaal
50 poke s+5,9:poke s+6,0       : rem attack 250ms, decay 6ms
60 read hi,lo,du
70 if hi<0 then poke s+4,0:poke s+24,0:end
80 poke s+1,hi:poke s,lo
90 poke s+4,17                 : rem driehoek, gate aan
100 for d=1 to du*40:next d
110 poke s+4,16                : rem gate uit -> release
120 for d=1 to 40:next d
130 goto 60
900 data 17,103,4, 19,137,4, 21,237,4, 23,59,4
910 data 26,19,4,  29,69,4,  32,218,4, 34,206,8
920 data -1,-1,-1
```

### 8.6 Geluidseffecten

```basic
1000 rem explosie: ruis met snelle decay
1010 poke s+5,0:poke s+6,9
1020 poke s+1,20:poke s,0
1030 poke s+4,129:for d=1 to 200:next d:poke s+4,128
1040 return
1100 rem sirene: frequentie opsweepen
1110 poke s+5,0:poke s+6,240:poke s+4,33
1120 for f=30 to 80:poke s+1,f:for d=1 to 10:next d:next f
1130 poke s+4,32:return
```

### 8.7 Valkuilen

- Volume (s+24) niet gezet → geen geluid. Altijd als eerste zetten.
- Puls-golfvorm zonder pulsbreedte (s+2/s+3) → stilte. Zet bijv.
  `poke s+3,8` (= 2048, blokgolf 50%).
- Registers niet gewist bij programmastart → willekeurig gepiep.
- Gate niet uitgezet → volgende noot klinkt niet opnieuw aan.
- Bij programmaeinde: `poke s+24,0` en alle gates op 0, anders blijft er
  een toon hangen.
- BASIC is te traag voor strakke timing. Voor echte muziek onder een spel
  is een machinetaal-speler via raster-interrupt nodig.

---

## 9. Invoer en timing

### 9.1 Toetsenbord

```basic
10 input "wat is je naam";n$      : rem blokkeert, wacht op return
20 get a$                          : rem leest 1 teken, blokkeert NIET
30 if a$="" then 20                : rem wachten op een toets
```

- `input` accepteert geen komma's in de invoer (die splitsen velden).
  Voor vrije tekst met komma's: bouw zelf een invoerroutine met `get`.
- `input a,b` leest twee waarden gescheiden door een komma of return.
- `get a$` levert `""` als er geen toets in de buffer staat.
- `get a` (numeriek) geeft `?syntax error` bij een niet-cijfertoets;
  gebruik altijd `get a$` en converteer met `val()`.

Nuttige adressen:

| Adres | Functie |
|---:|---|
| 198 | aantal tekens in de toetsenbordbuffer; `poke 198,0` wist hem |
| 631–640 | de buffer zelf |
| 197 | matrixcode van de nu ingedrukte toets (64 = geen) |
| 653 | modificatietoetsen: bit 0 = shift, bit 1 = commodore, bit 2 = ctrl |
| 650 | toetsherhaling: 128 = alle toetsen herhalen, 64 = geen |
| 808 | stop-routine; 239 blokkeert run/stop en list, 237 herstelt |

```basic
10 poke 650,128                    : rem alle toetsen herhalen
20 poke 198,0                      : rem buffer legen voor een nette start
30 print "druk op een toets"
40 wait 198,15                     : rem wachten tot er iets in de buffer staat
50 get a$
```

Meerdere toetsen tegelijk uitlezen kan niet met `get`. Gebruik daarvoor
`peek(197)` (één toets) of de joystick.

### 9.1a "Druk op een toets" — pauze zonder scroll

In een spel met een vaste schermindeling (§6.5) mag je geen `print` zonder
cursorpositionering gebruiken op de onderste rijen, want dat veroorzaakt
scroll. Combineer KERNAL PLOT met een `get`-wachtloop:

```basic
10 rem -- wacht op toets --
20 poke 781,21:poke 782,0:poke 783,0:sys 65520
30 print "druk op een toets...";
40 get a$:if a$ = "" then 40
50 return
```

Belangrijk: gebruik `print "...";` met puntkomma (geen return) om te
voorkomen dat de cursor naar de volgende rij springt en scroll triggert.

Dit patroon is ook geschikt voor een intro-scherm dat wacht tot de speler
klaar is om te lezen:

```basic
10 print "schat van het spookkasteel"
20 print:print "druk op een toets om te beginnen"
30 get a$:if a$ = "" then 30
```

### 9.2 Joystick

| Poort | Adres | Opmerking |
|---:|---:|---|
| 2 | 56320 | **gebruik deze** in BASIC |
| 1 | 56321 | deelt hardware met de toetsenbordscan; geeft valse waarden |

Bits zijn **actief laag**: een 0-bit betekent ingedrukt.

| Bit | Waarde | Richting |
|---:|---:|---|
| 0 | 1 | omhoog |
| 1 | 2 | omlaag |
| 2 | 4 | links |
| 3 | 8 | rechts |
| 4 | 16 | vuurknop |

```basic
100 j=peek(56320)
110 if (j and 1)=0 then y=y-1
120 if (j and 2)=0 then y=y+1
130 if (j and 4)=0 then x=x-1
140 if (j and 8)=0 then x=x+1
150 if (j and 16)=0 then gosub 500
```

Lees `peek(56320)` **één keer** per lus in een variabele — anders krijg je
inconsistente diagonalen en is de lus onnodig traag.

### 9.3 Timing

```basic
10 print ti$          : rem "hhmmss" sinds het aanzetten
20 print ti           : rem jiffies, ongeveer 1/60 seconde
30 ti$="000000"       : rem klok resetten (ti$ is schrijfbaar, ti niet)
```

Wachten op een vaste tijd — nauwkeuriger dan een telluslus:

```basic
100 t=ti
110 if ti-t<30 then 110    : rem een halve seconde wachten
```

Eenvoudige vertraging (vuistregel: ~1000 iteraties ≈ 1 seconde):

```basic
200 for d=1 to 500:next d
```

Beeldsynchronisatie tegen flikkering bij animatie:

```basic
300 wait 53265,128         : rem wacht tot de rasterstraal onder regel 256 is
```

`wait adres,masker1[,masker2]` blijft wachten tot
`(peek(adres) xor masker2) and masker1 <> 0`. Let op: als die voorwaarde
nooit waar wordt, hangt het programma en helpt alleen nog run/stop+restore.

---

## 10. Bestanden en randapparatuur

```basic
10 open 1,8,2,"data,s,w"    : rem schrijven naar disk (seq)
20 print#1,"regel 1"
30 close 1
40 open 1,8,2,"data,s,r"    : rem lezen
50 input#1,a$
60 close 1
```

| Apparaat | Nummer |
|---|---:|
| datassette | 1 |
| printer | 4 (of 5) |
| diskdrive | 8 t/m 11 |

Bestandstypen: `s` = sequentieel, `p` = program, `u` = user, `r` = relatief.
Modus: `r` = lezen, `w` = schrijven, `a` = toevoegen.

**Statusvariabele `st`** na elke I/O-operatie:

| Waarde | Betekenis |
|---:|---|
| 0 | in orde |
| 64 | einde bestand bereikt |
| −128 | apparaat niet aanwezig |

Teken voor teken lezen tot het einde:

```basic
10 open 1,8,2,"data,s,r"
20 get#1,a$
30 if st<>0 then 60
40 print a$;
50 goto 20
60 close 1:end
```

Foutkanaal van de drive uitlezen (altijd doen na een mislukte operatie):

```basic
10 open 15,8,15
20 input#15,en,em$,et,es
30 print en;em$;et;es
40 close 15
```

Printer:

```basic
10 open 4,4:print#4,"hallo printer":close 4
20 open 4,4:cmd 4:list:print#4:close 4   : rem listing naar de printer
```

Sluit **altijd** elk bestand met `close`. Een niet-gesloten bestand
verliest data en blokkeert het apparaat.

Programma's:

```text
save "naam",8      load "naam",8      verify "naam",8
load "naam",8,1    (laden op het originele adres, voor machinetaal/data)
```

---

## 11. Performance

BASIC V2 is traag. Deze maatregelen leveren het meeste op, in volgorde
van effect:

1. **Zet variabelen die je vaak gebruikt als eerste in het programma.**
   BASIC zoekt variabelen lineair in volgorde van eerste toekenning.
   ```basic
   10 x=0:y=0:j=0:o=0:v=53248:sm=1024
   ```
2. **Bereken vaste adressen en constanten vooraf**, buiten de lus.
   ```basic
   10 v=53248:se=v+21:sm=1024
   100 poke se,peek(se) or 1
   ```
   in plaats van `poke 53248+21,peek(53248+21) or 1`.
3. **Zet de hoofdlus en veelgebruikte subroutines op lage regelnummers.**
   Een sprong terug wordt vanaf het begin van het programma gezocht.
4. **Meerdere statements per regel.** Minder regels = minder linkstappen.
5. **Geen `rem` in een hete lus.** Commentaarregels kosten scantijd.
   Zet toelichting in een kopblok bovenaan.
6. **Vermijd `a%`-integers in berekeningen.** BASIC rekent intern altijd
   in floating point en converteert integers heen en terug. Gebruik `%`
   alleen in grote arrays om geheugen te sparen (2 bytes i.p.v. 5).
7. **Vermijd stringconcatenatie in lussen.** Dat veroorzaakt garbage
   collection en onvoorspelbare pauzes.
8. **Gebruik logische expressies in plaats van `if`** waar het kan:
   ```basic
   100 x=x+(j and 8)/8-(j and 4)/4
   ```
9. Voor raster-, muziek- en scroll-code: **verplaats naar 6502 machinetaal**
   en roep aan met `sys`. Zeg dit expliciet wanneer een eis in BASIC
   niet haalbaar is.

Vrij geheugen controleren:

```basic
10 f=fre(0):print f-65536*(f<0)
```

---

## 12. Foutmeldingen en diagnose

| Melding | Meest voorkomende oorzaak |
|---|---|
| `?syntax error` | Keyword in variabelenaam; dialect-constructie; ontbrekend haakje/komma; niet-getokeniseerde operator (§2.4); afkorting zoals `?` in de bron; `restore` met regelnummer (§4.5a) |
| `?undef'd statement error` | `goto`/`gosub`/`then <n>` naar een niet-bestaande regel |
| `?next without for` | `next` zonder `for`, of met `goto` een lus uitgesprongen |
| `?return without gosub` | Geen `end` vóór het subroutineblok |
| `?out of data error` | Meer `read` dan `data`; geen eindmarkering |
| `?illegal quantity error` | `poke`-waarde buiten 0–255; negatief argument bij `sqr`/`log`; `mid$` met positie 0; `asc("")` |
| `?overflow error` | Getal groter dan 1.7E38 |
| `?out of memory error` | Programma + variabelen te groot; te diepe `gosub`/`for`-nesting; met `goto` uit een lus gesprongen |
| `?bad subscript error` | Array-index buiten de gedimensioneerde grootte |
| `?redim'd array error` | Dezelfde array twee keer `dim`'d, of gebruikt vóór `dim` |
| `?division by zero error` | Deling door 0 |
| `?type mismatch error` | String waar een getal hoort of andersom (`a$=5`, `a="x"`) |
| `?string too long error` | String langer dan 255 tekens |
| `?formula too complex` | Te veel geneste string-expressies; splits de regel |
| `?can't continue error` | `cont` na een wijziging of na `end` |
| `?undef'd function error` | `fn` gebruikt zonder `def fn` |
| `?device not present error` | Drive/printer uit of verkeerd apparaatnummer |
| `?file not found` / `?file open` / `?file not open` | Bestandsbeheer; controleer `open`/`close` |

### Diagnoseroute bij een onverwachte `?syntax error`

1. Bekijk de **originele regel**, niet een moderne herschrijving ervan.
2. Controleer elke variabelenaam tegen de tokentabel (§3.1).
3. Controleer of twee variabelen op de eerste twee tekens botsen.
4. Controleer haakjes en komma's.
5. Controleer of alle gebruikte statements in §3.1 staan.
6. Controleer of de PRG met `invert_case=True` is gemaakt (§2.3).
7. Controleer of operatoren getokeniseerd zijn (§2.4).
8. Pas dán pas de logica aan.

Converteer nooit automatisch naar een ander BASIC-dialect om een fout
te "omzeilen".

---

## 13. Verificatiechecklist — loop deze af vóór elke oplevering

**Taal**
- [ ] Alle code in kleine letters.
- [ ] Alleen keywords uit de tabel in §3.1.
- [ ] Geen `else`, `while`, `do`, `cls`, `locate`, `sprite`, `sound`, enz.
- [ ] Geen afkortingen (`?`, `pO`) in de broncode.

**Regels**
- [ ] Elke regel heeft een regelnummer, stappen van 10.
- [ ] Regelnummers strikt oplopend, geen duplicaten, 0–63999.
- [ ] Geen regel langer dan 80 tekens.

**Variabelen**
- [ ] Alle variabelen uniek in de **eerste twee tekens**.
- [ ] Geen variabelenaam bevat een BASIC-keyword als deelstring.
- [ ] `st`, `ti`, `ti$` niet als eigen naam gebruikt.
- [ ] Naamregister in een `rem`-kopblok bovenaan.
- [ ] Strings eindigen op `$`, integers op `%`, types niet door elkaar.

**Structuur**
- [ ] Elke `for` heeft precies één bijbehorende `next` met dezelfde variabele.
- [ ] Nooit met `goto` een `for`-lus in- of uitgesprongen.
- [ ] Elke `gosub` heeft een `return`; `end` staat vóór het subroutineblok.
- [ ] Elk `goto`/`gosub`/`then <n>`-doel bestaat.
- [ ] `on ... goto/gosub` heeft een doorval-afhandeling voor 0 en te grote waarden.
- [ ] Aantal `read`-operaties past bij de `data`, of er is een eindmarkering.
- [ ] Tekst in `data` staat tussen dubbele quotes.
- [ ] `restore` heeft geen regelnummer (BASIC V2; §4.5a).
- [ ] Herhaalbare `data` (melodie, kaarten) is in arrays geladen (§4.5a).
- [ ] `get a$`-wachtlopen gebruiken `;` (geen return) om scroll te voorkomen (§9.1a).
- [ ] Vaste schermindeling gebruikt KERNAL PLOT, geen `print` op onderste rijen (§6.5).

**Hardware**
- [ ] Alle `poke`-adressen kloppen (§14 en de appendix).
- [ ] Alle `poke`-waarden liggen tussen 0 en 255.
- [ ] Bitregisters worden gemaskeerd met `or` / `and (255-b)`, bestaande bits blijven staan.
- [ ] Spritedata is precies 63 bytes; pointer = adres/64; blok 12 niet gebruikt.
- [ ] X > 255 wordt via register 53264 afgehandeld, in beide richtingen.
- [ ] SID: alle 25 registers gewist, volume gezet, gate aan én weer uit.
- [ ] Schermgeheugen krijgt **schermcodes**, `print`/`chr$` krijgt **PETSCII**.
- [ ] Color ram wordt meegezet bij het poken van tekens.
- [ ] Botsingsregisters 53278/53279 worden maar één keer per lus gelezen.

**Tooling**
- [ ] `c64_syntax_checker.py` geeft 0 ERRORs.
- [ ] Alle WARNINGs zijn ofwel opgelost, ofwel een gedocumenteerde false positive (§2.2).
- [ ] PRG gebouwd met `invert_case=True` / `-i`.
- [ ] Getest in VICE of op hardware.

**Opruimen**
- [ ] Sprites uitgezet en SID-volume op 0 bij programmaeinde.
- [ ] Alle geopende bestanden gesloten.

---

## 14. Kant-en-klare templates

Alle templates hieronder zijn gevalideerd: 0 ERRORs in de syntax checker
en succesvol getokeniseerd naar PRG.

### 14.1 Basisskelet

```basic
10 rem ---- titel ----
20 rem variabelen: v=vic sm=scherm cm=kleur
30 gosub 1000
40 gosub 2000
50 end
1000 rem -- initialisatie --
1010 v=53248:sm=1024:cm=55296
1020 poke 53280,0:poke 53281,0:poke 646,1
1030 print chr$(147)
1040 return
2000 rem -- hoofdlogica --
2010 print "hallo commodore 64"
2020 return
```

### 14.2 Menu met invoervalidatie

```basic
10 rem menu
20 print chr$(147)
30 print "1. starten"
40 print "2. instellingen"
50 print "3. stoppen"
60 get k$:if k$="" then 60
70 k=val(k$)
80 if k<1 or k>3 then 60
90 on k goto 100,200,300
100 print "starten":goto 20
200 print "instellingen":goto 20
300 print "tot ziens":end
```

### 14.3 Sprite besturen met joystick (poort 2)

```basic
10 rem sprite met joystick
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

### 14.4 SID-melodiespeler

```basic
10 rem sid melodie
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

### 14.5 Spelskelet met scherm-poking

```basic
10 rem ---- game skelet ----
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
2000 rem teken scherm
2010 print chr$(19);"score:";sc;" levens:";lv
2020 return
3000 rem hoofdlus
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

## Appendix A — Geheugenkaart, alleen wat je in BASIC nodig hebt

### Zero page en systeemvariabelen

| Adres | Functie |
|---:|---|
| 43–44 | Begin BASIC-programma (standaard 2049 = $0801) |
| 45–46 | Begin variabelen |
| 51–52 | Begin stringgeheugen (groeit omlaag) |
| 55–56 | Einde BASIC-geheugen (standaard 40960 = $A000) |
| 145 | Stop-toets: 127 = ingedrukt |
| 197 | Matrixcode van de nu ingedrukte toets |
| 198 | Lengte toetsenbordbuffer |
| 199 | Reverse-modus: 0 = normaal, 18 = invers |
| 211 | Cursorkolom (0–39) |
| 214 | Cursorregel (0–24) |
| 631–640 | Toetsenbordbuffer |
| 646 | Huidige tekstkleur |
| 648 | Hoge byte schermgeheugen (standaard 4 = 1024) |
| 650 | Toetsherhaling (128 = alles herhalen) |
| 653 | Shift/commodore/ctrl-status |
| 704 | Vrij, bruikbaar als spriteblok 11 |
| 768–819 | Systeemvectoren — **niet gebruiken** |
| 785–786 | Vector voor `usr()` |
| 788–789 | IRQ-vector (standaard $EA31 = 59953) |
| 808–809 | Stop-routine (237 = normaal, 239 = run/stop uit) |
| 828–1019 | Datassettebuffer — bruikbaar als spriteblok 13, 14, 15 |
| 1024–2023 | Schermgeheugen (schermcodes) |
| 2040–2047 | Sprite pointers |
| 2049 | Start BASIC-programma |

### VIC-II (v = 53248)

| Adres | Offset | Functie |
|---:|---:|---|
| 53248–53263 | v+0…v+15 | Sprite X/Y 0..7 |
| 53264 | v+16 | Sprite X bit 8 |
| 53265 | v+17 | Schermcontrole 1: rasterregel bit 8, scherm aan/uit, bitmap, 24/25 rijen |
| 53266 | v+18 | Huidige rasterregel (lezen) / interruptregel (schrijven) |
| 53269 | v+21 | Sprite aan/uit |
| 53270 | v+22 | Schermcontrole 2: multicolor tekst, 38/40 kolommen |
| 53271 | v+23 | Sprite Y-vergroting |
| 53272 | v+24 | Geheugenopzet: scherm- en tekengeheugen (21 = grafisch, 23 = kleine letters) |
| 53273 | v+25 | Interruptstatus |
| 53274 | v+26 | Interruptcontrole |
| 53275 | v+27 | Sprite-prioriteit |
| 53276 | v+28 | Sprite multicolor |
| 53277 | v+29 | Sprite X-vergroting |
| 53278 | v+30 | Sprite–sprite botsing (lezen wist) |
| 53279 | v+31 | Sprite–achtergrond botsing (lezen wist) |
| 53280 | v+32 | Randkleur |
| 53281 | v+33 | Achtergrondkleur |
| 53282–53284 | v+34…v+36 | Extra achtergrondkleuren 1–3 |
| 53285–53286 | v+37, v+38 | Sprite multicolor 1 en 2 |
| 53287–53294 | v+39…v+46 | Kleur sprite 0..7 |

### SID (s = 54272)

| Adres | Offset | Functie |
|---:|---:|---|
| 54272–54278 | s+0…s+6 | Stem 1: freq lo/hi, puls lo/hi, controle, attack/decay, sustain/release |
| 54279–54285 | s+7…s+13 | Stem 2, zelfde indeling |
| 54286–54292 | s+14…s+20 | Stem 3, zelfde indeling |
| 54293–54295 | s+21…s+23 | Filter: cutoff lo/hi, routering + resonantie |
| 54296 | s+24 | Volume (bits 0–3) en filtermodus |
| 54299 | s+27 | Golfvorm-uitgang stem 3 (lezen — bruikbaar als random) |

### Overig

| Adres | Functie |
|---:|---|
| 55296–56295 | Color ram (alleen bits 0–3) |
| 56320 | CIA1 poort A — **joystick poort 2** |
| 56321 | CIA1 poort B — joystick poort 1 + toetsenbord |
| 56333 | CIA1 interruptcontrole |
| 56576 | VIC-bankselectie (bits 0–1, geïnverteerd) |
| 64738 | `sys 64738` = soft reset |

---

## Appendix B — Snelle correctietabel

Wat de AI vaak fout doet, en wat het moet zijn:

| Fout | Goed |
|---|---|
| `if a=1 then x=1 else x=2` | `if a=1 then x=1` / `if a<>1 then x=2` |
| `cls` | `print chr$(147)` |
| `while a<10 ... wend` | `100 if a>=10 then 200` … `190 goto 100` |
| `locate 10,5:print "x"` | `poke 781,5:poke 782,10:poke 783,0:sys 65520:print "x"` |
| `sprite 1,1,2` | `poke 53269,peek(53269) or 2:poke 53288,2` |
| `sound 1,440,10` | zie §8: SID-registers pokeen |
| `color 0,1` | `poke 53281,0:poke 646,1` |
| `score=0` | `sc=0` (`score` bevat `or`) |
| `total=0` | `tt=0` (`total` bevat `to`) |
| `? "hallo"` | `print "hallo"` |
| `poke 1024,65` voor de letter a | `poke 1024,1` (schermcode) |
| `poke 53248+21,1` in een lus | `v=53248:se=v+21` … `poke se,1` |
| `poke 53269,1` (zet andere sprites uit) | `poke 53269,peek(53269) or 1` |
| `data een,twee` | `data "een","twee"` |
| `Bas2Prg().convert(src)` | `Bas2Prg(invert_case=True).convert(src)` |

---

*Bronnen: C64-Wiki (BASIC V2.0, C64-Commands, Color), Commodore 64
memory map, Commodore 64 Programmer's Reference Guide, en de projecttools
`bas2prg.py` en `c64_syntax_checker.py`. Alle codevoorbeelden in dit
document zijn geverifieerd met de syntax checker en de PRG-tokenizer.*
