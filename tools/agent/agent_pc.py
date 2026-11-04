#!/usr/bin/env python3
"""Programme PC de la Télécommande ESP32 (Windows).

- Envoie chaque seconde à l'ESP32 : CPU, RAM, volume, batterie (ligne « STAT »).
- Envoie chaque seconde la carte graphique NVIDIA : température, charge, mémoire (ligne « GPU »).
- Surveille et signale : sortie audio (casque ou haut-parleurs), manette, PC verrouillé,
  jeu en cours, Steam ou non (lignes « EVT »).
- Mode gamer : température du processeur (LibreHardwareMonitor) et FPS du jeu (PresentMon),
  ligne « PERF » chaque seconde.
- Météo d'aujourd'hui et de demain (Open-Meteo) toutes les 30 min, lignes « METEO_J »
  (position dans tools\\agent\\reglages.json).
- Serveur pour l'app Flutter du téléphone (WebSocket, port 8765, voir serveur_app.py) :
  appairage par code affiché sur l'ESP32, souris / texte directement sur le PC, état 4 fois / s.
- Mesures envoyées 4 fois par seconde (CPU, RAM, volume, GPU, FPS) pour un écran plus vif.
- Envoie l'heure du PC (ligne « TEMPS ») à la connexion puis chaque minute.
- Prévient l'ESP32 de chaque commande PC exécutée (« EVT ACTION … ») pour que la mascotte réagisse.
- Exécute les commandes « PC » : ouvrir une app, luminosité, verrouiller, écran noir,
  veille, arrêt. Les autres commandes (KEY, TEXT, VOL+, MOUSE…) sont transmises à l'ESP32.
- Phase 7 : « écran noir » sans veille (tous les écrans, le PC reste joignable), compte à
  rebours d'arrêt sur l'ESP32 (EVT ARRET), luminosité de l'ESP32 (LUM_ESP), raccourcis
  enregistrés depuis le téléphone (touches, texte, commande administrateur, app, pause…).
- Phase 8 : aperçu de l'écran du PC dans l'app (capture JPEG à la demande, tous les écrans),
  toucher l'aperçu = cliquer à cet endroit ; adresse /widget pour le widget Android.
- Phase 9 : jeux lancés hors Steam (DetecteurJeu, tools\\agent\\jeux.json facultatif).
- Phase 10 : vidéo au premier plan (EVT VIDEO source|titre), PC inutilisé (EVT INACTIF minutes),
  temps de jeu par jeu et par jour (tools\\agent\\stats_jeux.json, ligne JEU_TOTAL minutes).
- Phase 11 : suivi du master (master.py : ligne MASTER {json} et MASTER_INFO vers l'ESP32,
  onglet Master de l'app), page « Mes jeux » de l'app, /etat_court pour la notification Android.

Utilisation (dans le dossier Micro) :
  py -X utf8 tools\\agent\\agent_pc.py            port trouvé tout seul, avec console
  py -X utf8 tools\\agent\\agent_pc.py --port COM4
  pythonw tools\\agent\\agent_pc.py --service   sans console (démarrage automatique)
Pour libérer le port COM (mise à jour de la carte), crée le fichier tools\\agent\\PAUSE ;
supprime-le pour que l'agent se reconnecte.
"""
import argparse
import atexit
import base64
import collections
import ctypes
import faulthandler
import glob
import io
import json
import os
import queue
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

try:  # aperçu de l'écran (Phase 8) : py -m pip install --user mss Pillow
    import mss
    from PIL import Image, ImageDraw
except ImportError:
    mss = None

import winreg

try:
    from serveur_app import PORT as PORT_APP, ServeurApp
except ImportError:  # websockets pas installé
    PORT_APP, ServeurApp = 8765, None

from master import SuiviMaster  # Phase 11 : suivi du master
from media_windows import LecteurMedia  # Phase 11-bis : position de la vidéo

DOSSIER = Path(__file__).resolve().parent
FICHIER_APPS = DOSSIER / "apps.json"
FICHIER_PAUSE = DOSSIER / "PAUSE"
FICHIER_LOG = DOSSIER / "agent.log"
FICHIER_REGLAGES = DOSSIER / "reglages.json"
FICHIER_APPAREILS = DOSSIER / "appareils.json"   # téléphones appairés (jamais dans Git)
FICHIER_RACCOURCIS = DOSSIER / "raccourcis.json"
FICHIER_PREFERENCES = DOSSIER / "preferences.json"
DUREE_ARRET = 60    # s : compte à rebours de « Éteindre le PC »
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
  VERROU                verrouille        |  ECRAN_OFF / ECRAN_ON / ECRAN_BASCULE  écran noir
  VEILLE                mise en veille    |  ARRET          arrêt dans 60 s  |  ANNULER
  LUM_ESP 60            luminosité de l'écran de l'ESP32
  RAC nom               lance un raccourci (créés depuis le téléphone, raccourcis.json)
  TOUCHES ctrl+6        touches envoyées directement par Windows (disposition du clavier respectée)
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
        except Exception:  # port fermé pendant la lecture (PAUSE, carte débranchée…)
            if self.ser is ser:
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


# Heure de la dernière action venue du téléphone (souris, clavier, raccourci) : l'écran noir
# ne se rallume que pour le vrai clavier / la vraie souris du PC.
INJECTION = {"t": 0.0}


def _envoyer_entrees(entrees):
    INJECTION["t"] = time.time()
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


# --- raccourcis clavier directement par Windows (Phase 7) ---
# Les touches sont envoyées par leur code « scan », traduit selon la disposition du clavier
# du PC (AZERTY ou QWERTY) : « ctrl+a » appuie bien sur la touche A, et les jeux les voient.
TOUCHES_NOMMEES = {
    "ctrl": 0xA2, "control": 0xA2, "shift": 0xA0, "maj": 0xA0, "alt": 0xA4, "altgr": 0xA5,
    "win": 0x5B, "windows": 0x5B,
    "enter": 0x0D, "entree": 0x0D, "entrée": 0x0D, "esc": 0x1B, "echap": 0x1B, "échap": 0x1B,
    "tab": 0x09, "space": 0x20, "espace": 0x20, "backspace": 0x08, "retour": 0x08,
    "delete": 0x2E, "suppr": 0x2E, "insert": 0x2D, "inser": 0x2D, "home": 0x24, "debut": 0x24,
    "début": 0x24, "end": 0x23, "fin": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "up": 0x26, "haut": 0x26, "down": 0x28, "bas": 0x28, "left": 0x25, "gauche": 0x25,
    "right": 0x27, "droite": 0x27, "printscreen": 0x2C, "impr": 0x2C, "menu": 0x5D,
    "pause": 0x13, "capslock": 0x14, "verrmaj": 0x14,
    "volup": 0xAF, "voldown": 0xAE, "mute": 0xAD, "play": 0xB3, "next": 0xB0, "prev": 0xB1,
}
for _n in range(1, 25):
    TOUCHES_NOMMEES[f"f{_n}"] = 0x70 + _n - 1
