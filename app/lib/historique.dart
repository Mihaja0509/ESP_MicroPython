// Historique de jeu (Phase 14) : lecture du message « historique » envoyé par l'agent PC et
// agrégations (par titre, séries de jours). Pas de widget ici : tout est testable.

class PlageFps {
  final int min, moy, max, n;

  const PlageFps(this.min, this.moy, this.max, this.n);
}

class MesureTemp {
  final int moy, max, n;

  const MesureTemp(this.moy, this.max, this.n);
}

class MesureMoy {
  final int moy, n;

  const MesureMoy(this.moy, this.n);
}

int _entier(dynamic v, [int defaut = 0]) => v is num ? v.round() : defaut;

PlageFps? _plage(dynamic v) {
  if (v is! Map) return null;
  return PlageFps(
    _entier(v['min']),
    _entier(v['moy']),
    _entier(v['max']),
    _entier(v['n'], 1),
  );
}

MesureTemp? _temp(dynamic v) {
  if (v is! Map) return null;
  return MesureTemp(_entier(v['moy']), _entier(v['max']), _entier(v['n'], 1));
}

MesureMoy? _moy(dynamic v) {
  if (v is! Map) return null;
  return MesureMoy(_entier(v['moy']), _entier(v['n'], 1));
}

/// Un jeu, un jour.
class JeuJour {
  final String nom;
  final int secondes;
  final int sessions;
  final PlageFps? fps;
  final MesureTemp? cpu;
  final MesureTemp? gpu;
  final MesureMoy? charge;
  final MesureMoy? ram;

  const JeuJour({
    required this.nom,
    required this.secondes,
    this.sessions = 0,
    this.fps,
    this.cpu,
    this.gpu,
    this.charge,
    this.ram,
  });

  factory JeuJour.depuisJson(Map m) => JeuJour(
    nom: (m['nom'] ?? '').toString(),
    secondes: _entier(m['s']),
    sessions: _entier(m['sessions']),
    fps: _plage(m['fps']),
    cpu: _temp(m['cpu']),
    gpu: _temp(m['gpu']),
    charge: _moy(m['charge']),
    ram: _moy(m['ram']),
  );
}

/// Un jour : total (tous jeux) et détail de chaque jeu.
class Jour {
  final String date; // 2026-11-06
  final int secondes;
  final List<JeuJour> jeux;

  const Jour({required this.date, required this.secondes, required this.jeux});
}

/// Un jeu sur tous les jours (vue « par titre »).
class Titre {
  final String nom;
  final int secondes;
  final int sessions;
  final int nbJours;
  final PlageFps? fps;
  final MesureTemp? cpu;
  final MesureTemp? gpu;
  final MesureMoy? charge;
  final MesureMoy? ram;
  final List<(String, JeuJour)> jours; // du plus récent au plus ancien

  const Titre({
    required this.nom,
    required this.secondes,
    required this.sessions,
    required this.nbJours,
    required this.fps,
    required this.cpu,
    required this.gpu,
    required this.charge,
    required this.ram,
    required this.jours,
  });
}

// ---------------------------------------------------------------- fusion de mesures
/// Moyenne pondérée par le nombre d'échantillons.
int _pondere(Iterable<(int, int)> valeurs) {
  var somme = 0.0;
  var n = 0;
  for (final (v, k) in valeurs) {
    somme += v * k;
    n += k;
  }
  return n == 0 ? 0 : (somme / n).round();
}

PlageFps? fusionnerFps(Iterable<PlageFps?> liste) {
  final l = liste.whereType<PlageFps>().toList();
  if (l.isEmpty) return null;
  return PlageFps(
    l.map((p) => p.min).reduce((a, b) => a < b ? a : b),
    _pondere(l.map((p) => (p.moy, p.n))),
    l.map((p) => p.max).reduce((a, b) => a > b ? a : b),
    l.fold(0, (a, p) => a + p.n),
  );
}

