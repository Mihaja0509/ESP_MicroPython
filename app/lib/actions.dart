// Toutes les actions qu'on peut lancer d'un appui : actions du PC, apps, raccourcis.
// Servent aux tuiles de Contrôles, aux favoris de l'Accueil et au widget Android.
import 'package:flutter/material.dart';

import 'connexion.dart';
import 'theme.dart';

class ActionDadou {
  final String id; // app:Nom | rac:Nom | cmd:LIGNE
  final String nom;
  final IconData icone;
  final Color couleur;
  final String ligne; // commande envoyée au PC
  final String? confirmation; // question posée avant (veille, arrêt), sinon null
  final String code; // nom de l'icône du widget Android

  const ActionDadou({
    required this.id,
    required this.nom,
    required this.icone,
    required this.ligne,
    required this.code,
    this.couleur = Couleurs.cyan,
    this.confirmation,
  });
}

/// Actions du PC proposées dans l'onglet « PC » et comme favoris.
const List<ActionDadou> actionsPc = [
  ActionDadou(id: 'cmd:PLAY', nom: 'Lecture / pause', icone: Icons.play_arrow_rounded, ligne: 'PLAY', code: 'play'),
  ActionDadou(id: 'cmd:VOL-', nom: 'Volume −', icone: Icons.volume_down_rounded, ligne: 'VOL-', code: 'vol_moins'),
  ActionDadou(id: 'cmd:VOL+', nom: 'Volume +', icone: Icons.volume_up_rounded, ligne: 'VOL+', code: 'vol_plus'),
  ActionDadou(id: 'cmd:MUTE', nom: 'Muet', icone: Icons.volume_off_rounded, ligne: 'MUTE', code: 'muet'),
  ActionDadou(id: 'cmd:NEXT', nom: 'Suivant', icone: Icons.skip_next_rounded, ligne: 'NEXT', code: 'suivant'),
  ActionDadou(
      id: 'cmd:ECRAN_BASCULE',
      nom: 'Écran noir',
      icone: Icons.desktop_access_disabled_rounded,
      ligne: 'ECRAN_BASCULE',
      code: 'ecran'),
  ActionDadou(id: 'cmd:VERROU', nom: 'Verrouiller', icone: Icons.lock_rounded, ligne: 'VERROU', code: 'verrou'),
  ActionDadou(
      id: 'cmd:KEY win+d', nom: 'Bureau', icone: Icons.space_dashboard_rounded, ligne: 'KEY win+d', code: 'bureau'),
  ActionDadou(
      id: 'cmd:VEILLE',
      nom: 'Veille',
      icone: Icons.bedtime_rounded,
      ligne: 'VEILLE',
      code: 'veille',
      couleur: Couleurs.orange,
      confirmation: 'Le PC va se mettre en veille tout de suite. Il ne sera plus joignable '
          'depuis le téléphone avant d\'être réveillé.'),
  ActionDadou(
      id: 'cmd:ARRET',
      nom: 'Éteindre le PC',
      icone: Icons.power_settings_new_rounded,
      ligne: 'ARRET',
      code: 'power',
      couleur: Couleurs.rouge,
      confirmation: 'Le PC s\'éteindra dans 60 secondes. Tu pourras encore annuler.'),
  ActionDadou(
      id: 'cmd:ANNULER', nom: 'Annuler l\'arrêt', icone: Icons.cancel_rounded, ligne: 'ANNULER', code: 'annuler'),
];

/// Icônes possibles pour un raccourci (même liste que le programme PC).
const Map<String, IconData> iconesRaccourcis = {
  'eclair': Icons.bolt_rounded,
  'jeu': Icons.sports_esports_rounded,
  'terminal': Icons.terminal_rounded,
  'clavier': Icons.keyboard_rounded,
  'musique': Icons.music_note_rounded,
  'web': Icons.public_rounded,
  'dossier': Icons.folder_rounded,
  'etoile': Icons.star_rounded,
};

IconData iconeRaccourci(String nom) => iconesRaccourcis[nom] ?? Icons.bolt_rounded;

