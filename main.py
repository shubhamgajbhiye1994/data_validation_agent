"""
CLI entrypoint for the Data Quality Assistant.

Accepts a JSON file containing a list of item-master records,
runs all configured data-quality rules, and outputs structured
review candidates in JSON format.

Only JSON files are supported; other formats are rejected.
"""

import json
import sys
import argparse
from pathlib import Path
from dataclasses import asdict

from data_quality.models import ItemRecord
from data_quality.ai_provider import create_ai_provider
from config.settings import AppSettings
from config.logger import setup_logger

logger = setup_logger()

from data_quality.rules.core import (
    MalformedRowRule,
    MissingPartNumberRule,
    DuplicateRecordRule,
)
from data_quality.rules.ai import (
    CategoryMismatchAIRule,
    NormalizedDescriptionRule,
)
from data_quality.engine import DataQualityEngine


def load_records(input_path: Path) -> list:
    """Load and validate a JSON file, returning a list of ItemRecords."""

    # Only JSON files are supported
    if input_path.suffix.lower() != ".json":
        logger.error("Only JSON files are supported.")
        sys.exit(1)

    # Check file exists
    if not input_path.exists():
        logger.error(f"File not found: {input_path}")
        sys.exit(1)

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format — {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        sys.exit(1)

    if not isinstance(data, list):
        logger.error("Input JSON must contain a list of records.")
        sys.exit(1)

    records = []
    valid_keys = set(ItemRecord.__dataclass_fields__.keys())
    for item in data:
        filtered_item = {k: v for k, v in item.items() if k in valid_keys}
        records.append(ItemRecord(**filtered_item))

    return records


def main():
    parser = argparse.ArgumentParser(
        description="Data Quality Assistant — Review-Candidate Generator"
    )
    parser.add_argument(
        "input_file", type=str, help="Path to the input JSON file."
    )
    args = parser.parse_args()

    logger.info("Starting Data Quality Assistant CLI.")
    input_path = Path(args.input_file)
    logger.info(f"Loading records from: {input_path}")
    records = load_records(input_path)
    logger.info(f"Successfully loaded {len(records)} records.")

    # Load settings from environment and create AI provider
    settings = AppSettings.from_env()
    ai_provider = create_ai_provider(settings)

    if settings.ai_provider == "litellm":
        logger.info(
            f"Using LiteLLM provider: model={settings.litellm.model}, "
            f"api_base={settings.litellm.api_base}"
        )
    else:
        logger.info("Using mock AI provider.")

    # Core deterministic rules
    core_rules = [
        MalformedRowRule(),
        MissingPartNumberRule(),
    ]

    # AI-assisted rules
    ai_rules = [
        CategoryMismatchAIRule(ai_provider=ai_provider),
        NormalizedDescriptionRule(ai_provider=ai_provider),
    ]

    # Multi-record heuristic rules
    multi_rules = [
        DuplicateRecordRule(),
    ]

    logger.info("Initializing Data Quality Engine with selected rules.")
    engine = DataQualityEngine(rules=core_rules + ai_rules, multi_record_rules=multi_rules)
    findings = engine.evaluate(records)

    logger.info(f"Formatting {len(findings)} review candidates to JSON output.")
    output = [asdict(f) for f in findings]
    print(json.dumps(output, indent=2))
    logger.info("Data Quality Assistant finished successfully.")


if __name__ == "__main__":
    main()
