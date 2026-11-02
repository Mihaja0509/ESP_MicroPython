package com.mmdigitek.esp_micro

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.RemoteViews
import android.widget.Toast
import org.json.JSONArray
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/**
 * Widget « Dadou » de l'écran d'accueil (Phase 8) : les 4 premiers favoris de l'app.
 * Un appui envoie la commande au PC par une simple requête HTTP (GET /widget?ligne=…),
 * avec le token d'appairage de l'app : pas besoin d'ouvrir l'app.
 * Les boutons, l'adresse et le token sont lus dans les préférences de l'app Flutter.
 */
class DadouWidget : AppWidgetProvider() {

    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        for (id in ids) {
            manager.updateAppWidget(id, vues(context))
        }
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)
        if (intent.action != ACTION) return
        val ligne = intent.getStringExtra("ligne") ?: return
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val adresse = prefs.getString("flutter.adresse", "") ?: ""
        val token = prefs.getString("flutter.token", "") ?: ""
        val appli = context.applicationContext
        if (adresse.isEmpty() || token.isEmpty()) {
            Toast.makeText(appli, "Ouvre Dadou pour te connecter au PC", Toast.LENGTH_SHORT).show()
            return
        }
        val attente = goAsync()
        Thread {
            val texte = try {
                envoyer(adresse, token, ligne)
            } catch (e: Exception) {
                "PC injoignable (éteint, en veille ou Tailscale coupé ?)"
            }
            Handler(Looper.getMainLooper()).post {
                Toast.makeText(appli, texte, Toast.LENGTH_SHORT).show()
                attente.finish()
            }
        }.start()
    }

    companion object {
        const val ACTION = "com.mmdigitek.esp_micro.WIDGET_ACTION"
        private const val PREFS = "FlutterSharedPreferences"
        private const val PORT = 8765
        private val CELLULES = intArrayOf(R.id.b0, R.id.b1, R.id.b2, R.id.b3)
        private val ICONES = intArrayOf(R.id.i0, R.id.i1, R.id.i2, R.id.i3)
        private val TEXTES = intArrayOf(R.id.t0, R.id.t1, R.id.t2, R.id.t3)

        /** Redessine tous les widgets Dadou posés sur l'écran d'accueil. */
        fun toutMettreAJour(context: Context) {
            val manager = AppWidgetManager.getInstance(context)
            val ids = manager.getAppWidgetIds(ComponentName(context, DadouWidget::class.java))
            for (id in ids) {
                manager.updateAppWidget(id, vues(context))
            }
        }

        private fun vues(context: Context): RemoteViews {
            val v = RemoteViews(context.packageName, R.layout.widget_dadou)
            val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            val boutons = try {
                JSONArray(prefs.getString("flutter.widget_boutons", "[]") ?: "[]")
            } catch (e: Exception) {
                JSONArray()
            }
            v.setOnClickPendingIntent(R.id.logo, ouvrirApp(context))
            if (boutons.length() == 0) {
                v.setViewVisibility(R.id.vide, View.VISIBLE)
                v.setViewVisibility(R.id.rangee, View.GONE)
                v.setOnClickPendingIntent(R.id.vide, ouvrirApp(context))
                return v
            }
            v.setViewVisibility(R.id.vide, View.GONE)
            v.setViewVisibility(R.id.rangee, View.VISIBLE)
            for (i in CELLULES.indices) {
                if (i >= boutons.length()) {
                    v.setViewVisibility(CELLULES[i], View.GONE)
                    continue
                }
                val b = boutons.getJSONObject(i)
                v.setViewVisibility(CELLULES[i], View.VISIBLE)
                v.setTextViewText(TEXTES[i], b.optString("nom"))
                v.setImageViewResource(ICONES[i], icone(b.optString("code")))
                val intent = Intent(context, DadouWidget::class.java)
                    .setAction(ACTION)
                    .putExtra("ligne", b.optString("ligne"))
                val pi = PendingIntent.getBroadcast(
                    context, i, intent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
                v.setOnClickPendingIntent(CELLULES[i], pi)
            }
            return v
        }

        private fun ouvrirApp(context: Context): PendingIntent {
            val intent = Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            return PendingIntent.getActivity(
                context, 100, intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        }

        private fun icone(code: String): Int = when (code) {
            "play" -> R.drawable.w_play
            "vol_plus" -> R.drawable.w_vol_plus
            "vol_moins" -> R.drawable.w_vol_moins
            "muet" -> R.drawable.w_muet
            "suivant" -> R.drawable.w_suivant
            "ecran" -> R.drawable.w_ecran
            "verrou" -> R.drawable.w_verrou
            "bureau" -> R.drawable.w_bureau
            "veille" -> R.drawable.w_veille
            "power" -> R.drawable.w_power
            "annuler" -> R.drawable.w_annuler
            "web" -> R.drawable.w_web
            "jeu" -> R.drawable.w_jeu
            "terminal" -> R.drawable.w_terminal
            "clavier" -> R.drawable.w_clavier
            "musique" -> R.drawable.w_musique
            "dossier" -> R.drawable.w_dossier
            "etoile" -> R.drawable.w_etoile
            "app" -> R.drawable.w_app
            else -> R.drawable.w_eclair
        }

        private fun envoyer(adresse: String, token: String, ligne: String): String {
            val url = URL("http://$adresse:$PORT/widget?ligne=" + URLEncoder.encode(ligne, "UTF-8"))
            val c = url.openConnection() as HttpURLConnection
            c.connectTimeout = 4000
            c.readTimeout = 8000
            c.setRequestProperty("X-Token", token)
            try {
                val code = c.responseCode
                if (code == 401) return "Ce téléphone n'est plus appairé : ouvre Dadou"
                val flux = if (code < 400) c.inputStream else c.errorStream
                val texte = flux?.bufferedReader()?.use { it.readText() }?.trim() ?: ""
                return texte.ifEmpty { "OK" }
            } finally {
                c.disconnect()
            }
        }
    }
}