for _n in range(10):
    TOUCHES_NOMMEES[f"num{_n}"] = 0x60 + _n
TOUCHES_ETENDUES = {0x5B, 0x5C, 0x5D, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2C,
                    0x2D, 0x2E, 0x6F, 0x90, 0xA3, 0xA5, 0xAD, 0xAE, 0xAF, 0xB0, 0xB1, 0xB2, 0xB3}


def lire_touches(texte):
    """« ctrl+shift+esc » -> liste de codes de touches (VK), ou None si une touche est inconnue."""
    codes = []
    for morceau in str(texte).lower().replace(" ", "").split("+"):
        if not morceau:
            return None
        if morceau in TOUCHES_NOMMEES:
            codes.append(TOUCHES_NOMMEES[morceau])
        elif len(morceau) == 1 and ("a" <= morceau <= "z" or "0" <= morceau <= "9"):
            codes.append(ord(morceau.upper()))
        elif len(morceau) == 1 and sys.platform == "win32":
            vk = ctypes.windll.user32.VkKeyScanW(ord(morceau))
            if vk == -1 or vk & 0xFF == 0xFF:
                return None
            codes.append(vk & 0xFF)
        else:
            return None
    if not codes or len(codes) > 5:
        return None
    return codes


def _touche(vk, haut):
    scan = ctypes.windll.user32.MapVirtualKeyW(vk, 0) & 0xFF
    flags = 0x0008 if scan else 0          # KEYEVENTF_SCANCODE : vu aussi par les jeux
    if vk in TOUCHES_ETENDUES:
        flags |= 0x0001                    # KEYEVENTF_EXTENDEDKEY
    if haut:
        flags |= 0x0002                    # KEYEVENTF_KEYUP
    e = _INPUT(type=1)
    e.u.ki = _KEYBDINPUT(vk, scan, flags, 0, 0)
    return e


def touches_pc(texte):
    """Appuie sur un raccourci (ex. « ctrl+6 », « win+x », « alt+tab »). Renvoie False si inconnu."""
    codes = lire_touches(texte)
    if codes is None:
        return False
    _envoyer_entrees([_touche(c, False) for c in codes])
    time.sleep(0.04)
    _envoyer_entrees([_touche(c, True) for c in reversed(codes)])
    return True


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def moniteurs_windows():
    """Écrans allumés : [(x, y, largeur, hauteur)] en pixels réels (étendu, 2e écran seul…)."""
    res = []
    if sys.platform != "win32":
        return res
    u = ctypes.windll.user32
    proto = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                               ctypes.POINTER(_RECT), ctypes.c_ssize_t)

    def rappel(_hmon, _hdc, rect, _data):
        r = rect.contents
        res.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
        return 1

    fonction = proto(rappel)
    u.EnumDisplayMonitors(None, None, fonction, 0)
    if not res:
        res.append((0, 0, u.GetSystemMetrics(0), u.GetSystemMetrics(1)))
    return res


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
        return "pycaw is not installed"
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
            lignes.append(f" {marque} {d.FriendlyName}  |  hints: {', '.join(indices) or 'none'}"
                          f"  |  {len(props)} property characters")
    except Exception as e:
        return f"Audio error: {e!r}"
    nom, externe = sortie_audio()
    lignes.append(f"Default: {nom!r} -> {'HEADSET' if externe else 'speakers'}")
    return "Active audio outputs (* = default):\n" + "\n".join(lignes)


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
    return f"Steam game {appid}"


# --- Phase 9 : jeux lancés hors Steam (Rockstar, Epic, .exe lancé à la main…) ---------------
# Fichier facultatif (créé à la main si besoin, jamais obligatoire) :
#   tools\agent\jeux.json = {"jeux": ["tennis2.exe"], "pas_des_jeux": ["obs64.exe"]}
# « jeux » : toujours un jeu ; « pas_des_jeux » : jamais un jeu (faux positif).
FICHIER_JEUX = DOSSIER / "jeux.json"
# Un .exe rangé dans un de ces dossiers est un jeu (comparaison en minuscules)
DOSSIERS_JEUX = ("\\steamapps\\common\\", "\\epic games\\", "\\gog games\\", "\\gog galaxy\\games\\",
                 "\\xboxgames\\", "\\rockstar games\\", "\\ea games\\", "\\electronic arts\\",
                 "\\ubisoft game launcher\\games\\", "\\riot games\\", "\\games\\", "\\jeux\\")
# Ces mots dans le nom du .exe = lanceur ou outil, jamais le jeu lui-même
MOTS_PAS_JEUX = ("launcher", "unins", "setup", "install", "crash", "report", "redist", "vc_",
                 "dxsetup", "easyanticheat", "battleye", "helper", "updater", "overlay", "service")
# Programmes jamais considérés comme des jeux, même en plein écran (vidéo, navigateurs, outils)
APPS_PAS_JEUX = {
    "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "opera_gx.exe", "brave.exe",
    "vivaldi.exe", "vlc.exe", "mpc-hc.exe", "mpc-hc64.exe", "mpc-be64.exe", "potplayer64.exe",
    "potplayermini64.exe", "wmplayer.exe", "video.ui.exe", "microsoft.media.player.exe",
    "netflix.exe", "wwahost.exe", "applicationframehost.exe", "msedgewebview2.exe",
    "discord.exe", "obs64.exe", "code.exe", "explorer.exe", "dwm.exe", "python.exe",
    "pythonw.exe", "steam.exe", "steamwebhelper.exe", "epicgameslauncher.exe",
    "powerpnt.exe", "winword.exe", "excel.exe", "spotify.exe", "lockapp.exe", "searchhost.exe",
    "shellexperiencehost.exe", "startmenuexperiencehost.exe", "textinputhost.exe", "taskmgr.exe",
    "photos.exe", "mstsc.exe",
}
GPU_JEU = 30        # % : charge de la carte graphique au-dessus de laquelle le plein écran est un jeu
CONFIRMER_JEU = 3   # s : la fenêtre doit ressembler à un jeu pendant 3 s de suite
_U32 = ctypes.WinDLL("user32") if sys.platform == "win32" else None
if _U32 is not None:
    _U32.GetForegroundWindow.restype = ctypes.c_void_p
    _U32.GetWindowThreadProcessId.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))
    _U32.GetWindowRect.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _U32.MonitorFromWindow.argtypes = (ctypes.c_void_p, ctypes.c_ulong)
    _U32.MonitorFromWindow.restype = ctypes.c_void_p
    _U32.GetMonitorInfoW.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _U32.GetWindowTextW.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int)


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", _RECT), ("rcWork", _RECT),
                ("dwFlags", ctypes.c_ulong)]


