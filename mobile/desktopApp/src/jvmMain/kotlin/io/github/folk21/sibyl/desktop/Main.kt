package io.github.folk21.sibyl.desktop

import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import androidx.compose.ui.window.rememberWindowState
import io.github.folk21.sibyl.desktop.runtime.DesktopRuntime
import io.github.folk21.sibyl.desktop.runtime.DesktopRuntimePaths
import io.github.folk21.sibyl.ui.SibylApp

/** Starts Desktop in demo mode or wires a real local runtime from environment paths. */
fun main() {
    val paths = DesktopRuntimePaths.fromEnvironment()
    val runtime = paths?.let { DesktopRuntime.load(it.corpusDir, it.modelDir) }
    try {
        application {
            Window(
                onCloseRequest = ::exitApplication,
                state = rememberWindowState(width = 900.dp, height = 800.dp),
                title = "Sibyl Dev",
            ) {
                if (runtime == null) {
                    SibylApp()
                } else {
                    SibylApp(
                        retrievalService = runtime.retrievalService,
                        isDemo = false,
                        runtimeLabel = runtime.label,
                    )
                }
            }
        }
    } finally {
        runtime?.close()
    }
}
