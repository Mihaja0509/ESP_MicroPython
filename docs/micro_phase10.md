# Micro — Phase 10 : scènes cinéma et calme, météo régulière, mode jeu enrichi

Date : 2026-11-03 · Statut : à appliquer · Base : commit 405d343 (« Phase 9 : jeux hors Steam et ajout du widget »). Les blocs « avant » sont copiés du dépôt GitHub à ce commit.
Fichier joint : `docs/micro_phase10_fichiers.zip` (14 fichiers, SHA-256 du zip `5545e2c1…`).

## Ce que contient la phase

1. **Météo dans la scène normale** : toutes les 10 min (hh:00, hh:10, hh:20…), la météo d'aujourd'hui et de demain remplace pendant 2 min les anneaux CPU / RAM / volume, sous l'heure. Ensuite, retour automatique à la scène normale.
2. **Scène cinéma (vidéo)** : quand la fenêtre au premier plan montre une vidéo qui fait du son, l'ESP32 passe dans une salle de cinéma : rideaux rouges, faisceau du projecteur, fauteuils, et la mascotte avec un pot de pop-corn, qui rit de temps en temps. Sites et lecteurs reconnus : YouTube, Anime-Sama, Netflix (site ou app), Crunchyroll, Prime Video, Disney+, Twitch (sites) et VLC, MPC, PotPlayer, Films et TV (lecteurs). La carte affiche la source (dans sa couleur), le titre de la vidéo sur 3 lignes au plus, l'heure, le volume et le casque. L'écran baisse un peu (55 au lieu de 85). Une pause de quelques secondes ne fait pas sortir de la scène (8 s de tolérance). La page d'accueil de YouTube n'est pas une vidéo.
3. **Scène calme (PC allumé mais inutilisé)** : après 3 min sans clavier ni souris, sans jeu ni vidéo, l'écran passe dans un salon calme au crépuscule (fenêtre, lucioles, plante). Affichage : l'heure, une suggestion douce qui change toutes les 45 s, et « Pas d'activité depuis … ». La mascotte respire lentement et montre l'icône de la suggestion 3 s toutes les 15 s. Il n'y a ni bandeau ni clignotement. Suggestions :
   - « Une pause eau ? », « Lève-toi et étire-toi un peu » ;
   - « Où en es-tu dans tes recherches ? », « Une page de ton mémoire aujourd'hui ? » ;
   - s'il pleut : « Il pleut : les fenêtres sont fermées ? » ; si la pluie est prévue plus tard dans la journée : « Pluie vers 16 h : pense à fermer les fenêtres » ;
   - après un jeu : « Reprendre Red Dead Redemption 2 ? » (de 8 h à 23 h) ;
   - après 23 h : « Il se fait tard : au lit bientôt ? » ;
   - après 30 min : « Le PC t'attend depuis 45 min : l'éteindre ? ».
   Au moindre mouvement de souris, l'écran revient à la scène normale.
4. **Mode jeu enrichi, sans perdre l'essentiel** : le nom du jeu, les FPS en grand et les barres CPU / GPU restent à la même place. S'ajoutent :
   - le **chrono de la session** en haut à droite (« 1 h 12 ») ;
   - une **courbe des FPS de la dernière minute** sous le chiffre, avec le point le plus bas en rouge ;
   - une ligne du bas qui change toutes les 5 s : « GPU 97 % • RAM 54 % » → « 1 min : min 52 • moy. 97 FPS » → « Total sur ce jeu : 34 h 05 » ;
   - une **alerte de chauffe** : GPU ≥ 83 °C ou CPU ≥ 92 °C → bandeau « GPU chaud : 85° » (au plus toutes les 5 min) et une goutte de sueur sur la mascotte ;
   - un **rappel de pause** toutes les 2 h de jeu : « 2 h de jeu : petite pause ? ».
5. **Statistiques de jeu sur le PC** : `tools\agent\stats_jeux.json` (jamais dans Git) garde le temps par jeu, le nombre de sessions, les FPS moyens et le temps par jour (60 jours). Il est enregistré chaque minute et à la fin de chaque jeu. Il servira à l'onglet Statistiques de l'app (Phase 11).

Protocole série ajouté : `EVT VIDEO Source|Titre` (ou `EVT VIDEO -`), `EVT INACTIF n` (minutes, 0 = PC utilisé), `JEU_TOTAL n` (minutes sur le jeu en cours).
Priorité des scènes sur l'ESP32 : éteint > arrêt > absent > verrouillé > **jeu > vidéo > calme** > normale.

## Partie 1 — Nouveaux fichiers

Dans le zip `docs/micro_phase10_fichiers.zip`, à extraire à la racine de `Micro` (les chemins sont déjà dedans). Vérifier chaque empreinte : 16 premiers caractères du SHA-256.

| Fichier | Octets | SHA-256 (16 car.) |
|---|---|---|
| `esp/assets/fond_cine.bin` | 110080 | `247182201b6dd274` |
| `esp/assets/fond_calme.bin` | 110080 | `3ec470a1b05723fe` |
| `esp/assets/ico_popcorn.bin` | 648 | `1509217486728d03` |
| `esp/assets/ico_eau.bin` | 648 | `e93ecf3abee403e4` |
| `esp/assets/ico_fenetre.bin` | 648 | `134bcb9c5bb65c2b` |
| `esp/assets/ico_livre.bin` | 648 | `4f4257ae4a34b65d` |
| `esp/assets/ico_lit.bin` | 648 | `c69d057720f5dc0f` |
| `esp/assets/ico_thermo.bin` | 648 | `b4bb071349d5e28b` |
| `esp/assets/ico_chrono.bin` | 648 | `35a4cc92c9ff95ab` |
| `esp/assets/ico_etirer.bin` | 648 | `dd5710cfe0c2cb90` |
| `esp/assets/popcorn_main.bin` | 1248 | `ff4516a9fb1a69b2` |
| `esp/assets/goutte.bin` | 176 | `869faf15c78cc7a8` |
| `tools/assets/apercus/fond_cine.png` | 7322 | `0c82332654739ca5` |
| `tools/assets/apercus/fond_calme.png` | 6590 | `911a46e8bf123203` |

