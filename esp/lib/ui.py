# Interface animée de l'écran (Phase 4) : fonds, mascotte, polices, animations.
# Les images viennent de /assets (créées par tools/assets/generer_assets.py).
import math
import random
import time

import framebuf

from polices import Police, rgb565

DOSSIER = "assets/"
W, H = 320, 172
PERSO_W, PERSO_H = 95, 150
PERSO_X, PERSO_Y = W - PERSO_W - 12, H - PERSO_H - 6
CLE = rgb565(255, 0, 255)  # magenta = transparent dans les images

# Couleurs (r, g, b) — les fonds des cartes doivent être identiques au générateur
CARTE_JOUR = (18, 14, 40)
CARTE_NUIT = (10, 12, 30)
CARTE_JEU = (8, 6, 22)
BLANC = (255, 255, 255)
GRIS = (150, 150, 190)
DOUX = (200, 200, 235)
CYAN = (0, 210, 255)
VERT = (110, 255, 170)
ORANGE = (255, 170, 60)
ROUGE = (255, 70, 80)
MAGENTA = (255, 40, 200)
ENCRE = (40, 40, 80)

JOURS = ("Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim.")
MOIS = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.",
        "nov.", "déc.")

DUREE_BANDEAU = 2400
DUREE_REACTION = 1400


def _charger(nom, w, h):
    buf = bytearray(w * h * 2)
    with open(DOSSIER + nom, "rb") as f:
        f.readinto(buf)
    return framebuf.FrameBuffer(buf, w, h, framebuf.RGB565)


def _charger_brut(nom, taille):
    buf = bytearray(taille)
    with open(DOSSIER + nom, "rb") as f:
        f.readinto(buf)
    return buf


def _anneau(rayon, n=36):
    pts = []
    for i in range(n):
        a = -math.pi / 2 + 2 * math.pi * i / n
        pts.append((int(round(math.cos(a) * rayon)), int(round(math.sin(a) * rayon))))
    return pts


