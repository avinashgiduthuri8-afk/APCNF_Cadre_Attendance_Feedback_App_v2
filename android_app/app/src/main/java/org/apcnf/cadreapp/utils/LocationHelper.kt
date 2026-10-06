package org.apcnf.cadreapp.utils

import android.annotation.SuppressLint
import android.content.Context
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.Looper
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import kotlin.coroutines.resume
import kotlin.coroutines.suspendCancellableCoroutine

class LocationHelper(private val context: Context) {

    private val fusedClient: FusedLocationProviderClient =
        LocationServices.getFusedLocationProviderClient(context)
    private val locationManager =
        context.getSystemService(Context.LOCATION_SERVICE) as LocationManager

    @SuppressLint("MissingPermission")
    suspend fun getCurrentLocation(): Location? = suspendCancellableCoroutine { cont ->
        try {
            // Try FusedLocationProviderClient first (fastest and most accurate)
            val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 5000)
                .setMaxUpdates(1)
                .setWaitForAccurateLocation(true)
                .build()

            val callback = object : LocationCallback() {
                override fun LocationResult(result: LocationResult) {
                    fusedClient.removeLocationUpdates(this)
                    val loc = result.lastLocation
                    if (loc != null && cont.isActive) {
                        cont.resume(loc)
                    } else if (cont.isActive) {
                        fallbackLocationManager(cont)
                    }
                }
            }

            fusedClient.requestLocationUpdates(request, callback, Looper.getMainLooper())
                .addOnFailureListener {
                    if (cont.isActive) {
                        fallbackLocationManager(cont)
                    }
                }

            cont.invokeOnCancellation {
                fusedClient.removeLocationUpdates(callback)
            }
        } catch (e: Exception) {
            if (cont.isActive) {
                fallbackLocationManager(cont)
            }
        }
    }

    @SuppressLint("MissingPermission")
    private fun fallbackLocationManager(cont: kotlin.coroutines.Continuation<Location?>) {
        try {
            val isGpsEnabled = locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)
            val isNetEnabled = locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)

            val provider = when {
                isGpsEnabled -> LocationManager.GPS_PROVIDER
                isNetEnabled -> LocationManager.NETWORK_PROVIDER
                else -> null
            }

            if (provider == null) {
                cont.resume(null)
                return
            }

            // Check last known location first
            val lastKnown = locationManager.getLastKnownLocation(provider)
            if (lastKnown != null && (System.currentTimeMillis() - lastKnown.time) < 120_000) {
                cont.resume(lastKnown)
                return
            }

            val listener = object : LocationListener {
                override fun onLocationChanged(location: Location) {
                    locationManager.removeUpdates(this)
                    cont.resume(location)
                }
                override fun onProviderEnabled(provider: String) {}
                override fun onProviderDisabled(provider: String) {}
                @Deprecated("Deprecated in Java")
                override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
            }

            locationManager.requestSingleUpdate(provider, listener, Looper.getMainLooper())
        } catch (e: Exception) {
            cont.resume(null)
        }
    }
}