Ces images sont produites par le nouveau `tools/assets/generer_assets.py` (modifications 10 et 11, fonction `assets_phase10()`). **Ne pas relancer le générateur** : les fichiers du zip font foi.

## Partie 2 — Fichiers remplacés en entier

### `esp/lib/ui.py`

```python
# Interface animée de l'écran (Phase 4) : fonds, mascotte, polices, animations.
# Les images viennent de /assets (créées par tools/assets/generer_assets.py).
# Phase 10 : scène « cinéma » (vidéo), scène « calme » (PC allumé mais inutilisé),
# météo 2 min toutes les 10 min dans la scène normale, mode jeu enrichi (courbe des FPS,
# chrono de session, temps total du jeu, alerte de chauffe).
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

JOURS = ("Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim.")
MOIS = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.",
        "nov.", "déc.")

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
    """95 -> « 1 h 35 » ; 40 -> « 40 min »."""
    if minutes < 60:
        return "%d min" % minutes
    return "%d h %02d" % (minutes // 60, minutes % 60)


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
                      for n in ("jour", "nuit", "jeu", "cine", "calme")}
        self.persos = {}
        for casque in ("cou", "oreilles"):
            for nom in ("neutre", "cligne", "content", "surpris"):
                self.persos[(casque, nom)] = _charger("perso_%s_%s.bin" % (casque, nom), PERSO_W, PERSO_H)
        self.icones = {}
        for nom in ("son", "muet", "soleil", "cadenas", "clavier", "souris", "appli", "lune",
                    "power", "musique", "manette", "coucou",
                    "popcorn", "eau", "fenetre", "livre", "lit", "thermo", "chrono", "etirer"):
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
        mode = self._choisir_mode(etat)
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
        else:
            self._scene_nuit(etat, carte, mode)
        self._mascotte(etat, mode, t, maintenant)
        self._bandeau(maintenant)
        self.ecran.afficher()

    def _choisir_mode(self, etat):
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
            self.reagir("coucou", "Bonjour Mihaja !")  # le PC vient de démarrer
        elif nouveau == "arret":
            self.reagir("power", "Arrêt du PC")
        elif ancien == "arret":
            pass  # arrêt annulé : le bandeau « Arrêt annulé » vient de main.py
        elif ancien is None:
            self.reagir("coucou", "Bonjour !")
        elif nouveau == "absent":
            # pas de bandeau si on était verrouillé (on dort déjà) ou réveillé quelques secondes
            if ancien != "verrou" and duree_ancien > 20000:
                self.reagir("power", "À bientôt !")
        elif ancien == "absent":
            if duree_ancien > 60000:  # seulement après une vraie absence (pas un réveil bref)
                self.reagir("coucou", "Bonjour Mihaja !")
        elif nouveau == "jeu":
            self.reagir("manette", "Mode jeu")
        elif nouveau == "verrou":
            self.reagir("cadenas", "PC verrouillé")
        elif ancien == "verrou":
            self.reagir("coucou", "Re-bonjour !")
        elif nouveau == "video":
            self.reagir("popcorn", "Bon visionnage !")
        elif nouveau == "calme":
            self.bulle = None  # la scène calme arrive sans bruit
        elif ancien == "calme" and duree_ancien > 10 * 60000:
            self.reagir("coucou", "Te revoilà !", bandeau=False)

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
        else:
            couleurs = (rgb565(170, 190, 255), rgb565(120, 140, 220))
        lent = 0.35 if mode in ("video", "calme") else 1.0
        for i, p in enumerate(self.particules):
            if mode in ("video", "calme") and i % 2:
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
            jour = "Aujourd'hui" if i == 0 else "Demain"
            x = self.f_s.ecrire(fb, jour, 46, y, GRIS, carte) + 6
            self.f_s.ecrire(fb, "%d° / %d°" % (j["tmax"], j["tmin"]), x, y, BLANC, carte)
            if j["pluie"] >= 20 and j["heure_pluie"] is not None:
                texte = "Pluie %d %% vers %d h" % (j["pluie"], j["heure_pluie"])
                couleur = CYAN
            else:
                texte, couleur = "Pas de pluie prévue", VERT
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
            self.reagir("chrono", "%d h de jeu : petite pause ?" % heures, duree=6000)
        tg, tc = etat["gpu"]["temp"], etat["perf"]["cpu_temp"]
        self.chaud = tg >= CHAUFFE_GPU or tc >= CHAUFFE_CPU
        if self.chaud and time.ticks_diff(maintenant, self.chauffe_suivante) >= 0:
            self.chauffe_suivante = time.ticks_add(maintenant, CHAUFFE_RAPPEL_MS)
            if tg >= CHAUFFE_GPU:
                self.reagir("thermo", "GPU chaud : %d°" % tg, duree=5000)
            else:
                self.reagir("thermo", "CPU chaud : %d°" % tc, duree=5000)

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
            textes.append("1 min : min %d  •  moy. %d FPS" % (min(self.hist_fps), moyenne))
        total = etat["perf"].get("total", -1)
        if total >= 1:
            textes.append("Total sur ce jeu : %s" % duree_texte(total))
        if textes:
            texte = textes[(time.ticks_ms() // 5000) % len(textes)]
            self.f_xs.ecrire(fb, self.f_xs.couper(texte, 172), 16, 148, GRIS, carte)

    def _scene_arret(self, etat, carte, maintenant):
        """Compte à rebours avant l'arrêt du PC (annulable depuis l'app)."""
        fb = self.fb
        reste = time.ticks_diff(etat["arret_fin"], maintenant)
        total = max(1000, etat.get("arret_total", 60000))
        if reste > 0:
            self.f_s.ecrire(fb, "Arrêt du PC dans", 16, 10, DOUX, carte)
            secondes = (reste + 999) // 1000
            x = self.f_fps.ecrire(fb, "%d" % secondes, 14, 30, ORANGE if secondes > 10 else ROUGE, carte)
            self.f_m.ecrire(fb, "s", x + 6, 74, DOUX, carte)
            fb.fill_rect(18, 112, 158, 4, rgb565(45, 40, 80))
            fb.fill_rect(18, 112, 158 * min(reste, total) // total, 4, rgb565(*ORANGE))
            self.f_xs.ecrire(fb, "Tu peux encore annuler", 16, 126, GRIS, carte)
            self.f_xs.ecrire(fb, "depuis l'app Dadou.", 16, 142, GRIS, carte)
        else:
            self.f_m.ecrire(fb, "Au revoir !", 16, 52, BLANC, carte)
            self.f_xs.ecrire(fb, "Le PC s'éteint…", 16, 82, DOUX, carte)
            self.f_xs.ecrire(fb, "À bientôt Mihaja", 16, 100, GRIS, carte)

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
            lignes = ["Bon visionnage !"]
        for i, l in enumerate(lignes):
            self.f_m.ecrire(fb, l, 16, 34 + i * 20, BLANC, carte)
        # bas de la carte : heure + volume
        fb.fill_rect(16, 112, 162, 1, rgb565(70, 30, 40))
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

    def _suggestions(self, etat):
        """Petites idées douces quand le PC est allumé sans que personne s'en serve."""
        lt = time.localtime()
        heure = lt[3] if lt[0] >= 2025 else 12
        liste = [("eau", "Une pause eau ?"),
                 ("livre", "Où en es-tu dans tes recherches ?"),
                 ("etirer", "Lève-toi et étire-toi un peu"),
                 ("livre", "Une page de ton mémoire aujourd'hui ?")]
        jours = etat.get("meteo") or []
        if jours:
            j = jours[0]
            if j["icone"] in ("pluie", "orage"):
                liste.insert(0, ("fenetre", "Il pleut : les fenêtres sont fermées ?"))
            elif j["pluie"] >= 40 and j["heure_pluie"] is not None and j["heure_pluie"] >= heure:
                liste.insert(0, ("fenetre", "Pluie vers %d h : pense à fermer les fenêtres" % j["heure_pluie"]))
        if self.dernier_jeu and 8 <= heure < 23:
            liste.append(("manette", "Reprendre %s ?" % self.dernier_jeu))
        if heure >= 23 or heure < 5:
            liste.insert(0, ("lit", "Il se fait tard : au lit bientôt ?"))
        minutes = etat["evt"].get("inactif", 0)
        if minutes >= 30:
            liste.append(("power", "Le PC t'attend depuis %s : l'éteindre ?" % duree_texte(minutes)))
        return liste

    def _scene_calme(self, etat, carte, maintenant):
        fb = self.fb
        self._heure_date(carte)
        liste = self._suggestions(etat)
        icone, texte = liste[(self._age(self.mode_depuis, maintenant) // SUGGESTION_MS) % len(liste)]
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
        self.f_xs.ecrire(fb, "Pas d'activité depuis %s" % duree_texte(max(1, minutes)), 16, 148, GRIS, carte)

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
        if dort:
            visage = "cligne"
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
        if calme and bulle is None and self._age(self.mode_depuis, maintenant) % BULLE_CALME_MS < 3000:
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
```