def fenetre_premier_plan():
    """(fenêtre, pid) de la fenêtre au premier plan, ou (None, 0)."""
    if _U32 is None:
        return None, 0
    hwnd = _U32.GetForegroundWindow()
    if not hwnd:
        return None, 0
    pid = ctypes.c_ulong(0)
    _U32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return hwnd, pid.value


def fenetre_plein_ecran(hwnd):
    """Vrai si la fenêtre couvre tout son écran (plein écran ou fenêtré sans bordure)."""
    r = _RECT()
    if not _U32.GetWindowRect(hwnd, ctypes.byref(r)):
        return False
    hmon = _U32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
    info = _MONITORINFO()
    info.cbSize = ctypes.sizeof(_MONITORINFO)
    if not hmon or not _U32.GetMonitorInfoW(hmon, ctypes.byref(info)):
        return False
    m = info.rcMonitor
    return r.left <= m.left and r.top <= m.top and r.right >= m.right and r.bottom >= m.bottom


def titre_fenetre(hwnd):
    tampon = ctypes.create_unicode_buffer(256)
    _U32.GetWindowTextW(hwnd, tampon, 256)
    return tampon.value.strip()


def charger_jeux():
    """Listes de tools\\agent\\jeux.json : (toujours des jeux, jamais des jeux), en minuscules."""
    try:
        d = json.loads(FICHIER_JEUX.read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            d = {}
    except (OSError, ValueError):
        d = {}

    def liste(cle):
        v = d.get(cle, [])
        return {n.strip().lower() for n in v if isinstance(n, str)} if isinstance(v, list) else set()

    return liste("jeux"), liste("pas_des_jeux")


class DetecteurJeu:
    """Jeu en cours : Steam d'abord, sinon la fenêtre au premier plan si elle ressemble à un jeu
    (.exe dans un dossier de jeux, ou plein écran avec la carte graphique chargée).
    Un jeu repéré le reste tant que son programme tourne (même en Alt+Tab)."""

    def __init__(self):
        self.pid = 0
        self.exe = ""
        self.nom = ""
        self.candidat = (0, 0.0)   # (pid, depuis quand) de la fenêtre qui ressemble à un jeu
        self.listes = (set(), set())
        self.listes_lues = 0.0

    def _listes(self):
        if time.time() - self.listes_lues > 10:
            self.listes_lues = time.time()
            self.listes = charger_jeux()
        return self.listes

    def jeu(self, charge_gpu):
        """Nom du jeu en cours, '' si aucun. Appelé une fois par seconde."""
        steam = jeu_steam()
        if steam:
            return steam
        jeux, pas = self._listes()
        if self.pid:
            try:
                if psutil.Process(self.pid).name().lower() == self.exe and self.exe not in pas:
                    return self.nom
            except psutil.Error:
                pass
            print(f"[agent] fin du jeu : {self.nom}")
            self.pid, self.exe, self.nom = 0, "", ""
        hwnd, pid = fenetre_premier_plan()
        if not hwnd or not pid or pid == os.getpid():
            self.candidat = (0, 0.0)
            return ""
        try:
            p = psutil.Process(pid)
            exe = p.name().lower()
            chemin = p.exe() or ""
        except psutil.Error:
            self.candidat = (0, 0.0)
            return ""
        if exe in pas or exe in APPS_PAS_JEUX:
            self.candidat = (0, 0.0)
            return ""
        if exe in jeux:
            return self._retenir(pid, exe, chemin, hwnd)
        if any(m in exe for m in MOTS_PAS_JEUX):
            self.candidat = (0, 0.0)
            return ""
        dossier_jeu = any(d in chemin.lower() for d in DOSSIERS_JEUX)
        if dossier_jeu or (charge_gpu >= GPU_JEU and fenetre_plein_ecran(hwnd)):
            if self.candidat[0] != pid:
                self.candidat = (pid, time.time())
            if time.time() - self.candidat[1] >= CONFIRMER_JEU:
                return self._retenir(pid, exe, chemin, hwnd)
            return ""
        self.candidat = (0, 0.0)
        return ""

    def _retenir(self, pid, exe, chemin, hwnd):
        nom = titre_fenetre(hwnd)
        if not (2 <= len(nom) <= 40):
            m = re.search(r"\\steamapps\\common\\([^\\]+)\\", chemin, re.IGNORECASE)
            if m:
                nom = m.group(1)
            else:  # nom du dossier du jeu (ex. « AO Tennis 2 »), sinon nom du .exe
                from pathlib import PureWindowsPath
                c = PureWindowsPath(chemin or exe)
                nom = next((q.name for q in c.parents if q.name and q.name.lower() not in
                            ("bin", "bin64", "win64", "x64", "binaries", "game", "retail")), c.stem)
        self.pid, self.exe, self.nom = pid, exe, nom[:30]
        self.candidat = (0, 0.0)
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
                  "video.ui.exe": "Movies & TV", "microsoft.media.player.exe": "Media Player"}
_COMPTEUR_SON = {"m": None, "t": 0.0}


def son_en_cours():
    """Vrai si la sortie audio joue du son ; None si on ne peut pas le savoir (pycaw absent)."""
    if AudioUtilities is None:
        return None
    try:
        if _COMPTEUR_SON["m"] is None or time.time() - _COMPTEUR_SON["t"] > 30:
            # recréé toutes les 30 s : suit le changement de sortie (casque <-> haut-parleurs)
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import IAudioMeterInformation
            dev = AudioUtilities.GetSpeakers()
            brut = getattr(dev, "_dev", dev)  # pycaw récent : objet AudioDevice
            itf = brut.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
            # QueryInterface renvoie un pointeur COM qui garde l'objet en vie (un simple cast ne le
            # faisait pas : Windows libérait l'objet et la lecture suivante plantait Python).
            _COMPTEUR_SON["m"] = itf.QueryInterface(IAudioMeterInformation)
            _COMPTEUR_SON["dev"] = brut  # garde aussi l'appareil audio en vie
            _COMPTEUR_SON["t"] = time.time()
        return _COMPTEUR_SON["m"].GetPeakValue() > 0.01
    except Exception:
        _COMPTEUR_SON["m"] = None
        return None


FICHIER_SITES = DOSSIER / "sites_video.json"   # Phase 11-bis : sites ajoutés depuis l'app (jamais dans Git)
_SITES_PERSO = {"liste": [], "lu": 0.0}


