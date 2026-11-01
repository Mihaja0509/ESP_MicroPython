# État du code — Micro

Mis à jour : 2026-11-01 (fin de Phase 4 : écran vivant, mascotte et météo)

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
│   ├── micro_phase2_bis.md
│   └── micro_phase3_gamer.md
├── esp/
│   ├── lib/
│   │   ├── hid_pc.py
│   │   └── lcd.py
│   └── main.py
├── tools/
│   ├── agent/
│   │   ├── agent_pc.py
│   │   ├── apps.json
│   │   └── installer_demarrage.ps1
│   └── pc_test.py
├── .gitignore
└── CLAUDE.md
```

Ignorés par Git :
- `bin/` : `ESP32_GENERIC_S3-SPIRAM_OCT-20260824-v1.29.0.bin` ;
- `tools/agent/bin/` (règle `bin/`) : `PresentMon-2.6.0-x64.exe`, `LibreHardwareMonitor/` (43 fichiers) ;
- `tools/agent/PAUSE`, `tools/agent/agent.log`.

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
| PresentMon (console, `tools/agent/bin`) | 2.6.0 (signé Intel Corporation) |
| LibreHardwareMonitor (`tools/agent/bin/LibreHardwareMonitor`) | 0.9.6 (exe 0.9.6.0) |

## Port série

- **COM4** (USB 303a:4001), inchangé (`py -m mpremote devs`).
- Pendant le flash de la Phase 0 (bootloader) : COM3 (303a:1001).
- Un seul programme à la fois sur COM4 : l'agent (`agent_pc.py`), `pc_test.py` ou mpremote.

## Fichiers sur la carte

```
ls :
           0 assets/
         139 boot.py
         524 erreur.txt
           0 lib/
       10434 main.py
ls :lib
        6040 hid_pc.py
        4071 lcd.py
        5177 meteo.py
        3495 polices.py
       15091 ui.py
           0 usb/
```

`:assets` : 38 fichiers (détail dans « Copie sur la carte (Phase 4, étape 4) »). Pas de `:secrets.py` (`esp/secrets.py` n'existe pas sur le PC : normal, Wi-Fi facultatif).

`erreur.txt` (524 octets) contient uniquement d'anciennes traces de la version 3-bis (voir « Démarrage (Phase 4, étape 5) ») ; sa taille n'a pas changé après les démarrages et tests de la Phase 4.

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

## Téléchargements (Phase 3, étape 4)

Dernières versions stables (API GitHub `releases/latest`, `prerelease: false`) :

| Outil | Release | Fichier téléchargé | Emplacement |
|---|---|---|---|
| PresentMon (console) | v2.6.0 (2026-09-21) | `PresentMon-2.6.0-x64.exe` (980 320 octets, signature Authenticode valide : Intel Corporation) | `tools\agent\bin\PresentMon-2.6.0-x64.exe` |
| LibreHardwareMonitor | v0.9.6 (2026-02-14) | `LibreHardwareMonitor.zip` (6 632 626 octets), version .NET Framework | extrait dans `tools\agent\bin\LibreHardwareMonitor\` (43 fichiers, `LibreHardwareMonitor.exe` 0.9.6.0) |

Non retenus : `PresentMon-2.6.0.msi` (application avec overlay), `LibreHardwareMonitor.NET.10.zip` (demande le runtime .NET 10).
LibreHardwareMonitor n'a pas été lancé ; la tâche planifiée n'a pas été créée (par Mihaja, en administrateur).

## Aide PresentMon (Phase 3, étape 5)

`& tools\agent\bin\PresentMon-2.6.0-x64.exe --help` (86 lignes, code de sortie 1 ; 1re ligne : `PresentMon 2.6.0`). Lignes demandées :

```
  --output_stdout               Write CSV output to STDOUT.
  --v1_metrics                  Output a CSV using PresentMon 1.x metrics.
  --session_name name           Use the specified session name instead of the
  --stop_existing_session       If a trace session with the same name is already
```

Aussi présente (utilisée par l'agent) :

```
  --no_console_stats            Do not display active swap chains and frame
