"""
comparar_listas.py
==================
Compares two lists of football clubs (txt) using fuzzy matching,
city-based scoring, and alias normalization.

Usage:
    python comparar_listas.py list_a.txt list_b.txt [options]

Options:
    --umbral-exacto   INT   Min score for automatic match (default: 160)
    --umbral-dudoso   INT   Min score for interactive mode (default: 90)
    --no-interactivo        Mark borderline cases as "no match" automatically
    --debug                 Show internal scores

Output (console):
    ✅  Automatic matches (A → B)
    ❓  Borderline matches confirmed by user
    ❌  Only in A (no equivalent in B)
    ➕  Only in B (no equivalent in A)

Built for the Ligas Argentinas project:
    https://ligasargentinas.com.ar/
"""

import sys
import re
import unicodedata
import argparse
from thefuzz import process, fuzz

# ══════════════════════════════════════════════════════════
#  DEFAULT CONFIGURATION
# ══════════════════════════════════════════════════════════
UMBRAL_EXACTO     = 160   # final score >= this → automatic match
UMBRAL_DUDOSO     = 90    # final score >= this → interactive mode
UMBRAL_NOMBRE_MIN = 70    # name floor before evaluating city

# ══════════════════════════════════════════════════════════
#  NAME ALIASES
#  External variants → canonical form.
#  Keys in lowercase without accents (remover_acentos runs first).
# ══════════════════════════════════════════════════════════
ALIAS = {
    # Railway clubs — multiple common spellings
    'ferro carril': 'ferro',      # with space — must come BEFORE 'ferrocarril'
    'ferrocarril':  'ferro',
    'ff cc':        'ferro',
    'ffcc':         'ferro',
    # Morphological variants
    'argentinos':   'argentino',
    'deportiva':    'deportivo',
    'sociedad':     'social',
    # Football — lowercase variants
    'foot-ball':    'football',
    'foot ball':    'football',   # with space — must come BEFORE stopword regex
    'futbol':       'football',
    # Abbreviations
    'fc':           'futbol club',
    # Add more as detected in your data source
}

# ══════════════════════════════════════════════════════════
#  CITY ALIASES
#  Abbreviations → full name. Exact match on already-normalized city.
# ══════════════════════════════════════════════════════════
ALIAS_CIUDADES = {
    'mdp':  'mar del plata',
    'sde':  'santiago del estero',
    'caba': 'buenos aires',
    # Add more abbreviations as needed
}

# ══════════════════════════════════════════════════════════
#  NORMALIZATION
# ══════════════════════════════════════════════════════════
def remover_acentos(texto):
    if not texto:
        return ""
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).lower()

def aplicar_alias(texto):
    for variante, canonico in ALIAS.items():
        texto = re.sub(rf'\b{re.escape(variante)}\b', canonico, texto)
    return texto

def aplicar_alias_ciudad(ciudad):
    """Expands city abbreviations to their full name."""
    return ALIAS_CIUDADES.get(ciudad.strip(), ciudad)

STOPWORDS = re.compile(
    r'\b(de|del|la|las|los|y|e|club|atletico|atletica|social|deportivo|'
    r'deportiva|mutual|foot\s*ball|football|fc|sd|ca|ac)\b'
)

def normalizar_nucleo(texto, ciudad_a_strip=None):
    """
    Operation order (critical):
      1. remover_acentos + lowercase
      2. strip internal parentheses
      3. aplicar_alias  ← before stopwords to capture full phrases
      4. strip stopwords
      5. strip city (with empty-guard)
      6. strip non-alphanumeric
    """
    texto = remover_acentos(texto)
    texto = re.sub(r'\(.*?\)', '', texto)
    texto = aplicar_alias(texto)
    texto = STOPWORDS.sub('', texto)

    # City strip: removes the city from the core if already captured separately.
    # GUARD: if stripping would empty the core (name == city, e.g. "Grand Bourg"),
    # keep the text without stripping.
    if ciudad_a_strip:
        texto_con_strip = texto
        for palabra in ciudad_a_strip.split():
            if len(palabra) > 3:
                texto_con_strip = re.sub(rf'\b{re.escape(palabra)}\b', '', texto_con_strip)
        resultado_strip = ' '.join(re.sub(r'[^a-z0-9\s]', '', texto_con_strip).split())
        if resultado_strip:
            texto = texto_con_strip

    texto = re.sub(r'[^a-z0-9\s]', '', texto)
    return ' '.join(texto.split())

