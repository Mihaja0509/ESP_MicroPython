"""Tests de l'historique de jeu (Phase 14) :  py -X utf8 -m unittest tools\\agent\\test_historique.py"""
import json
import unittest

from historique import GARDER_JOURS, Historique


class TestHistorique(unittest.TestCase):
    def test_agregation_d_un_jeu_sur_un_jour(self):
        h = Historique()
        h.session("2026-11-06", "Jeu A")
        for fps, cpu, gpu, ch, ram in ((60, 50, 60, 80, 40), (90, 60, 70, 90, 50), (30, 55, 65, 70, 45)):
            h.echantillon("2026-11-06", "Jeu A", 1.0, fps=fps, cpu=cpu, gpu=gpu, charge=ch, ram=ram)
        j = h.pour_app("2026-11-06")["jours"][0]
        a = j["jeux"][0]
        self.assertEqual(j["s"], 3)
        self.assertEqual(a["sessions"], 1)
        self.assertEqual(a["fps"], {"min": 30, "moy": 60, "max": 90, "n": 3})
        self.assertEqual(a["cpu"]["moy"], 55)
        self.assertEqual(a["cpu"]["max"], 60)
        self.assertEqual(a["gpu"]["max"], 70)
        self.assertEqual(a["charge"]["moy"], 80)
        self.assertEqual(a["ram"]["moy"], 45)

    def test_mesures_inconnues_ignorees(self):
        h = Historique()
        h.echantillon("2026-11-06", "Jeu A", 1.0, fps=-1, cpu=-1, gpu=None, charge=-1, ram=None)
        a = h.pour_app("2026-11-06")["jours"][0]["jeux"][0]
        self.assertIsNone(a["fps"])
        self.assertIsNone(a["cpu"])
        self.assertIsNone(a["gpu"])
        self.assertIsNone(a["charge"])
        self.assertEqual(a["s"], 1)

    def test_total_du_jour_tous_jeux_et_remise_a_zero(self):
        h = Historique()
        h.echantillon("2026-11-06", "Jeu A", 100.0)
        h.echantillon("2026-11-06", "Jeu B", 50.0)
        self.assertEqual(h.total_jour("2026-11-06"), 150.0)
        self.assertEqual(h.secondes_jeu("2026-11-06", "Jeu A"), 100.0)
        # minuit : le nouveau jour repart de zéro, l'ancien reste archivé
        self.assertEqual(h.total_jour("2026-11-07"), 0.0)
        h.echantillon("2026-11-07", "Jeu A", 10.0)
        self.assertEqual(h.total_jour("2026-11-07"), 10.0)
        self.assertEqual(h.total_jour("2026-11-06"), 150.0)

    def test_sessions_par_jour(self):
        h = Historique()
        h.session("2026-11-06", "Jeu A")
        h.session("2026-11-06", "Jeu A")
        h.session("2026-11-07", "Jeu A")
        h.echantillon("2026-11-06", "Jeu A", 5.0)
        h.echantillon("2026-11-07", "Jeu A", 5.0)
        jours = {j["date"]: j for j in h.pour_app("2026-11-07")["jours"]}
        self.assertEqual(jours["2026-11-06"]["jeux"][0]["sessions"], 2)
        self.assertEqual(jours["2026-11-07"]["jeux"][0]["sessions"], 1)

    def test_migration_sans_perte_des_anciens_jours(self):
        anciens = {"2026-11-01": {"Jeu A": 3600, "Jeu B": 600}, "2026-11-02": {"Jeu A": 120}}
        h = Historique(anciens_jours=anciens)
        self.assertEqual(h.total_jour("2026-11-01"), 4200)
        self.assertEqual(h.secondes_jeu("2026-11-01", "Jeu B"), 600)
        self.assertEqual(h.secondes_jeu("2026-11-02", "Jeu A"), 120)
        # ordre : du plus récent au plus ancien, jeu le plus joué d'abord
        jours = h.pour_app("2026-11-02")["jours"]
        self.assertEqual([j["date"] for j in jours], ["2026-11-02", "2026-11-01"])
        self.assertEqual([g["nom"] for g in jours[1]["jeux"]], ["Jeu A", "Jeu B"])

    def test_aller_retour_fichier(self):
        h = Historique(anciens_jours={"2026-11-01": {"Jeu A": 300}})
        h.session("2026-11-06", "Jeu A")
        h.echantillon("2026-11-06", "Jeu A", 2.0, fps=75, cpu=62, gpu=71, charge=95, ram=60)
        brut = json.loads(json.dumps(h.vers_dict()))
        h2 = Historique(brut["historique"], brut["totaux"], None)
        self.assertEqual(h2.pour_app("2026-11-06"), h.pour_app("2026-11-06"))

    def test_365_jours_gardes(self):
        h = Historique()
        for i in range(GARDER_JOURS + 20):
            jour = "2025-%03d" % i  # clés triables, seul l'ordre compte ici
            h.echantillon(jour, "Jeu A", 1.0)
        h.elaguer()
        self.assertEqual(len(h.jours), GARDER_JOURS)
        self.assertEqual(len(h.totaux), GARDER_JOURS)
        self.assertNotIn("2025-000", h.jours)
        self.assertIn("2025-%03d" % (GARDER_JOURS + 19), h.jours)


if __name__ == "__main__":
    unittest.main()
