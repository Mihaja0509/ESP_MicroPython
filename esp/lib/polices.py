# Polices lissées pour l'écran (fichiers .fnt créés par tools/assets/generer_assets.py).
# Chaque pixel d'un caractère vaut 0 (vide), 1, 2 ou 3 (plein). Pour dessiner, on
# associe ces 4 niveaux à 4 couleurs (palette) : transparent, deux mélanges, couleur pleine.
import struct

import framebuf


def rgb565(r, g, b):
    """Couleur 0-255 -> valeur RGB565 dans l'ordre d'octets de l'écran (comme lcd.couleur)."""
    c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return ((c & 0xFF) << 8) | (c >> 8)


class Police:
    def __init__(self, chemin):
        with open(chemin, "rb") as f:
            donnees = bytearray(f.read())  # FrameBuffer demande un tampon modifiable
        if donnees[:4] != b"FNT1":
            raise ValueError("fichier de police invalide : " + chemin)
        self.hauteur, nb = struct.unpack_from("<BH", donnees, 4)
        debut_table = 7
        debut_pixels = debut_table + nb * 8
        self._pixels = memoryview(donnees)[debut_pixels:]
        self._donnees = donnees  # garde le tampon en vie
        self.glyphes = {}
        h = self.hauteur
        for i in range(nb):
            code, w, avance, decalage = struct.unpack_from("<HBBI", donnees, debut_table + i * 8)
            fb = framebuf.FrameBuffer(self._pixels[decalage:decalage + w * h], w, h, framebuf.GS8)
            self.glyphes[code] = (fb, avance)
        self._palettes = {}

    def _palette(self, avant, fond):
        cle = (avant, fond)
        p = self._palettes.get(cle)
        if p is None:
            # Une palette pour une source GS8 doit faire 256 pixels de large ;
            # seules les 4 premières couleurs servent. La couleur 0 (= fond) sert aussi
            # de « clé » : les pixels vides du caractère ne sont pas dessinés.
            pal = framebuf.FrameBuffer(bytearray(512), 256, 1, framebuf.RGB565)
            for i in range(4):
                t = i / 3
                r = int(fond[0] + (avant[0] - fond[0]) * t)
                g = int(fond[1] + (avant[1] - fond[1]) * t)
                b = int(fond[2] + (avant[2] - fond[2]) * t)
                pal.pixel(i, 0, rgb565(r, g, b))
            if len(self._palettes) > 40:
                self._palettes = {}
            p = (pal, rgb565(*fond))
            self._palettes[cle] = p
        return p

    def largeur(self, texte):
        total = 0
        for ch in texte:
            g = self.glyphes.get(ord(ch)) or self.glyphes.get(63)  # « ? » si inconnu
            if g:
                total += g[1]
        return total

    def ecrire(self, fb, texte, x, y, avant, fond):
        """Écrit `texte` en (x, y) (coin haut gauche). Couleurs en (r, g, b).
        `fond` = couleur moyenne derrière le texte (pour lisser les bords)."""
        pal, cle = self._palette(avant, fond)
        for ch in texte:
            g = self.glyphes.get(ord(ch)) or self.glyphes.get(63)
            if g is None:
                continue
            fb.blit(g[0], x, y, cle, pal)
            x += g[1]
        return x

    def ecrire_centre(self, fb, texte, cx, y, avant, fond):
        return self.ecrire(fb, texte, cx - self.largeur(texte) // 2, y, avant, fond)

    def couper(self, texte, largeur_max):
        """Raccourcit `texte` avec « … » pour qu'il tienne dans largeur_max pixels."""
        if self.largeur(texte) <= largeur_max:
            return texte
        while texte and self.largeur(texte + "…") > largeur_max:
            texte = texte[:-1]
        return texte + "…"
