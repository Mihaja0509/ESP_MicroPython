# Micro — MicroPython + écran

Projet séparé de `..\firmware` et `..\app` (projet clim, en pause).

- Carte : Waveshare **ESP32-S3-LCD-1.47** seule (ESP32-S3R8, 8 Mo PSRAM octal, 16 Mo flash, USB natif, écran ST7789 172×320), **sans module externe**.
- `esp/` : code MicroPython copié sur la carte (`main.py` à la racine, `lib/` dans le dossier `lib` de la carte).
- `app/` : app Dart/Flutter Android (`com.mmdigitek.esp_micro`, nom affiché « Télécommande PC »).
- `docs/` : documents de phase et état du code (à appliquer exactement).
- `bin/` : firmware MicroPython téléchargé (ignoré par Git).
- Dépôt : https://github.com/Mihaja0509/ESP_MicroPython.git

## Architecture (Phase 5)

```
App Android ⇄ WebSocket (port 8765) ⇄ agent PC (agent_pc.py + serveur_app.py) ⇄ USB série (COM4) ⇄ ESP32
```

- L'ESP32 n'a pas de Wi-Fi utilisable (box en 5 GHz) : tout passe par l'agent PC.
- Accès de partout : **Tailscale** sur le PC et le téléphone (même compte) ; dans l'app, adresse du PC en `100.x.y.z`. Pare-feu : `tools\agent\autoriser_app.ps1` (administrateur, lancé par Mihaja) ouvre 8765 au réseau local et à Tailscale seulement.
- **Appairage** : l'app demande un code → l'agent envoie `EVT PIN 123456` (bandeau 60 s sur l'ESP32) ; code valable 2 min, 5 essais. Téléphones appairés dans `tools\agent\appareils.json` (jamais lu, jamais commité). `EVT APP 1|0` = téléphone connecté / déconnecté.
- Souris, clics, défilement et texte de l'app : exécutés directement sur le PC (SendInput). Raccourcis (`KEY`) et touches multimédia : via l'ESP32. `VOL n` = volume exact. État envoyé à l'app 4 fois par seconde.
- Dépendance PC en plus : `websockets` (`py -m pip install --user -U websockets`).

## Fichiers de l'app (`app/`)

- `lib/main.dart` (navigation), `lib/etat.dart` (état reçu du PC), `lib/connexion.dart` (WebSocket + appairage), `lib/theme.dart` (couleurs, fonds crépuscule / néon / nuit).
- `lib/ecrans/` : `accueil.dart`, `souris.dart` (pavé tactile + clavier), `controles.dart` (volume, luminosité, apps, alimentation), `reglages.dart` (adresse, appairage, aide Tailscale).
- `lib/widgets/` : `mascotte.dart`, `anneau.dart`.
- `assets/images/perso_*.png` (8, exportées par `tools\assets\generer_assets.py`), `assets/fonts/Inter-*.otf` (4) + licence.
- `test/widget_test.dart` (2 tests). Dépendances : `web_socket_channel`, `shared_preferences`.
- Manifeste : permission `INTERNET`, `usesCleartextTraffic="true"` (WebSocket `ws://` en clair, protégé par Tailscale + appairage).
- APK release (signée avec la clé debug) : `app\build\app\outputs\flutter-apk\app-release.apk`.

## Brochage de la carte (Waveshare)

| Fonction | GPIO |
|---|---|
| Écran ST7789 172×320 : SCLK / MOSI / CS / DC / RST / rétroéclairage | 40 / 45 / 42 / 41 / 39 / 48 |
| LED RGB (WS2812) | 38 |
| Bouton BOOT | 0 |

## Commandes

Python : utiliser `py` (le `python` du PATH est l'alias Microsoft Store).

Carte (le port change après un flash ou un reset USB : le retrouver avec `devs`) :
- `py -m mpremote devs` : lister les ports
- `py -m mpremote connect <port> fs cp esp/main.py :main.py` : copier un fichier (`fs cp esp/lib/lcd.py :lib/lcd.py` pour la lib)
- `py -m mpremote connect <port> fs ls` : lister les fichiers de la carte
- `py -m mpremote connect <port> reset` : redémarrer
- `py -m mpremote connect <port> repl` : console interactive (Ctrl-] pour quitter)

Agent PC (`tools\agent\agent_pc.py`) : il occupe le port COM4 tant qu'il tourne.
- En fond : tâche planifiée « ESP32 Telecommande Agent » (pythonw, `--service`, administrateur, journal `tools\agent\agent.log`).
- Pour libérer COM4 avant mpremote ou `tools\pc_test.py` : créer le fichier `tools\agent\PAUSE` (l'agent ferme le port en ~1 s), puis le **supprimer** à la fin pour que l'agent se reconnecte.
- Version console (`py -X utf8 tools\agent\agent_pc.py`) : la quitter avec `q`.
- La 1re commande mpremote après un autre programme sur COM4 échoue souvent avec `ClearCommError` : la relancer une fois.
- Météo : l'agent la télécharge (Open-Meteo, toutes les 30 min, fil à part) et l'envoie à l'ESP32 (`METEO_J`). Position dans `tools\agent\reglages.json` (créé au 1er lancement, rempli par Mihaja : `ville` ou `latitude`/`longitude`) : jamais lu, jamais commité.

## Fichiers de la carte (Phase 4)

- `esp/main.py` → `:main.py` : boucle messages + dessin ~12 images/s ; erreurs ajoutées dans `:erreur.txt`.
- `esp/lib/` → `:lib/` : `lcd.py`, `hid_pc.py`, `ui.py` (scènes, mascotte, bandeaux, particules), `polices.py` (polices lissées Inter), `meteo.py` (Wi-Fi + Open-Meteo + heure, facultatif).
- `esp/assets/` → `:assets` (38 fichiers `.bin` / `.fnt` : fonds, mascotte, icônes, météo, polices) : `fs cp -r esp/assets :`.
- `esp/secrets.py` → `:secrets.py` (facultatif, Wi-Fi 2,4 GHz + position, modèle `esp/secrets.example.py`).
- Régénérer les images et polices : `py -m pip install --user pillow numpy scipy`, mettre les `Inter-*.otf` dans `tools/assets/sources/`, puis `py tools\assets\generer_assets.py` (aperçus dans `tools/assets/apercus/`).

## Lignes série PC → ESP32 (ajouts Phase 4)

- `TEMPS annee mois jour jour_semaine h min s` : l'agent donne l'heure (à la connexion puis chaque minute).
- `EVT ACTION <commande> [arg]` : l'agent signale une commande PC exécutée (APP, LUM, VERROU, ECRAN_OFF, VEILLE, ARRET, ANNULER…) → réaction de la mascotte.
- `METEO_J jour icone max min pluie heure` : météo du jour `0` (aujourd'hui) ou `1` (demain) ; `heure` = -1 si pas de pluie.
- `ECRAN_ESP 0|1` : éteindre / rallumer l'écran de l'ESP32.
- `METEO` : relire la météo gardée (`OK orage 32/24 pluie 80% vers 15h | …`).

Dans `app/` :
- `flutter pub get`
- `flutter analyze`
- `flutter test`
- `flutter build apk --release` (ou `--debug`) ; `flutter install` avec le téléphone branché (débogage USB)

## Règles

1. Appliquer **exactement** les documents de `docs\`.
2. Toujours faire le test à blanc des blocs « avant » (vérifier que le code actuel correspond au bloc « avant » avant de le remplacer).
3. Ne jamais lire, modifier ni commiter `..\firmware`, `..\app` ni `..\docs` (autre projet).
4. Les secrets vont dans `esp/secrets.py` : jamais lu, jamais commité.
5. En fin de phase : commit + push.
6. Demander avant toute commande destructive (suppression, reset Git, force push, effacement de la flash).
