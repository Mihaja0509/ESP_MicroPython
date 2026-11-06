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

  /// Version de la partie Android attendue par ce Dart (voir ClimPlan.VERSION côté Kotlin).
  static const int versionAttendue = 2;

  /// Version de la partie Android installée. 0 = injoignable ou trop ancienne (un rechargement à
  /// chaud ne met à jour que le Dart : il faut réinstaller l'APK).
  static Future<int> versionNative() async {
    try {
      return await _canal.invokeMethod<int>('version') ?? 0;
    } catch (_) {
      return 0;
    }
  }

  /// Lance le minuteur : la clim est allumée pendant [secondes], démarrage dans [delaiSecondes].
  /// Les durées sont TOUJOURS en secondes, de bout en bout.
  static Future<bool> minuteur(int secondes, int delaiSecondes) async {
    try {
      return await _canal.invokeMethod<bool>('minuteur', {
            'secondes': secondes,
            'delaiSecondes': delaiSecondes,
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

const String _messageNatifAncien =
    'The Android part of the app is outdated (a hot reload only updates the Dart part). '
    'Reinstall the APK, then try again.';

// ---------------------------------------------------------------- durées du minuteur (Phase 14)
/// Durée maximale du minuteur : 24 h.
const int minuteurMax = 24 * 3600;

/// Heures + minutes + secondes -> secondes.
int dureeEnSecondes(int h, int m, int s) => h * 3600 + m * 60 + s;

/// Secondes -> (heures, minutes, secondes).
({int h, int m, int s}) secondesEnHms(int total) {
  final t = total < 0 ? 0 : total;
  return (h: t ~/ 3600, m: (t % 3600) ~/ 60, s: t % 60);
}

/// Texte du compte à rebours : « 1:05:09 » (h:mm:ss).
String formaterReste(int secondes) {
  final d = secondesEnHms(secondes);
  return '${d.h}:${d.m.toString().padLeft(2, '0')}:${d.s.toString().padLeft(2, '0')}';
}

/// Remet les trois champs dans leurs limites (heures 0-24, minutes et secondes 0-59) et la durée
/// totale dans 0..24:00:00. Les champs vides ou illisibles valent 0.
({int h, int m, int s}) limiterHms(String h, String m, String s) {
  final hh = (int.tryParse(h) ?? 0).clamp(0, 24).toInt();
  final mm = (int.tryParse(m) ?? 0).clamp(0, 59).toInt();
  final ss = (int.tryParse(s) ?? 0).clamp(0, 59).toInt();
  final total = dureeEnSecondes(hh, mm, ss);
  if (total > minuteurMax) return (h: 24, m: 0, s: 0);
  return (h: hh, m: mm, s: ss);
}

/// null si la durée est valable, sinon le message à afficher.
String? verifierDuree(int total) {
  if (total < 1) return 'Minimum 1 second';
  if (total > minuteurMax) return 'Maximum 24:00:00';
  return null;
}

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
  int _tic = 0;
  Map<String, dynamic> _rt =
      {}; // état côté Android : on, minuteurFin, phase, exact…
  int _duree = 30 * 60; // durée du minuteur en SECONDES (champs h / min / s)
  bool _natifAJour = true; // la partie Android installée est-elle à jour ? (voir versionNative)
  final _champH = TextEditingController();
  final _champM = TextEditingController();
  final _champS = TextEditingController();
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
    // chaque seconde : le compte à rebours se met à jour ; toutes les 5 s : état lu chez Android
    _minuterie = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      _tic++;
      final fin = (_rt['minuteurFin'] as num?)?.toInt() ?? 0;
      final fini = fin > 0 && fin <= DateTime.now().millisecondsSinceEpoch;
      if (_tic % 5 == 0 || fini) {
        _rafraichir();
      } else if (fin > 0) {
        setState(() {});
      }
    });
  }

  @override
  void dispose() {
    _minuterie?.cancel();
    _champH.dispose();
    _champM.dispose();
    _champS.dispose();
    super.dispose();
  }

  /// Écrit une durée (secondes) dans les trois champs.
  void _remplirChamps(int secondes) {
    final d = secondesEnHms(secondes);
    _champH.text = d.h.toString();
    _champM.text = d.m.toString();
    _champS.text = d.s.toString();
    _duree = secondes;
  }

  Future<void> _charger() async {
    final p = await SharedPreferences.getInstance();
    final rt = await ClimPlan.etat();
    final version = await ClimPlan.versionNative();
    if (!mounted) return;
    setState(() {
      _natifAJour = version >= ClimPlan.versionAttendue;
      // dernière durée utilisée (secondes) ; l'ancienne valeur en minutes est reprise une fois
      final secondes =
          p.getInt('plan_duree_s') ?? (p.getInt('plan_duree') ?? 30) * 60;
      _remplirChamps(secondes.clamp(1, minuteurMax).toInt());
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
  /// Raccourci (15 min, 30 min, 1 h, 2 h) : remplit les trois champs.
  Future<void> _choisirDuree(int secondes) async {
    setState(() => _remplirChamps(secondes));
    final p = await SharedPreferences.getInstance();
    await p.setInt('plan_duree_s', secondes);
  }

  /// Saisie dans un des champs : on remet les valeurs dans leurs limites et on les garde.
  Future<void> _champModifie() async {
    final d = limiterHms(_champH.text, _champM.text, _champS.text);
    setState(() => _duree = dureeEnSecondes(d.h, d.m, d.s));
    final p = await SharedPreferences.getInstance();
    if (_duree >= 1) await p.setInt('plan_duree_s', _duree);
  }

  /// À la fin de la saisie : les champs affichent les valeurs corrigées.
  void _champTermine() {
    final d = limiterHms(_champH.text, _champM.text, _champS.text);
    setState(() {
      _champH.text = d.h.toString();
      _champM.text = d.m.toString();
      _champS.text = d.s.toString();
      _duree = dureeEnSecondes(d.h, d.m, d.s);
    });
  }

  Future<void> _lancerMinuteur() async {
    _champTermine();
    final erreur = verifierDuree(_duree);
    if (erreur != null) return;
    if (!_natifAJour) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text(_messageNatifAncien)),
      );
      return;
    }
    HapticFeedback.selectionClick();
    final ok = await ClimPlan.minuteur(_duree, 0);
    await _rafraichir();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          ok
              ? 'Timer set: the AC is on for ${formaterReste(_duree)}'
              : 'Could not send: no IR blaster, or open the AC card once first',
        ),
      ),
    );
  }

  Widget _champDuree(String etiquette, TextEditingController c, int maxi) {
    return Expanded(
      child: TextField(
        controller: c,
        keyboardType: TextInputType.number,
        textInputAction: TextInputAction.done,
        textAlign: TextAlign.center,
        maxLength: 2,
        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
        style: const TextStyle(
          fontSize: 22,
          fontWeight: FontWeight.w800,
          color: Colors.white,
        ),
        decoration: InputDecoration(
          labelText: etiquette,
          counterText: '',
          isDense: true,
          border: const OutlineInputBorder(),
        ),
        onChanged: (_) => _champModifie(),
        onEditingComplete: () {
          _champTermine();
          FocusScope.of(context).unfocus();
        },
        onTapOutside: (_) => _champTermine(),
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
    final resteSec = fin > 0
        ? ((fin - DateTime.now().millisecondsSinceEpoch) / 1000).ceil()
        : 0;
    final erreurDuree = verifierDuree(_duree);
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
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _champDuree('Hours', _champH, 24),
              const SizedBox(width: 8),
              _champDuree('Minutes', _champM, 59),
              const SizedBox(width: 8),
              _champDuree('Seconds', _champS, 59),
            ],
          ),
          if (erreurDuree != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                erreurDuree,
                style: const TextStyle(color: Couleurs.orange, fontSize: 12),
              ),
            ),
          if (!_natifAJour)
            const Padding(
              padding: EdgeInsets.only(top: 4),
              child: Text(
                _messageNatifAncien,
                style: TextStyle(color: Couleurs.rouge, fontSize: 12),
              ),
            ),
          const SizedBox(height: 4),
          Wrap(
            spacing: 6,
            children: [
              for (final raccourci in const [
                (15 * 60, '15 min'),
                (30 * 60, '30 min'),
                (3600, '1 h'),
                (2 * 3600, '2 h'),
              ])
                ActionChip(
                  label: Text(raccourci.$2),
                  onPressed: () => _choisirDuree(raccourci.$1),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: (erreurDuree == null && _natifAJour)
                      ? _lancerMinuteur
                      : null,
                  icon: const Icon(Icons.play_arrow_rounded),
                  label: Text('Run for ${formaterReste(_duree)}'),
                ),
              ),
              if (resteSec > 0) ...[
                const SizedBox(width: 8),
                OutlinedButton(
                  onPressed: _annulerMinuteur,
                  child: const Text('Cancel'),
                ),
              ],
            ],
          ),
          if (resteSec > 0)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                'The AC turns off in ${formaterReste(resteSec)}',
                style: const TextStyle(
                  color: Couleurs.orange,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  fontFeatures: [FontFeature.tabularFigures()],
                ),
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
