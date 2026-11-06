# État du code — Phase 14 (orientation, minuteur h/min/s, écran, historique de jeu)

Mis à jour : 2026-11-06 · dépôt public : https://github.com/Mihaja0509/ESP_MicroPython.git · base : `995da6a` (13H) puis `a632525` (capteur)

## Commits

| Étape | Commit | Contenu |
|---|---|---|
| 14.1 | `5eb699f` | orientation de l'écran ESP32 : retournement logiciel du tampon (+ 2 correctifs d'app : `Material` transparent dans `Carte`, ligne d'orientation sans débordement) |
| 14.2 | `2e2624c` | minuteur en heures / minutes / secondes (Dart, Kotlin, `/clim_maj`, ligne `CLIM`, ESP32) |
| 14.3 | `2577065` | scène normale : pièce en permanence, bandeau clim discret ; banc de rendu `tools/render_scenes.py` |
| 14.4 | `5513cde` | historique de jeu : agent, app, ESP32 |
| 14.5 | (aucun) | vérifications, copie sur la carte, agent redémarré, APK release |
| 14.6 | voir `git log` | documentation |

## Orientation de l'écran : cause

La chaîne bouton → agent → ESP32 fonctionnait : `ROT_ESP 180` répond `OK` sur la carte, et `executer` de l'agent renvoie la ligne et `rot_esp` (testé avec un faux lien série). Le seul maillon impossible à vérifier sans voir l'écran était le MADCTL `0xA0` du panneau. L'orientation ne dépend plus du contrôleur : `Ecran.afficher()` envoie les pixels dans l'ordre inverse (`_retourner`, viper). Coût mesuré sur la carte : `afficher()` passe de 23,4 ms à 35 ms (image toutes les 83 ms). L'exactitude du retournement est vérifiée (premier pixel retourné = dernier pixel). L'effet visuel reste à confirmer sur l'appareil.

## Minuteur

- Dart : `lib/clim_plan.dart` (`dureeEnSecondes`, `secondesEnHms`, `formaterReste`, `limiterHms`, `verifierDuree`, max `24:00:00`, min 1 s).
- Kotlin : `ClimPlan.minuteur(duree, delai)` en secondes ; `publier()` envoie `reste` en secondes (arrondi au-dessus) et `plage`. Les alarmes sont inchangées (heure de fin en millisecondes), donc un minuteur déjà armé avant la mise à jour reste valable.
- Agent : `clim_maj` accepte jusqu'à 90 000 s ; la ligne `CLIM on mode temp reste auto plage` part au changement d'état et toutes les 20 s.
- ESP32 : `reste_court()` (« 1h 05 », « 23 min », « 6:40 », « 45 s »).

## Écran (banc de rendu)

`py -X utf8 tools\render_scenes.py` : 37 aperçus dans `tools/assets/apercus/scene_*.png` (normal, calme, nuit, jeu ; avec et sans clim, plusieurs instants), 0 chevauchement de texte détecté. Largeurs réelles : `f_heure` « 88:88 » = 117 px (de x=16 à 133), `f_m` « 24.1° » = 37 px, bord droit de la carte x=190.

## Historique de jeu

- `tools/agent/historique.py` ; fichier `stats_jeux.json` : clés `jeux` et `jours` (Phase 10, conservées), `historique` et `totaux` (nouveau). Migration vérifiée sur un faux fichier : aucun jour perdu (sessions et FPS inconnus pour les anciens jours).
- Le total du jour est lu par date locale : il repart de zéro à minuit, l'ancien jour reste archivé. 365 jours gardés.
- Test sur la carte : `JEU_JOUR 192 100` accepté, ligne « Today: 3h 12 • this game 1h 40 ».

## Tests

- Python : `cd tools\agent` puis `py -X utf8 -m unittest test_historique` : 7 tests.
- Dart : `flutter test` : `clim_plan_test.dart` (5), `historique_test.dart` (6), tests existants.
- `flutter analyze` : aucune erreur. `py -m py_compile` sur tous les `.py` modifiés : OK.
- Carte : empreintes SHA-256 de `main.py`, `lib/lcd.py`, `lib/ui.py` identiques aux fichiers locaux, `erreur.txt` absent, lignes `CLIM` (secondes, plage), `JEU_JOUR`, `ROT_ESP` jouées sans erreur.

