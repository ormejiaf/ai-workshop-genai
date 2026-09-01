#!/usr/bin/env bash
set -euo pipefail

# Elimina exclusivamente los recursos con los nombres usados por esta guía:
# - VM, VCN y red creadas por create-vm.sh
# - Proyecto de OCI Generative AI
# - Dynamic Group y política IAM de la VM

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="${STATE_FILE:-$SCRIPT_DIR/.create-vm-state.env}"
INSTANCE_ID_ARG=""
PROJECT_ID_ARG=""
SKIP_VM=false

PROJECT_NAME="${PROJECT_NAME:-genai-workshop-project}"
DYNAMIC_GROUP_NAME="${DYNAMIC_GROUP_NAME:-genai-workshop-vm}"
POLICY_NAME="${POLICY_NAME:-genai-workshop-vm-policy}"

usage() {
  cat <<'EOF'
Uso:
  REGION=us-chicago-1 ./destroy-workshop.sh
  REGION=us-chicago-1 ./destroy-workshop.sh --instance-id <OCID_DE_LA_VM>

Opciones:
  --project-id <OCID>  Elimina este proyecto de OCI Generative AI.
  --instance-id <OCID> Elimina una VM creada por el workshop si no existe el archivo de estado.
  --skip-vm            Conserva la VM y elimina solamente proyecto, Dynamic Group y política.
EOF
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --instance-id) INSTANCE_ID_ARG="$2"; shift 2 ;;
    --project-id) PROJECT_ID_ARG="$2"; shift 2 ;;
    --skip-vm) SKIP_VM=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opción no reconocida: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for command in oci; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Falta el comando: $command" >&2
    exit 1
  }
done

OCI_CONFIG_FILE="${OCI_CLI_CONFIG_FILE:-$HOME/.oci/config}"
OCI_PROFILE="${OCI_CLI_PROFILE:-DEFAULT}"

oci_config_value() {
  local key="$1"
  [[ -r "$OCI_CONFIG_FILE" ]] || return 0
  awk -v profile="[$OCI_PROFILE]" -v key="$key" '
    $0 == profile { in_profile = 1; next }
    /^\[/ { in_profile = 0 }
    in_profile && $0 ~ "^[[:space:]]*" key "[[:space:]]*=" {
      sub("^[[:space:]]*" key "[[:space:]]*=[[:space:]]*", "")
      print
      exit
    }
  ' "$OCI_CONFIG_FILE"
}

state_value() {
  local key="$1"
  [[ -r "$STATE_FILE" ]] || return 0
  awk -v key="$key" '
    $0 ~ "^" key "=" {
      sub("^" key "=", "")
      gsub(/^\047|\047$/, "")
      print
      exit
    }
  ' "$STATE_FILE"
}

CONFIG_REGION="$(oci_config_value region || true)"
CONFIG_TENANCY_OCID="$(oci_config_value tenancy || true)"
STATE_REGION="$(state_value REGION || true)"
STATE_TENANCY_OCID="$(state_value COMPARTMENT_OCID || true)"
REGION="${REGION:-${OCI_REGION:-${CONFIG_REGION:-$STATE_REGION}}}"
TENANCY_OCID="${TENANCY_OCID:-${OCI_TENANCY:-${CONFIG_TENANCY_OCID:-$STATE_TENANCY_OCID}}}"
COMPARTMENT_OCID="${COMPARTMENT_OCID:-$TENANCY_OCID}"

if [[ -z "$REGION" || -z "$TENANCY_OCID" ]]; then
  echo "No se pudo obtener región o tenancy desde ~/.oci/config." >&2
  echo "Ejecute: REGION=us-chicago-1 TENANCY_OCID=<OCID_DEL_TENANCY> ./destroy-workshop.sh" >&2
  exit 1
fi

OCI=(oci --region "$REGION")

empty_if_missing() {
  case "${1:-}" in
    ""|None|null) printf '' ;;
    *) printf '%s' "$1" ;;
  esac
}

