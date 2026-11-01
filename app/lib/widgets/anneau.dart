// Anneau de progression animé (CPU, RAM, GPU…), comme sur l'écran de l'ESP32.
import 'dart:math';

import 'package:flutter/material.dart';

import '../theme.dart';

class Anneau extends StatelessWidget {
  final int valeur; // -1 = inconnu
  final String nom;
  final Color couleur;
  final double taille;
  final String unite;

  const Anneau({
    super.key,
    required this.valeur,
    required this.nom,
    required this.couleur,
    this.taille = 78,
    this.unite = '%',
  });

  @override
  Widget build(BuildContext context) {
    final connu = valeur >= 0;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        TweenAnimationBuilder<double>(
          tween: Tween<double>(end: connu ? valeur.toDouble() : 0.0),
          duration: const Duration(milliseconds: 450),
          curve: Curves.easeOutCubic,
          builder: (context, v, _) => SizedBox(
            width: taille,
            height: taille,
            child: CustomPaint(
              painter: _Peintre(v / 100, couleur),
              child: Center(
                child: Text(
                  connu ? '${v.round()}$unite' : '',
                  style: TextStyle(
                    fontSize: taille * 0.22,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                  ),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 6),
        Text(nom, style: const TextStyle(fontSize: 12, color: Couleurs.gris, fontWeight: FontWeight.w600)),
      ],
    );
  }
}

class _Peintre extends CustomPainter {
  final double part;
  final Color couleur;

  _Peintre(this.part, this.couleur);

  @override
  void paint(Canvas canvas, Size size) {
    final centre = size.center(Offset.zero);
    final rayon = size.width / 2 - 6;
    final fond = Paint()
      ..color = Couleurs.eteint
      ..style = PaintingStyle.stroke
      ..strokeWidth = 7;
    canvas.drawCircle(centre, rayon, fond);
    final arc = Paint()
      ..color = couleur
      ..style = PaintingStyle.stroke
      ..strokeWidth = 7
      ..strokeCap = StrokeCap.round;
    final p = part.clamp(0.0, 1.0).toDouble();
    if (p > 0) {
      canvas.drawArc(Rect.fromCircle(center: centre, radius: rayon), -pi / 2, 2 * pi * p, false, arc);
    }
  }

  @override
  bool shouldRepaint(_Peintre ancien) => ancien.part != part || ancien.couleur != couleur;
}

/// Barre horizontale de température (vert, orange, rouge).
class BarreTemperature extends StatelessWidget {
  final String nom;
  final int valeur;

  const BarreTemperature({super.key, required this.nom, required this.valeur});

  @override
  Widget build(BuildContext context) {
    final connu = valeur >= 0;
    final couleur = !connu
        ? Couleurs.gris
        : valeur < 65
            ? Couleurs.vert
            : valeur < 82
                ? Couleurs.orange
                : Couleurs.rouge;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          SizedBox(
            width: 44,
            child: Text(nom, style: const TextStyle(color: Couleurs.gris, fontWeight: FontWeight.w600)),
          ),
          Expanded(
            child: TweenAnimationBuilder<double>(
              tween: Tween<double>(end: connu ? (valeur / 100).clamp(0.0, 1.0).toDouble() : 0.0),
              duration: const Duration(milliseconds: 450),
              builder: (context, v, _) => ClipRRect(
                borderRadius: BorderRadius.circular(6),
                child: LinearProgressIndicator(
                  value: v,
                  minHeight: 10,
                  backgroundColor: Couleurs.eteint,
                  color: couleur,
                ),
              ),
            ),
          ),
          SizedBox(
            width: 56,
            child: Text(
              connu ? '$valeur°' : '',
              textAlign: TextAlign.right,
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: couleur),
            ),
          ),
        ],
      ),
    );
  }
}
