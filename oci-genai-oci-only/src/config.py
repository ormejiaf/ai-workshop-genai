import json
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RECIPES_DIR = DATA_DIR / "recipes"
EXTRACTED_DIR = RECIPES_DIR / "extracted"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"

load_dotenv(PROJECT_ROOT / ".env")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing environment variable: {name}\n"
            f"Check {PROJECT_ROOT / '.env'}"
        )
    return value


PROJECT_ID = require_env("OCI_GENAI_PROJECT_ID")
REGION = require_env("OCI_GENAI_REGION")
BASE_URL = require_env("OCI_GENAI_BASE_URL")
# La etapa RAG local no usa un OCI Vector Store. Se mantiene como variable
# opcional mientras se migra el material anterior del workshop.
VECTOR_STORE_ID = os.getenv("OCI_GENAI_VECTOR_STORE_ID")
DEFAULT_MODEL = require_env("OCI_GENAI_DEFAULT_MODEL")
AUTH_MODE = os.getenv("OCI_GENAI_AUTH_MODE", "instance_principal").strip().lower()
OCI_CONFIG_PROFILE = os.getenv("OCI_CONFIG_PROFILE", "DEFAULT")

if AUTH_MODE not in {"session", "instance_principal"}:
    raise RuntimeError(
        "OCI_GENAI_AUTH_MODE must be 'session' or 'instance_principal'"
    )

try:
    MODEL_ALIASES = json.loads(
        require_env("OCI_GENAI_MODELS_JSON")
    )
except json.JSONDecodeError as exc:
    raise RuntimeError(
        "OCI_GENAI_MODELS_JSON must be valid JSON, "
        'for example: {"gemini":"model-id","grok":"model-id"}'
    ) from exc

CIMA_BASE_URL = os.getenv(
    "CIMA_BASE_URL",
    "https://cima.aemps.es/cima/rest",
)
CIMA_MAX_RESULTS = int(os.getenv("CIMA_MAX_RESULTS", "2"))
CIMA_MAX_TO_EVALUATE = int(os.getenv("CIMA_MAX_TO_EVALUATE", "4"))


def resolve_model(model: str | None = None) -> str:
    logical = (model or DEFAULT_MODEL).strip()
    return MODEL_ALIASES.get(logical, logical)


def validate_model_alias(model: str | None = None) -> str:
    logical = (model or DEFAULT_MODEL).strip()
    if logical not in MODEL_ALIASES:
        allowed = ", ".join(MODEL_ALIASES.keys())
        raise ValueError(
            f"Unknown model alias '{logical}'. Allowed: {allowed}"
        )
    return logical


def recipe_image_path(recipe_name: str) -> Path:
    return RECIPES_DIR / Path(recipe_name).name


def extracted_path(image_path: Path) -> Path:
    return EXTRACTED_DIR / f"{image_path.stem}_extracted.json"


def external_validation_path(image_path: Path) -> Path:
    return EXTRACTED_DIR / f"{image_path.stem}_external_validation.json"
