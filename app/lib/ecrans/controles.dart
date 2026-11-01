// Volume, musique, luminosité, applications et alimentation du PC.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../connexion.dart';
import '../theme.dart';

class EcranControles extends StatefulWidget {
  final Connexion cx;

  const EcranControles({super.key, required this.cx});

  @override
  State<EcranControles> createState() => _EcranControlesState();
}

class _EcranControlesState extends State<EcranControles> {
  double? _volume; // valeur pendant qu'on fait glisser
  double _luminosite = 70;

  Connexion get cx => widget.cx;

  void _envoyer(String ligne) {
    HapticFeedback.selectionClick();
    cx.cmd(ligne);
  }

  Future<void> _confirmer(String titre, String texte, String commande) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1A1438),
        title: Text(titre),
        content: Text(texte),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Annuler')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Confirmer')),
        ],
      ),
    );
    if (ok == true) _envoyer(commande);
  }

  @override
  Widget build(BuildContext context) {
    final e = cx.etat;
    final volume = _volume ?? (e.vol >= 0 ? e.vol.toDouble() : 50);
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      children: [
        Carte(
          jeu: e.enJeu,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Titre('Son  ${volume.round()} %', icone: Icons.volume_up_rounded),
              Slider(
                value: volume.clamp(0.0, 100.0).toDouble(),
                max: 100,
                onChanged: (v) => setState(() => _volume = v),
                onChangeEnd: (v) {
                  _envoyer('VOL ${v.round()}');
                  Future.delayed(const Duration(milliseconds: 800), () {
                    if (mounted) setState(() => _volume = null);
                  });
                },
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _rond(Icons.volume_off_rounded, () => _envoyer('MUTE')),
                  _rond(Icons.skip_previous_rounded, () => _envoyer('PREV')),
                  _rond(Icons.play_arrow_rounded, () => _envoyer('PLAY'), grand: true),
                  _rond(Icons.skip_next_rounded, () => _envoyer('NEXT')),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Carte(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Titre('Luminosité  ${_luminosite.round()} %', icone: Icons.light_mode_rounded),
              Slider(
                value: _luminosite,
                max: 100,
                divisions: 20,
                onChanged: (v) => setState(() => _luminosite = v),
                onChangeEnd: (v) => _envoyer('LUM ${v.round()}'),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Carte(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Expanded(child: Titre('Applications', icone: Icons.apps_rounded)),
                  IconButton(
                    icon: const Icon(Icons.refresh_rounded, color: Couleurs.gris),
                    onPressed: cx.rafraichirApps,
                  ),
                ],
              ),
              if (cx.apps.isEmpty)
                const Text('Aucune app (ajoute-les dans tools\\agent\\apps.json sur le PC).',
                    style: TextStyle(color: Couleurs.gris))
              else
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    for (final app in cx.apps)
                      ActionChip(
                        avatar: const Icon(Icons.rocket_launch_rounded, size: 18, color: Couleurs.cyan),
                        label: Text(app[0].toUpperCase() + app.substring(1),
                            style: const TextStyle(fontWeight: FontWeight.w600)),
                        backgroundColor: Colors.white.withValues(alpha: 0.07),
                        side: BorderSide(color: Colors.white.withValues(alpha: 0.12)),
                        onPressed: () => _envoyer('APP $app'),
                      ),
                  ],
                ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Carte(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Titre('Alimentation', icone: Icons.power_settings_new_rounded),
              GridView.count(
                crossAxisCount: 3,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 10,
                crossAxisSpacing: 10,
                childAspectRatio: 1.05,
                children: [
                  BoutonAction(icone: Icons.lock_rounded, texte: 'Verrouiller', onTap: () => _envoyer('VERROU')),
                  BoutonAction(
                      icone: Icons.desktop_access_disabled_rounded,
                      texte: 'Éteindre\nl\'écran',
                      onTap: () => _envoyer('ECRAN_OFF')),
                  BoutonAction(
                    icone: Icons.bedtime_rounded,
                    texte: 'Veille',
                    couleur: Couleurs.orange,
                    onTap: () => _confirmer(
                        'Mettre en veille ?', 'Le PC va se mettre en veille tout de suite.', 'VEILLE'),
                  ),
                  BoutonAction(
                    icone: Icons.power_settings_new_rounded,
                    texte: 'Éteindre\nle PC',
                    couleur: Couleurs.rouge,
                    onTap: () => _confirmer('Éteindre le PC ?',
                        'Le PC s\'éteindra dans 60 secondes. Tu pourras encore annuler.', 'ARRET'),
                  ),
                  BoutonAction(
                      icone: Icons.cancel_rounded,
                      texte: 'Annuler\nl\'arrêt',
                      onTap: () => _envoyer('ANNULER')),
                  BoutonAction(
                    icone: e.ecranEsp ? Icons.lightbulb_rounded : Icons.lightbulb_outline_rounded,
                    texte: 'Écran\nESP32',
                    couleur: e.ecranEsp ? Couleurs.orange : Couleurs.gris,
                    onTap: () => _envoyer(e.ecranEsp ? 'ECRAN_ESP 0' : 'ECRAN_ESP 1'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _rond(IconData icone, VoidCallback onTap, {bool grand = false}) {
    final taille = grand ? 64.0 : 50.0;
    return Material(
      color: grand ? Couleurs.cyan : Colors.white.withValues(alpha: 0.08),
      shape: const CircleBorder(),
      child: InkWell(
        customBorder: const CircleBorder(),
        onTap: onTap,
        child: SizedBox(
          width: taille,
          height: taille,
          child: Icon(icone, color: grand ? const Color(0xFF120E28) : Colors.white, size: grand ? 34 : 26),
        ),
      ),
    );
  }
}
