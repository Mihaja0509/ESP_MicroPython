"""Historique de jeu par jour et par jeu (Phase 14).

Pour chaque jour et chaque jeu : secondes jouées, nombre de sessions, FPS (min / moyen / max),
température CPU et GPU (moyenne, max), charge GPU et RAM moyennes. 365 jours gardés. Le total du jour
(tous jeux) est gardé à part : un nouveau jour (minuit, heure locale) repart de zéro, l'ancien est
archivé tel quel.

Données dans tools\\agent\\stats_jeux.json. Les clés « jeux » et « jours » de la Phase 10 restent telles
quelles (aucune perte) ; on ajoute « historique » et « totaux ». Au premier lancement, les anciens
« jours » (secondes par jeu) sont repris dans l'historique (sessions et FPS inconnus pour ces jours).
"""
import threading

GARDER_JOURS = 365

# somme / nombre d'échantillons, un par seconde de jeu
_MOYENNES = ("fps", "cpu", "gpu", "ch", "ram")


def entree_vide():
    return {"s": 0.0, "n": 0,
            "fps_min": None, "fps_max": None, "fps_somme": 0.0, "fps_n": 0,
            "cpu_somme": 0.0, "cpu_n": 0, "cpu_max": None,
            "gpu_somme": 0.0, "gpu_n": 0, "gpu_max": None,
            "ch_somme": 0.0, "ch_n": 0,
            "ram_somme": 0.0, "ram_n": 0}


def _nombre(v, defaut=0.0):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else defaut


def _entree_depuis_json(d):
    """Remet une entrée lue dans le fichier dans la forme attendue (champs manquants = vides)."""
    e = entree_vide()
    if not isinstance(d, dict):
        return e
    for cle, defaut in e.items():
        v = d.get(cle)
        if cle in ("fps_min", "fps_max", "cpu_max", "gpu_max"):
            e[cle] = v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
        elif cle in ("n", "fps_n", "cpu_n", "gpu_n", "ch_n", "ram_n"):
            e[cle] = int(_nombre(v))
        else:
            e[cle] = _nombre(v)
    return e


def _moy(somme, n, chiffres=0):
    if not n:
        return None
    m = somme / n
    return round(m, chiffres) if chiffres else int(round(m))


def resume(nom, e):
    """Une entrée (jour, jeu) telle que l'app la reçoit. Les mesures absentes valent None."""
    fps = ({"min": int(e["fps_min"]), "moy": _moy(e["fps_somme"], e["fps_n"]), "max": int(e["fps_max"]),
            "n": e["fps_n"]} if e["fps_n"] else None)
    cpu = ({"moy": _moy(e["cpu_somme"], e["cpu_n"]), "max": int(e["cpu_max"]), "n": e["cpu_n"]}
           if e["cpu_n"] else None)
    gpu = ({"moy": _moy(e["gpu_somme"], e["gpu_n"]), "max": int(e["gpu_max"]), "n": e["gpu_n"]}
           if e["gpu_n"] else None)
    return {"nom": nom, "s": int(round(e["s"])), "sessions": e["n"], "fps": fps, "cpu": cpu, "gpu": gpu,
            "charge": ({"moy": _moy(e["ch_somme"], e["ch_n"]), "n": e["ch_n"]} if e["ch_n"] else None),
            "ram": ({"moy": _moy(e["ram_somme"], e["ram_n"]), "n": e["ram_n"]} if e["ram_n"] else None)}


