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
    {"type": "apercu", "ecran": 0, "largeur": 960, "qualite": 60}   une image de l'écran (Phase 8)
    {"type": "pointeur", "ecran": 0, "x": 0.5, "y": 0.5, "clic": "gauche"|"droit"|"double"|""}
  PC -> téléphone
    {"type": "auth_requise"} {"type": "auth_ok", "token": "..."} {"type": "erreur", "texte": "..."}
    {"type": "pin_affiche"} {"type": "etat", ...} (4 fois / s) {"type": "rep", "ligne": ..., "texte": ...}
    {"type": "apps", "apps": [{"nom": ..., "cible": ..., "type": "web"|"chemin"|"autre"}, ...]}
    {"type": "raccourcis", "raccourcis": [{"nom": ..., "icone": ..., "etapes": [...]}, ...]}
    {"type": "apercu_info", "ecran": 0, "ecrans": 1, "largeur": 2560, "hauteur": 1600, "verrou": false}
    puis l'image JPEG en message binaire ; {"type": "apercu_erreur", "texte": "..."}
  Phase 11 :
    {"type": "master"} -> {"type": "master", config, auto, temps_jour, chemins_ok, phases, version}
    {"type": "master_maj", "master": {…partie des réglages…}} -> rep (ligne « master_maj ») + master
    {"type": "master_afficher"} -> rep : la scène master s'affiche 15 s sur l'ESP32
    {"type": "jeux"} -> {"type": "jeux", stats, semaine, jeux, pas_des_jeux, en_cours}
    {"type": "jeux_maj", "jeux": [...], "pas_des_jeux": [...]} et {"type": "pas_un_jeu"} -> rep + jeux

Widget Android (Phase 8) : requête HTTP simple sur le même port, sans WebSocket :
  GET /widget?ligne=PLAY   avec l'en-tête « X-Token: <token du téléphone> »
  -> texte de la réponse (comme dans la console), 401 si le téléphone n'est pas appairé.
  GET /etat_court (même en-tête, Phase 11) -> JSON {repos_min, verrou, jeu, video, arret}
  pour la notification « PC inutilisé » du téléphone.
