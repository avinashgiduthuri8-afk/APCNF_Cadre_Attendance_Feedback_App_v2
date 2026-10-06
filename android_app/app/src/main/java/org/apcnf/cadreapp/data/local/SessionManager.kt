package org.apcnf.cadreapp.data.local

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.Gson
import org.apcnf.cadreapp.data.model.Cadre

class SessionManager(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
    private val gson = Gson()

    companion object {
        private const val PREF_NAME = "apcnf_cadre_prefs"
        private const val KEY_IS_LOGGED_IN = "is_logged_in"
        private const val KEY_CADRE_JSON = "cadre_json"
        private const val KEY_SERVER_URL = "server_url"

        // Default placeholder URL until configured in app settings
        const val DEFAULT_SERVER_URL = "https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec"
    }

    fun saveLogin(cadre: Cadre) {
        prefs.edit()
            .putBoolean(KEY_IS_LOGGED_IN, true)
            .putString(KEY_CADRE_JSON, gson.toJson(cadre))
            .apply()
    }

    fun isLoggedIn(): Boolean {
        return prefs.getBoolean(KEY_IS_LOGGED_IN, false) && getCadre() != null
    }

    fun getCadre(): Cadre? {
        val json = prefs.getString(KEY_CADRE_JSON, null) ?: return null
        return try {
            gson.fromJson(json, Cadre::class.java)
        } catch (e: Exception) {
            null
        }
    }

    fun logout() {
        prefs.edit()
            .putBoolean(KEY_IS_LOGGED_IN, false)
            .remove(KEY_CADRE_JSON)
            .apply()
    }

    fun getServerUrl(): String {
        return prefs.getString(KEY_SERVER_URL, DEFAULT_SERVER_URL) ?: DEFAULT_SERVER_URL
    }

    fun setServerUrl(url: String) {
        val cleanUrl = url.trim()
        prefs.edit().putString(KEY_SERVER_URL, cleanUrl).apply()
    }
}