# ══════════════════════════════════════════════════════════
#  LINE PARSER
#  Separators take priority over parentheses.
#  Covers "Name – City (Province)" → city without province.
# ══════════════════════════════════════════════════════════
def extraer_ultimo_parentesis(linea):
    """
    Extracts the content of the last parenthesis, even if nested.
    "Cruz del Sur (Bariloche) (Bariloche (Ñirihuau))" → content="Bariloche (Ñirihuau)", name="Cruz del Sur (Bariloche)"
    """
    ultima_cierre = linea.rfind(')')
    if ultima_cierre == -1:
        return None, linea
    profundidad = 0
    for i in range(ultima_cierre, -1, -1):
        if linea[i] == ')':
            profundidad += 1
        elif linea[i] == '(':
            profundidad -= 1
            if profundidad == 0:
                contenido = linea[i+1:ultima_cierre].strip()
                nombre    = linea[:i].strip()
                return contenido, nombre
    return None, linea

def ciudad_de_contenido(contenido):
    """
    Extracts the city from a parenthesis content, handling nested cases.
    "Bariloche (Ñirihuau)" → "Ñirihuau"   (takes the nested one)
    "Rafaela"              → "Rafaela"     (direct)
    "Paso de los Libres, Corrientes" → "Paso de los Libres"  (before comma)
    """
    m = re.search(r'\(([^)]+)\)\s*$', contenido)
    if m:
        return m.group(1).split(',')[0].strip()
    return contenido.split(',')[0].strip()

def parsear_linea(linea):
    """
    Extracts (original_name, normalized_city) from a text line.

    Priority order:
      1. Explicit separator (–, -, /)
           "Cruz del Sur – Ñirihuau"                      → name="Cruz del Sur",         city="nirihuau"
           "A.P.I.N.T.A. – Mercedes (Province)"           → name="A.P.I.N.T.A.",         city="mercedes"
      2. Parentheses (simple, double, or nested) — using extraer_ultimo_parentesis
           "Belgrano (Córdoba)"                           → name="Belgrano",              city="cordoba"
           "9 de Julio (Rafaela) (Rafaela)"               → name="9 de Julio (Rafaela)", city="rafaela"
           "Cruz del Sur (Bariloche) (Bariloche (Zone))"  → name="Cruz del Sur (Bariloche)", city="zone"
      3. Name only
    """
    # Strip leading numbering ONLY if followed by period/parenthesis/bracket + uppercase letter.
    # This ensures "9 de Julio" and "12 de Octubre" keep their initial number.
    linea = re.sub(r'^\d+[\.)\]]\s+', '', linea).strip()   # "95. Name", "95) Name" or "95] Name"
    linea = re.sub(r'^\d+\s*[-\u2013]\s+(?=[A-ZÁÉÍÓÚÑ])', '', linea).strip()  # "95 - Name" but not "9 de Julio"
    if not linea:
        return None, None

    # ── 1. Explicit separators (max priority) ─────────────────────────────
    for sep in ['–', ' - ', ' / ']:
        if sep in linea:
            partes    = linea.split(sep, 1)
            nombre    = partes[0].strip()
            ubicacion = partes[1].strip() if len(partes) > 1 else ""
            # Remove province in parentheses at end of location
            ubicacion = re.sub(r'\s*\(.*?\)\s*$', '', ubicacion).strip()
            return nombre, aplicar_alias_ciudad(remover_acentos(ubicacion))

    # ── 2. Parentheses (any nesting level) ────────────────────────────────
    contenido_par, nombre_par = extraer_ultimo_parentesis(linea)
    if contenido_par is not None and nombre_par:
        ciudad_raw = ciudad_de_contenido(contenido_par)
        return nombre_par, aplicar_alias_ciudad(remover_acentos(ciudad_raw))

    # ── 3. Name only ──────────────────────────────────────────────────────
    return linea.strip(), ""

