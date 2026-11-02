# Télécommande PC avec écran animé (Phase 7).
# - Les ordres et les données arrivent du PC par le port série USB (une ligne par message).
# - L'ESP32 joue le rôle de clavier + souris + touches multimédia (hid_pc.py).
# - L'écran est dessiné par ui.py environ 12 fois par seconde.
# - Phase 7 : compte à rebours quand le PC s'éteint (EVT ARRET n), écran complètement noir
#   quand le PC est éteint (et au démarrage de la carte tant que le PC ne parle pas),
#   luminosité réglable depuis l'app (LUM_ESP n).
import select
import sys
import time

import machine

import lcd
from hid_pc import MEDIA, PC
from meteo import Meteo
from ui import Interface

try:
    import secrets as reglages  # /secrets.py sur la carte : Wi-Fi + position (jamais dans Git)
except ImportError:
    reglages = None

ecran = lcd.Ecran(paysage=True)
ui = Interface(ecran)
pc = PC()

# Valeurs envoyées par le programme PC (agent_pc.py) ; -1 = inconnu
stat = {"cpu": -1, "ram": -1, "vol": -1, "bat": -1, "chg": 0}
gpu = {"temp": -1, "charge": -1, "vram": -1}
perf = {"cpu_temp": -1, "fps": -1}
evt = {"casque": "", "manette": 0, "verrou": 0, "jeu": ""}
etat = {"connecte": False, "stat": stat, "gpu": gpu, "perf": perf, "evt": evt, "meteo": [],
        "eteint": True,        # écran noir : PC éteint (ou carte qui vient de démarrer sans PC)
        "arret_fin": None,     # ticks de la fin du compte à rebours d'arrêt (None = pas d'arrêt)
        "arret_total": 60000,  # durée du compte à rebours (ms), pour la barre
        "lum": 85}             # luminosité choisie dans l'app (5 à 100)

ATTENTE_ABSENT = 12000     # sans données depuis 12 s = PC éteint / en veille / agent arrêté
RETOUR_PC = 5000           # il faut 5 s de données sans coupure pour dire « le PC est revenu »
                           # (en veille moderne, Windows se réveille quelques secondes de temps en temps)
IMAGE_MS = 80              # une image toutes les 80 ms (≈ 12 images / s)
derniere_donnee = time.ticks_add(time.ticks_ms(), -ATTENTE_ABSENT)
debut_flux = None          # début du flux de données en cours
ecran_allume = True
luminosite_actuelle = -1


def heure_connue():
    return time.localtime()[0] >= 2025  # avant le 1er « TEMPS » du PC, l'horloge est en 2000


def majuscule(texte):
    """Première lettre en majuscule (str.capitalize n'existe pas en MicroPython)."""
    return texte[:1].upper() + texte[1:] if texte else texte


def noter_erreur(e):
    """Garde la trace d'une erreur dans erreur.txt (sur la carte) sans arrêter le programme."""
    try:
        with open("erreur.txt", "a") as f:
            sys.print_exception(e, f)
    except OSError:
        pass


# Premier dessin tout de suite (écran noir tant que le PC ne parle pas), puis clavier/souris
ui.dessiner(etat, time.ticks_ms())
meteo = Meteo(reglages)  # lance la connexion Wi-Fi (sans attendre)
try:
    usb_ok = pc.demarrer()
except Exception as e:  # le PC n'était peut-être pas prêt (démarrage de Windows)
    noter_erreur(e)
    usb_ok = False

entree = select.poll()
entree.register(sys.stdin, select.POLLIN)
tampon = ""


def lire_ligne():
    """Renvoie une ligne complète reçue sur le port série, ou None.
    Les caractères bizarres (parasites au démarrage du PC) sont ignorés."""
    global tampon
    while entree.poll(0):
        try:
            c = sys.stdin.read(1)
        except UnicodeError:  # octets invalides (parasites au démarrage / à l'arrêt du PC)
            tampon = ""
            continue
        if not c:
            break
        if c in ("\n", "\r"):
            if tampon:
                ligne = tampon
                tampon = ""
                return ligne
        elif " " <= c <= "~" or ord(c) > 159:
            tampon += c
            if len(tampon) > 300:
                tampon = ""
    return None


