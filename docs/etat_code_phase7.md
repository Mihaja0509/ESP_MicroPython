# État du code — avant la Phase 7

Relevé du 2026-11-02, après le commit de la Phase 6 (`4336f7788df9a0c081dee536b141409fb013fd36`, poussé sur `origin/main`).
Aucun fichier de code modifié. Secrets (`appareils.json`, `reglages.json`, `secrets.py`) : contenu ni lu ni copié.

## a. Empreintes SHA-256 (16 car., CRLF → LF)

Commande :

```
py -X utf8 -c "import hashlib,sys; [print(f, hashlib.sha256(open(f,'rb').read().replace(b'\r\n',b'\n')).hexdigest()[:16]) for f in sys.argv[1:]]" esp/main.py esp/lib/ui.py tools/agent/agent_pc.py tools/agent/serveur_app.py app/lib/theme.dart app/lib/connexion.dart app/lib/ecrans/accueil.dart app/lib/ecrans/controles.dart app/lib/widgets/anneau.dart
```

| Fichier | Empreinte | « après » Phase 6 |
|---|---|---|
| `esp/main.py` | `bfa2089b8cf1c507` | identique |
| `esp/lib/ui.py` | `c1cb124fcd29a908` | identique |
| `tools/agent/agent_pc.py` | `8e9cee7c2f4d007a` | identique |
| `tools/agent/serveur_app.py` | `c0173d2d96390b94` | identique |
| `app/lib/theme.dart` | `4555169ea29d5035` | identique |
| `app/lib/connexion.dart` | `1fead79394ca5deb` | identique |
| `app/lib/ecrans/accueil.dart` | `fa80d9eb715c4c48` | identique |
| `app/lib/ecrans/controles.dart` | `cfa199dcad8bbebd` | identique |
| `app/lib/widgets/anneau.dart` | `837794ed059d43c7` | identique |

## b. `tools\agent\agent.log`

Codes PIN et tokens remplacés par `******`. Le journal n'a pas d'horodatage par ligne : les « 2 derniers jours » sont repérés par les en-têtes `--- démarrage <date> ---` (le fichier commence le 2026-11-01 19:58:33, donc tout le fichier est dans la fenêtre). Numéros de ligne à gauche.

Fichier : 5175 lignes

#### 120 dernières lignes

