package com.shopsync.tablet.ui.screen.locations

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
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.shopsync.tablet.data.repository.LocationRepository
import com.shopsync.tablet.domain.model.LocationOption
import com.shopsync.tablet.ui.simpleViewModelFactory
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

@OptIn(ExperimentalCoroutinesApi::class)
class LocationsViewModel(
    private val repository: LocationRepository
) : ViewModel() {
    private val campusId = MutableStateFlow<Long?>(null)
    private val buildingId = MutableStateFlow<Long?>(null)
    private val roomId = MutableStateFlow<Long?>(null)
    private val containerId = MutableStateFlow<Long?>(null)
    private val shelfId = MutableStateFlow<Long?>(null)
    private val drawerId = MutableStateFlow<Long?>(null)

    val campuses = repository.observeCampuses().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val buildings = campusId.flatMapLatest { repository.observeBuildings(it) }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val rooms = buildingId.flatMapLatest { repository.observeRoomsForBuilding(it) }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val containers = roomId.flatMapLatest { repository.observeContainers(it) }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val shelves = containerId.flatMapLatest { repository.observeShelves(it) }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val drawers = shelfId.flatMapLatest { repository.observeDrawers(it) }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val slots = drawerId.flatMapLatest { repository.observeSlots(it) }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun selectCampus(id: Long?) {
        campusId.value = id
        buildingId.value = null
        roomId.value = null
        containerId.value = null
        shelfId.value = null
        drawerId.value = null
    }

    fun selectBuilding(id: Long?) {
        buildingId.value = id
        roomId.value = null
        containerId.value = null
        shelfId.value = null
        drawerId.value = null
    }

    fun selectRoom(id: Long?) {
        roomId.value = id
        containerId.value = null
        shelfId.value = null
        drawerId.value = null
    }

    fun selectContainer(id: Long?) {
        containerId.value = id
        shelfId.value = null
        drawerId.value = null
    }

    fun selectShelf(id: Long?) {
        shelfId.value = id
        drawerId.value = null
    }

    fun selectDrawer(id: Long?) {
        drawerId.value = id
    }

    fun addCampus(name: String, onDone: (Result<Unit>) -> Unit) {
        viewModelScope.launch { runCatching { repository.addCampus(name) }.fold({ onDone(Result.success(Unit)) }, { onDone(Result.failure(it)) }) }
    }

    fun addBuilding(name: String, onDone: (Result<Unit>) -> Unit) {
        val selected = campusId.value ?: return onDone(Result.failure(IllegalArgumentException("Select a campus first.")))
        viewModelScope.launch { runCatching { repository.addBuilding(selected, name) }.fold({ onDone(Result.success(Unit)) }, { onDone(Result.failure(it)) }) }
    }

    fun addRoom(title: String, roomNumber: String, siteArea: String, onDone: (Result<Unit>) -> Unit) {
        val selected = buildingId.value ?: return onDone(Result.failure(IllegalArgumentException("Select a building first.")))
        viewModelScope.launch { runCatching { repository.addRoom(selected, title, roomNumber, siteArea) }.fold({ onDone(Result.success(Unit)) }, { onDone(Result.failure(it)) }) }
    }

    fun addContainer(name: String, onDone: (Result<Unit>) -> Unit) {
        val selected = roomId.value ?: return onDone(Result.failure(IllegalArgumentException("Select a room first.")))
        viewModelScope.launch { runCatching { repository.addContainer(selected, name) }.fold({ onDone(Result.success(Unit)) }, { onDone(Result.failure(it)) }) }
    }

    fun addShelf(name: String, onDone: (Result<Unit>) -> Unit) {
        val selected = containerId.value ?: return onDone(Result.failure(IllegalArgumentException("Select a container first.")))
        viewModelScope.launch { runCatching { repository.addShelf(selected, name) }.fold({ onDone(Result.success(Unit)) }, { onDone(Result.failure(it)) }) }
    }

    fun addDrawer(name: String, onDone: (Result<Unit>) -> Unit) {
        val selected = shelfId.value ?: return onDone(Result.failure(IllegalArgumentException("Select a shelf first.")))
        viewModelScope.launch { runCatching { repository.addDrawer(selected, name) }.fold({ onDone(Result.success(Unit)) }, { onDone(Result.failure(it)) }) }
    }

    fun addSlot(name: String, onDone: (Result<Unit>) -> Unit) {
        val selected = drawerId.value ?: return onDone(Result.failure(IllegalArgumentException("Select a drawer first.")))
        viewModelScope.launch { runCatching { repository.addSlot(selected, name) }.fold({ onDone(Result.success(Unit)) }, { onDone(Result.failure(it)) }) }
    }
}

