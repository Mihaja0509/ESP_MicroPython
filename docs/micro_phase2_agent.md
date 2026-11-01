# Micro — Phase 2 : le programme PC (agent)

- Date : 2026-11-01
- Statut : à appliquer
- Étape : « Télécommande PC » — étape 2 (programme PC)
- Basée sur : docs/etat_code.md (fin de Phase 1, esp/main.py de 102 lignes)

## Ce que contient la phase

Un programme Python qui tourne sur ton PC et qui parle à l'ESP32 par le câble USB :

- **Chaque seconde**, il envoie à l'ESP32 la charge du processeur, la mémoire, le volume et la batterie.
- **Il surveille** et prévient l'ESP32 quand :
  - la sortie audio change (casque Bluetooth connecté ou déconnecté) ;
  - une manette est branchée ou débranchée ;
  - le PC est verrouillé ou déverrouillé.
  Ce sont ces événements qui feront réagir ta mascotte (casque sur les oreilles, pensée « jeu vidéo », sommeil…).
- **Il exécute** ce qu'un faux clavier ne sait pas faire : ouvrir une app, régler la luminosité, verrouiller, éteindre l'écran, mettre en veille, éteindre le PC (avec 60 s pour annuler).
- Pour l'instant tu tapes les commandes dans sa fenêtre. À la phase suivante, elles viendront de l'app Flutter, par l'ESP32.
- L'écran de l'ESP32 affiche les valeurs reçues (affichage simple : le joli tableau de bord animé viendra à la phase « mascotte »).

⚠️ Tant que l'agent tourne, il occupe le port COM4 : ferme-le (q) avant d'utiliser mpremote ou pc_test.py.

## Partie 1 — Nouveaux fichiers

### 1.1 `tools/agent/agent_pc.py`

