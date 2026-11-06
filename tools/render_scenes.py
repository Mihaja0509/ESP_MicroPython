"""Banc de rendu des scènes de l'écran ESP32 : fait tourner esp/lib/ui.py sous CPython avec un faux
`framebuf` (numpy), sauve des aperçus PNG dans tools/assets/apercus/ et vérifie qu'aucun texte ne
se chevauche ni ne dépasse sur la mascotte.

    py -X utf8 tools\\render_scenes.py            # aperçus + vérification
    py -X utf8 tools\\render_scenes.py --mesures  # largeurs des polices

Nécessite : py -m pip install --user numpy pillow
"""
import os
import sys
import time
import types
from pathlib import Path

import numpy as np
from PIL import Image

RACINE = Path(__file__).resolve().parent.parent
ESP = RACINE / "esp"
SORTIE = RACINE / "tools" / "assets" / "apercus"
W, H = 320, 172
CARTE_DROITE = 185   # dernier pixel de la carte


# ------------------------------------------------------------------ faux framebuf (numpy)
class FrameBuffer:
    def __init__(self, buf, w, h, fmt, stride=None):
        self.w, self.h, self.fmt = w, h, fmt
        dtype = "<u2" if fmt == 1 else np.uint8
        self.a = np.frombuffer(buf, dtype=dtype, count=w * h).reshape(h, w)

    def fill(self, c):
        self.a[:] = c

    def _bornes(self, x, y, w, h):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        return x0, y0, x1, y1

    def fill_rect(self, x, y, w, h, c):
        x0, y0, x1, y1 = self._bornes(x, y, w, h)
        if x1 > x0 and y1 > y0:
            self.a[y0:y1, x0:x1] = c

    def hline(self, x, y, w, c):
        self.fill_rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        self.fill_rect(x, y, 1, h, c)

    def pixel(self, x, y, c=None):
        if 0 <= x < self.w and 0 <= y < self.h:
            if c is None:
                return int(self.a[y, x])
            self.a[y, x] = c

    def rect(self, x, y, w, h, c, fill=False):
        if fill:
            self.fill_rect(x, y, w, h, c)
            return
        self.hline(x, y, w, c)
        self.hline(x, y + h - 1, w, c)
        self.vline(x, y, h, c)
        self.vline(x + w - 1, y, h, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.pixel(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def ellipse(self, cx, cy, rx, ry, c, fill=False, m=15):
        yy, xx = np.ogrid[0:self.h, 0:self.w]
        dedans = ((xx - cx) / max(rx, 0.5)) ** 2 + ((yy - cy) / max(ry, 0.5)) ** 2 <= 1.0
        if not fill:
            dedans &= ~(((xx - cx) / max(rx - 1, 0.5)) ** 2 + ((yy - cy) / max(ry - 1, 0.5)) ** 2 <= 1.0)
        self.a[dedans] = c

    def blit(self, src, x, y, key=-1, palette=None):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + src.w), min(self.h, y + src.h)
        if x1 <= x0 or y1 <= y0:
            return
        s = src.a[y0 - y:y1 - y, x0 - x:x1 - x]
        if palette is not None:
            s = palette.a[0, s.astype(np.int64)]
        zone = self.a[y0:y1, x0:x1]
        zone[:] = np.where(s != key, s, zone)


framebuf = types.ModuleType("framebuf")
framebuf.FrameBuffer = FrameBuffer
framebuf.RGB565 = 1
framebuf.GS8 = 2
framebuf.MONO_HLSB = 3
sys.modules["framebuf"] = framebuf


# ------------------------------------------------------------------ horloge et heure simulées
class Horloge:
    ms = 0
    h, m = 17, 48      # heure affichée (modifiable par scénario)


time.ticks_ms = lambda: Horloge.ms
time.ticks_diff = lambda a, b: a - b
time.ticks_add = lambda a, b: a + b
HEURE = (2026, 11, 6, 17, 48, 30, 4, 310)
time.localtime = lambda *a: (HEURE[0], HEURE[1], HEURE[2], Horloge.h, Horloge.m, HEURE[5], HEURE[6], HEURE[7])

os.chdir(ESP)
sys.path.insert(0, str(ESP / "lib"))
import polices  # noqa: E402
import ui  # noqa: E402

JOURNAL = []
_ecrire = polices.Police.ecrire


def _ecrire_espion(self, fb, texte, x, y, avant, fond):
    JOURNAL.append((self, texte, x, y))
    return _ecrire(self, fb, texte, x, y, avant, fond)


polices.Police.ecrire = _ecrire_espion


class EcranFaux:
    def __init__(self):
        self.tampon = bytearray(W * H * 2)
        self.fb = FrameBuffer(self.tampon, W, H, 1)
        self.image = None

    def afficher(self):
        self.image = np.frombuffer(bytes(self.tampon), dtype="<u2").reshape(H, W).copy()


def vers_png(image, chemin, echelle=2):
    v = ((image & 0xFF) << 8) | (image >> 8)           # l'écran reçoit les octets inversés
    r = ((v >> 11) & 31) * 255 // 31
    g = ((v >> 5) & 63) * 255 // 63
    b = (v & 31) * 255 // 31
    rgb = np.stack([r, g, b], axis=-1).astype(np.uint8)
    img = Image.fromarray(rgb)
    if echelle != 1:
        img = img.resize((W * echelle, H * echelle), Image.NEAREST)
    img.save(chemin)


def masque_encre(interface, entree):
    """Pixels réellement dessinés par un texte (glyphes non vides), dilatés de 1 px."""
    police, texte, x, y = entree
    m = np.zeros((H, W), dtype=bool)
    for ch in texte:
        g = police.glyphes.get(ord(ch)) or police.glyphes.get(63)
        if g is None:
            continue
        fb, avance = g
        encre = fb.a > 0
        gx0, gy0 = max(0, x), max(0, y)
        gx1, gy1 = min(W, x + fb.w), min(H, y + fb.h)
        if gx1 > gx0 and gy1 > gy0:
            m[gy0:gy1, gx0:gx1] |= encre[gy0 - y:gy1 - y, gx0 - x:gx1 - x]
        x += avance
    d = m.copy()
    d[1:, :] |= m[:-1, :]
    d[:-1, :] |= m[1:, :]
    d[:, 1:] |= m[:, :-1]
    d[:, :-1] |= m[:, 1:]
    return m, d


def verifier(interface, nom):
    """Chevauchements entre textes + textes qui débordent sur la mascotte (x >= 200)."""
    noms = {id(getattr(interface, n)): n for n in ("f_fps", "f_heure", "f_m", "f_s", "f_xs")}
    # les « z » de la mascotte endormie se frôlent exprès : ignorés
    masques = [(e, *masque_encre(interface, e)) for e in JOURNAL if e[1].strip() and e[1] != "z"]
    problemes = []
    for i in range(len(masques)):
        e1, m1, d1 = masques[i]
        if m1.any() and np.nonzero(m1)[1].max() >= 200 and e1[2] < 200:
            problemes.append(f"déborde sur la mascotte : {e1[1]!r} ({noms[id(e1[0])]}) jusqu'à x={np.nonzero(m1)[1].max()}")
        for j in range(i + 1, len(masques)):
            e2, m2, d2 = masques[j]
            if (d1 & m2).any() or (m1 & d2).any():
                problemes.append(
                    f"chevauchement : {e1[1]!r} ({noms[id(e1[0])]} @{e1[2]},{e1[3]}) / "
                    f"{e2[1]!r} ({noms[id(e2[0])]} @{e2[2]},{e2[3]})")
    # scènes normale / calme / nuit : le bloc pièce à droite de l'heure garde 12 px avant le bord de la carte
    if nom.split("_")[0] in ("normal", "calme", "nuit"):
        for e, m, d in masques:
            if e[3] < 60 and e[2] >= 100 and m.any() and np.nonzero(m)[1].max() > CARTE_DROITE - 12:
                problemes.append(f"marge < 12 px au bord droit : {e[1]!r} jusqu'à x={np.nonzero(m)[1].max()}")
    return problemes


# ------------------------------------------------------------------ scénarios
def etat_base():
    return {"connecte": True, "stat": {"cpu": 23, "ram": 58, "vol": 60, "bat": 82, "chg": 1},
            "gpu": {"temp": 52, "charge": 35, "vram": 3}, "perf": {"cpu_temp": 61, "fps": -1, "total": -1},
            "evt": {"casque": "HECATE G30", "manette": 0, "verrou": 0, "jeu": "", "video": "",
                    "video_titre": "", "inactif": 0, "video_pos": None},
            "meteo": [], "eteint": False, "arret_fin": None, "arret_total": 60000, "lum": 85,
            "master": None, "meteo_now": None, "clim": None, "piece": None}


def clim(on=True, mode="cool", temp=24, reste=0, auto=False, plage=None):
    return {"on": on, "mode": mode, "temp": temp, "reste": reste, "auto": auto, "plage": plage,
            "recu": Horloge.ms}


def scenarios():
    """(nom du fichier, fonction qui prépare l'état, instants simulés en ms)."""
    liste = []

    def normal(**kw):
        e = etat_base()
        e.update(kw)
        return e

    liste.append(("normal_sans_clim", lambda: normal(), (1000,)))
    liste.append(("normal_clim_minuteur",
                  lambda: normal(clim=clim(reste=1380, auto=True), piece=(24.1, 58.0, 997)), (1000, 6000, 11000)))
    liste.append(("normal_clim_longue",
                  lambda: normal(clim=clim(mode="dry", temp=26, reste=3900, auto=True), piece=(31.4, 67.0, 997)),
                  (1000, 6000, 11000)))
    liste.append(("normal_plage_clim_eteinte",
                  lambda: normal(clim=clim(on=False, plage=(1140, 1260)), piece=(24.1, 58.0, 997)), (1000, 6000)))
    liste.append(("normal_clim_froide_trop_chaude",
                  lambda: normal(piece=(30.2, 71.0, 997)), (1000, 6000)))

    # pire cas : heure la plus large (00:00 = 121 px) ou la plus étroite (11:11), température à 2 chiffres
    # + une décimale, humidité à 3 chiffres
    liste.append(("normal_pire_heure_large", lambda: normal(piece=(31.4, 100.0, 997), clim=clim(reste=600, auto=True)),
                  (1000, 6000), (0, 0)))
    liste.append(("normal_pire_heure_etroite", lambda: normal(piece=(31.4, 100.0, 997)), (1000,), (11, 11)))
    liste.append(("normal_sans_mesure_heure_large", lambda: normal(), (1000,), (0, 0)))
    liste.append(("normal_negatif", lambda: normal(piece=(-5.2, 100.0, 997)), (1000,), (0, 0)))

    def calme(**kw):
        e = normal(**kw)
        e["evt"] = dict(e["evt"], inactif=31)
        return e
    liste.append(("calme_sans_clim", lambda: calme(), (1000,)))
    liste.append(("calme_clim", lambda: calme(clim=clim(reste=900), piece=(24.1, 58.0, 997)), (1000, 6000)))

    def nuit(**kw):
        e = normal(**kw)
        e["evt"] = dict(e["evt"], verrou=1)
        return e
    liste.append(("calme_pire_heure_large", lambda: calme(piece=(31.4, 100.0, 997), clim=clim(reste=600)),
                  (1000, 6000), (0, 0)))
    liste.append(("nuit_pire_heure_large", lambda: nuit(piece=(31.4, 100.0, 997), clim=clim(reste=2700, auto=True)),
                  (1000,), (0, 0)))
    liste.append(("nuit_sans_clim", lambda: nuit(), (1000,)))
    liste.append(("nuit_clim", lambda: nuit(clim=clim(reste=2700, auto=True), piece=(24.1, 58.0, 997)), (1000,)))

    def jeu(**kw):
        e = normal(**kw)
        e["evt"] = dict(e["evt"], jeu="God of War Ragnarok")
        e["perf"] = {"cpu_temp": 68, "fps": 87, "total": 312, "jour_total": 192, "jour_jeu": 100}
        e["gpu"] = {"temp": 71, "charge": 94, "vram": 6}
        return e
    liste.append(("jeu_sans_clim", lambda: jeu(), (1000, 6000, 11000, 16000, 21000, 26000)))
    liste.append(("jeu_clim", lambda: jeu(clim=clim(reste=1380, auto=True), piece=(24.1, 58.0, 997)),
                  (1000, 6000, 11000, 16000, 21000, 26000, 31000)))
    return liste


def main():
    if "--mesures" in sys.argv:
        e = EcranFaux()
        i = ui.Interface(e)
        for n in ("f_fps", "f_heure", "f_m", "f_s", "f_xs"):
            p = getattr(i, n)
            print(f"{n:8s} hauteur={p.hauteur:3d}  '88:88'={p.largeur('88:88'):3d}  '24.1°'={p.largeur('24.1°'):3d}  "
                  f"'58 %'={p.largeur('58 %'):3d}  '--°'={p.largeur('--°'):3d}  'AC Cool 24°'={p.largeur('AC Cool 24°'):3d}")
        return
    SORTIE.mkdir(parents=True, exist_ok=True)
    total = 0
    for nom, fabrique, instants, *heure in scenarios():
        Horloge.h, Horloge.m = heure[0] if heure else (17, 48)
        for k, t in enumerate(instants):
            ecran = EcranFaux()
            interface = ui.Interface(ecran)
            interface.hist_fps = [60, 72, 88, 91, 87, 84, 80, 86, 90, 87, 85, 88]
            Horloge.ms = 100000
            etat = fabrique()
            for e in (etat["clim"],):
                if e:
                    e["recu"] = Horloge.ms
            # le mode s'installe 10 s avant (la bulle « Hello! » du changement de scène a disparu),
            # puis l'image mesurée à l'instant t
            Horloge.ms = 90000
            interface.dessiner(etat, Horloge.ms)
            Horloge.ms = 100000 + t     # 100000 = multiple de 5 s : la phase de la ligne du bas = t // 5000
            JOURNAL.clear()
            interface.dessiner(etat, Horloge.ms)
            suffixe = f"_{k}" if len(instants) > 1 else ""
            chemin = SORTIE / f"scene_{nom}{suffixe}.png"
            vers_png(ecran.image, chemin)
            problemes = verifier(interface, nom)
            total += len(problemes)
            print(f"{chemin.name}: {'OK' if not problemes else str(len(problemes)) + ' problème(s)'}")
            for p in problemes:
                print("   !", p)
    print(f"\nproblèmes de texte : {total}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