```

## Copie sur la carte (Phase 3, étape 7)

| Essai | Commande | Résultat |
|---|---|---|
| 1 | `fs cp esp\main.py :main.py + reset` | échec : `ClearCommError` (trace ci-dessous) |
| 2 (relance immédiate) | idem | échec : `mpremote: failed to access COM4 (it may be in use by another program)` (aucun processus ne tenait COM4 : port pas encore libéré) |
| 3 (après 3 s) | idem | réussi (`cp esp\main.py :main.py`) |
| `fs cat :main.py` essai 1 | — | échec : `ClearCommError` |
| `fs cat :main.py` essai 2 (après 3 s) | — | réussi, contient `if cmd == "PERF":` ; puis `reset` |

Trace de l'essai 1 : seules les 2 dernières lignes ont été capturées (la sortie était filtrée). Elles sont identiques à la fin de la trace complète notée en Phase 2-bis (section « Trace mpremote ») :

```
    raise SerialException("ClearCommError failed ({!r})".format(ctypes.WinError()))
serial.serialutil.SerialException: ClearCommError failed (PermissionError(13, 'The device does not recognize the command.', None, 22))
```

`fs cat` essai 1 (dernière ligne seulement, capturée de la même façon) :

```
serial.serialutil.SerialException: ClearCommError failed (PermissionError(13, 'The device does not recognize the command.', None, 22))
```

## Réponse de la carte (Phase 3, étape 8)

```
> py -X utf8 tools\pc_test.py COM4 --cmd "PERF 70 144"
  -> OK
```

## Mise en place (Phase 3-bis, étapes 1, 4 et 7)

- `tools\agent\PAUSE` créé ; l'agent en fond (tâche « ESP32 Telecommande Agent », code Phase 3) a libéré COM4.
- Copie de main.py : ClearCommError au 1er essai, réussie au 2e (après 3 s). `fs cat` : idem (ClearCommError puis OK). Puis `reset`.
- Seule la dernière ligne des traces ClearCommError a été capturée ; c'est la même erreur que la trace complète de la section « Trace mpremote (Phase 2-bis, étape 4) » :

```
serial.serialutil.SerialException: ClearCommError failed (PermissionError(13, 'The device does not recognize the command.', None, 22))
```

- Pour l'étape 6, Mihaja a arrêté la tâche planifiée (`Stop-ScheduledTask`, état ensuite « Ready ») : avec PAUSE, l'agent console ne se connecte pas ; sans PAUSE, l'agent en fond reprend COM4.
- `PAUSE` supprimé juste avant de lancer l'agent console (étape 7 avancée), tâche planifiée toujours arrêtée.
- Après l'arrêt de la tâche, un processus `PresentMon-2.6.0-x64.exe` lancé par l'ancien agent tournait encore (non arrêté).

## Réponses de la carte (Phase 3-bis, étape 5)

```
> py -X utf8 tools\pc_test.py COM4 --cmd PING
  -> PONG
> py -X utf8 tools\pc_test.py COM4 --cmd "PERF 70 144"
  -> OK
```

## Relance automatique (Phase 3-bis, étape 6)

1. `py -m mpremote connect COM4 exec "raise SystemExit"` : ClearCommError au 1er essai, réussi au 2e (code 0) → la carte reste dans l'invite `>>>`.
2. Agent console (`py -X utf8 tools\agent\agent_pc.py`, non administrateur) lancé 15 s, puis `q` sur son entrée (code de sortie 0). Sortie complète :

```
Commandes PC :
  APPS                  liste des apps   |  APP spotify    ouvre une app
  LUM 70  LUM+  LUM-    luminosité de l'écran du PC
  VERROU                verrouille        |  ECRAN_OFF      verrouille + éteint l'écran
  VEILLE                mise en veille    |  ARRET          arrêt dans 60 s  |  ANNULER
  ETAT                  affiche ce que l'agent envoie à l'ESP32
  AUDIO                 liste les sorties audio (diagnostic du casque)
Toute autre commande (KEY win+d, TEXT …, VOL+, MOUSE 100 0, CLIC…) part à l'ESP32.
  q                     quitter
