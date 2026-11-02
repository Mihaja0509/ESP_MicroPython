# Micro — Phase 8 : aperçu de l'écran du PC + widget Android

- Date : 2026-11-02
- Statut : à appliquer **juste après la Phase 7** (ses fichiers « avant » sont les fichiers « après » de la Phase 7)
- Livraison : **`docs/micro_phase8_fichiers.zip`** (36 fichiers). SHA-256 : `571131938d8e79c7dac4be7fad830384f27b886b38306cf414573dacf0af91b9`
- Vérifié chez Claude web : `dart analyze` (Flutter 3.47.2 + flutter_lints) → aucune remarque ; Kotlin compilé avec `kotlinc` contre `android.jar` (API 33) → aucune erreur ; serveur testé de bout en bout (requête du widget, mauvais token → 401, image envoyée en binaire, clic) avec websockets 13.0 et 17.4 ; fabrication de l'image testée (couleurs, flèche de la souris, 2e écran). Le build Android (Gradle) reste à faire chez toi.

## Ce que contient la phase

1. **Onglet « Écran »** dans l'app (entre Souris et Contrôles) : l'**aperçu en direct** de l'écran du PC.
   - Une nouvelle image est demandée dès que la précédente arrive : le rythme s'adapte au réseau (Wi-Fi ou 4G par Tailscale). Le nombre d'images par seconde s'affiche.
   - Qualité (icône HQ) : **Éco** (640 px, ~4 img/s, pour la 4G), **Normal** (960 px), **HD** (1440 px).
   - En bas, ce que fait un toucher sur l'image : **Voir** (rien), **Clic**, **Double** (double-clic), **Droit**. Un appui long fait toujours un clic droit. Pincer pour zoomer.
   - La flèche de la souris est dessinée sur l'image.
   - Plusieurs écrans (« étendre ») : un bouton `1/2` passe d'un écran à l'autre ; le clic tombe sur le bon écran. En « 2e écran seulement », c'est l'écran allumé qui est montré.
   - **Écran noir actif** : l'aperçu montre quand même le vrai écran (la fenêtre noire est exclue des captures), et tes clics depuis l'aperçu ne rallument pas l'écran du PC. Pratique pour piloter le PC « en secret ».
   - L'aperçu ne tourne que si l'onglet est affiché et l'app au premier plan : pas de données gaspillées. Bouton pause.
   - PC verrouillé : Windows ne laisse capturer que l'écran de verrouillage, l'image peut être noire (un message le dit).
