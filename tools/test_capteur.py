"""Tests de esp/lib/capteur.py sous CPython avec un faux bus I2C (Phase 14-bis) :
    py -X utf8 tools\\test_capteur.py
Vérifie : mesure normale, capteur absent au démarrage puis branché, erreurs I2C en cours de route
(le bus est réinitialisé après 3 échecs de suite), mesures périmées jamais renvoyées."""
import os
import struct
import sys
import time
import types
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Horloge:
    ms = 0


time.ticks_ms = lambda: Horloge.ms
time.ticks_diff = lambda a, b: a - b
time.ticks_add = lambda a, b: a + b
time.sleep_ms = lambda n: None


class Bus:
    present = True       # le capteur répond-il ?
    erreurs = 0          # nombre d'accès qui échouent encore (OSError)
    crees = 0            # nombre de fois où le bus a été (re)créé
    scans = 0


class FauxPin:
    def __init__(self, *a, **k):
        pass


class FauxI2C:
    def __init__(self, ident, sda=None, scl=None, freq=100000):
        Bus.crees += 1

    def _acces(self):
        if not Bus.present:
            raise OSError(19)
        if Bus.erreurs > 0:
            Bus.erreurs -= 1
            raise OSError(110)

    def scan(self):
        Bus.scans += 1
        return [0x38, 0x77] if Bus.present else []

    def readfrom(self, adr, n):
        self._acces()
        # statut calibré / pas occupé, humidité 50 %, température 25 °C
        return bytes([0x1C, 0x80, 0x00, 0x06, 0x00, 0x00, 0x00])[:n]

    def writeto(self, adr, donnees):
        self._acces()

    def writeto_mem(self, adr, mem, donnees):
        self._acces()

    def readfrom_mem(self, adr, mem, n):
        self._acces()
        if mem == 0xD0:
            return b"\x58"
        if mem == 0x88:  # calibration typique de la fiche technique du BMP280
            return struct.pack("<HhhHhhhhhhhh", 27504, 26435, -1000, 36477, -10685, 3024, 2855, 140, -7,
                               15500, -14600, 6000)
        adc_p, adc_t = 415148, 519888  # exemple de la fiche technique : 25,08 °C, 100653 Pa
        return bytes([(adc_p >> 12) & 255, (adc_p >> 4) & 255, (adc_p & 15) << 4,
                      (adc_t >> 12) & 255, (adc_t >> 4) & 255, (adc_t & 15) << 4])


machine = types.ModuleType("machine")
machine.I2C = FauxI2C
machine.Pin = FauxPin
sys.modules["machine"] = machine
sys.path.insert(0, os.path.join(RACINE, "esp", "lib"))
import capteur  # noqa: E402


def avancer(c, secondes, pas_ms=20):
    """Fait tourner la boucle comme main.py ; renvoie le nombre de nouvelles mesures."""
    n = 0
    fin = Horloge.ms + int(secondes * 1000)
    while Horloge.ms < fin:
        if c.pas(Horloge.ms):
            n += 1
        Horloge.ms += pas_ms
    return n


class TestCapteur(unittest.TestCase):
    def setUp(self):
        Horloge.ms = 100000
        Bus.present, Bus.erreurs, Bus.crees, Bus.scans = True, 0, 0, 0

    def test_mesure_normale(self):
        c = capteur.Capteur()
        self.assertTrue(c.ok)
        self.assertGreaterEqual(avancer(c, 12), 2)
        t, h, p = c.mesure()
        self.assertAlmostEqual(t, 25.0, delta=0.3)
        self.assertAlmostEqual(h, 50.0, delta=0.5)
        self.assertAlmostEqual(p, 1006.5, delta=1.0)

    def test_capteur_absent_puis_branche(self):
        Bus.present = False
        c = capteur.Capteur()
        self.assertFalse(c.ok)
        self.assertEqual(avancer(c, 25), 0)          # des essais, aucune exception, aucune mesure
        self.assertIsNone(c.mesure())
        self.assertGreaterEqual(Bus.scans, 3)        # il réessaie toutes les 10 s
        Bus.present = True                           # on rebranche le fil
        self.assertGreaterEqual(avancer(c, 20), 1)   # nouvelle initialisation puis mesures
        self.assertTrue(c.ok)
        self.assertIsNotNone(c.mesure())

    def test_erreurs_i2c_bus_reinitialise_apres_3_echecs(self):
        c = capteur.Capteur()
        avancer(c, 12)
        self.assertIsNotNone(c.mesure())
        crees = Bus.crees
        Bus.present = False                          # le fil lâche
        avancer(c, 25)                               # plus de mesure, pas d'exception
        self.assertIsNone(c.mesure())
        self.assertGreater(Bus.crees, crees)         # le bus a été recréé après 3 échecs
        Bus.present = True
        self.assertGreaterEqual(avancer(c, 25), 1)   # reprise toute seule
        self.assertIsNotNone(c.mesure())

    def test_une_erreur_isolee_ne_perd_pas_la_mesure(self):
        c = capteur.Capteur()
        avancer(c, 12)
        Bus.erreurs = 1                              # un seul accès rate
        avancer(c, 12)
        self.assertIsNotNone(c.mesure())
        self.assertTrue(c.ok)

    def test_mesure_perimee_jamais_renvoyee(self):
        c = capteur.Capteur()
        avancer(c, 12)
        self.assertIsNotNone(c.mesure())
        Horloge.ms += 61000                          # plus aucune lecture pendant 61 s
        self.assertIsNone(c.mesure())

    def test_exception_inattendue_ne_sort_pas_de_pas(self):
        c = capteur.Capteur()
        avancer(c, 12)
        c.i2c = None                                 # état cassé : AttributeError dans _pas
        for _ in range(500):
            c.pas(Horloge.ms)                        # ne doit jamais lever
            Horloge.ms += 20


if __name__ == "__main__":
    unittest.main()
