# Micro — Phase 9 : jeux hors Steam + widget Android

Date : 2026-11-03 · Statut : à appliquer · Base : commit 48974c1 (« Phase 8 : aperçu de l'écran et widget Android »), blocs « avant » copiés du dépôt GitHub à ce commit.

## Ce que contient la phase

1. **Mode jeu pour tous les jeux.** Avant, l'agent ne reconnaissait que les jeux lancés par Steam (registre `RunningAppID`). Maintenant, si Steam ne dit rien, il regarde la fenêtre au premier plan. C'est un jeu si :
   - son .exe est dans un dossier de jeux (`steamapps\common`, `Epic Games`, `Rockstar Games`, `XboxGames`, `GOG Games`, `Games`…) ;
   - ou elle est en plein écran (ou fenêtré sans bordure) avec la carte graphique à plus de 30 %.
   Il faut que ça dure 3 s de suite pour éviter les faux départs. Les lanceurs (`Launcher.exe`…), les navigateurs, VLC, Netflix, Discord, OBS… ne sont jamais des jeux. Un jeu repéré le reste tant que son programme tourne, même en Alt+Tab. Le nom affiché vient du titre de la fenêtre, sinon du dossier du jeu (ex. « AO Tennis 2 »).
2. **Fichier facultatif `tools\agent\jeux.json`** pour forcer un cas qui raterait : `{"jeux": ["tennis2.exe"], "pas_des_jeux": ["obs64.exe"]}`. Il est relu toutes les 10 s, sans redémarrer l'agent.
3. **Widget Android.** Un widget Android n'apparaît jamais tout seul : il faut le poser sur l'écran d'accueil. Nouvelle carte dans **Réglages** : « Ajouter le widget à l'écran d'accueil ». Elle ouvre la fenêtre d'ajout du lanceur, dit si le widget est posé, et donne l'aide Xiaomi si le téléphone refuse (autorisation « Raccourcis de l'écran d'accueil »). Le widget gagne aussi une image d'aperçu pour les lanceurs qui n'affichent pas `previewLayout`.

## Partie 1 — Nouveaux fichiers

Aucun.

## Partie 2 — Fichiers remplacés en entier

### `app/android/app/src/main/kotlin/com/mmdigitek/esp_micro/MainActivity.kt`

```kotlin
package com.mmdigitek.esp_micro

import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.os.Build
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        // L'app prévient le widget quand les favoris changent (lib/widget_android.dart).
        // Phase 9 : l'app peut aussi demander au lanceur de poser le widget (« epingler »)
        // et savoir combien de widgets Dadou sont posés (« nombre »).
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "dadou/widget")
            .setMethodCallHandler { appel, resultat ->
                val manager = AppWidgetManager.getInstance(applicationContext)
                val composant = ComponentName(applicationContext, DadouWidget::class.java)
                when (appel.method) {
                    "mettreAJour" -> {
                        DadouWidget.toutMettreAJour(applicationContext)
                        resultat.success(true)
                    }
                    "nombre" -> resultat.success(manager.getAppWidgetIds(composant).size)
                    "epingler" -> {
                        val possible = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
                            manager.isRequestPinAppWidgetSupported
                        resultat.success(
                            possible && manager.requestPinAppWidget(composant, null, null)
                        )
                    }
                    else -> resultat.notImplemented()
                }
            }
    }
}
```

### `app/lib/widget_android.dart`

```dart
// Widget de l'écran d'accueil du téléphone (Phase 8) : les 4 premiers favoris.
// Les boutons sont enregistrés dans les préférences de l'app (lues par DadouWidget.kt),
// puis Android est prévenu pour redessiner le widget.
// Phase 9 : carte « Widget » des Réglages (poser le widget depuis l'app, aide Xiaomi).
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'actions.dart';
import 'connexion.dart';
import 'theme.dart';

const _canal = MethodChannel('dadou/widget');
const int boutonsWidget = 4;

Future<void> majWidget(Connexion cx) async {
  final boutons = [
    for (final a in favorisResolus(cx).take(boutonsWidget)) {'nom': a.nom, 'ligne': a.ligne, 'code': a.code},
  ];
  try {
    final p = await SharedPreferences.getInstance();
    await p.setString('widget_boutons', jsonEncode(boutons));
    await _canal.invokeMethod<bool>('mettreAJour');
  } catch (_) {
    // pas de widget (tests, autre plateforme) : rien à faire
  }
}

/// Nombre de widgets Dadou posés sur l'écran d'accueil (-1 si inconnu).
Future<int> widgetsPoses() async {
  try {
    return await _canal.invokeMethod<int>('nombre') ?? -1;
  } catch (_) {
    return -1;
  }
}

/// Demande au lanceur d'Android de poser le widget (une fenêtre de confirmation s'ouvre).
Future<bool> epinglerWidget() async {
  try {
    return await _canal.invokeMethod<bool>('epingler') ?? false;
  } catch (_) {
    return false;
  }
}

/// Carte des Réglages : poser le widget, et quoi faire si le téléphone (Xiaomi) refuse.
class CarteWidgetAndroid extends StatefulWidget {
  final Connexion cx;

  const CarteWidgetAndroid({super.key, required this.cx});

  @override
  State<CarteWidgetAndroid> createState() => _CarteWidgetAndroidState();
}

class _CarteWidgetAndroidState extends State<CarteWidgetAndroid> with WidgetsBindingObserver {
  int _poses = -1;
  bool _demande = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _compter();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // au retour sur l'app (après la fenêtre du lanceur) : recompter
    if (state == AppLifecycleState.resumed) _compter();
  }

  Future<void> _compter() async {
    final n = await widgetsPoses();
    if (mounted) setState(() => _poses = n);
  }

  Future<void> _poser() async {
    await majWidget(widget.cx); // le widget aura tout de suite les bons favoris
    final ok = await epinglerWidget();
    if (!mounted) return;
    setState(() => _demande = true);
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(ok
          ? 'Confirme dans la fenêtre du téléphone (« Ajouter »)'
          : "Ce téléphone refuse l'ajout direct : suis l'aide ci-dessous"),
    ));
    Future.delayed(const Duration(seconds: 3), _compter);
  }

  @override
  Widget build(BuildContext context) {
    final favoris = favorisResolus(widget.cx).length;
    final String statut;
    if (_poses > 0) {
      statut = _poses == 1 ? 'Widget posé sur l\'écran d\'accueil' : '$_poses widgets posés';
    } else if (_poses == 0) {
      statut = 'Aucun widget posé pour l\'instant';
    } else {
      statut = '';
    }
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre("Widget de l'écran d'accueil", icone: Icons.widgets_rounded),
          Text(
            favoris == 0
                ? "Ajoute d'abord des favoris (Contrôles, appui long sur un bouton)."
                : 'Il affichera tes ${favoris < boutonsWidget ? favoris : boutonsWidget} premiers favoris.',
            style: const TextStyle(color: Couleurs.doux),
          ),
          if (statut.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(statut, style: TextStyle(color: _poses > 0 ? Couleurs.vert : Couleurs.gris)),
          ],
          const SizedBox(height: 10),
          FilledButton.icon(
            icon: const Icon(Icons.add_to_home_screen_rounded),
            label: const Text("Ajouter le widget à l'écran d'accueil"),
            onPressed: _poser,
          ),
          if (_demande && _poses <= 0) ...[
            const SizedBox(height: 10),
            const Text(
              "Rien ne s'est affiché ? Sur Xiaomi :\n"
              '1. Paramètres → Applications → Gérer les applications → Dadou → '
              'Autres autorisations → « Raccourcis de l\'écran d\'accueil » → Autoriser, '
              'puis appuie de nouveau sur le bouton.\n'
              '2. Ou à la main : appui long sur un espace vide de l\'écran d\'accueil → '
              'Widgets → cherche « Dadou » → fais glisser le widget.',
              style: TextStyle(color: Couleurs.gris, height: 1.45),
            ),
          ],
        ],
      ),
    );
  }
}
```

## Partie 3 — Modifications « avant → après » (dans l'ordre)

### Modification 1 — `tools/agent/agent_pc.py`

Détecteur de jeux hors Steam, placé juste après la fonction jeu_steam().

**Avant :**

```python
    return f"Jeu Steam {appid}"


class LecteurLHM:
```

**Après :**

```python
    return f"Jeu Steam {appid}"


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


class LecteurLHM:
```

### Modification 2 — `tools/agent/agent_pc.py`

L'agent crée le détecteur au démarrage.

**Avant :**

```python
        self.fps = CompteurFPS()
```

**Après :**

```python
        self.fps = CompteurFPS()
        self.jeux = DetecteurJeu()   # Phase 9 : jeux hors Steam
```

### Modification 3 — `tools/agent/agent_pc.py`

Chaque seconde, le jeu en cours vient du détecteur (Steam + hors Steam).

**Avant :**

```python
        jeu = jeu_steam()
```

**Après :**

```python
        jeu = self.jeux.jeu(gpu()[1])
```

### Modification 4 — `tools/agent/agent_pc.py`

En-tête du fichier : mention du nouveau comportement.

**Avant :**

```python
  jeu Steam en cours (lignes « EVT »).
```

**Après :**

```python
  jeu en cours, Steam ou non (lignes « EVT »).
```

### Modification 5 — `app/android/app/src/main/res/xml/widget_dadou_info.xml`

Image d'aperçu pour les lanceurs qui n'affichent pas previewLayout (certains Xiaomi).

**Avant :**

```xml
    android:previewLayout="@layout/widget_dadou"
```

**Après :**

```xml
    android:previewImage="@mipmap/ic_launcher"
    android:previewLayout="@layout/widget_dadou"
```

### Modification 6 — `app/lib/ecrans/reglages.dart`

Import de la carte Widget.

**Avant :**

```dart
import '../theme.dart';
```

**Après :**

```dart
import '../theme.dart';
import '../widget_android.dart';
```

### Modification 7 — `app/lib/ecrans/reglages.dart`

Carte « Widget de l'écran d'accueil » entre Appairage et l'aide Tailscale.

**Avant :**

```dart
        const SizedBox(height: 14),
        const Carte(
```

**Après :**

```dart
        const SizedBox(height: 14),
        CarteWidgetAndroid(cx: cx),
        const SizedBox(height: 14),
        const Carte(
```

## Liste de contrôle

| Contrôle | Attendu |
|---|---|
| Test à blanc : les 7 blocs « avant » | chacun trouvé exactement 1 fois |
| `py -m py_compile tools\agent\agent_pc.py` | aucune erreur |
| `flutter analyze` (dans app/) | No issues found |
| `flutter build apk --release` (dans app/) | APK créée |
| `git status` | seuls agent_pc.py, widget_dadou_info.xml, reglages.dart, MainActivity.kt, widget_android.dart modifiés (+ ce document) |

Après le commit : redémarrer la tâche planifiée (admin) : `Stop-ScheduledTask "ESP32 Telecommande Agent"` puis `Start-ScheduledTask "ESP32 Telecommande Agent"`.

## Tests sur l'appareil (Mihaja)

1. Lance RDR2 par `Launcher.exe`. Pendant le lanceur Rockstar, l'ESP32 reste en scène normale. Environ 3 s après l'arrivée du jeu, l'ESP32 passe en **scène jeu** avec « Red Dead Redemption 2 », les FPS et les températures.
2. Alt+Tab vers le bureau : la scène jeu reste. Quitte le jeu : retour en scène normale en 1 à 2 s.
3. Lance `F:\AO Tennis 2\tennis2.exe` : scène jeu avec « AO Tennis 2 » (ou le titre de la fenêtre).
4. YouTube en plein écran dans Chrome, puis une vidéo VLC en plein écran : **pas** de scène jeu.
5. Un jeu Steam (God of War) : marche comme avant.
6. Si un jeu n'est pas reconnu : crée `tools\agent\jeux.json` avec `{"jeux": ["nom_du_jeu.exe"]}`. Pas besoin de redémarrer, c'est pris en compte en 10 s. Envoie-moi aussi la ligne `[agent] …` de `agent.log`.
7. App → **Réglages** → « Ajouter le widget à l'écran d'accueil ». Une fenêtre Xiaomi s'ouvre → « Ajouter ». Le widget apparaît avec tes 4 premiers favoris, et la carte affiche « Widget posé ». Appuie sur un bouton du widget : le PC exécute l'action et un petit message s'affiche.
8. Si rien ne s'ouvre au 7 : Paramètres → Applications → Gérer les applications → Dadou → Autres autorisations → « Raccourcis de l'écran d'accueil » → Autoriser, puis recommence. Sinon : appui long sur l'écran d'accueil → Widgets → « Dadou ».
