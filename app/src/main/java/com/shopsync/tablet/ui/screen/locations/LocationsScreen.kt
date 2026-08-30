package com.shopsync.tablet.ui.screen.locations

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
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
    val campusId = MutableStateFlow<Long?>(null)
    val buildingId = MutableStateFlow<Long?>(null)
    val roomId = MutableStateFlow<Long?>(null)
    val containerId = MutableStateFlow<Long?>(null)
    val shelfId = MutableStateFlow<Long?>(null)
    val drawerId = MutableStateFlow<Long?>(null)

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

    fun addCampus(name: String, onDone: (Result<Long>) -> Unit) {
        viewModelScope.launch {
            runCatching { repository.addCampus(name) }
                .fold(
                    { id -> selectCampus(id); onDone(Result.success(id)) },
                    { onDone(Result.failure(it)) }
                )
        }
    }

    fun addBuilding(name: String, onDone: (Result<Long>) -> Unit) {
        val selected = campusId.value ?: return onDone(Result.failure(IllegalArgumentException("Select a campus first.")))
        viewModelScope.launch {
            runCatching { repository.addBuilding(selected, name) }
                .fold(
                    { id -> selectBuilding(id); onDone(Result.success(id)) },
                    { onDone(Result.failure(it)) }
                )
        }
    }

    fun addRoom(title: String, roomNumber: String, siteArea: String, onDone: (Result<Long>) -> Unit) {
        val selected = buildingId.value ?: return onDone(Result.failure(IllegalArgumentException("Select a building first.")))
        viewModelScope.launch {
            runCatching { repository.addRoom(selected, title, roomNumber, siteArea) }
                .fold(
                    { id -> selectRoom(id); onDone(Result.success(id)) },
                    { onDone(Result.failure(it)) }
                )
        }
    }

    fun addContainer(name: String, onDone: (Result<Long>) -> Unit) {
        val selected = roomId.value ?: return onDone(Result.failure(IllegalArgumentException("Select a room first.")))
        viewModelScope.launch {
            runCatching { repository.addContainer(selected, name) }
                .fold(
                    { id -> selectContainer(id); onDone(Result.success(id)) },
                    { onDone(Result.failure(it)) }
                )
        }
    }

    fun addShelf(name: String, onDone: (Result<Long>) -> Unit) {
        val selected = containerId.value ?: return onDone(Result.failure(IllegalArgumentException("Select a container first.")))
        viewModelScope.launch {
            runCatching { repository.addShelf(selected, name) }
                .fold(
                    { id -> selectShelf(id); onDone(Result.success(id)) },
                    { onDone(Result.failure(it)) }
                )
        }
    }

    fun addDrawer(name: String, onDone: (Result<Long>) -> Unit) {
        val selected = shelfId.value ?: return onDone(Result.failure(IllegalArgumentException("Select a shelf first.")))
        viewModelScope.launch {
            runCatching { repository.addDrawer(selected, name) }
                .fold(
                    { id -> selectDrawer(id); onDone(Result.success(id)) },
                    { onDone(Result.failure(it)) }
                )
        }
    }

    fun addSlot(name: String, onDone: (Result<Long>) -> Unit) {
        val selected = drawerId.value ?: return onDone(Result.failure(IllegalArgumentException("Select a drawer first.")))
        viewModelScope.launch {
            runCatching { repository.addSlot(selected, name) }
                .fold(
                    { id -> onDone(Result.success(id)) },
                    { onDone(Result.failure(it)) }
                )
        }
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

    val selectedCampusId by viewModel.campusId.collectAsStateWithLifecycle()
    val selectedBuildingId by viewModel.buildingId.collectAsStateWithLifecycle()
    val selectedRoomId by viewModel.roomId.collectAsStateWithLifecycle()
    val selectedContainerId by viewModel.containerId.collectAsStateWithLifecycle()
    val selectedShelfId by viewModel.shelfId.collectAsStateWithLifecycle()
    val selectedDrawerId by viewModel.drawerId.collectAsStateWithLifecycle()

    val snackbars = remember { SnackbarHostState() }

    BoxWithConstraints(modifier = Modifier.fillMaxSize().padding(24.dp)) {
        val wide = maxWidth >= 900.dp
        if (wide) {
            Row(horizontalArrangement = Arrangement.spacedBy(24.dp), modifier = Modifier.fillMaxSize()) {
                LocationCreatePane(
                    viewModel = viewModel,
                    selectedCampusId = selectedCampusId,
                    selectedBuildingId = selectedBuildingId,
                    selectedRoomId = selectedRoomId,
                    selectedContainerId = selectedContainerId,
                    selectedShelfId = selectedShelfId,
                    selectedDrawerId = selectedDrawerId,
                    snackbars = snackbars,
                    modifier = Modifier.weight(1f).fillMaxHeight()
                )
                LocationHierarchyPane(
                    campuses = campuses,
                    buildings = buildings,
                    rooms = rooms,
                    containers = containers,
                    shelves = shelves,
                    drawers = drawers,
                    slots = slots,
                    selectedCampusId = selectedCampusId,
                    selectedBuildingId = selectedBuildingId,
                    selectedRoomId = selectedRoomId,
                    selectedContainerId = selectedContainerId,
                    selectedShelfId = selectedShelfId,
                    selectedDrawerId = selectedDrawerId,
                    modifier = Modifier.weight(1.2f).fillMaxHeight(),
                    viewModel = viewModel
                )
            }
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(20.dp), modifier = Modifier.fillMaxSize()) {
                LocationCreatePane(
                    viewModel = viewModel,
                    selectedCampusId = selectedCampusId,
                    selectedBuildingId = selectedBuildingId,
                    selectedRoomId = selectedRoomId,
                    selectedContainerId = selectedContainerId,
                    selectedShelfId = selectedShelfId,
                    selectedDrawerId = selectedDrawerId,
                    snackbars = snackbars,
                    modifier = Modifier.weight(1f).fillMaxWidth()
                )
                LocationHierarchyPane(
                    campuses = campuses,
                    buildings = buildings,
                    rooms = rooms,
                    containers = containers,
                    shelves = shelves,
                    drawers = drawers,
                    slots = slots,
                    selectedCampusId = selectedCampusId,
                    selectedBuildingId = selectedBuildingId,
                    selectedRoomId = selectedRoomId,
                    selectedContainerId = selectedContainerId,
                    selectedShelfId = selectedShelfId,
                    selectedDrawerId = selectedDrawerId,
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    viewModel = viewModel
                )
            }
        }
    }
    SnackbarHost(hostState = snackbars)
}

