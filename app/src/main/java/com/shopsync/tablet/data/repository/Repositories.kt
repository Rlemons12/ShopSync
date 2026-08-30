package com.shopsync.tablet.data.repository

import com.shopsync.tablet.data.local.ShopSyncDatabase
import com.shopsync.tablet.data.local.dao.PartDetailRow
import com.shopsync.tablet.data.local.dao.PartLocationRow
import com.shopsync.tablet.data.local.dao.PartSummaryRow
import com.shopsync.tablet.data.local.dao.SearchRow
import com.shopsync.tablet.data.local.entity.BuildingEntity
import com.shopsync.tablet.data.local.entity.CampusEntity
import com.shopsync.tablet.data.local.entity.ContainerEntity
import com.shopsync.tablet.data.local.entity.DrawerEntity
import com.shopsync.tablet.data.local.entity.PartEntity
import com.shopsync.tablet.data.local.entity.RoomEntity
import com.shopsync.tablet.data.local.entity.ScanLogEntity
import com.shopsync.tablet.data.local.entity.ShelfEntity
import com.shopsync.tablet.data.local.entity.SlotEntity
import com.shopsync.tablet.domain.model.AddPartRequest
import com.shopsync.tablet.domain.model.DashboardStats
import com.shopsync.tablet.domain.model.HierarchySelection
import com.shopsync.tablet.domain.model.LocationOption
import com.shopsync.tablet.domain.model.PartDetail
import com.shopsync.tablet.domain.model.PartLocation
import com.shopsync.tablet.domain.model.PartSummary
import com.shopsync.tablet.domain.model.RemoteContentItem
import com.shopsync.tablet.domain.model.RemoteSummary
import com.shopsync.tablet.domain.model.ScanLog
import com.shopsync.tablet.domain.model.SearchCategory
import com.shopsync.tablet.domain.model.SearchResult
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext

class InventoryRepository(
    private val database: ShopSyncDatabase,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    fun observePartSummaries(query: String): Flow<List<PartSummary>> =
        database.inventoryDao().observePartSummaries(query).map { rows ->
            rows.map { it.toModel() }
        }

    suspend fun getPartDetail(partId: Long): PartDetail? = withContext(ioDispatcher) {
        val part = database.inventoryDao().getPartDetailRow(partId) ?: return@withContext null
        val locations = database.inventoryDao().getPartLocations(partId).map { it.toModel() }
        part.toDetail(locations)
    }

    suspend fun addPart(request: AddPartRequest) = withContext(ioDispatcher) {
        val now = System.currentTimeMillis()
        val partId = database.inventoryDao().insertPart(
            PartEntity(
                partNumber = request.partNumber.trim(),
                name = request.name.trim(),
                manufacturer = request.manufacturer.trim(),
                model = request.model.trim(),
                category = request.category.trim(),
                notes = request.notes.trim(),
                documentation = request.documentation.trim(),
                updatedAt = now
            )
        )
        if (request.quantity > 0 && request.selection.containerId != null) {
            database.inventoryDao().upsertInventory(
                partId = partId,
                containerId = request.selection.containerId,
                shelfId = request.selection.shelfId,
                drawerId = request.selection.drawerId,
                slotId = request.selection.slotId,
                quantity = request.quantity,
                unit = request.unit.ifBlank { "ea" },
                updatedAt = now
            )
        }
    }

    suspend fun addStock(partId: Long, quantity: Int, unit: String, selection: HierarchySelection) =
        withContext(ioDispatcher) {
            require(selection.containerId != null) { "A container is required for stock placement." }
            val now = System.currentTimeMillis()
            database.inventoryDao().upsertInventory(
                partId = partId,
                containerId = selection.containerId,
                shelfId = selection.shelfId,
                drawerId = selection.drawerId,
                slotId = selection.slotId,
                quantity = quantity,
                unit = unit.ifBlank { "ea" },
                updatedAt = now
            )
        }
}

