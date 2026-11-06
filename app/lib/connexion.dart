// Connexion WebSocket avec le programme PC (tools/agent/serveur_app.py).
import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart' show AppLifecycleListener;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'clim_plan.dart' show ClimPlan;
import 'etat.dart';

const int portApp = 8765;

enum Statut { sansAdresse, deconnecte, connexion, appairage, connecte }

/// Une app du PC : un lien web, un chemin Windows, ou une commande (« autre »).
class AppPc {
  final String nom;
  final String cible;
  final String type; // web | chemin | autre

  const AppPc(this.nom, this.cible, this.type);

  bool get web => type == 'web';

  static AppPc depuis(dynamic e) {
    if (e is Map) {
      return AppPc((e['nom'] ?? '').toString(), (e['cible'] ?? '').toString(),
          (e['type'] ?? 'autre').toString());
    }
    return AppPc(e.toString(), '', 'autre'); // ancien programme PC : juste le nom
  }
}

/// Une étape d'un raccourci (Phase 7).
/// type : touches | texte | entree | commande | app | pause | action
class Etape {
  final String type;
  final String valeur;
  final String shell; // commande : powershell | cmd
  final bool visible; // commande : fenêtre visible

  const Etape(this.type, this.valeur, {this.shell = 'powershell', this.visible = true});

  static Etape depuis(dynamic e) {
    final m = e is Map ? e : const {};
    return Etape(
      (m['type'] ?? 'touches').toString(),
      (m['valeur'] ?? '').toString(),
      shell: m['shell'] == 'cmd' ? 'cmd' : 'powershell',
      visible: m['visible'] != false,
    );
  }

  Map<String, dynamic> versJson() => {
        'type': type,
        'valeur': valeur,
        if (type == 'commande') 'shell': shell,
        if (type == 'commande') 'visible': visible,
      };
}

/// Un raccourci : une suite d'étapes lancée d'un seul appui (Phase 7).
class Raccourci {
  final String nom;
  final String icone;
  final List<Etape> etapes;

  const Raccourci(this.nom, this.icone, this.etapes);

  static Raccourci depuis(dynamic e) {
    final m = e is Map ? e : const {};
    final brutes = m['etapes'];
    return Raccourci(
      (m['nom'] ?? '').toString(),
      (m['icone'] ?? 'eclair').toString(),
      brutes is List ? brutes.map(Etape.depuis).toList() : const [],
    );
  }

  Map<String, dynamic> versJson() => {
        'nom': nom,
        'icone': icone,
        'etapes': etapes.map((e) => e.versJson()).toList(),
      };
}

class Connexion extends ChangeNotifier {
  String adresse = '';
  String? _token;
  Statut statut = Statut.sansAdresse;
  EtatPC etat = EtatPC.vide();
  List<AppPc> apps = [];
  List<Raccourci> raccourcis = [];
  /// Favoris (Accueil + widget) : « app:Nom », « rac:Nom » ou « cmd:LIGNE ».
  List<String> favoris = [];
  String message = '';
  int numeroMessage = 0; // change à chaque nouveau message (pour afficher une notification)
  bool pinAffiche = false;
  DateTime derniereAction = DateTime.fromMillisecondsSinceEpoch(0);

  /// Aperçu de l'écran du PC (Phase 8) : à part, pour ne pas redessiner toute l'app à chaque image.
  final ValueNotifier<Uint8List?> apercuImage = ValueNotifier(null);
  final ValueNotifier<Map<String, dynamic>> apercuInfos = ValueNotifier(const {});

  /// Appelé quand les favoris, l'adresse ou l'appairage changent (mise à jour du widget).
  VoidCallback? surFavoris;

  WebSocketChannel? _canal;
  StreamSubscription<dynamic>? _abonnement;
  Timer? _reconnexion;
  Timer? _minuterieSouris;
  double _dx = 0;
  double _dy = 0;
  bool _authEnvoyee = false;
  bool _fini = false;
  int _echecs = 0;
  DateTime _dernierEtat = DateTime.fromMillisecondsSinceEpoch(0);
  AppLifecycleListener? _cycle;
  final Map<String, Completer<(bool, String)>> _attentes = {};

  /// Phase 11 : données de l'onglet Master et de la page « Mes jeux » (null = pas encore reçues).
  Map<String, dynamic>? master;
  Map<String, dynamic>? jeux;
  Map<String, dynamic>? historique; // Phase 14 : historique de jeu par jour
  Map<String, dynamic>? sites; // Phase 11-bis
  int _masterV = -1;

  bool get appaire => _token != null;
  bool get connecte => statut == Statut.connecte;
  String? get token => _token;

  Future<void> charger() async {
    // retour sur l'app : on se reconnecte tout de suite si la liaison est morte en arrière-plan
    _cycle ??= AppLifecycleListener(onResume: _auRetour);
    final p = await SharedPreferences.getInstance();
    adresse = p.getString('adresse') ?? '';
    _token = p.getString('token');
    favoris = p.getStringList('favoris') ?? [];
    statut = adresse.isEmpty ? Statut.sansAdresse : Statut.deconnecte;
    notifyListeners();
    favorisChanges();
    if (adresse.isNotEmpty) connecter();
  }