@Composable
fun LocationsRoute(repository: LocationRepository) {
    val viewModel: LocationsViewModel = viewModel(factory = simpleViewModelFactory { LocationsViewModel(repository) })
    LocationsScreen(viewModel)
}

@Composable
private fun LocationsScreen(viewModel: LocationsViewModel) {
    val campuses by viewModel.campuses.collectAsStateWithLifecycle()
    val buildings by viewModel.buildings.collectAsStateWithLifecycle()
    val rooms by viewModel.rooms.collectAsStateWithLifecycle()
    val containers by viewModel.containers.collectAsStateWithLifecycle()
    val shelves by viewModel.shelves.collectAsStateWithLifecycle()
    val drawers by viewModel.drawers.collectAsStateWithLifecycle()
    val slots by viewModel.slots.collectAsStateWithLifecycle()
    val snackbars = remember { SnackbarHostState() }
    BoxWithConstraints(modifier = Modifier.fillMaxSize().padding(24.dp)) {
        val wide = maxWidth >= 900.dp
        if (wide) {
            Row(horizontalArrangement = Arrangement.spacedBy(20.dp), modifier = Modifier.fillMaxSize()) {
                LocationCreatePane(viewModel, snackbars, Modifier.weight(0.95f).fillMaxHeight())
                LocationHierarchyPane(campuses, buildings, rooms, containers, shelves, drawers, slots, Modifier.weight(1.1f).fillMaxHeight(), viewModel)
            }
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(20.dp), modifier = Modifier.fillMaxSize()) {
                LocationCreatePane(viewModel, snackbars, Modifier.weight(1f).fillMaxWidth())
                LocationHierarchyPane(campuses, buildings, rooms, containers, shelves, drawers, slots, Modifier.weight(1f).fillMaxWidth(), viewModel)
            }
        }
    }
    SnackbarHost(hostState = snackbars)
}

