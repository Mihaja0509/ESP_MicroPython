// Pavé tactile (souris) + clavier.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../connexion.dart';
import '../theme.dart';

class EcranSouris extends StatefulWidget {
  final Connexion cx;

  const EcranSouris({super.key, required this.cx});

  @override
  State<EcranSouris> createState() => _EcranSourisState();
}

class _EcranSourisState extends State<EcranSouris> {
  final Map<int, Offset> _doigts = {};
  DateTime _debut = DateTime.now();
  Offset _depart = Offset.zero; // où le premier doigt a touché l'écran
  bool _bouge = false; // le doigt est sorti de la zone de tap
  bool _deuxDoigts = false;
  bool _aDefile = false; // le geste à deux doigts a vraiment fait défiler
  double _defilement = 0;
  static const double _tolerance =
      8; // pixels : en dessous, c'est un tap, le curseur ne bouge pas
  final _champ = TextEditingController();
  bool _entreeAuto = false;
  double _sensibilite = 1.8;

  Connexion get cx => widget.cx;

  @override
  void dispose() {
    _champ.dispose();
    super.dispose();
  }

  // ------------------------------------------------------------ pavé tactile
  void _bas(PointerDownEvent e) {
    _doigts[e.pointer] = e.position;
    if (_doigts.length == 1) {
      _debut = DateTime.now();
      _depart = e.position;
      _bouge = false;
      _deuxDoigts = false;
      _aDefile = false;
      _defilement = 0;
    } else {
      _deuxDoigts = true;
    }
  }

  void _deplace(PointerMoveEvent e) {
    _doigts[e.pointer] = e.position;
    if (_doigts.length >= 2) {
      // deux doigts : défilement (moyenne des deux doigts)
      _defilement += e.delta.dy / 2;
      while (_defilement.abs() >= 16) {
        final sens = _defilement > 0 ? 1 : -1;
        cx.molette(sens);
        _aDefile = true;
        _defilement -= 16 * sens;
      }
      return;
    }
    // un seul doigt resté après un geste à deux doigts : on attend qu'il se lève
    if (_deuxDoigts) return;
    if (!_bouge) {
      final r = e.position - _depart;
      if (r.distance <= _tolerance) {
        return; // peut-être un tap : le curseur reste en place
      }
      _bouge = true;
      // le geste devient un déplacement : on rattrape la distance déjà parcourue
      cx.souris(r.dx * _sensibilite, r.dy * _sensibilite);
      return;
    }
    final d = e.delta;
    // accélération : les gestes rapides vont plus loin
    final acc = 1 + (d.distance / 12).clamp(0.0, 1.5).toDouble();
    cx.souris(d.dx * _sensibilite * acc, d.dy * _sensibilite * acc);
  }

  void _haut(PointerUpEvent e) {
    _doigts.remove(e.pointer);
    if (_doigts.isNotEmpty) return;
    final duree = DateTime.now().difference(_debut);
    if (_deuxDoigts) {
      // tap à deux doigts = clic droit, sauf s'il y a eu défilement
      if (!_aDefile && duree < const Duration(milliseconds: 400)) {
        _clic('droit');
      }
    } else if (!_bouge) {
      if (duree < const Duration(milliseconds: 250)) {
        _clic('gauche');
      } else if (duree > const Duration(milliseconds: 500)) {
        _clic('droit');
      }
    }
    _deuxDoigts = false;
  }

  void _annule(PointerCancelEvent e) {
    _doigts.remove(e.pointer);
    _bouge = true; // un geste annulé ne doit jamais devenir un clic
    _aDefile = true;
    if (_doigts.isEmpty) _deuxDoigts = false;
  }

  void _clic(String bouton) {
    HapticFeedback.selectionClick();
    cx.clic(bouton);
  }

