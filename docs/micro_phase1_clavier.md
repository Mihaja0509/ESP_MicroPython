# Micro — Phase 1 : l'ESP32 devient clavier, souris et télécommande multimédia du PC

- Date : 2026-11-01
- Statut : à appliquer
- Étape : « Télécommande PC » — étape 1 (test du mode clavier/souris USB)
- Basée sur : docs/etat_code.md (fin de Phase 0 : esp/main.py et esp/lib/lcd.py)

## Pourquoi cette phase d'abord

Tout le projet repose sur une question : MicroPython 1.29 sait-il faire passer la carte pour un clavier + souris sur ton PC ? Ce mode a eu un bug sur cette puce dans les versions 1.26 et 1.27. On le teste avant de construire le reste (programme sur le PC, app Flutter, mascotte animée).

## Ce que contient la phase

- La carte, branchée sur le PC, apparaît comme **clavier + souris + télécommande multimédia**, tout en gardant son port série (COM4) pour les mises à jour.
- Un script PC (`tools/pc_test.py`) envoie des ordres à la carte par le câble USB :
  - `KEY win+l`, `KEY ctrl+c`, `KEY alt+tab`, `KEY f5`… (raccourcis clavier)
  - `TEXT bonjour` (tape du texte)
  - `VOL+`, `VOL-`, `MUTE`, `PLAY`, `NEXT`, `PREV`, `LUM+`, `LUM-`
  - `MOUSE 100 0` (déplace la souris), `CLIC`, `CLICD` (clic droit), `MOLETTE -3`
- L'écran de la carte affiche l'état USB et la dernière commande reçue.

## Partie 1 — Nouveaux fichiers

### 1.1 `esp/lib/hid_pc.py`

```python
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
```

### 1.2 `tools/pc_test.py`

```python
#!/usr/bin/env python3
"""Envoie des commandes de test à l'ESP32 (clavier / souris / multimédia).

Utilisation :
  py -X utf8 tools\\pc_test.py COM4                commandes tapées une par une
  py -X utf8 tools\\pc_test.py COM4 --cmd "VOL+"   une seule commande
"""
import argparse
import sys
import time

import serial

AIDE = """Commandes :
  PING                  test de connexion
  KEY win+l             raccourci (ctrl, shift, alt, win + lettre, chiffre, f1..f12,
                        enter, esc, tab, space, up/down/left/right, delete, home, end…)
  TEXT bonjour          tape du texte (disposition QWERTY US)
  VOL+  VOL-  MUTE  PLAY  NEXT  PREV  LUM+  LUM-
  MOUSE 100 -50         déplace la souris (x, y)
  CLIC  CLICD           clic gauche / clic droit
  MOLETTE -3            défilement (négatif = vers le bas)
  q                     quitter"""


def ouvrir(port):
    try:
        ser = serial.Serial(port, 115200, timeout=0.1)
    except serial.SerialException as e:
        sys.exit(f"Impossible d'ouvrir {port} : {e}\n(mpremote est peut-être encore connecté)")
    time.sleep(0.5)
    ser.reset_input_buffer()
    return ser


def envoyer(ser, commande, attente=3.0):
    ser.write((commande.strip() + "\n").encode())
    ser.flush()
    fin = time.time() + attente
    while time.time() < fin:
        ligne = ser.readline().decode(errors="ignore").strip()
        if ligne.startswith(("OK", "ERR", "PONG")):
            print("  ->", ligne)
            return ligne
    print("  -> pas de réponse")
    return None


def main():
    parser = argparse.ArgumentParser(description="Test clavier/souris de l'ESP32")
    parser.add_argument("port", help="port série de l'ESP32, ex. COM4")
    parser.add_argument("--cmd", help="envoie une seule commande puis quitte")
    args = parser.parse_args()

    ser = ouvrir(args.port)
    if args.cmd:
        envoyer(ser, args.cmd)
        return
    print(AIDE)
    while True:
        try:
            commande = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if commande.lower() == "q":
            break
        if commande:
            envoyer(ser, commande)


if __name__ == "__main__":
    main()
```

## Partie 2 — Fichier remplacé en entier

### 2.1 `esp/main.py`

