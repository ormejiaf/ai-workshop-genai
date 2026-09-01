import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import KNOWLEDGE_DIR
from local_vector_store import index_files

files = sorted(KNOWLEDGE_DIR.glob("*.md"))
if not files:
    raise FileNotFoundError(f"No se encontraron políticas en {KNOWLEDGE_DIR}")

chunks = index_files(files)
print(f"Políticas indexadas: {len(files)} archivos, {chunks} fragmentos.")
