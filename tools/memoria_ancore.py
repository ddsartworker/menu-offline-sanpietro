#!/usr/bin/env python3
"""Se la scoperta delle ancore va male, si tengono quelle gia' pubblicate.

tools/anchors.mjs apre il sito vero e clicca i chip delle zone dei vini. Quando
Menumal risponde male non scopre niente, e il 30 ottobre 2026 alle 10:07 UTC e'
uscito un menu con `ANCORE = {}`: Champagne, Bianchi Italiani e gli altri non
facevano piu' niente. E' rimasto cosi' cinque ore, perche' le catture dopo
fallivano, e se n'e' accorto il collaboratore in sala.

Le zone cambiano di rado, quindi le ancore di ieri valgono quasi sempre anche
oggi. Si usano solo se combaciano con il menu nuovo: stessi chip, nello stesso
ordine (il JS li abbina per posizione), e ogni vino-ancora ancora in carta.

Per ogni macro-categoria con chip:
  - ancore nuove che combaciano      -> quelle nuove
  - altrimenti pubblicate che combaciano -> quelle pubblicate
  - altrimenti                       -> quelle nuove, come prima

Uso: memoria_ancore.py ancore.json menu-nuovo.html menu-pubblicato.html
     (riscrive ancore.json; se il pubblicato manca non tocca nulla)
"""
import html
import json
import re
import sys

SEGNO = "var ANCORE = "
SLIDE = re.compile(r'class="?[^">]*\bcarousel__item\b')
CHIP = re.compile(
    r"<li\b[^>]*\bdata-section=\"?categories\b[^>]*>(.*?)(?=<li\b|</ul>)", re.S)
NOME = re.compile(r"<div\b[^>]*\bdata-tab=\"?name\b[^>]*>(.*?)</div>", re.S)
TAG = re.compile(r"<[^>]+>")


def testo(frammento):
    t = html.unescape(TAG.sub("", frammento))
    t = re.sub(r"categoria menu:", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip()


def slide_del_menu(doc):
    """Per ogni slide del carosello: (etichette dei chip, nomi dei piatti)."""
    inizi = [m.start() for m in SLIDE.finditer(doc)]
    pezzi = [doc[a:b] for a, b in zip(inizi, inizi[1:] + [len(doc)])]
    return [([testo(c) for c in CHIP.findall(p)], {testo(n) for n in NOME.findall(p)})
            for p in pezzi]


def combacia(mappa, slide):
    if not mappa or slide is None:
        return False
    chip, nomi = slide
    return ([v.get("chip") for v in mappa] == chip and
            all(v.get("ancora") in nomi for v in mappa))


def pubblicate(percorso):
    doc = open(percorso, encoding="utf-8", errors="ignore").read()
    at = doc.find(SEGNO)
    if at < 0:
        return {}
    dati, _ = json.JSONDecoder().raw_decode(doc, at + len(SEGNO))
    return dati or {}


def main():
    ancore_path, nuovo_path, vecchio_path = sys.argv[1:4]
    try:
        vecchie = pubblicate(vecchio_path)
    except (OSError, ValueError) as e:
        print(f"    ancore pubblicate non lette ({e}), si usano quelle nuove")
        return
    try:
        nuove = json.load(open(ancore_path, encoding="utf-8"))
    except (OSError, ValueError):
        nuove = {}

    slide = slide_del_menu(open(nuovo_path, encoding="utf-8", errors="ignore").read())
    risultato, riprese = {}, []
    for i, s in enumerate(slide):
        if len(s[0]) < 2:
            continue
        m = str(i)
        if combacia(nuove.get(m), s):
            risultato[m] = nuove[m]
        elif combacia(vecchie.get(m), s):
            risultato[m] = vecchie[m]
            riprese.append(m)
        elif nuove.get(m):
            risultato[m] = nuove[m]

    with open(ancore_path, "w", encoding="utf-8") as f:
        json.dump(risultato, f, ensure_ascii=False)
    if riprese:
        print(f"    ancore riprese dal menu pubblicato per le macro {', '.join(riprese)}")
    else:
        print("    ancore nuove confermate")


if __name__ == "__main__":
    main()
