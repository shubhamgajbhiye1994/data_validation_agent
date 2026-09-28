from dataclasses import dataclass
from typing import Optional

@dataclass
class ItemRecord:
    item_id: Optional[str] = None
    item_description: Optional[str] = None
    manufacturer: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    category: Optional[str] = None
    unit_of_measure: Optional[str] = None
    source_system: Optional[str] = None

@dataclass
class ReviewFinding:
    item_id: str
    issue_type: str
    severity: Optional[str]
    confidence: Optional[float]
    explanation: str
    suggested_action: str
    source: str
