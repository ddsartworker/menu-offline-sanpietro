#!/usr/bin/env python3
"""Reintegra nello snapshot le regole CSS delle icone Font Awesome.

La cattura incorpora correttamente i font (Pro nei pesi 100/300/400/900, Brands
e il font del kit), ma non il CSS che mappa le classi ai glifi: quello arriva da
`pro.min.css` e `custom-icons.css`, caricati a runtime dal kit, che SingleFile
non segue. Senza, ogni icona diventa un quadratino.

Riguarda gli allergeni (obbligatori per il Reg. UE 1169/2011) e i marcatori di
prodotto abbattuto, che su un menu di pesce crudo sono altrettanto seri.

Si tengono solo le regole delle icone davvero presenti nel menu, e si fallisce
se anche una sola resta senza glifo.
"""
import html
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coverage import missing_icons

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# Font Awesome serve i font spezzati in blocchi per intervallo Unicode, e la
# cattura incorpora solo quelli che il browser ha scaricato: per alcune icone il
# glifo non c'e' proprio, e nessun CSS puo' recuperarlo. Verificato rendendo la
# pagina: queste quattro restano quadratini, le altre quindici no.
#
# Si sostituiscono con SVG equivalenti, mascherati su `currentColor` cosi' da
# ereditare colore e dimensione dall'icona originale.
def _svg(body):
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
           "stroke='black' stroke-width='2' stroke-linecap='round'>%s</svg>" % body)
    return svg.replace("<", "%3C").replace(">", "%3E").replace("#", "%23")


FALLBACKS = {
    # fiocco di neve: prodotto abbattuto
    "fa-snowflake": _svg(
        "<path d='M12 2v20M3.3 7l17.4 10M3.3 17L20.7 7'/>"
        "<path d='M12 6l-2.2-2.2M12 6l2.2-2.2M12 18l-2.2 2.2M12 18l2.2 2.2'/>"),
    "fa-temperature-snow": _svg(
        "<path d='M12 2v20M3.3 7l17.4 10M3.3 17L20.7 7'/>"
        "<path d='M12 6l-2.2-2.2M12 6l2.2-2.2M12 18l-2.2 2.2M12 18l2.2 2.2'/>"),
    "fa-magnifying-glass": _svg(
        "<circle cx='10.5' cy='10.5' r='7'/><path d='M15.6 15.6L21 21'/>"),
    "fa-fingerprint": _svg(
        "<path d='M12 3a9 9 0 00-9 9v3'/><path d='M21 12a9 9 0 00-9-9'/>"
        "<path d='M12 7.5a4.5 4.5 0 00-4.5 4.5v5.5'/><path d='M16.5 12A4.5 4.5 0 0012 7.5'/>"
        "<path d='M12 11.5a1.5 1.5 0 011.5 1.5v5'/><path d='M10.5 13v6'/>"),
}


def fallback_css(icons):
    """Regole di sostituzione per le icone di cui manca il glifo."""
    rules = []
    for name in sorted(FALLBACKS):
        if name not in icons:
            continue
        url = "url(\"data:image/svg+xml,%s\") center/contain no-repeat" % FALLBACKS[name]
        rules.append(
            ".%s:before{content:'';display:inline-block;width:1em;height:1em;"
            "vertical-align:-.125em;background-color:currentColor;"
            "-webkit-mask:%s;mask:%s}" % (name, url, url))
    return rules


def fetch(url, referer=None):
    # I kit Font Awesome sono vincolati al dominio licenziato: senza Referer
    # coerente il CDN puo' rifiutare la richiesta.
    headers = {"User-Agent": UA}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def kit_stylesheets(page_url):
    """Tutti i CSS del kit. Il token non e' scritto a mano ma letto dalla pagina
    live: se Menumal lo rigenera, la pipeline continua a funzionare."""
    page = fetch(page_url)
    kit = re.search(r"https://kit\.fontawesome\.com/[A-Za-z0-9]+\.css", page)
    if not kit:
        sys.exit("ERRORE: kit Font Awesome non trovato nella pagina")

    kit_css = fetch(kit.group(0), referer=page_url)
    urls = re.findall(r"url\((https://[^)]+\.css[^)]*)\)", kit_css)
    if not urls:
        sys.exit("ERRORE: il kit non referenzia alcun CSS")

    parts = []
    for u in urls:
        try:
            parts.append(fetch(u, referer=page_url))
        except Exception as e:
            print("  avviso: %s non scaricato (%s)" % (u.split("/")[-1][:40], e))
    return "\n".join(parts)