> [agent] pas lancé en administrateur : les FPS ne seront pas disponibles
[agent] ESP32 connectée sur COM4
[agent] LibreHardwareMonitor : OK
[agent] PresentMon : PresentMon s'est arrêté (droits administrateur ?)
[agent] événement : CASQUE = Headphones (Xiaomi蓝牙音箱Pro)
[agent] événement : MANETTE = 0
[agent] événement : VERROU = 0
[agent] événement : JEU = -
[esp32] STAT 56 48 38 76 1
[esp32] Traceback (most recent call last):
[agent] programme de l'ESP32 arrêté : redémarrage (Ctrl-D)
[esp32] File "<stdin>", line 1
[esp32] SyntaxError: invalid syntax
[esp32] >>> GPU 46 0 3
[esp32] Traceback (most recent call last):
[esp32] File "<stdin>", line 1
[esp32] SyntaxError: invalid syntax
[esp32] >>> PERF 50 -1
[esp32] Traceback (most recent call last):
[esp32] File "<stdin>", line 1
[esp32] SyntaxError: invalid syntax
[esp32] >>> EVT CASQUE Headphones (XiaomiPro)
[esp32] Traceback (most recent call last):
[esp32] File "<stdin>", line 1
[esp32] SyntaxError: invalid syntax
[esp32] >>> EVT MANETTE 0
[esp32] Traceback (most recent call last):
[esp32] File "<stdin>", line 1
[esp32] SyntaxError: invalid syntax
[esp32] >>> EVT VERROU 0
[esp32] Traceback (most recent call last):
[esp32] File "<stdin>", line 1
[esp32] SyntaxError: invalid syntax
[esp32] >>> EVT JEU -
[esp32] Traceback (most recent call last):
[esp32] File "<stdin>", line 1
[esp32] SyntaxError: invalid syntax
[esp32] >>>
[esp32] >>>
[esp32] >>>
[esp32] MPY: soft reboot
[agent] ESP32 connectée sur COM4
[agent] événement : CASQUE = Headphones (Xiaomi蓝牙音箱Pro)
[agent] événement : MANETTE = 0
[agent] événement : VERROU = 0
[agent] événement : JEU = -

[lanceur] code de sortie : 0
```

Les `Traceback` / `SyntaxError` ci-dessus viennent de l'invite MicroPython de la carte (lignes STAT/GPU/PERF/EVT lues comme du Python pendant que le programme était arrêté), pas d'une erreur Python sur le PC. Après `MPY: soft reboot`, l'USB de la carte redémarre : l'agent se reconnecte (« ESP32 connectée sur COM4 ») et renvoie tous les événements ; plus aucune erreur ensuite.

## Copie sur la carte (Phase 4, étape 4)

- `tools\agent\PAUSE` créé, attente 3 s. `py -m mpremote devs` : COM4 (303a:4001).
- `fs cp esp/main.py :main.py` : ClearCommError au 1er essai, réussi au 2e (après 3 s). Dernière ligne de la trace :

```
serial.serialutil.SerialException: ClearCommError failed (PermissionError(13, 'The device does not recognize the command.', None, 22))
```

- `fs mkdir :lib` : `mpremote: mkdir: lib: File exists.` (normal).
- `fs cp esp/lib/ui.py :lib/ui.py + fs cp esp/lib/polices.py :lib/polices.py + fs cp esp/lib/meteo.py :lib/meteo.py` : OK.
- `fs cp -r esp/assets :` : OK.
- `esp/secrets.py` n'existe pas : rien copié en `:secrets.py` (normal).
- Module requests : `exec "import requests"` → sans erreur (`requests OK`).

```
ls :assets
        3344 bulle_manette.bin
      110080 fond_jeu.bin
      110080 fond_jour.bin
      110080 fond_nuit.bin
         648 ico_appli.bin
         648 ico_cadenas.bin
         288 ico_casque.bin
         648 ico_clavier.bin
         648 ico_coucou.bin
         288 ico_eclair.bin
         648 ico_lune.bin
         648 ico_manette.bin
         648 ico_muet.bin
         648 ico_musique.bin
         648 ico_power.bin
         648 ico_soleil.bin
         648 ico_son.bin
         648 ico_souris.bin
        1152 meteo_brouillard.bin
        1152 meteo_eclaircie.bin
        1152 meteo_neige.bin
        1152 meteo_nuage.bin
        1152 meteo_orage.bin
        1152 meteo_pluie.bin
        1152 meteo_soleil.bin
       28500 perso_cou_cligne.bin
       28500 perso_cou_content.bin
       28500 perso_cou_neutre.bin
       28500 perso_cou_surpris.bin
       28500 perso_oreilles_cligne.bin
       28500 perso_oreilles_content.bin
       28500 perso_oreilles_neutre.bin
       28500 perso_oreilles_surpris.bin
       26292 police_fps.fnt
       14754 police_heure.fnt
       23990 police_m.fnt
       15763 police_s.fnt
       11980 police_xs.fnt
