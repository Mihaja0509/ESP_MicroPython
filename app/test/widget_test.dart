import 'package:esp_micro/actions.dart';
import 'package:esp_micro/connexion.dart';
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
    expect(e.arretPrevu, isFalse); // ancien programme PC : pas de champ « arret »
    expect(e.ecrans, 1);
  });

  test('état vide', () {
    final e = EtatPC.vide();
    expect(e.recu, isFalse);
    expect(e.enJeu, isFalse);
    expect(e.ecranNoir, isFalse);
  });

  test('Phase 7 : arrêt, écran noir, luminosité de l\'ESP32', () {
    final e = EtatPC.depuisJson({'arret': 42, 'ecran_noir': true, 'lum_esp': 60, 'ecrans': 2});
    expect(e.arretPrevu, isTrue);
    expect(e.arret, 42);
    expect(e.ecranNoir, isTrue);
    expect(e.lumEsp, 60);
    expect(e.ecrans, 2);
  });

  test('raccourci : aller-retour JSON', () {
    final r = Raccourci.depuis({
      'nom': 'Prépa jeu',
      'icone': 'jeu',
      'etapes': [
        {'type': 'commande', 'valeur': 'Get-Date', 'shell': 'powershell', 'visible': false},
        {'type': 'touches', 'valeur': 'ctrl+6'},
      ],
    });
    expect(r.etapes.length, 2);
    expect(r.etapes.first.visible, isFalse);
    final j = r.versJson();
    expect(j['nom'], 'Prépa jeu');
    expect((j['etapes'] as List).last, {'type': 'touches', 'valeur': 'ctrl+6'});
  });

  test('Phase 8 : infos de l\'aperçu de l\'écran', () {
    final cx = Connexion();
    cx.recevoirAutre({'type': 'apercu_info', 'ecran': 1, 'ecrans': 2, 'largeur': 2560, 'hauteur': 1600});
    expect(cx.apercuInfos.value['ecrans'], 2);
    cx.recevoirAutre({'type': 'apercu_erreur', 'texte': 'Capture impossible'});
    expect(cx.apercuInfos.value['erreur'], 'Capture impossible');
    cx.dispose();
  });

  test('favoris : retrouvés même hors ligne', () {
    final cx = Connexion();
    expect(resoudre(cx, 'cmd:PLAY').nom, 'Lecture / pause');
    expect(resoudre(cx, 'app:netflix').ligne, 'APP netflix');
    expect(resoudre(cx, 'rac:Prépa jeu').ligne, 'RAC Prépa jeu');
    cx.dispose();
  });
}
