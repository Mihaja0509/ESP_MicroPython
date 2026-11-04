// Cartes contextuelles de l'Accueil (Phase 11) :
// - « Cinéma » pendant une vidéo (YouTube, Netflix, Anime-Sama, VLC…) : télécommande adaptée ;
// - « PC inutilisé » après 30 min sans clavier ni souris : éteindre, écran noir, verrouiller.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../connexion.dart';
import '../etat.dart';
import '../theme.dart';
import '../ecrans/master.dart' show duree;

const _couleurs = {
  'YouTube': Color(0xFFFF4646),
  'Netflix': Color(0xFFE51E28),
  'VLC': Color(0xFFFF961E),
  'Anime-Sama': Color(0xFF5AAAFF),
  'Crunchyroll': Color(0xFFFF8228),
  'Twitch': Color(0xFFAA6EFF),
  'Prime Video': Color(0xFF28AAFF),
  'Disney+': Color(0xFF5A8CFF),
};

/// Touches de chaque lecteur : (reculer, avancer, plein écran, sous-titres ou null).
(String, String, String, String?) _touches(String source) => switch (source) {
      'YouTube' => ('j', 'l', 'f', 'c'),
      'VLC' => ('alt+left', 'alt+right', 'f', 'v'),
      'MPC' || 'PotPlayer' => ('left', 'right', 'enter', null),
      _ => ('left', 'right', 'f', null),
    };

/// 152 -> « 02:32 » ; 3752 -> « 1:02:32 »
String _temps(int s) {
  String deux(int n) => n.toString().padLeft(2, '0');
  return s >= 3600 ? '${s ~/ 3600}:${deux(s ~/ 60 % 60)}:${deux(s % 60)}' : '${deux(s ~/ 60)}:${deux(s % 60)}';
}

class CarteCinema extends StatelessWidget {
  final Connexion cx;
  final EtatPC etat;

  const CarteCinema({super.key, required this.cx, required this.etat});

  void _touche(String t) {
    HapticFeedback.selectionClick();
    cx.cmd('TOUCHES $t');
  }

  @override
  Widget build(BuildContext context) {
    final couleur = _couleurs[etat.video] ?? Couleurs.orange;
    final (recul, avance, plein, sousTitres) = _touches(etat.video);
    final dix = etat.video == 'YouTube' || etat.video == 'Netflix' || etat.video == 'VLC';
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF2A0610), Color(0xFF10060C)],
        ),
        border: Border.all(color: couleur.withValues(alpha: 0.7)),
        boxShadow: [BoxShadow(color: couleur.withValues(alpha: 0.25), blurRadius: 18)],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.play_arrow_rounded, color: couleur, size: 22),
              const SizedBox(width: 4),
              Text(etat.video, style: TextStyle(color: couleur, fontWeight: FontWeight.w800, fontSize: 15)),
              const Spacer(),
              const Icon(Icons.local_movies_rounded, color: Couleurs.gris, size: 18),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            etat.videoTitre.isEmpty ? 'Enjoy the show!' : etat.videoTitre,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700, color: Colors.white),
          ),
          if (etat.videoDuree > 0) ...[
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: (etat.videoPos / etat.videoDuree).clamp(0.0, 1.0),
                minHeight: 5,
                color: etat.videoLecture ? couleur : Couleurs.orange,
                backgroundColor: Colors.white.withValues(alpha: 0.1),
              ),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Text(_temps(etat.videoPos), style: const TextStyle(fontSize: 12, color: Colors.white)),
                const Spacer(),
                if (!etat.videoLecture)
                  const Text('Pause', style: TextStyle(fontSize: 12, color: Couleurs.orange)),
                const Spacer(),
                Text(_temps(etat.videoDuree), style: const TextStyle(fontSize: 12, color: Couleurs.gris)),
              ],
            ),
          ],
          const SizedBox(height: 14),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _rond(dix ? Icons.replay_10_rounded : Icons.fast_rewind_rounded, () => _touche(recul)),
              _rond(Icons.play_arrow_rounded, () => cx.cmd('PLAY'), grand: true, couleur: couleur,
                  icone2: Icons.pause_rounded),
              _rond(dix ? Icons.forward_10_rounded : Icons.fast_forward_rounded, () => _touche(avance)),
            ],
          ),
          const SizedBox(height: 12),
          GrilleBoutons(
            colonnes: 4,
            espace: 8,
            enfants: [
              BoutonAction(icone: Icons.volume_down_rounded, texte: 'Vol -', onTap: () => cx.cmd('VOL-')),
              BoutonAction(icone: Icons.volume_up_rounded, texte: 'Vol +', onTap: () => cx.cmd('VOL+')),
              BoutonAction(icone: Icons.fullscreen_rounded, texte: 'Full screen', onTap: () => _touche(plein)),
              if (sousTitres != null)
                BoutonAction(icone: Icons.subtitles_rounded, texte: 'Subtitles', onTap: () => _touche(sousTitres))
              else
                BoutonAction(icone: Icons.skip_next_rounded, texte: 'Next', onTap: () => cx.cmd('NEXT')),
            ],
          ),
        ],
      ),
    );
  }

  Widget _rond(IconData icone, VoidCallback onTap, {bool grand = false, Color? couleur, IconData? icone2}) {
    final taille = grand ? 64.0 : 50.0;
    return Material(
      color: (couleur ?? Colors.white).withValues(alpha: grand ? 0.9 : 0.1),
      shape: const CircleBorder(),
      child: InkWell(
        customBorder: const CircleBorder(),
        onTap: onTap,
        child: SizedBox(
          width: taille,
          height: taille,
          child: icone2 == null
              ? Icon(icone, color: Colors.white, size: grand ? 34 : 26)
              : Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(icone, color: Colors.white, size: 22),
                    Icon(icone2, color: Colors.white, size: 22),
                  ],
                ),
        ),
      ),
    );
  }
}

class CartePcInutilise extends StatelessWidget {
  final Connexion cx;
  final int minutes;

  const CartePcInutilise({super.key, required this.cx, required this.minutes});

  @override
  Widget build(BuildContext context) {
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.bedtime_rounded, color: Couleurs.orange, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text('PC idle for ${duree(minutes)}',
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Text('Nobody has touched the keyboard or mouse. Shut it down?',
              style: TextStyle(color: Couleurs.doux, fontSize: 13)),
          const SizedBox(height: 12),
          GrilleBoutons(
            colonnes: 3,
            espace: 8,
            enfants: [
              BoutonAction(
                icone: Icons.power_settings_new_rounded,
                texte: 'Shut down',
                couleur: Couleurs.rouge,
                onTap: () async {
                  final ok = await confirmer(context, 'Shut down the PC?',
                      'The PC shuts down in 60 s (you can cancel from the app).',
                      bouton: 'Shut down', couleur: Couleurs.rouge);
                  if (ok) cx.cmd('ARRET');
                },
              ),
              BoutonAction(
                  icone: Icons.desktop_access_disabled_rounded,
                  texte: 'Black screen',
                  onTap: () => cx.cmd('ECRAN_OFF')),
              BoutonAction(icone: Icons.lock_rounded, texte: 'Lock', onTap: () => cx.cmd('VERROU')),
            ],
          ),
        ],
      ),
    );
  }
}