```

```
> py -m mpremote connect COM4 exec "import os; s=os.statvfs('/'); print(s[0]*s[3]//1024, 'Ko libres'); print(len(os.listdir('/assets')), 'fichiers assets')"
13460 Ko libres
38 fichiers assets
```

## Démarrage (Phase 4, étape 5)

- `:erreur.txt` existait déjà avant le reset (524 octets). Contenu (anciennes traces : `main.py` ligne 71 = `lire_ligne` de la version 3-bis) :

```
Traceback (most recent call last):
  File "main.py", line 156, in <module>
  File "main.py", line 71, in lire_ligne
UnicodeError: 
Traceback (most recent call last):
  File "main.py", line 156, in <module>
  File "main.py", line 71, in lire_ligne
UnicodeError: 
Traceback (most recent call last):
  File "main.py", line 156, in <module>
  File "main.py", line 71, in lire_ligne
UnicodeError: 
Traceback (most recent call last):
  File "main.py", line 156, in <module>
  File "main.py", line 71, in lire_ligne
UnicodeError: 
```

- `reset` (1er essai : ClearCommError dans `ensure_raw_repl`, 2e essai OK), puis lecture de COM4 pendant 10 s (pyserial, 115200, réouverture du port pendant le redémarrage USB) : **0 octet reçu**, aucune trace. Normal : le nouveau `main.py` n'affiche rien au démarrage (il ne répond qu'aux lignes reçues ; les erreurs vont dans `erreur.txt`).
- Après le démarrage : `fs ls :` → `erreur.txt` toujours 524 octets (aucune nouvelle erreur).

## Réponses de la carte (Phase 4, étape 6)

Après un `reset` (pour relancer `main.py`), PAUSE toujours présent :

```
> py -X utf8 tools\pc_test.py COM4 --cmd "METEO_J 0 orage 32 24 80 15"
  -> OK
> py -X utf8 tools\pc_test.py COM4 --cmd METEO
  -> OK orage 32/24 pluie 80% vers 15h
> py -X utf8 tools\pc_test.py COM4 --cmd "STAT 23 61 48 76 1"
  -> OK
> py -X utf8 tools\pc_test.py COM4 --cmd "EVT JEU Test"
  -> OK
> py -X utf8 tools\pc_test.py COM4 --cmd "EVT JEU -"
  -> OK
> py -X utf8 tools\pc_test.py COM4 --cmd "VOL+"
  -> OK
```

Ensuite : `fs ls :` (`erreur.txt` toujours 524 octets), `tools\agent\PAUSE` supprimé, `reset` de la carte (l'agent en fond reprend COM4).

## esp/main.py

```python
# Phase 4 : Télécommande PC avec écran animé.
# - Les ordres et les données arrivent du PC par le port série USB (une ligne par message).
# - L'ESP32 joue le rôle de clavier + souris + touches multimédia (hid_pc.py).
# - L'écran est dessiné par ui.py environ 12 fois par seconde.
import select
import sys
import time

import machine

import lcd
from hid_pc import MEDIA, PC
from meteo import Meteo
from ui import Interface

try:
    import secrets as reglages  # /secrets.py sur la carte : Wi-Fi + position (jamais dans Git)
except ImportError:
    reglages = None

ecran = lcd.Ecran(paysage=True)
ui = Interface(ecran)
pc = PC()

# Valeurs envoyées par le programme PC (agent_pc.py) ; -1 = inconnu
stat = {"cpu": -1, "ram": -1, "vol": -1, "bat": -1, "chg": 0}
gpu = {"temp": -1, "charge": -1, "vram": -1}
perf = {"cpu_temp": -1, "fps": -1}
evt = {"casque": "", "manette": 0, "verrou": 0, "jeu": ""}
etat = {"connecte": False, "stat": stat, "gpu": gpu, "perf": perf, "evt": evt, "meteo": []}

ATTENTE_ABSENT = 8000      # sans données depuis 8 s = PC éteint / en veille / agent arrêté
IMAGE_MS = 80              # une image toutes les 80 ms (≈ 12 images / s)
derniere_donnee = time.ticks_add(time.ticks_ms(), -ATTENTE_ABSENT)
ecran_allume = True
luminosite_actuelle = -1


