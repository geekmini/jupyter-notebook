#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${YELLOW}=== Uninstalling Airflow from k3s ===${NC}"
echo ""

read -p "Are you sure you want to uninstall Airflow? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Uninstall Airflow Helm release
echo -e "${YELLOW}Uninstalling Airflow Helm release...${NC}"
helm uninstall airflow --namespace airflow || true
echo ""

# Delete MinIO
echo -e "${YELLOW}Deleting MinIO...${NC}"
kubectl delete -f "$K8S_DIR/minio/" --ignore-not-found
echo ""

# Delete secrets
echo -e "${YELLOW}Deleting secrets...${NC}"
kubectl delete -f "$K8S_DIR/secrets.yaml" --ignore-not-found || true
echo ""

# Ask about namespace deletion
read -p "Delete the airflow namespace (this will remove all data)? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deleting namespace...${NC}"
    kubectl delete namespace airflow || true
fi

echo ""
echo -e "${GREEN}Uninstall complete!${NC}"
