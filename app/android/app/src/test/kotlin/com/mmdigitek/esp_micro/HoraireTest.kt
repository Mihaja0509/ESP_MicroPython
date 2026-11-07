package com.mmdigitek.esp_micro

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Calendar
import java.util.TimeZone

/** Lancer : dans app/android, gradlew :app:testDebugUnitTest */
class HoraireTest {
    private val fuseau = TimeZone.getTimeZone("Asia/Kuala_Lumpur")

    private fun instant(mois: Int, jour: Int, h: Int, m: Int): Long {
        val c = Calendar.getInstance(fuseau)
        c.clear()
        c.set(2026, mois, jour, h, m, 0)
        return c.timeInMillis
    }

    private fun instant(jour: Int, h: Int, m: Int) = instant(Calendar.NOVEMBER, jour, h, m)

    private fun min(h: Int, m: Int) = h * 60 + m

    @Test
    fun heureAVenirAujourdhui() {
        assertEquals(instant(7, 22, 30), Horaire.prochaine(instant(7, 20, 0), min(22, 30), fuseau))
    }

    @Test
    fun heurePasseeDemain() {
        assertEquals(instant(8, 22, 30), Horaire.prochaine(instant(7, 22, 31), min(22, 30), fuseau))
    }

    @Test
    fun heureExacteDemain() {
        // l'alarme vient de sonner : le réarmement ne doit pas resonner tout de suite
        assertEquals(instant(8, 22, 30), Horaire.prochaine(instant(7, 22, 30), min(22, 30), fuseau))
        assertEquals(instant(8, 22, 30), Horaire.prochaine(instant(7, 22, 30) + 500, min(22, 30), fuseau))
    }

    @Test
    fun changementDeMois() {
        assertEquals(
            instant(Calendar.DECEMBER, 1, 7, 0),
            Horaire.prochaine(instant(Calendar.NOVEMBER, 30, 7, 1), min(7, 0), fuseau),
        )
    }

    @Test
    fun plageNormale() {
        val de = min(22, 30)
        val a = min(23, 30)
        val avant = Horaire.prochainEvenement(instant(7, 20, 0), de, a, fuseau)
        assertTrue(avant.first)
        assertEquals(instant(7, 22, 30), avant.second)
        val dedans = Horaire.prochainEvenement(instant(7, 23, 0), de, a, fuseau)
        assertFalse(dedans.first)
        assertEquals(instant(7, 23, 30), dedans.second)
        val apres = Horaire.prochainEvenement(instant(7, 23, 45), de, a, fuseau)
        assertTrue(apres.first)
        assertEquals(instant(8, 22, 30), apres.second)
    }

    @Test
    fun plageQuiPasseMinuit() {
        val de = min(23, 0)
        val a = min(1, 0)
        val avant = Horaire.prochainEvenement(instant(7, 22, 0), de, a, fuseau)
        assertTrue(avant.first)
        assertEquals(instant(7, 23, 0), avant.second)
        // à 23:30 : extinction à 01:00 le LENDEMAIN
        val soir = Horaire.prochainEvenement(instant(7, 23, 30), de, a, fuseau)
        assertFalse(soir.first)
        assertEquals(instant(8, 1, 0), soir.second)
        // à 00:30 : extinction à 01:00 le jour même
        val nuit = Horaire.prochainEvenement(instant(8, 0, 30), de, a, fuseau)
        assertFalse(nuit.first)
        assertEquals(instant(8, 1, 0), nuit.second)
        // à 02:00 : allumage à 23:00 le jour même
        val matin = Horaire.prochainEvenement(instant(8, 2, 0), de, a, fuseau)
        assertTrue(matin.first)
        assertEquals(instant(8, 23, 0), matin.second)
    }

    @Test
    fun autoTemperatureSeuleSuffit() {
        assertEquals("cool", AutoRegles.mode(30.1, 66.0, 28.0, 70)) // 66 % n'empêche pas le froid
        assertEquals("cool", AutoRegles.mode(28.0, 40.0, 28.0, 70))
    }

    @Test
    fun autoHumiditeSeuleSuffit() {
        assertEquals("dry", AutoRegles.mode(25.0, 75.0, 28.0, 70))
        assertEquals("", AutoRegles.mode(25.0, 66.0, 28.0, 70))
        assertEquals("", AutoRegles.mode(25.0, -1.0, 28.0, 70))
    }

    @Test
    fun autoLesDeuxSeuilsLaTemperatureDabord() {
        assertEquals("cool", AutoRegles.mode(30.0, 75.0, 28.0, 70))
    }

    @Test
    fun autoRaisonsDAttente() {
        val pause = 180_000L
        assertEquals("on", AutoRegles.attente(true, 1_000_000, 0, 0, pause))
        assertEquals("manuel", AutoRegles.attente(false, 1_000_000, 1_000_001, 0, pause))
        assertEquals("compresseur", AutoRegles.attente(false, 1_000_000, 0, 900_000, pause))
        assertEquals("", AutoRegles.attente(false, 1_000_000, 1_000_000, 800_000, pause))
    }
}
