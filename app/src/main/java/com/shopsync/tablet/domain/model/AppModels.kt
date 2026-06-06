package com.shopsync.tablet.domain.model

data class DashboardStats(
    val totalParts: Int,
    val totalLocations: Int,
    val totalUnits: Int,
    val recentScans: Int,
    val lowStockParts: List<PartSummary>,
    val recentlyUpdated: List<PartSummary>
)

data class PartSummary(
    val id: Long,
    val partNumber: String,
    val name: String,
    val manufacturer: String,
    val model: String,
    val category: String,
    val totalQuantity: Int,
    val unit: String,
    val locationCount: Int,
    val updatedAt: Long
)

data class PartLocation(
    val inventoryId: Long,
    val roomLabel: String,
    val containerName: String?,
    val shelfName: String?,
    val drawerName: String?,
    val slotLabel: String?,
    val quantity: Int,
    val unit: String,
    val updatedAt: Long
) {
    val breadcrumb: String
        get() = listOfNotNull(roomLabel, containerName, shelfName, drawerName, slotLabel).joinToString(" / ")
}

data class PartDetail(
    val id: Long,
    val partNumber: String,
    val name: String,
    val manufacturer: String,
    val model: String,
    val category: String,
    val notes: String,
    val documentation: String,
    val totalQuantity: Int,
    val unit: String,
    val locations: List<PartLocation>
)

data class LocationOption(
    val id: Long,
    val label: String
)

data class HierarchySelection(
    val roomId: Long? = null,
    val containerId: Long? = null,
    val shelfId: Long? = null,
    val drawerId: Long? = null,
    val slotId: Long? = null
)

data class RemoteSummary(
    val heading: String,
    val detail: String,
    val contents: List<RemoteContentItem>
)

data class RemoteContentItem(
    val id: Long,
    val level: String,
    val name: String,
    val type: String,
    val quantityLabel: String,
    val updatedAt: Long
)

enum class SearchCategory {
    All,
    Parts,
    Rooms,
    Containers,
    Shelves,
    Drawers,
    Slots
}

data class SearchResult(
    val id: Long,
    val category: SearchCategory,
    val title: String,
    val subtitle: String,
    val supportingText: String
)

data class ScanLog(
    val id: Long,
    val masterCode: String,
    val readValue: String,
    val matched: Boolean,
    val score: Int,
    val createdAt: Long
)

data class AddPartRequest(
    val partNumber: String,
    val name: String,
    val manufacturer: String,
    val model: String,
    val category: String,
    val notes: String,
    val documentation: String,
    val quantity: Int,
    val unit: String,
    val selection: HierarchySelection
)
