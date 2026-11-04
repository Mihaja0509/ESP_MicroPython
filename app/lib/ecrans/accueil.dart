// Écran d'accueil : la mascotte, l'état du PC (comme l'écran de l'ESP32) et les actions rapides.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../actions.dart';
import '../connexion.dart';
import '../etat.dart';
import '../theme.dart';
import '../widgets/anneau.dart';
import '../widgets/cinema.dart';
import '../widgets/mascotte.dart';
import 'jeux.dart';
import 'controles.dart' show BandeauArret;

class EcranAccueil extends StatelessWidget {
  final Connexion cx;

  const EcranAccueil({super.key, required this.cx});

  @override
  Widget build(BuildContext context) {
    final e = cx.etat;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      children: [
        _entete(e),
        const SizedBox(height: 16),
        if (!cx.connecte) _horsLigne(context) else ...[
          if (e.arretPrevu) ...[
            BandeauArret(secondes: e.arret, onAnnuler: () => cx.cmd('ANNULER')),
            const SizedBox(height: 14),
          ],
          if (e.enJeu) ...[_carteJeu(e), const SizedBox(height: 14)],
          if (e.enVideo) ...[CarteCinema(cx: cx, etat: e), const SizedBox(height: 14)],
          if (e.inactif >= 30) ...[CartePcInutilise(cx: cx, minutes: e.inactif), const SizedBox(height: 14)],
          _carteStats(e),
          const SizedBox(height: 14),
          _favoris(context),
          const SizedBox(height: 14),
          if (e.meteo.isNotEmpty) ...[_carteMeteo(e), const SizedBox(height: 14)],
          _actions(context, e),
        ],
      ],
    );
  }

  Widget _entete(EtatPC e) {
    final (texte, couleur) = !cx.connecte
        ? ('Offline', Couleurs.gris)
        : e.verrou
            ? ('PC locked', Couleurs.doux)
            : e.enJeu
                ? ('Game mode', Couleurs.magenta)
                : ('Connected', Couleurs.vert);
    final heure = TimeOfDay.now();
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Mascotte(etat: e, derniereAction: cx.derniereAction, hauteur: 175),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${heure.hour.toString().padLeft(2, '0')}:${heure.minute.toString().padLeft(2, '0')}',
                style: const TextStyle(fontSize: 44, fontWeight: FontWeight.w900, color: Colors.white, height: 1),
              ),
              const SizedBox(height: 6),
              const Text('Hello Mihaja!',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Couleurs.doux)),
              const SizedBox(height: 10),
              AnimatedContainer(
                duration: const Duration(milliseconds: 400),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: couleur.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: couleur.withValues(alpha: 0.6)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.circle, size: 9, color: couleur),
                    const SizedBox(width: 6),
                    Text(texte, style: TextStyle(color: couleur, fontWeight: FontWeight.w700)),
                  ],
                ),
              ),
              if (cx.connecte && !e.esp)
                const Padding(
                  padding: EdgeInsets.only(top: 8),
                  child: Text('ESP32 not plugged in',
                      style: TextStyle(fontSize: 12, color: Couleurs.orange)),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _horsLigne(BuildContext context) {
    final texte = switch (cx.statut) {
      Statut.sansAdresse => "Enter your PC's address in the Settings tab.",
      Statut.appairage => "This phone is not paired yet: go to Settings.",
      Statut.connexion => 'Connecting to the PC…',
      _ => 'PC unreachable. It may be off, or Tailscale is down. Retrying every 3 s.',
    };
    return Carte(
      child: Row(
        children: [
          const Icon(Icons.wifi_off_rounded, color: Couleurs.gris),
          const SizedBox(width: 12),
          Expanded(child: Text(texte, style: const TextStyle(color: Couleurs.doux))),
        ],
      ),
    );
  }

  Widget _carteJeu(EtatPC e) {
    final couleurFps = e.fps >= 60
        ? Couleurs.vert
        : e.fps >= 30
            ? Couleurs.orange
            : Couleurs.rouge;
    return Carte(
      jeu: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.sports_esports_rounded, color: Couleurs.cyan, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(e.jeu,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Couleurs.cyan, fontWeight: FontWeight.w700, fontSize: 15)),
              ),
              if (e.manette) const Icon(Icons.gamepad_rounded, color: Couleurs.magenta, size: 20),
            ],
          ),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              TweenAnimationBuilder<double>(
                tween: Tween<double>(end: e.fps < 0 ? 0.0 : e.fps.toDouble()),
                duration: const Duration(milliseconds: 400),
                builder: (context, v, _) => Text(
                  e.fps < 0 ? '--' : v.round().toString(),
                  style: TextStyle(fontSize: 72, fontWeight: FontWeight.w900, color: couleurFps, height: 1.05),
                ),
              ),
              const SizedBox(width: 8),
              const Text('FPS',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: Couleurs.magenta)),
            ],
          ),
          const SizedBox(height: 6),
          BarreTemperature(nom: 'CPU', valeur: e.cpuTemp),
          BarreTemperature(nom: 'GPU', valeur: e.gpuTemp),
        ],
      ),
    );
  }

  Widget _carteStats(EtatPC e) {
    return Carte(
      jeu: e.enJeu,
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              Anneau(valeur: e.cpu, nom: 'CPU', couleur: Couleurs.vert),
              Anneau(valeur: e.ram, nom: 'RAM', couleur: Couleurs.cyan),
              Anneau(valeur: e.gpuCharge, nom: 'GPU', couleur: Couleurs.magenta),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 8,
            alignment: WrapAlignment.center,
            // toujours les mêmes pastilles, à la même place : rien ne saute quand une valeur manque
            children: [
              _pastille(e.enCharge ? Icons.bolt_rounded : Icons.battery_std_rounded, _v(e.bat, ' %'),
                  e.bat >= 0 && e.bat < 20 && !e.enCharge ? Couleurs.rouge : Couleurs.orange),
              _pastille(Icons.volume_up_rounded, _v(e.vol, ' %'), Couleurs.cyan),
              _pastille(Icons.thermostat_rounded, 'CPU ${_v(e.cpuTemp, '°')}', Couleurs.vert),
              _pastille(Icons.memory_rounded, 'GPU ${_v(e.gpuTemp, '°')}', Couleurs.magenta),
              if (e.casque.isNotEmpty) _pastille(Icons.headphones_rounded, e.casque, Couleurs.cyan),
            ],
          ),
        ],
      ),
    );
  }

  /// Valeur affichée, ou un tiret discret si elle est inconnue.
  String _v(int valeur, String unite) => valeur >= 0 ? '$valeur$unite' : '–';

  Widget _pastille(IconData icone, String texte, Color couleur) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: couleur.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icone, size: 16, color: couleur),
          const SizedBox(width: 5),
          Text(texte, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.white)),
        ],
      ),
    );
  }

  IconData _iconeMeteo(String nom) => switch (nom) {
        'soleil' => Icons.wb_sunny_rounded,
        'eclaircie' => Icons.wb_cloudy_outlined,
        'pluie' => Icons.water_drop_rounded,
        'orage' => Icons.thunderstorm_rounded,
        'brouillard' => Icons.foggy,
        'neige' => Icons.ac_unit_rounded,
        _ => Icons.cloud_rounded,
      };

  Widget _carteMeteo(EtatPC e) {
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('Weather', icone: Icons.cloud_queue_rounded),
          for (var i = 0; i < e.meteo.length && i < 2; i++)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(
                children: [
                  Icon(_iconeMeteo(e.meteo[i].icone), size: 34, color: Couleurs.orange),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(i == 0 ? 'Today' : 'Tomorrow',
                            style: const TextStyle(color: Couleurs.gris, fontSize: 12)),
                        Text('${e.meteo[i].tmax}° / ${e.meteo[i].tmin}°',
                            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
                        Text(e.meteo[i].textePluie,
                            style: TextStyle(
                                fontSize: 13,
                                color: e.meteo[i].pluie >= 20 ? Couleurs.cyan : Couleurs.vert)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  /// Favoris choisis dans Contrôles (appui long) : un appui pour les lancer.
  Widget _favoris(BuildContext context) {
    final favoris = favorisResolus(cx);
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Titre('Favorites', icone: Icons.star_rounded),
          if (favoris.isEmpty)
            const Text(
              'In Controls, long-press a shortcut, an app or an action, '
              'then "Add to favorites". They will show up here and in the phone widget.',
              style: TextStyle(color: Couleurs.gris, fontSize: 13),
            )
          else
            GrilleBoutons(
              colonnes: 4,
              espace: 8,
              enfants: [
                for (final a in favoris)
                  Tuile(
                    icone: a.icone,
                    texte: a.nom,
                    couleur: a.couleur,
                    onTap: () {
                      HapticFeedback.selectionClick();
                      lancerAction(context, cx, a);
                    },
                  ),
              ],
            ),
        ],
      ),
    );
  }

  Widget _actions(BuildContext context, EtatPC e) {
    return Carte(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Titre('Quick actions', icone: Icons.flash_on_rounded),
          GrilleBoutons(
            colonnes: 4,
            enfants: [
              BoutonAction(icone: Icons.lock_rounded, texte: 'Lock', onTap: () => cx.cmd('VERROU')),
              BoutonAction(
                  icone: e.ecranNoir ? Icons.desktop_windows_rounded : Icons.desktop_access_disabled_rounded,
                  texte: e.ecranNoir ? 'Wake' : 'Black screen',
                  couleur: e.ecranNoir ? Couleurs.orange : Couleurs.cyan,
                  onTap: () => cx.cmd('ECRAN_BASCULE')),
              BoutonAction(
                icone: e.ecranEsp ? Icons.lightbulb_rounded : Icons.lightbulb_outline_rounded,
                texte: 'ESP32',
                couleur: e.ecranEsp ? Couleurs.orange : Couleurs.gris,
                onTap: () => cx.cmd(e.ecranEsp ? 'ECRAN_ESP 0' : 'ECRAN_ESP 1'),
              ),
              BoutonAction(
                  icone: Icons.space_dashboard_rounded, texte: 'Desktop', onTap: () => cx.cmd('KEY win+d')),
              BoutonAction(
                icone: Icons.sports_esports_rounded,
                texte: 'My games',
                couleur: Couleurs.magenta,
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => EcranJeux(cx: cx))),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
