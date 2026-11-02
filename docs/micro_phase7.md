# Micro — Phase 7 : arrêt propre du PC, écran noir sans veille, raccourcis, Contrôles refaits

- Date : 2026-11-02
- Statut : à appliquer (avec la Phase 8, dans la foulée)
- Basée sur : commit `b71ba89` (« Phase 7 : état des lieux », lui-même après `4336f77` « Phase 6 »), code lu sur GitHub
- Livraison : **`docs/micro_phase7_fichiers.zip`** (15 fichiers, remplacements complets ou nouveaux). SHA-256 : `a53f41cb0f1464c33c1b9c780e035cb1ea2fcd02e027912b1fce55fe59b309c8`
- Vérifié chez Claude web : `mpy-cross` (fichiers de la carte), `py_compile` + `pyflakes` (programme PC), `dart analyze` avec Flutter 3.47.2 (la révision de `app/.metadata`) et `flutter_lints` → **aucune remarque** ; scénario complet de l'ESP32 simulé (démarrage, compte à rebours, annulation, arrêt, retour du PC) ; serveur testé avec websockets 13.0 et 17.4. `flutter test` et `flutter build` restent à faire chez toi.

## Ce que contient la phase

1. **Arrêt du PC (bouton « Éteindre le PC »)**
   - L'ESP32 affiche un **compte à rebours** (« Arrêt du PC dans 42 s », barre qui se vide, la mascotte fait coucou). « Annuler l'arrêt » le fait disparaître (« Arrêt annulé »).
   - L'app montre aussi un bandeau rouge « Arrêt du PC dans 42 s » avec un bouton **Annuler** (Accueil et onglet PC de Contrôles).
   - À 0 : « Au revoir ! ». Quand le PC est vraiment éteint (12 s sans données), l'écran de l'ESP32 devient **complètement noir** (rétroéclairage à 0).
   - Même si tu éteins depuis le menu Démarrer de Windows, le programme PC prévient l'ESP32 (« Au revoir ») au moment où la session se ferme.
   - Si le PC ne s'éteint finalement pas (une app bloque l'arrêt), l'ESP32 revient à l'écran normal 90 s plus tard.
