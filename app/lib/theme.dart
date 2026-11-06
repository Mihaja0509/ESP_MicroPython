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
      // Material transparent : les ListTile / SwitchListTile de la carte peignent leur fond et
      // leurs effets ici, et non sous le fond de la carte (sinon Flutter lève une assertion).
      child: Material(type: MaterialType.transparency, child: child),
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
          Flexible(
            child: Text(
              texte,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: Colors.white),
            ),
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
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 4),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icone, color: couleur, size: 26),
              const SizedBox(height: 6),
              Text(
                texte,
                textAlign: TextAlign.center,
                softWrap: true,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Couleurs.doux),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Grille de boutons dont la hauteur s'adapte au texte (jamais de débordement,
/// même avec une grande taille de police sur le téléphone).
class GrilleBoutons extends StatelessWidget {
  final int colonnes;
  final List<Widget> enfants;
  final double espace;

  const GrilleBoutons({super.key, required this.colonnes, required this.enfants, this.espace = 10});

  @override
  Widget build(BuildContext context) {
    final lignes = <Widget>[];
    for (var i = 0; i < enfants.length; i += colonnes) {
      final cellules = <Widget>[];
      for (var j = 0; j < colonnes; j++) {
        if (j > 0) cellules.add(SizedBox(width: espace));
        final k = i + j;
        cellules.add(Expanded(child: k < enfants.length ? enfants[k] : const SizedBox()));
      }
      if (lignes.isNotEmpty) lignes.add(SizedBox(height: espace));
      lignes.add(IntrinsicHeight(
        child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: cellules),
      ));
    }
    return Column(children: lignes);
  }
}

/// Fenêtre « Es-tu sûr ? ». Renvoie true si l'utilisateur confirme.
Future<bool> confirmer(BuildContext context, String titre, String texte,
    {String bouton = 'Confirm', Color? couleur}) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      backgroundColor: const Color(0xFF1A1438),
      title: Text(titre),
      content: SingleChildScrollView(child: Text(texte)),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
        FilledButton(
          style: couleur == null ? null : FilledButton.styleFrom(backgroundColor: couleur),
          onPressed: () => Navigator.pop(context, true),
          child: Text(bouton),
        ),
      ],
    ),
  );
  return ok == true;
}

/// Tuile carrée d'une grille (app, raccourci, action) : icône + nom sur 2 lignes au plus.
/// Une petite étoile si c'est un favori. Appui long = menu (favori, modifier, supprimer).
class Tuile extends StatelessWidget {
  final IconData icone;
  final String texte;
  final Color couleur;
  final bool favori;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  const Tuile({
    super.key,
    required this.icone,
    required this.texte,
    this.couleur = Couleurs.cyan,
    this.favori = false,
    this.onTap,
    this.onLongPress,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white.withValues(alpha: 0.06),
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        onLongPress: onLongPress,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(6, 12, 6, 10),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              SizedBox(
                width: 34,
                height: 30,
                child: Stack(
                  clipBehavior: Clip.none,
                  alignment: Alignment.center,
                  children: [
                    Icon(icone, color: couleur, size: 26),
                    if (favori)
                      const Positioned(
                        right: -4,
                        top: -4,
                        child: Icon(Icons.star_rounded, size: 14, color: Couleurs.orange),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 6),
              Text(
                texte,
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Couleurs.doux),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Barre d'onglets compacte (le texte se réduit au lieu de déborder).
class Onglets extends StatelessWidget {
  final List<(IconData, String)> onglets;
  final int choisi;
  final ValueChanged<int> onChange;

  const Onglets({super.key, required this.onglets, required this.choisi, required this.onChange});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          for (var i = 0; i < onglets.length; i++)
            Expanded(
              child: Material(
                color: i == choisi ? Couleurs.cyan.withValues(alpha: 0.2) : Colors.transparent,
                borderRadius: BorderRadius.circular(10),
                child: InkWell(
                  borderRadius: BorderRadius.circular(10),
                  onTap: () => onChange(i),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 9, horizontal: 4),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(onglets[i].$1, size: 16, color: i == choisi ? Couleurs.cyan : Couleurs.gris),
                        const SizedBox(width: 5),
                        Flexible(
                          child: Text(
                            onglets[i].$2,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: i == choisi ? Colors.white : Couleurs.gris,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
