import json
from pathlib import Path

from review.schemas.models import ReviewFinding

SCHEMA_PATH = Path(__file__).parent / "finding.schema.json"


def export_finding_schema(output_path: Path | None = None) -> dict:
    schema = ReviewFinding.model_json_schema()
    target = output_path or SCHEMA_PATH
    target.write_text(json.dumps(schema, indent=2) + "\n")
    return schema