```python
#!/usr/bin/env python3
"""Programme PC de la Télécommande ESP32 (Windows).

- Envoie chaque seconde à l'ESP32 : CPU, RAM, volume, batterie (ligne « STAT »).
- Surveille et signale : sortie audio (casque ou haut-parleurs), manette, PC verrouillé
  (lignes « EVT »).
- Exécute les commandes « PC » : ouvrir une app, luminosité, verrouiller, écran éteint,
  veille, arrêt. Les autres commandes (KEY, TEXT, VOL+, MOUSE…) sont transmises à l'ESP32.

Utilisation (dans le dossier Micro) :
  py -X utf8 tools\\agent\\agent_pc.py            port trouvé tout seul
  py -X utf8 tools\\agent\\agent_pc.py --port COM4
"""
import argparse
import ctypes
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil
import serial
from serial.tools import list_ports

try:
    import screen_brightness_control as sbc
except ImportError:
    sbc = None

try:
    import comtypes
    from pycaw.pycaw import AudioUtilities
except ImportError:
    comtypes = None
    AudioUtilities = None

DOSSIER = Path(__file__).resolve().parent
FICHIER_APPS = DOSSIER / "apps.json"
APPS_DEFAUT = {
    "spotify": "spotify:",
    "youtube": "https://www.youtube.com",
    "explorateur": "explorer",
    "calculatrice": "calc",
    "bloc-notes": "notepad",
    "vscode": "code",
}
# Une sortie audio dont le nom contient un de ces mots = haut-parleurs du PC.
# Toute autre sortie = casque / enceinte externe.
MOTS_HAUT_PARLEURS = ("speaker", "haut-parleur", "realtek", "display audio")

AIDE = """Commandes PC :
  APPS                  liste des apps   |  APP spotify    ouvre une app
  LUM 70  LUM+  LUM-    luminosité de l'écran du PC
  VERROU                verrouille        |  ECRAN_OFF      verrouille + éteint l'écran
  VEILLE                mise en veille    |  ARRET          arrêt dans 60 s  |  ANNULER
  ETAT                  affiche ce que l'agent envoie à l'ESP32
Toute autre commande (KEY win+d, TEXT …, VOL+, MOUSE 100 0, CLIC…) part à l'ESP32.
  q                     quitter"""


# --------------------------------------------------------------------------
# Liaison série avec l'ESP32
# --------------------------------------------------------------------------
class Liaison:
    def __init__(self, port_force=None):
        self.port_force = port_force
        self.ser = None
        self.verrou = threading.Lock()

    def trouver_port(self):
        if self.port_force:
            return self.port_force
        for p in list_ports.comports():
            if p.vid == 0x303A:  # Espressif
                return p.device
        return None

    def connecter(self):
        port = self.trouver_port()
        if port is None:
            return False
        try:
            self.ser = serial.Serial(port, 115200, timeout=0.2)
            print(f"[agent] ESP32 connectée sur {port}")
            return True
        except serial.SerialException as e:
            print(f"[agent] impossible d'ouvrir {port} : {e}")
            self.ser = None
            return False

    def envoyer(self, ligne):
        with self.verrou:
            if self.ser is None:
                return False
            try:
                self.ser.write((ligne.strip() + "\n").encode())
                return True
            except serial.SerialException:
                print("[agent] liaison perdue")
                self.ser = None
                return False

    def lire_ligne(self):
        ser = self.ser
        if ser is None:
            return None
        try:
            return ser.readline().decode(errors="ignore").strip()
        except serial.SerialException:
            self.ser = None
            return None


# --------------------------------------------------------------------------
# Mesures du PC
# --------------------------------------------------------------------------
def _volume_endpoint():
    dev = AudioUtilities.GetSpeakers()
    ev = getattr(dev, "EndpointVolume", None)  # pycaw récent
    if ev is not None:
        return ev
    from ctypes import POINTER, cast  # ancien pycaw
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import IAudioEndpointVolume
    itf = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(itf, POINTER(IAudioEndpointVolume))


def volume():
    if AudioUtilities is None:
        return -1
    try:
        return round(_volume_endpoint().GetMasterVolumeLevelScalar() * 100)
    except Exception:
        return -1


def sortie_audio():
    """Nom de la sortie audio par défaut ('' si inconnu)."""
    if AudioUtilities is None:
        return ""
    try:
        dev = AudioUtilities.GetSpeakers()
        nom = getattr(dev, "FriendlyName", None)
        if nom:
            return nom
        ident = dev.GetId()
        for d in AudioUtilities.GetAllDevices():
            if d.id == ident:
                return d.FriendlyName or ""
    except Exception:
        pass
    return ""


def est_casque(nom):
    if not nom:
        return False
    bas = nom.lower()
    return not any(m in bas for m in MOTS_HAUT_PARLEURS)


class _XGamepad(ctypes.Structure):
    _fields_ = [("wButtons", ctypes.c_ushort), ("bLeftTrigger", ctypes.c_ubyte),
                ("bRightTrigger", ctypes.c_ubyte), ("sThumbLX", ctypes.c_short),
                ("sThumbLY", ctypes.c_short), ("sThumbRX", ctypes.c_short),
                ("sThumbRY", ctypes.c_short)]


class _XState(ctypes.Structure):
    _fields_ = [("dwPacketNumber", ctypes.c_uint), ("Gamepad", _XGamepad)]


_xinput = None
for _nom in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
    try:
        _xinput = getattr(ctypes.windll, _nom)
        break
    except (OSError, AttributeError):
        _xinput = None


def manette_connectee():
    """True si une manette compatible XInput (Xbox et la plupart des manettes PC) est branchée."""
    if _xinput is None:
        return False
    etat = _XState()
    for i in range(4):
        if _xinput.XInputGetState(i, ctypes.byref(etat)) == 0:
            return True
    return False


def pc_verrouille():
    u = ctypes.windll.user32
    u.OpenInputDesktop.restype = ctypes.c_void_p
    h = u.OpenInputDesktop(0, False, 0x0100)
    if not h:
        return True
    ok = u.SwitchDesktop(ctypes.c_void_p(h))
    u.CloseDesktop(ctypes.c_void_p(h))
    return not ok


def batterie():
    b = psutil.sensors_battery()
    if b is None:
        return -1, 0
    return round(b.percent), 1 if b.power_plugged else 0


# --------------------------------------------------------------------------
# Commandes PC
# --------------------------------------------------------------------------
def charger_apps():
    if not FICHIER_APPS.exists():
        FICHIER_APPS.write_text(json.dumps(APPS_DEFAUT, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    return json.loads(FICHIER_APPS.read_text(encoding="utf-8"))


def luminosite_actuelle():
    valeurs = sbc.get_brightness()
    return valeurs[0] if isinstance(valeurs, list) else valeurs


def regler_luminosite(valeur):
    valeur = max(0, min(100, int(valeur)))
    sbc.set_brightness(valeur)
    return valeur


def executer_pc(ligne):
    """Exécute une commande PC. Renvoie un texte, ou None si ce n'est pas une commande PC."""
    mots = ligne.split(" ", 1)
    cmd = mots[0].upper()
    arg = mots[1].strip() if len(mots) > 1 else ""

    if cmd == "APPS":
        return "Apps : " + ", ".join(charger_apps().keys())
    if cmd == "APP":
        apps = charger_apps()
        cible = apps.get(arg.lower())
        if cible is None:
            return f"App inconnue : {arg} (ajoute-la dans {FICHIER_APPS})"
        subprocess.Popen(f'start "" "{cible}"', shell=True)
        return f"Ouverture : {arg}"
    if cmd in ("LUM", "LUM+", "LUM-"):
        if sbc is None:
            return "screen_brightness_control n'est pas installé"
        try:
            if cmd == "LUM":
                v = regler_luminosite(arg)
            else:
                pas = 10 if cmd == "LUM+" else -10
                v = regler_luminosite(luminosite_actuelle() + pas)
        except Exception as e:
            return f"Luminosité impossible : {e}"
        return f"Luminosité : {v} %"
    if cmd == "VERROU":
        ctypes.windll.user32.LockWorkStation()
        return "PC verrouillé"
    if cmd == "ECRAN_OFF":
        ctypes.windll.user32.LockWorkStation()
        time.sleep(0.5)
        ctypes.windll.user32.PostMessageW(0xFFFF, 0x0112, 0xF170, 2)
        return "Écran éteint"
    if cmd == "VEILLE":
        subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return "Mise en veille"
    if cmd == "ARRET":
        subprocess.Popen("shutdown /s /t 60", shell=True)
        return "Arrêt dans 60 s (ANNULER pour annuler)"
    if cmd == "ANNULER":
        subprocess.Popen("shutdown /a", shell=True)
        return "Arrêt annulé"
    return None


# --------------------------------------------------------------------------
# Boucles
# --------------------------------------------------------------------------
class Agent:
    def __init__(self, liaison):
        self.liaison = liaison
        self.actif = True
        self.dernier_stat = ""
        self.precedent = {}

    def boucle_mesures(self):
        if comtypes is not None:
            comtypes.CoInitialize()
        psutil.cpu_percent(interval=None)
        while self.actif:
            if self.liaison.ser is None:
                if not self.liaison.connecter():
                    time.sleep(3)
                    continue
                self.precedent = {}  # renvoie tous les états après reconnexion
            cpu = round(psutil.cpu_percent(interval=None))
            ram = round(psutil.virtual_memory().percent)
            bat, charge = batterie()
            self.dernier_stat = f"STAT {cpu} {ram} {volume()} {bat} {charge}"
            self.liaison.envoyer(self.dernier_stat)

            nom = sortie_audio()
            etats = {
                "CASQUE": nom if est_casque(nom) else "-",
                "MANETTE": "1" if manette_connectee() else "0",
                "VERROU": "1" if pc_verrouille() else "0",
            }
            for cle, valeur in etats.items():
                if self.precedent.get(cle) != valeur:
                    self.precedent[cle] = valeur
                    self.liaison.envoyer(f"EVT {cle} {valeur}")
                    print(f"[agent] événement : {cle} = {valeur}")
            time.sleep(1)

    def boucle_lecture(self):
        while self.actif:
            ligne = self.liaison.lire_ligne()
            if ligne is None:
                time.sleep(0.5)
                continue
            if ligne and ligne != "OK":
                print(f"[esp32] {ligne}")

    def console(self):
        print(AIDE)
        while self.actif:
            try:
                ligne = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not ligne:
                continue
            if ligne.lower() == "q":
                break
            if ligne.upper() == "ETAT":
                print(self.dernier_stat, self.precedent)
                continue
            reponse = executer_pc(ligne)
            if reponse is not None:
                print(reponse)
            elif not self.liaison.envoyer(ligne):
                print("ESP32 non connectée")
        self.actif = False


def main():
    if sys.platform != "win32":
        sys.exit("Ce programme est fait pour Windows.")
    parser = argparse.ArgumentParser(description="Agent PC de la Télécommande ESP32")
    parser.add_argument("--port", help="port série de l'ESP32 (sinon trouvé tout seul)")
    args = parser.parse_args()

    agent = Agent(Liaison(args.port))
    threading.Thread(target=agent.boucle_mesures, daemon=True).start()
    threading.Thread(target=agent.boucle_lecture, daemon=True).start()
    agent.console()


if __name__ == "__main__":
    main()
```

