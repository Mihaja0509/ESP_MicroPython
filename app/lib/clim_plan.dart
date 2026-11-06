// Clim programmée (Phase 13) : minuteur, plage horaire et mode automatique avec le capteur de
// la pièce. Tout tourne côté Android (ClimPlan.kt, alarmes exactes) : ça marche app fermée.
import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'clim_ir.dart';
import 'etat.dart';
import 'theme.dart';

const _canal = MethodChannel('dadou/clim');

/// Pont vers Android.
class ClimPlan {
  /// Range chez Android les trames IR à jour (réglage actuel avec « power », et mode Dry).
  static Future<void> enregistrerTrames({
    required ModeClim mode,
    required VentClim vent,
    required int temp,
    required bool swing,
  }) {
    List<int> d(ModeClim m) => ClimIr.durees(
      ClimIr.trame(
        mode: m,
        vent: vent,
        temp: temp,
        swing: swing,
        touchePower: true,
      ),
    );
    return _appeler('trames', {
      'frequence': ClimIr.frequence,
      'power': d(mode),
      'dryPower': d(ModeClim.dry),
      'mode': mode.name,
      'temp': temp,
    });
  }

  static Future<void> setOn(bool allume) => _appeler('setOn', {'on': allume});
  static Future<void> annulerMinuteur() => _appeler('annulerMinuteur');
  static Future<void> fenetre(bool actif, int de, int a) =>
      _appeler('fenetre', {'actif': actif, 'de': de, 'a': a});
  static Future<void> auto(Map<String, dynamic> reglages) =>
      _appeler('auto', {'json': jsonEncode(reglages)});
  static Future<void> publier() => _appeler('publier');

  static Future<bool> minuteur(int duree, int delai) async {
    try {
      return await _canal.invokeMethod<bool>('minuteur', {
            'duree': duree,
            'delai': delai,
          }) ??
          false;
    } catch (_) {
      return false;
    }
  }

  static Future<Map<String, dynamic>> etat() async {
    try {
      final r = await _canal.invokeMethod<Map>('etat');
      return r == null ? <String, dynamic>{} : Map<String, dynamic>.from(r);
    } catch (_) {
      return <String, dynamic>{};
    }
  }

  static Future<void> _appeler(
    String methode, [
    Map<String, dynamic>? args,
  ]) async {
    try {
      await _canal.invokeMethod<dynamic>(methode, args);
    } catch (_) {
      // pas Android (tests) : rien à faire
    }
  }
}

String _hhmm(int minutes) =>
    '${(minutes ~/ 60).toString().padLeft(2, '0')}:${(minutes % 60).toString().padLeft(2, '0')}';

class _Sous extends StatelessWidget {
  final String texte;

  const _Sous(this.texte);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 14, bottom: 6),
      child: Text(
        texte,
        style: const TextStyle(
          fontWeight: FontWeight.w800,
          color: Couleurs.cyan,
        ),
      ),
    );
  }
}

class CarteClimPlan extends StatefulWidget {
  final EtatPC etat;
  final bool jeu;

  const CarteClimPlan({super.key, required this.etat, this.jeu = false});

  @override
  State<CarteClimPlan> createState() => _CarteClimPlanState();
}

class _CarteClimPlanState extends State<CarteClimPlan> {
  Timer? _minuterie;
  Map<String, dynamic> _rt =
      {}; // état côté Android : on, minuteurFin, phase, exact…
  int _duree = 30;
  bool _fenActif = false;
  int _fenDe = 19 * 60;
  int _fenA = 21 * 60;
  bool _autoActif = false;
  int _tOn = 28;
  int _tOff = 25;
  int _base = 30;
  int _extra = 3;
  int _hDry = 70;
  int _dryMin = 45;

  @override
  void initState() {
    super.initState();
    _charger();
    _minuterie = Timer.periodic(
      const Duration(seconds: 5),
      (_) => _rafraichir(),
    );
  }

  @override
  void dispose() {
    _minuterie?.cancel();
    super.dispose();
  }

  Future<void> _charger() async {
    final p = await SharedPreferences.getInstance();
    final rt = await ClimPlan.etat();
    if (!mounted) return;
    setState(() {
      _duree = p.getInt('plan_duree') ?? 30;
      _fenActif = p.getBool('fen_actif') ?? false;
      _fenDe = p.getInt('fen_de') ?? 19 * 60;
      _fenA = p.getInt('fen_a') ?? 21 * 60;
      _autoActif = p.getBool('auto_actif') ?? false;
      _tOn = p.getInt('auto_t_on') ?? 28;
      _tOff = p.getInt('auto_t_off') ?? 25;
      _base = p.getInt('auto_base') ?? 30;
      _extra = p.getInt('auto_extra') ?? 3;
      _hDry = p.getInt('auto_h_dry') ?? 70;
      _dryMin = p.getInt('auto_dry_min') ?? 45;
      _rt = rt;
    });
    ClimPlan.publier(); // l'écran de l'ESP32 se met à jour à l'ouverture de l'app
  }

