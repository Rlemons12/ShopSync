package com.shopsync.tablet.ui.screen.inventory

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.shopsync.tablet.data.repository.InventoryRepository
import com.shopsync.tablet.data.repository.LocationRepository
import com.shopsync.tablet.domain.model.AddPartRequest
import com.shopsync.tablet.domain.model.HierarchySelection
import com.shopsync.tablet.domain.model.LocationOption
import com.shopsync.tablet.domain.model.PartDetail
import com.shopsync.tablet.domain.model.PartSummary
import com.shopsync.tablet.domain.model.UiState
import com.shopsync.tablet.ui.components.LabeledValue
import com.shopsync.tablet.ui.components.MessagePane
import com.shopsync.tablet.ui.components.SectionTitle
import com.shopsync.tablet.ui.components.StatePane
import com.shopsync.tablet.ui.components.formatTimestamp
import com.shopsync.tablet.ui.simpleViewModelFactory
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

@OptIn(ExperimentalCoroutinesApi::class)
class InventoryViewModel(
    private val inventoryRepository: InventoryRepository,
    private val locationRepository: LocationRepository
) : ViewModel() {
    private val query = MutableStateFlow("")
    private val selectedPartId = MutableStateFlow<Long?>(null)

    private val roomId = MutableStateFlow<Long?>(null)
    private val containerId = MutableStateFlow<Long?>(null)
    private val shelfId = MutableStateFlow<Long?>(null)
    private val drawerId = MutableStateFlow<Long?>(null)

    val parts = query.flatMapLatest { currentQuery ->
        inventoryRepository.observePartSummaries(currentQuery).map { list ->
            when {
                list.isEmpty() && currentQuery.isBlank() -> UiState.Empty("No parts yet", "Create a part or seed inventory to start tracking stock.")
                list.isEmpty() -> UiState.Empty("No matches", "Try another part number, manufacturer, or model.")
                else -> UiState.Success(list)
            }
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), UiState.Loading)

    val detail = selectedPartId.flatMapLatest { partId ->
        kotlinx.coroutines.flow.flow {
            if (partId == null) {
                emit(UiState.Empty("Select a part", "Choose a row to inspect metadata and stock locations."))
            } else {
                emit(UiState.Loading)
                val value = inventoryRepository.getPartDetail(partId)
                emit(
                    value?.let { UiState.Success(it) }
                        ?: UiState.Error("Part unavailable", "The selected part could not be loaded.")
                )
            }
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), UiState.Empty("Select a part", "Choose a row to inspect metadata and stock locations."))

    val rooms = locationRepository.observeRoomsByQuery("").stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val containers = roomId.flatMapLatest { locationRepository.observeContainers(it) }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val shelves = containerId.flatMapLatest { locationRepository.observeShelves(it) }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val drawers = shelfId.flatMapLatest { locationRepository.observeDrawers(it) }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val slots = drawerId.flatMapLatest { locationRepository.observeSlots(it) }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun setQuery(value: String) {
        query.value = value
    }

    fun selectPart(partId: Long) {
        selectedPartId.value = partId
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

    fun currentSelection(slotId: Long?) = HierarchySelection(
        roomId = roomId.value,
        containerId = containerId.value,
        shelfId = shelfId.value,
        drawerId = drawerId.value,
        slotId = slotId
    )

    fun addPart(request: AddPartRequest, onDone: (Result<Unit>) -> Unit) {
        viewModelScope.launch {
            runCatching { inventoryRepository.addPart(request) }
                .onSuccess { onDone(Result.success(Unit)) }
                .onFailure { onDone(Result.failure(it)) }
        }
    }

    fun addStock(partId: Long, quantity: Int, unit: String, slotId: Long?, onDone: (Result<Unit>) -> Unit) {
        viewModelScope.launch {
            runCatching { inventoryRepository.addStock(partId, quantity, unit, currentSelection(slotId)) }
                .onSuccess {
                    selectPart(partId)
                    onDone(Result.success(Unit))
                }
                .onFailure { onDone(Result.failure(it)) }
        }
    }
}

@Composable
fun InventoryRoute(
    inventoryRepository: InventoryRepository,
    locationRepository: LocationRepository
) {
    val viewModel: InventoryViewModel = viewModel(
        factory = simpleViewModelFactory { InventoryViewModel(inventoryRepository, locationRepository) }
    )
    InventoryScreen(viewModel)
}

@Composable
private fun InventoryScreen(viewModel: InventoryViewModel) {
    val parts by viewModel.parts.collectAsStateWithLifecycle()
    val detail by viewModel.detail.collectAsStateWithLifecycle()
    val rooms by viewModel.rooms.collectAsStateWithLifecycle()
    val containers by viewModel.containers.collectAsStateWithLifecycle()
    val shelves by viewModel.shelves.collectAsStateWithLifecycle()
    val drawers by viewModel.drawers.collectAsStateWithLifecycle()
    val slots by viewModel.slots.collectAsStateWithLifecycle()

    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    var showAddPart by rememberSaveable { mutableStateOf(false) }
    var showAddStock by rememberSaveable { mutableStateOf(false) }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        floatingActionButton = {
            FloatingActionButton(onClick = { showAddPart = true }) {
                Text("+")
            }
        }
    ) { padding ->
        BoxWithConstraints(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(24.dp)
        ) {
            val wide = maxWidth >= 900.dp
            if (wide) {
                Row(horizontalArrangement = Arrangement.spacedBy(20.dp), modifier = Modifier.fillMaxSize()) {
                    PartListPane(parts, Modifier.weight(0.95f).fillMaxHeight(), onSearch = viewModel::setQuery, onSelect = viewModel::selectPart)
                    PartDetailPane(
                        detailState = detail,
                        modifier = Modifier.weight(1.25f).fillMaxHeight(),
                        onAddStock = { showAddStock = true }
                    )
                }
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(20.dp), modifier = Modifier.fillMaxSize()) {
                    PartListPane(parts, Modifier.weight(1f).fillMaxWidth(), onSearch = viewModel::setQuery, onSelect = viewModel::selectPart)
                    PartDetailPane(detail, Modifier.weight(1f).fillMaxWidth(), onAddStock = { showAddStock = true })
                }
            }
        }
    }

    if (showAddPart) {
        AddPartDialog(
            rooms = rooms,
            containers = containers,
            shelves = shelves,
            drawers = drawers,
            slots = slots,
            onDismiss = { showAddPart = false },
            onRoomSelected = viewModel::selectRoom,
            onContainerSelected = viewModel::selectContainer,
            onShelfSelected = viewModel::selectShelf,
            onDrawerSelected = viewModel::selectDrawer,
            onSubmit = { request ->
                viewModel.addPart(request) { result ->
                    showAddPart = false
                    scope.launch {
                        snackbarHostState.showSnackbar(result.exceptionOrNull()?.message ?: "Part created.")
                    }
                }
            }
        )
    }

    val selectedPart = (detail as? UiState.Success<PartDetail>)?.data
    if (showAddStock && selectedPart != null) {
        AddStockDialog(
            part = selectedPart,
            rooms = rooms,
            containers = containers,
            shelves = shelves,
            drawers = drawers,
            slots = slots,
            onDismiss = { showAddStock = false },
            onRoomSelected = viewModel::selectRoom,
            onContainerSelected = viewModel::selectContainer,
            onShelfSelected = viewModel::selectShelf,
            onDrawerSelected = viewModel::selectDrawer,
            onSubmit = { quantity, unit, slotId ->
                viewModel.addStock(selectedPart.id, quantity, unit, slotId) { result ->
                    showAddStock = false
                    scope.launch {
                        snackbarHostState.showSnackbar(result.exceptionOrNull()?.message ?: "Stock updated.")
                    }
                }
            }
        )
    }
}