## Partie 3 — Modifications « avant → après » (dans l'ordre)

### Modification 1 — `tools/agent/agent_pc.py`

En-tête du fichier : ce qui est nouveau.

**Avant :**

```python
  toucher l'aperçu = cliquer à cet endroit ; adresse /widget pour le widget Android.
```

**Après :**

```python
  toucher l'aperçu = cliquer à cet endroit ; adresse /widget pour le widget Android.
- Phase 9 : jeux lancés hors Steam (DetecteurJeu, tools\\agent\\jeux.json facultatif).
- Phase 10 : vidéo au premier plan (EVT VIDEO source|titre), PC inutilisé (EVT INACTIF minutes),
  temps de jeu par jeu et par jour (tools\\agent\\stats_jeux.json, ligne JEU_TOTAL minutes).
```

### Modification 2 — `tools/agent/agent_pc.py`

Détection des vidéos, du son, et statistiques de jeu, placées juste après DetecteurJeu.

**Avant :**

```python
        print(f"[agent] jeu détecté hors Steam : {self.nom} ({exe})")
        return self.nom


class LecteurLHM:
```

**Après :**

```python
        print(f"[agent] jeu détecté hors Steam : {self.nom} ({exe})")
        return self.nom


# --- Phase 10 : vidéo en cours (scène cinéma), PC inutilisé, statistiques de jeu ------------
INACTIF_APRES = 180      # s sans clavier ni souris (et sans jeu ni vidéo) = PC inutilisé
VIDEO_SON = 8            # s : la vidéo doit faire du son depuis moins de 8 s…
VIDEO_TOLERANCE = 8      # … et la scène cinéma reste 8 s après (pause courte, épisode suivant)
FICHIER_STATS = DOSSIER / "stats_jeux.json"   # temps de jeu (jamais dans Git)
NAVIGATEURS = {"chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "opera_gx.exe",
               "brave.exe", "vivaldi.exe"}
# mot cherché dans le titre de l'onglet -> nom affiché
SITES_VIDEO = (("youtube", "YouTube"), ("anime-sama", "Anime-Sama"), ("animesama", "Anime-Sama"),
               ("netflix", "Netflix"), ("crunchyroll", "Crunchyroll"), ("prime video", "Prime Video"),
               ("disney+", "Disney+"), ("twitch", "Twitch"))
LECTEURS_VIDEO = {"vlc.exe": "VLC", "mpc-hc.exe": "MPC", "mpc-hc64.exe": "MPC",
                  "mpc-be64.exe": "MPC", "potplayer64.exe": "PotPlayer",
                  "potplayermini64.exe": "PotPlayer", "netflix.exe": "Netflix",
                  "video.ui.exe": "Films et TV", "microsoft.media.player.exe": "Lecteur multimédia"}
_COMPTEUR_SON = {"m": None, "t": 0.0}


def son_en_cours():
    """Vrai si la sortie audio joue du son ; None si on ne peut pas le savoir (pycaw absent)."""
    if AudioUtilities is None:
        return None
    try:
        if _COMPTEUR_SON["m"] is None or time.time() - _COMPTEUR_SON["t"] > 30:
            # recréé toutes les 30 s : suit le changement de sortie (casque <-> haut-parleurs)
            from ctypes import POINTER, cast
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import IAudioMeterInformation
            dev = AudioUtilities.GetSpeakers()
            brut = getattr(dev, "_dev", dev)  # pycaw récent : objet AudioDevice
            itf = brut.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
            _COMPTEUR_SON["m"] = cast(itf, POINTER(IAudioMeterInformation))
            _COMPTEUR_SON["t"] = time.time()
        return _COMPTEUR_SON["m"].GetPeakValue() > 0.01
    except Exception:
        _COMPTEUR_SON["m"] = None
        return None


def video_premier_plan():
    """(source, titre) de la vidéo de la fenêtre au premier plan, ou ('', '')."""
    hwnd, pid = fenetre_premier_plan()
    if not hwnd or not pid:
        return "", ""
    try:
        exe = psutil.Process(pid).name().lower()
    except psutil.Error:
        return "", ""
    titre = titre_fenetre(hwnd)
    if exe in LECTEURS_VIDEO:
        # « film.mkv - Lecteur multimédia VLC » -> « film »
        t = re.sub(r"\s+-\s+(Lecteur multimédia VLC|VLC media player)$", "", titre, flags=re.I)
        t = re.sub(r"\.(mkv|mp4|avi|mov|webm|m4v|wmv)$", "", t, flags=re.I)
        if t.lower() in ("lecteur multimédia vlc", "vlc media player", "netflix"):
            t = ""
        t = re.sub(r"[._]+", " ", t).strip()  # « Dune.Part.Two » -> « Dune Part Two »
        return LECTEURS_VIDEO[exe], t
    if exe in ("applicationframehost.exe", "wwahost.exe") and "netflix" in titre.lower():
        return "Netflix", ""
    if exe in NAVIGATEURS:
        bas = titre.lower()
        for cle, nom in SITES_VIDEO:
            if cle not in bas:
                continue
            # « (3) Titre - YouTube - Google Chrome » -> « Titre »
            avant = []
            for p in re.split(r"\s+[-–—|]\s+", titre):
                if cle in p.lower():
                    break
                avant.append(p.strip())
            t = re.sub(r"^\(\d+\)\s*", "", " - ".join(avant)).strip()
            if nom == "YouTube" and not t:
                return "", ""  # page d'accueil de YouTube : pas une vidéo
            return nom, t
    return "", ""


class DetecteurVideo:
    """Vidéo en cours = fenêtre vidéo au premier plan (YouTube, Netflix, VLC…) qui fait du son."""

    def __init__(self):
        self.son_vu = 0.0
        self.actuelle = ""
        self.perdue = 0.0

    def video(self):
        """« Source|Titre » (texte pour l'ESP32) ou '' si aucune vidéo."""
        maintenant = time.time()
        source, titre = video_premier_plan()
        son = son_en_cours()
        if son or son is None:
            self.son_vu = maintenant
        if source and maintenant - self.son_vu < VIDEO_SON:
            texte = texte_ascii(source)
            if titre:
                texte += "|" + texte_ascii(titre).replace("|", "/")[:90]
            self.actuelle, self.perdue = texte, 0.0
            return texte
        if self.actuelle:
            if not self.perdue:
                self.perdue = maintenant
            if maintenant - self.perdue < VIDEO_TOLERANCE:
                return self.actuelle
            self.actuelle = ""
        return ""


class StatsJeux:
    """Temps de jeu par jeu et par jour, FPS moyens (tools\\agent\\stats_jeux.json)."""

    def __init__(self):
        try:
            d = json.loads(FICHIER_STATS.read_text(encoding="utf-8"))
            if not isinstance(d, dict):
                d = {}
        except (OSError, ValueError):
            d = {}
        self.jeux = d.get("jeux") if isinstance(d.get("jeux"), dict) else {}
        self.jours = d.get("jours") if isinstance(d.get("jours"), dict) else {}
        self.en_cours = ""
        self.dernier = 0.0
        self.sauve = time.time()

    def compter(self, jeu, fps):
        """Ajoute le temps écoulé au jeu en cours. Renvoie son temps total en minutes (-1 si aucun jeu)."""
        maintenant = time.time()
        ecart = min(5.0, maintenant - self.dernier) if self.dernier else 0.0
        self.dernier = maintenant
        if not jeu:
            if self.en_cours:
                self.en_cours = ""
                self.sauver()
            return -1
        j = self.jeux.setdefault(jeu, {"secondes": 0, "sessions": 0, "fps_total": 0, "fps_n": 0,
                                       "dernier": ""})
        if jeu != self.en_cours:
            self.en_cours = jeu
            j["sessions"] = j.get("sessions", 0) + 1
            ecart = 0.0
        j["secondes"] = j.get("secondes", 0) + ecart
        if fps is not None and fps > 0:
            j["fps_total"] = j.get("fps_total", 0) + fps
            j["fps_n"] = j.get("fps_n", 0) + 1
        jour = time.strftime("%Y-%m-%d")
        j["dernier"] = jour
        du_jour = self.jours.setdefault(jour, {})
        du_jour[jeu] = du_jour.get(jeu, 0) + ecart
        if maintenant - self.sauve > 60:
            self.sauver()
        return int(j["secondes"] // 60)

    def sauver(self):
        self.sauve = time.time()
        for vieux in sorted(self.jours)[:-60]:  # garde les 60 derniers jours
            del self.jours[vieux]
        donnees = {"jeux": {n: {k: (round(v, 1) if isinstance(v, float) else v) for k, v in j.items()}
                            for n, j in self.jeux.items()},
                   "jours": {d: {n: round(s) for n, s in js.items()} for d, js in self.jours.items()}}
        try:
            tmp = FICHIER_STATS.with_suffix(".tmp")
            tmp.write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, FICHIER_STATS)
        except OSError as e:
            print(f"[agent] statistiques de jeu non enregistrées : {e}")


class LecteurLHM:
```