@Composable
private fun LocationCreatePane(
    viewModel: LocationsViewModel,
    selectedCampusId: Long?,
    selectedBuildingId: Long?,
    selectedRoomId: Long?,
    selectedContainerId: Long?,
    selectedShelfId: Long?,
    selectedDrawerId: Long?,
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
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            Column {
                Text("Inventory Hierarchy", style = MaterialTheme.typography.headlineSmall)
                Text("Define your site structure", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }

            // Campus Section
            CreateSection(
                title = "Add Campus",
                value = campusName,
                onValueChange = { campusName = it },
                label = "Campus name (e.g. North Plant)",
                onAdd = {
                    viewModel.addCampus(campusName) { result ->
                        scope.launch { snackbars.showSnackbar(result.fold({ "Campus added." }, { it.message ?: "Error adding campus." })) }
                        if (result.isSuccess) campusName = ""
                    }
                }
            )

            HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

            // Building Section
            CreateSection(
                title = "Add Building",
                value = buildingName,
                onValueChange = { buildingName = it },
                label = "Building name (e.g. Warehouse A)",
                enabled = selectedCampusId != null,
                onAdd = {
                    viewModel.addBuilding(buildingName) { result ->
                        scope.launch { snackbars.showSnackbar(result.fold({ "Building added." }, { it.message ?: "Error adding building." })) }
                        if (result.isSuccess) buildingName = ""
                    }
                }
            )

            HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

            // Room Section
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Add Room", style = MaterialTheme.typography.titleMedium, color = if (selectedBuildingId != null) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f))
                OutlinedTextField(roomTitle, { roomTitle = it }, label = { Text("Room title (e.g. Electrical Parts)") }, modifier = Modifier.fillMaxWidth(), enabled = selectedBuildingId != null)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(roomNumber, { roomNumber = it }, label = { Text("Room #") }, modifier = Modifier.weight(1f), enabled = selectedBuildingId != null)
                    OutlinedTextField(siteArea, { siteArea = it }, label = { Text("Area") }, modifier = Modifier.weight(1.5f), enabled = selectedBuildingId != null)
                }
                Button(
                    onClick = {
                        viewModel.addRoom(roomTitle, roomNumber, siteArea) { result ->
                            scope.launch { snackbars.showSnackbar(result.fold({ "Room added." }, { it.message ?: "Error adding room." })) }
                            if (result.isSuccess) { roomTitle = ""; roomNumber = ""; siteArea = "" }
                        }
                    },
                    enabled = selectedBuildingId != null && roomTitle.isNotBlank() && roomNumber.isNotBlank(),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Default.Add, null)
                    Spacer(Modifier.width(8.dp))
                    Text("Create Room")
                }
            }

            HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

            // Container Section
            CreateSection(
                title = "Add Container",
                value = containerName,
                onValueChange = { containerName = it },
                label = "Container name (e.g. Cabinet 01)",
                enabled = selectedRoomId != null,
                onAdd = {
                    viewModel.addContainer(containerName) { result ->
                        scope.launch { snackbars.showSnackbar(result.fold({ "Container added." }, { it.message ?: "Error adding container." })) }
                        if (result.isSuccess) containerName = ""
                    }
                }
            )

            HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

            // Shelf Section
            CreateSection(
                title = "Add Shelf",
                value = shelfName,
                onValueChange = { shelfName = it },
                label = "Shelf label (e.g. Shelf B)",
                enabled = selectedContainerId != null,
                onAdd = {
                    viewModel.addShelf(shelfName) { result ->
                        scope.launch { snackbars.showSnackbar(result.fold({ "Shelf added." }, { it.message ?: "Error adding shelf." })) }
                        if (result.isSuccess) shelfName = ""
                    }
                }
            )

            HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

            // Drawer Section
            CreateSection(
                title = "Add Drawer",
                value = drawerName,
                onValueChange = { drawerName = it },
                label = "Drawer name (e.g. Drawer 4)",
                enabled = selectedShelfId != null,
                onAdd = {
                    viewModel.addDrawer(drawerName) { result ->
                        scope.launch { snackbars.showSnackbar(result.fold({ "Drawer added." }, { it.message ?: "Error adding drawer." })) }
                        if (result.isSuccess) drawerName = ""
                    }
                }
            )

            HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

            // Slot Section
            CreateSection(
                title = "Add Slot",
                value = slotLabel,
                onValueChange = { slotLabel = it },
                label = "Slot/Bin label (e.g. Slot A-1)",
                enabled = selectedDrawerId != null,
                onAdd = {
                    viewModel.addSlot(slotLabel) { result ->
                        scope.launch { snackbars.showSnackbar(result.fold({ "Slot added." }, { it.message ?: "Error adding slot." })) }
                        if (result.isSuccess) slotLabel = ""
                    }
                }
            )
        }
    }
}