## Partie 2 — Fichiers remplacés en entier

Aucun.

## Partie 3 — Modifications « avant → après »

### Modification 1 — `esp/main.py` (variables d'état)

Avant :

```python
derniere = "-"
nb = 0
```

Après :

```python
derniere = "-"
nb = 0
# Valeurs envoyées par le programme PC (agent_pc.py)
stat = {"cpu": -1, "ram": -1, "vol": -1, "bat": -1, "chg": 0}
evt = {"casque": "", "manette": 0, "verrou": 0}
```

### Modification 2 — `esp/main.py` (affichage des valeurs)

Avant :

```python
    ecran.texte("Commandes : %d" % nb, 10, 130, lcd.ORANGE, 1)
    ecran.texte("tools/pc_test.py sur le PC", 10, 150, lcd.GRIS, 1)
```

Après :

```python
    ecran.texte("CPU %d%%  RAM %d%%  Vol %d%%" % (stat["cpu"], stat["ram"], stat["vol"]),
                10, 118, lcd.ORANGE, 1)
    ecran.texte("Batterie %d%%%s" % (stat["bat"], " (en charge)" if stat["chg"] else ""),
                10, 132, lcd.ORANGE, 1)
    ecran.texte("Casque : " + (evt["casque"][:30] or "non"), 10, 146, lcd.CYAN, 1)
    ecran.texte("Manette : %s   Verrou : %s" % ("oui" if evt["manette"] else "non",
                                                "oui" if evt["verrou"] else "non"),
                10, 160, lcd.CYAN, 1)
```

