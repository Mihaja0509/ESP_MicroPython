# Micro — Phase 11-ter : veille en jeu, filet de sécurité, journal des scènes, vraie pluie, sortie du cinéma

Date : 2026-11-04 · Statut : à appliquer · Base : commit c9e5437 (« Phase 11-bis »). Les blocs « avant » sont copiés du dépôt GitHub à ce commit (textes déjà traduits en anglais).

## Ce que contient la phase

1. **ESP32 « en veille » pendant un jeu** (diagnostic du 04/11 avec py-spy) : la boucle de mesures de l'agent passait la plupart de son temps dans pycaw. Chaque seconde, `sortie_audio()` demandait à Windows la liste de **tous** les appareils audio avec leurs propriétés (`GetAllDevices`). Quatre fois par seconde, `volume()` recréait l'appareil audio. Pendant un jeu, le son de Windows est très occupé ; si ces appels bloquent plus de 12 s, aucune ligne STAT ne part, et l'ESP32 affiche « PC asleep ». Correctifs :
   - **nouveau fil `LecteurAudio`** : volume et niveau sonore toutes les 0,5 s, casque toutes les 2 s, dans son propre fil. La boucle des mesures ne parle plus jamais au son de Windows ;
   - le volume garde son lien avec Windows 10 s au lieu de le recréer 4 fois par seconde ;
   - le casque est lu sur l'appareil par défaut seulement (pycaw récent), plus sur toute la liste ;
   - le journal signale « son de Windows lent : X s » au plus une fois par minute.
