import argparse
import json
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from client import client
from config import resolve_model, result_path, validate_model_alias
from enrollment_decision_schema import ReservationDecision
from local_vector_store import search


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Falta el resultado requerido: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


parser = argparse.ArgumentParser()
parser.add_argument("submission", help="Carpeta dentro de data/submissions")
parser.add_argument("--model", default=None)
args = parser.parse_args()

review = load_json(result_path(args.submission, "document_review.json"))
external_validation = load_json(result_path(args.submission, "external_validation.json"))
policy_context = search(
    "¿Cuándo se aprueba, rechaza o envía a revisión humana una reserva de matrícula?"
)

prompt = f"""
Decide el estado de una reserva de matrícula usando exclusivamente estas fuentes:
1. La extracción estructurada de documentos.
2. La validación externa, que solo confirma la existencia de un país emisor.
3. Los fragmentos de políticas recuperados.

No inventes información. La consulta externa no autentica la identidad del alumno.
Si faltan documentos requeridos, rechaza. Si los documentos son ambiguos, solicita
revisión humana. Conserva los nombres de las políticas empleadas en policy_sources.

EXTRACCIÓN:
{json.dumps(review, indent=2, ensure_ascii=False)}

VALIDACIÓN EXTERNA:
{json.dumps(external_validation, indent=2, ensure_ascii=False)}

POLÍTICAS RECUPERADAS:
{json.dumps(policy_context, indent=2, ensure_ascii=False)}
"""

logical = validate_model_alias(args.model)
response = client.responses.parse(
    model=resolve_model(logical),
    input=prompt,
    text_format=ReservationDecision,
)

decision = response.output_parsed
output = result_path(args.submission, "reservation_decision.json")
output.write_text(decision.model_dump_json(indent=2), encoding="utf-8")
print(f"MODEL: {logical}")
print(f"Decisión guardada en: {output}")
print(decision.model_dump_json(indent=2))
