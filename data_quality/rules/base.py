"""
Base interfaces for data quality rules.
"""
from typing import List
from data_quality.models import ItemRecord, ReviewFinding

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
