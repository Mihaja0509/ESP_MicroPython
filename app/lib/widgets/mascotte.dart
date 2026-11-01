// La mascotte (mêmes dessins que sur l'ESP32) : respire, cligne, sourit après une action,
// met le casque sur les oreilles avec un casque ou en jeu, dort quand le PC est verrouillé.
import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../etat.dart';

class Mascotte extends StatefulWidget {
  final EtatPC etat;
  final DateTime derniereAction;
  final double hauteur;

  const Mascotte({
    super.key,
    required this.etat,
    required this.derniereAction,
    this.hauteur = 170,
  });

  @override
  State<Mascotte> createState() => _MascotteState();
}

class _MascotteState extends State<Mascotte> with SingleTickerProviderStateMixin {
  late final AnimationController _souffle;
  Timer? _clin;
  bool _yeuxFermes = false;
  final _hasard = Random();

  @override
  void initState() {
    super.initState();
    _souffle = AnimationController(vsync: this, duration: const Duration(milliseconds: 2800))
      ..repeat(reverse: true);
    _planifierClin();
  }

  void _planifierClin() {
    _clin = Timer(Duration(milliseconds: 2500 + _hasard.nextInt(3000)), () {
      if (!mounted) return;
      setState(() => _yeuxFermes = true);
      Timer(const Duration(milliseconds: 160), () {
        if (!mounted) return;
        setState(() => _yeuxFermes = false);
        _planifierClin();
      });
    });
  }

  @override
  void dispose() {
    _clin?.cancel();
    _souffle.dispose();
    super.dispose();
  }

  String _image() {
    final e = widget.etat;
    final casque = (e.casque.isNotEmpty || e.enJeu) ? 'oreilles' : 'cou';
    final dort = e.verrou || !e.recu;
    final recent = DateTime.now().difference(widget.derniereAction) < const Duration(milliseconds: 1400);
    final visage = dort
        ? 'cligne'
        : recent
            ? 'content'
            : _yeuxFermes
                ? 'cligne'
                : 'neutre';
    return 'assets/images/perso_${casque}_$visage.png';
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _souffle,
      builder: (context, enfant) {
        final dy = (Curves.easeInOut.transform(_souffle.value) - 0.5) * 6;
        return Transform.translate(offset: Offset(0, dy), child: enfant);
      },
      child: Image.asset(
        _image(),
        height: widget.hauteur,
        gaplessPlayback: true,
        filterQuality: FilterQuality.medium,
      ),
    );
  }
}
