#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}=== Airflow on k3s Deployment ===${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl not found${NC}"
    exit 1
fi

if ! command -v helm &> /dev/null; then
    echo -e "${RED}Error: helm not found${NC}"
    exit 1
fi

# Check kubectl connection
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to Kubernetes cluster${NC}"
    exit 1
fi

echo -e "${GREEN}Prerequisites OK${NC}"
echo ""

# Step 1: Create namespace
echo -e "${YELLOW}Step 1: Creating namespace...${NC}"
kubectl apply -f "$K8S_DIR/namespace.yaml"
echo ""

# Step 2: Check for secrets
echo -e "${YELLOW}Step 2: Checking secrets...${NC}"
if [ ! -f "$K8S_DIR/secrets.yaml" ]; then
    echo -e "${RED}Error: secrets.yaml not found!${NC}"
    echo "Please copy secrets.yaml.example to secrets.yaml and fill in your values:"
    echo "  cp $K8S_DIR/secrets.yaml.example $K8S_DIR/secrets.yaml"
    echo "  # Edit secrets.yaml with your actual values"
    exit 1
fi
kubectl apply -f "$K8S_DIR/secrets.yaml"
echo ""

# Step 3: Deploy MinIO
echo -e "${YELLOW}Step 3: Deploying MinIO...${NC}"
kubectl apply -f "$K8S_DIR/minio/"
echo ""

# Wait for MinIO to be ready
echo -e "${YELLOW}Waiting for MinIO to be ready...${NC}"
kubectl wait --for=condition=available --timeout=120s deployment/minio -n airflow || {
    echo -e "${RED}MinIO deployment timed out. Check logs with: kubectl logs -n airflow -l app=minio${NC}"
    exit 1
}
echo -e "${GREEN}MinIO is ready${NC}"
echo ""

# Step 4: Add Helm repo
echo -e "${YELLOW}Step 4: Adding Airflow Helm repository...${NC}"
helm repo add airflow-stable https://airflow-helm.github.io/charts
helm repo update
echo ""

# Step 5: Deploy Airflow
echo -e "${YELLOW}Step 5: Deploying Airflow...${NC}"
helm upgrade --install airflow airflow-stable/airflow \
    --namespace airflow \
    --values "$K8S_DIR/airflow-values.yaml" \
    --wait \
    --timeout 10m
echo ""

# Step 6: Wait for Airflow to be ready
echo -e "${YELLOW}Step 6: Waiting for Airflow to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/airflow-web -n airflow || {
    echo -e "${RED}Airflow webserver deployment timed out.${NC}"
    echo "Check status with: kubectl get pods -n airflow"
    exit 1
}
echo ""

# Print access information
echo -e "${GREEN}=== Deployment Complete! ===${NC}"
echo ""
echo "Access Airflow Web UI:"
echo "  URL: http://airflow.tron.home"
echo "  Default credentials: admin / admin"
echo ""
echo "Access MinIO Console:"
echo "  URL: http://minio.tron.home"
echo "  Credentials: minioadmin / <your-secret-key>"
echo ""
echo "Make sure to add DNS entries in your router:"
echo "  airflow.tron.home -> <k3s-node-ip>"
echo "  minio.tron.home   -> <k3s-node-ip>"
echo ""
echo "Useful commands:"
echo "  kubectl get pods -n airflow           # Check pod status"
echo "  kubectl logs -f deploy/airflow-scheduler -n airflow  # View scheduler logs"
echo "  kubectl logs -f deploy/airflow-web -n airflow        # View webserver logs"
