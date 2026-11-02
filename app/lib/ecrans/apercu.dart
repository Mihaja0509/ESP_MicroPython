// Aperçu de l'écran du PC (Phase 8) : une image demandée dès que la précédente est arrivée
// (le rythme s'adapte tout seul au réseau). Toucher l'image = cliquer à cet endroit du PC.
// Pincer pour zoomer. Plusieurs écrans : bouton pour passer de l'un à l'autre.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../connexion.dart';
import '../theme.dart';

class EcranApercu extends StatefulWidget {
  final Connexion cx;
  final bool actif; // l'onglet est affiché

  const EcranApercu({super.key, required this.cx, required this.actif});

  @override
  State<EcranApercu> createState() => _EcranApercuState();
}

class _EcranApercuState extends State<EcranApercu> {
  // (largeur de l'image, qualité JPEG, pause minimale entre deux images en ms, nom)
  static const _reglages = [(640, 45, 250, 'Éco'), (960, 60, 150, 'Normal'), (1440, 72, 150, 'HD')];

  int _ecran = 0;
  int _qualite = 1;
  int _mode = 1; // 0 regarder, 1 clic, 2 double clic, 3 clic droit
  bool _enPause = false;
  bool _premierPlan = true;
  DateTime _derniereDemande = DateTime.fromMillisecondsSinceEpoch(0);
  Timer? _surveillance;
  Timer? _prochaine;
  AppLifecycleListener? _cycle;
  int _images = 0;
  double _ips = 0;
  DateTime _debutComptage = DateTime.now();
  final _vue = TransformationController();

  Connexion get cx => widget.cx;

  bool get _doitTourner => widget.actif && _premierPlan && !_enPause && cx.connecte;

  @override
  void initState() {
    super.initState();
    cx.apercuImage.addListener(_nouvelleImage);
    _cycle = AppLifecycleListener(
      onResume: () => _premierPlan = true,
      onPause: () => _premierPlan = false,
      onHide: () => _premierPlan = false,
      onShow: () => _premierPlan = true,
    );
    // relance si une image s'est perdue (ou au retour sur l'onglet)
    _surveillance = Timer.periodic(const Duration(milliseconds: 500), (_) {
      if (_doitTourner && DateTime.now().difference(_derniereDemande) > const Duration(seconds: 3)) {
        _demander();
      }
    });
  }

  @override
  void didUpdateWidget(EcranApercu ancien) {
    super.didUpdateWidget(ancien);
    if (widget.actif && !ancien.actif) _demander();
  }

  @override
  void dispose() {
    cx.apercuImage.removeListener(_nouvelleImage);
    _surveillance?.cancel();
    _prochaine?.cancel();
    _cycle?.dispose();
    _vue.dispose();
    super.dispose();
  }

  void _demander() {
    if (!_doitTourner) return;
    _derniereDemande = DateTime.now();
    final r = _reglages[_qualite];
    cx.demanderApercu(ecran: _ecran, largeur: r.$1, qualite: r.$2);
  }

  void _nouvelleImage() {
    _images++;
    final duree = DateTime.now().difference(_debutComptage);
    if (duree > const Duration(seconds: 2) && mounted) {
      setState(() {
        _ips = _images * 1000 / duree.inMilliseconds;
        _images = 0;
        _debutComptage = DateTime.now();
      });
    }
    final ecoule = DateTime.now().difference(_derniereDemande).inMilliseconds;
    final attente = _reglages[_qualite].$3 - ecoule;
    _prochaine?.cancel();
    _prochaine = Timer(Duration(milliseconds: attente > 0 ? attente : 0), _demander);
  }

  void _toucher(Offset position, Size taille, String clic) {
    if (taille.width <= 0 || taille.height <= 0) return;
    final x = (position.dx / taille.width).clamp(0.0, 1.0).toDouble();
    final y = (position.dy / taille.height).clamp(0.0, 1.0).toDouble();
    HapticFeedback.selectionClick();
    cx.pointeur(_ecran, x, y, clic);
    _prochaine?.cancel();
    _prochaine = Timer(const Duration(milliseconds: 120), _demander); // voir le résultat vite
  }

