package com.shopsync.tablet.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBarDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.unit.dp
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.shopsync.tablet.AppContainer
import com.shopsync.tablet.ui.navigation.ShopSyncDestination
import com.shopsync.tablet.ui.screen.dashboard.DashboardRoute
import com.shopsync.tablet.ui.screen.inventory.InventoryRoute
import com.shopsync.tablet.ui.screen.locations.LocationsRoute
import com.shopsync.tablet.ui.screen.remoteinventory.RemoteInventoryRoute
import com.shopsync.tablet.ui.screen.scanner.ScannerRoute
import com.shopsync.tablet.ui.screen.search.SearchRoute

@Composable
fun ShopSyncRoot(container: AppContainer) {
    val navController = rememberNavController()
    val destinations = ShopSyncDestination.entries

    BoxWithConstraints(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.linearGradient(
                    colors = listOf(
                        MaterialTheme.colorScheme.background,
                        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.65f),
                        MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.35f)
                    )
                )
            )
    ) {
        val wideLayout = maxWidth >= 900.dp
        val backStackEntry by navController.currentBackStackEntryAsState()
        val currentDestination = backStackEntry?.destination

        Scaffold(
            containerColor = androidx.compose.ui.graphics.Color.Transparent,
            bottomBar = {
                if (!wideLayout) {
                    Surface(
                        tonalElevation = 10.dp,
                        shadowElevation = 12.dp,
                        shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp),
                        color = MaterialTheme.colorScheme.surface.copy(alpha = 0.96f)
                    ) {
                        NavigationBar(
                            containerColor = androidx.compose.ui.graphics.Color.Transparent,
                            tonalElevation = 0.dp,
                            windowInsets = NavigationBarDefaults.windowInsets
                        ) {
                            destinations.forEach { destination ->
                                val selected = currentDestination?.hierarchy?.any { it.route == destination.route } == true
                                NavigationBarItem(
                                    selected = selected,
                                    onClick = {
                                        navController.navigate(destination.route) {
                                            popUpTo(navController.graph.startDestinationId) { saveState = true }
                                            launchSingleTop = true
                                            restoreState = true
                                        }
                                    },
                                    icon = { Icon(destination.icon, contentDescription = destination.label) },
                                    label = { Text(destination.label) }
                                )
                            }
                        }
                    }
                }
            }
        ) { padding ->
            Row(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(horizontal = 14.dp, vertical = 10.dp)
            ) {
                if (wideLayout) {
                    Surface(
                        modifier = Modifier.clip(RoundedCornerShape(30.dp)),
                        shape = RoundedCornerShape(30.dp),
                        color = MaterialTheme.colorScheme.surface.copy(alpha = 0.84f),
                        tonalElevation = 8.dp,
                        shadowElevation = 10.dp
                    ) {
                        Column(
                            modifier = Modifier.padding(vertical = 18.dp),
                            verticalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            Column(modifier = Modifier.padding(horizontal = 18.dp, vertical = 8.dp)) {
                                Text("ShopSync", style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.primary)
                                Text("Tablet console", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            NavigationRail(
                                containerColor = androidx.compose.ui.graphics.Color.Transparent
                            ) {
                                destinations.forEach { destination ->
                                    val selected = currentDestination?.hierarchy?.any { it.route == destination.route } == true
                                    NavigationRailItem(
                                        selected = selected,
                                        onClick = {
                                            navController.navigate(destination.route) {
                                                popUpTo(navController.graph.startDestinationId) { saveState = true }
                                                launchSingleTop = true
                                                restoreState = true
                                            }
                                        },
                                        icon = { Icon(destination.icon, contentDescription = destination.label) },
                                        label = { Text(destination.label) }
                                    )
                                }
                            }
                        }
                    }
                    Spacer(modifier = Modifier.width(14.dp))
                }

                Surface(
                    modifier = Modifier.fillMaxSize(),
                    shape = RoundedCornerShape(34.dp),
                    color = MaterialTheme.colorScheme.surface.copy(alpha = 0.78f),
                    tonalElevation = 6.dp,
                    shadowElevation = 10.dp
                ) {
                    NavHost(
                        navController = navController,
                        startDestination = ShopSyncDestination.Dashboard.route,
                        modifier = Modifier.fillMaxSize()
                    ) {
                        composable(ShopSyncDestination.Dashboard.route) { DashboardRoute(container.dashboardRepository) }
                        composable(ShopSyncDestination.Inventory.route) { InventoryRoute(container.inventoryRepository, container.locationRepository) }
                        composable(ShopSyncDestination.RemoteInventory.route) { RemoteInventoryRoute(container.remoteInventoryRepository, container.locationRepository) }
                        composable(ShopSyncDestination.Locations.route) { LocationsRoute(container.locationRepository) }
                        composable(ShopSyncDestination.Search.route) { SearchRoute(container.searchRepository) }
                        composable(ShopSyncDestination.Scanner.route) { ScannerRoute(container.scannerRepository) }
                    }
                }
            }
        }
    }
}