TOUCHES_LISIBLES = {"win": "Win", "ctrl": "Ctrl", "alt": "Alt", "shift": "Maj"}


def joli_raccourci(texte):
    morceaux = []
    for m in texte.split("+"):
        m = m.strip().lower()
        morceaux.append(TOUCHES_LISIBLES.get(m, m.upper() if len(m) == 1 else majuscule(m)))
    return " + ".join(morceaux)


REACTIONS_MEDIA = {
    "VOL+": ("son", "Volume +"), "VOL-": ("son", "Volume -"), "MUTE": ("muet", "Muet"),
    "PLAY": ("musique", "Lecture / pause"), "NEXT": ("musique", "Suivant"),
    "PREV": ("musique", "Précédent"), "LUM+": ("soleil", "Luminosité +"),
    "LUM-": ("soleil", "Luminosité -"),
}


def reaction_action(arg):
    """Réaction de la mascotte à une commande exécutée par le programme PC (EVT ACTION …)."""
    mots = arg.split(" ", 1)
    nom = mots[0].upper()
    reste = mots[1].strip() if len(mots) > 1 else ""
    if nom == "APP":
        ui.reagir("appli", majuscule(reste) or "Application")
    elif nom == "RAC":
        ui.reagir("clavier", majuscule(reste) or "Raccourci")
    elif nom == "TOUCHES":
        ui.reagir("clavier", joli_raccourci(reste) if reste else "Touches")
    elif nom in ("LUM", "LUM+", "LUM-"):
        ui.reagir("soleil", "Luminosité %s %%" % reste if reste else "Luminosité")
    elif nom == "VERROU":
        ui.reagir("cadenas", "Verrouillage")
    elif nom == "ECRAN_OFF":
        ui.reagir("lune", "Écran du PC noir")
    elif nom == "ECRAN_ON":
        ui.reagir("soleil", "Écran du PC rallumé")
    elif nom == "VEILLE":
        ui.reagir("lune", "Mise en veille")
    elif nom in ("ARRET", "ANNULER"):
        pass  # le compte à rebours (EVT ARRET n) s'en charge
    elif nom == "TEXTE":
        ui.reagir("clavier", "Texte envoyé")
    elif nom == "VOL":
        ui.reagir("son", "Volume %s %%" % reste)
    else:
        ui.reagir("appli", arg[:24])