def sites_perso():
    """[(mot du titre en minuscules, nom affiché)] ajoutés depuis l'app, relus toutes les 10 s."""
    if time.time() - _SITES_PERSO["lu"] > 10:
        _SITES_PERSO["lu"] = time.time()
        try:
            d = json.loads(FICHIER_SITES.read_text(encoding="utf-8"))
            _SITES_PERSO["liste"] = [(str(s["mot"]).strip().lower(), str(s["nom"]).strip()) for s in d
                                     if isinstance(s, dict) and str(s.get("mot", "")).strip()
                                     and str(s.get("nom", "")).strip()]
        except (OSError, ValueError, TypeError, KeyError):
            _SITES_PERSO["liste"] = []
    return _SITES_PERSO["liste"]


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
        for cle, nom in sites_perso() + list(SITES_VIDEO):  # sites ajoutés dans l'app d'abord
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
        return False, "Name empty or too long (30 characters max)"
    if any(ord(c) < 32 for c in nom + cible) or '"' in nom + cible:
        return False, "Forbidden characters (quotes, line breaks)"
    if not cible or len(cible) > 400:
        return False, "Link or path empty or too long"
    if sorte == "web":
        if not re.match(r"^[a-z][a-z0-9+.-]*://", cible, re.I):
            cible = "https://" + cible
        morceaux = urllib.parse.urlparse(cible)
        if (morceaux.scheme.lower() not in ("http", "https")
                or not re.match(r"^[\w.-]+(:\d{1,5})?$", morceaux.netloc)):
            return False, "Invalid web link (e.g. https://www.youtube.com)"
    elif sorte == "chemin":
        cible = cible.strip('"')
        if type_app(cible) != "chemin":
            return False, "Invalid Windows path (e.g. C:\\Games\\game.exe)"
        if not os.path.exists(os.path.expandvars(cible)):
            return False, f"Not found on the PC: {cible}"
    else:
        return False, "Unknown type (web or path)"
    apps = charger_apps()
    ancien = trouver_app(apps, nom)
    if ancien is not None:
        del apps[ancien]
    apps[nom] = cible
    _ecrire_apps(apps)
    return True, ("App updated: " if ancien else "App added: ") + nom


def retirer_app(nom):
    apps = charger_apps()
    trouve = trouver_app(apps, str(nom))
    if trouve is None:
        return False, f"Unknown app: {nom}"
    del apps[trouve]
    _ecrire_apps(apps)
    return True, f"App removed: {trouve}"


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
        return "Apps: " + ", ".join(charger_apps().keys())
    if cmd == "APP":
        apps = charger_apps()
        nom = trouver_app(apps, arg)
        if nom is None:
            return f"Unknown app: {arg} (add it from the phone)"
        lancer_app(apps[nom])
        return f"Opening: {nom}"
    if cmd in ("LUM", "LUM+", "LUM-"):
        if sbc is None:
            return "screen_brightness_control is not installed"
        try:
            if cmd == "LUM":
                v = regler_luminosite(arg)
            else:
                pas = 10 if cmd == "LUM+" else -10
                v = regler_luminosite(luminosite_actuelle() + pas)
        except Exception as e:
            return f"Brightness failed: {e}"
        return f"Brightness: {v} %"
    if cmd == "VOL" and arg.isdigit():
        if AudioUtilities is None:
            return "pycaw is not installed"
        try:
            if comtypes is not None:
                comtypes.CoInitialize()
            return f"Volume: {regler_volume(arg)} %"
        except Exception as e:
            return f"Volume failed: {e}"
    if cmd == "VERROU":
        ctypes.windll.user32.LockWorkStation()
        return "PC locked"
    if cmd == "VEILLE":
        # Ce PC n'a que la veille moderne (S0) : on y entre en verrouillant puis en coupant
        # l'écran (SetSuspendState ne marche pas sans S3 ni hibernation).
        ctypes.windll.user32.LockWorkStation()
        time.sleep(0.5)
        ctypes.windll.user32.PostMessageW(0xFFFF, 0x0112, 0xF170, 2)
        return "Going to sleep"
    if cmd == "TOUCHES":
        if not touches_pc(arg):
            return f"Unknown key: {arg}"
        return f"Keys: {arg}"
    if cmd == "ARRET":
        subprocess.Popen(f"shutdown /s /t {DUREE_ARRET}", shell=True)
        return f"Shutdown in {DUREE_ARRET} s (ANNULER to cancel)"
    if cmd == "ANNULER":
        subprocess.Popen("shutdown /a", shell=True)
        return "Shutdown cancelled"
    return None


# --------------------------------------------------------------------------
# Préférences gardées par l'agent (Phase 7)
# --------------------------------------------------------------------------
def charger_preferences():
    try:
        p = json.loads(FICHIER_PREFERENCES.read_text(encoding="utf-8"))
        return p if isinstance(p, dict) else {}
    except (OSError, ValueError):
        return {}


def ecrire_preferences(p):
    provisoire = FICHIER_PREFERENCES.with_suffix(".tmp")
    provisoire.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(provisoire, FICHIER_PREFERENCES)


