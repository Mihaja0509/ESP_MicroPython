# Micro — MicroPython + écran

Projet séparé de `..\firmware` et `..\app` (projet clim, en pause).

- Carte : Waveshare **ESP32-S3-LCD-1.47** seule (ESP32-S3R8, 8 Mo PSRAM octal, 16 Mo flash, USB natif, écran ST7789 172×320), **sans module externe**.
- `esp/` : code MicroPython copié sur la carte (`main.py` à la racine, `lib/` dans le dossier `lib` de la carte).
- `app/` : app Dart/Flutter Android (`com.mmdigitek.esp_micro`, nom affiché « Dadou »).
- `docs/` : documents de phase et état du code (à appliquer exactement).
- `bin/` : firmware MicroPython téléchargé (ignoré par Git).
- Dépôt : https://github.com/Mihaja0509/ESP_MicroPython.git

## Architecture (Phase 5)

```
App Android « Dadou » ⇄ WebSocket (port 8765) ⇄ agent PC (agent_pc.py + serveur_app.py) ⇄ USB série (COM4) ⇄ ESP32
```

- L'ESP32 n'a pas de Wi-Fi utilisable (box en 5 GHz) : tout passe par l'agent PC.
- Accès de partout : **Tailscale** sur le PC et le téléphone (même compte) ; dans l'app, adresse du PC en `100.x.y.z`. Pare-feu : `tools\agent\autoriser_app.ps1` (administrateur, lancé par Mihaja) ouvre 8765 au réseau local et à Tailscale seulement.
- **Appairage** : l'app demande un code → l'agent envoie `EVT PIN 123456` (bandeau 60 s sur l'ESP32) ; code valable 2 min, 5 essais. Téléphones appairés dans `tools\agent\appareils.json` (jamais lu, jamais commité). `EVT APP 1|0` = téléphone connecté / déconnecté.
- Souris, clics, défilement et texte de l'app : exécutés directement sur le PC (SendInput). Raccourcis (`KEY`) et touches multimédia : via l'ESP32. `VOL n` = volume exact. État envoyé à l'app 4 fois par seconde.
- Dépendance PC en plus : `websockets` (`py -m pip install --user -U websockets`).

## Fichiers de l'app (`app/`)

- `lib/main.dart` (navigation), `lib/etat.dart` (état reçu du PC), `lib/connexion.dart` (WebSocket + appairage), `lib/theme.dart` (couleurs, fonds crépuscule / néon / nuit).
- `lib/ecrans/` : `accueil.dart`, `souris.dart` (pavé tactile + clavier), `controles.dart` (volume, luminosité, apps, alimentation), `reglages.dart` (adresse, appairage, aide Tailscale).
- `lib/widgets/` : `mascotte.dart`, `anneau.dart`.
- `assets/images/perso_*.png` (8, exportées par `tools\assets\generer_assets.py`), `assets/fonts/Inter-*.otf` (4) + licence.
- `test/widget_test.dart` (2 tests). Dépendances : `web_socket_channel`, `shared_preferences`.
- Manifeste : permission `INTERNET`, `usesCleartextTraffic="true"` (WebSocket `ws://` en clair, protégé par Tailscale + appairage).
- Icône (visage de la mascotte qui rit, icône adaptative) : `py tools\assets\generer_icone.py` crée `app/assets/icone/icone.png`, `icone_avant.png`, `icone_fond.png` ; puis dans `app/` : `dart run flutter_launcher_icons` (réglages dans `pubspec.yaml`) génère `android/app/src/main/res/mipmap-*/ic_launcher.png`, `drawable-*/ic_launcher_background.png` / `ic_launcher_foreground.png` et `mipmap-anydpi-v26/ic_launcher.xml`.
- APK release (signée avec la clé debug) : `app\build\app\outputs\flutter-apk\app-release.apk`.

## Brochage de la carte (Waveshare)

| Fonction | GPIO |
|---|---|
| Écran ST7789 172×320 : SCLK / MOSI / CS / DC / RST / rétroéclairage | 40 / 45 / 42 / 41 / 39 / 48 |
| LED RGB (WS2812) | 38 |
| Bouton BOOT | 0 |

## Commandes

Python : utiliser `py` (le `python` du PATH est l'alias Microsoft Store).

Carte (le port change après un flash ou un reset USB : le retrouver avec `devs`) :
- `py -m mpremote devs` : lister les ports
- `py -m mpremote connect <port> fs cp esp/main.py :main.py` : copier un fichier (`fs cp esp/lib/lcd.py :lib/lcd.py` pour la lib)
- `py -m mpremote connect <port> fs ls` : lister les fichiers de la carte
- `py -m mpremote connect <port> reset` : redémarrer
- `py -m mpremote connect <port> repl` : console interactive (Ctrl-] pour quitter)

Agent PC (`tools\agent\agent_pc.py`) : il occupe le port COM4 tant qu'il tourne.
- En fond : tâche planifiée « ESP32 Telecommande Agent » (pythonw, `--service`, administrateur, journal `tools\agent\agent.log`).
- Pour libérer COM4 avant mpremote ou `tools\pc_test.py` : créer le fichier `tools\agent\PAUSE` (l'agent ferme le port en ~1 s), puis le **supprimer** à la fin pour que l'agent se reconnecte.
- Version console (`py -X utf8 tools\agent\agent_pc.py`) : la quitter avec `q`.
- La 1re commande mpremote après un autre programme sur COM4 échoue souvent avec `ClearCommError` : la relancer une fois.
- Météo : l'agent la télécharge (Open-Meteo, toutes les 15 min, fil à part) et l'envoie à l'ESP32 (`METEO_J` et, pour la pluie du moment, `METEO_NOW icone 0|1`). Position dans `tools\agent\reglages.json` (créé au 1er lancement, rempli par Mihaja : `ville` ou `latitude`/`longitude`) : jamais lu, jamais commité.

## Fichiers de la carte (Phase 4)

- `esp/main.py` → `:main.py` : boucle messages + dessin ~12 images/s ; erreurs ajoutées dans `:erreur.txt`.
- `esp/lib/` → `:lib/` : `lcd.py`, `hid_pc.py`, `ui.py` (scènes, mascotte, bandeaux, particules), `polices.py` (polices lissées Inter), `meteo.py` (Wi-Fi + Open-Meteo + heure, facultatif).
- `esp/assets/` → `:assets` (59 fichiers `.bin` / `.fnt` : fonds, mascotte, icônes, météo, polices) : `fs cp -r esp/assets/. :assets/`.
- `esp/lib/capteur.py` → `:lib/capteur.py` (Phase 13, capteur de la pièce). Attention : `fs cp a.py b.py :` copie à la **racine** de la carte (et `import` y trouverait ce fichier en premier) ; copier fichier par fichier vers `:lib/…`.
- `esp/secrets.py` → `:secrets.py` (facultatif, Wi-Fi 2,4 GHz + position, modèle `esp/secrets.example.py`).
- Régénérer les images et polices : `py -m pip install --user pillow numpy scipy`, mettre les `Inter-*.otf` dans `tools/assets/sources/`, puis `py tools\assets\generer_assets.py` (aperçus dans `tools/assets/apercus/`).

## Lignes série PC → ESP32 (ajouts Phase 4)

- `TEMPS annee mois jour jour_semaine h min s` : l'agent donne l'heure (à la connexion puis chaque minute).
- `EVT ACTION <commande> [arg]` : l'agent signale une commande PC exécutée (APP, LUM, VERROU, ECRAN_OFF, VEILLE, ARRET, ANNULER…) → réaction de la mascotte.
- `METEO_J jour icone max min pluie heure` : météo du jour `0` (aujourd'hui) ou `1` (demain) ; `heure` = -1 si pas de pluie.
- `ECRAN_ESP 0|1` : éteindre / rallumer l'écran de l'ESP32.
- `METEO` : relire la météo gardée (`OK orage 32/24 pluie 80% vers 15h | …`).

## Phase 7 : arrêt propre, écran noir, raccourcis

- Série PC → ESP32 : `EVT ARRET n` (compte à rebours n s ; `0` = annulé ; `-1` = Windows s'éteint maintenant), `LUM_ESP 5..100` (luminosité choisie dans l'app ; l'agent la garde dans `tools\agent\preferences.json` et la renvoie à chaque connexion).
- L'ESP32 démarre écran noir (rétroéclairage 0) et reste noir tant que le PC ne parle pas et que l'heure est inconnue, ou après un arrêt annoncé. Plus de flash gris quand le port USB du portable éteint coupe / remet le courant.
- Agent : `ECRAN_OFF` / `ECRAN_ON` / `ECRAN_BASCULE` = « écran noir » (fenêtre noire sur chaque écran + luminosité 0 + Windows empêché de dormir), **sans** verrouiller ni mettre en veille ; le vrai clavier / la vraie souris du PC le rallument. `VEILLE` = verrou + écran coupé (seule veille possible : S0 moderne). `TOUCHES ctrl+6` = touches envoyées par Windows (disposition du clavier respectée). `RAC nom` = raccourci.
- Raccourcis : `tools\agent\raccourcis.json` (créés depuis l'app ; étapes `touches`, `texte`, `entree`, `commande` (PowerShell / cmd, en administrateur, visible ou cachée), `app`, `pause`, `action`). WebSocket : `raccourcis`, `rac_ajout {raccourci, ancien}`, `rac_retrait {nom}`.
- `raccourcis.json` et `preferences.json` ne sont pas commités.

## Phase 8 : aperçu de l'écran et widget Android

- Aperçu : l'agent capture l'écran à la demande (`mss` + `Pillow` : `py -m pip install --user mss Pillow`), JPEG envoyé en message binaire après `apercu_info`. WebSocket : `apercu {ecran, largeur, qualite}`, `pointeur {ecran, x, y, clic}` (x, y de 0 à 1). L'écran noir est exclu de la capture.
- Widget Android : `android/app/src/main/kotlin/com/mmdigitek/esp_micro/DadouWidget.kt` + `res/layout/widget_dadou.xml`, `res/xml/widget_dadou_info.xml`, `res/drawable/w_*.xml`. Il affiche les 4 premiers favoris (préférence `widget_boutons`, écrite par `lib/widget_android.dart`) et envoie `GET /widget?ligne=…` avec l'en-tête `X-Token` (même port 8765, géré par `serveur_app.py`).

Dans `app/` :
- `flutter pub get`
- `dart run flutter_launcher_icons` : régénérer les icônes Android (après `generer_icone.py`)
- `flutter analyze`
- `flutter test`
- `flutter build apk --release` (ou `--debug`) ; `flutter install` avec le téléphone branché (débogage USB)

## Phases 12 et 13 : clim York depuis le téléphone, capteur, écran

Carte **en MicroPython v1.29.0** (reflashée le 2026-11-06, variante `ESP32_GENERIC_S3-SPIRAM_OCT`). Port série MicroPython : **COM4**. COM3 = mode BOOT / firmware C++ (ne plus s'en servir). Flash : `py -m esptool --chip esp32s3 --port COM3 erase-flash`, puis `write-flash -z 0x0 bin\<binaire>` (carte en mode BOOT). Après un flash : `mip install usb-device-hid`, copier `esp/main.py`, `esp/lib/*.py`, `esp/assets`.

```
Téléphone (IR + alarmes Android) ── HTTP :8765 ──> agent PC ──USB série──> ESP32 (écran, capteur)
```

- **Clim par IR du téléphone** : `lib/clim_ir.dart` (trame York 8 octets, bit 0 de l'octet 7 = swing actif), `lib/ecrans/clim.dart` (carte « Air conditioner »), canal Android `dadou/ir` (`MainActivity.kt`, `ConsumerIrManager`). La touche power est une **bascule** : l'état « allumée ? » est supposé.
- **Minuteur, plage horaire, automatisme** : `lib/clim_plan.dart` (carte « AC timer & automation ») + `ClimPlan.kt` (objet + `ClimReceiver`, alarmes exactes, réarmées au redémarrage) via le canal `dadou/clim` (`trames`, `setOn`, `minuteur`, `annulerMinuteur`, `fenetre`, `auto`, `publier`, `etat`). Tout tourne côté Android, app fermée. Permissions : `TRANSMIT_IR`, `USE_EXACT_ALARM`, `SCHEDULE_EXACT_ALARM` (≤ 32), `RECEIVE_BOOT_COMPLETED`.
- **Liaison clim → PC → ESP32** : le téléphone appelle `GET /clim_maj?on=&mode=&temp=&reste=&auto=` (agent : `clim_maj`) ; l'agent envoie `CLIM on mode temp reste auto` à l'ESP32 (affichage, bulle « thermo »). L'automatisme lit `GET /clim_mesure` (agent : `piece_pour_app`, mesure de moins de 30 s sinon `ok:false`). Les deux routes demandent l'en-tête `X-Token`.
- **Capteur AHT20 + BMP280 (I2C)** : `esp/lib/capteur.py` (mesure toutes les 5 s, `DECALAGE_T`), ligne série ESP32 → PC `CLIMAT t10 humidité pression` (t10 = 10 × °C, pas écrite dans agent.log), valeurs `piece_t/h/p` dans l'état de l'app. **SDA = GPIO7, SCL = GPIO6** (trouvés par `tools/i2c_scan.py` le 2026-11-06 : AHT20 `0x38`, BMP280 `0x77` ; le câblage prévu en GPIO2/GPIO5 ne répondait pas). Pour retrouver les pins : `tools/i2c_scan.py`, agent en PAUSE, puis les écrire dans `capteur.py`. 3,3 V uniquement.
- **Écran retourné** : `ROT_ESP 0|180` (agent → ESP32, gardé dans `preferences.json` côté PC et `rotation.txt` sur la carte ; choix dans l'app, carte Brightness). Mode jeu : heure en haut à droite, « Session: … » dans la ligne du bas.
- **Écran / mascotte** : coin haut droit « AC 24° » et « 24.1° 58 % », ligne du bas qui alterne PC / clim / pièce, flocons (Cool), gouttes (Dry), traits d'air (Fan, Auto), sueur si la pièce ≥ 29 °C et clim éteinte, idées « It's 29°: AC on? » et « Humid air: try Dry mode? ».
- **Souris** : tolérance de tap de 8 px, curseur de sensibilité hors de la zone tactile, réponses de l'agent calculées dans un fil (`_appel`), `sys.setswitchinterval(0.002)`, ligne `[agent] souris : …` toutes les 10 s dans agent.log (messages, écart max, boucle max, SendInput max).

## Phase 14 : orientation, minuteur h/min/s, écran, historique de jeu

- **Orientation de l'écran** : `Ecran.tourner(True)` ne touche plus au MADCTL (toujours `0x60`). `afficher()` envoie le tampon à l'envers (`_retourner`, boucle `@micropython.viper`, ~12 ms par image, mesuré). Commande `ROT_ESP 0|180` (l'agent la garde dans `preferences.json`, la carte dans `rotation.txt`) ; l'état affiché par l'app est le `rot_esp` renvoyé par l'agent.
- **Minuteur en secondes** : canal `dadou/clim` `minuteur {duree, delai}` en **secondes** (`ClimPlan.minuteur`, max 24:00:00 côté app, min 1 s) ; `/clim_maj?…&reste=<secondes>&plage=<de-a|0>` ; ligne `CLIM on mode temp reste_secondes auto plage` (plage = « de-a » en minutes depuis minuit ou `0`). L'agent renvoie la ligne à chaque changement d'état et toutes les 20 s ; l'ESP32 compte à rebours seul entre-temps. App : carte « AC timer & automation », champs Hours / Minutes / Seconds, raccourcis 15 min / 30 min / 1 h / 2 h, dernière durée gardée (`plan_duree_s`), compte à rebours h:mm:ss chaque seconde. Fonctions pures dans `lib/clim_plan.dart` (tests : `test/clim_plan_test.dart`).
- **Écran, scène normale** : température et humidité de la pièce en permanence à droite de l'heure (`--°` sans mesure) ; bandeau « AC Cool 24° • 23 min • auto » (ou « AC off • 19:00-21:00 » avec une plage) qui alterne avec batterie et casque toutes les 5 s, seulement si la clim est allumée ou programmée. Calme et nuit : version discrète dans le coin. Jeu : lignes tournantes.
- **Banc de rendu** : `py -X utf8 tools\render_scenes.py` (nécessite `py -m pip install --user numpy pillow`) fait tourner `esp/lib/ui.py` sous CPython, écrit `tools/assets/apercus/scene_*.png` et signale les textes qui se chevauchent ou débordent sur la mascotte. À relancer après toute modification de `ui.py`.
- **Historique de jeu** : `tools/agent/historique.py` (par jour et par jeu : secondes, sessions, FPS min/moy/max, températures CPU/GPU moyenne et max, charge GPU, RAM ; total du jour tous jeux ; 365 jours). `stats_jeux.json` garde les clés « jeux » et « jours » de la Phase 10 et ajoute « historique » et « totaux ». Message WebSocket `{"type":"historique"}` (réponse `{aujourdhui, jours:[{date, s, jeux:[…]}]}`), calculé hors boucle réseau. App : « My games » → carte « Play history » → écran `lib/ecrans/historique_jeux.dart` (Days, By game, Charts 7 / 30 jours) ; modèle et agrégations dans `lib/historique.dart`. ESP32 : ligne `JEU_JOUR total_jour jeu_jour` (minutes) → « Today: 3h 12 • this game 1h 40 » dans la ligne tournante du mode jeu.
- **Tests** : Python `cd tools\agent` puis `py -X utf8 -m unittest test_historique` ; Dart `flutter test` (`clim_plan_test.dart`, `historique_test.dart`).
- **Copie sur la carte** : fichier par fichier (`fs cp esp/main.py :main.py`, `fs cp esp/lib/ui.py :lib/ui.py`) ; une copie groupée `fs cp a b :` dépose tout à la racine.

## Phase 14-bis : correctifs (minuteur, clim fantôme, capteur, écran)

- **Hot reload ≠ Kotlin** : un rechargement à chaud (`flutter run`, touche `r`) ne met à jour que le Dart. Après toute modification de `ClimPlan.kt` / `MainActivity.kt`, **réinstaller l'APK**. Le canal `dadou/clim` a une version (`ClimPlan.VERSION`, méthode `version`) : si la partie Android est trop ancienne, la carte « AC timer & automation » refuse de lancer le minuteur (avertissement rouge). Unité du minuteur : **secondes de bout en bout** (`minuteur {secondes, delaiSecondes}`).
- **État clim** : `ClimPlan` met `on = false`, `reste = 0` et publie tout de suite quand le minuteur expire (même si l'IR échoue) ; il republie l'état toutes les 30 s (10 s après un échec) tant qu'il y a quelque chose à dire (alarme `CODE_REPUB`) et à chaque reconnexion WebSocket de l'app. L'app lit `ClimPlan.etat` chaque seconde (`statutClim`). Agent : 90 s sans `/clim_maj` → `CLIM 0 …` vers l'ESP32 (aussi à l'arrêt de l'agent), une ligne `[agent] clim : …` par changement dans agent.log. ESP32 : état clim effacé après 120 s sans ligne `CLIM`.
- **Capteur** : `capteur.py` retente l'initialisation toutes les 10 s, réinitialise le bus après 3 échecs de suite, ne lève jamais d'exception, ne renvoie jamais une mesure de plus de 60 s. Sans mesure : « --° » sur l'ESP32, « Room: -- °C · -- % » dans l'app. agent.log : `[agent] capteur : mesures reçues …` / `plus de mesure depuis 30 s`. Test : `py -X utf8 tools\test_capteur.py` (faux bus I2C). Diagnostic câblage : `adc_survey` (tension de chaque GPIO avec pull-down) — un fil SCL/SDA branché est tiré à ~3,0 V par le module.
- **Scène normale** : le bloc température / humidité est collé à l'heure réelle (largeur de `f_heure`), 12 px de marge avant le bord droit de la carte (`CARTE_DROITE = 185`), police la plus grande qui tient. `tools/render_scenes.py` contient les scénarios pire cas (00:00, 100 %) et contrôle la marge.
- **Tests** : `cd tools\agent` puis `py -X utf8 -m unittest test_clim_agent test_historique` ; Dart : `minuteur_canal_test.dart`, `statut_clim_test.dart`.

## Phase 15 : plage horaire, service de fond, capteur à chaud, bouton BOOT

Détails et résultats de test : `docs/etat_code_phase15.md`.

- **Heures fixes** : `ClimPlan.armerHeureFixe` = `setAlarmClock` (plage 103/104, minuteur 101/102), réarmement avant l'IR, à chaque ouverture de l'app, au boot, à la mise à jour, au changement d'heure ou de fuseau. Calculs purs dans `Horaire.kt` (tests : `cd app\android` puis `gradlew :app:testDebugUnitTest`). Choisir une heure active la plage.
- **Service** : `ClimService.kt` (`specialUse`, verrou de veille partiel) tourne tant que `ClimPlan.actif` : automatisme 60 s, publication 30 s, notification (canal « AC control », boutons Turn off / Cancel timer / Pause auto 30 min → `ClimReceiver`). `ClimPlan.VERSION = 3`. État unique : préférences `clim_plan`, l'app relit `ClimPlan.etat`.
- **HyperOS tue le service au balayage** (`SwipeUpClean`) ; les alarmes survivent. Alarme de garde 107, repoussée tant que le service vit : relance en moins de 2 min. Débogage : `adb logcat -s ClimPlan:I`, `adb shell dumpsys activity exit-info com.mmdigitek.esp_micro`, journal dans la carte Background.
- **Carte Background** : `lib/ecrans/clim_fond.dart`, canal `fond` / `ouvrirReglage`.
- **Capteur** : pins réelles **SDA=7 / SCL=6**. `capteur.py` : modules indépendants, 3 échecs → reset complet, scan 10 s. Série : `CLIMAT t10 h p` (h = -1 sans AHT20, p = 0 sans BMP280) ou `CLIMAT ERR absent|i2c|aberrant`. `/clim_mesure` : `{ok:false, absent:true, raison}`.
- **Bouton BOOT** : `esp/lib/bouton.py`. Court = capteurs réinitialisés. Long 3 s = `machine.reset()` **au relâchement** (GPIO0 à 0 au reset = risque de mode flash). `redemarre.txt` + ligne `REPRISE` vers l'agent pour un retour immédiat.
- **Écran noir après reset avec agent en PAUSE** : normal (heure inconnue, PC muet).
- **Agent** : CPU par `GetSystemTimes` (`psutil.cpu_times` a planté 4 fois). `installer_demarrage.ps1` (administrateur) ajoute la relance chaque minute si l'agent est mort. Le relancer : `schtasks /End` puis `/Run` sur « ESP32 Telecommande Agent ».
- **APK release** : `android/app/proguard-rules.pro` garde le constructeur Room (sinon plantage au démarrage). Toujours lancer le release une fois après l'avoir construit : l'APK debug ne passe pas par R8.
- **Copie carte** : après chaque `fs cp`, comparer `sha256sum` ; une copie ratée laisse `main.py` et `lib/` désaccordés.

## Règles

1. Appliquer **exactement** les documents de `docs\`.
2. Toujours faire le test à blanc des blocs « avant » (vérifier que le code actuel correspond au bloc « avant » avant de le remplacer).
3. Ne jamais lire, modifier ni commiter `..\firmware`, `..\app` ni `..\docs` (autre projet).
4. Les secrets vont dans `esp/secrets.py` : jamais lu, jamais commité.
5. En fin de phase : commit + push.
6. Demander avant toute commande destructive (suppression, reset Git, force push, effacement de la flash).