```
 5056: [agent] LibreHardwareMonitor : OK
 5057: [agent] PresentMon : PresentMon (en-tête non trouvé) : warning: a trace session named "ESP32Telecommande" is already running and it will be stopped.
 5058: [agent] Météo : OK
 5059: [agent] événement : CASQUE = XiaomiPro
 5060: [agent] événement : MANETTE = 0
 5061: [agent] événement : VERROU = 0
 5062: [agent] événement : JEU = -
 5063: [agent] PresentMon : OK
 5064: [agent] Météo : météo : position non réglée : remplis D:\FlutterProject\Esp32Maison\Micro\tools\agent\reglages.json
 5065: --- démarrage 2026-11-01 21:40:31 ---
 5066: [agent] impossible d'ouvrir COM4 : could not open port 'COM4': PermissionError(13, 'Access is denied.', None, 5)
 5067: [agent] ESP32 connectée sur COM4
 5068: [agent] LibreHardwareMonitor : OK
 5069: [agent] PresentMon : OK
 5070: [agent] Météo : OK
 5071: [agent] événement : CASQUE = XiaomiPro
 5072: [agent] événement : MANETTE = 0
 5073: [agent] événement : VERROU = 0
 5074: [agent] événement : JEU = -
 5075: [agent] événement : VERROU = 1
 5076: [agent] événement : VERROU = 0
 5077: [agent] événement : JEU = God of War Ragnarok
 5078: [agent] événement : JEU = -
 5079: [agent] événement : CASQUE = -
 5080: [agent] événement : CASQUE = HECATE G30
 5081: [agent] événement : CASQUE = XiaomiPro
 5082: Exception in thread Thread-2 (boucle_lecture):
 5083: [agent] pause : port COM libéré
 5084: Traceback (most recent call last):
 5085:   File "D:\Dadou\Dev\Python\Python313\Lib\threading.py", line 1044, in _bootstrap_inner
 5086:     self.run()
 5087:     ~~~~~~~~^^
 5088:   File "D:\Dadou\Dev\Python\Python313\Lib\threading.py", line 995, in run
 5089:     self._target(*self._args, **self._kwargs)
 5090:     ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 5091:   File "D:\FlutterProject\Esp32Maison\Micro\tools\agent\agent_pc.py", line 805, in boucle_lecture
 5092:     subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
 5093:                 ^^^^^^^^^^^^^^^^^^^^^^^^^
 5094:   File "D:\FlutterProject\Esp32Maison\Micro\tools\agent\agent_pc.py", line 168, in lire_ligne
 5095:     print("[agent] liaison perdue")
 5096:        ^^^^^^^^^^^^^^
 5097:   File "C:\Users\xisda\AppData\Roaming\Python\Python313\site-packages\serial\serialwin32.py", line 285, in read
 5098:     ctypes.byref(self._overlapped_read))
 5099:     ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
 5100: TypeError: byref() argument must be a ctypes instance, not 'NoneType'
 5101: [agent] impossible d'ouvrir COM4 : Cannot configure port, something went wrong. Original message: OSError(22, 'A device which does not exist was specified.', None, 433)
 5102: [agent] ESP32 connectée sur COM4
 5103: [agent] événement : CASQUE = XiaomiPro
 5104: [agent] événement : MANETTE = 0
 5105: [agent] événement : VERROU = 0
 5106: [agent] événement : JEU = -
 5107: [agent] événement : CASQUE = -
 5108: --- démarrage 2026-11-01 22:14:54 ---
 5109: [agent] adresses du PC pour l'app : 192.168.100.7 (Wi-Fi), 100.120.66.61 (Tailscale)
 5110: [agent] serveur app prêt sur le port 8765
 5111: [agent] ESP32 connectée sur COM4
 5112: [agent] LibreHardwareMonitor : OK
 5113: [agent] PresentMon : PresentMon (en-tête non trouvé) : warning: a trace session named "ESP32Telecommande" is already running and it will be stopped.
 5114: [agent] Météo : OK
 5115: [agent] événement : CASQUE = -
 5116: [agent] événement : MANETTE = 0
 5117: [agent] événement : VERROU = 0
 5118: [agent] événement : JEU = -
 5119: [agent] PresentMon : OK
 5120: [agent] code d'appairage : ******
 5121: [esp32] ERR interne : 'str' object has no attribute 'capitalize'
 5122: Exception in thread Thread-3 (boucle_lecture):
 5123: [agent] pause : port COM libéré
 5124: Traceback (most recent call last):
 5125:   File "D:\Dadou\Dev\Python\Python313\Lib\threading.py", line 1044, in _bootstrap_inner
 5126:     self.run()
 5127:     ~~~~~~~~^^
 5128:   File "D:\Dadou\Dev\Python\Python313\Lib\threading.py", line 995, in run
 5129:     self._target(*self._args, **self._kwargs)
 5130:     ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 5131:   File "D:\FlutterProject\Esp32Maison\Micro\tools\agent\agent_pc.py", line 979, in boucle_lecture
 5132:     self._reveil_discret("liaison USB revenue")
 5133:     ^^^^^^^^^^^^^^^^^^^^^
 5134:   File "D:\FlutterProject\Esp32Maison\Micro\tools\agent\agent_pc.py", line 177, in lire_ligne
 5135:     self.ser = None
 5136:        ^^^^^^^^^^^^
 5137:   File "C:\Users\xisda\AppData\Roaming\Python\Python313\site-packages\serial\serialwin32.py", line 285, in read
 5138:     ctypes.byref(self._overlapped_read))
 5139:     ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
 5140: TypeError: byref() argument must be a ctypes instance, not 'NoneType'
 5141: [agent] ESP32 connectée sur COM4
 5142: [agent] événement : CASQUE = -
 5143: [agent] événement : MANETTE = 0
 5144: [agent] événement : VERROU = 0
 5145: [agent] événement : JEU = -
 5146: [agent] événement : VERROU = 1
 5147: [agent] événement : VERROU = 0
 5148: [agent] événement : VERROU = 1
 5149: [agent] événement : VERROU = 0
 5150: [agent] événement : VERROU = 1
 5151: [agent] événement : VERROU = 0
 5152: [agent] événement : CASQUE = XiaomiPro
 5153: [agent] événement : CASQUE = -
 5154: [agent] événement : JEU = God of War Ragnarok
 5155: [agent] événement : JEU = -
 5156: [agent] événement : VERROU = 1
 5157: [agent] événement : VERROU = 0
 5158: [agent] événement : CASQUE = XiaomiPro
 5159: --- démarrage 2026-11-02 07:24:12 ---
 5160: [agent] adresses du PC pour l'app : 192.168.100.7 (Wi-Fi)
 5161: [agent] serveur app prêt sur le port 8765
 5162: [agent] LibreHardwareMonitor : LibreHardwareMonitor injoignable (URLError)
 5163: [agent] PresentMon : OK
 5164: [agent] Météo : OK
 5165: [agent] événement : CASQUE = -
 5166: [agent] événement : MANETTE = 0
 5167: [agent] événement : VERROU = 0
 5168: [agent] événement : JEU = -
 5169: [agent] LibreHardwareMonitor : LibreHardwareMonitor injoignable (TimeoutError)
 5170: [agent] LibreHardwareMonitor : OK
 5171: [agent] ESP32 connectée sur COM4
 5172: [agent] événement : CASQUE = -
 5173: [agent] événement : MANETTE = 0
 5174: [agent] événement : VERROU = 0
 5175: [agent] événement : JEU = -
```