class LocationRepository(
    private val database: ShopSyncDatabase,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    fun observeCampuses(): Flow<List<LocationOption>> =
        database.locationDao().observeCampuses().map { list ->
            list.map { campus -> LocationOption(campus.id, campus.name) }
        }

    fun observeBuildings(campusId: Long?): Flow<List<LocationOption>> =
        campusId?.let { id ->
            database.locationDao().observeBuildings(id).map { list ->
                list.map { building -> LocationOption(building.id, building.name) }
            }
        } ?: flow { emit(emptyList()) }

    fun observeRoomsForBuilding(buildingId: Long?): Flow<List<LocationOption>> =
        buildingId?.let { id ->
            database.locationDao().observeRooms(id).map { list ->
                list.map { room ->
                    LocationOption(room.id, "${room.title} (Room ${room.roomNumber}, ${room.siteArea})")
                }
            }
        } ?: flow { emit(emptyList()) }

    fun observeRoomsByQuery(query: String): Flow<List<LocationOption>> =
        database.locationDao().observeRoomsByQuery(query).map { list ->
            list.map { room ->
                LocationOption(room.id, "${room.title} (Room ${room.roomNumber}, ${room.siteArea})")
            }
        }

    fun observeContainers(roomId: Long?): Flow<List<LocationOption>> =
        roomId?.let { id ->
            database.locationDao().observeContainers(id).map { list ->
                list.map { container -> LocationOption(container.id, container.name) }
            }
        } ?: flow { emit(emptyList()) }

    fun observeShelves(containerId: Long?): Flow<List<LocationOption>> =
        containerId?.let { id ->
            database.locationDao().observeShelves(id).map { list ->
                list.map { shelf -> LocationOption(shelf.id, shelf.name) }
            }
        } ?: flow { emit(emptyList()) }

    fun observeDrawers(shelfId: Long?): Flow<List<LocationOption>> =
        shelfId?.let { id ->
            database.locationDao().observeDrawers(id).map { list ->
                list.map { drawer -> LocationOption(drawer.id, drawer.name) }
            }
        } ?: flow { emit(emptyList()) }

    fun observeSlots(drawerId: Long?): Flow<List<LocationOption>> =
        drawerId?.let { id ->
            database.locationDao().observeSlots(id).map { list ->
                list.map { slot -> LocationOption(slot.id, slot.label) }
            }
        } ?: flow { emit(emptyList()) }

    suspend fun addCampus(name: String): Long = withContext(ioDispatcher) {
        database.locationDao().insertCampus(CampusEntity(name = name.trim()))
    }

    suspend fun addBuilding(campusId: Long, name: String): Long = withContext(ioDispatcher) {
        database.locationDao().insertBuilding(BuildingEntity(campusId = campusId, name = name.trim()))
    }

    suspend fun addRoom(buildingId: Long, title: String, roomNumber: String, siteArea: String): Long = withContext(ioDispatcher) {
        database.locationDao().insertRoom(
            RoomEntity(
                buildingId = buildingId,
                title = title.trim(),
                roomNumber = roomNumber.trim(),
                siteArea = siteArea.trim()
            )
        )
    }

    suspend fun addContainer(roomId: Long, name: String): Long = withContext(ioDispatcher) {
        database.locationDao().insertContainer(ContainerEntity(roomId = roomId, name = name.trim()))
    }

    suspend fun addShelf(containerId: Long, name: String): Long = withContext(ioDispatcher) {
        database.locationDao().insertShelf(ShelfEntity(containerId = containerId, name = name.trim()))
    }

    suspend fun addDrawer(shelfId: Long, name: String): Long = withContext(ioDispatcher) {
        database.locationDao().insertDrawer(DrawerEntity(shelfId = shelfId, name = name.trim()))
    }

    suspend fun addSlot(drawerId: Long, label: String): Long = withContext(ioDispatcher) {
        database.locationDao().insertSlot(SlotEntity(drawerId = drawerId, label = label.trim()))
    }
}

class DashboardRepository(
    private val database: ShopSyncDatabase,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    suspend fun getStats(): DashboardStats = withContext(ioDispatcher) {
        DashboardStats(
            totalParts = database.inventoryDao().partCount(),
            totalLocations = database.locationDao().roomCount(),
            totalUnits = database.inventoryDao().unitCount(),
            recentScans = database.scanDao().recentScanCount(System.currentTimeMillis() - 7 * 24 * 60 * 60 * 1000L),
            lowStockParts = database.inventoryDao().getLowStockParts(threshold = 5, limit = 5).map { it.toModel() },
            recentlyUpdated = database.inventoryDao().getRecentlyUpdatedParts(limit = 5).map { it.toModel() }
        )
    }
}

