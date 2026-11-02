// Contrôles (Phase 7) : son, luminosité (PC + ESP32), et un lanceur rangé en onglets
// Raccourcis / Apps / PC, avec recherche, pour rester lisible même avec beaucoup d'éléments.
// Appui court = lancer ; appui long = favori, modifier, supprimer.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../actions.dart';
import '../connexion.dart';
import '../etat.dart';
import '../theme.dart';
import 'editeur_raccourci.dart';

class EcranControles extends StatefulWidget {
  final Connexion cx;

  const EcranControles({super.key, required this.cx});

  @override
  State<EcranControles> createState() => _EcranControlesState();
}

class _EcranControlesState extends State<EcranControles> {
  double? _volume; // valeur pendant qu'on fait glisser
  double _luminosite = 70;
  double? _lumEsp;
  int _onglet = 0; // 0 raccourcis, 1 apps, 2 PC
  final _recherche = TextEditingController();

  Connexion get cx => widget.cx;

  @override
  void dispose() {
    _recherche.dispose();
    super.dispose();
  }

  void _envoyer(String ligne) {
    HapticFeedback.selectionClick();
    cx.cmd(ligne);
  }

  int _colonnes(BuildContext context) => MediaQuery.sizeOf(context).width > 560 ? 5 : 3;

