# État du code — Micro

Mis à jour : 2026-11-01 (fin de Phase 0)

## Arborescence

Fichiers suivis par Git (sans `bin/`, `build/`, `.dart_tool/`, `.idea/`, `local.properties`) :

```
Micro/
├── .claude/
│   └── settings.json
├── app/
│   ├── android/
│   │   ├── app/
│   │   │   ├── src/
│   │   │   │   ├── debug/
│   │   │   │   │   └── AndroidManifest.xml
│   │   │   │   ├── main/
│   │   │   │   │   ├── kotlin/
│   │   │   │   │   │   └── com/
│   │   │   │   │   │       └── mmdigitek/
│   │   │   │   │   │           └── esp_micro/
│   │   │   │   │   │               └── MainActivity.kt
│   │   │   │   │   ├── res/
│   │   │   │   │   │   ├── drawable/
│   │   │   │   │   │   │   └── launch_background.xml
│   │   │   │   │   │   ├── drawable-v21/
│   │   │   │   │   │   │   └── launch_background.xml
│   │   │   │   │   │   ├── mipmap-hdpi/
│   │   │   │   │   │   │   └── ic_launcher.png
│   │   │   │   │   │   ├── mipmap-mdpi/
│   │   │   │   │   │   │   └── ic_launcher.png
│   │   │   │   │   │   ├── mipmap-xhdpi/
│   │   │   │   │   │   │   └── ic_launcher.png
│   │   │   │   │   │   ├── mipmap-xxhdpi/
│   │   │   │   │   │   │   └── ic_launcher.png
│   │   │   │   │   │   ├── mipmap-xxxhdpi/
│   │   │   │   │   │   │   └── ic_launcher.png
│   │   │   │   │   │   ├── values/
│   │   │   │   │   │   │   └── styles.xml
│   │   │   │   │   │   └── values-night/
│   │   │   │   │   │       └── styles.xml
│   │   │   │   │   └── AndroidManifest.xml
│   │   │   │   └── profile/
│   │   │   │       └── AndroidManifest.xml
│   │   │   └── build.gradle.kts
│   │   ├── gradle/
│   │   │   └── wrapper/
│   │   │       └── gradle-wrapper.properties
│   │   ├── .gitignore
│   │   ├── build.gradle.kts
│   │   ├── gradle.properties
│   │   └── settings.gradle.kts
│   ├── lib/
│   │   └── main.dart
│   ├── test/
│   │   └── widget_test.dart
│   ├── .gitignore
│   ├── .metadata
│   ├── analysis_options.yaml
│   ├── pubspec.lock
│   ├── pubspec.yaml
│   └── README.md
├── docs/
│   ├── etat_code.md
│   ├── etat_du_projet.md
│   └── micro_phase0.md
├── esp/
│   ├── lib/
│   │   └── lcd.py
│   └── main.py
├── .gitignore
└── CLAUDE.md
```

`bin/` (ignoré par Git) contient `ESP32_GENERIC_S3-SPIRAM_OCT-20260824-v1.29.0.bin`.

## Versions

| Outil | Version |
|---|---|
| esptool | 5.6.0 |
| mpremote | 1.29.0 |
| MicroPython sur la carte | v1.29.0 (2026-08-24), ESP32_GENERIC_S3-SPIRAM_OCT |
| Flutter | 3.47.2 (stable), Dart 3.13.2 |

## Port série

- Avant le flash (programme C++ / bootloader) : COM3 (USB 303a:1001).
- Après le flash MicroPython : **COM4** (USB 303a:4001). Retrouver le port avec `py -m mpremote devs`.

## REPL (étape 4)

Commande : `py -m mpremote connect COM4 exec "import sys, gc; print(sys.implementation); print(gc.mem_free())"`

```
(name='micropython', version=(1, 29, 0, ''), _machine='Generic ESP32S3 module with Octal-SPIRAM with ESP32-S3', _mpy=11014, _build='ESP32_GENERIC_S3-SPIRAM_OCT', _thread='GIL')
8320064
```

PSRAM utilisée : 8 320 064 octets libres (> 1 000 000).

## Fichiers sur la carte

```
ls :
         139 boot.py
           0 lib/
        1632 main.py
ls :lib
        4071 lcd.py
```