  Future<void> changerAdresse(String nouvelle) async {
    adresse = nouvelle.trim();
    final p = await SharedPreferences.getInstance();
    await p.setString('adresse', adresse);
    favorisChanges();
    connecter();
  }

  Future<void> oublierAppairage() async {
    _token = null;
    final p = await SharedPreferences.getInstance();
    await p.remove('token');
    favorisChanges();
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

  void _auRetour() {
    if (adresse.isEmpty) return;
    final silence = DateTime.now().difference(_dernierEtat);
    if (statut != Statut.connecte || silence > const Duration(seconds: 2)) {
      _echecs = 0;
      connecter();
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
    for (final c in _attentes.values) {
      if (!c.isCompleted) c.complete((false, 'Connection to the PC lost'));
    }
    _attentes.clear();
    if (_fini) return;
    if (statut != Statut.sansAdresse) {
      statut = Statut.deconnecte;
      etat = EtatPC.vide();
      notifyListeners();
    }
    _reconnexion?.cancel();
    // premier essai très vite (coupure brève), puis toutes les 3 s
    _echecs++;
    _reconnexion = Timer(Duration(milliseconds: _echecs <= 1 ? 500 : 3000), connecter);
  }

  /// Messages binaires : images de l'aperçu de l'écran.
  void recevoirBinaire(Uint8List octets) => apercuImage.value = octets;

  void _recevoir(dynamic brut) {
    if (brut is List<int>) {
      recevoirBinaire(brut is Uint8List ? brut : Uint8List.fromList(brut));
      return;
    }
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
          SharedPreferences.getInstance().then((p) async {
            await p.setString('token', token);
            favorisChanges();
          });
        }
        statut = Statut.connecte;
        _echecs = 0;
        pinAffiche = false;
        _envoyer({'type': 'apps'});
        _envoyer({'type': 'raccourcis'});
        _envoyer({'type': 'master'});
        // Phase 14-bis : le PC vient (re)devenir joignable : il retrouve tout de suite l'état de la clim
        ClimPlan.publier();
      case 'erreur':
        if (_authEnvoyee && statut != Statut.connecte) {
          // le PC ne reconnaît plus ce téléphone : il faut refaire l'appairage
          _token = null;
          _authEnvoyee = false;
          SharedPreferences.getInstance().then((p) => p.remove('token'));
          statut = Statut.appairage;
        }
        _annoncer((m['texte'] ?? 'Error').toString());
      case 'pin_affiche':
        pinAffiche = true;
      case 'etat':
        etat = EtatPC.depuisJson(m);
        _dernierEtat = DateTime.now();
        if (etat.masterV != _masterV) {
          _masterV = etat.masterV;
          _envoyer({'type': 'master'});
        }
      case 'rep':
        final ligne = (m['ligne'] ?? '').toString();
        final texte = (m['texte'] ?? '').toString();
        final attente = _attentes.remove(ligne);
        if (attente != null && !attente.isCompleted) {
          attente.complete((m['ok'] != false, texte));
        }
        _annoncer(texte);
      case 'apps':
        final liste = m['apps'];
        if (liste is List) apps = liste.map(AppPc.depuis).where((a) => a.nom.isNotEmpty).toList();
        favorisChanges(); // noms et icônes à jour dans le widget
      case 'raccourcis':
        final liste = m['raccourcis'];
        if (liste is List) {
          raccourcis = liste.map(Raccourci.depuis).where((r) => r.nom.isNotEmpty).toList();
        }
        favorisChanges();
      default:
        if (!recevoirAutre(m)) return;
    }
    notifyListeners();
  }

  /// Autres messages. Renvoie true si l'écran doit être redessiné.
  bool recevoirAutre(Map<String, dynamic> m) {
    switch (m['type']) {
      case 'apercu_info':
        apercuInfos.value = Map<String, dynamic>.from(m);
      case 'apercu_erreur':
        apercuInfos.value = {'erreur': (m['texte'] ?? 'Preview failed').toString()};
      case 'master':
        master = Map<String, dynamic>.from(m);
        return true;
      case 'sites':
        sites = Map<String, dynamic>.from(m);
        return true;
      case 'jeux':
        jeux = Map<String, dynamic>.from(m);
        return true;
      case 'historique':
        historique = Map<String, dynamic>.from(m);
        return true;
    }
    return false;
  }

  // ------------------------------------------------------------- aperçu de l'écran
  void demanderApercu({int ecran = 0, int largeur = 960, int qualite = 60}) =>
      _envoyer({'type': 'apercu', 'ecran': ecran, 'largeur': largeur, 'qualite': qualite});

  /// Place la souris à (x, y) (de 0 à 1) sur l'écran choisi, puis clique si [clic] n'est pas vide.
  void pointeur(int ecran, double x, double y, String clic) {
    derniereAction = DateTime.now();
    _envoyer({'type': 'pointeur', 'ecran': ecran, 'x': x, 'y': y, 'clic': clic});
  }

  void _annoncer(String texte) {
    if (texte.isEmpty) return;
    message = texte;
    numeroMessage++;
  }

