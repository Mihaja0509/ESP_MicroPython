# Capteur de la pièce (Phase 13) : AHT20 (température + humidité) et BMP280 (pression), en I2C.
# Mesure toutes les 5 s sans bloquer l'écran : on déclenche la mesure, puis on la lit 90 ms plus tard.
# Phase 15 : tolérant au débranchement à chaud.
# - toute erreur I2C ou valeur aberrante est un échec, jamais une exception ;
# - après un échec, nouvel essai dans 2 s ; après 3 échecs de suite : bus recréé, soft reset AHT20,
#   initialisation, réinitialisation BMP280, nouveau scan ;
# - capteur absent : nouveau scan toutes les 10 s, réinitialisation complète dès qu'il revient ;
# - les deux modules sont indépendants (BMP280 seul : température sans humidité, AHT20 seul : pas de pression).
import struct
import time

from machine import I2C, Pin

SDA = 7      # numéros des GPIO trouvés par tools/i2c_scan.py le 2026-11-06 (AHT20 0x38, BMP280 0x77)
SCL = 6
DECALAGE_T = 0.0    # °C ajoutés à la mesure (la carte chauffe un peu : à régler avec un vrai thermomètre)
PERIODE_MS = 5000
RETENTE_MS = 2000   # après un échec : « -- » à l'écran en moins de 15 s si le capteur a vraiment disparu
ECHECS_MAX = 3
REESSAI_MS = 10000  # capteur absent : nouveau scan toutes les 10 s
PEREMPTION_MS = 60000  # une mesure plus vieille que ça n'est plus affichée
RENVOI_ERREUR_MS = 10000  # « CLIMAT ERR » : au changement, puis toutes les 10 s
AHT = 0x38
ADRESSES_BMP = (0x76, 0x77)


def temperature_valide(t):
    return -20 <= t <= 80


def humidite_valide(h):
    return 0 <= h <= 100


def pression_valide(p):
    return 300 <= p <= 1100