def executer(ligne):
    global derniere_donnee, ecran_allume, debut_flux
    mots = ligne.split(" ", 1)
    cmd = mots[0].upper()
    arg = mots[1] if len(mots) > 1 else ""
    if cmd == "PING":
        return "PONG"
    if cmd == "METEO":
        if etat["meteo"]:
            return "OK " + " | ".join("%s %d/%d pluie %d%% vers %sh" % (
                j["icone"], j["tmax"], j["tmin"], j["pluie"], j["heure_pluie"]) for j in etat["meteo"])
        return "ERR pas encore de meteo (" + (meteo.probleme or "attente") + ")"
    if cmd == "METEO_J":
        # météo envoyée par le programme PC : METEO_J jour icone max min pluie heure
        try:
            p = arg.split()
            i = int(p[0])
            heure = int(p[5])
            jour = {"icone": p[1], "tmax": int(p[2]), "tmin": int(p[3]), "pluie": int(p[4]),
                    "heure_pluie": heure if heure >= 0 else None}
        except (ValueError, IndexError):
            return "ERR utilise : METEO_J jour icone max min pluie heure"
        liste = list(etat["meteo"])
        while len(liste) <= i:
            liste.append(jour)
        liste[i] = jour
        etat["meteo"] = liste
        return "OK"
    # --- données du programme PC -------------------------------------------
    if cmd in ("STAT", "GPU", "PERF", "EVT", "TEMPS", "METEO_J"):
        maintenant = time.ticks_ms()
        if not etat["connecte"]:
            if debut_flux is None or time.ticks_diff(maintenant, derniere_donnee) > 3000:
                debut_flux = maintenant
            if time.ticks_diff(maintenant, debut_flux) >= RETOUR_PC:
                etat["connecte"] = True
        derniere_donnee = maintenant
    if cmd == "STAT":
        try:
            v = [int(x) for x in arg.split()]
            stat["cpu"], stat["ram"], stat["vol"], stat["bat"], stat["chg"] = v[:5]
        except ValueError:
            return "ERR utilise : STAT cpu ram vol bat charge"
        return "OK"
    if cmd == "GPU":
        try:
            gpu["temp"], gpu["charge"], gpu["vram"] = [int(x) for x in arg.split()][:3]
        except ValueError:
            return "ERR utilise : GPU temp charge vram"
        return "OK"
    if cmd == "PERF":
        try:
            perf["cpu_temp"], perf["fps"] = [int(x) for x in arg.split()][:2]
        except ValueError:
            return "ERR utilise : PERF temp_cpu fps"
        return "OK"
    if cmd == "TEMPS":
        try:
            a, mo, j, js, h, mi, s = [int(x) for x in arg.split()][:7]
            machine.RTC().datetime((a, mo, j, js, h, mi, s, 0))
        except (ValueError, OSError):
            return "ERR utilise : TEMPS annee mois jour jour_semaine h min s"
        return "OK"
    if cmd == "EVT":
        morceaux = arg.split(" ", 1)
        typ = morceaux[0].upper()
        val = morceaux[1].strip() if len(morceaux) > 1 else ""
        if typ == "CASQUE":
            ancien = evt["casque"]
            evt["casque"] = "" if val in ("", "-") else val
            if evt["casque"] and not ancien:
                ui.reagir("son", "Casque connecté")
            elif ancien and not evt["casque"]:
                ui.reagir("son", "Casque retiré")
        elif typ == "MANETTE":
            nouveau = 1 if val == "1" else 0
            if nouveau and not evt["manette"]:
                ui.reagir("manette", "Manette connectée")
            evt["manette"] = nouveau
        elif typ == "VERROU":
            evt["verrou"] = 1 if val == "1" else 0
        elif typ == "JEU":
            evt["jeu"] = "" if val in ("", "-") else val
        elif typ == "ACTION":
            reaction_action(val)
        elif typ == "PIN":
            ui.reagir("coucou", "Code : %s" % val, duree=60000)
        elif typ == "ARRET":
            # EVT ARRET 60 : le PC s'éteint dans 60 s ; 0 : arrêt annulé ; -1 : il s'éteint maintenant
            try:
                n = int(val)
            except ValueError:
                return "ERR utilise : EVT ARRET secondes"
            maintenant = time.ticks_ms()
            if n == 0:
                if etat["arret_fin"] is not None:
                    ui.reagir("power", "Arrêt annulé")
                etat["arret_fin"] = None
            elif n > 0:
                etat["arret_total"] = n * 1000
                etat["arret_fin"] = time.ticks_add(maintenant, n * 1000)
            else:
                etat["arret_fin"] = maintenant
        elif typ == "APP":
            if val == "1":
                ui.reagir("coucou", "Téléphone connecté")
            else:
                ui.reagir("power", "Téléphone déconnecté")
        else:
            return "ERR evenement inconnu : " + typ
        return "OK"
    # --- écran de l'ESP32 ----------------------------------------------------
    if cmd == "ECRAN_ESP":
        ecran_allume = arg.strip() != "0"
        if not ecran_allume:
            ecran.luminosite(0)
        return "OK"
    if cmd == "LUM_ESP":
        try:
            etat["lum"] = max(5, min(100, int(arg)))
        except ValueError:
            return "ERR utilise : LUM_ESP 5..100"
        return "OK"
    # --- clavier / souris / multimédia ----------------------------------------
    if not pc.is_open():
        return "ERR USB pas reconnu par le PC"
    if cmd == "KEY":
        if not pc.raccourci(arg):
            return "ERR touche inconnue : " + arg
        ui.reagir("clavier", joli_raccourci(arg))
        return "OK"
    if cmd == "TEXT":
        ignores = pc.taper(arg)
        ui.reagir("clavier", "Texte envoyé")
        return "OK" if ignores == 0 else "OK (%d caracteres ignores)" % ignores
    if cmd in MEDIA:
        pc.media(cmd)
        ui.reagir(*REACTIONS_MEDIA[cmd])
        return "OK"
    if cmd == "MOUSE":
        try:
            dx, dy = [int(v) for v in arg.split()]
        except ValueError:
            return "ERR utilise : MOUSE dx dy"
        pc.souris(dx, dy)
        ui.reagir("souris", "Souris", bandeau=False)
        return "OK"
    if cmd == "CLIC":
        pc.clic(1)
        ui.reagir("souris", "Clic", bandeau=False)
        return "OK"
    if cmd == "CLICD":
        pc.clic(2)
        ui.reagir("souris", "Clic droit", bandeau=False)
        return "OK"
    if cmd == "MOLETTE":
        try:
            pc.souris(molette=int(arg))
        except ValueError:
            return "ERR utilise : MOLETTE n"
        ui.reagir("souris", "Défilement", bandeau=False)
        return "OK"
    return "ERR commande inconnue : " + cmd


