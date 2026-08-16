package io.github.folk21.sibyl

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import io.github.folk21.sibyl.ui.SibylApp

/** Hosts the shared Sibyl Compose UI inside the Android application. */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            SibylApp()
        }
    }
}
