import argparse
import json
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from client import client
from config import resolve_model, result_path, submission_path, validate_model_alias
from document_utils import document_content
from student_application_schema import EnrollmentReservationReview


PROMPT = """
Revisa los documentos entregados para una reserva de matrícula universitaria.

Documentos obligatorios: documento de identidad, certificado de notas y boleta de
pago o abono. Un documento es valid cuando es legible, corresponde al tipo esperado
y presenta información coherente; si no puedes determinarlo, usa unreadable o
not_detected. No inventes datos ni verifiques la identidad frente a sistemas externos.

Aprueba solo si están los tres documentos obligatorios y no hay inconsistencias
relevantes. Si la evidencia es insuficiente o ambigua, usa HUMAN_REVIEW.
"""

parser = argparse.ArgumentParser()
parser.add_argument("submission", help="Carpeta dentro de data/submissions")
parser.add_argument("--model", default=None)
args = parser.parse_args()

logical = validate_model_alias(args.model)
response = client.responses.parse(
    model=resolve_model(logical),
    input=[{"role": "user", "content": [{"type": "input_text", "text": f"{PROMPT}\nsubmission_id debe ser: {Path(args.submission).name}"}, *document_content(submission_path(args.submission))]}],
    text_format=EnrollmentReservationReview,
)

review = response.output_parsed
output = result_path(args.submission, "document_review.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(review.model_dump_json(indent=2), encoding="utf-8")
print(f"MODEL: {logical}")
print(f"JSON guardado en: {output}")
print(json.dumps(review.model_dump(), indent=2, ensure_ascii=False))