  String get _clicDuMode => switch (_mode) { 1 => 'gauche', 2 => 'double', 3 => 'droit', _ => '' };

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<Map<String, dynamic>>(
      valueListenable: cx.apercuInfos,
      builder: (context, infos, _) {
        final ecrans = infos['ecrans'] is num ? (infos['ecrans'] as num).toInt() : cx.etat.ecrans;
        final largeur = infos['largeur'] is num ? (infos['largeur'] as num).toDouble() : 16.0;
        final hauteur = infos['hauteur'] is num ? (infos['hauteur'] as num).toDouble() : 10.0;
        final erreur = infos['erreur'] as String?;
        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _entete(ecrans),
              const SizedBox(height: 10),
              Expanded(child: _zoneImage(largeur / hauteur, erreur, infos['verrou'] == true)),
              const SizedBox(height: 10),
              Onglets(
                onglets: const [
                  (Icons.visibility_rounded, 'Voir'),
                  (Icons.touch_app_rounded, 'Clic'),
                  (Icons.ads_click_rounded, 'Double'),
                  (Icons.mouse_rounded, 'Droit'),
                ],
                choisi: _mode,
                onChange: (i) => setState(() => _mode = i),
              ),
              const SizedBox(height: 6),
              Text(
                _mode == 0
                    ? 'Toucher l\'image ne clique pas. Pince pour zoomer.'
                    : 'Touche l\'image pour cliquer à cet endroit. Appui long = clic droit. Pince pour zoomer.',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Couleurs.gris, fontSize: 12),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _entete(int ecrans) {
    return Row(
      children: [
        const Icon(Icons.monitor_rounded, color: Couleurs.cyan, size: 20),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            _enPause
                ? 'Écran du PC (en pause)'
                : 'Écran du PC  ${_ips > 0 ? '${_ips.toStringAsFixed(1)} img/s' : ''}',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
        ),
        if (ecrans > 1)
          TextButton.icon(
            onPressed: () => setState(() {
              _ecran = (_ecran + 1) % ecrans;
              _vue.value = Matrix4.identity();
              _demander();
            }),
            icon: const Icon(Icons.swap_horiz_rounded, size: 18),
            label: Text('${_ecran + 1}/$ecrans'),
          ),
        PopupMenuButton<int>(
          tooltip: 'Qualité',
          initialValue: _qualite,
          icon: const Icon(Icons.high_quality_rounded, color: Couleurs.gris),
          onSelected: (i) => setState(() => _qualite = i),
          itemBuilder: (context) => [
            for (var i = 0; i < _reglages.length; i++)
              PopupMenuItem(value: i, child: Text(_reglages[i].$4)),
          ],
        ),
        IconButton(
          tooltip: _enPause ? 'Reprendre' : 'Pause',
          icon: Icon(_enPause ? Icons.play_arrow_rounded : Icons.pause_rounded, color: Couleurs.gris),
          onPressed: () => setState(() {
            _enPause = !_enPause;
            if (!_enPause) _demander();
          }),
        ),
      ],
    );
  }

  Widget _message(IconData icone, String texte) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icone, color: Couleurs.gris, size: 40),
              const SizedBox(height: 10),
              Text(texte, textAlign: TextAlign.center, style: const TextStyle(color: Couleurs.doux)),
            ],
          ),
        ),
      );

  Widget _zoneImage(double ratio, String? erreur, bool verrou) {
    return Carte(
      padding: const EdgeInsets.all(6),
      child: !cx.connecte
          ? _message(Icons.wifi_off_rounded, 'PC non connecté.')
          : erreur != null
              ? _message(Icons.error_outline_rounded, erreur)
              : ValueListenableBuilder<Uint8List?>(
                  valueListenable: cx.apercuImage,
                  builder: (context, octets, _) {
                    if (octets == null) {
                      return const Center(child: CircularProgressIndicator());
                    }
                    return Stack(
                      children: [
                        Positioned.fill(
                          child: InteractiveViewer(
                            transformationController: _vue,
                            minScale: 1,
                            maxScale: 6,
                            child: Center(
                              child: AspectRatio(
                                aspectRatio: ratio > 0 ? ratio : 1.6,
                                child: LayoutBuilder(
                                  builder: (context, contraintes) => GestureDetector(
                                    onTapUp: _mode == 0
                                        ? null
                                        : (d) => _toucher(d.localPosition, contraintes.biggest, _clicDuMode),
                                    onLongPressStart: (d) =>
                                        _toucher(d.localPosition, contraintes.biggest, 'droit'),
                                    child: ClipRRect(
                                      borderRadius: BorderRadius.circular(8),
                                      child: Image.memory(
                                        octets,
                                        gaplessPlayback: true,
                                        fit: BoxFit.fill,
                                        filterQuality: FilterQuality.medium,
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                        if (verrou || cx.etat.ecranNoir)
                          Positioned(
                            left: 8,
                            right: 8,
                            top: 8,
                            child: Align(
                              alignment: Alignment.topLeft,
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                                decoration: BoxDecoration(
                                  color: const Color(0xCC120E28),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Text(
                                  verrou
                                      ? 'PC verrouillé : l\'image peut rester noire'
                                      : 'Écran noir actif : tu vois quand même le PC ici',
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(fontSize: 12, color: Couleurs.orange),
                                ),
                              ),
                            ),
                          ),
                      ],
                    );
                  },
                ),
    );
  }
}
