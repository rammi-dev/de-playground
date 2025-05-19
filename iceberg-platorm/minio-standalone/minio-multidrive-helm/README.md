# MinIO Helm Chart

This repository contains a Helm chart for deploying MinIO, a high-performance, S3-compatible object storage service, using the Bitnami Helm repository. 

## Prerequisites

- [Docker](https://www.docker.com/get-started)
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
- [Helm](https://helm.sh/docs/intro/install/)
- [KinD](https://kind.sigs.k8s.io/docs/user/quick-start/)

## Setting Up a KinD Cluster

1. **Install KinD**: Follow the instructions on the [KinD installation page](https://kind.sigs.k8s.io/docs/user/quick-start/#installation) to install KinD.

2. **Create a KinD Cluster**:
   Run the following command to create a new KinD cluster named `data-cluster`:
   ```
   export KUBECONFIG=$(pwd)/custom-kubeconfig ; kind create cluster --name data-cluster
   ```

3. **Verify the Cluster**:
   Check that your cluster is running:
   ```
   kubectl cluster-info --context kind-data-cluster
   ```

4. **Set Up Helm**:
   Initialize Helm (if using Helm v2):
   ```
   helm init
   ```
   For Helm v3, you can skip this step as it does not require Tiller.

## Deploying MinIO

1. **Add the Bitnami Helm Repository**:
   ```
   helm repo add bitnami https://charts.bitnami.com/bitnami
   ```

2. **Install the MinIO Chart**:
   Navigate to the directory containing this chart and run:
   ```
   helm dependency build
   helm install minio . -f values.yaml --namespace minio-multi --create-namespace
   ```

3. **Accessing MinIO**:
   After installation, you can access MinIO using the service created by the Helm chart. Check the service details:

   You can port-forward to access the MinIO UI:
   ```
   k port-forward -n minio-multi svc/minio-minio-multidrive 9001:9001
   ```

   Open your browser and go to `http://localhost:9000` to access the MinIO web interface.

## Customizing the Deployment

You can customize the deployment by modifying the `values.yaml` file before installation. This file contains default configuration values that can be overridden.

## Uninstalling MinIO

To uninstall the MinIO release, run:
```
helm uninstall minio
```

## License

This project is licensed under the MIT License.