package org.apcnf.cadreapp.ui

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.textfield.TextInputEditText
import kotlinx.coroutines.launch
import org.apcnf.cadreapp.APCNFApplication
import org.apcnf.cadreapp.R
import org.apcnf.cadreapp.data.api.ApiService
import org.apcnf.cadreapp.databinding.ActivityLoginBinding

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private val sessionManager by lazy { APCNFApplication.instance.sessionManager }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // If already logged in, navigate directly to main dashboard
        if (sessionManager.isLoggedIn()) {
            startActivity(Intent(this, MainActivity::class.java))
            finish()
            return
        }

        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupListeners()
    }

    private fun setupListeners() {
        binding.btnLogin.setOnClickListener {
            performLogin()
        }

        binding.tvConfigServer.setOnClickListener {
            showServerConfigDialog()
        }
    }

    private fun performLogin() {
        val cadreId = binding.etCadreId.text?.toString()?.trim() ?: ""
        val mobile = binding.etMobile.text?.toString()?.trim() ?: ""

        if (cadreId.isEmpty() || mobile.isEmpty()) {
            showError(getString(R.string.err_empty_login))
            return
        }

        if (mobile.length != 10) {
            showError(getString(R.string.err_invalid_mobile))
            return
        }

        val serverUrl = sessionManager.getServerUrl()
        if (serverUrl.contains("YOUR_SCRIPT_ID")) {
            showServerConfigDialog("Please set your deployed Google Apps Script Web App URL first.")
            return
        }

        setLoading(true)

        lifecycleScope.launch {
            val apiService = ApiService(serverUrl)
            val result = apiService.login(cadreId, mobile)

            setLoading(false)

            result.onSuccess { cadre ->
                sessionManager.saveLogin(cadre)
                Toast.makeText(this@LoginActivity, "Welcome, ${cadre.name}!", Toast.LENGTH_SHORT).show()
                startActivity(Intent(this@LoginActivity, MainActivity::class.java))
                finish()
            }.onFailure { err ->
                showError(err.message ?: "Authentication failed. Check your network or details.")
            }
        }
    }

    private fun showServerConfigDialog(initialMessage: String? = null) {
        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_server_url, null)
        val etUrl = dialogView.findViewById<TextInputEditText>(R.id.etServerUrl)
        etUrl.setText(sessionManager.getServerUrl())

        val builder = MaterialAlertDialogBuilder(this)
            .setView(dialogView)
            .setPositiveButton(R.string.save_url) { _, _ ->
                val newUrl = etUrl.text?.toString()?.trim() ?: ""
                if (newUrl.isNotEmpty()) {
                    sessionManager.setServerUrl(newUrl)
                    Toast.makeText(this, "Server URL updated.", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton(R.string.cancel, null)

        if (!initialMessage.isNullOrEmpty()) {
            builder.setTitle(initialMessage)
        }

        builder.show()
    }

    private fun setLoading(isLoading: Boolean) {
        binding.btnLogin.isEnabled = !isLoading
        binding.pbLoading.visibility = if (isLoading) View.VISIBLE else View.GONE
        binding.tvStatus.visibility = View.GONE
    }

    private fun showError(msg: String) {
        binding.tvStatus.text = msg
        binding.tvStatus.visibility = View.VISIBLE
    }
}