  @override
  Widget build(BuildContext context) {
    final e = cx.etat;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      children: [
        _carteSon(e),
        const SizedBox(height: 14),
        _carteLuminosite(e),
        const SizedBox(height: 14),
        _carteLanceur(e),
      ],
    );
  }

  // ------------------------------------------------------------- son
  Widget _carteSon(EtatPC e) {
    final volume = _volume ?? (e.vol >= 0 ? e.vol.toDouble() : 50);
    return Carte(
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
    );
  }

  // ------------------------------------------------------------- luminosité
  Widget _carteLuminosite(EtatPC e) {
    final lumEsp = _lumEsp ?? (e.lumEsp > 0 ? e.lumEsp.toDouble() : 85);
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('Luminosité', icone: Icons.light_mode_rounded),
          _ligneReglage(
            'PC',
            _luminosite,
            0,
            (v) => setState(() => _luminosite = v),
            (v) => _envoyer('LUM ${v.round()}'),
          ),
          _ligneReglage(
            'ESP32',
            lumEsp.clamp(5.0, 100.0).toDouble(),
            5,
            (v) => setState(() => _lumEsp = v),
            (v) {
              _envoyer('LUM_ESP ${v.round()}');
              Future.delayed(const Duration(milliseconds: 1500), () {
                if (mounted) setState(() => _lumEsp = null);
              });
            },
            fin: IconButton(
              tooltip: e.ecranEsp ? 'Éteindre l\'écran de l\'ESP32' : 'Allumer l\'écran de l\'ESP32',
              icon: Icon(e.ecranEsp ? Icons.lightbulb_rounded : Icons.lightbulb_outline_rounded,
                  color: e.ecranEsp ? Couleurs.orange : Couleurs.gris),
              onPressed: () => _envoyer(e.ecranEsp ? 'ECRAN_ESP 0' : 'ECRAN_ESP 1'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _ligneReglage(String nom, double valeur, double min, ValueChanged<double> onChanged,
      ValueChanged<double> onChangeEnd,
      {Widget? fin}) {
    return Row(
      children: [
        SizedBox(
          width: 52,
          child: Text(nom,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w700, color: Couleurs.doux)),
        ),
        Expanded(
          child: Slider(value: valeur, min: min, max: 100, onChanged: onChanged, onChangeEnd: onChangeEnd),
        ),
        SizedBox(
          width: 44,
          child: Text('${valeur.round()} %',
              maxLines: 1,
              overflow: TextOverflow.fade,
              softWrap: false,
              textAlign: TextAlign.right,
              style: const TextStyle(fontSize: 12, color: Couleurs.gris)),
        ),
        ?fin,
      ],
    );
  }

  // ------------------------------------------------------------- lanceur
  Widget _carteLanceur(EtatPC e) {
    final contenu = switch (_onglet) {
      0 => _ongletRaccourcis(),
      1 => _ongletApps(),
      _ => _ongletPc(e),
    };
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Onglets(
            onglets: [
              (Icons.bolt_rounded, 'Raccourcis'),
              (Icons.apps_rounded, 'Apps'),
              (Icons.power_settings_new_rounded, 'PC'),
            ],
            choisi: _onglet,
            onChange: (i) => setState(() {
              _onglet = i;
              _recherche.clear();
            }),
          ),
          const SizedBox(height: 12),
          contenu,
        ],
      ),
    );
  }

  /// Barre « recherche + bouton Ajouter » (la recherche n'apparaît qu'avec beaucoup d'éléments).
  Widget _barre({required int nombre, required String texteAjout, required VoidCallback? ajouter}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Expanded(
            child: nombre > 6
                ? TextField(
                    controller: _recherche,
                    onChanged: (_) => setState(() {}),
                    decoration: InputDecoration(
                      isDense: true,
                      hintText: 'Rechercher',
                      prefixIcon: const Icon(Icons.search_rounded, size: 20),
                      suffixIcon: _recherche.text.isEmpty
                          ? null
                          : IconButton(
                              icon: const Icon(Icons.close_rounded, size: 18),
                              onPressed: () => setState(_recherche.clear),
                            ),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  )
                : Text(
                    'Appui long : favori, modifier, supprimer',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Couleurs.gris, fontSize: 12),
                  ),
          ),
          const SizedBox(width: 8),
          IconButton.filledTonal(
            tooltip: texteAjout,
            icon: const Icon(Icons.add_rounded),
            onPressed: ajouter,
          ),
        ],
      ),
    );
  }

  bool _correspond(String nom) {
    final r = _recherche.text.trim().toLowerCase();
    return r.isEmpty || nom.toLowerCase().contains(r);
  }

  Widget _grille(List<Widget> tuiles) {
    return GrilleBoutons(colonnes: _colonnes(context), espace: 8, enfants: tuiles);
  }

  Widget _vide(String texte) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Text(texte, style: const TextStyle(color: Couleurs.gris)),
      );

  // --- raccourcis
  Widget _ongletRaccourcis() {
    final liste = cx.raccourcis.where((r) => _correspond(r.nom)).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _barre(
          nombre: cx.raccourcis.length,
          texteAjout: 'Nouveau raccourci',
          ajouter: cx.connecte ? () => _editerRaccourci(null) : null,
        ),
        if (cx.raccourcis.isEmpty)
          _vide('Aucun raccourci. Touche + pour en créer un : touches (ex. Ctrl + 6), '
              'commande administrateur, texte, app… en un seul appui.')
        else if (liste.isEmpty)
          _vide('Aucun résultat.')
        else
          _grille([
            for (final r in liste)
              _tuile(actionRaccourci(r),
                  modifier: () => _editerRaccourci(r), supprimer: () => _supprimerRaccourci(r)),
          ]),
      ],
    );
  }

  Future<void> _editerRaccourci(Raccourci? r) async {
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => EditeurRaccourci(cx: cx, existant: r),
    ));
  }

  Future<void> _supprimerRaccourci(Raccourci r) async {
    final ok = await confirmer(context, 'Supprimer « ${r.nom} » ?', 'Le raccourci disparaîtra du PC.',
        bouton: 'Supprimer', couleur: Couleurs.rouge);
    if (ok) await cx.retirerRaccourci(r.nom);
  }

  // --- apps
  Widget _ongletApps() {
    final liste = cx.apps.where((a) => _correspond(a.nom)).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _barre(nombre: cx.apps.length, texteAjout: 'Ajouter une app', ajouter: cx.connecte ? () => _editerApp(null) : null),
        if (cx.apps.isEmpty)
          _vide('Aucune app pour l\'instant. Touche + pour ajouter un lien web ou un programme du PC.')
        else if (liste.isEmpty)
          _vide('Aucun résultat.')
        else
          _grille([
            for (final a in liste)
              _tuile(actionApp(a), modifier: () => _editerApp(a), supprimer: () => _supprimerApp(a)),
          ]),
      ],
    );
  }

  Future<void> _editerApp(AppPc? app) async {
    final resultat = await showDialog<(String, String, String)>(
      context: context,
      builder: (context) => _DialogueApp(existante: app),
    );
    if (resultat == null) return;
    HapticFeedback.selectionClick();
    await cx.ajouterApp(resultat.$1, resultat.$2, resultat.$3, ancien: app?.nom ?? '');
  }

  Future<void> _supprimerApp(AppPc app) async {
    final ok = await confirmer(context, 'Retirer « ${app.nom} » ?',
        app.cible.isEmpty ? 'L\'app disparaîtra de la liste.' : app.cible,
        bouton: 'Retirer', couleur: Couleurs.rouge);
    if (ok) {
      HapticFeedback.selectionClick();
      await cx.retirerApp(app.nom);
    }
  }

  // --- PC
  Widget _ongletPc(EtatPC e) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (e.arretPrevu)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: BandeauArret(secondes: e.arret, onAnnuler: () => _envoyer('ANNULER')),
          ),
        const Padding(
          padding: EdgeInsets.only(bottom: 10),
          child: Text('Appui long : ajouter aux favoris (Accueil et widget).',
              style: TextStyle(color: Couleurs.gris, fontSize: 12)),
        ),
        _grille([
          for (final a in actionsPc)
            if (a.id == 'cmd:ECRAN_BASCULE')
              _tuile(ActionDadou(
                id: a.id,
                nom: e.ecranNoir ? 'Rallumer l\'écran' : 'Écran noir',
                icone: e.ecranNoir ? Icons.desktop_windows_rounded : a.icone,
                ligne: a.ligne,
                code: a.code,
                couleur: e.ecranNoir ? Couleurs.orange : a.couleur,
              ))
            else
              _tuile(a),
        ]),
      ],
    );
  }

  // --- tuile commune + menu de l'appui long
  Widget _tuile(ActionDadou a, {VoidCallback? modifier, VoidCallback? supprimer}) {
    return Tuile(
      icone: a.icone,
      texte: a.nom,
      couleur: a.couleur,
      favori: cx.estFavori(a.id),
      onTap: cx.connecte
          ? () {
              HapticFeedback.selectionClick();
              lancerAction(context, cx, a);
            }
          : null,
      onLongPress: () => _menu(a, modifier: modifier, supprimer: supprimer),
    );
  }

  Future<void> _menu(ActionDadou a, {VoidCallback? modifier, VoidCallback? supprimer}) async {
    HapticFeedback.mediumImpact();
    final favori = cx.estFavori(a.id);
    final choix = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: const Color(0xFF1A1438),
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: Icon(a.icone, color: a.couleur),
              title: Text(a.nom, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w700)),
            ),
            const Divider(height: 1),
            ListTile(
              leading: Icon(favori ? Icons.star_outline_rounded : Icons.star_rounded, color: Couleurs.orange),
              title: Text(favori ? 'Retirer des favoris' : 'Ajouter aux favoris'),
              subtitle: const Text('Accueil et widget du téléphone'),
              onTap: () => Navigator.pop(context, 'favori'),
            ),
            if (modifier != null)
              ListTile(
                leading: const Icon(Icons.edit_rounded, color: Couleurs.cyan),
                title: const Text('Modifier'),
                onTap: () => Navigator.pop(context, 'modifier'),
              ),
            if (supprimer != null)
              ListTile(
                leading: const Icon(Icons.delete_rounded, color: Couleurs.rouge),
                title: const Text('Supprimer'),
                onTap: () => Navigator.pop(context, 'supprimer'),
              ),
          ],
        ),
      ),
    );
    if (!mounted) return;
    switch (choix) {
      case 'favori':
        cx.basculerFavori(a.id);
      case 'modifier':
        modifier?.call();
      case 'supprimer':
        supprimer?.call();
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

/// Bandeau « Arrêt du PC dans 42 s » avec un bouton Annuler (Accueil et Contrôles).
class BandeauArret extends StatelessWidget {
  final int secondes;
  final VoidCallback onAnnuler;

  const BandeauArret({super.key, required this.secondes, required this.onAnnuler});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 10, 10, 10),
      decoration: BoxDecoration(
        color: Couleurs.rouge.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Couleurs.rouge.withValues(alpha: 0.7)),
      ),
      child: Row(
        children: [
          const Icon(Icons.power_settings_new_rounded, color: Couleurs.rouge),
          const SizedBox(width: 10),
          Expanded(
            child: Text('Arrêt du PC dans $secondes s',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w700)),
          ),
          const SizedBox(width: 8),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Couleurs.rouge),
            onPressed: onAnnuler,
            child: const Text('Annuler'),
          ),
        ],
      ),
    );
  }
}

