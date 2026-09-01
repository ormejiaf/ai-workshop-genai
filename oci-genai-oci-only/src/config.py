import json
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SUBMISSIONS_DIR = DATA_DIR / "submissions"
RESULTS_DIR = DATA_DIR / "results"
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

COUNTRIES_API_BASE_URL = os.getenv(
    "COUNTRIES_API_BASE_URL",
    "https://api.first.org/data/v1",
)


def resolve_model(model: str | None = None) -> str:
    logical = (model or DEFAULT_MODEL).strip()
    return MODEL_ALIASES.get(logical, logical)


def validate_model_alias(model: str | None = None) -> str:
    logical = (model or DEFAULT_MODEL).strip()
    if not logical:
        raise ValueError("Debe indicar un alias o identificador de modelo.")
    return logical


def submission_path(submission: str) -> Path:
    path = Path(submission)
    return path if path.is_absolute() else SUBMISSIONS_DIR / path


def result_path(submission: str, filename: str) -> Path:
    return RESULTS_DIR / Path(submission).name / filename
