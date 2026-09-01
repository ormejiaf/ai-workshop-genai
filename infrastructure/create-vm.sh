#!/usr/bin/env bash
set -euo pipefail

# Ejecución:
#   REGION=us-chicago-1 ./create-vm.sh
# Opcionalmente, use otro compartment:
#   REGION=us-chicago-1 COMPARTMENT_OCID=ocid1.compartment.oc1..example ./create-vm.sh

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

CONFIG_REGION="$(oci_config_value region || true)"
CONFIG_TENANCY_OCID="$(oci_config_value tenancy || true)"

REGION="${REGION:-${OCI_REGION:-$CONFIG_REGION}}"
TENANCY_OCID="${TENANCY_OCID:-${OCI_TENANCY:-$CONFIG_TENANCY_OCID}}"
COMPARTMENT_OCID="${COMPARTMENT_OCID:-$TENANCY_OCID}"
NAME="${NAME:-genai-workshop}"
SHAPE="${SHAPE:-VM.Standard.E5.Flex}"
OCPUS="${OCPUS:-2}"
MEMORY_GBS="${MEMORY_GBS:-16}"
VCN_CIDR="${VCN_CIDR:-10.20.0.0/16}"
SUBNET_CIDR="${SUBNET_CIDR:-10.20.1.0/24}"
STATE_FILE="${STATE_FILE:-$PWD/.create-vm-state.env}"

if [[ -z "$REGION" || -z "$TENANCY_OCID" ]]; then
  echo "No se pudo obtener región o tenancy desde ~/.oci/config." >&2
  echo "Ejecute: REGION=us-chicago-1 TENANCY_OCID=ocid1.tenancy.oc1..example ./create-vm.sh" >&2
  exit 1
fi

for command in oci ssh-keygen; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Falta el comando: $command" >&2
    exit 1
  }
done

OCI=(oci --region "$REGION")

mkdir -p "$HOME/.ssh"
if [[ ! -f "$HOME/.ssh/workshop_oci" ]]; then
  ssh-keygen -t rsa -b 4096 -f "$HOME/.ssh/workshop_oci" -N "" -C "oci-genai-workshop"
fi

echo "Creando VCN..."
VCN_ID="$("${OCI[@]}" network vcn create \
  --compartment-id "$COMPARTMENT_OCID" \
  --cidr-block "$VCN_CIDR" \
  --display-name "${NAME}-vcn" \
  --query 'data.id' --raw-output)"

echo "Creando Internet Gateway..."
IGW_ID="$("${OCI[@]}" network internet-gateway create \
  --compartment-id "$COMPARTMENT_OCID" \
  --vcn-id "$VCN_ID" --is-enabled true \
  --display-name "${NAME}-igw" \
  --query 'data.id' --raw-output)"

echo "Creando ruta pública..."
ROUTE_TABLE_ID="$("${OCI[@]}" network route-table create \
  --compartment-id "$COMPARTMENT_OCID" --vcn-id "$VCN_ID" \
  --display-name "${NAME}-public-route" \
  --route-rules "[{\"cidrBlock\":\"0.0.0.0/0\",\"networkEntityId\":\"$IGW_ID\"}]" \
  --query 'data.id' --raw-output)"

echo "Creando regla SSH pública en el puerto 22..."
SECURITY_LIST_ID="$("${OCI[@]}" network security-list create \
  --compartment-id "$COMPARTMENT_OCID" --vcn-id "$VCN_ID" \
  --display-name "${NAME}-public-ssh" \
  --ingress-security-rules '[{"source":"0.0.0.0/0","protocol":"6","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":22,"max":22}}}]' \
  --egress-security-rules '[{"destination":"0.0.0.0/0","protocol":"all","isStateless":false}]' \
  --query 'data.id' --raw-output)"

echo "Creando subnet pública..."
SUBNET_ID="$("${OCI[@]}" network subnet create \
  --compartment-id "$COMPARTMENT_OCID" --vcn-id "$VCN_ID" \
  --cidr-block "$SUBNET_CIDR" --prohibit-public-ip-on-vnic false \
  --route-table-id "$ROUTE_TABLE_ID" \
  --security-list-ids "[\"$SECURITY_LIST_ID\"]" \
  --display-name "${NAME}-public-subnet" \
  --query 'data.id' --raw-output)"

AD="$("${OCI[@]}" iam availability-domain list \
  --compartment-id "$TENANCY_OCID" --query 'data[0].name' --raw-output)"

IMAGE_ID="$("${OCI[@]}" compute image list \
  --compartment-id "$COMPARTMENT_OCID" \
  --operating-system 'Oracle Linux' --operating-system-version '9' \
  --shape "$SHAPE" --sort-by TIMECREATED --sort-order DESC \
  --query 'data[0].id' --raw-output)"

echo "Creando VM..."
INSTANCE_ID="$("${OCI[@]}" compute instance launch \
  --compartment-id "$COMPARTMENT_OCID" --availability-domain "$AD" \
  --display-name "$NAME" --shape "$SHAPE" \
  --shape-config "{\"ocpus\":$OCPUS,\"memoryInGBs\":$MEMORY_GBS}" \
  --image-id "$IMAGE_ID" --subnet-id "$SUBNET_ID" --assign-public-ip true \
  --ssh-authorized-keys-file "$HOME/.ssh/workshop_oci.pub" \
  --wait-for-state RUNNING --max-wait-seconds 1200 \
  --query 'data.id' --raw-output)"

VNIC_ID="$("${OCI[@]}" compute vnic-attachment list \
  --compartment-id "$COMPARTMENT_OCID" --instance-id "$INSTANCE_ID" \
  --query 'data[0]."vnic-id"' --raw-output)"
PUBLIC_IP="$("${OCI[@]}" network vnic get --vnic-id "$VNIC_ID" --query 'data."public-ip"' --raw-output)"

printf '\nVM creada correctamente.\n'
printf 'IP pública: %s\n' "$PUBLIC_IP"
printf 'SSH: ssh -i ~/.ssh/workshop_oci opc@%s\n' "$PUBLIC_IP"
printf 'Instance OCID: %s\n' "$INSTANCE_ID"

umask 077
{
  printf 'REGION=%q\n' "$REGION"
  printf 'COMPARTMENT_OCID=%q\n' "$COMPARTMENT_OCID"
  printf 'VCN_ID=%q\n' "$VCN_ID"
  printf 'IGW_ID=%q\n' "$IGW_ID"
  printf 'ROUTE_TABLE_ID=%q\n' "$ROUTE_TABLE_ID"
  printf 'SECURITY_LIST_ID=%q\n' "$SECURITY_LIST_ID"
  printf 'SUBNET_ID=%q\n' "$SUBNET_ID"
  printf 'INSTANCE_ID=%q\n' "$INSTANCE_ID"
} > "$STATE_FILE"

printf 'Estado de recursos guardado en: %s\n' "$STATE_FILE"
