## 1. Project Mission

Build a small enterprise data-quality assistant that analyzes item-master
records and produces structured review candidates for human data stewards.

The system MUST NOT automatically modify production data.

The system identifies potential issues and provides explainable suggestions
for human review.


# 2. Core Product Principle

The application is a REVIEW-CANDIDATE GENERATOR.

It is NOT:

- an automatic data correction system
- an automatic approval system
- an automatic rejection system
- a production data mutation system

Never use language such as:

- Fixed record
- Corrected record
- Auto-approved
- Automatically rejected

Prefer:

- Candidate issue detected
- Potential duplicate
- Needs review
- Suggested action
- Review before approval
- Possible mismatch

---

# 3. Source Requirements

The assignment requires identifying data-quality review candidates from
item-master records.

Typical input fields:

- item_id
- item_description
- manufacturer
- manufacturer_part_number
- category
- unit_of_measure
- source_system

Input may contain:

- missing values
- null values
- blank strings
- malformed values
- duplicates
- inconsistent representations


# 4. Required Checks

The implementation should support at least these checks:

1. Missing manufacturer part number when manufacturer is present
2. Possible duplicate record
3. Category mismatch candidate
4. Normalized description suggestion
5. Malformed or incomplete row
6. Explanation generation

Prioritize correctness and tests over breadth.


# 5. Architecture

Maintain clear separation between:

## Deterministic Rules

Rules whose result can be established from explicit business/data conditions.

Examples:

- missing manufacturer part number
- malformed record
- duplicate item_id

Deterministic rules MUST NOT depend on an LLM.


## Heuristic Rules

Rules based on deterministic normalization, similarity, or scoring.

Examples:

- possible duplicate
- description similarity
- category mismatch candidate

Heuristic findings must remain review candidates.


## AI-Assisted Layer

AI may be used for:

- classification
- candidate generation
- explanation
- normalization suggestions

AI MUST NOT:

- mutate source records
- directly approve records
- directly reject records
- write production data
- bypass deterministic validation

AI must be behind an interface/protocol so the implementation can later
replace a mock provider with a real model provider.



# 6. Data Immutability

The original input record MUST NOT be mutated during analysis.

Bad:

    record["category"] = "Mechanical"

Good:

    return ReviewFinding(...)

Any future correction workflow must be a separate explicitly approved
operation.

---

# 7. ReviewFinding Contract

Every finding should contain:

- item_id
- issue_type
- severity (currently null)
- confidence (currently null)
- explanation
- suggested_action
- source

Example:

```json
{
  "item_id": "1001",
  "issue_type": "missing_part_number",
  "severity": null,
  "confidence": null,
  "explanation": "Manufacturer is present but manufacturer part number is missing.",
  "suggested_action": "Request manufacturer part number from the source owner.",
  "source": "deterministic_rule"
}