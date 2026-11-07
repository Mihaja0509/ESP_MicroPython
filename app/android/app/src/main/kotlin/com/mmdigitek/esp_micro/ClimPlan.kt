package com.mmdigitek.esp_micro

import android.Manifest
import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.ConsumerIrManager
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.max
import kotlin.math.min

/**
 * Clim programmée (Phase 13) : minuteur, plage horaire et mode automatique (capteur de la pièce).
 * Les trames IR (durées en µs) sont calculées par Dart (lib/clim_ir.dart) et rangées ici.
 * Heures fixes : setAlarmClock -> ClimReceiver -> executer(). Automatisme et republication : ClimService.
 * État dans les préférences « clim_plan » : seule source de vérité (app, service, notification).
 */
object ClimPlan {
    private const val PREFS = "clim_plan"
    private const val CANAL = "clim_auto"
    private const val ID_NOTIF = 4301
    const val CODE_MIN_OFF = 101
    const val CODE_MIN_ON = 102
    const val CODE_FEN_ON = 103
    const val CODE_FEN_OFF = 104
    const val CODE_AUTO = 105
    const val CODE_REPUB = 106                      // republication de l'état au PC (toutes les 30 s)
    const val CODE_GARDIEN = 107                    // relance le service tué par HyperOS (voir armerGardien)
    private const val GARDIEN_MS = 2 * 60_000L
    private const val REPUB_MS = 30_000L
    private const val REPUB_RETENTE_MS = 10_000L    // l'agent n'a pas répondu : nouvelle tentative plus vite

    /**
     * Version de la partie Android, demandée par Dart (canal « version »). 2 = minuteur en SECONDES
     * (Phase 14). Un rechargement à chaud ne met à jour que le Dart : si le Kotlin installé est plus
     * ancien, Dart le voit et refuse d'envoyer des secondes que l'ancien code lirait comme des minutes.
     */
    const val VERSION = 3 // 3 = service de premier plan et canaux fond / ouvrirReglage (Phase 15)
    private const val PAUSE_COMPRESSEUR_MS = 3 * 60_000L // le compresseur ne redémarre pas avant 3 min
    private const val MANUEL_MS = 30 * 60_000L           // après une action à la main, l'auto se tait
    private const val PAUSE_AUTO_MS = 30 * 60_000L       // bouton « Pause auto 30 min »
    private const val AUTO_MS = 60_000L                  // vérification de l'automatisme

    /** Dernière mesure de l'automatisme : null = capteur ou PC injoignable. */
    private class Mesure(val t: Double, val h: Double)

    @Volatile
    private var derniereMesure: Mesure? = null

    @Volatile
    private var autoProchain = 0L

    /** Pourquoi l'automatisme attend alors qu'un seuil est dépassé (affiché) ; "" = rien à signaler. */
    @Volatile
    private var autoRaison = ""

    private const val TAG = "ClimPlan"

    private fun p(c: Context) = c.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    private fun heure(ms: Long, format: String = "HH:mm"): String =
        SimpleDateFormat(format, Locale.US).format(Date(ms))

    /** Trace chaque décision : logcat (tag ClimPlan) + 20 dernières lignes pour l'app (sans adb). */
    @Synchronized
    fun journal(c: Context, texte: String) {
        Log.i(TAG, texte)
        val lignes = (p(c).getString("journal", "") ?: "").split("\n").filter { it.isNotEmpty() }
        val nouvelles = (lignes + "${heure(System.currentTimeMillis(), "dd/MM HH:mm:ss")} $texte").takeLast(20)
        p(c).edit().putString("journal", nouvelles.joinToString("\n")).apply()
    }

    // ------------------------------------------------------------------ trames et état
    fun trames(c: Context, frequence: Int, power: List<Int>, dryPower: List<Int>, mode: String, temp: Int) {
        p(c).edit()
            .putInt("freq", frequence)
            .putString("m_power", power.joinToString(","))
            .putString("m_dry_power", dryPower.joinToString(","))
            .putString("mode", mode)
            .putInt("temp", temp)
            .apply()
        changement(c)
    }

