package org.apcnf.cadreapp.data.model

import com.google.gson.annotations.SerializedName

/**
 * Supported User Roles in APCNF System.
 */
enum class UserRole {
    @SerializedName("CADRE")
    CADRE,

    @SerializedName("ADMIN")
    ADMIN
}

/**
 * Cadre profile details.
 */
data class Cadre(
    @SerializedName("cadreId") val cadreId: String,
    @SerializedName("name") val name: String,
    @SerializedName("mobile") val mobile: String,
    @SerializedName("cadreType") val cadreType: String,
    @SerializedName("district") val district: String? = null,
    @SerializedName("mandal") val mandal: String? = null,
    @SerializedName("village") val village: String? = null,
    @SerializedName("vo") val vo: String? = null,
    @SerializedName("status") val status: String? = "Active"
)

/**
 * Admin profile details.
 */
data class AdminUser(
    @SerializedName("username") val username: String,
    @SerializedName("name") val name: String,
    @SerializedName("role") val role: String = "ADMIN"
)

/**
 * Universal Authentication Response with Role & Session Token.
 */
data class AuthResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("message") val message: String? = null,
    @SerializedName("role") val role: String? = null,
    @SerializedName("token") val token: String? = null,
    @SerializedName("cadre") val cadre: Cadre? = null,
    @SerializedName("admin") val admin: AdminUser? = null
)

/**
 * Attendance payload submitted to doPost endpoint.
 */
data class AttendanceRequest(
    @SerializedName("action") val action: String = "saveAttendance",
    @SerializedName("token") val token: String? = null,
    @SerializedName("cadreId") val cadreId: String,
    @SerializedName("name") val name: String,
    @SerializedName("mobile") val mobile: String,
    @SerializedName("cadreType") val cadreType: String,
    @SerializedName("activity") val activity: String,
    @SerializedName("remarks") val remarks: String? = "",
    @SerializedName("photoBase64") val photoBase64: String,
    @SerializedName("latitude") val latitude: Double,
    @SerializedName("longitude") val longitude: Double,
    @SerializedName("accuracy") val accuracy: Float
)

/**
 * Feedback payload submitted to doPost endpoint.
 */
data class FeedbackRequest(
    @SerializedName("action") val action: String = "saveFeedback",
    @SerializedName("token") val token: String? = null,
    @SerializedName("cadreId") val cadreId: String,
    @SerializedName("name") val name: String,
    @SerializedName("mobile") val mobile: String,
    @SerializedName("cadreType") val cadreType: String,
    @SerializedName("training") val training: String,
    @SerializedName("trainer") val trainer: String,
    @SerializedName("contentRating") val contentRating: Int,
    @SerializedName("trainerRating") val trainerRating: Int,
    @SerializedName("usefulnessRating") val usefulnessRating: Int,
    @SerializedName("overallRating") val overallRating: Int,
    @SerializedName("suggestions") val suggestions: String? = ""
)

/**
 * Generic API response from Google Apps Script doPost endpoint.
 */
data class ApiResponse<T>(
    @SerializedName("success") val success: Boolean,
    @SerializedName("message") val message: String? = null,
    @SerializedName("role") val role: String? = null,
    @SerializedName("token") val token: String? = null,
    @SerializedName("data") val data: T? = null,
    @SerializedName("timestamp") val timestamp: String? = null
)

/**
 * Today's cadre dashboard statistics.
 */
data class DashboardData(
    @SerializedName("today") val today: String,
    @SerializedName("totalFieldVisits") val totalFieldVisits: Int,
    @SerializedName("totalMeetings") val totalMeetings: Int,
    @SerializedName("totalFeedback") val totalFeedback: Int,
    @SerializedName("myAttendance") val myAttendance: MyAttendanceStatus? = null
)

data class MyAttendanceStatus(
    @SerializedName("fieldVisitDone") val fieldVisitDone: Boolean,
    @SerializedName("meetingDone") val meetingDone: Boolean
)

/**
 * Admin Dashboard aggregated overview data.
 */
data class AdminDashboardData(
    @SerializedName("today") val today: String,
    @SerializedName("totalCadres") val totalCadres: Int,
    @SerializedName("activeCadres") val activeCadres: Int,
    @SerializedName("todayFieldVisits") val todayFieldVisits: Int,
    @SerializedName("todayMeetings") val todayMeetings: Int,
    @SerializedName("totalFeedback") val totalFeedback: Int,
    @SerializedName("averageRating") val averageRating: Double,
    @SerializedName("recentAttendance") val recentAttendance: List<RecentAttendanceRecord>? = null
)

data class RecentAttendanceRecord(
    @SerializedName("date") val date: String? = null,
    @SerializedName("time") val time: String? = null,
    @SerializedName("cadreId") val cadreId: String? = null,
    @SerializedName("name") val name: String? = null,
    @SerializedName("cadreType") val cadreType: String? = null,
    @SerializedName("activity") val activity: String? = null,
    @SerializedName("remarks") val remarks: String? = null,
    @SerializedName("photoLink") val photoLink: String? = null,
    @SerializedName("latitude") val latitude: Double? = null,
    @SerializedName("longitude") val longitude: Double? = null
)

/**
 * Item stored in local storage when device is offline.
 */
data class OfflineQueueItem(
    val id: String,
    val type: String,
    val jsonPayload: String,
    val timestamp: Long
)

/**
 * Detailed Attendance record returned to Admin oversight screens.
 */
data class AdminAttendanceRecord(
    @SerializedName("timestamp") val timestamp: Any? = null,
    @SerializedName("date") val date: String? = null,
    @SerializedName("time") val time: String? = null,
    @SerializedName("cadreId") val cadreId: String? = null,
    @SerializedName("name") val name: String? = null,
    @SerializedName("cadreType") val cadreType: String? = null,
    @SerializedName("activity") val activity: String? = null,
    @SerializedName("remarks") val remarks: String? = null,
    @SerializedName("photoLink") val photoLink: String? = null,
    @SerializedName("latitude") val latitude: Double? = null,
    @SerializedName("longitude") val longitude: Double? = null,
    @SerializedName("accuracy") val accuracy: Float? = null
)

/**
 * Detailed Feedback record returned to Admin review screens.
 */
data class AdminFeedbackRecord(
    @SerializedName("timestamp") val timestamp: Any? = null,
    @SerializedName("date") val date: String? = null,
    @SerializedName("cadreId") val cadreId: String? = null,
    @SerializedName("name") val name: String? = null,
    @SerializedName("cadreType") val cadreType: String? = null,
    @SerializedName("training") val training: String? = null,
    @SerializedName("trainer") val trainer: String? = null,
    @SerializedName("contentRating") val contentRating: Int = 0,
    @SerializedName("trainerRating") val trainerRating: Int = 0,
    @SerializedName("usefulnessRating") val usefulnessRating: Int = 0,
    @SerializedName("overallRating") val overallRating: Int = 0,
    @SerializedName("suggestions") val suggestions: String? = null
)

/**
 * Attendance Export result containing CSV text and summary for Admin.
 */
data class AttendanceExportResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("message") val message: String? = null,
    @SerializedName("filename") val filename: String? = null,
    @SerializedName("fromDate") val fromDate: String? = null,
    @SerializedName("toDate") val toDate: String? = null,
    @SerializedName("count") val count: Int = 0,
    @SerializedName("csvContent") val csvContent: String? = null,
    @SerializedName("sheetUrl") val sheetUrl: String? = null,
    @SerializedName("data") val data: List<AdminAttendanceRecord>? = null
)


