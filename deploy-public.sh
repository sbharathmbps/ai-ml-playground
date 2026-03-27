#!/bin/bash
set -eu

# =============================================================================
# deploy-public.sh
# Switches the Angular frontend to public-access mode:
#   1. environment.prod.ts  → relative API paths (browser-safe)
#   2. nginx.conf            → listen 80
#   3. Dockerfile-env        → EXPOSE 80
#   4. 12-angular.yaml       → containerPort/targetPort/nodePort → 80/80/30080
#   5. Rebuilds Angular image in minikube
#   6. Redeploys the Angular pod
#   7. Adds iptables rule: VM port 80 → minikube NodePort 30080
# =============================================================================

MINIKUBE_PROFILE="cpu-cluster"

BASE_DIR="/mnt/data/ml-platform"
ANGULAR_DIR="${BASE_DIR}/containers/Angular"
ENV_PROD="${ANGULAR_DIR}/codes/ml-platform-ui/src/environments/environment.prod.ts"
NGINX_CONF="${ANGULAR_DIR}/nginx.conf"
DOCKERFILE="${ANGULAR_DIR}/Dockerfile-env"
ANGULAR_YAML="${BASE_DIR}/kubernetes_deployment/yamls/12-angular.yaml"

echo "============================================="
echo "  Public Deployment - Starting"
echo "============================================="

# ── 1. Update environment.prod.ts ────────────────────────────────────────────
echo "[1/7] Updating environment.prod.ts → relative API paths..."
cat > "${ENV_PROD}" <<'EOF'
export const environment = {
  production: true,
  inferenceApiUrl: '/api/inference',
  chatbotApiUrl: '/api/chatbot'
};
EOF
echo "      Done."

# ── 2. Update nginx.conf ─────────────────────────────────────────────────────
echo "[2/7] Updating nginx.conf → listen 80..."
sed -i 's/listen 4200;/listen 80;/' "${NGINX_CONF}"
echo "      Done."

# ── 3. Update Dockerfile-env ─────────────────────────────────────────────────
echo "[3/7] Updating Dockerfile-env → EXPOSE 80..."
sed -i 's/EXPOSE 4200/EXPOSE 80/' "${DOCKERFILE}"
echo "      Done."

# ── 4. Update 12-angular.yaml ────────────────────────────────────────────────
echo "[4/7] Updating 12-angular.yaml → port 80, nodePort 30080..."
sed -i 's/containerPort: 4200/containerPort: 80/g' "${ANGULAR_YAML}"
sed -i 's/port: 4200/port: 80/g'                   "${ANGULAR_YAML}"
sed -i 's/targetPort: 4200/targetPort: 80/g'        "${ANGULAR_YAML}"
sed -i 's/nodePort: 30420/nodePort: 30080/'          "${ANGULAR_YAML}"
echo "      Done."

# ── 5. Rebuild Angular image ─────────────────────────────────────────────────
echo "[5/7] Rebuilding Angular Docker image in minikube..."
cd "${ANGULAR_DIR}"
minikube image build -f Dockerfile-env . -t angular-ml-platform:latest -p "${MINIKUBE_PROFILE}"
echo "      Done."

# ── 6. Redeploy Angular pod ──────────────────────────────────────────────────
echo "[6/7] Redeploying Angular pod..."
kubectl apply -f "${ANGULAR_YAML}"
kubectl rollout restart deployment/angular-app-deployment -n app
kubectl rollout status deployment/angular-app-deployment -n app --timeout=120s
echo "      Done."

# ── 7. Port-forward: VM port 80 → service port 80 ────────────────────────────
echo "[7/7] Starting kubectl port-forward (0.0.0.0:80 → svc/angular-app-service:80)..."

PID_FILE="/tmp/angular-port-forward.pid"

# Kill existing port-forward if running
if [ -f "${PID_FILE}" ]; then
  kill "$(cat "${PID_FILE}")" 2>/dev/null || true
  rm -f "${PID_FILE}"
fi

sudo nohup kubectl --kubeconfig "${HOME}/.kube/config" port-forward --address 0.0.0.0 svc/angular-app-service 80:80 -n app \
  > /tmp/angular-port-forward.log 2>&1 &
echo $! > "${PID_FILE}"
echo "      Done. PID: $(cat "${PID_FILE}")"

echo ""
echo "============================================="
echo "  Public Deployment - Complete"
echo "============================================="
echo ""
echo "  App is now accessible at:"
echo "    http://35.209.14.79"
echo ""
echo "  To rollback, run:"
echo "    bash ${BASE_DIR}/rollback-internal.sh"
echo "============================================="
