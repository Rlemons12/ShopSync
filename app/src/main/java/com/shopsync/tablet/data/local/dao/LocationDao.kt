package com.shopsync.tablet.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import com.shopsync.tablet.data.local.entity.BuildingEntity
import com.shopsync.tablet.data.local.entity.CampusEntity
import com.shopsync.tablet.data.local.entity.ContainerEntity
import com.shopsync.tablet.data.local.entity.DrawerEntity
import com.shopsync.tablet.data.local.entity.RoomEntity
import com.shopsync.tablet.data.local.entity.ShelfEntity
import com.shopsync.tablet.data.local.entity.SlotEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface LocationDao {
    @Query("SELECT * FROM campus ORDER BY name")
    fun observeCampuses(): Flow<List<CampusEntity>>

    @Query("SELECT * FROM building WHERE campusId = :campusId ORDER BY name")
    fun observeBuildings(campusId: Long): Flow<List<BuildingEntity>>

    @Query("SELECT * FROM room WHERE buildingId = :buildingId ORDER BY title, roomNumber")
    fun observeRooms(buildingId: Long): Flow<List<RoomEntity>>

    @Query("SELECT * FROM room WHERE title LIKE '%' || :query || '%' OR roomNumber LIKE '%' || :query || '%' OR siteArea LIKE '%' || :query || '%' ORDER BY title, roomNumber")
    fun observeRoomsByQuery(query: String): Flow<List<RoomEntity>>

    @Query("SELECT * FROM container WHERE roomId = :roomId ORDER BY name")
    fun observeContainers(roomId: Long): Flow<List<ContainerEntity>>

    @Query("SELECT * FROM shelf WHERE containerId = :containerId ORDER BY name")
    fun observeShelves(containerId: Long): Flow<List<ShelfEntity>>

    @Query("SELECT * FROM drawer WHERE shelfId = :shelfId ORDER BY name")
    fun observeDrawers(shelfId: Long): Flow<List<DrawerEntity>>

    @Query("SELECT * FROM slot WHERE drawerId = :drawerId ORDER BY label")
    fun observeSlots(drawerId: Long): Flow<List<SlotEntity>>

    @Query("SELECT COUNT(*) FROM room")
    suspend fun roomCount(): Int

    @Insert
    suspend fun insertCampus(campus: CampusEntity): Long

    @Insert
    suspend fun insertBuilding(building: BuildingEntity): Long

    @Insert
    suspend fun insertRoom(room: RoomEntity): Long

    @Insert
    suspend fun insertContainer(container: ContainerEntity): Long

    @Insert
    suspend fun insertShelf(shelf: ShelfEntity): Long

    @Insert
    suspend fun insertDrawer(drawer: DrawerEntity): Long

    @Insert
    suspend fun insertSlot(slot: SlotEntity): Long
}
