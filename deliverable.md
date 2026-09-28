# Interview Deliverables

This document consolidates the final state of the Data Quality Assistant for quick review during the interview.

---

## 1. Implementation & Architecture
The project strictly adheres to the immutability and contract requirements defined in `AGENTS.md`.

**Core Architecture:**
*   **Data Models:** `ItemRecord` and `ReviewFinding` dataclasses.
*   **Rule Engine:** A fully decoupled `DataQualityEngine` that accepts records and applies rules without mutating source data.
*   **AI Protocol:** An abstract `AIProvider` Protocol that allows hot-swapping between a `MockAIProvider` (for testing) and a `LiteLLMAIProvider` (for real API integration using `litellm` and LM Studio).
*   **Active Rules:**
    1.  `MalformedRowRule` (Deterministic) - Checks for missing `item_id`.
    2.  `MissingPartNumberRule` (Deterministic) - Checks for missing MPN when manufacturer exists.
    3.  `DuplicateRecordRule` (Heuristic) - Flags identical IDs or duplicate MFR+MPN combos.
    4.  `CategoryMismatchAIRule` (AI-Assisted) - Uses LLM to check if the description fits the category.
    5.  `NormalizedDescriptionRule` (AI-Assisted) - Uses LLM to suggest cleaned text formatting.

---

## 2. How to Run & Test
The project uses `uv` for dependency and environment management.

**Run the CLI (Generates JSON Review Candidates):**
```bash
uv run python main.py sample_data/sample.json
```
*(This loads `.env` variables and automatically connects to the configured LLM, while printing detailed progress to `logs/assistant.log` and `stderr`.)*

**Run the Test Suite (Fast, Deterministic, Mocked):**
```bash
uv run python -m unittest tests.test_assistant -v
```

---

## 3. Sample Input & Output

**Input (`sample_data/sample.json` snippet):**
```json
{
  "item_id": "1001",
  "item_description": "bearing",
  "manufacturer": "SKF",
  "manufacturer_part_number": "   ",
  "category": "Mechanical"
}
```

**Output (Generated Review Finding):**
```json
[
  {
    "item_id": "1001",
    "issue_type": "missing_part_number",
    "severity": null,
    "confidence": null,
    "explanation": "Manufacturer is present but manufacturer part number is missing.",
    "suggested_action": "Request manufacturer part number from the source owner.",
    "source": "deterministic_rule"
  }
]
```

---

## 4. Tests Added & Run
A comprehensive suite of **40 unit tests** was added in `tests/test_assistant.py`.
*   **Immutability Tests:** Verifies the engine never modifies the `ItemRecord` object in memory.
*   **Contract Tests:** Verifies that every generated `ReviewFinding` strictly contains every required key (even if mapped to `null`).
*   **Boundary Testing:** Tests how rules handle empty strings, whitespace, `None`, and missing JSON keys.
*   **Mock Testing:** Tests the AI-assisted rules against the `MockAIProvider` to ensure the application logic behaves correctly when receiving mocked classification responses.

---

## 5. Assumptions & Tradeoffs
*   **Assumption:** Duplicate checking via exact string equivalence (lower-cased and whitespace-stripped) is sufficient for a minimum viable product.
*   **Assumption:** An empty JSON field or missing key should gracefully default to `None` and be handled by the rules, rather than crashing the parser.
*   **Tradeoff (Synchronous AI):** The rules are currently evaluated synchronously in a standard loop. For the time available, this was the safest pattern to guarantee correct execution. A tradeoff was made against raw speed (which would require asynchronous batching).
*   **Tradeoff (Null Severity):** Due to strict constraints on scope, `severity` and `confidence` logic was deemed out-of-scope for the MVP and hardcoded to `null` to respect the JSON schema without introducing flawed assumptions.

---

## 6. How AI Tools Were Used
*   **Code Generation:** AI was used heavily to scaffold repetitive Python boilerplate (Dataclasses, `argparse` setups, `logging` handlers) and to rapidly generate the 40 test cases covering boundary logic.
*   **Course Correction:** Initial AI-generated rules were overly subjective and broad. As the developer, I actively rejected/refactored the AI's output, stripping out unsupported rules (like `SuspiciousUOMRule`) and forcing strict adherence to the 3 deterministic rules + 2 AI rules requirement. 
*   **Architecture Strategy:** Used AI generation to swiftly implement the Protocol/Mock patterns so that the actual business logic could be written and tested rapidly without waiting on real API calls.

---

## 7. What I Would Improve Next
1.  **Asynchronous Batching:** Implement `asyncio.gather` within the `DataQualityEngine` and `LiteLLMAIProvider` to evaluate records concurrently. This is critical for scaling to 10k+ rows.
2.  **Advanced Heuristics:** Upgrade `DuplicateRecordRule` to strip punctuation and hyphens (so `ABC-123` matches `ABC123`) or introduce fuzzy matching (Levenshtein distance).
3.  **Strict JSON LLM Parsing:** Wrap the LiteLLM calls with `pydantic` or `instructor` to guarantee the LLM outputs strict JSON when suggesting categories, rather than relying on regex or raw string parsing.
4.  **Dynamic Scoring:** Introduce a scoring algorithm for `severity` and `confidence` based on LLM `logprobs` or deterministic risk weighting.
