# État du code — Micro

Mis à jour : 2026-11-01 (fin de Phase 2-bis : casque, jeu Steam et GPU ; inclut la Phase 2, agent PC)

## Arborescence

Fichiers suivis par Git (sans `bin/`, `build/`, `.dart_tool/`, `.idea/`, `__pycache__/`, `local.properties`) :

```
Micro/
├── .claude/
│   └── settings.json
├── app/
│   ├── android/
│   │   ├── app/
│   │   │   ├── src/
│   │   │   │   ├── debug/
│   │   │   │   │   └── AndroidManifest.xml
│   │   │   │   ├── main/
│   │   │   │   │   ├── kotlin/
│   │   │   │   │   │   └── com/
│   │   │   │   │   │       └── mmdigitek/
│   │   │   │   │   │           └── esp_micro/
│   │   │   │   │   │               └── MainActivity.kt
│   │   │   │   │   ├── res/
│   │   │   │   │   │   ├── drawable/
│   │   │   │   │   │   │   └── launch_background.xml
│   │   │   │   │   │   ├── drawable-v21/
│   │   │   │   │   │   │   └── launch_background.xml
│   │   │   │   │   │   ├── mipmap-hdpi/
│   │   │   │   │   │   │   └── ic_launcher.png
│   │   │   │   │   │   ├── mipmap-mdpi/
│   │   │   │   │   │   │   └── ic_launcher.png
│   │   │   │   │   │   ├── mipmap-xhdpi/
│   │   │   │   │   │   │   └── ic_launcher.png
│   │   │   │   │   │   ├── mipmap-xxhdpi/
│   │   │   │   │   │   │   └── ic_launcher.png
│   │   │   │   │   │   ├── mipmap-xxxhdpi/
│   │   │   │   │   │   │   └── ic_launcher.png
│   │   │   │   │   │   ├── values/
│   │   │   │   │   │   │   └── styles.xml
│   │   │   │   │   │   └── values-night/
│   │   │   │   │   │       └── styles.xml
│   │   │   │   │   └── AndroidManifest.xml
│   │   │   │   └── profile/
│   │   │   │       └── AndroidManifest.xml
│   │   │   └── build.gradle.kts
│   │   ├── gradle/
│   │   │   └── wrapper/
│   │   │       └── gradle-wrapper.properties
│   │   ├── .gitignore
│   │   ├── build.gradle.kts
│   │   ├── gradle.properties
│   │   └── settings.gradle.kts
│   ├── lib/
│   │   └── main.dart
│   ├── test/
│   │   └── widget_test.dart
│   ├── .gitignore
│   ├── .metadata
│   ├── analysis_options.yaml
│   ├── pubspec.lock
│   ├── pubspec.yaml
│   └── README.md
├── docs/
│   ├── etat_code.md
│   ├── etat_du_projet.md
│   ├── etat_micro.md
│   ├── mascotte_expressions.md
│   ├── micro_phase0.md
│   ├── micro_phase1_clavier.md
│   ├── micro_phase2_agent.md
│   └── micro_phase2_bis.md
├── esp/
│   ├── lib/
│   │   ├── hid_pc.py
│   │   └── lcd.py
│   └── main.py
├── tools/
│   ├── agent/
│   │   ├── agent_pc.py
│   │   └── apps.json
│   └── pc_test.py
├── .gitignore
└── CLAUDE.md
```

`bin/` (ignoré par Git) contient `ESP32_GENERIC_S3-SPIRAM_OCT-20260824-v1.29.0.bin`.

## Versions

| Outil | Version |
|---|---|
| esptool | 5.6.0 |
| mpremote | 1.29.0 |
| MicroPython sur la carte | v1.29.0 (2026-08-24), ESP32_GENERIC_S3-SPIRAM_OCT |
| usb-device-hid (mip, sur la carte) | 0.2.0 (fichiers `.mpy`) |
| Flutter | 3.47.2 (stable), Dart 3.13.2 |

Dépendances PC de l'agent (`pip install --user`) :

| Paquet | Version |
|---|---|
| pyserial | 3.5 |
| psutil | 7.2.2 |
| pycaw | 20260927 |
| comtypes | 1.4.17 |
| screen-brightness-control | 0.27.2 |
| nvidia-ml-py (module `pynvml`) | 13.615.71 |

## Port série

- **COM4** (USB 303a:4001), inchangé (`py -m mpremote devs`).
- Pendant le flash de la Phase 0 (bootloader) : COM3 (303a:1001).
- Un seul programme à la fois sur COM4 : l'agent (`agent_pc.py`), `pc_test.py` ou mpremote.

## Fichiers sur la carte

```
ls :/
         139 boot.py
           0 lib/
        4624 main.py
ls :/lib
        6040 hid_pc.py
        4071 lcd.py
           0 usb/
ls :/lib/usb/device
          97 __init__.mpy
        4411 core.mpy
        1569 hid.mpy
```

Vérification (Phase 2-bis, étape 4) : `py -m mpremote connect COM4 fs cat :main.py` contient bien `    if cmd == "GPU":`.

## Installation de usb-device-hid (Phase 1, étape 4)

```
Install usb-device-hid
Installing usb-device-hid (latest) from https://micropython.org/pi/v2 to /lib
Installing: /lib/usb/device/__init__.mpy
Installing: /lib/usb/device/core.mpy
Installing: /lib/usb/device/hid.mpy
Done
```

## Réponses de la carte (Phase 1, étape 6)

```
> py -X utf8 tools\pc_test.py COM4 --cmd PING
  -> PONG
> py -X utf8 tools\pc_test.py COM4 --cmd "VOL+"
  -> OK
```

