// Connexion WebSocket avec le programme PC (tools/agent/serveur_app.py).
import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'etat.dart';

const int portApp = 8765;

enum Statut { sansAdresse, deconnecte, connexion, appairage, connecte }

class Connexion extends ChangeNotifier {
  String adresse = '';
  String? _token;
  Statut statut = Statut.sansAdresse;
  EtatPC etat = EtatPC.vide();
  List<String> apps = [];
  String message = '';
  int numeroMessage = 0; // change à chaque nouveau message (pour afficher une notification)
  bool pinAffiche = false;
  DateTime derniereAction = DateTime.fromMillisecondsSinceEpoch(0);

  WebSocketChannel? _canal;
  StreamSubscription<dynamic>? _abonnement;
  Timer? _reconnexion;
  Timer? _minuterieSouris;
  double _dx = 0;
  double _dy = 0;
  bool _authEnvoyee = false;
  bool _fini = false;

  bool get appaire => _token != null;
  bool get connecte => statut == Statut.connecte;

  Future<void> charger() async {
    final p = await SharedPreferences.getInstance();
    adresse = p.getString('adresse') ?? '';
    _token = p.getString('token');
    statut = adresse.isEmpty ? Statut.sansAdresse : Statut.deconnecte;
    notifyListeners();
    if (adresse.isNotEmpty) connecter();
  }

  Future<void> changerAdresse(String nouvelle) async {
    adresse = nouvelle.trim();
    final p = await SharedPreferences.getInstance();
    await p.setString('adresse', adresse);
    connecter();
  }

  Future<void> oublierAppairage() async {
    _token = null;
    final p = await SharedPreferences.getInstance();
    await p.remove('token');
    connecter();
  }

  void connecter() {
    _reconnexion?.cancel();
    _fermerCanal();
    if (adresse.isEmpty) {
      statut = Statut.sansAdresse;
      notifyListeners();
      return;
    }
    statut = Statut.connexion;
    _authEnvoyee = false;
    pinAffiche = false;
    notifyListeners();
    try {
      final canal = WebSocketChannel.connect(Uri.parse('ws://$adresse:$portApp'));
      _canal = canal;
      _abonnement = canal.stream.listen(
        _recevoir,
        onDone: _perdu,
        onError: (Object _) => _perdu(),
        cancelOnError: true,
      );
      canal.ready.catchError((Object _) => _perdu());
    } catch (_) {
      _perdu();
    }
  }

  void _fermerCanal() {
    _abonnement?.cancel();
    _abonnement = null;
    _canal?.sink.close();
    _canal = null;
  }

  void _perdu() {
    _fermerCanal();
    if (_fini) return;
    if (statut != Statut.sansAdresse) {
      statut = Statut.deconnecte;
      etat = EtatPC.vide();
      notifyListeners();
    }
    _reconnexion?.cancel();
    _reconnexion = Timer(const Duration(seconds: 3), connecter);
  }

  void _recevoir(dynamic brut) {
    Map<String, dynamic> m;
    try {
      m = jsonDecode(brut as String) as Map<String, dynamic>;
    } catch (_) {
      return;
    }
    switch (m['type']) {
      case 'auth_requise':
        if (_token != null) {
          _authEnvoyee = true;
          _envoyer({'type': 'auth', 'token': _token});
        } else {
          statut = Statut.appairage;
        }
      case 'auth_ok':
        final token = m['token'] as String?;
        if (token != null && token != _token) {
          _token = token;
          SharedPreferences.getInstance().then((p) => p.setString('token', token));
        }
        statut = Statut.connecte;
        pinAffiche = false;
        _envoyer({'type': 'apps'});
      case 'erreur':
        if (_authEnvoyee && statut != Statut.connecte) {
          // le PC ne reconnaît plus ce téléphone : il faut refaire l'appairage
          _token = null;
          _authEnvoyee = false;
          SharedPreferences.getInstance().then((p) => p.remove('token'));
          statut = Statut.appairage;
        }
        _annoncer((m['texte'] ?? 'Erreur').toString());
      case 'pin_affiche':
        pinAffiche = true;
      case 'etat':
        etat = EtatPC.depuisJson(m);
      case 'rep':
        _annoncer((m['texte'] ?? '').toString());
      case 'apps':
        final liste = m['apps'];
        if (liste is List) apps = liste.map((e) => e.toString()).toList();
    }
    notifyListeners();
  }

  void _annoncer(String texte) {
    if (texte.isEmpty) return;
    message = texte;
    numeroMessage++;
  }

  void _envoyer(Map<String, dynamic> m) {
    final canal = _canal;
    if (canal == null) return;
    try {
      canal.sink.add(jsonEncode(m));
    } catch (_) {}
  }

  // ------------------------------------------------------------- appairage
  void demanderPin() => _envoyer({'type': 'demande_pin'});

  void envoyerPin(String pin, String nom) =>
      _envoyer({'type': 'pin', 'pin': pin.trim(), 'nom': nom});

  // ------------------------------------------------------------- commandes
  void cmd(String ligne) {
    derniereAction = DateTime.now();
    _envoyer({'type': 'cmd', 'ligne': ligne});
  }

  void rafraichirApps() => _envoyer({'type': 'apps'});

  /// Déplacement de souris : regroupé et envoyé environ 60 fois par seconde.
  void souris(double dx, double dy) {
    _dx += dx;
    _dy += dy;
    _minuterieSouris ??= Timer.periodic(const Duration(milliseconds: 16), (_) {
      final x = _dx.truncate();
      final y = _dy.truncate();
      if (x == 0 && y == 0) {
        _minuterieSouris?.cancel();
        _minuterieSouris = null;
        return;
      }
      _dx -= x;
      _dy -= y;
      _envoyer({'type': 'souris', 'dx': x, 'dy': y});
    });
  }

  void clic(String bouton) => _envoyer({'type': 'clic', 'bouton': bouton});

  void molette(int n) => _envoyer({'type': 'molette', 'n': n});

  void texte(String t) {
    derniereAction = DateTime.now();
    _envoyer({'type': 'texte', 'texte': t});
  }

  @override
  void dispose() {
    _fini = true;
    _reconnexion?.cancel();
    _minuterieSouris?.cancel();
    _fermerCanal();
    super.dispose();
  }
}