def noter_erreur(e):
    """Garde la trace d'une erreur dans erreur.txt (sur la carte) sans arrêter le programme."""
    try:
        with open("erreur.txt", "a") as f:
            sys.print_exception(e, f)
    except OSError:
        pass


# Premier dessin tout de suite (écran « Bonjour »), puis déclaration du clavier/souris au PC
ui.dessiner(etat, time.ticks_ms())
meteo = Meteo(reglages)  # lance la connexion Wi-Fi (sans attendre)
try:
    usb_ok = pc.demarrer()
except Exception as e:  # le PC n'était peut-être pas prêt (démarrage de Windows)
    noter_erreur(e)
    usb_ok = False

entree = select.poll()
entree.register(sys.stdin, select.POLLIN)
tampon = ""


def lire_ligne():
    """Renvoie une ligne complète reçue sur le port série, ou None.
    Les caractères bizarres (parasites au démarrage du PC) sont ignorés."""
    global tampon
    while entree.poll(0):
        c = sys.stdin.read(1)
        if c in ("\n", "\r"):
            if tampon:
                ligne = tampon
                tampon = ""
                return ligne
        elif " " <= c <= "~" or ord(c) > 159:
            tampon += c
            if len(tampon) > 300:
                tampon = ""
    return None


TOUCHES_LISIBLES = {"win": "Win", "ctrl": "Ctrl", "alt": "Alt", "shift": "Maj"}


def joli_raccourci(texte):
    morceaux = []
    for m in texte.split("+"):
        m = m.strip().lower()
        morceaux.append(TOUCHES_LISIBLES.get(m, m.upper() if len(m) == 1 else m.capitalize()))
    return " + ".join(morceaux)


REACTIONS_MEDIA = {
    "VOL+": ("son", "Volume +"), "VOL-": ("son", "Volume -"), "MUTE": ("muet", "Muet"),
    "PLAY": ("musique", "Lecture / pause"), "NEXT": ("musique", "Suivant"),
    "PREV": ("musique", "Précédent"), "LUM+": ("soleil", "Luminosité +"),
    "LUM-": ("soleil", "Luminosité -"),
}


def reaction_action(arg):
    """Réaction de la mascotte à une commande exécutée par le programme PC (EVT ACTION …)."""
    mots = arg.split(" ", 1)
    nom = mots[0].upper()
    reste = mots[1].strip() if len(mots) > 1 else ""
    if nom == "APP":
        ui.reagir("appli", reste.capitalize() or "Application")
    elif nom in ("LUM", "LUM+", "LUM-"):
        ui.reagir("soleil", "Luminosité %s %%" % reste if reste else "Luminosité")
    elif nom == "VERROU":
        ui.reagir("cadenas", "Verrouillage")
    elif nom == "ECRAN_OFF":
        ui.reagir("lune", "Écran éteint")
    elif nom == "VEILLE":
        ui.reagir("lune", "Mise en veille")
    elif nom == "ARRET":
        ui.reagir("power", "Arrêt du PC…")
    elif nom == "ANNULER":
        ui.reagir("power", "Arrêt annulé")
    else:
        ui.reagir("appli", arg[:24])


