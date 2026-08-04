# Argentine Football Club Matching Engine

> A fuzzy matching system to reconcile football club names across heterogeneous data sources — built for the [Ligas Argentinas](https://argentinaleagues.web.app/) project.

## The Problem

When building a dataset of 1,000+ Argentine football clubs across multiple leagues and historical sources, the **same club can appear in very different forms** depending on the source:

| Source A | Source B |
|---|---|
| `Ferro Carril Oeste (Buenos Aires)` | `Ferrocarril Oeste` |
| `9 de Julio – Rafaela` | `9 de Julio (Rafaela)` |
| `Cruz del Sur (Bariloche) (Bariloche (Ñirihuau))` | `Cruz del Sur – Zona Sur` |
| `FC Atlántico (MDP)` | `Futbol Club Atlántico (Mar del Plata)` |
| `1. Racing (Puerto Nuevo)` | `Racing – Puerto Nuevo` |

Simple string matching fails on all of these. This engine handles them correctly.

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

### Edge Cases Handled

- **Nested parentheses** — `"Club (City) (City (Zone))"` → extracts innermost location
- **Number prefixes** — `"1. 9 de Julio"` strips the list number, keeps the club number
- **Historical names** — configurable alias dictionary maps old names to current ones
- **City abbreviations** — `"MDP"` → `"Mar del Plata"`, `"CABA"` → `"Buenos Aires"`
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
══════════════════════════════════════════════════════════════
  Argentine Football Club Matching Engine — Demo
══════════════════════════════════════════════════════════════
  Reference list  : 20 clubs  (data/sample_clubs.txt)
  Alternate list  : 20 clubs  (data/sample_clubs_alt.txt)

  The same clubs appear with different names, formats,
  and spelling across different sources. The engine
  reconciles them automatically.

══════════════════════════════════════════════════════════════
  ✅  MATCHES  (18)
══════════════════════════════════════════════════════════════
  ...
  📊  SUMMARY
  Automatic matches    : 18
  Manual matches       : 0
  Only in REFERENCE    : 2
  Only in ALTERNATE    : 2
```

## Repository Structure

```
ligas-argentinas-matching/
├── comparar_listas.py         # Core matching engine
├── demo.py                    # Non-interactive demonstration
├── requirements.txt
├── data/
│   ├── sample_clubs.txt       # Reference list (fictional clubs)
│   └── sample_clubs_alt.txt   # Same clubs with name variants
└── .gitignore
```

## Live Application

The complete dataset (1,000+ real clubs, full historical records) powers the deployed application:

**👉 [https://argentinaleagues.web.app/](https://argentinaleagues.web.app/)**

The app was built with React and Firebase, with all club data sourced and reconciled using this matching engine.

## Tech Stack

- **Python 3.8+**
- [`thefuzz`](https://github.com/seatgeek/thefuzz) — Levenshtein-based fuzzy string matching
- `python-Levenshtein` — C extension for speed (~10x faster than pure Python)
- `unicodedata` — accent stripping and Unicode normalization (stdlib)
- `re` — regex-based alias resolution and parsing (stdlib)

## License

MIT
