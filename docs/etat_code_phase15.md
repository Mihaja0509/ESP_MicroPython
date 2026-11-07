# État du code — Phase 15 (plage horaire, service de fond, capteur à chaud, bouton BOOT)

Mis à jour : 2026-11-07 · téléphone de test : Xiaomi 25113PN0EC, Android 17 (SDK 37), HyperOS 4.0, targetSdk 36.

## Commits

| Étape | Commit | Contenu |
|---|---|---|
| 15.1 | `2648587` | `setAlarmClock`, réarmement systématique, `Horaire.kt` + tests, journal des décisions |
| 15.2 | `120ce9f` | `ClimService`, notification, carte Background |
| 15.3 | `57fce39` | `capteur.py` tolérant au débranchement, `CLIMAT ERR` |
| 15.4 | `3f6272c` | bouton BOOT, CPU sans psutil, chien de garde de l'agent |
| 15.2-bis | `b923a2e` | alarme de garde du service, choisir une heure active la plage |
| 15.5 | `19b2bd2` | règle R8 (APK release), documentation |
| 15.6 | `1bf8799` | l'automatisme affiche pourquoi il attend ; réactiver Auto lève la priorité manuelle ; `AutoRegles` + tests |
| 15.7 | message « Phase 15.7 » | détection du capteur par 3 sondes au lieu de `i2c.scan()` : l'écran se rallume avec SCL bloquée |

Sur le release, `Log.i` n'apparaît pas dans logcat sur ce téléphone : lire le journal de la carte Background, la notification (`dumpsys notification --noredact`) et `agent.log`.

## Causes

- **Plage horaire** : `clim_plan.xml` contenait `{"actif":false,"de":1350,"a":1410}`. Les heures étaient gardées mais l'interrupteur était éteint : aucune alarme armée. Choisir une heure active maintenant la plage. Facteur aggravant vu dans `dumpsys activity exit-info` : kills HyperOS (`LockScreenClean`, `SwipeUpClean`) et un `FORCE STOP` (qui annule les alarmes) ; d'où le réarmement à chaque ouverture de l'app.
- **Capteur** : il répond sur SDA=7 / SCL=6, rien sur 2 / 5 (aucun fil détecté). Ces pins n'ont pas été modifiées. Le journal contenait 164 lignes « AHT20 absent » alternant avec des mesures. Vu une fois en direct : SCL flottante (pull-down = 0) et SDA haute, scan vide, puis retour seul : faux contact probable sur le fil SCL, à confirmer. L'ancien code bloquait aussi l'AHT20 quand le BMP280 échouait et ne réinitialisait pas les modules.
- **Valeurs fausses après rebranchement** : le BMP280 renvoyait ses registres de repos (0x80000), soit 23,8 °C et 668 hPa, plausibles mais faux. Rejetés.
- **Écran resté noir, capteur absent** : SCL lue à 0 même avec pull-up (2026-11-07). `i2c.scan()` bloquait alors 5,6 s (112 adresses × 50 ms) toutes les 10 s : il ne restait que 4,4 s de données sans trou, et `RETOUR_PC` en demande 5. `capteur.py` sonde maintenant 3 adresses (150 ms mesurées). Vérifié sur la carte, SCL toujours bloquée : `MODE normal <- eteint (5 s)`. La cause de SCL à 0 n'est pas identifiée (câblage ou module).
- **Agent mort** : 4 plantages natifs sur 4 dans `psutil.cpu_times` (0xC0000005) ; rien ne le relançait, et l'écran restait noir. CPU lu par `GetSystemTimes`.
- **APK release** : plantait à chaque démarrage (`NoSuchMethodException: WorkDatabase_Impl.<init>`), R8 retirait le constructeur. Règle dans `android/app/proguard-rules.pro`.

## Alarmes et service

