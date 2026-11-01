# Micro — Phase 4 (version 2) : l'écran vivant (mascotte, animations, thème gamer, météo)

- Date : 2026-11-01
- Statut : à appliquer (remplace la version 1 de la Phase 4, appliquée ou non)
- Étape : « Télécommande PC » — étape 4 (écran vivant)
- Basée sur : fin de Phase 3-ter (esp/main.py de la 3-bis, tools/agent/agent_pc.py de la 3-ter)
- Livraison : les fichiers sont dans **`docs/micro_phase4_fichiers.zip`** (images et polices = fichiers binaires, impossibles à mettre dans ce document). SHA-256 du zip : `a626986c07e80a4f56fdae72bdea3e0ce9a4a49bce3de933f0a8bea474093f64`

## Ce que contient la phase

L'écran de l'ESP32 change complètement, environ 12 images par seconde :

- **Mode normal** (fond crépuscule) : grande horloge, date, barre des secondes, anneaux CPU et RAM, barres de volume, batterie (éclair si en charge), nom du casque. À droite, ta mascotte respire, cligne des yeux, et met son casque sur les oreilles quand un casque est connecté.
- **Mode jeu** (dès qu'un jeu Steam tourne, fond néon synthwave) : nom du jeu, **FPS en très grand** (vert ≥ 60, orange ≥ 30, rouge en dessous), barres de température CPU et GPU, charge GPU et RAM. La mascotte a le casque sur les oreilles, et une bulle avec une manette quand une manette est connectée.
- **PC verrouillé** et **PC éteint / en veille / redémarrage** (fond de nuit, lune, étoiles) : horloge, **météo d'aujourd'hui et de demain** (icône, max / min, « Pluie 80 % vers 15 h » ou « Pas de pluie prévue »), la mascotte dort avec des « z z z ». Luminosité baissée (et très basse après 2 minutes sans PC).
- **Météo par le PC (plan B, choisi par Mihaja : sa box n'émet qu'en 5 GHz)** : le programme PC télécharge la météo d'aujourd'hui et de demain (Open-Meteo, gratuit, sans compte) toutes les 30 min, en arrière-plan, et l'envoie à l'ESP32 (lignes `METEO_J jour icone max min pluie heure`). L'ESP32 la garde et l'affiche quand le PC est verrouillé ou éteint. Position dans `tools\agent\reglages.json` (créé au premier lancement, à remplir par Mihaja, jamais commité).
- **Wi-Fi sur l'ESP32 (facultatif, pour plus tard)** : si un jour un Wi-Fi 2,4 GHz est disponible, `/secrets.py` sur la carte permet à l'ESP32 de récupérer la météo lui-même. Sans ce fichier, rien ne change.
- **Mascotte (version 2)** : quand elle rit, le sourire d'origine est effacé et remplacé par la bouche ouverte ; cou plus court ; casque qui suit la forme de la tête (arceau collé aux cheveux, attaches, écouteurs sur les oreilles).
- **Réactions** : à chaque commande, un bandeau glisse en haut avec une icône (« Volume + », « Win + D », « Spotify », « Luminosité 40 % »…), une bulle apparaît près de la tête, la mascotte saute et sourit. Transitions : « Bonjour Mihaja ! » quand le PC revient, « À bientôt ! » quand il s'éteint, « Mode jeu » au lancement d'un jeu, « Casque connecté », « Manette connectée »…
- Plus aucun « −1 » : une valeur inconnue n'est pas affichée (anneau vide, « -- » pour les FPS).
- Les caractères parasites au démarrage du PC (« Z//////TAT … ») sont ignorés.
- Nouvelles lignes : `TEMPS` (l'agent donne l'heure à l'ESP32 à la connexion puis chaque minute), `EVT ACTION …` (l'agent prévient l'ESP32 de chaque commande PC exécutée), `ECRAN_ESP 0|1` (éteindre / rallumer l'écran de l'ESP32, pour la future app).

## Contenu du zip (à extraire à la racine de Micro, en écrasant)

| Fichier | Rôle |
|---|---|
| `esp/main.py` | **remplacé** : boucle messages + dessin ~12 images/s |
| `esp/lib/ui.py` | **nouveau** : scènes, mascotte, bandeaux, particules |
| `esp/lib/polices.py` | **nouveau** : polices lissées (Inter) |
| `esp/lib/meteo.py` | **nouveau** : Wi-Fi + météo Open-Meteo + heure par Internet |
| `esp/secrets.example.py` | **nouveau** : modèle des réglages Wi-Fi + position |
| `esp/assets/*.bin`, `*.fnt` (38 fichiers, ~740 Ko) | **nouveaux** : 3 fonds, 8 images de mascotte, 14 icônes, 7 icônes météo, bulle manette, 5 polices |
| `tools/agent/agent_pc.py` | **remplacé** : + `TEMPS` + `EVT ACTION` |
| `tools/assets/generer_assets.py` | **nouveau** : programme qui a créé les images et polices (pour les refaire un jour) |
| `tools/assets/sources/tete.png` | **nouveau** : tête de la mascotte détourée |
| `tools/assets/apercus/*.png` | **nouveaux** : aperçus des fonds et de la mascotte |
| `tools/assets/LICENCE_POLICES.txt` | **nouveau** : licence des polices Inter (SIL OFL 1.1) |

Pour régénérer les images un jour : `py -m pip install --user pillow numpy scipy`, mettre les fichiers Inter-*.otf dans `tools/assets/sources/`, puis `py tools\assets\generer_assets.py`. **Pas nécessaire maintenant** : les fichiers générés sont déjà dans le zip.

## Test à blanc (avant d'extraire)

- `esp/main.py` doit contenir `def noter_erreur(e):` et `if cmd == "PERF":` (version 3-bis). Pour info, son SHA-256 en fins de ligne LF : `2d6efc69558b3994d549f29437d19d64e990150f0d2bbe88ef063108e32c40f0`.
- `tools/agent/agent_pc.py` doit contenir `def nom_court_audio(` (version 3-ter). SHA-256 en LF : `7c6518a333d1c8bbb7e8279d19447cf952968c0d2ad0035c1cbf563a2a1c9f11`.
- `esp/lib/ui.py` et `esp/lib/polices.py` peuvent déjà exister (version 1 de la Phase 4) : dans ce cas `esp/main.py` contient `from ui import Interface` au lieu des repères 3-bis, c'est normal.
- Si un repère manque : s'arrêter et montrer le fichier. Si seul le SHA-256 diffère (espaces, fin de fichier), le signaler mais continuer.

## Position pour la météo (par Mihaja, après l'installation)

Au premier lancement, l'agent crée `tools\agent\reglages.json` :

```json
{
  "ville": "",
  "latitude": null,
  "longitude": null
}
```

Remplis **soit** le nom de ta ville (ex. `"ville": "Kuala Lumpur"`), **soit** la position exacte de ta maison (Google Maps → clic droit sur ta maison → clique sur les deux nombres → `"latitude": 3.1390, "longitude": 101.6869`). Ce fichier n'est pas envoyé sur GitHub. Ensuite, relance l'agent (Stop / Start-ScheduledTask) : la météo arrive en moins d'une minute.

## Comprendre le code

- **Fond** : chaque image commence par la copie d'un fond déjà calculé (110 Ko copiés d'un coup, très rapide), puis on dessine par-dessus.
- **Mascotte et icônes** : images RGB565 où le magenta veut dire « transparent » ; `fb.blit(image, x, y, CLE)` les pose sans le magenta.
- **Polices** : chaque lettre est stockée avec 4 niveaux (vide, léger, moyen, plein). Au dessin, une petite « palette » transforme ces niveaux en couleurs mélangées avec le fond : les lettres sont lisses, dans n'importe quelle couleur.
- **Modes** : `ui.py` choisit la scène toute seule à partir des données (`connecte`, `verrou`, `jeu`). Sans données du PC depuis 8 s, on passe en « PC en veille ».
- **Réactions** : `ui.reagir(icône, texte)` lance le bandeau, la bulle et le saut ; `main.py` l'appelle pour chaque commande reçue.
- **Météo** : l'agent télécharge la prévision (JSON d'Open-Meteo) dans un fil à part, garde pour chaque jour : icône, max, min, et l'heure (à venir) où la probabilité de pluie est la plus forte, puis l'envoie à l'ESP32 (`METEO_J`) à chaque nouvelle prévision et à chaque reconnexion. L'ESP32 la garde en mémoire, même PC éteint.

## Liste de contrôle

| Contrôle | Attendu |
|---|---|
| Test à blanc | repères trouvés (version 3-bis ou Phase 4 v1) |
| SHA-256 du zip | identique à celui du document |
| Extraction | 55 fichiers, rien d'autre de modifié (`git status`) |
| `.gitignore` | contient `esp/secrets.py` et `tools/agent/reglages.json` |
| Module requests sur la carte | `py -m mpremote connect COM4 exec "import requests"` sans erreur ; sinon `py -m mpremote connect COM4 mip install requests` |
| Réglages Wi-Fi (facultatif) | si `esp/secrets.py` existe (NE PAS le lire), le copier en `:secrets.py` ; sinon le signaler, c'est normal |
| Météo envoyée par le PC (test sans l'agent) | `pc_test.py COM4 --cmd "METEO_J 0 orage 32 24 80 15"` puis `--cmd METEO` → « OK orage 32/24 pluie 80% vers 15h » |
| `py -m py_compile tools\agent\agent_pc.py tools\assets\generer_assets.py` | aucune erreur |
| Syntaxe : `py -m py_compile esp\main.py esp\lib\ui.py esp\lib\polices.py esp\lib\meteo.py` | aucune erreur |
| Copie sur la carte (avec PAUSE) | `:main.py`, `:lib/ui.py`, `:lib/polices.py`, `:lib/meteo.py`, dossier `:assets` avec 38 fichiers (`fs ls :assets`) |
| Espace libre sur la carte | `py -m mpremote connect COM4 exec "import os; s=os.statvfs('/'); print(s[0]*s[3]//1024, 'Ko libres')"` > 500 Ko |
| Démarrage | après reset, lire la console série 10 s : pas de trace d'erreur ; `fs cat :erreur.txt` (s'il existe) copié dans etat_code.md |
| `pc_test.py COM4 --cmd "STAT 23 61 48 76 1"`, `--cmd "EVT JEU Test"`, `--cmd "EVT JEU -"`, `--cmd "VOL+"` | « OK » à chaque fois |

## Tests sur l'appareil (par Mihaja)

D'abord : PowerShell administrateur → `Stop-ScheduledTask -TaskName 'ESP32 Telecommande Agent'` puis `Start-ScheduledTask -TaskName 'ESP32 Telecommande Agent'` (nouvel agent).

1. **Écran normal** : horloge à la bonne heure, date, anneaux CPU/RAM qui bougent, batterie, mascotte qui respire et cligne, petites lumières qui montent à droite. « Bonjour Mihaja ! » au moment où l'agent se connecte.
2. **Casque** : branche le dongle du HECATE → bandeau « Casque connecté », la mascotte a le casque sur les oreilles ; retire-le → « Casque retiré », casque au cou.
3. **Réactions** : crée `tools\agent\PAUSE`, lance l'agent console, tape `VOL+`, `KEY win+d`, `APP calculatrice`, `LUM 60` → bandeau + bulle + saut à chaque fois. Quitte (q), supprime PAUSE.
4. **Mode jeu** : lance God of War → fond néon, gros FPS, températures ; manette branchée → bulle manette. Quitte le jeu → retour au mode normal.
5. **Verrouillage** : (après avoir rempli reglages.json) Win + L → fond de nuit, la mascotte dort, avec la météo d'aujourd'hui et de demain. Déverrouille → « Re-bonjour ! ».
6. **Redémarrage / arrêt** : redémarre le PC → pendant le redémarrage « À bientôt ! » puis la mascotte dort (« PC en veille ») ; à l'ouverture de session « Bonjour Mihaja ! ». Si l'USB reste alimenté PC éteint, l'écran reste en mode nuit, très peu lumineux après 2 min.
7. **Fluidité** : l'animation doit être fluide (pas d'à-coups de plus d'une demi-seconde). Si ça rame, dis-le-moi.
8. Envoie-moi : photos ou vidéo courte de l'écran, et ce qui ne va pas.
