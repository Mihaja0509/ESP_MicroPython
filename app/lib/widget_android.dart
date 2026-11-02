// Widget de l'écran d'accueil du téléphone (Phase 8) : les 4 premiers favoris.
// Les boutons sont enregistrés dans les préférences de l'app (lues par DadouWidget.kt),
// puis Android est prévenu pour redessiner le widget.
import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'actions.dart';
import 'connexion.dart';

const _canal = MethodChannel('dadou/widget');
const int boutonsWidget = 4;

Future<void> majWidget(Connexion cx) async {
  final boutons = [
    for (final a in favorisResolus(cx).take(boutonsWidget)) {'nom': a.nom, 'ligne': a.ligne, 'code': a.code},
  ];
  try {
    final p = await SharedPreferences.getInstance();
    await p.setString('widget_boutons', jsonEncode(boutons));
    await _canal.invokeMethod<bool>('mettreAJour');
  } catch (_) {
    // pas de widget (tests, autre plateforme) : rien à faire
  }
}
