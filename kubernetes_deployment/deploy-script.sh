cd /mnt/data/ml-platform/kubernetes_deployment

############################### Create Name Space ############################################################


kubectl create namespace argo
kubectl create namespace app

############################### Finish Name Space ############################################################


# ############################### Create Artifact Registery Secrets ############################################################
# # kubectl create secret docker-registry artifact-registery-secret \
# #   --docker-server=https://us-central1-docker.pkg.dev/ \
# #   --docker-email=946201596129-compute@developer.gserviceaccount.com \
# #   --docker-username=_json_key \
# #   --docker-password="$(cat 946201596129-compute-developer-svc-ac-key.json)" \
# #   --namespace=default

# kubectl create secret docker-registry artifact-registery-secret \
#   --docker-server=https://us-central1-docker.pkg.dev/ \
#   --docker-email=946201596129-compute@developer.gserviceaccount.com \
#   --docker-username=_json_key \
#   --docker-password="$(cat 946201596129-compute-developer-svc-ac-key.json)" \
#   --namespace=uvision

# kubectl create secret docker-registry artifact-registery-secret \
#   --docker-server=https://us-central1-docker.pkg.dev/ \
#   --docker-email=946201596129-compute@developer.gserviceaccount.com \
#   --docker-username=_json_key \
#   --docker-password="$(cat 946201596129-compute-developer-svc-ac-key.json)" \
#   --namespace=argo

# kubectl create secret  generic gcp-svc-account-creds-secret -n uvision\
#   --from-file=946201596129-compute-developer-svc-ac-key.json

# ############################### Finish Artifact Registery Secrets ############################################################


############################### Deploy Argo Using Helm ##################################################################################

# ARGO_WORKFLOWS_VERSION="v3.6.7"
# kubectl apply -n argo -f "https://github.com/argoproj/argo-workflows/releases/download/${ARGO_WORKFLOWS_VERSION}/quick-start-minimal.yaml"

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



# Example: install chart version 0.46.2 (replace with your chosen chart version)
helm install argo-workflows argo/argo-workflows \
  --namespace argo \
  --version 0.46.2 \
  -f /mnt/data/ml-platform/kubernetes_deployment/values.yaml \
  --set crds.install=false

############################### Deploy Argo Finish##################################################################################

############################### Deploy Uvision Services ##################################################################################

kubectl apply -f yamls/

############################### Finish Uvision Services ##################################################################################

# kubectl apply -k "github.com/awslabs/mountpoint-s3-csi-driver/deploy/kubernetes/overlays/stable/"