# --------------------------------------------------------------------------
# Écran noir sans veille (Phase 7)
# --------------------------------------------------------------------------
class EcranNoir:
    """Rend tous les écrans noirs SANS mettre le PC en veille (il reste joignable).

    - une fenêtre noire plein écran sur chaque écran (étendu, 2e écran seul…), au premier plan,
      invisible pour les captures d'écran (l'aperçu du téléphone montre le vrai écran) ;
    - luminosité à 0 (écran du portable, et écrans externes qui l'acceptent) ;
    - Windows est prié de ne pas s'endormir tant que l'écran noir est actif ;
    - toucher le vrai clavier ou la vraie souris du PC rallume tout (le téléphone, lui, peut
      piloter le PC sans rallumer l'écran : bouton « Rallumer » de l'app).
    Tkinter n'accepte d'être utilisé que depuis un seul fil : tout passe par une file.
    """

    def __init__(self, fin_de_session=None):
        self.actif = False
        self.probleme = ""
        self._file = queue.Queue()
        self._fenetres = []
        self._depuis = 0.0
        self._fin_de_session = fin_de_session
        self._restaurer_luminosite()  # l'agent s'était arrêté pendant un écran noir
        threading.Thread(target=self._fil, daemon=True).start()

    # appelées par les autres fils
    def allumer_noir(self):
        self._file.put(True)

    def eteindre_noir(self):
        self._file.put(False)

    # --- fil de Tkinter ---
    def _fil(self):
        try:
            import tkinter as tk
            self._tk = tk
            self._racine = tk.Tk()
            self._racine.withdraw()
            if self._fin_de_session is not None:
                # Windows prévient les fenêtres quand la session se ferme (arrêt du PC)
                self._racine.protocol("WM_SAVE_YOURSELF", self._fin_de_session)
            self._racine.after(100, self._verifier)
            self._racine.mainloop()
        except Exception as e:
            self.probleme = f"Black screen unavailable: {e}"
            print(f"[agent] {self.probleme}")

    def _verifier(self):
        try:
            while True:
                demande = self._file.get_nowait()
                if demande and not self.actif:
                    self._noir()
                elif not demande and self.actif:
                    self._rallumer()
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[agent] écran noir : {e}")
        # quelqu'un touche le vrai clavier / la vraie souris du PC : on rallume
        # (pas pour les actions du téléphone : on peut piloter le PC avec l'écran noir)
        if (self.actif and time.time() - self._depuis > 1.5 and inactivite() < 0.5
                and time.time() - INJECTION["t"] > 1.0):
            self._rallumer()
        self._racine.after(100, self._verifier)

    def _noir(self):
        tk = self._tk
        u = ctypes.windll.user32
        for x, y, w, h in moniteurs_windows():
            f = tk.Toplevel(self._racine)
            f.overrideredirect(True)
            f.configure(bg="black", cursor="none")
            f.geometry(f"{w}x{h}+{x}+{y}")
            f.attributes("-topmost", True)
            f.update_idletasks()
            try:
                hwnd = u.GetAncestor(f.winfo_id(), 2) or f.winfo_id()  # GA_ROOT
                u.SetWindowDisplayAffinity(hwnd, 0x11)  # WDA_EXCLUDEFROMCAPTURE
            except Exception:
                pass
            self._fenetres.append(f)
        # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED : pas de veille tant que
        # ce fil le demande (l'écran reste « allumé » pour Windows, mais noir et sans lumière)
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)
        self._depuis = time.time()
        self.actif = True
        threading.Thread(target=self._luminosite_a_zero, daemon=True).start()
        print("[agent] écran noir")

    def _rallumer(self):
        for f in self._fenetres:
            try:
                f.destroy()
            except Exception:
                pass
        self._fenetres = []
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)  # retour à la normale
        self.actif = False
        threading.Thread(target=self._restaurer_luminosite, daemon=True).start()
        print("[agent] écran rallumé")

    @staticmethod
    def _luminosite_a_zero():
        if sbc is None:
            return
        try:
            avant = sbc.get_brightness()
            avant = avant if isinstance(avant, list) else [avant]
            p = charger_preferences()
            p["luminosite_avant_noir"] = avant
            ecrire_preferences(p)
            for i in range(len(avant)):
                try:
                    sbc.set_brightness(0, display=i)
                except Exception:
                    pass  # écran externe sans réglage (la fenêtre noire suffit)
        except Exception as e:
            print(f"[agent] luminosité (écran noir) : {e}")

    @staticmethod
    def _restaurer_luminosite():
        p = charger_preferences()
        avant = p.pop("luminosite_avant_noir", None)
        if not avant or sbc is None:
            return
        for i, v in enumerate(avant):
            try:
                sbc.set_brightness(max(10, int(v)), display=i)
            except Exception:
                pass
        try:
            ecrire_preferences(p)
        except OSError:
            pass


# --------------------------------------------------------------------------
# Raccourcis (Phase 7) : une suite d'étapes lancée d'un seul appui sur le téléphone
# --------------------------------------------------------------------------
VERROU_RACCOURCIS = threading.Lock()
TYPES_ETAPES = ("touches", "texte", "entree", "commande", "app", "pause", "action")
ICONES_RACCOURCIS = ("eclair", "jeu", "terminal", "clavier", "musique", "web", "dossier", "etoile")
RACCOURCIS_DEFAUT = [
    {"nom": "Ctrl + 6", "icone": "clavier", "etapes": [{"type": "touches", "valeur": "ctrl+6"}]},
]


