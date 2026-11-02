package com.mmdigitek.esp_micro

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        // L'app prévient le widget quand les favoris changent (lib/widget_android.dart)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "dadou/widget")
            .setMethodCallHandler { appel, resultat ->
                if (appel.method == "mettreAJour") {
                    DadouWidget.toutMettreAJour(applicationContext)
                    resultat.success(true)
                } else {
                    resultat.notImplemented()
                }
            }
    }
}
