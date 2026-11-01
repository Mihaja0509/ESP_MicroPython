#!/usr/bin/env python3
"""Envoie des commandes de test à l'ESP32 (clavier / souris / multimédia).

Utilisation :
  py -X utf8 tools\\pc_test.py COM4                commandes tapées une par une
  py -X utf8 tools\\pc_test.py COM4 --cmd "VOL+"   une seule commande
"""
import argparse
import sys
import time

import serial

AIDE = """Commandes :
  PING                  test de connexion
  KEY win+l             raccourci (ctrl, shift, alt, win + lettre, chiffre, f1..f12,
                        enter, esc, tab, space, up/down/left/right, delete, home, end…)
  TEXT bonjour          tape du texte (disposition QWERTY US)
  VOL+  VOL-  MUTE  PLAY  NEXT  PREV  LUM+  LUM-
  MOUSE 100 -50         déplace la souris (x, y)
  CLIC  CLICD           clic gauche / clic droit
  MOLETTE -3            défilement (négatif = vers le bas)
  q                     quitter"""


def ouvrir(port):
    try:
        ser = serial.Serial(port, 115200, timeout=0.1)
    except serial.SerialException as e:
        sys.exit(f"Impossible d'ouvrir {port} : {e}\n(mpremote est peut-être encore connecté)")
    time.sleep(0.5)
    ser.reset_input_buffer()
    return ser


def envoyer(ser, commande, attente=3.0):
    ser.write((commande.strip() + "\n").encode())
    ser.flush()
    fin = time.time() + attente
    while time.time() < fin:
        ligne = ser.readline().decode(errors="ignore").strip()
        if ligne.startswith(("OK", "ERR", "PONG")):
            print("  ->", ligne)
            return ligne
    print("  -> pas de réponse")
    return None


def main():
    parser = argparse.ArgumentParser(description="Test clavier/souris de l'ESP32")
    parser.add_argument("port", help="port série de l'ESP32, ex. COM4")
    parser.add_argument("--cmd", help="envoie une seule commande puis quitte")
    args = parser.parse_args()

    ser = ouvrir(args.port)
    if args.cmd:
        envoyer(ser, args.cmd)
        return
    print(AIDE)
    while True:
        try:
            commande = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if commande.lower() == "q":
            break
        if commande:
            envoyer(ser, commande)


if __name__ == "__main__":
    main()
