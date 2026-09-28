"""
Deterministic and heuristic data quality rules.
"""
from typing import List
from data_quality.models import ItemRecord, ReviewFinding
from data_quality.rules.base import Rule, MultiRecordRule

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
