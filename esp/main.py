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
# Valeurs envoyées par le programme PC (agent_pc.py)
stat = {"cpu": -1, "ram": -1, "vol": -1, "bat": -1, "chg": 0}
evt = {"casque": "", "manette": 0, "verrou": 0, "jeu": ""}
gpu = {"temp": -1, "charge": -1, "vram": -1}
perf = {"cpu_temp": -1, "fps": -1}


def dessiner():
    f = ecran.fb
    f.fill(lcd.NOIR)
    ecran.texte("Telecommande PC", 10, 8, lcd.CYAN, 2)
    couleur_usb = lcd.VERT if etat_usb == "pret" else lcd.ORANGE
    ecran.texte("USB : " + etat_usb, 10, 40, couleur_usb, 2)
    if evt["jeu"]:
        ecran.texte("JEU : " + evt["jeu"][:34], 10, 64, lcd.VERT, 1)
    ecran.texte("GPU %dC %d%%  CPU %dC  FPS %d" % (gpu["temp"], gpu["charge"],
                                                   perf["cpu_temp"], perf["fps"]),
                10, 78, lcd.VERT if evt["jeu"] else lcd.GRIS, 1)
    ecran.texte(derniere[:19], 10, 92, lcd.BLANC, 2)
    ecran.texte("CPU %d%%  RAM %d%%  Vol %d%%" % (stat["cpu"], stat["ram"], stat["vol"]),
                10, 118, lcd.ORANGE, 1)
    ecran.texte("Batterie %d%%%s" % (stat["bat"], " (en charge)" if stat["chg"] else ""),
                10, 132, lcd.ORANGE, 1)
    ecran.texte("Casque : " + (evt["casque"][:30] or "non"), 10, 146, lcd.CYAN, 1)
    ecran.texte("Manette : %s   Verrou : %s" % ("oui" if evt["manette"] else "non",
                                                "oui" if evt["verrou"] else "non"),
                10, 160, lcd.CYAN, 1)
    ecran.afficher()


dessiner()
def noter_erreur(e):
    """Garde la trace d'une erreur dans erreur.txt (sur la carte) sans arrêter le programme."""
    try:
        with open("erreur.txt", "a") as f:
            sys.print_exception(e, f)
    except OSError:
        pass


try:
    etat_usb = "pret" if pc.demarrer() else "pas reconnu"
except Exception as e:  # le PC n'était peut-être pas prêt (démarrage de Windows)
    noter_erreur(e)
    etat_usb = "pas reconnu"
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
    if cmd == "STAT":
        try:
            v = [int(x) for x in arg.split()]
            stat["cpu"], stat["ram"], stat["vol"], stat["bat"], stat["chg"] = v[:5]
        except ValueError:
            return "ERR utilise : STAT cpu ram vol bat charge"
        return "OK"
    if cmd == "PERF":
        try:
            perf["cpu_temp"], perf["fps"] = [int(x) for x in arg.split()][:2]
        except ValueError:
            return "ERR utilise : PERF temp_cpu fps"
        return "OK"
    if cmd == "GPU":
        try:
            gpu["temp"], gpu["charge"], gpu["vram"] = [int(x) for x in arg.split()][:3]
        except ValueError:
            return "ERR utilise : GPU temp charge vram"
        return "OK"
    if cmd == "EVT":
        morceaux = arg.split(" ", 1)
        typ = morceaux[0].upper()
        val = morceaux[1].strip() if len(morceaux) > 1 else ""
        if typ == "CASQUE":
            evt["casque"] = "" if val in ("", "-") else val
        elif typ == "MANETTE":
            evt["manette"] = 1 if val == "1" else 0
        elif typ == "VERROU":
            evt["verrou"] = 1 if val == "1" else 0
        elif typ == "JEU":
            evt["jeu"] = "" if val in ("", "-") else val
        else:
            return "ERR evenement inconnu : " + typ
        return "OK"
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
    try:
        ligne = lire_ligne()
        if ligne:
            reponse = executer(ligne.strip())
            print(reponse)
            if not ligne.startswith(("STAT", "EVT", "GPU", "PERF")):
                nb += 1
                derniere = ligne.strip()
            if pc.is_open():
                etat_usb = "pret"
            dessiner()
    except Exception as e:  # une erreur ne doit jamais arrêter la télécommande
        noter_erreur(e)
        print("ERR interne : %s" % e)
    time.sleep_ms(10)
