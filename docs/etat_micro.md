# État du projet Micro (MicroPython + écran)

Mis à jour : 2026-11-01

## Le projet
Projet à part (sans lien avec la clim ni le master) : la Waveshare ESP32-S3-LCD-1.47 seule, branchée sur le portable Windows de Mihaja, devient une « Télécommande PC » qu'il pilote depuis son téléphone (app Flutter), même loin de chez lui, avec une mascotte chibi animée sur l'écran. Objectif : effet « waouh ». MicroPython + Dart.

- Dossier : D:\FlutterProject\Esp32Maison\Micro (lancer `claude` depuis ce dossier)
- Dépôt : https://github.com/Mihaja0509/ESP_MicroPython.git (un seul dépôt : esp/ + app/ + tools/)
- Ne touche jamais ../firmware ni ../app (projet clim en pause ; le firmware C++ se remet avec `pio run -t upload`)

## Ce que veut Mihaja
- Raccourcis : clavier, souris (pavé tactile dans l'app), volume, luminosité, ouvrir une app, interagir dans les apps.
- Éteindre / allumer le PC, et éteindre / allumer l'écran de l'ESP32.
- Mascotte chibi qui lui ressemble (il enverra sa photo), animée : c'est elle qui « fait » les actions à l'écran.
- Pas besoin : diapos, Pomodoro (peu important).
- Le bouton BOOT n'est pas accessible quand la carte est branchée → tout se commande depuis l'app / le PC, aucune action ne dépend du bouton.

## Contraintes connues
- PC = portable Windows → pas d'allumage complet à distance (pas d'Ethernet / Wake-on-LAN fiable). On vise : éteindre l'écran + verrouiller (réveil instantané), veille, arrêt. Le réveil depuis la veille par l'ESP32 n'est pas garanti (réveil USB à distance probablement non géré par MicroPython ; à tester).
- `TEXT` en QWERTY US : disposition du clavier de Mihaja à confirmer.
- Le port série (COM4) ne peut être ouvert que par un seul programme à la fois (mpremote OU pc_test / futur programme PC).

## Environnement
- MicroPython v1.29.0 (2026-08-24), ESP32_GENERIC_S3-SPIRAM_OCT ; ~8,3 Mo de RAM libre (PSRAM utilisée).
- Port : COM4 sous MicroPython (USB 303a:4001) ; COM3 sous le bootloader / programme C++. `py -m mpremote devs` pour retrouver.
- esptool 5.6.0, mpremote 1.29.0 ; Flutter 3.47.2 / Dart 3.13.2 ; app package esp_micro (com.mmdigitek.esp_micro).

## Choix techniques
- Écran : pilote maison esp/lib/lcd.py (ST7789, SPI 40 MHz, framebuf RGB565 de 110 Ko, décalage 34, paysage MADCTL 0x60, inversion activée, BGR = False). Affichage validé par Mihaja (couleurs et cadrage bons).
- Brochage : SCLK 40, MOSI 45, CS 42, DC 41, RST 39, BL 48 (PWM), LED WS2812 38, BOOT 0.
- USB : HID composite (clavier rapport 1, souris rapport 2, multimédia rapport 3) via micropython-lib usb-device-hid, avec builtin_driver=True (le port série reste actif).
- Graphismes prévus : sprites dessinés à part, convertis sur le PC en RGB565 brut, stockés dans la flash et affichés avec framebuf.blit (rapide) ; polices bitmap plus belles converties depuis des TTF.

## Feuille de route
1. Test clavier / souris / multimédia USB (docs/micro_phase1_clavier.md) — décide si le mode clavier est fiable.
2. Programme PC (Python, démarre avec Windows) relié à l'ESP32 par le port série : ouvrir des apps, luminosité, veille / arrêt, éteindre l'écran, stats du PC renvoyées à l'écran de l'ESP32.
3. Wi-Fi + MQTT (accès depuis n'importe où) + app Flutter v1 : pavé tactile, clavier, volume, luminosité, lanceur d'apps, alimentation, écran ESP on/off.
4. Mascotte chibi animée (d'après la photo de Mihaja) qui joue les actions + tableau de bord (heure, stats PC).
5. Raccourcis par app (Spotify, YouTube, VS Code…), raccourcis personnalisables depuis l'app.

## Phases
| Phase | Sujet | Commit | État |
|---|---|---|---|
| 0 | MicroPython + pilote écran + démo + squelette Flutter (docs/micro_phase0.md) | poussé | terminée, écran validé |
| 1 | Clavier / souris / multimédia USB (docs/micro_phase1_clavier.md) | — | à appliquer |