## Périphériques Windows 303A (Phase 1, étape 7)

`Get-PnpDevice -PresentOnly -Class Keyboard,Mouse,HIDClass`, lignes contenant 303A :

```
Status Class    FriendlyName                          InstanceId
------ -----    ------------                          ----------
OK     Keyboard HID Keyboard Device                   HID\VID_303A&PID_4001&MI_02&COL01\7&24098D10&0&0000
OK     Mouse    HID-compliant mouse                   HID\VID_303A&PID_4001&MI_02&COL02\7&24098D10&0&0001
OK     HIDClass HID-compliant consumer control device HID\VID_303A&PID_4001&MI_02&COL03\7&24098D10&0&0002
OK     HIDClass USB Input Device                      USB\VID_303A&PID_4001&MI_02\6&32EC6B02&0&0002
```

## Réponses de la carte (Phase 2-bis, étape 5)

```
> py -X utf8 tools\pc_test.py COM4 --cmd "GPU 55 40 30"
  -> OK
> py -X utf8 tools\pc_test.py COM4 --cmd "EVT JEU Test"
  -> OK
```

## Test Python rapide (Phase 2-bis, étape 6)

Commande : `py -X utf8 -c "import sys; sys.path.insert(0, r'tools\agent'); import agent_pc as a, pynvml; pynvml.nvmlInit(); print(a.gpu(), repr(a.jeu_steam())); print(a.diagnostic_audio())"`

```
(41, 0, 3) ''
Sorties audio actives (* = par défaut) :
 * Speakers (HECATE G30)  |  indices : USB  |  1309 caractères de propriétés
   Speakers (Steam Streaming Speakers)  |  indices : aucun  |  1270 caractères de propriétés
   Speakers (High Definition Audio Device)  |  indices : HDAUDIO, INTELAUDIO  |  1408 caractères de propriétés
   Speakers (Steam Streaming Microphone)  |  indices : aucun  |  1292 caractères de propriétés
   Microphone Array (Intel® Smart Sound Technology for Digital Microphones)  |  indices : INTELAUDIO  |  1682 caractères de propriétés
   Microphone (HECATE G30)  |  indices : USB  |  1239 caractères de propriétés
   Microphone (Steam Streaming Microphone)  |  indices : aucun  |  1211 caractères de propriétés
Par défaut : 'Speakers (HECATE G30)' -> CASQUE
```

(GPU : 41 °C, 0 %, VRAM 3 % ; aucun jeu Steam lancé ; dongle du casque branché.)

## Trace mpremote (Phase 2-bis, étape 4)

La **première** commande mpremote lancée après qu'un autre programme a utilisé COM4 (agent qu'on vient de fermer, reset, ou `pc_test.py`) a échoué 3 fois avec la même trace. La commande relancée juste après a réussi à chaque fois (la copie de main.py a été faite au 2e essai). Rien n'a été corrigé dans le code.

```
Traceback (most recent call last):
  File "<frozen runpy>", line 203, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "C:\Users\xisda\AppData\Roaming\Python\Python313\site-packages\mpremote\__main__.py", line 6, in <module>
    sys.exit(main.main())
             ~~~~~~~~~^^
  File "C:\Users\xisda\AppData\Roaming\Python\Python313\site-packages\mpremote\main.py", line 622, in main
    handler_func(state, args)
    ~~~~~~~~~~~~^^^^^^^^^^^^^
  File "C:\Users\xisda\AppData\Roaming\Python\Python313\site-packages\mpremote\commands.py", line 381, in do_filesystem
    state.ensure_raw_repl()
    ~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\xisda\AppData\Roaming\Python\Python313\site-packages\mpremote\main.py", line 552, in ensure_raw_repl
    self.transport.enter_raw_repl(soft_reset=soft_reset)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\xisda\AppData\Roaming\Python\Python313\site-packages\mpremote\transport_serial.py", line 202, in enter_raw_repl
    data = self.read_until(1, b"soft reboot\r\n", timeout_overall=timeout_overall)
  File "C:\Users\xisda\AppData\Roaming\Python\Python313\site-packages\mpremote\transport_serial.py", line 158, in read_until
    if self.is_pty or self.serial.inWaiting() > 0:
                      ~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\xisda\AppData\Roaming\Python\Python313\site-packages\serial\serialutil.py", line 594, in inWaiting
    return self.in_waiting
           ^^^^^^^^^^^^^^^
  File "C:\Users\xisda\AppData\Roaming\Python\Python313\site-packages\serial\serialwin32.py", line 259, in in_waiting
    raise SerialException("ClearCommError failed ({!r})".format(ctypes.WinError()))
serial.serialutil.SerialException: ClearCommError failed (PermissionError(13, 'The device does not recognize the command.', None, 22))
```

## esp/main.py