### Modification 3 — `tools/agent/agent_pc.py`

L'agent crée le détecteur de vidéo et les statistiques au démarrage.

**Avant :**

```python
        self.jeux = DetecteurJeu()   # Phase 9 : jeux hors Steam
```

**Après :**

```python
        self.jeux = DetecteurJeu()   # Phase 9 : jeux hors Steam
        self.video = DetecteurVideo()  # Phase 10 : scène cinéma
        self.stats = StatsJeux()       # Phase 10 : temps de jeu par jeu
```

### Modification 4 — `tools/agent/agent_pc.py`

Chaque seconde : vidéo, inactivité et temps total du jeu envoyés à l'ESP32.

**Avant :**

```python
        jeu = self.jeux.jeu(gpu()[1])
        etats = {
            "CASQUE": nom_court_audio(nom) if externe else "-",
            "MANETTE": "1" if manette_connectee() else "0",
            "VERROU": "1" if pc_verrouille() else "0",
            "JEU": texte_ascii(jeu, "Jeu") if jeu else "-",
        }
        for cle, valeur in etats.items():
            if self.precedent.get(cle) != valeur:
                self.precedent[cle] = valeur
                self.liaison.envoyer(f"EVT {cle} {valeur}")
                print(f"[agent] événement : {cle} = {valeur}")
```

