# Phase 13 — Clim complète + capteur + écran + souris (Micro / Dadou)

Base : commit `f6422e5` (Phase 12). Écrit le 2026-11-06 sur le vrai code du dépôt.
Une seule phase, **8 étapes A→H**. Chaque étape = un commit à part, testable seule. Si une étape coince, on passe à la suivante et on y revient.

## Règles (rappel)
- Caveman : moins de blabla, plus d'action. Diffs chirurgicaux. Rien de détruit sans OK de Mihaja.
- Micro reste **MicroPython** (ESP32) + Dart + Kotlin (Android). Interface **en anglais**. Docs en français.
- Ne jamais lire ni copier le contenu de `secrets.py`, `appareils.json`, tokens. Ne rien toucher dans `C:\Windows\Temp` (Defender), ne pas en parler.
- Modèles : voir le tableau. `/model xxx` s'envoie **seul**, avant le prompt.
- Le sandbox de Claude web n'a pas Dart/Kotlin : **tu compiles** (`flutter analyze`, `flutter test`, `flutter build apk`). En cas d'erreur de compilation : corrige au plus petit, dis-le dans le commit.

| Étape | Sujet | Modèle |
|---|---|---|
| A | Swing inversé + tests | Haiku |
| B | Souris : correctifs + mesures | Sonnet |
| C | Retour à MicroPython sur la carte | Sonnet |
| D | Rotation écran ESP32 + heure en mode jeu | Sonnet |
| E | Minuteur + plage horaire (Android) + liaison clim → PC → ESP32 | Sonnet |
| F | Capteur AHT20/BMP280 + automatisme | Sonnet |
| G | Écran / avatar / animations : clim et pièce | Sonnet |
| H | Clôture : docs, tests, APK | Haiku |

Opus seulement si un bug résiste après 2 essais (ex. alarmes Android, souris).

Ordre conseillé : A → B → C → D → E → F → G → H. D–G ont besoin de MicroPython (C).

---

## A — Swing inversé

Constat de Mihaja : ça marche, mais le swing est à l'envers (on = off). Le bit 0 de l'octet 7 vaut donc **1 = swing actif**. Les trames capturées avec ce bit à 1 (les « normales ») sont des trames swing actif.

### A1. `app/lib/clim_ir.dart`

Avant :
```dart
  /// température en BCD (24 °C = 0x24). Octet 7 : checksum (haut) + drapeaux (bas) :
  /// bit 0 = 1 si le swing est arrêté, bit 3 = touche marche/arrêt.
```
Après :
```dart
  /// température en BCD (24 °C = 0x24). Octet 7 : checksum (haut) + drapeaux (bas) :
  /// bit 0 = 1 si le swing est actif (constaté sur la vraie clim, Phase 13), bit 3 = touche
  /// marche/arrêt.
```
(Si le commentaire d'origine est découpé autrement, ne change que « arrêté » → « actif ».)

Avant :
```dart
    final bas = (swing ? 0 : 1) | (touchePower ? 8 : 0);
```
Après :
```dart
    final bas = (swing ? 1 : 0) | (touchePower ? 8 : 0);
```

### A2. `app/test/clim_ir_test.dart` — remplacer tout le fichier

```dart
// Phase 12/13 : le générateur Dart doit reproduire exactement les trames capturées sur le Xiaomi.
// Phase 13 : le bit 0 de l'octet 7 = swing actif. Les trames capturées « normales » (bit 0 = 1)
// sont donc des trames swing: true.
import 'package:esp_micro/clim_ir.dart';
import 'package:flutter_test/flutter_test.dart';

List<int> _t(ModeClim m, VentClim v, int temp, bool swing, [bool power = false]) =>
    ClimIr.trame(mode: m, vent: v, temp: temp, swing: swing, touchePower: power);

void main() {
  test('trames de réglage capturées', () {
    expect(_t(ModeClim.cool, VentClim.auto, 24, true), [0x16, 0x12, 0, 0, 0, 0, 0x24, 0x11]);
    expect(_t(ModeClim.cool, VentClim.auto, 25, true), [0x16, 0x12, 0, 0, 0, 0, 0x25, 0x21]);
    expect(_t(ModeClim.cool, VentClim.auto, 30, true), [0x16, 0x12, 0, 0, 0, 0, 0x30, 0xE1]);
    expect(_t(ModeClim.cool, VentClim.auto, 16, true), [0x16, 0x12, 0, 0, 0, 0, 0x16, 0x21]);
    expect(_t(ModeClim.cool, VentClim.low, 24, true), [0x16, 0x82, 0, 0, 0, 0, 0x24, 0x81]);
    expect(_t(ModeClim.cool, VentClim.med, 24, true), [0x16, 0x42, 0, 0, 0, 0, 0x24, 0x41]);
    expect(_t(ModeClim.cool, VentClim.high, 24, true), [0x16, 0x22, 0, 0, 0, 0, 0x24, 0x21]);
    expect(_t(ModeClim.dry, VentClim.low, 23, true), [0x16, 0x81, 0, 0, 0, 0, 0x23, 0x61]);
    expect(_t(ModeClim.fan, VentClim.high, 21, true), [0x16, 0x24, 0, 0, 0, 0, 0x21, 0x11]);
    expect(_t(ModeClim.auto, VentClim.auto, 24, true), [0x16, 0x1A, 0, 0, 0, 0, 0x24, 0x91]);
    expect(_t(ModeClim.cool, VentClim.auto, 24, false), [0x16, 0x12, 0, 0, 0, 0, 0x24, 0x00]);
  });

  test('les deux trames power capturées', () {
    expect(_t(ModeClim.cool, VentClim.auto, 24, true, true), [0x16, 0x12, 0, 0, 0, 0, 0x24, 0x99]);
    expect(_t(ModeClim.cool, VentClim.auto, 16, true, true), [0x16, 0x12, 0, 0, 0, 0, 0x16, 0xA9]);
  });

  test('durées : 133 valeurs, en-tête puis marque finale', () {
    final d = ClimIr.durees(_t(ModeClim.cool, VentClim.auto, 24, true));
    expect(d.length, 133);
    expect(d.first, 4500);
    expect(d[1], 2500);
    expect(d.last, 4550);
  });
}
```

### A3. `app/lib/ecrans/clim.dart` — appui long sur power

Avant :
```dart
            mode: ModeClim.cool, vent: VentClim.auto, temp: 16, swing: false, touchePower: true),
```
Après :
```dart
            mode: ModeClim.cool, vent: VentClim.auto, temp: 16, swing: true, touchePower: true),
```
(La trame alternative capturée `…16 A9` a le bit 0 à 1 → `swing: true`.) Note : l'étape E réécrit ce fichier en entier ; si tu fais A puis E, ce changement y est déjà repris.

### Test A
`dart format app/lib/clim_ir.dart app/test/clim_ir_test.dart` ; `flutter test test/clim_ir_test.dart` (3 tests verts) ; `flutter analyze` propre. Commit : `Phase 13A : swing inversé (bit 0 = swing actif)`.
Mihaja (après build/installation) : bouton swing ON → la clim balance ; OFF → elle s'arrête. Si c'est encore à l'envers, dis-le (on remet l'ancien et on cherche ailleurs).

---

## B — Souris : correctifs + mesures

Je n'ai pas pu reproduire le bug (il dépend du téléphone/réseau). Je corrige les défauts **vus dans le code** et j'ajoute des mesures, pour trancher ensuite avec des chiffres.