def executer(ligne):
    global derniere_donnee, ecran_allume
    mots = ligne.split(" ", 1)
    cmd = mots[0].upper()
    arg = mots[1] if len(mots) > 1 else ""
    if cmd == "PING":
        return "PONG"
    if cmd == "METEO":
        if etat["meteo"]:
            return "OK " + " | ".join("%s %d/%d pluie %d%% vers %sh" % (
                j["icone"], j["tmax"], j["tmin"], j["pluie"], j["heure_pluie"]) for j in etat["meteo"])
        return "ERR pas encore de meteo (" + (meteo.probleme or "attente") + ")"
    if cmd == "METEO_J":
        # météo envoyée par le programme PC : METEO_J jour icone max min pluie heure
        try:
            p = arg.split()
            i = int(p[0])
            heure = int(p[5])
            jour = {"icone": p[1], "tmax": int(p[2]), "tmin": int(p[3]), "pluie": int(p[4]),
                    "heure_pluie": heure if heure >= 0 else None}
        except (ValueError, IndexError):
            return "ERR utilise : METEO_J jour icone max min pluie heure"
        liste = list(etat["meteo"])
        while len(liste) <= i:
            liste.append(jour)
        liste[i] = jour
        etat["meteo"] = liste
        return "OK"
    # --- données du programme PC -------------------------------------------
    if cmd in ("STAT", "GPU", "PERF", "EVT", "TEMPS", "METEO_J"):
        derniere_donnee = time.ticks_ms()
        etat["connecte"] = True
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
    if cmd == "PERF":
        try:
            perf["cpu_temp"], perf["fps"] = [int(x) for x in arg.split()][:2]
        except ValueError:
            return "ERR utilise : PERF temp_cpu fps"
        return "OK"
    if cmd == "TEMPS":
        try:
            a, mo, j, js, h, mi, s = [int(x) for x in arg.split()][:7]
            machine.RTC().datetime((a, mo, j, js, h, mi, s, 0))
        except (ValueError, OSError):
            return "ERR utilise : TEMPS annee mois jour jour_semaine h min s"
        return "OK"
    if cmd == "EVT":
        morceaux = arg.split(" ", 1)
        typ = morceaux[0].upper()
        val = morceaux[1].strip() if len(morceaux) > 1 else ""
        if typ == "CASQUE":
            ancien = evt["casque"]
            evt["casque"] = "" if val in ("", "-") else val
            if evt["casque"] and not ancien:
                ui.reagir("son", "Casque connecté")
            elif ancien and not evt["casque"]:
                ui.reagir("son", "Casque retiré")
        elif typ == "MANETTE":
            nouveau = 1 if val == "1" else 0
            if nouveau and not evt["manette"]:
                ui.reagir("manette", "Manette connectée")
            evt["manette"] = nouveau
        elif typ == "VERROU":
            evt["verrou"] = 1 if val == "1" else 0
        elif typ == "JEU":
            evt["jeu"] = "" if val in ("", "-") else val
        elif typ == "ACTION":
            reaction_action(val)
        else:
            return "ERR evenement inconnu : " + typ
        return "OK"
    # --- écran de l'ESP32 ----------------------------------------------------
    if cmd == "ECRAN_ESP":
        ecran_allume = arg.strip() != "0"
        if not ecran_allume:
            ecran.luminosite(0)
        return "OK"
    # --- clavier / souris / multimédia ----------------------------------------
    if not pc.is_open():
        return "ERR USB pas reconnu par le PC"
    if cmd == "KEY":
        if not pc.raccourci(arg):
            return "ERR touche inconnue : " + arg
        ui.reagir("clavier", joli_raccourci(arg))
        return "OK"
    if cmd == "TEXT":
        ignores = pc.taper(arg)
        ui.reagir("clavier", "Texte envoyé")
        return "OK" if ignores == 0 else "OK (%d caracteres ignores)" % ignores
    if cmd in MEDIA:
        pc.media(cmd)
        ui.reagir(*REACTIONS_MEDIA[cmd])
        return "OK"
    if cmd == "MOUSE":
        try:
            dx, dy = [int(v) for v in arg.split()]
        except ValueError:
            return "ERR utilise : MOUSE dx dy"
        pc.souris(dx, dy)
        ui.reagir("souris", "Souris", bandeau=False)
        return "OK"
    if cmd == "CLIC":
        pc.clic(1)
        ui.reagir("souris", "Clic", bandeau=False)
        return "OK"
    if cmd == "CLICD":
        pc.clic(2)
        ui.reagir("souris", "Clic droit", bandeau=False)
        return "OK"
    if cmd == "MOLETTE":
        try:
            pc.souris(molette=int(arg))
        except ValueError:
            return "ERR utilise : MOLETTE n"
        ui.reagir("souris", "Défilement", bandeau=False)
        return "OK"
    return "ERR commande inconnue : " + cmd


