// Carte « Sites vidéo » des Réglages (Phase 11-bis) : pour qu'un site de vidéos que le PC ne connaît
// pas déclenche quand même la scène cinéma. On donne un mot présent dans le titre de l'onglet et le nom
// à afficher. Enregistré sur le PC (tools\agent\sites_video.json).
import 'package:flutter/material.dart';

import '../connexion.dart';
import '../theme.dart';

class CarteSitesVideo extends StatefulWidget {
  final Connexion cx;

  const CarteSitesVideo({super.key, required this.cx});

  @override
  State<CarteSitesVideo> createState() => _CarteSitesVideoState();
}

class _CarteSitesVideoState extends State<CarteSitesVideo> {
  final _mot = TextEditingController();
  final _nom = TextEditingController();
  bool _ouvert = false;

  Connexion get cx => widget.cx;

  @override
  void dispose() {
    _mot.dispose();
    _nom.dispose();
    super.dispose();
  }

  List<Map<String, String>> _liste(dynamic v) => [
        if (v is List)
          for (final s in v)
            if (s is Map) {'mot': (s['mot'] ?? '').toString(), 'nom': (s['nom'] ?? '').toString()},
      ];

  Future<void> _ajouter(List<Map<String, String>> perso) async {
    final mot = _mot.text.trim().toLowerCase();
    final nom = _nom.text.trim();
    if (mot.length < 3 || nom.isEmpty) {
      cx.annoncer('A word of 3 letters or more, and a name');
      return;
    }
    FocusScope.of(context).unfocus();
    final (ok, _) = await cx.majSites([
      ...perso.where((s) => s['mot'] != mot),
      {'mot': mot, 'nom': nom},
    ]);
    if (ok) {
      _mot.clear();
      _nom.clear();
    }
  }

  /// Propose un mot tiré du titre de l'onglet ouvert sur le PC (« Titre - MonSite - Google Chrome »).
  void _depuisOnglet(String onglet) {
    final morceaux = onglet
        .split(RegExp(r'\s+[-–—|]\s+'))
        .map((m) => m.trim())
        .where((m) => m.isNotEmpty && !RegExp(r'chrome|edge|firefox|opera|brave|vivaldi', caseSensitive: false).hasMatch(m))
        .toList();
    if (morceaux.isEmpty) return;
    final site = morceaux.last;
    setState(() {
      _mot.text = site.toLowerCase();
      _nom.text = site.length > 20 ? site.substring(0, 20) : site;
    });
  }

  @override
  Widget build(BuildContext context) {
    final s = cx.sites;
    final perso = _liste(s?['perso']);
    final defaut = _liste(s?['defaut']);
    final onglet = (s?['onglet'] ?? '').toString();
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: () {
              setState(() => _ouvert = !_ouvert);
              if (_ouvert) cx.demanderSites();
            },
            child: Row(
              children: [
                const Expanded(child: Titre('Video sites', icone: Icons.local_movies_rounded)),
                Icon(_ouvert ? Icons.expand_less_rounded : Icons.expand_more_rounded, color: Couleurs.gris),
              ],
            ),
          ),
          if (!_ouvert)
            const Text(
              'A video site is not recognized? Add it here to get the cinema scene.',
              style: TextStyle(color: Couleurs.gris, fontSize: 12),
            )
          else if (s == null)
            const Padding(
              padding: EdgeInsets.all(8),
              child: Center(child: CircularProgressIndicator()),
            )
          else ...[
            const Text(
              'Open the video on the PC, then give a word from the tab title '
              '(often the site name) and the name to show on the ESP32.',
              style: TextStyle(color: Couleurs.gris, fontSize: 12),
            ),
            if (onglet.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Tab open on the PC: $onglet',
                  maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12)),
              TextButton.icon(
                icon: const Icon(Icons.auto_fix_high_rounded, size: 18),
                label: const Text('Use this tab'),
                onPressed: () => _depuisOnglet(onglet),
              ),
            ],
            TextButton.icon(
              icon: const Icon(Icons.refresh_rounded, size: 18),
              label: const Text('Reread the PC tab'),
              onPressed: cx.demanderSites,
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _mot,
                    decoration: const InputDecoration(
                      labelText: 'Title word',
                      hintText: 'e.g. voiranime',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _nom,
                    maxLength: 20,
                    decoration: const InputDecoration(
                      labelText: 'Display name',
                      hintText: 'e.g. VoirAnime',
                      border: OutlineInputBorder(),
                      isDense: true,
                      counterText: '',
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            FilledButton.icon(
              icon: const Icon(Icons.add_rounded),
              label: const Text('Add'),
              onPressed: () => _ajouter(perso),
            ),
            const SizedBox(height: 12),
            const Text('My sites', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            if (perso.isEmpty)
              const Text('(none)', style: TextStyle(color: Couleurs.gris, fontSize: 12))
            else
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final site in perso)
                    InputChip(
                      label: Text('${site['mot']} → ${site['nom']}', style: const TextStyle(fontSize: 12)),
                      onDeleted: () => cx.majSites(perso.where((x) => x['mot'] != site['mot']).toList()),
                    ),
                ],
              ),
            const SizedBox(height: 10),
            Text(
              'Already recognized: ${{for (final d in defaut) d['nom']}.join(', ')}, '
              'and the VLC, MPC, PotPlayer, Movies & TV players and the Netflix app.',
              style: const TextStyle(color: Couleurs.gris, fontSize: 12),
            ),
          ],
        ],
      ),
    );
  }
}
