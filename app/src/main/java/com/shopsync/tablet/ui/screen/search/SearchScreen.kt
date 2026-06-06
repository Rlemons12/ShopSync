package com.shopsync.tablet.ui.screen.search

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
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
import com.shopsync.tablet.data.repository.SearchRepository
import com.shopsync.tablet.domain.model.SearchCategory
import com.shopsync.tablet.domain.model.SearchResult
import com.shopsync.tablet.domain.model.UiState
import com.shopsync.tablet.ui.components.StatePane
import com.shopsync.tablet.ui.simpleViewModelFactory
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class SearchViewModel(
    private val repository: SearchRepository
) : ViewModel() {
    private val query = MutableStateFlow("")
    private val category = MutableStateFlow(SearchCategory.All)
    private val results = MutableStateFlow<UiState<List<SearchResult>>>(UiState.Empty("Start a search", "Search across parts and storage levels."))

    val state = results.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), UiState.Loading)
    val selectedCategory = category.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), SearchCategory.All)

    fun updateQuery(value: String) {
        query.value = value
    }

    fun updateCategory(value: SearchCategory) {
        category.value = value
    }

    fun search() {
        viewModelScope.launch {
            val currentQuery = query.value.trim()
            if (currentQuery.isBlank()) {
                results.value = UiState.Empty("Start a search", "Search across parts and storage levels.")
            } else {
                results.value = UiState.Loading
                results.value = runCatching { repository.search(currentQuery, category.value) }
                    .fold(
                        onSuccess = {
                            if (it.isEmpty()) UiState.Empty("No matches", "Try another identifier, room name, or manufacturer.")
                            else UiState.Success(it)
                        },
                        onFailure = {
                            UiState.Error("Search failed", it.message ?: "ShopSync could not complete the query.")
                        }
                    )
            }
        }
    }
}

@Composable
fun SearchRoute(repository: SearchRepository) {
    val viewModel: SearchViewModel = viewModel(factory = simpleViewModelFactory { SearchViewModel(repository) })
    SearchScreen(viewModel)
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun SearchScreen(viewModel: SearchViewModel) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val selectedCategory by viewModel.selectedCategory.collectAsStateWithLifecycle()
    var query by rememberSaveable { mutableStateOf("") }

    ElevatedCard(modifier = Modifier.fillMaxSize().padding(24.dp)) {
        Column(
            modifier = Modifier.fillMaxSize().padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("Search", style = MaterialTheme.typography.headlineSmall)
            OutlinedTextField(
                value = query,
                onValueChange = {
                    query = it
                    viewModel.updateQuery(it)
                },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Search ShopSync") },
                supportingText = { Text("Parts, rooms, containers, shelves, drawers, and slots") }
            )
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Filter", style = MaterialTheme.typography.labelLarge)
                androidx.compose.foundation.layout.FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    SearchCategory.entries.forEach { category ->
                        AssistChip(
                            onClick = {
                                viewModel.updateCategory(category)
                                viewModel.search()
                            },
                            label = { Text(category.name) },
                            leadingIcon = if (selectedCategory == category) ({ Text("•", color = MaterialTheme.colorScheme.primary) }) else null
                        )
                    }
                }
            }
            androidx.compose.material3.Button(onClick = { viewModel.search() }) { Text("Run search") }
            StatePane(state = state, modifier = Modifier.fillMaxSize()) { results ->
                LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    items(results) { result ->
                        Card {
                            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(result.title, style = MaterialTheme.typography.titleLarge)
                                Text(result.subtitle, color = MaterialTheme.colorScheme.primary)
                                Text(result.supportingText, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
            }
        }
    }
}
