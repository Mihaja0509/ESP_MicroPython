#!/usr/bin/env python3
"""Programme PC de la Télécommande ESP32 (Windows).

- Envoie chaque seconde à l'ESP32 : CPU, RAM, volume, batterie (ligne « STAT »).
- Envoie chaque seconde la carte graphique NVIDIA : température, charge, mémoire (ligne « GPU »).
- Surveille et signale : sortie audio (casque ou haut-parleurs), manette, PC verrouillé,
  jeu Steam en cours (lignes « EVT »).
- Mode gamer : température du processeur (LibreHardwareMonitor) et FPS du jeu (PresentMon),
  ligne « PERF » chaque seconde.
- Météo d'aujourd'hui et de demain (Open-Meteo) toutes les 30 min, lignes « METEO_J »
  (position dans tools\\agent\\reglages.json).
- Serveur pour l'app Flutter du téléphone (WebSocket, port 8765, voir serveur_app.py) :
  appairage par code affiché sur l'ESP32, souris / texte directement sur le PC, état 4 fois / s.
- Mesures envoyées 4 fois par seconde (CPU, RAM, volume, GPU, FPS) pour un écran plus vif.
- Envoie l'heure du PC (ligne « TEMPS ») à la connexion puis chaque minute.
- Prévient l'ESP32 de chaque commande PC exécutée (« EVT ACTION … ») pour que la mascotte réagisse.
- Exécute les commandes « PC » : ouvrir une app, luminosité, verrouiller, écran éteint,
  veille, arrêt. Les autres commandes (KEY, TEXT, VOL+, MOUSE…) sont transmises à l'ESP32.

Utilisation (dans le dossier Micro) :
  py -X utf8 tools\\agent\\agent_pc.py            port trouvé tout seul, avec console
  py -X utf8 tools\\agent\\agent_pc.py --port COM4
  pythonw tools\\agent\\agent_pc.py --service   sans console (démarrage automatique)
Pour libérer le port COM (mise à jour de la carte), crée le fichier tools\\agent\\PAUSE ;
supprime-le pour que l'agent se reconnecte.
"""
import argparse
import atexit
import collections
import ctypes
import glob
import json
import os
import re
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
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

try:
    import pynvml  # paquet « nvidia-ml-py »
except ImportError:
    pynvml = None

import winreg

try:
    from serveur_app import PORT as PORT_APP, ServeurApp
except ImportError:  # websockets pas installé
    PORT_APP, ServeurApp = 8765, None

DOSSIER = Path(__file__).resolve().parent
FICHIER_APPS = DOSSIER / "apps.json"
FICHIER_PAUSE = DOSSIER / "PAUSE"
FICHIER_LOG = DOSSIER / "agent.log"
FICHIER_REGLAGES = DOSSIER / "reglages.json"
FICHIER_APPAREILS = DOSSIER / "appareils.json"   # téléphones appairés (jamais dans Git)
ACTIF_SI = 60       # s : une touche / la souris dans la dernière minute = quelqu'un est là
MUET_MAX = 300      # s : après 5 min réveillé sans personne, on reprend quand même
REGLAGES_DEFAUT = {"ville": "", "latitude": None, "longitude": None}
URL_METEO = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
             "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
             "&hourly=precipitation_probability&timezone=auto&forecast_days=2")
URL_VILLE = "https://geocoding-api.open-meteo.com/v1/search?count=1&language=fr&name={nom}"
URL_LHM = "http://localhost:8085/data.json"
# Processus jamais considérés comme des jeux pour le calcul des FPS
PAS_DES_JEUX = {"dwm.exe", "explorer.exe", "steamwebhelper.exe", "steam.exe",
                "chrome.exe", "msedge.exe", "code.exe", "<unknown>"}
APPS_DEFAUT = {
    "spotify": "spotify:",
    "youtube": "https://www.youtube.com",
    "explorateur": "explorer",
    "calculatrice": "calc",
    "bloc-notes": "notepad",
    "vscode": "code",
}
# Une sortie audio branchée en USB (dongle) ou en Bluetooth = casque / enceinte externe.
# Si Windows ne donne pas cette information, on se rabat sur le nom :
# un nom contenant un de ces mots = haut-parleurs du PC.
MOTS_HAUT_PARLEURS = ("speaker", "haut-parleur", "realtek", "display audio")
MOTS_EXTERNES = ("USB", "BTH", "BLUETOOTH")

