// Dadou — télécommande du PC, app Flutter de l'ESP32 Maison (projet Micro).
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'connexion.dart';
import 'ecrans/accueil.dart';
import 'ecrans/controles.dart';
import 'ecrans/reglages.dart';
import 'ecrans/souris.dart';
import 'theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
  ));
  runApp(const TelecommandeApp());
}

class TelecommandeApp extends StatelessWidget {
  const TelecommandeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Dadou',
      debugShowCheckedModeBanner: false,
      theme: creerTheme(),
      home: const Accueil(),
    );
  }
}

class Accueil extends StatefulWidget {
  const Accueil({super.key});

  @override
  State<Accueil> createState() => _AccueilState();
}

class _AccueilState extends State<Accueil> {
  final Connexion _cx = Connexion();
  int _onglet = 0;
  int _messageVu = 0;

  @override
  void initState() {
    super.initState();
    _cx.charger();
    _cx.addListener(_nouveauMessage);
  }

  void _nouveauMessage() {
    if (_cx.numeroMessage == _messageVu || !mounted) return;
    _messageVu = _cx.numeroMessage;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(
        content: Text(_cx.message),
        duration: const Duration(milliseconds: 1400),
        behavior: SnackBarBehavior.floating,
        backgroundColor: const Color(0xF0201848),
      ));
  }

  @override
  void dispose() {
    _cx.removeListener(_nouveauMessage);
    _cx.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _cx,
      builder: (context, _) {
        final e = _cx.etat;
        final ambiance = !_cx.connecte || e.verrou
            ? Ambiance.nuit
            : e.enJeu
                ? Ambiance.jeu
                : Ambiance.jour;
        final ecrans = [
          EcranAccueil(cx: _cx),
          EcranSouris(cx: _cx),
          EcranControles(cx: _cx),
          EcranReglages(cx: _cx),
        ];
        return Fond(
          ambiance: ambiance,
          child: Scaffold(
            body: SafeArea(child: IndexedStack(index: _onglet, children: ecrans)),
            bottomNavigationBar: NavigationBar(
              selectedIndex: _onglet,
              onDestinationSelected: (i) => setState(() => _onglet = i),
              destinations: const [
                NavigationDestination(icon: Icon(Icons.home_rounded), label: 'Accueil'),
                NavigationDestination(icon: Icon(Icons.mouse_rounded), label: 'Souris'),
                NavigationDestination(icon: Icon(Icons.tune_rounded), label: 'Contrôles'),
                NavigationDestination(icon: Icon(Icons.settings_rounded), label: 'Réglages'),
              ],
            ),
          ),
        );
      },
    );
  }
}
