"""Suivi du master de Mihaja (Phase 11) pour l'écran de l'ESP32 et l'app Dadou.

- Réglages modifiés depuis l'app (tools\\agent\\master.json, jamais dans Git) :
  échéances, objectif du jour, réunion + question, phase, objectifs chiffrés, chemins.
- Calculé tout seul sur le PC :
  mots du mémoire (fichier .docx, lu sans module en plus), articles lus / à lire (dossiers de PDF),
  dernier résultat de mesure (CSV), temps passé dans les applis de recherche aujourd'hui.
- Historique : tools\\agent\\master_historique.json (jamais dans Git).

L'agent appelle seconde(...) une fois par seconde, puis envoie ligne_esp() à l'ESP32 quand elle
change, et les événements (bandeau + scène 15 s) donnés par evenements().
"""
import csv
import html
import json
import math
import re
import threading
import time
import unicodedata
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

PHASES = ("Etat de l'art", "Prototype", "Mesures", "Redaction")
MOIS = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")
# caractères que les polices de l'ESP32 savent dessiner (les autres sont simplifiés)
CARACTERES_ECRAN = set(chr(c) for c in range(32, 127)) | set("°éèêëàâäçîïôöùûüÉÈÀÇ…•")
NAVIGATEURS = {"chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "opera_gx.exe", "brave.exe",
               "vivaldi.exe"}
SITES_RECHERCHE = ("overleaf", "google scholar", "semantic scholar", "researchrabbit", "notebooklm",
                   "sciencedirect", "ieee xplore", "springer", "acm digital library", "arxiv",
                   "scopus", "web of science", "mendeley", "connected papers", "elicit")
APPS_RECHERCHE = ("mendeley", "godot", "unity", "studio64", "pulseview", "sumatrapdf", "acrord32",
                  "acrobat")
CONTINU = 120            # s dans une appli de recherche avant d'afficher la scène pendant le travail
COUPURE = 30             # s hors recherche tolérées (un coup d'œil ailleurs ne remet pas à zéro)
CALCUL = 30              # s entre deux calculs (mots, articles, résultats)
DEFAUT = {
    "echeances": [],                     # [{"titre": "Odin 3", "date": "2026-11-13"}]
    "objectif": {"texte": "", "date": "", "fait": False},
    "objectifs_passes": [],              # 20 derniers objectifs
    "reunion": {"date": "", "question": ""},   # date : "2026-11-10T10:00"
    "phase": "Etat de l'art",
    "objectif_articles": 20,
    "objectif_mots_jour": 300,
    "chemins": {"memoire": "", "a_lire": "", "lus": "", "resultats": ""},
    "mots_word": ["memoire", "mémoire", "thesis", "proposal", "synthese", "synthèse", "critique",
                  "master"],
    "mots_code": ["master", "xr", "orchestr"],
}


def texte_ecran(texte, longueur=60):
    """Garde les caractères que l'ESP32 sait dessiner ; les autres perdent leur accent."""
    res = []
    for ch in str(texte):
        if ch in CARACTERES_ECRAN:
            res.append(ch)
        else:
            simple = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode("ascii")
            res.append(simple)
    t = " ".join("".join(res).split())
    return t[:longueur]


def _date(texte):
    try:
        return date.fromisoformat(str(texte)[:10])
    except ValueError:
        return None


def _date_heure(texte):
    try:
        return datetime.fromisoformat(str(texte)[:16])
    except ValueError:
        return None


def mots_docx(chemin):
    """Nombre de mots d'un fichier Word (.docx), sans python-docx."""
    with zipfile.ZipFile(chemin) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = xml.replace("</w:p>", "\n").replace("<w:tab/>", " ")
    texte = html.unescape(re.sub(r"<[^>]+>", "", xml))
    return len(re.findall(r"\w+", texte))


def compter_pdf(dossier):
    """(nombre, noms sans .pdf triés du plus récent au plus ancien)."""
    d = Path(dossier)
    if not dossier or not d.is_dir():
        return -1, []
    fichiers = sorted(d.glob("*.pdf"), key=lambda f: f.stat().st_mtime, reverse=True)
    return len(fichiers), [f.stem for f in fichiers[:40]]