## Console après reset

`py -m mpremote connect COM4 reset`, puis lecture de COM4 à 115200 pendant 5 s : **aucune sortie** (main.py n'affiche rien ; aucune erreur).

Vérification complémentaire : Ctrl-C envoyé ensuite → le programme était bien dans la boucle :

```
Traceback (most recent call last):
  File "main.py", line 55, in <module>
KeyboardInterrupt: 
MicroPython v1.29.0 on 2026-08-24; Generic ESP32S3 module with Octal-SPIRAM with ESP32-S3
Type "help()" for more information.
>>> 
```

puis Ctrl-D (`MPY: soft reboot`) : la démo a redémarré.

## esp/main.py

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

## esp/lib/lcd.py

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

## app/pubspec.yaml

```yaml
name: esp_micro
description: "A new Flutter project."
# The following line prevents the package from being accidentally published to
# pub.dev using `flutter pub publish`. This is preferred for private packages.
publish_to: 'none' # Remove this line if you wish to publish to pub.dev

# The following defines the version and build number for your application.
# A version number is three numbers separated by dots, like 1.2.43
# followed by an optional build number separated by a +.
# Both the version and the builder number may be overridden in flutter
# build by specifying --build-name and --build-number, respectively.
# In Android, build-name is used as versionName while build-number used as versionCode.
# Read more about Android versioning at https://developer.android.com/studio/publish/versioning
# In iOS, build-name is used as CFBundleShortVersionString while build-number is used as CFBundleVersion.
# Read more about iOS versioning at
# https://developer.apple.com/library/archive/documentation/General/Reference/InfoPlistKeyReference/Articles/CoreFoundationKeys.html
# In Windows, build-name is used as the major, minor, and patch parts
# of the product and file versions while build-number is used as the build suffix.
version: 1.0.0+1

environment:
  sdk: ^3.13.2

# Dependencies specify other packages that your package needs in order to work.
# To automatically upgrade your package dependencies to the latest versions
# consider running `flutter pub upgrade --major-versions`. Alternatively,
# dependencies can be manually updated by changing the version numbers below to
# the latest version available on pub.dev. To see which dependencies have newer
# versions available, run `flutter pub outdated`.
dependencies:
  flutter:
    sdk: flutter

  # The following adds the Cupertino Icons font to your application.
  # Use with the CupertinoIcons class for iOS style icons.
  cupertino_icons: ^1.0.8

dev_dependencies:
  flutter_test:
    sdk: flutter

  # The "flutter_lints" package below contains a set of recommended lints to
  # encourage good coding practices. The lint set provided by the package is
  # activated in the `analysis_options.yaml` file located at the root of your
  # package. See that file for information about deactivating specific lint
  # rules and activating additional ones.
  flutter_lints: ^6.0.0

# For information on the generic Dart part of this file, see the
# following page: https://dart.dev/tools/pub/pubspec

# The following section is specific to Flutter packages.
flutter:

  # The following line ensures that the Material Icons font is
  # included with your application, so that you can use the icons in
  # the material Icons class.
  uses-material-design: true

  # To add assets to your application, add an assets section, like this:
  # assets:
  #   - images/a_dot_burr.jpeg
  #   - images/a_dot_ham.jpeg

  # An image asset can refer to one or more resolution-specific "variants", see
  # https://flutter.dev/to/resolution-aware-images

  # For details regarding adding assets from package dependencies, see
  # https://flutter.dev/to/asset-from-package

  # To add custom fonts to your application, add a fonts section here,
  # in this "flutter" section. Each entry in this list should have a
  # "family" key with the font family name, and a "fonts" key with a
  # list giving the asset and other descriptors for the font. For
  # example:
  # fonts:
  #   - family: Schyler
  #     fonts:
  #       - asset: fonts/Schyler-Regular.ttf
  #       - asset: fonts/Schyler-Italic.ttf
  #         style: italic
  #   - family: Trajan Pro
  #     fonts:
  #       - asset: fonts/TrajanPro.ttf
  #       - asset: fonts/TrajanPro_Bold.ttf
  #         weight: 700
  #
  # For details regarding fonts from package dependencies,
  # see https://flutter.dev/to/font-from-package
```
