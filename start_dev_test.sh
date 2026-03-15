nohup kubectl -n argo port-forward service/argo-workflows-server 2746:2746 > /dev/null 2>&1 &

nohup kubectl port-forward -n app service/inference-engine-app-service 8000:8000 > portforward.log 2>&1 &

kubectl logs deployment/inference-engine-app-deployment -n app -f