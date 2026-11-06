// Phase 14 : lecture et agrégation de l'historique de jeu.
import 'package:esp_micro/historique.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> exemple() => {
  'aujourdhui': '2026-11-06',
  'jours': [
    {
      'date': '2026-11-06',
      's': 5400,
      'jeux': [
        {
          'nom': 'Jeu A',
          's': 3600,
          'sessions': 2,
          'fps': {'min': 30, 'moy': 60, 'max': 90, 'n': 100},
          'cpu': {'moy': 60, 'max': 70, 'n': 100},
          'gpu': {'moy': 70, 'max': 80, 'n': 100},
          'charge': {'moy': 90, 'n': 100},
          'ram': {'moy': 50, 'n': 100},
        },
        {'nom': 'Jeu B', 's': 1800, 'sessions': 1},
      ],
    },
    {
      'date': '2026-11-04',
      's': 7200,
      'jeux': [
        {
          'nom': 'Jeu A',
          's': 7200,
          'sessions': 1,
          'fps': {'min': 20, 'moy': 90, 'max': 144, 'n': 300},
          'cpu': {'moy': 80, 'max': 85, 'n': 300},
          'gpu': {'moy': 60, 'max': 90, 'n': 300},
        },
      ],
    },
  ],
};

void main() {
  test('lecture du message historique', () {
    final h = HistoriqueJeux.depuisJson(exemple());
    expect(h.aujourdhui, '2026-11-06');
    expect(h.jours.length, 2);
    expect(h.jours.first.secondes, 5400);
    expect(h.jours.first.jeux.first.fps!.moy, 60);
    expect(h.jours.first.jeux.last.fps, isNull); // pas de mesure : null, pas 0
    expect(h.jours.first.jeux.last.cpu, isNull);
  });

  test('message vide ou abîmé : pas de plantage', () {
    expect(HistoriqueJeux.depuisJson({}).jours, isEmpty);
    final h = HistoriqueJeux.depuisJson({
      'jours': [
        'x',
        {'date': '2026-11-06', 'jeux': 3},
      ],
    });
    expect(h.jours.length, 1);
    expect(h.jours.first.jeux, isEmpty);
  });

  test('vue par titre : totaux et moyennes pondérées', () {
    final titres = HistoriqueJeux.depuisJson(exemple()).parTitre();
    expect(titres.map((t) => t.nom), [
      'Jeu A',
      'Jeu B',
    ]); // du plus joué au moins joué
    final a = titres.first;
    expect(a.secondes, 10800);
    expect(a.sessions, 3);
    expect(a.nbJours, 2);
    expect(a.fps!.min, 20);
    expect(a.fps!.max, 144);
    expect(a.fps!.moy, 83); // (60*100 + 90*300) / 400 = 82,5
    expect(a.fps!.n, 400);
    expect(a.cpu!.moy, 75); // (60*100 + 80*300) / 400
    expect(a.cpu!.max, 85);
    expect(a.gpu!.max, 90);
    expect(a.charge!.moy, 90); // un seul jour avec cette mesure
    expect(a.ram!.moy, 50);
    expect(titres.last.fps, isNull);
  });

  test('séries de jours pour les barres (7 et 30 jours)', () {
    final h = HistoriqueJeux.depuisJson(exemple());
    final sept = h.serie(7);
    expect(sept.length, 7);
    expect(sept.last, 5400); // aujourd'hui en dernier
    expect(sept[4], 7200); // 4 novembre = il y a 2 jours
    expect(sept[5], 0); // 5 novembre : rien
    expect(h.serie(30).length, 30);
    expect(h.serie(30).reduce((a, b) => a + b), 12600);
    // un seul jeu
    expect(h.serie(7, titre: 'Jeu B').last, 1800);
    expect(h.serie(7, titre: 'Jeu B')[4], 0);
  });

  test('série à cheval sur deux mois', () {
    final h = HistoriqueJeux.depuisJson({
      'aujourdhui': '2026-03-02',
      'jours': [
        {'date': '2026-02-28', 's': 600, 'jeux': []},
      ],
    });
    final s = h.serie(5);
    expect(s, [
      0,
      0,
      600,
      0,
      0,
    ]); // 26/02 27/02 28/02 01/03 02/03 -> 28/02 est en 3e position
  });

  test('durées affichées', () {
    expect(dureeSecondes(42), '42 s');
    expect(dureeSecondes(600), '10 min');
    expect(dureeSecondes(3725), '1h 02');
    expect(dureeSecondes(7200), '2h 00');
  });
}