- `setAlarmClock` : plage ON/OFF (103/104), minuteur (101/102). Effet visible : icône réveil dans la barre d'état.
- Prochaine occurrence réarmée avant l'IR, à chaque ouverture de l'app, au boot, à la mise à jour, au changement d'heure ou de fuseau.
- `ClimService` (`specialUse` : pas la limite de 6 h de `dataSync`, permis au boot) : tic de 10 s, automatisme 60 s, publication 30 s (10 s après échec). `PARTIAL_WAKE_LOCK` tenu tant qu'il tourne (sans lui le Handler s'arrête écran éteint), coût batterie assumé : téléphone branché conseillé.
- **HyperOS tue le service au balayage**, sans rappel ni redémarrage (`SwipeUpClean`). Les alarmes survivent. L'alarme 107 (gardien), repoussée toutes les 30 s à +2 min, ne sonne que si le service est mort et le relance. Mesuré : 1 min 42. Entre-temps, ni notification ni automatisme.
- Bascule power : `allumer` / `eteindre` ne font rien si l'état supposé est déjà le bon (`ON skipped…` dans le journal). Un état supposé faux reste possible : interrupteur « AC is ON/OFF (assumed) ».

## Capteur

Période 5 s, nouvel essai à 2 s après un échec, 3 échecs de suite : bus recréé, soft reset 0xBA, 20 ms, 0xBE 08 00, config + ctrl_meas du BMP280, nouveau scan. Module absent : sonde des 3 adresses toutes les 10 s, jamais `i2c.scan()`. Bornes : t -20..80, h 0..100, p 300..1100. `CLIMAT t10 h p` (h = -1 sans AHT20, p = 0 sans BMP280) ; `CLIMAT ERR absent|i2c|aberrant` au changement puis toutes les 10 s.

## Bouton BOOT

`esp/lib/bouton.py`, lu dans la boucle, anti-rebond 50 ms, armé seulement après un premier relâchement. Court : `Capteur.reinitialiser`, « Sensors reset » puis « Sensor OK » / « No sensor ». Long (3 s) : « Restarting… », `machine.reset()` **au relâchement** (GPIO0 à 0 pendant le reset risquerait le mode flash). Écart assumé par rapport à la demande. `redemarre.txt` marque ce redémarrage : écran allumé tout de suite, scène normale, `REPRISE` répété vers l'agent (sinon il prend le retour USB pour un réveil de Windows et reste muet).

## Vérifié

| Test | Résultat |
|---|---|
| Plage réelle, écran verrouillé (APK debug) | 103 à 10:40:00, 104 à 10:42:00, IR envoyés, réarmés pour demain |
| Minuteur + auto, écran éteint (debug) | 101 à l'heure, IR envoyé, PC prévenu |
| Minuteur, app balayée, process mort (debug) | `am_proc_start … broadcast`, IR envoyé, service relancé |
| Auto seul, app balayée (debug) | gardien : service revenu en 1 min 42 |
| Boutons Pause / Cancel / Turn off (debug) | les trois OK |
| Débranché / rebranché, bouton BOOT, mode flash (COM3 303a:1001) | OK à l'écran, confirmé par Mihaja |
| APK release | démarre, sans plantage |

## Non vérifié

- Effet réel des trames sur la clim : seul l'envoi est journalisé.
- APK release en marche : minuteur, service et notification testés en debug seulement (Mihaja utilisait le téléphone).
- Plage horaire, automatisme déclenchant une vraie mise en marche (seuils relevés à 40 °C pendant les tests).
- Redémarrage du téléphone (boot) ; chien de garde de l'agent (installateur à relancer en administrateur).

## Tests

`py -X utf8 tools\test_capteur.py` ; `py -X utf8 tools\test_bouton.py` ; `cd tools\agent` puis `py -X utf8 -m unittest test_clim_agent test_historique` ; `flutter test` ; `cd app\android` puis `gradlew :app:testDebugUnitTest` (`HoraireTest`).
