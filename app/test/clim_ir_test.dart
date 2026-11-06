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
