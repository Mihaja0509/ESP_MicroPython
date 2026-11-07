# Phase 15 : R8 retirait le constructeur de WorkDatabase_Impl (créé par réflexion par Room) :
# l'APK release plantait à chaque démarrage (NoSuchMethodException, InitializationProvider).
-keep class * extends androidx.room.RoomDatabase { <init>(); }
