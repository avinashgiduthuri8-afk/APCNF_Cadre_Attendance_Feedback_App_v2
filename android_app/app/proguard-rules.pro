# Proguard rules for APCNF Cadre App
-keep class org.apcnf.cadreapp.data.model.** { *; }
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}