class RemoteInventoryRepository(
    private val database: ShopSyncDatabase,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    fun observeSummary(selection: HierarchySelection): Flow<RemoteSummary> {
        val heading = when {
            selection.slotId != null -> "Slot selected"
            selection.drawerId != null -> "Drawer selected"
            selection.shelfId != null -> "Shelf selected"
            selection.containerId != null -> "Container selected"
            selection.roomId != null -> "Room selected"
            else -> "Remote inventory"
        }
        return database.remoteInventoryDao().observeRemoteItems(
            containerId = selection.containerId,
            shelfId = selection.shelfId,
            drawerId = selection.drawerId,
            slotId = selection.slotId
        ).map { rows ->
            val detail = when {
                selection.slotId != null -> "Focused on one slot."
                selection.drawerId != null -> "Reviewing stock assigned to the selected drawer."
                selection.shelfId != null -> "Reviewing stock assigned to the selected shelf."
                selection.containerId != null -> "Reviewing stock assigned to the selected container."
                selection.roomId != null -> "Choose a container, shelf, drawer, or slot to narrow the view."
                else -> "Search for a room to begin."
            }
            RemoteSummary(
                heading = heading,
                detail = detail,
                contents = rows.map {
                    RemoteContentItem(
                        id = it.id,
                        level = it.level,
                        name = it.name,
                        type = it.type,
                        quantityLabel = it.quantityLabel,
                        updatedAt = it.updatedAt
                    )
                }
            )
        }
    }
}

class SearchRepository(
    private val database: ShopSyncDatabase,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    suspend fun search(query: String, category: SearchCategory): List<SearchResult> = withContext(ioDispatcher) {
        val limit = 10
        val rows = buildList {
            if (category == SearchCategory.All || category == SearchCategory.Parts) addAll(database.searchDao().searchParts(query, limit))
            if (category == SearchCategory.All || category == SearchCategory.Rooms) addAll(database.searchDao().searchRooms(query, limit))
            if (category == SearchCategory.All || category == SearchCategory.Containers) addAll(database.searchDao().searchContainers(query, limit))
            if (category == SearchCategory.All || category == SearchCategory.Shelves) addAll(database.searchDao().searchShelves(query, limit))
            if (category == SearchCategory.All || category == SearchCategory.Drawers) addAll(database.searchDao().searchDrawers(query, limit))
            if (category == SearchCategory.All || category == SearchCategory.Slots) addAll(database.searchDao().searchSlots(query, limit))
        }
        rows.map { it.toModel() }
    }
}

class ScannerRepository(
    private val database: ShopSyncDatabase,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    fun observeRecentScans(): Flow<List<ScanLog>> =
        database.scanDao().observeRecentScans().map { list ->
            list.map {
                ScanLog(
                    id = it.id,
                    masterCode = it.masterCode,
                    readValue = it.readValue,
                    matched = it.matched,
                    score = it.score,
                    createdAt = it.createdAt
                )
            }
        }

    suspend fun saveScan(masterCode: String, readValue: String, matched: Boolean, score: Int) = withContext(ioDispatcher) {
        database.scanDao().insertScan(
            ScanLogEntity(
                masterCode = masterCode,
                readValue = readValue,
                matched = matched,
                score = score,
                createdAt = System.currentTimeMillis()
            )
        )
    }
}

private fun PartSummaryRow.toModel() = PartSummary(
    id = id,
    partNumber = partNumber,
    name = name,
    manufacturer = manufacturer,
    model = model,
    category = category,
    totalQuantity = totalQuantity,
    unit = unit,
    locationCount = locationCount,
    updatedAt = updatedAt
)

private fun PartLocationRow.toModel() = PartLocation(
    inventoryId = inventoryId,
    roomLabel = roomLabel,
    containerName = containerName,
    shelfName = shelfName,
    drawerName = drawerName,
    slotLabel = slotLabel,
    quantity = quantity,
    unit = unit,
    updatedAt = updatedAt
)

private fun PartDetailRow.toDetail(locations: List<PartLocation>): PartDetail {
    val total = locations.sumOf { it.quantity }
    return PartDetail(
        id = id,
        partNumber = partNumber,
        name = name,
        manufacturer = manufacturer,
        model = model,
        category = category,
        notes = notes,
        documentation = documentation,
        totalQuantity = total,
        unit = locations.firstOrNull()?.unit.orEmpty(),
        locations = locations
    )
}

private fun SearchRow.toModel(): SearchResult {
    val mappedCategory = when (category) {
        "Parts" -> SearchCategory.Parts
        "Rooms" -> SearchCategory.Rooms
        "Containers" -> SearchCategory.Containers
        "Shelves" -> SearchCategory.Shelves
        "Drawers" -> SearchCategory.Drawers
        "Slots" -> SearchCategory.Slots
        else -> SearchCategory.All
    }
    return SearchResult(
        id = id,
        category = mappedCategory,
        title = title,
        subtitle = subtitle,
        supportingText = supportingText
    )
}
