// Onglet « Master » (Phase 11) : ce qui s'affiche sur la scène master de l'ESP32.
// Échéances, objectif du jour, réunion avec le superviseur, phase, objectifs chiffrés,
// avancement calculé par le PC (lecture, rédaction, mesures, temps) et fichiers à suivre.
import 'package:flutter/material.dart';

import '../connexion.dart';
import '../theme.dart';

const _jours = ['lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.'];
const _mois = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];
const violet = Color(0xFF9670FF);

/// « lun. 10 nov. »
String dateCourte(DateTime d) => '${_jours[d.weekday - 1]} ${d.day} ${_mois[d.month - 1]}';

String _deux(int n) => n.toString().padLeft(2, '0');

String dateIso(DateTime d) => '${d.year}-${_deux(d.month)}-${_deux(d.day)}';

/// 95 -> « 1 h 35 » ; 40 -> « 40 min »
String duree(int minutes) => minutes < 60 ? '$minutes min' : '${minutes ~/ 60} h ${_deux(minutes % 60)}';

int _n(dynamic v, [int defaut = -1]) => v is num ? v.toInt() : defaut;

Map<String, dynamic> _carte(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};

/// Échéances proposées (devoirs du cours de méthodologie, matériel attendu).
const suggestionsEcheances = [
  'Assignment 2 : Reference Management',
  'Assignment 3 : Paper Critique',
  'Assignment 4 : Research Proposal',
  'Arrivée de la Odin 3',
  'Rapport au superviseur',
];

class Echeance {
  final String titre;
  final DateTime date;

  const Echeance(this.titre, this.date);

  int get joursRestants {
    final aujourdhui = DateTime.now();
    return DateTime(date.year, date.month, date.day)
        .difference(DateTime(aujourdhui.year, aujourdhui.month, aujourdhui.day))
        .inDays;
  }

  Map<String, dynamic> versJson() => {'titre': titre, 'date': dateIso(date)};
}

/// Données envoyées par le PC (message « master »).
class DonneesMaster {
  final Map<String, dynamic> config;
  final Map<String, dynamic> auto;
  final int tempsJour;
  final Map<String, dynamic> cheminsOk;
  final List<String> phases;

  DonneesMaster(Map<String, dynamic> m)
      : config = _carte(m['config']),
        auto = _carte(m['auto']),
        tempsJour = _n(m['temps_jour'], 0),
        cheminsOk = _carte(m['chemins_ok']),
        phases = (m['phases'] is List ? (m['phases'] as List) : const [])
            .map((e) => e.toString())
            .toList();

  List<Echeance> get echeances {
    final res = <Echeance>[];
    final brut = config['echeances'];
    if (brut is List) {
      for (final e in brut) {
        final d = DateTime.tryParse((e is Map ? e['date'] : '').toString());
        if (d != null) res.add(Echeance((e as Map)['titre'].toString(), d));
      }
    }
    res.sort((a, b) => a.date.compareTo(b.date));
    return res;
  }

  Echeance? get prochaine {
    for (final e in echeances) {
      if (e.joursRestants >= 0) return e;
    }
    return null;
  }

  Map<String, dynamic> get objectif => _carte(config['objectif']);

  /// L'objectif n'est valable que le jour où il a été fixé.
  bool get objectifDuJour =>
      (objectif['texte'] ?? '').toString().isNotEmpty && objectif['date'] == dateIso(DateTime.now());

  List<String> get objectifsPasses {
    final brut = config['objectifs_passes'];
    final res = <String>[];
    if (brut is List) {
      for (final o in brut) {
        final t = (o is Map ? o['texte'] : '').toString();
        if (t.isNotEmpty && !res.contains(t)) res.add(t);
      }
    }
    return res;
  }

  Map<String, dynamic> get reunion => _carte(config['reunion']);

  DateTime? get dateReunion => DateTime.tryParse((reunion['date'] ?? '').toString());

  String get phase => (config['phase'] ?? '').toString();

  int get objectifArticles => _n(config['objectif_articles'], 0);

  int get objectifMots => _n(config['objectif_mots_jour'], 0);

  Map<String, dynamic> get chemins => _carte(config['chemins']);

