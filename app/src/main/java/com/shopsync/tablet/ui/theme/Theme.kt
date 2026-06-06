package com.shopsync.tablet.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF0C6A61),
    onPrimary = Color(0xFFFFFFFF),
    primaryContainer = Color(0xFFB6EFE5),
    onPrimaryContainer = Color(0xFF042F2B),
    secondary = Color(0xFFE36A24),
    onSecondary = Color(0xFFFFFFFF),
    secondaryContainer = Color(0xFFFFD8C2),
    onSecondaryContainer = Color(0xFF4A1D00),
    tertiary = Color(0xFF274D8A),
    onTertiary = Color(0xFFFFFFFF),
    background = Color(0xFFF2EEE6),
    onBackground = Color(0xFF1A1F24),
    surface = Color(0xFFFFFCF6),
    onSurface = Color(0xFF172026),
    surfaceVariant = Color(0xFFE6DED1),
    onSurfaceVariant = Color(0xFF4F5B63),
    outline = Color(0xFF7A7C78),
    outlineVariant = Color(0xFFC9C1B7),
    error = Color(0xFFB42318)
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF6FD9CB),
    onPrimary = Color(0xFF003731),
    primaryContainer = Color(0xFF0A4C45),
    onPrimaryContainer = Color(0xFFB6EFE5),
    secondary = Color(0xFFFFA067),
    onSecondary = Color(0xFF542200),
    secondaryContainer = Color(0xFF733400),
    onSecondaryContainer = Color(0xFFFFD8C2),
    tertiary = Color(0xFF9CB9FF),
    onTertiary = Color(0xFF062B63),
    background = Color(0xFF11161A),
    onBackground = Color(0xFFE8EDF0),
    surface = Color(0xFF151D22),
    onSurface = Color(0xFFE7ECEF),
    surfaceVariant = Color(0xFF243038),
    onSurfaceVariant = Color(0xFFB6C2C8),
    outline = Color(0xFF88969D),
    outlineVariant = Color(0xFF334148),
    error = Color(0xFFFF6B6B)
)

@Composable
fun ShopSyncTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = Typography,
        content = content
    )
}
