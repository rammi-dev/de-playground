# Iceberg Rest Catalog Helm Chart

This Helm chart deploys the Iceberg Rest Catalog along with its dependencies, such as PostgreSQL and Trino.

## Prerequisites
- [Helm](https://helm.sh/docs/intro/install/) installed on your system.
- A Kubernetes cluster configured and running.
- `kubectl` configured to interact with your cluster.

## Commands

### 1. Update Dependencies
Before installing or upgrading the chart, ensure all dependencies (e.g., PostgreSQL, Trino) are up to date:
```bash
helm dependency update
```

helm install iceberg . -f values.yaml -f postgresql-values.yaml --create-namespace --namespace=iceberg

helm upgrade iceberg . -f values.yaml -f postgresql-values.yaml --namespace=iceberg

helm uninstall iceberg --namespace=iceberg


helm repo add trino https://trinodb.github.io/charts

helm upgrade iceberg . -f values.yaml -f postgresql-values.yaml -f trino-values.yaml --namespace=iceberg




