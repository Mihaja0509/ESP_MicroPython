// Phase 14 : conversions du minuteur heures / minutes / secondes.
import 'package:esp_micro/clim_plan.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('h / min / s -> secondes', () {
    expect(dureeEnSecondes(0, 0, 1), 1);
    expect(dureeEnSecondes(0, 15, 0), 900);
    expect(dureeEnSecondes(1, 0, 0), 3600);
    expect(dureeEnSecondes(2, 30, 15), 9015);
    expect(dureeEnSecondes(24, 0, 0), minuteurMax);
  });

  test('secondes -> h / min / s (aller-retour)', () {
    for (final s in [1, 59, 60, 61, 3599, 3600, 3661, 9015, 86399, 86400]) {
      final d = secondesEnHms(s);
      expect(dureeEnSecondes(d.h, d.m, d.s), s);
      expect(d.m, lessThan(60));
      expect(d.s, lessThan(60));
    }
    expect(secondesEnHms(3661), (h: 1, m: 1, s: 1));
    expect(secondesEnHms(-5), (h: 0, m: 0, s: 0));
  });

  test('affichage h:mm:ss', () {
    expect(formaterReste(1), '0:00:01');
    expect(formaterReste(75), '0:01:15');
    expect(formaterReste(3661), '1:01:01');
    expect(formaterReste(86400), '24:00:00');
  });

  test('saisie : champs vides, trop grands, total limité à 24 h', () {
    expect(limiterHms('', '', ''), (h: 0, m: 0, s: 0));
    expect(limiterHms('abc', '5', ''), (h: 0, m: 5, s: 0));
    expect(limiterHms('1', '99', '99'), (h: 1, m: 59, s: 59));
    expect(limiterHms('24', '0', '0'), (h: 24, m: 0, s: 0));
    expect(limiterHms('24', '1', '0'), (h: 24, m: 0, s: 0)); // dépasse 24 h
    expect(limiterHms('99', '0', '0'), (h: 24, m: 0, s: 0));
    expect(limiterHms('0', '0', '30'), (h: 0, m: 0, s: 30));
  });

  test('validation : minimum 1 seconde, maximum 24 h', () {
    expect(verifierDuree(0), isNotNull);
    expect(verifierDuree(1), isNull);
    expect(verifierDuree(86400), isNull);
    expect(verifierDuree(86401), isNotNull);
  });
}