```python
# Phase 1 : l'ESP32 devient clavier + souris + multimédia du PC.
# Les ordres arrivent par le port série USB, une ligne par commande.
import select
import sys
import time

import lcd
from hid_pc import MEDIA, PC

ecran = lcd.Ecran(paysage=True)
pc = PC()
etat_usb = "connexion..."
derniere = "-"
nb = 0
# Valeurs envoyées par le programme PC (agent_pc.py)
stat = {"cpu": -1, "ram": -1, "vol": -1, "bat": -1, "chg": 0}
evt = {"casque": "", "manette": 0, "verrou": 0, "jeu": ""}
gpu = {"temp": -1, "charge": -1, "vram": -1}


def dessiner():
    f = ecran.fb
    f.fill(lcd.NOIR)
    ecran.texte("Telecommande PC", 10, 8, lcd.CYAN, 2)
    couleur_usb = lcd.VERT if etat_usb == "pret" else lcd.ORANGE
    ecran.texte("USB : " + etat_usb, 10, 40, couleur_usb, 2)
    if evt["jeu"]:
        ecran.texte("JEU : " + evt["jeu"][:34], 10, 64, lcd.VERT, 1)
    ecran.texte("GPU %d C  %d%%  VRAM %d%%" % (gpu["temp"], gpu["charge"], gpu["vram"]),
                10, 78, lcd.GRIS, 1)
    ecran.texte(derniere[:19], 10, 92, lcd.BLANC, 2)
    ecran.texte("CPU %d%%  RAM %d%%  Vol %d%%" % (stat["cpu"], stat["ram"], stat["vol"]),
                10, 118, lcd.ORANGE, 1)
    ecran.texte("Batterie %d%%%s" % (stat["bat"], " (en charge)" if stat["chg"] else ""),
                10, 132, lcd.ORANGE, 1)
    ecran.texte("Casque : " + (evt["casque"][:30] or "non"), 10, 146, lcd.CYAN, 1)
    ecran.texte("Manette : %s   Verrou : %s" % ("oui" if evt["manette"] else "non",
                                                "oui" if evt["verrou"] else "non"),
                10, 160, lcd.CYAN, 1)
    ecran.afficher()


dessiner()
etat_usb = "pret" if pc.demarrer() else "pas reconnu"
dessiner()

entree = select.poll()
entree.register(sys.stdin, select.POLLIN)
tampon = ""


def lire_ligne():
    """Renvoie une ligne complète reçue sur le port série, ou None."""
    global tampon
    while entree.poll(0):
        c = sys.stdin.read(1)
        if c in ("\n", "\r"):
            if tampon:
                ligne = tampon
                tampon = ""
                return ligne
        else:
            tampon += c
    return None


def executer(ligne):
    mots = ligne.split(" ", 1)
    cmd = mots[0].upper()
    arg = mots[1] if len(mots) > 1 else ""
    if cmd == "PING":
        return "PONG"
    if cmd == "STAT":
        try:
            v = [int(x) for x in arg.split()]
            stat["cpu"], stat["ram"], stat["vol"], stat["bat"], stat["chg"] = v[:5]
        except ValueError:
            return "ERR utilise : STAT cpu ram vol bat charge"
        return "OK"
    if cmd == "GPU":
        try:
            gpu["temp"], gpu["charge"], gpu["vram"] = [int(x) for x in arg.split()][:3]
        except ValueError:
            return "ERR utilise : GPU temp charge vram"
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
        elif typ == "JEU":
            evt["jeu"] = "" if val in ("", "-") else val
        else:
            return "ERR evenement inconnu : " + typ
        return "OK"
    if etat_usb != "pret" and not pc.is_open():
        return "ERR USB pas reconnu par le PC"
    if cmd == "KEY":
        return "OK" if pc.raccourci(arg) else "ERR touche inconnue : " + arg
    if cmd == "TEXT":
        ignores = pc.taper(arg)
        return "OK" if ignores == 0 else "OK (%d caracteres ignores)" % ignores
    if cmd in MEDIA:
        pc.media(cmd)
        return "OK"
    if cmd == "MOUSE":
        try:
            dx, dy = [int(v) for v in arg.split()]
        except ValueError:
            return "ERR utilise : MOUSE dx dy"
        pc.souris(dx, dy)
        return "OK"
    if cmd == "CLIC":
        pc.clic(1)
        return "OK"
    if cmd == "CLICD":
        pc.clic(2)
        return "OK"
    if cmd == "MOLETTE":
        try:
            pc.souris(molette=int(arg))
        except ValueError:
            return "ERR utilise : MOLETTE n"
        return "OK"
    return "ERR commande inconnue : " + cmd


while True:
    ligne = lire_ligne()
    if ligne:
        reponse = executer(ligne.strip())
        print(reponse)
        if not ligne.startswith(("STAT", "EVT", "GPU")):
            nb += 1
            derniere = ligne.strip()
        if pc.is_open():
            etat_usb = "pret"
        dessiner()
    time.sleep_ms(10)
```

## tools/agent/agent_pc.py

```python
#!/usr/bin/env python3
"""Programme PC de la Télécommande ESP32 (Windows).

- Envoie chaque seconde à l'ESP32 : CPU, RAM, volume, batterie (ligne « STAT »).
- Envoie chaque seconde la carte graphique NVIDIA : température, charge, mémoire (ligne « GPU »).
- Surveille et signale : sortie audio (casque ou haut-parleurs), manette, PC verrouillé,
  jeu Steam en cours (lignes « EVT »).
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

try:
    import pynvml  # paquet « nvidia-ml-py »
except ImportError:
    pynvml = None

import winreg

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
        self.precedent = {}

    def boucle_mesures(self):
        if comtypes is not None:
            comtypes.CoInitialize()
        if pynvml is not None:
            try:
                pynvml.nvmlInit()
            except Exception as e:
                print(f"[agent] NVIDIA indisponible : {e}")
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

            t, u, mem = gpu()
            self.dernier_gpu = f"GPU {t} {u} {mem}"
            self.liaison.envoyer(self.dernier_gpu)

            nom, externe = sortie_audio()
            etats = {
                "CASQUE": nom if externe else "-",
                "MANETTE": "1" if manette_connectee() else "0",
                "VERROU": "1" if pc_verrouille() else "0",
                "JEU": jeu_steam() or "-",
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
                print(self.dernier_stat, self.dernier_gpu, self.precedent)
                continue
            if ligne.upper() == "AUDIO":
                if comtypes is not None:
                    comtypes.CoInitialize()
                print(diagnostic_audio())
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

## esp/lib/hid_pc.py (inchangé depuis la Phase 1)

```python
# Clavier + souris + touches multimédia USB pour le PC.
# Utilise la bibliothèque officielle micropython-lib « usb-device-hid ».
import time