prochaine_image = time.ticks_ms()
while True:
    try:
        # 1. tous les messages en attente (au plus 30 d'un coup)
        for _ in range(30):
            ligne = lire_ligne()
            if ligne is None:
                break
            print(executer(ligne.strip()))
        maintenant = time.ticks_ms()
        if etat["connecte"] and time.ticks_diff(maintenant, derniere_donnee) > ATTENTE_ABSENT:
            etat["connecte"] = False
        # météo : seulement quand le PC n'est pas utilisé (le téléchargement bloque 1 à 3 s)
        if (not etat["connecte"] or evt["verrou"]) and meteo.a_mettre_a_jour(maintenant):
            if meteo.mettre_a_jour(maintenant):
                etat["meteo"] = meteo.jours
        # 2. une nouvelle image si c'est l'heure
        if time.ticks_diff(maintenant, prochaine_image) >= 0:
            prochaine_image = time.ticks_add(maintenant, IMAGE_MS)
            if ecran_allume:
                ui.dessiner(etat, maintenant)
                voulue = ui.luminosite_voulue(maintenant)
                if voulue != luminosite_actuelle:
                    luminosite_actuelle = voulue
                    ecran.luminosite(voulue)
            else:
                luminosite_actuelle = -1
    except Exception as e:  # une erreur ne doit jamais arrêter la télécommande
        noter_erreur(e)
        print("ERR interne : %s" % e)
        time.sleep_ms(200)
    time.sleep_ms(2)
```

## tools/agent/agent_pc.py

```python
#!/usr/bin/env python3
"""Programme PC de la Télécommande ESP32 (Windows).

- Envoie chaque seconde à l'ESP32 : CPU, RAM, volume, batterie (ligne « STAT »).
- Envoie chaque seconde la carte graphique NVIDIA : température, charge, mémoire (ligne « GPU »).
- Surveille et signale : sortie audio (casque ou haut-parleurs), manette, PC verrouillé,
  jeu Steam en cours (lignes « EVT »).
- Mode gamer : température du processeur (LibreHardwareMonitor) et FPS du jeu (PresentMon),
  ligne « PERF » chaque seconde.
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

    def exe(self):
        trouves = sorted(glob.glob(str(DOSSIER / "bin" / "PresentMon*.exe")))
        return trouves[-1] if trouves else None

    def demarrer(self):
        chemin = self.exe()
        if chemin is None:
            self.probleme = "PresentMon absent de tools\\agent\\bin"
            return False
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
        for ligne in self.proc.stdout:
            morceaux = ligne.strip().split(",")
            if col is None:
                if "ProcessID" in morceaux and "MsBetweenPresents" in morceaux:
                    col = {nom: morceaux.index(nom) for nom in
                           ("Application", "ProcessID", "SwapChainAddress", "MsBetweenPresents")
                           if nom in morceaux}
                else:
                    self.probleme = "PresentMon : " + ligne.strip()[:120]
                continue
            try:
                pid = int(morceaux[col["ProcessID"]])
                ms = float(morceaux[col["MsBetweenPresents"]])
                chaine = morceaux[col["SwapChainAddress"]] if "SwapChainAddress" in col else ""
                app = morceaux[col["Application"]].lower() if "Application" in col else ""
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
            for nom, outil in (("LibreHardwareMonitor", self.lhm), ("PresentMon", self.fps)):
                if outil.probleme != self.problemes.get(nom):
                    self.problemes[nom] = outil.probleme
                    print(f"[agent] {nom} : {outil.probleme or 'OK'}")

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
```

## tools/agent/installer_demarrage.ps1

```powershell
# Démarrage automatique de l'agent de la Télécommande ESP32 (avec droits administrateur).
# À lancer UNE SEULE FOIS dans un PowerShell ouvert « en tant qu'administrateur » :
#   powershell -ExecutionPolicy Bypass -File tools\agent\installer_demarrage.ps1
# Pour supprimer : Unregister-ScheduledTask -TaskName "ESP32 Telecommande Agent" -Confirm:$false

$python = & py -c "import sys; print(sys.executable)"
$pythonw = Join-Path (Split-Path $python) "pythonw.exe"
$agent = Join-Path $PSScriptRoot "agent_pc.py"

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$agent`" --service" -WorkingDirectory $PSScriptRoot
$declencheur = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$compte = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest -LogonType Interactive
$reglages = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName "ESP32 Telecommande Agent" -Action $action -Trigger $declencheur `
    -Principal $compte -Settings $reglages -Force | Out-Null

Write-Host "Tâche « ESP32 Telecommande Agent » créée (pythonw : $pythonw)."
Write-Host "Elle démarrera à chaque ouverture de session. Pour la lancer tout de suite :"
Write-Host "  Start-ScheduledTask -TaskName 'ESP32 Telecommande Agent'"
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
