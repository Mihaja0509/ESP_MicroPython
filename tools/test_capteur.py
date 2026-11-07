"""Tests de esp/lib/capteur.py sous CPython avec un faux bus I2C (Phases 14-bis et 15) :
    py -X utf8 tools\\test_capteur.py
Vérifie : mesure normale, débranchement à chaud (« -- » en moins de 15 s), rebranchement (valeurs en
moins de 15 s), valeurs aberrantes, soft reset après 3 échecs, modules indépendants, réinitialisation."""
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
    aht = True           # l'AHT20 répond-il ?
    bmp = True           # le BMP280 répond-il ?
    erreurs = 0          # nombre d'accès qui échouent encore (OSError)
    crees = 0            # nombre de fois où le bus a été (re)créé
    scans = 0
    ecritures = []       # (adresse, octets)
    aht_octets = bytes([0x1C, 0x80, 0x00, 0x06, 0x00, 0x00, 0x00])  # 50 %, 25 °C


class FauxPin:
    def __init__(self, *a, **k):
        pass


class FauxI2C:
    def __init__(self, ident, sda=None, scl=None, freq=100000):
        Bus.crees += 1

    def _acces(self, present):
        if not present:
            raise OSError(19)
        if Bus.erreurs > 0:
            Bus.erreurs -= 1
            raise OSError(110)

    def scan(self):
        Bus.scans += 1
        return ([0x38] if Bus.aht else []) + ([0x77] if Bus.bmp else [])

    def readfrom(self, adr, n):
        self._acces(Bus.aht)
        return Bus.aht_octets[:n]

    def writeto(self, adr, donnees):
        self._acces(Bus.aht)
        Bus.ecritures.append((adr, bytes(donnees)))

    def writeto_mem(self, adr, mem, donnees):
        self._acces(Bus.bmp)
        Bus.ecritures.append((adr, bytes([mem]) + bytes(donnees)))

    def readfrom_mem(self, adr, mem, n):
        self._acces(Bus.bmp)
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


def delai_jusqua(c, condition, maxi=30):
    """Secondes avant que condition() soit vraie, en faisant tourner la boucle ; None si jamais."""
    debut = Horloge.ms
    while Horloge.ms - debut < maxi * 1000:
        c.pas(Horloge.ms)
        Horloge.ms += 20
        if condition():
            return (Horloge.ms - debut) / 1000
    return None


