# Mascotte — catalogue des expressions et réactions

Mis à jour : 2026-11-01 · Tenue retenue : A (hoodie bleu nuit, casque cyan), fond crépuscule.

Règle de Mihaja : toutes les expressions possibles, mais l'écran ne doit jamais être surchargé → une seule réaction à la fois, puis retour au repos. Les états durables (casque sur les oreilles, endormi) restent affichés tant que la situation dure.

## États durables (selon ce que signale le programme PC)
| Situation | Déclencheur (EVT / STAT) | Ce que fait la mascotte |
|---|---|---|
| Repos | — | respire (±2 px), cligne des yeux toutes les 3-5 s, regarde parfois sur le côté |
| Casque connecté | EVT CASQUE nom | animation : prend le casque du cou et l'enfile sur les oreilles ; reste avec le casque ; hoche la tête quand du son joue (plus tard : détection du son) |
| Casque déconnecté | EVT CASQUE - | enlève le casque et le repose autour du cou |
| Manette connectée | EVT MANETTE 1 | bulle de pensée avec une manette, petit sourire « mode jeu », étoiles dans les yeux |
| Manette déconnectée | EVT MANETTE 0 | la bulle disparaît |
| PC verrouillé / écran éteint | EVT VERROU 1 | baille, ferme les yeux, « z z z », écran assombri |
| PC déverrouillé | EVT VERROU 0 | se réveille, se frotte les yeux, sourit |
| PC très chargé | STAT cpu > 85 % pendant 5 s | concentré, goutte de sueur |
| Batterie faible | STAT bat < 20 % sans charge | inquiet, petite batterie rouge |
| En charge | STAT charge passe à 1 | éclair, content |

## Réactions courtes (1 à 2 s, à chaque commande reçue)
| Commande | Réaction |
|---|---|
| VOL+ / VOL- / MUTE | main au casque, bulle haut-parleur, barre de volume |
| LUM / LUM+ / LUM- | lunettes de soleil (monter) ou plisse les yeux (baisser) |
| MOUSE / CLIC / MOLETTE | regarde dans la direction du mouvement |
| KEY / TEXT | tape sur un petit clavier, bulle « … » |
| APP nom | clin d'œil + icône de l'app dans une bulle |
| PLAY / NEXT / PREV | note de musique |
| ARRET | fait coucou de la main, l'écran se ferme en fondu |

## Technique
- Sprites 95 × 150 px (RGB565 + transparence) générés sur le PC à partir de l'illustration de Mihaja (tête détourée + buste redessiné). Images de base : yeux ouverts, yeux fermés ; à produire : bouche ouverte / baille, regard gauche / droite, casque sur les oreilles (2-3 images de transition), étoiles dans les yeux, sueur, inquiet.
- Accessoires (bulles, icônes, z z z, lunettes) dessinés séparément et posés par-dessus, pour limiter le nombre d'images stockées.
