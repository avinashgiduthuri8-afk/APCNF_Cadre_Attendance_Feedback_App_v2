package org.apcnf.cadreapp.ui

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import org.apcnf.cadreapp.APCNFApplication
import org.apcnf.cadreapp.R
import org.apcnf.cadreapp.data.api.ApiClient
import org.apcnf.cadreapp.data.api.ApiService
import org.apcnf.cadreapp.data.model.AttendanceRequest
import org.apcnf.cadreapp.data.model.FeedbackRequest
import org.apcnf.cadreapp.databinding.FragmentDashboardBinding
import org.apcnf.cadreapp.utils.NetworkUtils

class DashboardFragment : Fragment() {

    private var _binding: FragmentDashboardBinding? = null
    private val binding get() = _binding!!

    private val sessionManager by lazy { APCNFApplication.instance.sessionManager }
    private val offlineQueueManager by lazy { APCNFApplication.instance.offlineQueueManager }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentDashboardBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        populateProfile()
        updateOfflineQueueUI()
        setupListeners()
        fetchDashboardStats()
    }

    override fun onResume() {
        super.onResume()
        updateOfflineQueueUI()
        fetchDashboardStats()
    }

    private fun populateProfile() {
        val cadre = sessionManager.getCadre() ?: return
        binding.tvProfileName.text = cadre.name
        binding.tvProfileIdMobile.text = "ID: ${cadre.cadreId} • Mobile: ${cadre.mobile} (${cadre.cadreType})"
        binding.tvProfileLocation.text = "Village: ${cadre.village ?: "N/A"}, Mandal: ${cadre.mandal ?: "N/A"}, District: ${cadre.district ?: "N/A"}"
        binding.tvProfileVO.text = "VO: ${cadre.vo ?: "N/A"} • Status: ${cadre.status ?: "Active"}"
    }

    private fun setupListeners() {
        binding.btnSyncQueue.setOnClickListener {
            syncOfflineQueue()
        }

        binding.btnLogout.setOnClickListener {
            sessionManager.logout()
            startActivity(Intent(requireContext(), LoginActivity::class.java))
            requireActivity().finish()
        }
    }

    private fun updateOfflineQueueUI() {
        val count = offlineQueueManager.getPendingCount()
        binding.tvPendingCount.text = "$count record(s) pending sync"
        binding.btnSyncQueue.isEnabled = count > 0
    }

    private fun fetchDashboardStats() {
        val cadre = sessionManager.getCadre() ?: return
        val serverUrl = sessionManager.getServerUrl()

        if (!NetworkUtils.isOnline(requireContext())) return

        lifecycleScope.launch {
            val apiService = ApiService(serverUrl)
            val result = apiService.getDashboard(cadre.cadreId, sessionManager.getAuthToken())

            result.onSuccess { data ->
                binding.tvFieldCount.text = data.totalFieldVisits.toString()
                binding.tvMeetingCount.text = data.totalMeetings.toString()
                binding.tvFeedbackCount.text = data.totalFeedback.toString()

                val myAtt = data.myAttendance
                if (myAtt != null) {
                    if (myAtt.fieldVisitDone) {
                        binding.tvMyFieldStatus.text = "✓ Field Visit: Marked for Today"
                        binding.tvMyFieldStatus.setTextColor(ContextCompat.getColor(requireContext(), R.color.status_present))
                    } else {
                        binding.tvMyFieldStatus.text = "• Field Visit: Not Marked Today"
                        binding.tvMyFieldStatus.setTextColor(ContextCompat.getColor(requireContext(), R.color.text_secondary))
                    }

                    if (myAtt.meetingDone) {
                        binding.tvMyMeetingStatus.text = "✓ Meeting: Marked for Today"
                        binding.tvMyMeetingStatus.setTextColor(ContextCompat.getColor(requireContext(), R.color.status_present))
                    } else {
                        binding.tvMyMeetingStatus.text = "• Meeting: Not Marked Today"
                        binding.tvMyMeetingStatus.setTextColor(ContextCompat.getColor(requireContext(), R.color.text_secondary))
                    }
                }
            }
        }
    }

    private fun syncOfflineQueue() {
        if (!NetworkUtils.isOnline(requireContext())) {
            Toast.makeText(requireContext(), "No internet connection available to sync.", Toast.LENGTH_SHORT).show()
            return
        }

        val items = offlineQueueManager.getPendingList()
        if (items.isEmpty()) {
            Toast.makeText(requireContext(), "No pending items to sync.", Toast.LENGTH_SHORT).show()
            return
        }

        binding.btnSyncQueue.isEnabled = false
        binding.btnSyncQueue.text = "Syncing..."

        lifecycleScope.launch {
            val apiService = ApiService(sessionManager.getServerUrl())
            val token = sessionManager.getAuthToken()
            var successCount = 0

            for (item in items) {
                try {
                    val result = if (item.type == "attendance") {
                        val req = ApiClient.gson.fromJson(item.jsonPayload, AttendanceRequest::class.java)
                        apiService.submitAttendance(req, token)
                    } else {
                        val req = ApiClient.gson.fromJson(item.jsonPayload, FeedbackRequest::class.java)
                        apiService.submitFeedback(req, token)
                    }

                    if (result.isSuccess) {
                        offlineQueueManager.remove(item.id)
                        successCount++
                    }
                } catch (e: Exception) {
                    // Stop on network break
                    break
                }
            }

            updateOfflineQueueUI()
            binding.btnSyncQueue.text = getString(R.string.btn_sync_now)
            Toast.makeText(requireContext(), "Synced $successCount record(s) to server.", Toast.LENGTH_SHORT).show()
            fetchDashboardStats()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
