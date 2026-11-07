"""Tests de l'état de la clim côté agent (Phase 14-bis) :  cd tools\\agent  puis  py -X utf8 -m unittest test_clim_agent"""
import unittest
from unittest import mock

import agent_pc as a


class LienFaux:
    muet = False

    def __init__(self):
        self.lignes = []

    def envoyer(self, ligne):
        self.lignes.append(ligne)
        return True


class Horloge:
    t = 1_000_000.0


def nouvel_agent():
    ag = a.Agent.__new__(a.Agent)
    ag.liaison = LienFaux()
    ag.precedent = {}
    ag.clim = None
    ag.clim_envoye = 0.0
    ag.clim_recu = 0.0
    ag.clim_cle = None
    return ag


class TestClimatAgent(unittest.TestCase):
    """Phase 15 : CLIMAT ERR marque la mesure absente, /clim_mesure le dit, l'automatisme ne fait rien."""

    def setUp(self):
        Horloge.t = 1_000_000.0
        p = mock.patch.object(a.time, "time", lambda: Horloge.t)
        p.start()
        self.addCleanup(p.stop)
        self.ag = nouvel_agent()
        self.ag.piece = {}
        self.ag.piece_vue = None
        self.ag.piece_erreur = None

    def test_mesure_valide(self):
        self.ag.lire_climat("CLIMAT 274 61 1008")
        m = self.ag.piece_pour_app()
        self.assertTrue(m["ok"])
        self.assertEqual((m["t"], m["h"], m["p"]), (27.4, 61, 1008))

    def test_climat_err_marque_absent(self):
        self.ag.lire_climat("CLIMAT 274 61 1008")
        self.ag.lire_climat("CLIMAT ERR absent")
        self.assertEqual(self.ag.piece_pour_app(), {"ok": False, "absent": True, "raison": "absent"})

    def test_retour_apres_erreur(self):
        self.ag.lire_climat("CLIMAT ERR i2c")
        self.ag.lire_climat("CLIMAT 250 50 1000")
        self.assertTrue(self.ag.piece_pour_app()["ok"])

    def test_mesure_trop_vieille_absente(self):
        self.ag.lire_climat("CLIMAT 274 61 1008")
        Horloge.t += 31
        m = self.ag.piece_pour_app()
        self.assertFalse(m["ok"])
        self.assertTrue(m["absent"])

    def test_humidite_inconnue_bmp_seul(self):
        self.ag.lire_climat("CLIMAT 250 -1 1000")
        self.assertEqual(self.ag.piece_pour_app()["h"], -1)

    def test_ligne_illisible_ignoree(self):
        self.ag.lire_climat("CLIMAT 274 61 1008")
        self.ag.lire_climat("CLIMAT abc")
        self.assertTrue(self.ag.piece_pour_app()["ok"])


class TestClimAgent(unittest.TestCase):
    def setUp(self):
        Horloge.t = 1_000_000.0
        p = mock.patch.object(a.time, "time", lambda: Horloge.t)
        p.start()
        self.addCleanup(p.stop)

    def clim_lignes(self, ag):
        return [l for l in ag.liaison.lignes if l.startswith("CLIM")]

    def test_minuteur_en_secondes_arrive_a_l_esp32(self):
        ag = nouvel_agent()
        ag.clim_maj({"on": "1", "mode": "cool", "temp": "24", "reste": "10", "auto": "0", "plage": "0"})
        ag._envoyer_clim()
        self.assertEqual(self.clim_lignes(ag), ["CLIM 1 cool 24 10 0 0"])  # 10 secondes, pas 10 minutes
        Horloge.t += 4
        ag.clim_maj({"on": "1", "mode": "cool", "temp": "24", "reste": "6", "auto": "0", "plage": "0"})
        ag._envoyer_clim()
        self.assertEqual(self.clim_lignes(ag)[-1], "CLIM 1 cool 24 6 0 0")

    def test_extinction_publiee_tout_de_suite(self):
        ag = nouvel_agent()
        ag.clim_maj({"on": "1", "mode": "cool", "temp": "24", "reste": "10", "auto": "0", "plage": "0"})
        ag._envoyer_clim()
        Horloge.t += 10
        ag.clim_maj({"on": "0", "mode": "cool", "temp": "24", "reste": "0", "auto": "0", "plage": "0"})
        ag._envoyer_clim()
        self.assertEqual(self.clim_lignes(ag)[-1], "CLIM 0 cool 24 0 0 0")

    def test_republication_toutes_les_20_secondes_sans_changement(self):
        ag = nouvel_agent()
        ag.clim_maj({"on": "1", "mode": "cool", "temp": "24", "reste": "600", "auto": "0", "plage": "0"})
        ag._envoyer_clim()
        n = len(self.clim_lignes(ag))
        Horloge.t += 5
        ag.clim_recu = Horloge.t  # le téléphone republie : même état
        ag.clim = dict(ag.clim)
        ag._envoyer_clim()
        self.assertEqual(len(self.clim_lignes(ag)), n)      # rien de neuf avant 20 s
        Horloge.t += 20
        ag.clim_recu = Horloge.t
        ag._envoyer_clim()
        self.assertEqual(len(self.clim_lignes(ag)), n + 1)  # recalage du compte à rebours

    def test_rien_du_telephone_depuis_90_s_clim_remise_a_off(self):
        ag = nouvel_agent()
        ag.clim_maj({"on": "1", "mode": "dry", "temp": "26", "reste": "3600", "auto": "1", "plage": "1140-1260"})
        ag._envoyer_clim()
        Horloge.t += 89
        ag._envoyer_clim()
        self.assertTrue(ag.clim["on"])                       # 89 s : encore valable
        Horloge.t += 2
        ag._envoyer_clim()                                   # 91 s : péremption
        self.assertEqual(ag.clim["on"], 0)
        self.assertEqual(self.clim_lignes(ag)[-1], "CLIM 0 dry 26 0 0 0")
        n = len(self.clim_lignes(ag))
        Horloge.t += 5
        ag._envoyer_clim()
        self.assertEqual(len(self.clim_lignes(ag)), n)       # pas de nouvelle ligne tant que rien ne change

    def test_le_telephone_revient_apres_la_peremption(self):
        ag = nouvel_agent()
        ag.clim_maj({"on": "1", "mode": "cool", "temp": "24", "reste": "600", "auto": "0", "plage": "0"})
        ag._envoyer_clim()
        Horloge.t += 100
        ag._envoyer_clim()                                   # remise à off
        ag.clim_maj({"on": "1", "mode": "cool", "temp": "24", "reste": "500", "auto": "0", "plage": "0"})
        ag._envoyer_clim()
        self.assertEqual(self.clim_lignes(ag)[-1], "CLIM 1 cool 24 500 0 0")

    def test_arret_de_l_agent_envoie_clim_off(self):
        ag = nouvel_agent()
        ag.clim_eteinte_esp()
        self.assertEqual(ag.liaison.lignes[-1], "CLIM 0 cool 24 0 0 0")


if __name__ == "__main__":
    unittest.main()
