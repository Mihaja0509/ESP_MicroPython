#!/usr/bin/env python3
"""Icône de l'app « Dadou » : visage de la mascotte qui rit, sur un fond crépuscule.

    py tools\\assets\\generer_icone.py
Produit app/assets/icone/icone.png (1024 px, icône complète)
     et app/assets/icone/icone_avant.png + icone_fond.png (icône adaptative Android).
"""
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generer_assets as g  # noqa: E402

SORTIE = g.ICI.parent.parent / "app" / "assets" / "icone"
T = 1024


def visage_rieur():
    t = g.tete(yeux="contents", bouche="rire")
    a = np.array(t)
    opaque = a[:, :, 3] > 40
    bord = ndimage.binary_dilation(opaque, iterations=14)
    out = np.zeros_like(a)
    out[bord] = (255, 255, 255, 255)
    im = Image.fromarray(out)
    im.alpha_composite(t)
    return im.crop(im.getbbox())


def fond():
    yy, xx = np.mgrid[0:T, 0:T].astype(np.float32)
    t = yy / (T - 1)
    haut = np.array([28, 18, 70], np.float32)
    milieu = np.array([120, 40, 140], np.float32)
    bas = np.array([255, 120, 100], np.float32)
    c = np.where(t[..., None] < 0.6,
                 haut + (milieu - haut) * (t[..., None] / 0.6),
                 milieu + (bas - milieu) * ((t[..., None] - 0.6) / 0.4))
    # halo cyan derrière la tête
    d = np.sqrt((xx - T / 2) ** 2 + (yy - T * 0.47) ** 2) / (T * 0.42)
    halo = np.clip(1 - d, 0, 1) ** 1.6
    c = c + np.array([0, 210, 255], np.float32)[None, None, :] * halo[..., None] * 0.45
    im = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).convert("RGBA")
    # petites étoiles / lumières
    d = ImageDraw.Draw(im)
    random.seed(5)
    for _ in range(40):
        x, y = random.randint(0, T), random.randint(0, int(T * 0.55))
        r = random.choice((2, 3, 3, 4, 6))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 240, 220, random.randint(120, 230)))
    return im


def poser(fond_img, visage, largeur):
    v = visage.resize((largeur, int(visage.height * largeur / visage.width)), Image.LANCZOS)
    ombre = Image.new("RGBA", fond_img.size, (0, 0, 0, 0))
    x = (T - v.width) // 2
    y = (T - v.height) // 2 + int(T * 0.02)
    masque = v.split()[3].point(lambda p: 110 if p > 0 else 0)
    ombre.paste((10, 0, 30, 255), (x + 10, y + 22), masque)
    ombre = ombre.filter(ImageFilter.GaussianBlur(18))
    out = fond_img.copy()
    out.alpha_composite(ombre)
    out.alpha_composite(v, (x, y))
    return out


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    visage = visage_rieur()
    f = fond()
    poser(f, visage, int(T * 0.78)).convert("RGB").save(SORTIE / "icone.png")
    # icône adaptative : le visage doit tenir dans le cercle central (~ 60 % de l'image)
    vide = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    poser(vide, visage, int(T * 0.60)).save(SORTIE / "icone_avant.png")
    f.convert("RGB").save(SORTIE / "icone_fond.png")
    print(f"Icônes écrites dans {SORTIE}")


if __name__ == "__main__":
    main()
