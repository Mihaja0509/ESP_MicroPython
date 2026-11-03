// Widget de l'écran d'accueil du téléphone (Phase 8) : les 4 premiers favoris.
// Les boutons sont enregistrés dans les préférences de l'app (lues par DadouWidget.kt),
// puis Android est prévenu pour redessiner le widget.
// Phase 9 : carte « Widget » des Réglages (poser le widget depuis l'app, aide Xiaomi).
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'actions.dart';
import 'connexion.dart';
import 'theme.dart';

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

/// Nombre de widgets Dadou posés sur l'écran d'accueil (-1 si inconnu).
Future<int> widgetsPoses() async {
  try {
    return await _canal.invokeMethod<int>('nombre') ?? -1;
  } catch (_) {
    return -1;
  }
}

/// Demande au lanceur d'Android de poser le widget (une fenêtre de confirmation s'ouvre).
Future<bool> epinglerWidget() async {
  try {
    return await _canal.invokeMethod<bool>('epingler') ?? false;
  } catch (_) {
    return false;
  }
}

/// Carte des Réglages : poser le widget, et quoi faire si le téléphone (Xiaomi) refuse.
class CarteWidgetAndroid extends StatefulWidget {
  final Connexion cx;

  const CarteWidgetAndroid({super.key, required this.cx});

  @override
  State<CarteWidgetAndroid> createState() => _CarteWidgetAndroidState();
}

class _CarteWidgetAndroidState extends State<CarteWidgetAndroid> with WidgetsBindingObserver {
  int _poses = -1;
  bool _demande = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _compter();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // au retour sur l'app (après la fenêtre du lanceur) : recompter
    if (state == AppLifecycleState.resumed) _compter();
  }

  Future<void> _compter() async {
    final n = await widgetsPoses();
    if (mounted) setState(() => _poses = n);
  }

  Future<void> _poser() async {
    await majWidget(widget.cx); // le widget aura tout de suite les bons favoris
    final ok = await epinglerWidget();
    if (!mounted) return;
    setState(() => _demande = true);
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(ok
          ? 'Confirme dans la fenêtre du téléphone (« Ajouter »)'
          : "Ce téléphone refuse l'ajout direct : suis l'aide ci-dessous"),
    ));
    Future.delayed(const Duration(seconds: 3), _compter);
  }

  @override
  Widget build(BuildContext context) {
    final favoris = favorisResolus(widget.cx).length;
    final String statut;
    if (_poses > 0) {
      statut = _poses == 1 ? 'Widget posé sur l\'écran d\'accueil' : '$_poses widgets posés';
    } else if (_poses == 0) {
      statut = 'Aucun widget posé pour l\'instant';
    } else {
      statut = '';
    }
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre("Widget de l'écran d'accueil", icone: Icons.widgets_rounded),
          Text(
            favoris == 0
                ? "Ajoute d'abord des favoris (Contrôles, appui long sur un bouton)."
                : 'Il affichera tes ${favoris < boutonsWidget ? favoris : boutonsWidget} premiers favoris.',
            style: const TextStyle(color: Couleurs.doux),
          ),
          if (statut.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(statut, style: TextStyle(color: _poses > 0 ? Couleurs.vert : Couleurs.gris)),
          ],
          const SizedBox(height: 10),
          FilledButton.icon(
            icon: const Icon(Icons.add_to_home_screen_rounded),
            label: const Text("Ajouter le widget à l'écran d'accueil"),
            onPressed: _poser,
          ),
          if (_demande && _poses <= 0) ...[
            const SizedBox(height: 10),
            const Text(
              "Rien ne s'est affiché ? Sur Xiaomi :\n"
              '1. Paramètres → Applications → Gérer les applications → Dadou → '
              'Autres autorisations → « Raccourcis de l\'écran d\'accueil » → Autoriser, '
              'puis appuie de nouveau sur le bouton.\n'
              '2. Ou à la main : appui long sur un espace vide de l\'écran d\'accueil → '
              'Widgets → cherche « Dadou » → fais glisser le widget.',
              style: TextStyle(color: Couleurs.gris, height: 1.45),
            ),
          ],
        ],
      ),
    );
  }
}
