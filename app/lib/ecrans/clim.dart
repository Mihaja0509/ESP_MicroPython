// Carte « Air conditioner » (Phase 12) : télécommande de la clim York avec l'émetteur
// infrarouge du téléphone. Aucun lien avec le PC : elle marche même hors connexion.
// Chaque appui envoie la trame complète (mode, ventilation, température, swing).
// Phase 13 : swing corrigé (bit 0 = swing actif) ; les trames sont aussi confiées à Android
// (minuteur, plage horaire, automatisme) et l'état « allumée ? » est suivi (clim_plan.dart).
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../clim_ir.dart';
import '../clim_plan.dart';
import '../theme.dart';

class CarteClim extends StatefulWidget {
  final bool jeu;

  const CarteClim({super.key, this.jeu = false});

  @override
  State<CarteClim> createState() => _CarteClimState();
}

class _CarteClimState extends State<CarteClim> {
  ModeClim _mode = ModeClim.cool;
  VentClim _vent = VentClim.auto;
  int _temp = 24;
  bool _swing = false;
  String _info = "Point the phone's IR blaster at the AC, then tap a button.";

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    final p = await SharedPreferences.getInstance();
    final dispo = await ClimIr.disponible();
    if (!mounted) return;
    setState(() {
      _mode =
          ModeClim.values[(p.getInt('clim_mode') ?? 0)
              .clamp(0, ModeClim.values.length - 1)
              .toInt()];
      _vent =
          VentClim.values[(p.getInt('clim_vent') ?? 0)
              .clamp(0, VentClim.values.length - 1)
              .toInt()];
      _temp = (p.getInt('clim_temp') ?? 24).clamp(16, 30).toInt();
      _swing = p.getBool('clim_swing') ?? false;
      if (!dispo) _info = 'This phone has no IR blaster.';
    });
    _confierTrames(); // Android a besoin des trames pour le minuteur et l'automatisme
  }

  void _confierTrames() => ClimPlan.enregistrerTrames(
    mode: _mode,
    vent: _vent,
    temp: _temp,
    swing: _swing,
  );

  Future<void> _sauver() async {
    final p = await SharedPreferences.getInstance();
    await p.setInt('clim_mode', _mode.index);
    await p.setInt('clim_vent', _vent.index);
    await p.setInt('clim_temp', _temp);
    await p.setBool('clim_swing', _swing);
    _confierTrames();
  }

  Future<bool> _envoyer(List<int> octets, String nom) async {
    HapticFeedback.selectionClick();
    final ok = await ClimIr.envoyer(octets);
    if (!mounted) return ok;
    setState(
      () => _info = ok ? 'Sent: $nom' : 'No IR blaster found on this phone.',
    );
    return ok;
  }

  /// Envoie l'état affiché (mode, ventilation, température, swing).
  void _envoyerEtat(String nom) {
    _sauver();
    _envoyer(
      ClimIr.trame(mode: _mode, vent: _vent, temp: _temp, swing: _swing),
      nom,
    );
  }

  /// La touche power est une bascule : après l'envoi, on retourne l'état « allumée ? » supposé.
  Future<void> _basculer() async {
    final e = await ClimPlan.etat();
    final nouveau = e['on'] != true;
    await ClimPlan.setOn(nouveau);
    if (mounted) {
      setState(
        () => _info = 'Sent: power (AC now assumed ${nouveau ? 'ON' : 'OFF'})',
      );
    }
  }

  /// Touche marche/arrêt : l'état affiché avec le drapeau « power ».
  Future<void> _power() async {
    final ok = await _envoyer(
      ClimIr.trame(
        mode: _mode,
        vent: _vent,
        temp: _temp,
        swing: _swing,
        touchePower: true,
      ),
      'power',
    );
    if (ok) await _basculer();
  }

  /// Appui long sur marche/arrêt : l'autre trame « power » vue pendant la collecte
  /// (Cool, Auto, 16 °C). À essayer si l'appui court ne fait rien.
  Future<void> _powerAlternatif() async {
    final ok = await _envoyer(
      ClimIr.trame(
        mode: ModeClim.cool,
        vent: VentClim.auto,
        temp: 16,
        swing: true,
        touchePower: true,
      ),
      'power (alt)',
    );
    if (ok) await _basculer();
  }

  void _changerTemp(int delta) {
    final t = (_temp + delta).clamp(16, 30).toInt();
    if (t == _temp) return;
    setState(() => _temp = t);
    _envoyerEtat('$_temp °C');
  }

  @override
  Widget build(BuildContext context) {
    return Carte(
      jeu: widget.jeu,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('Air conditioner', icone: Icons.ac_unit_rounded),
          Row(
            children: [
              _rond(
                Icons.power_settings_new_rounded,
                _power,
                onLong: _powerAlternatif,
                couleur: Couleurs.vert,
              ),
              const Spacer(),
              _rond(Icons.remove_rounded, () => _changerTemp(-1)),
              SizedBox(
                width: 84,
                child: Text(
                  '$_temp°',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 34,
                    fontWeight: FontWeight.w900,
                    color: Colors.white,
                  ),
                ),
              ),
              _rond(Icons.add_rounded, () => _changerTemp(1)),
              const Spacer(),
              _rond(
                Icons.swap_vert_rounded,
                () {
                  setState(() => _swing = !_swing);
                  _envoyerEtat(_swing ? 'swing on' : 'swing off');
                },
                couleur: Couleurs.orange,
                actif: _swing,
              ),
            ],
          ),
          const SizedBox(height: 14),
          Onglets(
            onglets: const [
              (Icons.ac_unit_rounded, 'Cool'),
              (Icons.water_drop_rounded, 'Dry'),
              (Icons.air_rounded, 'Fan'),
              (Icons.autorenew_rounded, 'Auto'),
            ],
            choisi: _mode.index,
            onChange: (i) {
              setState(() => _mode = ModeClim.values[i]);
              _envoyerEtat('mode ${_mode.name}');
            },
          ),
          const SizedBox(height: 10),
          Onglets(
            onglets: const [
              (Icons.autorenew_rounded, 'Auto'),
              (Icons.signal_cellular_alt_1_bar_rounded, 'Low'),
              (Icons.signal_cellular_alt_2_bar_rounded, 'Med'),
              (Icons.signal_cellular_alt_rounded, 'High'),
            ],
            choisi: _vent.index,
            onChange: (i) {
              setState(() => _vent = VentClim.values[i]);
              _envoyerEtat('fan ${_vent.name}');
            },
          ),
          const SizedBox(height: 10),
          Text(
            _info,
            style: const TextStyle(fontSize: 12, color: Couleurs.gris),
          ),
        ],
      ),
    );
  }

  Widget _rond(
    IconData icone,
    VoidCallback onTap, {
    VoidCallback? onLong,
    Color couleur = Couleurs.cyan,
    bool actif = false,
  }) {
    return Material(
      color: actif
          ? couleur.withValues(alpha: 0.25)
          : Colors.white.withValues(alpha: 0.08),
      shape: const CircleBorder(),
      child: InkWell(
        customBorder: const CircleBorder(),
        onTap: onTap,
        onLongPress: onLong,
        child: Padding(
          padding: const EdgeInsets.all(13),
          child: Icon(icone, color: couleur, size: 24),
        ),
      ),
    );
  }
}
