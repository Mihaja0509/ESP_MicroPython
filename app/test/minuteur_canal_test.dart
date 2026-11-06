// Phase 14-bis : ce que Dart envoie à Android pour le minuteur. Les durées sont en SECONDES de bout
// en bout : 0 h 0 min 10 s = 10, 1 h 2 min 3 s = 3723 (et non 10 minutes).
import 'package:esp_micro/clim_plan.dart';
import 'package:esp_micro/etat.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _canal = MethodChannel('dadou/clim');

Future<List<MethodCall>> _monter(
  WidgetTester tester, {
  int versionNative = 2,
}) async {
  SharedPreferences.setMockInitialValues({});
  final appels = <MethodCall>[];
  tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(_canal, (
    call,
  ) async {
    appels.add(call);
    switch (call.method) {
      case 'version':
        return versionNative;
      case 'etat':
        return <String, dynamic>{'on': false, 'minuteurFin': 0, 'exact': true};
      default:
        return true;
    }
  });
  tester.view.physicalSize = const Size(900, 4000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: SingleChildScrollView(child: CarteClimPlan(etat: EtatPC.vide())),
      ),
    ),
  );
  await tester.pump(const Duration(milliseconds: 200));
  return appels;
}

Future<void> _saisir(WidgetTester tester, String h, String m, String s) async {
  await tester.enterText(find.widgetWithText(TextField, 'Hours'), h);
  await tester.enterText(find.widgetWithText(TextField, 'Minutes'), m);
  await tester.enterText(find.widgetWithText(TextField, 'Seconds'), s);
  await tester.pump();
}

Future<void> _lancer(WidgetTester tester) async {
  await tester.tap(find.textContaining('Run for'));
  await tester.pump(const Duration(milliseconds: 100));
}

MethodCall _minuteur(List<MethodCall> appels) =>
    appels.lastWhere((a) => a.method == 'minuteur');

void main() {
  testWidgets('0 h 0 min 10 s -> 10 secondes (pas 10 minutes)', (tester) async {
    final appels = await _monter(tester);
    await _saisir(tester, '0', '0', '10');
    expect(find.text('Run for 0:00:10'), findsOneWidget);
    await _lancer(tester);
    final a = _minuteur(appels).arguments as Map;
    expect(a['secondes'], 10);
    expect(a['delaiSecondes'], 0);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('1 h 2 min 3 s -> 3723 secondes', (tester) async {
    final appels = await _monter(tester);
    await _saisir(tester, '1', '2', '3');
    expect(find.text('Run for 1:02:03'), findsOneWidget);
    await _lancer(tester);
    expect((_minuteur(appels).arguments as Map)['secondes'], 3723);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('raccourci 15 min -> 900 secondes', (tester) async {
    final appels = await _monter(tester);
    await tester.tap(find.text('15 min'));
    await tester.pump(const Duration(milliseconds: 100));
    await _lancer(tester);
    expect((_minuteur(appels).arguments as Map)['secondes'], 900);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('partie Android trop ancienne : rien n\'est envoyé', (
    tester,
  ) async {
    final appels = await _monter(tester, versionNative: 1);
    await _saisir(tester, '0', '0', '10');
    expect(find.textContaining('outdated'), findsWidgets);
    // le bouton est désactivé : aucun appel « minuteur » ne peut partir
    final bouton = tester.widget<FilledButton>(
      find.ancestor(
        of: find.textContaining('Run for'),
        matching: find.byWidgetPredicate((w) => w is FilledButton),
      ),
    );
    expect(bouton.onPressed, isNull);
    expect(appels.where((a) => a.method == 'minuteur'), isEmpty);
    await tester.pumpWidget(const SizedBox());
  });
}
