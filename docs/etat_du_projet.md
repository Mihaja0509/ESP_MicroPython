# État du projet — ESP32 Maison

Mis à jour : 2026-11-01

## ⏸ En pause
Projet clim mis en pause par Mihaja en attendant un breadboard. La carte passe sous MicroPython pour le projet séparé « Micro » (voir etat_micro.md). Pour reprendre : `pio run -t upload` dans firmware/ remet le programme C++. La Phase 1-bis reste à appliquer et à tester.

## Dépôts
- firmware : https://github.com/Mihaja0509/ESP32_Dash.git (PlatformIO, Arduino-ESP32 3.3.12, espressif32 8.0.0)
- app : https://github.com/Mihaja0509/app_ESP32.git (Flutter 3.47.2, package esp32_maison, com.mmdigitek.esp32_maison)
- Dossier : D:\FlutterProject\Esp32Maison (CLAUDE.md, docs/, .claude/ à la racine, hors dépôts)

## Environnement
- Windows ; Python via `py` (pas `python`, alias Store) ; pyserial 3.5 installé. Console Windows : accents mal affichés → `py -X utf8 ...`.
- pio : C:\Users\xisda\AppData\Roaming\Python\Python313\Scripts\pio.exe (pas dans le PATH).
- Carte sur COM3 ; upload sans bouton BOOT. 8 Mo PSRAM / 16 Mo flash confirmés.
- Licences Android pas acceptées (flutter doctor --android-licenses), sans effet sur le build.
- Git convertit LF → CRLF dans le dossier local (normal sous Windows).

## Décisions
- Langage firmware : C++ (Arduino) et pas MicroPython (timings IR, LVGL, mesures de latence du master). Mihaja débute en C++ : chaque phase contient une partie « Comprendre le code ».
- IRremoteESP8266 ne compile pas avec le core 3.x → capture/émission IR maison (interruption GPIO + LEDC 38 kHz).
- Broches : IR RX = GPIO 4 (module en 3V3), IR TX = GPIO 5 (module en 5V), BOOT = GPIO 0. Occupées par la carte : LCD 39-42, 45, 48 ; SD 14-18, 21 ; LED RGB 38.
- ac_remote (ancien projet) : protocoles Coolix, York GRYLH2A, Gree, Midea générés par calcul, aucun n'a marché sur la clim.
- Télécommande York = multi-marques : 4 protocoles par appui (Daikin160, inconnu 64 bits, LG 28 bits, inconnu 56 bits). Détails dans analyse_ir_york.md.

## Fichiers firmware actuels (après Phase 1)
- include/pins.h, include/secrets.example.h
- src/main.cpp (capture IR : lignes « IR_FRAME n d1,d2,… », commandes PING / SEND, bouton BOOT = renvoi)
- src/ir_raw.h, src/ir_raw.cpp (namespace ir : beginReceiver, readFrame, beginSender, send)
- tools/capture_ir.py (capture guidée → captures/york_ir.json, --list, --send NOM)
- captures/york_ir.json : 18 captures + 12 trames de test (test_off/on/t26 × 4 protocoles), fourni par Claude web

## Phases
| Phase | Sujet | Commit | État |
|---|---|---|---|
| 0 | Mise en place (outils, squelettes, Git) | firmware d62ee93 / app 6438d74 | terminée |
| 1 | Capture IR York (docs/phase1_capture_ir.md) | firmware 5453992 | capture OK (18 trames) ; émission KO |
| 1-bis | Diagnostic émetteur (docs/phase1_bis.md : INFO, TXDC, TXPWM, --cmd) | — | écrite, pas appliquée (pause) |

## Diagnostic émetteur (en cours)
- `--send off` (trame complète) : la clim ne réagit pas ; aucun flash de la LED à la caméra.
- La caméra voit bien l'IR de la vraie télécommande. Le module s'allume quand DAT est mis sur 3V3. Broches soudées.
- → suspect : GPIO 5 (soudure/broche) ou porteuse LEDC. La Phase 1-bis tranche.

## Prochaine étape (à la reprise)
Remettre le firmware C++ → appliquer la 1-bis → résultats (INFO, TXDC, TXPWM, --send off) → correctif → tester les 12 trames de test pour trouver le protocole compris par la clim → Phase 2.
