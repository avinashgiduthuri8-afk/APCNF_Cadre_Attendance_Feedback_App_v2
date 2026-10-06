package org.apcnf.cadreapp.ui.admin

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.button.MaterialButton
import kotlinx.coroutines.launch
import org.apcnf.cadreapp.APCNFApplication
import org.apcnf.cadreapp.R
import org.apcnf.cadreapp.data.api.ApiService
import org.apcnf.cadreapp.data.model.AdminDashboardData
import org.apcnf.cadreapp.data.model.UserRole
import org.apcnf.cadreapp.databinding.ActivityAdminMainBinding
import org.apcnf.cadreapp.ui.LoginActivity

class AdminMainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAdminMainBinding
    private val sessionManager by lazy { APCNFApplication.instance.sessionManager }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Strict client-side check before loading
        if (!sessionManager.isLoggedIn() || sessionManager.getUserRole() != UserRole.ADMIN) {
            redirectToLogin("Admin authorization required.")
            return
        }

        binding = ActivityAdminMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupHeader()
        setupListeners()
        loadAdminData()
    }

    private fun setupHeader() {
        val admin = sessionManager.getAdminUser()
        binding.tvAdminSubtitle.text = admin?.name ?: "State Administrator"
    }

    private fun setupListeners() {
        binding.btnAdminRefresh.setOnClickListener {
            loadAdminData()
        }

        binding.btnAdminLogout.setOnClickListener {
            sessionManager.logout()
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }
    }

    private fun loadAdminData() {
        val token = sessionManager.getAuthToken()
        if (token.isNullOrEmpty()) {
            redirectToLogin("Session token missing. Please log in again.")
            return
        }

        setLoading(true)

        lifecycleScope.launch {
            val apiService = ApiService(sessionManager.getServerUrl())
            val result = apiService.getAdminDashboard(token)

            setLoading(false)

            result.onSuccess { data ->
                renderDashboard(data)
            }.onFailure { err ->
                Toast.makeText(this@AdminMainActivity, "Admin API: ${err.message}", Toast.LENGTH_LONG).show()
                if (err.message?.contains("Unauthorized", ignoreCase = true) == true ||
                    err.message?.contains("expired", ignoreCase = true) == true ||
                    err.message?.contains("denied", ignoreCase = true) == true) {
                    sessionManager.logout()
                    redirectToLogin("Session expired or unauthorized. Please re-authenticate.")
                }
            }
        }
    }

    private fun renderDashboard(data: AdminDashboardData) {
        binding.tvAdminTotalCadres.text = data.totalCadres.toString()
        binding.tvAdminActiveCadres.text = data.activeCadres.toString()
        binding.tvAdminTodayField.text = data.todayFieldVisits.toString()
        binding.tvAdminTodayMeetings.text = data.todayMeetings.toString()
        binding.tvAdminTotalFeedback.text = data.totalFeedback.toString()
        binding.tvAdminAvgRating.text = String.format("%.1f ★", data.averageRating)

        // Render Recent Submissions
        binding.llRecentSubmissions.removeAllViews()
        val recents = data.recentAttendance
        if (recents.isNullOrEmpty()) {
            binding.tvNoSubmissions.visibility = View.VISIBLE
        } else {
            binding.tvNoSubmissions.visibility = View.GONE
            for (item in recents) {
                val itemView = LayoutInflater.from(this).inflate(R.layout.bg_card, binding.llRecentSubmissions, false)
                // Use a standard row container
                val rowLayout = android.widget.LinearLayout(this).apply {
                    orientation = android.widget.LinearLayout.VERTICAL
                    background = androidx.core.content.ContextCompat.getDrawable(this@AdminMainActivity, R.drawable.bg_card)
                    setPadding(32, 24, 32, 24)
                    val params = android.widget.LinearLayout.LayoutParams(
                        android.widget.LinearLayout.LayoutParams.MATCH_PARENT,
                        android.widget.LinearLayout.LayoutParams.WRAP_CONTENT
                    ).apply {
                        setMargins(0, 0, 0, 16)
                    }
                    layoutParams = params
                }

                val titleTv = TextView(this).apply {
                    text = "${item.name ?: "Cadre"} (${item.cadreType ?: "FMT"}) • ${item.activity ?: "Field Visit"}"
                    setTextColor(androidx.core.content.ContextCompat.getColor(this@AdminMainActivity, R.color.text_primary))
                    textSize = 14f
                    setTypeface(null, android.graphics.Typeface.BOLD)
                }

                val subTv = TextView(this).apply {
                    text = "ID: ${item.cadreId} • Time: ${item.time ?: ""} • Date: ${item.date ?: ""}"
                    setTextColor(androidx.core.content.ContextCompat.getColor(this@AdminMainActivity, R.color.text_secondary))
                    textSize = 12f
                }

                rowLayout.addView(titleTv)
                rowLayout.addView(subTv)

                if (!item.remarks.isNullOrEmpty()) {
                    val remTv = TextView(this).apply {
                        text = "Remarks: ${item.remarks}"
                        setTextColor(androidx.core.content.ContextCompat.getColor(this@AdminMainActivity, R.color.text_primary))
                        textSize = 12f
                    }
                    rowLayout.addView(remTv)
                }

                if (!item.photoLink.isNullOrEmpty()) {
                    val photoBtn = MaterialButton(this, null, com.google.android.material.R.attr.borderlessButtonStyle).apply {
                        text = "View Attendance Photo"
                        textSize = 11f
                        setTextColor(androidx.core.content.ContextCompat.getColor(this@AdminMainActivity, R.color.primary))
                        setOnClickListener {
                            try {
                                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(item.photoLink)))
                            } catch (e: Exception) {
                                Toast.makeText(this@AdminMainActivity, "Unable to open photo link", Toast.LENGTH_SHORT).show()
                            }
                        }
                    }
                    rowLayout.addView(photoBtn)
                }

                binding.llRecentSubmissions.addView(rowLayout)
            }
        }
    }

    private fun setLoading(isLoading: Boolean) {
        binding.pbAdminLoading.visibility = if (isLoading) View.VISIBLE else View.GONE
        binding.btnAdminRefresh.isEnabled = !isLoading
    }

    private fun redirectToLogin(reason: String) {
        Toast.makeText(this, reason, Toast.LENGTH_LONG).show()
        val intent = Intent(this, LoginActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        startActivity(intent)
        finish()
    }
}