    fun allume(c: Context) = p(c).getBoolean("on", false)

    /** Correction ou action à la main (appli) : pas d'IR, on note seulement l'état supposé. */
    fun setOn(c: Context, on: Boolean) {
        val e = p(c).edit().putBoolean("on", on).putLong("manuel_jusqua", System.currentTimeMillis() + MANUEL_MS)
        if (!on) {
            e.putString("phase", "idle").putLong("dernier_off", System.currentTimeMillis()).putLong("minuteur_fin", 0)
            annuler(c, CODE_MIN_OFF)
        }
        e.apply()
        changement(c)
    }

    private fun motif(c: Context, cle: String): IntArray? {
        val s = p(c).getString(cle, "") ?: ""
        if (s.isEmpty()) return null
        return try {
            s.split(",").map { it.trim().toInt() }.toIntArray()
        } catch (e: NumberFormatException) {
            null
        }
    }

    private fun emettre(c: Context, cle: String): Boolean {
        val ir = c.getSystemService(Context.CONSUMER_IR_SERVICE) as? ConsumerIrManager
        if (ir == null || !ir.hasIrEmitter()) {
            journal(c, "IR not sent: no IR blaster")
            return false
        }
        val m = motif(c, cle)
        if (m == null) {
            journal(c, "IR not sent: no frame stored (open the AC card once)")
            return false
        }
        return try {
            ir.transmit(p(c).getInt("freq", 38000), m) // une seule fois : la touche power est une bascule
            journal(c, "IR sent ($cle)")
            true
        } catch (e: Exception) {
            journal(c, "IR error: $e")
            false
        }
    }

    @Synchronized
    fun allumer(c: Context, cle: String = "m_power"): Boolean {
        if (allume(c)) {
            journal(c, "ON skipped: AC already assumed on (no IR, power is a toggle)")
            return false
        }
        if (!emettre(c, cle)) return false
        p(c).edit().putBoolean("on", true).apply()
        return true
    }

    @Synchronized
    fun eteindre(c: Context): Boolean {
        if (!allume(c)) {
            journal(c, "OFF skipped: AC already assumed off (no IR, power is a toggle)")
            return false
        }
        if (!emettre(c, "m_power")) return false
        marquerEteinte(c)
        return true
    }

    /**
     * La clim est considérée éteinte : on = false, plus de minuteur ni de phase automatique en cours
     * (sinon le PC et l'ESP32 afficheraient une clim « fantôme » avec un reste de compte à rebours).
     */
    private fun marquerEteinte(c: Context) {
        p(c).edit()
            .putBoolean("on", false)
            .putString("phase", "idle")
            .putLong("minuteur_fin", 0)
            .putLong("dernier_off", System.currentTimeMillis())
            .apply()
    }

