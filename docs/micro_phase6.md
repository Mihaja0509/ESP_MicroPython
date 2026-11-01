# Micro — Phase 6 : corrections de l'app « Dadou » + ajouter / retirer des apps

- Date : 2026-11-01
- Statut : à appliquer
- Basée sur : fin de Phase 5 v2 + 5-bis (fichiers du zip de la Phase 5 v2, appliqués exactement)
- Livraison : **`docs/micro_phase6_fichiers.zip`** (9 fichiers, tous des remplacements complets). SHA-256 : `72bfb7af3994e2a390772a8793cb00cd650ae629bab210d3af8be92a6cb9fb3d`

## Ce que corrige et ajoute la phase

1. **Plus de « BOTTOM OVERFLOWED »** : les boutons « Actions rapides » (Accueil) et « Alimentation » (Contrôles) sont rangés dans une grille dont la hauteur suit le texte (`GrilleBoutons`, dans `theme.dart`). Légendes plus courtes sur l'Accueil : « Verrou », « ESP32 ».
2. **L'Accueil ne saute plus** : les pastilles (batterie, volume, CPU °, GPU °) restent toujours à la même place ; une valeur inconnue s'affiche « – » (dans les anneaux aussi). Le programme PC garde la dernière bonne mesure quelques secondes quand une lecture rate (volume, GPU, température CPU, FPS) : plus de « 0 % » qui disparaît puis revient.
3. **L'ESP32 reste tranquille pendant la veille du PC** :
   - Programme PC : quand Windows réveille le PC tout seul (veille moderne), le programme ne dit plus rien à l'ESP32 tant que personne ne touche le clavier ou la souris (ou le téléphone). Après 5 minutes sans personne, il reprend quand même.
   - ESP32 : il faut 5 s de données sans coupure pour dire « le PC est revenu », et l'ESP32 dit « absent » après 12 s sans données (au lieu de 8). « Bonjour Mihaja ! » s'affiche seulement après une vraie absence (plus d'une minute) ; « À bientôt ! » seulement si le PC était allumé depuis plus de 20 s.
4. **Infos plus rapides** : quand on revient sur l'app, elle se reconnecte tout de suite si la liaison est morte en arrière-plan ; après une coupure, le premier essai de reconnexion part après 0,5 s (puis toutes les 3 s). Le programme PC réessaie la liaison USB toutes les 3 s au lieu de 10.
5. **Applications : ajouter et retirer depuis le téléphone** (onglet Contrôles) :
   - Bouton **+** : nom + **Lien web** (ex. `netflix.com`, `https://` ajouté si besoin) ou **Windows** (programme, fichier ou dossier, ex. `C:\Program Files\…\jeu.exe` ; « Copier en tant que chemin » de l'Explorateur marche, les guillemets sont retirés).
   - Bouton **crayon** : une croix rouge sur chaque app pour la retirer (avec confirmation).
   - Le programme PC vérifie tout (nom de 30 caractères max, pas de guillemets ni de retour à la ligne, lien http/https valide, chemin qui existe sur le PC) puis écrit `tools\agent\apps.json`. Un nom déjà pris remplace l'ancienne app.
   - Les apps s'ouvrent avec `os.startfile` (et `start` en secours pour les commandes comme `code`).
   - Nouveaux messages WebSocket : `app_ajout {nom, cible, sorte: web|chemin}`, `app_retrait {nom}` ; `apps` renvoie maintenant `[{nom, cible, type}]`.

## Contenu du zip (à extraire à la racine de Micro, en écrasant)

| Fichier | SHA-256 « avant » (16 premiers caractères, CRLF → LF) | SHA-256 « après » |
|---|---|---|
| `esp/main.py` | `5fed853eb38e10f8` | `bfa2089b8cf1c507` |
| `esp/lib/ui.py` | `5e01fe9715ab8efd` | `c1cb124fcd29a908` |
| `tools/agent/agent_pc.py` | `74b01176e14fc923` | `8e9cee7c2f4d007a` |
| `tools/agent/serveur_app.py` | `5e42920b33f3d616` | `c0173d2d96390b94` |
| `app/lib/theme.dart` | `0cfd0af2c01d77cd` | `4555169ea29d5035` |
| `app/lib/connexion.dart` | `116b1de6fdf252d0` | `1fead79394ca5deb` |
| `app/lib/ecrans/accueil.dart` | `60dc0e3dbb4aa7b1` | `fa80d9eb715c4c48` |
| `app/lib/ecrans/controles.dart` | `779cb0c6359f2fce` | `cfa199dcad8bbebd` |
| `app/lib/widgets/anneau.dart` | `b06d8a27ed91467f` | `837794ed059d43c7` |

Aucun autre fichier ne change (ni `esp/assets/`, ni `apps.json`, ni la tâche planifiée, ni le pare-feu).

## Test à blanc (avant d'extraire)

Dans le dossier Micro :

```
py -X utf8 -c "import hashlib,sys; [print(f, hashlib.sha256(open(f,'rb').read().replace(b'\r\n',b'\n')).hexdigest()[:16]) for f in sys.argv[1:]]" esp/main.py esp/lib/ui.py tools/agent/agent_pc.py tools/agent/serveur_app.py app/lib/theme.dart app/lib/connexion.dart app/lib/ecrans/accueil.dart app/lib/ecrans/controles.dart app/lib/widgets/anneau.dart
```

- Les 9 empreintes doivent être **exactement** celles de la colonne « avant ».
- Si une empreinte diffère : **ne rien extraire**, montrer `git diff` / `git log -3 -- <fichier>` pour ce fichier et s'arrêter.
- Après extraction : les 9 empreintes doivent être celles de la colonne « après ».

## Liste de contrôle

| Contrôle | Attendu |
|---|---|
| SHA-256 du zip | identique au document |
| Test à blanc | 9 empreintes « avant » identiques |
| Extraction | `git status` : seulement les 9 fichiers listés (+ les docs de la phase) |
| Empreintes après extraction | 9 empreintes « après » identiques |
| `py -m py_compile tools\agent\agent_pc.py tools\agent\serveur_app.py esp\main.py esp\lib\ui.py` | aucune erreur |
| Test des apps sans toucher au vrai `apps.json` : `py -X utf8 -c "import sys; sys.path.insert(0, r'tools\agent'); import agent_pc as a, tempfile, pathlib; a.FICHIER_APPS = pathlib.Path(tempfile.gettempdir())/'apps_test.json'; a.FICHIER_APPS.unlink(missing_ok=True); print(a.ajouter_app('Netflix','netflix.com','web')); print(a.ajouter_app('Bloc','C:/Windows/notepad.exe','chemin')); print(a.ajouter_app('X','C:/nexiste/pas.exe','chemin')); print(a.retirer_app('netflix')); print(a.liste_apps()[-1]); print('inactivite', round(a.inactivite()))"` | `(True, 'App ajoutée : Netflix')`, `(True, 'App ajoutée : Bloc')`, `(False, 'Introuvable sur le PC : …')`, `(True, 'App retirée : Netflix')`, `{'nom': 'Bloc', … 'type': 'chemin'}`, un nombre de secondes |
| Copie sur la carte (avec PAUSE) : `esp\main.py` → `:main.py`, `esp\lib\ui.py` → `:lib/ui.py`, puis reset ; console 10 s | pas de trace d'erreur |
| Redémarrer le programme PC : supprimer PAUSE, puis **demander à Mihaja** de lancer en PowerShell administrateur `Stop-ScheduledTask -TaskName 'ESP32 Telecommande Agent'` puis `Start-ScheduledTask -TaskName 'ESP32 Telecommande Agent'` | les 20 dernières lignes de `tools\agent\agent.log` : « serveur app prêt », « ESP32 connectée » |
| Dans `app` : `flutter pub get` puis `flutter analyze` | **aucune erreur** (les « info » de style sont acceptées : les lister sans les corriger) |
| `flutter test` | réussi |
| `flutter build apk --release` | APK construit (noter le chemin et la taille) |

En cas d'**erreur** de compilation Dart : ne rien corriger, copier les messages complets dans `docs/etat_code.md`.

## Tests sur l'appareil (par Mihaja)

1. **Accueil** et **Contrôles** : plus aucune bande jaune et noire « OVERFLOWED », même avec une grande taille de texte sur le téléphone.
2. **Accueil** pendant 1 minute : rien ne saute ; les pastilles restent en place.
3. **Applications** : + → « Lien web », nom « Netflix », lien `netflix.com` → « App ajoutée : Netflix » et la puce apparaît ; touche-la → Netflix s'ouvre sur le PC. + → « Windows », colle le chemin d'un programme (clic droit sur le .exe → « Copier en tant que chemin ») → il s'ouvre. Crayon → croix rouge → « Retirer » → l'app disparaît.
4. **Veille** : mets le PC en veille et laisse-le 15 minutes : l'ESP32 reste sur la scène de nuit (pas de « Bonjour Mihaja ! » qui revient). Réveille le PC et touche le clavier : « Bonjour Mihaja ! » une seule fois.
5. **Reconnexion** : quitte l'app 5 minutes puis reviens : les infos reviennent en moins de 2 s.
6. Envoie-moi des captures d'écran et ce qui ne va pas.