  List<String> get aLireNoms =>
      (auto['a_lire_noms'] is List ? (auto['a_lire_noms'] as List) : const []).map((e) => e.toString()).toList();

  Map<String, dynamic>? get resultat => auto['resultat'] is Map ? _carte(auto['resultat']) : null;

  List<int> get courbe =>
      (auto['courbe'] is List ? (auto['courbe'] as List) : const []).map((e) => _n(e, 0)).toList();

  bool cheminOk(String cle) => _carte(cheminsOk[cle])['ok'] == true;
}

class EcranMaster extends StatefulWidget {
  final Connexion cx;
  final bool actif;

  const EcranMaster({super.key, required this.cx, required this.actif});

  @override
  State<EcranMaster> createState() => _EcranMasterState();
}

class _EcranMasterState extends State<EcranMaster> {
  final _objectif = TextEditingController();
  final _question = TextEditingController();
  final _fObjectif = FocusNode();
  final _fQuestion = FocusNode();
  final _articles = TextEditingController();
  final _mots = TextEditingController();
  final Map<String, TextEditingController> _chemins = {
    for (final c in ['memoire', 'a_lire', 'lus', 'resultats']) c: TextEditingController(),
  };
  final _motsWord = TextEditingController();
  final _motsCode = TextEditingController();
  int _versionRemplie = -1;
  bool _fichiersOuverts = false;

  Connexion get cx => widget.cx;

  @override
  void initState() {
    super.initState();
    cx.demanderMaster();
  }

  @override
  void didUpdateWidget(EcranMaster ancien) {
    super.didUpdateWidget(ancien);
    if (widget.actif && !ancien.actif) cx.demanderMaster();
  }

  @override
  void dispose() {
    for (final c in [_objectif, _question, _articles, _mots, _motsWord, _motsCode, ..._chemins.values]) {
      c.dispose();
    }
    _fObjectif.dispose();
    _fQuestion.dispose();
    super.dispose();
  }

  /// Remplit les champs avec les valeurs du PC (une fois par nouvelle version, sans écraser la saisie).
  void _remplir(DonneesMaster d, int version) {
    if (version == _versionRemplie) return;
    _versionRemplie = version;
    // un champ en cours de saisie n'est jamais écrasé
    if (!_fObjectif.hasFocus) {
      _objectif.text = d.objectifDuJour ? (d.objectif['texte'] ?? '').toString() : '';
    }
    if (!_fQuestion.hasFocus) _question.text = (d.reunion['question'] ?? '').toString();
    _articles.text = d.objectifArticles.toString();
    _mots.text = d.objectifMots.toString();
    for (final e in _chemins.entries) {
      e.value.text = (d.chemins[e.key] ?? '').toString();
    }
    _motsWord.text = _liste(d.config['mots_word']).join(', ');
    _motsCode.text = _liste(d.config['mots_code']).join(', ');
  }

  List<String> _liste(dynamic v) => v is List ? v.map((e) => e.toString()).toList() : <String>[];

  List<String> _decouper(String texte) =>
      texte.split(',').map((m) => m.trim()).where((m) => m.isNotEmpty).toList();

  Future<void> _maj(Map<String, dynamic> changements) async {
    FocusScope.of(context).unfocus();
    await cx.majMaster(changements);
  }

