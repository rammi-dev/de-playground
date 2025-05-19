# filedr PostgreSQL Helm Chart

This chart deploys a PostgreSQL instance for the filedr service using the Bitnami PostgreSQL Helm chart as a dependency.

## Usage

```bash
helm dependency update
helm install postgres-standalone . --namespace postgres-standalone --create-namespace


helm upgrade --install postgres-standalone . -n postgres-standalone
```