### Modification 3 — `esp/main.py` (réception de STAT et EVT)

Avant :

```python
    if cmd == "PING":
        return "PONG"
```

Après :

```python
    if cmd == "PING":
        return "PONG"
    if cmd == "STAT":
        try:
            v = [int(x) for x in arg.split()]
            stat["cpu"], stat["ram"], stat["vol"], stat["bat"], stat["chg"] = v[:5]
        except ValueError:
            return "ERR utilise : STAT cpu ram vol bat charge"
        return "OK"
    if cmd == "EVT":
        morceaux = arg.split(" ", 1)
        typ = morceaux[0].upper()
        val = morceaux[1].strip() if len(morceaux) > 1 else ""
        if typ == "CASQUE":
            evt["casque"] = "" if val in ("", "-") else val
        elif typ == "MANETTE":
            evt["manette"] = 1 if val == "1" else 0
        elif typ == "VERROU":
            evt["verrou"] = 1 if val == "1" else 0
        else:
            return "ERR evenement inconnu : " + typ
        return "OK"
```

### Modification 4 — `esp/main.py` (« dernière commande » sans STAT/EVT)

Avant :

```python
        nb += 1
        derniere = ligne.strip()
```

Après :

```python
        if not ligne.startswith(("STAT", "EVT")):
            nb += 1
            derniere = ligne.strip()
```

## Dépendances (PC)