@Composable
private fun CreateSection(
    title: String,
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    enabled: Boolean = true,
    onAdd: () -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(title, style = MaterialTheme.typography.titleMedium, color = if (enabled) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f))
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            label = { Text(label) },
            modifier = Modifier.fillMaxWidth(),
            enabled = enabled
        )
        Button(
            onClick = onAdd,
            enabled = enabled && value.isNotBlank(),
            modifier = Modifier.fillMaxWidth()
        ) {
            Icon(Icons.Default.Add, null)
            Spacer(Modifier.width(8.dp))
            Text("Create ${title.removePrefix("Add ")}")
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
    selectedCampusId: Long?,
    selectedBuildingId: Long?,
    selectedRoomId: Long?,
    selectedContainerId: Long?,
    selectedShelfId: Long?,
    selectedDrawerId: Long?,
    modifier: Modifier,
    viewModel: LocationsViewModel
) {
    ElevatedCard(modifier = modifier) {
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            item {
                Column {
                    Text("Hierarchy Browser", style = MaterialTheme.typography.headlineSmall)
                    Text("Navigate and select locations", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            item { SelectChips("Campus", campuses, selectedCampusId, viewModel::selectCampus) }
            item { SelectChips("Building", buildings, selectedBuildingId, viewModel::selectBuilding) }
            item { SelectChips("Room", rooms, selectedRoomId, viewModel::selectRoom) }
            item { SelectChips("Container", containers, selectedContainerId, viewModel::selectContainer) }
            item { SelectChips("Shelf", shelves, selectedShelfId, viewModel::selectShelf) }
            item { SelectChips("Drawer", drawers, selectedDrawerId, viewModel::selectDrawer) }
            item { SectionList("Slots", slots) }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun SelectChips(
    title: String,
    items: List<LocationOption>,
    selectedId: Long?,
    onSelected: (Long?) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(title, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
        if (items.isEmpty()) {
            Text("No $title available", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                items.forEach { option ->
                    val selected = option.id == selectedId
                    FilterChip(
                        selected = selected,
                        onClick = { onSelected(if (selected) null else option.id) },
                        label = { Text(option.label) },
                        leadingIcon = if (selected) {
                            { Icon(Icons.Default.Check, null, modifier = Modifier.padding(end = 4.dp)) }
                        } else null
                    )
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
        Text(title, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
        if (items.isEmpty()) {
            Text("No $title available", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            items.forEach { option ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                ) {
                    Text(option.label, modifier = Modifier.padding(12.dp), style = MaterialTheme.typography.bodyLarge)
                }
            }
        }
    }
}
