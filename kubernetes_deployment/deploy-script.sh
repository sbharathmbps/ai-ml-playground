cd /mnt/data/ml-platform/kubernetes_deployment

############################### Create Name Space ############################################################


kubectl create namespace argo
kubectl create namespace app

############################### Finish Name Space ############################################################


# ############################### Create Artifact Registery Secrets ############################################################
kubectl -n argo create secret generic argo-postgres-config \
  --from-literal=username=argo_user \
  --from-literal=password='argo_user'

# From v4.0, Argo’s full CRDs include complete validation and must be applied with server‑side apply to avoid size limits. Helm can’t do server‑side apply natively, so apply CRDs with kubectl, then install the chart with crds.install=false.
# Create namespace
# Apply full CRDs for the Argo version you’ll use (example ref v3.7.3—replace with your chosen version)
kubectl apply --server-side --force-conflicts -k \
  "https://github.com/argoproj/argo-workflows/manifests/base/crds/full?ref=v3.7.6"

helm repo add argo https://argoproj.github.io/argo-helm
helm repo update



helm install argo-workflows argo/argo-workflows \
  --namespace argo \
  --version 0.46.2 \
  -f /mnt/data/ml-platform/kubernetes_deployment/values.yaml \
  --set crds.install=false


kubectl apply -f yamls/
