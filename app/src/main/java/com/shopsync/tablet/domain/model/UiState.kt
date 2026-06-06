package com.shopsync.tablet.domain.model

sealed interface UiState<out T> {
    data object Loading : UiState<Nothing>
    data class Success<T>(val data: T) : UiState<T>
    data class Empty(val title: String, val message: String) : UiState<Nothing>
    data class Error(val title: String, val message: String) : UiState<Nothing>
}