/// Fenêtre « Ajouter / modifier une app » : un nom + un lien web ou un chemin Windows.
class _DialogueApp extends StatefulWidget {
  final AppPc? existante;

  const _DialogueApp({this.existante});

  @override
  State<_DialogueApp> createState() => _DialogueAppState();
}

class _DialogueAppState extends State<_DialogueApp> {
  late final TextEditingController _nom;
  late final TextEditingController _cible;
  late String _sorte;
  String? _erreur;

  @override
  void initState() {
    super.initState();
    final a = widget.existante;
    _nom = TextEditingController(text: a?.nom ?? '');
    _cible = TextEditingController(text: a?.cible ?? '');
    _sorte = a != null && a.type == 'chemin' ? 'chemin' : 'web';
  }

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
    final modification = widget.existante != null;
    return AlertDialog(
      backgroundColor: const Color(0xFF1A1438),
      title: Text(modification ? 'Modifier l\'app' : 'Ajouter une app'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Onglets(
              onglets: const [(Icons.public_rounded, 'Lien web'), (Icons.folder_open_rounded, 'Windows')],
              choisi: web ? 0 : 1,
              onChange: (i) => setState(() {
                _sorte = i == 0 ? 'web' : 'chemin';
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
                    : 'Programme, fichier ou dossier. Astuce : clic droit sur le fichier '
                        '→ « Copier en tant que chemin », puis colle-le ici.',
                helperMaxLines: 4,
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
        FilledButton(onPressed: _valider, child: Text(modification ? 'Enregistrer' : 'Ajouter')),
      ],
    );
  }
}
