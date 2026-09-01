import argparse
import json
import sys
from pathlib import Path

import requests

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import COUNTRIES_API_BASE_URL, result_path


def validate_country(code: str | None) -> dict:
    if not code:
        return {"status": "NOT_AVAILABLE", "reason": "El documento no incluye un código de país."}
    try:
        response = requests.get(
            f"{COUNTRIES_API_BASE_URL}/alpha/{code}",
            params={"fields": "name,cca2,cca3,independent"},
            timeout=20,
        )
        response.raise_for_status()
        country = response.json()[0]
        return {
            "status": "CONFIRMED",
            "country_code": country["cca3"],
            "country_name": country["name"]["common"],
            "independent": country.get("independent"),
        }
    except requests.RequestException as exc:
        return {"status": "API_ERROR", "reason": str(exc)}


parser = argparse.ArgumentParser()
parser.add_argument("submission", help="Carpeta dentro de data/submissions")
args = parser.parse_args()

review_path = result_path(args.submission, "document_review.json")
review = json.loads(review_path.read_text(encoding="utf-8"))
documents = []
for document in review["documents"]:
    if document["document_type"] == "identity_document":
        documents.append({
            "filename": document["filename"],
            "issuing_country_validation": validate_country(document.get("issuing_country_code")),
        })

result = {
    "submission_id": review["submission_id"],
    "purpose": "Corroborar que el código de país emisor existe; no verifica identidad personal.",
    "documents": documents,
}
output = result_path(args.submission, "external_validation.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(result, indent=2, ensure_ascii=False))