`py -m pip install --user -U psutil pycaw comtypes screen-brightness-control` (pyserial est déjà installé).

`tools/agent/apps.json` est créé au premier lancement avec : spotify, youtube, explorateur, calculatrice, bloc-notes, vscode. Tu pourras y ajouter tes apps (nom → commande, chemin d'un .exe ou lien).

## Comprendre le code

- L'agent a trois fils d'exécution en parallèle :
  - `boucle_mesures` : toutes les secondes, il mesure et envoie `STAT …`, puis compare les états (casque, manette, verrou) à ceux d'avant. Il n'envoie un `EVT …` que si quelque chose a changé.
  - `boucle_lecture` : il affiche ce que répond l'ESP32 (sauf les « OK »).
  - `console` : il lit tes commandes. Si c'est une commande PC (`APP`, `LUM`, `VEILLE`…), il l'exécute lui-même, sinon il la transmet à l'ESP32 (`KEY`, `TEXT`, `VOL+`…).
- Casque : on regarde le nom de la sortie audio par défaut de Windows. Si ce n'est pas un haut-parleur interne (« Speakers », « Haut-parleurs », « Realtek »), on considère que c'est un casque ou une enceinte. Si ton casque n'est pas reconnu ou si tes haut-parleurs sont pris pour un casque, on ajustera la liste `MOTS_HAUT_PARLEURS`.
- Manette : on interroge XInput, l'interface des manettes Xbox (la plupart des manettes PC, filaires ou Bluetooth, l'utilisent).
- Côté ESP32, `main.py` range les valeurs reçues dans `stat` et `evt` et les affiche.

## Liste de contrôle

| Contrôle | Attendu |
|---|---|
| 4 blocs « avant » trouvés une seule fois dans esp/main.py | oui |
| `py -m py_compile tools\agent\agent_pc.py` | aucune erreur |
| Dépendances installées | psutil, pycaw, comtypes, screen-brightness-control (versions notées) |
| Copie de main.py sur la carte + reset | OK |
| `py -X utf8 tools\pc_test.py COM4 --cmd "STAT 12 34 56 78 1"` | « OK » |
| `py -X utf8 tools\pc_test.py COM4 --cmd "EVT MANETTE 1"` | « OK » |
| Lancement de l'agent ~10 s, puis q | « ESP32 connectée sur COM… », événements CASQUE / MANETTE / VERROU affichés, aucune trace d'erreur |
| Test Python rapide (sans l'ESP32) : `py -c "import sys; sys.path.insert(0, r'tools\agent'); import agent_pc as a; print(a.volume(), repr(a.sortie_audio()), a.manette_connectee(), a.pc_verrouille(), a.batterie())"` | valeurs plausibles (noter la ligne) |

## Tests sur l'appareil (par Mihaja)

Lance `py -X utf8 tools\agent\agent_pc.py` dans le dossier Micro.

1. L'écran de l'ESP32 affiche CPU, RAM, volume et batterie, mis à jour chaque seconde. Change le volume du PC : la valeur suit.
2. `APP calculatrice`, puis `APP youtube` → les apps s'ouvrent.
3. `LUM 30`, puis `LUM+`, puis `LUM 80` → la luminosité du PC change.
4. Connecte ton casque Bluetooth → l'agent écrit « événement : CASQUE = nom du casque » et l'écran de l'ESP32 le montre. Déconnecte-le → « CASQUE = - ».
5. Si tu as une manette : branche-la ou connecte-la → « MANETTE = 1 ».
6. `VERROU` → le PC se verrouille ; sur l'ESP32, « Verrou : oui ». Déverrouille → « non ».
7. `ECRAN_OFF` → l'écran du PC s'éteint ; bouge la souris et tape ton code pour revenir.
8. Les commandes de la Phase 1 marchent toujours depuis l'agent : `VOL+`, `KEY win+d`.
9. (Facultatif) `ARRET` puis `ANNULER` tout de suite → une notification d'arrêt apparaît puis disparaît.
10. Envoie-moi ce qui marche, ce qui ne marche pas, et le nom affiché pour ton casque.