def icons_in(doc):
    """Classi fa-* usate nel menu, escluse quelle di stile e dimensione."""
    styles = {"fa-kit", "fa-solid", "fa-regular", "fa-light", "fa-thin",
              "fa-duotone", "fa-brands", "fa-sharp", "fa-fw", "fa-xl", "fa-lg",
              "fa-sm", "fa-xs", "fa-2x", "fa-3x", "fa-spin", "fa-pulse"}
    found = set()
    for cls in re.findall(r'class="([^"]*\bfa-[a-z0-9-]+[^"]*)"', doc):
        for tok in cls.split():
            if tok.startswith("fa-") and tok not in styles:
                found.add(tok)
    return found


def wanted_rules(css, icons):
    """CSS ridotto alle sole icone presenti nel menu.

    Font Awesome 6.7 non definisce i glifi con `content:` ma con una variabile
    per icona (`--fa:"\\f2dc"`) piu' una regola generica `:before{content:var(--fa)}`.
    Vanno quindi tenute due cose diverse: le variabili delle icone usate, e tutte
    le regole strutturali che le fanno funzionare (famiglia, peso, :before).

    Gli @font-face del kit si scartano: puntano a file remoti che offline
    fallirebbero, mentre i font veri sono gia' incorporati nello snapshot.
    """
    css = re.sub(r"@font-face\s*\{[^}]*\}", "", css)

    kept, covered = [], set()
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selector, body = m.group(1).strip(), m.group(2).strip()
        if not body:
            continue

        # Le icone standard usano `--fa:"\f2dc"`, quelle personalizzate del kit
        # `content:"<carattere>"` con il glifo letterale. La regola generica
        # `content:var(--fa)` non ha virgolette e resta fra le strutturali.
        defines_glyph = "--fa:" in body or re.search(r'content\s*:\s*"', body)
        if defines_glyph:
            # Regola specifica di un'icona: si tiene solo se serve al menu.
            hits = {i for i in icons if re.search(r"\.%s(?![a-z0-9-])" % re.escape(i), selector)}
            if hits:
                kept.append("%s{%s}" % (selector, body))
                covered |= hits
        else:
            # Regola strutturale (famiglia, peso, :before): serve sempre.
            kept.append("%s{%s}" % (selector, body))
    return kept, covered


if __name__ == "__main__":
    src_file, dest_file, page_url = sys.argv[1], sys.argv[2], sys.argv[3]

    doc = open(src_file, encoding="utf-8", errors="ignore").read()
    icons = icons_in(html.unescape(doc))
    css = kit_stylesheets(page_url)
    rules, covered = wanted_rules(css, icons)

    missing = icons - covered
    if missing:
        sys.exit("ERRORE: icone senza glifo: %s" % sorted(missing))

    # Quali icone restano senza glifo va deciso leggendo i font, non da una
    # lista scritta a mano: se Menumal cambia il menu, la lista invecchierebbe
    # in silenzio. I sostituti vanno in coda perche' a parita' di specificita'
    # vince l'ultima regola.
    probe = '<style id="fa-icon-rules">%s</style>' % "".join(rules)
    missing, _, _ = missing_icons(doc + probe)

    unfixable = sorted(set(missing) - set(FALLBACKS))
    if unfixable:
        sys.exit("ERRORE: icone senza glifo e senza sostituto: %s" % unfixable)

    fallbacks = fallback_css(set(missing))
    style = '<style id="fa-icon-rules">%s</style>' % "".join(rules + fallbacks)

    # SingleFile puo' emettere `</head >` con spazi dentro il tag, quindi niente
    # ricerca di stringa esatta. Se la testa mancasse, <style> a inizio body va
    # altrettanto bene.
    head = re.search(r"</head\s*>", doc, re.I)
    body = re.search(r"<body\b[^>]*>", doc, re.I)
    if head:
        at = head.start()
    elif body:
        at = body.end()
    else:
        sys.exit("ERRORE: ne' </head> ne' <body>, documento inatteso")

    open(dest_file, "w", encoding="utf-8").write(doc[:at] + style + doc[at:])

    allergens = len([i for i in covered if "allergen" in i])
    print("icone risolte: %d (%d allergeni) | %d regole + %d sostituti SVG, +%d KB"
          % (len(covered), allergens, len(rules), len(fallbacks), len(style) // 1024))