**Après :**

```python
        jeu = self.jeux.jeu(gpu()[1])
        verrou = pc_verrouille()
        # Phase 10 : vidéo au premier plan, PC allumé mais inutilisé (en minutes, 0 = utilisé)
        video = "" if (jeu or verrou) else self.video.video()
        repos = inactivite()
        inactif = int(repos // 60) if repos >= INACTIF_APRES and not (jeu or video or verrou) else 0
        etats = {
            "CASQUE": nom_court_audio(nom) if externe else "-",
            "MANETTE": "1" if manette_connectee() else "0",
            "VERROU": "1" if verrou else "0",
            "JEU": texte_ascii(jeu, "Jeu") if jeu else "-",
            "VIDEO": video or "-",
            "INACTIF": str(inactif),
        }
        for cle, valeur in etats.items():
            if self.precedent.get(cle) != valeur:
                self.precedent[cle] = valeur
                self.liaison.envoyer(f"EVT {cle} {valeur}")
                if cle != "INACTIF" or valeur in ("0", str(INACTIF_APRES // 60)):
                    print(f"[agent] événement : {cle} = {valeur}")
        # temps total passé sur le jeu en cours (minutes), affiché par l'ESP32 en mode jeu
        total = self.stats.compter(jeu, self.donnees.get("fps", -1))
        if jeu and self.precedent.get("JEU_TOTAL") != total:
            self.precedent["JEU_TOTAL"] = total
            self.liaison.envoyer(f"JEU_TOTAL {total}")
```

### Modification 5 — `esp/main.py`

Nouvelles valeurs reçues du PC.

**Avant :**

```python
perf = {"cpu_temp": -1, "fps": -1}
evt = {"casque": "", "manette": 0, "verrou": 0, "jeu": ""}
```

**Après :**

```python
perf = {"cpu_temp": -1, "fps": -1, "total": -1}   # total : minutes passées sur le jeu en cours
evt = {"casque": "", "manette": 0, "verrou": 0, "jeu": "", "video": "", "video_titre": "",
       "inactif": 0}
```

### Modification 6 — `esp/main.py`

JEU_TOTAL compte comme une donnée du PC (le PC est là).

**Avant :**

```python
    if cmd in ("STAT", "GPU", "PERF", "EVT", "TEMPS", "METEO_J"):
```

**Après :**

```python
    if cmd in ("STAT", "GPU", "PERF", "EVT", "TEMPS", "METEO_J", "JEU_TOTAL"):
```

### Modification 7 — `esp/main.py`

Lecture de JEU_TOTAL.

**Avant :**

```python
    if cmd == "TEMPS":
        try:
```

**Après :**

```python
    if cmd == "JEU_TOTAL":
        try:
            perf["total"] = int(arg)
        except ValueError:
            return "ERR utilise : JEU_TOTAL minutes"
        return "OK"
    if cmd == "TEMPS":
        try:
```

### Modification 8 — `esp/main.py`

Événements VIDEO et INACTIF.

**Avant :**

```python
        elif typ == "JEU":
            evt["jeu"] = "" if val in ("", "-") else val
```

**Après :**

