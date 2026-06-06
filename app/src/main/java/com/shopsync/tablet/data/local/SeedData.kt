package com.shopsync.tablet.data.local

import com.shopsync.tablet.data.local.entity.BuildingEntity
import com.shopsync.tablet.data.local.entity.CampusEntity
import com.shopsync.tablet.data.local.entity.ContainerEntity
import com.shopsync.tablet.data.local.entity.DrawerEntity
import com.shopsync.tablet.data.local.entity.PartEntity
import com.shopsync.tablet.data.local.entity.RoomEntity
import com.shopsync.tablet.data.local.entity.ScanLogEntity
import com.shopsync.tablet.data.local.entity.ShelfEntity
import com.shopsync.tablet.data.local.entity.SlotEntity

class SeedData(
    private val database: ShopSyncDatabase
) {
    suspend fun seedIfEmpty() {
        if (database.inventoryDao().partCount() > 0) return

        val now = System.currentTimeMillis()

        val campusId = database.locationDao().insertCampus(CampusEntity(name = "North Plant"))
        val buildingId = database.locationDao().insertBuilding(
            BuildingEntity(campusId = campusId, name = "Maintenance Hub")
        )
        val roomAId = database.locationDao().insertRoom(
            RoomEntity(buildingId = buildingId, title = "Electrical Parts", roomNumber = "E-14", siteArea = "Utilities")
        )
        val roomBId = database.locationDao().insertRoom(
            RoomEntity(buildingId = buildingId, title = "Mechanical Stores", roomNumber = "M-08", siteArea = "Assembly")
        )

        val containerA = database.locationDao().insertContainer(ContainerEntity(roomId = roomAId, name = "Cabinet A"))
        val shelfA1 = database.locationDao().insertShelf(ShelfEntity(containerId = containerA, name = "Shelf 1"))
        val drawerA1 = database.locationDao().insertDrawer(DrawerEntity(shelfId = shelfA1, name = "Drawer A"))
        val slotA1 = database.locationDao().insertSlot(SlotEntity(drawerId = drawerA1, label = "Slot A1"))

        val containerB = database.locationDao().insertContainer(ContainerEntity(roomId = roomBId, name = "Rack B"))
        val shelfB1 = database.locationDao().insertShelf(ShelfEntity(containerId = containerB, name = "Shelf 2"))
        val drawerB1 = database.locationDao().insertDrawer(DrawerEntity(shelfId = shelfB1, name = "Drawer C"))
        val slotB1 = database.locationDao().insertSlot(SlotEntity(drawerId = drawerB1, label = "Slot C3"))

        val fuseId = database.inventoryDao().insertPart(
            PartEntity(
                partNumber = "SS-10021",
                name = "Control Fuse",
                manufacturer = "Eaton",
                model = "FNQ-R-10",
                category = "Electrical",
                notes = "Used across legacy panel assemblies.",
                documentation = "Verify amperage before installation.",
                updatedAt = now
            )
        )
        val beltId = database.inventoryDao().insertPart(
            PartEntity(
                partNumber = "SS-22018",
                name = "Drive Belt",
                manufacturer = "Gates",
                model = "BX57",
                category = "Mechanical",
                notes = "Keep one spare per line.",
                documentation = "Store flat and away from heat.",
                updatedAt = now
            )
        )
        val relayId = database.inventoryDao().insertPart(
            PartEntity(
                partNumber = "SS-30504",
                name = "Safety Relay",
                manufacturer = "Allen-Bradley",
                model = "440R-N23132",
                category = "Controls",
                notes = "Critical low-stock item.",
                documentation = "Check firmware match with line PLC.",
                updatedAt = now
            )
        )

        database.inventoryDao().upsertInventory(fuseId, containerA, shelfA1, drawerA1, slotA1, 24, "ea", now)
        database.inventoryDao().upsertInventory(beltId, containerB, shelfB1, drawerB1, slotB1, 6, "ea", now)
        database.inventoryDao().upsertInventory(relayId, containerA, shelfA1, drawerA1, null, 2, "ea", now)

        database.scanDao().insertScan(
            ScanLogEntity(masterCode = "MASTER-10021", readValue = "MASTER-10021", matched = true, score = 100, createdAt = now)
        )
    }
}
