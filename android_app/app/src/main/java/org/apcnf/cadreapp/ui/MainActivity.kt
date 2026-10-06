package org.apcnf.cadreapp.ui

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import org.apcnf.cadreapp.APCNFApplication
import org.apcnf.cadreapp.R
import org.apcnf.cadreapp.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val sessionManager by lazy { APCNFApplication.instance.sessionManager }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val cadre = sessionManager.getCadre()
        if (cadre == null) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupHeader(cadre)
        setupNavigation()

        // Default to Attendance tab on launch
        if (savedInstanceState == null) {
            loadFragment(AttendanceFragment())
        }
    }

    private fun setupHeader(cadre: org.apcnf.cadreapp.data.model.Cadre) {
        binding.tvWelcomeName.text = "Welcome, ${cadre.name}"
        binding.tvCadreLocation.text = "${cadre.mandal ?: ""} • ${cadre.village ?: ""} (${cadre.district ?: ""})"
        binding.tvRoleBadge.text = cadre.cadreType
    }

    private fun setupNavigation() {
        binding.bottomNav.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_attendance -> {
                    loadFragment(AttendanceFragment())
                    true
                }
                R.id.nav_feedback -> {
                    loadFragment(FeedbackFragment())
                    true
                }
                R.id.nav_dashboard -> {
                    loadFragment(DashboardFragment())
                    true
                }
                else -> false
            }
        }
    }

    private fun loadFragment(fragment: Fragment) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragmentContainer, fragment)
            .commit()
    }
}
