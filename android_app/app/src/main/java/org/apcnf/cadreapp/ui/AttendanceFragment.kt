package org.apcnf.cadreapp.ui

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import android.location.Location
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import org.apcnf.cadreapp.APCNFApplication
import org.apcnf.cadreapp.R
import org.apcnf.cadreapp.data.api.ApiClient
import org.apcnf.cadreapp.data.api.ApiService
import org.apcnf.cadreapp.data.model.AttendanceRequest
import org.apcnf.cadreapp.databinding.FragmentAttendanceBinding
import org.apcnf.cadreapp.utils.ImageCompressor
import org.apcnf.cadreapp.utils.LocationHelper
import org.apcnf.cadreapp.utils.NetworkUtils
import java.io.File

class AttendanceFragment : Fragment() {

    private var _binding: FragmentAttendanceBinding? = null
    private val binding get() = _binding!!

    private val sessionManager by lazy { APCNFApplication.instance.sessionManager }
    private val offlineQueueManager by lazy { APCNFApplication.instance.offlineQueueManager }
    private val locationHelper by lazy { LocationHelper(requireContext()) }

    private var currentPhotoFile: File? = null
    private var compressedPhotoBase64: String? = null
    private var currentLocation: Location? = null

    // Photo capture launcher using FileProvider
    private val takePictureLauncher = registerForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        if (success && currentPhotoFile != null) {
            lifecycleScope.launch {
                try {
                    val base64 = ImageCompressor.compressImageToBase64(currentPhotoFile!!)
                    compressedPhotoBase64 = base64

                    val bitmap = BitmapFactory.decodeFile(currentPhotoFile!!.absolutePath)
                    binding.ivPhotoPreview.setImageBitmap(bitmap)
                    binding.ivPhotoPreview.visibility = View.VISIBLE
                    binding.btnCapturePhoto.text = getString(R.string.retake_photo)
                } catch (e: Exception) {
                    Toast.makeText(requireContext(), "Failed to process photo: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    // Permission launchers
    private val cameraPermissionLauncher = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) launchCamera()
        else Toast.makeText(requireContext(), "Camera permission required for attendance photo", Toast.LENGTH_SHORT).show()
    }

    private val locationPermissionLauncher = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { permissions ->
        val granted = permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
                permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true
        if (granted) fetchLiveLocation()
        else {
            binding.tvGpsStatus.text = "GPS permission denied."
            binding.tvGpsDetails.text = "Please allow location access in Android Settings."
        }
    }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentAttendanceBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        setupListeners()
        checkLocationPermissionAndFetch()
    }

    private fun setupListeners() {
        binding.btnCapturePhoto.setOnClickListener {
            checkCameraPermissionAndLaunch()
        }

        binding.btnRefreshGps.setOnClickListener {
            fetchLiveLocation()
        }

        binding.btnSubmitAttendance.setOnClickListener {
            submitAttendance()
        }
    }

    private fun checkCameraPermissionAndLaunch() {
        if (ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            launchCamera()
        } else {
            cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    private fun launchCamera() {
        try {
            val photoDir = File(requireContext().cacheDir, "images").apply { mkdirs() }
            val photoFile = File.createTempFile("APCNF_", ".jpg", photoDir)
            currentPhotoFile = photoFile

            val uri: Uri = FileProvider.getUriForFile(
                requireContext(),
                "${requireContext().packageName}.fileprovider",
                photoFile
            )
            takePictureLauncher.launch(uri)
        } catch (e: Exception) {
            Toast.makeText(requireContext(), "Error opening camera: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun checkLocationPermissionAndFetch() {
        val fine = ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val coarse = ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

        if (fine || coarse) {
            fetchLiveLocation()
        } else {
            locationPermissionLauncher.launch(
                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
            )
        }
    }

    private fun fetchLiveLocation() {
        binding.tvGpsStatus.text = getString(R.string.gps_waiting)
        binding.tvGpsDetails.text = "Acquiring satellite lock..."

        lifecycleScope.launch {
            val loc = locationHelper.getCurrentLocation()
            currentLocation = loc
            if (loc != null) {
                binding.tvGpsStatus.text = "GPS Acquired"
                binding.tvGpsDetails.text = getString(
                    R.string.gps_captured_format,
                    loc.latitude,
                    loc.longitude,
                    loc.accuracy
                )
            } else {
                binding.tvGpsStatus.text = "Unable to acquire GPS."
                binding.tvGpsDetails.text = "Ensure location services are enabled on your device."
            }
        }
    }

    private fun submitAttendance() {
        val cadre = sessionManager.getCadre() ?: return

        if (compressedPhotoBase64.isNullOrEmpty()) {
            Toast.makeText(requireContext(), getString(R.string.err_photo_required), Toast.LENGTH_SHORT).show()
            return
        }

        val loc = currentLocation
        if (loc == null) {
            Toast.makeText(requireContext(), getString(R.string.err_gps_required), Toast.LENGTH_SHORT).show()
            return
        }

        val activity = if (binding.rbFieldVisit.isChecked) "Field Visit" else "Attend Meeting"
        val remarks = binding.etRemarks.text?.toString()?.trim() ?: ""

        val request = AttendanceRequest(
            cadreId = cadre.cadreId,
            name = cadre.name,
            mobile = cadre.mobile,
            cadreType = cadre.cadreType,
            activity = activity,
            remarks = remarks,
            photoBase64 = compressedPhotoBase64!!,
            latitude = loc.latitude,
            longitude = loc.longitude,
            accuracy = loc.accuracy
        )

        // Check if offline
        if (!NetworkUtils.isOnline(requireContext())) {
            offlineQueueManager.enqueue("attendance", ApiClient.gson.toJson(request))
            showSubmitMessage("Offline: Attendance queued. Will auto-sync when connected.", true)
            resetForm()
            return
        }

        setLoading(true)

        lifecycleScope.launch {
            val apiService = ApiService(sessionManager.getServerUrl())
            val result = apiService.submitAttendance(request)

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
        compressedPhotoBase64 = null
        currentPhotoFile = null
        binding.ivPhotoPreview.visibility = View.GONE
        binding.btnCapturePhoto.text = getString(R.string.btn_take_photo)
        binding.etRemarks.setText("")
    }

    private fun showSubmitMessage(msg: String, isSuccess: Boolean) {
        binding.tvSubmitMsg.text = msg
        binding.tvSubmitMsg.visibility = View.VISIBLE
        binding.tvSubmitMsg.setTextColor(
            ContextCompat.getColor(
                requireContext(),
                if (isSuccess) R.color.status_present else R.color.status_absent
            )
        )
    }

    private fun setLoading(isLoading: Boolean) {
        binding.btnSubmitAttendance.isEnabled = !isLoading
        binding.pbSubmit.visibility = if (isLoading) View.VISIBLE else View.GONE
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
