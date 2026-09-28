"""
AI-assisted data quality rules.
"""
from typing import List
from data_quality.models import ItemRecord, ReviewFinding
from data_quality.rules.base import Rule
from data_quality.ai_provider import AIProvider

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
