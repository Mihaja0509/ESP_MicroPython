# Micro — Phase 0 : MicroPython + écran

- Date : 2026-11-01
- Statut : à appliquer
- Projet : Micro (séparé de firmware/ et app/), dépôt https://github.com/Mihaja0509/ESP_MicroPython.git
- Matériel : Waveshare ESP32-S3-LCD-1.47 seule (aucun module branché)

## Ce que contient la phase

- MicroPython est installé sur la carte (à la place du programme C++ de la clim, qui reste sur GitHub et pourra être remis avec `pio run -t upload`).
- Un pilote d'écran en MicroPython (`lcd.py`) et une démo :
  - titre « ESP32 Maison » en grand, trois barres rouge / vert / bleu pour vérifier les couleurs ;
  - un compteur de secondes et la mémoire libre, mis à jour chaque seconde ;
  - la LED RGB de la carte change de couleur ;
  - le bouton BOOT change la luminosité de l'écran.
- Un squelette d'app Flutter dans `app/` (non modifié pour l'instant).

## Brochage de la carte (Waveshare)

| Fonction | GPIO |
|---|---|
| Écran ST7789 172×320 : SCLK / MOSI / CS / DC / RST / rétroéclairage | 40 / 45 / 42 / 41 / 39 / 48 |
| LED RGB (WS2812) | 38 |
| Bouton BOOT | 0 |

## Structure

```
D:\FlutterProject\Esp32Maison\Micro\      (dépôt ESP_MicroPython)
  esp\            code copié sur la carte
    main.py
    lib\lcd.py
  app\            app Flutter (squelette)
  docs\
  bin\            firmware MicroPython téléchargé (ignoré par Git)
  CLAUDE.md
  .claude\settings.json
  .gitignore
```

## Partie 1 — Nouveaux fichiers

### 1.1 `esp/lib/lcd.py`

```python
# Pilote minimal de l'écran ST7789 (Waveshare ESP32-S3-LCD-1.47, 172 x 320).
# On dessine dans une image en mémoire (framebuf), puis afficher() l'envoie
# d'un coup à l'écran.
import struct
import time

import framebuf
from machine import PWM, SPI, Pin

LARGEUR_PANNEAU = 172
HAUTEUR_PANNEAU = 320
DECALAGE = 34   # le contrôleur fait 240 de large, l'écran 172 est centré : (240 - 172) / 2
BGR = False     # mets True si le rouge et le bleu sont inversés à l'écran


def couleur(r, g, b):
    """Couleur 0-255 -> RGB565, octets inversés comme l'attend l'écran."""
    c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return ((c & 0xFF) << 8) | (c >> 8)


NOIR = couleur(0, 0, 0)
BLANC = couleur(255, 255, 255)
ROUGE = couleur(255, 0, 0)
VERT = couleur(0, 255, 0)
BLEU = couleur(0, 0, 255)
GRIS = couleur(90, 90, 90)
CYAN = couleur(0, 200, 255)
ORANGE = couleur(255, 140, 0)


class Ecran:
    def __init__(self, paysage=True):
        self.spi = SPI(1, baudrate=40_000_000, polarity=0, phase=0,
                       sck=Pin(40), mosi=Pin(45))
        self.cs = Pin(42, Pin.OUT, value=1)
        self.dc = Pin(41, Pin.OUT, value=0)
        self.rst = Pin(39, Pin.OUT, value=1)
        self.bl = PWM(Pin(48), freq=1000)
        self.paysage = paysage
        if paysage:
            self.largeur, self.hauteur = HAUTEUR_PANNEAU, LARGEUR_PANNEAU
        else:
            self.largeur, self.hauteur = LARGEUR_PANNEAU, HAUTEUR_PANNEAU
        self.tampon = bytearray(self.largeur * self.hauteur * 2)
        self.fb = framebuf.FrameBuffer(self.tampon, self.largeur, self.hauteur,
                                       framebuf.RGB565)
        self._lettre = bytearray(8)
        self._lettre_fb = framebuf.FrameBuffer(self._lettre, 8, 8, framebuf.MONO_HLSB)
        self._demarrer()
        self.luminosite(80)

    # --- bas niveau -------------------------------------------------------
    def _cmd(self, commande, donnees=None):
        self.cs(0)
        self.dc(0)
        self.spi.write(bytes([commande]))
        if donnees is not None:
            self.dc(1)
            self.spi.write(donnees)
        self.cs(1)

    def _demarrer(self):
        self.rst(0)
        time.sleep_ms(50)
        self.rst(1)
        time.sleep_ms(150)
        self._cmd(0x01)                  # reset logiciel
        time.sleep_ms(150)
        self._cmd(0x11)                  # sortie du mode veille
        time.sleep_ms(120)
        self._cmd(0x3A, b"\x55")         # 16 bits par pixel
        madctl = 0x60 if self.paysage else 0x00
        if BGR:
            madctl |= 0x08
        self._cmd(0x36, bytes([madctl]))  # orientation
        self._cmd(0x21)                  # inversion (écrans IPS)
        self._cmd(0x13)                  # mode normal
        self._cmd(0x29)                  # écran allumé
        time.sleep_ms(50)

    # --- usage -------------------------------------------------------------
    def luminosite(self, pourcent):
        pourcent = max(0, min(100, pourcent))
        self.bl.duty_u16(pourcent * 65535 // 100)

    def afficher(self):
        if self.paysage:
            x0, x1 = 0, self.largeur - 1
            y0, y1 = DECALAGE, DECALAGE + self.hauteur - 1
        else:
            x0, x1 = DECALAGE, DECALAGE + self.largeur - 1
            y0, y1 = 0, self.hauteur - 1
        self._cmd(0x2A, struct.pack(">HH", x0, x1))
        self._cmd(0x2B, struct.pack(">HH", y0, y1))
        self._cmd(0x2C, self.tampon)

    def texte(self, s, x, y, c, taille=1):
        """Texte avec la police 8x8 intégrée, agrandie `taille` fois."""
        if taille == 1:
            self.fb.text(s, x, y, c)
            return
        for car in s:
            self._lettre_fb.fill(0)
            self._lettre_fb.text(car, 0, 0, 1)
            for ligne in range(8):
                for col in range(8):
                    if self._lettre_fb.pixel(col, ligne):
                        self.fb.fill_rect(x + col * taille, y + ligne * taille,
                                          taille, taille, c)
            x += 8 * taille
```

