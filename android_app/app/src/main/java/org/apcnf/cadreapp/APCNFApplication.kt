package org.apcnf.cadreapp

import android.app.Application
import org.apcnf.cadreapp.data.local.OfflineQueueManager
import org.apcnf.cadreapp.data.local.SessionManager

class APCNFApplication : Application() {

    lateinit var sessionManager: SessionManager
        private set

    lateinit var offlineQueueManager: OfflineQueueManager
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        sessionManager = SessionManager(this)
        offlineQueueManager = OfflineQueueManager(this)
    }

    companion object {
        lateinit var instance: APCNFApplication
            private set
    }
}