class TestCapteur(unittest.TestCase):
    def setUp(self):
        Horloge.ms = 100000
        Bus.aht = Bus.bmp = True
        Bus.erreurs, Bus.crees, Bus.scans = 0, 0, 0
        Bus.ecritures = []
        Bus.aht_octets = bytes([0x1C, 0x80, 0x00, 0x06, 0x00, 0x00, 0x00])

    def test_mesure_normale(self):
        c = capteur.Capteur()
        self.assertTrue(c.ok)
        self.assertGreaterEqual(avancer(c, 12), 2)
        t, h, p = c.mesure()
        self.assertAlmostEqual(t, 25.0, delta=0.3)
        self.assertAlmostEqual(h, 50.0, delta=0.5)
        self.assertAlmostEqual(p, 1006.5, delta=1.0)
        self.assertIsNone(c.erreur)

    def test_absent_au_demarrage_puis_branche(self):
        Bus.aht = Bus.bmp = False
        c = capteur.Capteur()
        self.assertFalse(c.ok)
        self.assertEqual(c.erreur, "absent")
        self.assertEqual(avancer(c, 25), 0)          # des essais, aucune exception, aucune mesure
        self.assertIsNone(c.mesure())
        self.assertGreaterEqual(Bus.scans, 3)        # nouveau scan toutes les 10 s
        Bus.aht = Bus.bmp = True
        self.assertIsNotNone(delai_jusqua(c, lambda: c.mesure() is not None, 15))
        self.assertIsNone(c.erreur)

    def test_scenario_debranche_rebranche_moins_de_15_s(self):
        c = capteur.Capteur()
        avancer(c, 12)
        self.assertIsNotNone(c.mesure())
        Bus.aht = Bus.bmp = False                    # débranché à chaud
        delai = delai_jusqua(c, lambda: c.mesure() is None)
        self.assertIsNotNone(delai)
        self.assertLess(delai, 15)
        self.assertEqual(c.erreur, "absent")
        avancer(c, 3)
        Bus.aht = Bus.bmp = True                     # rebranché, sans toucher à la carte
        delai = delai_jusqua(c, lambda: c.mesure() is not None)
        self.assertIsNotNone(delai)
        self.assertLess(delai, 15)
        self.assertIsNone(c.erreur)

    def test_3_echecs_soft_reset_et_bus_recree(self):
        c = capteur.Capteur()
        avancer(c, 12)
        crees = Bus.crees
        Bus.ecritures = []
        Bus.aht_octets = bytes([0x98, 0, 0, 0, 0, 0, 0])  # toujours occupé : l'AHT20 répond mais ne mesure plus
        Bus.bmp = False
        avancer(c, 12)
        self.assertGreater(Bus.crees, crees)
        ecrit = [e for _, e in Bus.ecritures]
        self.assertIn(b"\xBA", ecrit)                # soft reset
        self.assertIn(b"\xBE\x08\x00", ecrit)        # initialisation / calibration
        self.assertLess(ecrit.index(b"\xBA"), ecrit.index(b"\xBE\x08\x00"))

    def test_reinit_bmp280_config_et_ctrl_meas(self):
        capteur.Capteur()
        ecrit = [e for _, e in Bus.ecritures]
        self.assertIn(b"\xF5\x00", ecrit)
        self.assertIn(b"\xF4\x24", ecrit)

    def test_une_erreur_isolee_ne_perd_pas_la_mesure(self):
        c = capteur.Capteur()
        avancer(c, 12)
        Bus.erreurs = 1                              # un seul accès rate
        avancer(c, 12)
        self.assertIsNotNone(c.mesure())
        self.assertTrue(c.ok)

    def test_valeurs_aberrantes_jamais_rendues(self):
        # temperature 150 °C (tous les bits à 1)
        Bus.bmp = False
        c = capteur.Capteur()
        Bus.aht_octets = bytes([0x1C, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00])
        self.assertEqual(avancer(c, 12), 0)
        self.assertIsNone(c.mesure())
        self.assertEqual(c.erreur, "aberrant")

    def test_bmp_registres_de_repos_rejetes(self):
        # vu sur le vrai module juste après rebranchement : 0x80000 donne 23,8 °C et 668 hPa
        Bus.aht = False
        c = capteur.Capteur()
        ancien = FauxI2C.readfrom_mem

        def repos(self, adr, mem, n):
            if mem == 0xF7:
                return bytes([0x80, 0, 0, 0x80, 0, 0])
            return ancien(self, adr, mem, n)

        FauxI2C.readfrom_mem = repos
        self.addCleanup(setattr, FauxI2C, "readfrom_mem", ancien)
        self.assertEqual(avancer(c, 3), 0)
        self.assertIsNone(c.mesure())

    def test_validation_des_bornes(self):
        self.assertTrue(capteur.temperature_valide(-20))
        self.assertTrue(capteur.temperature_valide(80))
        self.assertFalse(capteur.temperature_valide(-20.1))
        self.assertFalse(capteur.temperature_valide(80.1))
        self.assertTrue(capteur.humidite_valide(0))
        self.assertTrue(capteur.humidite_valide(100))
        self.assertFalse(capteur.humidite_valide(-0.1))
        self.assertFalse(capteur.humidite_valide(100.1))
        self.assertFalse(capteur.pression_valide(0))
        self.assertTrue(capteur.pression_valide(1013))

    def test_bmp_absent_ne_bloque_pas_aht(self):
        Bus.bmp = False
        c = capteur.Capteur()
        self.assertGreaterEqual(avancer(c, 12), 2)
        t, h, p = c.mesure()
        self.assertAlmostEqual(t, 25.0, delta=0.3)
        self.assertAlmostEqual(h, 50.0, delta=0.5)
        self.assertEqual(p, 0)

    def test_aht_absent_ne_bloque_pas_bmp(self):
        Bus.aht = False
        c = capteur.Capteur()
        self.assertGreaterEqual(avancer(c, 12), 2)
        t, h, p = c.mesure()
        self.assertAlmostEqual(t, 25.08, delta=0.1)
        self.assertEqual(h, -1)
        self.assertAlmostEqual(p, 1006.5, delta=1.0)

    def test_bmp_debranche_a_chaud_puis_revient(self):
        c = capteur.Capteur()
        avancer(c, 12)
        Bus.bmp = False
        avancer(c, 15)
        self.assertEqual(c.mesure()[2], 0)           # plus de pression, AHT20 toujours là
        self.assertAlmostEqual(c.mesure()[1], 50.0, delta=0.5)
        Bus.bmp = True
        avancer(c, 15)                               # rescan toutes les 10 s
        self.assertGreater(c.mesure()[2], 0)

    def test_erreur_envoyee_au_changement_puis_toutes_les_10_s(self):
        Bus.aht = Bus.bmp = False
        c = capteur.Capteur()
        self.assertEqual(c.erreur_a_envoyer(Horloge.ms), "absent")
        self.assertIsNone(c.erreur_a_envoyer(Horloge.ms + 100))
        Horloge.ms += 10000
        self.assertEqual(c.erreur_a_envoyer(Horloge.ms), "absent")

    def test_pas_d_erreur_a_envoyer_si_mesure_valide(self):
        c = capteur.Capteur()
        avancer(c, 1)
        self.assertIsNone(c.erreur_a_envoyer(Horloge.ms))

    def test_reinitialiser_bouton(self):
        c = capteur.Capteur()
        avancer(c, 2)                                # prochaine mesure dans 5 s
        self.assertTrue(c.reinitialiser(Horloge.ms))
        self.assertGreaterEqual(avancer(c, 0.3), 1)  # mesure renvoyée tout de suite
        Bus.aht = Bus.bmp = False
        self.assertFalse(c.reinitialiser(Horloge.ms))
        self.assertIsNone(c.mesure())

    def test_mesure_perimee_jamais_renvoyee(self):
        c = capteur.Capteur()
        avancer(c, 12)
        self.assertIsNotNone(c.mesure())
        Horloge.ms += 61000                          # plus aucune lecture pendant 61 s
        self.assertIsNone(c.mesure())

    def test_exception_inattendue_ne_sort_pas_de_pas(self):
        c = capteur.Capteur()
        avancer(c, 12)
        c.i2c = None                                 # état cassé
        for _ in range(1000):
            c.pas(Horloge.ms)                        # ne doit jamais lever
            Horloge.ms += 20
        self.assertIsNotNone(c.mesure())             # et ça repart tout seul


if __name__ == "__main__":
    unittest.main()
