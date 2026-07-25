#!/usr/bin/env python3
"""Controllo finale sul file che finira' sul tablet.

Verifica indipendente da come e' stato prodotto: si guarda solo il risultato.
Serve soprattutto per le icone, dove un errore non si vede da nessun log — il
menu si apre normalmente e mostra quadratini al posto degli allergeni.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coverage import missing_icons


def check(path):
    doc = open(path, encoding="utf-8", errors="ignore").read()
    problems = []

    # 1. Il menu deve essere davvero autonomo: qualunque risorsa remota
    #    diventerebbe un buco nella pagina appena manca la rete.
    remote = len(re.findall(r'\bsrc="https?://', doc))
    remote += len(re.findall(r'url\(\s*["\']?https?://', doc))
    remote += len(re.findall(r'<link[^>]+href="https?://', doc))
    if remote:
        problems.append("%d risorse esterne non incorporate" % remote)

    # 2. Contenuto: una cattura andata male produce una pagina che si apre ma e' vuota.
    prices = doc.count("€")
    if prices < 100:
        problems.append("solo %d prezzi, cattura probabilmente incompleta" % prices)

    allergens = len(re.findall(r"allergen-food", doc))
    if allergens < 20:
        problems.append("solo %d riferimenti allergene" % allergens)

    # 3. Ogni icona senza glifo nel font deve avere un sostituto SVG.
    missing, _, _ = missing_icons(doc)
    substituted = set(re.findall(r"\.(fa-[a-z0-9-]+):before\{[^{}]*background-color:currentColor", doc))
    broken = sorted(set(missing) - substituted)
    if broken:
        problems.append("icone rese come quadratino: %s" % broken)

    if problems:
        for p in problems:
            print("  ERRORE: %s" % p, file=sys.stderr)
        sys.exit(1)

    print("verifica: %d prezzi, %d allergeni, %d icone sostituite, 0 risorse esterne"
          % (prices, allergens, len(missing)))


if __name__ == "__main__":
    check(sys.argv[1])
