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
