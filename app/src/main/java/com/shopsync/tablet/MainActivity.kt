package com.shopsync.tablet

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.shopsync.tablet.ui.ShopSyncRoot
import com.shopsync.tablet.ui.theme.ShopSyncTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = (application as ShopSyncApplication).appContainer
        setContent {
            ShopSyncTheme {
                ShopSyncRoot(container = container)
            }
        }
    }
}
