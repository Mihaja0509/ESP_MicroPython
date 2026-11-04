# Micro — Phase 11-bis : plantage de l'agent, barre d'avancement des vidéos (VLC compris), sites vidéo, interface en anglais

Date : 2026-11-04 · Statut : à appliquer · Base : commit e4214ad (« Phase 11 »).

## Ce que contient la phase

1. **Plantage de l'agent (violation d'accès 0xC0000005).** Depuis la Phase 10, `son_en_cours()` (détection du son pour la scène cinéma) gardait un pointeur COM obtenu par `cast(...)`. Un `cast` ne garde pas l'objet Windows en vie : quand Python libérait la variable `itf`, Windows détruisait le compteur de son, et la lecture suivante (`GetPeakValue`) lisait de la mémoire libérée. Python plantait sans Traceback, de façon aléatoire. C'est le plantage de 00:27 : il arrive juste après `PresentMon : OK`, au moment où la détection vidéo démarre. Correctif : `QueryInterface`, qui garde l'objet en vie, et l'appareil audio gardé lui aussi.
2. **Traceur de plantage** (`faulthandler`) dans `agent.log` : si Python plante encore dans du code natif, la pile exacte de chaque fil sera écrite dans le journal.
3. **Barre d'avancement des vidéos** (demande de Mihaja) : dans la scène cinéma de l'ESP32, sous le titre, on voit le temps écoulé, la durée, une barre et un curseur, par exemple « 02:32 … 24:04 ». « Pause » s'affiche en orange quand la vidéo est en pause. La carte Cinéma de l'app a la même barre. La position vient des contrôles multimédias de Windows (le petit lecteur qui s'affiche quand on change le volume) : Chrome, Edge, Firefox et l'app Netflix la donnent ; **VLC aussi grâce au plugin libwin10smtc v5.0.0** fourni par Mihaja (`D:\libwin10smtc_plugin_v5.0.0_x64.zip`), que Claude Code installe et active (Partie 0). Windows ne met pas la position à jour en continu : l'agent la fait avancer lui-même pendant la lecture, et l'ESP32 la fait avancer entre deux messages. Le titre donné par Windows sert aussi quand la fenêtre n'en a pas (app Netflix : titre de l'épisode). Nouveau fichier `tools/agent/media_windows.py`, dans son propre fil. Il faut 3 paquets Python ; sans eux, tout marche, simplement sans barre.
4. **Sites vidéo modifiables depuis l'app** (demande de Mihaja) : nouvelle carte « Sites vidéo » dans Réglages. Pour un site que le PC ne reconnaît pas, on donne un mot du titre de l'onglet et le nom à afficher ; l'app peut proposer le mot à partir de l'onglet ouvert sur le PC. Enregistré sur le PC dans `tools\agent\sites_video.json` (jamais dans Git), relu toutes les 10 s, et cherché avant les sites connus d'office.
5. **Interface en anglais** : tout ce que Mihaja **voit** sur l'écran de l'ESP32, dans l'app Dadou, dans le widget et dans la notification Android passe en anglais (demande de Mihaja). Claude Code fait la traduction en suivant les règles de la Partie 2.

## Partie 0 — Plugin VLC (Claude Code fait tout le nécessaire)

But : VLC donne à Windows la position de la vidéo, donc l'ESP32 et l'app affichent la barre d'avancement aussi pour VLC. Les étapes qui écrivent dans `C:\Program Files` demandent les droits administrateur : si tu ne les as pas, donne à Mihaja la commande exacte à lancer dans un PowerShell administrateur, attends son retour, puis continue.

