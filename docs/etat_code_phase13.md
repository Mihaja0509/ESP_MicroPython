# État du code — Phase 13 (clim complète, capteur, écran, souris)

Mis à jour : 2026-11-06 · dernier commit de code : `8ac3a02` (13G) · dépôt public : https://github.com/Mihaja0509/ESP_MicroPython.git

## Commits

| Étape | Commit | Contenu |
|---|---|---|
| 11-ter | `0a2a148` | son lu à part, filet de sécurité, journal des scènes, vraie pluie, sortie du cinéma (appliquée le 04/11, commitée le 06/11) |
| 12 | `f6422e5` | clim York depuis le téléphone (IR) |
| 13A | `93f669c` | swing inversé : bit 0 de l'octet 7 = swing actif |
| 13B | `c4ab4c5` | souris : tolérance de tap, curseur hors zone, boucle réseau libre, mesures |
| 13C | (aucun) | carte reflashée en MicroPython v1.29.0 le 2026-11-06 |
| 13D | `0224e43` | écran ESP32 retournable (`ROT_ESP`), heure en mode jeu |
| 13E | `3f769a4` | minuteur, plage horaire, liaison clim → PC → ESP32 |
| 13F | `5ce44a7` | capteur AHT20/BMP280, mesure vers le PC, automatisme |
| 13G | `8ac3a02` | écran, mascotte et animations clim / pièce |

## Versions et matériel

- MicroPython **v1.29.0** (2026-08-24), variante `ESP32_GENERIC_S3-SPIRAM_OCT`, flashée après `erase-flash`. Le firmware C++ des tests IR n'est plus sur la carte.
- Port MicroPython : **COM4** (`303a:4001`). COM3 (`303a:1001`) = mode BOOT / firmware C++.
- Carte : `usb-device-hid` (mip), `main.py`, `lib/` (lcd, ui, meteo, hid_pc, polices, capteur), `assets/` (59 fichiers), `briefing.txt` (copié depuis la sauvegarde). Pas de `secrets.py` (absent de la sauvegarde ; Wi-Fi et position facultatifs).
- Agent PC : Python 3.13 (`D:\Dadou\Dev\Python\Python313`), tâche planifiée « ESP32 Telecommande Agent ».
- Pins du capteur : **SDA = None, SCL = None** (capteur pas câblé, `tools/i2c_scan.py` pas lancé). `DECALAGE_T = 0.0`.

## Seuils et réglages (valeurs par défaut)

- Automatisme (réglable dans l'app) : allumer à ≥ 28 °C, éteindre à ≤ 25 °C, durée de base 30 min + 3 min par °C au-dessus du seuil (10 à 180 min), mode Dry à partir de 70 % d'humidité pendant 45 min (arrêt à seuil − 8 %), pause compresseur 3 min, silence de l'automatisme 30 min après une action à la main.
- Écran (`ui.py`) : `PIECE_CHAUDE = 29` °C (mascotte transpire), `PIECE_SUGGERE = 28` °C, `PIECE_HUMIDE = 75` %.

## Architecture

```
Dadou (Dart) ── canal dadou/ir ──> ConsumerIrManager (trame de la clim)
Dadou (Dart) ── canal dadou/clim ──> ClimPlan.kt (alarmes exactes, ClimReceiver)
ClimPlan.kt ── GET /clim_maj ──> agent PC ── CLIM … ──> ESP32 (écran)
ClimPlan.kt ── GET /clim_mesure <── agent PC <── CLIMAT t10 h p <── ESP32 (capteur)
```

Lignes série : PC → ESP32 `ROT_ESP 0|180`, `CLIM on mode temp reste auto` ; ESP32 → PC `CLIMAT t10 humidité pression`, `MODE nouvelle <- ancienne (s)`.

## Tests

Faits par Claude Code (compilation, simulation) :
- **A** : `clim_ir_test` 3/3, `flutter analyze` propre. Reste : swing ON balance bien la clim (test à la main).
- **B** : `py_compile`, analyze, 9 tests verts. Reste : 3 min de souris puis lecture des lignes `[agent] souris :` de agent.log.
- **C** : MicroPython répond (`sys.implementation`), 59 assets, agent reconnecté, 0 Traceback, `/widget` → 401.
- **D** : empreintes de `main.py`, `lcd.py`, `ui.py` identiques sur la carte, `erreur.txt` absent. Reste : « Flipped » dans l'app retourne l'écran (et il reste retourné après rebranchement), l'heure du mode jeu.
- **E** : `flutter build apk` (Kotlin compilé), analyze, tests, `main.py` copié, `erreur.txt` absent. Reste : minuteur 15 min app fermée, plage horaire, redémarrage du téléphone avec minuteur en cours (voir `micro_phase13.md`, Test E).
- **F** : `capteur.py` et `main.py` copiés, `erreur.txt` absent, aucun message `CAPTEUR`. Reste : câbler, `i2c_scan.py`, remplir SDA/SCL, comparer avec un thermomètre.
- **G** : lignes `CLIM` simulées par le port série (Cool, Dry, Fan, Auto, éteinte) pendant les scènes normale, calme, jeu et nuit : `erreur.txt` absent. Non testés : tout ce qui dépend du capteur (coin « 24.1° 58 % », « Room … », sueur, idées pièce).

## Écarts avec le document `micro_phase13.md`

- Le document a été écrit avant la 11-ter. Deux « Avant » avaient changé et ont été rattachés aux lignes réelles, même changement : **E10.1** (`esp/main.py`, ajout de `clim` et `piece` après `meteo_now`) et **G6.2** (`esp/lib/ui.py`, bloc « pièce » inséré avant `jours`).
- `dart format` coupe certains `if` sur 2 lignes : accolades ajoutées dans `souris.dart` (B) et `clim.dart` (E).
- `dart format` a reformaté tout `controles.dart` et `etat.dart` (gros diff de mise en forme en 13D).

## Ce qui reste

- Installer l'APK, régler les droits Android de Dadou (batterie « Aucune restriction », démarrage automatique, « Alarmes et rappels », notifications).
- Câbler le capteur, lancer `tools/i2c_scan.py` (agent en PAUSE), remplir SDA et SCL dans `esp/lib/capteur.py`, recopier le fichier sur la carte.
- Tester A, B, D, E, F, G sur l'appareil (voir les sections « Test » de `micro_phase13.md`).
- La touche power de la clim est une bascule : si l'état supposé se désynchronise, utiliser l'interrupteur « AC is ON/OFF (assumed) » dans l'app.
