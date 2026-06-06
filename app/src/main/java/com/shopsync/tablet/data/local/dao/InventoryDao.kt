package com.shopsync.tablet.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Transaction
import com.shopsync.tablet.data.local.entity.InventoryEntity
import com.shopsync.tablet.data.local.entity.PartEntity
import kotlinx.coroutines.flow.Flow

data class PartSummaryRow(
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

data class PartDetailRow(
    val id: Long,
    val partNumber: String,
    val name: String,
    val manufacturer: String,
    val model: String,
    val category: String,
    val notes: String,
    val documentation: String,
    val updatedAt: Long
)

data class PartLocationRow(
    val inventoryId: Long,
    val roomLabel: String,
    val containerName: String?,
    val shelfName: String?,
    val drawerName: String?,
    val slotLabel: String?,
    val quantity: Int,
    val unit: String,
    val updatedAt: Long
)

@Dao
interface InventoryDao {
    @Query(
        """
        SELECT
            p.id,
            p.partNumber,
            p.name,
            p.manufacturer,
            p.model,
            p.category,
            COALESCE(SUM(i.quantity), 0) AS totalQuantity,
            COALESCE(MAX(i.unit), '') AS unit,
            COUNT(i.id) AS locationCount,
            MAX(COALESCE(i.updatedAt, p.updatedAt)) AS updatedAt
        FROM part p
        LEFT JOIN inventory i ON i.partId = p.id
        WHERE :query = '' OR p.partNumber LIKE '%' || :query || '%' OR p.name LIKE '%' || :query || '%' OR p.model LIKE '%' || :query || '%' OR p.manufacturer LIKE '%' || :query || '%'
        GROUP BY p.id
        ORDER BY p.partNumber
        """
    )
    fun observePartSummaries(query: String): Flow<List<PartSummaryRow>>

    @Query("SELECT * FROM part WHERE id = :partId")
    suspend fun getPart(partId: Long): PartEntity?

    @Query(
        """
        SELECT
            p.id,
            p.partNumber,
            p.name,
            p.manufacturer,
            p.model,
            p.category,
            p.notes,
            p.documentation,
            p.updatedAt
        FROM part p
        WHERE p.id = :partId
        """
    )
    suspend fun getPartDetailRow(partId: Long): PartDetailRow?

    @Query(
        """
        SELECT
            i.id AS inventoryId,
            room.title || ' / Room ' || room.roomNumber || ' / ' || room.siteArea AS roomLabel,
            container.name AS containerName,
            shelf.name AS shelfName,
            drawer.name AS drawerName,
            slot.label AS slotLabel,
            i.quantity,
            i.unit,
            i.updatedAt
        FROM inventory i
        INNER JOIN container ON container.id = i.containerId
        INNER JOIN room ON room.id = container.roomId
        LEFT JOIN shelf ON shelf.id = i.shelfId
        LEFT JOIN drawer ON drawer.id = i.drawerId
        LEFT JOIN slot ON slot.id = i.slotId
        WHERE i.partId = :partId
        ORDER BY room.title, container.name, shelf.name, drawer.name, slot.label
        """
    )
    suspend fun getPartLocations(partId: Long): List<PartLocationRow>

    @Query("SELECT COUNT(*) FROM part")
    suspend fun partCount(): Int

    @Query("SELECT COALESCE(SUM(quantity), 0) FROM inventory")
    suspend fun unitCount(): Int

    @Query(
        """
        SELECT
            p.id,
            p.partNumber,
            p.name,
            p.manufacturer,
            p.model,
            p.category,
            COALESCE(SUM(i.quantity), 0) AS totalQuantity,
            COALESCE(MAX(i.unit), '') AS unit,
            COUNT(i.id) AS locationCount,
            MAX(COALESCE(i.updatedAt, p.updatedAt)) AS updatedAt
        FROM part p
        LEFT JOIN inventory i ON i.partId = p.id
        GROUP BY p.id
        HAVING totalQuantity <= :threshold
        ORDER BY totalQuantity ASC, p.partNumber ASC
        LIMIT :limit
        """
    )
    suspend fun getLowStockParts(threshold: Int, limit: Int): List<PartSummaryRow>

    @Query(
        """
        SELECT
            p.id,
            p.partNumber,
            p.name,
            p.manufacturer,
            p.model,
            p.category,
            COALESCE(SUM(i.quantity), 0) AS totalQuantity,
            COALESCE(MAX(i.unit), '') AS unit,
            COUNT(i.id) AS locationCount,
            MAX(COALESCE(i.updatedAt, p.updatedAt)) AS updatedAt
        FROM part p
        LEFT JOIN inventory i ON i.partId = p.id
        GROUP BY p.id
        ORDER BY updatedAt DESC
        LIMIT :limit
        """
    )
    suspend fun getRecentlyUpdatedParts(limit: Int): List<PartSummaryRow>

    @Insert
    suspend fun insertPart(part: PartEntity): Long

    @Insert
    suspend fun insertInventory(inventory: InventoryEntity): Long

    @Query(
        """
        SELECT * FROM inventory
        WHERE partId = :partId
        AND ((containerId IS NULL AND :containerId IS NULL) OR containerId = :containerId)
        AND ((shelfId IS NULL AND :shelfId IS NULL) OR shelfId = :shelfId)
        AND ((drawerId IS NULL AND :drawerId IS NULL) OR drawerId = :drawerId)
        AND ((slotId IS NULL AND :slotId IS NULL) OR slotId = :slotId)
        LIMIT 1
        """
    )
    suspend fun findInventoryAtLocation(
        partId: Long,
        containerId: Long?,
        shelfId: Long?,
        drawerId: Long?,
        slotId: Long?
    ): InventoryEntity?

    @Query("UPDATE inventory SET quantity = :quantity, unit = :unit, updatedAt = :updatedAt WHERE id = :inventoryId")
    suspend fun updateInventory(inventoryId: Long, quantity: Int, unit: String, updatedAt: Long)

    @Query("UPDATE part SET updatedAt = :updatedAt WHERE id = :partId")
    suspend fun touchPart(partId: Long, updatedAt: Long)

    @Transaction
    suspend fun upsertInventory(
        partId: Long,
        containerId: Long?,
        shelfId: Long?,
        drawerId: Long?,
        slotId: Long?,
        quantity: Int,
        unit: String,
        updatedAt: Long
    ) {
        val existing = findInventoryAtLocation(partId, containerId, shelfId, drawerId, slotId)
        if (existing == null) {
            insertInventory(
                InventoryEntity(
                    partId = partId,
                    containerId = containerId,
                    shelfId = shelfId,
                    drawerId = drawerId,
                    slotId = slotId,
                    quantity = quantity,
                    unit = unit,
                    updatedAt = updatedAt
                )
            )
        } else {
            updateInventory(
                inventoryId = existing.id,
                quantity = existing.quantity + quantity,
                unit = unit,
                updatedAt = updatedAt
            )
        }
        touchPart(partId, updatedAt)
    }
}