### 1.2 `esp/main.py`

```python
# Démo Phase 0 : écran, LED RGB et bouton BOOT.
import gc
import time

from machine import Pin
from neopixel import NeoPixel

import lcd

ecran = lcd.Ecran(paysage=True)
led = NeoPixel(Pin(38), 1)
bouton = Pin(0, Pin.IN, Pin.PULL_UP)

COULEURS_LED = [(40, 0, 0), (0, 40, 0), (0, 0, 40), (30, 20, 0), (0, 0, 0)]
NIVEAUX = [20, 50, 80, 100]

niveau = 2
depart = time.ticks_ms()
dernier_appui = 0
i = 0

while True:
    # Bouton BOOT : luminosité suivante
    if bouton.value() == 0 and time.ticks_diff(time.ticks_ms(), dernier_appui) > 400:
        dernier_appui = time.ticks_ms()
        niveau = (niveau + 1) % len(NIVEAUX)
        ecran.luminosite(NIVEAUX[niveau])

    secondes = time.ticks_diff(time.ticks_ms(), depart) // 1000
    gc.collect()

    f = ecran.fb
    f.fill(lcd.NOIR)
    ecran.texte("ESP32 Maison", 10, 8, lcd.CYAN, 3)
    f.fill_rect(10, 44, 96, 30, lcd.ROUGE)
    f.fill_rect(112, 44, 96, 30, lcd.VERT)
    f.fill_rect(214, 44, 96, 30, lcd.BLEU)
    ecran.texte("R", 52, 51, lcd.BLANC, 2)
    ecran.texte("V", 154, 51, lcd.NOIR, 2)
    ecran.texte("B", 256, 51, lcd.BLANC, 2)
    ecran.texte("Depuis %d s" % secondes, 10, 90, lcd.BLANC, 2)
    ecran.texte("RAM libre : %d Ko" % (gc.mem_free() // 1024), 10, 120, lcd.ORANGE, 1)
    ecran.texte("Luminosite : %d %%" % NIVEAUX[niveau], 10, 135, lcd.ORANGE, 1)
    ecran.texte("BOOT = luminosite", 10, 155, lcd.GRIS, 1)
    ecran.afficher()

    led[0] = COULEURS_LED[i % len(COULEURS_LED)]
    led.write()
    i += 1

    # attend 1 s en surveillant le bouton
    for _ in range(20):
        if bouton.value() == 0:
            break
        time.sleep_ms(50)
```

## Comprendre le code

- `lcd.py` parle à l'écran par le bus SPI : `_cmd()` envoie un code de commande (`dc` à 0), puis ses données (`dc` à 1).
- On dessine tout dans `self.tampon` (320 × 172 pixels × 2 octets = 110 Ko, dans la PSRAM), grâce à `framebuf` intégré à MicroPython : `fill`, `fill_rect`, `text`, `line`… Ensuite, `afficher()` envoie l'image entière d'un coup. C'est comme un `CustomPainter` Flutter qui peint sur un canvas avant l'affichage.
- `texte(..., taille=3)` agrandit la petite police 8×8 en dessinant chaque point comme un carré.
- `main.py` tourne en boucle infinie, comme `loop()` en C++.

## Liste de contrôle

| Contrôle | Attendu |
|---|---|
| Outils | esptool et mpremote installés (pip --user), versions notées |
| Firmware | dernière version stable ESP32_GENERIC_S3, variante SPIRAM_OCT, dans `bin\` |
| Flash | erase + write à l'adresse 0x0 : réussis |
| REPL | `mpremote` répond ; `import sys; sys.implementation` montre MicroPython et le port |
| PSRAM | `import gc; gc.mem_free()` > 1 000 000 (la PSRAM de 8 Mo est utilisée) |
| Copie | `lib/lcd.py` et `main.py` présents sur la carte (`mpremote fs ls` et `fs ls lib`) |
| Démarrage | après reset, aucune erreur sur la console série pendant 5 s |
| `flutter analyze` (app) | aucun problème |
| Git | commit « Phase 0 : mise en place » poussé |

## Tests sur l'appareil (par Mihaja)

1. Regarde l'écran : tu dois voir « ESP32 Maison » en bleu clair, trois barres rouge / vert / bleu, et « Depuis … s » qui avance chaque seconde.
2. Si le rouge et le bleu sont inversés (barre « R » bleue) → dis-le-moi (on passera `BGR = True`).
3. Si l'image est décalée (bande de pixels parasites sur un bord) ou si l'écran reste noir → photo de l'écran.
4. La LED sous l'écran doit changer de couleur chaque seconde.
5. Appuie sur BOOT : la luminosité doit changer (20 / 50 / 80 / 100 %).
