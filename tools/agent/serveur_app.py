"""Serveur pour l'app Flutter (WebSocket, port 8765).

Le téléphone se connecte à ws://<adresse du PC>:8765 (à la maison, ou de partout avec Tailscale).

Messages (JSON, un par message) :
  téléphone -> PC
    {"type": "auth", "token": "..."}                 se reconnecter (téléphone déjà appairé)
    {"type": "demande_pin"}                          affiche un code à 6 chiffres sur l'ESP32
    {"type": "pin", "pin": "123456", "nom": "..."}   appairage avec le code
    {"type": "cmd", "ligne": "VOL+"}                 n'importe quelle commande (comme dans la console)
    {"type": "souris", "dx": 5, "dy": -3}            déplacement de souris (rapide, direct sur le PC)
    {"type": "clic", "bouton": "gauche"|"droit"}
    {"type": "molette", "n": -2}
    {"type": "texte", "texte": "Bonjour à tous"}     tape le texte (accents compris)
    {"type": "apps"}                                 liste des apps
    {"type": "app_ajout", "nom": "YouTube", "cible": "https://…", "sorte": "web"|"chemin"}
    {"type": "app_retrait", "nom": "YouTube"}
    {"type": "raccourcis"}                           liste des raccourcis (Phase 7)
    {"type": "rac_ajout", "raccourci": {nom, icone, etapes: [...]}, "ancien": "nom avant"}
    {"type": "rac_retrait", "nom": "Prépa jeu"}
    (lancer un raccourci : {"type": "cmd", "ligne": "RAC Prépa jeu"})
  PC -> téléphone
    {"type": "auth_requise"} {"type": "auth_ok", "token": "..."} {"type": "erreur", "texte": "..."}
    {"type": "pin_affiche"} {"type": "etat", ...} (4 fois / s) {"type": "rep", "ligne": ..., "texte": ...}
    {"type": "apps", "apps": [{"nom": ..., "cible": ..., "type": "web"|"chemin"|"autre"}, ...]}
    {"type": "raccourcis", "raccourcis": [{"nom": ..., "icone": ..., "etapes": [...]}, ...]}
"""
import asyncio
import json
import secrets as aleatoire
import threading
import time
from pathlib import Path

from websockets.asyncio.server import serve

PORT = 8765
DUREE_PIN = 120          # secondes
ESSAIS_PIN = 5


