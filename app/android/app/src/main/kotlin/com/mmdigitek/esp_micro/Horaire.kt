package com.mmdigitek.esp_micro

import java.util.Calendar
import java.util.TimeZone

/** Calculs d'heures de la plage horaire (Phase 15), sans Android : testés dans src/test. */
object Horaire {
    /** Prochaine occurrence (ms) d'une heure du jour, en minutes depuis minuit. Heure passée : demain. */
    fun prochaine(maintenant: Long, minutes: Int, fuseau: TimeZone = TimeZone.getDefault()): Long {
        val cal = Calendar.getInstance(fuseau)
        cal.timeInMillis = maintenant
        cal.set(Calendar.HOUR_OF_DAY, minutes / 60)
        cal.set(Calendar.MINUTE, minutes % 60)
        cal.set(Calendar.SECOND, 0)
        cal.set(Calendar.MILLISECOND, 0)
        if (cal.timeInMillis <= maintenant + 1000) cal.add(Calendar.DAY_OF_YEAR, 1)
        return cal.timeInMillis
    }

    /** Prochain événement d'une plage : allumage ou extinction (vaut aussi pour 23:00 -> 01:00). */
    fun prochainEvenement(
        maintenant: Long,
        de: Int,
        a: Int,
        fuseau: TimeZone = TimeZone.getDefault(),
    ): Pair<Boolean, Long> {
        val on = prochaine(maintenant, de, fuseau)
        val off = prochaine(maintenant, a, fuseau)
        return if (on <= off) Pair(true, on) else Pair(false, off)
    }
}

/** Décisions de l'automatisme (Phase 15), sans Android : testées dans src/test. */
object AutoRegles {
    /** Ce qui empêche de démarrer : "on" (déjà allumée), "manuel", "compresseur", ou "" si rien. */
    fun attente(on: Boolean, maintenant: Long, manuelJusqua: Long, dernierOff: Long, pauseCompresseurMs: Long): String =
        when {
            on -> "on"
            maintenant < manuelJusqua -> "manuel"
            maintenant - dernierOff < pauseCompresseurMs -> "compresseur"
            else -> ""
        }

    /**
     * Le mode à lancer. Température et humidité sont jugées chacune contre son seuil ; la clim n'a qu'un
     * mode à la fois, la température passe d'abord. h < 0 : humidité inconnue, jamais de Dry.
     */
    fun mode(t: Double, h: Double, tOn: Double, hDry: Int): String = when {
        t >= tOn -> "cool"
        h >= 0 && h >= hDry -> "dry"
        else -> ""
    }
}
