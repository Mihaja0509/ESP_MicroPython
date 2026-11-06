# Interface animée de l'écran (Phase 4) : fonds, mascotte, polices, animations.
# Les images viennent de /assets (créées par tools/assets/generer_assets.py).
# Phase 10 : scène « cinéma » (vidéo), scène « calme » (PC allumé mais inutilisé),
# météo 2 min toutes les 10 min dans la scène normale, mode jeu enrichi (courbe des FPS,
# chrono de session, temps total du jeu, alerte de chauffe).
# Phase 11 : scène « master » (labo AR de nuit, mascotte en veste de labo + lunettes AR) :
# échéance en J-x, objectif du jour, lecture, rédaction, dernier résultat de mesure ou réunion.
# Elle s'affiche : briefing du matin (60 s), 20 s toutes les 5 min pendant le travail de recherche,
# 1 suggestion sur 3 de la scène calme (15 s), et 15 s après un événement (MASTER_INFO).
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
CARTE_CINE = (16, 6, 12)
CARTE_CALME = (14, 20, 42)
CARTE_LABO = (20, 28, 48)
VIOLET = (150, 110, 255)
CYAN_AR = (0, 200, 230)
TEXTE_AR = (230, 236, 245)
GRIS_AR = (140, 150, 170)
BLANC = (255, 255, 255)
GRIS = (150, 150, 190)
DOUX = (200, 200, 235)
CYAN = (0, 210, 255)
VERT = (110, 255, 170)
ORANGE = (255, 170, 60)
ROUGE = (255, 70, 80)
MAGENTA = (255, 40, 200)
ENCRE = (40, 40, 80)
OR = (240, 190, 80)

JOURS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MOIS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
        "Nov", "Dec")

DUREE_BANDEAU = 2400
DUREE_REACTION = 1400

# Phase 10
METEO_TOUTES = 10          # min : la météo remplace les mesures de la scène normale…
METEO_PENDANT = 2          # … pendant 2 min (hh:00-hh:01, hh:10-hh:11, …)
SUGGESTION_MS = 45000      # scène calme : une nouvelle suggestion toutes les 45 s
BULLE_CALME_MS = 15000     # scène calme : la mascotte montre l'icône 3 s toutes les 15 s
PAUSE_JEU_MS = 2 * 3600 * 1000   # rappel « petite pause ? » toutes les 2 h de jeu
CHAUFFE_GPU = 83           # °C
CHAUFFE_CPU = 92           # °C
CHAUFFE_RAPPEL_MS = 5 * 60 * 1000
BRIEFING_MS = 60000        # scène master au premier usage du jour (après 6 h)
TRAVAIL_CYCLE_MS = 300000  # pendant le travail de recherche : 20 s toutes les 5 min
TRAVAIL_MONTRE_MS = 20000
INFO_MS = 15000            # après un événement (nouveau résultat, réunion dans 1 h…)
FICHIER_BRIEFING = "briefing.txt"
RAPPELS_MASTER = (
    ("livre", "One section at a time."), ("stylo", "Content first, style later."),
    ("stylo", "Cite while you write."), ("livre", "Source noted?"),
    ("livre", "1 paper read > 3 opened."), ("lunettes", "Reread your question."),
    ("calendrier", "A question for your SV?"), ("graphe", "Measure 3x, conclude 1x."),
    ("graphe", "Hz, mode, temp: noted?"), ("livre", "Matrix up to date?"),
    ("livre", "Journal quartile checked?"), ("stylo", "Structure, then refine."),
    ("chrono", "Commit, then rest."), ("chrono", "Five-minute break?"),
    ("stylo", "Write first, polish later."),
)
COULEURS_SOURCES = {"YouTube": (255, 70, 70), "Netflix": (229, 30, 40), "VLC": (255, 150, 30),
                    "Anime-Sama": (90, 170, 255), "Crunchyroll": (255, 130, 40),
                    "Twitch": (170, 110, 255), "Prime Video": (40, 170, 255),
                    "Disney+": (90, 140, 255)}


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


