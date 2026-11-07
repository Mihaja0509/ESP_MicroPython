package com.mmdigitek.esp_micro

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat

/**
 * Service de premier plan (Phase 15) : tourne tant qu'un minuteur, une plage horaire ou l'automatisme
 * est actif (ClimPlan.actif). Il fait tourner l'automatisme (60 s), publie l'état au PC (30 s, 10 s
 * après un échec) et tient la notification à jour. L'état reste dans ClimPlan (préférences).
 * Le verrou de veille partiel est nécessaire : sans lui, le Handler s'arrête écran éteint.
 */
class ClimService : Service() {
    private lateinit var fil: HandlerThread
    private lateinit var h: Handler
    private var verrou: PowerManager.WakeLock? = null
    private var prochainePub = 0L
    private var derniereVue: ClimPlan.VueNotif? = null

    private val tic = object : Runnable {
        override fun run() {
            val c = applicationContext
            try {
                if (!ClimPlan.actif(c)) {
                    stopSelf()
                    return
                }
                ClimPlan.ticAuto(c)
                val maintenant = System.currentTimeMillis()
                if (maintenant >= prochainePub) {
                    prochainePub = maintenant + if (ClimPlan.publierMaintenant(c)) PUB_MS else PUB_RETENTE_MS
                }
                majNotification()
            } catch (e: Exception) {
                ClimPlan.journal(c, "Service error: $e") // une erreur ne doit jamais arrêter le service
            }
            h.postDelayed(this, TIC_MS)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        fil = HandlerThread("clim").also { it.start() }
        h = Handler(fil.looper)
        verrou = (getSystemService(Context.POWER_SERVICE) as PowerManager)
            .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "dadou:clim")
            .also { it.setReferenceCounted(false) }
        enCours = true
        ClimPlan.journal(applicationContext, "Service started")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val c = applicationContext
        creerCanal(c)
        val vue = ClimPlan.vueNotif(c)
        try {
            ServiceCompat.startForeground(
                this, ID_NOTIF, construire(vue),
                if (Build.VERSION.SDK_INT >= 34) ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE else 0,
            )
            derniereVue = vue
        } catch (e: Exception) {
            // redémarrage refusé par Android : les alarmes d'heures fixes restent armées
            ClimPlan.journal(c, "Foreground start refused: $e")
            stopSelf()
            return START_NOT_STICKY
        }
        verrou?.takeIf { !it.isHeld }?.acquire()
        h.removeCallbacks(tic)
        h.post(tic)
        return START_STICKY
    }

    override fun onDestroy() {
        enCours = false
        h.removeCallbacksAndMessages(null)
        fil.quitSafely()
        verrou?.takeIf { it.isHeld }?.release()
        ClimPlan.journal(applicationContext, "Service stopped")
        super.onDestroy()
    }

    private fun majNotification() {
        val vue = ClimPlan.vueNotif(applicationContext)
        if (vue == derniereVue) return // pas de mise à jour inutile : le chronomètre défile tout seul
        derniereVue = vue
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) return
        try {
            NotificationManagerCompat.from(this).notify(ID_NOTIF, construire(vue))
        } catch (e: SecurityException) {
            // permission retirée entre-temps
        }
    }

    private fun action(code: Int, nom: String): PendingIntent = PendingIntent.getBroadcast(
        this, code,
        Intent(this, ClimReceiver::class.java).setAction(nom),
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
    )

    private fun construire(vue: ClimPlan.VueNotif): android.app.Notification {
        val texte = vue.lignes.joinToString("\n")
        val ouvrir = PendingIntent.getActivity(
            this, 309,
            Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val b = NotificationCompat.Builder(this, CANAL)
            .setSmallIcon(R.drawable.w_power)
            .setContentTitle(vue.titre)
            .setContentText(vue.lignes.firstOrNull() ?: "")
            .setStyle(NotificationCompat.BigTextStyle().bigText(texte))
            .setContentIntent(ouvrir)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setSilent(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
        if (vue.compteFin > 0) {
            // compte à rebours natif : Android le fait défiler sans mise à jour chaque seconde
            b.setWhen(vue.compteFin).setShowWhen(true).setUsesChronometer(true).setChronometerCountDown(true)
        } else {
            b.setShowWhen(false)
        }
        if (vue.on) b.addAction(0, "Turn off", action(310, ClimReceiver.ACTION_OFF))
        if (vue.minuteur) b.addAction(0, "Cancel timer", action(311, ClimReceiver.ACTION_ANNULER))
        if (vue.auto) b.addAction(0, "Pause auto 30 min", action(312, ClimReceiver.ACTION_PAUSE))
        return b.build()
    }

    companion object {
        @Volatile
        var enCours = false
            private set
        private const val ID_NOTIF = 4302
        private const val CANAL = "clim_service"
        private const val TIC_MS = 10_000L
        private const val PUB_MS = 30_000L
        private const val PUB_RETENTE_MS = 10_000L

        private fun creerCanal(c: Context) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val canal = NotificationChannel(CANAL, "AC control", NotificationManager.IMPORTANCE_LOW)
                canal.setShowBadge(false)
                canal.setSound(null, null)
                c.getSystemService(NotificationManager::class.java).createNotificationChannel(canal)
            }
        }
    }
}
