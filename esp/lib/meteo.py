# Wi-Fi de la maison + météo d'aujourd'hui et de demain (Open-Meteo, gratuit, sans clé).
# Réglages dans /secrets.py sur la carte (jamais dans Git) :
#   WIFI_SSID = "..."      WIFI_MDP = "..."
#   LATITUDE = 3.139       LONGITUDE = 101.687
import time

import network

URL = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
       "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
       "&hourly=precipitation_probability&timezone=auto&forecast_days=2")
INTERVALLE = 30 * 60 * 1000   # nouvelle météo toutes les 30 minutes au plus


def icone_meteo(code):
    """Code météo WMO -> nom d'icône."""
    if code == 0:
        return "soleil"
    if code in (1, 2):
        return "eclaircie"
    if code == 3:
        return "nuage"
    if code in (45, 48):
        return "brouillard"
    if 71 <= code <= 77 or code in (85, 86):
        return "neige"
    if code >= 95:
        return "orage"
    if 51 <= code <= 82:
        return "pluie"
    return "nuage"


class Meteo:
    def __init__(self, reglages):
        self.ssid = getattr(reglages, "WIFI_SSID", "")
        self.mdp = getattr(reglages, "WIFI_MDP", "")
        self.lat = getattr(reglages, "LATITUDE", None)
        self.lon = getattr(reglages, "LONGITUDE", None)
        self.jours = []          # [{icone, tmax, tmin, pluie, heure_pluie}, …] aujourd'hui, demain
        self.derniere = None     # ticks de la dernière mise à jour réussie
        self.dernier_essai = None
        self.probleme = ""
        self.wlan = None
        if self.ssid:
            try:
                self.wlan = network.WLAN(network.STA_IF)
                self.wlan.active(True)
                if not self.wlan.isconnected():
                    self.wlan.connect(self.ssid, self.mdp)  # ne bloque pas
            except Exception as e:
                self.probleme = "Wi-Fi : %s" % e
        else:
            self.probleme = "Wi-Fi non réglé (secrets.py)"

    def connecte(self):
        try:
            return self.wlan is not None and self.wlan.isconnected()
        except Exception:
            return False

    def a_mettre_a_jour(self, maintenant):
        """True si une mise à jour est utile maintenant (Wi-Fi prêt, données vieilles)."""
        if self.lat is None or not self.connecte():
            return False
        if self.dernier_essai is not None and time.ticks_diff(maintenant, self.dernier_essai) < 60000:
            return False  # au plus un essai par minute
        return self.derniere is None or time.ticks_diff(maintenant, self.derniere) > INTERVALLE

    def mettre_a_jour(self, maintenant):
        """Télécharge la météo (bloque 1 à 3 s). Renvoie True si réussi."""
        self.dernier_essai = maintenant
        try:
            import requests
        except ImportError:
            self.probleme = "module requests absent"
            return False
        try:
            try:
                r = requests.get(URL % (self.lat, self.lon), timeout=10)
            except TypeError:
                r = requests.get(URL % (self.lat, self.lon))
            donnees = r.json()
            r.close()
        except Exception as e:
            self.probleme = "météo : %s" % e
            return False
        try:
            self._regler_heure(donnees.get("utc_offset_seconds", 0))
            self.jours = self._lire(donnees)
        except Exception as e:
            self.probleme = "météo illisible : %s" % e
            return False
        self.derniere = maintenant
        self.probleme = ""
        return True

    def _regler_heure(self, decalage):
        """Si l'horloge n'a jamais été réglée (PC éteint), on la règle par Internet (NTP)."""
        if time.localtime()[0] >= 2025:
            return
        try:
            import machine
            import ntptime
            ntptime.settime()  # heure universelle
            t = time.gmtime(time.time() + decalage)
            machine.RTC().datetime((t[0], t[1], t[2], t[6], t[3], t[4], t[5], 0))
        except Exception:
            pass

    def _lire(self, d):
        jour = d["daily"]
        heures = d["hourly"]["time"]
        pluie_h = d["hourly"]["precipitation_probability"]
        lt = time.localtime()
        aujourdhui = "%04d-%02d-%02d" % (lt[0], lt[1], lt[2])
        jours = []
        for i in range(min(2, len(jour["time"]))):
            date = jour["time"][i]
            meilleure, heure = -1, None
            for t, p in zip(heures, pluie_h):
                if not t.startswith(date) or p is None:
                    continue
                h = int(t[11:13])
                if date == aujourdhui and h < lt[3]:
                    continue  # aujourd'hui : seulement les heures à venir
                if p > meilleure:
                    meilleure, heure = p, h
            jours.append({
                "icone": icone_meteo(int(jour["weather_code"][i] or 0)),
                "tmax": round(jour["temperature_2m_max"][i]),
                "tmin": round(jour["temperature_2m_min"][i]),
                "pluie": meilleure,
                "heure_pluie": heure,
            })
        return jours
