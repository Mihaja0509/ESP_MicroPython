# Phase 12 — Clim York depuis le téléphone (app Dadou, émetteur IR du Xiaomi)

Date : 2026-11-06 · Statut : à appliquer · Projet : Micro (dépôt ESP_MicroPython) · Étape : contrôle de la clim, première version sans ESP32
Basée sur : commit `c9e5437` (Phase 11-bis) du dépôt ESP_MicroPython, lu en entier côté `app/`. Si tu as appliqué la 11-ter depuis, le test à blanc le dira.

## Pourquoi
Le module IR de l'ESP32 est en panne (LED infrarouge morte). Le Xiaomi 17 a un émetteur IR et on connaît maintenant le protocole de la clim (`protocole_clim.md`). On met donc la télécommande de la clim directement dans Dadou : pas de module, pas de fils, et l'app est programmable. L'ESP32 reprendra la main plus tard avec les mêmes trames, pour les minuteries et l'accès à distance (le téléphone doit viser la clim, l'ESP32 reste en place).

## Ce que contient la phase
Une carte « Air conditioner » en haut de l'onglet **Controls** : bouton marche/arrêt, température (16 à 30 °C), modes Cool / Dry / Fan / Auto, ventilation Auto / Low / Med / High, swing. Chaque appui envoie la trame complète par l'émetteur IR du téléphone. L'état affiché est mémorisé. La carte marche sans le PC (aucune connexion nécessaire).

Un point reste à trancher pendant les tests : la marche/arrêt. Deux trames « power » ont été vues pendant la collecte. Appui court = l'état affiché avec le drapeau power ; appui long = l'autre trame (Cool, Auto, 16 °C). Dis-moi laquelle allume et laquelle éteint, ou si la clim bascule à chaque trame.

## Partie 1 — Nouveaux fichiers

### `Micro/app/lib/clim_ir.dart`
```dart
// Clim par infrarouge (Phase 12) : protocole de la clim York, décodé depuis les trames du
// Xiaomi (voir docs/protocole_clim.md), et envoi par l'émetteur IR du téléphone
// (ConsumerIrManager, côté Android : MainActivity.kt, canal « dadou/ir »).
import 'package:flutter/services.dart';

enum ModeClim { cool, dry, fan, auto }

enum VentClim { auto, low, med, high }

class ClimIr {
  static const _canal = MethodChannel('dadou/ir');

  /// Porteuse des télécommandes infrarouges.
  static const int frequence = 38000;

  // Durées en microsecondes (mesurées sur les vraies trames). Si la clim réagit mal,
  // c'est ici qu'on ajuste.
  static const int _marque = 412;
  static const int _zero = 350;
  static const int _un = 905;
  static const int _enteteMarque = 4500;
  static const int _enteteEspace = 2500;
  static const int _silence = 19950;
  static const int _marqueFin = 4550;

  static const _modes = {
    ModeClim.cool: 0x2,
    ModeClim.dry: 0x1,
    ModeClim.fan: 0x4,
    ModeClim.auto: 0xA,
  };

  static const _vents = {
    VentClim.auto: 0x1,
    VentClim.low: 0x8,
    VentClim.med: 0x4,
    VentClim.high: 0x2,
  };

  /// Les 8 octets de la trame. Octets 0 à 6 : 0x16, ventilation + mode, quatre zéros,
  /// température en BCD (24 °C = 0x24). Octet 7 : checksum (haut) + drapeaux (bas) :
  /// bit 0 = 1 si le swing est arrêté, bit 3 = touche marche/arrêt.
  static List<int> trame({
    required ModeClim mode,
    required VentClim vent,
    required int temp,
    required bool swing,
    bool touchePower = false,
  }) {
    final bcd = ((temp ~/ 10) << 4) | (temp % 10);
    final b = <int>[0x16, (_vents[vent]! << 4) | _modes[mode]!, 0, 0, 0, 0, bcd];
    final bas = (swing ? 0 : 1) | (touchePower ? 8 : 0);
    var somme = bas;
    for (final x in b) {
      somme += (x & 0xF) + (x >> 4);
    }
    b.add(((somme & 0xF) << 4) | bas);
    return b;
  }

  /// Convertit les octets en durées marque / espace (133 valeurs), octets LSB d'abord.
  static List<int> durees(List<int> octets) {
    final d = <int>[_enteteMarque, _enteteEspace];
    for (final x in octets) {
      for (var k = 0; k < 8; k++) {
        d.add(_marque);
        d.add(((x >> k) & 1) == 1 ? _un : _zero);
      }
    }
    d.add(_marque);
    d.add(_silence);
    d.add(_marqueFin);
    return d;
  }

  /// Le téléphone a-t-il un émetteur infrarouge ?
  static Future<bool> disponible() async {
    try {
      return await _canal.invokeMethod<bool>('disponible') ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Envoie une trame avec l'émetteur du téléphone. Renvoie false si ça n'a pas pu partir.
  static Future<bool> envoyer(List<int> octets) async {
    try {
      return await _canal.invokeMethod<bool>(
              'emettre', {'frequence': frequence, 'motif': durees(octets)}) ??
          false;
    } catch (_) {
      return false;
    }
  }
}
```

### `Micro/app/lib/ecrans/clim.dart`
```dart
// Carte « Air conditioner » (Phase 12) : télécommande de la clim York avec l'émetteur
// infrarouge du téléphone. Aucun lien avec le PC : elle marche même hors connexion.
// Chaque appui envoie la trame complète (mode, ventilation, température, swing).
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../clim_ir.dart';
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
  }

  Future<void> _sauver() async {
    final p = await SharedPreferences.getInstance();
    await p.setInt('clim_mode', _mode.index);
    await p.setInt('clim_vent', _vent.index);
    await p.setInt('clim_temp', _temp);
    await p.setBool('clim_swing', _swing);
  }

  Future<void> _envoyer(List<int> octets, String nom) async {
    HapticFeedback.selectionClick();
    final ok = await ClimIr.envoyer(octets);
    if (!mounted) return;
    setState(() => _info = ok ? 'Sent: $nom' : 'No IR blaster found on this phone.');
  }

  /// Envoie l'état affiché (mode, ventilation, température, swing).
  void _envoyerEtat(String nom) {
    _sauver();
    _envoyer(ClimIr.trame(mode: _mode, vent: _vent, temp: _temp, swing: _swing), nom);
  }

  /// Touche marche/arrêt : l'état affiché avec le drapeau « power ».
  void _power() => _envoyer(
        ClimIr.trame(mode: _mode, vent: _vent, temp: _temp, swing: _swing, touchePower: true),
        'power',
      );

  /// Appui long sur marche/arrêt : l'autre trame « power » vue pendant la collecte
  /// (Cool, Auto, 16 °C). À essayer si l'appui court ne fait rien.
  void _powerAlternatif() => _envoyer(
        ClimIr.trame(
            mode: ModeClim.cool, vent: VentClim.auto, temp: 16, swing: false, touchePower: true),
        'power (alt)',
      );

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

### `Micro/app/test/clim_ir_test.dart`
```dart
// Phase 12 : le générateur Dart doit reproduire exactement les trames capturées sur le Xiaomi.
import 'package:esp_micro/clim_ir.dart';
import 'package:flutter_test/flutter_test.dart';

List<int> _t(ModeClim m, VentClim v, int temp, bool swing, [bool power = false]) =>
    ClimIr.trame(mode: m, vent: v, temp: temp, swing: swing, touchePower: power);

void main() {
  test('trames de réglage capturées', () {
    expect(_t(ModeClim.cool, VentClim.auto, 24, false), [0x16, 0x12, 0, 0, 0, 0, 0x24, 0x11]);
    expect(_t(ModeClim.cool, VentClim.auto, 25, false), [0x16, 0x12, 0, 0, 0, 0, 0x25, 0x21]);
    expect(_t(ModeClim.cool, VentClim.auto, 30, false), [0x16, 0x12, 0, 0, 0, 0, 0x30, 0xE1]);
    expect(_t(ModeClim.cool, VentClim.auto, 16, false), [0x16, 0x12, 0, 0, 0, 0, 0x16, 0x21]);
    expect(_t(ModeClim.cool, VentClim.low, 24, false), [0x16, 0x82, 0, 0, 0, 0, 0x24, 0x81]);
    expect(_t(ModeClim.cool, VentClim.med, 24, false), [0x16, 0x42, 0, 0, 0, 0, 0x24, 0x41]);
    expect(_t(ModeClim.cool, VentClim.high, 24, false), [0x16, 0x22, 0, 0, 0, 0, 0x24, 0x21]);
    expect(_t(ModeClim.dry, VentClim.low, 23, false), [0x16, 0x81, 0, 0, 0, 0, 0x23, 0x61]);
    expect(_t(ModeClim.fan, VentClim.high, 21, false), [0x16, 0x24, 0, 0, 0, 0, 0x21, 0x11]);
    expect(_t(ModeClim.auto, VentClim.auto, 24, false), [0x16, 0x1A, 0, 0, 0, 0, 0x24, 0x91]);
    expect(_t(ModeClim.cool, VentClim.auto, 24, true), [0x16, 0x12, 0, 0, 0, 0, 0x24, 0x00]);
  });

  test('les deux trames power capturées', () {
    expect(_t(ModeClim.cool, VentClim.auto, 24, false, true), [0x16, 0x12, 0, 0, 0, 0, 0x24, 0x99]);
    expect(_t(ModeClim.cool, VentClim.auto, 16, false, true), [0x16, 0x12, 0, 0, 0, 0, 0x16, 0xA9]);
  });

  test('durées : 133 valeurs, en-tête puis marque finale', () {
    final d = ClimIr.durees(_t(ModeClim.cool, VentClim.auto, 24, false));
    expect(d.length, 133);
    expect(d.first, 4500);
    expect(d[1], 2500);
    expect(d.last, 4550);
  });
}
```

## Partie 2 — Fichiers remplacés en entier
Aucun.

## Partie 3 — Modifications « avant → après »

### Modification 1 — `Micro/app/android/app/src/main/kotlin/com/mmdigitek/esp_micro/MainActivity.kt` : Import de l'émetteur IR
Avant :
```kotlin
import android.content.pm.PackageManager
import android.os.Build
```
Après :
```kotlin
import android.content.pm.PackageManager
import android.hardware.ConsumerIrManager
import android.os.Build
```

### Modification 2 — `Micro/app/android/app/src/main/kotlin/com/mmdigitek/esp_micro/MainActivity.kt` : Canal « dadou/ir » (disponible / emettre)
Avant :
```kotlin
        // après une mise à jour de l'app, la vérification reprend toute seule
```
Après :
```kotlin
        // Phase 12 : clim infrarouge. L'émetteur IR du téléphone envoie la trame calculée par
        // Dart (lib/clim_ir.dart) : « disponible » (le téléphone a-t-il un émetteur ?) et « emettre ».
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "dadou/ir")
            .setMethodCallHandler { appel, resultat ->
                val ir = getSystemService(Context.CONSUMER_IR_SERVICE) as? ConsumerIrManager
                when (appel.method) {
                    "disponible" -> resultat.success(ir != null && ir.hasIrEmitter())
                    "emettre" -> {
                        val frequence = appel.argument<Int>("frequence") ?: 38000
                        val motif = appel.argument<List<Int>>("motif")
                        if (ir == null || !ir.hasIrEmitter() || motif == null) {
                            resultat.success(false)
                        } else {
                            ir.transmit(frequence, motif.toIntArray())
                            resultat.success(true)
                        }
                    }
                    else -> resultat.notImplemented()
                }
            }
        // après une mise à jour de l'app, la vérification reprend toute seule
