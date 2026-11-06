# Cherche où le capteur est branché : essaie toutes les paires de GPIO libres et affiche celles
# où quelque chose répond en I2C (AHT20 = 0x38, BMP280 = 0x76 ou 0x77).
# Lancer avec l'agent en PAUSE :  py -m mpremote connect COMx run tools/i2c_scan.py
from machine import I2C, Pin

LIBRES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 43, 44, 47]
trouve = []
for sda in LIBRES:
    for scl in LIBRES:
        if sda == scl:
            continue
        try:
            i2c = I2C(0, sda=Pin(sda), scl=Pin(scl), freq=100000)
            adr = i2c.scan()
        except Exception:
            continue
        if adr:
            print("SDA", sda, "SCL", scl, [hex(a) for a in adr])
            trouve.append((sda, scl))
print("fini :", trouve if trouve else "rien trouvé (vérifier le câblage et 3V3)")
