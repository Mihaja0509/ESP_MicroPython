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
- Écran vivant et joli, rien ne dépasse, pas de « -1 » visible.
- Mode gamer automatique (FPS, températures CPU et GPU bien visibles).
- Le design change quand le PC redémarre ou s'éteint (si l'USB reste alimenté).
- En veille : météo d'aujourd'hui et de demain + heure où la pluie est la plus probable.
- App Flutter au design assorti à l'écran de l'ESP32, avec souris (pavé tactile), clavier et tout le reste.
- Plus tard : raccourcis de préparation de certains jeux (commandes en terminal admin, redémarrage de Steam, Ctrl+6). À examiner à ce moment (demander les commandes exactes).
- Le bouton BOOT n'est pas accessible → tout se commande depuis l'app / le PC.

## PC et réseau de Mihaja
- Portable Windows, CPU Intel, GPU NVIDIA RTX 5070. Jeux via Steam (God of War Ragnarök = GoWR.exe, ~110 FPS ; Wukong, RDR2…).
- Audio : casque HECATE G30 par dongle USB ; enceinte Bluetooth « Headphones (Xiaomi蓝牙音箱Pro) » ; haut-parleurs internes. Manette par dongle (XInput).
- LibreHardwareMonitor 0.9.6 + PawnIO + PresentMon 2.6.0 console dans tools\agent\bin.
- **Wi-Fi « Cami-WiFi » en 5 GHz uniquement (canal 36, 802.11ax)** → l'ESP32 ne peut pas s'y connecter. Décision (plan B) : tout passe par le programme PC (météo maintenant, app Flutter ensuite), relié à l'ESP32 par USB. Le Wi-Fi de l'ESP32 (meteo.py + /secrets.py) reste en option si un 2,4 GHz devient disponible.

## Écran (Phase 4, version finale)
- Fichiers : esp/lib/ui.py (scènes), esp/lib/polices.py (polices lissées GS8 4 niveaux + palette 256 px, clé = couleur 0), esp/lib/meteo.py (Wi-Fi facultatif + Open-Meteo + NTP), esp/assets/ (38 fichiers : 3 fonds, 8 images de mascotte, 14 icônes, 7 icônes météo, bulle manette, 5 polices Inter), tools/assets/generer_assets.py (+ sources/tete.png, apercus/, LICENCE_POLICES.txt), esp/secrets.example.py.
- Modes : normal (fond jour : horloge, date, barre des secondes, anneaux CPU/RAM, volume, batterie, casque), jeu (fond néon synthwave : nom du jeu, gros FPS coloré, barres temp CPU/GPU, charge GPU/RAM, casque sur les oreilles + bulle manette ; la petite bulle de réaction n'est pas dessinée quand la bulle manette est là), verrou et absent (fond nuit : horloge, météo aujourd'hui / demain, mascotte qui dort + z z z ; sans météo : « Je t'attends… / Météo : en attente du PC… »). Absent = aucune donnée depuis 8 s. Luminosité : 85 / verrou 35 / absent 30 puis 6 après 2 min.
- Météo (plan B) : l'agent télécharge Open-Meteo toutes les 30 min (5 min tant qu'il n'a rien) dans un fil à part, position dans tools\agent\reglages.json ({"ville", "latitude", "longitude"}, gitignoré, rempli par Mihaja), envoie `METEO_J jour icone max min pluie heure(-1 = aucune)` à chaque nouvelle prévision et reconnexion ; l'ESP32 garde la dernière.
- Mascotte v2 : sourire d'origine effacé pour « rire » et « o » ; cou raccourci de 30 px ; casque sur la tête collé aux cheveux avec attaches. 2 casques × 4 visages.
- Réactions : bandeau (2,4 s) + bulle + saut. Transitions : « Bonjour ! », « Bonjour Mihaja ! », « À bientôt ! », « Mode jeu », « PC verrouillé », « Re-bonjour ! ».
- Claude web vérifie le rendu avec un émulateur framebuf (numpy) avant chaque livraison.
- Livraison des binaires : zip (docs/micro_phase4_fichiers.zip, 55 fichiers, SHA-256 a626986c…).

## Contraintes connues
- Pas d'allumage complet à distance (portable).
- Le port COM4 n'accepte qu'un programme à la fois. Agent en fond : créer tools\agent\PAUSE pour libérer le port, le supprimer ensuite.
- L'agent en fond tourne en administrateur : après tout changement de agent_pc.py ou de reglages.json, Mihaja fait Stop-ScheduledTask puis Start-ScheduledTask (PowerShell admin).
- La 1re commande mpremote après un autre programme sur COM4 échoue souvent (ClearCommError) : la relancer une fois (attendre ~3 s).
- Toute commande mpremote interrompt main.py : toujours finir par `reset`. L'agent relance main.py tout seul (Ctrl-C + Ctrl-D) s'il voit `>>>`, « Traceback » ou « Error: ».

## Protocole série (une ligne, réponse OK / ERR / PONG)
- HID : PING, KEY, TEXT, VOL+/VOL-/MUTE/PLAY/NEXT/PREV/LUM+/LUM-, MOUSE, CLIC, CLICD, MOLETTE.
- Données agent → ESP32 : `STAT cpu ram vol bat charge`, `GPU temp charge vram`, `PERF temp_cpu fps` (1/s) ; `TEMPS annee mois jour jour_semaine(0=lundi) h min s` (connexion + chaque minute) ; `METEO_J …` (nouvelle prévision / reconnexion).
- Événements : `EVT CASQUE nom|-`, `EVT MANETTE 0|1`, `EVT VERROU 0|1`, `EVT JEU nom|-`, `EVT ACTION <commande PC exécutée>`.
- Écran : `ECRAN_ESP 0|1`. Test : `METEO`.
- Commandes exécutées par l'agent : APPS, APP nom, LUM n / LUM+ / LUM-, VERROU, ECRAN_OFF, VEILLE, ARRET (60 s), ANNULER, AUDIO, ETAT (montre aussi la météo).

## Feuille de route
1-3. ✅ Clavier/souris USB, programme PC, données gamer.
4. Écran vivant + météo par le PC (docs/micro_phase4_ecran.md + zip) — à appliquer.
5. App Flutter assortie, connectée au **programme PC** (et non à l'ESP32, sans Wi-Fi 2,4 GHz) : pavé tactile, clavier, volume, luminosité, apps, alimentation, écran ESP on/off ; accès de partout (relais MQTT ou équivalent, à choisir).
6. Raccourcis par app et de jeux ; plus d'expressions (bâillement, sueur CPU chaud, batterie faible…).

## Phases
| Phase | Sujet | Commit | État |
|---|---|---|---|
| 0 | MicroPython + écran + squelette Flutter | poussé | terminée |
| 1 | Clavier / souris / multimédia USB | poussé | terminée |
| 2 / 2-bis | Programme PC, casque, jeu Steam, GPU | poussé | terminées |
| 3 / 3-bis / 3-ter | CPU, FPS, démarrage auto, relance auto, noms ASCII | poussé | terminées et validées |
| 4 (finale) | Écran vivant, mascotte v2, météo par le PC (55 fichiers) | — | à appliquer |