2. **Fini la boucle gris / ancien écran / noir quand le PC est éteint**
   - Cause : le port USB du portable éteint coupe et remet le courant, donc la carte redémarre sans arrêt. À chaque démarrage, le rétroéclairage s'allumait **avant** la première image (le gris), puis la scène de veille s'affichait **sans heure** (l'heure vient du PC).
   - Maintenant la carte démarre **noire**, et le reste tant que le PC ne lui parle pas et qu'elle ne connaît pas l'heure. Elle peut encore redémarrer quand le portable coupe le courant (on ne peut pas l'empêcher depuis le code), mais **on ne voit plus rien**. Dès que le PC démarre : « Bonjour Mihaja ! ».
   - Réponse à ta question : non, la carte ne s'éteint pas électriquement avec le PC (c'est le portable qui décide du courant sur son port USB), mais elle est maintenant noire et silencieuse.
3. **« Écran noir » au lieu d'« Éteindre l'écran »** (ce bouton mettait le PC en veille)
   - Une fenêtre noire couvre **chaque écran** (portable, écran externe en « étendre », « 2e écran seulement »…), la luminosité passe à 0, et Windows est **empêché de dormir** tant que l'écran noir est actif. Le PC n'est **pas verrouillé** (comme convenu).
   - Le PC reste joignable : musique, téléchargements, souris et raccourcis depuis le téléphone fonctionnent, **sans rallumer l'écran**.
   - Pour rallumer : bouton « Rallumer » dans l'app (Accueil, onglet PC), ou toucher le **vrai** clavier ou la **vraie** souris du PC. La luminosité d'avant revient (même si le programme PC a redémarré entre-temps).
   - « Veille » utilise maintenant la seule veille qui existe sur ton PC (veille moderne S0 : verrouillage + écran coupé). L'ancienne méthode `SetSuspendState` ne pouvait pas marcher sans S3 ni hibernation.
4. **Luminosité de l'écran de l'ESP32** dans Contrôles → carte « Luminosité » : un curseur « PC » et un curseur « ESP32 » (de 5 à 100 %), plus l'ampoule pour éteindre / allumer l'écran de l'ESP32. Le réglage est gardé par le programme PC et renvoyé à l'ESP32 à chaque connexion. Les niveaux « verrouillé » et « veille » suivent ce réglage.
5. **Raccourcis** (Contrôles → onglet « Raccourcis » → **+**) : un nom, une icône, et des étapes dans l'ordre :
   - **Touches** (ex. `ctrl+6`, `win+x`, `alt+tab`) : envoyées par Windows selon la disposition de ton clavier (AZERTY ou QWERTY), vues aussi par les jeux.
   - **Commande administrateur** (PowerShell ou cmd) : le programme PC est déjà administrateur, donc la commande part **directement**, sans Win+X, sans « Terminal (admin) » et **sans la fenêtre de confirmation Windows** (que le téléphone ne peut pas cliquer). « Fenêtre visible » : la fenêtre reste ouverte pour voir le résultat. Sinon : pas de fenêtre, et Dadou attend la fin avant l'étape suivante.
   - **Écrire un texte**, **Appuyer sur Entrée**, **Ouvrir une app**, **Attendre** (en ms), **Action Dadou** (volume, lecture, écran noir, verrouillage…).
   - Modèles pour démarrer : « Commande admin », « Ctrl + 6 », « Relancer Steam ».
   - Le programme PC vérifie tout (nom de 30 caractères max, 20 étapes max, touches connues…) avant d'enregistrer dans `tools\agent\raccourcis.json` (pas commité).
6. **Contrôles refait pour rester lisible** même avec beaucoup d'apps et de raccourcis :
   - en haut : Son, puis Luminosité (PC + ESP32) ;
   - puis un **lanceur à 3 onglets** : Raccourcis / Apps / PC, en grille de tuiles (3 par ligne, 5 sur grand écran), avec une **recherche** dès qu'il y a plus de 6 éléments ;
   - appui court = lancer ; **appui long** = Favori / Modifier / Supprimer ;
   - les apps se modifient maintenant (nom, lien, chemin) ; « Éteindre le PC » et « Veille » demandent confirmation.
7. **Favoris** : carte « Favoris » sur l'Accueil (et, en Phase 8, le widget du téléphone). On les choisit par appui long dans Contrôles.
8. **Plus de fusée** : chaque app a une icône selon son type ou son nom (navigateur, dossier, programme, musique, vidéo, jeu, terminal, calculatrice…).
9. **Débordements** : tous les nouveaux textes sont coupés proprement (« … ») ou passent à la ligne. Onglets maison au lieu de `SegmentedButton`, titres sur une ligne. Vérifié par l'analyse, à confirmer sur le téléphone avec une grande taille de texte.
10. **Corrections trouvées dans `erreur.txt` et `agent.log`** :
    - `'str' object has no attribute 'capitalize'` (n'existe pas en MicroPython) → remplacé ;
    - `UnicodeError` dans `lire_ligne` (octets bizarres au démarrage / à l'arrêt du PC) → ignorés ;
    - `TypeError: byref() … NoneType` dans `boucle_lecture` : le fil de lecture **mourait** pendant une PAUSE. Ensuite plus personne ne lisait l'ESP32, et sa sortie série pouvait se bloquer. Maintenant aucune boucle de l'agent ne peut plus s'arrêter sur une erreur.

## Plusieurs écrans (étendre, 2e écran seulement, dupliquer)

- Écran noir : une fenêtre noire sur **chaque** écran allumé. La luminosité passe à 0 sur l'écran du portable, et sur les écrans externes qui acceptent le réglage (DDC/CI). Pour les autres, la fenêtre noire suffit.
- « 2e écran seulement » : l'écran du portable est éteint par Windows ; seul l'écran externe est couvert.
- Le programme PC travaille en pixels réels (`SetProcessDpiAwareness`), donc la mise à l'échelle à 150 % ne décale rien.
- Le nombre d'écrans est envoyé à l'app (`ecrans`) ; il sert à l'aperçu de la Phase 8.

## Nouveautés du protocole

- Série PC → ESP32 : `EVT ARRET n` (n s ; `0` annulé ; `-1` Windows s'éteint maintenant), `LUM_ESP 5..100`, `EVT ACTION RAC nom`, `EVT ACTION TOUCHES ctrl+6`, `EVT ACTION ECRAN_ON`.
- Commandes de l'agent : `ECRAN_OFF` / `ECRAN_ON` / `ECRAN_BASCULE`, `LUM_ESP n`, `RAC nom`, `TOUCHES ctrl+6` ; `ARRET` refuse un 2e arrêt déjà prévu.
- WebSocket : `raccourcis`, `rac_ajout {raccourci, ancien}`, `rac_retrait {nom}` ; réponse `raccourcis [...]` ; `etat` contient en plus `arret` (s, -1 = rien), `ecran_noir`, `lum_esp`, `ecrans`.
- Fichiers de l'agent non commités : `raccourcis.json`, `preferences.json` (ajoutés au `.gitignore`).

## Contenu du zip (à extraire à la racine de Micro, en écrasant)

| Fichier | SHA-256 « avant » (16 car., CRLF → LF) | SHA-256 « après » |
|---|---|---|
| `.gitignore` | `7c130c6258d6c581` | `8b2eb9516d170616` |
| `CLAUDE.md` | `72016e27efe4fd33` | `62b57effa871f9fc` |
| `app/lib/actions.dart` | nouveau | `50d739f18e870921` |
| `app/lib/connexion.dart` | `1fead79394ca5deb` | `c0c184760ec41202` |
| `app/lib/ecrans/accueil.dart` | `fa80d9eb715c4c48` | `026a7f96f0a8d198` |
| `app/lib/ecrans/controles.dart` | `cfa199dcad8bbebd` | `7c65e4f372fe76b5` |
| `app/lib/ecrans/editeur_raccourci.dart` | nouveau | `a51cf1dfb134d195` |
| `app/lib/etat.dart` | `e29db5d17c414c54` | `e61be5f31caf980b` |
| `app/lib/theme.dart` | `4555169ea29d5035` | `f96229a027333829` |
| `app/test/widget_test.dart` | `b010fe2132f96e8c` | `13f8ccaf8cd9401d` |
| `esp/lib/lcd.py` | `29d29b7ae85e7c0f` | `c829459e9a68f6a3` |
| `esp/lib/ui.py` | `c1cb124fcd29a908` | `c947595ded93e838` |
| `esp/main.py` | `bfa2089b8cf1c507` | `af5bf552b8acf100` |
| `tools/agent/agent_pc.py` | `8e9cee7c2f4d007a` | `b1303369c2184a1d` |
| `tools/agent/serveur_app.py` | `c0173d2d96390b94` | `93865df271f51b82` |

## Test à blanc (avant d'extraire)

Dans le dossier Micro :

```
py -X utf8 -c "import hashlib,sys,os; [print(f, hashlib.sha256(open(f,'rb').read().replace(b'\r\n',b'\n')).hexdigest()[:16] if os.path.exists(f) else 'absent') for f in sys.argv[1:]]" .gitignore CLAUDE.md app/lib/actions.dart app/lib/connexion.dart app/lib/ecrans/accueil.dart app/lib/ecrans/controles.dart app/lib/ecrans/editeur_raccourci.dart app/lib/etat.dart app/lib/theme.dart app/test/widget_test.dart esp/lib/lcd.py esp/lib/ui.py esp/main.py tools/agent/agent_pc.py tools/agent/serveur_app.py
```

- Chaque empreinte doit être **exactement** celle de la colonne « avant » (« absent » pour les fichiers nouveaux).
- Si une empreinte diffère : **ne rien extraire**, montrer `git diff` / `git log -3 -- <fichier>` pour ce fichier et s'arrêter.
- Après extraction : toutes les empreintes doivent être celles de la colonne « après ».

## Liste de contrôle

| Contrôle | Attendu |
|---|---|
| SHA-256 du zip | `a53f41cb0f1464c33c1b9c780e035cb1ea2fcd02e027912b1fce55fe59b309c8` |
| Test à blanc | 15 empreintes « avant » identiques (ou « absent ») |
| Extraction | `git status` : seulement les 15 fichiers listés (+ les docs de la phase) |
| Empreintes après extraction | toutes identiques à la colonne « après » |
| `py -m py_compile tools\agent\agent_pc.py tools\agent\serveur_app.py esp\main.py esp\lib\ui.py esp\lib\lcd.py` | aucune erreur |
| Test des raccourcis sans toucher aux vrais fichiers (voir plus bas) | les lignes attendues |
| Copie sur la carte (avec PAUSE) : `esp\main.py` → `:main.py`, `esp\lib\ui.py` → `:lib/ui.py`, `esp\lib\lcd.py` → `:lib/lcd.py`, puis `reset` ; console 10 s | pas de trace d'erreur ; l'écran reste **noir** (le programme PC est en pause, c'est normal) |
| Dans `app` : `flutter pub get` puis `flutter analyze` | **aucune erreur** (les « info » de style : les lister sans les corriger) |
| `flutter test` | 5 tests réussis |

Test des raccourcis :

```
py -X utf8 -c "import sys, tempfile, pathlib; sys.path.insert(0, r'tools\agent'); import agent_pc as a; d = pathlib.Path(tempfile.mkdtemp()); a.FICHIER_RACCOURCIS = d/'r.json'; a.FICHIER_APPS = d/'a.json'; print(a.lire_touches('ctrl+6'), a.lire_touches('win+x'), a.lire_touches('ctrl+zz')); print(a.ajouter_raccourci({'nom': 'Essai', 'icone': 'jeu', 'etapes': [{'type': 'commande', 'valeur': 'Get-Date', 'visible': False}, {'type': 'pause', 'valeur': '500'}, {'type': 'touches', 'valeur': 'ctrl+6'}]})); print(a.ajouter_raccourci({'nom': 'X', 'etapes': [{'type': 'touches', 'valeur': 'ctrl+zz'}]})); print(a.retirer_raccourci('essai')); print(len(a.moniteurs_windows()), 'écran(s)')"
```

Attendu : `[162, 54] [91, 88] None`, `(True, 'Raccourci ajouté : Essai')`, `(False, 'Étape 1 : touches inconnues « ctrl+zz » (ex. ctrl+6, win+x)')`, `(True, 'Raccourci retiré : Essai')`, `1 écran(s)` (ou plus si un écran externe est branché).

En cas d'**erreur** de compilation Dart : ne rien corriger, copier les messages complets dans `docs/etat_code.md`.

## Tests sur l'appareil (par Mihaja, après la Phase 8)

Voir la fin de `docs/micro_phase8.md` : tous les tests des Phases 7 et 8 y sont regroupés.