  Future<void> _rafraichir() async {
    final rt = await ClimPlan.etat();
    if (mounted) setState(() => _rt = rt);
  }

  // ------------------------------------------------------------ minuteur
  Future<void> _choisirDuree(int m) async {
    setState(() => _duree = m);
    final p = await SharedPreferences.getInstance();
    await p.setInt('plan_duree', m);
  }

  Future<void> _lancerMinuteur() async {
    HapticFeedback.selectionClick();
    final ok = await ClimPlan.minuteur(_duree, 0);
    await _rafraichir();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          ok
              ? 'Timer set: the AC is on for $_duree min'
              : 'Could not send: no IR blaster, or open the AC card once first',
        ),
      ),
    );
  }

  Future<void> _annulerMinuteur() async {
    await ClimPlan.annulerMinuteur();
    await _rafraichir();
  }

  // ------------------------------------------------------------ plage horaire
  Future<void> _sauverFenetre() async {
    final p = await SharedPreferences.getInstance();
    await p.setBool('fen_actif', _fenActif);
    await p.setInt('fen_de', _fenDe);
    await p.setInt('fen_a', _fenA);
    await ClimPlan.fenetre(_fenActif, _fenDe, _fenA);
  }

  Future<void> _choisirHeure(bool debut) async {
    final m = debut ? _fenDe : _fenA;
    final t = await showTimePicker(
      context: context,
      initialTime: TimeOfDay(hour: m ~/ 60, minute: m % 60),
    );
    if (t == null) return;
    setState(() {
      if (debut) {
        _fenDe = t.hour * 60 + t.minute;
      } else {
        _fenA = t.hour * 60 + t.minute;
      }
    });
    await _sauverFenetre();
  }

  // ------------------------------------------------------------ automatisme
  Future<void> _sauverAuto() async {
    if (_tOff >= _tOn) _tOff = _tOn - 1;
    final p = await SharedPreferences.getInstance();
    await p.setBool('auto_actif', _autoActif);
    await p.setInt('auto_t_on', _tOn);
    await p.setInt('auto_t_off', _tOff);
    await p.setInt('auto_base', _base);
    await p.setInt('auto_extra', _extra);
    await p.setInt('auto_h_dry', _hDry);
    await p.setInt('auto_dry_min', _dryMin);
    await ClimPlan.auto({
      'actif': _autoActif,
      't_on': _tOn,
      't_off': _tOff,
      'base': _base,
      'extra': _extra,
      'h_dry': _hDry,
      'dry_min': _dryMin,
    });
    await _rafraichir();
  }

  void _regler(VoidCallback f) {
    setState(f);
    _sauverAuto();
  }

  Widget _pas(
    String nom,
    String valeur,
    VoidCallback moins,
    VoidCallback plus,
  ) {
    return Padding(
      padding: const EdgeInsets.only(top: 2),
      child: Row(
        children: [
          Expanded(
            child: Text(
              nom,
              style: const TextStyle(color: Couleurs.doux, fontSize: 13),
            ),
          ),
          IconButton(
            visualDensity: VisualDensity.compact,
            icon: const Icon(
              Icons.remove_circle_outline_rounded,
              color: Couleurs.cyan,
            ),
            onPressed: moins,
          ),
          SizedBox(
            width: 72,
            child: Text(
              valeur,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontWeight: FontWeight.w800,
                color: Colors.white,
              ),
            ),
          ),
          IconButton(
            visualDensity: VisualDensity.compact,
            icon: const Icon(
              Icons.add_circle_outline_rounded,
              color: Couleurs.cyan,
            ),
            onPressed: plus,
          ),
        ],
      ),
    );
  }

  // ------------------------------------------------------------ affichage
  @override
  Widget build(BuildContext context) {
    final e = widget.etat;
    final allume = _rt['on'] == true;
    final fin = (_rt['minuteurFin'] as num?)?.toInt() ?? 0;
    final resteMin = fin > 0
        ? ((fin - DateTime.now().millisecondsSinceEpoch) / 60000).ceil()
        : 0;
    final phase = (_rt['phase'] ?? 'idle').toString();
    final t = e.pieceT;
    final piece = t == null
        ? 'Room: no reading (sensor not connected?)'
        : 'Room: ${t.toStringAsFixed(1)} °C · ${e.pieceH} %'
              '${e.pieceP > 0 ? ' · ${e.pieceP} hPa' : ''}';
    return Carte(
      jeu: widget.jeu,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('AC timer & automation', icone: Icons.timer_rounded),
          Text(piece, style: const TextStyle(color: Couleurs.doux)),
          SwitchListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text(allume ? 'AC is ON (assumed)' : 'AC is OFF (assumed)'),
            subtitle: const Text(
              'Flip it if the app is out of sync with the real AC',
              style: TextStyle(fontSize: 11, color: Couleurs.gris),
            ),
            value: allume,
            onChanged: (v) async {
              await ClimPlan.setOn(v);
              await _rafraichir();
            },
          ),
          const _Sous('Timer'),
          Wrap(
            spacing: 6,
            children: [
              for (final m in const [15, 30, 45, 60, 90, 120])
                ChoiceChip(
                  label: Text('$m min'),
                  selected: _duree == m,
                  onSelected: (_) => _choisirDuree(m),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: _lancerMinuteur,
                  icon: const Icon(Icons.play_arrow_rounded),
                  label: Text('Run for $_duree min'),
                ),
              ),
              if (resteMin > 0) ...[
                const SizedBox(width: 8),
                OutlinedButton(
                  onPressed: _annulerMinuteur,
                  child: const Text('Cancel'),
                ),
              ],
            ],
          ),
          if (resteMin > 0)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                'The AC turns off in $resteMin min',
                style: const TextStyle(color: Couleurs.orange, fontSize: 12),
              ),
            ),
          const _Sous('Daily window'),
          SwitchListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text('On at ${_hhmm(_fenDe)}, off at ${_hhmm(_fenA)}'),
            value: _fenActif,
            onChanged: (v) {
              setState(() => _fenActif = v);
              _sauverFenetre();
            },
          ),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _choisirHeure(true),
                  child: Text('From ${_hhmm(_fenDe)}'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _choisirHeure(false),
                  child: Text('To ${_hhmm(_fenA)}'),
                ),
              ),
            ],
          ),
          const _Sous('Automatic (room sensor)'),
          SwitchListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: const Text('Auto mode'),
            subtitle: Text(
              phase == 'cool'
                  ? 'Cooling now'
                  : phase == 'dry'
                  ? 'Drying the air now'
                  : 'Watching the room every minute',
              style: const TextStyle(fontSize: 11, color: Couleurs.gris),
            ),
            value: _autoActif,
            onChanged: (v) => _regler(() => _autoActif = v),
          ),
          _pas(
            'Turn on at ≥',
            '$_tOn °C',
            () => _regler(() => _tOn = (_tOn - 1).clamp(18, 40).toInt()),
            () => _regler(() => _tOn = (_tOn + 1).clamp(18, 40).toInt()),
          ),
          _pas(
            'Turn off at ≤',
            '$_tOff °C',
            () =>
                _regler(() => _tOff = (_tOff - 1).clamp(14, _tOn - 1).toInt()),
            () =>
                _regler(() => _tOff = (_tOff + 1).clamp(14, _tOn - 1).toInt()),
          ),
          _pas(
            'Run time',
            '$_base min',
            () => _regler(() => _base = (_base - 5).clamp(10, 120).toInt()),
            () => _regler(() => _base = (_base + 5).clamp(10, 120).toInt()),
          ),
          _pas(
            '+ per °C above',
            '$_extra min',
            () => _regler(() => _extra = (_extra - 1).clamp(0, 10).toInt()),
            () => _regler(() => _extra = (_extra + 1).clamp(0, 10).toInt()),
          ),
          _pas(
            'Dry mode above',
            '$_hDry %',
            () => _regler(() => _hDry = (_hDry - 5).clamp(50, 95).toInt()),
            () => _regler(() => _hDry = (_hDry + 5).clamp(50, 95).toInt()),
          ),
          _pas(
            'Dry run time',
            '$_dryMin min',
            () => _regler(() => _dryMin = (_dryMin - 5).clamp(10, 120).toInt()),
            () => _regler(() => _dryMin = (_dryMin + 5).clamp(10, 120).toInt()),
          ),
          const SizedBox(height: 8),
          if (_rt['exact'] == false)
            const Text(
              'Exact alarms are blocked: allow "Alarms & reminders" for Dadou in Android settings.',
              style: TextStyle(fontSize: 12, color: Couleurs.orange),
            ),
          const Text(
            'Keep the phone aimed at the AC and plugged in. In Android settings set Dadou to '
            '"No restrictions" for battery and allow autostart.',
            style: TextStyle(fontSize: 11, color: Couleurs.gris),
          ),
        ],
      ),
    );
  }
}
