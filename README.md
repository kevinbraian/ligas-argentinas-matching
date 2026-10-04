# Argentine Football Club Matching Engine

> A fuzzy matching system to reconcile football club names across heterogeneous data sources — built for the [Ligas Argentinas](https://ligasargentinas.com.ar/) project.

## The Problem

When building a dataset of 2,600+ Argentine football clubs across multiple leagues and historical sources, the **same club can appear in very different forms** depending on the source:

| Source A | Source B |
|---|---|
| `Ferro Carril Oeste (Buenos Aires)` | `Ferrocarril Oeste (CABA)` |
| `9 de Julio – Rafaela` | `9 de Julio (Rafaela)` |
| `Cruz del Sur (Bariloche) (Bariloche (Ñirihuau))` | `Cruz del Sur – Ñirihuau` |
| `FC Atlántico (MDP)` | `Futbol Club Atlántico (Mar del Plata)` |
| `1. Racing (Puerto Nuevo)` | `Racing – Puerto Nuevo` |

Simple string matching fails on all of these. This engine matches all five automatically.

## The Solution

A multi-step scoring pipeline:

```
Raw text line
    │
    ▼
① Unicode normalization   — strip accents, lowercase
    │
    ▼
② Alias resolution        — "Ferro Carril" → "ferro", "FC" → "futbol club"
    │
    ▼
③ Stopword stripping      — remove "Club", "Atlético", "Deportivo", etc.
    │
    ▼
④ City extraction         — handles –, /, (), and nested ((()))
    │
    ▼
⑤ Fuzzy core matching     — fuzz.token_set_ratio (thefuzz)
    │
    ▼
⑥ City bonus / penalty    — +100 if cities match, −1000 if they conflict
    │
    ▼
⑦ Length penalty          — penalizes word-count differences
    │
    ▼
Score ≥ 160 → automatic match
Score 90–159 → interactive confirmation (optional)
Score < 90  → no match
```

**The city is what makes a match automatic.** A perfect name match scores 100, and only the +100 city bonus carries a pair past 160. When either side has no city the pair cannot score above 100, so it is left for interactive confirmation instead of being matched on the name alone — homonymous clubs in different cities are common in Argentine football, and a name is not proof.

### Edge Cases Handled

- **Nested parentheses** — `"Club (City) (City (Zone))"` → extracts innermost location
- **Number prefixes** — `"1. 9 de Julio"` strips the list number (`1.`, `1)`, `1]`), keeps the club number
- **Historical names** — configurable alias dictionary maps old names to current ones
- **City abbreviations** — `"MDP"` → `"Mar del Plata"`, `"SDE"` → `"Santiago del Estero"`, `"CABA"` → `"Buenos Aires"`
- **Multiple separator styles** — `–`, ` - `, ` / `, `()`, nested `(())`

## Quick Start

```bash
# Install dependencies
pip install thefuzz python-Levenshtein

# Run the demo (sample datasets included)
python demo.py

# Run with debug scores
python demo.py --debug

# Compare your own lists
python comparar_listas.py my_list_a.txt my_list_b.txt
python comparar_listas.py my_list_a.txt my_list_b.txt --no-interactivo
```

## Expected Demo Output

```
════════════════════════════════════════════════════════════
  Argentine Football Club Matching Engine — Demo
════════════════════════════════════════════════════════════
  Reference list  : 19 clubs  (data/sample_clubs.txt)
  Alternate list  : 19 clubs  (data/sample_clubs_alt.txt)

  The same clubs appear with different names, formats,
  and spelling across different sources. The engine
  reconciles them automatically.


════════════════════════════════════════════════════════════
  ✅  MATCHES  (16)
════════════════════════════════════════════════════════════
  REFERENCE                           → ALTERNATE
  ────────────────────────────────────────────────────────────
     12 de Octubre (posadas)
     25 de Mayo (san rafael)
     9 de Julio (rio cuarto)
     9 de Julio (Ciudad Ejemplo) (ciudad ejemplo) → 9 de Julio (ciudad ejemplo)
     Asociación Atlética Norte (rio grande)   → At. Norte (rio grande)
     Belgrano (ciudad norte)                  → Club Belgrano (ciudad norte)
     Club Deportivo Estrella (villa nueva)    → Deportivo Estrella (villa nueva)
     Cruz del Norte (Bariloche) (zona sur)    → Cruz del Norte (zona sur)
     Deportivo del Valle (General Roca) (valle inferior) → Deportivo del Valle (valle inferior)
     FC Pioneros (corrientes)                 → Futbol Club Pioneros (corrientes)
     Ferro Carril Central (tucuman)           → Ferrocarril Central (tucuman)
     Ferroviario Andino (mendoza)             → FF CC Andino (mendoza)
     Foot-Ball Club Atlántico (mar del plata) → Football Club Atlántico (mar del plata)
     Juventud Unida (La Pampa) (santa rosa)   → Juventud Unida (santa rosa)
     Racing (puerto nuevo)                    → Club Racing (puerto nuevo)
     Sociedad Deportiva Poniente (san martin) → S.D. Poniente (san martin)

  (❓ = manually confirmed)

════════════════════════════════════════════════════════════
  ❌  ONLY IN REFERENCE  (3)
════════════════════════════════════════════════════════════
  Huracán
  Olimpo
  San Lorenzo (villa del sur)

════════════════════════════════════════════════════════════
  ➕  ONLY IN ALTERNATE  (3)
════════════════════════════════════════════════════════════
  Huracan
  Olimpo
  San Lorenzo de Villa del Sur

════════════════════════════════════════════════════════════
  📊  SUMMARY
════════════════════════════════════════════════════════════
  Automatic matches    : 16
  Manual matches       : 0
  Only in REFERENCE     : 3
  Only in ALTERNATE     : 3
  ────────────────────────────────────────
  Total list A         : 19
  Total list B         : 19
```

Cities are printed normalized (lowercase, no accents, abbreviations expanded); a match whose two sides read the same is printed once, without the arrow.

> The 3 unmatched pairs are the sample's edge cases. `Huracán` / `Huracan` and `Olimpo` / `Olimpo` have no city on either side, so they stop at a score of 100: the demo runs non-interactively, and in the real workflow they are confirmed by hand. `San Lorenzo (Villa del Sur)` vs `San Lorenzo de Villa del Sur` is a real miss: the second form hides the city inside the name, so there is no city bonus and the two extra words cost 20 points, leaving it at 80 — below even the interactive band.

## Repository Structure

```
ligas-argentinas-matching/
├── comparar_listas.py         # Core matching engine
├── demo.py                    # Non-interactive demonstration
├── requirements.txt
├── data/
│   ├── sample_clubs.txt       # Reference list (fictional clubs)
│   └── sample_clubs_alt.txt   # Same clubs with name variants
├── LICENSE
└── .gitignore
```

## Live Application

The complete dataset (2,600+ real clubs, 136 seasons from 1891 to 2026) powers the deployed application:

**👉 [https://ligasargentinas.com.ar/](https://ligasargentinas.com.ar/)**

The app is a React site served from Cloudflare Pages. This engine was written to cross-check its dataset against official AFA and Consejo Federal club lists, to find missing and duplicated clubs.

As the project grew, reconciliation moved to a broader toolchain — tournament-by-tournament cross-checks against Wikipedia and RSSSF participant tables, and Argentina's official gazetteer (Georef) for cities and provinces. This repository is the original, standalone list-vs-list engine.

## Tech Stack

- **Python 3.8+**
- [`thefuzz`](https://github.com/seatgeek/thefuzz) — Levenshtein-based fuzzy string matching
- `python-Levenshtein` — C extension for speed (~10x faster than pure Python)
- `unicodedata` — accent stripping and Unicode normalization (stdlib)
- `re` — regex-based alias resolution and parsing (stdlib)

## License

MIT
