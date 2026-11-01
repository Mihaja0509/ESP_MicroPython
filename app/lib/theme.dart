// Couleurs et éléments visuels, assortis à l'écran de l'ESP32.
import 'package:flutter/material.dart';

class Couleurs {
  static const fondHaut = Color(0xFF140E30);
  static const fondMilieu = Color(0xFF3A1A5E);
  static const fondBas = Color(0xFF7A2A6A);
  static const jeuHaut = Color(0xFF02020A);
  static const jeuMilieu = Color(0xFF140628);
  static const jeuBas = Color(0xFF3C0846);
  static const nuitHaut = Color(0xFF04061A);
  static const nuitBas = Color(0xFF1E1C4E);
  static const carte = Color(0xE6120E28);
  static const carteJeu = Color(0xEB080616);
  static const cyan = Color(0xFF00D2FF);
  static const magenta = Color(0xFFFF28C8);
  static const vert = Color(0xFF6EFFAA);
  static const orange = Color(0xFFFFAA3C);
  static const rouge = Color(0xFFFF4650);
  static const doux = Color(0xFFC8C8EB);
  static const gris = Color(0xFF9696BE);
  static const eteint = Color(0xFF322E54);
}

enum Ambiance { jour, jeu, nuit }

ThemeData creerTheme() {
  final base = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    fontFamily: 'Inter',
    colorScheme: ColorScheme.fromSeed(
      seedColor: Couleurs.cyan,
      brightness: Brightness.dark,
      primary: Couleurs.cyan,
      secondary: Couleurs.magenta,
    ),
    scaffoldBackgroundColor: Colors.transparent,
  );
  return base.copyWith(
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: const Color(0xF0100C24),
      indicatorColor: Couleurs.cyan.withValues(alpha: 0.18),
      labelTextStyle: const WidgetStatePropertyAll(
        TextStyle(fontFamily: 'Inter', fontSize: 12, fontWeight: FontWeight.w600),
      ),
    ),
    sliderTheme: base.sliderTheme.copyWith(
      activeTrackColor: Couleurs.cyan,
      thumbColor: Colors.white,
      inactiveTrackColor: Couleurs.eteint,
    ),
  );
}

/// Fond dégradé qui change doucement selon l'ambiance (jour, jeu, nuit).
class Fond extends StatelessWidget {
  final Ambiance ambiance;
  final Widget child;

  const Fond({super.key, required this.ambiance, required this.child});

  @override
  Widget build(BuildContext context) {
    final couleurs = switch (ambiance) {
      Ambiance.jeu => [Couleurs.jeuHaut, Couleurs.jeuMilieu, Couleurs.jeuBas],
      Ambiance.nuit => [Couleurs.nuitHaut, Couleurs.nuitHaut, Couleurs.nuitBas],
      Ambiance.jour => [Couleurs.fondHaut, Couleurs.fondMilieu, Couleurs.fondBas],
    };
    return AnimatedContainer(
      duration: const Duration(milliseconds: 700),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: couleurs,
          stops: const [0.0, 0.55, 1.0],
        ),
      ),
      child: child,
    );
  }
}

/// Carte « verre », comme celle de l'écran de l'ESP32.
class Carte extends StatelessWidget {
  final Widget child;
  final bool jeu;
  final EdgeInsetsGeometry padding;

  const Carte({
    super.key,
    required this.child,
    this.jeu = false,
    this.padding = const EdgeInsets.all(16),
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 500),
      padding: padding,
      decoration: BoxDecoration(
        color: jeu ? Couleurs.carteJeu : Couleurs.carte,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: jeu ? Couleurs.cyan.withValues(alpha: 0.8) : Colors.white.withValues(alpha: 0.12),
        ),
        boxShadow: jeu
            ? [BoxShadow(color: Couleurs.cyan.withValues(alpha: 0.25), blurRadius: 18)]
            : const [],
      ),
      child: child,
    );
  }
}

class Titre extends StatelessWidget {
  final String texte;
  final IconData? icone;

  const Titre(this.texte, {super.key, this.icone});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          if (icone != null) ...[
            Icon(icone, size: 18, color: Couleurs.cyan),
            const SizedBox(width: 8),
          ],
          Text(
            texte,
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: Colors.white),
          ),
        ],
      ),
    );
  }
}

/// Gros bouton rond avec icône et légende.
class BoutonAction extends StatelessWidget {
  final IconData icone;
  final String texte;
  final Color couleur;
  final VoidCallback onTap;

  const BoutonAction({
    super.key,
    required this.icone,
    required this.texte,
    required this.onTap,
    this.couleur = Couleurs.cyan,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white.withValues(alpha: 0.06),
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 6),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icone, color: couleur, size: 26),
              const SizedBox(height: 6),
              Text(
                texte,
                textAlign: TextAlign.center,
                maxLines: 2,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Couleurs.doux),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
