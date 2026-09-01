import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import argparse

from client import client
from config import resolve_model, validate_model_alias

parser = argparse.ArgumentParser(description="Pregunta abierta a OCI Generative AI")
parser.add_argument("--model", default=None, help="Alias configurado, por ejemplo gemini")
args = parser.parse_args()
logical = validate_model_alias(args.model)
model = resolve_model(logical)

response = client.responses.create(
    model=model,
    input=(
        "En dos oraciones, explica cómo un modelo multimodal puede ayudar a una "
        "universidad a revisar los documentos para una reserva de matrícula."
    ),
)

print(f"MODEL: {logical}")
print(response.output_text)
