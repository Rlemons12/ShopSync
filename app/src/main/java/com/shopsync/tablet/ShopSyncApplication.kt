package com.shopsync.tablet

import android.app.Application
import com.shopsync.tablet.data.local.SeedData
import com.shopsync.tablet.data.local.ShopSyncDatabase
import com.shopsync.tablet.data.repository.DashboardRepository
import com.shopsync.tablet.data.repository.InventoryRepository
import com.shopsync.tablet.data.repository.LocationRepository
import com.shopsync.tablet.data.repository.RemoteInventoryRepository
import com.shopsync.tablet.data.repository.ScannerRepository
import com.shopsync.tablet.data.repository.SearchRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class ShopSyncApplication : Application() {
    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    lateinit var appContainer: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        val database = ShopSyncDatabase.getInstance(this)
        appContainer = AppContainer(
            inventoryRepository = InventoryRepository(database),
            locationRepository = LocationRepository(database),
            dashboardRepository = DashboardRepository(database),
            remoteInventoryRepository = RemoteInventoryRepository(database),
            searchRepository = SearchRepository(database),
            scannerRepository = ScannerRepository(database)
        )
        applicationScope.launch {
            SeedData(database).seedIfEmpty()
        }
    }
}

data class AppContainer(
    val inventoryRepository: InventoryRepository,
    val locationRepository: LocationRepository,
    val dashboardRepository: DashboardRepository,
    val remoteInventoryRepository: RemoteInventoryRepository,
    val searchRepository: SearchRepository,
    val scannerRepository: ScannerRepository
)
