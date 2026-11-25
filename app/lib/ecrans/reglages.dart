// Adresse du PC, appairage avec le code affiché sur l'ESP32, aide Tailscale.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../connexion.dart';
import '../theme.dart';
import '../notifications.dart';
import 'piece.dart';
import '../widgets/sites_video.dart';
import '../widget_android.dart';

class EcranReglages extends StatefulWidget {
  final Connexion cx;

  const EcranReglages({super.key, required this.cx});

  @override
  State<EcranReglages> createState() => _EcranReglagesState();
}

class _EcranReglagesState extends State<EcranReglages> {
  late final TextEditingController _adresse;
  final _pin = TextEditingController();
  final _esp = TextEditingController();
  final _espToken = TextEditingController();
  final _alerte = TextEditingController();
  String _espInfo = '';

  Connexion get cx => widget.cx;

  @override
  void initState() {
    super.initState();
    _adresse = TextEditingController(text: cx.adresse);
    SharedPreferences.getInstance().then((p) {
      if (!mounted) return;
      _esp.text = p.getString('esp_adresse') ?? '';
      _espToken.text = p.getString('esp_token') ?? '';
      _alerte.text = p.getString('alerte_t') ?? '';
    });
  }

  /// Commande protégée par le jeton (WEB_TOKEN de secrets.py) : /ecran?on=0|1, /redemarrer.
  Future<void> _commandeEsp(String chemin, String ok) async {
    final p = await SharedPreferences.getInstance();
    final a = (p.getString('esp_adresse') ?? '').trim();
    final t = (p.getString('esp_token') ?? '').trim();
    if (a.isEmpty || t.isEmpty) {
      setState(() => _espInfo = 'Set the address and the token first');
      return;
    }
    try {
      final c = HttpClient()..connectionTimeout = const Duration(seconds: 4);
      final req = await c.getUrl(Uri.parse('http://$a$chemin'));
      req.headers.set('X-Token', t);
      final r = await req.close().timeout(const Duration(seconds: 5));
      await r.drain();
      c.close();
      if (mounted) setState(() => _espInfo = r.statusCode == 200 ? ok : r.statusCode == 401 ? 'Wrong token' : 'Error ${r.statusCode}');
    } catch (_) {
      if (mounted) setState(() => _espInfo = 'ESP32 unreachable');
    }
  }

  /// Phase 16 : adresse Wi-Fi de l'ESP32 (/mesure). Gardée dans « flutter.esp_adresse », lue par
  /// ClimPlan.kt (automatisme) ; le PC reste le plan B.
  Future<void> _enregistrerEsp() async {
    final a = _esp.text.trim();
    final p = await SharedPreferences.getInstance();
    await p.setString('esp_token', _espToken.text.trim());
    final seuil = double.tryParse(_alerte.text.trim().replaceAll(',', '.'));
    if (seuil == null) {
      await p.remove('alerte_t');
    } else {
      await p.setString('alerte_t', seuil.toString());
    }
    if (a.isEmpty) {
      await p.remove('esp_adresse');
      setState(() => _espInfo = 'Removed (the PC is used instead)');
      return;
    }
    await p.setString('esp_adresse', a);
    setState(() => _espInfo = 'Testing…');
    try {
      final c = HttpClient()..connectionTimeout = const Duration(seconds: 4);
      final r = await (await c.getUrl(Uri.parse('http://$a/mesure'))).close().timeout(const Duration(seconds: 5));
      final m = jsonDecode(await r.transform(utf8.decoder).join()) as Map;
      c.close();
      if (!mounted) return;
      setState(() => _espInfo = m['ok'] == true
          ? 'OK: ${m['t']} °C${m['h'] != null ? ' · ${m['h']} %' : ''}'
          : 'ESP32 reached, but no measurement (sensor?)');
    } catch (_) {
      if (mounted) setState(() => _espInfo = 'ESP32 unreachable (same Wi-Fi? address?)');
    }
  }

  @override
  void dispose() {
    _esp.dispose();
    _espToken.dispose();
    _alerte.dispose();
    _adresse.dispose();
    _pin.dispose();
    super.dispose();
  }

