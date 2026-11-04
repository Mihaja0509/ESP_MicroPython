"""Position de la vidéo en cours (Phase 11-bis), lue dans les contrôles multimédias de Windows.

C'est la même information que le petit lecteur que Windows affiche quand on change le volume
(« Global System Media Transport Controls ») : Chrome, Edge, Firefox, l'app Netflix… la donnent.
VLC 3 ne la donne pas (sauf avec le plugin vlc-win10smtc).

Dépendance (dans le Python de la tâche planifiée) :
    py -m pip install --user winrt-runtime winrt-Windows.Foundation winrt-Windows.Media.Control
Sans ces paquets, tout continue de marcher, simplement sans barre d'avancement.

Windows ne met pas la position à jour en continu : elle est valable à l'instant last_updated_time.
Pendant la lecture, on ajoute donc le temps écoulé depuis cet instant.
"""
import asyncio
import threading
import time
from datetime import datetime, timezone

try:
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as Gestionnaire,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as Statut,
    )
except ImportError:
    Gestionnaire = None
    Statut = None

IGNORER = ("spotify",)   # musique : jamais prise pour la vidéo en cours


class LecteurMedia:
    """Fil à part : une fois par seconde, lit la session multimédia courante de Windows."""

    def __init__(self):
        self.infos = None
        if Gestionnaire is None:
            self.probleme = ("paquets winrt absents (barre d'avancement des vidéos désactivée) : "
                             "py -m pip install --user winrt-runtime winrt-Windows.Foundation "
                             "winrt-Windows.Media.Control")
            return
        self.probleme = ""
        threading.Thread(target=self._fil, daemon=True).start()

    def _fil(self):
        try:
            asyncio.run(self._boucle())
        except Exception as e:  # ne doit jamais arrêter l'agent
            self.infos = None
            self.probleme = f"lecteur média arrêté : {e!r}"

    async def _boucle(self):
        gestionnaire = await Gestionnaire.request_async()
        while True:
            try:
                self.infos = await self._lire(gestionnaire)
                self.probleme = ""
            except Exception as e:
                self.infos = None
                self.probleme = f"lecteur média : {e!r}"
            await asyncio.sleep(1)

    async def _lire(self, gestionnaire):
        session = gestionnaire.get_current_session()
        if session is None:
            return None
        appli = (session.source_app_user_model_id or "").lower()
        if any(m in appli for m in IGNORER):
            return None
        tl = session.get_timeline_properties()
        duree = (tl.end_time - tl.start_time).total_seconds()
        if duree <= 1:
            return None  # direct, publicité ou pas de durée connue
        pos = (tl.position - tl.start_time).total_seconds()
        lecture = session.get_playback_info().playback_status == Statut.PLAYING
        if lecture:
            maj = tl.last_updated_time
            if isinstance(maj, datetime) and maj.year > 1700:  # date vide = 1601
                if maj.tzinfo is None:
                    maj = maj.replace(tzinfo=timezone.utc)
                ecart = (datetime.now(timezone.utc) - maj).total_seconds()
                if 0 < ecart < 6 * 3600:
                    pos += ecart
        titre = ""
        try:
            props = await session.try_get_media_properties_async()
            titre = (props.title or "") if props is not None else ""
        except Exception:
            pass
        return {"pos": int(max(0, min(pos, duree))), "duree": int(duree), "lecture": bool(lecture),
                "titre": titre, "appli": appli, "t": time.time()}

    def actuel(self):
        """Dernière lecture (moins de 5 s), ou None."""
        i = self.infos
        if not i or time.time() - i["t"] > 5:
            return None
        return i
