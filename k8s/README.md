# Airflow on k3s Deployment

This directory contains Kubernetes manifests for deploying Apache Airflow on k3s.

## Architecture

- **Airflow**: Deployed via official community Helm chart with KubernetesExecutor
- **PostgreSQL**: Embedded in Helm chart (can be replaced with external DB)
- **MinIO**: Separate deployment for S3-compatible object storage
- **Git-sync**: Sidecar that syncs DAGs from this repository

## Prerequisites

1. k3s cluster running with kubectl configured
2. Helm 3.x installed
3. NFS storage class available (or local-path)
4. Git SSH key for accessing the DAGs repository

## Quick Start

```bash
# 1. Create namespace
kubectl create namespace airflow

# 2. Create secrets
./scripts/create-secrets.sh

# 3. Deploy MinIO
kubectl apply -f minio/

# 4. Add Airflow Helm repo
helm repo add airflow-stable https://airflow-helm.github.io/charts
helm repo update

# 5. Deploy Airflow
helm install airflow airflow-stable/airflow \
  --namespace airflow \
  --values airflow-values.yaml

# 6. Wait for pods to be ready
kubectl get pods -n airflow -w
```

## Accessing Services

### Airflow Web UI
```bash
# Via Ingress (if configured)
http://airflow.local

# Via port-forward
kubectl port-forward svc/airflow-web -n airflow 8080:8080
```

### MinIO Console
```bash
# Via port-forward
kubectl port-forward svc/minio-console -n airflow 9001:9001
```

## Configuration

### Environment Variables

Create a `.env.k8s` file (not committed) with:
```
OPENROUTER_API_KEY=your_key_here
GIT_SYNC_USERNAME=your_github_username
GIT_SYNC_PASSWORD=your_github_token
```

### Customization

Edit `airflow-values.yaml` to customize:
- Resource limits
- Replica counts
- Ingress settings
- Git repository URL

## Updating DAGs

DAGs are automatically synced from Git every 60 seconds. Simply push changes to the repository.

## Troubleshooting

```bash
# Check pod status
kubectl get pods -n airflow

# View logs
kubectl logs -f deployment/airflow-scheduler -n airflow

# Check git-sync logs
kubectl logs -f deployment/airflow-scheduler -n airflow -c git-sync

# Restart a deployment
kubectl rollout restart deployment/airflow-scheduler -n airflow
```
