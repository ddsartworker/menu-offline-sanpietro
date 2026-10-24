#!/usr/bin/env python3
"""Rende il file uguale a se stesso quando il menu non cambia.

Menumal riordina a caso due cose a ogni caricamento, senza che il menu cambi:
le variabili CSS nello `style` di <html> e i link social nel pie' di pagina.
Bastava quello a dare uno sha nuovo a ogni cattura, e il tablet riscaricava
2 MB ogni quarto d'ora per niente. Qui si mettono entrambi in un ordine fisso.

L'ordine non conta per chi guarda: le variabili sono nomi diversi fra loro e
i link sono quattro icone affiancate.

Uso: stabilizza.py menu.html   (riscrive il file sul posto)
"""
import re
import sys

STILE_HTML = re.compile(r"(<html\b[^>]*?\sstyle=')([^']*)(')")
# Un gruppo di link social uno dopo l'altro, senza nulla in mezzo.
LINK = r"<a\b[^>]*\bdata-subsection=link\b[^>]*>.*?</a>"
GRUPPO_LINK = re.compile(rf"(?:{LINK})+", re.S)


def dichiarazioni(stile):
    """Divide sui ';' che non stanno dentro una stringa fra virgolette."""
    parti, attuale, virgolette = [], [], None
    for c in stile:
        if virgolette:
            if c == virgolette:
                virgolette = None
        elif c in "\"'":
            virgolette = c
        elif c == ";":
            parti.append("".join(attuale))
            attuale = []
            continue
        attuale.append(c)
    parti.append("".join(attuale))
    return [p.strip() for p in parti if p.strip()]


def ordina_stile(m):
    valori = {}
    for d in dichiarazioni(m.group(2)):
        nome, _, valore = d.partition(":")
        # Con un nome ripetuto vale l'ultimo, come per il browser.
        valori[nome.strip()] = valore.strip()
    stile = ";".join(f"{n}:{valori[n]}" for n in sorted(valori))
    return m.group(1) + stile + m.group(3)


def ordina_link(m):
    return "".join(sorted(re.findall(LINK, m.group(0), re.S)))


def main():
    percorso = sys.argv[1]
    with open(percorso, encoding="utf-8") as f:
        testo = f.read()

    testo, n_stili = STILE_HTML.subn(ordina_stile, testo, count=1)
    testo, n_gruppi = GRUPPO_LINK.subn(ordina_link, testo)

    with open(percorso, "w", encoding="utf-8") as f:
        f.write(testo)
    print(f"    stile di <html> ordinato: {'si' if n_stili else 'non trovato'}"
          f" | gruppi di link ordinati: {n_gruppi}")


if __name__ == "__main__":
    main()
