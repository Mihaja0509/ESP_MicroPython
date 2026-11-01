#!/usr/bin/env python3
"""Génère les images et polices de l'écran de l'ESP32 (Phase 4).

À lancer sur le PC (pas sur la carte) :
    py -m pip install --user pillow numpy scipy
    py tools\\assets\\generer_assets.py

Produit dans esp/assets/ :
  - fond_*.bin      fonds 320 x 172 (RGB565, octets dans l'ordre de l'écran)
  - perso_*.bin     images de la mascotte 95 x 150 (RGB565, magenta = transparent)
  - ico_*.bin       petites icônes (RGB565, magenta = transparent)
  - *.fnt           polices (4 niveaux de gris par pixel, voir polices.py)
Et dans tools/assets/apercus/ : des aperçus PNG pour vérifier à l'œil.

Polices : Inter (licence SIL Open Font License 1.1, voir LICENCE_POLICES.txt).
"""
import math
import random
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ICI = Path(__file__).resolve().parent
SORTIE = ICI.parent.parent / "esp" / "assets"
SOURCES = ICI / "sources"
APERCUS = ICI / "apercus"
W, H = 320, 172
MAGENTA = (255, 0, 255)

# Couleurs partagées avec esp/lib/ui.py (garder identiques)
CARTE_JOUR = (18, 14, 40)
CARTE_NUIT = (10, 12, 30)
CARTE_JEU = (8, 6, 22)
CYAN = (0, 210, 255)
MAGENTA_NEON = (255, 40, 200)

# Position de la mascotte (doit correspondre à ui.py)
PERSO_W, PERSO_H = 95, 150
PERSO_X, PERSO_Y = W - PERSO_W - 12, H - PERSO_H - 6


def chercher_police(nom):
    candidats = [
        SOURCES / nom,
        Path("/usr/share/fonts/opentype/inter") / nom,
        Path("C:/Windows/Fonts") / nom,
        Path.home() / "AppData/Local/Microsoft/Windows/Fonts" / nom,
    ]
    for c in candidats:
        if c.exists():
            return str(c)
    sys.exit(f"Police {nom} introuvable : mets le fichier dans {SOURCES}")


# ---------------------------------------------------------------------------
# Conversion RGB565 (octets « gros-boutiste », comme l'écran les attend)
# ---------------------------------------------------------------------------
def rgb565(img):
    a = np.asarray(img.convert("RGB")).astype(np.uint16)
    v = ((a[:, :, 0] & 0xF8) << 8) | ((a[:, :, 1] & 0xFC) << 3) | (a[:, :, 2] >> 3)
    return v.astype(">u2").tobytes()


def ecrire(nom, donnees):
    (SORTIE / nom).write_bytes(donnees)
    print(f"  {nom:24} {len(donnees):7} octets")


def sprite_transparent(img_rgba, fond_moyen):
    """RGBA -> RGB565 avec magenta pour le transparent.
    Les bords semi-transparents sont mélangés avec la couleur `fond_moyen`."""
    a = np.asarray(img_rgba).astype(np.float32)
    alpha = a[:, :, 3:4] / 255.0
    rgb = a[:, :, :3] * alpha + np.array(fond_moyen, np.float32) * (1 - alpha)
    rgb = rgb.clip(0, 255).astype(np.uint8)
    out = Image.fromarray(rgb)
    px = np.array(out)
    px[a[:, :, 3] < 60] = MAGENTA
    # évite qu'un pixel visible tombe par hasard sur le magenta
    vrai = (a[:, :, 3] >= 60) & (px[:, :, 0] > 245) & (px[:, :, 1] < 10) & (px[:, :, 2] > 245)
    px[vrai] = (250, 0, 250)
    return Image.fromarray(px)


# ---------------------------------------------------------------------------
# Fonds
# ---------------------------------------------------------------------------
def degrade(haut, milieu, bas, coupure=0.62):
    g = np.zeros((H, W, 3), np.float32)
    haut, milieu, bas = (np.array(c, np.float32) for c in (haut, milieu, bas))
    for y in range(H):
        t = y / (H - 1)
        if t < coupure:
            c = haut + (milieu - haut) * (t / coupure)
        else:
            c = milieu + (bas - milieu) * ((t - coupure) / (1 - coupure))
        g[y, :] = c
    return Image.fromarray(g.clip(0, 255).astype(np.uint8)).convert("RGBA")


