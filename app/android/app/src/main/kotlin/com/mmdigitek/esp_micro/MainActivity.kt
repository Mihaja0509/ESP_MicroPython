package com.mmdigitek.esp_micro

import android.Manifest
import android.app.AlarmManager
import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.ConsumerIrManager
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.provider.Settings
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        // L'app prévient le widget quand les favoris changent (lib/widget_android.dart).
        // Phase 9 : l'app peut aussi demander au lanceur de poser le widget (« epingler »)
        // et savoir combien de widgets Dadou sont posés (« nombre »).
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "dadou/widget")
            .setMethodCallHandler { appel, resultat ->
                val manager = AppWidgetManager.getInstance(applicationContext)
                val composant = ComponentName(applicationContext, DadouWidget::class.java)
                when (appel.method) {
                    "mettreAJour" -> {
                        DadouWidget.toutMettreAJour(applicationContext)
                        resultat.success(true)
                    }
                    "nombre" -> resultat.success(manager.getAppWidgetIds(composant).size)
                    "epingler" -> {
                        val possible = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
                            manager.isRequestPinAppWidgetSupported
                        resultat.success(
                            possible && manager.requestPinAppWidget(composant, null, null)
                        )
                    }
                    else -> resultat.notImplemented()
                }
            }
        // Phase 11 : notification « PC inutilisé » (lib/notifications.dart, VeilleurPC.kt)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "dadou/notif")
            .setMethodCallHandler { appel, resultat ->
                when (appel.method) {
                    "activer" -> {
                        val actif = appel.argument<Boolean>("actif") ?: false
                        if (actif) demanderPermission()
                        VeilleurPC.programmer(applicationContext, actif)
                        resultat.success(true)
                    }
                    "tester" -> {
                        demanderPermission()
                        VeilleurPC.tester(applicationContext)
                        resultat.success(true)
                    }
                    else -> resultat.notImplemented()
                }
            }
        // Phase 12 : clim infrarouge. L'émetteur IR du téléphone envoie la trame calculée par
        // Dart (lib/clim_ir.dart) : « disponible » (le téléphone a-t-il un émetteur ?) et « emettre ».
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "dadou/ir")
            .setMethodCallHandler { appel, resultat ->
                val ir = getSystemService(Context.CONSUMER_IR_SERVICE) as? ConsumerIrManager
                when (appel.method) {
                    "disponible" -> resultat.success(ir != null && ir.hasIrEmitter())
                    "emettre" -> {
                        val frequence = appel.argument<Int>("frequence") ?: 38000
                        val motif = appel.argument<List<Int>>("motif")
                        if (ir == null || !ir.hasIrEmitter() || motif == null) {
                            resultat.success(false)
                        } else {
                            ir.transmit(frequence, motif.toIntArray())
                            resultat.success(true)
                        }
                    }
                    else -> resultat.notImplemented()
                }
            }
        // Phase 13 : clim programmée (lib/clim_plan.dart, ClimPlan.kt)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "dadou/clim")
            .setMethodCallHandler { appel, resultat ->
                val c = applicationContext
                when (appel.method) {
                    "trames" -> {
                        ClimPlan.trames(
                            c,
                            appel.argument<Int>("frequence") ?: 38000,
                            appel.argument<List<Int>>("power") ?: emptyList(),
                            appel.argument<List<Int>>("dryPower") ?: emptyList(),
                            appel.argument<String>("mode") ?: "cool",
                            appel.argument<Int>("temp") ?: 24
                        )
                        resultat.success(true)
                    }
                    "setOn" -> {
                        ClimPlan.setOn(c, appel.argument<Boolean>("on") ?: false)
                        resultat.success(true)
                    }
                    "version" -> resultat.success(ClimPlan.VERSION)
                    "minuteur" -> {
                        demanderPermission()
                        resultat.success(
                            ClimPlan.minuteur(
                                c,
                                appel.argument<Int>("secondes") ?: 1800,
                                appel.argument<Int>("delaiSecondes") ?: 0
                            )
                        )
                    }
                    "annulerMinuteur" -> {
                        ClimPlan.annulerMinuteur(c)
                        resultat.success(true)
                    }
                    "fenetre" -> {
                        ClimPlan.fenetre(
                            c,
                            appel.argument<Boolean>("actif") ?: false,
                            appel.argument<Int>("de") ?: 0,
                            appel.argument<Int>("a") ?: 0
                        )
                        if (ClimPlan.actif(c)) demanderPermission()
                        resultat.success(true)
                    }
                    "auto" -> {
                        ClimPlan.setAuto(c, appel.argument<String>("json") ?: "{}")
                        if (ClimPlan.actif(c)) demanderPermission()
                        resultat.success(true)
                    }
                    "publier" -> {
                        ClimPlan.publier(c)
                        resultat.success(true)
                    }
                    "etat" -> resultat.success(ClimPlan.etat(c))
                    "fond" -> resultat.success(etatFond())
                    "ouvrirReglage" -> {
                        ouvrirReglage(appel.argument<String>("quoi") ?: "")
                        resultat.success(true)
                    }
                    else -> resultat.notImplemented()
                }
            }
        // Phase 15 : à chaque ouverture, on réarme la clim (Xiaomi peut avoir supprimé les alarmes)
        ClimPlan.rearmer(applicationContext)
        // après une mise à jour de l'app, la vérification reprend toute seule
        val prefs = getSharedPreferences(VeilleurPC.PREFS, Context.MODE_PRIVATE)
        if (prefs.getBoolean("flutter.notif_actif", false)) {
            VeilleurPC.programmer(applicationContext, true)
        }
    }

    /** Phase 15 : carte « Background » de l'app. */
    private fun etatFond(): Map<String, Any> {
        val am = getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        return mapOf(
            "notifs" to NotificationManagerCompat.from(this).areNotificationsEnabled(),
            "exact" to (Build.VERSION.SDK_INT < 31 || am.canScheduleExactAlarms()),
            "batterie" to pm.isIgnoringBatteryOptimizations(packageName),
            "autostart" to (packageManager.resolveActivity(intentionAutostart(), 0) != null),
        )
    }

    private fun intentionAutostart() = Intent().setComponent(
        ComponentName("com.miui.securitycenter", "com.miui.permcenter.autostart.AutoStartManagementActivity")
    )

    private fun detailsApp() =
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName"))

    /** Ouvre l'écran système demandé ; s'il n'existe pas : la fiche de l'app, jamais de plantage. */
    private fun ouvrirReglage(quoi: String) {
        val paquet = Uri.parse("package:$packageName")
        val cible = when (quoi) {
            "notifs" -> {
                if (Build.VERSION.SDK_INT >= 33 &&
                    ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
                    PackageManager.PERMISSION_GRANTED &&
                    shouldShowRequestPermissionRationale(Manifest.permission.POST_NOTIFICATIONS)
                ) {
                    demanderPermission()
                    return
                }
                Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                    .putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
            }
            "exact" -> if (Build.VERSION.SDK_INT >= 31) {
                Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM, paquet)
            } else {
                detailsApp()
            }
            "batterie" -> Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, paquet)
            "autostart" -> intentionAutostart()
            else -> detailsApp()
        }
        try {
            startActivity(cible)
        } catch (e: Exception) { // écran absent, ou refusé par la surcouche du fabricant
            try {
                startActivity(detailsApp())
            } catch (e2: Exception) {
                ClimPlan.journal(applicationContext, "Cannot open settings: $e2")
            }
        }
    }

    /** Android 13 et plus : il faut l'accord de l'utilisateur pour afficher des notifications. */
    private fun demanderPermission() {
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 42)
        }
    }
}
