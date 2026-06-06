package com.shopsync.tablet.data.local.dao

import androidx.room.Dao
import androidx.room.Query

data class SearchRow(
    val id: Long,
    val category: String,
    val title: String,
    val subtitle: String,
    val supportingText: String
)

@Dao
interface SearchDao {
    @Query(
        """
        SELECT id, 'Parts' AS category, partNumber || ' - ' || name AS title, manufacturer AS subtitle, model AS supportingText
        FROM part
        WHERE :query != '' AND (partNumber LIKE '%' || :query || '%' OR name LIKE '%' || :query || '%' OR manufacturer LIKE '%' || :query || '%' OR model LIKE '%' || :query || '%')
        ORDER BY partNumber
        LIMIT :limit
        """
    )
    suspend fun searchParts(query: String, limit: Int): List<SearchRow>

    @Query(
        """
        SELECT id, 'Rooms' AS category, title AS title, 'Room ' || roomNumber AS subtitle, siteArea AS supportingText
        FROM room
        WHERE :query != '' AND (title LIKE '%' || :query || '%' OR roomNumber LIKE '%' || :query || '%' OR siteArea LIKE '%' || :query || '%')
        ORDER BY title
        LIMIT :limit
        """
    )
    suspend fun searchRooms(query: String, limit: Int): List<SearchRow>

    @Query(
        """
        SELECT c.id, 'Containers' AS category, c.name AS title, r.title AS subtitle, r.siteArea AS supportingText
        FROM container c
        INNER JOIN room r ON r.id = c.roomId
        WHERE :query != '' AND (c.name LIKE '%' || :query || '%' OR r.title LIKE '%' || :query || '%')
        ORDER BY c.name
        LIMIT :limit
        """
    )
    suspend fun searchContainers(query: String, limit: Int): List<SearchRow>

    @Query(
        """
        SELECT s.id, 'Shelves' AS category, s.name AS title, c.name AS subtitle, r.title AS supportingText
        FROM shelf s
        INNER JOIN container c ON c.id = s.containerId
        INNER JOIN room r ON r.id = c.roomId
        WHERE :query != '' AND (s.name LIKE '%' || :query || '%' OR c.name LIKE '%' || :query || '%' OR r.title LIKE '%' || :query || '%')
        ORDER BY s.name
        LIMIT :limit
        """
    )
    suspend fun searchShelves(query: String, limit: Int): List<SearchRow>

    @Query(
        """
        SELECT d.id, 'Drawers' AS category, d.name AS title, s.name AS subtitle, c.name AS supportingText
        FROM drawer d
        INNER JOIN shelf s ON s.id = d.shelfId
        INNER JOIN container c ON c.id = s.containerId
        WHERE :query != '' AND (d.name LIKE '%' || :query || '%' OR s.name LIKE '%' || :query || '%' OR c.name LIKE '%' || :query || '%')
        ORDER BY d.name
        LIMIT :limit
        """
    )
    suspend fun searchDrawers(query: String, limit: Int): List<SearchRow>

    @Query(
        """
        SELECT sl.id, 'Slots' AS category, sl.label AS title, d.name AS subtitle, s.name AS supportingText
        FROM slot sl
        INNER JOIN drawer d ON d.id = sl.drawerId
        INNER JOIN shelf s ON s.id = d.shelfId
        WHERE :query != '' AND (sl.label LIKE '%' || :query || '%' OR d.name LIKE '%' || :query || '%' OR s.name LIKE '%' || :query || '%')
        ORDER BY sl.label
        LIMIT :limit
        """
    )
    suspend fun searchSlots(query: String, limit: Int): List<SearchRow>
}
