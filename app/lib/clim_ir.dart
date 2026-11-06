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
