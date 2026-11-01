# Micro — Phase 5 (version 2) : l'app Flutter « Dadou » + icône + écran plus fluide

- Date : 2026-11-01
- Statut : à appliquer (remplace la version 1, jamais appliquée)
- Étape : « Télécommande PC » — étape 5 (app Flutter, accès de partout avec Tailscale)
- Basée sur : fin de Phase 4 (fichiers du zip de la Phase 4, appliqués exactement) ; app = squelette `flutter create` non modifié
- Livraison : **`docs/micro_phase5_fichiers.zip`** (42 entrées). SHA-256 : `53c7edd0065cc53fa50a26f4c42dcafdc8e9bdfe58b6a46aeeb00232c7d1e71e`

## Ce que contient la phase

**Architecture** : téléphone (app) ⇄ WebSocket (port 8765) ⇄ **programme PC** ⇄ USB ⇄ ESP32. L'ESP32 n'a pas besoin de Wi-Fi (box en 5 GHz). De partout grâce à **Tailscale** (réseau privé gratuit entre le PC et le téléphone).

**App Android « Dadou »** (Flutter), avec son **icône** (le visage de la mascotte qui rit sur un fond crépuscule étoilé, icône adaptative Android), même style que l'écran de l'ESP32 (dégradé crépuscule, cartes « verre », police Inter, ta mascotte) ; le fond passe en **néon** pendant un jeu et en **nuit** quand le PC est verrouillé ou hors ligne :
- **Accueil** : ta mascotte animée (respire, cligne, sourit après une commande, casque sur les oreilles avec un casque ou en jeu, dort si le PC est verrouillé), heure, état ; en jeu : nom du jeu, **gros FPS**, barres de température CPU/GPU ; anneaux CPU / RAM / GPU animés, batterie, volume, températures, casque ; météo ; actions rapides (verrouiller, éteindre l'écran, écran ESP32, bureau).
- **Souris** : grand **pavé tactile** (glisser = bouger, toucher = clic, appui long ou toucher à deux doigts = clic droit, deux doigts = défiler, réglage de vitesse), boutons clic gauche / droit, **clavier** (le texte tapé est écrit sur le PC, accents compris) et touches rapides (Entrée, Échap, ⌫, Tab, flèches, Alt+Tab, Ctrl+C/V/Z, Win, F5, F11).
- **Contrôles** : volume (curseur + muet + précédent / lecture / suivant), luminosité, **lanceur d'apps** (liste de apps.json), alimentation (verrouiller, éteindre l'écran, veille et arrêt avec confirmation, annuler l'arrêt, écran ESP32).
- **Réglages** : adresse du PC, **appairage** avec un code à 6 chiffres affiché sur l'écran de l'ESP32 (personne d'autre ne peut commander le PC), aide Tailscale.

**Programme PC** (`agent_pc.py` remplacé + nouveau `serveur_app.py`) :
- Serveur WebSocket pour l'app : appairage par code (valable 2 min, 5 essais), téléphones appairés dans `tools\agent\appareils.json` (jamais commité), état envoyé 4 fois par seconde.
- Souris, clics, défilement et texte de l'app **exécutés directement sur le PC** (SendInput) : instantané et fluide. Les raccourcis (KEY…) et touches multimédia passent toujours par l'ESP32.
- Nouvelle commande `VOL n` (volume exact).
- **Mesures 4 fois par seconde** (CPU, RAM, volume, GPU, FPS) au lieu d'une ; les mesures plus lourdes (casque, manette, verrou, jeu, batterie, température CPU) restent à 1 fois par seconde. Les mesures continuent même si l'ESP32 est débranchée (pour l'app).
- Événements vers l'ESP32 : `EVT PIN 123456` (code affiché 60 s), `EVT APP 1|0` (téléphone connecté / déconnecté), `EVT ACTION TEXTE`, `EVT ACTION VOL n`.

**ESP32** (`main.py`, `ui.py` remplacés) :
- Les anneaux, le volume, les températures et les FPS **glissent en douceur** vers la nouvelle valeur.
- Bandeaux : « Code : 123456 » (60 s), « Téléphone connecté / déconnecté », « Texte envoyé », « Volume 40 % ».

## Contenu du zip (à extraire à la racine de Micro, en écrasant)

| Fichier | Rôle |
|---|---|
| `esp/main.py`, `esp/lib/ui.py` | **remplacés** (lissage, nouveaux bandeaux) |
| `tools/agent/agent_pc.py` | **remplacé** (serveur app, mesures rapides, SendInput, VOL n) |
| `tools/agent/serveur_app.py` | **nouveau** (WebSocket, appairage) |
| `tools/agent/autoriser_app.ps1` | **nouveau** (règle du pare-feu Windows, à lancer en administrateur par Mihaja) |
| `tools/assets/generer_assets.py` | **remplacé** (exporte aussi les images de l'app) |
| `app/pubspec.yaml`, `app/lib/main.dart`, `app/test/widget_test.dart` | **remplacés** |
| `app/lib/etat.dart`, `connexion.dart`, `theme.dart`, `ecrans/*.dart` (4), `widgets/*.dart` (2) | **nouveaux** |
| `app/assets/images/perso_*.png` (8) | **nouveaux** (mascotte en grand) |
| `app/assets/fonts/Inter-*.otf` (4) + `LICENCE_POLICES.txt` | **nouveaux** (polices, SIL OFL 1.1) |
| `app/assets/icone/icone.png`, `icone_avant.png`, `icone_fond.png` | **nouveaux** (icône 1024 px + couches de l'icône adaptative) |
| `tools/assets/generer_icone.py` | **nouveau** (programme qui a créé l'icône) |

Les fichiers de `esp/assets/` ne changent pas.

## Partie 3 — Modification « avant → après »

### Modification 1 — `app/android/app/src/main/AndroidManifest.xml` (accès réseau + nom de l'app « Dadou »)

Avant :

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application
        android:label="esp_micro"
```

Après :

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET"/>
    <application
        android:label="Dadou"
        android:usesCleartextTraffic="true"
```

## Test à blanc (avant d'extraire)

- `esp/main.py` contient `def reaction_action(` et `METEO_J` ; `esp/lib/ui.py` contient `def _scene_nuit` ; `tools/agent/agent_pc.py` contient `class Meteo:` (Phase 4).
- `app/lib/main.dart` est le modèle de `flutter create` (contient `MyHomePage`) ; `app/lib/connexion.dart` et `tools/agent/serveur_app.py` n'existent pas.
- Le bloc « avant » de la Modification 1 existe exactement une fois (ignorer CRLF/LF).
- Si un repère manque : s'arrêter et montrer le fichier.

## Liste de contrôle

| Contrôle | Attendu |
|---|---|
| SHA-256 du zip | identique au document |
| Test à blanc | repères trouvés |
| Extraction + Modification 1 | `git status` : seulement les fichiers listés |
| `.gitignore` | contient `tools/agent/appareils.json` |
| `py -m pip install --user -U websockets` | version notée (≥ 13) |
| `py -m py_compile` sur agent_pc.py, serveur_app.py, generer_assets.py, esp\main.py, esp\lib\ui.py | aucune erreur |
| Test du serveur sans Windows ni ESP32 : `py -X utf8 -c "import sys; sys.path.insert(0, r'tools\agent'); import serveur_app as s; print(s.PORT, s.ServeurApp)"` | `8765 <class ...>` |
| Copie sur la carte (avec PAUSE) : `esp\main.py` → `:main.py`, `esp\lib\ui.py` → `:lib/ui.py`, puis reset ; console 10 s | pas de trace d'erreur |
| `pc_test.py COM4 --cmd "EVT PIN 123456"` puis `--cmd "EVT APP 1"` | « OK » ×2 |
| Dans `app` : `flutter pub get` | réussi |
| `flutter analyze` | **aucune erreur** (les « info » de style sont acceptées : les lister sans les corriger) |
| `dart run flutter_launcher_icons` (dans app) | icônes Android générées (mipmap-*/ic_launcher.png, mipmap-anydpi-v26/ic_launcher.xml…) |
| `flutter test` | 2 tests réussis |
| `flutter build apk --release` | APK construit (noter le chemin et la taille) |

En cas d'**erreur** de compilation Dart : ne rien corriger, copier les messages complets dans `docs/etat_code.md`.

## Mise en route (par Mihaja)

1. **PowerShell administrateur**, dans le dossier Micro :
   - `powershell -ExecutionPolicy Bypass -File tools\agent\autoriser_app.ps1` (ouvre le port 8765 seulement pour le réseau local et Tailscale)
   - `Stop-ScheduledTask -TaskName 'ESP32 Telecommande Agent'` puis `Start-ScheduledTask -TaskName 'ESP32 Telecommande Agent'`
2. **Tailscale** (gratuit) : installe-le sur le PC (tailscale.com/download) et sur le téléphone (Play Store), connecte-toi **avec le même compte** sur les deux. Dans Tailscale sur le PC, note l'adresse du PC (commence par **100.**).
3. Installe l'APK sur le téléphone : `app\build\app\outputs\flutter-apk\app-release.apk` (copie-le sur le téléphone ou `flutter install` avec le téléphone branché en USB et le débogage USB activé).
4. Dans l'app → **Réglages** : mets l'adresse 100.x.y.z → « Se connecter » → « Afficher le code sur l'ESP32 » → tape le code qui s'affiche sur l'écran de l'ESP32 → « Valider ».

## Tests sur l'appareil (par Mihaja)

0. **Icône et nom** : sur le téléphone, l'app s'appelle « Dadou » avec le visage de la mascotte qui rit.
1. **Appairage** : le code s'affiche sur l'ESP32 (bandeau 60 s) ; après validation, l'ESP32 affiche « Téléphone connecté » et l'app passe sur « Connecté ».
2. **Accueil** : la mascotte bouge, les anneaux CPU / RAM / GPU suivent le PC ; l'écran de l'ESP32 est plus vif (valeurs qui glissent, 4 mises à jour par seconde).
3. **Souris** : le curseur suit ton doigt sans à-coups ; toucher = clic ; deux doigts = défilement dans une page web ; appui long = clic droit.
4. **Clavier** : ouvre le Bloc-notes, tape « Bonjour à tous, ça marche ! » dans l'app → le texte s'écrit avec les accents ; l'ESP32 affiche « Texte envoyé ».
5. **Contrôles** : curseur de volume, lecture / pause sur YouTube, luminosité, lance une app de la liste, verrouille le PC (l'app passe en mode nuit).
6. **Jeu** : lance God of War → l'app passe en néon avec les gros FPS.
7. **De partout** : coupe le Wi-Fi du téléphone (4G seulement, Tailscale actif) → l'app marche toujours.
8. Envoie-moi des captures d'écran de l'app et ce qui ne va pas.