class ServeurApp:
    def __init__(self, fichier_appareils, rappels):
        """rappels : dict de fonctions fournies par l'agent :
        executer(ligne) -> str, etat() -> dict, apps() -> list, afficher_pin(pin),
        ajouter_app(nom, cible, sorte) -> (ok, texte), retirer_app(nom) -> (ok, texte),
        raccourcis() -> list, ajouter_raccourci(dict, ancien) -> (ok, texte),
        retirer_raccourci(nom) -> (ok, texte),
        souris(dx, dy), clic(bouton), molette(n), texte(t), connexion(nb_telephones)."""
        self.fichier = Path(fichier_appareils)
        self.r = rappels
        self.pin = None
        self.pin_expire = 0.0
        self.essais = 0
        self.clients = 0
        self.probleme = ""

    # ------------------------------------------------------------ appareils
    def _appareils(self):
        try:
            return json.loads(self.fichier.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _ajouter(self, nom):
        appareils = self._appareils()
        token = aleatoire.token_urlsafe(24)
        appareils[token] = {"nom": nom[:40], "depuis": time.strftime("%Y-%m-%d %H:%M")}
        self.fichier.write_text(json.dumps(appareils, ensure_ascii=False, indent=2), encoding="utf-8")
        return token

    def token_valide(self, token):
        return bool(token) and token in self._appareils()

    def nouveau_pin(self):
        self.pin = "%06d" % aleatoire.randbelow(1000000)
        self.pin_expire = time.time() + DUREE_PIN
        self.essais = 0
        return self.pin

    def verifier_pin(self, pin):
        if self.pin is None or time.time() > self.pin_expire:
            return False
        self.essais += 1
        if self.essais > ESSAIS_PIN:
            self.pin = None
            return False
        if aleatoire.compare_digest(str(pin), self.pin):
            self.pin = None
            return True
        return False

    # ------------------------------------------------------------ réseau
    def demarrer(self):
        threading.Thread(target=self._fil, daemon=True).start()

    def _fil(self):
        try:
            asyncio.run(self._principal())
        except Exception as e:
            self.probleme = f"serveur app : {e}"
            print(f"[agent] {self.probleme}")

    async def _principal(self):
        async with serve(self._client, "0.0.0.0", PORT, ping_interval=20, ping_timeout=20,
                         max_size=65536):
            print(f"[agent] serveur app prêt sur le port {PORT}")
            await asyncio.Future()

    async def _envoyer(self, ws, donnees):
        await ws.send(json.dumps(donnees, ensure_ascii=False))

    async def _pousser_etat(self, ws):
        while True:
            await self._envoyer(ws, {"type": "etat", **self.r["etat"]()})
            await asyncio.sleep(0.25)

    async def _client(self, ws):
        boucle = asyncio.get_running_loop()
        authentifie = False
        tache_etat = None
        await self._envoyer(ws, {"type": "auth_requise"})
        try:
            async for brut in ws:
                try:
                    m = json.loads(brut)
                    typ = m.get("type")
                except (ValueError, AttributeError):
                    continue
                if not authentifie:
                    if typ == "auth" and self.token_valide(m.get("token")):
                        authentifie = True
                    elif typ == "demande_pin":
                        pin = self.nouveau_pin()
                        await boucle.run_in_executor(None, self.r["afficher_pin"], pin)
                        await self._envoyer(ws, {"type": "pin_affiche"})
                        continue
                    elif typ == "pin" and self.verifier_pin(m.get("pin", "")):
                        token = self._ajouter(str(m.get("nom") or "Téléphone"))
                        await self._envoyer(ws, {"type": "auth_ok", "token": token})
                        authentifie = True
                    else:
                        await self._envoyer(ws, {"type": "erreur", "texte": "Non autorisé"})
                        continue
                    if authentifie:
                        if typ == "auth":
                            await self._envoyer(ws, {"type": "auth_ok", "token": m.get("token")})
                        self.clients += 1
                        await boucle.run_in_executor(None, self.r["connexion"], self.clients)
                        tache_etat = asyncio.create_task(self._pousser_etat(ws))
                    continue
                if typ == "souris":
                    self.r["souris"](int(m.get("dx", 0)), int(m.get("dy", 0)))
                elif typ == "clic":
                    self.r["clic"](m.get("bouton", "gauche"))
                elif typ == "molette":
                    self.r["molette"](int(m.get("n", 0)))
                elif typ == "texte":
                    await boucle.run_in_executor(None, self.r["texte"], str(m.get("texte", ""))[:500])
                elif typ == "apps":
                    await self._envoyer(ws, {"type": "apps", "apps": self.r["apps"]()})
                elif typ in ("app_ajout", "app_retrait"):
                    if typ == "app_ajout":
                        ok, texte = await boucle.run_in_executor(
                            None, self.r["ajouter_app"], str(m.get("nom", "")),
                            str(m.get("cible", "")), str(m.get("sorte", "")))
                    else:
                        ok, texte = await boucle.run_in_executor(
                            None, self.r["retirer_app"], str(m.get("nom", "")))
                    await self._envoyer(ws, {"type": "rep", "ligne": typ, "texte": texte, "ok": ok})
                    await self._envoyer(ws, {"type": "apps", "apps": self.r["apps"]()})
                elif typ == "raccourcis":
                    await self._envoyer(ws, {"type": "raccourcis", "raccourcis": self.r["raccourcis"]()})
                elif typ in ("rac_ajout", "rac_retrait"):
                    if typ == "rac_ajout":
                        ok, texte = await boucle.run_in_executor(
                            None, self.r["ajouter_raccourci"], m.get("raccourci"),
                            str(m.get("ancien") or ""))
                    else:
                        ok, texte = await boucle.run_in_executor(
                            None, self.r["retirer_raccourci"], str(m.get("nom", "")))
                    await self._envoyer(ws, {"type": "rep", "ligne": typ, "texte": texte, "ok": ok})
                    await self._envoyer(ws, {"type": "raccourcis", "raccourcis": self.r["raccourcis"]()})
                elif typ == "cmd":
                    ligne = str(m.get("ligne", ""))[:200]
                    texte = await boucle.run_in_executor(None, self.r["executer"], ligne)
                    await self._envoyer(ws, {"type": "rep", "ligne": ligne, "texte": texte})
        except Exception:
            pass  # téléphone déconnecté
        finally:
            if tache_etat is not None:
                tache_etat.cancel()
            if authentifie:
                self.clients = max(0, self.clients - 1)
                try:
                    self.r["connexion"](self.clients)
                except Exception:
                    pass