```

### Modification 3 — `Micro/app/android/app/src/main/AndroidManifest.xml` : Permission TRANSMIT_IR
Avant :
```xml
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
```
Après :
```xml
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
    <!-- Phase 12 : émetteur infrarouge du téléphone (permission normale, sans demande à l'écran) -->
    <uses-permission android:name="android.permission.TRANSMIT_IR"/>
    <uses-feature android:name="android.hardware.consumerir" android:required="false"/>
```

### Modification 4 — `Micro/app/lib/ecrans/controles.dart` : Import de la carte clim
Avant :
```dart
import '../theme.dart';
import 'editeur_raccourci.dart';
```
Après :
```dart
import '../theme.dart';
import 'clim.dart';
import 'editeur_raccourci.dart';
```

### Modification 5 — `Micro/app/lib/ecrans/controles.dart` : La carte clim dans l'onglet Controls
Avant :
```dart
        _carteLuminosite(e),
        const SizedBox(height: 14),
        _carteLanceur(e),
```
Après :
```dart
        _carteLuminosite(e),
        const SizedBox(height: 14),
        CarteClim(jeu: e.enJeu),
        const SizedBox(height: 14),
        _carteLanceur(e),
```

## Liste de contrôle (Claude Code)
| Contrôle | Attendu |
|---|---|
| Test à blanc | 5 blocs « avant », 1 occurrence chacun ; 3 fichiers de la Partie 1 absents avant |
| `flutter analyze` (dans `Micro/app`) | No issues found |
| `flutter test` | tous les tests passent, dont `clim_ir_test.dart` (3 tests) |
| `flutter build apk --debug` | SUCCESS |
| Commit | « Phase 12 : clim York depuis le téléphone » + push du dépôt Micro |

## Tests sur le téléphone (Mihaja)
1. Installe l'APK. Onglet **Controls** : la carte « Air conditioner » est en haut. Si elle écrit « This phone has no IR blaster. », dis-le-moi.
2. Place-toi à 2 ou 3 m de la clim, face à elle. Vise avec l'émetteur IR du téléphone (la petite fenêtre sombre sur une tranche du Xiaomi), sans rien devant.
3. Clim éteinte : appui court sur le bouton marche/arrêt. Elle doit bipper et s'allumer. Sinon, appui long (autre trame power).
4. Clim allumée : touche **+** puis **−** (la température doit changer sur la clim), puis Fan Low, Fan High, Dry, Cool, swing.
5. Marche/arrêt : éteins-la avec la touche qui a marché à l'étape 3.
6. Réponds-moi avec une ligne par étape : bip ou pas, allumée, éteinte, température obtenue.

Si la clim ne réagit à rien alors que le Xiaomi la commande avec Mi Remote, dis-le-moi : on ajuste les durées dans `clim_ir.dart`.
