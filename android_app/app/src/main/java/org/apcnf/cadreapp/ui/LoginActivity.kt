package org.apcnf.cadreapp.ui

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.textfield.TextInputEditText
import kotlinx.coroutines.launch
import org.apcnf.cadreapp.APCNFApplication
import org.apcnf.cadreapp.R
import org.apcnf.cadreapp.data.api.ApiService
import org.apcnf.cadreapp.data.model.UserRole
import org.apcnf.cadreapp.databinding.ActivityLoginBinding
import org.apcnf.cadreapp.ui.admin.AdminMainActivity

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private val sessionManager by lazy { APCNFApplication.instance.sessionManager }
    private var selectedRole: UserRole = UserRole.CADRE

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // If already logged in, route directly to the appropriate role dashboard
        if (sessionManager.isLoggedIn()) {
            routeToRoleDashboard()
            return
        }

        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupRoleToggle()
        setupListeners()
    }

    private fun routeToRoleDashboard() {
        val role = sessionManager.getUserRole()
        if (role == UserRole.ADMIN) {
            startActivity(Intent(this, AdminMainActivity::class.java))
        } else {
            startActivity(Intent(this, MainActivity::class.java))
        }
        finish()
    }

    private fun setupRoleToggle() {
        binding.toggleRoleGroup.addOnButtonCheckedListener { _, checkedId, isChecked ->
            if (isChecked) {
                if (checkedId == R.id.btnRoleAdmin) {
                    selectedRole = UserRole.ADMIN
                    binding.llCadreFields.visibility = View.GONE
                    binding.llAdminFields.visibility = View.VISIBLE
                    binding.btnLogin.text = getString(R.string.btn_admin_login)
                    binding.tvInstruction.text = "Enter administrator username/email and password"
                } else {
                    selectedRole = UserRole.CADRE
                    binding.llCadreFields.visibility = View.VISIBLE
                    binding.llAdminFields.visibility = View.GONE
                    binding.btnLogin.text = getString(R.string.btn_login)
                    binding.tvInstruction.text = getString(R.string.login_instruction)
                }
                binding.tvStatus.visibility = View.GONE
            }
        }
    }

    private fun setupListeners() {
        binding.btnLogin.setOnClickListener {
            if (selectedRole == UserRole.ADMIN) {
                performAdminLogin()
            } else {
                performCadreLogin()
            }
        }

        binding.tvConfigServer.setOnClickListener {
            showServerConfigDialog()
        }
    }

    private fun performCadreLogin() {
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
            showServerConfigDialog("Please configure your Google Apps Script Web App URL first.")
            return
        }

        setLoading(true)

        lifecycleScope.launch {
            val apiService = ApiService(serverUrl)
            val result = apiService.cadreLogin(cadreId, mobile)

            setLoading(false)

            result.onSuccess { auth ->
                if (auth.cadre != null) {
                    sessionManager.saveCadreLogin(auth.cadre, auth.token)
                    Toast.makeText(this@LoginActivity, "Welcome, ${auth.cadre.name}!", Toast.LENGTH_SHORT).show()
                    startActivity(Intent(this@LoginActivity, MainActivity::class.java))
                    finish()
                } else {
                    showError("Invalid response format from server.")
                }
            }.onFailure { err ->
                showError(err.message ?: "Cadre verification failed.")
            }
        }
    }

    private fun performAdminLogin() {
        val username = binding.etAdminUsername.text?.toString()?.trim() ?: ""
        val password = binding.etAdminPassword.text?.toString() ?: ""

        if (username.isEmpty() || password.isEmpty()) {
            showError("Please enter both Admin username and password.")
            return
        }

        val serverUrl = sessionManager.getServerUrl()
        if (serverUrl.contains("YOUR_SCRIPT_ID")) {
            showServerConfigDialog("Please configure your Google Apps Script Web App URL first.")
            return
        }

        setLoading(true)

        lifecycleScope.launch {
            val apiService = ApiService(serverUrl)
            val result = apiService.adminLogin(username, password)

            setLoading(false)

            result.onSuccess { auth ->
                if (auth.admin != null) {
                    sessionManager.saveAdminLogin(auth.admin, auth.token)
                    Toast.makeText(this@LoginActivity, "Admin authentication successful.", Toast.LENGTH_SHORT).show()
                    startActivity(Intent(this@LoginActivity, AdminMainActivity::class.java))
                    finish()
                } else {
                    showError("Invalid admin response from server.")
                }
            }.onFailure { err ->
                showError(err.message ?: "Admin authentication failed.")
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
