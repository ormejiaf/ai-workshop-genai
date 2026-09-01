import argparse
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from client import client
from config import resolve_model, submission_path, validate_model_alias
from document_utils import document_content


PROMPT = """
Analiza los documentos de una solicitud de reserva de matrícula universitaria.

Para cada archivo, identifica el tipo de documento, resume la información legible
y explica cómo podría contribuir a la revisión de la solicitud. Indica con claridad
lo ilegible, ausente o que no puedas confirmar. No inventes datos, no valides la
identidad de la persona y no tomes todavía la decisión final.
"""

parser = argparse.ArgumentParser()
parser.add_argument("submission", help="Carpeta dentro de data/submissions")
parser.add_argument("--model", default=None)
args = parser.parse_args()

logical = validate_model_alias(args.model)
response = client.responses.create(
    model=resolve_model(logical),
    input=[{"role": "user", "content": [{"type": "input_text", "text": PROMPT}, *document_content(submission_path(args.submission))]}],
)

print(f"MODEL: {logical}")
print(response.output_text)
