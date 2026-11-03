// Notification « PC inutilisé » (Phase 11).
// Android vérifie toutes les 15 min (WorkManager, VeilleurPC.kt) en demandant GET /etat_court au PC.
// Si personne n'a touché le PC depuis le seuil choisi (30 min par défaut), une notification
// propose de l'éteindre. Réglages enregistrés dans les préférences (lues par Kotlin).
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'theme.dart';

const _canal = MethodChannel('dadou/notif');

class CarteNotifications extends StatefulWidget {
  const CarteNotifications({super.key});

  @override
  State<CarteNotifications> createState() => _CarteNotificationsState();
}

class _CarteNotificationsState extends State<CarteNotifications> {
  bool _actif = false;
  int _minutes = 30;
  bool _charge = false;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    final p = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() {
      _actif = p.getBool('notif_actif') ?? false;
      _minutes = p.getInt('notif_minutes') ?? 30;
      _charge = true;
    });
  }

  Future<void> _changer(bool actif, int minutes) async {
    setState(() {
      _actif = actif;
      _minutes = minutes;
    });
    final p = await SharedPreferences.getInstance();
    await p.setBool('notif_actif', actif);
    await p.setInt('notif_minutes', minutes);
    try {
      await _canal.invokeMethod<bool>('activer', {'actif': actif});
    } catch (_) {
      // pas Android (tests) : rien à faire
    }
  }

  Future<void> _tester() async {
    try {
      await _canal.invokeMethod<bool>('tester');
    } catch (_) {}
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
      content: Text('Test envoyé : la notification arrive dans quelques secondes'),
    ));
  }

  @override
  Widget build(BuildContext context) {
    if (!_charge) return const SizedBox();
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('Notification « PC inutilisé »', icone: Icons.notifications_active_rounded),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text('Me prévenir après $_minutes min sans activité'),
            subtitle: const Text('Avec un bouton « Éteindre » dans la notification.',
                style: TextStyle(color: Couleurs.gris, fontSize: 12)),
            value: _actif,
            onChanged: (v) => _changer(v, _minutes),
          ),
          if (_actif) ...[
            Wrap(
              spacing: 6,
              children: [
                for (final m in const [15, 30, 60])
                  ChoiceChip(
                    label: Text('$m min'),
                    selected: _minutes == m,
                    onSelected: (_) => _changer(true, m),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              icon: const Icon(Icons.send_rounded),
              label: const Text('Tester maintenant'),
              onPressed: _tester,
            ),
            const SizedBox(height: 8),
            const Text(
              'Android vérifie environ toutes les 15 min. Sur Xiaomi, pour que ce soit fiable : '
              'Paramètres → Applications → Dadou → Économiseur de batterie → « Aucune restriction », '
              'et active « Démarrage automatique ».',
              style: TextStyle(color: Couleurs.gris, fontSize: 12, height: 1.4),
            ),
          ],
        ],
      ),
    );
  }
}
