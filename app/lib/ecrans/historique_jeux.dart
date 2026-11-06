// Historique de jeu (Phase 14), ouvert depuis « My games » : jours, vue par titre, barres 7 / 30 jours.
import 'package:flutter/material.dart';

import '../connexion.dart';
import '../historique.dart';
import '../theme.dart';

const _jours = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const _mois = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

/// « Today », « Yesterday » ou « Mon 3 Nov ».
String libelleJour(String iso, String aujourdhui) {
  if (iso == aujourdhui) return 'Today';
  final d = DateTime.tryParse(iso);
  final a = DateTime.tryParse(aujourdhui);
  if (d == null) return iso;
  if (a != null && dateIso(DateTime(a.year, a.month, a.day - 1)) == iso) {
    return 'Yesterday';
  }
  return '${_jours[d.weekday - 1]} ${d.day} ${_mois[d.month - 1]}';
}

class EcranHistoriqueJeux extends StatefulWidget {
  final Connexion cx;

  const EcranHistoriqueJeux({super.key, required this.cx});

  @override
  State<EcranHistoriqueJeux> createState() => _EcranHistoriqueJeuxState();
}

class _EcranHistoriqueJeuxState extends State<EcranHistoriqueJeux> {
  int _nbJours = 7;
  String? _titre; // null = tous les jeux

  Connexion get cx => widget.cx;