1. **Trouver VLC** : `C:\Program Files\VideoLAN\VLC\vlc.exe`, sinon le dossier `InstallDir` de `HKLM\SOFTWARE\VideoLAN\VLC` (ou `HKLM\SOFTWARE\WOW6432Node\VideoLAN\VLC`). Donne la version (`(Get-Item vlc.exe).VersionInfo.ProductVersion`).
2. **Architecture de VLC** (pas celle du PC) : lis l'en-tête PE de `vlc.exe` (champ Machine : `0x8664` = x64, `0x14c` = x86). Le zip de Mihaja est **x64**. Si VLC est x86, arrête-toi et dis à Mihaja de télécharger la version x86 du plugin.
3. **Contenu du zip** `D:\libwin10smtc_plugin_v5.0.0_x64.zip` : liste-le et lis le README ou les notes qu'il contient. Si ses instructions diffèrent de ce qui suit, ce sont les siennes qui comptent : dis-moi ce qui diffère.
4. **Visual C++ 2022 Redistributable x64** : vérifie `HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64` (`Installed` = 1, `Major` = 14, `Minor` ≥ 30). S'il manque : `winget install --id Microsoft.VCRedist.2015+.x64 -e` (administrateur), ou le lien officiel de Microsoft `https://aka.ms/vs/17/release/vc_redist.x64.exe`.
5. **Fermer VLC** (aucun `vlc.exe` en cours), puis copier `libwin10smtc_plugin.dll` du zip dans `<dossier de VLC>\plugins\misc\` (administrateur). Si un ancien `libwin10smtc_plugin.dll` est déjà là, remplace-le.
6. **Cache des plugins** : si `<dossier de VLC>\vlc-cache-gen.exe` existe, lance `& "<dossier de VLC>\vlc-cache-gen.exe" "<dossier de VLC>\plugins"` (administrateur).
7. **Activer le plugin** dans VLC : c'est l'interface de contrôle « Windows 10 SMTC integration » (Outils → Préférences → Afficher les paramètres : Tous → Interface → Interfaces de contrôle → cocher, puis Enregistrer).
   - Essaie d'abord de le faire dans le fichier de réglages `%APPDATA%\vlc\vlcrc` : trouve le nom court du module (README du zip, ou `& "<VLC>\vlc.exe" --list` qui écrit la liste des modules ; cherche « smtc »). Mets ce nom dans la ligne `control=` (décommente-la si besoin ; s'il y a déjà des valeurs, ajoute-le après une virgule). Garde une copie `vlcrc.avant_smtc`.
   - Si tu ne trouves pas le nom court avec certitude, n'invente rien : donne à Mihaja les clics ci-dessus, en anglais et en français (« Tools → Preferences → Show settings: All → Interface → Control interfaces → Windows 10 SMTC integration → Save »).
8. **Vérification** : un petit script **temporaire** (non commité), lancé avec le Python de la tâche après l'installation des paquets winrt (Partie 1), qui affiche la session multimédia courante de Windows : `source_app_user_model_id`, titre, position et durée (`GlobalSystemMediaTransportControlsSessionManager.request_async()`, `get_current_session()`, `get_timeline_properties()`, `try_get_media_properties_async()`). Demande à Mihaja d'ouvrir une vidéo dans VLC, lance le script : l'appli doit contenir « vlc » et la durée doit être > 0. Refais le test avec une vidéo YouTube dans Chrome.

## Partie 1 — Nouveaux fichiers

### `tools/agent/media_windows.py`

```python
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
```

### `app/lib/widgets/sites_video.dart`

```dart
// Carte « Sites vidéo » des Réglages (Phase 11-bis) : pour qu'un site de vidéos que le PC ne connaît
// pas déclenche quand même la scène cinéma. On donne un mot présent dans le titre de l'onglet et le nom
// à afficher. Enregistré sur le PC (tools\agent\sites_video.json).
import 'package:flutter/material.dart';

import '../connexion.dart';
import '../theme.dart';

class CarteSitesVideo extends StatefulWidget {
  final Connexion cx;

  const CarteSitesVideo({super.key, required this.cx});

  @override
  State<CarteSitesVideo> createState() => _CarteSitesVideoState();
}

class _CarteSitesVideoState extends State<CarteSitesVideo> {
  final _mot = TextEditingController();
  final _nom = TextEditingController();
  bool _ouvert = false;

  Connexion get cx => widget.cx;

  @override
  void dispose() {
    _mot.dispose();
    _nom.dispose();
    super.dispose();
  }

  List<Map<String, String>> _liste(dynamic v) => [
        if (v is List)
          for (final s in v)
            if (s is Map) {'mot': (s['mot'] ?? '').toString(), 'nom': (s['nom'] ?? '').toString()},
      ];

  Future<void> _ajouter(List<Map<String, String>> perso) async {
    final mot = _mot.text.trim().toLowerCase();
    final nom = _nom.text.trim();
    if (mot.length < 3 || nom.isEmpty) {
      cx.annoncer('Mot de 3 lettres au moins, et un nom');
      return;
    }
    FocusScope.of(context).unfocus();
    final (ok, _) = await cx.majSites([
      ...perso.where((s) => s['mot'] != mot),
      {'mot': mot, 'nom': nom},
    ]);
    if (ok) {
      _mot.clear();
      _nom.clear();
    }
  }

  /// Propose un mot tiré du titre de l'onglet ouvert sur le PC (« Titre - MonSite - Google Chrome »).
  void _depuisOnglet(String onglet) {
    final morceaux = onglet
        .split(RegExp(r'\s+[-–—|]\s+'))
        .map((m) => m.trim())
        .where((m) => m.isNotEmpty && !RegExp(r'chrome|edge|firefox|opera|brave|vivaldi', caseSensitive: false).hasMatch(m))
        .toList();
    if (morceaux.isEmpty) return;
    final site = morceaux.last;
    setState(() {
      _mot.text = site.toLowerCase();
      _nom.text = site.length > 20 ? site.substring(0, 20) : site;
    });
  }

