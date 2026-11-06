// Phase 14-bis : l'état de la clim affiché dans l'app vient de l'état réel, jamais d'un état figé.
import 'package:esp_micro/clim_plan.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const maintenant = 1000000;

  test('clim éteinte : jamais de compte à rebours, même si une fin traîne', () {
    expect(
      statutClim({'on': false, 'minuteurFin': 0}, maintenant),
      'AC is OFF',
    );
    expect(
      statutClim({'on': false, 'minuteurFin': maintenant + 60000}, maintenant),
      'AC is OFF',
    );
    expect(statutClim({}, maintenant), 'AC is OFF');
  });

  test('clim allumée : état et compte à rebours h:mm:ss', () {
    expect(statutClim({'on': true, 'minuteurFin': 0}, maintenant), 'AC is ON');
    expect(
      statutClim({'on': true, 'minuteurFin': maintenant + 9500}, maintenant),
      'AC is ON • off in 0:00:10',
    );
    expect(
      statutClim({'on': true, 'minuteurFin': maintenant + 3723000}, maintenant),
      'AC is ON • off in 1:02:03',
    );
  });

  test(
    'minuteur échu mais état pas encore relu : plus de compte à rebours',
    () {
      expect(
        statutClim({'on': true, 'minuteurFin': maintenant - 500}, maintenant),
        'AC is ON',
      );
    },
  );
}