import usb.device
from usb.device.hid import HIDInterface

# Description de l'appareil envoyée au PC :
# rapport 1 = clavier, rapport 2 = souris, rapport 3 = multimédia.
_DESCRIPTEUR = bytes((
    # --- Clavier (rapport 1) ---
    0x05, 0x01, 0x09, 0x06, 0xA1, 0x01, 0x85, 0x01,
    0x05, 0x07, 0x19, 0xE0, 0x29, 0xE7, 0x15, 0x00, 0x25, 0x01,
    0x75, 0x01, 0x95, 0x08, 0x81, 0x02,             # 8 touches de modification
    0x95, 0x01, 0x75, 0x08, 0x81, 0x01,             # octet réservé
    0x95, 0x06, 0x75, 0x08, 0x15, 0x00, 0x25, 0x65,
    0x05, 0x07, 0x19, 0x00, 0x29, 0x65, 0x81, 0x00, # 6 touches
    0xC0,
    # --- Souris (rapport 2) ---
    0x05, 0x01, 0x09, 0x02, 0xA1, 0x01, 0x85, 0x02,
    0x09, 0x01, 0xA1, 0x00,
    0x05, 0x09, 0x19, 0x01, 0x29, 0x03, 0x15, 0x00, 0x25, 0x01,
    0x95, 0x03, 0x75, 0x01, 0x81, 0x02,             # 3 boutons
    0x95, 0x01, 0x75, 0x05, 0x81, 0x01,             # bourrage
    0x05, 0x01, 0x09, 0x30, 0x09, 0x31, 0x09, 0x38,
    0x15, 0x81, 0x25, 0x7F, 0x75, 0x08, 0x95, 0x03, 0x81, 0x06,  # X, Y, molette
    0xC0, 0xC0,
    # --- Multimédia (rapport 3) ---
    0x05, 0x0C, 0x09, 0x01, 0xA1, 0x01, 0x85, 0x03,
    0x15, 0x00, 0x26, 0xFF, 0x03, 0x19, 0x00, 0x2A, 0xFF, 0x03,
    0x75, 0x10, 0x95, 0x01, 0x81, 0x00,
    0xC0,
))

# Touches de modification
MODS = {"ctrl": 0x01, "shift": 0x02, "alt": 0x04, "win": 0x08}

# Touches spéciales (codes USB HID)
SPECIALES = {
    "enter": 0x28, "entree": 0x28, "esc": 0x29, "echap": 0x29,
    "backspace": 0x2A, "tab": 0x2B, "space": 0x2C, "espace": 0x2C,
    "printscreen": 0x46, "home": 0x4A, "pageup": 0x4B, "delete": 0x4C,
    "suppr": 0x4C, "end": 0x4D, "pagedown": 0x4E,
    "right": 0x4F, "left": 0x50, "down": 0x51, "up": 0x52,
}
for _n in range(1, 13):
    SPECIALES["f%d" % _n] = 0x3A + _n - 1

# Touches multimédia (codes « Consumer »)
MEDIA = {
    "VOL+": 0xE9, "VOL-": 0xEA, "MUTE": 0xE2, "PLAY": 0xCD,
    "NEXT": 0xB5, "PREV": 0xB6, "LUM+": 0x6F, "LUM-": 0x70,
}

# Caractères tapables (disposition QWERTY US) : caractère -> (shift, code)
_SANS_SHIFT = "-=[]\\;'`,./"
_CODES_SANS_SHIFT = (0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38)
_AVEC_SHIFT = "_+{}|:\"~<>?"
_CHIFFRES_SHIFT = "!@#$%^&*()"


def _caractere(c):
    if "a" <= c <= "z":
        return False, 0x04 + ord(c) - ord("a")
    if "A" <= c <= "Z":
        return True, 0x04 + ord(c) - ord("A")
    if "1" <= c <= "9":
        return False, 0x1E + ord(c) - ord("1")
    if c == "0":
        return False, 0x27
    if c == " ":
        return False, 0x2C
    if c in _SANS_SHIFT:
        return False, _CODES_SANS_SHIFT[_SANS_SHIFT.index(c)]
    if c in _AVEC_SHIFT:
        return True, _CODES_SANS_SHIFT[_AVEC_SHIFT.index(c)]
    if c in _CHIFFRES_SHIFT:
        return True, 0x1E + _CHIFFRES_SHIFT.index(c)
    return None