  @override
  Widget build(BuildContext context) {
    final s = cx.sites;
    final perso = _liste(s?['perso']);
    final defaut = _liste(s?['defaut']);
    final onglet = (s?['onglet'] ?? '').toString();
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: () {
              setState(() => _ouvert = !_ouvert);
              if (_ouvert) cx.demanderSites();
            },
            child: Row(
              children: [
                const Expanded(child: Titre('Sites vidéo', icone: Icons.local_movies_rounded)),
                Icon(_ouvert ? Icons.expand_less_rounded : Icons.expand_more_rounded, color: Couleurs.gris),
              ],
            ),
          ),
          if (!_ouvert)
            const Text(
              "Un site de vidéos n'est pas reconnu ? Ajoute-le ici pour avoir la scène cinéma.",
              style: TextStyle(color: Couleurs.gris, fontSize: 12),
            )
          else if (s == null)
            const Padding(
              padding: EdgeInsets.all(8),
              child: Center(child: CircularProgressIndicator()),
            )
          else ...[
            const Text(
              "Ouvre la vidéo sur le PC, puis donne un mot qui est dans le titre de l'onglet "
              "(souvent le nom du site) et le nom à afficher sur l'ESP32.",
              style: TextStyle(color: Couleurs.gris, fontSize: 12),
            ),
            if (onglet.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Onglet ouvert sur le PC : $onglet',
                  maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12)),
              TextButton.icon(
                icon: const Icon(Icons.auto_fix_high_rounded, size: 18),
                label: const Text('Utiliser cet onglet'),
                onPressed: () => _depuisOnglet(onglet),
              ),
            ],
            TextButton.icon(
              icon: const Icon(Icons.refresh_rounded, size: 18),
              label: const Text("Relire l'onglet du PC"),
              onPressed: cx.demanderSites,
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _mot,
                    decoration: const InputDecoration(
                      labelText: 'Mot du titre',
                      hintText: 'ex. voiranime',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _nom,
                    maxLength: 20,
                    decoration: const InputDecoration(
                      labelText: 'Nom affiché',
                      hintText: 'ex. VoirAnime',
                      border: OutlineInputBorder(),
                      isDense: true,
                      counterText: '',
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            FilledButton.icon(
              icon: const Icon(Icons.add_rounded),
              label: const Text('Ajouter'),
              onPressed: () => _ajouter(perso),
            ),
            const SizedBox(height: 12),
            const Text('Mes sites', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            if (perso.isEmpty)
              const Text('(aucun)', style: TextStyle(color: Couleurs.gris, fontSize: 12))
            else
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final site in perso)
                    InputChip(
                      label: Text('${site['mot']} → ${site['nom']}', style: const TextStyle(fontSize: 12)),
                      onDeleted: () => cx.majSites(perso.where((x) => x['mot'] != site['mot']).toList()),
                    ),
                ],
              ),
            const SizedBox(height: 10),
            Text(
              'Déjà reconnus : ${{for (final d in defaut) d['nom']}.join(', ')}, '
              'et les lecteurs VLC, MPC, PotPlayer, Films et TV, app Netflix.',
              style: const TextStyle(color: Couleurs.gris, fontSize: 12),
            ),
          ],
        ],
      ),
    );
  }
}
```

**Paquets à installer** dans le Python **utilisé par la tâche planifiée**. Trouve-le avec `(Get-ScheduledTask "ESP32 Telecommande Agent").Actions` : c'est le `pythonw.exe` indiqué, il faut prendre le `python.exe` du même dossier. Puis :
`<ce python.exe> -m pip install --user winrt-runtime winrt-Windows.Foundation winrt-Windows.Media.Control`
Vérifie ensuite : `<ce python.exe> -c "from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager; print('ok')"`.

## Partie 1 bis — Modifications « avant → après » (exactes, dans l'ordre)

### Modification 1 — `tools/agent/agent_pc.py`

Module faulthandler : si Python plante encore (erreur native), la ligne exacte sera écrite dans agent.log.

**Avant :**

```python
import ctypes
import glob
```

**Après :**

```python
import ctypes
import faulthandler
import glob
```

### Modification 2 — `tools/agent/agent_pc.py`

Mesure du son : garder un vrai pointeur COM (QueryInterface) et l'appareil audio, au lieu d'un cast qui laissait Windows libérer l'objet (cause de la violation d'accès 0xC0000005).

**Avant :**

```python
            from ctypes import POINTER, cast
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import IAudioMeterInformation
            dev = AudioUtilities.GetSpeakers()
            brut = getattr(dev, "_dev", dev)  # pycaw récent : objet AudioDevice
            itf = brut.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
            _COMPTEUR_SON["m"] = cast(itf, POINTER(IAudioMeterInformation))
            _COMPTEUR_SON["t"] = time.time()
```

**Après :**

```python
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import IAudioMeterInformation
            dev = AudioUtilities.GetSpeakers()
            brut = getattr(dev, "_dev", dev)  # pycaw récent : objet AudioDevice
            itf = brut.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
            # QueryInterface renvoie un pointeur COM qui garde l'objet en vie (un simple cast ne le
            # faisait pas : Windows libérait l'objet et la lecture suivante plantait Python).
            _COMPTEUR_SON["m"] = itf.QueryInterface(IAudioMeterInformation)
            _COMPTEUR_SON["dev"] = brut  # garde aussi l'appareil audio en vie
            _COMPTEUR_SON["t"] = time.time()
