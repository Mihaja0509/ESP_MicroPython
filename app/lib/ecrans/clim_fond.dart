// Carte « Background » (Phase 15) : ce qui peut empêcher la clim programmée de tourner app fermée.
// Chaque ligne dit si le réglage est bon et ouvre le bon écran système.
import 'dart:async';

import 'package:flutter/material.dart';

import '../clim_plan.dart';
import '../theme.dart';

class CarteClimFond extends StatefulWidget {
  final bool jeu;

  const CarteClimFond({super.key, this.jeu = false});

  @override
  State<CarteClimFond> createState() => _CarteClimFondState();
}

class _CarteClimFondState extends State<CarteClimFond>
    with WidgetsBindingObserver {
  Map<String, dynamic> _fond = {};
  String _journal = '';
  bool _service = false;
  Timer? _suivi;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _lire();
    _suivi = Timer.periodic(const Duration(seconds: 5), (_) => _lire());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _suivi?.cancel();
    super.dispose();
  }

  // retour d'un écran système : on relit tout de suite
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _lire();
  }

  Future<void> _lire() async {
    final fond = await ClimPlan.fond();
    final rt = await ClimPlan.etat();
    if (!mounted) return;
    setState(() {
      _fond = fond;
      _journal = (rt['journal'] ?? '').toString();
      _service = rt['service'] == true;
    });
  }

  Widget _ligne(String nom, bool? ok, String reglage) {
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Row(
        children: [
          Icon(
            ok == null
                ? Icons.help_outline_rounded
                : ok
                ? Icons.check_circle_rounded
                : Icons.error_rounded,
            size: 20,
            color: ok == null
                ? Couleurs.gris
                : ok
                ? Couleurs.vert
                : Couleurs.orange,
          ),
          const SizedBox(width: 8),
          Expanded(child: Text(nom, style: const TextStyle(fontSize: 13))),
          TextButton(
            onPressed: () => ClimPlan.ouvrirReglage(reglage),
            child: const Text('Open'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Carte(
      jeu: widget.jeu,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('Background', icone: Icons.shield_moon_rounded),
          Text(
            _service
                ? 'Background service running'
                : 'Background service stopped (nothing scheduled)',
            style: const TextStyle(fontSize: 12, color: Couleurs.gris),
          ),
          _ligne('Notifications', _fond['notifs'] as bool?, 'notifs'),
          _ligne('Exact alarms', _fond['exact'] as bool?, 'exact'),
          _ligne(
            'Battery optimization ignored',
            _fond['batterie'] as bool?,
            'batterie',
          ),
          if (_fond['autostart'] == true)
            _ligne('Autostart (Xiaomi: check it by hand)', null, 'autostart'),
          if (_journal.isNotEmpty)
            Theme(
              data: Theme.of(context)
                  .copyWith(dividerColor: Colors.transparent),
              child: ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: const Text(
                  'Recent events',
                  style: TextStyle(fontSize: 13),
                ),
                children: [
                  Align(
                    alignment: Alignment.centerLeft,
                    child: SelectableText(
                      _journal,
                      style: const TextStyle(
                        fontSize: 11,
                        color: Couleurs.gris,
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
}
