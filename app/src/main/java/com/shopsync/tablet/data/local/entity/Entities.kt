package com.shopsync.tablet.data.local.entity

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(tableName = "campus")
data class CampusEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String
)

@Entity(
    tableName = "building",
    foreignKeys = [
        ForeignKey(
            entity = CampusEntity::class,
            parentColumns = ["id"],
            childColumns = ["campusId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("campusId")]
)
data class BuildingEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val campusId: Long,
    val name: String
)

@Entity(
    tableName = "room",
    foreignKeys = [
        ForeignKey(
            entity = BuildingEntity::class,
            parentColumns = ["id"],
            childColumns = ["buildingId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("buildingId")]
)
data class RoomEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val buildingId: Long,
    val title: String,
    val roomNumber: String,
    val siteArea: String
)

@Entity(
    tableName = "container",
    foreignKeys = [
        ForeignKey(
            entity = RoomEntity::class,
            parentColumns = ["id"],
            childColumns = ["roomId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("roomId")]
)
data class ContainerEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val roomId: Long,
    val name: String
)

@Entity(
    tableName = "shelf",
    foreignKeys = [
        ForeignKey(
            entity = ContainerEntity::class,
            parentColumns = ["id"],
            childColumns = ["containerId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("containerId")]
)
data class ShelfEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val containerId: Long,
    val name: String
)

@Entity(
    tableName = "drawer",
    foreignKeys = [
        ForeignKey(
            entity = ShelfEntity::class,
            parentColumns = ["id"],
            childColumns = ["shelfId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("shelfId")]
)
data class DrawerEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val shelfId: Long,
    val name: String
)

@Entity(
    tableName = "slot",
    foreignKeys = [
        ForeignKey(
            entity = DrawerEntity::class,
            parentColumns = ["id"],
            childColumns = ["drawerId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("drawerId")]
)
data class SlotEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val drawerId: Long,
    val label: String
)

@Entity(
    tableName = "part",
    indices = [Index(value = ["partNumber"], unique = true), Index("name")]
)
data class PartEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val partNumber: String,
    val name: String,
    val manufacturer: String,
    val model: String,
    val category: String,
    val notes: String,
    val documentation: String,
    val updatedAt: Long
)

@Entity(
    tableName = "inventory",
    foreignKeys = [
        ForeignKey(
            entity = PartEntity::class,
            parentColumns = ["id"],
            childColumns = ["partId"],
            onDelete = ForeignKey.CASCADE
        ),
        ForeignKey(
            entity = ContainerEntity::class,
            parentColumns = ["id"],
            childColumns = ["containerId"],
            onDelete = ForeignKey.CASCADE
        ),
        ForeignKey(
            entity = ShelfEntity::class,
            parentColumns = ["id"],
            childColumns = ["shelfId"],
            onDelete = ForeignKey.CASCADE
        ),
        ForeignKey(
            entity = DrawerEntity::class,
            parentColumns = ["id"],
            childColumns = ["drawerId"],
            onDelete = ForeignKey.CASCADE
        ),
        ForeignKey(
            entity = SlotEntity::class,
            parentColumns = ["id"],
            childColumns = ["slotId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("partId"), Index("containerId"), Index("shelfId"), Index("drawerId"), Index("slotId")]
)
data class InventoryEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val partId: Long,
    val containerId: Long?,
    val shelfId: Long?,
    val drawerId: Long?,
    val slotId: Long?,
    val quantity: Int,
    val unit: String,
    val updatedAt: Long
)

@Entity(tableName = "scan_log", indices = [Index("createdAt")])
data class ScanLogEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val masterCode: String,
    val readValue: String,
    val matched: Boolean,
    val score: Int,
    val createdAt: Long
)
