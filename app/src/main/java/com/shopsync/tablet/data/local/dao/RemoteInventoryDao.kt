package com.shopsync.tablet.data.local.dao

import androidx.room.Dao
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

data class RemoteItemRow(
    val id: Long,
    val level: String,
    val name: String,
    val type: String,
    val quantityLabel: String,
    val updatedAt: Long
)

@Dao
interface RemoteInventoryDao {
    @Query(
        """
        SELECT
            p.id AS id,
            'Part' AS level,
            p.partNumber || ' - ' || p.name AS name,
            COALESCE(p.model, '') AS type,
            CAST(i.quantity AS TEXT) || ' ' || i.unit AS quantityLabel,
            i.updatedAt AS updatedAt
        FROM inventory i
        INNER JOIN part p ON p.id = i.partId
        WHERE (:slotId IS NOT NULL AND i.slotId = :slotId)
           OR (:slotId IS NULL AND :drawerId IS NOT NULL AND i.drawerId = :drawerId)
           OR (:slotId IS NULL AND :drawerId IS NULL AND :shelfId IS NOT NULL AND i.shelfId = :shelfId)
           OR (:slotId IS NULL AND :drawerId IS NULL AND :shelfId IS NULL AND :containerId IS NOT NULL AND i.containerId = :containerId)
        ORDER BY p.partNumber
        """
    )
    fun observeRemoteItems(
        containerId: Long?,
        shelfId: Long?,
        drawerId: Long?,
        slotId: Long?
    ): Flow<List<RemoteItemRow>>

    @Query("SELECT COUNT(*) FROM shelf WHERE containerId = :containerId")
    suspend fun shelfCount(containerId: Long): Int

    @Query("SELECT COUNT(*) FROM drawer WHERE shelfId = :shelfId")
    suspend fun drawerCount(shelfId: Long): Int

    @Query("SELECT COUNT(*) FROM slot WHERE drawerId = :drawerId")
    suspend fun slotCount(drawerId: Long): Int
}