@Composable
private fun LocationCreatePane(
    viewModel: LocationsViewModel,
    snackbars: SnackbarHostState,
    modifier: Modifier
) {
    val scope = rememberCoroutineScope()
    var campusName by rememberSaveable { mutableStateOf("") }
    var buildingName by rememberSaveable { mutableStateOf("") }
    var roomTitle by rememberSaveable { mutableStateOf("") }
    var roomNumber by rememberSaveable { mutableStateOf("") }
    var siteArea by rememberSaveable { mutableStateOf("") }
    var containerName by rememberSaveable { mutableStateOf("") }
    var shelfName by rememberSaveable { mutableStateOf("") }
    var drawerName by rememberSaveable { mutableStateOf("") }
    var slotLabel by rememberSaveable { mutableStateOf("") }

    ElevatedCard(modifier = modifier) {
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item { Text("Add new location", style = MaterialTheme.typography.headlineSmall) }
            item { OutlinedTextField(campusName, { campusName = it }, label = { Text("Campus name") }, modifier = Modifier.fillMaxWidth()) }
            item {
                Button(onClick = {
                    viewModel.addCampus(campusName) { result ->
                        scope.launch { snackbars.showSnackbar(result.exceptionOrNull()?.message ?: "Campus added.") }
                        if (result.isSuccess) campusName = ""
                    }
                }, enabled = campusName.isNotBlank()) { Text("Add campus") }
            }
            item { OutlinedTextField(buildingName, { buildingName = it }, label = { Text("Building name") }, modifier = Modifier.fillMaxWidth()) }
            item {
                Button(onClick = {
                    viewModel.addBuilding(buildingName) { result ->
                        scope.launch { snackbars.showSnackbar(result.exceptionOrNull()?.message ?: "Building added.") }
                        if (result.isSuccess) buildingName = ""
                    }
                }, enabled = buildingName.isNotBlank()) { Text("Add building") }
            }
            item { OutlinedTextField(roomTitle, { roomTitle = it }, label = { Text("Room title") }, modifier = Modifier.fillMaxWidth()) }
            item { OutlinedTextField(roomNumber, { roomNumber = it }, label = { Text("Room number") }, modifier = Modifier.fillMaxWidth()) }
            item { OutlinedTextField(siteArea, { siteArea = it }, label = { Text("Site area") }, modifier = Modifier.fillMaxWidth()) }
            item {
                Button(onClick = {
                    viewModel.addRoom(roomTitle, roomNumber, siteArea) { result ->
                        scope.launch { snackbars.showSnackbar(result.exceptionOrNull()?.message ?: "Room added.") }
                        if (result.isSuccess) {
                            roomTitle = ""
                            roomNumber = ""
                            siteArea = ""
                        }
                    }
                }, enabled = roomTitle.isNotBlank() && roomNumber.isNotBlank() && siteArea.isNotBlank()) { Text("Add room") }
            }
            item { OutlinedTextField(containerName, { containerName = it }, label = { Text("Container name") }, modifier = Modifier.fillMaxWidth()) }
            item {
                Button(onClick = {
                    viewModel.addContainer(containerName) { result ->
                        scope.launch { snackbars.showSnackbar(result.exceptionOrNull()?.message ?: "Container added.") }
                        if (result.isSuccess) containerName = ""
                    }
                }, enabled = containerName.isNotBlank()) { Text("Add container") }
            }
            item { OutlinedTextField(shelfName, { shelfName = it }, label = { Text("Shelf name") }, modifier = Modifier.fillMaxWidth()) }
            item {
                Button(onClick = {
                    viewModel.addShelf(shelfName) { result ->
                        scope.launch { snackbars.showSnackbar(result.exceptionOrNull()?.message ?: "Shelf added.") }
                        if (result.isSuccess) shelfName = ""
                    }
                }, enabled = shelfName.isNotBlank()) { Text("Add shelf") }
            }
            item { OutlinedTextField(drawerName, { drawerName = it }, label = { Text("Drawer name") }, modifier = Modifier.fillMaxWidth()) }
            item {
                Button(onClick = {
                    viewModel.addDrawer(drawerName) { result ->
                        scope.launch { snackbars.showSnackbar(result.exceptionOrNull()?.message ?: "Drawer added.") }
                        if (result.isSuccess) drawerName = ""
                    }
                }, enabled = drawerName.isNotBlank()) { Text("Add drawer") }
            }
            item { OutlinedTextField(slotLabel, { slotLabel = it }, label = { Text("Slot label") }, modifier = Modifier.fillMaxWidth()) }
            item {
                Button(onClick = {
                    viewModel.addSlot(slotLabel) { result ->
                        scope.launch { snackbars.showSnackbar(result.exceptionOrNull()?.message ?: "Slot added.") }
                        if (result.isSuccess) slotLabel = ""
                    }
                }, enabled = slotLabel.isNotBlank()) { Text("Add slot") }
            }
        }
    }
}

@Composable
private fun LocationHierarchyPane(
    campuses: List<LocationOption>,
    buildings: List<LocationOption>,
    rooms: List<LocationOption>,
    containers: List<LocationOption>,
    shelves: List<LocationOption>,
    drawers: List<LocationOption>,
    slots: List<LocationOption>,
    modifier: Modifier,
    viewModel: LocationsViewModel
) {
    ElevatedCard(modifier = modifier) {
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item { Text("Hierarchy browser", style = MaterialTheme.typography.headlineSmall) }
            item { SelectChips("Campus", campuses, viewModel::selectCampus) }
            item { SelectChips("Building", buildings, viewModel::selectBuilding) }
            item { SelectChips("Room", rooms, viewModel::selectRoom) }
            item { SelectChips("Container", containers, viewModel::selectContainer) }
            item { SelectChips("Shelf", shelves, viewModel::selectShelf) }
            item { SelectChips("Drawer", drawers, viewModel::selectDrawer) }
            item { SectionList("Slots", slots) }
        }
    }
}

@Composable
private fun SelectChips(
    title: String,
    items: List<LocationOption>,
    onSelected: (Long?) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(title, style = MaterialTheme.typography.titleLarge)
        if (items.isEmpty()) {
            Text("No $title records yet.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                items.take(6).forEach { option ->
                    AssistChip(onClick = { onSelected(option.id) }, label = { Text(option.label) })
                }
            }
        }
    }
}

@Composable
private fun SectionList(
    title: String,
    items: List<LocationOption>
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(title, style = MaterialTheme.typography.titleLarge)
        if (items.isEmpty()) {
            Text("No $title records yet.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            items.forEach { option ->
                Card {
                    Text(option.label, modifier = Modifier.fillMaxWidth().padding(16.dp))
                }
            }
        }
    }
}