lookup_resource() {
  local label="$1"
  shift
  local value
  if ! value="$("$@")"; then
    echo "No se pudo consultar $label. La limpieza se cancela sin eliminar recursos." >&2
    exit 1
  fi
  empty_if_missing "$value"
}

if [[ -n "$PROJECT_ID_ARG" ]]; then
  PROJECT_ID="$PROJECT_ID_ARG"
else
  PROJECT_ID="$(lookup_resource "el proyecto de OCI Generative AI" "${OCI[@]}" generative-ai generative-ai-project-collection list-generative-ai-projects \
    --compartment-id "$COMPARTMENT_OCID" --display-name "$PROJECT_NAME" --all \
    --query 'data[0].id' --raw-output)"
fi

DYNAMIC_GROUP_ID="$(lookup_resource "el Dynamic Group" "${OCI[@]}" iam dynamic-group list \
  --compartment-id "$TENANCY_OCID" --name "$DYNAMIC_GROUP_NAME" --all \
  --query 'data[0].id' --raw-output)"

POLICY_ID="$(lookup_resource "la política IAM" "${OCI[@]}" iam policy list \
  --compartment-id "$TENANCY_OCID" --name "$POLICY_NAME" --all \
  --query 'data[0].id' --raw-output)"

HAS_VM=false
if [[ "$SKIP_VM" == false ]] && { [[ -r "$STATE_FILE" ]] || [[ -n "$INSTANCE_ID_ARG" ]]; }; then
  HAS_VM=true
fi

if [[ "$HAS_VM" == false && -z "$PROJECT_ID" && -z "$DYNAMIC_GROUP_ID" && -z "$POLICY_ID" ]]; then
  echo "No se encontraron recursos del workshop para eliminar."
  exit 0
fi

echo "Se eliminarán exclusivamente los siguientes recursos del workshop:"
if [[ "$HAS_VM" == true ]]; then
  if [[ -r "$STATE_FILE" ]]; then
    echo "  VM y red: archivo de estado $STATE_FILE"
  else
    echo "  VM y red: instancia $INSTANCE_ID_ARG"
  fi
fi
[[ -n "$PROJECT_ID" ]] && echo "  Proyecto Generative AI: $PROJECT_ID"
[[ -n "$DYNAMIC_GROUP_ID" ]] && echo "  Dynamic Group: $DYNAMIC_GROUP_ID"
[[ -n "$POLICY_ID" ]] && echo "  Política IAM: $POLICY_ID"

read -r -p "Escriba DELETE_WORKSHOP para continuar: " confirmation
[[ "$confirmation" == "DELETE_WORKSHOP" ]] || {
  echo "Operación cancelada."
  exit 0
}

if [[ "$HAS_VM" == true ]]; then
  echo "Eliminando VM y red..."
  if [[ -r "$STATE_FILE" ]]; then
    STATE_FILE="$STATE_FILE" "$SCRIPT_DIR/destroy-vm.sh"
  else
    REGION="$REGION" "$SCRIPT_DIR/destroy-vm.sh" --instance-id "$INSTANCE_ID_ARG"
  fi
fi

if [[ -n "$POLICY_ID" ]]; then
  echo "Eliminando política IAM..."
  "${OCI[@]}" iam policy delete --policy-id "$POLICY_ID" --force >/dev/null
fi

if [[ -n "$DYNAMIC_GROUP_ID" ]]; then
  echo "Eliminando Dynamic Group..."
  "${OCI[@]}" iam dynamic-group delete --dynamic-group-id "$DYNAMIC_GROUP_ID" --force >/dev/null
fi

if [[ -n "$PROJECT_ID" ]]; then
  echo "Eliminando proyecto de OCI Generative AI..."
  "${OCI[@]}" generative-ai generative-ai-project delete \
    --generative-ai-project-id "$PROJECT_ID" --force \
    --wait-for-state SUCCEEDED --max-wait-seconds 1200 >/dev/null
fi

echo "Limpieza integral completada. El tenancy queda listo para repetir la guía."
