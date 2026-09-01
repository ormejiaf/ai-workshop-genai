import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import argparse

from client import client
from config import resolve_model, validate_model_alias

parser = argparse.ArgumentParser(description="Cambio de modelo por alias")
parser.add_argument("--model", default=None, help="gemini o grok, según .env")
args = parser.parse_args()
logical = validate_model_alias(args.model)
model = resolve_model(logical)

response = client.responses.create(
    model=model,
    input=(
        "En una oración, explica qué información puede verificarse en un "
        "certificado de notas para una reserva de matrícula."
    ),
)

print(f"MODEL: {logical}")
print(response.output_text)
