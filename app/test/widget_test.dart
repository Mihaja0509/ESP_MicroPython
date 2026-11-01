import 'package:esp_micro/etat.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('lecture de l\'état envoyé par le PC', () {
    final e = EtatPC.depuisJson({
      'cpu': 23,
      'ram': 61,
      'fps': 104,
      'jeu': 'God of War Ragnarok',
      'casque': 'HECATE G30',
      'manette': true,
      'meteo': [
        {'icone': 'orage', 'tmax': 32, 'tmin': 24, 'pluie': 80, 'heure': 15},
      ],
    });
    expect(e.cpu, 23);
    expect(e.enJeu, isTrue);
    expect(e.gpuTemp, -1);
    expect(e.meteo.first.textePluie, 'Pluie 80 % vers 15 h');
  });

  test('état vide', () {
    final e = EtatPC.vide();
    expect(e.recu, isFalse);
    expect(e.enJeu, isFalse);
  });
}
