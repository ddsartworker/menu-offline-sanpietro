#!/usr/bin/env python3
"""Rimuove dallo snapshot i @font-face non utilizzati.

Menumal precarica ~65 famiglie Google Fonts di cui il singolo menu ne usa 2-3:
sono ~6.4 MB su 9.7 MB. Toglierle rende l'aggiornamento scaricabile su 4G debole.

Sicurezza: se una famiglia usata nel documento non sopravvive al taglio, lo script
esce con errore invece di pubblicare un menu con i font rotti.
"""
import html
import re
import sys

# Subset non-latini: il menu e' in italiano/inglese.
NON_LATIN = ("U+04", "U+05", "U+06", "U+03", "U+01AB", "U+1E00", "U+0102",
             "U+0110", "U+0128", "U+2DE", "U+A64", "U+2C6")


def family_of(block):
    """Nome della famiglia. Va unescapizzato PRIMA del parsing: '&quot;'
    contiene un ';' che spezzerebbe il regex a meta' valore."""
    m = re.search(r"font-family\s*:\s*([^;}]+)", html.unescape(block))
    return m.group(1).strip().strip("\"'").lower() if m else ""


def unicode_range_of(block):
    m = re.search(r"unicode-range\s*:\s*([^;}]+)", block)
    return m.group(1).strip() if m else ""


def slim(source):
    blocks = [(m.group(0), m.start(), m.end())
              for m in re.finditer(r"@font-face\s*\{.*?\}", source, re.S)]
    declared = {family_of(b) for b, _, _ in blocks} - {""}

    # Famiglie realmente applicate da una regola CSS o da uno style inline.
    doc = html.unescape(re.sub(r"@font-face\s*\{.*?\}", "", source, flags=re.S))
    used = set()
    for m in re.finditer(r"font-family\s*:\s*([^;}]+)", doc):
        for token in m.group(1).split(","):
            token = token.strip().strip("\"'").lower()
            if token in declared:
                used.add(token)

    drop, kept_families, freed = [], set(), 0
    for block, start, end in blocks:
        fam = family_of(block)
        urange = unicode_range_of(block)
        non_latin = urange and any(x in urange for x in NON_LATIN) and "U+0000" not in urange
        weight = sum(len(x) * 3 // 4 for x in re.findall(r"base64,([A-Za-z0-9+/=]+)", block))
        if fam not in used or non_latin:
            drop.append((start, end))
            freed += weight
        else:
            kept_families.add(fam)

    # Rete di sicurezza: nessuna famiglia usata deve sparire del tutto.
    lost = used - kept_families
    if lost:
        sys.exit("ERRORE: famiglie usate ma eliminate: %s" % sorted(lost))

    out, prev = [], 0
    for start, end in sorted(drop):
        out.append(source[prev:start])
        prev = end
    out.append(source[prev:])
    return "".join(out), used, kept_families, freed


if __name__ == "__main__":
    src = open(sys.argv[1], encoding="utf-8", errors="ignore").read()
    result, used, kept, freed = slim(src)
    open(sys.argv[2], "w", encoding="utf-8").write(result)
    print("famiglie usate: %s" % sorted(used))
    print("famiglie conservate: %s" % sorted(kept))
    print("liberati %.2f MB | %.2f MB -> %.2f MB"
          % (freed / 1048576, len(src) / 1048576, len(result) / 1048576))