AIDE = """Commandes PC :
  APPS                  liste des apps   |  APP spotify    ouvre une app
  (les apps s'ajoutent / se retirent depuis l'app du téléphone, ou dans apps.json)
  LUM 70  LUM+  LUM-    luminosité de l'écran du PC
  VERROU                verrouille        |  ECRAN_OFF      verrouille + éteint l'écran
  VEILLE                mise en veille    |  ARRET          arrêt dans 60 s  |  ANNULER
  ETAT                  affiche ce que l'agent envoie à l'ESP32
  AUDIO                 liste les sorties audio (diagnostic du casque)
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
        self.muet = False  # PC réveillé tout seul par Windows : on ne dit rien à l'ESP32

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

    def fermer(self):
        with self.verrou:
            if self.ser is not None:
                try:
                    self.ser.close()
                except serial.SerialException:
                    pass
                self.ser = None

    def envoyer_brut(self, octets):
        with self.verrou:
            if self.ser is None:
                return False
            try:
                self.ser.write(octets)
                return True
            except serial.SerialException:
                self.ser = None
                return False

    def envoyer(self, ligne):
        with self.verrou:
            if self.ser is None:
                return False
            if self.muet:
                return True
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


def regler_volume(pourcent):
    v = max(0, min(100, int(pourcent)))
    _volume_endpoint().SetMasterVolumeLevelScalar(v / 100, None)
    return v


# --- souris et clavier directement sur le PC (SendInput), pour l'app : plus fluide que l'USB ---
class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.c_size_t)]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.c_size_t)]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_ushort), ("wParamH", ctypes.c_ushort)]


class _UNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT), ("hi", _HARDWAREINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("u", _UNION)]


def _envoyer_entrees(entrees):
    tableau = (_INPUT * len(entrees))(*entrees)
    ctypes.windll.user32.SendInput(len(entrees), tableau, ctypes.sizeof(_INPUT))


def _souris(flags, dx=0, dy=0, data=0):
    e = _INPUT(type=0)
    e.u.mi = _MOUSEINPUT(dx, dy, data & 0xFFFFFFFF, flags, 0, 0)
    return e


def souris_pc(dx, dy):
    _envoyer_entrees([_souris(0x0001, dx, dy)])


def clic_pc(bouton):
    bas, haut = (0x0008, 0x0010) if bouton == "droit" else (0x0002, 0x0004)
    _envoyer_entrees([_souris(bas), _souris(haut)])


def molette_pc(n):
    _envoyer_entrees([_souris(0x0800, data=int(n) * 120)])


def taper_pc(texte):
    """Tape n'importe quel texte (accents, emoji…) quelle que soit la disposition du clavier."""
    entrees = []
    for ch in texte:
        if ch == "\n":
            for haut in (0, 0x0002):
                e = _INPUT(type=1)
                e.u.ki = _KEYBDINPUT(0x0D, 0, haut, 0, 0)
                entrees.append(e)
            continue
        code = ord(ch)
        unites = [code] if code < 0x10000 else [0xD800 + ((code - 0x10000) >> 10),
                                                0xDC00 + ((code - 0x10000) & 0x3FF)]
        for u in unites:
            for haut in (0, 0x0002):
                e = _INPUT(type=1)
                e.u.ki = _KEYBDINPUT(0, u, 0x0004 | haut, 0, 0)
                entrees.append(e)
    if entrees:
        _envoyer_entrees(entrees)


def adresses_ip():
    """Adresses IPv4 du PC (réseau local et Tailscale 100.x.y.z)."""
    ips = []
    for nom, adrs in psutil.net_if_addrs().items():
        for a in adrs:
            if getattr(a, "family", None) == 2 and not a.address.startswith(("127.", "169.254.")):
                ips.append((nom, a.address))
    return ips


def texte_ascii(texte, defaut=""):
    """Enlève accents et caractères non latins (l'écran de l'ESP32 ne les connaît pas).
    Ex. « God of War Ragnarök » -> « God of War Ragnarok »."""
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii")
    t = " ".join(t.split())
    return t or defaut


def nom_court_audio(nom):
    """« Headphones (Xiaomi蓝牙音箱Pro) » -> « XiaomiPro » ; « Speakers (HECATE G30) » -> « HECATE G30 »."""
    if "(" in nom and nom.endswith(")"):
        nom = nom[nom.index("(") + 1:-1]
    return texte_ascii(nom, "Casque")


def _appareil_defaut():
    """Sortie audio par défaut, sous la forme d'un AudioDevice pycaw (ou None)."""
    dev = AudioUtilities.GetSpeakers()
    ident = getattr(dev, "id", None)
    if not isinstance(ident, str):
        ident = dev.GetId()
    for d in AudioUtilities.GetAllDevices():
        if d.id == ident:
            return d
    return None


def _texte_proprietes(appareil):
    try:
        return " ".join(str(v) for v in (appareil.properties or {}).values()).upper()
    except Exception:
        return ""


