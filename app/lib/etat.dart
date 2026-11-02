// Données reçues du programme PC (message « etat », 4 fois par seconde).

int _entier(dynamic v) => v is num ? v.toInt() : -1;

class JourMeteo {
  final String icone;
  final int tmax;
  final int tmin;
  final int pluie;
  final int heure;

  const JourMeteo({
    required this.icone,
    required this.tmax,
    required this.tmin,
    required this.pluie,
    required this.heure,
  });

  factory JourMeteo.depuisJson(Map<String, dynamic> m) => JourMeteo(
        icone: (m['icone'] ?? 'nuage').toString(),
        tmax: _entier(m['tmax']),
        tmin: _entier(m['tmin']),
        pluie: _entier(m['pluie']),
        heure: _entier(m['heure']),
      );

  String get textePluie =>
      (pluie >= 20 && heure >= 0) ? 'Pluie $pluie % vers $heure h' : 'Pas de pluie prévue';
}

class EtatPC {
  final bool recu;
  final int cpu;
  final int ram;
  final int vol;
  final int bat;
  final bool enCharge;
  final int gpuTemp;
  final int gpuCharge;
  final int vram;
  final int cpuTemp;
  final int fps;
  final String casque;
  final bool manette;
  final bool verrou;
  final String jeu;
  final List<JourMeteo> meteo;
  final bool esp;
  final bool ecranEsp;
  final int arret; // secondes avant l'arrêt du PC, -1 = pas d'arrêt prévu
  final bool ecranNoir; // écran du PC en mode « écran noir »
  final int lumEsp; // luminosité de l'écran de l'ESP32 (5 à 100), -1 = inconnue
  final int ecrans; // nombre d'écrans allumés sur le PC

  const EtatPC({
    required this.recu,
    required this.cpu,
    required this.ram,
    required this.vol,
    required this.bat,
    required this.enCharge,
    required this.gpuTemp,
    required this.gpuCharge,
    required this.vram,
    required this.cpuTemp,
    required this.fps,
    required this.casque,
    required this.manette,
    required this.verrou,
    required this.jeu,
    required this.meteo,
    required this.esp,
    required this.ecranEsp,
    this.arret = -1,
    this.ecranNoir = false,
    this.lumEsp = -1,
    this.ecrans = 1,
  });

  factory EtatPC.vide() => const EtatPC(
        recu: false,
        cpu: -1,
        ram: -1,
        vol: -1,
        bat: -1,
        enCharge: false,
        gpuTemp: -1,
        gpuCharge: -1,
        vram: -1,
        cpuTemp: -1,
        fps: -1,
        casque: '',
        manette: false,
        verrou: false,
        jeu: '',
        meteo: [],
        esp: false,
        ecranEsp: true,
      );

  factory EtatPC.depuisJson(Map<String, dynamic> m) {
    final meteo = <JourMeteo>[];
    final brut = m['meteo'];
    if (brut is List) {
      for (final j in brut) {
        if (j is Map<String, dynamic>) meteo.add(JourMeteo.depuisJson(j));
      }
    }
    return EtatPC(
      recu: true,
      cpu: _entier(m['cpu']),
      ram: _entier(m['ram']),
      vol: _entier(m['vol']),
      bat: _entier(m['bat']),
      enCharge: _entier(m['chg']) == 1,
      gpuTemp: _entier(m['gpu_temp']),
      gpuCharge: _entier(m['gpu_charge']),
      vram: _entier(m['vram']),
      cpuTemp: _entier(m['cpu_temp']),
      fps: _entier(m['fps']),
      casque: (m['casque'] ?? '').toString(),
      manette: m['manette'] == true,
      verrou: m['verrou'] == true,
      jeu: (m['jeu'] ?? '').toString(),
      meteo: meteo,
      esp: m['esp'] == true,
      ecranEsp: m['ecran_esp'] != false,
      arret: m.containsKey('arret') ? _entier(m['arret']) : -1,
      ecranNoir: m['ecran_noir'] == true,
      lumEsp: _entier(m['lum_esp']),
      ecrans: m['ecrans'] is num ? (m['ecrans'] as num).toInt() : 1,
    );
  }

  bool get enJeu => jeu.isNotEmpty;

  bool get arretPrevu => arret > 0;
}
