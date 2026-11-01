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
