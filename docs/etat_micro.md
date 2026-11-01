# État du projet Micro (MicroPython + écran)

Mis à jour : 2026-11-01

## Le projet
Projet à part (sans lien avec la clim ni le master) : la Waveshare ESP32-S3-LCD-1.47 seule, branchée sur le portable Windows de Mihaja, devient une « Télécommande PC » qu'il pilote depuis son téléphone (app Flutter), même loin de chez lui, avec une mascotte chibi animée sur l'écran. Objectif : effet « waouh ». MicroPython + Dart. Mihaja fait confiance aux choix de Claude web.

- Dossier : D:\FlutterProject\Esp32Maison\Micro (lancer `claude` depuis ce dossier)
- Dépôt : https://github.com/Mihaja0509/ESP_MicroPython.git (un seul dépôt : esp/ + app/ + tools/)
- Ne touche jamais ../firmware ni ../app (projet clim en pause)

## Ce que veut Mihaja
- Raccourcis : clavier, souris, volume, luminosité, ouvrir une app, interagir dans les apps.
- Éteindre / allumer le PC, éteindre / allumer l'écran de l'ESP32.
- Mascotte chibi animée qui « fait » les actions (catalogue : mascotte_expressions.md).
- Écran vivant et joli, rien ne dépasse. Texte actuel (police 8×8) trop petit → à régler à la phase écran.
- Pas de « -1 » visible : une valeur indisponible est masquée ou remplacée par quelque chose de discret (phase écran).
- Mode gamer : quand un jeu tourne, écran + mascotte en thème gamer, FPS, températures CPU et GPU bien visibles.
- App Flutter au design assorti à l'écran de l'ESP32, avec souris (pavé tactile), clavier et tout le reste.
- Plus tard : raccourcis de préparation de certains jeux (commandes en terminal admin, redémarrage de Steam, Ctrl+6). À examiner à ce moment (demander les commandes exactes).
- Le bouton BOOT n'est pas accessible → tout se commande depuis l'app / le PC.

## PC de Mihaja
- Portable Windows, CPU Intel, GPU NVIDIA RTX 5070. Jeux via Steam (God of War Ragnarök, Wukong, RDR2…).
- Casque : HECATE G30 par dongle USB, parfois Bluetooth. Haut-parleurs internes : « Speakers (High Definition Audio Device) ». Manette par dongle (XInput).
- LibreHardwareMonitor 0.9.6 + PresentMon 2.6.0 console dans tools\agent\bin (ignorés par Git). LHM 0.9.6 exige le pilote PawnIO (winget install PawnIO) + admin pour les capteurs CPU.

## Mascotte et design de l'écran
- Tête de l'illustration chibi de Mihaja (détourée, contour blanc) + buste redessiné : hoodie bleu nuit, casque cyan autour du cou. Tenue A retenue, fond crépuscule (violet → rose/orange, halo, ville, particules).
- Sprite 95 × 150 px ; images faites : yeux ouverts, yeux fermés. Scripts mascotte.py / maquette.py dans la session Claude web (à reproduire dans tools/).
- Maquette animée : carte « verre » (horloge, date, barre des secondes, jauges CPU/RAM, volume, pastilles), mascotte qui respire et cligne ; bandeau + bulle + saut à chaque commande ; assombri + z z z quand verrouillé.
- À concevoir : thème gamer (fond sombre néon, gros FPS, températures CPU/GPU, mascotte casque sur les oreilles + manette).

## Contraintes connues
- Pas d'allumage complet à distance (portable).
- Le port COM4 n'accepte qu'un programme à la fois. Agent console : quitter avec `q`. Agent en fond : créer tools\agent\PAUSE pour libérer le port, le supprimer ensuite.
- La 1re commande mpremote après un autre programme sur COM4 échoue souvent (ClearCommError) : la relancer une fois (attendre ~3 s).
- Toute commande mpremote interrompt main.py et laisse la carte dans l'invite `>>>` : toujours finir par `reset`. Depuis la 3-bis, l'agent relance main.py tout seul (Ctrl-C + Ctrl-D) s'il voit `>>>`, « Traceback » ou « Error: ».
- Après chaque modification de esp/main.py, la recopier sur la carte.

