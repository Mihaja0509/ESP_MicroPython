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
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import org.json.JSONObject
import java.util.Calendar
import kotlin.math.max
import kotlin.math.min

/**
 * Clim programmée (Phase 13) : minuteur, plage horaire et mode automatique (capteur de la pièce).
 * Les trames IR (durées en µs) sont calculées par Dart (lib/clim_ir.dart) et rangées ici.
 * Alarmes exactes -> ClimReceiver -> executer(). État dans les préférences « clim_plan ».
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
    private const val PAUSE_COMPRESSEUR_MS = 3 * 60_000L // le compresseur ne redémarre pas avant 3 min
    private const val MANUEL_MS = 30 * 60_000L           // après une action à la main, l'auto se tait

    private fun p(c: Context) = c.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    // ------------------------------------------------------------------ trames et état
    fun trames(c: Context, frequence: Int, power: List<Int>, dryPower: List<Int>, mode: String, temp: Int) {
        p(c).edit()
            .putInt("freq", frequence)
            .putString("m_power", power.joinToString(","))
            .putString("m_dry_power", dryPower.joinToString(","))
            .putString("mode", mode)
            .putInt("temp", temp)
            .apply()
        publier(c)
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
        publier(c)
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
        val ir = c.getSystemService(Context.CONSUMER_IR_SERVICE) as? ConsumerIrManager ?: return false
        if (!ir.hasIrEmitter()) return false
        val m = motif(c, cle) ?: return false
        ir.transmit(p(c).getInt("freq", 38000), m) // une seule fois : la touche power est une bascule
        return true
    }

    fun allumer(c: Context, cle: String = "m_power"): Boolean {
        if (allume(c)) return false
        if (!emettre(c, cle)) return false
        p(c).edit().putBoolean("on", true).apply()
        return true
    }

    fun eteindre(c: Context): Boolean {
        if (!allume(c)) return false
        if (!emettre(c, "m_power")) return false
        p(c).edit().putBoolean("on", false).putLong("dernier_off", System.currentTimeMillis()).apply()
        return true
    }

    // ------------------------------------------------------------------ alarmes
    private fun intention(c: Context, code: Int): PendingIntent =
        PendingIntent.getBroadcast(
            c, code,
            Intent(c, ClimReceiver::class.java).setAction("dadou.clim.$code").putExtra("code", code),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

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

    /** Prochaine occurrence (ms) d'une heure du jour exprimée en minutes depuis minuit. */
    private fun prochaine(minutes: Int): Long {
        val cal = Calendar.getInstance()
        cal.set(Calendar.HOUR_OF_DAY, minutes / 60)
        cal.set(Calendar.MINUTE, minutes % 60)
        cal.set(Calendar.SECOND, 0)
        cal.set(Calendar.MILLISECOND, 0)
        if (cal.timeInMillis <= System.currentTimeMillis() + 1000) cal.add(Calendar.DAY_OF_YEAR, 1)
        return cal.timeInMillis
    }

    // ------------------------------------------------------------------ minuteur
    /** « Marche pendant [duree] min » (démarrage dans [delai] min, 0 = tout de suite). */
    fun minuteur(c: Context, duree: Int, delai: Int): Boolean {
        val maintenant = System.currentTimeMillis()
        annuler(c, CODE_MIN_ON)
        annuler(c, CODE_MIN_OFF)
        val debut = maintenant + delai * 60_000L
        val fin = debut + duree * 60_000L
        if (delai <= 0) {
            if (!allume(c) && !allumer(c)) return false
            p(c).edit().putLong("minuteur_debut", 0).apply()
        } else {
            programmer(c, CODE_MIN_ON, debut)
            p(c).edit().putLong("minuteur_debut", debut).apply()
        }
        p(c).edit().putLong("minuteur_fin", fin).apply()
        programmer(c, CODE_MIN_OFF, fin)
        publier(c)
        return true
    }

    fun annulerMinuteur(c: Context) {
        annuler(c, CODE_MIN_ON)
        annuler(c, CODE_MIN_OFF)
        p(c).edit().putLong("minuteur_fin", 0).putLong("minuteur_debut", 0).apply()
        publier(c)
    }

    // ------------------------------------------------------------------ plage horaire
    private fun fen(c: Context): JSONObject? = p(c).getString("fen", null)?.let { JSONObject(it) }

    fun fenetre(c: Context, actif: Boolean, de: Int, a: Int) {
        p(c).edit().putString("fen", JSONObject().put("actif", actif).put("de", de).put("a", a).toString()).apply()
        annuler(c, CODE_FEN_ON)
        annuler(c, CODE_FEN_OFF)
        if (actif) {
            programmer(c, CODE_FEN_ON, prochaine(de))
            programmer(c, CODE_FEN_OFF, prochaine(a))
        }
    }

    private fun rearmerFenetre(c: Context, code: Int) {
        val f = fen(c) ?: return
        if (!f.optBoolean("actif")) return
        programmer(c, code, prochaine(f.optInt(if (code == CODE_FEN_ON) "de" else "a")))
    }

    // ------------------------------------------------------------------ réception des alarmes
    fun executer(c: Context, code: Int) {
        when (code) {
            CODE_MIN_OFF -> {
                p(c).edit().putLong("minuteur_fin", 0).apply()
                if (eteindre(c)) notifier(c, "Timer finished: AC turned off")
            }
            CODE_MIN_ON -> if (allumer(c)) notifier(c, "Timer: AC turned on")
            CODE_FEN_ON -> {
                if (allumer(c)) notifier(c, "Schedule: AC turned on")
                rearmerFenetre(c, code)
            }
            CODE_FEN_OFF -> {
                if (eteindre(c)) notifier(c, "Schedule: AC turned off")
                rearmerFenetre(c, code)
            }
            CODE_AUTO -> auto(c)
        }
        publier(c)
    }

    /** Après un redémarrage du téléphone ou une mise à jour de l'app. */
    fun rearmer(c: Context) {
        val pr = p(c)
        val maintenant = System.currentTimeMillis()
        val debut = pr.getLong("minuteur_debut", 0)
        if (debut > maintenant) programmer(c, CODE_MIN_ON, debut)
        val fin = pr.getLong("minuteur_fin", 0)
        if (fin > 0) programmer(c, CODE_MIN_OFF, max(fin, maintenant + 5_000))
        fen(c)?.let {
            if (it.optBoolean("actif")) {
                programmer(c, CODE_FEN_ON, prochaine(it.optInt("de")))
                programmer(c, CODE_FEN_OFF, prochaine(it.optInt("a")))
            }
        }
        pr.getString("auto", null)?.let {
            if (JSONObject(it).optBoolean("actif")) programmer(c, CODE_AUTO, maintenant + 30_000)
        }
    }

    // ------------------------------------------------------------------ pour l'app
    fun etat(c: Context): Map<String, Any> {
        val pr = p(c)
        val am = c.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        return mapOf(
            "on" to allume(c),
            "minuteurFin" to pr.getLong("minuteur_fin", 0),
            "phase" to (pr.getString("phase", "idle") ?: "idle"),
            "autoFin" to pr.getLong("auto_fin", 0),
            "exact" to (Build.VERSION.SDK_INT < 31 || am.canScheduleExactAlarms()),
        )
    }

    /** Dit au PC (agent) où en est la clim : il l'affiche sur l'écran de l'ESP32. Sans bloquer. */
    fun publier(c: Context) {
        val fp = c.getSharedPreferences(VeilleurPC.PREFS, Context.MODE_PRIVATE)
        val adresse = fp.getString("flutter.adresse", "") ?: ""
        val token = fp.getString("flutter.token", "") ?: ""
        if (adresse.isEmpty() || token.isEmpty()) return
        val pr = p(c)
        val maintenant = System.currentTimeMillis()
        val phase = pr.getString("phase", "idle") ?: "idle"
        var fin = pr.getLong("minuteur_fin", 0)
        if (fin <= maintenant && phase != "idle") fin = pr.getLong("auto_fin", 0)
        val reste = if (fin > maintenant) ((fin - maintenant) / 60_000L + 1).toInt() else 0
        val mode = if (phase == "dry" && allume(c)) "dry" else (pr.getString("mode", "cool") ?: "cool")
        val auto = pr.getString("auto", null)?.let { JSONObject(it).optBoolean("actif") } ?: false
        val chemin = "/clim_maj?on=${if (allume(c)) 1 else 0}&mode=$mode&temp=${pr.getInt("temp", 24)}" +
            "&reste=$reste&auto=${if (auto) 1 else 0}"
        Thread {
            try {
                VeilleurPC.lire(adresse, token, chemin)
            } catch (e: Exception) {
                // PC éteint ou injoignable : tant pis, l'écran de l'ESP32 n'est qu'un plus
            }
        }.start()
    }

    // ------------------------------------------------------------------ automatisme (étape F)
    fun setAuto(c: Context, json: String) {
        p(c).edit().putString("auto", json).apply()
        annuler(c, CODE_AUTO)
        if (JSONObject(json).optBoolean("actif")) {
            programmer(c, CODE_AUTO, System.currentTimeMillis() + 5_000)
        } else {
            p(c).edit().putString("phase", "idle").apply()
        }
        publier(c)
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
        programmer(c, CODE_AUTO, System.currentTimeMillis() + 60_000) // prochain passage dans 1 min
        val mesure = lireMesure(c) ?: return // capteur ou PC injoignable : on ne fait rien
        val t = mesure.optDouble("t")
        val h = mesure.optDouble("h")
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
            "dry" -> if (h <= hDry - 8 || maintenant >= pr.getLong("auto_fin", 0)) {
                if (eteindre(c)) notifier(c, "AC off (auto): humidity %d %%".format(h.toInt()))
                pr.edit().putString("phase", "idle").apply()
            }
            else -> {
                if (allume(c)) return // la clim tourne déjà (lancée à la main) : on n'y touche pas
                if (maintenant < pr.getLong("manuel_jusqua", 0)) return
                if (maintenant - pr.getLong("dernier_off", 0) < PAUSE_COMPRESSEUR_MS) return
                if (t >= tOn) {
                    // plus il fait chaud, plus elle tourne longtemps
                    val minutes = min(180, max(10, base + (extra * (t - tOn)).toInt()))
                    if (allumer(c)) {
                        pr.edit().putString("phase", "cool").putLong("auto_fin", maintenant + minutes * 60_000L).apply()
                        notifier(c, "AC on (auto): %.1f °C, off in %d min".format(t, minutes))
                    }
                } else if (h >= hDry) {
                    if (allumer(c, "m_dry_power")) {
                        pr.edit().putString("phase", "dry").putLong("auto_fin", maintenant + dryMin * 60_000L).apply()
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
        val ouvrir = PendingIntent.getActivity(
            c, 300,
            Intent(c, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val n = NotificationCompat.Builder(c, CANAL)
            .setSmallIcon(R.drawable.w_power)
            .setContentTitle("Air conditioner")
            .setContentText(texte)
            .setContentIntent(ouvrir)
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
    override fun onReceive(context: Context, intent: Intent) {
        val appli = context.applicationContext
        if (intent.action == Intent.ACTION_BOOT_COMPLETED || intent.action == Intent.ACTION_MY_PACKAGE_REPLACED) {
            ClimPlan.rearmer(appli)
            return
        }
        val code = intent.getIntExtra("code", 0)
        val attente = goAsync()
        Thread {
            try {
                ClimPlan.executer(appli, code)
            } catch (e: Exception) {
                // une alarme ratée ne doit jamais faire planter l'app
            } finally {
                attente.finish()
            }
        }.start()
    }
}