  @override
  Widget build(BuildContext context) {
    if (!cx.connecte) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text('Connecte-toi au PC pour suivre ton master.',
              textAlign: TextAlign.center, style: TextStyle(color: Couleurs.gris)),
        ),
      );
    }
    final brut = cx.master;
    if (brut == null) {
      return const Center(child: CircularProgressIndicator());
    }
    final d = DonneesMaster(brut);
    _remplir(d, _n(brut['version'], 0));
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      children: [
        _carteEcheances(d),
        const SizedBox(height: 14),
        _carteObjectif(d),
        const SizedBox(height: 14),
        _carteAvancement(d),
        const SizedBox(height: 14),
        _carteReunion(d),
        const SizedBox(height: 14),
        _cartePhase(d),
        const SizedBox(height: 14),
        _carteFichiers(d),
        const SizedBox(height: 14),
        OutlinedButton.icon(
          icon: const Icon(Icons.view_in_ar_rounded),
          label: const Text("Afficher la scène master sur l'ESP32"),
          onPressed: cx.afficherMaster,
        ),
      ],
    );
  }

  // ------------------------------------------------------------------ échéances
  Widget _carteEcheances(DonneesMaster d) {
    final p = d.prochaine;
    final j = p?.joursRestants ?? 0;
    final couleur = j <= 3 ? Couleurs.rouge : (j <= 7 ? Couleurs.orange : Couleurs.cyan);
    final avenir = d.echeances.where((e) => e.joursRestants >= 0).toList();
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('Échéances', icone: Icons.flag_rounded),
          if (p == null)
            const Text('Aucune échéance à venir.', style: TextStyle(color: Couleurs.gris))
          else
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Text(j == 0 ? "Aujourd'hui" : 'J-$j',
                    style: TextStyle(fontSize: j == 0 ? 26 : 40, fontWeight: FontWeight.w900, color: couleur)),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(p.titre,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                      Text(dateCourte(p.date), style: const TextStyle(color: Couleurs.gris)),
                    ],
                  ),
                ),
              ],
            ),
          if (avenir.length > 1 || (avenir.length == 1 && p == null)) const SizedBox(height: 8),
          for (final e in avenir.skip(p == null ? 0 : 1))
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: Text('J-${e.joursRestants}',
                  style: const TextStyle(fontWeight: FontWeight.w800, color: Couleurs.doux)),
              title: Text(e.titre, maxLines: 1, overflow: TextOverflow.ellipsis),
              subtitle: Text(dateCourte(e.date)),
              trailing: IconButton(
                icon: const Icon(Icons.close_rounded, size: 18),
                onPressed: () => _retirerEcheance(d, e),
              ),
            ),
          const SizedBox(height: 6),
          Row(
            children: [
              FilledButton.icon(
                icon: const Icon(Icons.add_rounded),
                label: const Text('Ajouter'),
                onPressed: () => _ajouterEcheance(d),
              ),
              const SizedBox(width: 8),
              if (p != null)
                TextButton(
                  onPressed: () => _retirerEcheance(d, p),
                  child: const Text('Retirer la prochaine'),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _ajouterEcheance(DonneesMaster d) async {
    final titre = TextEditingController();
    DateTime? choisie;
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialog) => AlertDialog(
          backgroundColor: const Color(0xFF1A1438),
          title: const Text('Nouvelle échéance'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: titre,
                  maxLength: 60,
                  decoration: const InputDecoration(hintText: 'ex. Rapport superviseur', counterText: ''),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    for (final s in suggestionsEcheances)
                      ActionChip(label: Text(s, style: const TextStyle(fontSize: 12)), onPressed: () {
                        titre.text = s;
                        setDialog(() {});
                      }),
                  ],
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  icon: const Icon(Icons.event_rounded),
                  label: Text(choisie == null ? 'Choisir la date' : dateCourte(choisie!)),
                  onPressed: () async {
                    final maintenant = DateTime.now();
                    final r = await showDatePicker(
                      context: context,
                      initialDate: maintenant.add(const Duration(days: 7)),
                      firstDate: DateTime(maintenant.year, maintenant.month, maintenant.day),
                      lastDate: maintenant.add(const Duration(days: 1000)),
                    );
                    if (r != null) setDialog(() => choisie = r);
                  },
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Annuler')),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Ajouter')),
          ],
        ),
      ),
    );
    final texte = titre.text.trim();
    titre.dispose();
    if (ok != true || texte.isEmpty || choisie == null) return;
    final liste = [...d.echeances.map((e) => e.versJson()), Echeance(texte, choisie!).versJson()];
    await _maj({'echeances': liste});
  }

  Future<void> _retirerEcheance(DonneesMaster d, Echeance e) async {
    final liste = d.echeances
        .where((x) => !(x.titre == e.titre && dateIso(x.date) == dateIso(e.date)))
        .map((x) => x.versJson())
        .toList();
    await _maj({'echeances': liste});
  }

  // ------------------------------------------------------------------ objectif du jour
  Widget _carteObjectif(DonneesMaster d) {
    final fait = d.objectifDuJour && d.objectif['fait'] == true;
    final suggestions = [
      for (final n in d.aLireNoms.take(5)) 'Lire $n',
      for (final o in d.objectifsPasses.take(4)) o,
    ];
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('Objectif du jour', icone: Icons.my_location_rounded),
          TextField(
            controller: _objectif,
            focusNode: _fObjectif,
            maxLength: 120,
            textInputAction: TextInputAction.done,
            onSubmitted: (t) => _maj({
              'objectif': {'texte': t.trim(), 'fait': false}
            }),
            decoration: const InputDecoration(
              hintText: 'ex. Lire Sonkoly 2024',
              border: OutlineInputBorder(),
              isDense: true,
              counterText: '',
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              FilledButton(
                onPressed: () => _maj({
                  'objectif': {'texte': _objectif.text.trim(), 'fait': false}
                }),
                child: const Text('Enregistrer'),
              ),
              const SizedBox(width: 10),
              if (d.objectifDuJour)
                FilterChip(
                  avatar: Icon(fait ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                      size: 18, color: fait ? Couleurs.vert : Couleurs.gris),
                  showCheckmark: false,
                  label: Text(fait ? 'Fait !' : 'Marquer comme fait'),
                  selected: fait,
                  onSelected: (v) => _maj({
                    'objectif': {'texte': (d.objectif['texte'] ?? '').toString(), 'fait': v}
                  }),
                ),
            ],
          ),
          if (suggestions.isNotEmpty) ...[
            const SizedBox(height: 10),
            const Text('Idées (articles à lire, objectifs récents) :',
                style: TextStyle(color: Couleurs.gris, fontSize: 12)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final s in suggestions)
                  ActionChip(
                    label: Text(s, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12)),
                    onPressed: () {
                      _objectif.text = s;
                      _maj({
                        'objectif': {'texte': s, 'fait': false}
                      });
                    },
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  // ------------------------------------------------------------------ avancement
  Widget _carteAvancement(DonneesMaster d) {
    final a = d.auto;
    final lus = _n(a['lus']);
    final aLire = _n(a['a_lire']);
    final motsJour = _n(a['mots_jour']);
    final mots = _n(a['mots']);
    final r = d.resultat;
    final probleme = (a['probleme'] ?? '').toString();
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('Avancement', icone: Icons.insights_rounded),
          _barre('Lecture', lus >= 0 ? '$lus/${d.objectifArticles} articles' : 'dossiers à choisir',
              lus, d.objectifArticles, violet,
              detail: aLire >= 0 ? '$aLire à lire' : null),
          const SizedBox(height: 12),
          _barre('Rédaction aujourd\'hui', motsJour >= 0 ? '$motsJour/${d.objectifMots} mots' : 'mémoire à choisir',
              motsJour, d.objectifMots, Couleurs.vert,
              detail: mots >= 0 ? '$mots mots en tout' : null),
          const SizedBox(height: 12),
          Row(
            children: [
              const Icon(Icons.timer_outlined, size: 18, color: Couleurs.cyan),
              const SizedBox(width: 8),
              Text('Master aujourd\'hui : ${duree(d.tempsJour)}', style: const TextStyle(color: Couleurs.doux)),
              if (cx.etat.masterActif) ...[
                const SizedBox(width: 8),
                const Icon(Icons.circle, size: 8, color: Couleurs.vert),
                const SizedBox(width: 4),
                const Text('en cours', style: TextStyle(color: Couleurs.vert, fontSize: 12)),
              ],
            ],
          ),
          const SizedBox(height: 12),
          if (r == null)
            const Text('Mesures : aucun résultat pour l\'instant (la Odin 3 et la photodiode arrivent).',
                style: TextStyle(color: Couleurs.gris, fontSize: 13))
          else
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Latence ${r['mediane']} ms  •  p95 ${r['p95']}',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                      Text('Session ${r['session']} • ${r['n']} essais • ${r['mode']} ${r['hz']} Hz',
                          style: const TextStyle(color: Couleurs.gris, fontSize: 12)),
                    ],
                  ),
                ),
                SizedBox(width: 90, height: 36, child: CustomPaint(painter: _Courbe(d.courbe))),
              ],
            ),
          if (probleme.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(probleme, style: const TextStyle(color: Couleurs.orange, fontSize: 12)),
          ],
        ],
      ),
    );
  }

  Widget _barre(String nom, String texte, int valeur, int but, Color couleur, {String? detail}) {
    final part = (but > 0 && valeur > 0) ? (valeur / but).clamp(0.0, 1.0) : 0.0;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: Text(nom, style: const TextStyle(color: Couleurs.gris, fontSize: 13))),
            Text(texte, style: const TextStyle(fontWeight: FontWeight.w700)),
          ],
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: part,
            minHeight: 7,
            color: couleur,
            backgroundColor: Colors.white.withValues(alpha: 0.08),
          ),
        ),
        if (detail != null)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(detail, style: const TextStyle(color: Couleurs.gris, fontSize: 12)),
          ),
      ],
    );
  }

  // ------------------------------------------------------------------ réunion
  Widget _carteReunion(DonneesMaster d) {
    final quand = d.dateReunion;
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('Réunion avec le superviseur', icone: Icons.groups_rounded),
          OutlinedButton.icon(
            icon: const Icon(Icons.event_available_rounded),
            label: Text(quand == null
                ? 'Choisir la date et l\'heure'
                : '${dateCourte(quand)} à ${_deux(quand.hour)}:${_deux(quand.minute)}'),
            onPressed: () => _choisirReunion(quand),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _question,
            focusNode: _fQuestion,
            maxLength: 120,
            decoration: const InputDecoration(
              hintText: 'Question à lui poser (ex. APA ou IEEE ?)',
              border: OutlineInputBorder(),
              isDense: true,
              counterText: '',
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              FilledButton(
                onPressed: () => _maj({
                  'reunion': {'date': (d.reunion['date'] ?? '').toString(), 'question': _question.text.trim()}
                }),
                child: const Text('Enregistrer la question'),
              ),
              const SizedBox(width: 8),
              if (quand != null)
                TextButton(
                  onPressed: () => _maj({
                    'reunion': {'date': '', 'question': ''}
                  }),
                  child: const Text('Effacer'),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _choisirReunion(DateTime? actuelle) async {
    final maintenant = DateTime.now();
    final jour = await showDatePicker(
      context: context,
      initialDate: actuelle ?? maintenant,
      firstDate: DateTime(maintenant.year, maintenant.month, maintenant.day),
      lastDate: maintenant.add(const Duration(days: 365)),
    );
    if (jour == null || !mounted) return;
    final heure = await showTimePicker(
      context: context,
      initialTime: actuelle != null ? TimeOfDay.fromDateTime(actuelle) : const TimeOfDay(hour: 10, minute: 0),
    );
    if (heure == null) return;
    final iso = '${dateIso(jour)}T${_deux(heure.hour)}:${_deux(heure.minute)}';
    await _maj({
      'reunion': {'date': iso, 'question': _question.text.trim()}
    });
  }

  // ------------------------------------------------------------------ phase et objectifs chiffrés
  Widget _cartePhase(DonneesMaster d) {
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('Phase et objectifs', icone: Icons.timeline_rounded),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              for (final p in d.phases)
                ChoiceChip(
                  label: Text(p),
                  selected: p == d.phase,
                  onSelected: (_) => _maj({'phase': p}),
                ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(child: _champNombre(_articles, 'Articles visés')),
              const SizedBox(width: 10),
              Expanded(child: _champNombre(_mots, 'Mots par jour')),
            ],
          ),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: () => _maj({
              'objectif_articles': int.tryParse(_articles.text) ?? d.objectifArticles,
              'objectif_mots_jour': int.tryParse(_mots.text) ?? d.objectifMots,
            }),
            child: const Text('Enregistrer les objectifs'),
          ),
        ],
      ),
    );
  }

  Widget _champNombre(TextEditingController c, String nom) => TextField(
        controller: c,
        keyboardType: TextInputType.number,
        decoration: InputDecoration(labelText: nom, border: const OutlineInputBorder(), isDense: true),
      );

  // ------------------------------------------------------------------ fichiers suivis
  Widget _carteFichiers(DonneesMaster d) {
    const noms = {
      'memoire': ('Mémoire (.docx)', r'ex. D:\Master\redaction\memoire.docx'),
      'a_lire': ('Dossier des PDF à lire', r'ex. D:\Master\articles\a_lire'),
      'lus': ('Dossier des PDF lus', r'ex. D:\Master\articles\lus'),
      'resultats': ('CSV des mesures', r'ex. D:\Master\experiences\resultats.csv'),
    };
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: () => setState(() => _fichiersOuverts = !_fichiersOuverts),
            child: Row(
              children: [
                const Expanded(child: Titre('Fichiers suivis sur le PC', icone: Icons.folder_open_rounded)),
                Icon(_fichiersOuverts ? Icons.expand_less_rounded : Icons.expand_more_rounded,
                    color: Couleurs.gris),
              ],
            ),
          ),
          if (!_fichiersOuverts)
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                for (final e in noms.entries)
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(d.cheminOk(e.key) ? Icons.check_circle_rounded : Icons.error_outline_rounded,
                          size: 15, color: d.cheminOk(e.key) ? Couleurs.vert : Couleurs.gris),
                      const SizedBox(width: 4),
                      Text(e.value.$1, style: const TextStyle(fontSize: 12, color: Couleurs.doux)),
                    ],
                  ),
              ],
            )
          else ...[
            const Text(
              'Copie le chemin depuis l\'Explorateur Windows (clic droit → Copier en tant que chemin d\'accès). '
              'Le CSV : timestamp,session,essai,mode_xreal,refresh_hz,perf_mode,temp_c,latence_ms.',
              style: TextStyle(color: Couleurs.gris, fontSize: 12),
            ),
            const SizedBox(height: 10),
            for (final e in noms.entries) ...[
              TextField(
                controller: _chemins[e.key],
                decoration: InputDecoration(
                  labelText: e.value.$1,
                  hintText: e.value.$2,
                  border: const OutlineInputBorder(),
                  isDense: true,
                  suffixIcon: Icon(d.cheminOk(e.key) ? Icons.check_circle_rounded : Icons.error_outline_rounded,
                      color: d.cheminOk(e.key) ? Couleurs.vert : Couleurs.gris),
                ),
              ),
              const SizedBox(height: 10),
            ],
            TextField(
              controller: _motsWord,
              decoration: const InputDecoration(
                labelText: 'Mots du titre Word comptés comme master',
                helperText: 'Séparés par des virgules (ex. memoire, thesis, proposal)',
                border: OutlineInputBorder(),
                isDense: true,
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _motsCode,
              decoration: const InputDecoration(
                labelText: 'Mots du titre VS Code comptés comme master',
                border: OutlineInputBorder(),
                isDense: true,
              ),
            ),
            const SizedBox(height: 10),
            FilledButton(
              onPressed: () => _maj({
                'chemins': {for (final e in _chemins.entries) e.key: e.value.text.trim()},
                'mots_word': _decouper(_motsWord.text),
                'mots_code': _decouper(_motsCode.text),
              }),
              child: const Text('Enregistrer'),
            ),
          ],
        ],
      ),
    );
  }
}

/// Médianes de latence des dernières sessions (plus haut = plus rapide, comme sur l'ESP32).
class _Courbe extends CustomPainter {
  final List<int> serie;

  _Courbe(this.serie);

  @override
  void paint(Canvas canvas, Size size) {
    if (serie.length < 2) return;
    final haut = serie.reduce((a, b) => a > b ? a : b);
    final bas = serie.reduce((a, b) => a < b ? a : b);
    final ecart = (haut - bas) == 0 ? 1 : haut - bas;
    final chemin = Path();
    for (var i = 0; i < serie.length; i++) {
      final x = size.width * i / (serie.length - 1);
      final y = size.height * (serie[i] - bas) / ecart;
      if (i == 0) {
        chemin.moveTo(x, y);
      } else {
        chemin.lineTo(x, y);
      }
    }
    canvas.drawPath(
        chemin,
        Paint()
          ..color = Couleurs.cyan
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2);
  }

  @override
  bool shouldRepaint(_Courbe ancien) => ancien.serie != serie;
}