def lire_resultats(chemin):
    """Sessions du CSV de mesures : [(session, [latences], dernière ligne)], dans l'ordre du fichier.
    Colonnes attendues : timestamp,session,essai,mode_xreal,refresh_hz,perf_mode,temp_c,latence_ms"""
    sessions = {}
    ordre = []
    with open(chemin, newline="", encoding="utf-8-sig") as f:
        for ligne in csv.DictReader(f):
            try:
                lat = float(str(ligne.get("latence_ms", "")).replace(",", "."))
            except ValueError:
                continue
            s = str(ligne.get("session", "")).strip() or "?"
            if s not in sessions:
                sessions[s] = ([], ligne)
                ordre.append(s)
            sessions[s][0].append(lat)
            sessions[s] = (sessions[s][0], ligne)
    return [(s, sessions[s][0], sessions[s][1]) for s in ordre]


def mediane(v):
    v = sorted(v)
    n = len(v)
    return (v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2) if n else 0


def p95(v):
    v = sorted(v)
    return v[max(0, math.ceil(0.95 * len(v)) - 1)] if v else 0


class SuiviMaster:
    def __init__(self, dossier):
        self.fichier = Path(dossier) / "master.json"
        self.fichier_hist = Path(dossier) / "master_historique.json"
        self.verrou = threading.Lock()
        self.config = self._lire(self.fichier, DEFAUT)
        self.hist = self._lire(self.fichier_hist, {"mots_base": {}, "dernier_mots": -1, "temps": {},
                                                     "notifie": {}})
        self.auto = {"mots": -1, "mots_jour": -1, "lus": -1, "a_lire": -1, "a_lire_noms": [],
                     "resultat": None, "courbe": [], "probleme": ""}
        self.version = 1          # change dès que l'app doit relire les données
        self._evenements = []
        self._dernier_calcul = 0.0
        self._caches = {}
        self._derniere_session = None
        self._recherche_debut = 0.0
        self._recherche_vue = 0.0
        self._hist_sauve = time.time()
        self.actif = False        # appli de recherche au premier plan depuis 2 min

    # ------------------------------------------------------------ fichiers
    def _lire(self, fichier, defaut):
        try:
            d = json.loads(fichier.read_text(encoding="utf-8"))
            if not isinstance(d, dict):
                d = {}
        except (OSError, ValueError):
            d = {}
        res = json.loads(json.dumps(defaut))
        for k, v in d.items():
            if k in res and isinstance(v, type(res[k])):
                if isinstance(v, dict):
                    res[k].update(v)
                else:
                    res[k] = v
        return res

    def _ecrire(self, fichier, donnees):
        try:
            tmp = fichier.with_suffix(".tmp")
            tmp.write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")
            tmp.replace(fichier)
        except OSError as e:
            print(f"[agent] master : {fichier.name} non enregistré ({e})")

    # ------------------------------------------------------------ depuis l'app
    def maj(self, d):
        """Change une partie des réglages (message « master_maj » de l'app). -> (ok, texte)."""
        if not isinstance(d, dict):
            return False, "Données invalides"
        with self.verrou:
            c = self.config
            if "echeances" in d:
                liste = []
                for e in d["echeances"] if isinstance(d["echeances"], list) else []:
                    if isinstance(e, dict) and str(e.get("titre", "")).strip() and _date(e.get("date")):
                        liste.append({"titre": str(e["titre"]).strip()[:60], "date": str(e["date"])[:10]})
                c["echeances"] = sorted(liste, key=lambda e: e["date"])[:30]
            if "objectif" in d and isinstance(d["objectif"], dict):
                o = d["objectif"]
                texte = str(o.get("texte", "")).strip()[:120]
                ancien = c["objectif"]
                if texte != ancien.get("texte") and ancien.get("texte"):
                    c["objectifs_passes"] = ([dict(ancien)] + c["objectifs_passes"])[:20]
                fait = bool(o.get("fait", False)) and bool(texte)
                if fait and not ancien.get("fait"):
                    self._evenements.append(("livre", "Objectif du jour atteint. Bien joué."))
                c["objectif"] = {"texte": texte, "date": date.today().isoformat() if texte else "",
                                 "fait": fait}
            if "reunion" in d and isinstance(d["reunion"], dict):
                r = d["reunion"]
                quand = str(r.get("date", "")).strip()
                if quand and not _date_heure(quand):
                    return False, "Date de réunion invalide"
                c["reunion"] = {"date": quand[:16], "question": str(r.get("question", "")).strip()[:120]}
            if "phase" in d:
                c["phase"] = str(d["phase"]).strip()[:30] or "Etat de l'art"
            for cle, maxi in (("objectif_articles", 500), ("objectif_mots_jour", 5000)):
                if cle in d:
                    try:
                        c[cle] = max(0, min(maxi, int(d[cle])))
                    except (TypeError, ValueError):
                        return False, "Nombre invalide"
            if "chemins" in d and isinstance(d["chemins"], dict):
                for cle in ("memoire", "a_lire", "lus", "resultats"):
                    if cle in d["chemins"]:
                        c["chemins"][cle] = str(d["chemins"][cle]).strip().strip('"')[:260]
            for cle in ("mots_word", "mots_code"):
                if cle in d and isinstance(d[cle], list):
                    c[cle] = [str(m).strip().lower()[:30] for m in d[cle] if str(m).strip()][:20]
            self._ecrire(self.fichier, c)
            self._dernier_calcul = 0.0   # recalcule tout de suite (chemins changés…)
            self.version += 1
        return True, "Master mis à jour"

    def pour_app(self):
        """Tout ce que l'onglet Master de l'app affiche."""
        with self.verrou:
            c = json.loads(json.dumps(self.config))
            a = dict(self.auto)
            temps = int(self.hist["temps"].get(date.today().isoformat(), 0) // 60)
        chemins = {k: {"chemin": v, "ok": bool(v) and Path(v).exists()} for k, v in c["chemins"].items()}
        return {"config": c, "auto": a, "temps_jour": temps, "chemins_ok": chemins,
                "phases": list(PHASES), "version": self.version}

    # ------------------------------------------------------------ chaque seconde
    def seconde(self, exe, titre, repos, occupe):
        """exe / titre : appli au premier plan ; repos : s sans clavier ni souris ;
        occupe : jeu ou PC verrouillé (pas de temps master compté)."""
        maintenant = time.time()
        recherche = not occupe and repos < 120 and self._est_recherche(exe, titre)
        if recherche:
            if not self._recherche_debut or maintenant - self._recherche_vue > COUPURE:
                self._recherche_debut = maintenant
            self._recherche_vue = maintenant
            jour = date.today().isoformat()
            with self.verrou:
                self.hist["temps"][jour] = self.hist["temps"].get(jour, 0) + 1
        actif = bool(self._recherche_debut) and maintenant - self._recherche_vue <= COUPURE \
            and maintenant - self._recherche_debut >= CONTINU
        self.actif = actif
        if maintenant - self._dernier_calcul >= CALCUL:
            self._dernier_calcul = maintenant
            self._calculer()
        if maintenant - self._hist_sauve > 120:
            self._hist_sauve = maintenant
            with self.verrou:
                self._ecrire(self.fichier_hist, self.hist)

    def _est_recherche(self, exe, titre):
        exe = (exe or "").lower()
        t = (titre or "").lower()
        if not exe:
            return False
        if any(m in exe for m in APPS_RECHERCHE):
            return True
        if exe == "winword.exe":
            return any(m in t for m in self.config["mots_word"])
        if exe == "code.exe":
            return any(m in t for m in self.config["mots_code"])
        if exe in NAVIGATEURS:
            return any(s in t for s in SITES_RECHERCHE) or ".pdf" in t
        return False

    def _cache(self, cle, chemin, calcul):
        """Recalcule seulement si le fichier a changé (date + taille)."""
        try:
            st = Path(chemin).stat()
        except OSError:
            self._caches.pop(cle, None)
            return None
        signe = (st.st_mtime, st.st_size)
        ancien = self._caches.get(cle)
        if ancien and ancien[0] == signe:
            return ancien[1]
        valeur = calcul(chemin)
        self._caches[cle] = (signe, valeur)
        return valeur

    def _calculer(self):
        c = self.config["chemins"]
        a = dict(self.auto)
        a["probleme"] = ""
        jour = date.today().isoformat()
        # mots du mémoire (.docx)
        if c["memoire"].lower().endswith(".docx"):
            try:
                mots = self._cache("memoire", c["memoire"], mots_docx)
            except (OSError, KeyError, zipfile.BadZipFile) as e:
                mots, a["probleme"] = None, f"Mémoire illisible : {e}"
            if mots is not None:
                with self.verrou:
                    base = self.hist["mots_base"]
                    if jour not in base:  # base du jour = dernier compte des jours précédents
                        dernier = self.hist.get("dernier_mots", -1)
                        base[jour] = dernier if dernier >= 0 else mots
                        for vieux in sorted(base)[:-60]:
                            del base[vieux]
                    self.hist["dernier_mots"] = mots
                    a["mots"], a["mots_jour"] = mots, max(0, mots - base[jour])
                but = self.config["objectif_mots_jour"]
                if but and a["mots_jour"] >= but and self._une_fois(f"mots:{jour}"):
                    self._evenements.append(("stylo", "Objectif de mots atteint !"))
        else:
            a["mots"], a["mots_jour"] = -1, -1
        # articles
        a["lus"], _ = compter_pdf(c["lus"])
        a["a_lire"], a["a_lire_noms"] = compter_pdf(c["a_lire"])
        # résultats de mesure
        a["resultat"], a["courbe"] = None, []
        if c["resultats"]:
            try:
                sessions = self._cache("resultats", c["resultats"], lire_resultats) or []
            except (OSError, csv.Error, UnicodeDecodeError) as e:
                sessions, a["probleme"] = [], f"CSV illisible : {e}"
            if sessions:
                s, lat, derniere = sessions[-1]
                a["resultat"] = {"session": s, "mediane": round(mediane(lat)), "p95": round(p95(lat)),
                                 "n": len(lat), "mode": str(derniere.get("mode_xreal", "")).strip()[:10],
                                 "hz": str(derniere.get("refresh_hz", "")).strip()[:5]}
                a["courbe"] = [round(mediane(v)) for _, v, _ in sessions[-10:]]
                cle = (s, len(lat))
                if self._derniere_session is not None and cle != self._derniere_session:
                    self._evenements.append(("graphe", "Nouveau résultat : %d ms" % a["resultat"]["mediane"]))
                self._derniere_session = cle
        # réunion dans 1 h, échéance à J-3
        r = _date_heure(self.config["reunion"].get("date"))
        if r and 0 < (r - datetime.now()).total_seconds() <= 3600 and self._une_fois(f"reunion:{r}"):
            self._evenements.append(("calendrier", "Réunion dans 1 h : notes prêtes ?"))
        e = self.prochaine_echeance()
        if e and e[0] == 3 and self._une_fois(f"j3:{e[1]}:{jour}"):
            self._evenements.append(("calendrier", "J-3 : %s" % e[1]))
        with self.verrou:
            if a != self.auto:
                self.auto = a
                self.version += 1

    def _une_fois(self, cle):
        with self.verrou:
            n = self.hist.setdefault("notifie", {})
            if cle in n:
                return False
            n[cle] = date.today().isoformat()
            for vieux in sorted(n, key=n.get)[:-100]:
                del n[vieux]
            return True

    # ------------------------------------------------------------ pour l'ESP32
    def prochaine_echeance(self):
        """(jours restants, titre) de la prochaine échéance (aujourd'hui compris), ou None."""
        aujourdhui = date.today()
        for e in self.config["echeances"]:
            d = _date(e.get("date"))
            if d and d >= aujourdhui:
                return (d - aujourdhui).days, e["titre"]
        return None

    def evenements(self):
        with self.verrou:
            ev, self._evenements = self._evenements, []
        return [(i, texte_ecran(t, 40)) for i, t in ev]

    def ligne_esp(self):
        """Ligne « MASTER {json} » (JSON en ASCII : les accents passent en \\u00e9)."""
        with self.verrou:
            c = self.config
            a = self.auto
            temps = int(self.hist["temps"].get(date.today().isoformat(), 0) // 60)
            d = {}
            e = self.prochaine_echeance()
            d["e"] = [e[0], texte_ecran(e[1], 40)] if e else None
            o = c["objectif"]
            d["o"] = [texte_ecran(o["texte"], 60), 1 if o["fait"] else 0] \
                if o.get("texte") and o.get("date") == date.today().isoformat() else None
            d["l"] = [a["lus"], c["objectif_articles"]] if a["lus"] >= 0 else None
            d["r"] = [a["mots_jour"], c["objectif_mots_jour"]] if a["mots_jour"] >= 0 else None
            d["t"] = temps
            r = a["resultat"]
            d["x"] = [r["mediane"], r["p95"], r["n"], texte_ecran(r["mode"], 10), texte_ecran(r["hz"], 5)] \
                if r else None
            d["c"] = a["courbe"]
            reu = _date_heure(c["reunion"].get("date"))
            if reu and reu >= datetime.now() - timedelta(hours=1):
                quand = "%d %s %02d:%02d" % (reu.day, MOIS[reu.month - 1], reu.hour, reu.minute)
                d["m"] = [texte_ecran(quand, 20), texte_ecran(c["reunion"].get("question", ""), 60)]
            else:
                d["m"] = None
            d["p"] = texte_ecran(c["phase"], 30)
            d["a"] = 1 if self.actif else 0
        return "MASTER " + json.dumps(d, ensure_ascii=True, separators=(",", ":"))