2. **Widget Android « Dadou »** (4 × 1, redimensionnable) : le logo (ouvre l'app) + les **4 premiers favoris**.
   - Un appui envoie la commande au PC **sans ouvrir l'app** (petite requête au programme PC, avec l'appairage de l'app) ; le résultat s'affiche en petit message (« Volume : 30 % », « PC injoignable »…).
   - Les favoris se choisissent dans Contrôles (appui long → Ajouter aux favoris) ; l'ordre est celui de l'ajout. Le widget se met à jour tout seul.
   - Attention : dans le widget, « Éteindre le PC » et « Veille » partent **sans confirmation** (l'arrêt reste annulable 60 s).
   - Icônes dessinées en vectoriel (même style que l'app), fond dégradé crépuscule.

## Ce qu'il faut installer sur le PC

`py -m pip install --user mss Pillow` (capture d'écran rapide et JPEG). Sans eux, l'aperçu affiche « Aperçu indisponible : il manque mss et Pillow sur le PC » ; le reste marche.

## Nouveautés du protocole

- WebSocket téléphone → PC : `apercu {ecran, largeur, qualite}` (une image à la fois par téléphone), `pointeur {ecran, x, y, clic}` (x, y de 0 à 1 ; clic `gauche`, `droit`, `double` ou vide).
- PC → téléphone : `apercu_info {ecran, ecrans, largeur, hauteur, verrou}` puis l'image JPEG en **message binaire** ; `apercu_erreur {texte}`.
- HTTP sur le même port 8765 (pour le widget) : `GET /widget?ligne=PLAY` avec l'en-tête `X-Token: <token>` → texte de la réponse ; `401` si le téléphone n'est pas appairé. Rien de nouveau à ouvrir dans le pare-feu.

## Contenu du zip (à extraire à la racine de Micro, en écrasant)

| Fichier | SHA-256 « avant » (16 car., CRLF → LF) | SHA-256 « après » |
|---|---|---|
| `CLAUDE.md` | `62b57effa871f9fc` | `f5646e9fe6adf5db` |
| `app/android/app/src/main/AndroidManifest.xml` | `cca2dbb77824dd65` | `26929b7514efafce` |
| `app/android/app/src/main/kotlin/com/mmdigitek/esp_micro/DadouWidget.kt` | nouveau | `7bd577974f69d64b` |
| `app/android/app/src/main/kotlin/com/mmdigitek/esp_micro/MainActivity.kt` | `e3a36510453ab858` | `915b45375a4a1b47` |
| `app/android/app/src/main/res/drawable/w_annuler.xml` | nouveau | `e895ba1cda19b0a5` |
| `app/android/app/src/main/res/drawable/w_app.xml` | nouveau | `a89e9196261767b9` |
| `app/android/app/src/main/res/drawable/w_bureau.xml` | nouveau | `0ffc01f18da33b68` |
| `app/android/app/src/main/res/drawable/w_clavier.xml` | nouveau | `ed1bad4d7144af9a` |
| `app/android/app/src/main/res/drawable/w_dossier.xml` | nouveau | `61187f11edda9486` |
| `app/android/app/src/main/res/drawable/w_eclair.xml` | nouveau | `5dfa436b45dbcf16` |
| `app/android/app/src/main/res/drawable/w_ecran.xml` | nouveau | `3176cdfd2873e027` |
| `app/android/app/src/main/res/drawable/w_etoile.xml` | nouveau | `6e7b354db7ace212` |
| `app/android/app/src/main/res/drawable/w_jeu.xml` | nouveau | `d71187f70ffdee01` |
| `app/android/app/src/main/res/drawable/w_muet.xml` | nouveau | `5daddac80fe7e96a` |
| `app/android/app/src/main/res/drawable/w_musique.xml` | nouveau | `f612e600f1ec7588` |
| `app/android/app/src/main/res/drawable/w_play.xml` | nouveau | `ec089f85781ffd42` |
| `app/android/app/src/main/res/drawable/w_power.xml` | nouveau | `7e9bc6339c91d216` |
| `app/android/app/src/main/res/drawable/w_suivant.xml` | nouveau | `1005bfe54cce6597` |
| `app/android/app/src/main/res/drawable/w_terminal.xml` | nouveau | `4dd74fe072ea176f` |
| `app/android/app/src/main/res/drawable/w_veille.xml` | nouveau | `078cf5e35888e29d` |
| `app/android/app/src/main/res/drawable/w_verrou.xml` | nouveau | `ad9d02d39aa43642` |
| `app/android/app/src/main/res/drawable/w_vol_moins.xml` | nouveau | `f9db7d29dc8bdcf2` |
| `app/android/app/src/main/res/drawable/w_vol_plus.xml` | nouveau | `ac3ed1af02aa6b68` |
| `app/android/app/src/main/res/drawable/w_web.xml` | nouveau | `22d725593579b9b0` |
| `app/android/app/src/main/res/drawable/widget_bouton.xml` | nouveau | `5fec343075f9db17` |
| `app/android/app/src/main/res/drawable/widget_fond.xml` | nouveau | `c4dfb1af04fea570` |
| `app/android/app/src/main/res/layout/widget_dadou.xml` | nouveau | `0256911568af4fe2` |
| `app/android/app/src/main/res/values/strings.xml` | nouveau | `bf036370baece82e` |
| `app/android/app/src/main/res/xml/widget_dadou_info.xml` | nouveau | `857856922c0d777c` |
| `app/lib/connexion.dart` | `c0c184760ec41202` | `5e27ae26229a0f61` |
| `app/lib/ecrans/apercu.dart` | nouveau | `e94d5d4432978f7f` |
| `app/lib/main.dart` | `3c5d48b8c3cb95ec` | `350749b0601006cb` |
| `app/lib/widget_android.dart` | nouveau | `24adf2403fce9030` |
| `app/test/widget_test.dart` | `13f8ccaf8cd9401d` | `ce71e9084c245a28` |
| `tools/agent/agent_pc.py` | `b1303369c2184a1d` | `b21f52df54fe5bda` |
| `tools/agent/serveur_app.py` | `93865df271f51b82` | `5abfd3e95ad9cb00` |

## Test à blanc (avant d'extraire, APRÈS la Phase 7)

```
py -X utf8 -c "import hashlib,sys,os; [print(f, hashlib.sha256(open(f,'rb').read().replace(b'\r\n',b'\n')).hexdigest()[:16] if os.path.exists(f) else 'absent') for f in sys.argv[1:]]" CLAUDE.md app/android/app/src/main/AndroidManifest.xml app/android/app/src/main/kotlin/com/mmdigitek/esp_micro/DadouWidget.kt app/android/app/src/main/kotlin/com/mmdigitek/esp_micro/MainActivity.kt app/android/app/src/main/res/drawable/w_annuler.xml app/android/app/src/main/res/drawable/w_app.xml app/android/app/src/main/res/drawable/w_bureau.xml app/android/app/src/main/res/drawable/w_clavier.xml app/android/app/src/main/res/drawable/w_dossier.xml app/android/app/src/main/res/drawable/w_eclair.xml app/android/app/src/main/res/drawable/w_ecran.xml app/android/app/src/main/res/drawable/w_etoile.xml app/android/app/src/main/res/drawable/w_jeu.xml app/android/app/src/main/res/drawable/w_muet.xml app/android/app/src/main/res/drawable/w_musique.xml app/android/app/src/main/res/drawable/w_play.xml app/android/app/src/main/res/drawable/w_power.xml app/android/app/src/main/res/drawable/w_suivant.xml app/android/app/src/main/res/drawable/w_terminal.xml app/android/app/src/main/res/drawable/w_veille.xml app/android/app/src/main/res/drawable/w_verrou.xml app/android/app/src/main/res/drawable/w_vol_moins.xml app/android/app/src/main/res/drawable/w_vol_plus.xml app/android/app/src/main/res/drawable/w_web.xml app/android/app/src/main/res/drawable/widget_bouton.xml app/android/app/src/main/res/drawable/widget_fond.xml app/android/app/src/main/res/layout/widget_dadou.xml app/android/app/src/main/res/values/strings.xml app/android/app/src/main/res/xml/widget_dadou_info.xml app/lib/connexion.dart app/lib/ecrans/apercu.dart app/lib/main.dart app/lib/widget_android.dart app/test/widget_test.dart tools/agent/agent_pc.py tools/agent/serveur_app.py
```

- Chaque empreinte doit être celle de la colonne « avant » (« absent » pour les nouveaux fichiers).
- Si une empreinte diffère : **ne rien extraire**, montrer `git diff` pour ce fichier et s'arrêter.

## Liste de contrôle

| Contrôle | Attendu |
|---|---|
| SHA-256 du zip | `571131938d8e79c7dac4be7fad830384f27b886b38306cf414573dacf0af91b9` |
| Test à blanc | 36 empreintes « avant » identiques (ou « absent ») |
| Extraction | `git status` : seulement les 36 fichiers listés (+ docs) |
| Empreintes après extraction | toutes identiques à la colonne « après » |
| `py -m pip install --user mss Pillow` puis `py -c "import mss, PIL; print(mss.__version__, PIL.__version__)"` | deux numéros de version |
| `py -m py_compile tools\agent\agent_pc.py tools\agent\serveur_app.py` | aucune erreur |
| Test de capture (voir plus bas) | une taille en octets (quelques dizaines de milliers) et les infos de l'écran (`largeur` 2560, `hauteur` 1600 pour l'écran du portable) |
| Dans `app` : `flutter pub get`, `flutter analyze` | **aucune erreur** (lister les « info » sans les corriger) |
| `flutter test` | 6 tests réussis |
| `flutter build apk --release` | APK construit (noter le chemin et la taille) |

Test de capture (lit l'écran, ne clique rien) :

```
py -X utf8 -c "import sys; sys.path.insert(0, r'tools\agent'); import agent_pc as a; o, i = a.capture_ecran(0, 960, 60); print(len(o) if o else o, i)"
```

En cas d'**erreur** de compilation (Dart, Kotlin ou Gradle) : ne rien corriger, copier les messages complets dans `docs/etat_code.md`.

## Tests sur l'appareil (par Mihaja) — Phases 7 et 8

Avant : programme PC redémarré (Stop / Start de la tâche, en administrateur), nouvel APK installé.

1. **ESP32 au démarrage** : débranche / rebranche la carte, PC allumé. L'écran reste **noir** quelques secondes (pas de gris), puis « Bonjour Mihaja ! ».
2. **Luminosité de l'ESP32** : Contrôles → curseur « ESP32 » à 20 % puis 100 % → l'écran de l'ESP32 suit. Redémarre le programme PC : la valeur est gardée.
3. **Écran noir** : Accueil → « Écran noir ». Les écrans du PC deviennent noirs. Attends **5 minutes** : le PC ne s'endort pas (l'app reste « Connecté », la musique continue). Bouge la souris depuis l'onglet Souris : l'écran **reste noir**. Touche le vrai clavier du PC : tout se rallume, avec la luminosité d'avant. Refais-le et rallume avec « Rallumer » dans l'app.
4. Si tu as un écran externe : refais le test 3 en mode « Étendre » puis « 2e écran seulement ».
5. **Aperçu** : onglet Écran. L'image du PC arrive et bouge (img/s affiché). Mode « Clic » : touche une icône du bureau → elle est sélectionnée ; mode « Double » → elle s'ouvre. Appui long → menu du clic droit. Essaie Éco / HD. Active l'écran noir : l'aperçu montre toujours le vrai écran.
6. **Raccourci Ctrl + 6** : Contrôles → Raccourcis → + → modèle « Ctrl + 6 » → Enregistrer. Ouvre l'app ou le jeu qui utilise Ctrl + 6, touche la tuile → ça marche. La mascotte affiche « Ctrl + 6 ».
7. **Commande administrateur** : + → modèle « Commande admin », écris `Get-Date; whoami /groups | findstr /i "S-1-16-12288"` → Enregistrer → touche la tuile. Une fenêtre PowerShell « Dadou : Commande admin » s'ouvre **sans demande de confirmation** et affiche la date puis une ligne contenant `S-1-16-12288` (= niveau administrateur).
8. Envoie-moi les **commandes exactes** de tes préparations de jeu : je te prépare les raccourcis tout faits.
9. **Contrôles chargé** : ajoute 8 apps ou raccourcis → la recherche apparaît ; appui long → Favori / Modifier / Supprimer. Mets la taille de police du téléphone au maximum : **aucune bande « OVERFLOWED »** nulle part (Accueil, Écran, Contrôles, éditeur de raccourci, fenêtres).
10. **Favoris + widget** : mets 4 favoris (ex. Lecture/pause, Volume −, Volume +, Écran noir). Ils apparaissent sur l'Accueil. Écran d'accueil du téléphone → appui long → Widgets → Dadou → pose-le. Touche « Volume + » : un petit message s'affiche et le volume du PC monte, **sans ouvrir l'app**. Coupe le Wi-Fi (4G + Tailscale) : ça marche toujours.
11. **Arrêt** : Contrôles → PC → « Éteindre le PC » → l'ESP32 affiche le compte à rebours, l'app le bandeau rouge. « Annuler » → « Arrêt annulé ». Recommence sans annuler : « Au revoir ! », puis, PC éteint, l'ESP32 devient **noir et le reste** (plus de boucle). Rallume le PC : « Bonjour Mihaja ! » une seule fois.
12. **Arrêt par Windows** (menu Démarrer → Arrêter) : l'ESP32 dit « Au revoir ! » puis devient noir.
13. Envoie-moi des captures d'écran et ce qui ne va pas.
