package com.shopsync.tablet.ui.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Dashboard
import androidx.compose.material.icons.outlined.Inventory2
import androidx.compose.material.icons.outlined.QrCodeScanner
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.Warehouse
import androidx.compose.material.icons.outlined.Widgets
import androidx.compose.ui.graphics.vector.ImageVector

enum class ShopSyncDestination(
    val route: String,
    val label: String,
    val icon: ImageVector
) {
    Dashboard("dashboard", "Overview", Icons.Outlined.Dashboard),
    Inventory("inventory", "Inventory", Icons.Outlined.Inventory2),
    RemoteInventory("remote_inventory", "Remote", Icons.Outlined.Warehouse),
    Locations("locations", "Locations", Icons.Outlined.Widgets),
    Search("search", "Search", Icons.Outlined.Search),
    Scanner("scanner", "Scanner", Icons.Outlined.QrCodeScanner)
}
