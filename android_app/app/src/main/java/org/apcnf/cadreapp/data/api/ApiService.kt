package org.apcnf.cadreapp.data.api

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.apcnf.cadreapp.data.model.AdminDashboardData
import org.apcnf.cadreapp.data.model.AdminUser
import org.apcnf.cadreapp.data.model.AttendanceRequest
import org.apcnf.cadreapp.data.model.AuthResponse
import org.apcnf.cadreapp.data.model.Cadre
import org.apcnf.cadreapp.data.model.DashboardData
import org.apcnf.cadreapp.data.model.FeedbackRequest
import org.json.JSONObject

class ApiService(private val serverUrl: String) {

    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    /**
     * Authenticates a Field Cadre using Cadre ID and Registered Mobile Number.
     */
    suspend fun cadreLogin(cadreId: String, mobile: String): Result<AuthResponse> = withContext(Dispatchers.IO) {
        try {
            val payload = JSONObject().apply {
                put("action", "login")
                put("cadreId", cadreId.trim().uppercase())
                put("mobile", mobile.trim())
            }.toString()

            val responseBody = postJson(payload)
            val json = JSONObject(responseBody)
            val success = json.optBoolean("success", false)

            if (success) {
                val token = json.optString("token", "")
                val role = json.optString("role", "CADRE")
                val cadreJson = json.optJSONObject("cadre")
                    ?: return@withContext Result.failure(Exception("Cadre details missing in server response."))
                val cadre = ApiClient.gson.fromJson(cadreJson.toString(), Cadre::class.java)

                Result.success(AuthResponse(
                    success = true,
                    role = role,
                    token = token,
                    cadre = cadre,
                    message = json.optString("message", "Login successful.")
                ))
            } else {
                val msg = json.optString("message", "Authentication failed. Check Cadre ID and Mobile.")
                Result.failure(Exception(msg))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Authenticates an Administrator using server-verified Username/Email & Password.
     * Passwords are never hardcoded and verified strictly on the server.
     */
    suspend fun adminLogin(username: String, password: String): Result<AuthResponse> = withContext(Dispatchers.IO) {
        try {
            val payload = JSONObject().apply {
                put("action", "adminLogin")
                put("username", username.trim())
                put("password", password)
            }.toString()

            val responseBody = postJson(payload)
            val json = JSONObject(responseBody)
            val success = json.optBoolean("success", false)

            if (success) {
                val token = json.optString("token", "")
                val role = json.optString("role", "ADMIN")
                val adminJson = json.optJSONObject("admin")
                    ?: return@withContext Result.failure(Exception("Admin profile missing in server response."))
                val admin = ApiClient.gson.fromJson(adminJson.toString(), AdminUser::class.java)

                Result.success(AuthResponse(
                    success = true,
                    role = role,
                    token = token,
                    admin = admin,
                    message = json.optString("message", "Admin authentication successful.")
                ))
            } else {
                val msg = json.optString("message", "Invalid admin credentials.")
                Result.failure(Exception(msg))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Fetches aggregated overall system metrics for authenticated Administrators.
     * Server verifies caller's ADMIN role token.
     */
    suspend fun getAdminDashboard(token: String): Result<AdminDashboardData> = withContext(Dispatchers.IO) {
        try {
            val payload = JSONObject().apply {
                put("action", "getAdminDashboard")
                put("token", token)
            }.toString()

            val responseBody = postJson(payload)
            val json = JSONObject(responseBody)
            val success = json.optBoolean("success", false)

            if (success) {
                val dataObj = json.optJSONObject("data")
                    ?: return@withContext Result.failure(Exception("Dashboard data missing in response."))
                val data = ApiClient.gson.fromJson(dataObj.toString(), AdminDashboardData::class.java)
                Result.success(data)
            } else {
                val msg = json.optString("message", "Unauthorized or failed to fetch admin dashboard.")
                Result.failure(Exception(msg))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Submits daily attendance record with signed Cadre session token.
     */
    suspend fun submitAttendance(request: AttendanceRequest, token: String? = null): Result<String> = withContext(Dispatchers.IO) {
        try {
            val reqWithToken = if (token != null) request.copy(token = token) else request
            val payload = ApiClient.gson.toJson(reqWithToken)
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

    /**
     * Submits training/meeting feedback with signed Cadre session token.
     */
    suspend fun submitFeedback(request: FeedbackRequest, token: String? = null): Result<String> = withContext(Dispatchers.IO) {
        try {
            val reqWithToken = if (token != null) request.copy(token = token) else request
            val payload = ApiClient.gson.toJson(reqWithToken)
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

    /**
     * Fetches today's cadre-specific dashboard metrics.
     */
    suspend fun getDashboard(cadreId: String, token: String? = null): Result<DashboardData> = withContext(Dispatchers.IO) {
        try {
            val payload = JSONObject().apply {
                put("action", "getDashboard")
                put("cadreId", cadreId.trim())
                if (token != null) put("token", token)
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
        val responseBody = response.body?.string() ?: throw Exception("Empty response from server.")

        if (response.code == 403 || response.code == 401) {
            try {
                val json = JSONObject(responseBody)
                throw Exception(json.optString("message", "Unauthorized (HTTP ${response.code})"))
            } catch (e: Exception) {
                throw Exception("Unauthorized: HTTP ${response.code}")
            }
        }

        if (!response.isSuccessful) {
            throw Exception("HTTP ${response.code}: ${response.message}")
        }
        return responseBody
    }
}