```python
        elif typ == "JEU":
            nouveau = "" if val in ("", "-") else val
            if nouveau != evt["jeu"]:
                perf["total"] = -1  # le PC renvoie le temps total du nouveau jeu (JEU_TOTAL)
            evt["jeu"] = nouveau
        elif typ == "VIDEO":
            # EVT VIDEO YouTube|Titre de la vidéo ; EVT VIDEO - = plus de vidéo
            if val in ("", "-"):
                evt["video"], evt["video_titre"] = "", ""
            else:
                source, _, titre = val.partition("|")
                evt["video"], evt["video_titre"] = source.strip() or "Vidéo", titre.strip()
        elif typ == "INACTIF":
            # EVT INACTIF n : PC allumé sans clavier ni souris depuis n minutes (0 = utilisé)
            try:
                evt["inactif"] = max(0, int(val))
            except ValueError:
                return "ERR utilise : EVT INACTIF minutes"
```

### Modification 9 — `esp/main.py`

En-tête du fichier.

**Avant :**

```python
#   luminosité réglable depuis l'app (LUM_ESP n).
```

**Après :**

```python
#   luminosité réglable depuis l'app (LUM_ESP n).
# - Phase 10 : EVT VIDEO (scène cinéma), EVT INACTIF (scène calme), JEU_TOTAL (mode jeu).
```

### Modification 10 — `tools/assets/generer_assets.py`

Dessins de la Phase 10 (salle de cinéma, salon calme, icônes), avant la partie Polices.

**Avant :**

```python
# ---------------------------------------------------------------------------
# Polices : fichier .fnt
```

**Après :**

