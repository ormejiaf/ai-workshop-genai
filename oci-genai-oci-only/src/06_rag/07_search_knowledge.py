import argparse
import json
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from local_vector_store import search

parser = argparse.ArgumentParser()
parser.add_argument("question", help="Pregunta que se responderá con las políticas")
args = parser.parse_args()

print(json.dumps(search(args.question), indent=2, ensure_ascii=False))
