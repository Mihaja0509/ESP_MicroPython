// Créer / modifier un raccourci (Phase 7) : un nom, une icône et une suite d'étapes
// (touches, texte, Entrée, commande administrateur, app, pause, action Dadou).
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../actions.dart';
import '../connexion.dart';
import '../theme.dart';

class _TypeEtape {
  final String type;
  final String titre;
  final String aide;
  final IconData icone;

  const _TypeEtape(this.type, this.titre, this.aide, this.icone);
}

const List<_TypeEtape> _types = [
  _TypeEtape('touches', 'Touches', 'Un raccourci clavier : ctrl+6, win+x, alt+tab…', Icons.keyboard_rounded),
  _TypeEtape('commande', 'Commande administrateur',
      'PowerShell ou cmd, lancée directement en administrateur (sans Win+X ni fenêtre de confirmation)',
      Icons.terminal_rounded),
  _TypeEtape('texte', 'Écrire un texte', 'Tape le texte dans la fenêtre ouverte', Icons.text_fields_rounded),
  _TypeEtape('entree', 'Appuyer sur Entrée', 'Valide (touche Entrée)', Icons.keyboard_return_rounded),
  _TypeEtape('app', 'Ouvrir une app', 'Une app de l\'onglet Apps', Icons.apps_rounded),
  _TypeEtape('pause', 'Attendre', 'Laisse le temps à une fenêtre de s\'ouvrir', Icons.hourglass_bottom_rounded),
  _TypeEtape('action', 'Action Dadou', 'Volume, lecture, écran noir, verrouillage…', Icons.bolt_rounded),
];

_TypeEtape _infos(String type) => _types.firstWhere((t) => t.type == type, orElse: () => _types.first);

/// Actions proposées pour l'étape « Action Dadou » (ligne envoyée au PC, nom affiché).
const List<(String, String)> _actionsDadou = [
  ('PLAY', 'Lecture / pause'),
  ('NEXT', 'Suivant'),
  ('PREV', 'Précédent'),
  ('VOL+', 'Volume +'),
  ('VOL-', 'Volume −'),
  ('MUTE', 'Muet'),
  ('VOL 30', 'Volume à 30 %'),
  ('ECRAN_OFF', 'Écran noir'),
  ('ECRAN_ON', 'Rallumer l\'écran'),
  ('VERROU', 'Verrouiller'),
  ('KEY win+d', 'Afficher le bureau'),
  ('ECRAN_ESP 0', 'Éteindre l\'écran de l\'ESP32'),
  ('ECRAN_ESP 1', 'Allumer l\'écran de l\'ESP32'),
];

/// Une étape en cours de modification.
class _EtapeEdit {
  String type;
  final TextEditingController champ;
  String shell;
  bool visible;

  _EtapeEdit(this.type, String valeur, {this.shell = 'powershell', this.visible = true})
      : champ = TextEditingController(text: valeur);

  factory _EtapeEdit.depuis(Etape e) => _EtapeEdit(e.type, e.valeur, shell: e.shell, visible: e.visible);

  Etape vers() {
    final v = switch (type) {
      'entree' => '',
      'texte' => champ.text,
      'commande' => champ.text.trimRight(),
      _ => champ.text.trim(),
    };
    return Etape(type, v, shell: shell, visible: visible);
  }
}

class EditeurRaccourci extends StatefulWidget {
  final Connexion cx;
  final Raccourci? existant;

  const EditeurRaccourci({super.key, required this.cx, this.existant});

  @override
  State<EditeurRaccourci> createState() => _EditeurRaccourciState();
}

class _EditeurRaccourciState extends State<EditeurRaccourci> {
  final _nom = TextEditingController();
  String _icone = 'eclair';
  final List<_EtapeEdit> _etapes = [];
  bool _enCours = false;
  String? _erreur;

  Connexion get cx => widget.cx;

  @override
  void initState() {
    super.initState();
    final r = widget.existant;
    if (r != null) {
      _nom.text = r.nom;
      _icone = r.icone;
      _etapes.addAll(r.etapes.map(_EtapeEdit.depuis));
    }
  }

  @override
  void dispose() {
    _nom.dispose();
    for (final e in _etapes) {
      e.champ.dispose();
    }
    super.dispose();
  }