```python
# Phase 1 : l'ESP32 devient clavier + souris + multimédia du PC.
# Les ordres arrivent par le port série USB, une ligne par commande.
import select
import sys
import time

import lcd
from hid_pc import MEDIA, PC

ecran = lcd.Ecran(paysage=True)
pc = PC()
etat_usb = "connexion..."
derniere = "-"
nb = 0


def dessiner():
    f = ecran.fb
    f.fill(lcd.NOIR)
    ecran.texte("Telecommande PC", 10, 8, lcd.CYAN, 2)
    couleur_usb = lcd.VERT if etat_usb == "pret" else lcd.ORANGE
    ecran.texte("USB : " + etat_usb, 10, 40, couleur_usb, 2)
    ecran.texte("Derniere commande :", 10, 76, lcd.GRIS, 1)
    ecran.texte(derniere[:19], 10, 92, lcd.BLANC, 2)
    ecran.texte("Commandes : %d" % nb, 10, 130, lcd.ORANGE, 1)
    ecran.texte("tools/pc_test.py sur le PC", 10, 150, lcd.GRIS, 1)
    ecran.afficher()


dessiner()
etat_usb = "pret" if pc.demarrer() else "pas reconnu"
dessiner()

entree = select.poll()
entree.register(sys.stdin, select.POLLIN)
tampon = ""


def lire_ligne():
    """Renvoie une ligne complète reçue sur le port série, ou None."""
    global tampon
    while entree.poll(0):
        c = sys.stdin.read(1)
        if c in ("\n", "\r"):
            if tampon:
                ligne = tampon
                tampon = ""
                return ligne
        else:
            tampon += c
    return None


def executer(ligne):
    mots = ligne.split(" ", 1)
    cmd = mots[0].upper()
    arg = mots[1] if len(mots) > 1 else ""
    if cmd == "PING":
        return "PONG"
    if etat_usb != "pret" and not pc.is_open():
        return "ERR USB pas reconnu par le PC"
    if cmd == "KEY":
        return "OK" if pc.raccourci(arg) else "ERR touche inconnue : " + arg
    if cmd == "TEXT":
        ignores = pc.taper(arg)
        return "OK" if ignores == 0 else "OK (%d caracteres ignores)" % ignores
    if cmd in MEDIA:
        pc.media(cmd)
        return "OK"
    if cmd == "MOUSE":
        try:
            dx, dy = [int(v) for v in arg.split()]
        except ValueError:
            return "ERR utilise : MOUSE dx dy"
        pc.souris(dx, dy)
        return "OK"
    if cmd == "CLIC":
        pc.clic(1)
        return "OK"
    if cmd == "CLICD":
        pc.clic(2)
        return "OK"
    if cmd == "MOLETTE":
        try:
            pc.souris(molette=int(arg))
        except ValueError:
            return "ERR utilise : MOLETTE n"
        return "OK"
    return "ERR commande inconnue : " + cmd


while True:
    ligne = lire_ligne()
    if ligne:
        reponse = executer(ligne.strip())
        print(reponse)
        nb += 1
        derniere = ligne.strip()
        if pc.is_open():
            etat_usb = "pret"
        dessiner()
    time.sleep_ms(10)
```

## Partie 3 — Modifications « avant → après »

Aucune.

## Bibliothèque à installer sur la carte

`py -m mpremote connect COM4 mip install usb-device-hid` (installe aussi `usb-device`, dans `/lib` de la carte).

## Comprendre le code

- `hid_pc.py` décrit au PC un appareil avec trois « rapports » : clavier, souris et multimédia. Un rapport, c'est un petit paquet d'octets. Par exemple `(1, 0x08, 0, 0x0F, …)` veut dire « clavier : touche Windows + L enfoncées ». On envoie ensuite un rapport vide pour relâcher.
- `builtin_driver=True` garde le port série (COM4) en plus du clavier et de la souris. C'est par lui que le PC envoie les ordres, et qu'on met à jour la carte.
- `main.py` lit le port série sans bloquer (`select.poll`), exécute chaque ligne, répond `OK` ou `ERR …`, puis redessine l'écran.
- `TEXT` suit la disposition QWERTY US : sur un PC réglé en AZERTY, les lettres seront mélangées. On ajoutera ta disposition plus tard si besoin.

## Liste de contrôle

| Contrôle | Attendu |
|---|---|
| `mip install usb-device-hid` | réussi ; `/lib/usb/device/hid.py` présent sur la carte |
| Fichiers créés / remplacés | esp/lib/hid_pc.py, tools/pc_test.py, esp/main.py |
| `py -m py_compile tools\pc_test.py` | aucune erreur |
| Copie sur la carte | main.py et lib/hid_pc.py copiés, puis reset |
| Port série après reset | toujours visible avec `mpremote devs` (noter le port) |
| `pc_test.py <port> --cmd PING` | « PONG » |
| `pc_test.py <port> --cmd "VOL+"` | « OK » |
| Windows voit le clavier | PowerShell `Get-PnpDevice -PresentOnly -Class Keyboard,Mouse,HIDClass` liste un appareil HID récent (noter les noms) |

## Tests sur l'appareil (par Mihaja)

Lance `py -X utf8 tools\pc_test.py COM4` dans le dossier Micro (ferme d'abord toute autre connexion au port). Tape les commandes une par une :

1. Écran de la carte : « USB : pret » en vert.
2. `VOL+` puis `VOL-` → le volume de Windows bouge (l'icône de volume apparaît).
3. `MUTE` → son coupé, puis `MUTE` → son revenu.
4. `LUM+` puis `LUM-` → la luminosité de l'écran du portable change (peut ne pas marcher, note-le).
5. `MOUSE 200 0` → la souris part à droite. `MOLETTE -5` → la page défile.
6. Ouvre le Bloc-notes, clique dedans, puis `TEXT Hello Mihaja 123` → le texte s'écrit (lettres mélangées = ton clavier est en AZERTY, note-le).
7. `KEY win+d` → le bureau s'affiche. `KEY win+l` → le PC se verrouille.
8. Envoie-moi : ce qui marche, ce qui ne marche pas, et ce que dit la ligne « USB : … » de l'écran.