## Environnement
- MicroPython v1.29.0, ESP32_GENERIC_S3-SPIRAM_OCT. Port COM4 (303a:4001). esptool 5.6.0, mpremote 1.29.0 ; Flutter 3.47.2 / Dart 3.13.2.
- Sur la carte : boot.py, main.py, lib/lcd.py, lib/hid_pc.py, lib/usb/device/*.mpy (usb-device-hid 0.2.0). Erreurs notées dans erreur.txt (3-bis).
- PC : pyserial 3.5, psutil 7.2.2, pycaw 20260927, comtypes 1.4.17, screen-brightness-control 0.27.2, nvidia-ml-py 13.615.71.

## Protocole série (une ligne, réponse OK / ERR / PONG)
- HID : PING, KEY, TEXT, VOL+/VOL-/MUTE/PLAY/NEXT/PREV/LUM+/LUM-, MOUSE, CLIC, CLICD, MOLETTE.
- Données agent → ESP32 (1/s) : `STAT cpu ram vol bat charge`, `GPU temp charge vram`, `PERF temp_cpu fps`.
- Événements : `EVT CASQUE nom|-`, `EVT MANETTE 0|1`, `EVT VERROU 0|1`, `EVT JEU nom|-`.
- Commandes exécutées par l'agent : APPS, APP nom, LUM n / LUM+ / LUM-, VERROU, ECRAN_OFF, VEILLE, ARRET (60 s), ANNULER, AUDIO, ETAT.

## Choix techniques
- Casque : sortie par défaut en USB/Bluetooth d'après les propriétés Windows (validé).
- Jeu : registre Steam RunningAppID (validé).
- GPU : NVML. CPU : serveur web LHM (localhost:8085/data.json, « CPU Package »). FPS : PresentMon console (--output_stdout --v1_metrics) ; depuis la 3-bis calcul à partir de MsBetweenPresents (le comptage des lignes donnait 228/322 FPS faux, lignes livrées par paquets).
- Agent au démarrage : tâche planifiée « ESP32 Telecommande Agent » (pythonw, --service, droits les plus élevés), journal tools\agent\agent.log (UTF-8 : lire avec -Encoding utf8).

## Feuille de route
1. ✅ Clavier / souris / multimédia USB.
2. ✅ Programme PC + 2-bis (casque, jeu Steam, GPU).
3. Données gamer 2 : température CPU, FPS, démarrage auto — 3-bis en cours.
4. Écran vivant : tableau de bord animé + mascotte + thème gamer automatique (grosses polices, pas de -1).
5. Wi-Fi + MQTT (accès de partout) + app Flutter assortie : pavé tactile, clavier, volume, luminosité, apps, alimentation, écran ESP on/off.
6. Raccourcis par app et raccourcis de jeux.

## Phases
| Phase | Sujet | Commit | État |
|---|---|---|---|
| 0 | MicroPython + écran + squelette Flutter | poussé | terminée |
| 1 | Clavier / souris / multimédia USB | poussé | terminée |
| 2 | Programme PC (agent) | poussé | terminée |
| 2-bis | Casque (USB/BT), jeu Steam, GPU NVIDIA | poussé | terminée |
| 3 | Température CPU, FPS, démarrage auto | poussé | appliquée ; problèmes : carte retombée en `>>>` après redémarrage du PC (données figées), FPS faux, CPU à -1 (PawnIO manquant) |
| 3-bis | ESP32 protégée + relance auto, FPS par MsBetweenPresents, PawnIO (docs/micro_phase3_bis.md) | — | à appliquer |