class PC(HIDInterface):
    def __init__(self):
        super().__init__(_DESCRIPTEUR, interface_str="ESP32 Maison PC")

    def demarrer(self, attente_ms=5000):
        """Déclare clavier + souris au PC (le port série reste actif)."""
        usb.device.get().init(self, builtin_driver=True)
        debut = time.ticks_ms()
        while not self.is_open():
            if time.ticks_diff(time.ticks_ms(), debut) > attente_ms:
                return False
            time.sleep_ms(100)
        return True

    def _envoyer(self, rapport):
        # Toujours un nouvel objet bytes : le tampon ne doit pas changer
        # pendant que l'USB l'envoie.
        for _ in range(20):
            if self.send_report(bytes(rapport)):
                return True
            time.sleep_ms(5)
        return False

    # --- Clavier -------------------------------------------------------------
    def _touches(self, mods, code):
        self._envoyer((1, mods, 0, code, 0, 0, 0, 0, 0))
        time.sleep_ms(15)
        self._envoyer((1, 0, 0, 0, 0, 0, 0, 0, 0))
        time.sleep_ms(15)

    def raccourci(self, texte):
        """Ex. 'win+l', 'ctrl+shift+esc', 'f5', 'a'. Renvoie False si inconnu."""
        mods = 0
        code = 0
        for morceau in texte.lower().split("+"):
            morceau = morceau.strip()
            if morceau in MODS:
                mods |= MODS[morceau]
            elif morceau in SPECIALES:
                code = SPECIALES[morceau]
            elif len(morceau) == 1 and _caractere(morceau) is not None:
                code = _caractere(morceau)[1]
            else:
                return False
        self._touches(mods, code)
        return True

    def taper(self, texte):
        """Tape un texte (QWERTY US). Renvoie le nombre de caractères ignorés."""
        ignores = 0
        for c in texte:
            r = _caractere(c)
            if r is None:
                ignores += 1
                continue
            shift, code = r
            self._touches(MODS["shift"] if shift else 0, code)
        return ignores

    # --- Multimédia ----------------------------------------------------------
    def media(self, nom):
        usage = MEDIA.get(nom)
        if usage is None:
            return False
        self._envoyer((3, usage & 0xFF, usage >> 8))
        time.sleep_ms(30)
        self._envoyer((3, 0, 0))
        return True

    # --- Souris --------------------------------------------------------------
    def souris(self, dx=0, dy=0, boutons=0, molette=0):
        # Les grands déplacements sont découpés en pas de 127 au maximum.
        while True:
            px = max(-127, min(127, dx))
            py = max(-127, min(127, dy))
            self._envoyer((2, boutons, px & 0xFF, py & 0xFF, molette & 0xFF))
            dx -= px
            dy -= py
            molette = 0
            if dx == 0 and dy == 0:
                break
            time.sleep_ms(8)

    def clic(self, bouton=1):
        self.souris(boutons=bouton)
        time.sleep_ms(20)
        self.souris(boutons=0)
```

## esp/lib/lcd.py (inchangé depuis la Phase 0)

```python
# Pilote minimal de l'écran ST7789 (Waveshare ESP32-S3-LCD-1.47, 172 x 320).
# On dessine dans une image en mémoire (framebuf), puis afficher() l'envoie
# d'un coup à l'écran.
import struct
import time

import framebuf
from machine import PWM, SPI, Pin

LARGEUR_PANNEAU = 172
HAUTEUR_PANNEAU = 320
DECALAGE = 34   # le contrôleur fait 240 de large, l'écran 172 est centré : (240 - 172) / 2
BGR = False     # mets True si le rouge et le bleu sont inversés à l'écran


def couleur(r, g, b):
    """Couleur 0-255 -> RGB565, octets inversés comme l'attend l'écran."""
    c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return ((c & 0xFF) << 8) | (c >> 8)


NOIR = couleur(0, 0, 0)
BLANC = couleur(255, 255, 255)
ROUGE = couleur(255, 0, 0)
VERT = couleur(0, 255, 0)
BLEU = couleur(0, 0, 255)
GRIS = couleur(90, 90, 90)
CYAN = couleur(0, 200, 255)
ORANGE = couleur(255, 140, 0)


