"""
Data quality rules — deterministic, heuristic, and AI-assisted.

Architecture:
  - Deterministic rules: result from explicit business/data conditions; no LLM.
  - Heuristic rules: normalization, similarity, scoring; findings remain candidates.
  - AI-assisted rules: behind AIProvider interface; never mutate source records.
"""

from typing import List, Optional
from data_quality.models import ItemRecord, ReviewFinding
from data_quality.ai_provider import AIProvider


# ---------------------------------------------------------------------------
# Base interfaces
# ---------------------------------------------------------------------------

class Rule:
    """Single-record rule interface."""

    def evaluate(self, record: ItemRecord) -> List[ReviewFinding]:
        """Return zero or more findings for a single record."""
        raise NotImplementedError


class MultiRecordRule:
    """Multi-record rule interface (e.g. duplicate detection)."""

    def evaluate_all(self, records: List[ItemRecord]) -> List[ReviewFinding]:
        """Return zero or more findings across all records."""
        raise NotImplementedError


# ===========================================================================
# DETERMINISTIC RULES
# ===========================================================================

class MissingPartNumberRule(Rule):
    """Flag records where manufacturer is present but part number is missing."""

    def evaluate(self, record: ItemRecord) -> List[ReviewFinding]:
        item_id = record.item_id or "unknown"
        has_mfr = bool(record.manufacturer and str(record.manufacturer).strip())
        has_mpn = bool(
            record.manufacturer_part_number
            and str(record.manufacturer_part_number).strip()
        )

        if has_mfr and not has_mpn:
            return [ReviewFinding(
                item_id=item_id,
                issue_type="missing_part_number",
                severity=None,
                confidence=None,
                explanation="Manufacturer is present but manufacturer part number is missing.",
                suggested_action="Request manufacturer part number from the source owner.",
                source="deterministic_rule",
            )]
        return []


class MalformedRowRule(Rule):
    """Flag records that are missing a required item_id."""

    def evaluate(self, record: ItemRecord) -> List[ReviewFinding]:
        if not record.item_id or not str(record.item_id).strip():
            return [ReviewFinding(
                item_id="missing_id",
                issue_type="malformed_row",
                severity=None,
                confidence=None,
                explanation="Row is missing a required item_id.",
                suggested_action="Review record and request missing identifier before approval.",
                source="deterministic_rule",
            )]
        return []





# ===========================================================================
# HEURISTIC RULES
# ===========================================================================

class DuplicateRecordRule(MultiRecordRule):
    """Flag possible duplicate records by item_id or (manufacturer, part_number)."""

    def evaluate_all(self, records: List[ItemRecord]) -> List[ReviewFinding]:
        findings: List[ReviewFinding] = []

        # --- Check 1: Duplicate item_id ---
        id_seen: dict[str, int] = {}
        for idx, record in enumerate(records):
            rid = (record.item_id or "").strip()
            if not rid:
                continue
            if rid in id_seen:
                findings.append(ReviewFinding(
                    item_id=rid,
                    issue_type="possible_duplicate",
                    severity=None,
                    confidence=None,
                    explanation=f"Potential duplicate — item_id '{rid}' appears more than once.",
                    suggested_action="Review before approval — verify these are not duplicate records.",
                    source="heuristic_rule",
                ))
            id_seen[rid] = idx

        # --- Check 2: Duplicate (manufacturer, manufacturer_part_number) ---
        mpn_seen: dict[tuple[str, str], str] = {}
        for record in records:
            mfr = (record.manufacturer or "").strip().lower()
            mpn = (record.manufacturer_part_number or "").strip().lower()
            if not mfr or not mpn:
                continue
            key = (mfr, mpn)
            item_id = record.item_id or "unknown"
            if key in mpn_seen:
                original_id = mpn_seen[key]
                findings.append(ReviewFinding(
                    item_id=item_id,
                    issue_type="possible_duplicate",
                    severity=None,
                    confidence=None,
                    explanation=(
                        f"Potential duplicate — manufacturer '{record.manufacturer}' "
                        f"and part number '{record.manufacturer_part_number}' "
                        f"match an earlier record (item_id='{original_id}')."
                    ),
                    suggested_action="Review before approval — possible mismatch or duplicate entry.",
                    source="heuristic_rule",
                ))
            else:
                mpn_seen[key] = item_id

        return findings


# ===========================================================================
# AI-ASSISTED RULES
# ===========================================================================

class CategoryMismatchAIRule(Rule):
    """Use AI provider to detect category mismatch candidates."""

    def __init__(self, ai_provider: AIProvider):
        self.ai_provider = ai_provider

    def evaluate(self, record: ItemRecord) -> List[ReviewFinding]:
        item_id = record.item_id or "unknown"
        desc = record.item_description or ""
        cat = (record.category or "").strip()

        if not desc.strip() or not cat:
            return []

        suggested_category = self.ai_provider.classify_category(desc)

        if suggested_category.lower() != cat.lower():
            return [ReviewFinding(
                item_id=item_id,
                issue_type="category_mismatch_candidate",
                severity=None,
                confidence=None,
                explanation=(
                    f"Description suggests category '{suggested_category}', "
                    f"but record has category '{cat}'. Possible mismatch."
                ),
                suggested_action="Review category assignment before approval.",
                source="ai_assisted",
            )]
        return []


class NormalizedDescriptionRule(Rule):
    """Use AI provider to suggest a normalized version of the description."""

    def __init__(self, ai_provider: AIProvider):
        self.ai_provider = ai_provider

    def evaluate(self, record: ItemRecord) -> List[ReviewFinding]:
        item_id = record.item_id or "unknown"
        desc = record.item_description or ""

        if not desc.strip():
            return []

        normalized = self.ai_provider.normalize_description(desc)

        if normalized != desc:
            return [ReviewFinding(
                item_id=item_id,
                issue_type="normalized_description_suggestion",
                severity=None,
                confidence=None,
                explanation=(
                    f"Description may benefit from normalization. "
                    f"Current: '{desc}' → Suggested: '{normalized}'."
                ),
                suggested_action="Review suggested normalized description before approval.",
                source="ai_assisted",
            )]
        return []
