"""
Comprehensive tests for the Data Quality Assistant.

Tests cover:
  - Every deterministic rule (positive and negative cases)
  - Every heuristic rule (duplicate detection)
  - Every AI-assisted rule (category mismatch, normalized description)
  - The AIProvider mock and LiteLLM provider factory
  - The DataQualityEngine with both single and multi-record rules
  - ReviewFinding contract compliance
  - Data immutability guarantee
  - Settings / configuration
"""

import unittest
import json
import sys
import os
import copy
import tempfile
from pathlib import Path
from dataclasses import asdict
from unittest.mock import patch

from data_quality.models import ItemRecord, ReviewFinding
from data_quality.ai_provider import MockAIProvider, LiteLLMAIProvider, create_ai_provider
from config.settings import AppSettings, LiteLLMSettings
from data_quality.rules import (
    MissingPartNumberRule,
    MalformedRowRule,
    CategoryMismatchAIRule,
    NormalizedDescriptionRule,
    DuplicateRecordRule,
)
from data_quality.engine import DataQualityEngine


# ===========================================================================
# Deterministic Rules
# ===========================================================================

class TestMissingPartNumberRule(unittest.TestCase):
    """Check 1: Missing manufacturer part number."""

    def setUp(self):
        self.rule = MissingPartNumberRule()

    def test_missing_mpn_triggers_finding(self):
        record = ItemRecord(item_id="1", manufacturer="SKF", manufacturer_part_number="")
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].issue_type, "missing_part_number")
        self.assertEqual(findings[0].source, "deterministic_rule")

    def test_none_mpn_triggers_finding(self):
        record = ItemRecord(item_id="1", manufacturer="SKF", manufacturer_part_number=None)
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 1)

    def test_whitespace_mpn_triggers_finding(self):
        record = ItemRecord(item_id="1", manufacturer="SKF", manufacturer_part_number="   ")
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 1)

    def test_valid_mpn_no_finding(self):
        record = ItemRecord(item_id="2", manufacturer="SKF", manufacturer_part_number="123")
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 0)

    def test_no_manufacturer_no_finding(self):
        record = ItemRecord(item_id="3", manufacturer="", manufacturer_part_number="")
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 0)

    def test_none_manufacturer_no_finding(self):
        record = ItemRecord(item_id="4", manufacturer=None)
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 0)


class TestMalformedRowRule(unittest.TestCase):
    """Check 7: Malformed or incomplete row."""

    def setUp(self):
        self.rule = MalformedRowRule()

    def test_empty_id_triggers_finding(self):
        record = ItemRecord(item_id="", manufacturer="SKF")
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].issue_type, "malformed_row")
        self.assertIsNone(findings[0].severity)

    def test_none_id_triggers_finding(self):
        record = ItemRecord(item_id=None)
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 1)

    def test_whitespace_id_triggers_finding(self):
        record = ItemRecord(item_id="   ")
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 1)

    def test_valid_id_no_finding(self):
        record = ItemRecord(item_id="1001")
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 0)

    def test_language_compliance(self):
        """suggested_action must not say 'Reject record'."""
        record = ItemRecord(item_id="")
        findings = self.rule.evaluate(record)
        self.assertNotIn("Reject record", findings[0].suggested_action)



# ===========================================================================
# Heuristic Rules
# ===========================================================================

class TestDuplicateRecordRule(unittest.TestCase):
    """Check 3: Possible duplicate record."""

    def setUp(self):
        self.rule = DuplicateRecordRule()

    def test_duplicate_item_id_triggers_finding(self):
        records = [
            ItemRecord(item_id="1001", item_description="Bearing A"),
            ItemRecord(item_id="1001", item_description="Bearing B"),
        ]
        findings = self.rule.evaluate_all(records)
        self.assertTrue(len(findings) >= 1)
        self.assertEqual(findings[0].issue_type, "possible_duplicate")
        self.assertEqual(findings[0].source, "heuristic_rule")

    def test_duplicate_mfr_mpn_triggers_finding(self):
        records = [
            ItemRecord(item_id="1", manufacturer="SKF", manufacturer_part_number="6205-ZZ"),
            ItemRecord(item_id="2", manufacturer="SKF", manufacturer_part_number="6205-ZZ"),
        ]
        findings = self.rule.evaluate_all(records)
        self.assertTrue(len(findings) >= 1)
        dup_findings = [f for f in findings if f.issue_type == "possible_duplicate"]
        self.assertTrue(len(dup_findings) >= 1)

    def test_unique_records_no_finding(self):
        records = [
            ItemRecord(item_id="1", manufacturer="SKF", manufacturer_part_number="A"),
            ItemRecord(item_id="2", manufacturer="Parker", manufacturer_part_number="B"),
        ]
        findings = self.rule.evaluate_all(records)
        self.assertEqual(len(findings), 0)

    def test_empty_records_no_crash(self):
        findings = self.rule.evaluate_all([])
        self.assertEqual(len(findings), 0)