prochaine_image = time.ticks_ms()
while True:
    try:
        # 1. tous les messages en attente (au plus 30 d'un coup)
        for _ in range(30):
            ligne = lire_ligne()
            if ligne is None:
                break
            print(executer(ligne.strip()))
        maintenant = time.ticks_ms()
        if etat["connecte"] and time.ticks_diff(maintenant, derniere_donnee) > ATTENTE_ABSENT:
            etat["connecte"] = False
        # écran noir : le PC s'est éteint après un arrêt annoncé, ou la carte vient de démarrer
        # sans heure (PC éteint : son port USB coupe et remet le courant de temps en temps)
        if etat["connecte"]:
            etat["eteint"] = False
            # l'arrêt était annoncé mais le PC tourne encore 90 s après (arrêt bloqué par une app,
            # ou annulé depuis Windows) : on revient à l'écran normal
            if etat["arret_fin"] is not None and time.ticks_diff(maintenant, etat["arret_fin"]) > 90000:
                etat["arret_fin"] = None
        elif etat["arret_fin"] is not None or not heure_connue():
            etat["eteint"] = True
            etat["arret_fin"] = None
        # météo : seulement quand le PC n'est pas utilisé (le téléchargement bloque 1 à 3 s)
        if (not etat["connecte"] or evt["verrou"]) and meteo.a_mettre_a_jour(maintenant):
            if meteo.mettre_a_jour(maintenant):
                etat["meteo"] = meteo.jours
        # 2. une nouvelle image si c'est l'heure
        if time.ticks_diff(maintenant, prochaine_image) >= 0:
            prochaine_image = time.ticks_add(maintenant, IMAGE_MS)
            if ecran_allume:
                ui.dessiner(etat, maintenant)
                voulue = ui.luminosite_voulue(maintenant)
                if voulue != luminosite_actuelle:
                    luminosite_actuelle = voulue
                    ecran.luminosite(voulue)
            else:
                luminosite_actuelle = -1
    except Exception as e:  # une erreur ne doit jamais arrêter la télécommande
        noter_erreur(e)
        print("ERR interne : %s" % e)
        time.sleep_ms(200)
    time.sleep_ms(2)
