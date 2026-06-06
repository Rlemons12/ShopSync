package com.shopsync.tablet.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.shopsync.tablet.data.local.dao.InventoryDao
import com.shopsync.tablet.data.local.dao.LocationDao
import com.shopsync.tablet.data.local.dao.RemoteInventoryDao
import com.shopsync.tablet.data.local.dao.ScanDao
import com.shopsync.tablet.data.local.dao.SearchDao
import com.shopsync.tablet.data.local.entity.BuildingEntity
import com.shopsync.tablet.data.local.entity.CampusEntity
import com.shopsync.tablet.data.local.entity.ContainerEntity
import com.shopsync.tablet.data.local.entity.DrawerEntity
import com.shopsync.tablet.data.local.entity.InventoryEntity
import com.shopsync.tablet.data.local.entity.PartEntity
import com.shopsync.tablet.data.local.entity.RoomEntity
import com.shopsync.tablet.data.local.entity.ScanLogEntity
import com.shopsync.tablet.data.local.entity.ShelfEntity
import com.shopsync.tablet.data.local.entity.SlotEntity
@Database(
    entities = [
        CampusEntity::class,
        BuildingEntity::class,
        RoomEntity::class,
        ContainerEntity::class,
        ShelfEntity::class,
        DrawerEntity::class,
        SlotEntity::class,
        PartEntity::class,
        InventoryEntity::class,
        ScanLogEntity::class
    ],
    version = 1,
    exportSchema = false
)
abstract class ShopSyncDatabase : RoomDatabase() {
    abstract fun locationDao(): LocationDao
    abstract fun inventoryDao(): InventoryDao
    abstract fun remoteInventoryDao(): RemoteInventoryDao
    abstract fun searchDao(): SearchDao
    abstract fun scanDao(): ScanDao

    companion object {
        fun build(context: Context): ShopSyncDatabase =
            Room.databaseBuilder(context, ShopSyncDatabase::class.java, "shopsync-tablet.db")
                .fallbackToDestructiveMigration()
                .build()

        @Volatile
        private var INSTANCE: ShopSyncDatabase? = null

        fun getInstance(context: Context): ShopSyncDatabase =
            INSTANCE ?: synchronized(this) {
                INSTANCE ?: build(context.applicationContext).also { INSTANCE = it }
            }
    }
}
