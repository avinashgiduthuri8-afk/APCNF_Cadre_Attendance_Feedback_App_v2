package org.apcnf.cadreapp.data.local

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.Gson
import org.apcnf.cadreapp.data.model.AdminUser
import org.apcnf.cadreapp.data.model.Cadre
import org.apcnf.cadreapp.data.model.UserRole

class SessionManager(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
    private val gson = Gson()

    companion object {
        private const val PREF_NAME = "apcnf_cadre_prefs"
        private const val KEY_IS_LOGGED_IN = "is_logged_in"
        private const val KEY_USER_ROLE = "user_role"
        private const val KEY_AUTH_TOKEN = "auth_token"
        private const val KEY_CADRE_JSON = "cadre_json"
        private const val KEY_ADMIN_JSON = "admin_json"
        private const val KEY_SERVER_URL = "server_url"

        // Default placeholder URL until configured in app settings
        const val DEFAULT_SERVER_URL = "https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec"
    }

    /**
     * Persists Cadre session with signed auth token and role CADRE.
     */
    fun saveCadreLogin(cadre: Cadre, token: String?) {
        prefs.edit()
            .putBoolean(KEY_IS_LOGGED_IN, true)
            .putString(KEY_USER_ROLE, UserRole.CADRE.name)
            .putString(KEY_AUTH_TOKEN, token ?: "")
            .putString(KEY_CADRE_JSON, gson.toJson(cadre))
            .remove(KEY_ADMIN_JSON)
            .apply()
    }

    /**
     * Persists Admin session with signed auth token and role ADMIN.
     */
    fun saveAdminLogin(admin: AdminUser, token: String?) {
        prefs.edit()
            .putBoolean(KEY_IS_LOGGED_IN, true)
            .putString(KEY_USER_ROLE, UserRole.ADMIN.name)
            .putString(KEY_AUTH_TOKEN, token ?: "")
            .putString(KEY_ADMIN_JSON, gson.toJson(admin))
            .remove(KEY_CADRE_JSON)
            .apply()
    }

    fun isLoggedIn(): Boolean {
        return prefs.getBoolean(KEY_IS_LOGGED_IN, false) && getUserRole() != null
    }

    fun getUserRole(): UserRole? {
        val roleStr = prefs.getString(KEY_USER_ROLE, null) ?: return null
        return try {
            UserRole.valueOf(roleStr)
        } catch (e: Exception) {
            null
        }
    }

    fun getAuthToken(): String? {
        return prefs.getString(KEY_AUTH_TOKEN, null)
    }

    fun getCadre(): Cadre? {
        val json = prefs.getString(KEY_CADRE_JSON, null) ?: return null
        return try {
            gson.fromJson(json, Cadre::class.java)
        } catch (e: Exception) {
            null
        }
    }

    fun getAdminUser(): AdminUser? {
        val json = prefs.getString(KEY_ADMIN_JSON, null) ?: return null
        return try {
            gson.fromJson(json, AdminUser::class.java)
        } catch (e: Exception) {
            null
        }
    }

    fun logout() {
        prefs.edit()
            .putBoolean(KEY_IS_LOGGED_IN, false)
            .remove(KEY_USER_ROLE)
            .remove(KEY_AUTH_TOKEN)
            .remove(KEY_CADRE_JSON)
            .remove(KEY_ADMIN_JSON)
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