MesureTemp? fusionnerTemp(Iterable<MesureTemp?> liste) {
  final l = liste.whereType<MesureTemp>().toList();
  if (l.isEmpty) return null;
  return MesureTemp(
    _pondere(l.map((p) => (p.moy, p.n))),
    l.map((p) => p.max).reduce((a, b) => a > b ? a : b),
    l.fold(0, (a, p) => a + p.n),
  );
}

MesureMoy? fusionnerMoy(Iterable<MesureMoy?> liste) {
  final l = liste.whereType<MesureMoy>().toList();
  if (l.isEmpty) return null;
  return MesureMoy(
    _pondere(l.map((p) => (p.moy, p.n))),
    l.fold(0, (a, p) => a + p.n),
  );
}

/// L'historique complet reçu de l'agent.
class HistoriqueJeux {
  final String aujourdhui;
  final List<Jour> jours; // du plus récent au plus ancien

  const HistoriqueJeux({required this.aujourdhui, required this.jours});

  factory HistoriqueJeux.depuisJson(Map<String, dynamic> m) {
    final jours = <Jour>[];
    for (final j in (m['jours'] is List ? m['jours'] as List : const [])) {
      if (j is! Map) continue;
      jours.add(
        Jour(
          date: (j['date'] ?? '').toString(),
          secondes: _entier(j['s']),
          jeux: [
            for (final g in (j['jeux'] is List ? j['jeux'] as List : const []))
              if (g is Map) JeuJour.depuisJson(g),
          ],
        ),
      );
    }
    return HistoriqueJeux(
      aujourdhui: (m['aujourdhui'] ?? '').toString(),
      jours: jours,
    );
  }

  /// Tous les jours de chaque jeu, du plus joué au moins joué.
  List<Titre> parTitre() {
    final noms = <String, List<(String, JeuJour)>>{};
    for (final j in jours) {
      for (final g in j.jeux) {
        noms.putIfAbsent(g.nom, () => []).add((j.date, g));
      }
    }
    final liste = <Titre>[
      for (final e in noms.entries)
        Titre(
          nom: e.key,
          secondes: e.value.fold(0, (a, p) => a + p.$2.secondes),
          sessions: e.value.fold(0, (a, p) => a + p.$2.sessions),
          nbJours: e.value.length,
          fps: fusionnerFps(e.value.map((p) => p.$2.fps)),
          cpu: fusionnerTemp(e.value.map((p) => p.$2.cpu)),
          gpu: fusionnerTemp(e.value.map((p) => p.$2.gpu)),
          charge: fusionnerMoy(e.value.map((p) => p.$2.charge)),
          ram: fusionnerMoy(e.value.map((p) => p.$2.ram)),
          jours: e.value,
        ),
    ];
    liste.sort((a, b) => b.secondes.compareTo(a.secondes));
    return liste;
  }

  /// Secondes jouées par jour sur les [nbJours] derniers jours (du plus ancien au plus récent,
  /// aujourd'hui en dernier ; 0 les jours sans jeu). [titre] limite à un jeu.
  List<int> serie(int nbJours, {String? titre}) {
    final fin = DateTime.tryParse(aujourdhui) ?? DateTime.now();
    final parDate = <String, int>{};
    for (final j in jours) {
      parDate[j.date] = titre == null
          ? j.secondes
          : j.jeux
                .where((g) => g.nom == titre)
                .fold(0, (a, g) => a + g.secondes);
    }
    return [
      for (var i = nbJours - 1; i >= 0; i--)
        parDate[dateIso(DateTime(fin.year, fin.month, fin.day - i))] ?? 0,
    ];
  }
}

String dateIso(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

/// 3725 -> « 1h 02 » ; 600 -> « 10 min » ; 42 -> « 42 s ».
String dureeSecondes(int s) {
  if (s >= 3600) {
    return '${s ~/ 3600}h ${((s % 3600) ~/ 60).toString().padLeft(2, '0')}';
  }
  if (s >= 60) return '${s ~/ 60} min';
  return '$s s';
}