def charger_raccourcis():
    with VERROU_RACCOURCIS:
        if not FICHIER_RACCOURCIS.exists():
            FICHIER_RACCOURCIS.write_text(json.dumps(RACCOURCIS_DEFAUT, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
        try:
            liste = json.loads(FICHIER_RACCOURCIS.read_text(encoding="utf-8"))
        except ValueError:
            return []
    return [r for r in liste if isinstance(r, dict) and r.get("nom")] if isinstance(liste, list) else []


def _ecrire_raccourcis(liste):
    with VERROU_RACCOURCIS:
        provisoire = FICHIER_RACCOURCIS.with_suffix(".tmp")
        provisoire.write_text(json.dumps(liste, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(provisoire, FICHIER_RACCOURCIS)


def _trouver_raccourci(liste, nom):
    nom = str(nom).strip().lower()
    for i, r in enumerate(liste):
        if str(r.get("nom", "")).lower() == nom:
            return i
    return None


def valider_raccourci(d):
    """Vérifie un raccourci venu du téléphone. Renvoie (ok, texte, raccourci propre)."""
    if not isinstance(d, dict):
        return False, "Invalid shortcut", None
    nom = " ".join(str(d.get("nom", "")).split())
    if not nom or len(nom) > 30 or any(ord(c) < 32 for c in nom) or '"' in nom:
        return False, "Name empty, too long (30 max) or with quotes", None
    icone = str(d.get("icone", "eclair"))
    if icone not in ICONES_RACCOURCIS:
        icone = "eclair"
    brutes = d.get("etapes")
    if not isinstance(brutes, list) or not brutes:
        return False, "Add at least one step", None
    if len(brutes) > 20:
        return False, "20 steps maximum", None
    etapes = []
    for n, e in enumerate(brutes, 1):
        if not isinstance(e, dict) or e.get("type") not in TYPES_ETAPES:
            return False, f"Step {n}: unknown type", None
        t = e["type"]
        v = str(e.get("valeur", ""))
        propre = {"type": t, "valeur": v}
        if t == "touches":
            if lire_touches(v) is None:
                return False, f"Step {n}: unknown keys '{v}' (e.g. ctrl+6, win+x)", None
        elif t == "texte":
            if not v or len(v) > 500:
                return False, f"Step {n}: text empty or too long", None
        elif t == "entree":
            propre["valeur"] = ""
        elif t == "commande":
            if not v.strip() or len(v) > 2000:
                return False, f"Step {n}: command empty or too long", None
            propre["shell"] = "cmd" if e.get("shell") == "cmd" else "powershell"
            propre["visible"] = bool(e.get("visible", True))
        elif t == "app":
            if not v.strip():
                return False, f"Step {n}: pick an app", None
        elif t == "pause":
            try:
                ms = int(float(v))
            except ValueError:
                return False, f"Step {n}: pause in milliseconds (e.g. 1500)", None
            if not 0 <= ms <= 30000:
                return False, f"Step {n}: pause from 0 to 30000 ms", None
            propre["valeur"] = str(ms)
        elif t == "action":
            if not v.strip() or len(v) > 200 or v.strip().upper().startswith("RAC"):
                return False, f"Step {n}: invalid action", None
        etapes.append(propre)
    return True, "", {"nom": nom, "icone": icone, "etapes": etapes}


def ajouter_raccourci(d, ancien=""):
    """Ajoute ou modifie un raccourci. [ancien] = nom avant modification (renommage)."""
    ok, texte, propre = valider_raccourci(d)
    if not ok:
        return False, texte
    liste = charger_raccourcis()
    remplace = False
    for nom in {str(ancien or ""), propre["nom"]}:
        i = _trouver_raccourci(liste, nom) if nom else None
        if i is not None:
            del liste[i]
            remplace = True
    liste.append(propre)
    _ecrire_raccourcis(liste)
    return True, ("Shortcut updated: " if remplace else "Shortcut added: ") + propre["nom"]


def retirer_raccourci(nom):
    liste = charger_raccourcis()
    i = _trouver_raccourci(liste, nom)
    if i is None:
        return False, f"Unknown shortcut: {nom}"
    nom = liste[i]["nom"]
    del liste[i]
    _ecrire_raccourcis(liste)
    return True, f"Shortcut removed: {nom}"


def lancer_commande(commande, shell, visible, titre):
    """Lance une commande en administrateur (l'agent l'est déjà : pas de fenêtre UAC).
    Visible : une fenêtre PowerShell / cmd reste ouverte pour voir le résultat.
    Cachée : l'agent attend la fin (2 min max) avant l'étape suivante."""
    if shell == "cmd":
        args = f'cmd.exe {"/k" if visible else "/c"} {commande}'
    else:
        if visible:
            titre = titre.replace("'", "''")
            commande = f"$host.UI.RawUI.WindowTitle = 'Dadou: {titre}'\n" + commande
        code = base64.b64encode(commande.encode("utf-16-le")).decode("ascii")
        args = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass"]
        args += ["-NoExit"] if visible else []
        args += ["-EncodedCommand", code]
    flags = 0x00000010 if visible else 0x08000000  # nouvelle console / sans fenêtre
    p = subprocess.Popen(args, creationflags=flags, cwd=os.path.expanduser("~"))
    if not visible:
        try:
            p.wait(timeout=120)
        except subprocess.TimeoutExpired:
            return "toujours en cours après 2 min"
        if p.returncode:
            return f"code de sortie {p.returncode}"
    return ""


def derouler_raccourci(r, executer):
    """Exécute les étapes une par une (dans un fil à part). executer(ligne) = commande Dadou."""
    print(f"[agent] raccourci : {r['nom']}")
    for n, e in enumerate(r["etapes"], 1):
        t, v = e["type"], e.get("valeur", "")
        try:
            if t == "touches":
                touches_pc(v)
            elif t == "texte":
                taper_pc(v)
            elif t == "entree":
                touches_pc("enter")
            elif t == "commande":
                probleme = lancer_commande(v, e.get("shell", "powershell"), e.get("visible", True),
                                           r["nom"])
                if probleme:
                    print(f"[agent] raccourci {r['nom']}, étape {n} : {probleme}")
            elif t == "app":
                apps = charger_apps()
                nom = trouver_app(apps, v)
                if nom is None:
                    print(f"[agent] raccourci {r['nom']}, étape {n} : app inconnue {v}")
                else:
                    lancer_app(apps[nom])
            elif t == "pause":
                time.sleep(min(30.0, int(v) / 1000))
                continue
            elif t == "action":
                executer(v)
        except Exception as ex:
            print(f"[agent] raccourci {r['nom']}, étape {n} ({t}) : {ex!r}")
        time.sleep(0.15)  # laisse Windows suivre entre deux étapes


# --------------------------------------------------------------------------
# Aperçu de l'écran (Phase 8)
# --------------------------------------------------------------------------
class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def _ecrans_mss(sct):
    """Écrans dans l'ordre de Windows (sct.monitors[0] = tous les écrans ensemble)."""
    return sct.monitors[1:] or sct.monitors[:1]


def _dessiner_curseur(img, x, y):
    """Petite flèche blanche bordée de noir là où est la souris."""
    t = max(14, img.width // 60)
    pts = [(x, y), (x, y + t), (x + t * 0.28, y + t * 0.72), (x + t * 0.72, y + t * 0.72)]
    d = ImageDraw.Draw(img)
    d.polygon(pts, fill=(255, 255, 255), outline=(0, 0, 0))


def capture_ecran(ecran=0, largeur=960, qualite=60):
    """Capture un écran en JPEG pour le téléphone. Renvoie (octets, infos) ou (None, problème)."""
    if mss is None:
        return None, "Preview unavailable: mss and Pillow are missing on the PC"
    try:
        with mss.mss() as sct:
            ecrans = _ecrans_mss(sct)
            i = max(0, min(len(ecrans) - 1, int(ecran)))
            m = ecrans[i]
            brut = sct.grab(m)
        img = Image.frombytes("RGB", brut.size, brut.bgra, "raw", "BGRX")
        w, h = brut.size
        largeur = max(320, min(2560, int(largeur)))
        echelle = 1.0
        if w > largeur:
            echelle = largeur / w
            img = img.resize((largeur, max(1, round(h * echelle))), Image.BILINEAR)
        pt = _POINT()
        if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
            cx, cy = pt.x - m["left"], pt.y - m["top"]
            if 0 <= cx < w and 0 <= cy < h:
                _dessiner_curseur(img, cx * echelle, cy * echelle)
        sortie = io.BytesIO()
        img.save(sortie, "JPEG", quality=max(20, min(90, int(qualite))))
        infos = {"ecran": i, "ecrans": len(ecrans), "largeur": w, "hauteur": h,
                 "verrou": pc_verrouille()}
        return sortie.getvalue(), infos
    except Exception as e:
        return None, f"Capture failed: {e}"


def pointeur_pc(ecran, x, y, clic=""):
    """Place la souris à (x, y) (de 0 à 1 sur l'écran choisi), puis clique si demandé."""
    if mss is not None:
        with mss.mss() as sct:
            ecrans = _ecrans_mss(sct)
            m = ecrans[max(0, min(len(ecrans) - 1, int(ecran)))]
            gauche, haut, w, h = m["left"], m["top"], m["width"], m["height"]
    else:
        ecrans = moniteurs_windows()
        gauche, haut, w, h = ecrans[max(0, min(len(ecrans) - 1, int(ecran)))]
    x = max(0.0, min(1.0, float(x)))
    y = max(0.0, min(1.0, float(y)))
    INJECTION["t"] = time.time()
    ctypes.windll.user32.SetCursorPos(gauche + round(x * (w - 1)), haut + round(y * (h - 1)))
    if clic in ("gauche", "droit"):
        time.sleep(0.02)
        clic_pc(clic)
    elif clic == "double":
        time.sleep(0.02)
        clic_pc("gauche")
        time.sleep(0.06)
        clic_pc("gauche")


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
        self.jeux = DetecteurJeu()   # Phase 9 : jeux hors Steam
        self.video = DetecteurVideo()  # Phase 10 : scène cinéma
        self.stats = StatsJeux()       # Phase 10 : temps de jeu par jeu
        self.master = SuiviMaster(DOSSIER)  # Phase 11 : suivi du master
        self.media = LecteurMedia()          # Phase 11-bis : position de la vidéo
        self.video_pos = None
        self.arret_fin = 0.0     # heure prévue de l'arrêt du PC (0 = pas d'arrêt)
        self.lum_esp = max(5, min(100, int(charger_preferences().get("lum_esp", 85))))
        self.lent["ecrans"] = 1
        self.noir = EcranNoir(fin_de_session=self._fin_de_session)

    def _fin_de_session(self):
        """Windows ferme la session (arrêt ou redémarrage, même lancé depuis le menu Démarrer) :
        l'ESP32 dit au revoir puis s'éteint quand les données s'arrêtent."""
        print("[agent] fin de session Windows : au revoir")
        self.liaison.muet = False
        self.liaison.envoyer("EVT ARRET -1")

    def arret_reste(self):
        reste = round(self.arret_fin - time.time())
        return reste if self.arret_fin and reste > 0 else -1

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
        self.prochaine_connexion = 0.0
        tour_avant = time.time()
        while self.actif:
            debut = time.time()
            try:
                tour = self._tour_mesures(tour, debut, tour_avant)
            except Exception as e:  # une mesure qui plante ne doit jamais arrêter l'agent
                print(f"[agent] erreur dans la boucle des mesures : {e!r}")
                tour += 1
                time.sleep(1)
            tour_avant = debut
            time.sleep(max(0.0, 0.25 - (time.time() - debut)))

    def _tour_mesures(self, tour, debut, tour_avant):
        self._surveiller_reveil(debut - tour_avant)
        # --- liaison avec l'ESP32 (les mesures continuent même sans elle, pour l'app) ---
        if FICHIER_PAUSE.exists():
            if self.liaison.ser is not None:
                self.liaison.fermer()
                print("[agent] pause : port COM libéré")
        elif self.liaison.ser is None and debut >= self.prochaine_connexion:
            if self.liaison.connecter():
                if tour > 0:
                    self._reveil_discret("liaison USB revenue")
                self.precedent = {}  # renvoie tous les états après reconnexion
                self.dernier_temps = 0.0
                self.meteo_envoyee = -1
            else:
                self.prochaine_connexion = debut + 3

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
            "arret": self.arret_reste(), "ecran_noir": self.noir.actif,
            "lum_esp": self.lum_esp, "ecrans": self.lent["ecrans"],
            # Phase 11
            "video": "" if p.get("VIDEO", "-") == "-" else p.get("VIDEO", "").split("|")[0],
            "video_titre": p.get("VIDEO", "").partition("|")[2],
            "video_pos": self.video_pos["pos"] if self.video_pos else -1,
            "video_duree": self.video_pos["duree"] if self.video_pos else -1,
            "video_lecture": bool(self.video_pos and self.video_pos["lecture"]),
            "inactif": int(p.get("INACTIF", "0") or 0),
            "jeu_total": p.get("JEU_TOTAL", -1),
            "master_v": self.master.version, "master_actif": self.master.actif,
        }
        return tour + 1

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
        self.lent["ecrans"] = len(moniteurs_windows())
        # luminosité de l'ESP32 et arrêt en cours : renvoyés après chaque (re)connexion
        if self.precedent.get("LUM_ESP") != self.lum_esp:
            self.precedent["LUM_ESP"] = self.lum_esp
            self.liaison.envoyer(f"LUM_ESP {self.lum_esp}")
        reste = self.arret_reste()
        if self.precedent.get("ARRET") != (reste > 0):
            self.precedent["ARRET"] = reste > 0
            if reste > 0:
                self.liaison.envoyer(f"EVT ARRET {reste}")
        if self.meteo.a_mettre_a_jour():
            self.meteo.lancer()
        if self.meteo.jours and self.meteo_envoyee != self.meteo.version:
            self.meteo_envoyee = self.meteo.version
            for ligne in self.meteo.lignes():
                self.liaison.envoyer(ligne)
        for nom, outil in (("LibreHardwareMonitor", self.lhm), ("PresentMon", self.fps),
                           ("Météo", self.meteo), ("Lecteur média", self.media)):
            if outil.probleme != self.problemes.get(nom):
                self.problemes[nom] = outil.probleme
                print(f"[agent] {nom} : {outil.probleme or 'OK'}")
        nom, externe = sortie_audio()
        jeu = self.jeux.jeu(gpu()[1])
        verrou = pc_verrouille()
        # Phase 10 : vidéo au premier plan, PC allumé mais inutilisé (en minutes, 0 = utilisé)
        video = "" if (jeu or verrou) else self.video.video()
        # Phase 11-bis : position de la vidéo (contrôles multimédias de Windows)
        media = self.media.actuel() if video else None
        if media and "|" not in video and media["titre"]:
            video += "|" + texte_ascii(media["titre"]).replace("|", "/")[:90]
        self.video_pos = media
        position = f'{media["pos"]} {media["duree"]} {1 if media["lecture"] else 0}' if media else "-"
        if self.precedent.get("VIDEO_POS") != position:
            self.precedent["VIDEO_POS"] = position
            self.liaison.envoyer(f"EVT VIDEO_POS {position}")
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

    # --------------------------------------------------------------- pour l'app
    def executer(self, ligne):
        """Exécute une commande venant de la console ou de l'app. Renvoie un texte."""
        ligne = ligne.strip()
        if not ligne:
            return ""
        mots = ligne.split(" ", 1)
        cmd = mots[0].upper()
        arg = mots[1].strip() if len(mots) > 1 else ""
        self.reprendre()
        special = self._executer_special(cmd, arg)
        if special is not None:
            return special
        reponse = executer_pc(ligne)
        if reponse is not None:
            if cmd not in ("APPS", "AUDIO"):
                self.liaison.envoyer("EVT ACTION " + texte_ascii(ligne))
            return reponse
        if cmd == "ECRAN_ESP":
            self.ecran_esp = ligne.split(" ", 1)[-1].strip() != "0"
        else:
            INJECTION["t"] = time.time()  # touches / souris par l'ESP32 : action du téléphone
        if self.liaison.envoyer(ligne):
            return "Sent to the ESP32"
        return "ESP32 not connected"

    def _executer_special(self, cmd, arg):
        """Commandes qui ont besoin de l'état de l'agent (Phase 7). None = pas pour moi."""
        if cmd in ("ECRAN_OFF", "ECRAN_ON", "ECRAN_BASCULE"):
            allumer_noir = cmd == "ECRAN_OFF" or (cmd == "ECRAN_BASCULE" and not self.noir.actif)
            if self.noir.probleme:
                return self.noir.probleme
            if allumer_noir:
                self.noir.allumer_noir()
                self.liaison.envoyer("EVT ACTION ECRAN_OFF")
                return "PC screen black (the PC stays on and reachable)"
            self.noir.eteindre_noir()
            self.liaison.envoyer("EVT ACTION ECRAN_ON")
            return "PC screen back on"
        if cmd == "VEILLE" and self.noir.actif:
            self.noir.eteindre_noir()
            time.sleep(0.3)
            return None  # puis la vraie mise en veille (executer_pc)
        if cmd == "ARRET":
            reste = self.arret_reste()
            if reste > 0:
                return f"Shutdown already planned in {reste} s"
            texte = executer_pc("ARRET")
            self.arret_fin = time.time() + DUREE_ARRET
            self.precedent["ARRET"] = True
            self.liaison.envoyer(f"EVT ARRET {DUREE_ARRET}")
            return texte
        if cmd == "ANNULER":
            texte = executer_pc("ANNULER")
            self.arret_fin = 0.0
            self.precedent["ARRET"] = False
            self.liaison.envoyer("EVT ARRET 0")
            return texte
        if cmd == "LUM_ESP":
            try:
                self.lum_esp = max(5, min(100, int(float(arg))))
            except ValueError:
                return "Use: LUM_ESP 5..100"
            p = charger_preferences()
            p["lum_esp"] = self.lum_esp
            try:
                ecrire_preferences(p)
            except OSError:
                pass
            self.precedent["LUM_ESP"] = self.lum_esp
            self.liaison.envoyer(f"LUM_ESP {self.lum_esp}")
            return f"ESP32 brightness: {self.lum_esp} %"
        if cmd == "RAC":
            return self.lancer_raccourci(arg)
        return None

    def lancer_raccourci(self, nom):
        liste = charger_raccourcis()
        i = _trouver_raccourci(liste, nom)
        if i is None:
            return f"Unknown shortcut: {nom}"
        r = liste[i]
        self.liaison.envoyer("EVT ACTION RAC " + texte_ascii(r["nom"]))
        threading.Thread(target=derouler_raccourci, args=(r, self.executer), daemon=True).start()
        return f"Shortcut: {r['nom']}"

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
            return False, f"jeux.json not saved: {e}"
        self.jeux.listes_lues = 0.0  # relu à la prochaine seconde
        return True, "Game list saved"

    def pas_un_jeu(self):
        """Le jeu détecté hors Steam n'en est pas un : son .exe va dans « pas_des_jeux »."""
        exe = self.jeux.exe
        if not exe:
            return False, "No non-Steam game running (a Steam game cannot be removed)"
        jeux, pas = charger_jeux()
        ok, texte = self.jeux_maj([n for n in jeux if n != exe], sorted(pas | {exe}))
        return ok, (f"{exe} will no longer count as a game" if ok else texte)

    def etat_court(self):
        """Pour la notification Android « PC inutilisé » (GET /etat_court)."""
        p = self.precedent
        return {"repos_min": int(inactivite() // 60), "verrou": p.get("VERROU") == "1",
                "jeu": "" if p.get("JEU", "-") == "-" else p.get("JEU"),
                "video": "" if p.get("VIDEO", "-") == "-" else p.get("VIDEO", "").split("|")[0],
                "arret": self.arret_reste()}

    def sites_pour_app(self):
        """Sites vidéo de l'app, sites reconnus d'office et titre de l'onglet ouvert sur le PC."""
        hwnd, pid = fenetre_premier_plan()
        onglet = ""
        if hwnd and pid:
            try:
                if psutil.Process(pid).name().lower() in NAVIGATEURS:
                    onglet = titre_fenetre(hwnd)[:150]
            except psutil.Error:
                pass
        _SITES_PERSO["lu"] = 0.0
        return {"perso": [{"mot": m, "nom": n} for m, n in sites_perso()],
                "defaut": [{"mot": m, "nom": n} for m, n in SITES_VIDEO], "onglet": onglet}

    def sites_maj(self, liste):
        """Enregistre tools\\agent\\sites_video.json (liste modifiée dans l'app)."""
        propres = []
        for s in liste if isinstance(liste, list) else []:
            if not isinstance(s, dict):
                continue
            mot = str(s.get("mot", "")).strip().lower()[:40]
            nom = str(s.get("nom", "")).strip()[:20]
            if len(mot) >= 3 and nom and mot not in [p["mot"] for p in propres]:
                propres.append({"mot": mot, "nom": nom})
        try:
            FICHIER_SITES.write_text(json.dumps(propres[:50], ensure_ascii=False, indent=1),
                                     encoding="utf-8")
        except OSError as e:
            return False, f"sites_video.json not saved: {e}"
        _SITES_PERSO["lu"] = 0.0
        return True, "Video sites saved"

    def master_afficher(self):
        self.liaison.envoyer("MASTER_INFO " + json.dumps(["lunettes", "Master check-in"]))
        return True, "Master scene shown on the ESP32"

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
            "raccourcis": charger_raccourcis,
            "ajouter_raccourci": ajouter_raccourci, "retirer_raccourci": retirer_raccourci,
            "afficher_pin": afficher_pin,
            "souris": souris_pc, "clic": clic_pc, "molette": molette_pc,
            "texte": texte, "connexion": connexion,
            "apercu": capture_ecran, "pointeur": pointeur_pc,
            "master": self.master.pour_app, "master_maj": self.master.maj,
            "master_afficher": self.master_afficher,
            "jeux": self.jeux_pour_app, "jeux_maj": self.jeux_maj, "pas_un_jeu": self.pas_un_jeu,
            "etat_court": self.etat_court,
            "sites": self.sites_pour_app, "sites_maj": self.sites_maj,
        }

    def boucle_lecture(self):
        while self.actif:
            try:
                self._lire_esp()
            except Exception as e:  # ne doit jamais s'arrêter : sinon l'ESP32 n'est plus lue
                print(f"[agent] erreur de lecture de l'ESP32 : {e!r}")
                time.sleep(1)

    def _lire_esp(self):
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

    # Pixels réels sur chaque écran (écran noir et aperçu justes même avec la mise à l'échelle)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    if args.service:
        journal = open(FICHIER_LOG, "a", encoding="utf-8", buffering=1)
        sys.stdout = journal
        sys.stderr = journal
        print(f"--- démarrage {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
        faulthandler.enable(file=journal, all_threads=True)  # plantage natif : ligne exacte dans le journal

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
