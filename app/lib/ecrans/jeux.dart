// Page « Mes jeux » (Phase 11) : temps de jeu, semaine, FPS moyens, jeux reconnus.
// Ouverte depuis l'Accueil. Les listes modifient tools\agent\jeux.json sur le PC.
import 'package:flutter/material.dart';

import '../connexion.dart';
import '../theme.dart';
import 'master.dart' show duree;

class EcranJeux extends StatefulWidget {
  final Connexion cx;

  const EcranJeux({super.key, required this.cx});

  @override
  State<EcranJeux> createState() => _EcranJeuxState();
}

class _EcranJeuxState extends State<EcranJeux> {
  final _ajout = TextEditingController();

  Connexion get cx => widget.cx;

  @override
  void initState() {
    super.initState();
    cx.demanderJeux();
  }

  @override
  void dispose() {
    _ajout.dispose();
    super.dispose();
  }

  List<String> _liste(dynamic v) => v is List ? v.map((e) => e.toString()).toList() : <String>[];

  int _n(dynamic v) => v is num ? v.toInt() : -1;

  @override
  Widget build(BuildContext context) {
    return Fond(
      ambiance: Ambiance.jeu,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Mes jeux'),
          backgroundColor: Colors.transparent,
          actions: [
            IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: cx.demanderJeux),
          ],
        ),
        body: ListenableBuilder(
          listenable: cx,
          builder: (context, _) {
            final j = cx.jeux;
            if (j == null) return const Center(child: CircularProgressIndicator());
            final stats = j['stats'] is List ? (j['stats'] as List) : const [];
            final semaine = j['semaine'] is List ? (j['semaine'] as List) : const [];
            final enCours = j['en_cours'] is Map ? (j['en_cours'] as Map) : const {};
            final jeux = _liste(j['jeux']);
            final pas = _liste(j['pas_des_jeux']);
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
              children: [
                if ((enCours['nom'] ?? '').toString().isNotEmpty) ...[
                  _carteEnCours(enCours),
                  const SizedBox(height: 14),
                ],
                _carteSemaine(semaine),
                const SizedBox(height: 14),
                _carteStats(stats),
                const SizedBox(height: 14),
                _carteListes(jeux, pas),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _carteEnCours(Map enCours) {
    final exe = (enCours['exe'] ?? '').toString();
    return Carte(
      jeu: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('En cours', icone: Icons.sports_esports_rounded),
          Text(enCours['nom'].toString(), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          if (exe.isNotEmpty) Text(exe, style: const TextStyle(color: Couleurs.gris, fontSize: 12)),
          const SizedBox(height: 10),
          if (exe.isNotEmpty)
            OutlinedButton.icon(
              icon: const Icon(Icons.block_rounded),
              label: const Text("Ce n'est pas un jeu"),
              onPressed: () async {
                final ok = await confirmer(context, "Ce n'est pas un jeu",
                    '$exe ne déclenchera plus le mode jeu. Tu pourras le remettre plus bas.');
                if (ok) await cx.pasUnJeu();
              },
            )
          else
            const Text('Jeu lancé par Steam : toujours reconnu.',
                style: TextStyle(color: Couleurs.gris, fontSize: 12)),
        ],
      ),
    );
  }

  Widget _carteSemaine(List semaine) {
    final minutes = [for (final s in semaine) _n((s as Map)['minutes'])];
    final total = minutes.fold<int>(0, (a, b) => a + (b > 0 ? b : 0));
    final maxi = minutes.fold<int>(1, (a, b) => b > a ? b : a);
    const jours = ['L', 'M', 'M', 'J', 'V', 'S', 'D'];
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('7 derniers jours', icone: Icons.bar_chart_rounded),
          Text('Total : ${duree(total)}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          const SizedBox(height: 12),
          SizedBox(
            height: 110,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                for (var i = 0; i < semaine.length; i++)
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          if (minutes[i] > 0)
                            Text(minutes[i] >= 60 ? '${minutes[i] ~/ 60}h' : '${minutes[i]}',
                                style: const TextStyle(fontSize: 10, color: Couleurs.gris)),
                          const SizedBox(height: 2),
                          Container(
                            height: 4 + 70.0 * (minutes[i] > 0 ? minutes[i] : 0) / maxi,
                            decoration: BoxDecoration(
                              color: i == semaine.length - 1 ? Couleurs.magenta : Couleurs.cyan,
                              borderRadius: BorderRadius.circular(4),
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(_jourSemaine((semaine[i] as Map)['date'].toString(), jours),
                              style: const TextStyle(fontSize: 11, color: Couleurs.doux)),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _jourSemaine(String iso, List<String> jours) {
    final d = DateTime.tryParse(iso);
    return d == null ? '' : jours[d.weekday - 1];
  }

  Widget _carteStats(List stats) {
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('Temps par jeu', icone: Icons.emoji_events_rounded),
          if (stats.isEmpty)
            const Text('Pas encore de session enregistrée.', style: TextStyle(color: Couleurs.gris)),
          for (final s in stats.take(15))
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text((s as Map)['nom'].toString(),
                            maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontWeight: FontWeight.w700)),
                        Text(
                          '${_n(s['sessions'])} session${_n(s['sessions']) > 1 ? 's' : ''}'
                          '${_n(s['fps']) > 0 ? ' • ${_n(s['fps'])} FPS moyens' : ''}'
                          '${(s['dernier'] ?? '').toString().isNotEmpty ? ' • ${s['dernier']}' : ''}',
                          style: const TextStyle(color: Couleurs.gris, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  Text(duree(_n(s['minutes']) > 0 ? _n(s['minutes']) : 0),
                      style: const TextStyle(fontWeight: FontWeight.w800, color: Couleurs.cyan)),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _carteListes(List<String> jeux, List<String> pas) {
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('Jeux reconnus', icone: Icons.rule_rounded),
          const Text(
            'Les jeux Steam et ceux des dossiers de jeux sont reconnus tout seuls. '
            'Ici, tu forces un programme (nom du .exe) dans un sens ou dans l\'autre.',
            style: TextStyle(color: Couleurs.gris, fontSize: 12),
          ),
          const SizedBox(height: 10),
          const Text('Toujours un jeu', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          _puces(jeux, Couleurs.vert, (n) => cx.majJeux(jeux.where((x) => x != n).toList(), pas)),
          const SizedBox(height: 10),
          const Text('Jamais un jeu', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          _puces(pas, Couleurs.rouge, (n) => cx.majJeux(jeux, pas.where((x) => x != n).toList())),
          const SizedBox(height: 12),
          TextField(
            controller: _ajout,
            decoration: const InputDecoration(
              hintText: 'ex. tennis2.exe',
              border: OutlineInputBorder(),
              isDense: true,
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              FilledButton(
                onPressed: () => _ajouter(jeux, pas, toujours: true),
                child: const Text('Toujours un jeu'),
              ),
              OutlinedButton(
                onPressed: () => _ajouter(jeux, pas, toujours: false),
                child: const Text('Jamais un jeu'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _puces(List<String> noms, Color couleur, Future<(bool, String)> Function(String) retirer) {
    if (noms.isEmpty) return const Text('(vide)', style: TextStyle(color: Couleurs.gris, fontSize: 12));
    return Wrap(
      spacing: 6,
      runSpacing: 6,
      children: [
        for (final n in noms)
          InputChip(
            label: Text(n, style: const TextStyle(fontSize: 12)),
            side: BorderSide(color: couleur.withValues(alpha: 0.6)),
            onDeleted: () => retirer(n),
          ),
      ],
    );
  }

  Future<void> _ajouter(List<String> jeux, List<String> pas, {required bool toujours}) async {
    var n = _ajout.text.trim().toLowerCase();
    if (n.isEmpty) return;
    if (!n.endsWith('.exe')) n = '$n.exe';
    FocusScope.of(context).unfocus();
    final (ok, _) = toujours
        ? await cx.majJeux([...jeux.where((x) => x != n), n], pas.where((x) => x != n).toList())
        : await cx.majJeux(jeux.where((x) => x != n).toList(), [...pas.where((x) => x != n), n]);
    if (ok) _ajout.clear();
  }
}