def sortie_audio():
    """(nom, externe) de la sortie audio par défaut. externe = casque / dongle / Bluetooth."""
    if AudioUtilities is None:
        return "", False
    try:
        d = _appareil_defaut()
    except Exception:
        return "", False
    if d is None:
        return "", False
    nom = d.FriendlyName or ""
    props = _texte_proprietes(d)
    if props:
        externe = any(m in props for m in MOTS_EXTERNES)
    else:
        bas = nom.lower()
        externe = bool(nom) and not any(m in bas for m in MOTS_HAUT_PARLEURS)
    return nom, externe


def diagnostic_audio():
    if AudioUtilities is None:
        return "pycaw n'est pas installé"
    lignes = []
    try:
        defaut = _appareil_defaut()
        id_defaut = defaut.id if defaut is not None else None
        for d in AudioUtilities.GetAllDevices():
            etat = str(getattr(d, "state", ""))
            if "Active" not in etat:
                continue
            props = _texte_proprietes(d)
            indices = [m for m in ("USB", "BTH", "BLUETOOTH", "HDAUDIO", "INTELAUDIO") if m in props]
            marque = "*" if d.id == id_defaut else " "
            lignes.append(f" {marque} {d.FriendlyName}  |  indices : {', '.join(indices) or 'aucun'}"
                          f"  |  {len(props)} caractères de propriétés")
    except Exception as e:
        return f"Erreur audio : {e!r}"
    nom, externe = sortie_audio()
    lignes.append(f"Par défaut : {nom!r} -> {'CASQUE' if externe else 'haut-parleurs'}")
    return "Sorties audio actives (* = par défaut) :\n" + "\n".join(lignes)


def gpu():
    """(température °C, charge %, mémoire %) de la carte NVIDIA, ou (-1, -1, -1)."""
    if pynvml is None:
        return -1, -1, -1
    try:
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        t = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
        u = pynvml.nvmlDeviceGetUtilizationRates(h).gpu
        m = pynvml.nvmlDeviceGetMemoryInfo(h)
        return int(t), int(u), round(m.used * 100 / m.total)
    except Exception:
        return -1, -1, -1


