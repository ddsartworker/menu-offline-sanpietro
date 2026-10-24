#!/usr/bin/env python3
"""Tiene le traduzioni gia' pubblicate per le frasi che non sono cambiate.

Google Translate non e' deterministico: la stessa frase italiana esce a volte
"dried tomatoes from Vesuvius" e a volte "Vesuvius dried tomatoes". Bastava
questo a dare un file nuovo quasi a ogni cattura, e il tablet riscaricava 2 MB
a menu fermo. Qui, per ogni frase italiana gia' presente nel menu pubblicato,
si tiene la traduzione di allora; si usa quella nuova solo per le frasi nuove.

Uso: memoria_traduzioni.py traduzioni.json menu-pubblicato.html
     (riscrive traduzioni.json sul posto; se qualcosa manca non tocca nulla)
"""
import json
import sys

SEGNO = "var TRADUZIONI = "


def pubblicate(percorso):
    testo = open(percorso, encoding="utf-8", errors="ignore").read()
    at = testo.find(SEGNO)
    if at < 0:
        return {}
    dati, _ = json.JSONDecoder().raw_decode(testo, at + len(SEGNO))
    return (dati or {}).get("voci", {})


def main():
    nuove_path, vecchio_menu = sys.argv[1], sys.argv[2]
    try:
        nuove = json.load(open(nuove_path, encoding="utf-8"))
        vecchie = pubblicate(vecchio_menu)
    except (OSError, ValueError) as e:
        print(f"    traduzioni precedenti non lette ({e}), si usano quelle nuove")
        return

    voci = nuove.get("voci", {})
    tenute = 0
    for italiano in voci:
        if italiano in vecchie and vecchie[italiano] != voci[italiano]:
            voci[italiano] = vecchie[italiano]
            tenute += 1

    with open(nuove_path, "w", encoding="utf-8") as f:
        json.dump(nuove, f, ensure_ascii=False)
    print(f"    {tenute} traduzioni riprese da quelle pubblicate, "
          f"{sum(1 for k in voci if k not in vecchie)} frasi nuove")


if __name__ == "__main__":
    main()
