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
  bool _modifier = false; // mode « retirer des apps »

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
        _carteApps(),
        const SizedBox(height: 14),
        Carte(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Titre('Alimentation', icone: Icons.power_settings_new_rounded),
              GrilleBoutons(
                colonnes: 3,
                enfants: [
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

  // ------------------------------------------------------------- applications
  Widget _carteApps() {
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(child: Titre('Applications', icone: Icons.apps_rounded)),
              IconButton(
                tooltip: 'Ajouter',
                icon: const Icon(Icons.add_circle_rounded, color: Couleurs.cyan),
                onPressed: cx.connecte ? _ajouterApp : null,
              ),
              IconButton(
                tooltip: _modifier ? 'Terminé' : 'Retirer des apps',
                icon: Icon(_modifier ? Icons.check_rounded : Icons.edit_rounded,
                    color: _modifier ? Couleurs.vert : Couleurs.gris),
                onPressed: cx.apps.isEmpty && !_modifier ? null : () => setState(() => _modifier = !_modifier),
              ),
            ],
          ),
          if (cx.apps.isEmpty)
            const Text('Aucune app pour l\'instant. Touche + pour ajouter un lien web ou un programme du PC.',
                style: TextStyle(color: Couleurs.gris))
          else
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                for (final app in cx.apps) _puceApp(app),
              ],
            ),
          if (_modifier && cx.apps.isNotEmpty)
            const Padding(
              padding: EdgeInsets.only(top: 10),
              child: Text('Touche la croix d\'une app pour la retirer.',
                  style: TextStyle(color: Couleurs.gris, fontSize: 12)),
            ),
        ],
      ),
    );
  }

  Widget _puceApp(AppPc app) {
    final icone = app.web
        ? Icons.public_rounded
        : app.type == 'chemin'
            ? Icons.folder_open_rounded
            : Icons.rocket_launch_rounded;
    final nom = app.nom.isEmpty ? app.nom : app.nom[0].toUpperCase() + app.nom.substring(1);
    final fond = Colors.white.withValues(alpha: 0.07);
    final bord = BorderSide(color: Colors.white.withValues(alpha: 0.12));
    if (_modifier) {
      return InputChip(
        avatar: Icon(icone, size: 18, color: Couleurs.gris),
        label: Text(nom, style: const TextStyle(fontWeight: FontWeight.w600)),
        backgroundColor: fond,
        side: bord,
        deleteIcon: const Icon(Icons.close_rounded, size: 18, color: Couleurs.rouge),
        onDeleted: () => _retirerApp(app),
      );
    }
    return Tooltip(
      message: app.cible,
      child: ActionChip(
        avatar: Icon(icone, size: 18, color: Couleurs.cyan),
        label: Text(nom, style: const TextStyle(fontWeight: FontWeight.w600)),
        backgroundColor: fond,
        side: bord,
        onPressed: () => _envoyer('APP ${app.nom}'),
      ),
    );
  }

  Future<void> _retirerApp(AppPc app) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1A1438),
        title: Text('Retirer « ${app.nom} » ?'),
        content: Text(app.cible.isEmpty ? 'L\'app disparaîtra de la liste.' : app.cible),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Annuler')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Couleurs.rouge),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Retirer'),
          ),
        ],
      ),
    );
    if (ok == true) {
      HapticFeedback.selectionClick();
      cx.retirerApp(app.nom);
    }
  }

  Future<void> _ajouterApp() async {
    final resultat = await showDialog<(String, String, String)>(
      context: context,
      builder: (context) => const _DialogueApp(),
    );
    if (resultat != null) {
      HapticFeedback.selectionClick();
      cx.ajouterApp(resultat.$1, resultat.$2, resultat.$3);
    }
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

/// Fenêtre « Ajouter une app » : un nom + un lien web ou un chemin Windows.
class _DialogueApp extends StatefulWidget {
  const _DialogueApp();

  @override
  State<_DialogueApp> createState() => _DialogueAppState();
}

class _DialogueAppState extends State<_DialogueApp> {
  final _nom = TextEditingController();
  final _cible = TextEditingController();
  String _sorte = 'web';
  String? _erreur;

  @override
  void dispose() {
    _nom.dispose();
    _cible.dispose();
    super.dispose();
  }

  void _valider() {
    final nom = _nom.text.trim();
    var cible = _cible.text.trim();
    if (cible.length > 1 && cible.startsWith('"') && cible.endsWith('"')) {
      cible = cible.substring(1, cible.length - 1); // « Copier en tant que chemin » ajoute des guillemets
    }
    String? erreur;
    if (nom.isEmpty) {
      erreur = 'Donne un nom à l\'app.';
    } else if (nom.length > 30) {
      erreur = 'Nom trop long (30 caractères max).';
    } else if (cible.isEmpty) {
      erreur = _sorte == 'web' ? 'Colle le lien web.' : 'Colle le chemin du fichier ou du programme.';
    } else if (cible.contains('"')) {
      erreur = 'Pas de guillemets dans le lien ou le chemin.';
    } else if (_sorte == 'chemin' && !RegExp(r'^([A-Za-z]:[\\/]|\\\\|%)').hasMatch(cible)) {
      erreur = 'Un chemin Windows commence par une lettre de disque, ex. C:\\…';
    } else if (_sorte == 'web' && (cible.contains(' ') || !cible.contains('.'))) {
      erreur = 'Lien web invalide, ex. https://www.youtube.com';
    }
    if (erreur != null) {
      setState(() => _erreur = erreur);
      return;
    }
    Navigator.pop(context, (nom, cible, _sorte));
  }

  @override
  Widget build(BuildContext context) {
    final web = _sorte == 'web';
    return AlertDialog(
      backgroundColor: const Color(0xFF1A1438),
      title: const Text('Ajouter une app'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'web', icon: Icon(Icons.public_rounded), label: Text('Lien web')),
                ButtonSegment(value: 'chemin', icon: Icon(Icons.folder_open_rounded), label: Text('Windows')),
              ],
              selected: {_sorte},
              onSelectionChanged: (s) => setState(() {
                _sorte = s.first;
                _erreur = null;
              }),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _nom,
              textCapitalization: TextCapitalization.sentences,
              maxLength: 30,
              decoration: const InputDecoration(labelText: 'Nom', hintText: 'ex. Netflix'),
            ),
            const SizedBox(height: 6),
            TextField(
              controller: _cible,
              autocorrect: false,
              keyboardType: web ? TextInputType.url : TextInputType.text,
              decoration: InputDecoration(
                labelText: web ? 'Lien web' : 'Chemin Windows',
                hintText: web ? 'https://www.netflix.com' : r'C:\Program Files\…\jeu.exe',
                helperText: web
                    ? 'S\'ouvre dans le navigateur du PC.'
                    : 'Programme, fichier ou dossier. Astuce : clic droit sur le fichier\n'
                        '→ « Copier en tant que chemin », puis colle-le ici.',
                helperMaxLines: 3,
              ),
              onSubmitted: (_) => _valider(),
            ),
            if (_erreur != null)
              Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Text(_erreur!, style: const TextStyle(color: Couleurs.rouge)),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Annuler')),
        FilledButton(onPressed: _valider, child: const Text('Ajouter')),
      ],
    );
  }
}