def duree_texte(minutes):
    """95 -> « 1h 35 » ; 40 -> « 40 min »."""
    if minutes < 60:
        return "%d min" % minutes
    return "%dh %02d" % (minutes // 60, minutes % 60)


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
        self.fonds = {n: _charger_brut("fond_%s.bin" % n, taille_fond)
                      for n in ("jour", "nuit", "jeu", "cine", "calme", "labo")}
        self.persos = {}
        for casque in ("cou", "oreilles"):
            for nom in ("neutre", "cligne", "content", "surpris"):
                self.persos[(casque, nom)] = _charger("perso_%s_%s.bin" % (casque, nom), PERSO_W, PERSO_H)
        for nom in ("neutre", "cligne", "content", "surpris"):  # tenue labo AR (scène master)
            self.persos[("ar", nom)] = _charger("perso_ar_%s.bin" % nom, PERSO_W, PERSO_H)
        self.icones = {}
        for nom in ("son", "muet", "soleil", "cadenas", "clavier", "souris", "appli", "lune",
                    "power", "musique", "manette", "coucou",
                    "popcorn", "eau", "fenetre", "livre", "lit", "thermo", "chrono", "etirer",
                    "stylo", "graphe", "lunettes", "calendrier"):
            self.icones[nom] = _charger("ico_%s.bin" % nom, 18, 18)
        self.ico_eclair = _charger("ico_eclair.bin", 12, 12)
        self.ico_casque = _charger("ico_casque.bin", 12, 12)
        self.bulle_manette = _charger("bulle_manette.bin", 44, 38)
        self.popcorn = _charger("popcorn_main.bin", 24, 26)
        self.goutte = _charger("goutte.bin", 8, 11)
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
        self.lum = 85            # luminosité choisie dans l'app (etat["lum"])
        self.noir_affiche = False  # mode « éteint » : l'image noire est déjà sur l'écran
        # Phase 10 : mode jeu
        self.jeu_nom = ""        # jeu de la session en cours
        self.jeu_debut = 0       # ticks du début de la session de jeu
        self.pause_suivante = 0  # ticks du prochain rappel « petite pause ? »
        self.chauffe_suivante = 0
        self.hist_fps = []       # FPS de chaque seconde (60 dernières)
        self.hist_seconde = 0    # ticks de la dernière valeur ajoutée
        self.dernier_jeu = ""    # pour proposer « Reprendre … ? » dans la scène calme
        self.chaud = False
        self.bulle_calme = None  # icône de la suggestion affichée (scène calme)
        # Phase 11 : scène master
        self.base = None          # scène « de fond » (normale, calme…) sans la scène master
        self.base_depuis = time.ticks_ms()
        self.master_fin = None    # ticks de fin d'un affichage forcé (briefing, événement)
        self.travail_depuis = None
        self.rappel = 0           # prochain rappel de la liste RAPPELS_MASTER
        self.surpris_jusqua = None
        self.tard_jour = -1       # jour où « on reprend demain ? » a déjà été dit
        try:
            with open(FICHIER_BRIEFING) as f:
                self.briefing_jour = f.read().strip()
        except OSError:
            self.briefing_jour = ""

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

    def _lignes(self, police, texte, largeur, nb_max):
        """Coupe `texte` en au plus `nb_max` lignes de `largeur` pixels (« … » à la fin si trop long)."""
        mots = texte.split()
        lignes = []
        courante = ""
        while mots:
            essai = (courante + " " + mots[0]) if courante else mots[0]
            if police.largeur(essai) <= largeur:
                courante = essai
                mots.pop(0)
                continue
            if not courante:  # un mot plus large que la ligne
                courante = police.couper(mots.pop(0), largeur)
            lignes.append(courante)
            courante = ""
            if len(lignes) == nb_max:
                break
        if courante and len(lignes) < nb_max:
            lignes.append(courante)
        if mots and lignes:
            lignes[-1] = police.couper(lignes[-1] + " " + " ".join(mots), largeur)
        return lignes

    def luminosite_voulue(self, maintenant):
        """Luminosité du rétroéclairage. Les niveaux suivent celle choisie dans l'app
        (85 = réglage d'origine : verrou 35, absent 30 puis 6, vidéo 55, calme 60)."""
        age = self._age(self.mode_depuis, maintenant)
        lum = self.lum
        if self.mode == "eteint":
            return 0
        if self.mode == "absent":
            return max(4, lum * 30 // 85) if age < 120000 else max(2, lum * 6 // 85)
        if self.mode == "verrou":
            return max(5, lum * 35 // 85)
        if self.mode == "video":
            return max(5, lum * 55 // 85)
        if self.mode == "calme":
            return max(5, lum * 60 // 85)
        return lum

    # ------------------------------------------------------------------ dessin
    def dessiner(self, etat, maintenant):
        self.lum = etat.get("lum", 85)
        mode = self._choisir_mode(etat, maintenant)
        if mode != self.mode:
            self._changer_mode(self.mode, mode, etat, maintenant)
        if mode == "eteint":
            # écran noir, dessiné une seule fois (le rétroéclairage est à 0)
            if not self.noir_affiche:
                self.fb.fill(0)
                self.ecran.afficher()
                self.noir_affiche = True
            return
        self.noir_affiche = False
        t = maintenant / 1000
        if mode == "jeu":
            fond, carte = "jeu", CARTE_JEU
        elif mode in ("absent", "verrou", "arret"):
            fond, carte = "nuit", CARTE_NUIT
        elif mode == "video":
            fond, carte = "cine", CARTE_CINE
        elif mode == "calme":
            fond, carte = "calme", CARTE_CALME
        elif mode == "master":
            fond, carte = "labo", CARTE_LABO
        else:
            fond, carte = "jour", CARTE_JOUR
        self.ecran.tampon[:] = self.fonds[fond]
        self._particules(t, mode)
        if mode == "jeu":
            self._scene_jeu(etat, carte, maintenant)
        elif mode == "normal":
            self._scene_normale(etat, carte, maintenant)
        elif mode == "arret":
            self._scene_arret(etat, carte, maintenant)
        elif mode == "video":
            self._scene_video(etat, carte, maintenant)
        elif mode == "calme":
            self._scene_calme(etat, carte, maintenant)
        elif mode == "master":
            self._scene_master(etat, carte, maintenant)
        else:
            self._scene_nuit(etat, carte, mode)
        self._mascotte(etat, mode, t, maintenant)
        self._bandeau(maintenant)
        self.ecran.afficher()

    def _choisir_mode(self, etat, maintenant):
        base = self._choisir_base(etat)
        if base != self.base:
            self.base = base
            self.base_depuis = maintenant
        if base in ("normal", "calme") and self._master_visible(etat, base, maintenant):
            return "master"
        if base != "normal" or not (etat.get("master") or {}).get("a"):
            self.travail_depuis = None
        return base

    def _master_visible(self, etat, base, maintenant):
        """Vrai si la scène master doit remplacer la scène normale ou calme maintenant."""
        m = etat.get("master")
        if not m:
            return False
        if self.master_fin is not None:
            if time.ticks_diff(self.master_fin, maintenant) > 0:
                return True
            self.master_fin = None
        lt = time.localtime()
        if base == "normal" and lt[0] >= 2025 and lt[3] >= 6:
            jour = "%04d-%02d-%02d" % lt[:3]
            if jour != self.briefing_jour:  # briefing : premier usage du jour
                self.briefing_jour = jour
                try:
                    with open(FICHIER_BRIEFING, "w") as f:
                        f.write(jour)
                except OSError:
                    pass
                self.master_fin = time.ticks_add(maintenant, BRIEFING_MS)
                return True
        if base == "normal" and m.get("a"):
            if self.travail_depuis is None:
                self.travail_depuis = maintenant
            return time.ticks_diff(maintenant, self.travail_depuis) % TRAVAIL_CYCLE_MS < TRAVAIL_MONTRE_MS
        if base == "calme":
            age = time.ticks_diff(maintenant, self.base_depuis)
            return (age // SUGGESTION_MS) % 3 == 2 and age % SUGGESTION_MS < INFO_MS
        return False

    def info_master(self, icone, texte):
        """Événement du master (MASTER_INFO) : bandeau 3 s puis scène master 15 s
        (jamais par-dessus un jeu, une vidéo, ni quand le PC dort)."""
        if self.base not in ("normal", "calme"):
            return
        maintenant = time.ticks_ms()
        self.reagir(icone, texte, duree=3000)
        self.master_fin = time.ticks_add(maintenant, INFO_MS)
        if icone == "graphe":
            self.surpris_jusqua = time.ticks_add(maintenant, 1500)

    def _choisir_base(self, etat):
        if etat.get("eteint"):
            return "eteint"
        if etat.get("arret_fin") is not None:
            return "arret"
        if not etat["connecte"]:
            return "absent"
        if etat["evt"]["verrou"]:
            return "verrou"
        if etat["evt"]["jeu"]:
            return "jeu"
        if etat["evt"].get("video"):
            return "video"
        if etat["evt"].get("inactif", 0) > 0:
            return "calme"
        return "normal"

    def _changer_mode(self, ancien, nouveau, etat, maintenant):
        duree_ancien = self._age(self.mode_depuis, maintenant)
        self.mode = nouveau
        self.mode_depuis = maintenant
        # Phase 11-ter : le PC écrit cette ligne dans agent.log (« [esp32] MODE … »)
        print("MODE %s <- %s (%d s)" % (nouveau, ancien, duree_ancien // 1000))
        if nouveau == "jeu":
            nom = etat["evt"]["jeu"]
            # nouvelle session si autre jeu, ou si on revient après plus de 10 min
            if nom != self.jeu_nom or ancien in ("absent", "eteint") or \
                    self._age(self.hist_seconde, maintenant) > 600000:
                self.jeu_nom = nom
                self.jeu_debut = maintenant
                self.pause_suivante = time.ticks_add(maintenant, PAUSE_JEU_MS)
                self.hist_fps = []
        elif ancien == "jeu":
            self.dernier_jeu = self.jeu_nom
        if nouveau == "eteint":
            self.bandeau = None  # rien ne reste affiché
        elif ancien == "eteint":
            self.reagir("coucou", "Hello Mihaja!")  # le PC vient de démarrer
        elif nouveau == "arret":
            self.reagir("power", "PC shutdown")
        elif ancien == "arret":
            pass  # arrêt annulé : le bandeau « Arrêt annulé » vient de main.py
        elif ancien is None:
            self.reagir("coucou", "Hello!")
        elif nouveau == "absent":
            # pas de bandeau si on était verrouillé (on dort déjà) ou réveillé quelques secondes
            if ancien != "verrou" and duree_ancien > 20000:
                self.reagir("power", "See you!")
        elif ancien == "absent":
            if duree_ancien > 60000:  # seulement après une vraie absence (pas un réveil bref)
                self.reagir("coucou", "Hello Mihaja!")
        elif nouveau == "jeu":
            self.reagir("manette", "Gaming")
        elif nouveau == "verrou":
            self.reagir("cadenas", "PC locked")
        elif ancien == "verrou":
            self.reagir("coucou", "Hi again!")
        elif nouveau == "video":
            self.reagir("popcorn", "Enjoy the show!")
        elif nouveau == "calme":
            if ancien != "master":
                self.bulle = None  # la scène calme arrive sans bruit
        elif nouveau == "master":
            self._rappel_master()
        elif ancien == "master" or (ancien == "calme" and nouveau == "master"):
            pass
        elif ancien == "calme" and duree_ancien > 10 * 60000:
            self.reagir("coucou", "You're back!", bandeau=False)

    def _particules(self, t, mode):
        fb = self.fb
        if mode == "jeu":
            couleurs = (rgb565(255, 60, 210), rgb565(0, 220, 255))
        elif mode == "normal":
            couleurs = (rgb565(255, 240, 220), rgb565(255, 200, 150))
        elif mode == "video":
            couleurs = (rgb565(255, 220, 160), rgb565(170, 120, 90))  # poussière dans le faisceau
        elif mode == "calme":
            couleurs = (rgb565(255, 240, 150), rgb565(150, 170, 255))  # lucioles
        elif mode == "master":
            couleurs = (rgb565(0, 200, 230), rgb565(0, 110, 140))  # points « hologramme »
        else:
            couleurs = (rgb565(170, 190, 255), rgb565(120, 140, 220))
        lent = 0.35 if mode in ("video", "calme", "master") else 1.0
        for i, p in enumerate(self.particules):
            if mode in ("video", "calme", "master") and i % 2:
                continue  # moitié moins de particules : ambiance tranquille
            p[1] -= p[2] * lent
            if p[1] < 0:
                p[1] = H
                p[0] = random.randint(196, W - 1)
            x = int(p[0] + math.sin(t * 2 * lent + p[3]) * 2)
            if x < 200 and p[1] < 168:
                continue  # pas de particules sur la carte de gauche
            taille = 2 if p[2] > 0.7 else 1
            if math.sin(t * 4 * lent + p[3]) > -0.3:
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

    def _meteo_visible(self, etat):
        lt = time.localtime()
        return bool(etat.get("meteo")) and lt[0] >= 2025 and lt[4] % METEO_TOUTES < METEO_PENDANT

    def _scene_normale(self, etat, carte, maintenant):
        fb = self.fb
        secondes = self._heure_date(carte)
        fb.fill_rect(18, 76, 158, 3, rgb565(45, 40, 80))
        fb.fill_rect(18, 76, 158 * secondes // 59, 3, rgb565(*CYAN))
        if self._meteo_visible(etat):
            self._meteo_compacte(etat, carte)
            return
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

    def _meteo_compacte(self, etat, carte):
        """Météo d'aujourd'hui et de demain sous l'heure (scène normale, 2 min toutes les 10 min)."""
        fb = self.fb
        for i, j in enumerate(etat["meteo"][:2]):
            y = 86 + i * 40
            fb.blit(self.icones_meteo.get(j["icone"], self.icones_meteo["nuage"]), 14, y + 3, CLE)
            jour = "Today" if i == 0 else "Tomorrow"
            x = self.f_s.ecrire(fb, jour, 46, y, GRIS, carte) + 6
            self.f_s.ecrire(fb, "%d° / %d°" % (j["tmax"], j["tmin"]), x, y, BLANC, carte)
            if j["pluie"] >= 20 and j["heure_pluie"] is not None:
                texte = "Rain %d %% at %d:00" % (j["pluie"], j["heure_pluie"])
                couleur = CYAN
            else:
                texte, couleur = "No rain expected", VERT
            self.f_xs.ecrire(fb, texte, 46, y + 17, couleur, carte)

    def _barre_temp(self, y, nom, valeur, carte):
        fb = self.fb
        self.f_s.ecrire(fb, nom, 16, y - 2, GRIS, carte)
        fb.fill_rect(52, y + 3, 96, 6, rgb565(40, 30, 70))
        if valeur is None or valeur < 0:
            return
        couleur = VERT if valeur < 65 else (ORANGE if valeur < 82 else ROUGE)
        fb.fill_rect(52, y + 3, min(96, valeur * 96 // 100), 6, rgb565(*couleur))
        self.f_m.ecrire(fb, "%d°" % valeur, 154, y - 4, couleur, carte)

    def _suivre_jeu(self, etat, maintenant):
        """Une fois par seconde : historique des FPS, rappel de pause, alerte de chauffe."""
        if self._age(self.hist_seconde, maintenant) < 1000:
            return
        self.hist_seconde = maintenant
        fps = etat["perf"]["fps"]
        if fps >= 0:
            self.hist_fps.append(fps)
            if len(self.hist_fps) > 60:
                self.hist_fps.pop(0)
        if time.ticks_diff(maintenant, self.pause_suivante) >= 0:
            self.pause_suivante = time.ticks_add(maintenant, PAUSE_JEU_MS)
            heures = self._age(self.jeu_debut, maintenant) // 3600000
            self.reagir("chrono", "%dh of play: take a break?" % heures, duree=6000)
        tg, tc = etat["gpu"]["temp"], etat["perf"]["cpu_temp"]
        self.chaud = tg >= CHAUFFE_GPU or tc >= CHAUFFE_CPU
        if self.chaud and time.ticks_diff(maintenant, self.chauffe_suivante) >= 0:
            self.chauffe_suivante = time.ticks_add(maintenant, CHAUFFE_RAPPEL_MS)
            if tg >= CHAUFFE_GPU:
                self.reagir("thermo", "GPU hot: %d°" % tg, duree=5000)
            else:
                self.reagir("thermo", "CPU hot: %d°" % tc, duree=5000)

    def _courbe_fps(self, x0, y0, w, h):
        """Petite courbe des FPS de la dernière minute (vert ≥ 60, orange ≥ 30, rouge)."""
        fb = self.fb
        fb.fill_rect(x0, y0 + h, w, 1, rgb565(45, 30, 80))
        serie = self.hist_fps
        if len(serie) < 2:
            return
        haut = max(60, max(serie))
        pas = w / 59
        x_debut = x0 + w - (len(serie) - 1) * pas
        avant = None
        for i, v in enumerate(serie):
            x = int(x_debut + i * pas)
            y = y0 + h - int(min(v, haut) * h / haut)
            if avant is not None:
                c = VERT if v >= 60 else (ORANGE if v >= 30 else ROUGE)
                fb.line(avant[0], avant[1], x, y, rgb565(*c))
            avant = (x, y)
        # le point le plus bas de la minute, en rouge
        bas = min(serie)
        i = serie.index(bas)
        fb.fill_rect(int(x_debut + i * pas) - 1, y0 + h - int(min(bas, haut) * h / haut) - 1, 3, 3,
                     rgb565(*ROUGE))

    def _scene_jeu(self, etat, carte, maintenant):
        fb = self.fb
        self._suivre_jeu(etat, maintenant)
        # nom du jeu + chrono de la session
        session = self._age(self.jeu_debut, maintenant) // 60000
        chrono = duree_texte(session) if session >= 1 else ""
        largeur_chrono = self.f_xs.largeur(chrono) + 16 if chrono else 0
        nom = self.f_s.couper(etat["evt"]["jeu"], 172 - largeur_chrono)
        self.f_s.ecrire(fb, nom, 14, 10, CYAN, carte)
        if chrono:
            self.f_xs.ecrire(fb, chrono, 186 - self.f_xs.largeur(chrono), 12, GRIS, carte)
        # FPS en grand (l'essentiel)
        fps = self._lisse("fps", etat["perf"]["fps"])
        if fps >= 0:
            couleur = VERT if fps >= 60 else (ORANGE if fps >= 30 else ROUGE)
            x = self.f_fps.ecrire(fb, "%d" % fps, 12, 24, couleur, carte)
        else:
            x = self.f_fps.ecrire(fb, "--", 12, 24, (70, 60, 110), carte)
        self.f_m.ecrire(fb, "FPS", x + 6, 64, MAGENTA, carte)
        self._courbe_fps(16, 84, 160, 11)
        self._barre_temp(102, "CPU", self._lisse("tcpu", etat["perf"]["cpu_temp"]), carte)
        self._barre_temp(124, "GPU", self._lisse("tgpu", etat["gpu"]["temp"]), carte)
        # ligne du bas : change toutes les 5 s (charge / minimum et moyenne / temps total)
        textes = []
        morceaux = []
        if etat["gpu"]["charge"] >= 0:
            morceaux.append("GPU %d %%" % etat["gpu"]["charge"])
        if etat["stat"]["ram"] >= 0:
            morceaux.append("RAM %d %%" % etat["stat"]["ram"])
        if morceaux:
            textes.append("   •   ".join(morceaux))
        if len(self.hist_fps) >= 10:
            moyenne = sum(self.hist_fps) // len(self.hist_fps)
            textes.append("1 min: min %d  •  avg %d FPS" % (min(self.hist_fps), moyenne))
        total = etat["perf"].get("total", -1)
        if total >= 1:
            textes.append("Game total: %s" % duree_texte(total))
        if textes:
            texte = textes[(time.ticks_ms() // 5000) % len(textes)]
            self.f_xs.ecrire(fb, self.f_xs.couper(texte, 172), 16, 148, GRIS, carte)

    def _scene_arret(self, etat, carte, maintenant):
        """Compte à rebours avant l'arrêt du PC (annulable depuis l'app)."""
        fb = self.fb
        reste = time.ticks_diff(etat["arret_fin"], maintenant)
        total = max(1000, etat.get("arret_total", 60000))
        if reste > 0:
            self.f_s.ecrire(fb, "PC shutdown in", 16, 10, DOUX, carte)
            secondes = (reste + 999) // 1000
            x = self.f_fps.ecrire(fb, "%d" % secondes, 14, 30, ORANGE if secondes > 10 else ROUGE, carte)
            self.f_m.ecrire(fb, "s", x + 6, 74, DOUX, carte)
            fb.fill_rect(18, 112, 158, 4, rgb565(45, 40, 80))
            fb.fill_rect(18, 112, 158 * min(reste, total) // total, 4, rgb565(*ORANGE))
            self.f_xs.ecrire(fb, "You can still cancel", 16, 126, GRIS, carte)
            self.f_xs.ecrire(fb, "from the Dadou app.", 16, 142, GRIS, carte)
        else:
            self.f_m.ecrire(fb, "Goodbye!", 16, 52, BLANC, carte)
            self.f_xs.ecrire(fb, "PC turning off…", 16, 82, DOUX, carte)
            self.f_xs.ecrire(fb, "See you Mihaja", 16, 100, GRIS, carte)

    def _scene_video(self, etat, carte, maintenant):
        """Salle de cinéma : la source (YouTube, Netflix…), le titre, l'heure et le volume."""
        fb = self.fb
        source = etat["evt"]["video"]
        couleur = COULEURS_SOURCES.get(source, OR)
        # petit triangle « lecture » + nom de la source
        for i in range(9):
            fb.fill_rect(16, 12 + i, 1 + 2 * min(i, 8 - i), 1, rgb565(*couleur))
        self.f_s.ecrire(fb, source, 30, 9, couleur, carte)
        titre = etat["evt"].get("video_titre", "")
        lignes = self._lignes(self.f_m, titre, 166, 3) if titre else []
        if not lignes:
            lignes = ["Enjoy the show!"]
        pos = etat["evt"].get("video_pos")
        avancement = bool(pos) and pos[1] > 0
        if avancement:
            # 2 lignes de titre au plus (avec « … ») : place pour la barre d'avancement
            lignes = self._lignes(self.f_m, titre, 166, 2) if titre else lignes[:2]
        for i, l in enumerate(lignes):
            self.f_m.ecrire(fb, l, 16, 34 + i * 20, BLANC, carte)
        if avancement:
            self._avancement(pos, couleur, carte, maintenant)
        else:
            fb.fill_rect(16, 112, 162, 1, rgb565(70, 30, 40))
        # bas de la carte : heure + volume
        lt = time.localtime()
        if lt[0] >= 2025:
            self.f_m.ecrire(fb, "%02d:%02d" % (lt[3], lt[4]), 16, 122, DOUX, carte)
        vol = self._lisse("vol", etat["stat"]["vol"])
        if vol >= 0:
            self.f_xs.ecrire(fb, "VOL", 86, 126, GRIS, carte)
            fb.fill_rect(110, 130, 66, 4, rgb565(60, 30, 40))
            fb.fill_rect(110, 130, 66 * min(100, vol) // 100, 4, rgb565(*couleur))
        if etat["evt"]["casque"]:
            fb.blit(self.ico_casque, 16, 148, CLE)
            self.f_xs.ecrire(fb, self.f_xs.couper(etat["evt"]["casque"], 146), 30, 148, GRIS, carte)

    def _temps_video(self, s):
        """152 -> « 02:32 » ; 3752 -> « 1:02:32 »."""
        if s >= 3600:
            return "%d:%02d:%02d" % (s // 3600, s // 60 % 60, s % 60)
        return "%02d:%02d" % (s // 60, s % 60)

    def _avancement(self, pos, couleur, carte, maintenant):
        fb = self.fb
        p, duree, lecture, recu = pos
        if lecture:
            p += time.ticks_diff(maintenant, recu) // 1000
        p = max(0, min(p, duree))
        self.f_xs.ecrire(fb, self._temps_video(p), 16, 88, BLANC, carte)
        fin = self._temps_video(duree)
        self.f_xs.ecrire(fb, fin, 178 - self.f_xs.largeur(fin), 88, GRIS, carte)
        if not lecture:
            self.f_xs.ecrire_centre(fb, "Pause", 97, 88, ORANGE, carte)
        fb.fill_rect(16, 106, 162, 4, rgb565(60, 30, 40))
        x = 16 + 162 * p // duree
        fb.fill_rect(16, 106, x - 16, 4, rgb565(*(couleur if lecture else ORANGE)))
        fb.fill_rect(x - 2, 103, 4, 10, rgb565(*BLANC))  # curseur

    def _suggestions(self, etat):
        """Petites idées douces quand le PC est allumé sans que personne s'en serve."""
        lt = time.localtime()
        heure = lt[3] if lt[0] >= 2025 else 12
        liste = [("eau", "Time for some water?"),
                 ("livre", "How is your research going?"),
                 ("etirer", "Stand up and stretch a bit"),
                 ("livre", "One page of your thesis today?")]
        jours = etat.get("meteo") or []
        actuel = etat.get("meteo_now")
        if actuel and actuel["pluie"]:  # il pleut maintenant (météo actuelle, pas celle de la journée)
            liste.insert(0, ("fenetre", "It's raining: windows closed?"))
        elif jours:
            j = jours[0]
            if j["pluie"] >= 40 and j["heure_pluie"] is not None and j["heure_pluie"] > heure:
                liste.insert(0, ("fenetre", "Rain around %d: close the windows" % j["heure_pluie"]))
        if self.dernier_jeu and 8 <= heure < 23:
            liste.append(("manette", "Back to %s?" % self.dernier_jeu))
        if heure >= 23 or heure < 5:
            liste.insert(0, ("lit", "It's late: bed soon?"))
        minutes = etat["evt"].get("inactif", 0)
        if minutes >= 30:
            liste.append(("power", "PC idle for %s: shut it down?" % duree_texte(minutes)))
        return liste

    def _scene_calme(self, etat, carte, maintenant):
        fb = self.fb
        self._heure_date(carte)
        liste = self._suggestions(etat)
        icone, texte = liste[(self._age(self.base_depuis, maintenant) // SUGGESTION_MS) % len(liste)]
        self.bulle_calme = icone
        # la suggestion, dans un petit encadré
        fb.rect(14, 82, 166, 56, rgb565(60, 70, 120))
        fb.ellipse(32, 110, 13, 13, rgb565(*BLANC), True)
        ico = self.icones.get(icone)
        if ico:
            fb.blit(ico, 23, 101, CLE)
        lignes = self._lignes(self.f_s, texte, 126, 3)
        y = 110 - len(lignes) * 8
        for l in lignes:
            self.f_s.ecrire(fb, l, 52, y, BLANC, carte)
            y += 16
        minutes = etat["evt"].get("inactif", 0)
        self.f_xs.ecrire(fb, "No activity for %s" % duree_texte(max(1, minutes)), 16, 148, GRIS, carte)

    def _scene_nuit(self, etat, carte, mode):
        fb = self.fb
        self._heure_date(carte, y_heure=4)
        titre = "PC locked" if mode == "verrou" else "PC asleep"
        self.f_xs.ecrire(fb, titre, 120, 58, GRIS, carte)
        jours = etat.get("meteo") or []
        if not jours:
            self.f_m.ecrire(fb, "I'm waiting…", 16, 92, DOUX, carte)
            self.f_xs.ecrire(fb, "Weather: waiting for PC…", 16, 118, GRIS, carte)
            return
        for i, j in enumerate(jours[:2]):
            y = 76 + i * 45
            fb.blit(self.icones_meteo.get(j["icone"], self.icones_meteo["nuage"]), 14, y + 4, CLE)
            self.f_xs.ecrire(fb, "Today" if i == 0 else "Tomorrow", 46, y, GRIS, carte)
            self.f_m.ecrire(fb, "%d° / %d°" % (j["tmax"], j["tmin"]), 46, y + 11, BLANC, carte)
            if j["pluie"] >= 20 and j["heure_pluie"] is not None:
                texte = "Rain %d %% at %d:00" % (j["pluie"], j["heure_pluie"])
                couleur = CYAN
            else:
                texte, couleur = "No rain expected", VERT
            self.f_xs.ecrire(fb, texte, 46, y + 30, couleur, carte)

    # ------------------------------------------------------------------ mascotte
    def _mascotte(self, etat, mode, t, maintenant):
        fb = self.fb
        casque = "oreilles" if (etat["evt"]["casque"] or mode == "jeu") else "cou"
        if mode == "master":
            casque = "ar"  # veste de labo + lunettes AR
        dort = mode in ("absent", "verrou")
        calme = mode == "calme"
        age_reaction = self._age(self.reaction, maintenant)
        if time.ticks_diff(maintenant, self.prochain_clin) >= 0:
            if calme:  # clignements plus lents, paupières lourdes
                self.prochain_clin = time.ticks_add(maintenant, random.randint(4000, 8000))
            else:
                self.prochain_clin = time.ticks_add(maintenant, random.randint(2500, 5500))
        clin = time.ticks_diff(maintenant, self.prochain_clin) > (-400 if calme else -160)
        # au cinéma, la mascotte rit de temps en temps (≈ 2 s toutes les 25 s)
        rit = mode == "video" and (maintenant // 1000) % 25 < 2
        m = etat.get("master") or {}
        tard = mode == "master" and self._tard()
        if dort or tard:
            visage = "cligne"
        elif mode == "master" and self.surpris_jusqua is not None and \
                time.ticks_diff(self.surpris_jusqua, maintenant) > 0:
            visage = "surpris"
        elif mode == "master" and m.get("o") and m["o"][1]:
            visage = "neutre" if clin and age_reaction >= DUREE_REACTION else "content"
        elif age_reaction < DUREE_REACTION or rit:
            visage = "content"
        elif clin:
            visage = "cligne"
        else:
            visage = "neutre"
        souffle = 0.8 if dort else (1.1 if calme or mode == "video" else 2.2)
        dy = int(round(2 * math.sin(t * souffle)))
        if age_reaction < 500:
            dy -= int(7 * math.sin(math.pi * age_reaction / 500))
        fb.blit(self.persos[(casque, visage)], PERSO_X, PERSO_Y + dy, CLE)
        if mode == "video":
            fb.blit(self.popcorn, PERSO_X + 8, PERSO_Y + 112 + dy, CLE)
        if mode == "jeu" and self.chaud:
            ph = (t * 0.7) % 1
            fb.blit(self.goutte, PERSO_X + 72, PERSO_Y + 30 + int(ph * 10) + dy, CLE)
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
        bulle = self.bulle if age_reaction < DUREE_REACTION else None
        if mode == "arret":
            bulle = "coucou"  # la mascotte fait coucou pendant tout le compte à rebours
        if calme and bulle is None and self._age(self.base_depuis, maintenant) % BULLE_CALME_MS < 3000:
            bulle = self.bulle_calme  # rappelle doucement la suggestion
        if bulle and not dort and not pensee:
            cx, cy = PERSO_X - 2, PERSO_Y + 24
            fb.ellipse(cx, cy, 15, 15, rgb565(*CYAN), True)
            fb.ellipse(cx, cy, 13, 13, rgb565(*BLANC), True)
            ico = self.icones.get(bulle)
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

    # ------------------------------------------------------------------ scène master (Phase 11)
    def _tard(self):
        lt = time.localtime()
        return lt[0] >= 2025 and (lt[3] >= 23 or lt[3] < 5)

    def _rappel_master(self):
        if self.bandeau is not None:
            return  # un événement a déjà son bandeau
        lt = time.localtime()
        if self._tard():
            if self.tard_jour != lt[2]:
                self.tard_jour = lt[2]
                self.reagir("lit", "Late: see you tomorrow?", duree=3000)
            return
        icone, texte = RAPPELS_MASTER[self.rappel % len(RAPPELS_MASTER)]
        self.rappel += 1
        self.reagir(icone, texte, duree=3000)

    def _barre_master(self, y, nom, texte, valeur, but, couleur, carte):
        fb = self.fb
        self.f_xs.ecrire(fb, nom, 16, y, GRIS_AR, carte)
        self.f_xs.ecrire(fb, texte, 180 - self.f_xs.largeur(texte), y, TEXTE_AR, carte)
        fb.fill_rect(16, y + 14, 162, 4, rgb565(40, 50, 78))
        if but > 0 and valeur > 0:
            fb.fill_rect(16, y + 14, 162 * min(valeur, but) // but, 4, rgb565(*couleur))

    def _scene_master(self, etat, carte, maintenant):
        fb = self.fb
        m = etat.get("master") or {}
        # 1. prochaine échéance : J-x en grand + titre
        e = m.get("e")
        if e:
            jours, titre = e[0], e[1]
            couleur = ROUGE if jours <= 3 else (ORANGE if jours <= 7 else CYAN_AR)
            if jours == 0:
                x = self.f_m.ecrire(fb, "Today", 14, 16, couleur, carte) + 8
            else:
                x = self.f_m.ecrire(fb, "D-", 14, 24, couleur, carte)
                x = self.f_heure.ecrire(fb, "%d" % jours, x + 1, 2, couleur, carte) + 8
            lignes = self._lignes(self.f_s, titre, 180 - x, 2)
            y = 26 - len(lignes) * 8
            for l in lignes:
                self.f_s.ecrire(fb, l, x, y, TEXTE_AR, carte)
                y += 16
        else:
            self.f_m.ecrire(fb, "No deadline", 14, 12, GRIS_AR, carte)
            self.f_xs.ecrire(fb, "Add one in the Dadou app", 14, 32, GRIS_AR, carte)
        # 2. objectif du jour
        o = m.get("o")
        if o:
            fait = o[1]
            fb.rect(14, 53, 11, 11, rgb565(*(VERT if fait else CYAN_AR)))
            if fait:  # petite coche
                fb.line(16, 58, 19, 61, rgb565(*VERT))
                fb.line(19, 61, 24, 54, rgb565(*VERT))
            self.f_m.ecrire(fb, self.f_m.couper(o[0], 150), 30, 49, VERT if fait else TEXTE_AR, carte)
        else:
            self.f_s.ecrire(fb, "Daily goal: set it in the app", 14, 51, GRIS_AR, carte)
        fb.fill_rect(14, 69, 166, 1, rgb565(40, 50, 78))
        # 3. lecture et rédaction
        l = m.get("l")
        if l:
            texte = "%d/%d" % (l[0], l[1]) if l[1] else "%d read" % l[0]
            self._barre_master(73, "Reading", texte, l[0], l[1], VIOLET, carte)
        else:
            self.f_xs.ecrire(fb, "Reading: pick the folders", 16, 76, GRIS_AR, carte)
        r = m.get("r")
        if r:
            texte = "%d/%d" % (r[0], r[1]) if r[1] else "%d" % r[0]
            self._barre_master(93, "Words", texte, r[0], r[1], VERT, carte)
        else:
            self.f_xs.ecrire(fb, "Writing: pick your thesis", 16, 96, GRIS_AR, carte)
        fb.fill_rect(14, 115, 166, 1, rgb565(40, 50, 78))
        # 4. dernier résultat de mesure, sinon prochaine réunion, sinon temps du jour
        x = m.get("x")
        reu = m.get("m")
        t = m.get("t", 0)
        if x:
            self.f_s.ecrire(fb, "Lat. %d ms  •  p95 %d" % (x[0], x[1]), 14, 119, TEXTE_AR, carte)
            self._courbe_master(m.get("c") or [], 16, 137, 84, 12)
            details = ("%s %s Hz" % (x[3], x[4])).strip() if (x[3] or x[4]) else ""
            self.f_xs.ecrire(fb, self.f_xs.couper(details, 74), 106, 135, GRIS_AR, carte)
            self.f_xs.ecrire(fb, "%d run%s" % (x[2], "s" if x[2] > 1 else ""), 106, 148, GRIS_AR, carte)
        elif reu:
            self.f_s.ecrire(fb, "Meeting: %s" % reu[0], 14, 119, CYAN_AR, carte)
            for i, ligne in enumerate(self._lignes(self.f_xs, reu[1], 166, 2)):
                self.f_xs.ecrire(fb, ligne, 14, 136 + i * 12, TEXTE_AR, carte)
        else:
            self.f_s.ecrire(fb, "Master: %s today" % (duree_texte(t) if t else "0 min"),
                            14, 119, CYAN_AR, carte)
            self.f_xs.ecrire(fb, "Phase: %s" % m.get("p", ""), 14, 140, GRIS_AR, carte)

    def _courbe_master(self, serie, x0, y0, w, h):
        """Médianes de latence des 10 dernières sessions (plus bas = mieux)."""
        fb = self.fb
        fb.fill_rect(x0, y0 + h, w, 1, rgb565(40, 50, 78))
        if len(serie) < 2:
            return
        haut, bas = max(serie), min(serie)
        ecart = max(1, haut - bas)
        pas = w / (len(serie) - 1)
        avant = None
        for i, v in enumerate(serie):
            pt = (int(x0 + i * pas), y0 + int((v - bas) * h / ecart))
            if avant:
                fb.line(avant[0], avant[1], pt[0], pt[1], rgb565(*CYAN_AR))
            avant = pt
        fb.fill_rect(avant[0] - 1, avant[1] - 1, 3, 3, rgb565(*VERT))