2. **Filet de sécurité** (`boucle_secours`) : si la boucle des mesures a plus de 2 s de retard, pour quelque raison que ce soit, les dernières lignes STAT, GPU et PERF sont renvoyées chaque seconde. Tant que l'agent tourne, l'ESP32 ne s'endort plus. Le journal le signale au plus une fois par minute.
3. **Journal des scènes** : à chaque changement de scène, l'ESP32 envoie `MODE nouvelle <- ancienne (durée)`, que l'agent écrit dans `agent.log` (`[esp32] MODE absent <- jeu (95 s)`). La prochaine fois, on saura tout de suite ce qui s'est passé.
4. **Vraie pluie** : l'agent demande aussi la **météo actuelle** à Open-Meteo et envoie `METEO_NOW icone 0|1`. « It's raining: windows closed? » ne s'affiche que s'il pleut **maintenant**. « Rain around X » seulement si X est **après** l'heure actuelle et que la probabilité est d'au moins 40 %. La météo est mise à jour toutes les 15 min (au lieu de 30).
5. **Sortie du cinéma** : quand la fenêtre de la vidéo n'est plus au premier plan, retour à la scène normale en **~2 s** (au lieu d'environ 16 s). Une vidéo **en pause** que Windows connaît (barre d'avancement) reste au cinéma tant que sa fenêtre est devant, avec « Pause ».
6. **Fenêtre d'autorisation administrateur ≠ verrouillage** : elle change de bureau quelques secondes (vu le 04/11 à 11:03 : VERROU = 1 pendant 5 s). Le verrouillage n'est maintenant compté qu'après 4 s de suite, et jamais si `consent.exe` (UAC) est ouvert.

## Partie 1 — Modifications « avant → après » (exactes, dans l'ordre)

### Modification 1 — `tools/agent/agent_pc.py`

Le casque est lu sur l'appareil par défaut (pycaw récent : déjà complet), plus sur la liste de tous les appareils audio.

**Avant :**

```python
    dev = AudioUtilities.GetSpeakers()
    ident = getattr(dev, "id", None)
```

**Après :**

```python
    dev = AudioUtilities.GetSpeakers()
    if getattr(dev, "FriendlyName", None) is not None:
        return dev  # pycaw récent : GetSpeakers donne déjà l'appareil complet (pas besoin de GetAllDevices)
    ident = getattr(dev, "id", None)
```

### Modification 2 — `tools/agent/agent_pc.py`

Ancien pycaw : pointeur COM gardé par QueryInterface (le volume est maintenant gardé 10 s).

**Avant :**

```python
    from ctypes import POINTER, cast  # ancien pycaw
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import IAudioEndpointVolume
    itf = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(itf, POINTER(IAudioEndpointVolume))
```

**Après :**

```python
    from comtypes import CLSCTX_ALL  # ancien pycaw
    from pycaw.pycaw import IAudioEndpointVolume
    itf = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return itf.QueryInterface(IAudioEndpointVolume)
```

### Modification 3 — `tools/agent/agent_pc.py`

Le niveau sonore est mesuré par le fil audio ; son_en_cours() lit seulement le dernier résultat.

**Avant :**

```python
def son_en_cours():
    """Vrai si la sortie audio joue du son ; None si on ne peut pas le savoir (pycaw absent)."""
```

**Après :**

```python
_SON_MESURE = {"v": None, "t": 0.0}   # Phase 11-ter : rempli par le fil audio (LecteurAudio)


def son_en_cours():
    """Dernier résultat du fil audio (moins de 3 s) : True / False, ou None si inconnu."""
    if time.time() - _SON_MESURE["t"] > 3:
        return None
    return _SON_MESURE["v"]


def mesurer_son():
    """Vrai si la sortie audio joue du son ; None si on ne peut pas le savoir (pycaw absent)."""
```

### Modification 4 — `tools/agent/agent_pc.py`

Constante : sortie rapide du cinéma quand la fenêtre vidéo n'est plus au premier plan.

**Avant :**

```python
VIDEO_TOLERANCE = 8      # … et la scène cinéma reste 8 s après (pause courte, épisode suivant)
```

**Après :**

```python
VIDEO_TOLERANCE = 8      # … et la scène cinéma reste 8 s après (pause courte, épisode suivant)
VIDEO_SORTIE = 2         # Phase 11-ter : fenêtre vidéo quittée -> retour à la scène normale en 2 s
```

### Modification 5 — `tools/agent/agent_pc.py`

Cinéma : une vidéo en pause que Windows connaît reste au cinéma ; fenêtre quittée -> sortie en 2 s.

**Avant :**

```python
    def video(self):
        """« Source|Titre » (texte pour l'ESP32) ou '' si aucune vidéo."""
        maintenant = time.time()
        source, titre = video_premier_plan()
        son = son_en_cours()
        if son or son is None:
            self.son_vu = maintenant
        if source and maintenant - self.son_vu < VIDEO_SON:
```

**Après :**

```python
    def video(self, media=None):
        """« Source|Titre » (texte pour l'ESP32) ou '' si aucune vidéo.
        media : lecture des contrôles multimédias de Windows (une vidéo en pause y est encore)."""
        maintenant = time.time()
        source, titre = video_premier_plan()
        son = son_en_cours()
        if son or son is None:
            self.son_vu = maintenant
        connue = bool(media) and media.get("duree", 0) > 0
        if source and (maintenant - self.son_vu < VIDEO_SON or connue):
```

### Modification 6 — `tools/agent/agent_pc.py`

Tolérance : longue seulement si la fenêtre vidéo est toujours devant (petite pause sans son).

**Avant :**

```python
            if maintenant - self.perdue < VIDEO_TOLERANCE:
                return self.actuelle
```

**Après :**

```python
            # fenêtre vidéo quittée : sortie rapide ; même fenêtre sans son : petite pause tolérée
            if maintenant - self.perdue < (VIDEO_TOLERANCE if source else VIDEO_SORTIE):
                return self.actuelle
```

### Modification 7 — `tools/agent/agent_pc.py`

Nouveau fil audio (LecteurAudio), placé juste avant StatsJeux.

**Avant :**

```python
class StatsJeux:
```

**Après :**

```python
class LecteurAudio:
    """Phase 11-ter : sortie audio (casque), volume et niveau sonore lus dans un fil à part.
    Pendant un jeu, Windows peut mettre plusieurs secondes à répondre (pycaw) : avant, ça bloquait
    la boucle des mesures et l'ESP32 ne recevait plus rien pendant plus de 12 s (« PC asleep »)."""

    def __init__(self):
        self.sortie = ("", False)   # (nom, externe)
        self.volume = -1
        if AudioUtilities is not None:
            threading.Thread(target=self._fil, daemon=True).start()

    def _fil(self):
        if comtypes is not None:
            comtypes.CoInitialize()
        endpoint, endpoint_t, sortie_t, signale = None, 0.0, 0.0, 0.0
        while True:
            debut = time.time()
            try:
                if endpoint is None or debut - endpoint_t > 10:  # gardé 10 s (suit casque <-> HP)
                    endpoint, endpoint_t = _volume_endpoint(), debut
                self.volume = round(endpoint.GetMasterVolumeLevelScalar() * 100)
            except Exception:
                endpoint, self.volume = None, -1
            _SON_MESURE["v"] = mesurer_son()
            _SON_MESURE["t"] = time.time()
            if debut - sortie_t >= 2:
                sortie_t = debut
                self.sortie = sortie_audio()
            duree = time.time() - debut
            if duree > 3 and time.time() - signale > 60:
                signale = time.time()
                print(f"[agent] son de Windows lent : {duree:.1f} s (sans effet sur l'ESP32)")
            time.sleep(max(0.1, 0.5 - duree))


class StatsJeux:
```

### Modification 8 — `tools/agent/agent_pc.py`

Fenêtre d'autorisation administrateur (UAC) : pas un verrouillage.

**Avant :**

```python
class _LASTINPUTINFO(ctypes.Structure):
```

**Après :**

```python
def uac_ouvert():
    """Vrai si la fenêtre d'autorisation administrateur (consent.exe) est ouverte."""
    try:
        return any((p.info["name"] or "").lower() == "consent.exe" for p in psutil.process_iter(["name"]))
    except psutil.Error:
        return False


class _LASTINPUTINFO(ctypes.Structure):
```

### Modification 9 — `tools/agent/agent_pc.py`

Open-Meteo : on demande aussi la météo actuelle.

**Avant :**

```python
             "&hourly=precipitation_probability&timezone=auto&forecast_days=2")
```

**Après :**

```python
             "&hourly=precipitation_probability&current=weather_code,precipitation"
             "&timezone=auto&forecast_days=2")
```

### Modification 10 — `tools/agent/agent_pc.py`

Météo actuelle gardée par la classe Meteo.

**Avant :**

```python
        self.version = 0          # augmente à chaque nouvelle météo
```

**Après :**

```python
        self.version = 0          # augmente à chaque nouvelle météo
        self.actuel = None        # Phase 11-ter : (icône, il pleut maintenant 0/1)
```

### Modification 11 — `tools/agent/agent_pc.py`

Météo mise à jour toutes les 15 min (la météo actuelle change plus vite que la prévision).

**Avant :**

```python
        attente = 1800 if self.jours else 300  # 30 min, ou 5 min tant qu'on n'a rien
```

**Après :**

```python
        attente = 900 if self.jours else 300  # 15 min, ou 5 min tant qu'on n'a rien
```

### Modification 12 — `tools/agent/agent_pc.py`

Lecture de la météo actuelle.

**Avant :**

```python
            self.jours = self._lire(d)
```

**Après :**

```python
            self.jours = self._lire(d)
            self.actuel = self._lire_actuel(d)
```

### Modification 13 — `tools/agent/agent_pc.py`

Ligne METEO_NOW envoyée à l'ESP32 avec les deux jours.

**Avant :**

```python
    def lignes(self):
        return [f"METEO_J {i} {ic} {tmax} {tmin} {pluie} {heure}"
                for i, (ic, tmax, tmin, pluie, heure) in enumerate(self.jours)]
```

**Après :**

```python
    @staticmethod
    def _lire_actuel(d):
        """(icône, 1 s'il pleut maintenant sinon 0) d'après la météo actuelle, ou None."""
        c = d.get("current") or {}
        if "weather_code" not in c:
            return None
        code = int(c.get("weather_code") or 0)
        pluie = (c.get("precipitation") or 0) > 0.05 or 51 <= code <= 67 or 80 <= code <= 82 or code >= 95
        return icone_meteo(code), 1 if pluie else 0

    def lignes(self):
        lignes = [f"METEO_J {i} {ic} {tmax} {tmin} {pluie} {heure}"
                  for i, (ic, tmax, tmin, pluie, heure) in enumerate(self.jours)]
        if self.actuel:
            lignes.append(f"METEO_NOW {self.actuel[0]} {self.actuel[1]}")
        return lignes
```

### Modification 14 — `tools/agent/agent_pc.py`

L'agent démarre le fil audio et note l'heure du dernier envoi à l'ESP32.

**Avant :**

```python
        self.video_pos = None
```

**Après :**

```python
        self.video_pos = None
        self.audio = LecteurAudio()          # Phase 11-ter : son lu à part
        self.dernier_envoi = time.time()     # dernier envoi STAT par la boucle des mesures
        self.verrou_depuis = 0.0
```

### Modification 15 — `tools/agent/agent_pc.py`

Boucle rapide : le volume vient du fil audio (plus d'appel à Windows ici) ; heure du dernier envoi.

**Avant :**

```python
        vol = self._garder("vol", volume(), 10)
        bat, charge = self.lent["bat"]
        self.dernier_stat = f"STAT {cpu} {ram} {vol} {bat} {charge}"
        self.liaison.envoyer(self.dernier_stat)
```

**Après :**

```python
        vol = self._garder("vol", self.audio.volume, 10)
        bat, charge = self.lent["bat"]
        self.dernier_stat = f"STAT {cpu} {ram} {vol} {bat} {charge}"
        self.liaison.envoyer(self.dernier_stat)
        self.dernier_envoi = time.time()
```

### Modification 16 — `tools/agent/agent_pc.py`

Verrouillage confirmé après 4 s (et pas pendant la fenêtre administrateur), filet de sécurité.

**Avant :**

```python
    def _mesures_lentes(self):
```

**Après :**

```python
    def _verrou_stable(self):
        """Verrouillé seulement après 4 s de suite, et jamais pendant la fenêtre d'autorisation
        administrateur (UAC) : elle change aussi de bureau, ce n'est pas un verrouillage."""
        if not pc_verrouille():
            self.verrou_depuis = 0.0
            return False
        if not self.verrou_depuis:
            self.verrou_depuis = time.time()
        return time.time() - self.verrou_depuis >= 4 and not uac_ouvert()

    def boucle_secours(self):
        """Phase 11-ter : si la boucle des mesures prend du retard, renvoie les dernières valeurs
        chaque seconde. Tant que l'agent tourne, l'ESP32 ne croit jamais que le PC dort."""
        signale = 0.0
        while self.actif:
            time.sleep(1)
            retard = time.time() - self.dernier_envoi
            if retard > 2 and self.dernier_stat:
                for ligne in (self.dernier_stat, self.dernier_gpu, self.dernier_perf):
                    if ligne:
                        self.liaison.envoyer(ligne)
                if retard > 5 and time.time() - signale > 60:
                    signale = time.time()
                    print(f"[agent] boucle des mesures en retard de {retard:.0f} s : "
                          "dernières valeurs renvoyées à l'ESP32")

    def _mesures_lentes(self):
```

### Modification 17 — `tools/agent/agent_pc.py`

Mesures lentes : casque lu par le fil audio, verrou stable, vidéo avec les contrôles multimédias.

**Avant :**

```python
        nom, externe = sortie_audio()
        jeu = self.jeux.jeu(gpu()[1])
        verrou = pc_verrouille()
        # Phase 10 : vidéo au premier plan, PC allumé mais inutilisé (en minutes, 0 = utilisé)
        video = "" if (jeu or verrou) else self.video.video()
        # Phase 11-bis : position de la vidéo (contrôles multimédias de Windows)
        media = self.media.actuel() if video else None
```

**Après :**

```python
        nom, externe = self.audio.sortie
        jeu = self.jeux.jeu(gpu()[1])
        verrou = self._verrou_stable()
        # Phase 10 : vidéo au premier plan, PC allumé mais inutilisé (en minutes, 0 = utilisé)
        media_brut = None if (jeu or verrou) else self.media.actuel()
        video = "" if (jeu or verrou) else self.video.video(media_brut)
        # Phase 11-bis : position de la vidéo (contrôles multimédias de Windows)
        media = media_brut if video else None
```

### Modification 18 — `tools/agent/agent_pc.py`

Démarrage du filet de sécurité.

**Avant :**

```python
    threading.Thread(target=agent.boucle_mesures, daemon=True).start()
```

**Après :**

```python
    threading.Thread(target=agent.boucle_mesures, daemon=True).start()
    threading.Thread(target=agent.boucle_secours, daemon=True).start()  # Phase 11-ter
```

### Modification 19 — `esp/main.py`

Météo actuelle gardée dans l'état.

**Avant :**

```python
        "master": None}        # Phase 11 : données du master (ligne MASTER du PC)
```

**Après :**

```python
        "master": None,        # Phase 11 : données du master (ligne MASTER du PC)
        "meteo_now": None}     # Phase 11-ter : météo actuelle {icone, pluie}
```

### Modification 20 — `esp/main.py`

Lecture de METEO_NOW.

**Avant :**

```python
    if cmd == "METEO_J":
```

**Après :**

```python
    if cmd == "METEO_NOW":
        # météo actuelle envoyée par le PC : METEO_NOW icone pluie (1 = il pleut maintenant)
        try:
            p = arg.split()
            etat["meteo_now"] = {"icone": p[0], "pluie": int(p[1]) == 1}
        except (ValueError, IndexError):
            return "ERR utilise : METEO_NOW icone pluie"
        return "OK"
    if cmd == "METEO_J":
```

### Modification 21 — `esp/lib/ui.py`

Pluie : « il pleut » seulement s'il pleut maintenant ; « pluie vers X h » seulement si X est à venir.

**Avant :**

```python
        jours = etat.get("meteo") or []
        if jours:
            j = jours[0]
            if j["icone"] in ("pluie", "orage"):
                liste.insert(0, ("fenetre", "It's raining: windows closed?"))
            elif j["pluie"] >= 40 and j["heure_pluie"] is not None and j["heure_pluie"] >= heure:
```

**Après :**

```python
        jours = etat.get("meteo") or []
        actuel = etat.get("meteo_now")
        if actuel and actuel["pluie"]:  # il pleut maintenant (météo actuelle, pas celle de la journée)
            liste.insert(0, ("fenetre", "It's raining: windows closed?"))
        elif jours:
            j = jours[0]
            if j["pluie"] >= 40 and j["heure_pluie"] is not None and j["heure_pluie"] > heure:
```

### Modification 22 — `esp/lib/ui.py`

Journal des scènes : chaque changement part vers le PC (écrit dans agent.log).

**Avant :**

```python
    def _changer_mode(self, ancien, nouveau, etat, maintenant):
        duree_ancien = self._age(self.mode_depuis, maintenant)
        self.mode = nouveau
        self.mode_depuis = maintenant
```

**Après :**

```python
    def _changer_mode(self, ancien, nouveau, etat, maintenant):
        duree_ancien = self._age(self.mode_depuis, maintenant)
        self.mode = nouveau
        self.mode_depuis = maintenant
        # Phase 11-ter : le PC écrit cette ligne dans agent.log (« [esp32] MODE … »)
        print("MODE %s <- %s (%d s)" % (nouveau, ancien, duree_ancien // 1000))
```

## Copie sur la carte

1. Crée `tools\agent\PAUSE`, attends 2 s.
2. `py -m mpremote devs`, puis copie (relance une fois si `ClearCommError`) : `esp/main.py` → `:main.py`, `esp/lib/ui.py` → `:lib/ui.py`. Vérifie les empreintes SHA-256 des deux fichiers sur la carte. Puis `reset`.
3. Supprime `tools\agent\PAUSE`.
4. Redémarre la tâche (administrateur) : `Stop-ScheduledTask "ESP32 Telecommande Agent"` puis `Start-ScheduledTask "ESP32 Telecommande Agent"`.

## Liste de contrôle

| Contrôle | Attendu |
|---|---|
| Test à blanc : les 22 blocs « avant » | chacun trouvé exactement 1 fois |
| `py -m py_compile` sur agent_pc.py, esp/main.py, esp/lib/ui.py | aucune erreur |
| `grep -n "volume()" tools/agent/agent_pc.py` | seulement la définition `def volume():` (plus d'appel dans la boucle) |
| Empreintes de :main.py et :lib/ui.py sur la carte | identiques aux fichiers locaux |
| Carte : :erreur.txt 30 s après le reset | 1402 octets (inchangé) |
| Tâche après 2 min | Running, `/widget` → 401 |
| agent.log après démarrage | lignes `[esp32] MODE …` (ex. `MODE normal <- eteint`) et `Météo : OK` |

Commit « Phase 11-ter : son lu à part, filet de sécurité, journal des scènes, vraie pluie, sortie du cinéma » (avec docs/micro_phase11_ter.md ; sans docs/etat_micro.md, tools/agent/apps.json, docs/micro_phase6_fichiers.zip, docs/optimiser_pc.*, vlc-help.txt), puis push.

## Tests sur l'appareil (Mihaja)

1. **Jeu** : lance God of War (ou RDR2) et ne touche à rien pendant 5 min. L'ESP32 doit rester en scène jeu tout le temps. Ensuite, Claude Code regarde agent.log : aucune ligne `MODE absent` pendant ces 5 min. Des lignes « son de Windows lent » ou « boucle des mesures en retard » peuvent apparaître : elles confirment simplement que le problème venait de là, et qu'il est maintenant absorbé.
2. **Cinéma** : vidéo YouTube, puis passe sur le Bureau : retour à la scène normale en 2 à 3 s. Reviens sur la vidéo et mets en pause : la scène cinéma reste, avec « Pause ».
3. **Pluie** : quand il ne pleut pas, la scène calme ne dit plus « It's raining ». « Rain around X » seulement si X est plus tard dans la journée.
4. **Fenêtre administrateur** : ouvre un PowerShell administrateur. L'ESP32 ne passe pas en « PC locked ». Verrouille vraiment le PC (Win+L) : « PC locked » apparaît en 4 à 5 s.
5. Si un bug revient : les lignes `[esp32] MODE …` de agent.log autour de l'heure du problème suffiront à le comprendre.