/// Icône d'une app selon son type et son nom (plus de fusée pour les commandes).
(IconData, String) iconeApp(AppPc a) {
  final nom = a.nom.toLowerCase();
  final cible = a.cible.toLowerCase();
  bool contient(List<String> mots) => mots.any((m) => nom.contains(m) || cible.contains(m));
  if (contient(['spotify', 'deezer', 'music', 'musique'])) return (Icons.music_note_rounded, 'musique');
  if (contient(['youtube', 'netflix', 'prime', 'disney', 'twitch'])) return (Icons.smart_display_rounded, 'web');
  if (contient(['steam', 'epic', 'jeu', 'game'])) return (Icons.sports_esports_rounded, 'jeu');
  if (contient(['calc'])) return (Icons.calculate_rounded, 'app');
  if (contient(['notepad', 'bloc-notes', 'word'])) return (Icons.description_rounded, 'app');
  if (contient(['vscode', 'code', 'terminal', 'powershell', 'cmd'])) return (Icons.terminal_rounded, 'terminal');
  if (contient(['explor', 'dossier'])) return (Icons.folder_rounded, 'dossier');
  if (a.web) return (Icons.public_rounded, 'web');
  if (a.type == 'chemin') {
    final fichier = cible.split(RegExp(r'[\\/]')).last;
    if (!fichier.contains('.')) return (Icons.folder_rounded, 'dossier');
    if (fichier.endsWith('.exe') || fichier.endsWith('.lnk')) return (Icons.desktop_windows_rounded, 'app');
    return (Icons.insert_drive_file_rounded, 'dossier');
  }
  return (Icons.widgets_rounded, 'app');
}

String majuscule(String t) => t.isEmpty ? t : t[0].toUpperCase() + t.substring(1);

ActionDadou actionApp(AppPc a) {
  final (icone, code) = iconeApp(a);
  return ActionDadou(id: 'app:${a.nom}', nom: majuscule(a.nom), icone: icone, ligne: 'APP ${a.nom}', code: code);
}

ActionDadou actionRaccourci(Raccourci r) => ActionDadou(
      id: 'rac:${r.nom}',
      nom: r.nom,
      icone: iconeRaccourci(r.icone),
      ligne: 'RAC ${r.nom}',
      code: r.icone,
      couleur: Couleurs.magenta,
    );

/// Retrouve une action à partir de son identifiant (favori). Toujours un résultat, même
/// hors ligne (on garde alors le nom et une icône simple).
ActionDadou resoudre(Connexion cx, String id) {
  if (id.startsWith('cmd:')) {
    for (final a in actionsPc) {
      if (a.id == id) return a;
    }
    final ligne = id.substring(4);
    return ActionDadou(id: id, nom: ligne, icone: Icons.bolt_rounded, ligne: ligne, code: 'eclair');
  }
  final nom = id.length > 4 ? id.substring(4) : id;
  if (id.startsWith('app:')) {
    for (final a in cx.apps) {
      if (a.nom.toLowerCase() == nom.toLowerCase()) return actionApp(a);
    }
    return ActionDadou(id: id, nom: majuscule(nom), icone: Icons.widgets_rounded, ligne: 'APP $nom', code: 'app');
  }
  for (final r in cx.raccourcis) {
    if (r.nom.toLowerCase() == nom.toLowerCase()) return actionRaccourci(r);
  }
  return ActionDadou(
      id: id, nom: nom, icone: Icons.bolt_rounded, ligne: 'RAC $nom', code: 'eclair', couleur: Couleurs.magenta);
}

List<ActionDadou> favorisResolus(Connexion cx) => [for (final id in cx.favoris) resoudre(cx, id)];

/// Lance une action (avec une question avant si elle est « dangereuse »).
Future<void> lancerAction(BuildContext context, Connexion cx, ActionDadou a) async {
  if (a.confirmation != null) {
    final ok = await confirmer(context, '${a.nom} ?', a.confirmation!);
    if (!ok) return;
  }
  cx.cmd(a.ligne);
}
