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

DOSSIER = Path(__file__).resolve().parent
FICHIER_APPS = DOSSIER / "apps.json"
FICHIER_PAUSE = DOSSIER / "PAUSE"
FICHIER_LOG = DOSSIER / "agent.log"
FICHIER_REGLAGES = DOSSIER / "reglages.json"
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
            self.reessayer_a = time.time() + 10
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
        self.dernier_gpu = ""
        self.dernier_perf = ""
        self.precedent = {}
        self.problemes = {}
        self.dernier_temps = 0.0
        self.meteo = Meteo()
        self.meteo_envoyee = -1
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
        while self.actif:
            if FICHIER_PAUSE.exists():
                if self.liaison.ser is not None:
                    self.liaison.fermer()
                    print("[agent] pause : port COM libéré")
                time.sleep(1)
                continue
            if self.liaison.ser is None:
                if not self.liaison.connecter():
                    time.sleep(3)
                    continue
                self.precedent = {}  # renvoie tous les états après reconnexion
                self.dernier_temps = 0.0
                self.meteo_envoyee = -1
            if time.time() - self.dernier_temps > 60:
                self.dernier_temps = time.time()
                lt = time.localtime()
                self.liaison.envoyer(f"TEMPS {lt.tm_year} {lt.tm_mon} {lt.tm_mday} {lt.tm_wday} "
                                     f"{lt.tm_hour} {lt.tm_min} {lt.tm_sec}")
            cpu = round(psutil.cpu_percent(interval=None))
            ram = round(psutil.virtual_memory().percent)
            bat, charge = batterie()
            self.dernier_stat = f"STAT {cpu} {ram} {volume()} {bat} {charge}"
            self.liaison.envoyer(self.dernier_stat)

            t, u, mem = gpu()
            self.dernier_gpu = f"GPU {t} {u} {mem}"
            self.liaison.envoyer(self.dernier_gpu)

            en_jeu = self.precedent.get("JEU", "-") != "-"
            fps = self.fps.fps() if en_jeu else -1
            self.dernier_perf = f"PERF {self.lhm.temperature_cpu()} {fps}"
            self.liaison.envoyer(self.dernier_perf)
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
            etats = {
                "CASQUE": nom_court_audio(nom) if externe else "-",
                "MANETTE": "1" if manette_connectee() else "0",
                "VERROU": "1" if pc_verrouille() else "0",
                "JEU": texte_ascii(jeu_steam(), "Jeu") if jeu_steam() else "-",
            }
            for cle, valeur in etats.items():
                if self.precedent.get(cle) != valeur:
                    self.precedent[cle] = valeur
                    self.liaison.envoyer(f"EVT {cle} {valeur}")
                    print(f"[agent] événement : {cle} = {valeur}")
            time.sleep(1)

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
                print("LibreHardwareMonitor :", self.lhm.probleme or "OK",
                      "| PresentMon :", self.fps.probleme or "OK",
                      "| administrateur :", "oui" if est_admin() else "non")
                continue
            if ligne.upper() == "AUDIO":
                if comtypes is not None:
                    comtypes.CoInitialize()
                print(diagnostic_audio())
                continue
            reponse = executer_pc(ligne)
            if reponse is not None:
                print(reponse)
                if ligne.split(" ", 1)[0].upper() not in ("APPS", "AUDIO"):
                    # la mascotte réagit sur l'écran de l'ESP32
                    self.liaison.envoyer("EVT ACTION " + texte_ascii(ligne))
            elif not self.liaison.envoyer(ligne):
                print("ESP32 non connectée")
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
    threading.Thread(target=agent.boucle_lecture, daemon=True).start()
    if args.service:
        while True:
            time.sleep(3600)
    agent.console()


if __name__ == "__main__":
    main()
