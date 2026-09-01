#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="${STATE_FILE:-$PWD/.create-vm-state.env}"
INSTANCE_ID_ARG=""

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --instance-id)
      INSTANCE_ID_ARG="$2"
      shift 2
      ;;
    -h|--help)
      echo "Uso: REGION=us-chicago-1 ./destroy-vm.sh [--instance-id <OCID_DE_LA_VM>]"
      exit 0
      ;;
    *)
      echo "Opción no reconocida: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -n "$INSTANCE_ID_ARG" ]]; then
  [[ -n "${REGION:-}" ]] || {
    echo "Al usar --instance-id debe indicar REGION, por ejemplo REGION=us-chicago-1." >&2
    exit 1
  }

  OCI=(oci --region "$REGION")
  INSTANCE_ID="$INSTANCE_ID_ARG"
  COMPARTMENT_OCID="$("${OCI[@]}" compute instance get --instance-id "$INSTANCE_ID" --query 'data."compartment-id"' --raw-output)"
  VNIC_ID="$("${OCI[@]}" compute vnic-attachment list --compartment-id "$COMPARTMENT_OCID" --instance-id "$INSTANCE_ID" --query 'data[0]."vnic-id"' --raw-output)"
  SUBNET_ID="$("${OCI[@]}" network vnic get --vnic-id "$VNIC_ID" --query 'data."subnet-id"' --raw-output)"
  VCN_ID="$("${OCI[@]}" network subnet get --subnet-id "$SUBNET_ID" --query 'data."vcn-id"' --raw-output)"
  ROUTE_TABLE_ID="$("${OCI[@]}" network subnet get --subnet-id "$SUBNET_ID" --query 'data."route-table-id"' --raw-output)"
  SECURITY_LIST_ID="$("${OCI[@]}" network subnet get --subnet-id "$SUBNET_ID" --query 'data."security-list-ids"[0]' --raw-output)"
  IGW_ID="$("${OCI[@]}" network internet-gateway list --compartment-id "$COMPARTMENT_OCID" --vcn-id "$VCN_ID" --all --query 'data[0].id' --raw-output)"
else
  if [[ ! -r "$STATE_FILE" ]]; then
    echo "No se encontró $STATE_FILE. Use --instance-id para una VM creada antes de esta versión del script." >&2
    exit 1
  fi

  # El archivo lo genera create-vm.sh y solo contiene OCIDs de los recursos creados.
  source "$STATE_FILE"
  OCI=(oci --region "$REGION")
fi

echo "Se eliminarán exclusivamente estos recursos:"
echo "  VM:     $INSTANCE_ID"
echo "  Subnet: $SUBNET_ID"
echo "  VCN:    $VCN_ID"
read -r -p "Escriba DELETE para continuar: " confirmation
[[ "$confirmation" == "DELETE" ]] || {
  echo "Operación cancelada."
  exit 0
}

echo "Terminando VM y boot volume..."
"${OCI[@]}" compute instance terminate \
  --instance-id "$INSTANCE_ID" \
  --preserve-boot-volume false \
  --preserve-data-volumes-created-at-launch false \
  --force --wait-for-state SUCCEEDED --max-wait-seconds 1200 >/dev/null

echo "Eliminando subnet..."
"${OCI[@]}" network subnet delete \
  --subnet-id "$SUBNET_ID" \
  --force --wait-for-state TERMINATED --max-wait-seconds 1200 >/dev/null

echo "Eliminando security list, ruta e Internet Gateway..."
"${OCI[@]}" network security-list delete \
  --security-list-id "$SECURITY_LIST_ID" \
  --force --wait-for-state TERMINATED --max-wait-seconds 1200 >/dev/null
"${OCI[@]}" network route-table delete \
  --rt-id "$ROUTE_TABLE_ID" \
  --force --wait-for-state TERMINATED --max-wait-seconds 1200 >/dev/null
"${OCI[@]}" network internet-gateway delete \
  --ig-id "$IGW_ID" \
  --force --wait-for-state TERMINATED --max-wait-seconds 1200 >/dev/null

echo "Eliminando VCN..."
"${OCI[@]}" network vcn delete \
  --vcn-id "$VCN_ID" \
  --force --wait-for-state TERMINATED --max-wait-seconds 1200 >/dev/null

[[ -n "$INSTANCE_ID_ARG" ]] || rm -f "$STATE_FILE"
echo "Limpieza completada. Puede ejecutar ./create-vm.sh nuevamente."