```python
# ---------------------------------------------------------------------------
# Phase 10 : salle de cinéma (vidéo), salon calme (PC inutilisé), nouvelles icônes
# ---------------------------------------------------------------------------
CARTE_CINE = (16, 6, 12)
CARTE_CALME = (14, 20, 42)


def fond_cine():
    """Salle de cinéma : rideaux rouges, faisceau du projecteur, rangées de fauteuils."""
    im = degrade((10, 3, 8), (28, 6, 16), (46, 8, 20), coupure=0.5)
    # faisceau du projecteur (du coin haut droit vers la mascotte)
    calque = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    for k in range(14, 0, -1):
        a = int(5 + 3 * (14 - k))
        d.polygon([(W - 4, 6), (W - 4 - k * 8, H), (W - 4 + k * 3, H)], fill=(255, 230, 170, a // 3))
    im.alpha_composite(calque)
    halo(im, PERSO_X + PERSO_W // 2, 70, 64, (255, 190, 120), 40)
    d = ImageDraw.Draw(im, "RGBA")
    # rideaux : drapé vertical à droite et à gauche de la zone de la mascotte
    for x0, x1 in ((192, 212), (W - 14, W)):
        for x in range(x0, x1):
            t = (math.sin((x - x0) * 0.9) + 1) / 2
            r = int(120 + 70 * t)
            d.line((x, 0, x, H), fill=(r, 12, 24, 255))
    # lambrequin festonné en haut
    d.rectangle((192, 0, W, 9), fill=(150, 16, 30, 255))
    for x in range(192, W, 16):
        d.pieslice((x, 1, x + 16, 17), 0, 180, fill=(150, 16, 30, 255))
    d.line((192, 9, W, 9), fill=(230, 180, 60, 255))
    for x in range(192, W, 16):
        d.arc((x, 1, x + 16, 17), 0, 180, fill=(230, 180, 60, 255))
    # rangées de fauteuils (silhouettes) en bas
    for rang, (y, c) in enumerate(((H - 22, (36, 8, 18, 255)), (H - 11, (22, 4, 12, 255)))):
        for x in range(196 - rang * 9, W, 18):
            d.rounded_rectangle((x, y, x + 15, y + 16), 5, fill=c)
    carte(im, (6, 6, 186, 166), CARTE_CINE, (255, 120, 120, 45))
    return im


def fond_calme():
    """Salon calme au crépuscule : fenêtre sur le ciel, étoiles douces, plante."""
    im = degrade((14, 18, 44), (34, 44, 86), (70, 76, 120), coupure=0.6)
    d = ImageDraw.Draw(im, "RGBA")
    # fenêtre derrière la mascotte
    fx0, fy0, fx1, fy1 = 214, 14, 304, 104
    ciel = degrade((30, 40, 100), (120, 90, 150), (240, 150, 120), coupure=0.55)
    ciel = ciel.crop((0, 0, fx1 - fx0, fy1 - fy0)).resize((fx1 - fx0, fy1 - fy0))
    im.alpha_composite(ciel, (fx0, fy0))
    d = ImageDraw.Draw(im, "RGBA")
    random.seed(5)
    for _ in range(14):
        x, y = random.randint(fx0 + 3, fx1 - 3), random.randint(fy0 + 3, fy0 + 45)
        d.point((x, y), fill=(255, 250, 230, 220))
    d.rectangle((fx0, fy0, fx1, fy1), outline=(20, 22, 48, 255), width=3)
    d.line(((fx0 + fx1) // 2, fy0, (fx0 + fx1) // 2, fy1), fill=(20, 22, 48, 255), width=3)
    d.line((fx0, (fy0 + fy1) // 2, fx1, (fy0 + fy1) // 2), fill=(20, 22, 48, 255), width=3)
    d.rectangle((fx0 - 6, fy1, fx1 + 6, fy1 + 5), fill=(30, 30, 62, 255))  # rebord
    halo(im, PERSO_X + PERSO_W // 2, 110, 60, (150, 170, 255), 35)
    d = ImageDraw.Draw(im, "RGBA")
    # plante en pot à droite
    d.polygon([(298, 150), (316, 150), (313, 170), (301, 170)], fill=(170, 90, 70, 255))
    for k, (dx, h) in enumerate(((-6, 26), (2, 34), (10, 24), (-1, 18))):
        d.ellipse((306 + dx - 4, 150 - h, 306 + dx + 4, 150 - h + 18), fill=(70, 150, 110, 255))
    carte(im, (6, 6, 186, 166), CARTE_CALME, (255, 255, 255, 40))
    return im


def i_popcorn(d, T):
    for k, (x, y) in enumerate(((.30, .22), (.50, .14), (.70, .22), (.40, .32), (.60, .32))):
        r = T * .14
        d.ellipse((T * x - r, T * y - r + T * .06, T * x + r, T * y + r + T * .06), fill=(255, 236, 170, 255))
    d.polygon([(T * .18, T * .40), (T * .82, T * .40), (T * .72, T * .95), (T * .28, T * .95)],
              fill=(230, 40, 50, 255))
    for x in (.38, .50, .62):
        d.line((T * x, T * .42, T * x, T * .93), fill=(255, 255, 255, 255), width=int(T * .05))


def i_eau(d, T):
    d.polygon([(T * .5, T * .06), (T * .22, T * .55), (T * .78, T * .55)], fill=(60, 160, 255, 255))
    d.ellipse((T * .2, T * .36, T * .8, T * .94), fill=(60, 160, 255, 255))
    d.ellipse((T * .34, T * .56, T * .46, T * .70), fill=(220, 240, 255, 255))


def i_fenetre(d, T):
    d.rectangle((T * .14, T * .12, T * .86, T * .88), fill=(150, 200, 255, 255), outline=ENCRE, width=int(T * .08))
    d.line((T * .5, T * .12, T * .5, T * .88), fill=ENCRE, width=int(T * .07))
    d.line((T * .14, T * .5, T * .86, T * .5), fill=ENCRE, width=int(T * .07))


def i_livre(d, T):
    d.polygon([(T * .5, T * .26), (T * .08, T * .16), (T * .08, T * .80), (T * .5, T * .90)], fill=(0, 170, 220, 255))
    d.polygon([(T * .5, T * .26), (T * .92, T * .16), (T * .92, T * .80), (T * .5, T * .90)], fill=(0, 140, 200, 255))
    for k in range(3):
        y = .36 + k * .14
        d.line((T * .16, T * y, T * .42, T * (y + .05)), fill=(255, 255, 255, 255), width=int(T * .04))
        d.line((T * .58, T * (y + .05), T * .84, T * y), fill=(255, 255, 255, 255), width=int(T * .04))


def i_lit(d, T):
    d.rounded_rectangle((T * .08, T * .46, T * .92, T * .74), int(T * .06), fill=(110, 120, 220, 255))
    d.rounded_rectangle((T * .12, T * .34, T * .36, T * .50), int(T * .06), fill=(235, 235, 250, 255))
    d.rectangle((T * .08, T * .30, T * .14, T * .88), fill=ENCRE)
    d.rectangle((T * .86, T * .52, T * .92, T * .88), fill=ENCRE)
    w = int(T * .06)  # petit « z »
    d.line((T * .56, T * .06, T * .82, T * .06), fill=ENCRE, width=w)
    d.line((T * .82, T * .06, T * .56, T * .28), fill=ENCRE, width=w)
    d.line((T * .56, T * .28, T * .82, T * .28), fill=ENCRE, width=w)


def i_thermo(d, T):
    d.rounded_rectangle((T * .40, T * .06, T * .60, T * .66), int(T * .1), fill=(255, 255, 255, 255), outline=ENCRE, width=int(T * .06))
    d.ellipse((T * .28, T * .56, T * .72, T * .96), fill=(255, 80, 60, 255), outline=ENCRE, width=int(T * .06))
    d.rectangle((T * .46, T * .30, T * .54, T * .66), fill=(255, 80, 60, 255))


def i_chrono(d, T):
    d.ellipse((T * .12, T * .16, T * .88, T * .92), fill=(255, 255, 255, 255), outline=ENCRE, width=int(T * .08))
    d.rectangle((T * .42, T * .02, T * .58, T * .14), fill=ENCRE)
    d.line((T * .5, T * .54, T * .5, T * .30), fill=ENCRE, width=int(T * .07))
    d.line((T * .5, T * .54, T * .68, T * .62), fill=(0, 170, 220, 255), width=int(T * .07))


def i_etirer(d, T):  # bonhomme qui s'étire
    d.ellipse((T * .40, T * .06, T * .60, T * .26), fill=ENCRE)
    d.line((T * .5, T * .26, T * .5, T * .62), fill=ENCRE, width=int(T * .09))
    d.line((T * .5, T * .34, T * .18, T * .10), fill=ENCRE, width=int(T * .08))
    d.line((T * .5, T * .34, T * .82, T * .10), fill=ENCRE, width=int(T * .08))
    d.line((T * .5, T * .62, T * .30, T * .94), fill=ENCRE, width=int(T * .08))
    d.line((T * .5, T * .62, T * .70, T * .94), fill=ENCRE, width=int(T * .08))


def popcorn_main():
    """Pot de pop-corn tenu par la mascotte dans la salle de cinéma (24 × 26)."""
    im = Image.new("RGBA", (24 * 8, 26 * 8), (0, 0, 0, 0))
    i_popcorn(ImageDraw.Draw(im), 24 * 8)
    im = im.resize((24, 26), Image.LANCZOS)
    return sprite_transparent(im, (40, 52, 96))


def goutte_sueur():
    """Goutte de sueur près de la tête quand le PC chauffe (8 × 11)."""
    T = 8
    im = Image.new("RGBA", (8 * T, 11 * T), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(4 * T, 0), (1 * T, 6 * T), (7 * T, 6 * T)], fill=(120, 210, 255, 255))
    d.ellipse((1 * T, 3 * T, 7 * T, 10.5 * T), fill=(120, 210, 255, 255))
    d.ellipse((2.6 * T, 5 * T, 4 * T, 7 * T), fill=(235, 250, 255, 255))
    im = im.resize((8, 11), Image.LANCZOS)
    return sprite_transparent(im, (60, 30, 90))


def assets_phase10():
    """Écrit seulement les fichiers ajoutés en Phase 10 (les autres ne changent pas)."""
    SORTIE.mkdir(parents=True, exist_ok=True)
    APERCUS.mkdir(parents=True, exist_ok=True)
    for nom, f in (("cine", fond_cine), ("calme", fond_calme)):
        im = f()
        ecrire(f"fond_{nom}.bin", rgb565(im))
        im.convert("RGB").save(APERCUS / f"fond_{nom}.png")
    for nom, f in (("popcorn", i_popcorn), ("eau", i_eau), ("fenetre", i_fenetre), ("livre", i_livre),
                   ("lit", i_lit), ("thermo", i_thermo), ("chrono", i_chrono), ("etirer", i_etirer)):
        ecrire(f"ico_{nom}.bin", rgb565(icone(f)))
    ecrire("popcorn_main.bin", rgb565(popcorn_main()))
    ecrire("goutte.bin", rgb565(goutte_sueur()))


# ---------------------------------------------------------------------------
# Polices : fichier .fnt
```