def jeu_steam():
    """Nom du jeu Steam en cours, ou '' si aucun."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            appid = int(winreg.QueryValueEx(k, "RunningAppID")[0])
    except (OSError, ValueError):
        return ""
    if appid == 0:
        return ""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            rf"Software\Valve\Steam\Apps\{appid}") as k:
            nom = str(winreg.QueryValueEx(k, "Name")[0])
            if nom:
                return nom
    except OSError:
        pass
    return f"Jeu Steam {appid}"


class LecteurLHM:
    """Température du processeur lue dans le serveur web de LibreHardwareMonitor."""

    def __init__(self):
        self.reessayer_a = 0.0
        self.probleme = ""

    def temperature_cpu(self):
        if time.time() < self.reessayer_a:
            return -1
        try:
            with urllib.request.urlopen(URL_LHM, timeout=0.5) as r:
                arbre = json.loads(r.read().decode("utf-8", errors="ignore"))
        except Exception as e:
            self.probleme = f"LibreHardwareMonitor injoignable ({e.__class__.__name__})"
            self.reessayer_a = time.time() + 3
            return -1
        self.probleme = ""
        valeurs = {}
        self._parcourir(arbre, "", valeurs)
        for nom in ("CPU Package", "Core Max", "Core Average", "Core (Tctl/Tdie)"):
            if nom in valeurs:
                return round(valeurs[nom])
        return -1

    def _parcourir(self, noeud, parent, valeurs):
        texte = str(noeud.get("Text", ""))
        identifiant = str(noeud.get("SensorId", ""))
        est_cpu = "cpu" in identifiant.lower() or not identifiant
        if parent == "Temperatures" and not noeud.get("Children") and est_cpu:
            v = noeud.get("RawValue")
            if not isinstance(v, (int, float)):
                brut = str(noeud.get("Value", "")).split(" ")[0].replace(",", ".")
                try:
                    v = float(brut)
                except ValueError:
                    v = None
            if v is not None and texte not in valeurs:
                valeurs[texte] = float(v)
        for enfant in noeud.get("Children", []) or []:
            self._parcourir(enfant, texte, valeurs)


def pid_premier_plan():
    u = ctypes.windll.user32
    pid = ctypes.c_ulong(0)
    u.GetWindowThreadProcessId(u.GetForegroundWindow(), ctypes.byref(pid))
    return pid.value


class CompteurFPS:
    """Lance PresentMon et calcule les FPS à partir du temps entre deux images.

    On utilise la colonne MsBetweenPresents (temps mesuré par Windows entre deux images),
    pas l'heure d'arrivée des lignes : PresentMon envoie ses lignes par paquets, ce qui
    faussait le comptage (valeurs comme 228 ou 322).
    """

    def __init__(self):
        self.proc = None
        self.series = {}      # (pid, swapchain) -> durées récentes en ms
        self.vu = {}          # (pid, swapchain) -> heure de la dernière ligne
        self.noms = {}        # pid -> nom de l'exe
        self.verrou = threading.Lock()
        self.probleme = ""
        self.entete = ""

    def exe(self):
        trouves = sorted(glob.glob(str(DOSSIER / "bin" / "PresentMon*.exe")))
        return trouves[-1] if trouves else None

    def demarrer(self):
        chemin = self.exe()
        if chemin is None:
            self.probleme = "PresentMon absent de tools\\agent\\bin"
            return False
        # Un PresentMon d'un ancien agent peut encore tourner et garder la session : on l'arrête.
        for p in psutil.process_iter(["name"]):
            try:
                if (p.info["name"] or "").lower().startswith("presentmon"):
                    p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(1)
        cmd = [chemin, "--output_stdout", "--no_console_stats", "--v1_metrics",
               "--stop_existing_session", "--session_name", "ESP32Telecommande"]
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, encoding="utf-8", errors="ignore",
                                         creationflags=0x08000000)  # pas de fenêtre
        except OSError as e:
            self.probleme = f"PresentMon ne démarre pas : {e}"
            return False
        atexit.register(self.arreter)
        threading.Thread(target=self._lire, daemon=True).start()
        return True

    def arreter(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()

    def _lire(self):
        col = None
        lignes_avant_entete = 0
        for ligne in self.proc.stdout:
            morceaux = [m.strip() for m in ligne.strip().split(",")]
            if col is None:
                bas = [m.lower() for m in morceaux]
                # Les noms de colonnes changent selon les versions (msBetweenPresents,
                # MsBetweenPresents, FrameTime…) : on compare sans tenir compte des majuscules.
                duree = next((n for n in ("msbetweenpresents", "frametime", "msbetweenappstart")
                              if n in bas), None)
                if "processid" in bas and duree is not None:
                    col = {"pid": bas.index("processid"), "ms": bas.index(duree),
                           "app": bas.index("application") if "application" in bas else None,
                           "chaine": bas.index("swapchainaddress")
                           if "swapchainaddress" in bas else None}
                    self.entete = ligne.strip()[:200]
                    self.probleme = ""
                else:
                    lignes_avant_entete += 1
                    if lignes_avant_entete == 1 or lignes_avant_entete == 50:
                        self.probleme = "PresentMon (en-tête non trouvé) : " + ligne.strip()[:150]
                continue
            try:
                pid = int(morceaux[col["pid"]])
                ms = float(morceaux[col["ms"]])
                chaine = morceaux[col["chaine"]] if col["chaine"] is not None else ""
                app = morceaux[col["app"]].lower() if col["app"] is not None else ""
            except (ValueError, IndexError):
                continue
            if ms <= 0:
                continue
            cle = (pid, chaine)
            with self.verrou:
                serie = self.series.get(cle)
                if serie is None:
                    serie = self.series[cle] = collections.deque(maxlen=300)
                serie.append(ms)
                self.vu[cle] = time.time()
                self.noms[pid] = app
        self.probleme = "PresentMon s'est arrêté (droits administrateur ?)"

    @staticmethod
    def _fps_de(serie):
        # Moyenne sur environ la dernière seconde d'images
        total = 0.0
        n = 0
        for ms in reversed(serie):
            total += ms
            n += 1
            if total >= 1000:
                break
        return round(1000 * n / total) if total > 0 else -1

    def fps(self):
        """FPS du jeu au premier plan (ou -1)."""
        maintenant = time.time()
        cible = pid_premier_plan()
        with self.verrou:
            actives = {c: s for c, s in self.series.items()
                       if maintenant - self.vu.get(c, 0) < 2 and len(s) >= 5
                       and self.noms.get(c[0]) not in PAS_DES_JEUX}
            # oublie les chaînes inactives depuis longtemps
            for c in [c for c, t in self.vu.items() if maintenant - t > 30]:
                self.vu.pop(c, None)
                self.series.pop(c, None)
            if not actives:
                return -1
            # la chaîne d'images la plus active du jeu au premier plan, sinon de tous les jeux
            du_jeu = {c: s for c, s in actives.items() if c[0] == cible} or actives
            return max(self._fps_de(list(s)) for s in du_jeu.values())


def icone_meteo(code):
    """Code météo WMO -> nom d'icône de l'écran."""
    if code == 0:
        return "soleil"
    if code in (1, 2):
        return "eclaircie"
    if code == 3:
        return "nuage"
    if code in (45, 48):
        return "brouillard"
    if 71 <= code <= 77 or code in (85, 86):
        return "neige"
    if code >= 95:
        return "orage"
    if 51 <= code <= 82:
        return "pluie"
    return "nuage"


def _json(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


class Meteo:
    """Récupère la météo d'aujourd'hui et de demain, sans bloquer l'agent."""

    def __init__(self):
        self.jours = []
        self.version = 0          # augmente à chaque nouvelle météo
        self.derniere = 0.0
        self.probleme = ""
        self.en_cours = False
        self.position = None

    def _reglages(self):
        if not FICHIER_REGLAGES.exists():
            FICHIER_REGLAGES.write_text(json.dumps(REGLAGES_DEFAUT, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
        return json.loads(FICHIER_REGLAGES.read_text(encoding="utf-8"))

    def _trouver_position(self):
        r = self._reglages()
        if r.get("latitude") is not None and r.get("longitude") is not None:
            return float(r["latitude"]), float(r["longitude"])
        ville = (r.get("ville") or "").strip()
        if not ville:
            raise ValueError(f"position non réglée : remplis {FICHIER_REGLAGES}")
        res = _json(URL_VILLE.format(nom=urllib.parse.quote(ville))).get("results") or []
        if not res:
            raise ValueError(f"ville introuvable : {ville}")
        return float(res[0]["latitude"]), float(res[0]["longitude"])

    def a_mettre_a_jour(self):
        attente = 1800 if self.jours else 300  # 30 min, ou 5 min tant qu'on n'a rien
        return not self.en_cours and time.time() - self.derniere > attente

    def lancer(self):
        self.en_cours = True
        self.derniere = time.time()
        threading.Thread(target=self._telecharger, daemon=True).start()

    def _telecharger(self):
        try:
            if self.position is None:
                self.position = self._trouver_position()
            lat, lon = self.position
            d = _json(URL_METEO.format(lat=lat, lon=lon))
            self.jours = self._lire(d)
            self.version += 1
            self.probleme = ""
        except Exception as e:
            self.probleme = f"météo : {e}"
        finally:
            self.en_cours = False

    @staticmethod
    def _lire(d):
        jour = d["daily"]
        heures = d["hourly"]["time"]
        pluie_h = d["hourly"]["precipitation_probability"]
        lt = time.localtime()
        aujourdhui = time.strftime("%Y-%m-%d", lt)
        jours = []
        for i in range(min(2, len(jour["time"]))):
            date = jour["time"][i]
            meilleure, heure = -1, -1
            for t, p in zip(heures, pluie_h):
                if not t.startswith(date) or p is None:
                    continue
                h = int(t[11:13])
                if date == aujourdhui and h < lt.tm_hour:
                    continue  # aujourd'hui : seulement les heures à venir
                if p > meilleure:
                    meilleure, heure = p, h
            jours.append((icone_meteo(int(jour["weather_code"][i] or 0)),
                          round(jour["temperature_2m_max"][i]), round(jour["temperature_2m_min"][i]),
                          meilleure, heure))
        return jours

    def lignes(self):
        return [f"METEO_J {i} {ic} {tmax} {tmin} {pluie} {heure}"
                for i, (ic, tmax, tmin, pluie, heure) in enumerate(self.jours)]


def est_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


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


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def inactivite():
    """Secondes depuis la dernière touche / souris sur le PC."""
    info = _LASTINPUTINFO(ctypes.sizeof(_LASTINPUTINFO), 0)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    maintenant = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF
    return ((maintenant - info.dwTime) & 0xFFFFFFFF) / 1000.0


def batterie():
    b = psutil.sensors_battery()
    if b is None:
        return -1, 0
    return round(b.percent), 1 if b.power_plugged else 0


# --------------------------------------------------------------------------
# Commandes PC
# --------------------------------------------------------------------------
VERROU_APPS = threading.Lock()


def charger_apps():
    """Apps du PC : dict nom -> cible (lien web, chemin Windows ou commande)."""
    with VERROU_APPS:
        if not FICHIER_APPS.exists():
            FICHIER_APPS.write_text(json.dumps(APPS_DEFAUT, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
        try:
            apps = json.loads(FICHIER_APPS.read_text(encoding="utf-8"))
        except ValueError:
            return {}
    return {str(k): str(v) for k, v in apps.items()} if isinstance(apps, dict) else {}


def _ecrire_apps(apps):
    with VERROU_APPS:
        provisoire = FICHIER_APPS.with_suffix(".tmp")
        provisoire.write_text(json.dumps(apps, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(provisoire, FICHIER_APPS)


def type_app(cible):
    if re.match(r"^https?://", cible, re.I):
        return "web"
    if re.match(r"^([A-Za-z]:[\\/]|\\\\|%)", cible):
        return "chemin"
    return "autre"


def liste_apps():
    """Pour le téléphone : [{nom, cible, type}]."""
    return [{"nom": n, "cible": c, "type": type_app(c)} for n, c in charger_apps().items()]


def trouver_app(apps, nom):
    nom = nom.strip().lower()
    for n in apps:
        if n.lower() == nom:
            return n
    return None


def ajouter_app(nom, cible, sorte):
    """Ajoute (ou remplace) une app. Renvoie (ok, texte)."""
    nom = " ".join(str(nom).split())
    cible = str(cible).strip()
    if not nom or len(nom) > 30:
        return False, "Nom vide ou trop long (30 caractères max)"
    if any(ord(c) < 32 for c in nom + cible) or '"' in nom + cible:
        return False, "Caractères interdits (guillemets, retours à la ligne)"
    if not cible or len(cible) > 400:
        return False, "Lien ou chemin vide ou trop long"
    if sorte == "web":
        if not re.match(r"^[a-z][a-z0-9+.-]*://", cible, re.I):
            cible = "https://" + cible
        morceaux = urllib.parse.urlparse(cible)
        if (morceaux.scheme.lower() not in ("http", "https")
                or not re.match(r"^[\w.-]+(:\d{1,5})?$", morceaux.netloc)):
            return False, "Lien web invalide (ex. https://www.youtube.com)"
    elif sorte == "chemin":
        cible = cible.strip('"')
        if type_app(cible) != "chemin":
            return False, "Chemin Windows invalide (ex. C:\\Jeux\\jeu.exe)"
        if not os.path.exists(os.path.expandvars(cible)):
            return False, f"Introuvable sur le PC : {cible}"
    else:
        return False, "Type inconnu (web ou chemin)"
    apps = charger_apps()
    ancien = trouver_app(apps, nom)
    if ancien is not None:
        del apps[ancien]
    apps[nom] = cible
    _ecrire_apps(apps)
    return True, ("App modifiée : " if ancien else "App ajoutée : ") + nom


def retirer_app(nom):
    apps = charger_apps()
    trouve = trouver_app(apps, str(nom))
    if trouve is None:
        return False, f"App inconnue : {nom}"
    del apps[trouve]
    _ecrire_apps(apps)
    return True, f"App retirée : {trouve}"


def lancer_app(cible):
    cible = os.path.expandvars(cible)
    try:
        os.startfile(cible)
    except OSError:
        # commandes du PATH (code, explorer…) : on passe par « start »
        subprocess.Popen(f'start "" "{cible}"', shell=True)


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
        nom = trouver_app(apps, arg)
        if nom is None:
            return f"App inconnue : {arg} (ajoute-la depuis le téléphone)"
        lancer_app(apps[nom])
        return f"Ouverture : {nom}"
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
    if cmd == "VOL" and arg.isdigit():
        if AudioUtilities is None:
            return "pycaw n'est pas installé"
        try:
            if comtypes is not None:
                comtypes.CoInitialize()
            return f"Volume : {regler_volume(arg)} %"
        except Exception as e:
            return f"Volume impossible : {e}"
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
        self.dernier_gpu = ""
        self.dernier_perf = ""
        self.precedent = {}
        self.problemes = {}
        self.dernier_temps = 0.0
        self.meteo = Meteo()
        self.meteo_envoyee = -1
        self.donnees = {}        # dernières valeurs, pour l'app
        self.ecran_esp = True
        self.telephones = 0
        self.lent = {"bat": (-1, 0), "cpu_temp": -1}
        self.bons = {}           # dernière valeur valide de chaque mesure (évite les « trous »)
        self.reveil = 0.0        # heure du dernier réveil « tout seul » (veille moderne), 0 = non
        self.lhm = LecteurLHM()
        self.fps = CompteurFPS()

    def boucle_mesures(self):
        if comtypes is not None:
            comtypes.CoInitialize()
        if pynvml is not None:
            try:
                pynvml.nvmlInit()
            except Exception as e:
                print(f"[agent] NVIDIA indisponible : {e}")
        psutil.cpu_percent(interval=None)
        if not est_admin():
            print("[agent] pas lancé en administrateur : les FPS ne seront pas disponibles")
        if not self.fps.demarrer():
            print(f"[agent] {self.fps.probleme}")
        tour = 0
        prochaine_connexion = 0.0
        tour_avant = time.time()
        while self.actif:
            debut = time.time()
            self._surveiller_reveil(debut - tour_avant)
            tour_avant = debut
            # --- liaison avec l'ESP32 (les mesures continuent même sans elle, pour l'app) ---
            if FICHIER_PAUSE.exists():
                if self.liaison.ser is not None:
                    self.liaison.fermer()
                    print("[agent] pause : port COM libéré")
            elif self.liaison.ser is None and debut >= prochaine_connexion:
                if self.liaison.connecter():
                    if tour > 0:
                        self._reveil_discret("liaison USB revenue")
                    self.precedent = {}  # renvoie tous les états après reconnexion
                    self.dernier_temps = 0.0
                    self.meteo_envoyee = -1
                else:
                    prochaine_connexion = debut + 3

            lent = tour % 4 == 0  # une fois par seconde
            if lent:
                self._mesures_lentes()

            # --- mesures rapides : 4 fois par seconde ---
            cpu = round(psutil.cpu_percent(interval=None))
            ram = round(psutil.virtual_memory().percent)
            vol = self._garder("vol", volume(), 10)
            bat, charge = self.lent["bat"]
            self.dernier_stat = f"STAT {cpu} {ram} {vol} {bat} {charge}"
            self.liaison.envoyer(self.dernier_stat)
            t, u, mem = gpu()
            t = self._garder("gpu_t", t)
            u = self._garder("gpu_u", u)
            mem = self._garder("gpu_m", mem)
            self.dernier_gpu = f"GPU {t} {u} {mem}"
            self.liaison.envoyer(self.dernier_gpu)
            en_jeu = self.precedent.get("JEU", "-") != "-"
            fps = self._garder("fps", self.fps.fps(), 3) if en_jeu else -1
            self.dernier_perf = f"PERF {self.lent['cpu_temp']} {fps}"
            self.liaison.envoyer(self.dernier_perf)

            p = self.precedent
            self.donnees = {
                "cpu": cpu, "ram": ram, "vol": vol, "bat": bat, "chg": charge,
                "gpu_temp": t, "gpu_charge": u, "vram": mem,
                "cpu_temp": self.lent["cpu_temp"], "fps": fps,
                "casque": "" if p.get("CASQUE", "-") == "-" else p.get("CASQUE"),
                "manette": p.get("MANETTE") == "1", "verrou": p.get("VERROU") == "1",
                "jeu": "" if p.get("JEU", "-") == "-" else p.get("JEU"),
                "meteo": [dict(zip(("icone", "tmax", "tmin", "pluie", "heure"), j))
                          for j in self.meteo.jours],
                "esp": self.liaison.ser is not None, "ecran_esp": self.ecran_esp,
            }
            tour += 1
            time.sleep(max(0.0, 0.25 - (time.time() - debut)))

    def _reveil_discret(self, raison):
        """Windows (veille moderne) réveille le PC quelques secondes de temps en temps.
        Tant que personne n'utilise le PC, on ne dit rien à l'ESP32 : elle reste en veille
        au lieu de dire « Bonjour » à chaque petit réveil."""
        if inactivite() < ACTIF_SI:
            return
        if not self.liaison.muet:
            print(f"[agent] réveil sans utilisateur ({raison}) : ESP32 laissée en veille")
        self.liaison.muet = True
        self.reveil = time.time()

    def _surveiller_reveil(self, ecart):
        if ecart > 45:  # la boucle a été endormie : le PC sort de veille
            self._reveil_discret(f"pause de {round(ecart)} s")
        if self.liaison.muet:
            if inactivite() < ACTIF_SI or time.time() - self.reveil > MUET_MAX:
                self.reprendre()

    def reprendre(self):
        """Quelqu'un utilise le PC (ou le téléphone) : l'ESP32 se réveille."""
        if not self.liaison.muet:
            return
        self.liaison.muet = False
        self.precedent = {}  # renvoie tous les états
        self.dernier_temps = 0.0
        self.meteo_envoyee = -1
        print("[agent] PC utilisé : l'ESP32 se réveille")

    def _garder(self, cle, valeur, duree=30):
        """Une mesure ratée (-1) garde la dernière bonne valeur pendant `duree` secondes,
        pour que l'écran et l'app ne clignotent pas."""
        if valeur is not None and valeur >= 0:
            self.bons[cle] = (valeur, time.time())
            return valeur
        ancien = self.bons.get(cle)
        if ancien is not None and time.time() - ancien[1] < duree:
            return ancien[0]
        return valeur

    def _mesures_lentes(self):
        if time.time() - self.dernier_temps > 60:
            self.dernier_temps = time.time()
            lt = time.localtime()
            self.liaison.envoyer(f"TEMPS {lt.tm_year} {lt.tm_mon} {lt.tm_mday} {lt.tm_wday} "
                                 f"{lt.tm_hour} {lt.tm_min} {lt.tm_sec}")
        self.lent["bat"] = batterie()
        self.lent["cpu_temp"] = self._garder("cpu_t", self.lhm.temperature_cpu())
        if self.meteo.a_mettre_a_jour():
            self.meteo.lancer()
        if self.meteo.jours and self.meteo_envoyee != self.meteo.version:
            self.meteo_envoyee = self.meteo.version
            for ligne in self.meteo.lignes():
                self.liaison.envoyer(ligne)
        for nom, outil in (("LibreHardwareMonitor", self.lhm), ("PresentMon", self.fps),
                           ("Météo", self.meteo)):
            if outil.probleme != self.problemes.get(nom):
                self.problemes[nom] = outil.probleme
                print(f"[agent] {nom} : {outil.probleme or 'OK'}")
        nom, externe = sortie_audio()
        jeu = jeu_steam()
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

    # --------------------------------------------------------------- pour l'app
    def executer(self, ligne):
        """Exécute une commande venant de la console ou de l'app. Renvoie un texte."""
        ligne = ligne.strip()
        if not ligne:
            return ""
        cmd = ligne.split(" ", 1)[0].upper()
        self.reprendre()
        reponse = executer_pc(ligne)
        if reponse is not None:
            if cmd not in ("APPS", "AUDIO"):
                self.liaison.envoyer("EVT ACTION " + texte_ascii(ligne))
            return reponse
        if cmd == "ECRAN_ESP":
            self.ecran_esp = ligne.split(" ", 1)[-1].strip() != "0"
        if self.liaison.envoyer(ligne):
            return "Envoyé à l'ESP32"
        return "ESP32 non connectée"

    def rappels_app(self):
        def afficher_pin(pin):
            print(f"[agent] code d'appairage : {pin}")
            self.liaison.envoyer(f"EVT PIN {pin}")

        def connexion(n):
            if n != self.telephones:
                self.liaison.envoyer(f"EVT APP {1 if n else 0}")
            self.telephones = n

        def texte(t):
            taper_pc(t)
            self.liaison.envoyer("EVT ACTION TEXTE")

        return {
            "executer": self.executer,
            "etat": lambda: self.donnees,
            "apps": liste_apps,
            "ajouter_app": ajouter_app, "retirer_app": retirer_app,
            "afficher_pin": afficher_pin,
            "souris": souris_pc, "clic": clic_pc, "molette": molette_pc,
            "texte": texte, "connexion": connexion,
        }

    def boucle_lecture(self):
        dernier_redemarrage = 0.0
        while self.actif:
            ligne = self.liaison.lire_ligne()
            if ligne is None:
                time.sleep(0.5)
                continue
            if ligne and ligne != "OK":
                print(f"[esp32] {ligne}")
            # L'ESP32 est retombée dans l'invite MicroPython (programme arrêté) :
            # Ctrl-D relance main.py.
            en_repl = ligne.startswith((">>>", "Traceback", "MicroPython v")) or "Error:" in ligne
            if en_repl and time.time() - dernier_redemarrage > 15:
                dernier_redemarrage = time.time()
                print("[agent] programme de l'ESP32 arrêté : redémarrage (Ctrl-D)")
                self.liaison.envoyer_brut(b"\r\x03\x03\x04")
                self.precedent = {}  # renvoie tous les états une fois relancé
                self.dernier_temps = 0.0
                self.meteo_envoyee = -1

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
                print(self.dernier_stat, self.dernier_gpu, self.dernier_perf, self.precedent)
                print("Colonnes PresentMon :", self.fps.entete or "(pas encore reçues)")
                print("Météo :", self.meteo.lignes() or self.meteo.probleme or "en cours…")
                print("App : port", PORT_APP, "| téléphones connectés :", self.telephones,
                      "| adresses :", ", ".join(f"{n} {ip}" for n, ip in adresses_ip()))
                print("LibreHardwareMonitor :", self.lhm.probleme or "OK",
                      "| PresentMon :", self.fps.probleme or "OK",
                      "| administrateur :", "oui" if est_admin() else "non")
                continue
            if ligne.upper() == "AUDIO":
                if comtypes is not None:
                    comtypes.CoInitialize()
                print(diagnostic_audio())
                continue
            print(self.executer(ligne))
        self.actif = False


def main():
    if sys.platform != "win32":
        sys.exit("Ce programme est fait pour Windows.")
    parser = argparse.ArgumentParser(description="Agent PC de la Télécommande ESP32")
    parser.add_argument("--port", help="port série de l'ESP32 (sinon trouvé tout seul)")
    parser.add_argument("--service", action="store_true",
                        help="sans console : tourne en fond, écrit dans agent.log")
    args = parser.parse_args()

    if args.service:
        journal = open(FICHIER_LOG, "a", encoding="utf-8", buffering=1)
        sys.stdout = journal
        sys.stderr = journal
        print(f"--- démarrage {time.strftime('%Y-%m-%d %H:%M:%S')} ---")

    agent = Agent(Liaison(args.port))
    threading.Thread(target=agent.boucle_mesures, daemon=True).start()
    if ServeurApp is not None:
        ServeurApp(FICHIER_APPAREILS, agent.rappels_app()).demarrer()
        print("[agent] adresses du PC pour l'app : "
              + ", ".join(f"{ip} ({n})" for n, ip in adresses_ip()))
    else:
        print("[agent] serveur app indisponible : py -m pip install --user websockets")
    threading.Thread(target=agent.boucle_lecture, daemon=True).start()
    if args.service:
        while True:
            time.sleep(3600)
    agent.console()


if __name__ == "__main__":
    main()
