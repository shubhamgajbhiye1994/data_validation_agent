"""
Data Quality Engine — orchestrates rules against item records.

Accepts a list of ItemRecords, applies configured single-record and
multi-record rules WITHOUT mutating the original records, and collects
ReviewFindings.
"""

from typing import List
from data_quality.models import ItemRecord, ReviewFinding
from data_quality.rules import Rule, MultiRecordRule
from config.logger import get_logger

logger = get_logger()


class DataQualityEngine:
    """Orchestrator that evaluates rules and collects review findings."""

    def __init__(
        self,
        rules: List[Rule] | None = None,
        multi_record_rules: List[MultiRecordRule] | None = None,
    ):
        self.rules: List[Rule] = rules or []
        self.multi_record_rules: List[MultiRecordRule] = multi_record_rules or []

    def evaluate(self, records: List[ItemRecord]) -> List[ReviewFinding]:
        """Run all rules and return aggregated findings."""
        findings: List[ReviewFinding] = []
        logger.info(f"Engine starting evaluation of {len(records)} records.")

        # Single-record rules
        if self.rules:
            logger.info(f"Applying {len(self.rules)} single-record rules...")
        for rule in self.rules:
            logger.info(f" -> Running {rule.__class__.__name__}")
            rule_findings = 0
            for record in records:
                results = rule.evaluate(record)
                findings.extend(results)
                rule_findings += len(results)
            if rule_findings > 0:
                logger.debug(f"    Found {rule_findings} candidate issues.")

        # Multi-record rules (e.g. duplicate detection)
        if self.multi_record_rules:
            logger.info(f"Applying {len(self.multi_record_rules)} multi-record rules...")
        for rule in self.multi_record_rules:
            logger.info(f" -> Running {rule.__class__.__name__}")
            results = rule.evaluate_all(records)
            findings.extend(results)
            if results:
                logger.debug(f"    Found {len(results)} candidate issues.")

        logger.info(f"Engine evaluation completed. Total findings: {len(findings)}")
        return findings
