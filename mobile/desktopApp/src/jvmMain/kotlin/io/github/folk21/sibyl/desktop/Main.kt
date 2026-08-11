package io.github.folk21.sibyl.desktop

import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import androidx.compose.ui.window.rememberWindowState
import io.github.folk21.sibyl.ui.SibylApp

fun main() = application {
    Window(
        onCloseRequest = ::exitApplication,
        state = rememberWindowState(width = 900.dp, height = 800.dp),
        title = "Sibyl Dev",
    ) {
        SibylApp()
    }
}
