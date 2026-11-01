// Adresse du PC, appairage avec le code affiché sur l'ESP32, aide Tailscale.
import 'package:flutter/material.dart';

import '../connexion.dart';
import '../theme.dart';

class EcranReglages extends StatefulWidget {
  final Connexion cx;

  const EcranReglages({super.key, required this.cx});

  @override
  State<EcranReglages> createState() => _EcranReglagesState();
}

class _EcranReglagesState extends State<EcranReglages> {
  late final TextEditingController _adresse;
  final _pin = TextEditingController();

  Connexion get cx => widget.cx;

  @override
  void initState() {
    super.initState();
    _adresse = TextEditingController(text: cx.adresse);
  }

  @override
  void dispose() {
    _adresse.dispose();
    _pin.dispose();
    super.dispose();
  }

  String get _texteStatut => switch (cx.statut) {
        Statut.sansAdresse => 'Aucune adresse',
        Statut.deconnecte => 'PC injoignable (nouvel essai toutes les 3 s)',
        Statut.connexion => 'Connexion…',
        Statut.appairage => 'Connecté, appairage nécessaire',
        Statut.connecte => 'Connecté et appairé',
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
              const Titre('Adresse du PC', icone: Icons.computer_rounded),
              TextField(
                controller: _adresse,
                keyboardType: TextInputType.url,
                decoration: const InputDecoration(
                  hintText: 'ex. 100.101.102.103 (adresse Tailscale du PC)',
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
                    child: const Text('Se connecter'),
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
              const Titre('Appairage', icone: Icons.verified_user_rounded),
              if (cx.statut == Statut.appairage) ...[
                const Text(
                  "Pour que personne d'autre ne puisse commander ton PC, ce téléphone doit être "
                  "appairé une fois avec un code affiché sur l'écran de l'ESP32.",
                  style: TextStyle(color: Couleurs.doux),
                ),
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  icon: const Icon(Icons.pin_rounded),
                  label: Text(cx.pinAffiche ? 'Nouveau code' : "Afficher le code sur l'ESP32"),
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
                            hintText: 'Code à 6 chiffres',
                            border: OutlineInputBorder(),
                            isDense: true,
                            counterText: '',
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      FilledButton(
                        onPressed: () {
                          cx.envoyerPin(_pin.text, 'Téléphone de Mihaja');
                          _pin.clear();
                        },
                        child: const Text('Valider'),
                      ),
                    ],
                  ),
                ],
              ] else if (cx.appaire)
                Row(
                  children: [
                    const Icon(Icons.check_circle_rounded, color: Couleurs.vert),
                    const SizedBox(width: 8),
                    const Expanded(child: Text('Ce téléphone est appairé.')),
                    TextButton(onPressed: cx.oublierAppairage, child: const Text('Oublier')),
                  ],
                )
              else
                const Text("Connecte-toi d'abord au PC.", style: TextStyle(color: Couleurs.gris)),
            ],
          ),
        ),
        const SizedBox(height: 14),
        const Carte(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Titre('Depuis n\'importe où', icone: Icons.public_rounded),
              Text(
                '1. Installe Tailscale sur le PC et sur ce téléphone, avec le même compte.\n'
                '2. Dans Tailscale sur le PC, copie l\'adresse du PC (elle commence par 100.).\n'
                '3. Mets cette adresse ci-dessus : l\'app marche alors à la maison, en 4G, partout.\n'
                '4. À la maison sans Tailscale, l\'adresse locale du PC (192.168…) marche aussi.',
                style: TextStyle(color: Couleurs.doux, height: 1.5),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
