package io.github.folk21.sibyl.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
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
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
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
import io.github.folk21.sibyl.domain.GuidedQuestion
import io.github.folk21.sibyl.domain.PassageTextRole
import io.github.folk21.sibyl.retrieval.GuidedRetrievalService
import io.github.folk21.sibyl.retrieval.RetrievalService
import io.github.folk21.sibyl.selection.RandomSource
import io.github.folk21.sibyl.selection.SelectionEngine
import io.github.folk21.sibyl.selection.SelectionPolicy
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

/** Selects whether the shared input delegates to stable guided IDs or free-form semantic retrieval. */
private enum class QuestionInputMode {
    GUIDED,
    FREE_FORM,
}

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
 * Runs the shared Compose UI against injected free-form and optional guided retrieval implementations.
 *
 * Compose owns only interaction state and presentation. Free-form text delegates to [RetrievalService]; guided
 * prompts delegate to [GuidedRetrievalService] by stable ID. Both modes then use the same [SelectionEngine] for the
 * controlled-random final choice, and the UI renders only stored `PassageVariant` text. Guided mode is shown only
 * when the installed corpus exposes at least one mapped question.
 *
 * [isDemo] controls synthetic-fixture labelling only; it does not change retrieval or selection semantics.
 */
@Composable
fun SibylApp(
    retrievalService: RetrievalService,
    isDemo: Boolean,
    runtimeLabel: String? = null,
    guidedRetrievalService: GuidedRetrievalService? = null,
) {
    MaterialTheme {
        val selector = remember { SelectionEngine(RandomSource { kotlin.random.Random.nextDouble() }) }
        val scope = rememberCoroutineScope()
        val history = remember { mutableStateListOf<Answer>() }
        val savedEncounters = remember { mutableStateListOf<Answer>() }
        var freeFormQuestion by remember { mutableStateOf("") }
        var inputMode by remember { mutableStateOf(QuestionInputMode.FREE_FORM) }
        var guidedQuestions by remember { mutableStateOf<List<GuidedQuestion>>(emptyList()) }
        var selectedGuidedQuestion by remember { mutableStateOf<GuidedQuestion?>(null) }
        var guidedMenuExpanded by remember { mutableStateOf(false) }
        var answer by remember { mutableStateOf<Answer?>(null) }
        var retrievalError by remember { mutableStateOf<String?>(null) }

        LaunchedEffect(guidedRetrievalService) {
            guidedQuestions = emptyList()
            selectedGuidedQuestion = null
            inputMode = QuestionInputMode.FREE_FORM
            val service = guidedRetrievalService ?: return@LaunchedEffect
            try {
                guidedQuestions = service.availableQuestions()
                selectedGuidedQuestion = guidedQuestions.firstOrNull()
                if (guidedQuestions.isNotEmpty()) {
                    inputMode = QuestionInputMode.GUIDED
                }
            } catch (error: CancellationException) {
                throw error
            } catch (_: Exception) {
                guidedQuestions = emptyList()
                selectedGuidedQuestion = null
            }
        }

        // Keep the asynchronous request boundary in UI state while retrieval and ranking remain outside Compose.
        fun requestAnswer() {
            scope.launch {
                retrievalError = null
                try {
                    val selected = when (inputMode) {
                        QuestionInputMode.FREE_FORM -> {
                            val question = freeFormQuestion
                            val candidates = retrievalService.candidates(question = question, limit = 50)
                            selector.select(question = question, candidates = candidates)
                        }
                        QuestionInputMode.GUIDED -> {
                            val guided = selectedGuidedQuestion
                            val service = guidedRetrievalService
                            if (guided == null || service == null) {
                                retrievalError = "No guided question is available in this corpus."
                                return@launch
                            }
                            val candidates = service.candidates(questionId = guided.id, limit = 50)
                            selector.select(
                                question = guided.text,
                                candidates = candidates,
                                policy = SelectionPolicy.guidedDefaults(),
                            )
                        }
                    }
                    if (selected == null) {
                        retrievalError = if (inputMode == QuestionInputMode.GUIDED) {
                            "No curated passage is available for this question."
                        } else {
                            "No sufficiently relevant passage was found."
                        }
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
                    "Choose a prepared question or ask your own. Answers come from the loaded local corpus."
                },
                style = MaterialTheme.typography.bodyMedium,
            )
            runtimeLabel?.let {
                Text(it, style = MaterialTheme.typography.labelMedium)
            }

            if (guidedQuestions.isNotEmpty()) {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    if (inputMode == QuestionInputMode.GUIDED) {
                        Button(onClick = {
                            inputMode = QuestionInputMode.GUIDED
                            answer = null
                            retrievalError = null
                        }) {
                            Text("Guided question")
                        }
                    } else {
                        OutlinedButton(onClick = {
                            inputMode = QuestionInputMode.GUIDED
                            answer = null
                            retrievalError = null
                        }) {
                            Text("Guided question")
                        }
                    }
                    if (inputMode == QuestionInputMode.FREE_FORM) {
                        Button(onClick = {
                            inputMode = QuestionInputMode.FREE_FORM
                            answer = null
                            retrievalError = null
                        }) {
                            Text("Own question")
                        }
                    } else {
                        OutlinedButton(onClick = {
                            inputMode = QuestionInputMode.FREE_FORM
                            answer = null
                            retrievalError = null
                        }) {
                            Text("Own question")
                        }
                    }
                }
            }

            if (inputMode == QuestionInputMode.GUIDED && guidedQuestions.isNotEmpty()) {
                Text("Standard question", style = MaterialTheme.typography.labelLarge)
                Box(modifier = Modifier.fillMaxWidth()) {
                    OutlinedButton(
                        onClick = { guidedMenuExpanded = true },
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Text(selectedGuidedQuestion?.text ?: "Choose a question")
                    }
                    DropdownMenu(
                        expanded = guidedMenuExpanded,
                        onDismissRequest = { guidedMenuExpanded = false },
                    ) {
                        guidedQuestions.forEach { guided ->
                            DropdownMenuItem(
                                text = { Text(guided.text) },
                                onClick = {
                                    selectedGuidedQuestion = guided
                                    guidedMenuExpanded = false
                                    answer = null
                                    retrievalError = null
                                },
                            )
                        }
                    }
                }
            } else {
                OutlinedTextField(
                    value = freeFormQuestion,
                    onValueChange = { freeFormQuestion = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Your question") },
                    minLines = 3,
                )
            }

            Button(
                onClick = ::requestAnswer,
                enabled = when (inputMode) {
                    QuestionInputMode.GUIDED -> selectedGuidedQuestion != null
                    QuestionInputMode.FREE_FORM -> freeFormQuestion.isNotBlank()
                },
            ) {
                Text("Find passage")
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
                        current.passage.location?.let {
                            Text(it, style = MaterialTheme.typography.bodySmall)
                        }
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
                        Text("Another passage")
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
