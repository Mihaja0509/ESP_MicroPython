# Capteur de la pièce (Phase 13) : AHT20 (température + humidité) et BMP280 (pression), en I2C.
# Mesure toutes les 5 s sans bloquer l'écran : on déclenche la mesure, puis on la lit 90 ms plus tard.
# Phase 14-bis : lecture robuste. Une erreur I2C ne tue jamais la boucle ; l'initialisation est retentée
# toutes les 10 s tant que le capteur ne répond pas (fil débranché puis rebranché) ; le bus est
# réinitialisé après 3 échecs de suite ; une mesure de plus de 60 s n'est jamais renvoyée.
import struct
import time

from machine import I2C, Pin

SDA = 7      # numéros des GPIO trouvés par tools/i2c_scan.py le 2026-11-06 (AHT20 0x38, BMP280 0x77)
SCL = 6
DECALAGE_T = 0.0    # °C ajoutés à la mesure (la carte chauffe un peu : à régler avec un vrai thermomètre)
PERIODE_MS = 5000
REESSAI_MS = 10000  # capteur absent : nouvel essai d'initialisation toutes les 10 s
PEREMPTION_MS = 60000  # une mesure plus vieille que ça n'est plus affichée
AHT = 0x38


class Capteur:
    def __init__(self):
        self.ok = False
        self.i2c = None
        self._t = self._h = self._p = None
        self._vu = None            # ticks de la dernière bonne mesure
        self._lance = None
        self._prochain = time.ticks_ms()
        self._echecs = 0
        self._bmp = None
        self._prochain_essai = time.ticks_ms()
        self._derniere_alerte = None
        self._init()

    # --- initialisation (jamais d'exception) --------------------------------------------
    def _alerte(self, texte):
        """Au plus un message par minute (ils finissent dans agent.log)."""
        maintenant = time.ticks_ms()
        if self._derniere_alerte is None or time.ticks_diff(maintenant, self._derniere_alerte) > 60000:
            self._derniere_alerte = maintenant
            print(texte)

    def _init(self):
        """(Ré)initialise le bus et le capteur. Renvoie True si l'AHT20 répond."""
        self.ok = False
        self._bmp = None
        self._lance = None
        if SDA is None or SCL is None:
            return False
        try:
            self.i2c = I2C(0, sda=Pin(SDA), scl=Pin(SCL), freq=100_000)
            adresses = self.i2c.scan()
            if AHT not in adresses:
                self._alerte("CAPTEUR AHT20 absent (câblage SDA %d / SCL %d ?)" % (SDA, SCL))
                return False
            time.sleep_ms(40)
            if not (self.i2c.readfrom(AHT, 1)[0] & 0x08):  # pas calibré : commande d'initialisation
                self.i2c.writeto(AHT, b"\xBE\x08\x00")
                time.sleep_ms(20)
            for a in (0x76, 0x77):
                if a in adresses:
                    try:
                        self._bmp_init(a)
                    except OSError:
                        self._bmp = None
                    break
            self.ok = True
            self._echecs = 0
            self._prochain = time.ticks_ms()
            return True
        except Exception as e:
            self._alerte("CAPTEUR erreur %s" % e)
            return False

    # --- BMP280 (formules du constructeur, version à virgule flottante) ----------------
    def _bmp_init(self, adr):
        if self.i2c.readfrom_mem(adr, 0xD0, 1)[0] not in (0x58, 0x60):
            raise OSError("pas un BMP280")
        self._bmp = adr
        (self.T1, self.T2, self.T3, self.P1, self.P2, self.P3, self.P4, self.P5, self.P6,
         self.P7, self.P8, self.P9) = struct.unpack("<HhhHhhhhhhhh", self.i2c.readfrom_mem(adr, 0x88, 24))

    def _bmp_lire(self):
        d = self.i2c.readfrom_mem(self._bmp, 0xF7, 6)
        adc_p = (d[0] << 12) | (d[1] << 4) | (d[2] >> 4)
        adc_t = (d[3] << 12) | (d[4] << 4) | (d[5] >> 4)
        v1 = (adc_t / 16384.0 - self.T1 / 1024.0) * self.T2
        v2 = ((adc_t / 131072.0 - self.T1 / 8192.0) ** 2) * self.T3
        tfine = v1 + v2
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
        return (p + (v1 + v2 + self.P7) / 16.0) / 100.0  # hPa

    # --- boucle -------------------------------------------------------------------------
    def _echec(self, maintenant):
        self._lance = None
        self._echecs += 1
        self._prochain = time.ticks_add(maintenant, PERIODE_MS)
        if self._echecs >= 3:
            # 3 échecs de suite : plus de mesure fiable, et on repart de zéro sur le bus
            self._t = self._h = self._p = None
            self._vu = None
            self._prochain_essai = time.ticks_add(maintenant, REESSAI_MS)
            self._init()

    def pas(self, maintenant):
        """À appeler à chaque tour de boucle. Renvoie True quand une nouvelle mesure est prête.
        Ne lève jamais d'exception : une erreur I2C n'arrête pas l'écran."""
        try:
            return self._pas(maintenant)
        except Exception as e:  # filet de sécurité : on retentera au tour suivant
            self._alerte("CAPTEUR erreur %s" % e)
            self._lance = None
            return False

    def _pas(self, maintenant):
        if not self.ok:
            # capteur absent ou en panne : nouvel essai d'initialisation toutes les 10 s
            if SDA is not None and SCL is not None and time.ticks_diff(maintenant, self._prochain_essai) >= 0:
                self._prochain_essai = time.ticks_add(maintenant, REESSAI_MS)
                self._init()
            return False
        if self._lance is None:
            if time.ticks_diff(maintenant, self._prochain) >= 0:
                try:
                    self.i2c.writeto(AHT, b"\xAC\x33\x00")
                    if self._bmp:
                        self.i2c.writeto_mem(self._bmp, 0xF4, b"\x25")  # une mesure (mode forcé)
                    self._lance = maintenant
                except OSError:
                    self._echec(maintenant)
            return False
        if time.ticks_diff(maintenant, self._lance) < 90:
            return False
        try:
            d = self.i2c.readfrom(AHT, 7)
            if d[0] & 0x80:
                raise OSError("occupé")
            h = ((d[1] << 12) | (d[2] << 4) | (d[3] >> 4)) * 100 / 1048576
            t = (((d[3] & 0x0F) << 16) | (d[4] << 8) | d[5]) * 200 / 1048576 - 50 + DECALAGE_T
            if not (-20 <= t <= 60) or not (0 <= h <= 100):
                raise OSError("mesure absurde")
            p = self._bmp_lire() if self._bmp else None
        except OSError:
            self._echec(maintenant)
            return False
        self._lance = None
        self._echecs = 0
        self._prochain = time.ticks_add(maintenant, PERIODE_MS)
        self._vu = maintenant
        # lissage léger : le bruit de mesure ne fait pas clignoter l'écran ni l'automatisme
        self._t = t if self._t is None else self._t + 0.4 * (t - self._t)
        self._h = h if self._h is None else self._h + 0.4 * (h - self._h)
        if p is not None:
            self._p = p
        return True

    def mesure(self):
        """(°C, % d'humidité, hPa) ou None. hPa = 0 si pas de BMP280. None aussi quand la dernière
        bonne mesure a plus de 60 s : jamais de valeur périmée à l'écran."""
        if self._t is None or self._vu is None:
            return None
        if time.ticks_diff(time.ticks_ms(), self._vu) > PEREMPTION_MS:
            return None
        return (self._t, self._h, self._p or 0)
