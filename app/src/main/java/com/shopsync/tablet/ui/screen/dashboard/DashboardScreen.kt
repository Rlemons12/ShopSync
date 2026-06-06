package com.shopsync.tablet.ui.screen.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewmodel.compose.viewModel
import com.shopsync.tablet.data.repository.DashboardRepository
import com.shopsync.tablet.domain.model.DashboardStats
import com.shopsync.tablet.domain.model.UiState
import com.shopsync.tablet.ui.simpleViewModelFactory
import com.shopsync.tablet.ui.components.AdaptiveCards
import com.shopsync.tablet.ui.components.MessagePane
import com.shopsync.tablet.ui.components.SectionTitle
import com.shopsync.tablet.ui.components.StatCard
import java.text.NumberFormat

class DashboardViewModel(
    private val repository: DashboardRepository
) : ViewModel() {
    suspend fun load(): UiState<DashboardStats> = try {
        UiState.Success(repository.getStats())
    } catch (error: Exception) {
        UiState.Error("Dashboard unavailable", error.message ?: "Could not load ShopSync overview.")
    }
}

@Composable
fun DashboardRoute(repository: DashboardRepository) {
    val viewModel: DashboardViewModel = viewModel(
        factory = simpleViewModelFactory { DashboardViewModel(repository) }
    )
    val state by produceState<UiState<DashboardStats>>(initialValue = UiState.Loading) {
        value = viewModel.load()
    }

    when (val current = state) {
        UiState.Loading -> MessagePane("Loading ShopSync", "Preparing the tablet workspace.", Modifier.fillMaxSize())
        is UiState.Error -> MessagePane(current.title, current.message, Modifier.fillMaxSize())
        is UiState.Empty -> MessagePane(current.title, current.message, Modifier.fillMaxSize())
        is UiState.Success -> DashboardScreen(current.data)
    }
}

@Composable
private fun DashboardScreen(stats: DashboardStats) {
    val formatter = NumberFormat.getIntegerInstance()
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(24.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp)
    ) {
        item {
            Card(
                shape = RoundedCornerShape(30.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.78f))
            ) {
                Column(
                    modifier = Modifier.fillMaxWidth().padding(24.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text("ShopSync", style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.onPrimaryContainer)
                    Text(
                        "Tablet-first inventory control for rooms, containers, drawers, and spare parts.",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f)
                    )
                    Text(
                        "Modernized for live scanning, fast location lookup, and large-screen warehouse workflows.",
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.secondary
                    )
                }
            }
        }
        item {
            AdaptiveCards(
                items = listOf(
                    { StatCard("Parts", formatter.format(stats.totalParts), "Tracked catalog entries") },
                    { StatCard("Rooms", formatter.format(stats.totalLocations), "Site locations in the hierarchy") },
                    { StatCard("Units", formatter.format(stats.totalUnits), "Total on-hand stock") },
                    { StatCard("Scans", formatter.format(stats.recentScans), "Master/verify events in the last 7 days") }
                ),
                modifier = Modifier.fillMaxWidth()
            )
        }
        item { SectionTitle("Low stock watchlist") }
        if (stats.lowStockParts.isEmpty()) {
            item { MessagePane("Nothing urgent", "No parts are below the low stock threshold.", Modifier.fillMaxWidth()) }
        } else {
            items(stats.lowStockParts) { part ->
                Card(
                    shape = RoundedCornerShape(24.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.92f))
                ) {
                    Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("${part.partNumber} - ${part.name}", style = MaterialTheme.typography.titleLarge)
                        Text("${part.totalQuantity} ${part.unit} on hand across ${part.locationCount} locations", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
        item { SectionTitle("Recently updated") }
        items(stats.recentlyUpdated) { part ->
            Card(
                shape = RoundedCornerShape(24.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.92f))
            ) {
                Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("${part.partNumber} - ${part.name}", style = MaterialTheme.typography.titleLarge)
                    Text("${part.category} • ${part.manufacturer} ${part.model}".trim(), color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}
