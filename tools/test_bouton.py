"""Tests de esp/lib/bouton.py sous CPython (Phase 15) :  py -X utf8 tools\\test_bouton.py"""
import os
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "esp", "lib"))
from bouton import Bouton  # noqa: E402


class Banc:
    def __init__(self, niveau=1):
        self.niveau = niveau
        self.t = 1000
        self.b = Bouton(lambda: self.niveau, self.t)
        self.evenements = []
        self.avancer(200)  # démarrage : armement

    def avancer(self, ms, pas=10):
        for _ in range(ms // pas):
            self.t += pas
            e = self.b.pas(self.t)
            if e:
                self.evenements.append(e)


class TestBouton(unittest.TestCase):
    def test_appui_court(self):
        b = Banc()
        b.niveau = 0
        b.avancer(200)
        self.assertEqual(b.evenements, [])
        b.niveau = 1
        b.avancer(100)
        self.assertEqual(b.evenements, ["court"])

    def test_rebond_ignore(self):
        b = Banc()
        for _ in range(3):           # impulsions de 20 ms, plus courtes que l'anti-rebond
            b.niveau = 0
            b.avancer(20)
            b.niveau = 1
            b.avancer(20)
        b.avancer(100)
        self.assertEqual(b.evenements, [])

    def test_appui_long_redemarre_au_relachement(self):
        b = Banc()
        b.niveau = 0
        b.avancer(2900)
        self.assertEqual(b.evenements, [])
        b.avancer(300)
        self.assertEqual(b.evenements, ["long"])     # annoncé une seule fois, encore enfoncé
        b.avancer(5000)
        self.assertEqual(b.evenements, ["long"])
        b.niveau = 1
        b.avancer(100)
        self.assertEqual(b.evenements, ["long", "relache"])

    def test_enfonce_au_demarrage_ignore(self):
        b = Banc(niveau=0)
        b.avancer(5000)
        b.niveau = 1
        b.avancer(100)
        self.assertEqual(b.evenements, [])
        b.niveau = 0                                 # le prochain appui compte
        b.avancer(100)
        b.niveau = 1
        b.avancer(100)
        self.assertEqual(b.evenements, ["court"])


if __name__ == "__main__":
    unittest.main()