### Modification 11 — `tools/assets/generer_assets.py`

main() écrit aussi les images de la Phase 10.

**Avant :**

```python
    print("Polices :")
```

**Après :**

```python
    print("Phase 10 :")
    assets_phase10()

    print("Polices :")
```

### Modification 12 — `.gitignore`

Fichiers personnels de l'agent jamais commités.

**Avant :**

```text
tools/agent/preferences.json
```

**Après :**

```text
tools/agent/preferences.json
tools/agent/jeux.json
tools/agent/stats_jeux.json
```

## Copie sur la carte

Comme d'habitude (voir CLAUDE.md) :
1. Crée `tools\agent\PAUSE` pour libérer le port de l'agent, attends 2 s.
2. `py -m mpremote devs` pour trouver le port, puis copie (relance une fois si `ClearCommError`) :
   - `esp/main.py` → `:main.py`
   - `esp/lib/ui.py` → `:lib/ui.py`
   - les 12 fichiers `esp/assets/*.bin` de la Partie 1 → `:assets/` (même nom)
3. `py -m mpremote connect <port> fs ls :assets` : 50 fichiers attendus. Puis `reset`.
4. Supprime `tools\agent\PAUSE`.

## Liste de contrôle

| Contrôle | Attendu |
|---|---|
| Test à blanc : les 12 blocs « avant » | chacun trouvé exactement 1 fois |
| Empreintes des 14 fichiers du zip | identiques au tableau de la Partie 1 |
| `py -m py_compile` sur agent_pc.py, esp/main.py, esp/lib/ui.py, tools/assets/generer_assets.py | aucune erreur |
| Carte : `fs ls :assets` | 50 fichiers, dont fond_cine.bin et fond_calme.bin (110080 octets) |
| Carte : `fs cat :erreur.txt` 30 s après le reset (s'il existe) | aucune nouvelle erreur |
| `git status` | modifiés : agent_pc.py, main.py, ui.py, generer_assets.py, .gitignore ; nouveaux : 12 .bin, 2 .png, docs/micro_phase10.md, docs/micro_phase10_fichiers.zip |

Commit des fichiers de la phase seulement (pas `docs/etat_micro.md`, `tools/agent/apps.json` ni `docs/micro_phase6_fichiers.zip`).
Ensuite, Mihaja redémarre la tâche planifiée en admin : `Stop-ScheduledTask "ESP32 Telecommande Agent"` puis `Start-ScheduledTask "ESP32 Telecommande Agent"`.

## Tests sur l'appareil (Mihaja)

1. **Météo** : attends une heure qui finit par 0 (ex. 21:30). Sous l'heure, les anneaux CPU / RAM laissent place à la météo d'aujourd'hui et de demain. À 21:32, retour aux anneaux.
2. **YouTube** : ouvre une vidéo dans Chrome. En 1 à 2 s, bandeau « Bon visionnage ! » puis salle de cinéma avec « YouTube » en rouge et le titre de la vidéo. Mets en pause plus de 10 s : retour à la scène normale. Relance : retour au cinéma.
3. **Page d'accueil YouTube** (aucune vidéo) : pas de cinéma.
4. **Anime-Sama** : un épisode → cinéma « Anime-Sama » en bleu, avec le titre.
5. **Netflix** : sur le site et dans l'app, cinéma « Netflix » pendant la lecture (le titre peut manquer : Netflix ne le met pas dans la fenêtre).
6. **VLC** : un film → cinéma « VLC » en orange, titre = nom du fichier sans « .mkv ».
7. **Calme** : laisse le PC sur le bureau sans toucher à rien pendant 3 min. Salon calme, une suggestion qui change toutes les 45 s, mascotte tranquille. Bouge la souris : retour immédiat à la scène normale.
8. **Jeu** : lance RDR2. Chrono de session en haut à droite (dès 1 min), courbe des FPS sous le chiffre, ligne du bas qui change toutes les 5 s. « Total sur ce jeu » apparaît dès la 1re minute.
9. **Chauffe** (si ça arrive) : GPU à 83 °C ou plus → bandeau « GPU chaud » et goutte de sueur.
10. Après une session de jeu : `tools\agent\stats_jeux.json` existe et contient le jeu.
11. Si quelque chose ne marche pas : envoie-moi les lignes `[agent] …` de `agent.log` et le contenu de `erreur.txt` sur la carte.
