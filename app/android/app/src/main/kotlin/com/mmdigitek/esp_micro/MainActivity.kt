package com.mmdigitek.esp_micro

import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.os.Build
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
    }
}
