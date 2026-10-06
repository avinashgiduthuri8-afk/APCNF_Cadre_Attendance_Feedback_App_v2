package org.apcnf.cadreapp.ui

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
import org.apcnf.cadreapp.data.model.FeedbackRequest
import org.apcnf.cadreapp.databinding.FragmentFeedbackBinding
import org.apcnf.cadreapp.utils.NetworkUtils

class FeedbackFragment : Fragment() {

    private var _binding: FragmentFeedbackBinding? = null
    private val binding get() = _binding!!

    private val sessionManager by lazy { APCNFApplication.instance.sessionManager }
    private val offlineQueueManager by lazy { APCNFApplication.instance.offlineQueueManager }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentFeedbackBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnSubmitFeedback.setOnClickListener {
            submitFeedback()
        }
    }

    private fun submitFeedback() {
        val cadre = sessionManager.getCadre() ?: return

        val training = binding.etTrainingTopic.text?.toString()?.trim() ?: ""
        val trainer = binding.etTrainerName.text?.toString()?.trim() ?: ""
        val suggestions = binding.etSuggestions.text?.toString()?.trim() ?: ""

        if (training.isEmpty()) {
            Toast.makeText(requireContext(), "Please enter the Training / Meeting Topic.", Toast.LENGTH_SHORT).show()
            return
        }

        val contentRating = binding.rbContent.rating.toInt().coerceIn(1, 5)
        val trainerRating = binding.rbTrainer.rating.toInt().coerceIn(1, 5)
        val usefulnessRating = binding.rbUsefulness.rating.toInt().coerceIn(1, 5)
        val overallRating = binding.rbOverall.rating.toInt().coerceIn(1, 5)

        val request = FeedbackRequest(
            cadreId = cadre.cadreId,
            name = cadre.name,
            mobile = cadre.mobile,
            cadreType = cadre.cadreType,
            training = training,
            trainer = trainer.ifEmpty { "Resource Person" },
            contentRating = contentRating,
            trainerRating = trainerRating,
            usefulnessRating = usefulnessRating,
            overallRating = overallRating,
            suggestions = suggestions
        )

        if (!NetworkUtils.isOnline(requireContext())) {
            offlineQueueManager.enqueue("feedback", ApiClient.gson.toJson(request))
            showSubmitMessage("Offline: Feedback queued. Will auto-sync when online.", true)
            resetForm()
            return
        }

        setLoading(true)

        lifecycleScope.launch {
            val apiService = ApiService(sessionManager.getServerUrl())
            val result = apiService.submitFeedback(request, sessionManager.getAuthToken())

            setLoading(false)

            result.onSuccess { msg ->
                showSubmitMessage(msg, true)
                resetForm()
            }.onFailure { err ->
                showSubmitMessage("Error: ${err.message}", false)
            }
        }
    }

    private fun resetForm() {
        binding.etTrainingTopic.setText("")
        binding.etTrainerName.setText("")
        binding.etSuggestions.setText("")
        binding.rbContent.rating = 5f
        binding.rbTrainer.rating = 5f
        binding.rbUsefulness.rating = 5f
        binding.rbOverall.rating = 5f
    }

    private fun showSubmitMessage(msg: String, isSuccess: Boolean) {
        binding.tvFeedbackMsg.text = msg
        binding.tvFeedbackMsg.visibility = View.VISIBLE
        binding.tvFeedbackMsg.setTextColor(
            ContextCompat.getColor(
                requireContext(),
                if (isSuccess) R.color.status_present else R.color.status_absent
            )
        )
    }

    private fun setLoading(isLoading: Boolean) {
        binding.btnSubmitFeedback.isEnabled = !isLoading
        binding.pbFeedback.visibility = if (isLoading) View.VISIBLE else View.GONE
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