## Écarts et remarques

- Capteur : le brochage utilisé est **SDA = GPIO7, SCL = GPIO6** (seule paire qui répond au scan, AHT20 `0x38` et BMP280 `0x77`), pas GPIO2 / GPIO5. `capteur.py` n'a pas été modifié en Phase 14.
- `dart format` n'a été appliqué qu'aux fichiers neufs : sur les fichiers existants il reformate tout le fichier (gros diff sans rapport).
- Le banc de rendu a installé `numpy` et `pillow` pour `py` (Python 3.13 de la tâche planifiée).

## Phase 14-bis (correctifs)

| Étape | Commit | Contenu |
|---|---|---|
| 14b.1 | `bf3ffbc` | minuteur : secondes de bout en bout + contrôle de version Android ↔ Dart |
| 14b.2 | `dd95f4c` | plus d'état clim fantôme (Android, app, agent, ESP32) |
| 14b.3 | `ef49abe` | capteur : lecture robuste, « -- » sans mesure |
| 14b.4 | `0be5ff3` | scène normale : température / humidité collées à l'heure, marge de 12 px |
| 14b.5 | voir `git log` | documentation |

**Causes**
- Minuteur « 10 s devient 10 min » : l'APK du téléphone datait de 19:04, avant le minuteur h/min/s (commit de 19:28). Un rechargement à chaud met à jour le Dart seul : Dart envoyait 10 (secondes), le Kotlin installé le lisait en minutes (alarme `dadou.clim.101` programmée à +10 min, relevée avec `adb shell dumpsys alarm`). Aucune conversion ×60 résiduelle dans le code actuel. Garde-fou : version du canal (`ClimPlan.VERSION = 2`).
- État fantôme : à l'expiration, `eteindre()` ne mettait l'état à off que si l'IR partait, une phase automatique laissait un `reste` périmé, et rien ne republiait ni ne péremptait l'état côté PC / ESP32.
- Température / humidité absentes : le fil **SCL (GPIO6) ne fait plus contact** (GPIO6 lit 8 mV avec son pull-down, contre 3,0 V quand le module est branché ; GPIO7/SDA est toujours tiré à 3,0 V) ; en plus, l'ancien code ne retentait jamais l'initialisation après un échec au démarrage. Ce n'est pas GPIO2 / GPIO5 : aucun rappel du module n'y est vu.

**Vérifications faites** : tests Dart (minuteur 10 s → 10, 1 h 2 min 3 s → 3723, version Android trop ancienne, `statutClim`), tests Python agent (13), `tools/test_capteur.py` (6, faux bus I2C), banc de rendu (37 aperçus, pire cas `00:00` / 100 %, 0 chevauchement, marge de 12 px), carte : empreintes identiques, `erreur.txt` absent, lignes `CLIM` / message `CAPTEUR` jouées, carte vivante après 130 s sans ligne `CLIM`. APK release installé sur le téléphone (`adb install -r`, 20:13).

**Non vérifié (téléphone verrouillé)** : l'alarme Android réelle à 10 s, la coupure de la clim et l'effacement sur l'ESP32 en moins de 5 s, et le test « PC éteint, minuteur lancé, PC rallumé ». Procédure : déverrouiller, ouvrir Controls, saisir 0 / 0 / 10, « Run for 0:00:10 » ; agent.log doit montrer `[agent] clim : on …, minuteur 10 s` puis, dix secondes plus tard, `[agent] clim : off …`. Pour le PC éteint : `Stop-ScheduledTask "ESP32 Telecommande Agent"`, lancer un minuteur de 3 min, attendre 40 s, `Start-ScheduledTask` : une ligne `clim : on … minuteur <n> s` doit apparaître en moins de 30 s.

## À faire à la main

- Installer `app\build\app\outputs\flutter-apk\app-release.apk`.
- Tester : « Flipped » / « Normal » (l'écran se retourne tout de suite, et reste retourné après rebranchement) ; le minuteur (champs, raccourcis, compte à rebours h:mm:ss, extinction à l'heure, app fermée, notification) ; l'écran de la carte (heure + température et humidité, bandeau clim toutes les 5 s, scènes calme, nuit, jeu) ; l'historique après une session de jeu (My games → Play history).
- Si l'écran retourné est décalé d'un côté : le dire (la marge `DECALAGE` n'est alors pas symétrique).