"""
import asyncio
import json
import secrets as aleatoire
import threading
import time
import urllib.parse
from http import HTTPStatus
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
        souris(dx, dy), clic(bouton), molette(n), texte(t), connexion(nb_telephones),
        apercu(ecran, largeur, qualite) -> (octets, infos) | (None, problème),
        pointeur(ecran, x, y, clic)."""
        self.fichier = Path(fichier_appareils)
        self.r = rappels
        self.pin = None
        self.pin_expire = 0.0
        self.essais = 0
        self.clients = 0
        self.probleme = ""
        # Phase 13 : mesures pour la souris (voir _veille_boucle)
        self.stats = {"n": 0, "ecart": 0.0, "boucle": 0.0, "appel": 0.0, "dernier": 0.0}

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
                         max_size=65536, process_request=self._http):
            print(f"[agent] serveur app prêt sur le port {PORT}")
            asyncio.create_task(self._veille_boucle())
            await asyncio.Future()

    async def _http(self, connexion, requete):
        """Requêtes HTTP simples (widget Android). None = on continue en WebSocket."""
        morceaux = urllib.parse.urlsplit(requete.path)
        if morceaux.path not in ("/widget", "/etat_court"):
            return None
        if not self.token_valide(requete.headers.get("X-Token", "")):
            return connexion.respond(HTTPStatus.UNAUTHORIZED, "Unauthorized\n")
        if morceaux.path == "/etat_court":
            try:
                court = self.r["etat_court"]()
            except Exception as e:
                court = {"erreur": str(e)}
            return connexion.respond(HTTPStatus.OK, json.dumps(court, ensure_ascii=False))
        ligne = (urllib.parse.parse_qs(morceaux.query).get("ligne") or [""])[0].strip()[:200]
        if not ligne:
            return connexion.respond(HTTPStatus.BAD_REQUEST, "Empty command\n")
        boucle = asyncio.get_running_loop()
        try:
            texte = await boucle.run_in_executor(None, self.r["executer"], ligne)
        except Exception as e:
            texte = f"Error: {e}"
        return connexion.respond(HTTPStatus.OK, (texte or "OK") + "\n")

    async def _apercu(self, ws, m, etat):
        """Capture puis envoie une image (une seule à la fois par téléphone)."""
        try:
            octets, infos = await asyncio.get_running_loop().run_in_executor(
                None, self.r["apercu"], int(m.get("ecran", 0)), int(m.get("largeur", 960)),
                int(m.get("qualite", 60)))
            if octets is None:
                await self._envoyer(ws, {"type": "apercu_erreur", "texte": infos})
            else:
                await self._envoyer(ws, {"type": "apercu_info", **infos})
                await ws.send(octets)
        except Exception:
            pass
        finally:
            etat["apercu"] = False

    async def _envoyer(self, ws, donnees):
        await ws.send(json.dumps(donnees, ensure_ascii=False))

    async def _appel(self, nom, *args):
        """Appelle une fonction de l'agent dans un fil à part : la boucle réseau (et donc la
        souris) ne reste jamais bloquée par une lecture de fichier."""
        return await asyncio.get_running_loop().run_in_executor(None, self.r[nom], *args)

    def _noter_souris(self, dx, dy):
        s = self.stats
        t0 = time.perf_counter()
        if s["dernier"] and t0 - s["dernier"] < 1.0:  # même geste : plus grand silence entre 2 messages
            s["ecart"] = max(s["ecart"], t0 - s["dernier"])
        s["dernier"] = t0
        self.r["souris"](dx, dy)
        s["appel"] = max(s["appel"], time.perf_counter() - t0)
        s["n"] += 1

    async def _veille_boucle(self):
        """Souris saccadée ? Mesure ce qui coince : boucle réseau bloquée, silence du téléphone
        ou SendInput lent. Une ligne dans agent.log toutes les 10 s, seulement si on s'est servi
        de la souris."""
        s = self.stats
        attendu = time.perf_counter() + 0.05
        debut = time.monotonic()
        while True:
            await asyncio.sleep(0.05)
            maintenant = time.perf_counter()
            s["boucle"] = max(s["boucle"], maintenant - attendu)
            attendu = maintenant + 0.05
            if time.monotonic() - debut >= 10:
                if s["n"]:
                    print("[agent] souris : %d msg / 10 s, ecart max %d ms, boucle max %d ms, "
                          "SendInput max %d ms" % (s["n"], s["ecart"] * 1000, s["boucle"] * 1000,
                                                   s["appel"] * 1000))
                s.update(n=0, ecart=0.0, boucle=0.0, appel=0.0)
                debut = time.monotonic()

    async def _pousser_etat(self, ws):
        while True:
            await self._envoyer(ws, {"type": "etat", **self.r["etat"]()})
            await asyncio.sleep(0.25)

    async def _client(self, ws):
        boucle = asyncio.get_running_loop()
        authentifie = False
        tache_etat = None
        etat_client = {"apercu": False}
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
                        token = self._ajouter(str(m.get("nom") or "Phone"))
                        await self._envoyer(ws, {"type": "auth_ok", "token": token})
                        authentifie = True
                    else:
                        await self._envoyer(ws, {"type": "erreur", "texte": "Unauthorized"})
                        continue
                    if authentifie:
                        if typ == "auth":
                            await self._envoyer(ws, {"type": "auth_ok", "token": m.get("token")})
                        self.clients += 1
                        await boucle.run_in_executor(None, self.r["connexion"], self.clients)
                        tache_etat = asyncio.create_task(self._pousser_etat(ws))
                    continue
                if typ == "souris":
                    self._noter_souris(int(m.get("dx", 0)), int(m.get("dy", 0)))
                elif typ == "clic":
                    self.r["clic"](m.get("bouton", "gauche"))
                elif typ == "molette":
                    self.r["molette"](int(m.get("n", 0)))
                elif typ == "texte":
                    await boucle.run_in_executor(None, self.r["texte"], str(m.get("texte", ""))[:500])
                elif typ == "apps":
                    await self._envoyer(ws, {"type": "apps", "apps": (await self._appel("apps"))})
                elif typ in ("app_ajout", "app_retrait"):
                    if typ == "app_ajout":
                        ok, texte = await boucle.run_in_executor(
                            None, self.r["ajouter_app"], str(m.get("nom", "")),
                            str(m.get("cible", "")), str(m.get("sorte", "")))
                    else:
                        ok, texte = await boucle.run_in_executor(
                            None, self.r["retirer_app"], str(m.get("nom", "")))
                    await self._envoyer(ws, {"type": "rep", "ligne": typ, "texte": texte, "ok": ok})
                    await self._envoyer(ws, {"type": "apps", "apps": (await self._appel("apps"))})
                elif typ == "raccourcis":
                    await self._envoyer(ws, {"type": "raccourcis", "raccourcis": (await self._appel("raccourcis"))})
                elif typ in ("rac_ajout", "rac_retrait"):
                    if typ == "rac_ajout":
                        ok, texte = await boucle.run_in_executor(
                            None, self.r["ajouter_raccourci"], m.get("raccourci"),
                            str(m.get("ancien") or ""))
                    else:
                        ok, texte = await boucle.run_in_executor(
                            None, self.r["retirer_raccourci"], str(m.get("nom", "")))
                    await self._envoyer(ws, {"type": "rep", "ligne": typ, "texte": texte, "ok": ok})
                    await self._envoyer(ws, {"type": "raccourcis", "raccourcis": (await self._appel("raccourcis"))})
                elif typ == "apercu":
                    if not etat_client["apercu"]:  # sinon on attend la fin de l'image en cours
                        etat_client["apercu"] = True
                        asyncio.create_task(self._apercu(ws, m, etat_client))
                elif typ == "master":
                    await self._envoyer(ws, {"type": "master", **(await self._appel("master"))})
                elif typ == "master_maj":
                    ok, texte = await boucle.run_in_executor(None, self.r["master_maj"], m.get("master"))
                    await self._envoyer(ws, {"type": "rep", "ligne": typ, "texte": texte, "ok": ok})
                    await self._envoyer(ws, {"type": "master", **(await self._appel("master"))})
                elif typ == "master_afficher":
                    ok, texte = self.r["master_afficher"]()
                    await self._envoyer(ws, {"type": "rep", "ligne": typ, "texte": texte, "ok": ok})
                elif typ == "jeux":
                    await self._envoyer(ws, {"type": "jeux", **(await self._appel("jeux"))})
                elif typ in ("jeux_maj", "pas_un_jeu"):
                    if typ == "jeux_maj":
                        ok, texte = await boucle.run_in_executor(
                            None, self.r["jeux_maj"], m.get("jeux"), m.get("pas_des_jeux"))
                    else:
                        ok, texte = await boucle.run_in_executor(None, self.r["pas_un_jeu"])
                    await self._envoyer(ws, {"type": "rep", "ligne": typ, "texte": texte, "ok": ok})
                    await self._envoyer(ws, {"type": "jeux", **(await self._appel("jeux"))})
                elif typ == "sites":
                    await self._envoyer(ws, {"type": "sites", **(await self._appel("sites"))})
                elif typ == "sites_maj":
                    ok, texte = await boucle.run_in_executor(None, self.r["sites_maj"], m.get("sites"))
                    await self._envoyer(ws, {"type": "rep", "ligne": typ, "texte": texte, "ok": ok})
                    await self._envoyer(ws, {"type": "sites", **(await self._appel("sites"))})
                elif typ == "pointeur":
                    await boucle.run_in_executor(
                        None, self.r["pointeur"], int(m.get("ecran", 0)), float(m.get("x", 0)),
                        float(m.get("y", 0)), str(m.get("clic", "")))
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