def cargar_lista(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lineas = [l.strip() for l in f if l.strip() and not l.strip().startswith('#')]
    except FileNotFoundError:
        print(f"❌ File not found: {path}")
        sys.exit(1)

    entradas = []
    for linea in lineas:
        nombre, ciudad = parsear_linea(linea)
        if nombre:
            entradas.append((nombre, ciudad or ""))
    return entradas

# ══════════════════════════════════════════════════════════
#  CITY VALIDATION
# ══════════════════════════════════════════════════════════
def ciudad_coincide(ciudad_a, ciudad_b):
    """
    True  → match (bonus +100)
    False → no match (penalty -1000)
    None  → one is empty (neutral)
    """
    if not ciudad_a or not ciudad_b:
        return None
    if ciudad_a in ciudad_b or ciudad_b in ciudad_a:
        return True
    if fuzz.partial_ratio(ciudad_a, ciudad_b) >= 85:
        return True
    return False

# ══════════════════════════════════════════════════════════
#  SCORING
# ══════════════════════════════════════════════════════════
def calcular_score(nucleo_a, ciudad_a, nucleo_b, ciudad_b):
    """
    Returns (base_score, final_score).

    base_score must exceed UMBRAL_NOMBRE_MIN before evaluating city.
    Prevents city bonus from rescuing completely different names.
    """
    score_base = fuzz.token_set_ratio(nucleo_a, nucleo_b)
    if score_base < UMBRAL_NOMBRE_MIN:
        return score_base, -9999

    score = score_base
    resultado_ciudad = ciudad_coincide(ciudad_a, ciudad_b)
    if resultado_ciudad is True:
        score += 100
    elif resultado_ciudad is False:
        score -= 1000

    dif    = abs(len(nucleo_a.split()) - len(nucleo_b.split()))
    score -= dif * 10

    return score_base, score

# ══════════════════════════════════════════════════════════
#  MAIN COMPARISON
# ══════════════════════════════════════════════════════════
def comparar(lista_a, lista_b, interactivo=True, debug=False):
    """
    Returns:
        matches_exactos  : [(entry_a, entry_b)]
        matches_dudosos  : [(entry_a, entry_b)]  ← manually confirmed
        solo_en_a        : [entry_a]
        solo_en_b        : [entry_b]
    """
    # Build index of B with city strip (same as main workflow)
    nucleos_b = [
        normalizar_nucleo(nombre_b,
            ciudad_a_strip=re.sub(r'\(.*?\)', '', ciudad_b).strip())
        for nombre_b, ciudad_b in lista_b
    ]

    usados_b        = set()
    matches_exactos = []
    matches_dudosos = []
    solo_en_a       = []

    total = len(lista_a)
    for idx_a, (nombre_a, ciudad_a) in enumerate(lista_a):
        nucleo_a = normalizar_nucleo(nombre_a, ciudad_a_strip=ciudad_a)

        if debug:
            print(f"\n🔍 [{nombre_a}] city='{ciudad_a}' | core='{nucleo_a}'")

        candidatos = process.extract(
            nucleo_a,
            nucleos_b,
            scorer=fuzz.token_set_ratio,
            limit=50
        )

        mejor_idx_b = None
        mejor_score = -9999
        mejor_base  = -9999

        for nucleo_b_match, _ in candidatos:
            indices = [i for i, x in enumerate(nucleos_b) if x == nucleo_b_match]
            for idx_b in indices:
                if idx_b in usados_b:
                    continue
                nombre_b, ciudad_b = lista_b[idx_b]
                score_base, score_final = calcular_score(
                    nucleo_a, ciudad_a, nucleo_b_match, ciudad_b
                )
                if debug:
                    print(f"   cand: {nombre_b:<35} ({ciudad_b:<15}) "
                          f"base={score_base:>3}  final={score_final:>5}")
                if score_final > mejor_score:
                    mejor_score = score_final
                    mejor_base  = score_base
                    mejor_idx_b = idx_b

        entrada_a = (nombre_a, ciudad_a)

        if mejor_idx_b is not None and mejor_score >= UMBRAL_EXACTO:
            entrada_b = lista_b[mejor_idx_b]
            matches_exactos.append((entrada_a, entrada_b))
            usados_b.add(mejor_idx_b)
            if debug:
                print(f"   ✅ Auto-match: {lista_b[mejor_idx_b][0]} (base={mejor_base} final={mejor_score})")

        elif mejor_idx_b is not None and mejor_score >= UMBRAL_DUDOSO:
            entrada_b = lista_b[mejor_idx_b]
            if interactivo:
                confirmado = preguntar_usuario(entrada_a, entrada_b, mejor_base, mejor_score, idx_a + 1, total)
                if confirmado:
                    matches_dudosos.append((entrada_a, entrada_b))
                    usados_b.add(mejor_idx_b)
                else:
                    solo_en_a.append(entrada_a)
            else:
                solo_en_a.append(entrada_a)
        else:
            solo_en_a.append(entrada_a)

    solo_en_b = [lista_b[i] for i in range(len(lista_b)) if i not in usados_b]
    return matches_exactos, matches_dudosos, solo_en_a, solo_en_b

# ══════════════════════════════════════════════════════════
#  INTERACTIVE MODE
# ══════════════════════════════════════════════════════════
CYAN   = '\033[96m'
YELLOW = '\033[93m'
GREEN  = '\033[92m'
RED    = '\033[91m'
RESET  = '\033[0m'
BOLD   = '\033[1m'
DIM    = '\033[2m'

def fmt_entrada(nombre, ciudad):
    return f"{nombre} ({ciudad})" if ciudad else nombre

def preguntar_usuario(entrada_a, entrada_b, score_base, score_final, num, total):
    nombre_a, ciudad_a = entrada_a
    nombre_b, ciudad_b = entrada_b

    print(f"\n{'─'*60}")
    print(f"{YELLOW}{BOLD}❓ BORDERLINE [{num}/{total}]{RESET}")
    print(f"  List A : {CYAN}{fmt_entrada(nombre_a, ciudad_a)}{RESET}")
    print(f"  List B : {CYAN}{fmt_entrada(nombre_b, ciudad_b)}{RESET}")
    print(f"  {DIM}Score: base={score_base}  final={score_final}{RESET}")

    while True:
        resp = input(f"  Same club? [{GREEN}y{RESET}/{RED}n{RESET}/{YELLOW}?{RESET}=show cores] ").strip().lower()
        if resp in ('s', 'si', 'sí', 'y', 'yes'):
            return True
        if resp in ('n', 'no'):
            return False
        if resp == '?':
            print(f"    core A: '{normalizar_nucleo(nombre_a, ciudad_a_strip=ciudad_a)}'")
            print(f"    core B: '{normalizar_nucleo(nombre_b, ciudad_a_strip=ciudad_b)}'")
        else:
            print(f"    Type {GREEN}y{RESET}, {RED}n{RESET} or {YELLOW}?{RESET} to see cores.")

# ══════════════════════════════════════════════════════════
#  OUTPUT
# ══════════════════════════════════════════════════════════
def imprimir_resultados(matches_exactos, matches_dudosos, solo_en_a, solo_en_b,
                        nombre_a, nombre_b):
    ancho = 60

    def separador(titulo, color):
        print(f"\n{color}{BOLD}{'═'*ancho}{RESET}")
        print(f"{color}{BOLD}  {titulo}{RESET}")
        print(f"{color}{BOLD}{'═'*ancho}{RESET}")

    todos_matches = matches_exactos + matches_dudosos

    # ── MATCHES ──────────────────────────────────────────
    separador(f"✅  MATCHES  ({len(todos_matches)})", GREEN)
    print(f"  {DIM}{nombre_a:<35} → {nombre_b}{RESET}")
    print(f"  {'─'*ancho}")
    for (na, ca), (nb, cb) in sorted(todos_matches, key=lambda x: x[0][0].lower()):
        marca = "❓" if ((na, ca), (nb, cb)) in matches_dudosos else "  "
        izq   = fmt_entrada(na, ca)
        der   = fmt_entrada(nb, cb)
        if remover_acentos(na) != remover_acentos(nb) or (ca and cb and ca != cb):
            print(f"  {marca} {izq:<40} → {der}")
        else:
            print(f"  {marca} {izq}")
    print(f"\n  {DIM}(❓ = manually confirmed){RESET}")

    # ── ONLY IN A ────────────────────────────────────────
    separador(f"❌  ONLY IN {nombre_a}  ({len(solo_en_a)})", RED)
    for nombre, ciudad in sorted(solo_en_a, key=lambda x: x[0].lower()):
        print(f"  {fmt_entrada(nombre, ciudad)}")

    # ── ONLY IN B ────────────────────────────────────────
    separador(f"➕  ONLY IN {nombre_b}  ({len(solo_en_b)})", CYAN)
    for nombre, ciudad in sorted(solo_en_b, key=lambda x: x[0].lower()):
        print(f"  {fmt_entrada(nombre, ciudad)}")

    # ── SUMMARY ──────────────────────────────────────────
    separador("📊  SUMMARY", YELLOW)
    print(f"  Automatic matches    : {GREEN}{len(matches_exactos)}{RESET}")
    print(f"  Manual matches       : {YELLOW}{len(matches_dudosos)}{RESET}")
    print(f"  Only in {nombre_a:<14}: {RED}{len(solo_en_a)}{RESET}")
    print(f"  Only in {nombre_b:<14}: {CYAN}{len(solo_en_b)}{RESET}")
    print(f"  {'─'*40}")
    total_a = len(matches_exactos) + len(matches_dudosos) + len(solo_en_a)
    total_b = len(matches_exactos) + len(matches_dudosos) + len(solo_en_b)
    print(f"  Total list A         : {total_a}")
    print(f"  Total list B         : {total_b}")
    print()

# ══════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════
def main():
    global UMBRAL_EXACTO, UMBRAL_DUDOSO

    parser = argparse.ArgumentParser(
        description="Compare two football club lists using fuzzy matching."
    )
    parser.add_argument('lista_a',  help="TXT file for list A (e.g. reference.txt)")
    parser.add_argument('lista_b',  help="TXT file for list B (e.g. alternate.txt)")
    parser.add_argument('--umbral-exacto',  type=int, default=UMBRAL_EXACTO,
                        help=f"Min score for automatic match (default: {UMBRAL_EXACTO})")
    parser.add_argument('--umbral-dudoso',  type=int, default=UMBRAL_DUDOSO,
                        help=f"Min score for interactive mode (default: {UMBRAL_DUDOSO})")
    parser.add_argument('--no-interactivo', action='store_true',
                        help="Mark borderline cases as no-match automatically")
    parser.add_argument('--debug', action='store_true',
                        help="Show internal scores during matching")
    args = parser.parse_args()

    UMBRAL_EXACTO = args.umbral_exacto
    UMBRAL_DUDOSO = args.umbral_dudoso

    lista_a = cargar_lista(args.lista_a)
    lista_b = cargar_lista(args.lista_b)

    nombre_a = args.lista_a.replace('.txt', '').upper()
    nombre_b = args.lista_b.replace('.txt', '').upper()

    print(f"\n{BOLD}Comparing:{RESET}")
    print(f"  A: {CYAN}{args.lista_a}{RESET}  ({len(lista_a)} entries)")
    print(f"  B: {CYAN}{args.lista_b}{RESET}  ({len(lista_b)} entries)")
    print(f"  Exact threshold: {UMBRAL_EXACTO}  |  Borderline threshold: {UMBRAL_DUDOSO}")

    if not args.no_interactivo:
        print(f"\n{YELLOW}Interactive mode active.{RESET} "
              f"You'll be prompted for matches with score between "
              f"{UMBRAL_DUDOSO} and {UMBRAL_EXACTO - 1}.")

    matches_exactos, matches_dudosos, solo_en_a, solo_en_b = comparar(
        lista_a, lista_b,
        interactivo=not args.no_interactivo,
        debug=args.debug
    )

    imprimir_resultados(
        matches_exactos, matches_dudosos, solo_en_a, solo_en_b,
        nombre_a, nombre_b
    )

if __name__ == '__main__':
    main()