# ===========================================================================
# AI-Assisted Rules
# ===========================================================================

class TestMockAIProvider(unittest.TestCase):
    """Test the MockAIProvider implementation."""

    def setUp(self):
        self.provider = MockAIProvider()

    def test_classify_bearing(self):
        self.assertEqual(self.provider.classify_category("SKF Bearing 6205"), "Mechanical")

    def test_classify_cable(self):
        self.assertEqual(self.provider.classify_category("High voltage cable"), "Electrical")

    def test_classify_unknown(self):
        self.assertEqual(self.provider.classify_category("Something random"), "General")

    def test_normalize_whitespace(self):
        result = self.provider.normalize_description("  high voltage   cable  ")
        self.assertEqual(result, "High Voltage Cable")

    def test_normalize_already_clean(self):
        result = self.provider.normalize_description("High Voltage Cable")
        self.assertEqual(result, "High Voltage Cable")

    def test_normalize_empty(self):
        result = self.provider.normalize_description("")
        self.assertEqual(result, "")


class TestCategoryMismatchAIRule(unittest.TestCase):
    """Check 4: Category mismatch candidate."""

    def setUp(self):
        self.ai = MockAIProvider()
        self.rule = CategoryMismatchAIRule(ai_provider=self.ai)

    def test_mismatch_triggers_finding(self):
        record = ItemRecord(item_id="1", item_description="bearing", category="Electrical")
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].issue_type, "category_mismatch_candidate")
        self.assertEqual(findings[0].source, "ai_assisted")

    def test_matching_category_no_finding(self):
        record = ItemRecord(item_id="2", item_description="bearing", category="Mechanical")
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 0)

    def test_empty_description_no_finding(self):
        record = ItemRecord(item_id="3", item_description="", category="Mechanical")
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 0)

    def test_empty_category_no_finding(self):
        record = ItemRecord(item_id="4", item_description="bearing", category="")
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 0)


class TestNormalizedDescriptionRule(unittest.TestCase):
    """Check 6: Normalized description suggestion."""

    def setUp(self):
        self.ai = MockAIProvider()
        self.rule = NormalizedDescriptionRule(ai_provider=self.ai)

    def test_unnormalized_triggers_finding(self):
        record = ItemRecord(item_id="1", item_description="  high voltage   cable  ")
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].issue_type, "normalized_description_suggestion")
        self.assertEqual(findings[0].source, "ai_assisted")

    def test_already_normalized_no_finding(self):
        record = ItemRecord(item_id="2", item_description="High Voltage Cable")
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 0)

    def test_blank_description_no_finding(self):
        record = ItemRecord(item_id="3", item_description="")
        findings = self.rule.evaluate(record)
        self.assertEqual(len(findings), 0)


# ===========================================================================
# Engine
# ===========================================================================

class TestDataQualityEngine(unittest.TestCase):
    """Test the orchestration engine."""

    def test_single_record_rules(self):
        rules = [MissingPartNumberRule(), MalformedRowRule()]
        engine = DataQualityEngine(rules=rules)
        records = [
            ItemRecord(item_id="", manufacturer="A"),
            ItemRecord(item_id="2", manufacturer="B", manufacturer_part_number=""),
        ]
        findings = engine.evaluate(records)
        issue_types = {f.issue_type for f in findings}
        self.assertIn("malformed_row", issue_types)
        self.assertIn("missing_part_number", issue_types)

    def test_multi_record_rules(self):
        engine = DataQualityEngine(multi_record_rules=[DuplicateRecordRule()])
        records = [
            ItemRecord(item_id="1001"),
            ItemRecord(item_id="1001"),
        ]
        findings = engine.evaluate(records)
        self.assertTrue(len(findings) >= 1)
        self.assertEqual(findings[0].issue_type, "possible_duplicate")

    def test_combined_rules(self):
        ai = MockAIProvider()
        engine = DataQualityEngine(
            rules=[MalformedRowRule(), CategoryMismatchAIRule(ai)],
            multi_record_rules=[DuplicateRecordRule()],
        )
        records = [
            ItemRecord(item_id="1", item_description="part", category="Mechanical"),
            ItemRecord(item_id="1", item_description="bearing", category="Electrical"),
        ]
        findings = engine.evaluate(records)
        issue_types = {f.issue_type for f in findings}

        self.assertIn("category_mismatch_candidate", issue_types)
        self.assertIn("possible_duplicate", issue_types)

    def test_empty_records_no_crash(self):
        engine = DataQualityEngine(rules=[MalformedRowRule()])
        findings = engine.evaluate([])
        self.assertEqual(len(findings), 0)


# ===========================================================================
# ReviewFinding Contract & Data Immutability
# ===========================================================================