  String get _texteStatut => switch (cx.statut) {
        Statut.sansAdresse => 'No address',
        Statut.deconnecte => 'PC unreachable (retrying every 3 s)',
        Statut.connexion => 'Connecting…',
        Statut.appairage => 'Connected, pairing needed',
        Statut.connecte => 'Connected and paired',
      };

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      children: [
        Carte(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Titre('PC address', icone: Icons.computer_rounded),
              TextField(
                controller: _adresse,
                keyboardType: TextInputType.url,
                decoration: const InputDecoration(
                  hintText: 'e.g. 100.101.102.103 (Tailscale address of the PC)',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: Text(_texteStatut,
                        style: TextStyle(color: cx.connecte ? Couleurs.vert : Couleurs.doux)),
                  ),
                  FilledButton(
                    onPressed: () => cx.changerAdresse(_adresse.text),
                    child: const Text('Connect'),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Carte(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Titre('Room sensor (Wi-Fi)', icone: Icons.thermostat_rounded),
              const Text(
                'Address of the ESP32 on your home Wi-Fi. The AC automation reads the room '
                'temperature straight from it, even when the PC is off.',
                style: TextStyle(color: Couleurs.doux),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _esp,
                keyboardType: TextInputType.url,
                decoration: const InputDecoration(
                  hintText: 'e.g. 192.168.100.29',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _espToken,
                obscureText: true,
                decoration: const InputDecoration(
                  hintText: 'Token (WEB_TOKEN of the ESP32, for screen / restart)',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _alerte,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                  hintText: 'Alert above … °C (empty = no alert)',
                  helperText: 'The alert works while the AC service runs (automation, timer or time range on).',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(child: Text(_espInfo, style: const TextStyle(color: Couleurs.doux))),
                  FilledButton(onPressed: _enregistrerEsp, child: const Text('Save & test')),
                ],
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  OutlinedButton(
                    onPressed: () => Navigator.of(context)
                        .push(MaterialPageRoute(builder: (_) => const EcranPiece())),
                    child: const Text('Room history'),
                  ),
                  OutlinedButton(
                    onPressed: () => _commandeEsp('/ecran?on=0', 'Screen off'),
                    child: const Text('ESP screen off'),
                  ),
                  OutlinedButton(
                    onPressed: () => _commandeEsp('/ecran?on=1', 'Screen on'),
                    child: const Text('ESP screen on'),
                  ),
                  OutlinedButton(
                    onPressed: () => _commandeEsp('/redemarrer', 'Restarting…'),
                    child: const Text('Restart ESP32'),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Carte(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Titre('Pairing', icone: Icons.verified_user_rounded),
              if (cx.statut == Statut.appairage) ...[
                const Text(
                  "So that nobody else can control your PC, this phone must be "
                  "paired once with a code shown on the ESP32 screen.",
                  style: TextStyle(color: Couleurs.doux),
                ),
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  icon: const Icon(Icons.pin_rounded),
                  label: Text(cx.pinAffiche ? 'New code' : 'Show the code on the ESP32'),
                  onPressed: cx.demanderPin,
                ),
                if (cx.pinAffiche) ...[
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _pin,
                          keyboardType: TextInputType.number,
                          maxLength: 6,
                          decoration: const InputDecoration(
                            hintText: '6-digit code',
                            border: OutlineInputBorder(),
                            isDense: true,
                            counterText: '',
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      FilledButton(
                        onPressed: () {
                          cx.envoyerPin(_pin.text, "Mihaja's phone");
                          _pin.clear();
                        },
                        child: const Text('Confirm'),
                      ),
                    ],
                  ),
                ],
              ] else if (cx.appaire)
                Row(
                  children: [
                    const Icon(Icons.check_circle_rounded, color: Couleurs.vert),
                    const SizedBox(width: 8),
                    const Expanded(child: Text('This phone is paired.')),
                    TextButton(onPressed: cx.oublierAppairage, child: const Text('Forget')),
                  ],
                )
              else
                const Text('Connect to the PC first.', style: TextStyle(color: Couleurs.gris)),
            ],
          ),
        ),
        const SizedBox(height: 14),
        CarteWidgetAndroid(cx: cx),
        const SizedBox(height: 14),
        const CarteNotifications(),
        const SizedBox(height: 14),
        CarteSitesVideo(cx: cx),
        const SizedBox(height: 14),
        const Carte(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Titre('From anywhere', icone: Icons.public_rounded),
              Text(
                '1. Install Tailscale on the PC and on this phone, with the same account.\n'
                '2. In Tailscale on the PC, copy the PC address (it starts with 100.).\n'
                '3. Put this address above: the app then works at home, on 4G, everywhere.\n'
                '4. At home without Tailscale, the local PC address (192.168…) works too.',
                style: TextStyle(color: Couleurs.doux, height: 1.5),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