  void annoncer(String texte) {
    _annoncer(texte);
    notifyListeners();
  }

  void envoyer(Map<String, dynamic> m) => _envoyer(m);

  void _envoyer(Map<String, dynamic> m) {
    final canal = _canal;
    if (canal == null) return;
    try {
      canal.sink.add(jsonEncode(m));
    } catch (_) {}
  }

  /// Envoie [m] et attend la réponse « rep » du PC (ok, texte).
  Future<(bool, String)> _demander(Map<String, dynamic> m) {
    final cle = m['type'] as String;
    final ancienne = _attentes.remove(cle);
    if (ancienne != null && !ancienne.isCompleted) {
      ancienne.complete((false, 'Replaced by a new request'));
    }
    final c = Completer<(bool, String)>();
    _attentes[cle] = c;
    if (_canal == null) {
      _attentes.remove(cle);
      return Future.value((false, 'PC not connected'));
    }
    _envoyer(m);
    return c.future.timeout(const Duration(seconds: 6), onTimeout: () {
      _attentes.remove(cle);
      return (false, 'The PC is not responding');
    });
  }

  // ------------------------------------------------------------- master et jeux (Phase 11)
  void demanderMaster() => _envoyer({'type': 'master'});

  Future<(bool, String)> majMaster(Map<String, dynamic> changements) =>
      _demander({'type': 'master_maj', 'master': changements});

  Future<(bool, String)> afficherMaster() => _demander({'type': 'master_afficher'});

  void demanderJeux() => _envoyer({'type': 'jeux'});

  void demanderHistorique() => _envoyer({'type': 'historique'});

  Future<(bool, String)> majJeux(List<String> jeux, List<String> pasDesJeux) =>
      _demander({'type': 'jeux_maj', 'jeux': jeux, 'pas_des_jeux': pasDesJeux});

  Future<(bool, String)> pasUnJeu() => _demander({'type': 'pas_un_jeu'});

  void demanderSites() => _envoyer({'type': 'sites'});

  Future<(bool, String)> majSites(List<Map<String, String>> liste) =>
      _demander({'type': 'sites_maj', 'sites': liste});

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

  /// Ajoute une app sur le PC. [sorte] : 'web' (lien) ou 'chemin' (fichier / programme Windows).
  Future<(bool, String)> ajouterApp(String nom, String cible, String sorte, {String ancien = ''}) async {
    nom = nom.trim();
    if (ancien.isNotEmpty && ancien.toLowerCase() != nom.toLowerCase()) {
      final r = await _demander({'type': 'app_retrait', 'nom': ancien});
      if (!r.$1) return r;
      _renommerFavori('app:$ancien', 'app:$nom');
    }
    return _demander({'type': 'app_ajout', 'nom': nom, 'cible': cible.trim(), 'sorte': sorte});
  }

  Future<(bool, String)> retirerApp(String nom) async {
    final r = await _demander({'type': 'app_retrait', 'nom': nom});
    if (r.$1) _renommerFavori('app:$nom', null);
    return r;
  }

  // ------------------------------------------------------------- raccourcis
  void lancerRaccourci(String nom) => cmd('RAC $nom');

  Future<(bool, String)> enregistrerRaccourci(Raccourci r, {String ancien = ''}) async {
    final res = await _demander({'type': 'rac_ajout', 'raccourci': r.versJson(), 'ancien': ancien});
    if (res.$1 && ancien.isNotEmpty) _renommerFavori('rac:$ancien', 'rac:${r.nom}');
    return res;
  }

  Future<(bool, String)> retirerRaccourci(String nom) async {
    final r = await _demander({'type': 'rac_retrait', 'nom': nom});
    if (r.$1) _renommerFavori('rac:$nom', null);
    return r;
  }

  // ------------------------------------------------------------- favoris
  bool estFavori(String id) => favoris.contains(id);

  void basculerFavori(String id) {
    if (favoris.contains(id)) {
      favoris.remove(id);
    } else {
      favoris.add(id);
    }
    _sauverFavoris();
  }

  void deplacerFavori(int ancien, int nouveau) {
    if (ancien < 0 || ancien >= favoris.length) return;
    final id = favoris.removeAt(ancien);
    favoris.insert(nouveau < 0 ? 0 : (nouveau > favoris.length ? favoris.length : nouveau), id);
    _sauverFavoris();
  }

  void _renommerFavori(String ancien, String? nouveau) {
    final i = favoris.indexWhere((f) => f.toLowerCase() == ancien.toLowerCase());
    if (i < 0) return;
    if (nouveau == null) {
      favoris.removeAt(i);
    } else {
      favoris[i] = nouveau;
    }
    _sauverFavoris();
  }

  void _sauverFavoris() {
    notifyListeners();
    SharedPreferences.getInstance().then((p) async {
      await p.setStringList('favoris', favoris);
      favorisChanges();
    });
  }

  void favorisChanges() => surFavoris?.call();

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
    _cycle?.dispose();
    _reconnexion?.cancel();
    _minuterieSouris?.cancel();
    _fermerCanal();
    apercuImage.dispose();
    apercuInfos.dispose();
    super.dispose();
  }
}
