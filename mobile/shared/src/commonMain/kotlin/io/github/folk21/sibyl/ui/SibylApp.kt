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
import io.github.folk21.sibyl.selection.RandomSource
import io.github.folk21.sibyl.selection.SelectionEngine
import kotlinx.coroutines.launch

@Composable
fun SibylApp() {
    MaterialTheme {
        val retrieval = remember { DemoRetrievalService() }
        val selector = remember { SelectionEngine(RandomSource { kotlin.random.Random.nextDouble() }) }
        val scope = rememberCoroutineScope()
        val history = remember { mutableStateListOf<Answer>() }
        val savedEncounters = remember { mutableStateListOf<Answer>() }
        var question by remember { mutableStateOf("") }
        var answer by remember { mutableStateOf<Answer?>(null) }

        fun requestAnswer() {
            scope.launch {
                val candidates = retrieval.candidates(question = question, limit = 50)
                selector.select(question = question, candidates = candidates)?.let { selected ->
                    answer = selected
                    history += selected
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
                "Ask a question. The production version will answer only with stored literary text. " +
                    "This first build uses clearly labelled synthetic fixtures.",
                style = MaterialTheme.typography.bodyMedium,
            )

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
                        Text(
                            "DEMO: synthetic fixture, not a literary quotation",
                            style = MaterialTheme.typography.labelSmall,
                        )
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
                "History and saved encounters are separate in the demo but remain in memory only. " +
                    "SQLite persistence is the next storage adapter milestone.",
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}
