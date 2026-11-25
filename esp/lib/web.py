# Mini serveur HTTP de la carte (Wi-Fi, port 80), sans bloquer l'écran : accept non bloquant,
# une requête traitée par tour de boucle. Ne touche pas au chemin USB (FPS, état du PC).
#   GET /mesure           -> {"ok":true,"t":23.4,"h":58,"p":998.2}  (lecture seule, sans jeton)
#   GET /ir?mode=cool&temp=24&vent=auto&swing=0&power=0   -> envoie la trame IR (jeton obligatoire)
# Le jeton est WEB_TOKEN dans /secrets.py (en-tête X-Token). Sans WEB_TOKEN, /ir est désactivé.
import json
import socket
import time

import ir


class Web:
    def __init__(self, reglages, wlan_connecte, mesure, actions=None):
        self.token = getattr(reglages, "WEB_TOKEN", "") or ""
        self.connecte = wlan_connecte   # fonction () -> bool
        self.mesure = mesure            # fonction () -> (°C, %, hPa) ou None
        self.actions = actions or {}    # "ecran": fn(bool), "reset": fn()
        self.srv = None
        self.histo = []                 # [(ticks, °C, %, hPa)] : un point toutes les 5 min, 24 h
        self._dernier_point = None

    def noter(self, maintenant, mesure):
        """Garde un point d'historique toutes les 5 minutes (en RAM, perdu au redémarrage)."""
        if mesure is None:
            return
        if self._dernier_point is not None and time.ticks_diff(maintenant, self._dernier_point) < 300000:
            return
        self._dernier_point = maintenant
        t, h, p = mesure
        self.histo.append((maintenant, round(t, 1), round(h) if h >= 0 else None, round(p, 1) if p else None))
        if len(self.histo) > 288:
            self.histo.pop(0)

    def _jeton_ok(self, texte):
        recu = ""
        for l in texte.split("\r\n")[1:]:
            nom, _, val = l.partition(":")
            if nom.strip().lower() == "x-token":
                recu = val.strip()
        return bool(self.token) and recu == self.token

    def _ouvrir(self):
        try:
            s = socket.socket()
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", 80))
            s.listen(2)
            s.setblocking(False)
            self.srv = s
        except Exception:
            self.srv = None

    def pas(self):
        """À appeler à chaque tour de boucle. Ne lève jamais d'exception."""
        try:
            if not self.connecte():
                return
            if self.srv is None:
                self._ouvrir()
                return
            try:
                conn, _ = self.srv.accept()
            except OSError:
                return
            try:
                conn.settimeout(0.3)
                data = conn.recv(600)
                code, corps = self._repondre(data)
                conn.settimeout(2)
                conn.sendall(("HTTP/1.0 %s\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n%s"
                              % (code, json.dumps(corps))).encode())
            except Exception:
                pass
            finally:
                conn.close()
        except Exception:
            self.srv = None

    def _repondre(self, data):
        try:
            texte = data.decode()
            ligne = texte.split("\r\n", 1)[0].split(" ")
            if ligne[0] != "GET":
                return "405 Method Not Allowed", {"ok": False}
            chemin, _, requete = ligne[1].partition("?")
        except Exception:
            return "400 Bad Request", {"ok": False}
        if chemin == "/mesure":
            m = self.mesure()
            if m is None:
                return "200 OK", {"ok": False}
            t, h, p = m
            return "200 OK", {"ok": True, "t": round(t, 1), "h": round(h) if h >= 0 else None,
                              "p": round(p, 1) if p else None}
        if chemin == "/ir":
            if not self.token:
                return "403 Forbidden", {"ok": False, "raison": "WEB_TOKEN absent de secrets.py"}
            if not self._jeton_ok(texte):
                return "401 Unauthorized", {"ok": False}
            p = {}
            for kv in requete.split("&"):
                k, _, v = kv.partition("=")
                p[k] = v
            err = ir.commande([p.get("mode", ""), p.get("temp", ""), p.get("vent", "auto"),
                               p.get("swing", "0"), p.get("power", "0")])
            return ("200 OK", {"ok": True}) if err is None else ("400 Bad Request", {"ok": False, "raison": err})
        if chemin == "/historique":
            # lecture seule : points de 5 min, « age » = secondes depuis la mesure
            now = time.ticks_ms()
            return "200 OK", {"ok": True, "pas_s": 300, "points": [
                {"age": time.ticks_diff(now, x[0]) // 1000, "t": x[1], "h": x[2], "p": x[3]} for x in self.histo]}
        if chemin in ("/ecran", "/redemarrer"):
            if not self.token:
                return "403 Forbidden", {"ok": False, "raison": "WEB_TOKEN absent de secrets.py"}
            if not self._jeton_ok(texte):
                return "401 Unauthorized", {"ok": False}
            if chemin == "/ecran":
                if "ecran" not in self.actions:
                    return "404 Not Found", {"ok": False}
                self.actions["ecran"]("on=0" not in requete)
            else:
                self.actions["reset"]()
            return "200 OK", {"ok": True}
        return "404 Not Found", {"ok": False}
