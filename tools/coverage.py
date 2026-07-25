#!/usr/bin/env python3
"""Quali glifi contengono davvero i font incorporati nello snapshot.

Serve perche' una regola CSS corretta non garantisce l'icona: Font Awesome
spezza i font per intervallo Unicode e la cattura incorpora solo i pezzi che il
browser aveva scaricato, quindi alcuni glifi mancano proprio dai dati del font.

Verificarlo dal browser non funziona: `document.fonts.check` risponde di si'
anche quando il glifo non c'e', e le larghezze su canvas non sono confrontabili
perche' i font Font Awesome popolano quasi tutta l'area privata. L'unico modo
affidabile e' leggere la tabella cmap dei font.
"""
import base64
import binascii
import html
import io
import re

from fontTools.ttLib import TTFont

# Le classi di stile scelgono famiglia e peso del font.
STYLE_FONTS = {
    "fa-solid": ("font awesome 6 pro", "900"),
    "fa-regular": ("font awesome 6 pro", "400"),
    "fa-light": ("font awesome 6 pro", "300"),
    "fa-thin": ("font awesome 6 pro", "100"),
    "fa-brands": ("font awesome 6 brands", "400"),
    "fa-kit": ("font awesome kit", None),
}


def embedded_fonts(doc):
    """(famiglia, peso) -> insieme dei codepoint effettivamente presenti."""
    coverage = {}
    for m in re.finditer(r"@font-face\s*\{.*?\}", doc, re.S):
        block = html.unescape(m.group(0))
        fam = re.search(r'font-family\s*:\s*["\']?([^;}"\']+)', block)
        weight = re.search(r"font-weight\s*:\s*(\d+)", block)
        data = re.search(r"base64,\s*([A-Za-z0-9+/=]+)", block)
        if not (fam and data):
            continue

        raw = data.group(1)
        try:
            font_bytes = base64.b64decode(raw + "=" * (-len(raw) % 4))
            font = TTFont(io.BytesIO(font_bytes), fontNumber=0, lazy=True)
            points = set(font.getBestCmap())
        except (binascii.Error, Exception):
            continue

        key = (fam.group(1).strip().lower(), weight.group(1) if weight else None)
        coverage.setdefault(key, set()).update(points)
    return coverage


def icon_codepoints(doc):
    """classe icona -> codepoint, dalle regole CSS presenti nel documento.

    Una stessa regola vale spesso per piu' alias (`.fa-temperature-snow,
    .fa-temperature-frigid{--fa:"\\f768"}`), quindi va letto tutto il selettore:
    fermarsi alla prima classe perderebbe le altre.
    """
    # Scansionare l'intero documento sarebbe proibitivo: contiene megabyte di
    # font in base64. Via quelli, restano solo le regole CSS vere.
    doc = html.unescape(doc)
    doc = re.sub(r"@font-face\s*\{.*?\}", "", doc, flags=re.S)
    doc = re.sub(r"data:[^\"')\s]{200,}", "", doc)

    points = {}
    for selector, body in re.findall(r"([^{}]{0,400})\{([^{}]{0,400})\}", doc):
        cp = None
        m = re.search(r'--fa:\s*"\\([0-9a-fA-F]+)"', body)
        if m:
            cp = int(m.group(1), 16)
        else:
            m = re.search(r'content:\s*"(.)"', body)
            if m and ord(m.group(1)) >= 0xE000:  # solo area privata: sono icone
                cp = ord(m.group(1))
        if cp is None:
            continue
        for name in re.findall(r"\.(fa-[a-z0-9-]+)(?![a-z0-9-])", selector):
            points.setdefault(name, cp)
    return points


def missing_icons(doc):
    """Icone usate nel menu il cui glifo non e' nei font incorporati."""
    coverage = embedded_fonts(doc)
    points = icon_codepoints(doc)
    unescaped = html.unescape(doc)

    missing = {}
    for classes in re.findall(r'class="([^"]*\bfa-[a-z0-9-]+[^"]*)"', unescaped):
        tokens = classes.split()
        style = next((t for t in tokens if t in STYLE_FONTS), None)
        if not style:
            continue
        fam, weight = STYLE_FONTS[style]

        for name in tokens:
            if name == style or name not in points:
                continue
            cp = points[name]
            covered = any(
                f == fam and (weight is None or w is None or w == weight) and cp in pts
                for (f, w), pts in coverage.items()
            )
            if not covered:
                missing[name] = cp
    return missing, coverage, points