@Composable
private fun PartListPane(
    state: UiState<List<PartSummary>>,
    modifier: Modifier,
    onSearch: (String) -> Unit,
    onSelect: (Long) -> Unit
) {
    var query by rememberSaveable { mutableStateOf("") }
    ElevatedCard(modifier = modifier) {
        Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text("Inventory", style = MaterialTheme.typography.headlineSmall)
            OutlinedTextField(
                value = query,
                onValueChange = {
                    query = it
                    onSearch(it)
                },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Search parts") },
                supportingText = { Text("Part number, description, manufacturer, or model") }
            )
            StatePane(state = state, modifier = Modifier.fillMaxSize()) { parts ->
                LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    items(parts) { part ->
                        Card(modifier = Modifier.fillMaxWidth().clickable { onSelect(part.id) }) {
                            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Text("${part.partNumber} - ${part.name}", style = MaterialTheme.typography.titleLarge)
                                Text("${part.manufacturer} • ${part.model}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text("${part.totalQuantity} ${part.unit} across ${part.locationCount} locations")
                            }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun PartDetailPane(
    detailState: UiState<PartDetail>,
    modifier: Modifier,
    onAddStock: () -> Unit
) {
    ElevatedCard(modifier = modifier) {
        StatePane(state = detailState, modifier = Modifier.fillMaxSize()) { part ->
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                item {
                    Column(Modifier.fillMaxWidth().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Text(part.name, style = MaterialTheme.typography.headlineSmall)
                        Text(part.partNumber, color = MaterialTheme.colorScheme.primary)
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            AssistChip(onClick = {}, label = { Text(part.category.ifBlank { "Uncategorized" }) })
                            AssistChip(onClick = {}, label = { Text("${part.totalQuantity} ${part.unit.ifBlank { "ea" }} on hand") })
                            AssistChip(onClick = {}, label = { Text("${part.locations.size} active locations") })
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            OutlinedButton(onClick = onAddStock) { Text("Add stock") }
                        }
                        LabeledValue("Manufacturer", part.manufacturer)
                        LabeledValue("Model", part.model)
                        LabeledValue("Notes", part.notes)
                        LabeledValue("Documentation", part.documentation)
                    }
                }
                item { HorizontalDivider() }
                item { SectionTitle("Stock locations", Modifier.padding(horizontal = 20.dp)) }
                if (part.locations.isEmpty()) {
                    item { MessagePane("No stock placed", "This part exists in the catalog but is not assigned to any room or drawer.", Modifier.fillMaxWidth()) }
                } else {
                    items(part.locations) { location ->
                        Card(modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp)) {
                            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(location.breadcrumb, style = MaterialTheme.typography.titleLarge)
                                Text("${location.quantity} ${location.unit}", color = MaterialTheme.colorScheme.primary)
                                Text("Updated ${formatTimestamp(location.updatedAt)}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun AddPartDialog(
    rooms: List<LocationOption>,
    containers: List<LocationOption>,
    shelves: List<LocationOption>,
    drawers: List<LocationOption>,
    slots: List<LocationOption>,
    onDismiss: () -> Unit,
    onRoomSelected: (Long?) -> Unit,
    onContainerSelected: (Long?) -> Unit,
    onShelfSelected: (Long?) -> Unit,
    onDrawerSelected: (Long?) -> Unit,
    onSubmit: (AddPartRequest) -> Unit
) {
    var partNumber by rememberSaveable { mutableStateOf("") }
    var name by rememberSaveable { mutableStateOf("") }
    var manufacturer by rememberSaveable { mutableStateOf("") }
    var model by rememberSaveable { mutableStateOf("") }
    var category by rememberSaveable { mutableStateOf("") }
    var notes by rememberSaveable { mutableStateOf("") }
    var documentation by rememberSaveable { mutableStateOf("") }
    var quantity by rememberSaveable { mutableStateOf("0") }
    var unit by rememberSaveable { mutableStateOf("ea") }
    var selectedRoom by rememberSaveable { mutableStateOf<Long?>(null) }
    var selectedContainer by rememberSaveable { mutableStateOf<Long?>(null) }
    var selectedShelf by rememberSaveable { mutableStateOf<Long?>(null) }
    var selectedDrawer by rememberSaveable { mutableStateOf<Long?>(null) }
    var selectedSlot by rememberSaveable { mutableStateOf<Long?>(null) }

    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            Button(
                onClick = {
                    onSubmit(
                        AddPartRequest(
                            partNumber = partNumber,
                            name = name,
                            manufacturer = manufacturer,
                            model = model,
                            category = category,
                            notes = notes,
                            documentation = documentation,
                            quantity = quantity.toIntOrNull() ?: 0,
                            unit = unit,
                            selection = HierarchySelection(selectedRoom, selectedContainer, selectedShelf, selectedDrawer, selectedSlot)
                        )
                    )
                },
                enabled = partNumber.isNotBlank() && name.isNotBlank()
            ) { Text("Save part") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
        title = { Text("Add part") },
        text = {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                item { OutlinedTextField(partNumber, { partNumber = it }, label = { Text("Part number") }, modifier = Modifier.fillMaxWidth()) }
                item { OutlinedTextField(name, { name = it }, label = { Text("Part name") }, modifier = Modifier.fillMaxWidth()) }
                item { OutlinedTextField(manufacturer, { manufacturer = it }, label = { Text("Manufacturer") }, modifier = Modifier.fillMaxWidth()) }
                item { OutlinedTextField(model, { model = it }, label = { Text("Model") }, modifier = Modifier.fillMaxWidth()) }
                item { OutlinedTextField(category, { category = it }, label = { Text("Category") }, modifier = Modifier.fillMaxWidth()) }
                item { OutlinedTextField(quantity, { quantity = it }, label = { Text("Initial quantity") }, modifier = Modifier.fillMaxWidth()) }
                item { OutlinedTextField(unit, { unit = it }, label = { Text("Unit") }, modifier = Modifier.fillMaxWidth()) }
                item { OutlinedTextField(notes, { notes = it }, label = { Text("Notes") }, modifier = Modifier.fillMaxWidth()) }
                item { OutlinedTextField(documentation, { documentation = it }, label = { Text("Documentation") }, modifier = Modifier.fillMaxWidth()) }
                item {
                    LocationSelectors(
                        rooms = rooms,
                        containers = containers,
                        shelves = shelves,
                        drawers = drawers,
                        slots = slots,
                        selectedRoom = selectedRoom,
                        selectedContainer = selectedContainer,
                        selectedShelf = selectedShelf,
                        selectedDrawer = selectedDrawer,
                        selectedSlot = selectedSlot,
                        onRoomSelected = {
                            selectedRoom = it
                            selectedContainer = null
                            selectedShelf = null
                            selectedDrawer = null
                            selectedSlot = null
                            onRoomSelected(it)
                        },
                        onContainerSelected = {
                            selectedContainer = it
                            selectedShelf = null
                            selectedDrawer = null
                            selectedSlot = null
                            onContainerSelected(it)
                        },
                        onShelfSelected = {
                            selectedShelf = it
                            selectedDrawer = null
                            selectedSlot = null
                            onShelfSelected(it)
                        },
                        onDrawerSelected = {
                            selectedDrawer = it
                            selectedSlot = null
                            onDrawerSelected(it)
                        },
                        onSlotSelected = { selectedSlot = it }
                    )
                }
            }
        }
    )
}

@Composable
private fun AddStockDialog(
    part: PartDetail,
    rooms: List<LocationOption>,
    containers: List<LocationOption>,
    shelves: List<LocationOption>,
    drawers: List<LocationOption>,
    slots: List<LocationOption>,
    onDismiss: () -> Unit,
    onRoomSelected: (Long?) -> Unit,
    onContainerSelected: (Long?) -> Unit,
    onShelfSelected: (Long?) -> Unit,
    onDrawerSelected: (Long?) -> Unit,
    onSubmit: (Int, String, Long?) -> Unit
) {
    var quantity by rememberSaveable { mutableStateOf("0") }
    var unit by rememberSaveable { mutableStateOf(part.unit.ifBlank { "ea" }) }
    var selectedRoom by rememberSaveable { mutableStateOf<Long?>(null) }
    var selectedContainer by rememberSaveable { mutableStateOf<Long?>(null) }
    var selectedShelf by rememberSaveable { mutableStateOf<Long?>(null) }
    var selectedDrawer by rememberSaveable { mutableStateOf<Long?>(null) }
    var selectedSlot by rememberSaveable { mutableStateOf<Long?>(null) }

    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            Button(
                onClick = { onSubmit(quantity.toIntOrNull() ?: 0, unit, selectedSlot) },
                enabled = (quantity.toIntOrNull() ?: 0) > 0 && selectedContainer != null
            ) { Text("Add stock") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
        title = { Text("Add stock to ${part.partNumber}") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(quantity, { quantity = it }, label = { Text("Quantity") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(unit, { unit = it }, label = { Text("Unit") }, modifier = Modifier.fillMaxWidth())
                LocationSelectors(
                    rooms = rooms,
                    containers = containers,
                    shelves = shelves,
                    drawers = drawers,
                    slots = slots,
                    selectedRoom = selectedRoom,
                    selectedContainer = selectedContainer,
                    selectedShelf = selectedShelf,
                    selectedDrawer = selectedDrawer,
                    selectedSlot = selectedSlot,
                    onRoomSelected = {
                        selectedRoom = it
                        selectedContainer = null
                        selectedShelf = null
                        selectedDrawer = null
                        selectedSlot = null
                        onRoomSelected(it)
                    },
                    onContainerSelected = {
                        selectedContainer = it
                        selectedShelf = null
                        selectedDrawer = null
                        selectedSlot = null
                        onContainerSelected(it)
                    },
                    onShelfSelected = {
                        selectedShelf = it
                        selectedDrawer = null
                        selectedSlot = null
                        onShelfSelected(it)
                    },
                    onDrawerSelected = {
                        selectedDrawer = it
                        selectedSlot = null
                        onDrawerSelected(it)
                    },
                    onSlotSelected = { selectedSlot = it }
                )
            }
        }
    )
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun LocationSelectors(
    rooms: List<LocationOption>,
    containers: List<LocationOption>,
    shelves: List<LocationOption>,
    drawers: List<LocationOption>,
    slots: List<LocationOption>,
    selectedRoom: Long?,
    selectedContainer: Long?,
    selectedShelf: Long?,
    selectedDrawer: Long?,
    selectedSlot: Long?,
    onRoomSelected: (Long?) -> Unit,
    onContainerSelected: (Long?) -> Unit,
    onShelfSelected: (Long?) -> Unit,
    onDrawerSelected: (Long?) -> Unit,
    onSlotSelected: (Long?) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        PickerField("Room", rooms, selectedRoom, onRoomSelected)
        PickerField("Container", containers, selectedContainer, onContainerSelected)
        PickerField("Shelf", shelves, selectedShelf, onShelfSelected)
        PickerField("Drawer", drawers, selectedDrawer, onDrawerSelected)
        PickerField("Slot", slots, selectedSlot, onSlotSelected)
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun PickerField(
    label: String,
    options: List<LocationOption>,
    selectedId: Long?,
    onSelected: (Long?) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(label, style = MaterialTheme.typography.labelLarge)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            options.forEach { option ->
                AssistChip(
                    onClick = { onSelected(option.id) },
                    label = { Text(option.label) },
                    leadingIcon = if (selectedId == option.id) ({
                        Text("•", color = MaterialTheme.colorScheme.primary)
                    }) else null
                )
            }
        }
    }
}
