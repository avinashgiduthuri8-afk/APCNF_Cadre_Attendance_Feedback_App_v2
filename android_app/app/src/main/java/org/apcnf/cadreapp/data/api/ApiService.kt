package org.apcnf.cadreapp.data.api

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.apcnf.cadreapp.data.model.ApiResponse
import org.apcnf.cadreapp.data.model.AttendanceRequest
import org.apcnf.cadreapp.data.model.Cadre
import org.apcnf.cadreapp.data.model.DashboardData
import org.apcnf.cadreapp.data.model.FeedbackRequest
import org.json.JSONObject

class ApiService(private val serverUrl: String) {

    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    suspend fun login(cadreId: String, mobile: String): Result<Cadre> = withContext(Dispatchers.IO) {
        try {
            val payload = JSONObject().apply {
                put("action", "login")
                put("cadreId", cadreId.trim())
                put("mobile", mobile.trim())
            }.toString()

            val responseBody = postJson(payload)
            val json = JSONObject(responseBody)
            val success = json.optBoolean("success", false)

            if (success) {
                val cadreJson = json.optJSONObject("cadre")
                    ?: return@withContext Result.failure(Exception("Cadre details missing in response."))
                val cadre = ApiClient.gson.fromJson(cadreJson.toString(), Cadre::class.java)
                Result.success(cadre)
            } else {
                val msg = json.optString("message", "Authentication failed. Check Cadre ID and Mobile.")
                Result.failure(Exception(msg))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun submitAttendance(request: AttendanceRequest): Result<String> = withContext(Dispatchers.IO) {
        try {
            val payload = ApiClient.gson.toJson(request)
            val responseBody = postJson(payload)
            val json = JSONObject(responseBody)
            val success = json.optBoolean("success", false)
            val msg = json.optString("message", if (success) "Attendance submitted successfully." else "Submission failed.")

            if (success) {
                Result.success(msg)
            } else {
                Result.failure(Exception(msg))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun submitFeedback(request: FeedbackRequest): Result<String> = withContext(Dispatchers.IO) {
        try {
            val payload = ApiClient.gson.toJson(request)
            val responseBody = postJson(payload)
            val json = JSONObject(responseBody)
            val success = json.optBoolean("success", false)
            val msg = json.optString("message", if (success) "Feedback submitted successfully." else "Failed to submit feedback.")

            if (success) {
                Result.success(msg)
            } else {
                Result.failure(Exception(msg))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getDashboard(cadreId: String): Result<DashboardData> = withContext(Dispatchers.IO) {
        try {
            val payload = JSONObject().apply {
                put("action", "getDashboard")
                put("cadreId", cadreId.trim())
            }.toString()

            val responseBody = postJson(payload)
            val json = JSONObject(responseBody)
            val success = json.optBoolean("success", false)

            if (success) {
                val dataObj = json.optJSONObject("data")
                    ?: return@withContext Result.failure(Exception("Dashboard data missing in response."))
                val data = ApiClient.gson.fromJson(dataObj.toString(), DashboardData::class.java)
                Result.success(data)
            } else {
                val msg = json.optString("message", "Failed to fetch dashboard data.")
                Result.failure(Exception(msg))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private fun postJson(jsonPayload: String): String {
        val body = jsonPayload.toRequestBody(jsonMediaType)
        val request = Request.Builder()
            .url(serverUrl)
            .post(body)
            .build()

        val response = ApiClient.httpClient.newCall(request).execute()
        if (!response.isSuccessful) {
            throw Exception("HTTP ${response.code}: ${response.message}")
        }
        return response.body?.string() ?: throw Exception("Empty response received from server.")
    }
}
