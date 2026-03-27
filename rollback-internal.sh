#!/bin/bash
set -eu

# =============================================================================
# rollback-internal.sh
# Reverts Angular frontend to the original internal (minikube-only) setup:
#   1. environment.prod.ts  → K8s internal DNS URLs
#   2. nginx.conf            → listen 4200
#   3. Dockerfile-env        → EXPOSE 4200
#   4. 12-angular.yaml       → containerPort/targetPort/nodePort → 4200/4200/30420
#   5. Rebuilds Angular image in minikube
#   6. Redeploys the Angular pod
#   7. Removes iptables port forwarding rule
# =============================================================================

MINIKUBE_PROFILE="cpu-cluster"

BASE_DIR="/mnt/data/ml-platform"
ANGULAR_DIR="${BASE_DIR}/containers/Angular"
ENV_PROD="${ANGULAR_DIR}/codes/ml-platform-ui/src/environments/environment.prod.ts"
NGINX_CONF="${ANGULAR_DIR}/nginx.conf"
DOCKERFILE="${ANGULAR_DIR}/Dockerfile-env"
ANGULAR_YAML="${BASE_DIR}/kubernetes_deployment/yamls/12-angular.yaml"

echo "============================================="
echo "  Rollback to Internal Setup - Starting"
echo "============================================="

# ── 1. Restore environment.prod.ts ───────────────────────────────────────────
echo "[1/7] Restoring environment.prod.ts → K8s internal DNS URLs..."
cat > "${ENV_PROD}" <<'EOF'
export const environment = {
  production: true,
  inferenceApiUrl: 'http://inference-engine-app-service.app.svc.cluster.local:8000',
  chatbotApiUrl: 'http://chatbot-app-service.app.svc.cluster.local:5000'
};
EOF
echo "      Done."

# ── 2. Restore nginx.conf ────────────────────────────────────────────────────
echo "[2/7] Restoring nginx.conf → listen 4200..."
sed -i 's/listen 80;/listen 4200;/' "${NGINX_CONF}"
echo "      Done."

# ── 3. Restore Dockerfile-env ────────────────────────────────────────────────
echo "[3/7] Restoring Dockerfile-env → EXPOSE 4200..."
sed -i 's/EXPOSE 80/EXPOSE 4200/' "${DOCKERFILE}"
echo "      Done."

# ── 4. Restore 12-angular.yaml ───────────────────────────────────────────────
echo "[4/7] Restoring 12-angular.yaml → port 4200, nodePort 30420..."
sed -i 's/containerPort: 80/containerPort: 4200/g' "${ANGULAR_YAML}"
sed -i 's/port: 80/port: 4200/g'                   "${ANGULAR_YAML}"
sed -i 's/targetPort: 80/targetPort: 4200/g'        "${ANGULAR_YAML}"
sed -i 's/nodePort: 30080/nodePort: 30420/'          "${ANGULAR_YAML}"
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

# ── 7. Stop port-forward ──────────────────────────────────────────────────────
echo "[7/7] Stopping kubectl port-forward..."
PID_FILE="/tmp/angular-port-forward.pid"
if [ -f "${PID_FILE}" ]; then
  sudo kill "$(cat "${PID_FILE}")" 2>/dev/null || true
  rm -f "${PID_FILE}"
fi
echo "      Done."

echo ""
echo "============================================="
echo "  Rollback to Internal Setup - Complete"
echo "============================================="
echo ""
echo "  App is now accessible only via minikube:"
echo "    http://<minikube-ip>:30420"
echo ""
echo "  To switch to public mode, run:"
echo "    bash ${BASE_DIR}/deploy-public.sh"
echo "============================================="
