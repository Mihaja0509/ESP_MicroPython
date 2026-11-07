// Phase 15 : carte « Background » : état de chaque réglage et bouton vers l'écran système.
import 'package:esp_micro/ecrans/clim_fond.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

const _canal = MethodChannel('dadou/clim');

Future<List<MethodCall>> _monter(
  WidgetTester tester, {
  required bool autostart,
}) async {
  final appels = <MethodCall>[];
  tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(_canal, (
    call,
  ) async {
    appels.add(call);
    switch (call.method) {
      case 'fond':
        return <String, dynamic>{
          'notifs': true,
          'exact': true,
          'batterie': false,
          'autostart': autostart,
        };
      case 'etat':
        return <String, dynamic>{'service': true, 'journal': ''};
      default:
        return true;
    }
  });
  await tester.pumpWidget(
    const MaterialApp(
      home: Scaffold(body: SingleChildScrollView(child: CarteClimFond())),
    ),
  );
  await tester.pump();
  await tester.pump();
  return appels;
}

void main() {
  testWidgets('un bouton par réglage, le bon écran système est demandé', (
    tester,
  ) async {
    final appels = await _monter(tester, autostart: true);
    expect(find.text('Background service running'), findsOneWidget);
    expect(find.text('Open'), findsNWidgets(4));
    await tester.tap(find.text('Open').at(2));
    await tester.pump();
    final ouvert = appels.lastWhere((a) => a.method == 'ouvrirReglage');
    expect((ouvert.arguments as Map)['quoi'], 'batterie');
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('pas de ligne autostart hors Xiaomi', (tester) async {
    await _monter(tester, autostart: false);
    expect(find.text('Open'), findsNWidgets(3));
    await tester.pumpWidget(const SizedBox());
  });
}
