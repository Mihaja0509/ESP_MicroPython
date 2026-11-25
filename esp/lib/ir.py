# Émetteur IR de la clim York (même trame que app/lib/clim_ir.dart, déjà validée avec le téléphone).
# LED IR sur GPIO3 (RMT, porteuse 38 kHz). Durées en microsecondes.
import esp32
from machine import Pin

PIN_IR = 3
FREQ = 38000
MARQUE, ZERO, UN = 412, 350, 905
ENTETE_M, ENTETE_E = 4500, 2500
SILENCE, MARQUE_FIN = 19950, 4550
MODES = {"cool": 0x2, "dry": 0x1, "fan": 0x4, "auto": 0xA}
VENTS = {"auto": 0x1, "low": 0x8, "med": 0x4, "high": 0x2}


def trame(mode="cool", vent="auto", temp=24, swing=False, power=False):
    b = [0x16, (VENTS[vent] << 4) | MODES[mode], 0, 0, 0, 0, ((temp // 10) << 4) | (temp % 10)]
    bas = (1 if swing else 0) | (8 if power else 0)
    somme = bas
    for x in b:
        somme += (x & 0xF) + (x >> 4)
    b.append(((somme & 0xF) << 4) | bas)
    return b


def durees(octets):
    d = [ENTETE_M, ENTETE_E]
    for x in octets:
        for k in range(8):
            d.append(MARQUE)
            d.append(UN if (x >> k) & 1 else ZERO)
    d += [MARQUE, SILENCE, MARQUE_FIN]
    return d


def commande(mots):
    """mots = [mode, temp, vent, swing 0|1, power 0|1] (tous facultatifs sauf mode et temp).
    Envoie la trame. Renvoie None si OK, sinon le texte de l'erreur."""
    try:
        mode = mots[0].lower()
        temp = int(mots[1])
        vent = mots[2].lower() if len(mots) > 2 else "auto"
        swing = len(mots) > 3 and mots[3] == "1"
        power = len(mots) > 4 and mots[4] == "1"
    except (IndexError, ValueError):
        return "utilise : IR mode temp [vent swing power]"
    if mode not in MODES or vent not in VENTS or not 16 <= temp <= 30:
        return "mode cool|dry|fan|auto, vent auto|low|med|high, temp 16-30"
    try:
        envoyer(trame(mode, vent, temp, swing, power))
    except Exception as e:
        return "IR : %s" % e
    return None


_rmt = None


def envoyer(octets):
    """Émet la trame (RMT 1 µs/tick, porteuse 38 kHz, rapport cyclique 33 %)."""
    global _rmt
    if _rmt is None:
        _rmt = esp32.RMT(0, pin=Pin(PIN_IR), clock_div=80, tx_carrier=(FREQ, 33, 1))
    _rmt.write_pulses(durees(octets), 1)
