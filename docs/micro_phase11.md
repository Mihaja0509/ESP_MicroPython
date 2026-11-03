# Micro — Phase 11 : scène master (labo AR), onglet Master, Cinéma, Mes jeux, notification

Date : 2026-11-04 · Statut : à appliquer · Base : commit b18705c (« Phase 10 : scènes cinéma et calme, météo, mode jeu enrichi »). Les blocs « avant » sont copiés du dépôt GitHub à ce commit.
Fichier joint : `docs/micro_phase11_fichiers.zip` (21 fichiers, SHA-256 du zip `62359eef…`).

## Ce que contient la phase

### Écran de l'ESP32 : scène « master »
- **Ambiance « labo AR de nuit »** : fond bleu nuit en aplats, grille en perspective discrète, lunettes AR en filigrane, points « hologramme ». La mascotte change de tenue : **veste de labo claire et lunettes AR**. Ses yeux restent visibles derrière les verres, avec les 4 visages.
- **Contenu de la carte** :
  - « J-9 » en grand avec le titre de la prochaine échéance (orange à J-7, rouge à J-3, « Aujourd'hui » le jour même) ;
  - l'objectif du jour, avec une case cochée en vert quand il est fait ;
  - les barres Lecture (PDF lus / objectif) et Rédaction (mots écrits aujourd'hui / objectif) ;
  - en bas : le dernier résultat de mesure (latence médiane, p95, petite courbe des 10 dernières sessions, mode, Hz, essais). S'il n'y en a pas, la prochaine réunion et la question à poser. Sinon, le temps passé sur le master aujourd'hui et la phase.
- **Quand la scène s'affiche** (jamais pendant un jeu ou une vidéo, ni quand le PC dort) :
  - **briefing du matin** : 60 s au premier usage du PC de la journée, après 6 h (mémorisé dans `briefing.txt` sur la carte, une seule fois par jour) ;
  - **pendant le travail** : quand une appli de recherche est au premier plan depuis 2 min, 20 s toutes les 5 min, en alternance avec la scène normale ;
  - **scène calme** : 1 suggestion sur 3 est remplacée par la carte master pendant 15 s ;
  - **événements** : bandeau 3 s puis scène 15 s pour un nouveau résultat de mesure, une réunion dans 1 h, une échéance à J-3, un objectif du jour atteint ou un objectif de mots atteint.
- **Rappels** : à chaque entrée dans la scène, un rappel sobre de 3 s. Ils tirent des règles de ton cours de méthodologie (matrice de synthèse, quartile de la revue, « structure, puis affine »), avec 2 phrases en anglais. Après 23 h : une seule fois « Tard : à demain ? », mascotte aux yeux fermés.
- La **mascotte réagit** : contente quand l'objectif est fait, surprise à l'arrivée d'un nouveau résultat.

### Programme PC : nouveau fichier `tools/agent/master.py`
- Réglages enregistrés dans `tools\agent\master.json` (jamais dans Git), modifiés depuis l'app : échéances, objectif du jour (il ne vaut que le jour où il est fixé ; les 20 derniers sont gardés), réunion + question, phase, objectifs chiffrés, chemins, mots-clés.
- **Calculé tout seul** (toutes les 30 s, et seulement si le fichier a changé) :
  - mots du mémoire `.docx`, lus directement dans le fichier, sans module en plus ;
  - mots écrits aujourd'hui (comparés au compte du jour précédent) ;
  - PDF lus et PDF à lire (les noms des PDF à lire servent d'idées d'objectif dans l'app) ;
  - dernier résultat du CSV de mesures : médiane, p95, nombre d'essais, mode, Hz, et médianes des 10 dernières sessions ;
  - temps passé dans les applis de recherche aujourd'hui. Applis comptées : Mendeley, Godot, Unity, Android Studio, PulseView, lecteurs PDF ; Word si le titre contient un des mots choisis ; VS Code de même ; navigateur sur Overleaf, Google Scholar, Semantic Scholar, ResearchRabbit, NotebookLM, ScienceDirect, IEEE Xplore, Springer, arXiv… ou sur un PDF.
- Historique dans `tools\agent\master_historique.json` (jamais dans Git).
- Vers l'ESP32 : `MASTER {json}` (en ASCII, les accents sont codés en `\u00e9`), et `MASTER_INFO ["icone", "texte"]` pour les événements.
- Pour l'app : messages `master`, `master_maj`, `master_afficher`, `jeux`, `jeux_maj`, `pas_un_jeu`. L'état envoyé 4 fois par seconde contient en plus `video`, `video_titre`, `inactif`, `jeu_total`, `master_v`, `master_actif`. HTTP `GET /etat_court` (avec `X-Token`) sert à la notification Android.

### App Dadou
- **Nouvel onglet « Master »** (6 onglets ; le nom ne s'affiche que sous l'onglet choisi) :
  - échéances : grand J-x, liste, ajout avec un calendrier et des suggestions (Assignments 2, 3 et 4 du cours, arrivée de la Odin 3, rapport au superviseur) ;
  - objectif du jour : à écrire, « Marquer comme fait », idées tirées des PDF à lire et des objectifs récents ;
  - avancement : lecture, rédaction, temps du jour (« en cours » quand tu travailles), dernier résultat avec sa petite courbe ;
  - réunion : date, heure et question ;
  - phase (État de l'art, Prototype, Mesures, Rédaction) et objectifs chiffrés ;
  - fichiers suivis sur le PC : mémoire, dossiers de PDF, CSV des mesures, mots-clés Word et VS Code, avec une coche verte quand le chemin existe ;
  - bouton « Afficher la scène master sur l'ESP32 ».
- **Accueil** :
  - **carte Cinéma** pendant une vidéo : source dans sa couleur, titre, ⏪ / lecture-pause / ⏩, volume, plein écran, sous-titres (YouTube, VLC) ou « Suivant ». Les touches sont adaptées à YouTube (J / K / L), VLC (Alt+flèches), Netflix et Anime-Sama (flèches) ;
  - **carte « PC inutilisé »** après 30 min : Éteindre (avec confirmation), Écran noir, Verrouiller ;
  - bouton **« Mes jeux »** dans les actions rapides.
- **Page « Mes jeux »** :
  - jeu en cours, avec « Ce n'est pas un jeu » ;
  - barres des 7 derniers jours ;
  - temps par jeu, sessions, FPS moyens, dernier jour joué ;
  - jeux reconnus : « Toujours un jeu » et « Jamais un jeu » (modifie `jeux.json` sur le PC).
- **Réglages** : carte « Notification PC inutilisé », avec interrupteur, seuil (15, 30 ou 60 min) et « Tester maintenant ». Android vérifie toutes les 15 min (WorkManager) et n'envoie qu'**une** notification par période d'inactivité, avec un bouton **Éteindre** (compte à rebours de 60 s, annulable). Rien n'est envoyé pendant un jeu, une vidéo ou un arrêt en cours.

### Plus tard (pas dans cette phase)
La scène « banc de test » (essai 12/50, checklist validée depuis l'app, écran figé pendant les mesures) viendra quand la Odin 3 et la photodiode seront là. Le CSV de résultats est déjà lu.

## Partie 1 et Partie 2 — Fichiers du zip

Extraire `docs/micro_phase11_fichiers.zip` à la racine de `Micro` (les chemins sont déjà dans le zip). Les fichiers marqués « remplacé en entier » écrasent la version actuelle. Vérifier chaque empreinte : 16 premiers caractères du SHA-256.

| Fichier | Rôle | Octets | SHA-256 (16 car.) |
|---|---|---|---|
| `tools/agent/master.py` | nouveau | 18599 | `f9a308fb77b89c2e` |
| `app/lib/ecrans/master.dart` | nouveau | 29871 | `cdf719e6fd1b551d` |
| `app/lib/ecrans/jeux.dart` | nouveau | 10521 | `1ccfe8e77d3aa562` |
| `app/lib/widgets/cinema.dart` | nouveau | 7050 | `4856746acfb55930` |
| `app/lib/notifications.dart` | nouveau | 3721 | `d375e9e83ea95655` |
| `app/android/app/src/main/kotlin/com/mmdigitek/esp_micro/VeilleurPC.kt` | nouveau | 8838 | `fabcd2bcedeea53d` |
| `esp/assets/fond_labo.bin` | nouveau | 110080 | `a5bd4136bdd2bb74` |
| `esp/assets/perso_ar_neutre.bin` | nouveau | 28500 | `0b873f9d8f9ce29b` |
| `esp/assets/perso_ar_cligne.bin` | nouveau | 28500 | `8894329d9ef46d3a` |
| `esp/assets/perso_ar_content.bin` | nouveau | 28500 | `c8cc0742819ad815` |
| `esp/assets/perso_ar_surpris.bin` | nouveau | 28500 | `11ecab9d1ed29761` |
| `esp/assets/ico_stylo.bin` | nouveau | 648 | `87f421621cbaf5c1` |
| `esp/assets/ico_graphe.bin` | nouveau | 648 | `f9eaa7f11dcc6727` |
| `esp/assets/ico_lunettes.bin` | nouveau | 648 | `efd216bb2ae5306a` |
| `esp/assets/ico_calendrier.bin` | nouveau | 648 | `48ddd2eb8ef1d55d` |
| `tools/assets/apercus/fond_labo.png` | nouveau | 3553 | `3f62b278f5329dbf` |
| `tools/assets/apercus/mascotte_ar.png` | nouveau | 25023 | `f6159332f45cc926` |
| `esp/lib/ui.py` | remplacé en entier | 43986 | `765785a11818639d` |
| `app/lib/etat.dart` | remplacé en entier | 4705 | `f807fd919ba2512e` |
| `app/lib/main.dart` | remplacé en entier | 3689 | `2aaed7d3a8a88937` |
| `app/android/app/src/main/kotlin/com/mmdigitek/esp_micro/MainActivity.kt` | remplacé en entier | 3596 | `f1a6f051c4f0706a` |

Les images sont produites par `tools/assets/generer_assets.py` modifié (fonction `assets_phase11()`, modifications 18 et 19). **Ne pas relancer le générateur** : les fichiers du zip font foi.

## Partie 3 — Modifications « avant → après » (dans l'ordre)

### Modification 1 — `tools/agent/agent_pc.py`

En-tête : nouveautés de la Phase 11.

**Avant :**

```python
  temps de jeu par jeu et par jour (tools\\agent\\stats_jeux.json, ligne JEU_TOTAL minutes).
```

**Après :**

```python
  temps de jeu par jeu et par jour (tools\\agent\\stats_jeux.json, ligne JEU_TOTAL minutes).
- Phase 11 : suivi du master (master.py : ligne MASTER {json} et MASTER_INFO vers l'ESP32,
  onglet Master de l'app), page « Mes jeux » de l'app, /etat_court pour la notification Android.
```

### Modification 2 — `tools/agent/agent_pc.py`

Import du module master.py (nouveau fichier, Partie 1).

**Avant :**

```python
    PORT_APP, ServeurApp = 8765, None
```

**Après :**

```python
    PORT_APP, ServeurApp = 8765, None

from master import SuiviMaster  # Phase 11 : suivi du master
```

### Modification 3 — `tools/agent/agent_pc.py`

L'agent crée le suivi du master au démarrage.

**Avant :**

```python
        self.stats = StatsJeux()       # Phase 10 : temps de jeu par jeu
```

**Après :**

```python
        self.stats = StatsJeux()       # Phase 10 : temps de jeu par jeu
        self.master = SuiviMaster(DOSSIER)  # Phase 11 : suivi du master
```

### Modification 4 — `tools/agent/agent_pc.py`

État envoyé à l'app 4 fois par seconde : vidéo, inactivité, temps total du jeu, version du master.

**Avant :**

```python
            "lum_esp": self.lum_esp, "ecrans": self.lent["ecrans"],
        }
```

**Après :**

```python
            "lum_esp": self.lum_esp, "ecrans": self.lent["ecrans"],
            # Phase 11
            "video": "" if p.get("VIDEO", "-") == "-" else p.get("VIDEO", "").split("|")[0],
            "video_titre": p.get("VIDEO", "").partition("|")[2],
            "inactif": int(p.get("INACTIF", "0") or 0),
            "jeu_total": p.get("JEU_TOTAL", -1),
            "master_v": self.master.version, "master_actif": self.master.actif,
        }
```

### Modification 5 — `tools/agent/agent_pc.py`

Chaque seconde : suivi du master, événements et ligne MASTER envoyés à l'ESP32.

**Avant :**

```python
            self.liaison.envoyer(f"JEU_TOTAL {total}")
```

**Après :**

```python
            self.liaison.envoyer(f"JEU_TOTAL {total}")
        # Phase 11 : suivi du master (appli au premier plan, échéances, mesures…)
        hwnd, pid = fenetre_premier_plan()
        exe = titre = ""
        if hwnd and pid:
            try:
                exe = psutil.Process(pid).name().lower()
            except psutil.Error:
                exe = ""
            titre = titre_fenetre(hwnd)
        self.master.seconde(exe, titre, repos, bool(jeu) or verrou)
        for icone, texte in self.master.evenements():
            self.liaison.envoyer("MASTER_INFO " + json.dumps([icone, texte], ensure_ascii=True))
            print(f"[agent] master : {texte}")
        ligne_master = self.master.ligne_esp()
        if self.precedent.get("MASTER") != ligne_master:
            self.precedent["MASTER"] = ligne_master
            self.liaison.envoyer(ligne_master)
```

### Modification 6 — `tools/agent/agent_pc.py`

Fonctions pour l'app (jeux, master, état court), juste avant rappels_app().

**Avant :**

```python
    def rappels_app(self):
```

**Après :**

```python
    # --------------------------------------------------------------- Phase 11 : app
    def jeux_pour_app(self):
        """Statistiques de jeu, listes de jeux.json et jeu en cours (page « Mes jeux » de l'app)."""
        jeux, pas = charger_jeux()
        liste = []
        for nom, j in list(self.stats.jeux.items()):
            n = j.get("fps_n", 0)
            liste.append({"nom": nom, "minutes": int(j.get("secondes", 0) // 60),
                          "sessions": j.get("sessions", 0),
                          "fps": round(j.get("fps_total", 0) / n) if n else -1,
                          "dernier": j.get("dernier", "")})
        liste.sort(key=lambda j: j["minutes"], reverse=True)
        semaine = []
        for k in range(6, -1, -1):
            jour = time.strftime("%Y-%m-%d", time.localtime(time.time() - k * 86400))
            secondes = sum(dict(self.stats.jours.get(jour, {})).values())
            semaine.append({"date": jour, "minutes": int(secondes // 60)})
        p = self.precedent
        return {"stats": liste, "semaine": semaine, "jeux": sorted(jeux), "pas_des_jeux": sorted(pas),
                "en_cours": {"nom": "" if p.get("JEU", "-") == "-" else p.get("JEU"),
                             "exe": self.jeux.exe}}

    def jeux_maj(self, jeux, pas):
        """Enregistre tools\\agent\\jeux.json (listes modifiées dans l'app)."""
        def propre(liste):
            res = []
            for n in liste if isinstance(liste, list) else []:
                n = str(n).strip().strip('"').lower()
                if n and not n.endswith(".exe"):
                    n += ".exe"
                if n and len(n) <= 60 and "\\" not in n and "/" not in n and n not in res:
                    res.append(n)
            return res[:100]
        j = propre(jeux)
        p = [n for n in propre(pas) if n not in j]
        try:
            FICHIER_JEUX.write_text(json.dumps({"jeux": j, "pas_des_jeux": p}, ensure_ascii=False,
                                               indent=1), encoding="utf-8")
        except OSError as e:
            return False, f"jeux.json non enregistré : {e}"
        self.jeux.listes_lues = 0.0  # relu à la prochaine seconde
        return True, "Liste des jeux enregistrée"

    def pas_un_jeu(self):
        """Le jeu détecté hors Steam n'en est pas un : son .exe va dans « pas_des_jeux »."""
        exe = self.jeux.exe
        if not exe:
            return False, "Aucun jeu hors Steam en cours (un jeu Steam ne peut pas être retiré)"
        jeux, pas = charger_jeux()
        ok, texte = self.jeux_maj([n for n in jeux if n != exe], sorted(pas | {exe}))
        return ok, (f"{exe} ne sera plus pris pour un jeu" if ok else texte)

    def etat_court(self):
        """Pour la notification Android « PC inutilisé » (GET /etat_court)."""
        p = self.precedent
        return {"repos_min": int(inactivite() // 60), "verrou": p.get("VERROU") == "1",
                "jeu": "" if p.get("JEU", "-") == "-" else p.get("JEU"),
                "video": "" if p.get("VIDEO", "-") == "-" else p.get("VIDEO", "").split("|")[0],
                "arret": self.arret_reste()}

    def master_afficher(self):
        self.liaison.envoyer("MASTER_INFO " + json.dumps(["lunettes", "Point sur le master"]))
        return True, "Scène master affichée sur l'ESP32"

    def rappels_app(self):
```

### Modification 7 — `tools/agent/agent_pc.py`

Nouvelles fonctions données au serveur de l'app.

**Avant :**

```python
            "apercu": capture_ecran, "pointeur": pointeur_pc,
```

**Après :**

```python
            "apercu": capture_ecran, "pointeur": pointeur_pc,
            "master": self.master.pour_app, "master_maj": self.master.maj,
            "master_afficher": self.master_afficher,
            "jeux": self.jeux_pour_app, "jeux_maj": self.jeux_maj, "pas_un_jeu": self.pas_un_jeu,
            "etat_court": self.etat_court,
```

### Modification 8 — `tools/agent/serveur_app.py`

Documentation des nouveaux messages.

**Avant :**

```python
    puis l'image JPEG en message binaire ; {"type": "apercu_erreur", "texte": "..."}
```

**Après :**

```python
    puis l'image JPEG en message binaire ; {"type": "apercu_erreur", "texte": "..."}
  Phase 11 :
    {"type": "master"} -> {"type": "master", config, auto, temps_jour, chemins_ok, phases, version}
    {"type": "master_maj", "master": {…partie des réglages…}} -> rep (ligne « master_maj ») + master
    {"type": "master_afficher"} -> rep : la scène master s'affiche 15 s sur l'ESP32
    {"type": "jeux"} -> {"type": "jeux", stats, semaine, jeux, pas_des_jeux, en_cours}
    {"type": "jeux_maj", "jeux": [...], "pas_des_jeux": [...]} et {"type": "pas_un_jeu"} -> rep + jeux
```

### Modification 9 — `tools/agent/serveur_app.py`

Documentation de /etat_court.

**Avant :**

```python
  -> texte de la réponse (comme dans la console), 401 si le téléphone n'est pas appairé.
```

**Après :**

```python
  -> texte de la réponse (comme dans la console), 401 si le téléphone n'est pas appairé.
  GET /etat_court (même en-tête, Phase 11) -> JSON {repos_min, verrou, jeu, video, arret}
  pour la notification « PC inutilisé » du téléphone.
```

### Modification 10 — `tools/agent/serveur_app.py`

Requête HTTP /etat_court (notification Android).

**Avant :**

```python
        morceaux = urllib.parse.urlsplit(requete.path)
        if morceaux.path != "/widget":
            return None
        if not self.token_valide(requete.headers.get("X-Token", "")):
            return connexion.respond(HTTPStatus.UNAUTHORIZED, "Non autorisé\n")
```

**Après :**

```python
        morceaux = urllib.parse.urlsplit(requete.path)
        if morceaux.path not in ("/widget", "/etat_court"):
            return None
        if not self.token_valide(requete.headers.get("X-Token", "")):
            return connexion.respond(HTTPStatus.UNAUTHORIZED, "Non autorisé\n")
        if morceaux.path == "/etat_court":
            try:
                court = self.r["etat_court"]()
            except Exception as e:
                court = {"erreur": str(e)}
            return connexion.respond(HTTPStatus.OK, json.dumps(court, ensure_ascii=False))
```

### Modification 11 — `tools/agent/serveur_app.py`

Messages master et jeux.

**Avant :**

```python
                elif typ == "pointeur":
```

**Après :**

```python
                elif typ == "master":
                    await self._envoyer(ws, {"type": "master", **self.r["master"]()})
                elif typ == "master_maj":
                    ok, texte = await boucle.run_in_executor(None, self.r["master_maj"], m.get("master"))
                    await self._envoyer(ws, {"type": "rep", "ligne": typ, "texte": texte, "ok": ok})
                    await self._envoyer(ws, {"type": "master", **self.r["master"]()})
                elif typ == "master_afficher":
                    ok, texte = self.r["master_afficher"]()
                    await self._envoyer(ws, {"type": "rep", "ligne": typ, "texte": texte, "ok": ok})
                elif typ == "jeux":
                    await self._envoyer(ws, {"type": "jeux", **self.r["jeux"]()})
                elif typ in ("jeux_maj", "pas_un_jeu"):
                    if typ == "jeux_maj":
                        ok, texte = await boucle.run_in_executor(
                            None, self.r["jeux_maj"], m.get("jeux"), m.get("pas_des_jeux"))
                    else:
                        ok, texte = await boucle.run_in_executor(None, self.r["pas_un_jeu"])
                    await self._envoyer(ws, {"type": "rep", "ligne": typ, "texte": texte, "ok": ok})
                    await self._envoyer(ws, {"type": "jeux", **self.r["jeux"]()})
                elif typ == "pointeur":
```

### Modification 12 — `esp/main.py`

En-tête.

**Avant :**

```python
# - Phase 10 : EVT VIDEO (scène cinéma), EVT INACTIF (scène calme), JEU_TOTAL (mode jeu).
```

**Après :**

```python
# - Phase 10 : EVT VIDEO (scène cinéma), EVT INACTIF (scène calme), JEU_TOTAL (mode jeu).
# - Phase 11 : MASTER {json} (scène master), MASTER_INFO ["icone", "texte"] (événement).
```

### Modification 13 — `esp/main.py`

Module json (lecture des lignes MASTER).

**Avant :**

```python
import select
```

**Après :**

```python
import json
import select
```

### Modification 14 — `esp/main.py`

Données du master dans l'état.

**Avant :**

```python
        "lum": 85}             # luminosité choisie dans l'app (5 à 100)
```

**Après :**

```python
        "lum": 85,             # luminosité choisie dans l'app (5 à 100)
        "master": None}        # Phase 11 : données du master (ligne MASTER du PC)
```

### Modification 15 — `esp/main.py`

Les lignes MASTER sont plus longues (JSON).

**Avant :**

```python
            if len(tampon) > 300:
```

**Après :**

```python
            if len(tampon) > 900:
```

### Modification 16 — `esp/main.py`

MASTER et MASTER_INFO comptent comme des données du PC.

**Avant :**

```python
    if cmd in ("STAT", "GPU", "PERF", "EVT", "TEMPS", "METEO_J", "JEU_TOTAL"):
```

**Après :**

```python
    if cmd in ("STAT", "GPU", "PERF", "EVT", "TEMPS", "METEO_J", "JEU_TOTAL", "MASTER", "MASTER_INFO"):
```

### Modification 17 — `esp/main.py`

Lecture de MASTER et MASTER_INFO.

**Avant :**

```python
    if cmd == "JEU_TOTAL":
```

**Après :**

```python
    if cmd == "MASTER":
        try:
            m = json.loads(arg)
        except ValueError:
            return "ERR MASTER : JSON invalide"
        if not isinstance(m, dict):
            return "ERR MASTER : objet attendu"
        etat["master"] = m
        return "OK"
    if cmd == "MASTER_INFO":
        try:
            icone, texte = json.loads(arg)[:2]
        except (ValueError, TypeError):
            return "ERR utilise : MASTER_INFO [\"icone\", \"texte\"]"
        ui.info_master(str(icone), str(texte))
        return "OK"
    if cmd == "JEU_TOTAL":
```

### Modification 18 — `tools/assets/generer_assets.py`

Dessins de la Phase 11 (tenue labo AR, fond labo, icônes), avant la partie Polices.

**Avant :**

```python
# ---------------------------------------------------------------------------
# Polices : fichier .fnt
```

**Après :**

```python
# ---------------------------------------------------------------------------
# Phase 11 : tenue « labo AR » (scène master) — veste claire + lunettes AR
# ---------------------------------------------------------------------------
VESTE = (226, 232, 242, 255)
VESTE_OMBRE = (176, 188, 210, 255)
MONTURE = (28, 32, 46, 255)


def corps_labo(remonter=30):
    """Buste en veste de labo claire, col et fermeture éclair cyan, badge sur la poitrine."""
    L = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    bas_cou = 660 - remonter
    d.rectangle((474, 540, 548, bas_cou), fill=PEAU)
    d.line([(474, 540), (474, bas_cou)], fill=CONTOUR, width=7)
    d.line([(548, 540), (548, bas_cou)], fill=CONTOUR, width=7)
    d.rectangle((477, 572, 545, 584), fill=PEAU_OMBRE)
    avant = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    d = ImageDraw.Draw(avant)
    # t-shirt sombre dans l'encolure
    d.polygon([(430, 624), (512, 700), (594, 624)], fill=(24, 30, 52, 255))
    # les deux pans de la veste (encolure en V)
    gauche = [(300, 690), (352, 640), (430, 616), (512, 720), (512, 870), (272, 870)]
    droite = [(724, 690), (672, 640), (594, 616), (512, 720), (512, 870), (752, 870)]
    for pan in (gauche, droite):
        d.polygon(pan, fill=VESTE, outline=CONTOUR, width=9)
    # revers du col, bordés de cyan
    d.polygon([(430, 616), (468, 640), (500, 712), (512, 720)], fill=VESTE_OMBRE)
    d.polygon([(594, 616), (556, 640), (524, 712), (512, 720)], fill=VESTE_OMBRE)
    d.line([(430, 616), (512, 720), (594, 616)], fill=ACCENT, width=8)
    d.line([(512, 720), (512, 870)], fill=CONTOUR, width=7)
    # plis des manches
    d.line([(352, 700), (336, 860)], fill=VESTE_OMBRE, width=10)
    d.line([(672, 700), (688, 860)], fill=VESTE_OMBRE, width=10)
    # badge « AR » sur la poitrine (rectangle cyan + petit trait)
    d.rounded_rectangle((560, 742, 640, 790), 8, fill=ACCENT, outline=CONTOUR, width=5)
    d.rectangle((574, 756, 626, 764), fill=(255, 255, 255, 255))
    d.rectangle((574, 770, 608, 776), fill=(255, 255, 255, 255))
    L.alpha_composite(avant, (0, -remonter))
    return L


def lunettes_ar(img):
    """Lunettes AR (style XREAL) : monture sombre, verres teintés transparents, reflet cyan."""
    verres = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(verres)
    boites = ((372, 372, 492, 456), (528, 372, 648, 456))
    for b in boites:
        d.rounded_rectangle(b, 26, fill=(20, 60, 110, 95))
    img.alpha_composite(verres)
    d = ImageDraw.Draw(img)
    for b in boites:
        d.rounded_rectangle(b, 26, outline=MONTURE, width=12)
        # reflet holographique en haut du verre
        d.line([(b[0] + 26, b[1] + 16), (b[2] - 40, b[1] + 16)], fill=(120, 235, 255, 255), width=6)
    d.line([(492, 400), (528, 400)], fill=MONTURE, width=12)       # pont
    d.line([(372, 398), (316, 386)], fill=MONTURE, width=12)       # branches
    d.line([(648, 398), (704, 386)], fill=MONTURE, width=12)
    d.rectangle((596, 362, 640, 372), fill=ACCENT)                 # petite diode cyan


def perso_ar(yeux="ouverts", bouche="normale", taille=(PERSO_W, PERSO_H)):
    base = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    base.alpha_composite(corps_labo())
    base.alpha_composite(tete(yeux, bouche))
    lunettes_ar(base)
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
    o = o.crop((262, 44, 762, 834))
    return o.resize(taille, Image.LANCZOS)

CARTE_LABO = (20, 28, 48)


def fond_labo():
    """Labo AR de nuit : bleu nuit en aplats, grille en perspective discrète, lunettes AR en filigrane."""
    im = Image.new("RGBA", (W, H), (11, 16, 32, 255))
    d = ImageDraw.Draw(im, "RGBA")
    # léger halo derrière la mascotte (aplats concentriques, pas de dégradé fin)
    for r, c in ((78, (14, 22, 44)), (60, (16, 27, 52)), (42, (18, 31, 58))):
        d.ellipse((PERSO_X + PERSO_W // 2 - r, 92 - r, PERSO_X + PERSO_W // 2 + r, 92 + r), fill=c + (255,))
    # grille en perspective en bas à droite
    horizon = 128
    for i in range(-10, 11):
        x0 = 256 + i * 9
        x1 = 256 + i * 46
        d.line((x0, horizon, x1, H), fill=(0, 60, 75, 255), width=1)
    y, pas = horizon, 4
    while y < H:
        d.line((190, y, W, y), fill=(0, 60, 75, 255), width=1)
        y += pas
        pas += 3
    # contour de lunettes AR en filigrane, derrière la tête de la mascotte
    cx, cy = PERSO_X + PERSO_W // 2, 46
    for dx in (-26, 26):
        d.rounded_rectangle((cx + dx - 22, cy - 13, cx + dx + 22, cy + 13), 9, outline=(0, 90, 115, 255), width=2)
    d.line((cx - 4, cy - 4, cx + 4, cy - 4), fill=(0, 90, 115, 255), width=2)
    d.line((cx - 48, cy - 6, cx - 60, cy - 10), fill=(0, 90, 115, 255), width=2)
    d.line((cx + 48, cy - 6, cx + 60, cy - 10), fill=(0, 90, 115, 255), width=2)
    # petits points « hologramme »
    random.seed(21)
    for _ in range(26):
        x, y = random.randint(196, W - 4), random.randint(4, 124)
        c = random.choice(((0, 200, 230), (0, 120, 150), (90, 160, 200)))
        d.rectangle((x, y, x + (1 if random.random() < .7 else 2), y + 1), fill=c + (255,))
    # carte de gauche
    d.rounded_rectangle((6, 6, 186, 166), 10, fill=CARTE_LABO + (255,), outline=(0, 200, 230, 90), width=1)
    return im


def i_stylo(d, T):
    d.polygon([(T * .70, T * .10), (T * .90, T * .30), (T * .38, T * .82), (T * .18, T * .62)], fill=(0, 170, 220, 255))
    d.polygon([(T * .18, T * .62), (T * .38, T * .82), (T * .10, T * .92)], fill=(240, 200, 140, 255))
    d.polygon([(T * .10, T * .92), (T * .16, T * .84), (T * .19, T * .87)], fill=ENCRE)
    d.line((T * .62, T * .18, T * .82, T * .38), fill=ENCRE, width=int(T * .06))


def i_graphe(d, T):
    d.line((T * .12, T * .10, T * .12, T * .88, T * .92, T * .88), fill=ENCRE, width=int(T * .07))
    pts = [(T * .18, T * .70), (T * .38, T * .48), (T * .56, T * .58), (T * .84, T * .22)]
    d.line(pts, fill=(80, 200, 140, 255), width=int(T * .09), joint="curve")
    for x, y in pts:
        d.ellipse((x - T * .06, y - T * .06, x + T * .06, y + T * .06), fill=(80, 200, 140, 255))


def i_lunettes(d, T):
    for x0 in (.06, .54):
        d.rounded_rectangle((T * x0, T * .34, T * (x0 + .40), T * .68), int(T * .1),
                            fill=(60, 140, 200, 255), outline=ENCRE, width=int(T * .07))
        d.line((T * (x0 + .07), T * .44, T * (x0 + .22), T * .44), fill=(200, 245, 255, 255), width=int(T * .05))
    d.line((T * .46, T * .44, T * .54, T * .44), fill=ENCRE, width=int(T * .07))


def i_calendrier(d, T):
    d.rounded_rectangle((T * .10, T * .18, T * .90, T * .90), int(T * .1), fill=(255, 255, 255, 255), outline=ENCRE, width=int(T * .07))
    d.rectangle((T * .10, T * .18, T * .90, T * .38), fill=(255, 90, 90, 255))
    for x in (.30, .70):
        d.line((T * x, T * .08, T * x, T * .28), fill=ENCRE, width=int(T * .08))
    for k in range(6):
        x = .24 + (k % 3) * .2
        y = .52 + (k // 3) * .18
        d.rectangle((T * x, T * y, T * (x + .1), T * (y + .1)), fill=ENCRE)


def assets_phase11():
    """Écrit seulement les fichiers ajoutés en Phase 11."""
    SORTIE.mkdir(parents=True, exist_ok=True)
    APERCUS.mkdir(parents=True, exist_ok=True)
    im = fond_labo()
    ecrire("fond_labo.bin", rgb565(im))
    im.convert("RGB").save(APERCUS / "fond_labo.png")
    images = {"neutre": dict(), "cligne": dict(yeux="fermes"),
              "content": dict(yeux="contents", bouche="rire"), "surpris": dict(bouche="o")}
    planche = Image.new("RGB", (PERSO_W * 4 + 40, PERSO_H + 10), (11, 16, 32))
    for i, (nom, opts) in enumerate(images.items()):
        im = perso_ar(**opts)
        ecrire(f"perso_ar_{nom}.bin", rgb565(sprite_transparent(im, (18, 31, 58))))
        planche.paste(im, (5 + i * (PERSO_W + 10), 5), im)
    planche.save(APERCUS / "mascotte_ar.png")
    for nom, f in (("stylo", i_stylo), ("graphe", i_graphe), ("lunettes", i_lunettes),
                   ("calendrier", i_calendrier)):
        ecrire(f"ico_{nom}.bin", rgb565(icone(f)))


# ---------------------------------------------------------------------------
# Polices : fichier .fnt
```

### Modification 19 — `tools/assets/generer_assets.py`

main() écrit aussi les images de la Phase 11.

**Avant :**

```python
    print("Phase 10 :")
    assets_phase10()
```

**Après :**

```python
    print("Phase 10 :")
    assets_phase10()
    print("Phase 11 :")
    assets_phase11()
```

### Modification 20 — `.gitignore`

Fichiers personnels du master jamais commités.

**Avant :**

```text
tools/agent/stats_jeux.json
```

**Après :**

```text
tools/agent/stats_jeux.json
tools/agent/master.json
tools/agent/master_historique.json
```

### Modification 21 — `app/lib/connexion.dart`

Données du master et des jeux gardées par la connexion.

**Avant :**

```dart
  final Map<String, Completer<(bool, String)>> _attentes = {};
```

**Après :**

```dart
  final Map<String, Completer<(bool, String)>> _attentes = {};

  /// Phase 11 : données de l'onglet Master et de la page « Mes jeux » (null = pas encore reçues).
  Map<String, dynamic>? master;
  Map<String, dynamic>? jeux;
  int _masterV = -1;
```

### Modification 22 — `app/lib/connexion.dart`

Après l'appairage : demande aussi les données du master.

**Avant :**

```dart
        _envoyer({'type': 'raccourcis'});
```

**Après :**

```dart
        _envoyer({'type': 'raccourcis'});
        _envoyer({'type': 'master'});
```

### Modification 23 — `app/lib/connexion.dart`

Quand les données du master changent sur le PC (version), l'app les redemande.

**Avant :**

```dart
        etat = EtatPC.depuisJson(m);
        _dernierEtat = DateTime.now();
```

**Après :**

```dart
        etat = EtatPC.depuisJson(m);
        _dernierEtat = DateTime.now();
        if (etat.masterV != _masterV) {
          _masterV = etat.masterV;
          _envoyer({'type': 'master'});
        }
```

### Modification 24 — `app/lib/connexion.dart`

Réception des messages « master » et « jeux ».

**Avant :**

```dart
      case 'apercu_erreur':
        apercuInfos.value = {'erreur': (m['texte'] ?? 'Aperçu impossible').toString()};
    }
    return false;
```

**Après :**

```dart
      case 'apercu_erreur':
        apercuInfos.value = {'erreur': (m['texte'] ?? 'Aperçu impossible').toString()};
      case 'master':
        master = Map<String, dynamic>.from(m);
        return true;
      case 'jeux':
        jeux = Map<String, dynamic>.from(m);
        return true;
    }
    return false;
```

### Modification 25 — `app/lib/connexion.dart`

Demandes au PC pour le master et les jeux.

**Avant :**

```dart
  // ------------------------------------------------------------- appairage
```

**Après :**

```dart
  // ------------------------------------------------------------- master et jeux (Phase 11)
  void demanderMaster() => _envoyer({'type': 'master'});

  Future<(bool, String)> majMaster(Map<String, dynamic> changements) =>
      _demander({'type': 'master_maj', 'master': changements});

  Future<(bool, String)> afficherMaster() => _demander({'type': 'master_afficher'});

  void demanderJeux() => _envoyer({'type': 'jeux'});

  Future<(bool, String)> majJeux(List<String> jeux, List<String> pasDesJeux) =>
      _demander({'type': 'jeux_maj', 'jeux': jeux, 'pas_des_jeux': pasDesJeux});

  Future<(bool, String)> pasUnJeu() => _demander({'type': 'pas_un_jeu'});

  // ------------------------------------------------------------- appairage
```

### Modification 26 — `app/lib/ecrans/accueil.dart`

Imports des cartes Cinéma / PC inutilisé et de la page « Mes jeux ».

**Avant :**

```dart
import '../widgets/mascotte.dart';
```

**Après :**

```dart
import '../widgets/cinema.dart';
import '../widgets/mascotte.dart';
import 'jeux.dart';
```

### Modification 27 — `app/lib/ecrans/accueil.dart`

Carte Cinéma pendant une vidéo, carte « PC inutilisé » après 30 min.

**Avant :**

```dart
          if (e.enJeu) ...[_carteJeu(e), const SizedBox(height: 14)],
```

**Après :**

```dart
          if (e.enJeu) ...[_carteJeu(e), const SizedBox(height: 14)],
          if (e.enVideo) ...[CarteCinema(cx: cx, etat: e), const SizedBox(height: 14)],
          if (e.inactif >= 30) ...[CartePcInutilise(cx: cx, minutes: e.inactif), const SizedBox(height: 14)],
```

### Modification 28 — `app/lib/ecrans/accueil.dart`

Bouton « Mes jeux » dans les actions rapides.

**Avant :**

```dart
                  icone: Icons.space_dashboard_rounded, texte: 'Bureau', onTap: () => cx.cmd('KEY win+d')),
```

**Après :**

```dart
                  icone: Icons.space_dashboard_rounded, texte: 'Bureau', onTap: () => cx.cmd('KEY win+d')),
              BoutonAction(
                icone: Icons.sports_esports_rounded,
                texte: 'Mes jeux',
                couleur: Couleurs.magenta,
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => EcranJeux(cx: cx))),
              ),
```

### Modification 29 — `app/lib/ecrans/reglages.dart`

Import de la carte Notification.

**Avant :**

```dart
import '../widget_android.dart';
```

**Après :**

```dart
import '../notifications.dart';
import '../widget_android.dart';
```

### Modification 30 — `app/lib/ecrans/reglages.dart`

Carte « Notification PC inutilisé » sous la carte Widget.

**Avant :**

```dart
        CarteWidgetAndroid(cx: cx),
```

**Après :**

```dart
        CarteWidgetAndroid(cx: cx),
        const SizedBox(height: 14),
        const CarteNotifications(),
```

### Modification 31 — `app/android/app/src/main/AndroidManifest.xml`

Permission d'afficher des notifications (Android 13 et plus).

**Avant :**

```xml
    <uses-permission android:name="android.permission.INTERNET"/>
```

**Après :**

```xml
    <uses-permission android:name="android.permission.INTERNET"/>
    <!-- Phase 11 : notification « PC inutilisé » -->
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
```

### Modification 32 — `app/android/app/src/main/AndroidManifest.xml`

Récepteur du bouton « Éteindre » de la notification.

**Avant :**

```xml
        <!-- Don't delete the meta-data below.
```

**Après :**

```xml
        <!-- Phase 11 : bouton « Éteindre » de la notification « PC inutilisé » -->
        <receiver
            android:name=".ActionNotification"
            android:exported="false" />
        <!-- Don't delete the meta-data below.
```

### Modification 33 — `app/android/app/build.gradle.kts`

WorkManager (vérification toutes les 15 min en arrière-plan).

**Avant :**

```kotlin
flutter {
    source = "../.."
}
```

**Après :**

```kotlin
flutter {
    source = "../.."
}

dependencies {
    // Phase 11 : notification « PC inutilisé » (VeilleurPC.kt)
    implementation("androidx.work:work-runtime-ktx:2.10.0")
    implementation("androidx.core:core-ktx:1.13.1")
}
```

## Copie sur la carte

Comme d'habitude (voir CLAUDE.md) :
1. Crée `tools\agent\PAUSE`, attends 2 s.
2. `py -m mpremote devs` pour trouver le port, puis copie (relance une fois si `ClearCommError`) :
   - `esp/main.py` → `:main.py`
   - `esp/lib/ui.py` → `:lib/ui.py`
   - les 9 fichiers `esp/assets/*.bin` de la Partie 1 → `:assets/` (même nom)
3. `fs ls :assets` : **59 fichiers** attendus. Puis `reset`.
4. Supprime `tools\agent\PAUSE`.

## Liste de contrôle

| Contrôle | Attendu |
|---|---|
| Empreintes des 21 fichiers du zip | identiques au tableau |
| Test à blanc : les 33 blocs « avant » | chacun trouvé exactement 1 fois |
| `py -m py_compile` sur agent_pc.py, serveur_app.py, master.py, esp/main.py, esp/lib/ui.py, generer_assets.py | aucune erreur |
| `py -X utf8 -c "import sys; sys.path.insert(0, r'tools\agent'); import master; print(master.SuiviMaster(r'tools\agent').ligne_esp())"` | une ligne qui commence par `MASTER {` |
| `flutter analyze` (dans app/) | No issues found |
| `flutter build apk --release` (dans app/) | APK créée (Gradle télécharge WorkManager la 1re fois) |
| Carte : `fs ls :assets` | 59 fichiers |
| Carte : `fs cat :erreur.txt` 30 s après le reset | pas d'erreur nouvelle (taille inchangée : 1402 octets) |
| `git status` | modifiés : agent_pc.py, serveur_app.py, main.py, ui.py, generer_assets.py, .gitignore, connexion.dart, accueil.dart, reglages.dart, etat.dart, main.dart, MainActivity.kt, AndroidManifest.xml, build.gradle.kts ; nouveaux : master.py, master.dart, jeux.dart, cinema.dart, notifications.dart, VeilleurPC.kt, 9 .bin, 2 .png, docs/micro_phase11.md, docs/micro_phase11_fichiers.zip |

Commit des fichiers de la phase seulement (pas `docs/etat_micro.md`, `tools/agent/apps.json` ni `docs/micro_phase6_fichiers.zip`).
Ensuite, Mihaja redémarre la tâche planifiée en admin et installe la nouvelle APK.

## Tests sur l'appareil (Mihaja)

**Première configuration (app → onglet Master)**
1. « Fichiers suivis sur le PC » → ouvre la carte. Mets les chemins de ton mémoire `.docx`, de tes dossiers de PDF « à lire » et « lus » (crée-les s'ils n'existent pas), et laisse le CSV vide pour l'instant → « Enregistrer ». Les coches deviennent vertes.
2. Ajoute une échéance (ex. « Arrivée de la Odin 3 », le 13 nov.), un objectif du jour, la réunion avec sa question et les objectifs chiffrés.
3. « Afficher la scène master sur l'ESP32 » : bandeau « Point sur le master » puis scène labo AR pendant 15 s, avec J-x, l'objectif, les barres et la réunion.

**ESP32**
4. Ouvre Mendeley (ou Google Scholar, ou ton mémoire dans Word) et travaille 2 min : la scène master s'affiche 20 s, puis revient toutes les 5 min. Dans l'app, « en cours » apparaît à côté du temps du jour.
5. « Marquer comme fait » dans l'app : bandeau « Objectif du jour atteint. Bien joué. », mascotte contente, case verte.
6. Laisse le PC 3 min sans rien toucher : salon calme ; la 3e suggestion (vers 1 min 30) est remplacée 15 s par la carte master.
7. Demain matin, au premier usage du PC : briefing de 60 s.
8. Lance un jeu ou une vidéo : la scène master ne s'affiche jamais par-dessus.

**App**
9. Lance une vidéo YouTube : la carte Cinéma apparaît sur l'Accueil ; ⏪ / ⏩ font -10 s / +10 s, lecture-pause marche, plein écran et sous-titres aussi. Même chose sur Anime-Sama et VLC.
10. Accueil → « Mes jeux » : la semaine, le temps par jeu (RDR2, AO Tennis 2…). Pendant un jeu, « Ce n'est pas un jeu » le retire. Ajoute ou retire un .exe dans les listes.
11. Réglages → « Notification PC inutilisé » → active-la (Android demande l'autorisation des notifications → Autoriser) → « Tester maintenant » : une notification « Test : PC inutilisé depuis … » arrive avec un bouton « Éteindre » (n'appuie pas dessus pendant le test, sinon le compte à rebours d'arrêt démarre ; on peut l'annuler dans l'app).
12. Sur Xiaomi, pour que la vérification en arrière-plan soit fiable : Paramètres → Applications → Dadou → Économiseur de batterie → « Aucune restriction », et « Démarrage automatique » activé.
13. Laisse le PC 30 min sans y toucher (sans jeu ni vidéo) : une seule notification « PC inutilisé depuis 30 min » dans les 15 min qui suivent.
14. Si quelque chose ne marche pas : envoie-moi les lignes `[agent] …` de `agent.log`, `erreur.txt` de la carte, et une capture de l'écran concerné.
