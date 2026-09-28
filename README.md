# Data Quality Assistant

An enterprise data-quality assistant that analyzes item-master records and produces structured review candidates for human data stewards.

## What is Implemented

The system is fully functional and adheres to the strict architecture defined in `AGENTS.md`.

*   **CLI Orchestrator:** A command-line interface (`main.py`) that reads `sample_data/sample.json`, runs the data quality engine, and outputs a clean JSON array of review findings to `stdout`.
*   **Logging Framework:** Comprehensive lifecycle logging to both `stderr` (console) and a rotating file at `logs/assistant.log` without interfering with the JSON output.
*   **Data Immutability:** Original input records are never mutated. The engine is entirely decoupled and purely generates `ReviewFinding` objects.
*   **AI Protocol Abstraction:** 
    *   `MockAIProvider`: Used for deterministic, fast unit testing without an internet connection.
    *   `LiteLLMAIProvider`: Real LLM integration using `litellm` (configured via `.env` to connect to local instances like LM Studio).
*   **Active Rules (Exactly 5):**
    1.  `MalformedRowRule` (Deterministic): Flags records missing an `item_id`.
    2.  `MissingPartNumberRule` (Deterministic): Flags records that have a manufacturer but are missing the manufacturer part number.
    3.  `DuplicateRecordRule` (Heuristic): Flags duplicate `item_id`s or identical manufacturer & part number combinations.
    4.  `CategoryMismatchAIRule` (AI-Assisted): Queries the LLM to verify if the description matches the assigned category.
    5.  `NormalizedDescriptionRule` (AI-Assisted): Queries the LLM to generate cleaned, standardized descriptions (fixing typos, capitalization, etc.).
*   **Comprehensive Test Suite:** 40 unit tests covering positive/negative cases, rule logic, contract compliance, and immutability. All tests execute and pass in milliseconds.

---

## What is Pending / Half-Cooked / Not Implemented

Based on recent simplifications and remaining edge cases, the following areas require future attention:

### 1. Severity and Confidence Scoring
*   **Status:** Hardcoded to `null`.
*   **Detail:** As explicitly requested for the current iteration, `severity` and `confidence` fields are present in the JSON schema but are explicitly assigned `null`. We need to implement a dynamic scoring algorithm or LLM-based certainty metric later.

### 2. Advanced Duplicate Detection (MPN Formatting)
*   **Status:** Basic casing handled; advanced normalizations missing.
*   **Detail:** `DuplicateRecordRule` uses `.strip().lower()` to find duplicates. It does *not* strip special characters or hyphens. Therefore, `ABC-123` and `ABC123` will currently bypass the duplicate check.

### 3. Cross-Source System Conflicts
*   **Status:** Not implemented.
*   **Detail:** The system doesn't analyze the `source_system` field for conflicts. If two identical items come from different source systems, they are flagged as generic duplicates, but no merging/trust-level logic is applied.

### 4. Removed Deterministic Rules
*   **Status:** Removed from codebase per user instruction.
*   **Detail:** 
    *   `SuspiciousUOMRule`: The system currently does **not** validate if `unit_of_measure` is standard (e.g., `EA`, `KG`).
    *   `WeakDescriptionRule`: Replaced largely by AI normalization. Purely useless descriptions (like "part") might simply be capitalized to "Part" by the AI rather than aggressively flagged as invalid data.

### 5. Performance / LLM Bottlenecks
*   **Status:** Synchronous processing.
*   **Detail:** The AI rules are currently evaluated sequentially (record-by-record) in a synchronous loop. For a massive enterprise dataset (e.g., 100k rows), the LLM calls will take a significantly long time. An asynchronous batching mechanism (like `asyncio.gather` for LiteLLM) should be introduced for scale.
