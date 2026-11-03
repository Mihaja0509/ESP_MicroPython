package com.mmdigitek.esp_micro

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.widget.Toast
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.Constraints
import androidx.work.Data
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit
import kotlin.math.abs

/**
 * Notification « PC inutilisé » (Phase 11).
 * Toutes les 15 min, Android lance ce travail : il demande au PC GET /etat_court (avec le token
 * d'appairage de l'app). Si personne n'a touché le PC depuis le seuil choisi dans l'app (30 min par
 * défaut), sans jeu, vidéo ni arrêt en cours, une notification propose « Éteindre ».
 * Une seule notification par période d'inactivité.
 */
class VeilleurPC(context: Context, params: WorkerParameters) : Worker(context, params) {

    override fun doWork(): Result {
        val prefs = applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val adresse = prefs.getString("flutter.adresse", "") ?: ""
        val token = prefs.getString("flutter.token", "") ?: ""
        val test = inputData.getBoolean("test", false)
        if (adresse.isEmpty() || token.isEmpty()) return Result.success()
        if (!test && !prefs.getBoolean("flutter.notif_actif", false)) return Result.success()
        val seuil = prefs.getLong("flutter.notif_minutes", 30L).toInt()
        val etat = try {
            JSONObject(lire(adresse, token, "/etat_court"))
        } catch (e: Exception) {
            if (test) notifier(applicationContext, "PC injoignable",
                "Éteint, en veille ou Tailscale coupé ?", false)
            return Result.success()
        }
        val repos = etat.optInt("repos_min", 0)
        val occupe = etat.optString("jeu").isNotEmpty() || etat.optString("video").isNotEmpty() ||
            etat.optInt("arret", -1) > 0
        if (test) {
            notifier(applicationContext, "Test : PC inutilisé depuis ${duree(repos)}",
                "Voici à quoi ressemblera la notification.", true)
            return Result.success()
        }
        val memoire = applicationContext.getSharedPreferences(MEMOIRE, Context.MODE_PRIVATE)
        if (repos < seuil || occupe) {
            memoire.edit().putLong("debut_notifie", 0L).apply()
            return Result.success()
        }
        // minute (depuis 1970) où l'inactivité a commencé : une seule notification par période
        val debut = System.currentTimeMillis() / 60000L - repos
        if (abs(memoire.getLong("debut_notifie", 0L) - debut) <= 3) return Result.success()
        memoire.edit().putLong("debut_notifie", debut).apply()
        val texte = if (etat.optBoolean("verrou")) "Le PC est verrouillé. Tu veux l'éteindre ?"
        else "Personne ne s'en sert. Tu veux l'éteindre ?"
        notifier(applicationContext, "PC inutilisé depuis ${duree(repos)}", texte, true)
        return Result.success()
    }

    companion object {
        const val PREFS = "FlutterSharedPreferences"
        private const val MEMOIRE = "dadou_veilleur"
        private const val TRAVAIL = "veilleur_pc"
        private const val CANAL = "pc_inutilise"
        const val ID_NOTIF = 4201
        const val ACTION_ETEINDRE = "com.mmdigitek.esp_micro.ETEINDRE_PC"
        private const val PORT = 8765

        fun duree(minutes: Int): String =
            if (minutes < 60) "$minutes min" else "${minutes / 60} h ${"%02d".format(minutes % 60)}"

        /** Lance ou arrête la vérification toutes les 15 min. */
        fun programmer(context: Context, actif: Boolean) {
            val wm = WorkManager.getInstance(context)
            if (!actif) {
                wm.cancelUniqueWork(TRAVAIL)
                return
            }
            val contraintes = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
            val travail = PeriodicWorkRequestBuilder<VeilleurPC>(15, TimeUnit.MINUTES)
                .setConstraints(contraintes)
                .build()
            wm.enqueueUniquePeriodicWork(TRAVAIL, ExistingPeriodicWorkPolicy.UPDATE, travail)
        }

        /** Vérification immédiate qui affiche toujours une notification (bouton « Tester »). */
        fun tester(context: Context) {
            val travail = OneTimeWorkRequestBuilder<VeilleurPC>()
                .setInputData(Data.Builder().putBoolean("test", true).build())
                .build()
            WorkManager.getInstance(context).enqueue(travail)
        }

        fun lire(adresse: String, token: String, chemin: String): String {
            val c = URL("http://$adresse:$PORT$chemin").openConnection() as HttpURLConnection
            c.connectTimeout = 5000
            c.readTimeout = 10000
            c.setRequestProperty("X-Token", token)
            try {
                if (c.responseCode != 200) throw IllegalStateException("HTTP ${c.responseCode}")
                return c.inputStream.bufferedReader().use { it.readText() }
            } finally {
                c.disconnect()
            }
        }

        fun notifier(context: Context, titre: String, texte: String, avecBouton: Boolean) {
            if (Build.VERSION.SDK_INT >= 33 &&
                ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) !=
                PackageManager.PERMISSION_GRANTED
            ) return
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val canal = NotificationChannel(CANAL, "PC inutilisé", NotificationManager.IMPORTANCE_DEFAULT)
                canal.description = "Prévient quand le PC reste allumé sans être utilisé"
                context.getSystemService(NotificationManager::class.java).createNotificationChannel(canal)
            }
            val ouvrir = PendingIntent.getActivity(
                context, 200,
                Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            val n = NotificationCompat.Builder(context, CANAL)
                .setSmallIcon(R.drawable.w_power)
                .setContentTitle(titre)
                .setContentText(texte)
                .setContentIntent(ouvrir)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            if (avecBouton) {
                val eteindre = PendingIntent.getBroadcast(
                    context, 201,
                    Intent(context, ActionNotification::class.java).setAction(ACTION_ETEINDRE),
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
                n.addAction(R.drawable.w_power, "Éteindre", eteindre)
            }
            try {
                NotificationManagerCompat.from(context).notify(ID_NOTIF, n.build())
            } catch (e: SecurityException) {
                // permission retirée entre-temps : rien à afficher
            }
        }
    }
}

/** Bouton « Éteindre » de la notification : envoie ARRET au PC (compte à rebours de 60 s). */
class ActionNotification : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != VeilleurPC.ACTION_ETEINDRE) return
        NotificationManagerCompat.from(context).cancel(VeilleurPC.ID_NOTIF)
        val prefs = context.getSharedPreferences(VeilleurPC.PREFS, Context.MODE_PRIVATE)
        val adresse = prefs.getString("flutter.adresse", "") ?: ""
        val token = prefs.getString("flutter.token", "") ?: ""
        val appli = context.applicationContext
        val attente = goAsync()
        Thread {
            val texte = try {
                VeilleurPC.lire(adresse, token, "/widget?ligne=ARRET").trim()
                    .ifEmpty { "Le PC s'éteint dans 60 s" }
            } catch (e: Exception) {
                "PC injoignable"
            }
            Handler(Looper.getMainLooper()).post {
                Toast.makeText(appli, texte, Toast.LENGTH_LONG).show()
                attente.finish()
            }
        }.start()
    }
}
