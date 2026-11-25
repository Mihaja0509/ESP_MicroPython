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


_rmt = None


def envoyer(octets):
    """Émet la trame (RMT 1 µs/tick, porteuse 38 kHz, rapport cyclique 33 %)."""
    global _rmt
    if _rmt is None:
        _rmt = esp32.RMT(0, pin=Pin(PIN_IR), clock_div=80, tx_carrier=(FREQ, 33, 1))
    _rmt.write_pulses(durees(octets), 1)
