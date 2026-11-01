# Clavier + souris + touches multimédia USB pour le PC.
# Utilise la bibliothèque officielle micropython-lib « usb-device-hid ».
import time

import usb.device
from usb.device.hid import HIDInterface

# Description de l'appareil envoyée au PC :
# rapport 1 = clavier, rapport 2 = souris, rapport 3 = multimédia.
_DESCRIPTEUR = bytes((
    # --- Clavier (rapport 1) ---
    0x05, 0x01, 0x09, 0x06, 0xA1, 0x01, 0x85, 0x01,
    0x05, 0x07, 0x19, 0xE0, 0x29, 0xE7, 0x15, 0x00, 0x25, 0x01,
    0x75, 0x01, 0x95, 0x08, 0x81, 0x02,             # 8 touches de modification
    0x95, 0x01, 0x75, 0x08, 0x81, 0x01,             # octet réservé
    0x95, 0x06, 0x75, 0x08, 0x15, 0x00, 0x25, 0x65,
    0x05, 0x07, 0x19, 0x00, 0x29, 0x65, 0x81, 0x00, # 6 touches
    0xC0,
    # --- Souris (rapport 2) ---
    0x05, 0x01, 0x09, 0x02, 0xA1, 0x01, 0x85, 0x02,
    0x09, 0x01, 0xA1, 0x00,
    0x05, 0x09, 0x19, 0x01, 0x29, 0x03, 0x15, 0x00, 0x25, 0x01,
    0x95, 0x03, 0x75, 0x01, 0x81, 0x02,             # 3 boutons
    0x95, 0x01, 0x75, 0x05, 0x81, 0x01,             # bourrage
    0x05, 0x01, 0x09, 0x30, 0x09, 0x31, 0x09, 0x38,
    0x15, 0x81, 0x25, 0x7F, 0x75, 0x08, 0x95, 0x03, 0x81, 0x06,  # X, Y, molette
    0xC0, 0xC0,
    # --- Multimédia (rapport 3) ---
    0x05, 0x0C, 0x09, 0x01, 0xA1, 0x01, 0x85, 0x03,
    0x15, 0x00, 0x26, 0xFF, 0x03, 0x19, 0x00, 0x2A, 0xFF, 0x03,
    0x75, 0x10, 0x95, 0x01, 0x81, 0x00,
    0xC0,
))

# Touches de modification
MODS = {"ctrl": 0x01, "shift": 0x02, "alt": 0x04, "win": 0x08}

# Touches spéciales (codes USB HID)
SPECIALES = {
    "enter": 0x28, "entree": 0x28, "esc": 0x29, "echap": 0x29,
    "backspace": 0x2A, "tab": 0x2B, "space": 0x2C, "espace": 0x2C,
    "printscreen": 0x46, "home": 0x4A, "pageup": 0x4B, "delete": 0x4C,
    "suppr": 0x4C, "end": 0x4D, "pagedown": 0x4E,
    "right": 0x4F, "left": 0x50, "down": 0x51, "up": 0x52,
}
for _n in range(1, 13):
    SPECIALES["f%d" % _n] = 0x3A + _n - 1

# Touches multimédia (codes « Consumer »)
MEDIA = {
    "VOL+": 0xE9, "VOL-": 0xEA, "MUTE": 0xE2, "PLAY": 0xCD,
    "NEXT": 0xB5, "PREV": 0xB6, "LUM+": 0x6F, "LUM-": 0x70,
}

# Caractères tapables (disposition QWERTY US) : caractère -> (shift, code)
_SANS_SHIFT = "-=[]\\;'`,./"
_CODES_SANS_SHIFT = (0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38)
_AVEC_SHIFT = "_+{}|:\"~<>?"
_CHIFFRES_SHIFT = "!@#$%^&*()"


def _caractere(c):
    if "a" <= c <= "z":
        return False, 0x04 + ord(c) - ord("a")
    if "A" <= c <= "Z":
        return True, 0x04 + ord(c) - ord("A")
    if "1" <= c <= "9":
        return False, 0x1E + ord(c) - ord("1")
    if c == "0":
        return False, 0x27
    if c == " ":
        return False, 0x2C
    if c in _SANS_SHIFT:
        return False, _CODES_SANS_SHIFT[_SANS_SHIFT.index(c)]
    if c in _AVEC_SHIFT:
        return True, _CODES_SANS_SHIFT[_AVEC_SHIFT.index(c)]
    if c in _CHIFFRES_SHIFT:
        return True, 0x1E + _CHIFFRES_SHIFT.index(c)
    return None


class PC(HIDInterface):
    def __init__(self):
        super().__init__(_DESCRIPTEUR, interface_str="ESP32 Maison PC")

    def demarrer(self, attente_ms=5000):
        """Déclare clavier + souris au PC (le port série reste actif)."""
        usb.device.get().init(self, builtin_driver=True)
        debut = time.ticks_ms()
        while not self.is_open():
            if time.ticks_diff(time.ticks_ms(), debut) > attente_ms:
                return False
            time.sleep_ms(100)
        return True

    def _envoyer(self, rapport):
        # Toujours un nouvel objet bytes : le tampon ne doit pas changer
        # pendant que l'USB l'envoie.
        for _ in range(20):
            if self.send_report(bytes(rapport)):
                return True
            time.sleep_ms(5)
        return False

    # --- Clavier -------------------------------------------------------------
    def _touches(self, mods, code):
        self._envoyer((1, mods, 0, code, 0, 0, 0, 0, 0))
        time.sleep_ms(15)
        self._envoyer((1, 0, 0, 0, 0, 0, 0, 0, 0))
        time.sleep_ms(15)

    def raccourci(self, texte):
        """Ex. 'win+l', 'ctrl+shift+esc', 'f5', 'a'. Renvoie False si inconnu."""
        mods = 0
        code = 0
        for morceau in texte.lower().split("+"):
            morceau = morceau.strip()
            if morceau in MODS:
                mods |= MODS[morceau]
            elif morceau in SPECIALES:
                code = SPECIALES[morceau]
            elif len(morceau) == 1 and _caractere(morceau) is not None:
                code = _caractere(morceau)[1]
            else:
                return False
        self._touches(mods, code)
        return True

    def taper(self, texte):
        """Tape un texte (QWERTY US). Renvoie le nombre de caractères ignorés."""
        ignores = 0
        for c in texte:
            r = _caractere(c)
            if r is None:
                ignores += 1
                continue
            shift, code = r
            self._touches(MODS["shift"] if shift else 0, code)
        return ignores

    # --- Multimédia ----------------------------------------------------------
    def media(self, nom):
        usage = MEDIA.get(nom)
        if usage is None:
            return False
        self._envoyer((3, usage & 0xFF, usage >> 8))
        time.sleep_ms(30)
        self._envoyer((3, 0, 0))
        return True

    # --- Souris --------------------------------------------------------------
    def souris(self, dx=0, dy=0, boutons=0, molette=0):
        # Les grands déplacements sont découpés en pas de 127 au maximum.
        while True:
            px = max(-127, min(127, dx))
            py = max(-127, min(127, dy))
            self._envoyer((2, boutons, px & 0xFF, py & 0xFF, molette & 0xFF))
            dx -= px
            dy -= py
            molette = 0
            if dx == 0 and dy == 0:
                break
            time.sleep_ms(8)

    def clic(self, bouton=1):
        self.souris(boutons=bouton)
        time.sleep_ms(20)
        self.souris(boutons=0)
