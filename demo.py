"""
demo.py
=======
Quick demonstration of the Argentine Football Club Matching Engine.
Loads the sample datasets and runs the matching pipeline without
requiring user interaction.

Usage:
    python demo.py
    python demo.py --debug    # show internal scores
"""

import argparse
from comparar_listas import cargar_lista, comparar, imprimir_resultados

def main():
    parser = argparse.ArgumentParser(
        description="Demo: fuzzy matching on sample Argentine football club lists."
    )
    parser.add_argument('--debug', action='store_true',
                        help="Show internal scores during matching")
    args = parser.parse_args()

    lista_a = cargar_lista("data/sample_clubs.txt")
    lista_b = cargar_lista("data/sample_clubs_alt.txt")

    print(f"\n{'═'*60}")
    print(f"  Argentine Football Club Matching Engine — Demo")
    print(f"{'═'*60}")
    print(f"  Reference list  : {len(lista_a)} clubs  (data/sample_clubs.txt)")
    print(f"  Alternate list  : {len(lista_b)} clubs  (data/sample_clubs_alt.txt)")
    print(f"\n  The same clubs appear with different names, formats,")
    print(f"  and spelling across different sources. The engine")
    print(f"  reconciles them automatically.\n")

    matches_exactos, matches_dudosos, solo_a, solo_b = comparar(
        lista_a, lista_b,
        interactivo=False,   # non-interactive for demo
        debug=args.debug
    )

    imprimir_resultados(
        matches_exactos, matches_dudosos, solo_a, solo_b,
        "REFERENCE", "ALTERNATE"
    )

if __name__ == '__main__':
    main()
