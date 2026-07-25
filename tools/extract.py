#!/usr/bin/env python3
"""Estrae il menu vero dallo snapshot della pagina Menumal.

L'URL pubblico e' una vetrina: mostra il menu dentro un finto tablet disegnato,
con header Menumal e pulsante "Accedi" intorno. Il menu vero e' il documento
HTML che l'app Nuxt inietta nell'iframe via `srcdoc`.

Quel documento e' gia' completo e autonomo: estrarlo da' un menu a schermo
intero senza cornici, che e' quello che serve su un tablet al tavolo.
"""
import html
import re
import sys


def extract(source):
    # srcdoc e' un attributo tra virgolette doppie il cui contenuto ha le
    # virgolette interne escapate: la prima " letterale chiude l'attributo.
    start = source.find('srcdoc="')
    if start == -1:
        sys.exit("ERRORE: nessun iframe con srcdoc, la pagina e' cambiata")
    start += len('srcdoc="')
    end = source.find('"', start)
    if end == -1:
        sys.exit("ERRORE: attributo srcdoc non terminato")

    doc = html.unescape(source[start:end])

    if "<html" not in doc.lower():
        sys.exit("ERRORE: srcdoc non contiene un documento HTML")
    if "€" not in doc:
        sys.exit("ERRORE: nessun prezzo nel menu estratto")
    return doc


if __name__ == "__main__":
    src = open(sys.argv[1], encoding="utf-8", errors="ignore").read()
    menu = extract(src)
    open(sys.argv[2], "w", encoding="utf-8").write(menu)

    # Contano solo le risorse che il browser andrebbe a scaricare. Un <a href>
    # verso Instagram o TripAdvisor e' un link su cui il cliente puo' cliccare:
    # offline non porta da nessuna parte, ma non impedisce al menu di aprirsi.
    resources = len(re.findall(r'\bsrc="https?://', menu))
    resources += len(re.findall(r'url\(\s*["\']?https?://', menu))
    resources += len(re.findall(r'<link[^>]+href="https?://', menu))
    links = len(re.findall(r'<a\b[^>]+href="https?://', menu))

    print("menu estratto: %.2f MB | prezzi: %d | risorse esterne: %d | link: %d"
          % (len(menu) / 1048576, menu.count("€"), resources, links))
    if resources:
        sys.exit("ERRORE: %d risorse esterne non incorporate, offline si romperebbe"
                 % resources)
