#!/usr/bin/env python3
"""Prepara l'icona dell'app a partire dal logo del ristorante.

Il logo arriva come disegno su una tela quadrata molto piu' grande, spostato
rispetto al centro. Android ritaglia le icone in cerchio, quadrato stondato o
goccia a seconda del telefono, quindi il disegno va ritagliato, centrato e
tenuto dentro la zona che nessuna maschera taglia: il 66% centrale.

Si producono due cose: le icone classiche per Android piu' vecchi e il primo
piano dell'icona adattiva per Android 8 e successivi.
"""
import os
import sys

from PIL import Image, ImageChops

# Densita' Android e lato dell'icona in pixel.
DENSITA = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}

# Quanto del lato occupa il disegno. Le maschere di Android mangiano gli angoli:
# oltre il 66% il pesce rischia di perdere pinne e coda.
QUOTA_CLASSICA = 0.66
QUOTA_ADATTIVA = 0.50   # la tela adattiva e' piu' grande della parte visibile

SFONDO = (255, 255, 255, 255)


def ritaglia(percorso):
    """Il disegno, senza il bianco attorno."""
    im = Image.open(percorso).convert("RGBA")
    piatto = Image.new("RGB", im.size, SFONDO[:3])
    piatto.paste(im, mask=im.split()[3] if im.mode == "RGBA" else None)
    riquadro = ImageChops.difference(piatto, Image.new("RGB", im.size, SFONDO[:3])).getbbox()
    if not riquadro:
        sys.exit("ERRORE: il logo sembra vuoto")
    return im.crop(riquadro)


def componi(disegno, lato, quota, trasparente):
    tela = Image.new("RGBA", (lato, lato), (0, 0, 0, 0) if trasparente else SFONDO)
    largo = int(lato * quota)
    scala = min(largo / disegno.width, largo / disegno.height)
    misura = (max(1, int(disegno.width * scala)), max(1, int(disegno.height * scala)))
    ridotto = disegno.resize(misura, Image.LANCZOS)
    tela.paste(ridotto, ((lato - misura[0]) // 2, (lato - misura[1]) // 2), ridotto)
    return tela


if __name__ == "__main__":
    sorgente = sys.argv[1]
    res = sys.argv[2] if len(sys.argv) > 2 else "android/app/src/main/res"

    disegno = ritaglia(sorgente)
    print("disegno ritagliato: %dx%d" % disegno.size)

    for nome, lato in DENSITA.items():
        cartella = os.path.join(res, "mipmap-" + nome)
        os.makedirs(cartella, exist_ok=True)
        componi(disegno, lato, QUOTA_CLASSICA, False).save(
            os.path.join(cartella, "ic_launcher.png"))
        # Il primo piano dell'icona adattiva e' sempre a 108dp di lato.
        componi(disegno, round(lato * 108 / 48), QUOTA_ADATTIVA, True).save(
            os.path.join(cartella, "ic_launcher_foreground.png"))

    print("icone scritte per %d densita'" % len(DENSITA))