def halo(img, cx, cy, r, couleur, force=70):
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    for rr in range(r, 0, -2):
        a = int(force * (1 - rr / r) ** 1.5)
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=couleur + (a,))
    img.alpha_composite(calque)


def ville(img, couleur, fenetres, proba, graine=3):
    d = ImageDraw.Draw(img)
    random.seed(graine)
    x = 0
    while x < W:
        w = random.randint(10, 22)
        h = random.randint(8, 26)
        d.rectangle((x, H - h, x + w, H), fill=couleur)
        for wy in range(H - h + 4, H - 2, 6):
            for wx in range(x + 3, x + w - 2, 6):
                if random.random() < proba:
                    d.rectangle((wx, wy, wx + 1, wy + 1), fill=fenetres)
        x += w


def carte(img, boite, couleur, bord):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(boite, 12, fill=couleur + (255,))
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(calque).rounded_rectangle(boite, 12, outline=bord, width=1)
    img.alpha_composite(calque)


def fond_jour():
    im = degrade((20, 14, 48), (88, 30, 110), (236, 96, 92))
    halo(im, PERSO_X + PERSO_W // 2, 92, 70, CYAN)
    ville(im, (36, 16, 56, 255), (255, 200, 120, 255), 0.35)
    carte(im, (6, 6, 186, 166), CARTE_JOUR, (255, 255, 255, 50))
    return im


def fond_nuit():
    im = degrade((4, 6, 20), (14, 18, 52), (30, 28, 78))
    d = ImageDraw.Draw(im)
    random.seed(11)
    for _ in range(60):
        x, y = random.randint(0, W - 1), random.randint(0, 120)
        c = random.randint(120, 255)
        d.point((x, y), fill=(c, c, min(255, c + 20), 255))
    # lune
    cx, cy = 300, 20
    halo(im, cx, cy, 26, (180, 200, 255), 50)
    d = ImageDraw.Draw(im)
    d.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), fill=(240, 236, 210, 255))
    d.ellipse((cx - 4, cy - 12, cx + 12, cy + 6), fill=(8, 10, 28, 255))
    halo(im, PERSO_X + PERSO_W // 2, 96, 60, (90, 110, 255), 45)
    ville(im, (10, 10, 30, 255), (255, 210, 120, 255), 0.10, graine=3)
    carte(im, (6, 6, 186, 166), CARTE_NUIT, (255, 255, 255, 35))
    return im


def fond_jeu():
    im = degrade((2, 2, 10), (20, 6, 40), (60, 8, 70), coupure=0.55)
    d = ImageDraw.Draw(im, "RGBA")
    # soleil néon rayé
    cx, cy, r = 258, 96, 44
    halo(im, cx, cy, 78, MAGENTA_NEON, 60)
    d = ImageDraw.Draw(im, "RGBA")
    for y in range(cy - r, cy + 1):
        dx = int(math.sqrt(max(0, r * r - (y - cy) ** 2)))
        t = (y - (cy - r)) / r
        col = (255, int(200 - 150 * t), int(60 + 120 * t), 255)
        if y > cy - 18 and (y // 3) % 3 == 0:
            continue
        d.line((cx - dx, y, cx + dx, y), fill=col)
    # grille en perspective
    horizon = 112
    d.rectangle((0, horizon, W, H), fill=(14, 2, 30, 255))
    for i in range(-14, 15):
        x0 = W // 2 + i * 12
        x1 = W // 2 + i * 70
        d.line((x0, horizon, x1, H), fill=(255, 40, 200, 150), width=1)
    y = horizon
    pas = 3
    while y < H:
        d.line((0, y, W, y), fill=(255, 40, 200, 170), width=1)
        y += pas
        pas += 2
    d.line((0, horizon, W, horizon), fill=(0, 230, 255, 255), width=1)
    # panneau gauche
    d.rounded_rectangle((6, 6, 196, 166), 10, fill=CARTE_JEU + (255,), outline=CYAN + (255,), width=1)
    d.rounded_rectangle((8, 8, 194, 164), 9, outline=(0, 210, 255, 60), width=1)
    return im


# ---------------------------------------------------------------------------
# Mascotte
# ---------------------------------------------------------------------------
CONTOUR = (38, 24, 20, 255)
PEAU = (232, 160, 118, 255)
PEAU_OMBRE = (205, 135, 98, 255)
PEAU_YEUX = (237, 168, 126, 255)
HOODIE = (40, 52, 96, 255)
HOODIE_SOMBRE = (26, 32, 64, 255)
ACCENT = (0, 210, 255, 255)
GRIS_CASQUE = (36, 36, 44, 255)


def tete(yeux="ouverts", bouche="normale"):
    t = Image.open(SOURCES / "tete.png").convert("RGBA")
    c = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    c.alpha_composite(t, (288, 92))
    d = ImageDraw.Draw(c)
    if yeux != "ouverts":
        for cx in (432, 588):
            d.ellipse((cx - 30, 385, cx + 30, 450), fill=PEAU_YEUX)
            if yeux == "fermes":
                d.arc((cx - 24, 395, cx + 24, 440), 20, 160, fill=CONTOUR, width=8)
            elif yeux == "contents":  # ^ ^
                d.arc((cx - 24, 400, cx + 24, 450), 200, 340, fill=CONTOUR, width=9)
    if bouche != "normale":
        # efface le sourire dessiné d'origine (et l'ombre de la lèvre) avant d'en dessiner un autre
        d.ellipse((456, 474, 570, 536), fill=(238, 169, 127, 255))
    if bouche == "rire":
        d.chord((470, 470, 554, 540), 0, 180, fill=(110, 34, 38, 255), outline=CONTOUR, width=7)
        d.chord((490, 506, 534, 538), 0, 180, fill=(232, 112, 112, 255))
        d.rectangle((476, 505, 548, 512), fill=(255, 255, 255, 255))
    elif bouche == "o":
        d.ellipse((494, 488, 530, 528), fill=(110, 34, 38, 255), outline=CONTOUR, width=7)
    return c


def corps(casque_au_cou=True, remonter=30):
    """Buste (hoodie). `remonter` raccourcit le cou en remontant tout le buste."""
    arriere = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    d = ImageDraw.Draw(arriere)
    d.ellipse((370, 575, 650, 690), fill=HOODIE_SOMBRE, outline=CONTOUR, width=9)
    if casque_au_cou:
        d.arc((408, 570, 616, 700), 180, 360, fill=CONTOUR, width=24)
        d.arc((408, 570, 616, 700), 180, 360, fill=ACCENT, width=14)
    avant = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    d = ImageDraw.Draw(avant)
    pts = [(300, 690), (352, 640), (420, 622)]
    encolure = [(420 + t * 184, 622 + math.sin(t * math.pi) * 48) for t in np.linspace(0, 1, 15)]
    pts += encolure + [(604, 622), (672, 640), (724, 690), (752, 870), (272, 870)]
    d.polygon(pts, fill=HOODIE, outline=CONTOUR, width=9)
    d.line(encolure, fill=HOODIE_SOMBRE, width=14)
    d.line([(x, y + 8) for x, y in encolure], fill=CONTOUR, width=5)
    d.line([(352, 700), (336, 860)], fill=HOODIE_SOMBRE, width=10)
    d.line([(672, 700), (688, 860)], fill=HOODIE_SOMBRE, width=10)
    for x0, dx in ((478, -6), (546, 6)):
        d.line([(x0, 680), (x0 + dx, 760)], fill=(245, 245, 245, 255), width=8)
        d.rounded_rectangle((x0 + dx - 7, 752, x0 + dx + 7, 782), 4, fill=ACCENT, outline=CONTOUR, width=4)
    if casque_au_cou:
        for cx in (404, 620):
            d.ellipse((cx - 34, 605, cx + 34, 690), fill=GRIS_CASQUE, outline=CONTOUR, width=8)
            d.ellipse((cx - 19, 622, cx + 19, 673), fill=ACCENT)
            d.ellipse((cx - 8, 630, cx + 4, 646), fill=(255, 255, 255, 170))
    L = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    L.alpha_composite(arriere, (0, -remonter))
    d = ImageDraw.Draw(L)
    bas_cou = 660 - remonter
    d.rectangle((474, 540, 548, bas_cou), fill=PEAU)
    d.line([(474, 540), (474, bas_cou)], fill=CONTOUR, width=7)
    d.line([(548, 540), (548, bas_cou)], fill=CONTOUR, width=7)
    d.rectangle((477, 572, 545, 584), fill=PEAU_OMBRE)
    L.alpha_composite(avant, (0, -remonter))
    return L


def casque_sur_tete(img):
    """Casque sur les oreilles : l'arceau suit le haut de la tête, les écouteurs couvrent les oreilles."""
    d = ImageDraw.Draw(img)
    boite = (322, 74, 702, 660)  # ellipse qui colle au contour des cheveux
    d.arc(boite, 184, 356, fill=CONTOUR, width=30)
    d.arc(boite, 184, 356, fill=ACCENT, width=17)
    d.arc((boite[0] + 10, boite[1] + 10, boite[2] - 10, boite[3] - 10), 215, 325,
          fill=(150, 240, 255, 255), width=4)  # reflet
    for x0, x1 in ((290, 372), (652, 734)):
        d.rounded_rectangle((x0, 368, x1, 500), 32, fill=GRIS_CASQUE, outline=CONTOUR, width=9)
        d.rounded_rectangle((x0 + 15, 388, x1 - 15, 480), 20, fill=ACCENT)
        d.ellipse((x0 + 22, 396, x0 + 38, 424), fill=(255, 255, 255, 170))
    # attaches entre l'arceau et les écouteurs
    for x in (318, 706):
        d.rounded_rectangle((x - 10, 330, x + 10, 380), 6, fill=GRIS_CASQUE, outline=CONTOUR, width=6)


def perso(yeux="ouverts", bouche="normale", casque="cou", taille=(PERSO_W, PERSO_H)):
    base = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    base.alpha_composite(corps(casque_au_cou=(casque == "cou")))
    base.alpha_composite(tete(yeux, bouche))
    if casque == "oreilles":
        casque_sur_tete(base)
    A = np.array(base)
    yy, xx = np.mgrid[0:1024, 0:1024]
    garder = (((xx - 512) / 250.0) ** 2 + ((yy - 560) / 250.0) ** 2 <= 1) | (yy < 640)
    A[~garder] = 0
    opaque = A[:, :, 3] > 40
    bord = ndimage.binary_dilation(opaque, iterations=12)
    out = np.zeros_like(A)
    out[bord] = (255, 255, 255, 255)
    o = Image.fromarray(out)
    o.alpha_composite(Image.fromarray(A))
    # cadrage fixe (le même pour toutes les images, pour qu'elles se superposent)
    o = o.crop((262, 44, 762, 834))
    return o.resize(taille, Image.LANCZOS)


# ---------------------------------------------------------------------------
# Icônes (dessinées en grand puis réduites)
# ---------------------------------------------------------------------------
def icone(dessin, taille=18, fond=(255, 255, 255), echelle=8):
    T = taille * echelle
    im = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    dessin(ImageDraw.Draw(im), T)
    im = im.resize((taille, taille), Image.LANCZOS)
    return sprite_transparent(im, fond)


ENCRE = (40, 40, 80, 255)


def i_son(d, T):
    d.rectangle((T * .10, T * .36, T * .30, T * .64), fill=ENCRE)
    d.polygon([(T * .30, T * .36), (T * .52, T * .16), (T * .52, T * .84), (T * .30, T * .64)], fill=ENCRE)
    d.arc((T * .45, T * .28, T * .75, T * .72), -55, 55, fill=ENCRE, width=int(T * .08))
    d.arc((T * .45, T * .12, T * .95, T * .88), -50, 50, fill=ENCRE, width=int(T * .08))


def i_muet(d, T):
    i_son(d, T)
    d.line((T * .55, T * .25, T * .95, T * .75), fill=(230, 50, 60, 255), width=int(T * .1))


def i_soleil(d, T):
    c = T / 2
    d.ellipse((c - T * .2, c - T * .2, c + T * .2, c + T * .2), fill=(255, 170, 0, 255))
    for k in range(8):
        a = k * math.pi / 4
        d.line((c + math.cos(a) * T * .3, c + math.sin(a) * T * .3,
                c + math.cos(a) * T * .45, c + math.sin(a) * T * .45), fill=(255, 170, 0, 255), width=int(T * .08))


def i_cadenas(d, T):
    d.arc((T * .28, T * .10, T * .72, T * .60), 180, 360, fill=ENCRE, width=int(T * .1))
    d.line((T * .28, T * .35, T * .28, T * .45), fill=ENCRE, width=int(T * .1))
    d.line((T * .72, T * .35, T * .72, T * .45), fill=ENCRE, width=int(T * .1))
    d.rounded_rectangle((T * .18, T * .42, T * .82, T * .92), int(T * .08), fill=ENCRE)


def i_clavier(d, T):
    d.rounded_rectangle((T * .05, T * .25, T * .95, T * .78), int(T * .08), fill=ENCRE)
    for r in range(2):
        for k in range(5):
            x = T * (.14 + k * .155)
            y = T * (.34 + r * .16)
            d.rectangle((x, y, x + T * .1, y + T * .09), fill=(255, 255, 255, 255))
    d.rectangle((T * .25, T * .64, T * .75, T * .70), fill=(255, 255, 255, 255))


def i_souris(d, T):
    d.rounded_rectangle((T * .26, T * .08, T * .74, T * .92), int(T * .24), fill=ENCRE)
    d.line((T * .5, T * .1, T * .5, T * .4), fill=(255, 255, 255, 255), width=int(T * .06))


def i_appli(d, T):  # fusée
    d.ellipse((T * .34, T * .06, T * .66, T * .72), fill=ENCRE)
    d.polygon([(T * .34, T * .5), (T * .16, T * .76), (T * .38, T * .68)], fill=ENCRE)
    d.polygon([(T * .66, T * .5), (T * .84, T * .76), (T * .62, T * .68)], fill=ENCRE)
    d.ellipse((T * .43, T * .26, T * .57, T * .40), fill=(0, 190, 240, 255))
    d.polygon([(T * .42, T * .74), (T * .5, T * .96), (T * .58, T * .74)], fill=(255, 120, 0, 255))


def i_lune(d, T):
    d.ellipse((T * .12, T * .12, T * .88, T * .88), fill=(250, 200, 60, 255))
    d.ellipse((T * .34, T * .02, T * 1.04, T * .72), fill=(0, 0, 0, 0))


def i_power(d, T):
    d.arc((T * .14, T * .18, T * .86, T * .90), -60, 240, fill=(230, 50, 60, 255), width=int(T * .11))
    d.line((T * .5, T * .06, T * .5, T * .5), fill=(230, 50, 60, 255), width=int(T * .11))


def i_musique(d, T):
    d.ellipse((T * .14, T * .62, T * .42, T * .86), fill=ENCRE)
    d.ellipse((T * .58, T * .52, T * .86, T * .76), fill=ENCRE)
    d.line((T * .38, T * .72, T * .38, T * .16), fill=ENCRE, width=int(T * .08))
    d.line((T * .82, T * .62, T * .82, T * .08), fill=ENCRE, width=int(T * .08))
    d.polygon([(T * .38, T * .14), (T * .84, T * .04), (T * .84, T * .2), (T * .38, T * .3)], fill=ENCRE)


def i_manette(d, T):
    d.rounded_rectangle((T * .06, T * .28, T * .94, T * .74), int(T * .2), fill=ENCRE)
    d.ellipse((T * .06, T * .4, T * .38, T * .92), fill=ENCRE)
    d.ellipse((T * .62, T * .4, T * .94, T * .92), fill=ENCRE)
    d.rectangle((T * .2, T * .44, T * .34, T * .5), fill=(255, 255, 255, 255))
    d.rectangle((T * .24, T * .40, T * .30, T * .54), fill=(255, 255, 255, 255))
    d.ellipse((T * .66, T * .38, T * .74, T * .46), fill=(0, 200, 120, 255))
    d.ellipse((T * .74, T * .46, T * .82, T * .54), fill=(230, 60, 60, 255))


def i_coucou(d, T):  # main qui salue
    d.rounded_rectangle((T * .28, T * .36, T * .78, T * .9), int(T * .14), fill=(232, 160, 118, 255))
    for k in range(4):
        x = T * (.28 + k * .125)
        d.rounded_rectangle((x, T * (.10 + abs(k - 1.5) * .05), x + T * .1, T * .5), int(T * .05),
                            fill=(232, 160, 118, 255))
    d.rounded_rectangle((T * .1, T * .45, T * .34, T * .6), int(T * .06), fill=(232, 160, 118, 255))


def i_eclair(d, T):
    d.polygon([(T * .58, T * .04), (T * .2, T * .56), (T * .48, T * .56), (T * .38, T * .96),
               (T * .82, T * .40), (T * .52, T * .40)], fill=(255, 210, 0, 255))


def i_casque(d, T):
    d.arc((T * .14, T * .1, T * .86, T * .9), 180, 360, fill=(0, 210, 255, 255), width=int(T * .1))
    d.rounded_rectangle((T * .08, T * .46, T * .32, T * .86), int(T * .08), fill=(0, 210, 255, 255))
    d.rounded_rectangle((T * .68, T * .46, T * .92, T * .86), int(T * .08), fill=(0, 210, 255, 255))


# --- icônes météo (posées sur la carte de nuit) ---
def _nuage(d, T, dx=0.0, dy=0.0, couleur=(225, 230, 245, 255)):
    d.ellipse((T * (.12 + dx), T * (.42 + dy), T * (.46 + dx), T * (.76 + dy)), fill=couleur)
    d.ellipse((T * (.30 + dx), T * (.26 + dy), T * (.70 + dx), T * (.66 + dy)), fill=couleur)
    d.ellipse((T * (.52 + dx), T * (.40 + dy), T * (.88 + dx), T * (.76 + dy)), fill=couleur)
    d.rectangle((T * (.28 + dx), T * (.56 + dy), T * (.72 + dx), T * (.76 + dy)), fill=couleur)


def m_soleil(d, T):
    i_soleil(d, T)


def m_eclaircie(d, T):
    c = T * .36
    d.ellipse((c - T * .17, c - T * .17, c + T * .17, c + T * .17), fill=(255, 190, 0, 255))
    for k in range(8):
        a = k * math.pi / 4
        d.line((c + math.cos(a) * T * .24, c + math.sin(a) * T * .24,
                c + math.cos(a) * T * .33, c + math.sin(a) * T * .33), fill=(255, 190, 0, 255), width=int(T * .06))
    _nuage(d, T, .06, .12)


def m_nuage(d, T):
    _nuage(d, T, 0, -.04, (170, 180, 205, 255))
    _nuage(d, T, .06, .06)


def m_pluie(d, T):
    _nuage(d, T, 0, -.14, (180, 190, 215, 255))
    for k in range(3):
        x = T * (.32 + k * .18)
        d.line((x, T * .70, x - T * .07, T * .92), fill=(80, 170, 255, 255), width=int(T * .07))


def m_orage(d, T):
    _nuage(d, T, 0, -.16, (150, 155, 180, 255))
    d.polygon([(T * .52, T * .56), (T * .36, T * .80), (T * .50, T * .80), (T * .42, T * .98),
               (T * .66, T * .70), (T * .52, T * .70)], fill=(255, 210, 0, 255))


def m_brouillard(d, T):
    for k in range(4):
        y = T * (.28 + k * .16)
        d.rounded_rectangle((T * (.10 + (k % 2) * .08), y, T * (.90 - (k % 2) * .08), y + T * .08),
                            int(T * .04), fill=(190, 195, 215, 255))


def m_neige(d, T):
    _nuage(d, T, 0, -.14)
    for k in range(3):
        x = T * (.30 + k * .2)
        d.ellipse((x - T * .04, T * .78, x + T * .04, T * .86), fill=(255, 255, 255, 255))


def bulle_manette():
    T = 8
    w, h = 44, 38
    im = Image.new("RGBA", (w * T, h * T), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((2 * T, 2 * T, 42 * T, 30 * T), fill=(255, 255, 255, 255), outline=(0, 210, 255, 255), width=2 * T)
    d.ellipse((4 * T, 30 * T, 10 * T, 35 * T), fill=(255, 255, 255, 255))
    d.ellipse((1 * T, 34 * T, 4 * T, 37 * T), fill=(255, 255, 255, 255))
    icn = Image.new("RGBA", (24 * T, 24 * T), (0, 0, 0, 0))
    i_manette(ImageDraw.Draw(icn), 24 * T)
    im.alpha_composite(icn, (10 * T, 4 * T))
    im = im.resize((w, h), Image.LANCZOS)
    return sprite_transparent(im, (60, 30, 90))


# ---------------------------------------------------------------------------
# Polices : fichier .fnt, 4 niveaux par pixel (0 = vide … 3 = plein), 1 octet par pixel
# ---------------------------------------------------------------------------
CARACTERES = "".join(chr(c) for c in range(32, 127)) + "°éèêëàâäçîïôöùûüÉÈÀÇ…•"


def police(nom_fichier, taille, sortie, caracteres=CARACTERES):
    f = ImageFont.truetype(chercher_police(nom_fichier), taille)
    ascent, descent = f.getmetrics()
    h = ascent + descent
    entrees = []
    donnees = bytearray()
    for ch in caracteres:
        avance = f.getlength(ch)
        w = max(1, int(math.ceil(avance)) + 1)
        im = Image.new("L", (w, h), 0)
        ImageDraw.Draw(im).text((0, ascent), ch, font=f, fill=255, anchor="ls")
        a = np.asarray(im).astype(np.float32) / 255.0
        niveaux = np.clip(np.round(a * 3), 0, 3).astype(np.uint8)
        entrees.append((ord(ch), w, int(round(avance)), len(donnees)))
        donnees += niveaux.tobytes()
    tete_fichier = b"FNT1" + struct.pack("<BH", h, len(entrees))
    table = b"".join(struct.pack("<HBBI", c, w, a, o) for c, w, a, o in entrees)
    ecrire(sortie, tete_fichier + table + bytes(donnees))


# ---------------------------------------------------------------------------
def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    APERCUS.mkdir(parents=True, exist_ok=True)
    print("Fonds :")
    fonds = {"jour": fond_jour(), "nuit": fond_nuit(), "jeu": fond_jeu()}
    for nom, im in fonds.items():
        ecrire(f"fond_{nom}.bin", rgb565(im))
        im.convert("RGB").save(APERCUS / f"fond_{nom}.png")

    print("Mascotte :")
    halo_moyen = {"cou": (70, 60, 130), "oreilles": (110, 40, 120)}
    images = {
        "neutre": dict(),
        "cligne": dict(yeux="fermes"),
        "content": dict(yeux="contents", bouche="rire"),
        "surpris": dict(bouche="o"),
    }
    planche = Image.new("RGB", (PERSO_W * 8 + 70, PERSO_H + 10), (40, 30, 70))
    i = 0
    for casque in ("cou", "oreilles"):
        for nom, opts in images.items():
            im = perso(casque=casque, **opts)
            ecrire(f"perso_{casque}_{nom}.bin", rgb565(sprite_transparent(im, halo_moyen[casque])))
            planche.paste(im, (5 + i * (PERSO_W + 8), 5), im)
            i += 1
    planche.save(APERCUS / "mascotte.png")

    print("Images pour l'app Flutter :")
    dossier_app = ICI.parent.parent / "app" / "assets" / "images"
    dossier_app.mkdir(parents=True, exist_ok=True)
    for casque in ("cou", "oreilles"):
        for nom, opts in images.items():
            grand = perso(casque=casque, taille=(PERSO_W * 3, PERSO_H * 3), **opts)
            grand.save(dossier_app / f"perso_{casque}_{nom}.png", optimize=True)
            print(f"  perso_{casque}_{nom}.png")

    print("Icônes :")
    for nom, f in (("son", i_son), ("muet", i_muet), ("soleil", i_soleil), ("cadenas", i_cadenas),
                   ("clavier", i_clavier), ("souris", i_souris), ("appli", i_appli),
                   ("lune", i_lune), ("power", i_power), ("musique", i_musique),
                   ("manette", i_manette), ("coucou", i_coucou)):
        ecrire(f"ico_{nom}.bin", rgb565(icone(f)))
    ecrire("ico_eclair.bin", rgb565(icone(i_eclair, 12, CARTE_JOUR)))
    ecrire("ico_casque.bin", rgb565(icone(i_casque, 12, CARTE_JOUR)))
    ecrire("bulle_manette.bin", rgb565(bulle_manette()))
    for nom, f in (("soleil", m_soleil), ("eclaircie", m_eclaircie), ("nuage", m_nuage),
                   ("pluie", m_pluie), ("orage", m_orage), ("brouillard", m_brouillard),
                   ("neige", m_neige)):
        ecrire(f"meteo_{nom}.bin", rgb565(icone(f, 24, CARTE_NUIT)))

    print("Polices :")
    police("Inter-Black.otf", 54, "police_fps.fnt", "0123456789-")
    police("Inter-Bold.otf", 40, "police_heure.fnt", "0123456789:-")
    police("Inter-Bold.otf", 15, "police_m.fnt")
    police("Inter-SemiBold.otf", 12, "police_s.fnt")
    police("Inter-Medium.otf", 10, "police_xs.fnt")
    print(f"Terminé : {SORTIE}")


if __name__ == "__main__":
    main()
