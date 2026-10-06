package org.apcnf.cadreapp.data.model

import com.google.gson.annotations.SerializedName

/**
 * Cadre profile details returned upon successful verification.
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
 * Attendance payload submitted to doPost endpoint.
 */
data class AttendanceRequest(
    @SerializedName("action") val action: String = "saveAttendance",
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
    @SerializedName("cadre") val cadre: Cadre? = null,
    @SerializedName("data") val data: T? = null,
    @SerializedName("timestamp") val timestamp: String? = null
)

/**
 * Today's dashboard statistics and cadre status.
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
 * Item stored in local storage when device is offline.
 */
data class OfflineQueueItem(
    val id: String,
    val type: String, // "attendance" or "feedback"
    val jsonPayload: String,
    val timestamp: Long
)