  // ------------------------------------------------------------ clavier
  void _envoyerTexte() {
    final t = _champ.text;
    if (t.isEmpty && !_entreeAuto) return;
    cx.texte(_entreeAuto ? '$t\n' : t);
    _champ.clear();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: Column(
        children: [
          Expanded(child: _pave()),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(child: _boutonClic('Left click', 'gauche')),
              const SizedBox(width: 10),
              Expanded(child: _boutonClic('Right click', 'droit')),
            ],
          ),
          const SizedBox(height: 10),
          _clavier(),
        ],
      ),
    );
  }

  Widget _pave() {
    return Stack(
      children: [
        Positioned.fill(
          child: Listener(
            behavior: HitTestBehavior.opaque,
            onPointerDown: _bas,
            onPointerMove: _deplace,
            onPointerUp: _haut,
            onPointerCancel: _annule,
            child: Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(24),
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Couleurs.cyan.withValues(alpha: 0.10),
                    Couleurs.magenta.withValues(alpha: 0.10),
                  ],
                ),
                border: Border.all(
                  color: Couleurs.cyan.withValues(alpha: 0.45),
                  width: 1.5,
                ),
              ),
              child: const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    'Slide a finger to move the mouse\nTap = click · Long press = right click\n'
                    'Two fingers = scroll · Two-finger tap = right click',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Couleurs.gris,
                      fontSize: 13,
                      height: 1.5,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
        // le réglage de sensibilité est HORS de la zone tactile (sinon il déplaçait la souris)
        Positioned(
          right: 8,
          top: 4,
          child: Row(
            children: [
              const Icon(Icons.speed_rounded, size: 16, color: Couleurs.gris),
              SizedBox(
                width: 120,
                child: Slider(
                  value: _sensibilite,
                  min: 0.8,
                  max: 3.5,
                  onChanged: (v) => setState(() => _sensibilite = v),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _boutonClic(String texte, String bouton) {
    return Material(
      color: Colors.white.withValues(alpha: 0.07),
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _clic(bouton),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 16),
          child: Center(
            child: Text(
              texte,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                color: Couleurs.doux,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _touche(String texte, String commande) {
    return ActionChip(
      label: Text(texte, style: const TextStyle(fontWeight: FontWeight.w600)),
      backgroundColor: Colors.white.withValues(alpha: 0.07),
      side: BorderSide(color: Colors.white.withValues(alpha: 0.12)),
      onPressed: () {
        HapticFeedback.selectionClick();
        cx.cmd(commande);
      },
    );
  }

  Widget _clavier() {
    return Carte(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _champ,
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => _envoyerTexte(),
                  decoration: const InputDecoration(
                    hintText: 'Type text on the PC…',
                    border: InputBorder.none,
                    isDense: true,
                  ),
                ),
              ),
              Tooltip(
                message: 'Press Enter after the text',
                child: FilterChip(
                  label: const Text('↵'),
                  selected: _entreeAuto,
                  onSelected: (v) => setState(() => _entreeAuto = v),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.send_rounded, color: Couleurs.cyan),
                onPressed: _envoyerTexte,
              ),
            ],
          ),
          const SizedBox(height: 6),
          SizedBox(
            height: 40,
            child: ListView(
              scrollDirection: Axis.horizontal,
              children: [
                for (final (t, c) in const [
                  ('Enter', 'KEY enter'),
                  ('Esc', 'KEY esc'),
                  ('⌫', 'KEY backspace'),
                  ('Tab', 'KEY tab'),
                  ('←', 'KEY left'),
                  ('↑', 'KEY up'),
                  ('↓', 'KEY down'),
                  ('→', 'KEY right'),
                  ('Alt+Tab', 'KEY alt+tab'),
                  ('Ctrl+C', 'KEY ctrl+c'),
                  ('Ctrl+V', 'KEY ctrl+v'),
                  ('Ctrl+Z', 'KEY ctrl+z'),
                  ('Win', 'KEY win'),
                  ('F5', 'KEY f5'),
                  ('F11', 'KEY f11'),
                ]) ...[_touche(t, c), const SizedBox(width: 6)],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
