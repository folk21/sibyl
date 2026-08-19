package io.github.folk21.sibyl.desktop

import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import androidx.compose.ui.window.rememberWindowState
import io.github.folk21.sibyl.desktop.runtime.DesktopRuntime
import io.github.folk21.sibyl.desktop.runtime.DesktopRuntimePaths
import io.github.folk21.sibyl.ui.SibylApp

/**
 * Starts the Desktop development host in demo mode or with a real local corpus runtime.
 *
 * Environment paths are resolved before Compose starts. When both corpus/model paths are present, the runtime is
 * created once and injected into the shared UI; otherwise the synthetic demo entry point is used. The `finally`
 * block owns shutdown so native ONNX/tokenizer resources and the read-only SQLite connection are closed even when
 * the Compose application exits through an exception.
 */
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
                        guidedRetrievalService = runtime.guidedRetrievalService,
                    )
                }
            }
        }
    } finally {
        runtime?.close()
    }
}