class Ecran:
    def __init__(self, paysage=True):
        self.spi = SPI(1, baudrate=40_000_000, polarity=0, phase=0,
                       sck=Pin(40), mosi=Pin(45))
        self.cs = Pin(42, Pin.OUT, value=1)
        self.dc = Pin(41, Pin.OUT, value=0)
        self.rst = Pin(39, Pin.OUT, value=1)
        self.bl = PWM(Pin(48), freq=1000)
        self.paysage = paysage
        if paysage:
            self.largeur, self.hauteur = HAUTEUR_PANNEAU, LARGEUR_PANNEAU
        else:
            self.largeur, self.hauteur = LARGEUR_PANNEAU, HAUTEUR_PANNEAU
        self.tampon = bytearray(self.largeur * self.hauteur * 2)
        self.fb = framebuf.FrameBuffer(self.tampon, self.largeur, self.hauteur,
                                       framebuf.RGB565)
        self._lettre = bytearray(8)
        self._lettre_fb = framebuf.FrameBuffer(self._lettre, 8, 8, framebuf.MONO_HLSB)
        self._demarrer()
        self.luminosite(80)

    # --- bas niveau -------------------------------------------------------
    def _cmd(self, commande, donnees=None):
        self.cs(0)
        self.dc(0)
        self.spi.write(bytes([commande]))
        if donnees is not None:
            self.dc(1)
            self.spi.write(donnees)
        self.cs(1)

    def _demarrer(self):
        self.rst(0)
        time.sleep_ms(50)
        self.rst(1)
        time.sleep_ms(150)
        self._cmd(0x01)                  # reset logiciel
        time.sleep_ms(150)
        self._cmd(0x11)                  # sortie du mode veille
        time.sleep_ms(120)
        self._cmd(0x3A, b"\x55")         # 16 bits par pixel
        madctl = 0x60 if self.paysage else 0x00
        if BGR:
            madctl |= 0x08
        self._cmd(0x36, bytes([madctl]))  # orientation
        self._cmd(0x21)                  # inversion (écrans IPS)
        self._cmd(0x13)                  # mode normal
        self._cmd(0x29)                  # écran allumé
        time.sleep_ms(50)

    # --- usage -------------------------------------------------------------
    def luminosite(self, pourcent):
        pourcent = max(0, min(100, pourcent))
        self.bl.duty_u16(pourcent * 65535 // 100)

    def afficher(self):
        if self.paysage:
            x0, x1 = 0, self.largeur - 1
            y0, y1 = DECALAGE, DECALAGE + self.hauteur - 1
        else:
            x0, x1 = DECALAGE, DECALAGE + self.largeur - 1
            y0, y1 = 0, self.hauteur - 1
        self._cmd(0x2A, struct.pack(">HH", x0, x1))
        self._cmd(0x2B, struct.pack(">HH", y0, y1))
        self._cmd(0x2C, self.tampon)

    def texte(self, s, x, y, c, taille=1):
        """Texte avec la police 8x8 intégrée, agrandie `taille` fois."""
        if taille == 1:
            self.fb.text(s, x, y, c)
            return
        for car in s:
            self._lettre_fb.fill(0)
            self._lettre_fb.text(car, 0, 0, 1)
            for ligne in range(8):
                for col in range(8):
                    if self._lettre_fb.pixel(col, ligne):
                        self.fb.fill_rect(x + col * taille, y + ligne * taille,
                                          taille, taille, c)
            x += 8 * taille
```

## tools/pc_test.py (inchangé depuis la Phase 1)

```python
#!/usr/bin/env python3
"""Envoie des commandes de test à l'ESP32 (clavier / souris / multimédia).

Utilisation :
  py -X utf8 tools\\pc_test.py COM4                commandes tapées une par une
  py -X utf8 tools\\pc_test.py COM4 --cmd "VOL+"   une seule commande
"""
import argparse
import sys
import time

import serial

AIDE = """Commandes :
  PING                  test de connexion
  KEY win+l             raccourci (ctrl, shift, alt, win + lettre, chiffre, f1..f12,
                        enter, esc, tab, space, up/down/left/right, delete, home, end…)
  TEXT bonjour          tape du texte (disposition QWERTY US)
  VOL+  VOL-  MUTE  PLAY  NEXT  PREV  LUM+  LUM-
  MOUSE 100 -50         déplace la souris (x, y)
  CLIC  CLICD           clic gauche / clic droit
  MOLETTE -3            défilement (négatif = vers le bas)
  q                     quitter"""


def ouvrir(port):
    try:
        ser = serial.Serial(port, 115200, timeout=0.1)
    except serial.SerialException as e:
        sys.exit(f"Impossible d'ouvrir {port} : {e}\n(mpremote est peut-être encore connecté)")
    time.sleep(0.5)
    ser.reset_input_buffer()
    return ser


def envoyer(ser, commande, attente=3.0):
    ser.write((commande.strip() + "\n").encode())
    ser.flush()
    fin = time.time() + attente
    while time.time() < fin:
        ligne = ser.readline().decode(errors="ignore").strip()
        if ligne.startswith(("OK", "ERR", "PONG")):
            print("  ->", ligne)
            return ligne
    print("  -> pas de réponse")
    return None


def main():
    parser = argparse.ArgumentParser(description="Test clavier/souris de l'ESP32")
    parser.add_argument("port", help="port série de l'ESP32, ex. COM4")
    parser.add_argument("--cmd", help="envoie une seule commande puis quitte")
    args = parser.parse_args()

    ser = ouvrir(args.port)
    if args.cmd:
        envoyer(ser, args.cmd)
        return
    print(AIDE)
    while True:
        try:
            commande = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if commande.lower() == "q":
            break
        if commande:
            envoyer(ser, commande)


if __name__ == "__main__":
    main()
```

## app/pubspec.yaml (inchangé depuis la Phase 0)

```yaml
name: esp_micro
description: "A new Flutter project."
# The following line prevents the package from being accidentally published to
# pub.dev using `flutter pub publish`. This is preferred for private packages.
publish_to: 'none' # Remove this line if you wish to publish to pub.dev

# The following defines the version and build number for your application.
# A version number is three numbers separated by dots, like 1.2.43
# followed by an optional build number separated by a +.
# Both the version and the builder number may be overridden in flutter
# build by specifying --build-name and --build-number, respectively.
# In Android, build-name is used as versionName while build-number used as versionCode.
# Read more about Android versioning at https://developer.android.com/studio/publish/versioning
# In iOS, build-name is used as CFBundleShortVersionString while build-number is used as CFBundleVersion.
# Read more about iOS versioning at
# https://developer.apple.com/library/archive/documentation/General/Reference/InfoPlistKeyReference/Articles/CoreFoundationKeys.html
# In Windows, build-name is used as the major, minor, and patch parts
# of the product and file versions while build-number is used as the build suffix.
version: 1.0.0+1

environment:
  sdk: ^3.13.2

# Dependencies specify other packages that your package needs in order to work.
# To automatically upgrade your package dependencies to the latest versions
# consider running `flutter pub upgrade --major-versions`. Alternatively,
# dependencies can be manually updated by changing the version numbers below to
# the latest version available on pub.dev. To see which dependencies have newer
# versions available, run `flutter pub outdated`.
dependencies:
  flutter:
    sdk: flutter

  # The following adds the Cupertino Icons font to your application.
  # Use with the CupertinoIcons class for iOS style icons.
  cupertino_icons: ^1.0.8

dev_dependencies:
  flutter_test:
    sdk: flutter

  # The "flutter_lints" package below contains a set of recommended lints to
  # encourage good coding practices. The lint set provided by the package is
  # activated in the `analysis_options.yaml` file located at the root of your
  # package. See that file for information about deactivating specific lint
  # rules and activating additional ones.
  flutter_lints: ^6.0.0

# For information on the generic Dart part of this file, see the
# following page: https://dart.dev/tools/pub/pubspec

# The following section is specific to Flutter packages.
flutter:

  # The following line ensures that the Material Icons font is
  # included with your application, so that you can use the icons in
  # the material Icons class.
  uses-material-design: true

  # To add assets to your application, add an assets section, like this:
  # assets:
  #   - images/a_dot_burr.jpeg
  #   - images/a_dot_ham.jpeg

  # An image asset can refer to one or more resolution-specific "variants", see
  # https://flutter.dev/to/resolution-aware-images

  # For details regarding adding assets from package dependencies, see
  # https://flutter.dev/to/asset-from-package

  # To add custom fonts to your application, add a fonts section here,
  # in this "flutter" section. Each entry in this list should have a
  # "family" key with the font family name, and a "fonts" key with a
  # list giving the asset and other descriptors for the font. For
  # example:
  # fonts:
  #   - family: Schyler
  #     fonts:
  #       - asset: fonts/Schyler-Regular.ttf
  #       - asset: fonts/Schyler-Italic.ttf
  #         style: italic
  #   - family: Trajan Pro
  #     fonts:
  #       - asset: fonts/TrajanPro.ttf
  #       - asset: fonts/TrajanPro_Bold.ttf
  #         weight: 700
  #
  # For details regarding fonts from package dependencies,
  # see https://flutter.dev/to/font-from-package
```

## hid.py installé

mip a installé la version **compilée** `/lib/usb/device/hid.mpy` (1569 octets, SHA-256 `dd106a6a2ee2597457695d05a703dffe533865827d2dff2af0154a45e34f4ac8`), pas de `hid.py` lisible sur la carte. Le hash correspond à l'entrée `usb/device/hid.mpy` (`dd106a6a`) de l'index mip pour usb-device-hid **0.2.0**. Ci-dessous, la source `usb/device/hid.py` de la même version 0.2.0, téléchargée depuis le même index (`https://micropython.org/pi/v2/file/95/951892ce`, hash vérifié `951892ce`) :

```python
# MicroPython USB hid module
#
# This implements a base HIDInterface class that can be used directly,
# or subclassed into more specific HID interface types.
#
# MIT license; Copyright (c) 2023 Angus Gratton
from micropython import const
import machine
import struct
import time
from .core import Interface, Descriptor, split_bmRequestType

_EP_IN_FLAG = const(1 << 7)

# Control transfer stages
_STAGE_IDLE = const(0)
_STAGE_SETUP = const(1)
_STAGE_DATA = const(2)
_STAGE_ACK = const(3)

# Request types
_REQ_TYPE_STANDARD = const(0x0)
_REQ_TYPE_CLASS = const(0x1)
_REQ_TYPE_VENDOR = const(0x2)
_REQ_TYPE_RESERVED = const(0x3)

# Descriptor types
_DESC_HID_TYPE = const(0x21)
_DESC_REPORT_TYPE = const(0x22)
_DESC_PHYSICAL_TYPE = const(0x23)

# Interface and protocol identifiers
_INTERFACE_CLASS = const(0x03)
_INTERFACE_SUBCLASS_NONE = const(0x00)
_INTERFACE_SUBCLASS_BOOT = const(0x01)

# These values will only make sense when interface subclass
# is 0x01, which indicates boot protocol support.
_INTERFACE_PROTOCOL_NONE = const(0x00)
_INTERFACE_PROTOCOL_KEYBOARD = const(0x01)
_INTERFACE_PROTOCOL_MOUSE = const(0x02)

# bRequest values for HID control requests
_REQ_CONTROL_GET_REPORT = const(0x01)
_REQ_CONTROL_GET_IDLE = const(0x02)
_REQ_CONTROL_GET_PROTOCOL = const(0x03)
_REQ_CONTROL_GET_DESCRIPTOR = const(0x06)
_REQ_CONTROL_SET_REPORT = const(0x09)
_REQ_CONTROL_SET_IDLE = const(0x0A)
_REQ_CONTROL_SET_PROTOCOL = const(0x0B)

# Standard descriptor lengths
_STD_DESC_INTERFACE_LEN = const(9)
_STD_DESC_ENDPOINT_LEN = const(7)


class HIDInterface(Interface):
    # Abstract base class to implement a USB device HID interface in Python.

    def __init__(
        self,
        report_descriptor,
        extra_descriptors=[],
        set_report_buf=None,
        protocol=_INTERFACE_PROTOCOL_NONE,
        interface_str=None,
        interval_ms=8,
    ):
        # Construct a new HID interface.
        #
        # - report_descriptor is the only mandatory argument, which is the binary
        # data consisting of the HID Report Descriptor. See Device Class
        # Definition for Human Interface Devices (HID) v1.11 section 6.2.2 Report
        # Descriptor, p23.
        #
        # - extra_descriptors is an optional argument holding additional HID
        #   descriptors, to append after the mandatory report descriptor. Most
        #   HID devices do not use these.
        #
        # - set_report_buf is an optional writable buffer object (i.e.
        #   bytearray), where SET_REPORT requests from the host can be
        #   written. Only necessary if the report_descriptor contains Output
        #   entries. If set, the size must be at least the size of the largest
        #   Output entry.
        #
        # - protocol can be set to a specific value as per HID v1.11 section 4.3 Protocols, p9.
        #
        # - interface_str is an optional string descriptor to associate with the HID USB interface.
        #
        # - interval_ms this is the polling rate the device will request the host use in milliseconds.
        super().__init__()
        self.report_descriptor = report_descriptor
        self.extra_descriptors = extra_descriptors
        self._set_report_buf = set_report_buf
        self.protocol = protocol
        self.interface_str = interface_str
        self.interval_ms = interval_ms

        self._int_ep = None  # set during enumeration

    def get_report(self):
        return False

    def on_set_report(self, report_data, report_id, report_type):
        # Override this function in order to handle SET REPORT requests from the host,
        # where it sends data to the HID device.
        #
        # This function will only be called if the Report descriptor contains at least one Output entry,
        # and the set_report_buf argument is provided to the constructor.
        #
        # Return True to complete the control transfer normally, False to abort it.
        return True

    def busy(self):
        # Returns True if the interrupt endpoint is busy (i.e. existing transfer is pending)
        return self.is_open() and self.xfer_pending(self._int_ep)

    def send_report(self, report_data, timeout_ms=100):
        # Helper function to send a HID report in the typical USB interrupt
        # endpoint associated with a HID interface.
        #
        # Returns True if successful, False if HID device is not active or timeout
        # is reached without being able to queue the report for sending.
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        while self.busy():
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                return False
            machine.idle()
        if not self.is_open():
            return False
        self.submit_xfer(self._int_ep, report_data)
        return True

    def desc_cfg(self, desc, itf_num, ep_num, strs):
        # Add the standard interface descriptor
        desc.interface(
            itf_num,
            1,
            _INTERFACE_CLASS,
            _INTERFACE_SUBCLASS_NONE
            if self.protocol == _INTERFACE_PROTOCOL_NONE
            else _INTERFACE_SUBCLASS_BOOT,
            self.protocol,
            len(strs) if self.interface_str else 0,
        )

        if self.interface_str:
            strs.append(self.interface_str)

        # As per HID v1.11 section 7.1 Standard Requests, return the contents of
        # the standard HID descriptor before the associated endpoint descriptor.
        self.get_hid_descriptor(desc)

        # Add the typical single USB interrupt endpoint descriptor associated
        # with a HID interface.
        self._int_ep = ep_num | _EP_IN_FLAG
        desc.endpoint(self._int_ep, "interrupt", 8, self.interval_ms)

        self.idle_rate = 0

        # This variable is reused to track boot protocol status.
        # 0 for boot protocol, 1 for report protocol
        # According to Device Class Definition for Human Interface Devices (HID) v1.11
        # Appendix F.5, the device comes up in non-boot mode by default.
        self.protocol = 1

    def num_eps(self):
        return 1

    def get_hid_descriptor(self, desc=None):
        # Append a full USB HID descriptor from the object's report descriptor
        # and optional additional descriptors.
        #
        # See HID Specification Version 1.1, Section 6.2.1 HID Descriptor p22

        l = 9 + 3 * len(self.extra_descriptors)  # total length

        if desc is None:
            desc = Descriptor(bytearray(l))

        desc.pack(
            "<BBHBBBH",
            l,  # bLength
            _DESC_HID_TYPE,  # bDescriptorType
            0x111,  # bcdHID
            0,  # bCountryCode
            len(self.extra_descriptors) + 1,  # bNumDescriptors
            0x22,  # bDescriptorType, Report
            len(self.report_descriptor),  # wDescriptorLength, Report
        )
        # Fill in any additional descriptor type/length pairs
        #
        # TODO: unclear if this functionality is ever used, may be easier to not
        # support in base class
        for dt, dd in self.extra_descriptors:
            desc.pack("<BH", dt, len(dd))

        return desc.b

    def on_interface_control_xfer(self, stage, request):
        # Handle standard and class-specific interface control transfers for HID devices.
        bmRequestType, bRequest, wValue, _, wLength = struct.unpack("BBHHH", request)

        recipient, req_type, _ = split_bmRequestType(bmRequestType)

        if stage == _STAGE_SETUP:
            if req_type == _REQ_TYPE_STANDARD:
                # HID Spec p48: 7.1 Standard Requests
                if bRequest == _REQ_CONTROL_GET_DESCRIPTOR:
                    desc_type = wValue >> 8
                    if desc_type == _DESC_HID_TYPE:
                        return self.get_hid_descriptor()
                    if desc_type == _DESC_REPORT_TYPE:
                        # Reset to report protocol when report descriptor is requested
                        self.protocol = 1
                        return self.report_descriptor
            elif req_type == _REQ_TYPE_CLASS:
                # HID Spec p50: 7.2 Class-Specific Requests
                if bRequest == _REQ_CONTROL_GET_REPORT:
                    print("GET_REPORT?")
                    return False  # Unsupported for now
                if bRequest == _REQ_CONTROL_GET_IDLE:
                    return bytes([self.idle_rate])
                if bRequest == _REQ_CONTROL_GET_PROTOCOL:
                    return bytes([self.protocol])
                if bRequest in (_REQ_CONTROL_SET_IDLE, _REQ_CONTROL_SET_PROTOCOL):
                    return True
                if bRequest == _REQ_CONTROL_SET_REPORT:
                    return self._set_report_buf  # If None, request will stall
            return False  # Unsupported request

        if stage == _STAGE_ACK:
            if req_type == _REQ_TYPE_CLASS:
                if bRequest == _REQ_CONTROL_SET_IDLE:
                    self.idle_rate = wValue >> 8
                elif bRequest == _REQ_CONTROL_SET_PROTOCOL:
                    self.protocol = wValue
                elif bRequest == _REQ_CONTROL_SET_REPORT:
                    report_id = wValue & 0xFF
                    report_type = wValue >> 8
                    report_data = self._set_report_buf
                    if wLength < len(report_data):
                        # need to truncate the response in the callback if we got less bytes
                        # than allowed for in the buffer
                        report_data = memoryview(self._set_report_buf)[:wLength]
                    self.on_set_report(report_data, report_id, report_type)

        return True  # allow DATA/ACK stages to complete normally


__version__ = '0.2.0'
```
