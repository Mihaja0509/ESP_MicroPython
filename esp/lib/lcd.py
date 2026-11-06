# Pilote minimal de l'écran ST7789 (Waveshare ESP32-S3-LCD-1.47, 172 x 320).
# On dessine dans une image en mémoire (framebuf), puis afficher() l'envoie
# d'un coup à l'écran.
import struct
import time

import framebuf
import micropython
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


@micropython.viper
def _retourner(src: ptr16, dst: ptr16, n: int):
    """Copie n pixels RGB565 de src vers dst dans l'ordre inverse (rotation de 180°), ~2 ms."""
    i = 0
    j = n - 1
    while i < n:
        dst[j] = src[i]
        i += 1
        j -= 1


class Ecran:
    def __init__(self, paysage=True, demi_tour=False):
        self.spi = SPI(1, baudrate=40_000_000, polarity=0, phase=0,
                       sck=Pin(40), mosi=Pin(45))
        self.cs = Pin(42, Pin.OUT, value=1)
        self.dc = Pin(41, Pin.OUT, value=0)
        self.rst = Pin(39, Pin.OUT, value=1)
        self.bl = PWM(Pin(48), freq=1000)
        self.paysage = paysage
        self.demi_tour = bool(demi_tour)  # Phase 13 : image retournée de 180° (carte posée à l'envers)
        if paysage:
            self.largeur, self.hauteur = HAUTEUR_PANNEAU, LARGEUR_PANNEAU
        else:
            self.largeur, self.hauteur = LARGEUR_PANNEAU, HAUTEUR_PANNEAU
        self.tampon = bytearray(self.largeur * self.hauteur * 2)
        self.tampon_retourne = bytearray(len(self.tampon)) if self.demi_tour else None
        self.fb = framebuf.FrameBuffer(self.tampon, self.largeur, self.hauteur,
                                       framebuf.RGB565)
        self._lettre = bytearray(8)
        self._lettre_fb = framebuf.FrameBuffer(self._lettre, 8, 8, framebuf.MONO_HLSB)
        self._demarrer()
        # Phase 7 : rétroéclairage éteint au démarrage. Il ne s'allume qu'après la 1re
        # vraie image (plus de flash gris quand la carte redémarre, PC éteint).
        self.luminosite(0)

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
        self._madctl()                   # orientation
        self._cmd(0x21)                  # inversion (écrans IPS)
        self._cmd(0x13)                  # mode normal
        self._cmd(0x29)                  # écran allumé
        time.sleep_ms(50)

    def _madctl(self):
        # Phase 14 : l'orientation du contrôleur ne change plus. Le retournement de 180° se fait
        # sur le tampon, dans afficher() (le MADCTL 0xA0 / 0xC0 n'avait aucun effet visible).
        madctl = 0x60 if self.paysage else 0x00
        if BGR:
            madctl |= 0x08
        self._cmd(0x36, bytes([madctl]))

    def tourner(self, demi_tour):
        """Retourne l'image de 180° : les pixels du tampon sont envoyés dans l'ordre inverse
        (les marges de 34 px de l'écran sont symétriques)."""
        self.demi_tour = bool(demi_tour)
        if self.demi_tour and self.tampon_retourne is None:
            self.tampon_retourne = bytearray(len(self.tampon))

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
        if self.demi_tour:
            _retourner(self.tampon, self.tampon_retourne, self.largeur * self.hauteur)
            self._cmd(0x2C, self.tampon_retourne)
        else:
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