class Historique:
    def __init__(self, historique=None, totaux=None, anciens_jours=None):
        self.verrou = threading.Lock()
        self.jours = {}    # "2026-11-06" -> {jeu -> entrée}
        self.totaux = {}   # "2026-11-06" -> secondes, tous jeux
        if isinstance(historique, dict):
            for jour, jeux in historique.items():
                if isinstance(jeux, dict):
                    self.jours[str(jour)] = {str(n): _entree_depuis_json(e) for n, e in jeux.items()}
        if isinstance(totaux, dict):
            for jour, s in totaux.items():
                self.totaux[str(jour)] = _nombre(s)
        # migration : les secondes par jour et par jeu de la Phase 10 (rien n'est perdu)
        if isinstance(anciens_jours, dict):
            for jour, jeux in anciens_jours.items():
                if not isinstance(jeux, dict):
                    continue
                du_jour = self.jours.setdefault(str(jour), {})
                for nom, s in jeux.items():
                    if str(nom) not in du_jour:
                        e = entree_vide()
                        e["s"] = _nombre(s)
                        du_jour[str(nom)] = e
        for jour, jeux in self.jours.items():
            if jour not in self.totaux:
                self.totaux[jour] = sum(e["s"] for e in jeux.values())

    # ---------------------------------------------------------------- écriture
    def _entree(self, jour, jeu):
        return self.jours.setdefault(jour, {}).setdefault(jeu, entree_vide())

    def session(self, jour, jeu):
        """Une nouvelle session de jeu commence ce jour-là."""
        with self.verrou:
            self._entree(jour, jeu)["n"] += 1

    def echantillon(self, jour, jeu, ecart, fps=None, cpu=None, gpu=None, charge=None, ram=None):
        """`ecart` secondes de jeu en plus, avec les mesures de cet instant (None ou négatif = inconnu)."""
        with self.verrou:
            e = self._entree(jour, jeu)
            e["s"] += ecart
            self.totaux[jour] = self.totaux.get(jour, 0.0) + ecart
            if isinstance(fps, (int, float)) and fps > 0:
                e["fps_somme"] += fps
                e["fps_n"] += 1
                e["fps_min"] = fps if e["fps_min"] is None else min(e["fps_min"], fps)
                e["fps_max"] = fps if e["fps_max"] is None else max(e["fps_max"], fps)
            for cle, v in (("cpu", cpu), ("gpu", gpu)):
                if isinstance(v, (int, float)) and 1 <= v <= 130:  # °C ; -1 = mesure ratée
                    e[cle + "_somme"] += v
                    e[cle + "_n"] += 1
                    e[cle + "_max"] = v if e[cle + "_max"] is None else max(e[cle + "_max"], v)
            for cle, v in (("ch", charge), ("ram", ram)):
                if isinstance(v, (int, float)) and 0 <= v <= 100:
                    e[cle + "_somme"] += v
                    e[cle + "_n"] += 1

    def elaguer(self):
        """Garde les 365 derniers jours."""
        with self.verrou:
            for vieux in sorted(self.jours)[:-GARDER_JOURS]:
                del self.jours[vieux]
            for vieux in sorted(self.totaux)[:-GARDER_JOURS]:
                del self.totaux[vieux]

    # ---------------------------------------------------------------- lecture
    def total_jour(self, jour):
        with self.verrou:
            return self.totaux.get(jour, 0.0)

    def secondes_jeu(self, jour, jeu):
        with self.verrou:
            e = self.jours.get(jour, {}).get(jeu)
            return e["s"] if e else 0.0

    def vers_dict(self):
        """Ce qui est écrit dans stats_jeux.json (clés « historique » et « totaux »)."""
        with self.verrou:
            historique = {}
            for jour, jeux in self.jours.items():
                historique[jour] = {}
                for nom, e in jeux.items():
                    sortie = {}
                    for cle, v in e.items():
                        sortie[cle] = round(v, 1) if isinstance(v, float) else v
                    historique[jour][nom] = sortie
            return {"historique": historique, "totaux": {j: round(s) for j, s in self.totaux.items()}}

    def pour_app(self, aujourdhui, nb_jours=GARDER_JOURS):
        """Message « historique » de l'app : les jours (du plus récent au plus ancien) avec, pour
        chacun, le total et le détail de chaque jeu."""
        with self.verrou:
            dates = sorted(self.jours, reverse=True)[:nb_jours]
            jours = []
            for jour in dates:
                jeux = [resume(nom, e) for nom, e in self.jours[jour].items() if e["s"] >= 1 or e["n"]]
                if not jeux:
                    continue
                jeux.sort(key=lambda j: j["s"], reverse=True)
                jours.append({"date": jour, "s": int(round(self.totaux.get(jour, 0.0))), "jeux": jeux})
        return {"aujourdhui": aujourdhui, "jours": jours}
