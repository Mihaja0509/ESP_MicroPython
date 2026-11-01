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
- Mascotte chibi qui lui ressemble, animée : c'est elle qui « fait » les actions à l'écran. Catalogue : mascotte_expressions.md.
- Écran vivant et joli (animations partout), rien ne doit dépasser de l'écran.
- **Mode gamer** : quand un jeu tourne, l'écran et la mascotte passent en thème gamer, avec FPS, température CPU et GPU bien visibles.
- Plus tard dans l'app : raccourcis pour la préparation de certains jeux (commandes en terminal admin, redémarrage de Steam, Ctrl+6 avant Play). À examiner quand on y arrivera (demander quelles commandes exactement).
- Pas besoin : diapos, Pomodoro.
- Le bouton BOOT n'est pas accessible quand la carte est branchée → tout se commande depuis l'app / le PC.

## PC de Mihaja
- Portable Windows, CPU Intel, GPU NVIDIA RTX 5070.
- Jeux lancés depuis Steam (bibliothèque de 18 jeux : God of War Ragnarök, Black Myth: Wukong, RDR2, Spider-Man 2, Ghost of Tsushima…).
- Casque : surtout par dongle USB 2,4 GHz, parfois Bluetooth. Manette par dongle (reconnue par XInput).
- D'accord pour installer LibreHardwareMonitor + PresentMon et lancer l'agent en administrateur.

## Mascotte et design de l'écran
- Source : illustration chibi de Mihaja. Tête détourée (contour blanc « sticker ») + buste redessiné : hoodie bleu nuit, casque cyan autour du cou (arceau derrière le cou), bas arrondi.
- Tenue A retenue, fond crépuscule (violet → rose/orange, halo, ville, particules).
- Sprite 95 × 150 px ; images faites : yeux ouverts, yeux fermés. Scripts mascotte.py / maquette.py dans la session Claude web (à reproduire dans tools/).
- Maquette animée validée dans l'esprit : carte « verre » (horloge, date, barre des secondes, jauges CPU/RAM, volume, pastilles), mascotte qui respire et cligne ; bandeau + bulle + saut à chaque commande ; assombri + z z z quand verrouillé.
- À concevoir : thème gamer (fond sombre néon, gros FPS, températures CPU/GPU, mascotte casque sur les oreilles + manette).

## Contraintes connues
- Pas d'allumage complet à distance (portable). Éteindre l'écran + verrouiller, veille, arrêt : OK.
- `TEXT` en QWERTY US, compatible avec le clavier de Mihaja.
- Le port série (COM4) ne peut être ouvert que par un seul programme à la fois (agent OU mpremote OU pc_test). L'agent se quitte avec `q`.
- Après chaque modification de esp/main.py, il faut le recopier sur la carte (sinon « ERR commande inconnue »).

## Environnement
- MicroPython v1.29.0, ESP32_GENERIC_S3-SPIRAM_OCT ; ~8,3 Mo de RAM libre.
- Port COM4 (303a:4001). esptool 5.6.0, mpremote 1.29.0 ; Flutter 3.47.2 / Dart 3.13.2.
- Sur la carte : boot.py, main.py, lib/lcd.py, lib/hid_pc.py, lib/usb/device/*.mpy (usb-device-hid 0.2.0).
- PC : psutil, pycaw, comtypes, screen-brightness-control, pyserial (+ nvidia-ml-py à la 2-bis).

## Choix techniques
- Écran : esp/lib/lcd.py (ST7789, SPI 40 MHz, framebuf RGB565, décalage 34, paysage).
- USB HID composite (clavier 1, souris 2, multimédia 3), port série conservé.
- Protocole série (une ligne, réponse OK / ERR / PONG) :
  - PC → ESP32 (HID) : PING, KEY, TEXT, VOL+/VOL-/MUTE/PLAY/NEXT/PREV/LUM+/LUM-, MOUSE, CLIC, CLICD, MOLETTE.
  - Agent → ESP32 (données) : `STAT cpu ram vol bat charge` (1/s), `GPU temp charge vram` (1/s, 2-bis), `EVT CASQUE nom|-`, `EVT MANETTE 0|1`, `EVT VERROU 0|1`, `EVT JEU nom|-` (2-bis).
  - Commandes exécutées par l'agent : APPS, APP nom, LUM n / LUM+ / LUM-, VERROU, ECRAN_OFF, VEILLE, ARRET (60 s), ANNULER, AUDIO (diagnostic).
- Casque (2-bis) : sortie audio par défaut branchée en USB/Bluetooth (d'après les propriétés Windows) = casque.
- Jeu en cours : registre HKCU\Software\Valve\Steam\RunningAppID (+ Apps\<id>\Name).
- GPU : NVML (nvidia-ml-py), sans admin. À venir : température CPU via LibreHardwareMonitor, FPS via PresentMon (admin).

## Feuille de route
1. ✅ Clavier / souris / multimédia USB.
2. ✅ (sauf casque) Programme PC : apps, luminosité, verrou, écran éteint, stats ; 2-bis : casque, jeu Steam, GPU.
3. Données gamer 2 : température CPU (LibreHardwareMonitor), FPS (PresentMon), démarrage auto de l'agent en admin.
4. Écran vivant : tableau de bord animé + mascotte + thème gamer automatique.
5. Wi-Fi + MQTT (accès de partout) + app Flutter : pavé tactile, clavier, volume, luminosité, apps, alimentation, écran ESP on/off.
6. Raccourcis par app et raccourcis de jeux.

## Phases
| Phase | Sujet | Commit | État |
|---|---|---|---|
| 0 | MicroPython + pilote écran + démo + squelette Flutter | poussé | terminée |
| 1 | Clavier / souris / multimédia USB | poussé | terminée (LUM+/-, CLIC, PLAY… non testés) |
| 2 | Programme PC (agent) | poussé | testée : apps, luminosité, manette, verrou, écran éteint, VOL+/KEY via agent OK ; casque KO (nom « Speakers… » probable) |
| 2-bis | Casque par type de branchement + jeu Steam + GPU NVIDIA (docs/micro_phase2_bis.md) | — | à appliquer |
