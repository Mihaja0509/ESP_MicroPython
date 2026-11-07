# Bouton BOOT de la carte (Phase 15) : lu dans la boucle principale, jamais d'interruption.
# pas() renvoie :
#   "court"   : appui court, relâché ;
#   "long"    : tenu 3 s, encore enfoncé (annonce à l'écran) ;
#   "relache" : relâché après un appui long. On redémarre seulement là : si GPIO0 était encore
#               à 0 pendant le reset, la puce pourrait partir en mode flash.
# Un appui déjà en cours au démarrage est ignoré tant que le bouton n'a pas été relâché une fois.
ANTI_REBOND_MS = 50
LONG_MS = 3000


class Bouton:
    def __init__(self, lire, maintenant):
        self._lire = lire           # renvoie 0 quand le bouton est enfoncé
        self._stable = 0            # on part « enfoncé » : il faudra un relâchement pour armer
        self._brut = 0
        self._change = maintenant
        self._debut = None
        self._long = False

    def pas(self, maintenant):
        valeur = 1 if self._lire() else 0
        if valeur != self._brut:
            self._brut = valeur
            self._change = maintenant
            return None
        if valeur != self._stable and maintenant - self._change >= ANTI_REBOND_MS:
            self._stable = valeur
            if valeur == 0:         # appui confirmé
                self._debut = maintenant
                self._long = False
                return None
            debut, long_emis = self._debut, self._long
            self._debut = None
            self._long = False
            if debut is None:       # relâchement de l'appui présent au démarrage
                return None
            return "relache" if long_emis else "court"
        if self._debut is not None and not self._long and maintenant - self._debut >= LONG_MS:
            self._long = True
            return "long"
        return None
