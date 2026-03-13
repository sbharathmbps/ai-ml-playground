kubectl delete -f /mnt/data/ml-platform/kubernetes_deployment/yamls
helm uninstall argo-workflows -n argo --wait

# Delete Argo Workflows CRDs
kubectl delete crd workflows.argoproj.io \
  workflowtemplates.argoproj.io \
  clusterworkflowtemplates.argoproj.io \
  cronworkflows.argoproj.io \
  workflowartifactgctasks.argoproj.io


kubectl delete namespace argo
kubectl delete namespace app
# kubectl delete secret/artifact-registery-secret -n default