  @override
  void initState() {
    super.initState();
    cx.demanderHistorique();
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Fond(
        ambiance: Ambiance.jeu,
        child: Scaffold(
          appBar: AppBar(
            title: const Text('Play history'),
            backgroundColor: Colors.transparent,
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh_rounded),
                onPressed: cx.demanderHistorique,
              ),
            ],
            bottom: const TabBar(
              tabs: [
                Tab(text: 'Days'),
                Tab(text: 'By game'),
                Tab(text: 'Charts'),
              ],
            ),
          ),
          body: ListenableBuilder(
            listenable: cx,
            builder: (context, _) {
              final brut = cx.historique;
              if (brut == null) {
                return const Center(child: CircularProgressIndicator());
              }
              final h = HistoriqueJeux.depuisJson(brut);
              if (h.jours.isEmpty) {
                return const Center(
                  child: Text(
                    'No game session recorded yet.',
                    style: TextStyle(color: Couleurs.gris),
                  ),
                );
              }
              return TabBarView(
                children: [_vueJours(h), _vueTitres(h), _vueBarres(h)],
              );
            },
          ),
        ),
      ),
    );
  }

  // ------------------------------------------------------------ jours
  Widget _vueJours(HistoriqueJeux h) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: [
        for (final j in h.jours) ...[
          Carte(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        libelleJour(j.date, h.aujourdhui),
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    Text(
                      dureeSecondes(j.secondes),
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: Couleurs.magenta,
                      ),
                    ),
                  ],
                ),
                for (final g in j.jeux) ...[
                  const Divider(height: 18),
                  _detailJeu(g.nom, g),
                ],
              ],
            ),
          ),
          const SizedBox(height: 12),
        ],
      ],
    );
  }

  Widget _detailJeu(String nom, JeuJour g) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                nom,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
            ),
            Text(
              dureeSecondes(g.secondes),
              style: const TextStyle(
                fontWeight: FontWeight.w800,
                color: Couleurs.cyan,
              ),
            ),
          ],
        ),
        Text(
          _lignes(
            sessions: g.sessions,
            fps: g.fps,
            cpu: g.cpu,
            gpu: g.gpu,
            charge: g.charge,
            ram: g.ram,
          ),
          style: const TextStyle(color: Couleurs.gris, fontSize: 12),
        ),
      ],
    );
  }

  /// Détail sur trois lignes : sessions + FPS, températures, charge + RAM.
  String _lignes({
    required int sessions,
    PlageFps? fps,
    MesureTemp? cpu,
    MesureTemp? gpu,
    MesureMoy? charge,
    MesureMoy? ram,
  }) {
    final l1 = <String>[
      if (sessions > 0) '$sessions session${sessions > 1 ? 's' : ''}',
      if (fps != null)
        'FPS ${fps.min} / ${fps.moy} / ${fps.max} (min / avg / max)',
    ];
    final l2 = <String>[
      if (cpu != null) 'CPU ${cpu.moy}° (max ${cpu.max}°)',
      if (gpu != null) 'GPU ${gpu.moy}° (max ${gpu.max}°)',
    ];
    final l3 = <String>[
      if (charge != null) 'GPU load ${charge.moy} %',
      if (ram != null) 'RAM ${ram.moy} %',
    ];
    final lignes = [
      l1,
      l2,
      l3,
    ].where((l) => l.isNotEmpty).map((l) => l.join(' • '));
    return lignes.isEmpty ? 'No measurement' : lignes.join('\n');
  }

  // ------------------------------------------------------------ par titre
  Widget _vueTitres(HistoriqueJeux h) {
    final titres = h.parTitre();
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: [
        for (final t in titres) ...[
          Carte(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: ExpansionTile(
              tilePadding: EdgeInsets.zero,
              childrenPadding: const EdgeInsets.only(bottom: 10),
              shape: const Border(),
              collapsedShape: const Border(),
              title: Text(
                t.nom,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
              subtitle: Text(
                'Total ${dureeSecondes(t.secondes)} • ${t.nbJours} day${t.nbJours > 1 ? 's' : ''}',
                style: const TextStyle(color: Couleurs.cyan, fontSize: 13),
              ),
              expandedCrossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _lignes(
                    sessions: t.sessions,
                    fps: t.fps,
                    cpu: t.cpu,
                    gpu: t.gpu,
                    charge: t.charge,
                    ram: t.ram,
                  ),
                  style: const TextStyle(color: Couleurs.doux, fontSize: 12),
                ),
                const Divider(height: 18),
                for (final (date, g) in t.jours)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 3),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            libelleJour(date, h.aujourdhui),
                            style: const TextStyle(fontSize: 13),
                          ),
                        ),
                        Text(
                          '${dureeSecondes(g.secondes)}'
                          '${g.fps != null ? ' • ${g.fps!.moy} FPS' : ''}',
                          style: const TextStyle(
                            color: Couleurs.gris,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 12),
        ],
      ],
    );
  }

  // ------------------------------------------------------------ barres
  Widget _vueBarres(HistoriqueJeux h) {
    final titres = h.parTitre().map((t) => t.nom).toList();
    final choix = (_titre != null && titres.contains(_titre)) ? _titre : null;
    final serie = h.serie(_nbJours, titre: choix);
    final total = serie.fold<int>(0, (a, b) => a + b);
    final maxi = serie.fold<int>(1, (a, b) => b > a ? b : a);
    final fin = DateTime.tryParse(h.aujourdhui) ?? DateTime.now();
    String etiquette(int i) {
      final d = DateTime(fin.year, fin.month, fin.day - (serie.length - 1 - i));
      return _nbJours <= 7 ? _jours[d.weekday - 1].substring(0, 1) : '${d.day}';
    }

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: [
        Carte(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SegmentedButton<int>(
                segments: const [
                  ButtonSegment(value: 7, label: Text('7 days')),
                  ButtonSegment(value: 30, label: Text('30 days')),
                ],
                selected: {_nbJours},
                onSelectionChanged: (s) => setState(() => _nbJours = s.first),
              ),
              const SizedBox(height: 10),
              DropdownButton<String?>(
                isExpanded: true,
                value: choix,
                items: [
                  const DropdownMenuItem(value: null, child: Text('All games')),
                  for (final n in titres)
                    DropdownMenuItem(
                      value: n,
                      child: Text(n, overflow: TextOverflow.ellipsis),
                    ),
                ],
                onChanged: (v) => setState(() => _titre = v),
              ),
              const SizedBox(height: 6),
              Text(
                'Total: ${dureeSecondes(total)} • average '
                '${dureeSecondes(total ~/ _nbJours)} per day',
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 14),
              SizedBox(
                height: 150,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    for (var i = 0; i < serie.length; i++)
                      Expanded(
                        child: Padding(
                          padding: EdgeInsets.symmetric(
                            horizontal: _nbJours <= 7 ? 4 : 1,
                          ),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              if (_nbJours <= 7 && serie[i] > 0)
                                Text(
                                  serie[i] >= 3600
                                      ? '${serie[i] ~/ 3600}h'
                                      : '${serie[i] ~/ 60}m',
                                  style: const TextStyle(
                                    fontSize: 10,
                                    color: Couleurs.gris,
                                  ),
                                ),
                              const SizedBox(height: 2),
                              Container(
                                height: 3 + 96.0 * serie[i] / maxi,
                                decoration: BoxDecoration(
                                  color: i == serie.length - 1
                                      ? Couleurs.magenta
                                      : Couleurs.cyan.withValues(
                                          alpha: serie[i] > 0 ? 1 : 0.25,
                                        ),
                                  borderRadius: BorderRadius.circular(3),
                                ),
                              ),
                              const SizedBox(height: 4),
                              if (_nbJours <= 7 ||
                                  i % 5 == 0 ||
                                  i == serie.length - 1)
                                Text(
                                  etiquette(i),
                                  style: const TextStyle(
                                    fontSize: 10,
                                    color: Couleurs.doux,
                                  ),
                                )
                              else
                                const SizedBox(height: 12),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