  // ------------------------------------------------------------- modèles
  void _modele(String nom, String icone, List<_EtapeEdit> etapes) {
    setState(() {
      for (final e in _etapes) {
        e.champ.dispose();
      }
      _etapes
        ..clear()
        ..addAll(etapes);
      if (_nom.text.trim().isEmpty) _nom.text = nom;
      _icone = icone;
      _erreur = null;
    });
  }

  Widget _carteModeles() {
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('Pour commencer', icone: Icons.auto_awesome_rounded),
          const Text(
            'Plus besoin de Win+X → Terminal (admin) → taper → Entrée : une étape « Commande '
            'administrateur » fait tout ça d\'un coup, sans fenêtre de confirmation.',
            style: TextStyle(color: Couleurs.doux, fontSize: 13),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              ActionChip(
                avatar: const Icon(Icons.terminal_rounded, size: 18),
                label: const Text('Commande admin'),
                onPressed: () => _modele('Commande admin', 'terminal', [_EtapeEdit('commande', '')]),
              ),
              ActionChip(
                avatar: const Icon(Icons.keyboard_rounded, size: 18),
                label: const Text('Ctrl + 6'),
                onPressed: () => _modele('Ctrl + 6', 'clavier', [_EtapeEdit('touches', 'ctrl+6')]),
              ),
              ActionChip(
                avatar: const Icon(Icons.sports_esports_rounded, size: 18),
                label: const Text('Relancer Steam'),
                onPressed: () => _modele('Relancer Steam', 'jeu', [
                  _EtapeEdit(
                      'commande',
                      'Stop-Process -Name steam -Force -ErrorAction SilentlyContinue\n'
                          'Start-Sleep -Seconds 3\n'
                          "Start-Process 'steam://open/main'",
                      visible: false),
                ]),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ------------------------------------------------------------- étapes
  Future<void> _ajouterEtape() async {
    final type = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: const Color(0xFF1A1438),
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) => SafeArea(
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (final t in _types)
                ListTile(
                  leading: Icon(t.icone, color: Couleurs.cyan),
                  title: Text(t.titre),
                  subtitle: Text(t.aide, maxLines: 3, overflow: TextOverflow.ellipsis),
                  onTap: () => Navigator.pop(context, t.type),
                ),
            ],
          ),
        ),
      ),
    );
    if (type == null || !mounted) return;
    final valeur = switch (type) {
      'pause' => '1000',
      'action' => 'PLAY',
      'app' => cx.apps.isNotEmpty ? cx.apps.first.nom : '',
      _ => '',
    };
    setState(() {
      _etapes.add(_EtapeEdit(type, valeur));
      _erreur = null;
    });
  }

  void _deplacer(int i, int sens) {
    final j = i + sens;
    if (j < 0 || j >= _etapes.length) return;
    setState(() {
      final e = _etapes.removeAt(i);
      _etapes.insert(j, e);
    });
  }

  void _supprimer(int i) {
    setState(() {
      _etapes.removeAt(i).champ.dispose();
    });
  }

  Widget _petitBouton(IconData icone, String aide, VoidCallback? onPressed, {Color? couleur}) {
    return IconButton(
      tooltip: aide,
      visualDensity: VisualDensity.compact,
      constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
      padding: EdgeInsets.zero,
      icon: Icon(icone, size: 20, color: onPressed == null ? Couleurs.eteint : (couleur ?? Couleurs.gris)),
      onPressed: onPressed,
    );
  }

  Widget _carteEtape(int i) {
    final e = _etapes[i];
    final infos = _infos(e.type);
    return Padding(
      key: ObjectKey(e), // chaque étape garde ses champs quand on la déplace
      padding: const EdgeInsets.only(bottom: 10),
      child: Carte(
        padding: const EdgeInsets.fromLTRB(12, 8, 6, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 12,
                  backgroundColor: Couleurs.cyan.withValues(alpha: 0.2),
                  child: Text('${i + 1}',
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Couleurs.cyan)),
                ),
                const SizedBox(width: 8),
                Icon(infos.icone, size: 18, color: Couleurs.doux),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(infos.titre,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                ),
                _petitBouton(Icons.arrow_upward_rounded, 'Monter', i > 0 ? () => _deplacer(i, -1) : null),
                _petitBouton(Icons.arrow_downward_rounded, 'Descendre',
                    i < _etapes.length - 1 ? () => _deplacer(i, 1) : null),
                _petitBouton(Icons.delete_outline_rounded, 'Supprimer', () => _supprimer(i), couleur: Couleurs.rouge),
              ],
            ),
            Padding(
              padding: const EdgeInsets.only(top: 6, right: 6),
              child: _champEtape(e),
            ),
          ],
        ),
      ),
    );
  }

  Widget _champEtape(_EtapeEdit e) {
    switch (e.type) {
      case 'touches':
        return TextField(
          controller: e.champ,
          autocorrect: false,
          enableSuggestions: false,
          decoration: const InputDecoration(
            isDense: true,
            hintText: 'ex. ctrl+6',
            helperText: 'ctrl, shift, alt, win + une lettre, un chiffre, f1…f24, enter, esc, tab, '
                'espace, suppr, haut, bas, gauche, droite…',
            helperMaxLines: 3,
          ),
        );
      case 'texte':
        return TextField(
          controller: e.champ,
          minLines: 1,
          maxLines: 4,
          decoration: const InputDecoration(isDense: true, hintText: 'Texte à écrire'),
        );
      case 'entree':
        return const Text('Appuie sur la touche Entrée.', style: TextStyle(color: Couleurs.gris));
      case 'commande':
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: e.champ,
              autocorrect: false,
              enableSuggestions: false,
              minLines: 2,
              maxLines: 8,
              style: const TextStyle(fontFamily: 'monospace', fontSize: 13),
              decoration: InputDecoration(
                isDense: true,
                hintText: e.shell == 'cmd' ? r'ex. ipconfig /flushdns' : 'ex. Restart-Service Spooler',
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                ChoiceChip(
                  label: const Text('PowerShell'),
                  selected: e.shell == 'powershell',
                  onSelected: (_) => setState(() => e.shell = 'powershell'),
                ),
                ChoiceChip(
                  label: const Text('cmd'),
                  selected: e.shell == 'cmd',
                  onSelected: (_) => setState(() => e.shell = 'cmd'),
                ),
              ],
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              value: e.visible,
              onChanged: (v) => setState(() => e.visible = v),
              title: const Text('Fenêtre visible'),
              subtitle: Text(
                e.visible
                    ? 'La fenêtre reste ouverte pour voir le résultat.'
                    : 'Sans fenêtre : Dadou attend la fin avant l\'étape suivante.',
                style: const TextStyle(fontSize: 12),
              ),
            ),
          ],
        );
      case 'app':
        final noms = cx.apps.map((a) => a.nom).toList();
        if (noms.isEmpty) {
          return TextField(
            controller: e.champ,
            decoration: const InputDecoration(isDense: true, hintText: 'Nom de l\'app (onglet Apps)'),
          );
        }
        if (!noms.contains(e.champ.text) && e.champ.text.isNotEmpty) noms.insert(0, e.champ.text);
        return DropdownButtonFormField<String>(
          isExpanded: true,
          initialValue: e.champ.text.isEmpty ? null : e.champ.text,
          hint: const Text('Choisis une app'),
          items: [
            for (final n in noms)
              DropdownMenuItem(value: n, child: Text(majuscule(n), overflow: TextOverflow.ellipsis)),
          ],
          onChanged: (v) => setState(() => e.champ.text = v ?? ''),
        );
      case 'pause':
        return TextField(
          controller: e.champ,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: const InputDecoration(
            isDense: true,
            suffixText: 'ms',
            helperText: '1000 ms = 1 seconde (30 s au plus)',
          ),
        );
      default: // action
        final lignes = [for (final a in _actionsDadou) a];
        if (e.champ.text.isNotEmpty && !lignes.any((a) => a.$1 == e.champ.text)) {
          lignes.insert(0, (e.champ.text, e.champ.text));
        }
        return DropdownButtonFormField<String>(
          isExpanded: true,
          initialValue: e.champ.text.isEmpty ? null : e.champ.text,
          hint: const Text('Choisis une action'),
          items: [
            for (final a in lignes)
              DropdownMenuItem(value: a.$1, child: Text(a.$2, overflow: TextOverflow.ellipsis)),
          ],
          onChanged: (v) => setState(() => e.champ.text = v ?? ''),
        );
    }
  }

  // ------------------------------------------------------------- enregistrer
  String? _verifier() {
    final nom = _nom.text.trim();
    if (nom.isEmpty) return 'Donne un nom au raccourci.';
    if (nom.length > 30) return 'Nom trop long (30 caractères max).';
    if (nom.contains('"')) return 'Pas de guillemets dans le nom.';
    if (_etapes.isEmpty) return 'Ajoute au moins une étape.';
    for (var i = 0; i < _etapes.length; i++) {
      final e = _etapes[i].vers();
      final vide = e.valeur.trim().isEmpty;
      if (vide && e.type != 'entree') return 'Étape ${i + 1} : à remplir.';
      if (e.type == 'pause' && (int.tryParse(e.valeur) ?? 99999) > 30000) {
        return 'Étape ${i + 1} : 30000 ms au maximum.';
      }
    }
    return null;
  }

  Future<void> _enregistrer() async {
    final erreur = _verifier();
    if (erreur != null) {
      setState(() => _erreur = erreur);
      return;
    }
    setState(() {
      _enCours = true;
      _erreur = null;
    });
    final r = Raccourci(_nom.text.trim(), _icone, _etapes.map((e) => e.vers()).toList());
    final (ok, texte) = await cx.enregistrerRaccourci(r, ancien: widget.existant?.nom ?? '');
    if (!mounted) return;
    if (ok) {
      HapticFeedback.selectionClick();
      Navigator.pop(context);
    } else {
      setState(() {
        _enCours = false;
        _erreur = texte;
      });
    }
  }

  Future<void> _supprimerTout() async {
    final r = widget.existant;
    if (r == null) return;
    final ok = await confirmer(context, 'Supprimer « ${r.nom} » ?', 'Le raccourci disparaîtra du PC.',
        bouton: 'Supprimer', couleur: Couleurs.rouge);
    if (!ok || !mounted) return;
    final (fait, texte) = await cx.retirerRaccourci(r.nom);
    if (!mounted) return;
    if (fait) {
      Navigator.pop(context);
    } else {
      setState(() => _erreur = texte);
    }
  }

  @override
  Widget build(BuildContext context) {
    final nouveau = widget.existant == null;
    return ListenableBuilder(listenable: cx, builder: (context, _) => _page(context, nouveau));
  }

  Widget _page(BuildContext context, bool nouveau) {
    return Fond(
      ambiance: Ambiance.jour,
      child: Scaffold(
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          title: Text(nouveau ? 'Nouveau raccourci' : 'Modifier le raccourci'),
          actions: [
            if (!nouveau)
              IconButton(
                tooltip: 'Supprimer',
                icon: const Icon(Icons.delete_rounded, color: Couleurs.rouge),
                onPressed: _enCours ? null : _supprimerTout,
              ),
          ],
        ),
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
            children: [
              Carte(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    TextField(
                      controller: _nom,
                      maxLength: 30,
                      textCapitalization: TextCapitalization.sentences,
                      decoration: const InputDecoration(labelText: 'Nom', hintText: 'ex. Prépa jeu'),
                    ),
                    const SizedBox(height: 4),
                    const Text('Icône', style: TextStyle(color: Couleurs.gris, fontSize: 12)),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        for (final entree in iconesRaccourcis.entries)
                          ChoiceChip(
                            showCheckmark: false,
                            label: Icon(entree.value,
                                size: 20, color: _icone == entree.key ? Colors.white : Couleurs.gris),
                            selected: _icone == entree.key,
                            onSelected: (_) => setState(() => _icone = entree.key),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              if (nouveau && _etapes.isEmpty) ...[_carteModeles(), const SizedBox(height: 14)],
              const Titre('Étapes (dans l\'ordre)', icone: Icons.format_list_numbered_rounded),
              for (var i = 0; i < _etapes.length; i++) _carteEtape(i),
              OutlinedButton.icon(
                onPressed: _etapes.length >= 20 ? null : _ajouterEtape,
                icon: const Icon(Icons.add_rounded),
                label: const Text('Ajouter une étape'),
              ),
              if (_erreur != null)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Text(_erreur!, style: const TextStyle(color: Couleurs.rouge)),
                ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _enCours || !cx.connecte ? null : _enregistrer,
                icon: _enCours
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.check_rounded),
                label: Text(cx.connecte ? 'Enregistrer sur le PC' : 'PC non connecté'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