#### Lignes « ARRET / Arrêt / démarrage / ESP32 / muet » depuis le 2026-10-31 (25 lignes)

```
    1: --- démarrage 2026-11-01 19:58:33 ---
    2: [agent] ESP32 connectée sur COM4
    9: --- démarrage 2026-11-01 20:05:08 ---
   10: [agent] ESP32 connectée sur COM4
 4863: --- démarrage 2026-11-01 20:34:41 ---
 4864: --- démarrage 2026-11-01 20:43:08 ---
 4865: [agent] ESP32 connectée sur COM4
 5000: --- démarrage 2026-11-01 20:50:38 ---
 5003: [agent] ESP32 connectée sur COM4
 5005: [agent] PresentMon : PresentMon (en-tête non trouvé) : warning: a trace session named "ESP32Telecommande" is already running and it will be stopped.
 5014: --- démarrage 2026-11-01 20:53:02 ---
 5015: [agent] ESP32 connectée sur COM4
 5049: [agent] ESP32 connectée sur COM4
 5054: --- démarrage 2026-11-01 21:36:59 ---
 5055: [agent] ESP32 connectée sur COM4
 5057: [agent] PresentMon : PresentMon (en-tête non trouvé) : warning: a trace session named "ESP32Telecommande" is already running and it will be stopped.
 5065: --- démarrage 2026-11-01 21:40:31 ---
 5067: [agent] ESP32 connectée sur COM4
 5102: [agent] ESP32 connectée sur COM4
 5108: --- démarrage 2026-11-01 22:14:54 ---
 5111: [agent] ESP32 connectée sur COM4
 5113: [agent] PresentMon : PresentMon (en-tête non trouvé) : warning: a trace session named "ESP32Telecommande" is already running and it will be stopped.
 5141: [agent] ESP32 connectée sur COM4
 5159: --- démarrage 2026-11-02 07:24:12 ---
 5171: [agent] ESP32 connectée sur COM4
```

