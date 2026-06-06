package com.shopsync.tablet.ui.screen.remoteinventory

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Card
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.shopsync.tablet.data.repository.LocationRepository
import com.shopsync.tablet.data.repository.RemoteInventoryRepository
import com.shopsync.tablet.domain.model.HierarchySelection
import com.shopsync.tablet.domain.model.LocationOption
import com.shopsync.tablet.domain.model.RemoteSummary
import com.shopsync.tablet.ui.components.MessagePane
import com.shopsync.tablet.ui.components.SectionTitle
import com.shopsync.tablet.ui.components.formatTimestamp
import com.shopsync.tablet.ui.simpleViewModelFactory
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn

@OptIn(ExperimentalCoroutinesApi::class)
class RemoteInventoryViewModel(
    private val remoteInventoryRepository: RemoteInventoryRepository,
    private val locationRepository: LocationRepository
) : ViewModel() {
    private val roomQuery = MutableStateFlow("")
    private val roomId = MutableStateFlow<Long?>(null)
    private val containerId = MutableStateFlow<Long?>(null)
    private val shelfId = MutableStateFlow<Long?>(null)
    private val drawerId = MutableStateFlow<Long?>(null)
    private val slotId = MutableStateFlow<Long?>(null)

    val rooms = roomQuery.flatMapLatest { locationRepository.observeRoomsByQuery(it) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val containers = roomId.flatMapLatest { locationRepository.observeContainers(it) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val shelves = containerId.flatMapLatest { locationRepository.observeShelves(it) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val drawers = shelfId.flatMapLatest { locationRepository.observeDrawers(it) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val slots = drawerId.flatMapLatest { locationRepository.observeSlots(it) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    val summary = kotlinx.coroutines.flow.combine(roomId, containerId, shelfId, drawerId, slotId) { room, container, shelf, drawer, slot ->
        HierarchySelection(room, container, shelf, drawer, slot)
    }.flatMapLatest(remoteInventoryRepository::observeSummary)
        .stateIn(
            viewModelScope,
            SharingStarted.WhileSubscribed(5_000),
            RemoteSummary("Remote inventory", "Search for a room to begin.", emptyList())
        )

    fun setRoomQuery(query: String) {
        roomQuery.value = query
    }

    fun selectRoom(id: Long?) {
        roomId.value = id
        containerId.value = null
        shelfId.value = null
        drawerId.value = null
        slotId.value = null
    }

    fun selectContainer(id: Long?) {
        containerId.value = id
        shelfId.value = null
        drawerId.value = null
        slotId.value = null
    }

    fun selectShelf(id: Long?) {
        shelfId.value = id
        drawerId.value = null
        slotId.value = null
    }

    fun selectDrawer(id: Long?) {
        drawerId.value = id
        slotId.value = null
    }

    fun selectSlot(id: Long?) {
        slotId.value = id
    }
}

@Composable
fun RemoteInventoryRoute(
    remoteInventoryRepository: RemoteInventoryRepository,
    locationRepository: LocationRepository
) {
    val viewModel: RemoteInventoryViewModel = viewModel(
        factory = simpleViewModelFactory { RemoteInventoryViewModel(remoteInventoryRepository, locationRepository) }
    )
    RemoteInventoryScreen(viewModel)
}

@Composable
private fun RemoteInventoryScreen(viewModel: RemoteInventoryViewModel) {
    val rooms by viewModel.rooms.collectAsStateWithLifecycle()
    val containers by viewModel.containers.collectAsStateWithLifecycle()
    val shelves by viewModel.shelves.collectAsStateWithLifecycle()
    val drawers by viewModel.drawers.collectAsStateWithLifecycle()
    val slots by viewModel.slots.collectAsStateWithLifecycle()
    val summary by viewModel.summary.collectAsStateWithLifecycle()

    BoxWithConstraints(modifier = Modifier.fillMaxSize().padding(24.dp)) {
        val wide = maxWidth >= 900.dp
        if (wide) {
            Row(horizontalArrangement = Arrangement.spacedBy(20.dp), modifier = Modifier.fillMaxSize()) {
                RemoteSelectionPane(
                    rooms = rooms,
                    containers = containers,
                    shelves = shelves,
                    drawers = drawers,
                    slots = slots,
                    modifier = Modifier.weight(0.95f).fillMaxHeight(),
                    onQueryChanged = viewModel::setRoomQuery,
                    onRoomSelected = viewModel::selectRoom,
                    onContainerSelected = viewModel::selectContainer,
                    onShelfSelected = viewModel::selectShelf,
                    onDrawerSelected = viewModel::selectDrawer,
                    onSlotSelected = viewModel::selectSlot
                )
                RemoteSummaryPane(summary, Modifier.weight(1.25f).fillMaxHeight())
            }
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(20.dp), modifier = Modifier.fillMaxSize()) {
                RemoteSelectionPane(
                    rooms = rooms,
                    containers = containers,
                    shelves = shelves,
                    drawers = drawers,
                    slots = slots,
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    onQueryChanged = viewModel::setRoomQuery,
                    onRoomSelected = viewModel::selectRoom,
                    onContainerSelected = viewModel::selectContainer,
                    onShelfSelected = viewModel::selectShelf,
                    onDrawerSelected = viewModel::selectDrawer,
                    onSlotSelected = viewModel::selectSlot
                )
                RemoteSummaryPane(summary, Modifier.weight(1f).fillMaxWidth())
            }
        }
    }
}

@Composable
private fun RemoteSelectionPane(
    rooms: List<LocationOption>,
    containers: List<LocationOption>,
    shelves: List<LocationOption>,
    drawers: List<LocationOption>,
    slots: List<LocationOption>,
    modifier: Modifier,
    onQueryChanged: (String) -> Unit,
    onRoomSelected: (Long?) -> Unit,
    onContainerSelected: (Long?) -> Unit,
    onShelfSelected: (Long?) -> Unit,
    onDrawerSelected: (Long?) -> Unit,
    onSlotSelected: (Long?) -> Unit
) {
    var query by rememberSaveable { mutableStateOf("") }
    ElevatedCard(modifier = modifier) {
        Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text("Remote inventory", style = MaterialTheme.typography.headlineSmall)
            OutlinedTextField(
                value = query,
                onValueChange = {
                    query = it
                    onQueryChanged(it)
                },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Search room") },
                supportingText = { Text("Search by title, room number, or site area") }
            )
            SelectorChips("Rooms", rooms, onRoomSelected)
            SelectorChips("Containers", containers, onContainerSelected)
            SelectorChips("Shelves", shelves, onShelfSelected)
            SelectorChips("Drawers", drawers, onDrawerSelected)
            SelectorChips("Slots", slots, onSlotSelected)
        }
    }
}

@Composable
private fun RemoteSummaryPane(summary: RemoteSummary, modifier: Modifier) {
    ElevatedCard(modifier = modifier) {
        Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text(summary.heading, style = MaterialTheme.typography.headlineSmall)
            Text(summary.detail, color = MaterialTheme.colorScheme.onSurfaceVariant)
            SectionTitle("Contents")
            if (summary.contents.isEmpty()) {
                MessagePane("Nothing at this level", "Select a more specific storage level or add stock to this branch.", Modifier.fillMaxWidth())
            } else {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    items(summary.contents) { item ->
                        Card {
                            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(item.name, style = MaterialTheme.typography.titleLarge)
                                Text(item.quantityLabel, color = MaterialTheme.colorScheme.primary)
                                Text("Updated ${formatTimestamp(item.updatedAt)}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SelectorChips(
    label: String,
    options: List<LocationOption>,
    onSelected: (Long?) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, style = MaterialTheme.typography.labelLarge)
        if (options.isEmpty()) {
            Text("No options available yet.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                options.take(6).forEach { option ->
                    AssistChip(onClick = { onSelected(option.id) }, label = { Text(option.label) })
                }
            }
        }
    }
}
