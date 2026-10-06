package org.apcnf.cadreapp.ui.admin

import android.app.DatePickerDialog
import android.content.Intent
import android.graphics.Typeface
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.lifecycle.lifecycleScope
import com.google.android.material.button.MaterialButton
import kotlinx.coroutines.launch
import org.apcnf.cadreapp.APCNFApplication
import org.apcnf.cadreapp.R
import org.apcnf.cadreapp.data.api.ApiService
import org.apcnf.cadreapp.data.model.AdminAttendanceRecord
import org.apcnf.cadreapp.data.model.AdminDashboardData
import org.apcnf.cadreapp.data.model.AdminFeedbackRecord
import org.apcnf.cadreapp.data.model.Cadre
import org.apcnf.cadreapp.data.model.RecentAttendanceRecord
import org.apcnf.cadreapp.data.model.UserRole
import org.apcnf.cadreapp.databinding.ActivityAdminMainBinding
import org.apcnf.cadreapp.ui.LoginActivity
import java.io.File
import java.util.Calendar

enum class AdminTab {
    OVERVIEW, ATTENDANCE, FEEDBACK, CADRES
}

class AdminMainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAdminMainBinding
    private val sessionManager by lazy { APCNFApplication.instance.sessionManager }
    private var currentTab = AdminTab.OVERVIEW
    private var selectedFromDate: String? = null
    private var selectedToDate: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Strict client-side check
        if (!sessionManager.isLoggedIn() || sessionManager.getUserRole() != UserRole.ADMIN) {
            redirectToLogin("Admin authorization required.")
            return
        }

        binding = ActivityAdminMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupHeader()
        setupSpinners()
        setupTabListeners()
        setupFilterListeners()

        // Load initial overview
        loadOverviewData()
    }

    private fun setupHeader() {
        val admin = sessionManager.getAdminUser()
        binding.tvAdminSubtitle.text = admin?.name ?: "State Administrator"

        binding.btnAdminTopRefresh.setOnClickListener {
            when (currentTab) {
                AdminTab.OVERVIEW -> loadOverviewData()
                AdminTab.ATTENDANCE -> loadAttendanceData()
                AdminTab.FEEDBACK -> loadFeedbackData()
                AdminTab.CADRES -> loadCadresData()
            }
        }

        binding.btnAdminLogout.setOnClickListener {
            sessionManager.logout()
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }
    }

    private fun setupSpinners() {
        val activities = arrayOf("All Activities", "Field Visit", "Attend Meeting")
        val cadreTypes = arrayOf("All Types", "FMT", "ICRP", "T-ICRP")
        val ratings = arrayOf("All Ratings", "5 Stars Only", "4+ Stars", "3+ Stars")
        val statuses = arrayOf("All Statuses", "Active", "Inactive")

        val spinnerLayout = android.R.layout.simple_spinner_dropdown_item

        binding.spAttendanceActivity.adapter = ArrayAdapter(this, spinnerLayout, activities)
        binding.spAttendanceCadreType.adapter = ArrayAdapter(this, spinnerLayout, cadreTypes)

        binding.spFeedbackCadreType.adapter = ArrayAdapter(this, spinnerLayout, cadreTypes)
        binding.spFeedbackRating.adapter = ArrayAdapter(this, spinnerLayout, ratings)

        binding.spCadresType.adapter = ArrayAdapter(this, spinnerLayout, cadreTypes)
        binding.spCadresStatus.adapter = ArrayAdapter(this, spinnerLayout, statuses)
    }

    private fun setupTabListeners() {
        binding.btnTabOverview.setOnClickListener { selectTab(AdminTab.OVERVIEW) }
        binding.btnTabAttendance.setOnClickListener { selectTab(AdminTab.ATTENDANCE) }
        binding.btnTabFeedback.setOnClickListener { selectTab(AdminTab.FEEDBACK) }
        binding.btnTabCadres.setOnClickListener { selectTab(AdminTab.CADRES) }
    }

    private fun setupFilterListeners() {
        binding.btnFilterAttendance.setOnClickListener { loadAttendanceData() }
        binding.btnDateFrom.setOnClickListener { showDatePicker(isFrom = true) }
        binding.btnDateTo.setOnClickListener { showDatePicker(isFrom = false) }
        binding.btnExportAttendance.setOnClickListener { exportAttendanceToExcel() }
        binding.btnFilterFeedback.setOnClickListener { loadFeedbackData() }
        binding.btnFilterCadres.setOnClickListener { loadCadresData() }
    }

    private fun showDatePicker(isFrom: Boolean) {
        val cal = Calendar.getInstance()
        val year = cal.get(Calendar.YEAR)
        val month = cal.get(Calendar.MONTH)
        val day = cal.get(Calendar.DAY_OF_MONTH)

        DatePickerDialog(this, { _, y, m, d ->
            val dateStr = String.format("%04d-%02d-%02d", y, m + 1, d)
            if (isFrom) {
                selectedFromDate = dateStr
                binding.btnDateFrom.text = "From: $dateStr"
            } else {
                selectedToDate = dateStr
                binding.btnDateTo.text = "To: $dateStr"
            }
        }, year, month, day).show()
    }

    private fun selectTab(tab: AdminTab) {
        currentTab = tab

        // Update button visual states
        val activeBg = ContextCompat.getColor(this, R.color.white)
        val activeText = ContextCompat.getColor(this, R.color.primary)
        val inactiveText = ContextCompat.getColor(this, R.color.white)

        fun styleTabBtn(btn: MaterialButton, isActive: Boolean) {
            if (isActive) {
                btn.setBackgroundColor(activeBg)
                btn.setTextColor(activeText)
                btn.strokeWidth = 0
            } else {
                btn.setBackgroundColor(android.graphics.Color.TRANSPARENT)
                btn.setTextColor(inactiveText)
                btn.strokeColor = ContextCompat.getColorStateList(this, R.color.white)
                btn.strokeWidth = 2
            }
        }

        styleTabBtn(binding.btnTabOverview, tab == AdminTab.OVERVIEW)
        styleTabBtn(binding.btnTabAttendance, tab == AdminTab.ATTENDANCE)
        styleTabBtn(binding.btnTabFeedback, tab == AdminTab.FEEDBACK)
        styleTabBtn(binding.btnTabCadres, tab == AdminTab.CADRES)

        binding.layoutOverview.visibility = if (tab == AdminTab.OVERVIEW) View.VISIBLE else View.GONE
        binding.layoutAttendance.visibility = if (tab == AdminTab.ATTENDANCE) View.VISIBLE else View.GONE
        binding.layoutFeedback.visibility = if (tab == AdminTab.FEEDBACK) View.VISIBLE else View.GONE
        binding.layoutCadres.visibility = if (tab == AdminTab.CADRES) View.VISIBLE else View.GONE

        // Trigger loading for selected tab
        when (tab) {
            AdminTab.OVERVIEW -> loadOverviewData()
            AdminTab.ATTENDANCE -> loadAttendanceData()
            AdminTab.FEEDBACK -> loadFeedbackData()
            AdminTab.CADRES -> loadCadresData()
        }
    }

    private fun setLoading(loading: Boolean) {
        binding.pbAdminLoading.visibility = if (loading) View.VISIBLE else View.GONE
    }

    // ----------------- TAB 1: OVERVIEW -----------------
    private fun loadOverviewData() {
        val token = sessionManager.getAuthToken() ?: return redirectToLogin("Missing token")
        setLoading(true)

        lifecycleScope.launch {
            val apiService = ApiService(sessionManager.getServerUrl())
            val result = apiService.getAdminDashboard(token)
            setLoading(false)

            result.onSuccess { data ->
                renderOverview(data)
            }.onFailure { err ->
                handleApiError(err)
            }
        }
    }

    private fun renderOverview(data: AdminDashboardData) {
        binding.tvAdminTotalCadres.text = data.totalCadres.toString()
        binding.tvAdminActiveCadres.text = data.activeCadres.toString()
        binding.tvAdminTodayField.text = data.todayFieldVisits.toString()
        binding.tvAdminTodayMeetings.text = data.todayMeetings.toString()
        binding.tvAdminTotalFeedback.text = data.totalFeedback.toString()
        binding.tvAdminAvgRating.text = String.format("%.1f ★", data.averageRating)

        binding.llRecentSubmissions.removeAllViews()
        val recents = data.recentAttendance
        if (recents.isNullOrEmpty()) {
            binding.tvNoSubmissions.visibility = View.VISIBLE
        } else {
            binding.tvNoSubmissions.visibility = View.GONE
            for (item in recents) {
                binding.llRecentSubmissions.addView(createRecentItemView(item))
            }
        }
    }

    private fun createRecentItemView(item: RecentAttendanceRecord): View {
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = ContextCompat.getDrawable(this@AdminMainActivity, R.drawable.bg_card)
            setPadding(28, 20, 28, 20)
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, 14) }
            layoutParams = params
        }

        val titleTv = TextView(this).apply {
            text = "${item.name ?: "Cadre"} (${item.cadreType ?: "FMT"}) • ${item.activity ?: "Field Visit"}"
            setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.text_primary))
            textSize = 14f
            setTypeface(null, Typeface.BOLD)
        }

        val subTv = TextView(this).apply {
            text = "ID: ${item.cadreId} • Time: ${item.time ?: ""} • Date: ${item.date ?: ""}"
            setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.text_secondary))
            textSize = 12f
        }

        card.addView(titleTv)
        card.addView(subTv)

        if (!item.remarks.isNullOrEmpty()) {
            val remTv = TextView(this).apply {
                text = "Remarks: ${item.remarks}"
                setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.text_primary))
                textSize = 12f
                setPadding(0, 4, 0, 0)
            }
            card.addView(remTv)
        }

        if (!item.photoLink.isNullOrEmpty()) {
            val photoBtn = MaterialButton(this, null, com.google.android.material.R.attr.borderlessButtonStyle).apply {
                text = "📸 View Attendance Photo"
                textSize = 11f
                setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.primary))
                setOnClickListener { openUrl(item.photoLink) }
            }
            card.addView(photoBtn)
        }

        return card
    }

    // ----------------- TAB 2: ATTENDANCE -----------------
    private fun loadAttendanceData() {
        val token = sessionManager.getAuthToken() ?: return redirectToLogin("Missing token")
        setLoading(true)

        val query = binding.etAttendanceSearch.text.toString().trim().ifEmpty { null }
        val actPos = binding.spAttendanceActivity.selectedItemPosition
        val activity = if (actPos > 0) binding.spAttendanceActivity.selectedItem.toString() else null

        val typePos = binding.spAttendanceCadreType.selectedItemPosition
        val cadreType = if (typePos > 0) binding.spAttendanceCadreType.selectedItem.toString() else null

        lifecycleScope.launch {
            val apiService = ApiService(sessionManager.getServerUrl())
            val result = apiService.getAdminAttendanceList(
                token = token,
                fromDate = selectedFromDate,
                toDate = selectedToDate,
                activity = activity,
                cadreType = cadreType,
                query = query
            )
            setLoading(false)

            result.onSuccess { list ->
                renderAttendanceList(list)
            }.onFailure { err ->
                handleApiError(err)
            }
        }
    }

    private fun exportAttendanceToExcel() {
        val token = sessionManager.getAuthToken() ?: return redirectToLogin("Missing token")
        setLoading(true)

        val actPos = binding.spAttendanceActivity.selectedItemPosition
        val activity = if (actPos > 0) binding.spAttendanceActivity.selectedItem.toString() else null

        val typePos = binding.spAttendanceCadreType.selectedItemPosition
        val cadreType = if (typePos > 0) binding.spAttendanceCadreType.selectedItem.toString() else null

        lifecycleScope.launch {
            val apiService = ApiService(sessionManager.getServerUrl())
            val result = apiService.exportAdminAttendance(
                token = token,
                fromDate = selectedFromDate,
                toDate = selectedToDate,
                activity = activity,
                cadreType = cadreType
            )
            setLoading(false)

            result.onSuccess { res ->
                val filename = res.filename ?: "APCNF_Attendance_${System.currentTimeMillis()}.csv"
                val csvData = "\uFEFF" + (res.csvContent ?: "")

                try {
                    val exportFile = File(cacheDir, filename)
                    exportFile.writeText(csvData, Charsets.UTF_8)

                    val fileUri = FileProvider.getUriForFile(
                        this@AdminMainActivity,
                        "${applicationContext.packageName}.fileprovider",
                        exportFile
                    )

                    val shareIntent = Intent(Intent.ACTION_SEND).apply {
                        type = "text/csv"
                        putExtra(Intent.EXTRA_STREAM, fileUri)
                        putExtra(Intent.EXTRA_SUBJECT, "APCNF Attendance Export ($filename)")
                        putExtra(Intent.EXTRA_TEXT, "Exported ${res.count} cadre attendance records (${res.fromDate ?: "Start"} to ${res.toDate ?: "Present"}).")
                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    }

                    startActivity(Intent.createChooser(shareIntent, "Open with Excel or Share CSV"))
                    Toast.makeText(this@AdminMainActivity, "Exported ${res.count} records to Excel/CSV successfully!", Toast.LENGTH_LONG).show()
                } catch (e: Exception) {
                    Toast.makeText(this@AdminMainActivity, "Export file created: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }.onFailure { err ->
                handleApiError(err)
            }
        }
    }

    private fun renderAttendanceList(records: List<AdminAttendanceRecord>) {
        binding.llAttendanceCards.removeAllViews()
        binding.tvAttendanceCount.text = "Found ${records.size} attendance records"

        if (records.isEmpty()) {
            binding.tvNoAttendanceMatches.visibility = View.VISIBLE
            return
        }
        binding.tvNoAttendanceMatches.visibility = View.GONE

        for (item in records) {
            val card = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                background = ContextCompat.getDrawable(this@AdminMainActivity, R.drawable.bg_card)
                setPadding(28, 24, 28, 24)
                val params = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply { setMargins(0, 0, 0, 16) }
                layoutParams = params
            }

            // Top Header: Name (Role) + Activity
            val headerTv = TextView(this).apply {
                text = "${item.name ?: "Cadre"} • ${item.cadreType ?: "FMT"}"
                setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.primary))
                textSize = 15f
                setTypeface(null, Typeface.BOLD)
            }

            val metaTv = TextView(this).apply {
                text = "Cadre ID: ${item.cadreId} | ${item.date ?: ""} at ${item.time ?: ""}"
                setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.text_secondary))
                textSize = 12f
            }

            val actTv = TextView(this).apply {
                text = "Activity: ${item.activity ?: "Field Visit"}"
                setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.text_primary))
                textSize = 13f
                setTypeface(null, Typeface.BOLD)
                setPadding(0, 4, 0, 0)
            }

            card.addView(headerTv)
            card.addView(metaTv)
            card.addView(actTv)

            if (!item.remarks.isNullOrEmpty()) {
                val remTv = TextView(this).apply {
                    text = "Remarks: ${item.remarks}"
                    setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.text_primary))
                    textSize = 12f
                    setPadding(0, 4, 0, 0)
                }
                card.addView(remTv)
            }

            // GPS Coordinates if present
            if (item.latitude != null && item.longitude != null) {
                val gpsTv = TextView(this).apply {
                    val acc = item.accuracy?.let { " (±$it m)" } ?: ""
                    text = String.format("📍 GPS: %.5f, %.5f%s", item.latitude, item.longitude, acc)
                    setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.text_secondary))
                    textSize = 11f
                    setPadding(0, 6, 0, 0)
                }
                card.addView(gpsTv)
            }

            // Buttons row: Map & Photo
            val btnRow = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                setPadding(0, 8, 0, 0)
            }

            if (item.latitude != null && item.longitude != null) {
                val mapBtn = MaterialButton(this, null, com.google.android.material.R.attr.borderlessButtonStyle).apply {
                    text = "🗺️ View GPS"
                    textSize = 11f
                    setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.primary))
                    setOnClickListener {
                        val geoUri = Uri.parse("geo:${item.latitude},${item.longitude}?q=${item.latitude},${item.longitude}(Cadre+Attendance)")
                        try {
                            startActivity(Intent(Intent.ACTION_VIEW, geoUri))
                        } catch (e: Exception) {
                            Toast.makeText(this@AdminMainActivity, "No maps app found", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
                btnRow.addView(mapBtn)
            }

            if (!item.photoLink.isNullOrEmpty()) {
                val photoBtn = MaterialButton(this, null, com.google.android.material.R.attr.borderlessButtonStyle).apply {
                    text = "📸 Photo Evidence"
                    textSize = 11f
                    setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.accent))
                    setOnClickListener { openUrl(item.photoLink) }
                }
                btnRow.addView(photoBtn)
            }

            if (btnRow.childCount > 0) {
                card.addView(btnRow)
            }

            binding.llAttendanceCards.addView(card)
        }
    }

    // ----------------- TAB 3: FEEDBACK -----------------
    private fun loadFeedbackData() {
        val token = sessionManager.getAuthToken() ?: return redirectToLogin("Missing token")
        setLoading(true)

        val query = binding.etFeedbackSearch.text.toString().trim().ifEmpty { null }
        val typePos = binding.spFeedbackCadreType.selectedItemPosition
        val cadreType = if (typePos > 0) binding.spFeedbackCadreType.selectedItem.toString() else null

        val ratingPos = binding.spFeedbackRating.selectedItemPosition
        val minRating = when (ratingPos) {
            1 -> 5
            2 -> 4
            3 -> 3
            else -> null
        }

        lifecycleScope.launch {
            val apiService = ApiService(sessionManager.getServerUrl())
            val result = apiService.getAdminFeedbackList(
                token = token,
                cadreType = cadreType,
                minRating = minRating,
                query = query
            )
            setLoading(false)

            result.onSuccess { list ->
                renderFeedbackList(list)
            }.onFailure { err ->
                handleApiError(err)
            }
        }
    }

    private fun renderFeedbackList(records: List<AdminFeedbackRecord>) {
        binding.llFeedbackCards.removeAllViews()
        binding.tvFeedbackCount.text = "Found ${records.size} feedback submissions"

        if (records.isEmpty()) {
            binding.tvNoFeedbackMatches.visibility = View.VISIBLE
            return
        }
        binding.tvNoFeedbackMatches.visibility = View.GONE

        for (item in records) {
            val card = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                background = ContextCompat.getDrawable(this@AdminMainActivity, R.drawable.bg_card)
                setPadding(28, 24, 28, 24)
                val params = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply { setMargins(0, 0, 0, 16) }
                layoutParams = params
            }

            val topicTv = TextView(this).apply {
                text = "📝 ${item.training ?: "Training Session"}"
                setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.primary))
                textSize = 15f
                setTypeface(null, Typeface.BOLD)
            }

            val trainerTv = TextView(this).apply {
                text = "Trainer: ${item.trainer ?: "Resource Person"} | Date: ${item.date ?: ""}"
                setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.text_secondary))
                textSize = 12f
            }

            val cadreTv = TextView(this).apply {
                text = "Submitted by: ${item.name ?: "Cadre"} (${item.cadreType ?: "FMT"}, ID: ${item.cadreId ?: ""})"
                setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.text_primary))
                textSize = 12f
                setTypeface(null, Typeface.BOLD)
                setPadding(0, 4, 0, 0)
            }

            val stars = "★".repeat(item.overallRating) + "☆".repeat(5 - item.overallRating)
            val ratingTv = TextView(this).apply {
                text = "Overall Rating: $stars (${item.overallRating}/5)"
                setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.accent))
                textSize = 13f
                setTypeface(null, Typeface.BOLD)
                setPadding(0, 4, 0, 0)
            }

            val breakdownTv = TextView(this).apply {
                text = "Content: ${item.contentRating}★ | Delivery: ${item.trainerRating}★ | Usefulness: ${item.usefulnessRating}★"
                setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.text_secondary))
                textSize = 11f
            }

            card.addView(topicTv)
            card.addView(trainerTv)
            card.addView(cadreTv)
            card.addView(ratingTv)
            card.addView(breakdownTv)

            if (!item.suggestions.isNullOrEmpty()) {
                val sugTv = TextView(this).apply {
                    text = "Suggestions: \"${item.suggestions}\""
                    setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.text_primary))
                    textSize = 12f
                    setTypeface(null, Typeface.ITALIC)
                    setPadding(0, 6, 0, 0)
                }
                card.addView(sugTv)
            }

            binding.llFeedbackCards.addView(card)
        }
    }

    // ----------------- TAB 4: CADRES DIRECTORY -----------------
    private fun loadCadresData() {
        val token = sessionManager.getAuthToken() ?: return redirectToLogin("Missing token")
        setLoading(true)

        val query = binding.etCadresSearch.text.toString().trim().ifEmpty { null }
        val typePos = binding.spCadresType.selectedItemPosition
        val cadreType = if (typePos > 0) binding.spCadresType.selectedItem.toString() else null

        val statusPos = binding.spCadresStatus.selectedItemPosition
        val status = if (statusPos > 0) binding.spCadresStatus.selectedItem.toString() else null

        lifecycleScope.launch {
            val apiService = ApiService(sessionManager.getServerUrl())
            val result = apiService.getAdminCadreList(
                token = token,
                cadreType = cadreType,
                status = status,
                query = query
            )
            setLoading(false)

            result.onSuccess { list ->
                renderCadresList(list)
            }.onFailure { err ->
                handleApiError(err)
            }
        }
    }

    private fun renderCadresList(cadres: List<Cadre>) {
        binding.llCadresCards.removeAllViews()
        binding.tvCadresCount.text = "Found ${cadres.size} registered cadres"

        if (cadres.isEmpty()) {
            binding.tvNoCadresMatches.visibility = View.VISIBLE
            return
        }
        binding.tvNoCadresMatches.visibility = View.GONE

        for (cadre in cadres) {
            val card = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                background = ContextCompat.getDrawable(this@AdminMainActivity, R.drawable.bg_card)
                setPadding(28, 24, 28, 24)
                val params = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply { setMargins(0, 0, 0, 16) }
                layoutParams = params
            }

            val nameTv = TextView(this).apply {
                text = "${cadre.name} (${cadre.cadreType})"
                setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.primary))
                textSize = 15f
                setTypeface(null, Typeface.BOLD)
            }

            val idTv = TextView(this).apply {
                val isAct = cadre.status?.equals("Active", ignoreCase = true) == true
                val statusText = if (isAct) "● Active" else "○ Inactive"
                text = "Cadre ID: ${cadre.cadreId} | Status: $statusText"
                setTextColor(if (isAct) ContextCompat.getColor(this@AdminMainActivity, R.color.status_present)
                else ContextCompat.getColor(this@AdminMainActivity, R.color.status_absent))
                textSize = 12f
                setTypeface(null, Typeface.BOLD)
            }

            val locTv = TextView(this).apply {
                text = "District: ${cadre.district ?: "AP"} | Mandal: ${cadre.mandal ?: ""} | Village: ${cadre.village ?: ""}"
                setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.text_secondary))
                textSize = 12f
                setPadding(0, 4, 0, 0)
            }

            val voTv = TextView(this).apply {
                text = "VO: ${cadre.vo ?: "N/A"}"
                setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.text_secondary))
                textSize = 12f
            }

            card.addView(nameTv)
            card.addView(idTv)
            card.addView(locTv)
            card.addView(voTv)

            val callBtn = MaterialButton(this, null, com.google.android.material.R.attr.borderlessButtonStyle).apply {
                text = "📞 Call Cadre (${cadre.mobile})"
                textSize = 11f
                setTextColor(ContextCompat.getColor(this@AdminMainActivity, R.color.primary))
                setOnClickListener {
                    try {
                        startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:${cadre.mobile}")))
                    } catch (e: Exception) {
                        Toast.makeText(this@AdminMainActivity, "Unable to initiate call", Toast.LENGTH_SHORT).show()
                    }
                }
            }
            card.addView(callBtn)

            binding.llCadresCards.addView(card)
        }
    }

    private fun openUrl(url: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (e: Exception) {
            Toast.makeText(this, "Unable to open link", Toast.LENGTH_SHORT).show()
        }
    }

    private fun handleApiError(err: Throwable) {
        val msg = err.message ?: "Unknown error"
        Toast.makeText(this, "Admin API: $msg", Toast.LENGTH_LONG).show()

        if (msg.contains("Unauthorized", ignoreCase = true) ||
            msg.contains("expired", ignoreCase = true) ||
            msg.contains("denied", ignoreCase = true)) {
            sessionManager.logout()
            redirectToLogin("Session expired or unauthorized. Please re-authenticate.")
        }
    }

    private fun redirectToLogin(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }
}
