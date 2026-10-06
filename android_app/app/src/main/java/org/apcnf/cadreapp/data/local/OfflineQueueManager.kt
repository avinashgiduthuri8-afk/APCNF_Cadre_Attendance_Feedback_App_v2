package org.apcnf.cadreapp.data.local

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import org.apcnf.cadreapp.data.model.OfflineQueueItem
import java.util.UUID

class OfflineQueueManager(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(QUEUE_PREF_NAME, Context.MODE_PRIVATE)
    private val gson = Gson()

    companion object {
        private const val QUEUE_PREF_NAME = "apcnf_offline_queue"
        private const val KEY_QUEUE = "pending_items"
    }

    @Synchronized
    fun enqueue(type: String, jsonPayload: String) {
        val list = getPendingList().toMutableList()
        val item = OfflineQueueItem(
            id = UUID.randomUUID().toString(),
            type = type,
            jsonPayload = jsonPayload,
            timestamp = System.currentTimeMillis()
        )
        list.add(item)
        saveList(list)
    }

    @Synchronized
    fun getPendingList(): List<OfflineQueueItem> {
        val json = prefs.getString(KEY_QUEUE, null) ?: return emptyList()
        return try {
            val type = object : TypeToken<List<OfflineQueueItem>>() {}.type
            gson.fromJson(json, type) ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    @Synchronized
    fun getPendingCount(): Int {
        return getPendingList().size
    }

    @Synchronized
    fun remove(itemId: String) {
        val list = getPendingList().filter { it.id != itemId }
        saveList(list)
    }

    @Synchronized
    fun clear() {
        prefs.edit().remove(KEY_QUEUE).apply()
    }

    private fun saveList(list: List<OfflineQueueItem>) {
        val json = gson.toJson(list)
        prefs.edit().putString(KEY_QUEUE, json).apply()
    }
}