class Capteur:
    def __init__(self):
        self.ok = False            # au moins un module répond
        self.erreur = None         # raison de l'absence de mesure : "absent", "i2c", "aberrant" ou None
        self.i2c = None
        self._aht = False
        self._bmp = None           # adresse du BMP280 ou None
        self._t = self._h = None   # AHT20
        self._tb = self._p = None  # BMP280
        self._vu = None            # ticks de la dernière bonne mesure
        self._lance = None
        self._ko_aht = self._ko_bmp = False  # déclenchement de la mesure raté
        self._echecs_aht = self._echecs_bmp = 0
        maintenant = time.ticks_ms()
        self._prochain = maintenant
        self._prochain_scan = maintenant
        self._err_envoyee = None
        self._err_quand = maintenant
        self.reinitialiser(maintenant)

    # --- initialisation (jamais d'exception) --------------------------------------------
    def reinitialiser(self, maintenant=None):
        """Remet tout à zéro et cherche les modules (démarrage, 3 échecs, bouton BOOT).
        La prochaine mesure part tout de suite. Renvoie True si un module répond."""
        if maintenant is None:
            maintenant = time.ticks_ms()
        self._reinit(maintenant)
        self._prochain = maintenant
        self._err_envoyee = None  # l'erreur éventuelle repart tout de suite
        return self.ok

    def _reinit(self, maintenant):
        self._lance = None
        self._echecs_aht = self._echecs_bmp = 0
        self._aht = False
        self._bmp = None
        self._prochain_scan = time.ticks_add(maintenant, REESSAI_MS)
        try:
            self.i2c = I2C(0, sda=Pin(SDA), scl=Pin(SCL), freq=100_000)
            adresses = self._sonder()
        except Exception:
            adresses = ()
        self._chercher(adresses)
        self._apres_detection()

    def _sonder(self):
        """Les adresses qui répondent, parmi celles des deux modules. Jamais i2c.scan() : SCL tenue à 0,
        il bloque 5,6 s (112 adresses × 50 ms, mesuré) et l'écran ne peut plus se rallumer."""
        adresses = []
        for a in (AHT,) + ADRESSES_BMP:
            try:
                self.i2c.writeto(a, b"")
                adresses.append(a)
            except OSError:
                pass
        return adresses

    def _chercher(self, adresses):
        """Initialise les modules vus par le scan et pas encore en service."""
        if not self._aht and AHT in adresses:
            self._aht = self._aht_init()
        if self._bmp is None:
            for a in ADRESSES_BMP:
                if a in adresses and self._bmp_init(a):
                    break

    def _apres_detection(self):
        if not self._aht:
            self._t = self._h = None
        if self._bmp is None:
            self._tb = self._p = None
        self.ok = self._aht or self._bmp is not None
        if not self.ok:
            self._vu = None
            self.erreur = "absent"

    def _aht_init(self):
        try:
            self.i2c.writeto(AHT, b"\xBA")           # soft reset
            time.sleep_ms(20)
            self.i2c.writeto(AHT, b"\xBE\x08\x00")   # initialisation / calibration
            time.sleep_ms(10)
            return True
        except Exception:
            return False

    # --- BMP280 (formules du constructeur, version à virgule flottante) ----------------
    def _bmp_init(self, adr):
        try:
            if self.i2c.readfrom_mem(adr, 0xD0, 1)[0] not in (0x58, 0x60):
                return False
            self.i2c.writeto_mem(adr, 0xF5, b"\x00")  # config : pas de filtre
            self.i2c.writeto_mem(adr, 0xF4, b"\x24")  # ctrl_meas : x1, x1, en sommeil
            (self.T1, self.T2, self.T3, self.P1, self.P2, self.P3, self.P4, self.P5, self.P6,
             self.P7, self.P8, self.P9) = struct.unpack("<HhhHhhhhhhhh", self.i2c.readfrom_mem(adr, 0x88, 24))
            self._bmp = adr
            return True
        except Exception:
            self._bmp = None
            return False

    def _bmp_lire(self):
        """(°C, hPa) ou None si le calcul est impossible."""
        d = self.i2c.readfrom_mem(self._bmp, 0xF7, 6)
        adc_p = (d[0] << 12) | (d[1] << 4) | (d[2] >> 4)
        adc_t = (d[3] << 12) | (d[4] << 4) | (d[5] >> 4)
        # 0x80000 = valeur de repos des registres : rebranché, il n'a encore rien mesuré (lu sur le
        # vrai module : 23,8 °C et 668 hPa, plausibles mais faux)
        if adc_p == 0x80000 or adc_t == 0x80000:
            return None
        v1 = (adc_t / 16384.0 - self.T1 / 1024.0) * self.T2
        v2 = ((adc_t / 131072.0 - self.T1 / 8192.0) ** 2) * self.T3
        tfine = v1 + v2
        t = tfine / 5120.0
        v1 = tfine / 2.0 - 64000.0
        v2 = v1 * v1 * self.P6 / 32768.0
        v2 = v2 + v1 * self.P5 * 2.0
        v2 = v2 / 4.0 + self.P4 * 65536.0
        v1 = (self.P3 * v1 * v1 / 524288.0 + self.P2 * v1) / 524288.0
        v1 = (1.0 + v1 / 32768.0) * self.P1
        if v1 == 0:
            return None
        p = 1048576.0 - adc_p
        p = (p - v2 / 4096.0) * 6250.0 / v1
        v1 = self.P9 * p * p / 2147483648.0
        v2 = p * self.P8 / 32768.0
        return t, (p + (v1 + v2 + self.P7) / 16.0) / 100.0  # hPa

    # --- boucle -------------------------------------------------------------------------
    def pas(self, maintenant):
        """À appeler à chaque tour de boucle. Renvoie True quand une nouvelle mesure est prête.
        Ne lève jamais d'exception : une erreur I2C n'arrête pas l'écran."""
        try:
            return self._pas(maintenant)
        except Exception:  # filet de sécurité : tout est repris au prochain scan
            self._reinit(maintenant)
            return False

    def _pas(self, maintenant):
        if self._lance is None:
            self._balayer(maintenant)
            if self.ok and time.ticks_diff(maintenant, self._prochain) >= 0:
                self._declencher(maintenant)
            return False
        if time.ticks_diff(maintenant, self._lance) < 90:
            return False
        return self._lire(maintenant)

    def _balayer(self, maintenant):
        """Toutes les 10 s, tant qu'un module manque : nouveau scan."""
        if self._aht and self._bmp is not None:
            return
        if time.ticks_diff(maintenant, self._prochain_scan) < 0:
            return
        if not self.ok:
            self.reinitialiser(maintenant)  # rien ne répond : on repart du bus
            return
        self._prochain_scan = time.ticks_add(maintenant, REESSAI_MS)
        try:
            adresses = self._sonder()
        except Exception:
            return
        avant = (self._aht, self._bmp)
        self._chercher(adresses)
        if (self._aht, self._bmp) != avant:
            self._prochain = maintenant

    def _declencher(self, maintenant):
        self._ko_aht = self._ko_bmp = False
        if self._aht:
            try:
                self.i2c.writeto(AHT, b"\xAC\x33\x00")
            except Exception:
                self._ko_aht = True
        if self._bmp is not None:
            try:
                self.i2c.writeto_mem(self._bmp, 0xF4, b"\x25")  # une mesure (mode forcé)
            except Exception:
                self._ko_bmp = True
        self._lance = maintenant

    def _lire_aht(self):
        """(°C, %) ou lève OSError (I2C) / ValueError (valeur aberrante)."""
        d = self.i2c.readfrom(AHT, 7)
        if d[0] & 0x80:
            raise OSError("occupé")
        h = ((d[1] << 12) | (d[2] << 4) | (d[3] >> 4)) * 100 / 1048576
        t = (((d[3] & 0x0F) << 16) | (d[4] << 8) | d[5]) * 200 / 1048576 - 50 + DECALAGE_T
        if not temperature_valide(t) or not humidite_valide(h):
            raise ValueError("aberrant")
        return t, h

    def _lire_bmp(self):
        r = self._bmp_lire()
        if r is None or not temperature_valide(r[0] + DECALAGE_T) or not pression_valide(r[1]):
            raise ValueError("aberrant")
        return r[0] + DECALAGE_T, r[1]

    def _lire(self, maintenant):
        self._lance = None
        bon = False
        raison = None
        reinit = False
        if self._aht:
            try:
                if self._ko_aht:
                    raise OSError("déclenchement")
                t, h = self._lire_aht()
                # lissage léger : le bruit de mesure ne fait pas clignoter l'écran ni l'automatisme
                self._t = t if self._t is None else self._t + 0.4 * (t - self._t)
                self._h = h if self._h is None else self._h + 0.4 * (h - self._h)
                self._echecs_aht = 0
                bon = True
            except Exception as e:
                raison = "aberrant" if isinstance(e, ValueError) else "i2c"
                self._echecs_aht += 1
                if self._echecs_aht >= ECHECS_MAX:
                    self._t = self._h = None
                    reinit = True
        if self._bmp is not None:
            try:
                if self._ko_bmp:
                    raise OSError("déclenchement")
                t, p = self._lire_bmp()
                self._tb = t
                self._p = p
                self._echecs_bmp = 0
                bon = True
            except Exception as e:
                raison = raison or ("aberrant" if isinstance(e, ValueError) else "i2c")
                self._echecs_bmp += 1
                if self._echecs_bmp >= ECHECS_MAX:
                    self._tb = self._p = None
                    reinit = True
        echec = raison is not None
        if reinit:
            self._reinit(maintenant)
        self._prochain = time.ticks_add(maintenant, RETENTE_MS if echec else PERIODE_MS)
        if bon:
            self._vu = maintenant
        if self.mesure() is None:
            if self.ok:
                self.erreur = raison or self.erreur or "i2c"
            return False
        self.erreur = None
        return bon

    def mesure(self):
        """(°C, % d'humidité, hPa) ou None. % = -1 sans AHT20, hPa = 0 sans BMP280. None aussi quand la
        dernière bonne mesure a plus de 60 s : jamais de valeur périmée à l'écran."""
        t = self._t if self._t is not None else self._tb
        if t is None or self._vu is None:
            return None
        if time.ticks_diff(time.ticks_ms(), self._vu) > PEREMPTION_MS:
            return None
        return (t, self._h if self._h is not None else -1, self._p or 0)

    def erreur_a_envoyer(self, maintenant):
        """Raison à envoyer dans « CLIMAT ERR » : au changement, puis toutes les 10 s. Sinon None."""
        if self.mesure() is not None or self.erreur is None:
            self._err_envoyee = None
            return None
        if self.erreur != self._err_envoyee or time.ticks_diff(maintenant, self._err_quand) >= RENVOI_ERREUR_MS:
            self._err_envoyee = self.erreur
            self._err_quand = maintenant
            return self.erreur
        return None