## c. `powercfg /a`

```
The following sleep states are available on this system:
    Standby (S0 Low Power Idle) Network Connected

The following sleep states are not available on this system:
    Standby (S1)
	The system firmware does not support this standby state.
	This standby state is disabled when S0 low power idle is supported.

    Standby (S2)
	The system firmware does not support this standby state.
	This standby state is disabled when S0 low power idle is supported.

    Standby (S3)
	This standby state is disabled when S0 low power idle is supported.

    Hibernate
	Hibernation has not been enabled.

    Hybrid Sleep
	Standby (S3) is not available.
	Hibernation is not available.
	The hypervisor does not support this standby state.

    Fast Startup
	Hibernation is not available.
```

## d. Tâche planifiée « ESP32 Telecommande Agent »

`Get-ScheduledTask -TaskName 'ESP32 Telecommande Agent' | Select-Object -ExpandProperty <X> | Format-List`

### -ExpandProperty Principal

```
DisplayName         : 
GroupId             : 
Id                  : Author
LogonType           : Interactive
RunLevel            : Highest
UserId              : xisda
ProcessTokenSidType : Default
RequiredPrivilege   : 
PSComputerName      :
```

### -ExpandProperty Actions

```
Id               : 
Arguments        : "D:\FlutterProject\Esp32Maison\Micro\tools\agent\agent_pc.py" --service
Execute          : D:\Dadou\Dev\Python\Python313\pythonw.exe
WorkingDirectory : D:\FlutterProject\Esp32Maison\Micro\tools\agent
PSComputerName   :
```

### -ExpandProperty Settings

```
AllowDemandStart                : True
AllowHardTerminate              : True
Compatibility                   : Win7
DeleteExpiredTaskAfter          : 
DisallowStartIfOnBatteries      : False
Enabled                         : True
ExecutionTimeLimit              : PT0S
Hidden                          : False
IdleSettings                    : MSFT_TaskIdleSettings
MultipleInstances               : IgnoreNew
NetworkSettings                 : MSFT_TaskNetworkSettings
Priority                        : 7
RestartCount                    : 0
RestartInterval                 : 
RunOnlyIfIdle                   : False
RunOnlyIfNetworkAvailable       : False
StartWhenAvailable              : False
StopIfGoingOnBatteries          : False
WakeToRun                       : False
DisallowStartOnRemoteAppSession : False
UseUnifiedSchedulingEngine      : True
MaintenanceSettings             : 
volatile                        : False
PSComputerName                  :
```

## e. Python côté PC

La tâche lance `D:\Dadou\Dev\Python\Python313\pythonw.exe` ; `py` pointe sur le même dossier (`sys.executable` = `D:\Dadou\Dev\Python\Python313\python.exe`). Chaque commande a été passée avec `py` et avec ce `python.exe` : mêmes résultats. Rien installé.

```
> py --version
Python 3.13.15
> py -c "import tkinter; print('tkinter', tkinter.TkVersion)"
tkinter 8.6
> py -c "import PIL; print('Pillow', PIL.__version__)"
ModuleNotFoundError: No module named 'PIL'
> py -c "import mss; print('mss', mss.__version__)"
ModuleNotFoundError: No module named 'mss'
> py -c "import screen_brightness_control as s; print('sbc', s.__version__, s.list_monitors())"
sbc 0.27.2 ['BOE Display Technology Generic Monitor']
```

## f. Écrans

```
> py -c "import ctypes; u=ctypes.windll.user32; u.SetProcessDPIAware(); print(u.GetSystemMetrics(0), u.GetSystemMetrics(1), 'ecrans', u.GetSystemMetrics(80))"
2560 1600 ecrans 1
```

## g. Carte ESP32