    // ------------------------------------------------------------------ alarmes
    private fun intention(c: Context, code: Int): PendingIntent =
        PendingIntent.getBroadcast(
            c, code,
            Intent(c, ClimReceiver::class.java).setAction("dadou.clim.$code").putExtra("code", code),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

    /** Ce qu'Android affiche pour l'alarme (icône réveil) : ouvre l'app. */
    private fun ouvrirApp(c: Context): PendingIntent = PendingIntent.getActivity(
        c, 300,
        Intent(c, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
    )

    /**
     * Heure fixe (plage ON/OFF, minuteur) : setAlarmClock, le plus fiable sur Xiaomi/HyperOS. C'est un
     * réveil pour le système : ni Doze ni l'économie de batterie ne le retardent.
     */
    fun armerHeureFixe(c: Context, code: Int, quand: Long) {
        val am = c.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        try {
            am.setAlarmClock(AlarmManager.AlarmClockInfo(quand, ouvrirApp(c)), intention(c, code))
            journal(c, "Armed $code for ${heure(quand, "dd/MM HH:mm:ss")}")
        } catch (e: SecurityException) {
            // alarmes exactes refusées : mieux vaut une alarme un peu en retard que pas d'alarme
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, quand, intention(c, code))
            journal(c, "Exact alarms refused: $code armed inexact for ${heure(quand, "dd/MM HH:mm:ss")}")
        }
    }

    /** Alarme de fond (republication) : pas besoin de réveil à l'heure pile. */
    fun programmer(c: Context, code: Int, quand: Long) {
        val am = c.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        if (Build.VERSION.SDK_INT >= 31 && !am.canScheduleExactAlarms()) {
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, quand, intention(c, code))
        } else {
            am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, quand, intention(c, code))
        }
    }

    fun annuler(c: Context, code: Int) {
        (c.getSystemService(Context.ALARM_SERVICE) as AlarmManager).cancel(intention(c, code))
    }

    // ------------------------------------------------------------------ minuteur
    /** Heure de fin (ms) d'un minuteur : démarrage dans [delaiSecondes] puis [dureeSecondes] de marche. */
    fun finMinuteur(maintenant: Long, delaiSecondes: Int, dureeSecondes: Int): Long =
        maintenant + delaiSecondes * 1_000L + dureeSecondes * 1_000L

    /** « Marche pendant [dureeSecondes] secondes » (démarrage dans [delaiSecondes] s, 0 = tout de suite). */
    fun minuteur(c: Context, dureeSecondes: Int, delaiSecondes: Int): Boolean {
        if (dureeSecondes < 1) return false
        val maintenant = System.currentTimeMillis()
        annuler(c, CODE_MIN_ON)
        annuler(c, CODE_MIN_OFF)
        val debut = maintenant + delaiSecondes * 1_000L
        val fin = finMinuteur(maintenant, delaiSecondes, dureeSecondes)
        if (delaiSecondes <= 0) {
            if (!allume(c) && !allumer(c)) return false
            p(c).edit().putLong("minuteur_debut", 0).apply()
        } else {
            armerHeureFixe(c, CODE_MIN_ON, debut)
            p(c).edit().putLong("minuteur_debut", debut).apply()
        }
        p(c).edit().putLong("minuteur_fin", fin).apply()
        armerHeureFixe(c, CODE_MIN_OFF, fin)
        changement(c)
        return true
    }

    fun annulerMinuteur(c: Context) {
        annuler(c, CODE_MIN_ON)
        annuler(c, CODE_MIN_OFF)
        p(c).edit().putLong("minuteur_fin", 0).putLong("minuteur_debut", 0).apply()
        changement(c)
    }

    // ------------------------------------------------------------------ plage horaire
    private fun fen(c: Context): JSONObject? = p(c).getString("fen", null)?.let { JSONObject(it) }

    fun fenetre(c: Context, actif: Boolean, de: Int, a: Int) {
        p(c).edit().putString("fen", JSONObject().put("actif", actif).put("de", de).put("a", a).toString()).apply()
        annuler(c, CODE_FEN_ON)
        annuler(c, CODE_FEN_OFF)
        journal(c, "Window ${if (actif) "enabled" else "disabled"}: on $de off $a (minutes)")
        armerFenetre(c)
        changement(c) // Phase 14 : l'écran de l'ESP32 sait qu'une plage horaire est active
    }

    /** Arme les deux alarmes de la plage à leur prochaine occurrence (modification, boot, ouverture de l'app). */
    fun armerFenetre(c: Context) {
        rearmerFenetre(c, CODE_FEN_ON)
        rearmerFenetre(c, CODE_FEN_OFF)
    }

    private fun rearmerFenetre(c: Context, code: Int) {
        val f = fen(c) ?: return
        if (!f.optBoolean("actif")) return
        val minutes = f.optInt(if (code == CODE_FEN_ON) "de" else "a")
        armerHeureFixe(c, code, Horaire.prochaine(System.currentTimeMillis(), minutes))
    }

    // ------------------------------------------------------------------ réception des alarmes
    fun executer(c: Context, code: Int) {
        if (code == CODE_GARDIEN) {
            journal(c, "Watchdog: service was killed, restarting")
        } else if (code != CODE_REPUB) {
            journal(c, "Alarm $code fired (assumed ${if (allume(c)) "on" else "off"})")
        }
        // la prochaine occurrence d'abord : quoi qu'il arrive à l'IR, la plage de demain reste armée
        if (code == CODE_FEN_ON || code == CODE_FEN_OFF) rearmerFenetre(c, code)
        when (code) {
            CODE_MIN_OFF -> {
                p(c).edit().putLong("minuteur_fin", 0).apply()
                if (eteindre(c)) {
                    notifier(c, "Timer finished: AC turned off")
                } else {
                    // IR impossible ou clim déjà supposée éteinte : le minuteur est fini quand même,
                    // l'état passe à « off » et le PC l'apprend tout de suite
                    marquerEteinte(c)
                }
            }
            CODE_REPUB -> Unit // rien à faire : la republication a lieu juste après
            CODE_MIN_ON -> if (allumer(c)) notifier(c, "Timer: AC turned on")
            CODE_FEN_ON -> if (allumer(c)) notifier(c, "Schedule: AC turned on")
            CODE_FEN_OFF -> if (eteindre(c)) notifier(c, "Schedule: AC turned off")
        }
        changement(c, attendre = true) // dans le fil du récepteur : l'envoi finit avant la fin de l'alarme
    }

    // ------------------------------------------------------------------ boutons de la notification
    fun actionEteindre(c: Context) {
        val ok = eteindre(c)
        annuler(c, CODE_MIN_ON)
        annuler(c, CODE_MIN_OFF)
        // priorité manuelle : l'automatisme ne relance pas tout de suite ce qu'on vient de couper
        p(c).edit()
            .putLong("minuteur_debut", 0)
            .putLong("manuel_jusqua", System.currentTimeMillis() + MANUEL_MS)
            .apply()
        journal(c, "Notification: turn off (IR sent: $ok)")
        changement(c, attendre = true)
    }

    fun actionPauseAuto(c: Context) {
        p(c).edit().putLong("auto_pause_jusqua", System.currentTimeMillis() + PAUSE_AUTO_MS).apply()
        journal(c, "Notification: auto paused for 30 min")
        changement(c, attendre = true)
    }

    /** Après un redémarrage du téléphone ou une mise à jour de l'app. */
    fun rearmer(c: Context) {
        val pr = p(c)
        val maintenant = System.currentTimeMillis()
        val debut = pr.getLong("minuteur_debut", 0)
        if (debut > maintenant) armerHeureFixe(c, CODE_MIN_ON, debut)
        val fin = pr.getLong("minuteur_fin", 0)
        if (fin > 0) armerHeureFixe(c, CODE_MIN_OFF, max(fin, maintenant + 5_000))
        armerFenetre(c)
        annuler(c, CODE_AUTO) // ancienne alarme répétée : l'automatisme tourne dans ClimService
        changement(c) // relance le service et la republication
    }

    // ------------------------------------------------------------------ service et notification
    private fun autoActif(c: Context) =
        p(c).getString("auto", null)?.let { JSONObject(it).optBoolean("actif") } ?: false

    /** Quelque chose à surveiller ? Le service tourne tant que c'est vrai. */
    fun actif(c: Context): Boolean {
        val pr = p(c)
        return pr.getLong("minuteur_fin", 0) > 0 || pr.getLong("minuteur_debut", 0) > 0 ||
            fen(c)?.optBoolean("actif") == true || autoActif(c)
    }

    /** L'état a changé : démarre / arrête le service (sa notification suit) et prévient le PC. */
    fun changement(c: Context, attendre: Boolean = false) {
        synchroService(c)
        publier(c, attendre)
    }

    /**
     * HyperOS tue le service quand l'app est balayée des récents, sans rappel ni redémarrage. Tant
     * qu'il vit, le service repousse cette alarme ; elle ne sonne donc que s'il est mort, et executer()
     * le relance. Les alarmes survivent à ce kill : vu sur le téléphone (am_proc_start … broadcast).
     */
    fun armerGardien(c: Context) = programmer(c, CODE_GARDIEN, System.currentTimeMillis() + GARDIEN_MS)

    private fun synchroService(c: Context) {
        val intention = Intent(c, ClimService::class.java)
        if (!actif(c)) {
            annuler(c, CODE_GARDIEN)
            c.stopService(intention)
            return
        }
        armerGardien(c)
        try {
            ContextCompat.startForegroundService(c, intention)
        } catch (e: IllegalStateException) {
            // Android refuse le démarrage en arrière-plan : les alarmes d'heures fixes restent armées
            journal(c, "Service start refused: $e")
        }
    }

    /** Ce que montre la notification. Comparable : pas de mise à jour si rien n'a changé. */
    data class VueNotif(
        val titre: String,
        val lignes: List<String>,
        val compteFin: Long,
        val on: Boolean,
        val minuteur: Boolean,
        val auto: Boolean,
    )

    private fun prochainTexte(c: Context, maintenant: Long): String {
        val f = fen(c) ?: return ""
        if (!f.optBoolean("actif")) return ""
        val (on, quand) = Horaire.prochainEvenement(maintenant, f.optInt("de"), f.optInt("a"))
        return "Next: ${if (on) "ON" else "OFF"} ${heure(quand)}"
    }

    private fun texteAuto(c: Context, maintenant: Long): String {
        val pause = p(c).getLong("auto_pause_jusqua", 0)
        if (pause > maintenant) return "Auto: paused until ${heure(pause)}"
        val m = derniereMesure
            ?: return "Auto: room -- (no sensor or PC)"
        val h = if (m.h >= 0) "%d %%".format(Locale.US, m.h.toInt()) else "-- %"
        val phase = when (p(c).getString("phase", "idle")) {
            "cool" -> "cooling"
            "dry" -> "drying"
            else -> "waiting" + if (autoRaison.isEmpty()) "" else " ($autoRaison)"
        }
        return "Auto: room %.1f° %s — %s".format(Locale.US, m.t, h, phase)
    }

    fun vueNotif(c: Context): VueNotif {
        val pr = p(c)
        val maintenant = System.currentTimeMillis()
        val on = allume(c)
        val phase = pr.getString("phase", "idle") ?: "idle"
        val mode = if (phase == "dry" && on) "dry" else (pr.getString("mode", "cool") ?: "cool")
        val titre = if (on) {
            "${mode.replaceFirstChar { it.uppercase() }} ${pr.getInt("temp", 24)}°C on"
        } else {
            "Off"
        }
        val lignes = mutableListOf<String>()
        val debut = pr.getLong("minuteur_debut", 0)
        val finMinuteur = pr.getLong("minuteur_fin", 0)
        val minuteur = finMinuteur > maintenant
        if (debut > maintenant) lignes.add("Timer: on at ${heure(debut)}")
        if (minuteur) lignes.add("Timer: off at ${heure(finMinuteur)}")
        prochainTexte(c, maintenant).takeIf { it.isNotEmpty() }?.let { lignes.add(it) }
        val auto = autoActif(c)
        if (auto) lignes.add(texteAuto(c, maintenant))
        val finAuto = if (phase != "idle" && on) pr.getLong("auto_fin", 0) else 0L
        val compte = when {
            minuteur && on -> finMinuteur
            debut > maintenant -> debut
            finAuto > maintenant -> finAuto
            else -> 0L
        }
        return VueNotif(titre, lignes, compte, on, minuteur || debut > maintenant, auto)
    }

    // ------------------------------------------------------------------ pour l'app
    fun etat(c: Context): Map<String, Any> {
        val pr = p(c)
        val am = c.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val f = fen(c)
        // clim éteinte : jamais de compte à rebours affiché (pas d'état figé)
        return mapOf(
            "on" to allume(c),
            "minuteurFin" to (if (allume(c)) pr.getLong("minuteur_fin", 0) else 0L),
            "phase" to (pr.getString("phase", "idle") ?: "idle"),
            "autoFin" to pr.getLong("auto_fin", 0),
            "exact" to (Build.VERSION.SDK_INT < 31 || am.canScheduleExactAlarms()),
            // Phase 15 : l'app lit les réglages ici, ClimPlan reste la seule source de vérité
            "service" to ClimService.enCours,
            "fenActif" to (f?.optBoolean("actif") ?: false),
            "fenConnue" to (f != null),
            "fenDe" to (f?.optInt("de") ?: 0),
            "fenA" to (f?.optInt("a") ?: 0),
            "auto" to (pr.getString("auto", "") ?: ""),
            "autoPause" to pr.getLong("auto_pause_jusqua", 0),
            "autoTexte" to texteAuto(c, System.currentTimeMillis()),
            "prochain" to prochainTexte(c, System.currentTimeMillis()),
            "journal" to (pr.getString("journal", "") ?: ""),
        )
    }

    /**
     * Dit au PC (agent) où en est la clim : il l'affiche sur l'écran de l'ESP32.
     * Le service republie toutes les 30 s (10 s après un échec) : un PC allumé après coup retrouve le
     * minuteur en cours. Service arrêté mais clim allumée : l'alarme CODE_REPUB prend le relais.
     * Renvoie false si le PC n'a pas répondu.
     */
    fun publierMaintenant(c: Context): Boolean {
        val fp = c.getSharedPreferences(VeilleurPC.PREFS, Context.MODE_PRIVATE)
        val adresse = fp.getString("flutter.adresse", "") ?: ""
        val token = fp.getString("flutter.token", "") ?: ""
        if (adresse.isEmpty() || token.isEmpty()) return true
        val pr = p(c)
        val maintenant = System.currentTimeMillis()
        val phase = pr.getString("phase", "idle") ?: "idle"
        var fin = pr.getLong("minuteur_fin", 0)
        if (fin <= maintenant && phase != "idle") fin = pr.getLong("auto_fin", 0)
        // temps restant en SECONDES (Phase 14) : l'agent et l'ESP32 l'affichent en h:mm:ss / min.
        // Clim éteinte : toujours 0 (jamais un reste de compte à rebours fantôme).
        val reste = if (allume(c) && fin > maintenant) ((fin - maintenant + 999L) / 1_000L).toInt() else 0
        val mode = if (phase == "dry" && allume(c)) "dry" else (pr.getString("mode", "cool") ?: "cool")
        // plage horaire active : « de-a » en minutes depuis minuit (ex. 1140-1260), sinon 0
        val f = fen(c)
        val plage = if (f != null && f.optBoolean("actif")) "${f.optInt("de")}-${f.optInt("a")}" else "0"
        val chemin = "/clim_maj?on=${if (allume(c)) 1 else 0}&mode=$mode&temp=${pr.getInt("temp", 24)}" +
            "&reste=$reste&auto=${if (autoActif(c)) 1 else 0}&plage=$plage"
        return try {
            VeilleurPC.lire(adresse, token, chemin)
            true
        } catch (e: Exception) {
            false // PC éteint ou injoignable
        }
    }

    /** [attendre] = false : l'envoi part dans un fil (appel depuis l'app) ; true : dans le fil courant. */
    fun publier(c: Context, attendre: Boolean = false) {
        val relais = allume(c) && !actif(c) // personne d'autre ne republiera : alarme de secours
        if (relais) programmer(c, CODE_REPUB, System.currentTimeMillis() + REPUB_MS) else annuler(c, CODE_REPUB)
        val envoi = {
            if (!publierMaintenant(c) && relais) {
                programmer(c, CODE_REPUB, System.currentTimeMillis() + REPUB_RETENTE_MS)
            }
        }
        if (attendre) envoi() else Thread { envoi() }.start()
    }

    // ------------------------------------------------------------------ automatisme (étape F)
    fun setAuto(c: Context, json: String) {
        val etaitActif = autoActif(c)
        val e = p(c).edit().putString("auto", json).putLong("auto_pause_jusqua", 0)
        // on (ré)active Auto : c'est une demande explicite, l'action manuelle d'avant ne compte plus
        if (!etaitActif && JSONObject(json).optBoolean("actif")) e.remove("manuel_jusqua")
        e.apply()
        annuler(c, CODE_AUTO)
        autoProchain = 0L // vérification au prochain tour du service
        if (!JSONObject(json).optBoolean("actif")) {
            p(c).edit().putString("phase", "idle").apply()
            derniereMesure = null
        }
        changement(c)
    }

    /** Appelé par ClimService : un passage de l'automatisme toutes les 60 s. */
    fun ticAuto(c: Context) {
        val maintenant = System.currentTimeMillis()
        if (maintenant < autoProchain) return
        autoProchain = maintenant + AUTO_MS
        val avant = allume(c)
        auto(c)
        if (allume(c) != avant) publier(c, attendre = true)
    }

    private fun lireMesure(c: Context): JSONObject? {
        val fp = c.getSharedPreferences(VeilleurPC.PREFS, Context.MODE_PRIVATE)
        val adresse = fp.getString("flutter.adresse", "") ?: ""
        val token = fp.getString("flutter.token", "") ?: ""
        if (adresse.isEmpty() || token.isEmpty()) return null
        return try {
            val m = JSONObject(VeilleurPC.lire(adresse, token, "/clim_mesure"))
            if (m.optBoolean("ok")) m else null
        } catch (e: Exception) {
            null
        }
    }

    private fun auto(c: Context) {
        val cfg = p(c).getString("auto", null)?.let { JSONObject(it) } ?: return
        if (!cfg.optBoolean("actif")) return
        val mesure = lireMesure(c)
        if (mesure == null) { // capteur ou PC injoignable : on ne fait rien
            derniereMesure = null
            return
        }
        val t = mesure.optDouble("t")
        val h = mesure.optDouble("h", -1.0) // -1 : pas d'humidité (AHT20 absent, BMP280 seul)
        derniereMesure = Mesure(t, h)
        if (System.currentTimeMillis() < p(c).getLong("auto_pause_jusqua", 0)) return
        val tOn = cfg.optDouble("t_on", 28.0)
        val tOff = cfg.optDouble("t_off", 25.0)
        val base = cfg.optInt("base", 30)
        val extra = cfg.optInt("extra", 3)
        val hDry = cfg.optInt("h_dry", 70)
        val dryMin = cfg.optInt("dry_min", 45)
        val maintenant = System.currentTimeMillis()
        val pr = p(c)
        when (pr.getString("phase", "idle")) {
            "cool" -> if (t <= tOff || maintenant >= pr.getLong("auto_fin", 0)) {
                if (eteindre(c)) notifier(c, "AC off (auto): %.1f °C".format(t))
                pr.edit().putString("phase", "idle").apply()
            }
            "dry" -> if ((h >= 0 && h <= hDry - 8) || maintenant >= pr.getLong("auto_fin", 0)) {
                if (eteindre(c)) notifier(c, "AC off (auto): humidity %d %%".format(h.toInt()))
                pr.edit().putString("phase", "idle").apply()
            }
            else -> {
                val dernierOff = pr.getLong("dernier_off", 0)
                val manuel = pr.getLong("manuel_jusqua", 0)
                val voulu = AutoRegles.mode(t, h, tOn, hDry)
                // même logique qu'avant : déjà allumée à la main, priorité manuelle, pause du compresseur
                val raison = when (AutoRegles.attente(allume(c), maintenant, manuel, dernierOff, PAUSE_COMPRESSEUR_MS)) {
                    "on" -> "AC on by hand"
                    "manuel" -> "manual action, until ${heure(manuel)}"
                    "compresseur" -> "compressor rest, until ${heure(dernierOff + PAUSE_COMPRESSEUR_MS)}"
                    else -> ""
                }
                val affiche = if (voulu.isEmpty()) "" else raison
                if (affiche != autoRaison) {
                    autoRaison = affiche
                    if (affiche.isNotEmpty()) journal(c, "Auto waiting: $affiche")
                }
                if (raison.isNotEmpty()) return
                when (voulu) {
                    "cool" -> {
                        // plus il fait chaud, plus elle tourne longtemps
                        val minutes = min(180, max(10, base + (extra * (t - tOn)).toInt()))
                        if (allumer(c)) {
                            pr.edit().putString("phase", "cool").putLong("auto_fin", maintenant + minutes * 60_000L).apply()
                            journal(c, "Auto: cool, %.1f °C, %d min".format(Locale.US, t, minutes))
                            notifier(c, "AC on (auto): %.1f °C, off in %d min".format(t, minutes))
                        }
                    }
                    "dry" -> if (allumer(c, "m_dry_power")) {
                        pr.edit().putString("phase", "dry").putLong("auto_fin", maintenant + dryMin * 60_000L).apply()
                        journal(c, "Auto: dry, %d %%, %d min".format(Locale.US, h.toInt(), dryMin))
                        notifier(c, "AC on (Dry): humidity %d %%, off in %d min".format(h.toInt(), dryMin))
                    }
                }
            }
        }
    }

    private fun notifier(c: Context, texte: String) {
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(c, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) return
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val canal = NotificationChannel(CANAL, "Air conditioner", NotificationManager.IMPORTANCE_LOW)
            c.getSystemService(NotificationManager::class.java).createNotificationChannel(canal)
        }
        val n = NotificationCompat.Builder(c, CANAL)
            .setSmallIcon(R.drawable.w_power)
            .setContentTitle("Air conditioner")
            .setContentText(texte)
            .setContentIntent(ouvrirApp(c))
            .setAutoCancel(true)
            .build()
        try {
            NotificationManagerCompat.from(c).notify(ID_NOTIF, n)
        } catch (e: SecurityException) {
            // permission retirée entre-temps
        }
    }
}