class TestReviewFindingContract(unittest.TestCase):
    """Every finding must contain the required fields."""

    REQUIRED_FIELDS = {
        "item_id", "issue_type", "severity", "confidence",
        "explanation", "suggested_action", "source"
    }

    def test_all_fields_present(self):
        finding = ReviewFinding(
            item_id="1",
            issue_type="test",
            severity="low",
            confidence=0.5,
            explanation="test explanation",
            suggested_action="test action",
            source="test_source",
        )
        finding_dict = asdict(finding)
        for field in self.REQUIRED_FIELDS:
            self.assertIn(field, finding_dict)

    def test_all_rules_produce_valid_findings(self):
        """Run all rules and verify every finding has all required fields."""
        ai = MockAIProvider()
        rules = [
            MalformedRowRule(),
            MissingPartNumberRule(),
            CategoryMismatchAIRule(ai),
            NormalizedDescriptionRule(ai),
        ]
        multi_rules = [DuplicateRecordRule()]

        records = [
            ItemRecord(item_id="", manufacturer="A"),
            ItemRecord(item_id="1", manufacturer="B", manufacturer_part_number="",
                       item_description="part", unit_of_measure="XYZ",
                       category="Electrical"),
            ItemRecord(item_id="1", item_description="  bearing  ",
                       category="Electrical"),
        ]

        engine = DataQualityEngine(rules=rules, multi_record_rules=multi_rules)
        findings = engine.evaluate(records)

        self.assertTrue(len(findings) > 0, "Expected at least one finding")
        for finding in findings:
            finding_dict = asdict(finding)
            for field in self.REQUIRED_FIELDS:
                self.assertIn(field, finding_dict)
                if field not in {"severity", "confidence"}:
                    self.assertIsNotNone(finding_dict[field])


class TestDataImmutability(unittest.TestCase):
    """The original input record MUST NOT be mutated."""

    def test_records_not_mutated_by_engine(self):
        ai = MockAIProvider()
        original_record = ItemRecord(
            item_id="1",
            item_description="  bearing  ",
            manufacturer="SKF",
            manufacturer_part_number="",
            category="Electrical",
            unit_of_measure="XYZ",
            source_system="ERP-A",
        )
        record_copy = copy.deepcopy(original_record)

        engine = DataQualityEngine(
            rules=[
                MalformedRowRule(),
                MissingPartNumberRule(),
                CategoryMismatchAIRule(ai),
                NormalizedDescriptionRule(ai),
            ],
            multi_record_rules=[DuplicateRecordRule()],
        )
        engine.evaluate([original_record])

        # Verify original record was not modified
        self.assertEqual(original_record, record_copy)


# ===========================================================================
# Settings & AI Provider Factory
# ===========================================================================

class TestAppSettings(unittest.TestCase):
    """Test settings load from environment variables."""

    @patch.dict(os.environ, {
        "AI_PROVIDER": "litellm",
        "LITELLM_MODEL": "openai/test-model",
        "LITELLM_API_BASE": "http://localhost:9999/v1",
        "LITELLM_API_KEY": "test-key",
        "LITELLM_TEMPERATURE": "0.5",
        "LITELLM_MAX_TOKENS": "512",
    })
    def test_from_env_litellm(self):
        settings = AppSettings.from_env()
        self.assertEqual(settings.ai_provider, "litellm")
        self.assertEqual(settings.litellm.model, "openai/test-model")
        self.assertEqual(settings.litellm.api_base, "http://localhost:9999/v1")
        self.assertEqual(settings.litellm.api_key, "test-key")
        self.assertEqual(settings.litellm.temperature, 0.5)
        self.assertEqual(settings.litellm.max_tokens, 512)

    @patch("config.settings.load_dotenv")
    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_defaults(self, mock_dotenv):
        settings = AppSettings.from_env()
        self.assertEqual(settings.ai_provider, "mock")
        self.assertEqual(settings.litellm.model, "openai/google/gemma-4-26b-a4b-qat")
        self.assertEqual(settings.litellm.api_base, "http://192.168.0.101:1234/v1")


class TestCreateAIProvider(unittest.TestCase):
    """Test the AI provider factory function."""

    def test_mock_provider_by_default(self):
        settings = AppSettings(ai_provider="mock")
        provider = create_ai_provider(settings)
        self.assertIsInstance(provider, MockAIProvider)

    def test_litellm_provider_when_configured(self):
        settings = AppSettings(ai_provider="litellm")
        provider = create_ai_provider(settings)
        self.assertIsInstance(provider, LiteLLMAIProvider)

    @patch.dict(os.environ, {"AI_PROVIDER": "mock"})
    def test_factory_reads_env(self):
        provider = create_ai_provider()
        self.assertIsInstance(provider, MockAIProvider)


if __name__ == "__main__":
    unittest.main()
