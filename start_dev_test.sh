# nohup kubectl -n argo port-forward service/argo-workflows-server 2746:2746 > /dev/null 2>&1 &

# nohup kubectl port-forward -n app service/inference-engine-app-service 8000:8000 > portforward.log 2>&1 &

# kubectl logs deployment/inference-engine-app-deployment -n app -f

# # Step 1 — Build Angular locally (no Docker needed):                                                                            
#   cd /mnt/data/ml-platform/containers/Angular/codes/ml-platform-ui                                                              
#   npm run build -- --configuration=production                                                                                   
                                                                                                                                
# #   Step 2 — Copy built files directly into the running pod:                                                                      
#   # kubectl cp dist/ml-platform-ui/browser/. app/angular-app-deployment-7d8dd9567d-wthbq:/usr/share/nginx/html/     
#   kubectl cp dist/ml-platform-ui/browser/. app/angular-app-deployment-68b645ffd-mjxdt:/usr/share/nginx/html/ 2>&1