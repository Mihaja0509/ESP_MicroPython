# Micro — MicroPython + écran

Projet séparé de `..\firmware` et `..\app` (projet clim, en pause).

- Carte : Waveshare **ESP32-S3-LCD-1.47** seule (ESP32-S3R8, 8 Mo PSRAM octal, 16 Mo flash, USB natif, écran ST7789 172×320), **sans module externe**.
- `esp/` : code MicroPython copié sur la carte (`main.py` à la racine, `lib/` dans le dossier `lib` de la carte).
- `app/` : app Dart/Flutter Android (`com.mmdigitek.esp_micro`).
- `docs/` : documents de phase et état du code (à appliquer exactement).
- `bin/` : firmware MicroPython téléchargé (ignoré par Git).
- Dépôt : https://github.com/Mihaja0509/ESP_MicroPython.git

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

Dans `app/` :
- `flutter analyze`
- `flutter build apk --debug`

## Règles

1. Appliquer **exactement** les documents de `docs\`.
2. Toujours faire le test à blanc des blocs « avant » (vérifier que le code actuel correspond au bloc « avant » avant de le remplacer).
3. Ne jamais lire, modifier ni commiter `..\firmware`, `..\app` ni `..\docs` (autre projet).
4. Les secrets vont dans `esp/secrets.py` : jamais lu, jamais commité.
5. En fin de phase : commit + push.
6. Demander avant toute commande destructive (suppression, reset Git, force push, effacement de la flash).