Défauts trouvés :
1. Le curseur bouge pendant un simple tap (le moindre tremblement de doigt déplace la souris, donc le clic tombe à côté ; au-delà de 1,5 px par évènement le tap est même refusé).
2. Le curseur de sensibilité est **dans** la zone tactile : régler la sensibilité déplaçait la souris du PC.
3. Après un geste à deux doigts, le doigt restant bougeait la souris par à-coups.
4. Un tap à deux doigts avec un micro-mouvement n'était pas pris pour un clic droit.
5. Annulation d'un geste (appel entrant, bord d'écran) : état non remis à zéro.
6. Côté PC : les réponses « apps / raccourcis / master / jeux / sites / état court » lisent des fichiers **dans la boucle réseau** → la souris se fige pendant ce temps (surtout quand on change d'onglet). Et les nombreux fils de l'agent se disputent le processeur (intervalle de bascule Python 5 ms).

### B1. `app/lib/ecrans/souris.dart`

Avant (champs) :
```dart
  final Map<int, Offset> _doigts = {};
  DateTime _debut = DateTime.now();
  bool _bouge = false;
  bool _deuxDoigts = false;
  double _defilement = 0;
```
Après :
```dart
  final Map<int, Offset> _doigts = {};
  DateTime _debut = DateTime.now();
  Offset _depart = Offset.zero; // où le premier doigt a touché l'écran
  bool _bouge = false; // le doigt est sorti de la zone de tap
  bool _deuxDoigts = false;
  bool _aDefile = false; // le geste à deux doigts a vraiment fait défiler
  double _defilement = 0;
  static const double _tolerance = 8; // pixels : en dessous, c'est un tap, le curseur ne bouge pas
```

**Remplacer les 3 méthodes `_bas`, `_deplace`, `_haut`** (de `void _bas(PointerDownEvent e) {` jusqu'à la fin de `_haut`, juste avant `void _clic(String bouton) {`) par :
```dart
  void _bas(PointerDownEvent e) {
    _doigts[e.pointer] = e.position;
    if (_doigts.length == 1) {
      _debut = DateTime.now();
      _depart = e.position;
      _bouge = false;
      _deuxDoigts = false;
      _aDefile = false;
      _defilement = 0;
    } else {
      _deuxDoigts = true;
    }
  }

  void _deplace(PointerMoveEvent e) {
    _doigts[e.pointer] = e.position;
    if (_doigts.length >= 2) {
      // deux doigts : défilement (moyenne des deux doigts)
      _defilement += e.delta.dy / 2;
      while (_defilement.abs() >= 16) {
        final sens = _defilement > 0 ? 1 : -1;
        cx.molette(sens);
        _aDefile = true;
        _defilement -= 16 * sens;
      }
      return;
    }
    // un seul doigt resté après un geste à deux doigts : on attend qu'il se lève
    if (_deuxDoigts) return;
    if (!_bouge) {
      final r = e.position - _depart;
      if (r.distance <= _tolerance) return; // peut-être un tap : le curseur reste en place
      _bouge = true;
      // le geste devient un déplacement : on rattrape la distance déjà parcourue
      cx.souris(r.dx * _sensibilite, r.dy * _sensibilite);
      return;
    }
    final d = e.delta;
    // accélération : les gestes rapides vont plus loin
    final acc = 1 + (d.distance / 12).clamp(0.0, 1.5).toDouble();
    cx.souris(d.dx * _sensibilite * acc, d.dy * _sensibilite * acc);
  }

  void _haut(PointerUpEvent e) {
    _doigts.remove(e.pointer);
    if (_doigts.isNotEmpty) return;
    final duree = DateTime.now().difference(_debut);
    if (_deuxDoigts) {
      // tap à deux doigts = clic droit, sauf s'il y a eu défilement
      if (!_aDefile && duree < const Duration(milliseconds: 400)) _clic('droit');
    } else if (!_bouge) {
      if (duree < const Duration(milliseconds: 250)) {
        _clic('gauche');
      } else if (duree > const Duration(milliseconds: 500)) {
        _clic('droit');
      }
    }
    _deuxDoigts = false;
  }

  void _annule(PointerCancelEvent e) {
    _doigts.remove(e.pointer);
    _bouge = true; // un geste annulé ne doit jamais devenir un clic
    _aDefile = true;
    if (_doigts.isEmpty) _deuxDoigts = false;
  }
```

**Remplacer la méthode `_pave()`** (de `Widget _pave() {` jusqu'à son `}` de fin, juste avant `Widget _boutonClic(`) par :
```dart
  Widget _pave() {
    return Stack(
      children: [
        Positioned.fill(
          child: Listener(
            behavior: HitTestBehavior.opaque,
            onPointerDown: _bas,
            onPointerMove: _deplace,
            onPointerUp: _haut,
            onPointerCancel: _annule,
            child: Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(24),
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Couleurs.cyan.withValues(alpha: 0.10),
                    Couleurs.magenta.withValues(alpha: 0.10)
                  ],
                ),
                border: Border.all(color: Couleurs.cyan.withValues(alpha: 0.45), width: 1.5),
              ),
              child: const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    'Slide a finger to move the mouse\nTap = click · Long press = right click\n'
                    'Two fingers = scroll · Two-finger tap = right click',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Couleurs.gris, fontSize: 13, height: 1.5),
                  ),
                ),
              ),
            ),
          ),
        ),
        // le réglage de sensibilité est HORS de la zone tactile (sinon il déplaçait la souris)
        Positioned(
          right: 8,
          top: 4,
          child: Row(
            children: [
              const Icon(Icons.speed_rounded, size: 16, color: Couleurs.gris),
              SizedBox(
                width: 120,
                child: Slider(
                  value: _sensibilite,
                  min: 0.8,
                  max: 3.5,
                  onChanged: (v) => setState(() => _sensibilite = v),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
```

### B2. `tools/agent/serveur_app.py`

(a) Avant :
```python
        self.clients = 0
        self.probleme = ""

    # ------------------------------------------------------------ appareils
```
Après :
```python
        self.clients = 0
        self.probleme = ""
        # Phase 13 : mesures pour la souris (voir _veille_boucle)
        self.stats = {"n": 0, "ecart": 0.0, "boucle": 0.0, "appel": 0.0, "dernier": 0.0}

    # ------------------------------------------------------------ appareils
```

(b) Avant :
```python
            print(f"[agent] serveur app prêt sur le port {PORT}")
            await asyncio.Future()
```
Après :
```python
            print(f"[agent] serveur app prêt sur le port {PORT}")
            asyncio.create_task(self._veille_boucle())
            await asyncio.Future()
```

(c) Avant :
```python
    async def _envoyer(self, ws, donnees):
        await ws.send(json.dumps(donnees, ensure_ascii=False))
```
Après :
```python
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
```

(d) Avant :
```python
                if typ == "souris":
                    self.r["souris"](int(m.get("dx", 0)), int(m.get("dy", 0)))
```
Après :
```python
                if typ == "souris":
                    self._noter_souris(int(m.get("dx", 0)), int(m.get("dy", 0)))
```

(e) Remplacements textuels dans **tout** `serveur_app.py` (dans `_client` uniquement ; ne touche pas `_http`, l'étape E s'en charge) :

| Chercher | Remplacer par |
|---|---|
| `self.r["apps"]()` | `(await self._appel("apps"))` |
| `self.r["raccourcis"]()` | `(await self._appel("raccourcis"))` |
| `self.r["master"]()` | `(await self._appel("master"))` |
| `self.r["jeux"]()` | `(await self._appel("jeux"))` |
| `self.r["sites"]()` | `(await self._appel("sites"))` |

Ex. : `{"type": "master", **self.r["master"]()}` devient `{"type": "master", **(await self._appel("master"))}`. Vérifie que chaque ligne modifiée est bien dans une fonction `async def`.

### B3. `tools/agent/agent_pc.py`

Dans `main()`, juste après `args = parser.parse_args()` :
```python
    sys.setswitchinterval(0.002)  # Phase 13 : les fils se passent la main plus souvent (souris plus fluide)
```

### Test B
- `flutter analyze` + `flutter test` verts ; `py -m py_compile tools/agent/serveur_app.py tools/agent/agent_pc.py`.
- Redémarrer l'agent (tâche planifiée). Mihaja : 3 min de souris depuis l'app (déplacements lents, rapides, taps, clic droit, deux doigts, régler la sensibilité).
- Claude Code lit `tools/agent/agent.log` (seulement les lignes `souris :`) et résume en 3 lignes :
  - `boucle max` > 100 ms → l'agent est bloqué → chercher qui (py-spy, Opus).
  - `ecart max` > 150 ms avec `boucle max` petit → réseau/téléphone (Tailscale, Wi-Fi, économie d'énergie Xiaomi).
  - `SendInput max` > 20 ms → Windows/UIPI.
  - Tout petit mais ça saccade → « Améliorer la précision du pointeur » de Windows (Paramètres souris → Options du pointeur) double l'accélération de l'app : le décocher pour tester.
- Commit : `Phase 13B : souris (tolérance de tap, curseur hors zone, boucle réseau libre, mesures)`.

---

## C — Retour à MicroPython sur la carte

La carte tourne en C++ (tests IR). On remet MicroPython et on restaure les fichiers. **Mihaja doit faire l'étape BOOT lui-même.**

1. Arrêter l'agent : créer `tools\agent\PAUSE` (ou `Stop-ScheduledTask "ESP32 Telecommande Agent"`, déjà arrêtée normalement).
2. Vérifier `bin\ESP32_GENERIC_S3-SPIRAM_OCT-20260824-v1.29.0.bin`. Absent → le re-télécharger depuis micropython.org/download/ESP32_GENERIC_S3 (même variante `SPIRAM_OCT`, dernière stable).
3. **Mihaja** : débrancher la carte, **maintenir BOOT**, rebrancher, relâcher BOOT. Dire à Claude Code le port COM qui apparaît (Gestionnaire de périphériques ou `py -m serial.tools.list_ports`).
4. Flasher (remplace `COMx`) :
```
py -m esptool --chip esp32s3 --port COMx erase-flash
py -m esptool --chip esp32s3 --port COMx --baud 460800 write-flash -z 0x0 bin\ESP32_GENERIC_S3-SPIRAM_OCT-20260824-v1.29.0.bin
```
(esptool 5.x : tirets. Si « command not found », essayer `erase_flash` / `write_flash`.)
5. **Mihaja** : débrancher et rebrancher **sans** BOOT. `py -m mpremote devs` → noter le port (normalement COM4).
6. Restaurer (ordre) :
```
py -m mpremote connect COMx mip install usb-device-hid
py -m mpremote connect COMx fs mkdir :lib
py -m mpremote connect COMx fs cp esp/main.py :main.py
py -m mpremote connect COMx fs cp esp/lib/lcd.py esp/lib/ui.py esp/lib/meteo.py esp/lib/hid_pc.py esp/lib/polices.py :lib/
py -m mpremote connect COMx fs mkdir :assets
py -m mpremote connect COMx fs cp -r esp/assets/. :assets/
```
Adapter si `mkdir` dit « existe déjà ». Si `mip` ne marche pas (pas d'Internet sur la carte, mais `mip` passe par le PC), copier le dossier `usb` depuis `Micro_backup_carte` (`:lib/usb/...`). Copier aussi depuis `Micro_backup_carte` `secrets.py` et `briefing.txt` **s'ils existent**, octet pour octet, sans afficher leur contenu.
7. Vérifier : `py -m mpremote connect COMx exec "import sys; print(sys.implementation); import os; print(os.listdir())"` → `micropython`, `main.py`, `lib`, `assets`. `fs ls :assets` → 59 fichiers.
8. `py -m mpremote connect COMx reset`, puis supprimer `tools\agent\PAUSE` ou `Start-ScheduledTask "ESP32 Telecommande Agent"`.
9. Regarder `agent.log` : lignes `[esp32]`, pas de `Traceback`. L'écran affiche la mascotte, l'app Dadou se connecte, un raccourci clavier de l'app marche (HID = `usb-device-hid` bien installé).
10. Pas de commit de code. Note dans `docs/etat_micro.md` : « carte en MicroPython v1.29.0, <date> ».

---

## D — Rotation de l'écran ESP32 + heure en mode jeu

### D1. `esp/lib/lcd.py`

Avant :
```python
class Ecran:
    def __init__(self, paysage=True):
```
Après :
```python
class Ecran:
    def __init__(self, paysage=True, demi_tour=False):
```

Avant :
```python
        self.paysage = paysage
        if paysage:
```
Après :
```python
        self.paysage = paysage
        self.demi_tour = bool(demi_tour)  # Phase 13 : image retournée de 180° (carte posée à l'envers)
        if paysage:
```

Avant :
```python
        madctl = 0x60 if self.paysage else 0x00
        if BGR:
            madctl |= 0x08
        self._cmd(0x36, bytes([madctl]))  # orientation
        self._cmd(0x21)                  # inversion (écrans IPS)
```
Après :
```python
        self._madctl()                   # orientation
        self._cmd(0x21)                  # inversion (écrans IPS)
```

Avant :
```python
    # --- usage -------------------------------------------------------------
    def luminosite(self, pourcent):
```
Après :
```python
    def _madctl(self):
        if self.paysage:
            madctl = 0xA0 if self.demi_tour else 0x60
        else:
            madctl = 0xC0 if self.demi_tour else 0x00
        if BGR:
            madctl |= 0x08
        self._cmd(0x36, bytes([madctl]))

    def tourner(self, demi_tour):
        """Retourne l'image de 180° sans toucher au tampon (les marges de 34 px sont symétriques)."""
        demi_tour = bool(demi_tour)
        if demi_tour != self.demi_tour:
            self.demi_tour = demi_tour
            self._madctl()

    # --- usage -------------------------------------------------------------
    def luminosite(self, pourcent):
```
Si, après essai, l'image est **retournée mais décalée** (bande noire d'un côté), dis-le à Mihaja : la marge `DECALAGE` n'est alors pas symétrique et on la corrige (Opus pas nécessaire).

### D2. `esp/main.py`

Avant :
```python
ecran = lcd.Ecran(paysage=True)
```
Après :
```python
def lire_rotation():
    """Phase 13 : sens de l'écran gardé dans rotation.txt (« 180 » = retourné)."""
    try:
        with open("rotation.txt") as f:
            return f.read().strip() == "180"
    except OSError:
        return False


ecran = lcd.Ecran(paysage=True, demi_tour=lire_rotation())
```

Avant :
```python
    if cmd == "LUM_ESP":
        try:
            etat["lum"] = max(5, min(100, int(arg)))
        except ValueError:
            return "ERR utilise : LUM_ESP 5..100"
        return "OK"
```
Après (ajoute `ROT_ESP` juste après) :
```python
    if cmd == "LUM_ESP":
        try:
            etat["lum"] = max(5, min(100, int(arg)))
        except ValueError:
            return "ERR utilise : LUM_ESP 5..100"
        return "OK"
    if cmd == "ROT_ESP":
        demi = arg.strip() == "180"
        ecran.tourner(demi)
        try:
            with open("rotation.txt", "w") as f:
                f.write("180" if demi else "0")
        except OSError:
            pass
        return "OK"
```
Et dans l'en-tête de `main.py`, ajoute la ligne de commentaire `# - Phase 13 : ROT_ESP 0|180 (écran retourné), CLIM / CLIMAT (clim et capteur).` à la fin de la liste des phases.

### D3. `tools/agent/agent_pc.py`

Avant :
```python
        self.lum_esp = max(5, min(100, int(charger_preferences().get("lum_esp", 85))))
```
Après :
```python
        self.lum_esp = max(5, min(100, int(charger_preferences().get("lum_esp", 85))))
        self.rot_esp = 180 if int(charger_preferences().get("rot_esp", 0)) == 180 else 0
```

Avant :
```python
            "lum_esp": self.lum_esp, "ecrans": self.lent["ecrans"],
```
Après :
```python
            "lum_esp": self.lum_esp, "rot_esp": self.rot_esp, "ecrans": self.lent["ecrans"],
```

Avant :
```python
        if self.precedent.get("LUM_ESP") != self.lum_esp:
            self.precedent["LUM_ESP"] = self.lum_esp
            self.liaison.envoyer(f"LUM_ESP {self.lum_esp}")
```
Après :
```python
        if self.precedent.get("LUM_ESP") != self.lum_esp:
            self.precedent["LUM_ESP"] = self.lum_esp
            self.liaison.envoyer(f"LUM_ESP {self.lum_esp}")
        if self.precedent.get("ROT_ESP") != self.rot_esp:
            self.precedent["ROT_ESP"] = self.rot_esp
            self.liaison.envoyer(f"ROT_ESP {self.rot_esp}")
```

Avant :
```python
            self.precedent["LUM_ESP"] = self.lum_esp
            self.liaison.envoyer(f"LUM_ESP {self.lum_esp}")
            return f"ESP32 brightness: {self.lum_esp} %"
```
Après :
```python
            self.precedent["LUM_ESP"] = self.lum_esp
            self.liaison.envoyer(f"LUM_ESP {self.lum_esp}")
            return f"ESP32 brightness: {self.lum_esp} %"
        if cmd == "ROT_ESP":
            self.rot_esp = 180 if arg.strip() == "180" else 0
            p = charger_preferences()
            p["rot_esp"] = self.rot_esp
            try:
                ecrire_preferences(p)
            except OSError:
                pass
            self.precedent["ROT_ESP"] = self.rot_esp
            self.liaison.envoyer(f"ROT_ESP {self.rot_esp}")
            return "ESP32 orientation: " + ("flipped" if self.rot_esp else "normal")
```
(Les deux « Avant » qui contiennent `self.precedent["LUM_ESP"] = self.lum_esp` sont distincts : le 1er est dans `_mesures_lentes`, le 2e dans la gestion des commandes. Vérifie l'unicité avec le `return` qui suit.)

Dans le texte `AIDE`, après la ligne `LUM_ESP 60 …` ajoute :
```
  ROT_ESP 180           retourne l'écran de l'ESP32 (0 = normal)
```

### D4. App — `app/lib/etat.dart`

Avant : `  final int lumEsp; // luminosité de l'écran de l'ESP32 (5 à 100), -1 = inconnue`
Après : la même ligne puis `  final int rotEsp; // 0 = normal, 180 = écran retourné (Phase 13)`

Avant : `    this.lumEsp = -1,`
Après : `    this.lumEsp = -1,` puis `    this.rotEsp = 0,`

Avant : `      lumEsp: _entier(m['lum_esp']),`
Après : la même ligne puis `      rotEsp: _entier(m['rot_esp']) == 180 ? 180 : 0,`

### D5. App — `app/lib/ecrans/controles.dart` (carte Brightness)

Avant :
```dart
              onPressed: () => _envoyer(e.ecranEsp ? 'ECRAN_ESP 0' : 'ECRAN_ESP 1'),
            ),
          ),
        ],
      ),
    );
  }
```
Après :
```dart
              onPressed: () => _envoyer(e.ecranEsp ? 'ECRAN_ESP 0' : 'ECRAN_ESP 1'),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              const Icon(Icons.screen_rotation_rounded, size: 18, color: Couleurs.gris),
              const SizedBox(width: 8),
              const Text('ESP32 orientation', style: TextStyle(color: Couleurs.doux)),
              const Spacer(),
              ChoiceChip(
                label: const Text('Normal'),
                selected: e.rotEsp != 180,
                onSelected: (_) => _envoyer('ROT_ESP 0'),
              ),
              const SizedBox(width: 6),
              ChoiceChip(
                label: const Text('Flipped'),
                selected: e.rotEsp == 180,
                onSelected: (_) => _envoyer('ROT_ESP 180'),
              ),
            ],
          ),
        ],
      ),
    );
  }
```

### D6. Heure en mode jeu — `esp/lib/ui.py`, `_scene_jeu`

Avant :
```python
        session = self._age(self.jeu_debut, maintenant) // 60000
        chrono = duree_texte(session) if session >= 1 else ""
        largeur_chrono = self.f_xs.largeur(chrono) + 16 if chrono else 0
        nom = self.f_s.couper(etat["evt"]["jeu"], 172 - largeur_chrono)
        self.f_s.ecrire(fb, nom, 14, 10, CYAN, carte)
        if chrono:
            self.f_xs.ecrire(fb, chrono, 186 - self.f_xs.largeur(chrono), 12, GRIS, carte)
```
Après :
```python
        # nom du jeu à gauche, heure à droite ; la durée de session passe dans la ligne du bas
        session = self._age(self.jeu_debut, maintenant) // 60000
        lt = time.localtime()
        heure = "%02d:%02d" % (lt[3], lt[4]) if lt[0] >= 2025 else "--:--"
        largeur_heure = self.f_s.largeur(heure)
        nom = self.f_s.couper(etat["evt"]["jeu"], 172 - largeur_heure - 8)
        self.f_s.ecrire(fb, nom, 14, 10, CYAN, carte)
        self.f_s.ecrire(fb, heure, 186 - largeur_heure, 10, BLANC, carte)
```

Avant :
```python
        # ligne du bas : change toutes les 5 s (charge / minimum et moyenne / temps total)
        textes = []
```
Après :
```python
        # ligne du bas : change toutes les 5 s (session / charge / minimum et moyenne / temps total)
        textes = []
        if session >= 1:
            textes.append("Session: %s" % duree_texte(session))
```

### Test D
- `py -m py_compile` des 3 fichiers Python ; copier `esp/main.py`, `esp/lib/lcd.py`, `esp/lib/ui.py` sur la carte (PAUSE de l'agent pendant la copie, puis le retirer) ; `flutter analyze`, `flutter test`.
- Mihaja : lance un jeu → l'heure s'affiche en haut à droite, le nom du jeu à gauche (tronqué si long), « Session: … » apparaît dans la ligne du bas. App → Controls → Brightness → « Flipped » : l'écran se retourne tout de suite, et reste retourné après débranchement/rebranchement. « Normal » le remet.
- Commit : `Phase 13D : écran ESP32 retournable, heure en mode jeu`.

---

## E — Minuteur + plage horaire (Android) + liaison clim → PC → ESP32

Principe : tout tourne **côté Android** avec des alarmes exactes (`AlarmManager`) et un `BroadcastReceiver` qui émet l'IR : ça marche **app fermée**, et ça se réarme après redémarrage du téléphone. Dart calcule les trames IR et les confie à Kotlin. Le téléphone doit viser la clim (branché au chargeur la nuit).

⚠ La touche power de cette clim est probablement une **bascule** (même trame pour allumer et éteindre). Kotlin garde donc un état « clim allumée ? » **supposé** (`on`). Mihaja peut le corriger d'un interrupteur dans l'app si ça se désynchronise (clim allumée à la main avec la télécommande du Xiaomi, etc.).

### E1. Kotlin — nouveau fichier `app/android/app/src/main/kotlin/com/mmdigitek/esp_micro/ClimPlan.kt`

```kotlin
package com.mmdigitek.esp_micro

import android.Manifest
import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.ConsumerIrManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import org.json.JSONObject
import java.util.Calendar
import kotlin.math.max
import kotlin.math.min

/**
 * Clim programmée (Phase 13) : minuteur, plage horaire et mode automatique (capteur de la pièce).
 * Les trames IR (durées en µs) sont calculées par Dart (lib/clim_ir.dart) et rangées ici.
 * Alarmes exactes -> ClimReceiver -> executer(). État dans les préférences « clim_plan ».
 */
object ClimPlan {
    private const val PREFS = "clim_plan"
    private const val CANAL = "clim_auto"
    private const val ID_NOTIF = 4301
    const val CODE_MIN_OFF = 101
    const val CODE_MIN_ON = 102
    const val CODE_FEN_ON = 103
    const val CODE_FEN_OFF = 104
    const val CODE_AUTO = 105
    private const val PAUSE_COMPRESSEUR_MS = 3 * 60_000L // le compresseur ne redémarre pas avant 3 min
    private const val MANUEL_MS = 30 * 60_000L           // après une action à la main, l'auto se tait

    private fun p(c: Context) = c.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    // ------------------------------------------------------------------ trames et état
    fun trames(c: Context, frequence: Int, power: List<Int>, dryPower: List<Int>, mode: String, temp: Int) {
        p(c).edit()
            .putInt("freq", frequence)
            .putString("m_power", power.joinToString(","))
            .putString("m_dry_power", dryPower.joinToString(","))
            .putString("mode", mode)
            .putInt("temp", temp)
            .apply()
        publier(c)
    }

    fun allume(c: Context) = p(c).getBoolean("on", false)

    /** Correction ou action à la main (appli) : pas d'IR, on note seulement l'état supposé. */
    fun setOn(c: Context, on: Boolean) {
        val e = p(c).edit().putBoolean("on", on).putLong("manuel_jusqua", System.currentTimeMillis() + MANUEL_MS)
        if (!on) {
            e.putString("phase", "idle").putLong("dernier_off", System.currentTimeMillis()).putLong("minuteur_fin", 0)
            annuler(c, CODE_MIN_OFF)
        }
        e.apply()
        publier(c)
    }

    private fun motif(c: Context, cle: String): IntArray? {
        val s = p(c).getString(cle, "") ?: ""
        if (s.isEmpty()) return null
        return try {
            s.split(",").map { it.trim().toInt() }.toIntArray()
        } catch (e: NumberFormatException) {
            null
        }
    }

    private fun emettre(c: Context, cle: String): Boolean {
        val ir = c.getSystemService(Context.CONSUMER_IR_SERVICE) as? ConsumerIrManager ?: return false
        if (!ir.hasIrEmitter()) return false
        val m = motif(c, cle) ?: return false
        ir.transmit(p(c).getInt("freq", 38000), m) // une seule fois : la touche power est une bascule
        return true
    }

    fun allumer(c: Context, cle: String = "m_power"): Boolean {
        if (allume(c)) return false
        if (!emettre(c, cle)) return false
        p(c).edit().putBoolean("on", true).apply()
        return true
    }

    fun eteindre(c: Context): Boolean {
        if (!allume(c)) return false
        if (!emettre(c, "m_power")) return false
        p(c).edit().putBoolean("on", false).putLong("dernier_off", System.currentTimeMillis()).apply()
        return true
    }

    // ------------------------------------------------------------------ alarmes
    private fun intention(c: Context, code: Int): PendingIntent =
        PendingIntent.getBroadcast(
            c, code,
            Intent(c, ClimReceiver::class.java).setAction("dadou.clim.$code").putExtra("code", code),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

    fun programmer(c: Context, code: Int, quand: Long) {
        val am = c.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        if (Build.VERSION.SDK_INT >= 31 && !am.canScheduleExactAlarms()) {
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, quand, intention(c, code))
        } else {
            am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, quand, intention(c, code))
        }
    }

    fun annuler(c: Context, code: Int) {
        (c.getSystemService(Context.ALARM_SERVICE) as AlarmManager).cancel(intention(c, code))
    }

    /** Prochaine occurrence (ms) d'une heure du jour exprimée en minutes depuis minuit. */
    private fun prochaine(minutes: Int): Long {
        val cal = Calendar.getInstance()
        cal.set(Calendar.HOUR_OF_DAY, minutes / 60)
        cal.set(Calendar.MINUTE, minutes % 60)
        cal.set(Calendar.SECOND, 0)
        cal.set(Calendar.MILLISECOND, 0)
        if (cal.timeInMillis <= System.currentTimeMillis() + 1000) cal.add(Calendar.DAY_OF_YEAR, 1)
        return cal.timeInMillis
    }

    // ------------------------------------------------------------------ minuteur
    /** « Marche pendant [duree] min » (démarrage dans [delai] min, 0 = tout de suite). */
    fun minuteur(c: Context, duree: Int, delai: Int): Boolean {
        val maintenant = System.currentTimeMillis()
        annuler(c, CODE_MIN_ON)
        annuler(c, CODE_MIN_OFF)
        val debut = maintenant + delai * 60_000L
        val fin = debut + duree * 60_000L
        if (delai <= 0) {
            if (!allume(c) && !allumer(c)) return false
            p(c).edit().putLong("minuteur_debut", 0).apply()
        } else {
            programmer(c, CODE_MIN_ON, debut)
            p(c).edit().putLong("minuteur_debut", debut).apply()
        }
        p(c).edit().putLong("minuteur_fin", fin).apply()
        programmer(c, CODE_MIN_OFF, fin)
        publier(c)
        return true
    }

    fun annulerMinuteur(c: Context) {
        annuler(c, CODE_MIN_ON)
        annuler(c, CODE_MIN_OFF)
        p(c).edit().putLong("minuteur_fin", 0).putLong("minuteur_debut", 0).apply()
        publier(c)
    }

    // ------------------------------------------------------------------ plage horaire
    private fun fen(c: Context): JSONObject? = p(c).getString("fen", null)?.let { JSONObject(it) }

    fun fenetre(c: Context, actif: Boolean, de: Int, a: Int) {
        p(c).edit().putString("fen", JSONObject().put("actif", actif).put("de", de).put("a", a).toString()).apply()
        annuler(c, CODE_FEN_ON)
        annuler(c, CODE_FEN_OFF)
        if (actif) {
            programmer(c, CODE_FEN_ON, prochaine(de))
            programmer(c, CODE_FEN_OFF, prochaine(a))
        }
    }

    private fun rearmerFenetre(c: Context, code: Int) {
        val f = fen(c) ?: return
        if (!f.optBoolean("actif")) return
        programmer(c, code, prochaine(f.optInt(if (code == CODE_FEN_ON) "de" else "a")))
    }

    // ------------------------------------------------------------------ réception des alarmes
    fun executer(c: Context, code: Int) {
        when (code) {
            CODE_MIN_OFF -> {
                p(c).edit().putLong("minuteur_fin", 0).apply()
                if (eteindre(c)) notifier(c, "Timer finished: AC turned off")
            }
            CODE_MIN_ON -> if (allumer(c)) notifier(c, "Timer: AC turned on")
            CODE_FEN_ON -> {
                if (allumer(c)) notifier(c, "Schedule: AC turned on")
                rearmerFenetre(c, code)
            }
            CODE_FEN_OFF -> {
                if (eteindre(c)) notifier(c, "Schedule: AC turned off")
                rearmerFenetre(c, code)
            }
            CODE_AUTO -> auto(c)
        }
        publier(c)
    }

    /** Après un redémarrage du téléphone ou une mise à jour de l'app. */
    fun rearmer(c: Context) {
        val pr = p(c)
        val maintenant = System.currentTimeMillis()
        val debut = pr.getLong("minuteur_debut", 0)
        if (debut > maintenant) programmer(c, CODE_MIN_ON, debut)
        val fin = pr.getLong("minuteur_fin", 0)
        if (fin > 0) programmer(c, CODE_MIN_OFF, max(fin, maintenant + 5_000))
        fen(c)?.let {
            if (it.optBoolean("actif")) {
                programmer(c, CODE_FEN_ON, prochaine(it.optInt("de")))
                programmer(c, CODE_FEN_OFF, prochaine(it.optInt("a")))
            }
        }
        pr.getString("auto", null)?.let {
            if (JSONObject(it).optBoolean("actif")) programmer(c, CODE_AUTO, maintenant + 30_000)
        }
    }

    // ------------------------------------------------------------------ pour l'app
    fun etat(c: Context): Map<String, Any> {
        val pr = p(c)
        val am = c.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        return mapOf(
            "on" to allume(c),
            "minuteurFin" to pr.getLong("minuteur_fin", 0),
            "phase" to (pr.getString("phase", "idle") ?: "idle"),
            "autoFin" to pr.getLong("auto_fin", 0),
            "exact" to (Build.VERSION.SDK_INT < 31 || am.canScheduleExactAlarms()),
        )
    }

    /** Dit au PC (agent) où en est la clim : il l'affiche sur l'écran de l'ESP32. Sans bloquer. */
    fun publier(c: Context) {
        val fp = c.getSharedPreferences(VeilleurPC.PREFS, Context.MODE_PRIVATE)
        val adresse = fp.getString("flutter.adresse", "") ?: ""
        val token = fp.getString("flutter.token", "") ?: ""
        if (adresse.isEmpty() || token.isEmpty()) return
        val pr = p(c)
        val maintenant = System.currentTimeMillis()
        val phase = pr.getString("phase", "idle") ?: "idle"
        var fin = pr.getLong("minuteur_fin", 0)
        if (fin <= maintenant && phase != "idle") fin = pr.getLong("auto_fin", 0)
        val reste = if (fin > maintenant) ((fin - maintenant) / 60_000L + 1).toInt() else 0
        val mode = if (phase == "dry" && allume(c)) "dry" else (pr.getString("mode", "cool") ?: "cool")
        val auto = pr.getString("auto", null)?.let { JSONObject(it).optBoolean("actif") } ?: false
        val chemin = "/clim_maj?on=${if (allume(c)) 1 else 0}&mode=$mode&temp=${pr.getInt("temp", 24)}" +
            "&reste=$reste&auto=${if (auto) 1 else 0}"
        Thread {
            try {
                VeilleurPC.lire(adresse, token, chemin)
            } catch (e: Exception) {
                // PC éteint ou injoignable : tant pis, l'écran de l'ESP32 n'est qu'un plus
            }
        }.start()
    }

    // ------------------------------------------------------------------ automatisme (étape F)
    fun setAuto(c: Context, json: String) {
        p(c).edit().putString("auto", json).apply()
        annuler(c, CODE_AUTO)
        if (JSONObject(json).optBoolean("actif")) {
            programmer(c, CODE_AUTO, System.currentTimeMillis() + 5_000)
        } else {
            p(c).edit().putString("phase", "idle").apply()
        }
        publier(c)
    }

    private fun lireMesure(c: Context): JSONObject? {
        val fp = c.getSharedPreferences(VeilleurPC.PREFS, Context.MODE_PRIVATE)
        val adresse = fp.getString("flutter.adresse", "") ?: ""
        val token = fp.getString("flutter.token", "") ?: ""
        if (adresse.isEmpty() || token.isEmpty()) return null
        return try {
            val m = JSONObject(VeilleurPC.lire(adresse, token, "/clim_mesure"))
            if (m.optBoolean("ok")) m else null
        } catch (e: Exception) {
            null
        }
    }

    private fun auto(c: Context) {
        val cfg = p(c).getString("auto", null)?.let { JSONObject(it) } ?: return
        if (!cfg.optBoolean("actif")) return
        programmer(c, CODE_AUTO, System.currentTimeMillis() + 60_000) // prochain passage dans 1 min
        val mesure = lireMesure(c) ?: return // capteur ou PC injoignable : on ne fait rien
        val t = mesure.optDouble("t")
        val h = mesure.optDouble("h")
        val tOn = cfg.optDouble("t_on", 28.0)
        val tOff = cfg.optDouble("t_off", 25.0)
        val base = cfg.optInt("base", 30)
        val extra = cfg.optInt("extra", 3)
        val hDry = cfg.optInt("h_dry", 70)
        val dryMin = cfg.optInt("dry_min", 45)
        val maintenant = System.currentTimeMillis()
        val pr = p(c)
        when (pr.getString("phase", "idle")) {
            "cool" -> if (t <= tOff || maintenant >= pr.getLong("auto_fin", 0)) {
                if (eteindre(c)) notifier(c, "AC off (auto): %.1f °C".format(t))
                pr.edit().putString("phase", "idle").apply()
            }
            "dry" -> if (h <= hDry - 8 || maintenant >= pr.getLong("auto_fin", 0)) {
                if (eteindre(c)) notifier(c, "AC off (auto): humidity %d %%".format(h.toInt()))
                pr.edit().putString("phase", "idle").apply()
            }
            else -> {
                if (allume(c)) return // la clim tourne déjà (lancée à la main) : on n'y touche pas
                if (maintenant < pr.getLong("manuel_jusqua", 0)) return
                if (maintenant - pr.getLong("dernier_off", 0) < PAUSE_COMPRESSEUR_MS) return
                if (t >= tOn) {
                    // plus il fait chaud, plus elle tourne longtemps
                    val minutes = min(180, max(10, base + (extra * (t - tOn)).toInt()))
                    if (allumer(c)) {
                        pr.edit().putString("phase", "cool").putLong("auto_fin", maintenant + minutes * 60_000L).apply()
                        notifier(c, "AC on (auto): %.1f °C, off in %d min".format(t, minutes))
                    }
                } else if (h >= hDry) {
                    if (allumer(c, "m_dry_power")) {
                        pr.edit().putString("phase", "dry").putLong("auto_fin", maintenant + dryMin * 60_000L).apply()
                        notifier(c, "AC on (Dry): humidity %d %%, off in %d min".format(h.toInt(), dryMin))
                    }
                }
            }
        }
    }

    private fun notifier(c: Context, texte: String) {
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(c, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) return
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val canal = NotificationChannel(CANAL, "Air conditioner", NotificationManager.IMPORTANCE_LOW)
            c.getSystemService(NotificationManager::class.java).createNotificationChannel(canal)
        }
        val ouvrir = PendingIntent.getActivity(
            c, 300,
            Intent(c, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val n = NotificationCompat.Builder(c, CANAL)
            .setSmallIcon(R.drawable.w_power)
            .setContentTitle("Air conditioner")
            .setContentText(texte)
            .setContentIntent(ouvrir)
            .setAutoCancel(true)
            .build()
        try {
            NotificationManagerCompat.from(c).notify(ID_NOTIF, n)
        } catch (e: SecurityException) {
            // permission retirée entre-temps
        }
    }
}

/** Reçoit les alarmes (minuteur, plage horaire, automatisme) et le redémarrage du téléphone. */
class ClimReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val appli = context.applicationContext
        if (intent.action == Intent.ACTION_BOOT_COMPLETED || intent.action == Intent.ACTION_MY_PACKAGE_REPLACED) {
            ClimPlan.rearmer(appli)
            return
        }
        val code = intent.getIntExtra("code", 0)
        val attente = goAsync()
        Thread {
            try {
                ClimPlan.executer(appli, code)
            } catch (e: Exception) {
                // une alarme ratée ne doit jamais faire planter l'app
            } finally {
                attente.finish()
            }
        }.start()
    }
}
```

### E2. Kotlin — `MainActivity.kt`

Avant :
```kotlin
        // après une mise à jour de l'app, la vérification reprend toute seule
```
Après (le nouveau canal est inséré juste avant ce commentaire) :
```kotlin
        // Phase 13 : clim programmée (lib/clim_plan.dart, ClimPlan.kt)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "dadou/clim")
            .setMethodCallHandler { appel, resultat ->
                val c = applicationContext
                when (appel.method) {
                    "trames" -> {
                        ClimPlan.trames(
                            c,
                            appel.argument<Int>("frequence") ?: 38000,
                            appel.argument<List<Int>>("power") ?: emptyList(),
                            appel.argument<List<Int>>("dryPower") ?: emptyList(),
                            appel.argument<String>("mode") ?: "cool",
                            appel.argument<Int>("temp") ?: 24
                        )
                        resultat.success(true)
                    }
                    "setOn" -> {
                        ClimPlan.setOn(c, appel.argument<Boolean>("on") ?: false)
                        resultat.success(true)
                    }
                    "minuteur" -> resultat.success(
                        ClimPlan.minuteur(c, appel.argument<Int>("duree") ?: 30, appel.argument<Int>("delai") ?: 0)
                    )
                    "annulerMinuteur" -> {
                        ClimPlan.annulerMinuteur(c)
                        resultat.success(true)
                    }
                    "fenetre" -> {
                        ClimPlan.fenetre(
                            c,
                            appel.argument<Boolean>("actif") ?: false,
                            appel.argument<Int>("de") ?: 0,
                            appel.argument<Int>("a") ?: 0
                        )
                        resultat.success(true)
                    }
                    "auto" -> {
                        ClimPlan.setAuto(c, appel.argument<String>("json") ?: "{}")
                        resultat.success(true)
                    }
                    "publier" -> {
                        ClimPlan.publier(c)
                        resultat.success(true)
                    }
                    "etat" -> resultat.success(ClimPlan.etat(c))
                    else -> resultat.notImplemented()
                }
            }
        // après une mise à jour de l'app, la vérification reprend toute seule
```

### E3. `app/android/app/src/main/AndroidManifest.xml`

Avant :
```xml
    <uses-feature android:name="android.hardware.consumerir" android:required="false"/>
```
Après :
```xml
    <uses-feature android:name="android.hardware.consumerir" android:required="false"/>
    <!-- Phase 13 : minuteur, plage horaire et automatisme de la clim (alarmes exactes) -->
    <uses-permission android:name="android.permission.USE_EXACT_ALARM"/>
    <uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" android:maxSdkVersion="32"/>
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
```
Avant :
```xml
        <!-- Don't delete the meta-data below.
```
Après :
```xml
        <!-- Phase 13 : alarmes de la clim + réarmement au redémarrage -->
        <receiver
            android:name=".ClimReceiver"
            android:exported="false">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
                <action android:name="android.intent.action.MY_PACKAGE_REPLACED" />
            </intent-filter>
        </receiver>
        <!-- Don't delete the meta-data below.
```

### E4. Dart — nouveau fichier `app/lib/clim_plan.dart`

```dart
// Clim programmée (Phase 13) : minuteur, plage horaire et mode automatique avec le capteur de
// la pièce. Tout tourne côté Android (ClimPlan.kt, alarmes exactes) : ça marche app fermée.
import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'clim_ir.dart';
import 'etat.dart';
import 'theme.dart';

const _canal = MethodChannel('dadou/clim');

/// Pont vers Android.
class ClimPlan {
  /// Range chez Android les trames IR à jour (réglage actuel avec « power », et mode Dry).
  static Future<void> enregistrerTrames({
    required ModeClim mode,
    required VentClim vent,
    required int temp,
    required bool swing,
  }) {
    List<int> d(ModeClim m) => ClimIr.durees(
        ClimIr.trame(mode: m, vent: vent, temp: temp, swing: swing, touchePower: true));
    return _appeler('trames', {
      'frequence': ClimIr.frequence,
      'power': d(mode),
      'dryPower': d(ModeClim.dry),
      'mode': mode.name,
      'temp': temp,
    });
  }

  static Future<void> setOn(bool allume) => _appeler('setOn', {'on': allume});
  static Future<void> annulerMinuteur() => _appeler('annulerMinuteur');
  static Future<void> fenetre(bool actif, int de, int a) =>
      _appeler('fenetre', {'actif': actif, 'de': de, 'a': a});
  static Future<void> auto(Map<String, dynamic> reglages) =>
      _appeler('auto', {'json': jsonEncode(reglages)});
  static Future<void> publier() => _appeler('publier');

  static Future<bool> minuteur(int duree, int delai) async {
    try {
      return await _canal.invokeMethod<bool>('minuteur', {'duree': duree, 'delai': delai}) ?? false;
    } catch (_) {
      return false;
    }
  }

  static Future<Map<String, dynamic>> etat() async {
    try {
      final r = await _canal.invokeMethod<Map>('etat');
      return r == null ? <String, dynamic>{} : Map<String, dynamic>.from(r);
    } catch (_) {
      return <String, dynamic>{};
    }
  }

  static Future<void> _appeler(String methode, [Map<String, dynamic>? args]) async {
    try {
      await _canal.invokeMethod<dynamic>(methode, args);
    } catch (_) {
      // pas Android (tests) : rien à faire
    }
  }
}

String _hhmm(int minutes) =>
    '${(minutes ~/ 60).toString().padLeft(2, '0')}:${(minutes % 60).toString().padLeft(2, '0')}';

class _Sous extends StatelessWidget {
  final String texte;

  const _Sous(this.texte);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 14, bottom: 6),
      child: Text(texte,
          style: const TextStyle(fontWeight: FontWeight.w800, color: Couleurs.cyan)),
    );
  }
}

class CarteClimPlan extends StatefulWidget {
  final EtatPC etat;
  final bool jeu;

  const CarteClimPlan({super.key, required this.etat, this.jeu = false});

  @override
  State<CarteClimPlan> createState() => _CarteClimPlanState();
}

class _CarteClimPlanState extends State<CarteClimPlan> {
  Timer? _minuterie;
  Map<String, dynamic> _rt = {}; // état côté Android : on, minuteurFin, phase, exact…
  int _duree = 30;
  bool _fenActif = false;
  int _fenDe = 19 * 60;
  int _fenA = 21 * 60;
  bool _autoActif = false;
  int _tOn = 28;
  int _tOff = 25;
  int _base = 30;
  int _extra = 3;
  int _hDry = 70;
  int _dryMin = 45;

  @override
  void initState() {
    super.initState();
    _charger();
    _minuterie = Timer.periodic(const Duration(seconds: 5), (_) => _rafraichir());
  }

  @override
  void dispose() {
    _minuterie?.cancel();
    super.dispose();
  }

  Future<void> _charger() async {
    final p = await SharedPreferences.getInstance();
    final rt = await ClimPlan.etat();
    if (!mounted) return;
    setState(() {
      _duree = p.getInt('plan_duree') ?? 30;
      _fenActif = p.getBool('fen_actif') ?? false;
      _fenDe = p.getInt('fen_de') ?? 19 * 60;
      _fenA = p.getInt('fen_a') ?? 21 * 60;
      _autoActif = p.getBool('auto_actif') ?? false;
      _tOn = p.getInt('auto_t_on') ?? 28;
      _tOff = p.getInt('auto_t_off') ?? 25;
      _base = p.getInt('auto_base') ?? 30;
      _extra = p.getInt('auto_extra') ?? 3;
      _hDry = p.getInt('auto_h_dry') ?? 70;
      _dryMin = p.getInt('auto_dry_min') ?? 45;
      _rt = rt;
    });
    ClimPlan.publier(); // l'écran de l'ESP32 se met à jour à l'ouverture de l'app
  }

  Future<void> _rafraichir() async {
    final rt = await ClimPlan.etat();
    if (mounted) setState(() => _rt = rt);
  }

  // ------------------------------------------------------------ minuteur
  Future<void> _choisirDuree(int m) async {
    setState(() => _duree = m);
    final p = await SharedPreferences.getInstance();
    await p.setInt('plan_duree', m);
  }

  Future<void> _lancerMinuteur() async {
    HapticFeedback.selectionClick();
    final ok = await ClimPlan.minuteur(_duree, 0);
    await _rafraichir();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(ok
            ? 'Timer set: the AC is on for $_duree min'
            : 'Could not send: no IR blaster, or open the AC card once first')));
  }

  Future<void> _annulerMinuteur() async {
    await ClimPlan.annulerMinuteur();
    await _rafraichir();
  }

  // ------------------------------------------------------------ plage horaire
  Future<void> _sauverFenetre() async {
    final p = await SharedPreferences.getInstance();
    await p.setBool('fen_actif', _fenActif);
    await p.setInt('fen_de', _fenDe);
    await p.setInt('fen_a', _fenA);
    await ClimPlan.fenetre(_fenActif, _fenDe, _fenA);
  }

  Future<void> _choisirHeure(bool debut) async {
    final m = debut ? _fenDe : _fenA;
    final t = await showTimePicker(
        context: context, initialTime: TimeOfDay(hour: m ~/ 60, minute: m % 60));
    if (t == null) return;
    setState(() {
      if (debut) {
        _fenDe = t.hour * 60 + t.minute;
      } else {
        _fenA = t.hour * 60 + t.minute;
      }
    });
    await _sauverFenetre();
  }

  // ------------------------------------------------------------ automatisme
  Future<void> _sauverAuto() async {
    if (_tOff >= _tOn) _tOff = _tOn - 1;
    final p = await SharedPreferences.getInstance();
    await p.setBool('auto_actif', _autoActif);
    await p.setInt('auto_t_on', _tOn);
    await p.setInt('auto_t_off', _tOff);
    await p.setInt('auto_base', _base);
    await p.setInt('auto_extra', _extra);
    await p.setInt('auto_h_dry', _hDry);
    await p.setInt('auto_dry_min', _dryMin);
    await ClimPlan.auto({
      'actif': _autoActif,
      't_on': _tOn,
      't_off': _tOff,
      'base': _base,
      'extra': _extra,
      'h_dry': _hDry,
      'dry_min': _dryMin,
    });
    await _rafraichir();
  }

  void _regler(VoidCallback f) {
    setState(f);
    _sauverAuto();
  }

  Widget _pas(String nom, String valeur, VoidCallback moins, VoidCallback plus) {
    return Padding(
      padding: const EdgeInsets.only(top: 2),
      child: Row(
        children: [
          Expanded(child: Text(nom, style: const TextStyle(color: Couleurs.doux, fontSize: 13))),
          IconButton(
            visualDensity: VisualDensity.compact,
            icon: const Icon(Icons.remove_circle_outline_rounded, color: Couleurs.cyan),
            onPressed: moins,
          ),
          SizedBox(
            width: 72,
            child: Text(valeur,
                textAlign: TextAlign.center,
                style: const TextStyle(fontWeight: FontWeight.w800, color: Colors.white)),
          ),
          IconButton(
            visualDensity: VisualDensity.compact,
            icon: const Icon(Icons.add_circle_outline_rounded, color: Couleurs.cyan),
            onPressed: plus,
          ),
        ],
      ),
    );
  }

  // ------------------------------------------------------------ affichage
  @override
  Widget build(BuildContext context) {
    final e = widget.etat;
    final allume = _rt['on'] == true;
    final fin = (_rt['minuteurFin'] as num?)?.toInt() ?? 0;
    final resteMin =
        fin > 0 ? ((fin - DateTime.now().millisecondsSinceEpoch) / 60000).ceil() : 0;
    final phase = (_rt['phase'] ?? 'idle').toString();
    final t = e.pieceT;
    final piece = t == null
        ? 'Room: no reading (sensor not connected?)'
        : 'Room: ${t.toStringAsFixed(1)} °C · ${e.pieceH} %'
            '${e.pieceP > 0 ? ' · ${e.pieceP} hPa' : ''}';
    return Carte(
      jeu: widget.jeu,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('AC timer & automation', icone: Icons.timer_rounded),
          Text(piece, style: const TextStyle(color: Couleurs.doux)),
          SwitchListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text(allume ? 'AC is ON (assumed)' : 'AC is OFF (assumed)'),
            subtitle: const Text('Flip it if the app is out of sync with the real AC',
                style: TextStyle(fontSize: 11, color: Couleurs.gris)),
            value: allume,
            onChanged: (v) async {
              await ClimPlan.setOn(v);
              await _rafraichir();
            },
          ),
          const _Sous('Timer'),
          Wrap(
            spacing: 6,
            children: [
              for (final m in const [15, 30, 45, 60, 90, 120])
                ChoiceChip(
                  label: Text('$m min'),
                  selected: _duree == m,
                  onSelected: (_) => _choisirDuree(m),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: _lancerMinuteur,
                  icon: const Icon(Icons.play_arrow_rounded),
                  label: Text('Run for $_duree min'),
                ),
              ),
              if (resteMin > 0) ...[
                const SizedBox(width: 8),
                OutlinedButton(onPressed: _annulerMinuteur, child: const Text('Cancel')),
              ],
            ],
          ),
          if (resteMin > 0)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text('The AC turns off in $resteMin min',
                  style: const TextStyle(color: Couleurs.orange, fontSize: 12)),
            ),
          const _Sous('Daily window'),
          SwitchListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text('On at ${_hhmm(_fenDe)}, off at ${_hhmm(_fenA)}'),
            value: _fenActif,
            onChanged: (v) {
              setState(() => _fenActif = v);
              _sauverFenetre();
            },
          ),
          Row(
            children: [
              Expanded(
                  child: OutlinedButton(
                      onPressed: () => _choisirHeure(true), child: Text('From ${_hhmm(_fenDe)}'))),
              const SizedBox(width: 8),
              Expanded(
                  child: OutlinedButton(
                      onPressed: () => _choisirHeure(false), child: Text('To ${_hhmm(_fenA)}'))),
            ],
          ),
          const _Sous('Automatic (room sensor)'),
          SwitchListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: const Text('Auto mode'),
            subtitle: Text(
              phase == 'cool'
                  ? 'Cooling now'
                  : phase == 'dry'
                      ? 'Drying the air now'
                      : 'Watching the room every minute',
              style: const TextStyle(fontSize: 11, color: Couleurs.gris),
            ),
            value: _autoActif,
            onChanged: (v) => _regler(() => _autoActif = v),
          ),
          _pas('Turn on at ≥', '$_tOn °C', () => _regler(() => _tOn = (_tOn - 1).clamp(18, 40).toInt()),
              () => _regler(() => _tOn = (_tOn + 1).clamp(18, 40).toInt())),
          _pas('Turn off at ≤', '$_tOff °C',
              () => _regler(() => _tOff = (_tOff - 1).clamp(14, _tOn - 1).toInt()),
              () => _regler(() => _tOff = (_tOff + 1).clamp(14, _tOn - 1).toInt())),
          _pas('Run time', '$_base min', () => _regler(() => _base = (_base - 5).clamp(10, 120).toInt()),
              () => _regler(() => _base = (_base + 5).clamp(10, 120).toInt())),
          _pas('+ per °C above', '$_extra min', () => _regler(() => _extra = (_extra - 1).clamp(0, 10).toInt()),
              () => _regler(() => _extra = (_extra + 1).clamp(0, 10).toInt())),
          _pas('Dry mode above', '$_hDry %', () => _regler(() => _hDry = (_hDry - 5).clamp(50, 95).toInt()),
              () => _regler(() => _hDry = (_hDry + 5).clamp(50, 95).toInt())),
          _pas('Dry run time', '$_dryMin min',
              () => _regler(() => _dryMin = (_dryMin - 5).clamp(10, 120).toInt()),
              () => _regler(() => _dryMin = (_dryMin + 5).clamp(10, 120).toInt())),
          const SizedBox(height: 8),
          if (_rt['exact'] == false)
            const Text('Exact alarms are blocked: allow "Alarms & reminders" for Dadou in Android settings.',
                style: TextStyle(fontSize: 12, color: Couleurs.orange)),
          const Text(
            'Keep the phone aimed at the AC and plugged in. In Android settings set Dadou to '
            '"No restrictions" for battery and allow autostart.',
            style: TextStyle(fontSize: 11, color: Couleurs.gris),
          ),
        ],
      ),
    );
  }
}
```
### E5. Dart — `app/lib/etat.dart` (valeurs du capteur, utiles dès F)

Avant : `  final int rotEsp; // 0 = normal, 180 = écran retourné (Phase 13)`
Après : la même ligne puis :
```dart
  final double? pieceT; // température de la pièce (capteur de l'ESP32), null = pas de mesure
  final int pieceH; // humidité en %, -1 = inconnue
  final int pieceP; // pression en hPa, -1 = inconnue
```
Avant : `    this.rotEsp = 0,`
Après : la même ligne puis `    this.pieceT,` `    this.pieceH = -1,` `    this.pieceP = -1,`

Avant : `      rotEsp: _entier(m['rot_esp']) == 180 ? 180 : 0,`
Après : la même ligne puis :
```dart
      pieceT: m['piece_t'] is num ? (m['piece_t'] as num).toDouble() : null,
      pieceH: _entier(m['piece_h']),
      pieceP: _entier(m['piece_p']),
```

### E6. Dart — `app/lib/ecrans/clim.dart` : remplacer tout le fichier

```dart
// Carte « Air conditioner » (Phase 12) : télécommande de la clim York avec l'émetteur
// infrarouge du téléphone. Aucun lien avec le PC : elle marche même hors connexion.
// Chaque appui envoie la trame complète (mode, ventilation, température, swing).
// Phase 13 : swing corrigé (bit 0 = swing actif) ; les trames sont aussi confiées à Android
// (minuteur, plage horaire, automatisme) et l'état « allumée ? » est suivi (clim_plan.dart).
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../clim_ir.dart';
import '../clim_plan.dart';
import '../theme.dart';

class CarteClim extends StatefulWidget {
  final bool jeu;

  const CarteClim({super.key, this.jeu = false});

  @override
  State<CarteClim> createState() => _CarteClimState();
}

class _CarteClimState extends State<CarteClim> {
  ModeClim _mode = ModeClim.cool;
  VentClim _vent = VentClim.auto;
  int _temp = 24;
  bool _swing = false;
  String _info = "Point the phone's IR blaster at the AC, then tap a button.";

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    final p = await SharedPreferences.getInstance();
    final dispo = await ClimIr.disponible();
    if (!mounted) return;
    setState(() {
      _mode = ModeClim.values[(p.getInt('clim_mode') ?? 0).clamp(0, ModeClim.values.length - 1).toInt()];
      _vent = VentClim.values[(p.getInt('clim_vent') ?? 0).clamp(0, VentClim.values.length - 1).toInt()];
      _temp = (p.getInt('clim_temp') ?? 24).clamp(16, 30).toInt();
      _swing = p.getBool('clim_swing') ?? false;
      if (!dispo) _info = 'This phone has no IR blaster.';
    });
    _confierTrames(); // Android a besoin des trames pour le minuteur et l'automatisme
  }

  void _confierTrames() =>
      ClimPlan.enregistrerTrames(mode: _mode, vent: _vent, temp: _temp, swing: _swing);

  Future<void> _sauver() async {
    final p = await SharedPreferences.getInstance();
    await p.setInt('clim_mode', _mode.index);
    await p.setInt('clim_vent', _vent.index);
    await p.setInt('clim_temp', _temp);
    await p.setBool('clim_swing', _swing);
    _confierTrames();
  }

  Future<bool> _envoyer(List<int> octets, String nom) async {
    HapticFeedback.selectionClick();
    final ok = await ClimIr.envoyer(octets);
    if (!mounted) return ok;
    setState(() => _info = ok ? 'Sent: $nom' : 'No IR blaster found on this phone.');
    return ok;
  }

  /// Envoie l'état affiché (mode, ventilation, température, swing).
  void _envoyerEtat(String nom) {
    _sauver();
    _envoyer(ClimIr.trame(mode: _mode, vent: _vent, temp: _temp, swing: _swing), nom);
  }

  /// La touche power est une bascule : après l'envoi, on retourne l'état « allumée ? » supposé.
  Future<void> _basculer() async {
    final e = await ClimPlan.etat();
    final nouveau = e['on'] != true;
    await ClimPlan.setOn(nouveau);
    if (mounted) setState(() => _info = 'Sent: power (AC now assumed ${nouveau ? 'ON' : 'OFF'})');
  }

  /// Touche marche/arrêt : l'état affiché avec le drapeau « power ».
  Future<void> _power() async {
    final ok = await _envoyer(
      ClimIr.trame(mode: _mode, vent: _vent, temp: _temp, swing: _swing, touchePower: true),
      'power',
    );
    if (ok) await _basculer();
  }

  /// Appui long sur marche/arrêt : l'autre trame « power » vue pendant la collecte
  /// (Cool, Auto, 16 °C). À essayer si l'appui court ne fait rien.
  Future<void> _powerAlternatif() async {
    final ok = await _envoyer(
      ClimIr.trame(
          mode: ModeClim.cool, vent: VentClim.auto, temp: 16, swing: true, touchePower: true),
      'power (alt)',
    );
    if (ok) await _basculer();
  }

  void _changerTemp(int delta) {
    final t = (_temp + delta).clamp(16, 30).toInt();
    if (t == _temp) return;
    setState(() => _temp = t);
    _envoyerEtat('$_temp °C');
  }

  @override
  Widget build(BuildContext context) {
    return Carte(
      jeu: widget.jeu,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('Air conditioner', icone: Icons.ac_unit_rounded),
          Row(
            children: [
              _rond(Icons.power_settings_new_rounded, _power,
                  onLong: _powerAlternatif, couleur: Couleurs.vert),
              const Spacer(),
              _rond(Icons.remove_rounded, () => _changerTemp(-1)),
              SizedBox(
                width: 84,
                child: Text(
                  '$_temp°',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      fontSize: 34, fontWeight: FontWeight.w900, color: Colors.white),
                ),
              ),
              _rond(Icons.add_rounded, () => _changerTemp(1)),
              const Spacer(),
              _rond(Icons.swap_vert_rounded, () {
                setState(() => _swing = !_swing);
                _envoyerEtat(_swing ? 'swing on' : 'swing off');
              }, couleur: Couleurs.orange, actif: _swing),
            ],
          ),
          const SizedBox(height: 14),
          Onglets(
            onglets: const [
              (Icons.ac_unit_rounded, 'Cool'),
              (Icons.water_drop_rounded, 'Dry'),
              (Icons.air_rounded, 'Fan'),
              (Icons.autorenew_rounded, 'Auto'),
            ],
            choisi: _mode.index,
            onChange: (i) {
              setState(() => _mode = ModeClim.values[i]);
              _envoyerEtat('mode ${_mode.name}');
            },
          ),
          const SizedBox(height: 10),
          Onglets(
            onglets: const [
              (Icons.autorenew_rounded, 'Auto'),
              (Icons.signal_cellular_alt_1_bar_rounded, 'Low'),
              (Icons.signal_cellular_alt_2_bar_rounded, 'Med'),
              (Icons.signal_cellular_alt_rounded, 'High'),
            ],
            choisi: _vent.index,
            onChange: (i) {
              setState(() => _vent = VentClim.values[i]);
              _envoyerEtat('fan ${_vent.name}');
            },
          ),
          const SizedBox(height: 10),
          Text(
            _info,
            style: const TextStyle(fontSize: 12, color: Couleurs.gris),
          ),
        ],
      ),
    );
  }

  Widget _rond(IconData icone, VoidCallback onTap,
      {VoidCallback? onLong, Color couleur = Couleurs.cyan, bool actif = false}) {
    return Material(
      color: actif ? couleur.withValues(alpha: 0.25) : Colors.white.withValues(alpha: 0.08),
      shape: const CircleBorder(),
      child: InkWell(
        customBorder: const CircleBorder(),
        onTap: onTap,
        onLongPress: onLong,
        child: Padding(
          padding: const EdgeInsets.all(13),
          child: Icon(icone, color: couleur, size: 24),
        ),
      ),
    );
  }
}
```

### E7. Dart — `app/lib/ecrans/controles.dart`

Avant : `import '../actions.dart';`
Après : `import '../actions.dart';` puis `import '../clim_plan.dart';`

Avant :
```dart
        CarteClim(jeu: e.enJeu),
        const SizedBox(height: 14),
```
Après :
```dart
        CarteClim(jeu: e.enJeu),
        const SizedBox(height: 14),
        CarteClimPlan(etat: e, jeu: e.enJeu),
        const SizedBox(height: 14),
```

### E8. Agent PC — `tools/agent/serveur_app.py` (`_http`)

Avant :
```python
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
```
Après :
```python
        if morceaux.path not in ("/widget", "/etat_court", "/clim_mesure", "/clim_maj"):
            return None
        if not self.token_valide(requete.headers.get("X-Token", "")):
            return connexion.respond(HTTPStatus.UNAUTHORIZED, "Unauthorized\n")
        if morceaux.path == "/clim_mesure":  # Phase 13 : capteur de la pièce, pour l'automatisme
            try:
                mesure = await self._appel("piece")
            except Exception as e:
                mesure = {"ok": False, "erreur": str(e)}
            return connexion.respond(HTTPStatus.OK, json.dumps(mesure, ensure_ascii=False))
        if morceaux.path == "/clim_maj":  # Phase 13 : état de la clim, poussé par le téléphone
            q = {k: v[0] for k, v in urllib.parse.parse_qs(morceaux.query).items()}
            try:
                await self._appel("clim_maj", q)
            except Exception:
                pass
            return connexion.respond(HTTPStatus.OK, "OK\n")
        if morceaux.path == "/etat_court":
            try:
                court = await self._appel("etat_court")
            except Exception as e:
                court = {"erreur": str(e)}
            return connexion.respond(HTTPStatus.OK, json.dumps(court, ensure_ascii=False))
```

### E9. Agent PC — `tools/agent/agent_pc.py`

(a) Avant :
```python
        self.rot_esp = 180 if int(charger_preferences().get("rot_esp", 0)) == 180 else 0
```
Après : la même ligne puis :
```python
        self.piece = {}          # Phase 13 : dernière mesure du capteur (CLIMAT), voir lire_climat
        self.clim = None         # Phase 13 : état de la clim donné par le téléphone (/clim_maj)
```

(b) Avant :
```python
            if ligne and ligne != "OK":
                print(f"[esp32] {ligne}")
```
Après :
```python
            if ligne.startswith("CLIMAT "):  # mesure du capteur : pas dans le journal
                self.lire_climat(ligne)
                continue
            if ligne and ligne != "OK":
                print(f"[esp32] {ligne}")
```

(c) Avant :
```python
    def boucle_lecture(self):
```
Après (3 méthodes ajoutées juste avant) :
```python
    def lire_climat(self, ligne):
        """CLIMAT t10 humidité pression : mesure du capteur branché sur l'ESP32 (t10 = 10 × °C)."""
        try:
            t10, h, p = [int(x) for x in ligne.split()[1:4]]
        except ValueError:
            return
        self.piece = {"t": t10 / 10.0, "h": h, "p": p, "vu": time.time()}

    def piece_pour_app(self):
        """Pour /clim_mesure et l'app : la mesure, ou ok=False si elle a plus de 30 s."""
        p = self.piece
        if not p or time.time() - p["vu"] > 30:
            return {"ok": False}
        return {"ok": True, "t": p["t"], "h": p["h"], "p": p["p"], "age": round(time.time() - p["vu"])}

    def clim_maj(self, d):
        """État de la clim poussé par le téléphone : on, mode, temp, reste (min), auto."""
        try:
            mode = str(d.get("mode", "cool"))
            if mode not in ("cool", "dry", "fan", "auto"):
                mode = "cool"
            reste = max(0, min(999, int(float(d.get("reste", 0)))))
            self.clim = {
                "on": 1 if str(d.get("on", "0")) == "1" else 0,
                "mode": mode,
                "temp": max(16, min(30, int(float(d.get("temp", 24))))),
                "fin": time.time() + reste * 60 if reste > 0 else 0,
                "auto": 1 if str(d.get("auto", "0")) == "1" else 0,
            }
        except (TypeError, ValueError):
            return
        self.precedent.pop("CLIM", None)  # renvoie la ligne à l'ESP32 au prochain tour

    def boucle_lecture(self):
```

(d) `_mesures_lentes` — Avant :
```python
        if self.precedent.get("ROT_ESP") != self.rot_esp:
            self.precedent["ROT_ESP"] = self.rot_esp
            self.liaison.envoyer(f"ROT_ESP {self.rot_esp}")
```
Après : ce bloc puis :
```python
        c = self.clim
        if c:
            reste = max(0, int((c["fin"] - time.time()) / 60) + 1) if c["fin"] else 0
            ligne = "CLIM %d %s %d %d %d" % (c["on"], c["mode"], c["temp"], reste, c["auto"])
            if self.precedent.get("CLIM") != ligne:
                self.precedent["CLIM"] = ligne
                self.liaison.envoyer(ligne)
```

(e) `donnees` — Avant :
```python
        p = self.precedent
        self.donnees = {
```
Après :
```python
        p = self.precedent
        piece = self.piece if self.piece and time.time() - self.piece["vu"] < 30 else None
        self.donnees = {
```
Et avant :
```python
            "master_v": self.master.version, "master_actif": self.master.actif,
        }
```
Après :
```python
            "master_v": self.master.version, "master_actif": self.master.actif,
            # Phase 13 : capteur de la pièce (null / -1 = pas de mesure)
            "piece_t": piece["t"] if piece else None,
            "piece_h": piece["h"] if piece else -1,
            "piece_p": piece["p"] if piece else -1,
        }
```

(f) `rappels_app` — Avant :
```python
            "etat_court": self.etat_court,
```
Après :
```python
            "etat_court": self.etat_court,
            "piece": self.piece_pour_app, "clim_maj": self.clim_maj,
```

### E10. ESP32 — `esp/main.py` (le CLIM est reçu dès maintenant, affiché à l'étape G)

Avant :
```python
        "master": None}        # Phase 11 : données du master (ligne MASTER du PC)
```
Après :
```python
        "master": None,        # Phase 11 : données du master (ligne MASTER du PC)
        "clim": None,          # Phase 13 : état de la clim (ligne CLIM du PC)
        "piece": None}         # Phase 13 : (°C, % humidité, hPa) du capteur, None = pas de capteur
```

Avant :
```python
    if cmd == "ROT_ESP":
```
Après (CLIM inséré juste avant) :
```python
    if cmd == "CLIM":
        # CLIM on mode temp reste auto : envoyé par le PC, venu du téléphone (minutes restantes)
        try:
            p = arg.split()
            nouveau = {"on": p[0] == "1", "mode": p[1], "temp": int(p[2]), "reste": int(p[3]),
                       "auto": p[4] == "1", "recu": time.ticks_ms()}
        except (ValueError, IndexError):
            return "ERR utilise : CLIM on mode temp reste auto"
        ancien = etat["clim"]
        etat["clim"] = nouveau
        if ancien is not None and ancien["on"] != nouveau["on"]:
            if not nouveau["on"]:
                ui.reagir("thermo", "AC off")
            elif nouveau["mode"] == "dry":
                ui.reagir("thermo", "AC dry mode")
            else:
                ui.reagir("thermo", "AC on %d°" % nouveau["temp"])
        return "OK"
    if cmd == "ROT_ESP":
```

### Test E
- Compiler : `flutter analyze`, `flutter test`, `cd app && flutter build apk` ; `py -m py_compile` ; copier `esp/main.py` sur la carte (PAUSE) ; redémarrer l'agent ; installer l'APK.
- Mihaja (téléphone visant la clim, branché) : ouvrir Controls, appuyer une fois sur le réglage de température (range les trames) ; **Run for 15 min** → la clim s'allume tout de suite, le texte « The AC turns off in 15 min » apparaît ; **fermer complètement l'app** ; au bout de 15 min la clim s'éteint et une notification « Timer finished » apparaît. Test rapide possible : durée 15 min mais regarder `agent.log` n'est pas nécessaire.
- Plage horaire : régler « From » dans 2 min et « To » dans 4 min, activer ; la clim s'allume puis s'éteint toute seule ; le lendemain elle recommence (alarme réarmée).
- Redémarrer le téléphone avec un minuteur en cours : l'extinction a lieu quand même.
- `agent.log` : pas d'erreur sur `/clim_maj`. Console agent : `ETAT` montre `CLIM …` dans `precedent`. L'ESP32 répond `OK` (pas `ERR commande inconnue`).
- Commit : `Phase 13E : minuteur, plage horaire, liaison clim vers le PC et l'ESP32`.
- Si l'alarme n'arrive pas à l'heure : Xiaomi/HyperOS tue l'app → Paramètres → Applications → Dadou → Économie de batterie « Aucune restriction » + « Démarrage automatique » ON ; autorisation « Alarmes et rappels » ON. Sinon → Opus avec `adb logcat -s ClimPlan` (ajouter des `Log.d` si besoin).

---

## F — Capteur AHT20 + BMP280 et automatisme

Branchement (3,3 V, **jamais 5 V**) : capteur VDD → 3V3 de la carte, GND → GND, SDA et SCL → **deux GPIO libres de l'en-tête** (au choix de Mihaja ; GPIO 1 à 13 sont des choix sûrs, pas ceux de l'écran 39-42/45/48, SD 14-18/21, LED 38, BOOT 0, USB 19/20). Poser le capteur à 20-30 cm de la carte et loin de la sortie d'air du portable (sinon il mesure le portable).

### F1. Trouver les pins — nouveau fichier `tools/i2c_scan.py`

```python
# Cherche où le capteur est branché : essaie toutes les paires de GPIO libres et affiche celles
# où quelque chose répond en I2C (AHT20 = 0x38, BMP280 = 0x76 ou 0x77).
# Lancer avec l'agent en PAUSE :  py -m mpremote connect COMx run tools/i2c_scan.py
from machine import I2C, Pin

LIBRES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 43, 44, 47]
trouve = []
for sda in LIBRES:
    for scl in LIBRES:
        if sda == scl:
            continue
        try:
            i2c = I2C(0, sda=Pin(sda), scl=Pin(scl), freq=100000)
            adr = i2c.scan()
        except Exception:
            continue
        if adr:
            print("SDA", sda, "SCL", scl, [hex(a) for a in adr])
            trouve.append((sda, scl))
print("fini :", trouve if trouve else "rien trouvé (vérifier le câblage et 3V3)")
```
Lancer. Attendu : une ligne avec `0x38` (et `0x76`/`0x77`) pour **une** paire (SDA, SCL). Si plusieurs paires affichent des adresses, prendre celle qui contient `0x38` ; si aucune → recontrôler les fils (SDA/SCL inversés = aucune réponse, essayer l'inversion physique).

### F2. Pilote — nouveau fichier `esp/lib/capteur.py`

```python
# Capteur de la pièce (Phase 13) : AHT20 (température + humidité) et BMP280 (pression), en I2C.
# Mesure toutes les 5 s sans bloquer l'écran : on déclenche la mesure, puis on la lit 90 ms plus tard.
import struct
import time

from machine import I2C, Pin

SDA = None   # numéros des GPIO : à remplir avec le résultat de tools/i2c_scan.py
SCL = None
DECALAGE_T = 0.0    # °C ajoutés à la mesure (la carte chauffe un peu : à régler avec un vrai thermomètre)
PERIODE_MS = 5000
AHT = 0x38


class Capteur:
    def __init__(self):
        self.ok = False
        self._t = self._h = self._p = None
        self._lance = None
        self._prochain = time.ticks_ms()
        self._echecs = 0
        self._bmp = None
        if SDA is None or SCL is None:
            return
        try:
            self.i2c = I2C(0, sda=Pin(SDA), scl=Pin(SCL), freq=100_000)
            adresses = self.i2c.scan()
            if AHT not in adresses:
                print("CAPTEUR AHT20 absent")
                return
            time.sleep_ms(40)
            if not (self.i2c.readfrom(AHT, 1)[0] & 0x08):  # pas calibré : commande d'initialisation
                self.i2c.writeto(AHT, b"\xBE\x08\x00")
                time.sleep_ms(20)
            for a in (0x76, 0x77):
                if a in adresses:
                    try:
                        self._bmp_init(a)
                    except OSError:
                        self._bmp = None
                    break
            self.ok = True
        except Exception as e:
            print("CAPTEUR erreur %s" % e)

    # --- BMP280 (formules du constructeur, version à virgule flottante) ----------------
    def _bmp_init(self, adr):
        if self.i2c.readfrom_mem(adr, 0xD0, 1)[0] not in (0x58, 0x60):
            raise OSError("pas un BMP280")
        self._bmp = adr
        (self.T1, self.T2, self.T3, self.P1, self.P2, self.P3, self.P4, self.P5, self.P6,
         self.P7, self.P8, self.P9) = struct.unpack("<HhhHhhhhhhhh", self.i2c.readfrom_mem(adr, 0x88, 24))

    def _bmp_lire(self):
        d = self.i2c.readfrom_mem(self._bmp, 0xF7, 6)
        adc_p = (d[0] << 12) | (d[1] << 4) | (d[2] >> 4)
        adc_t = (d[3] << 12) | (d[4] << 4) | (d[5] >> 4)
        v1 = (adc_t / 16384.0 - self.T1 / 1024.0) * self.T2
        v2 = ((adc_t / 131072.0 - self.T1 / 8192.0) ** 2) * self.T3
        tfine = v1 + v2
        v1 = tfine / 2.0 - 64000.0
        v2 = v1 * v1 * self.P6 / 32768.0
        v2 = v2 + v1 * self.P5 * 2.0
        v2 = v2 / 4.0 + self.P4 * 65536.0
        v1 = (self.P3 * v1 * v1 / 524288.0 + self.P2 * v1) / 524288.0
        v1 = (1.0 + v1 / 32768.0) * self.P1
        if v1 == 0:
            return None
        p = 1048576.0 - adc_p
        p = (p - v2 / 4096.0) * 6250.0 / v1
        v1 = self.P9 * p * p / 2147483648.0
        v2 = p * self.P8 / 32768.0
        return (p + (v1 + v2 + self.P7) / 16.0) / 100.0  # hPa

    # --- boucle -------------------------------------------------------------------------
    def _echec(self, maintenant):
        self._lance = None
        self._echecs += 1
        self._prochain = time.ticks_add(maintenant, PERIODE_MS)
        if self._echecs >= 3:
            self._t = self._h = self._p = None  # plus de mesure fiable : l'écran n'affiche rien

    def pas(self, maintenant):
        """À appeler à chaque tour de boucle. Renvoie True quand une nouvelle mesure est prête."""
        if not self.ok:
            return False
        if self._lance is None:
            if time.ticks_diff(maintenant, self._prochain) >= 0:
                try:
                    self.i2c.writeto(AHT, b"\xAC\x33\x00")
                    if self._bmp:
                        self.i2c.writeto_mem(self._bmp, 0xF4, b"\x25")  # une mesure (mode forcé)
                    self._lance = maintenant
                except OSError:
                    self._echec(maintenant)
            return False
        if time.ticks_diff(maintenant, self._lance) < 90:
            return False
        try:
            d = self.i2c.readfrom(AHT, 7)
            if d[0] & 0x80:
                raise OSError("occupé")
            h = ((d[1] << 12) | (d[2] << 4) | (d[3] >> 4)) * 100 / 1048576
            t = (((d[3] & 0x0F) << 16) | (d[4] << 8) | d[5]) * 200 / 1048576 - 50 + DECALAGE_T
            if not (-20 <= t <= 60) or not (0 <= h <= 100):
                raise OSError("mesure absurde")
            p = self._bmp_lire() if self._bmp else None
        except OSError:
            self._echec(maintenant)
            return False
        self._lance = None
        self._echecs = 0
        self._prochain = time.ticks_add(maintenant, PERIODE_MS)
        # lissage léger : le bruit de mesure ne fait pas clignoter l'écran ni l'automatisme
        self._t = t if self._t is None else self._t + 0.4 * (t - self._t)
        self._h = h if self._h is None else self._h + 0.4 * (h - self._h)
        if p is not None:
            self._p = p
        return True

    def mesure(self):
        """(°C, % d'humidité, hPa) ou None. hPa = 0 si pas de BMP280."""
        if self._t is None:
            return None
        return (self._t, self._h, self._p or 0)
```
Ouvre `esp/lib/capteur.py` et mets `SDA` et `SCL` aux valeurs trouvées en F1 (ex. `SDA = 8`, `SCL = 9`).

### F3. `esp/main.py`

Avant :
```python
from meteo import Meteo
from ui import Interface
```
Après :
```python
from capteur import Capteur
from meteo import Meteo
from ui import Interface
```

Avant :
```python
meteo = Meteo(reglages)  # lance la connexion Wi-Fi (sans attendre)
```
Après :
```python
meteo = Meteo(reglages)  # lance la connexion Wi-Fi (sans attendre)
capteur = Capteur()      # Phase 13 : AHT20 + BMP280 (silencieux si pas branché)
```

Avant (dans la boucle principale) :
```python
        maintenant = time.ticks_ms()
        if etat["connecte"] and time.ticks_diff(maintenant, derniere_donnee) > ATTENTE_ABSENT:
```
Après :
```python
        maintenant = time.ticks_ms()
        if capteur.pas(maintenant):
            etat["piece"] = capteur.mesure()
            if etat["piece"]:
                t, h, p = etat["piece"]
                print("CLIMAT %d %d %d" % (round(t * 10), round(h), round(p)))
        elif capteur.ok and capteur.mesure() is None:
            etat["piece"] = None  # le capteur ne répond plus : l'écran n'affiche plus la pièce
        if etat["connecte"] and time.ticks_diff(maintenant, derniere_donnee) > ATTENTE_ABSENT:
```

### F4. Réglage de l'automatisme — déjà fait en E (Kotlin + `lib/clim_plan.dart`)

Règles appliquées toutes les minutes par Android (`ClimPlan.auto`), avec la mesure lue via `GET /clim_mesure` :
- Clim éteinte + `T ≥ t_on` → **Cool** (trame courante avec « power »), durée = `base + extra × (T − t_on)` min, entre 10 et 180 ; arrêt plus tôt si `T ≤ t_off`.
- Clim éteinte + `T < t_on` + `humidité ≥ h_dry` → **Dry** pendant `dry_min` min ; arrêt plus tôt si l'humidité redescend à `h_dry − 8`.
- Pause de **3 min** entre un arrêt et le démarrage suivant (compresseur). Après une action à la main dans l'app, l'auto se tait 30 min. Clim déjà allumée à la main → l'auto n'y touche pas.
- Capteur ou PC injoignable → il ne fait rien (pas d'allumage « à l'aveugle »).
- L'état supposé (`on`) peut se désynchroniser (toggle) : l'interrupteur « AC is ON/OFF (assumed) » le corrige sans émettre d'IR.

### Test F
- `py -m py_compile esp/lib/capteur.py esp/main.py tools/agent/agent_pc.py` ; copier `esp/lib/capteur.py` et `esp/main.py` sur la carte (PAUSE de l'agent) ; relancer l'agent.
- `agent.log` : aucune ligne `CAPTEUR …` d'erreur. Console agent `ETAT` ou l'app : « Room: 24.3 °C · 58 % · 1008 hPa » dans la carte « AC timer & automation » (se met à jour toutes les 5 s). Souffler sur le capteur : l'humidité monte.
- Comparer avec un thermomètre (ou la météo de la pièce) 10 min plus tard ; écart constant → ajuster `DECALAGE_T`.
- Automatisme : « Turn on at ≥ » = température actuelle − 1 → au passage suivant (≤ 1 min) la clim s'allume (notification « AC on (auto) … »), puis s'éteint à la fin de la durée ou à `t_off`. Remettre les vrais seuils après le test. Dry : mettre « Dry mode above » juste sous l'humidité actuelle et `t_on` à 40 → la clim démarre en Dry.
- Commit : `Phase 13F : capteur AHT20/BMP280, mesure vers le PC, automatisme`.

---

## G — Écran / avatar / animations : clim et pièce

Rien de nouveau à générer (pas de nouveaux `.bin`) : on réutilise `ico_thermo`, `ico_eau`, `goutte` et on dessine les flocons / traits d'air par code. Toutes les modifications sont dans `esp/lib/ui.py`.

Ce que ça donne :
- Coin haut droit (scènes normale, calme, nuit) : « AC 24° » (cyan) ou « AC off » (gris), et sous la ligne « 24.1° 58 % » — seulement s'il y a la place à droite de l'heure.
- Scène normale : la ligne du bas alterne toutes les 5 s : PC (batterie, casque) → « AC Cool 24° • off in 23 min • auto » → « Room 24.1° • 58 % ».
- Scène calme : idées « It's 29°: AC on? » ou « Humid air: try Dry mode? » ; le coin haut droit aussi.
- Mode jeu : « Session: … », « AC … » et « Room … » dans la ligne du bas qui tourne.
- Mascotte : **flocons** qui tombent (Cool), **gouttes** (Dry), **traits d'air** (Fan/Auto) quand la clim tourne ; **goutte de sueur** quand la pièce est ≥ 29 °C et la clim éteinte ; bulle « thermo » à l'allumage/arrêt (déjà géré par `CLIM` en E10).

### G1. Constantes — après `CHAUFFE_RAPPEL_MS = …`

Avant :
```python
CHAUFFE_RAPPEL_MS = 5 * 60 * 1000
```
Après :
```python
CHAUFFE_RAPPEL_MS = 5 * 60 * 1000
PIECE_CHAUDE = 29          # °C : la mascotte transpire si la pièce est plus chaude et la clim éteinte
PIECE_SUGGERE = 28         # °C : la scène calme propose d'allumer la clim
PIECE_HUMIDE = 75          # % : la scène calme propose le mode Dry
```

### G2. `__init__` de `Interface`

Avant :
```python
        self.bulle_calme = None  # icône de la suggestion affichée (scène calme)
```
Après :
```python
        self.bulle_calme = None  # icône de la suggestion affichée (scène calme)
        self.piece_chaude = False  # Phase 13 : pièce trop chaude et clim éteinte (sueur de la mascotte)
```

### G3. `dessiner`

Avant :
```python
        self.lum = etat.get("lum", 85)
        mode = self._choisir_mode(etat, maintenant)
```
Après :
```python
        self.lum = etat.get("lum", 85)
        piece = etat.get("piece")
        clim = etat.get("clim")
        self.piece_chaude = bool(piece) and piece[0] >= PIECE_CHAUDE and not (clim and clim["on"])
        mode = self._choisir_mode(etat, maintenant)
```

### G4. Nouvelles méthodes — à ajouter juste avant `def _heure_date(self, carte, y_heure=8):`

```python
    # ------------------------------------------------------------------ clim et pièce (Phase 13)
    def _clim_actif(self, etat):
        c = etat.get("clim")
        return c if c and c["on"] else None

    def _texte_clim(self, etat, maintenant):
        """« AC Cool 24° • off in 23 min • auto », ou None si la clim est éteinte / inconnue."""
        c = self._clim_actif(etat)
        if not c:
            return None
        noms = {"cool": "Cool", "dry": "Dry", "fan": "Fan", "auto": "Auto"}
        texte = "AC %s %d°" % (noms.get(c["mode"], "Cool"), c["temp"])
        reste = c["reste"] - time.ticks_diff(maintenant, c["recu"]) // 60000
        if c["reste"] > 0 and reste > 0:
            texte += " • off in %s" % duree_texte(reste)
        if c["auto"]:
            texte += " • auto"
        return texte

    def _texte_piece(self, etat):
        piece = etat.get("piece")
        if not piece:
            return None
        return "Room %.1f° • %d %%" % (piece[0], piece[1])

    def _coin_clim(self, etat, carte, y=8):
        """Coin haut droit : état de la clim (AC 24°) et climat de la pièce (24.1° 58 %)."""
        fb = self.fb
        libre = 186 - (16 + self.f_heure.largeur("88:88") + 10)  # place à droite de l'heure
        c = etat.get("clim")
        if c:
            texte = ("AC %d°" % c["temp"]) if c["on"] else "AC off"
            if self.f_s.largeur(texte) <= libre:
                self.f_s.ecrire(fb, texte, 186 - self.f_s.largeur(texte), y + 2,
                                CYAN if c["on"] else GRIS, carte)
        piece = etat.get("piece")
        if piece:
            texte = "%.1f° %d %%" % (piece[0], piece[1])
            if self.f_xs.largeur(texte) <= libre:
                self.f_xs.ecrire(fb, texte, 186 - self.f_xs.largeur(texte), y + 22, DOUX, carte)

    def _ligne_bas(self, etat, carte, maintenant):
        """Ligne du bas de la scène normale : PC (batterie, casque), puis clim et pièce
        quand il y en a, en alternance toutes les 5 s."""
        extras = [t for t in (self._texte_clim(etat, maintenant), self._texte_piece(etat)) if t]
        phase = (maintenant // 5000) % (1 + len(extras))
        if phase == 0:
            self._ligne_bas_pc(etat, carte)
            return
        texte = extras[phase - 1]
        self.fb.blit(self.icones["thermo"], 14, 145, CLE)
        self.f_xs.ecrire(self.fb, self.f_xs.couper(texte, 150), 36, 147,
                         CYAN if texte.startswith("AC") else DOUX, carte)

    def _ligne_bas_pc(self, etat, carte):
        fb = self.fb
        st = etat["stat"]
        x = 16
        if st["bat"] >= 0:
            if st["chg"]:
                fb.blit(self.ico_eclair, x, 147, CLE)
                x += 13
            couleur_bat = ROUGE if st["bat"] < 20 and not st["chg"] else DOUX
            x = self.f_xs.ecrire(fb, "%d %%" % st["bat"], x, 147, couleur_bat, carte) + 8
        if etat["evt"]["casque"]:
            fb.blit(self.ico_casque, x, 147, CLE)
            nom = self.f_xs.couper(etat["evt"]["casque"], 176 - x - 14)
            self.f_xs.ecrire(fb, nom, x + 14, 147, CYAN, carte)

    def _flocon(self, x, y, ph):
        lum = int(255 * min(1.0, (1 - ph) * 1.6))
        c = rgb565(lum, lum, 255)
        fb = self.fb
        fb.hline(x - 2, y, 5, c)
        fb.vline(x, y - 2, 5, c)
        for dx, dy in ((-1, -1), (1, 1), (-1, 1), (1, -1)):
            fb.pixel(x + dx, y + dy, c)

    def _effets_clim(self, etat, t):
        """Autour de la mascotte quand la clim tourne : flocons (Cool), gouttes (Dry),
        traits d'air (Fan / Auto). Dessiné AVANT la mascotte : elle reste devant."""
        c = self._clim_actif(etat)
        if not c:
            return
        fb = self.fb
        for i in range(4):
            ph = (t * 0.45 + i / 4) % 1
            x = PERSO_X + 6 + i * 24 + int(math.sin(t * 1.3 + i * 2) * 4)
            y = 4 + int(ph * (PERSO_H - 10))
            if c["mode"] == "dry":
                fb.blit(self.goutte, x, y, CLE)
            elif c["mode"] == "cool":
                self._flocon(x, y, ph)
            else:
                xl = PERSO_X - 10 + int(ph * 90)
                fb.hline(xl, 20 + i * 14, 10, rgb565(150, 200, 235))

```

### G5. `_scene_normale` — remplacer la ligne du bas

Avant :
```python
        secondes = self._heure_date(carte)
        fb.fill_rect(18, 76, 158, 3, rgb565(45, 40, 80))
```
Après :
```python
        secondes = self._heure_date(carte)
        self._coin_clim(etat, carte)
        fb.fill_rect(18, 76, 158, 3, rgb565(45, 40, 80))
```

Avant :
```python
        # ligne du bas : batterie + casque
        x = 16
        if st["bat"] >= 0:
            if st["chg"]:
                fb.blit(self.ico_eclair, x, 147, CLE)
                x += 13
            couleur_bat = ROUGE if st["bat"] < 20 and not st["chg"] else DOUX
            x = self.f_xs.ecrire(fb, "%d %%" % st["bat"], x, 147, couleur_bat, carte) + 8
        if etat["evt"]["casque"]:
            fb.blit(self.ico_casque, x, 147, CLE)
            nom = self.f_xs.couper(etat["evt"]["casque"], 176 - x - 14)
            self.f_xs.ecrire(fb, nom, x + 14, 147, CYAN, carte)
```
Après :
```python
        # ligne du bas : PC (batterie, casque), clim, pièce — en alternance
        self._ligne_bas(etat, carte, maintenant)
```
(L'ancien bloc existe maintenant dans `_ligne_bas_pc`.)

### G6. Scène calme

Avant (dans `_scene_calme`) :
```python
        fb = self.fb
        self._heure_date(carte)
        liste = self._suggestions(etat)
```
Après :
```python
        fb = self.fb
        self._heure_date(carte)
        self._coin_clim(etat, carte)
        liste = self._suggestions(etat)
```

Avant (dans `_suggestions`) :
```python
        jours = etat.get("meteo") or []
        if jours:
            j = jours[0]
```
Après :
```python
        piece = etat.get("piece")
        clim = etat.get("clim")
        if piece and not (clim and clim["on"]):
            if piece[0] >= PIECE_SUGGERE:
                liste.insert(0, ("thermo", "It's %.0f°: AC on?" % piece[0]))
            elif piece[1] >= PIECE_HUMIDE:
                liste.insert(0, ("eau", "Humid air: try Dry mode?"))
        jours = etat.get("meteo") or []
        if jours:
            j = jours[0]
```

### G7. Scène nuit

Avant (dans `_scene_nuit`) :
```python
        self._heure_date(carte, y_heure=4)
        titre = "PC locked" if mode == "verrou" else "PC asleep"
```
Après :
```python
        self._heure_date(carte, y_heure=4)
        self._coin_clim(etat, carte, y=4)
        titre = "PC locked" if mode == "verrou" else "PC asleep"
```

### G8. Mode jeu — lignes du bas

Avant :
```python
        total = etat["perf"].get("total", -1)
        if total >= 1:
            textes.append("Game total: %s" % duree_texte(total))
```
Après :
```python
        total = etat["perf"].get("total", -1)
        if total >= 1:
            textes.append("Game total: %s" % duree_texte(total))
        for extra in (self._texte_clim(etat, maintenant), self._texte_piece(etat)):
            if extra:
                textes.append(extra)
```

### G9. Mascotte — `_mascotte`

Avant :
```python
        fb.blit(self.persos[(casque, visage)], PERSO_X, PERSO_Y + dy, CLE)
```
Après :
```python
        self._effets_clim(etat, t)
        fb.blit(self.persos[(casque, visage)], PERSO_X, PERSO_Y + dy, CLE)
```

Avant :
```python
        if mode == "jeu" and self.chaud:
```
Après :
```python
        if (mode == "jeu" and self.chaud) or (self.piece_chaude and not dort):
```

Commentaire d'en-tête de `ui.py` : ajoute la ligne `# Phase 13 : clim (AC), climat de la pièce (capteur), flocons / gouttes / traits d'air autour de la mascotte.`

### Test G
- `py -m py_compile esp/lib/ui.py` ; copier `esp/lib/ui.py` sur la carte (PAUSE) ; relancer l'agent.
- Mihaja regarde chaque scène (la clim allumée depuis l'app, puis éteinte) : normale (coin haut droit + ligne du bas qui tourne), calme (attendre l'inactivité), nuit (verrouiller le PC), jeu. Flocons quand la clim est en Cool, gouttes en Dry, traits en Fan/Auto. Faire chauffer artificiellement (`PIECE_CHAUDE = 20` un instant) → la mascotte transpire.
- Si le coin haut droit **chevauche l'heure** : mettre le texte plus court (`"%d°"`) ou baisser `libre`. Si le texte du bas déborde : `couper(texte, 130)`.
- Si une erreur survient : elle est dans `erreur.txt` sur la carte (`py -m mpremote connect COMx fs cat :erreur.txt`).
- Commit : `Phase 13G : écran, mascotte et animations pour la clim et le capteur`.

---

## H — Clôture

1. `flutter analyze`, `flutter test`, `py -m py_compile` sur tous les `.py` modifiés ; `flutter build apk` ; installer l'APK (Mihaja).
2. Mettre à jour `CLAUDE.md` du dossier Micro : architecture (Kotlin `ClimPlan`, canal `dadou/clim`, `/clim_maj`, `/clim_mesure`, `CLIM`/`CLIMAT`/`ROT_ESP`), brochage du capteur (SDA/SCL trouvés), carte en MicroPython.
3. Ajouter `docs/etat_code_phase13.md` : commits A–G, versions, port COM, pins du capteur, `DECALAGE_T`, seuils choisis, résultats des tests de chaque étape (3 lignes par étape), ce qui reste.
4. `git add -A` (sans `bin/`, `secrets.py`, `appareils.json`, `agent.log`), commit `Phase 13H : documentation`, `git push`.
5. Dire à Mihaja : pousse le dépôt pour que Claude web puisse relire, et envoie `docs/etat_code_phase13.md`.

---

## Prompts à copier dans Claude Code (un par étape)

Envoyer d'abord seul : `/model haiku` (A, H) ou `/model sonnet` (B à G). Puis :

```
Lis docs/micro_phase13.md. Applique l'étape <LETTRE> seulement, bloc par bloc, exactement comme écrit.
Test à blanc d'abord : vérifie que chaque « Avant » existe une seule fois dans le fichier. S'il manque ou s'il y en a plusieurs, STOP et dis-moi lequel, ne devine pas.
Ensuite applique, compile/teste comme décrit dans « Test <LETTRE> », corrige au plus petit, commite (un commit pour l'étape), pousse.
Réponse courte : étapes faites, sorties des tests, ce que Mihaja doit faire à la main. Pas de recap des fichiers.
```
Pour **C** : même prompt, mais dis-moi à chaque point où Mihaja doit agir (BOOT, débrancher) et attends son OK. Pour **B** et **F** : après le test, résume les lignes du journal en 3 lignes.

## À faire par Mihaja (rappel)
- **C** : mode BOOT (débrancher, maintenir BOOT, rebrancher, relâcher) puis rebrancher normalement.
- **F** : câbler le capteur (3V3, GND, 2 GPIO), lire le résultat de `i2c_scan.py`.
- **E/F** : Android → Dadou → Batterie « Aucune restriction », Démarrage automatique, « Alarmes et rappels » autorisé, notifications autorisées. Téléphone visant la clim, branché la nuit.
- Après chaque étape testée : envoyer à Claude web un mot (« A ok », « B : log … ») ou la sortie en cas de souci.