/** Reçoit les alarmes (minuteur, plage horaire, automatisme) et le redémarrage du téléphone. */
class ClimReceiver : BroadcastReceiver() {
    companion object {
        const val ACTION_OFF = "dadou.clim.action.OFF"
        const val ACTION_ANNULER = "dadou.clim.action.ANNULER"
        const val ACTION_PAUSE = "dadou.clim.action.PAUSE"
    }

    override fun onReceive(context: Context, intent: Intent) {
        val appli = context.applicationContext
        when (intent.action) {
            Intent.ACTION_BOOT_COMPLETED, Intent.ACTION_MY_PACKAGE_REPLACED,
            "android.intent.action.QUICKBOOT_POWERON",
            Intent.ACTION_TIMEZONE_CHANGED, Intent.ACTION_TIME_CHANGED -> {
                ClimPlan.journal(appli, "Re-arm after ${intent.action}")
                ClimPlan.rearmer(appli)
                return
            }
        }
        val code = intent.getIntExtra("code", 0)
        val attente = goAsync()
        Thread {
            try {
                when (intent.action) {
                    ACTION_OFF -> ClimPlan.actionEteindre(appli)
                    ACTION_ANNULER -> ClimPlan.annulerMinuteur(appli)
                    ACTION_PAUSE -> ClimPlan.actionPauseAuto(appli)
                    else -> ClimPlan.executer(appli, code)
                }
            } catch (e: Exception) {
                // une alarme ratée ne doit jamais faire planter l'app
                ClimPlan.journal(appli, "Alarm $code error: $e")
            } finally {
                attente.finish()
            }
        }.start()
    }
}