```

### Modification 3 — `tools/agent/agent_pc.py`

Traceur de plantage natif écrit dans agent.log (mode tâche planifiée).

**Avant :**

```python
        print(f"--- démarrage {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
```

**Après :**

```python
        print(f"--- démarrage {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
        faulthandler.enable(file=journal, all_threads=True)  # plantage natif : ligne exacte dans le journal
```

### Modification 4 — `tools/agent/agent_pc.py`

Import du lecteur des contrôles multimédias de Windows (nouveau fichier media_windows.py).

**Avant :**

```python
from master import SuiviMaster  # Phase 11 : suivi du master
```

**Après :**

```python
from master import SuiviMaster  # Phase 11 : suivi du master
from media_windows import LecteurMedia  # Phase 11-bis : position de la vidéo
```

### Modification 5 — `tools/agent/agent_pc.py`

L'agent lance la lecture de la position des vidéos au démarrage.

**Avant :**

```python
        self.master = SuiviMaster(DOSSIER)  # Phase 11 : suivi du master
```

**Après :**

```python
        self.master = SuiviMaster(DOSSIER)  # Phase 11 : suivi du master
        self.media = LecteurMedia()          # Phase 11-bis : position de la vidéo
        self.video_pos = None
```

### Modification 6 — `tools/agent/agent_pc.py`

Le journal signale si le lecteur média manque (paquets winrt) ou s'arrête.

**Avant :**

```python
        for nom, outil in (("LibreHardwareMonitor", self.lhm), ("PresentMon", self.fps),
                           ("Météo", self.meteo)):
```

**Après :**

```python
        for nom, outil in (("LibreHardwareMonitor", self.lhm), ("PresentMon", self.fps),
                           ("Météo", self.meteo), ("Lecteur média", self.media)):
```

### Modification 7 — `tools/agent/agent_pc.py`

Chaque seconde pendant une vidéo : position, durée, lecture/pause (EVT VIDEO_POS) ; titre de Windows quand la fenêtre n'en donne pas (ex. app Netflix).

**Avant :**

```python
        video = "" if (jeu or verrou) else self.video.video()
```

**Après :**

```python
        video = "" if (jeu or verrou) else self.video.video()
        # Phase 11-bis : position de la vidéo (contrôles multimédias de Windows)
        media = self.media.actuel() if video else None
        if media and "|" not in video and media["titre"]:
            video += "|" + texte_ascii(media["titre"]).replace("|", "/")[:90]
        self.video_pos = media
        position = f'{media["pos"]} {media["duree"]} {1 if media["lecture"] else 0}' if media else "-"
        if self.precedent.get("VIDEO_POS") != position:
            self.precedent["VIDEO_POS"] = position
            self.liaison.envoyer(f"EVT VIDEO_POS {position}")
```

### Modification 8 — `tools/agent/agent_pc.py`

Position de la vidéo dans l'état envoyé à l'app.

**Avant :**

```python
            "video_titre": p.get("VIDEO", "").partition("|")[2],
```

**Après :**

```python
            "video_titre": p.get("VIDEO", "").partition("|")[2],
            "video_pos": self.video_pos["pos"] if self.video_pos else -1,
            "video_duree": self.video_pos["duree"] if self.video_pos else -1,
            "video_lecture": bool(self.video_pos and self.video_pos["lecture"]),
```

### Modification 9 — `esp/main.py`

Position de la vidéo gardée dans l'état.

**Avant :**

```python
evt = {"casque": "", "manette": 0, "verrou": 0, "jeu": "", "video": "", "video_titre": "",
       "inactif": 0}
```

**Après :**

```python
evt = {"casque": "", "manette": 0, "verrou": 0, "jeu": "", "video": "", "video_titre": "",
       "inactif": 0, "video_pos": None}  # video_pos : (position s, durée s, lecture 0/1, ticks reçu)
```

### Modification 10 — `esp/main.py`

Lecture de EVT VIDEO_POS.

**Avant :**

```python
        elif typ == "INACTIF":
```

**Après :**

```python
        elif typ == "VIDEO_POS":
            # EVT VIDEO_POS position durée lecture (secondes ; lecture 1 / pause 0) ; - = inconnue
            try:
                p = [int(x) for x in val.split()]
                evt["video_pos"] = (p[0], p[1], p[2], time.ticks_ms())
            except (ValueError, IndexError):
                evt["video_pos"] = None
        elif typ == "INACTIF":
```

### Modification 11 — `esp/lib/ui.py`

Scène cinéma : barre d'avancement sous le titre (2 lignes de titre au plus quand elle est là).

**Avant :**

```python
        for i, l in enumerate(lignes):
            self.f_m.ecrire(fb, l, 16, 34 + i * 20, BLANC, carte)
        # bas de la carte : heure + volume
        fb.fill_rect(16, 112, 162, 1, rgb565(70, 30, 40))
```

**Après :**

```python
        pos = etat["evt"].get("video_pos")
        avancement = bool(pos) and pos[1] > 0
        if avancement:
            # 2 lignes de titre au plus (avec « … ») : place pour la barre d'avancement
            lignes = self._lignes(self.f_m, titre, 166, 2) if titre else lignes[:2]
        for i, l in enumerate(lignes):
            self.f_m.ecrire(fb, l, 16, 34 + i * 20, BLANC, carte)
        if avancement:
            self._avancement(pos, couleur, carte, maintenant)
        else:
            fb.fill_rect(16, 112, 162, 1, rgb565(70, 30, 40))
        # bas de la carte : heure + volume
```

### Modification 12 — `esp/lib/ui.py`

Dessin de la barre d'avancement (la position avance toute seule entre deux messages du PC).

**Avant :**

```python
    def _suggestions(self, etat):
```

**Après :**

```python
    def _temps_video(self, s):
        """152 -> « 02:32 » ; 3752 -> « 1:02:32 »."""
        if s >= 3600:
            return "%d:%02d:%02d" % (s // 3600, s // 60 % 60, s % 60)
        return "%02d:%02d" % (s // 60, s % 60)

    def _avancement(self, pos, couleur, carte, maintenant):
        fb = self.fb
        p, duree, lecture, recu = pos
        if lecture:
            p += time.ticks_diff(maintenant, recu) // 1000
        p = max(0, min(p, duree))
        self.f_xs.ecrire(fb, self._temps_video(p), 16, 88, BLANC, carte)
        fin = self._temps_video(duree)
        self.f_xs.ecrire(fb, fin, 178 - self.f_xs.largeur(fin), 88, GRIS, carte)
        if not lecture:
            self.f_xs.ecrire_centre(fb, "Pause", 97, 88, ORANGE, carte)
        fb.fill_rect(16, 106, 162, 4, rgb565(60, 30, 40))
        x = 16 + 162 * p // duree
        fb.fill_rect(16, 106, x - 16, 4, rgb565(*(couleur if lecture else ORANGE)))
        fb.fill_rect(x - 2, 103, 4, 10, rgb565(*BLANC))  # curseur

    def _suggestions(self, etat):
```

### Modification 13 — `app/lib/etat.dart`

Position de la vidéo dans l'état reçu du PC.

**Avant :**

```dart
  final bool masterActif; // appli de recherche au premier plan depuis 2 min
```

**Après :**

```dart
  final bool masterActif; // appli de recherche au premier plan depuis 2 min
  final int videoPos; // secondes depuis le début de la vidéo, -1 = inconnue (Phase 11-bis)
  final int videoDuree; // durée de la vidéo en secondes, -1 = inconnue
  final bool videoLecture; // true = en lecture, false = en pause
```

### Modification 14 — `app/lib/etat.dart`

Valeurs par défaut.

**Avant :**

```dart
    this.masterActif = false,
```

**Après :**

```dart
    this.masterActif = false,
    this.videoPos = -1,
    this.videoDuree = -1,
    this.videoLecture = false,
```

### Modification 15 — `app/lib/etat.dart`

Lecture depuis le message « etat ».

**Avant :**

```dart
      masterActif: m['master_actif'] == true,
```

**Après :**

```dart
      masterActif: m['master_actif'] == true,
      videoPos: _entier(m['video_pos']),
      videoDuree: _entier(m['video_duree']),
      videoLecture: m['video_lecture'] == true,
```

### Modification 16 — `app/lib/widgets/cinema.dart`

Format des temps de la vidéo.

**Avant :**

```dart
class CarteCinema extends StatelessWidget {
```

**Après :**

```dart
/// 152 -> « 02:32 » ; 3752 -> « 1:02:32 »
String _temps(int s) {
  String deux(int n) => n.toString().padLeft(2, '0');
  return s >= 3600 ? '${s ~/ 3600}:${deux(s ~/ 60 % 60)}:${deux(s % 60)}' : '${deux(s ~/ 60)}:${deux(s % 60)}';
}

class CarteCinema extends StatelessWidget {
```

### Modification 17 — `app/lib/widgets/cinema.dart`

Barre d'avancement sous le titre dans la carte Cinéma.

**Avant :**

```dart
          const SizedBox(height: 14),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
```

**Après :**

```dart
          if (etat.videoDuree > 0) ...[
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: (etat.videoPos / etat.videoDuree).clamp(0.0, 1.0),
                minHeight: 5,
                color: etat.videoLecture ? couleur : Couleurs.orange,
                backgroundColor: Colors.white.withValues(alpha: 0.1),
              ),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Text(_temps(etat.videoPos), style: const TextStyle(fontSize: 12, color: Colors.white)),
                const Spacer(),
                if (!etat.videoLecture)
                  const Text('Pause', style: TextStyle(fontSize: 12, color: Couleurs.orange)),
                const Spacer(),
                Text(_temps(etat.videoDuree), style: const TextStyle(fontSize: 12, color: Couleurs.gris)),
              ],
            ),
          ],
          const SizedBox(height: 14),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
```

### Modification 18 — `tools/agent/agent_pc.py`

Sites vidéo ajoutés depuis l'app (tools\agent\sites_video.json), relus toutes les 10 s.

**Avant :**

```python
def video_premier_plan():
```

**Après :**

```python
FICHIER_SITES = DOSSIER / "sites_video.json"   # Phase 11-bis : sites ajoutés depuis l'app (jamais dans Git)
_SITES_PERSO = {"liste": [], "lu": 0.0}


def sites_perso():
    """[(mot du titre en minuscules, nom affiché)] ajoutés depuis l'app, relus toutes les 10 s."""
    if time.time() - _SITES_PERSO["lu"] > 10:
        _SITES_PERSO["lu"] = time.time()
        try:
            d = json.loads(FICHIER_SITES.read_text(encoding="utf-8"))
            _SITES_PERSO["liste"] = [(str(s["mot"]).strip().lower(), str(s["nom"]).strip()) for s in d
                                     if isinstance(s, dict) and str(s.get("mot", "")).strip()
                                     and str(s.get("nom", "")).strip()]
        except (OSError, ValueError, TypeError, KeyError):
            _SITES_PERSO["liste"] = []
    return _SITES_PERSO["liste"]


def video_premier_plan():
```

### Modification 19 — `tools/agent/agent_pc.py`

Les sites de l'app sont cherchés avant les sites connus d'office.

**Avant :**

```python
        for cle, nom in SITES_VIDEO:
```

**Après :**

```python
        for cle, nom in sites_perso() + list(SITES_VIDEO):  # sites ajoutés dans l'app d'abord
```

### Modification 20 — `tools/agent/agent_pc.py`

Fonctions pour la carte « Sites vidéo » de l'app.

**Avant :**

```python
    def master_afficher(self):
```

**Après :**

```python
    def sites_pour_app(self):
        """Sites vidéo de l'app, sites reconnus d'office et titre de l'onglet ouvert sur le PC."""
        hwnd, pid = fenetre_premier_plan()
        onglet = ""
        if hwnd and pid:
            try:
                if psutil.Process(pid).name().lower() in NAVIGATEURS:
                    onglet = titre_fenetre(hwnd)[:150]
            except psutil.Error:
                pass
        _SITES_PERSO["lu"] = 0.0
        return {"perso": [{"mot": m, "nom": n} for m, n in sites_perso()],
                "defaut": [{"mot": m, "nom": n} for m, n in SITES_VIDEO], "onglet": onglet}

    def sites_maj(self, liste):
        """Enregistre tools\\agent\\sites_video.json (liste modifiée dans l'app)."""
        propres = []
        for s in liste if isinstance(liste, list) else []:
            if not isinstance(s, dict):
                continue
            mot = str(s.get("mot", "")).strip().lower()[:40]
            nom = str(s.get("nom", "")).strip()[:20]
            if len(mot) >= 3 and nom and mot not in [p["mot"] for p in propres]:
                propres.append({"mot": mot, "nom": nom})
        try:
            FICHIER_SITES.write_text(json.dumps(propres[:50], ensure_ascii=False, indent=1),
                                     encoding="utf-8")
        except OSError as e:
            return False, f"sites_video.json non enregistré : {e}"
        _SITES_PERSO["lu"] = 0.0
        return True, "Sites vidéo enregistrés"

    def master_afficher(self):
```

### Modification 21 — `tools/agent/agent_pc.py`

Fonctions données au serveur de l'app.

**Avant :**

```python
            "etat_court": self.etat_court,
```

**Après :**

```python
            "etat_court": self.etat_court,
            "sites": self.sites_pour_app, "sites_maj": self.sites_maj,
```

### Modification 22 — `tools/agent/serveur_app.py`

Messages « sites » et « sites_maj ».

**Avant :**

```python
                elif typ == "pointeur":
```

**Après :**

```python
                elif typ == "sites":
                    await self._envoyer(ws, {"type": "sites", **self.r["sites"]()})
                elif typ == "sites_maj":
                    ok, texte = await boucle.run_in_executor(None, self.r["sites_maj"], m.get("sites"))
                    await self._envoyer(ws, {"type": "rep", "ligne": typ, "texte": texte, "ok": ok})
                    await self._envoyer(ws, {"type": "sites", **self.r["sites"]()})
                elif typ == "pointeur":
```

### Modification 23 — `.gitignore`

sites_video.json jamais commité.

**Avant :**

```text
tools/agent/master_historique.json
```

**Après :**

```text
tools/agent/master_historique.json
tools/agent/sites_video.json
```

### Modification 24 — `app/lib/connexion.dart`

Données de la carte « Sites vidéo ».

**Avant :**

```dart
  Map<String, dynamic>? jeux;
```

**Après :**

```dart
  Map<String, dynamic>? jeux;
  Map<String, dynamic>? sites; // Phase 11-bis
```

### Modification 25 — `app/lib/connexion.dart`

Réception du message « sites ».

**Avant :**

```dart
      case 'jeux':
```

**Après :**

```dart
      case 'sites':
        sites = Map<String, dynamic>.from(m);
        return true;
      case 'jeux':
```

### Modification 26 — `app/lib/connexion.dart`

Demandes au PC pour les sites vidéo.

**Avant :**

```dart
  Future<(bool, String)> pasUnJeu() => _demander({'type': 'pas_un_jeu'});
```

**Après :**

```dart
  Future<(bool, String)> pasUnJeu() => _demander({'type': 'pas_un_jeu'});

  void demanderSites() => _envoyer({'type': 'sites'});

  Future<(bool, String)> majSites(List<Map<String, String>> liste) =>
      _demander({'type': 'sites_maj', 'sites': liste});
```

### Modification 27 — `app/lib/ecrans/reglages.dart`

Import de la carte « Sites vidéo ».

**Avant :**

```dart
import '../notifications.dart';
```

**Après :**

```dart
import '../notifications.dart';
import '../widgets/sites_video.dart';
```

### Modification 28 — `app/lib/ecrans/reglages.dart`

Carte « Sites vidéo » sous la carte Notification.

**Avant :**

```dart
        const CarteNotifications(),
```

**Après :**

```dart
        const CarteNotifications(),
        const SizedBox(height: 14),
        CarteSitesVideo(cx: cx),
```

## Partie 2 — Traduction en anglais (à faire par Claude Code, APRÈS la Partie 1 bis)

Ici, pas de blocs « avant → après » : c'est une traduction mécanique sur beaucoup de fichiers. Respecte **toutes** les règles suivantes.

### À traduire (seulement les textes visibles par l'utilisateur)
- **ESP32** : `esp/lib/ui.py` (bandeaux, titres, jours `JOURS` et mois `MOIS`, suggestions de la scène calme, `RAPPELS_MASTER`, textes des scènes) et `esp/main.py` (réactions : `REACTIONS_MEDIA`, `reaction_action`, « Code : … », « Casque connecté »…).
- **Programme PC**, seulement ce qui finit à l'écran : textes renvoyés à l'app (réponses `rep`, messages d'erreur des `return False, "…"`, `"Envoyé à l'ESP32"`…), textes envoyés à l'ESP32 (`MASTER_INFO`, `EVT ACTION …` si c'est affiché tel quel), mois `MOIS` et événements de `tools/agent/master.py`, `PHASES` de master.py.
- **App** : tout `app/lib/**` (y compris la nouvelle carte `widgets/sites_video.dart` : « Sites vidéo » → « Video sites ») (textes des widgets, snackbars, dialogues, indications, suggestions d'échéances, jours et mois de `master.dart`), `DadouWidget.kt`, `VeilleurPC.kt` (titre, texte et bouton de la notification, nom du canal), `MainActivity.kt` s'il contient du texte visible, `res/values/strings.xml`, `res/layout/widget_dadou.xml` (texte « Ajoute des favoris… »).

### À NE PAS changer
- Les noms de variables, fonctions, classes et fichiers, les commentaires et les messages `print(...)` du journal de l'agent (ils restent en français).
- Le protocole : commandes série (`STAT`, `EVT …`, `MASTER`, `KEY`…), clés JSON (`type`, `texte`, `objectif`…), noms des messages WebSocket, chemins HTTP, noms des icônes (`"livre"`, `"graphe"`…), noms des fichiers de réglages.
- Les mots-clés de détection (`SITES_VIDEO`, `SITES_RECHERCHE`, `APPS_RECHERCHE`, `mots_word` par défaut, titres de fenêtres comme « Lecteur multimédia VLC ») : ils servent à reconnaître des fenêtres, pas à afficher.
- Le nom de l'app « Dadou » et le nom de la mascotte.

### Règles de longueur (écran de l'ESP32 : 320 × 172 px)
- Chaque texte affiché sur l'ESP32 doit avoir **au plus autant de caractères** que le texte français qu'il remplace. Raccourcis si besoin (ex. « Pas de pluie prévue » → « No rain expected »).
- Textes des bandeaux (`reagir(...)`, `RAPPELS_MASTER`, `MASTER_INFO`) : **26 caractères maximum**.
- « J-9 » devient **« D-9 »** (« D- » est dessiné avec la police moyenne, le chiffre avec la police de l'heure : ne change pas les polices).
- Les polices de l'ESP32 n'ont que l'ASCII, plus `°éèêëàâäçîïôöùûüÉÈÀÇ…•` : n'utilise **pas** d'apostrophe typographique (’), ni de tiret long (—), ni d'emoji. Utilise `'` et `-`.
- Formats : date sur l'ESP32 « Tue 4 Nov » (jours `Mon`…`Sun`, mois `Jan`…`Dec`) ; réunion « 10 Nov 10:00 » ; durées « 1 h 35 » → « 1h 35 » et « 40 min » (garde la même longueur ou moins).

### Phases du master (valeurs enregistrées dans master.json)
- `PHASES` devient `("Literature review", "Prototype", "Measurements", "Writing")`.
- Dans `SuiviMaster.__init__`, juste après la lecture de `master.json`, convertis une ancienne valeur française : `{"Etat de l'art": "Literature review", "Mesures": "Measurements", "Redaction": "Writing"}`. La phase par défaut de `DEFAUT` devient `"Literature review"`.

### Suggestions de la scène calme et rappels du master (traductions imposées, déjà à la bonne longueur)
| Français | Anglais |
|---|---|
| Une pause eau ? | Time for some water? |
| Où en es-tu dans tes recherches ? | How is your research going? |
| Lève-toi et étire-toi un peu | Stand up and stretch a bit |
| Une page de ton mémoire aujourd'hui ? | One page of your thesis today? |
| Il pleut : les fenêtres sont fermées ? | It's raining: windows closed? |
| Pluie vers %d h : pense à fermer les fenêtres | Rain around %d: close the windows |
| Reprendre %s ? | Back to %s? |
| Il se fait tard : au lit bientôt ? | It's late: bed soon? |
| Le PC t'attend depuis %s : l'éteindre ? | PC idle for %s: shut it down? |
| Une section à la fois. | One section at a time. |
| Le fond, puis le style. | Content first, style later. |
| Cite pendant que tu écris. | Cite while you write. |
| Source notée ? | Source noted? |
| 1 article lu > 3 ouverts. | 1 paper read > 3 opened. |
| Relis ta question. | Reread your question. |
| Question au superviseur ? | A question for your SV? |
| Mesure 3 fois, conclus 1. | Measure 3x, conclude 1x. |
| Hz, mode, temp. : notés ? | Hz, mode, temp: noted? |
| Ta matrice est à jour ? | Matrix up to date? |
| Quartile de la revue vu ? | Journal quartile checked? |
| Structure, puis affine. | Structure, then refine. |
| Commit, puis pause. | Commit, then rest. |
| Cinq minutes de pause ? | Five-minute break? |
| Tard : à demain ? | Late: see you tomorrow? |
| Objectif du jour atteint. Bien joué. | Daily goal done. Nice! |
| Réunion dans 1 h : notes prêtes ? | Meeting in 1h: notes? |
| Bon visionnage ! | Enjoy the show! |
| Bonjour Mihaja ! | Hello Mihaja! |

Les deux anciennes phrases en anglais de `RAPPELS_MASTER` (« One section at a time. », « Write first, polish later. ») restent ; supprime le doublon « One section at a time. ».

### Vérifications à faire
1. `py -m py_compile` sur agent_pc.py, serveur_app.py, master.py, media_windows.py, esp/main.py, esp/lib/ui.py.
2. Contrôle des longueurs : écris un petit script **temporaire** (non commité) qui lit `esp/assets/police_m.fnt` (format dans `esp/lib/polices.py` : `FNT1`, hauteur, nombre, puis entrées `<HBBI` code, largeur, avance, décalage) et calcule la largeur en pixels (somme des avances) de chaque texte de bandeau de ui.py, main.py et master.py. Chacun doit faire **194 px au plus**. Donne le tableau texte / largeur.
3. Recherche des caractères interdits dans les textes de l'ESP32 (’ — “ ” et emoji) : aucun.
4. `flutter analyze` puis `flutter build apk --release` dans app/.
5. `grep` de contrôle : plus aucun texte français visible dans app/lib (cherche « é », « è », « à », « ç » dans les chaînes de caractères, hors commentaires) ; donne les éventuels restes en justifiant.

## Copie sur la carte, puis test de l'agent

1. PAUSE, puis copie `esp/main.py` → `:main.py` et `esp/lib/ui.py` → `:lib/ui.py`, `reset`, supprime PAUSE.
2. En admin : `Stop-ScheduledTask "ESP32 Telecommande Agent"` puis `Start-ScheduledTask "ESP32 Telecommande Agent"`.
3. Attends 2 min, puis vérifie : `Get-ScheduledTask "ESP32 Telecommande Agent" | Get-ScheduledTaskInfo` (état `Running`, pas de `3221225477`), `curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8765/widget` → `401`, et les 30 dernières lignes de `agent.log` (on doit voir des lignes `[agent] événement : …` après `PresentMon : OK`).
4. Ouvre une vidéo YouTube 30 s (le compteur de son et le lecteur média sont alors utilisés) et refais le point 3 : l'agent tourne toujours, et le journal contient des lignes `EVT VIDEO_POS` envoyées (ou au moins aucune erreur « Lecteur média »).

## Liste de contrôle

| Contrôle | Attendu |
|---|---|
| Partie 0 : plugin VLC | VLC x64, VC++ 2022 x64 présent, DLL dans plugins\misc, module activé, script : appli « vlc », durée > 0 |
| Test à blanc : les 28 blocs « avant » de la Partie 1 bis | chacun trouvé 1 fois |
| Paquets winrt dans le Python de la tâche | import ok |
| agent.log après démarrage | pas de ligne « Lecteur média : paquets winrt absents » |
| py_compile (agent_pc.py, serveur_app.py, master.py, media_windows.py, esp/main.py, esp/lib/ui.py) | aucune erreur |
| Largeur des textes de bandeau | tous ≤ 194 px |
| Caractères interdits sur l'ESP32 | aucun |
| flutter analyze / build apk --release | No issues found / APK créée |
| Carte : erreur.txt 30 s après reset | 1402 octets (inchangé) |
| Tâche après 2 min + vidéo YouTube | Running, 401, « événement » dans le journal |

Commit « Phase 11-bis : plantage de l'agent corrigé, barre d'avancement des vidéos, sites vidéo, interface en anglais » (avec tools/agent/media_windows.py et app/lib/widgets/sites_video.dart ; le plugin VLC, vlcrc et le script de test ne sont pas dans le dépôt), sans docs/etat_micro.md, tools/agent/apps.json ni docs/micro_phase6_fichiers.zip, puis push.

## Tests sur l'appareil (Mihaja)

1. Installe la nouvelle APK. Dadou est en anglais (onglets Home, Mouse, Screen, Master, Controls, Settings).
2. Settings → adresse du PC → Connect. Le statut doit passer à « Connected and paired » en 1 à 2 s. À la maison, essaie d'abord l'adresse locale `192.168…` (affichée dans agent.log au démarrage), puis l'adresse Tailscale `100.…`.
3. Si ça reste sur « Connecting… » alors que l'agent tourne (`401` en local) : le téléphone n'atteint pas le PC. Ouvre `http://ADRESSE:8765/widget` dans Chrome sur le téléphone : « Non autorisé » (ou « Unauthorized ») veut dire que le réseau est bon. Une page introuvable veut dire Tailscale ou Wi-Fi.
4. L'écran de l'ESP32 est en anglais (heure + « Tue 4 Nov », météo « Today / Tomorrow », scène master « D-9 »…).
5. Regarde une vidéo YouTube 5 min : la scène cinéma reste, et l'agent ne plante plus. Sous le titre, le temps avance seconde par seconde (ex. « 02:32 … 24:04 ») ; mets en pause : « Pause » en orange, la barre devient orange et le temps s'arrête. La carte Cinéma de l'app montre la même barre.
6. Netflix (site ou app), Anime-Sama et **VLC** : la barre s'affiche aussi si Windows connaît la vidéo (en touchant le volume, le petit lecteur de Windows montre le titre et une barre). Dans VLC, tu peux même faire glisser la barre du petit lecteur de Windows.
7. Un site de vidéos non reconnu : ouvre la vidéo sur le PC, puis dans l'app Settings → « Video sites » → « Use this tab » (le mot et le nom sont proposés), corrige si besoin → Add. Dans les 10 s, la scène cinéma s'affiche sur l'ESP32 (avec le son de la vidéo).