`tools\agent\PAUSE` créé, port trouvé : **COM4** (`303a:4001`, n° de série A0F262E394140000). 1re commande `exec` : `ClearCommError` → relancée après 3 s : OK.

```
> py -m mpremote devs
COM4 A0F262E394140000 303a:4001 Microsoft None
COM5 None 0000:0000 Microsoft None
COM6 None 0000:0000 Microsoft None
COM7 None 0000:0000 Microsoft None
COM8 None 0000:0000 Microsoft None

> py -m mpremote connect COM4 exec "import machine, os, sys; ..."
reset_cause 5
(name='micropython', version=(1, 29, 0, ''), _machine='Generic ESP32S3 module with Octal-SPIRAM with ESP32-S3', _mpy=11014, _build='ESP32_GENERIC_S3-SPIRAM_OCT', _thread='GIL')
['assets', 'boot.py', 'erreur.txt', 'lib', 'main.py']
['hid_pc.py', 'lcd.py', 'meteo.py', 'polices.py', 'ui.py', 'usb']

> import secrets (wifi_regle)
secrets absent   (ImportError : pas de secrets.py sur la carte)
```

`reset_cause 5` = `machine.SOFT_RESET` (dû au mode raw REPL de mpremote).

### `:erreur.txt` (36 lignes, tout le fichier)

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
Traceback (most recent call last):
  File "main.py", line 272, in <module>
  File "main.py", line 228, in executer
  File "main.py", line 87, in joli_raccourci
AttributeError: 'str' object has no attribute 'capitalize'
Traceback (most recent call last):
  File "main.py", line 280, in <module>
  File "main.py", line 213, in executer
  File "main.py", line 108, in reaction_action
AttributeError: 'str' object has no attribute 'capitalize'
Traceback (most recent call last):
  File "main.py", line 280, in <module>
  File "main.py", line 236, in executer
  File "main.py", line 90, in joli_raccourci
AttributeError: 'str' object has no attribute 'capitalize'
Traceback (most recent call last):
  File "main.py", line 280, in <module>
  File "main.py", line 236, in executer
  File "main.py", line 90, in joli_raccourci
AttributeError: 'str' object has no attribute 'capitalize'
```

### Reset puis reprise de l'agent

`py -m mpremote connect COM4 reset` : OK. `PAUSE` supprimé ; fin de `agent.log` 8 s après :

```
[agent] pause : port COM libéré
[agent] impossible d'ouvrir COM4 : could not open port 'COM4': FileNotFoundError(2, 'The system cannot find the file specified.', None, 2)
[agent] ESP32 connectée sur COM4
[agent] réveil sans utilisateur (liaison USB revenue) : ESP32 laissée en veille
```

## Points à retenir pour la Phase 7

- Mise en veille : seul **S0 Low Power Idle (Modern Standby)** existe ; pas de S3, **hibernation désactivée** (donc pas de démarrage rapide ni de veille hybride). `SetSuspendState 0,1,0` (utilisé par l'agent) ne peut pas faire de vraie veille S3.
- **Pillow et mss absents** de l'interpréteur de la tâche (tkinter 8.6 et screen_brightness_control 0.27.2 présents). Un seul écran, 2560×1600.
- `str.capitalize` n'existe pas en MicroPython : 4 plantages dans `erreur.txt` (`joli_raccourci`, `reaction_action`) ; aussi visible dans `agent.log` (`ERR interne`). 4 `UnicodeError` dans `lire_ligne` (anciennes versions de `main.py`, n° de ligne 156).
- `agent.log` : 2 traces `TypeError: byref() ... NoneType` dans `boucle_lecture` → `lire_ligne` (pyserial lit pendant que le port est fermé par la pause).
- Tâche planifiée : `RestartCount 0` (pas de redémarrage auto si l'agent plante), `StartWhenAvailable False`.
- Pas de `secrets.py` sur la carte (Wi-Fi ESP32 non réglé, météo par l'agent seulement).
