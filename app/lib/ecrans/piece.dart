// Phase 16 : historique de la pièce (24 h), lu sur l'ESP32 (GET /historique par Wi-Fi).
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../theme.dart';

class PointPiece {
  final int age; // secondes depuis la mesure
  final double t;
  final int? h;
  PointPiece(this.age, this.t, this.h);
}

class EcranPiece extends StatefulWidget {
  const EcranPiece({super.key});

  @override
  State<EcranPiece> createState() => _EcranPieceState();
}

class _EcranPieceState extends State<EcranPiece> {
  List<PointPiece> _points = [];
  String _info = 'Loading…';

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    final p = await SharedPreferences.getInstance();
    final a = (p.getString('esp_adresse') ?? '').trim();
    if (a.isEmpty) {
      setState(() => _info = 'Set the ESP32 address in Settings first');
      return;
    }
    try {
      final c = HttpClient()..connectionTimeout = const Duration(seconds: 4);
      final r = await (await c.getUrl(Uri.parse('http://$a/historique'))).close().timeout(const Duration(seconds: 8));
      final m = jsonDecode(await r.transform(utf8.decoder).join()) as Map;
      c.close();
      final pts = <PointPiece>[
        for (final x in (m['points'] as List))
          PointPiece((x['age'] as num).toInt(), (x['t'] as num).toDouble(), (x['h'] as num?)?.toInt()),
      ];
      if (!mounted) return;
      setState(() {
        _points = pts;
        _info = pts.isEmpty ? 'No data yet (the ESP32 keeps 24 h, one point every 5 min)' : '';
      });
    } catch (_) {
      if (mounted) setState(() => _info = 'ESP32 unreachable (same Wi-Fi?)');
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = _points.map((p) => p.t);
    return Scaffold(
      appBar: AppBar(title: const Text('Room history (24 h)'), actions: [
        IconButton(onPressed: _charger, icon: const Icon(Icons.refresh_rounded)),
      ]),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_info.isNotEmpty) Text(_info, style: const TextStyle(color: Couleurs.doux)),
          if (_points.isNotEmpty) ...[
            Text(
              'Now ${_points.last.t.toStringAsFixed(1)} °C'
              '${_points.last.h != null ? ' · ${_points.last.h} %' : ''}'
              ' — min ${t.reduce((a, b) => a < b ? a : b).toStringAsFixed(1)}'
              ' / max ${t.reduce((a, b) => a > b ? a : b).toStringAsFixed(1)} °C',
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 220,
              child: CustomPaint(painter: _Courbe(_points), size: Size.infinite),
            ),
            const SizedBox(height: 6),
            const Text('Left = oldest, right = now', style: TextStyle(color: Couleurs.doux)),
          ],
        ],
      ),
    );
  }
}

class _Courbe extends CustomPainter {
  final List<PointPiece> pts;
  _Courbe(this.pts);

  @override
  void paint(Canvas canvas, Size s) {
    if (pts.length < 2) return;
    final ts = pts.map((p) => p.t);
    var lo = ts.reduce((a, b) => a < b ? a : b) - 0.5;
    var hi = ts.reduce((a, b) => a > b ? a : b) + 0.5;
    final agemax = pts.map((p) => p.age).reduce((a, b) => a > b ? a : b).clamp(1, 1 << 30);
    final cadre = Paint()
      ..color = Colors.grey.withValues(alpha: 0.4)
      ..style = PaintingStyle.stroke;
    canvas.drawRect(Offset.zero & s, cadre);
    final ligne = Paint()
      ..color = Colors.orangeAccent
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;
    final chemin = Path();
    for (var i = 0; i < pts.length; i++) {
      final x = s.width * (1 - pts[i].age / agemax);
      final y = s.height * (1 - (pts[i].t - lo) / (hi - lo));
      i == 0 ? chemin.moveTo(x, y) : chemin.lineTo(x, y);
    }
    canvas.drawPath(chemin, ligne);
    for (final (v, y) in [(hi, 0.0), (lo, s.height - 14)]) {
      (TextPainter(
        text: TextSpan(text: v.toStringAsFixed(1), style: const TextStyle(fontSize: 11, color: Colors.grey)),
        textDirection: TextDirection.ltr,
      )..layout())
          .paint(canvas, Offset(4, y));
    }
  }

  @override
  bool shouldRepaint(covariant _Courbe old) => old.pts != pts;
}
