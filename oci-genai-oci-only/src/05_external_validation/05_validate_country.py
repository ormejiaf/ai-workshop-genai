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

    normalized_code = code.strip().upper()
    if len(normalized_code) != 3:
        return {
            "status": "NOT_CONFIRMED",
            "country_code": normalized_code,
            "reason": "Se espera un código ISO alpha-3 de tres letras.",
        }

    try:
        response = requests.get(
            f"{COUNTRIES_API_BASE_URL}/country/{normalized_code}",
            params={"format": "json"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        countries = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
        if not countries:
            return {
                "status": "NOT_CONFIRMED",
                "country_code": normalized_code,
                "reason": "El código no fue encontrado por la fuente externa.",
            }

        country = countries[0]
        return {
            "status": "CONFIRMED",
            "country_code": normalized_code,
            "country_name": country["name"],
            "region": country.get("region", {}).get("value"),
        }
    except (requests.RequestException, ValueError, AttributeError, KeyError) as exc:
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
