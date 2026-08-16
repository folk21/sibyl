package io.github.folk21.sibyl.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import io.github.folk21.sibyl.demo.DemoRetrievalService
import io.github.folk21.sibyl.domain.Answer
import io.github.folk21.sibyl.domain.PassageTextRole
import io.github.folk21.sibyl.retrieval.RetrievalService
import io.github.folk21.sibyl.selection.RandomSource
import io.github.folk21.sibyl.selection.SelectionEngine
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

/**
 * Runs the shared application UI with the clearly labelled synthetic demo retrieval service.
 *
 * This entry point is intentionally self-contained for previews/Android scaffolding that has not yet wired a real
 * corpus runtime. Synthetic fixture text remains visibly marked and must never be mistaken for a literary quotation.
 */
@Composable
fun SibylApp() {
    val retrieval = remember { DemoRetrievalService() }
    SibylApp(retrievalService = retrieval, isDemo = true)
}

/**
 * Runs the shared Compose UI against an injected retrieval implementation.
 *
 * Compose owns only interaction state and presentation. A question is delegated to [RetrievalService] for a candidate
 * pool, then [SelectionEngine] performs the controlled-random final choice. The UI renders the selected stored
 * `PassageVariant`, keeps temporary in-memory history/saved encounters, and never performs vector ranking or corpus
 * parsing itself.
 *
 * [isDemo] controls synthetic-fixture labelling only; it does not change retrieval or selection semantics.
 */
@Composable
fun SibylApp(
    retrievalService: RetrievalService,
    isDemo: Boolean,
    runtimeLabel: String? = null,
) {
    MaterialTheme {
        val retrieval = retrievalService
        val selector = remember { SelectionEngine(RandomSource { kotlin.random.Random.nextDouble() }) }
        val scope = rememberCoroutineScope()
        val history = remember { mutableStateListOf<Answer>() }
        val savedEncounters = remember { mutableStateListOf<Answer>() }
        var question by remember { mutableStateOf("") }
        var answer by remember { mutableStateOf<Answer?>(null) }
        var retrievalError by remember { mutableStateOf<String?>(null) }

        // Keep the asynchronous request boundary in UI state while retrieval and ranking remain outside Compose.
        fun requestAnswer() {
            scope.launch {
                retrievalError = null
                try {
                    val candidates = retrieval.candidates(question = question, limit = 50)
                    val selected = selector.select(question = question, candidates = candidates)
                    if (selected == null) {
                        retrievalError = "No sufficiently relevant passage was found."
                    } else {
                        answer = selected
                        history += selected
                    }
                } catch (error: CancellationException) {
                    throw error
                } catch (error: Exception) {
                    retrievalError = error.message ?: "Local retrieval failed."
                }
            }
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text("Sibyl", style = MaterialTheme.typography.headlineLarge)
            Text(
                if (isDemo) {
                    "Ask a question. This demo uses clearly labelled synthetic fixtures."
                } else {
                    "Ask a question. Answers are selected from the loaded local corpus."
                },
                style = MaterialTheme.typography.bodyMedium,
            )
            runtimeLabel?.let {
                Text(it, style = MaterialTheme.typography.labelMedium)
            }

            OutlinedTextField(
                value = question,
                onValueChange = { question = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Your question") },
                minLines = 3,
            )

            Button(
                onClick = ::requestAnswer,
                enabled = question.isNotBlank(),
            ) {
                Text("Ask the library")
            }

            retrievalError?.let { message ->
                Text(message, color = MaterialTheme.colorScheme.error)
            }

            answer?.let { current ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        val displayText = current.variant.preferredText("ru")
                        Text(displayText.text, style = MaterialTheme.typography.titleLarge)
                        Text(
                            "${current.passage.author} — ${current.passage.work}",
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        current.passage.location?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                        if (displayText.role == PassageTextRole.MACHINE_TRANSLATION) {
                            Text("Machine translation", style = MaterialTheme.typography.labelSmall)
                        }
                        if (isDemo) {
                            Text(
                                "DEMO: synthetic fixture, not a literary quotation",
                                style = MaterialTheme.typography.labelSmall,
                            )
                        }
                    }
                }

                val isSaved = savedEncounters.any {
                    it.question == current.question && it.passage.id == current.passage.id
                }
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    OutlinedButton(
                        onClick = {
                            if (!isSaved) {
                                savedEncounters += current
                            }
                        },
                    ) {
                        Text(if (isSaved) "Saved" else "Remember this")
                    }
                    OutlinedButton(onClick = ::requestAnswer) {
                        Text("Another answer")
                    }
                }
            }

            if (savedEncounters.isNotEmpty()) {
                Text("Saved encounters", style = MaterialTheme.typography.titleMedium)
                savedEncounters.asReversed().take(3).forEach { encounter ->
                    Text(
                        "${encounter.question} → ${encounter.variant.preferredText("ru").text}",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }

            if (history.isNotEmpty()) {
                Text("History", style = MaterialTheme.typography.titleMedium)
                history.asReversed().take(5).forEach { entry ->
                    Text(
                        "${entry.question} → ${entry.passage.work}",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }

            Spacer(Modifier.height(8.dp))
            Text(
                "History and saved encounters remain in memory only. " +
                    "User-state persistence is a later storage adapter milestone.",
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}