class Interface:
    def __init__(self, ecran):
        self.ecran = ecran
        self.fb = ecran.fb
        self.f_fps = Police(DOSSIER + "police_fps.fnt")
        self.f_heure = Police(DOSSIER + "police_heure.fnt")
        self.f_m = Police(DOSSIER + "police_m.fnt")
        self.f_s = Police(DOSSIER + "police_s.fnt")
        self.f_xs = Police(DOSSIER + "police_xs.fnt")
        taille_fond = W * H * 2
        self.fonds = {n: _charger_brut("fond_%s.bin" % n, taille_fond) for n in ("jour", "nuit", "jeu")}
        self.persos = {}
        for casque in ("cou", "oreilles"):
            for nom in ("neutre", "cligne", "content", "surpris"):
                self.persos[(casque, nom)] = _charger("perso_%s_%s.bin" % (casque, nom), PERSO_W, PERSO_H)
        self.icones = {}
        for nom in ("son", "muet", "soleil", "cadenas", "clavier", "souris", "appli", "lune",
                    "power", "musique", "manette", "coucou"):
            self.icones[nom] = _charger("ico_%s.bin" % nom, 18, 18)
        self.ico_eclair = _charger("ico_eclair.bin", 12, 12)
        self.ico_casque = _charger("ico_casque.bin", 12, 12)
        self.bulle_manette = _charger("bulle_manette.bin", 44, 38)
        self.icones_meteo = {}
        for nom in ("soleil", "eclaircie", "nuage", "pluie", "orage", "brouillard", "neige"):
            self.icones_meteo[nom] = _charger("meteo_%s.bin" % nom, 24, 24)
        self.points_anneau = _anneau(19)
        random.seed(7)
        self.particules = [[random.randint(196, W - 1), random.randint(0, H - 1),
                            random.randint(3, 10) / 10, random.randint(0, 62) / 10] for _ in range(24)]
        self.mode = None
        self.mode_depuis = time.ticks_ms()
        self.bandeau = None      # (icône, texte, début)
        self.reaction = 0        # début de la dernière réaction (saut + visage content)
        self.bulle = None        # icône dans la bulle près de la tête
        self.prochain_clin = time.ticks_add(time.ticks_ms(), 3000)
        self.valeurs = {}        # valeurs affichées, qui glissent vers les vraies valeurs

    # ------------------------------------------------------------------ outils
    def _couleur(self, rgb):
        return rgb565(*rgb)

    def reagir(self, icone, texte, bandeau=True, duree=DUREE_BANDEAU):
        maintenant = time.ticks_ms()
        if bandeau:
            self.bandeau = (icone, texte, maintenant, duree)
        self.reaction = maintenant
        self.bulle = icone

    def _age(self, debut, maintenant):
        return time.ticks_diff(maintenant, debut)

    def _lisse(self, cle, valeur):
        """Fait glisser la valeur affichée vers la vraie valeur (animation douce)."""
        if valeur is None or valeur < 0:
            self.valeurs.pop(cle, None)
            return valeur
        avant = self.valeurs.get(cle, valeur)
        nouveau = avant + (valeur - avant) * 0.35
        if abs(nouveau - valeur) < 0.5:
            nouveau = valeur
        self.valeurs[cle] = nouveau
        return int(nouveau + 0.5)

    def luminosite_voulue(self, maintenant):
        age = self._age(self.mode_depuis, maintenant)
        if self.mode == "absent":
            return 30 if age < 120000 else 6
        if self.mode == "verrou":
            return 35
        return 85

    # ------------------------------------------------------------------ dessin
    def dessiner(self, etat, maintenant):
        mode = self._choisir_mode(etat)
        if mode != self.mode:
            self._changer_mode(self.mode, mode, etat, maintenant)
        t = maintenant / 1000
        fb = self.fb
        if mode == "jeu":
            fond, carte = "jeu", CARTE_JEU
        elif mode in ("absent", "verrou"):
            fond, carte = "nuit", CARTE_NUIT
        else:
            fond, carte = "jour", CARTE_JOUR
        self.ecran.tampon[:] = self.fonds[fond]
        self._particules(t, mode)
        if mode == "jeu":
            self._scene_jeu(etat, carte)
        elif mode == "normal":
            self._scene_normale(etat, carte, maintenant)
        else:
            self._scene_nuit(etat, carte, mode)
        self._mascotte(etat, mode, t, maintenant)
        self._bandeau(maintenant)
        self.ecran.afficher()

    def _choisir_mode(self, etat):
        if not etat["connecte"]:
            return "absent"
        if etat["evt"]["verrou"]:
            return "verrou"
        if etat["evt"]["jeu"]:
            return "jeu"
        return "normal"

    def _changer_mode(self, ancien, nouveau, etat, maintenant):
        self.mode = nouveau
        self.mode_depuis = maintenant
        if ancien is None:
            self.reagir("coucou", "Bonjour !")
        elif nouveau == "absent":
            self.reagir("power", "À bientôt !")
        elif ancien == "absent":
            self.reagir("coucou", "Bonjour Mihaja !")
        elif nouveau == "jeu":
            self.reagir("manette", "Mode jeu")
        elif nouveau == "verrou":
            self.reagir("cadenas", "PC verrouillé")
        elif ancien == "verrou":
            self.reagir("coucou", "Re-bonjour !")

    def _particules(self, t, mode):
        fb = self.fb
        if mode == "jeu":
            couleurs = (rgb565(255, 60, 210), rgb565(0, 220, 255))
        elif mode == "normal":
            couleurs = (rgb565(255, 240, 220), rgb565(255, 200, 150))
        else:
            couleurs = (rgb565(170, 190, 255), rgb565(120, 140, 220))
        for p in self.particules:
            p[1] -= p[2]
            if p[1] < 0:
                p[1] = H
                p[0] = random.randint(196, W - 1)
            x = int(p[0] + math.sin(t * 2 + p[3]) * 2)
            if x < 200 and p[1] < 168:
                continue  # pas de particules sur la carte de gauche
            taille = 2 if p[2] > 0.7 else 1
            if math.sin(t * 4 + p[3]) > -0.3:
                fb.fill_rect(x, int(p[1]), taille, taille, couleurs[0 if taille == 2 else 1])

    # ------------------------------------------------------------------ scènes
    def _heure_date(self, carte, y_heure=8):
        lt = time.localtime()
        if lt[0] >= 2025:
            heure = "%02d:%02d" % (lt[3], lt[4])
            date = "%s %d %s" % (JOURS[lt[6]], lt[2], MOIS[lt[1] - 1])
            secondes = lt[5]
        else:
            heure, date, secondes = "--:--", "", 0
        self.f_heure.ecrire(self.fb, heure, 16, y_heure, BLANC, carte)
        if date:
            self.f_s.ecrire(self.fb, date, 18, y_heure + 48, DOUX, carte)
        return secondes

    def _anneau_valeur(self, cx, cy, valeur, couleur, nom, carte):
        fb = self.fb
        eteint = rgb565(50, 46, 84)
        allume = rgb565(*couleur)
        n = len(self.points_anneau)
        nb = 0 if valeur is None or valeur < 0 else int(min(100, valeur) * n / 100 + 0.5)
        for i, (dx, dy) in enumerate(self.points_anneau):
            fb.fill_rect(cx + dx - 1, cy + dy - 1, 3, 3, allume if i < nb else eteint)
        if valeur is not None and valeur >= 0:
            self.f_m.ecrire_centre(fb, "%d" % valeur, cx, cy - 9, BLANC, carte)
        self.f_xs.ecrire_centre(fb, nom, cx, cy + 22, GRIS, carte)

    def _scene_normale(self, etat, carte, maintenant):
        fb = self.fb
        secondes = self._heure_date(carte)
        fb.fill_rect(18, 76, 158, 3, rgb565(45, 40, 80))
        fb.fill_rect(18, 76, 158 * secondes // 59, 3, rgb565(*CYAN))
        st = etat["stat"]
        self._anneau_valeur(42, 108, self._lisse("cpu", st["cpu"]), VERT, "CPU", carte)
        self._anneau_valeur(98, 108, self._lisse("ram", st["ram"]), CYAN, "RAM", carte)
        # volume
        vol = self._lisse("vol", st["vol"])
        if vol >= 0:
            self.f_xs.ecrire(fb, "VOL", 140, 128, GRIS, carte)
            for i in range(5):
                h = 5 + i * 4
                allume = vol >= (i + 1) * 20 - 10
                fb.fill_rect(140 + i * 7, 122 - h, 5, h, rgb565(*CYAN) if allume else rgb565(50, 46, 84))
        # ligne du bas : batterie + casque
        x = 16
        if st["bat"] >= 0:
            if st["chg"]:
                fb.blit(self.ico_eclair, x, 147, CLE)
                x += 13
            couleur_bat = ROUGE if st["bat"] < 20 and not st["chg"] else DOUX
            x = self.f_xs.ecrire(fb, "%d %%" % st["bat"], x, 147, couleur_bat, carte) + 8
        if etat["evt"]["casque"]:
            fb.blit(self.ico_casque, x, 147, CLE)
            nom = self.f_xs.couper(etat["evt"]["casque"], 176 - x - 14)
            self.f_xs.ecrire(fb, nom, x + 14, 147, CYAN, carte)

    def _barre_temp(self, y, nom, valeur, carte):
        fb = self.fb
        self.f_s.ecrire(fb, nom, 16, y - 2, GRIS, carte)
        fb.fill_rect(52, y + 3, 96, 6, rgb565(40, 30, 70))
        if valeur is None or valeur < 0:
            return
        couleur = VERT if valeur < 65 else (ORANGE if valeur < 82 else ROUGE)
        fb.fill_rect(52, y + 3, min(96, valeur * 96 // 100), 6, rgb565(*couleur))
        self.f_m.ecrire(fb, "%d°" % valeur, 154, y - 4, couleur, carte)

    def _scene_jeu(self, etat, carte):
        fb = self.fb
        nom = self.f_s.couper(etat["evt"]["jeu"], 176)
        self.f_s.ecrire(fb, nom, 14, 10, CYAN, carte)
        fps = self._lisse("fps", etat["perf"]["fps"])
        if fps >= 0:
            couleur = VERT if fps >= 60 else (ORANGE if fps >= 30 else ROUGE)
            x = self.f_fps.ecrire(fb, "%d" % fps, 12, 24, couleur, carte)
        else:
            x = self.f_fps.ecrire(fb, "--", 12, 24, (70, 60, 110), carte)
        self.f_m.ecrire(fb, "FPS", x + 6, 64, MAGENTA, carte)
        self._barre_temp(100, "CPU", self._lisse("tcpu", etat["perf"]["cpu_temp"]), carte)
        self._barre_temp(124, "GPU", self._lisse("tgpu", etat["gpu"]["temp"]), carte)
        morceaux = []
        if etat["gpu"]["charge"] >= 0:
            morceaux.append("GPU %d %%" % etat["gpu"]["charge"])
        if etat["stat"]["ram"] >= 0:
            morceaux.append("RAM %d %%" % etat["stat"]["ram"])
        if morceaux:
            self.f_xs.ecrire(fb, "   •   ".join(morceaux), 16, 148, GRIS, carte)

    def _scene_nuit(self, etat, carte, mode):
        fb = self.fb
        self._heure_date(carte, y_heure=4)
        titre = "PC verrouillé" if mode == "verrou" else "PC en veille"
        self.f_xs.ecrire(fb, titre, 120, 58, GRIS, carte)
        jours = etat.get("meteo") or []
        if not jours:
            self.f_m.ecrire(fb, "Je t'attends…", 16, 92, DOUX, carte)
            self.f_xs.ecrire(fb, "Météo : en attente du PC…", 16, 118, GRIS, carte)
            return
        for i, j in enumerate(jours[:2]):
            y = 76 + i * 45
            fb.blit(self.icones_meteo.get(j["icone"], self.icones_meteo["nuage"]), 14, y + 4, CLE)
            self.f_xs.ecrire(fb, "Aujourd'hui" if i == 0 else "Demain", 46, y, GRIS, carte)
            self.f_m.ecrire(fb, "%d° / %d°" % (j["tmax"], j["tmin"]), 46, y + 11, BLANC, carte)
            if j["pluie"] >= 20 and j["heure_pluie"] is not None:
                texte = "Pluie %d %% vers %d h" % (j["pluie"], j["heure_pluie"])
                couleur = CYAN
            else:
                texte, couleur = "Pas de pluie prévue", VERT
            self.f_xs.ecrire(fb, texte, 46, y + 30, couleur, carte)

    # ------------------------------------------------------------------ mascotte
    def _mascotte(self, etat, mode, t, maintenant):
        fb = self.fb
        casque = "oreilles" if (etat["evt"]["casque"] or mode == "jeu") else "cou"
        dort = mode in ("absent", "verrou")
        age_reaction = self._age(self.reaction, maintenant)
        if time.ticks_diff(maintenant, self.prochain_clin) >= 0:
            self.prochain_clin = time.ticks_add(maintenant, random.randint(2500, 5500))
        clin = time.ticks_diff(maintenant, self.prochain_clin) > -160
        if dort:
            visage = "cligne"
        elif age_reaction < DUREE_REACTION:
            visage = "content"
        elif clin:
            visage = "cligne"
        else:
            visage = "neutre"
        souffle = 0.8 if dort else 2.2
        dy = int(round(2 * math.sin(t * souffle)))
        if age_reaction < 500:
            dy -= int(7 * math.sin(math.pi * age_reaction / 500))
        fb.blit(self.persos[(casque, visage)], PERSO_X, PERSO_Y + dy, CLE)
        if dort:
            for i in range(3):
                ph = (t * 0.6 + i / 3) % 1
                x = PERSO_X + 70 + int(ph * 16) + i * 3
                y = PERSO_Y + 22 - int(ph * 28) - i * 5
                lum = int(255 * (1 - ph))
                self.f_m.ecrire(fb, "z", x, y, (lum, lum, min(255, lum + 40)), (20, 22, 60))
        pensee = mode == "jeu" and etat["evt"]["manette"]
        if pensee:
            fb.blit(self.bulle_manette, PERSO_X - 34, PERSO_Y + 2 + dy // 2, CLE)
        # la petite bulle de réaction n'est pas dessinée par-dessus la bulle « manette »
        if self.bulle and age_reaction < DUREE_REACTION and not dort and not pensee:
            cx, cy = PERSO_X - 2, PERSO_Y + 24
            fb.ellipse(cx, cy, 15, 15, rgb565(*CYAN), True)
            fb.ellipse(cx, cy, 13, 13, rgb565(*BLANC), True)
            ico = self.icones.get(self.bulle)
            if ico:
                fb.blit(ico, cx - 9, cy - 9, CLE)

    def _bandeau(self, maintenant):
        if self.bandeau is None:
            return
        icone, texte, debut, duree = self.bandeau
        age = self._age(debut, maintenant)
        if age > duree:
            self.bandeau = None
            return
        largeur = min(240, self.f_m.largeur(texte) + 46)
        if age < 250:
            x = -largeur + int((largeur + 8) * age / 250)
        elif age > duree - 250:
            x = 8 - int((largeur + 8) * (age - (duree - 250)) / 250)
        else:
            x = 8
        fb = self.fb
        blanc = rgb565(*BLANC)
        y, h = 8, 26
        fb.fill_rect(x + 13, y, largeur - 26, h, blanc)
        fb.ellipse(x + 13, y + 13, 13, 13, blanc, True)
        fb.ellipse(x + largeur - 13, y + 13, 13, 13, blanc, True)
        ico = self.icones.get(icone)
        if ico:
            fb.blit(ico, x + 8, y + 4, CLE)
        self.f_m.ecrire(fb, self.f_m.couper(texte, largeur - 44), x + 32, y + 4, ENCRE, BLANC)
