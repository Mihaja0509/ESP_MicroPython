# Mini serveur HTTP de la carte (Wi-Fi, port 80), sans bloquer l'écran : accept non bloquant,
# une requête traitée par tour de boucle. Ne touche pas au chemin USB (FPS, état du PC).
#   GET /mesure           -> {"ok":true,"t":23.4,"h":58,"p":998.2}  (lecture seule, sans jeton)
#   GET /ir?mode=cool&temp=24&vent=auto&swing=0&power=0   -> envoie la trame IR (jeton obligatoire)
# Le jeton est WEB_TOKEN dans /secrets.py (en-tête X-Token). Sans WEB_TOKEN, /ir est désactivé.
import json
import socket

import ir


class Web:
    def __init__(self, reglages, wlan_connecte, mesure):
        self.token = getattr(reglages, "WEB_TOKEN", "") or ""
        self.connecte = wlan_connecte   # fonction () -> bool
        self.mesure = mesure            # fonction () -> (°C, %, hPa) ou None
        self.srv = None

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
                conn.send(("HTTP/1.0 %s\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n%s"
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
            recu = ""
            for l in texte.split("\r\n")[1:]:
                nom, _, val = l.partition(":")
                if nom.strip().lower() == "x-token":
                    recu = val.strip()
            if recu != self.token:
                return "401 Unauthorized", {"ok": False}
            p = {}
            for kv in requete.split("&"):
                k, _, v = kv.partition("=")
                p[k] = v
            err = ir.commande([p.get("mode", ""), p.get("temp", ""), p.get("vent", "auto"),
                               p.get("swing", "0"), p.get("power", "0")])
            return ("200 OK", {"ok": True}) if err is None else ("400 Bad Request", {"ok": False, "raison": err})
        return "404 Not Found", {"ok": False}
