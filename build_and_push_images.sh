# cd /mnt/data/ml-platform/containers/risk_warning_system/sentenced_object_detection
# minikube image build -f Dockerfile-env . -t sentenced-obj-det-env:python-3.10-slim -p cpu-cluster


# cd /mnt/data/ml-platform/containers/risk_warning_system/sentenced_object_detection
# minikube image build -f Dockerfile-cli-input . -t sentenced-obj-det-cli-input:python-3.10-slim -p cpu-cluster

 
# docker run --rm \
# -v /mnt/data/ml-platform/containers/risk_warning_system/sentenced_object_detection:/input \
# -v /mnt/data/ml-platform/containers/risk_warning_system/sentenced_object_detection/output:/output \
# sentenced-obj-det-cli-input:python-3.10-slim \
# --src /input/traffic.jpg \
# --risk_json /input/risk_factors.json \
# --output /output/florence_output.jpg \
# --workflow_name vlm_pipeline \
# --folder_name workorder_1234


#=====================================================================================================================================================================================================================


# cd /mnt/data/ml-platform/containers/risk_warning_system/risk_detection
# minikube image build -f Dockerfile-env . -t risk-detection-env:python-3.12 -p cpu-cluster


# cd /mnt/data/ml-platform/containers/risk_warning_system/risk_detection
# minikube image build -f Dockerfile-cli-input . -t risk-detection-cli-input:python-3.12 -p cpu-cluster


# docker run --rm \
# -v /mnt/data/ml-platform/containers/risk_warning_system/risk_detection:/input \
# -v /mnt/data/ml-platform/containers/risk_warning_system/risk_detection/output:/output \
# risk-detection-cli-input:python-3.12 \
# --src /input/u-shaped-modular-kitchen-1000x1000.jpg \
# --output_json /output/risk_factors.json \
# --workflow_name vlm_pipeline \
# --folder_name workorder_1234


##=====================================================================================================================================================================================================================

# cd /mnt/data/ml-platform/containers/resume_salary_intelligence/field_extraction
# minikube image build -f Dockerfile-env . -t field-extraction-env:python-3.10-slim -p cpu-cluster


# cd /mnt/data/ml-platform/containers/resume_salary_intelligence/field_extraction
# minikube image build -f Dockerfile-cli-input . -t field-extraction-cli-input:python-3.10-slim -p cpu-cluster

#=====================================================================================================================================================================================================================

# cd /mnt/data/ml-platform/containers/resume_salary_intelligence/recommendation_engine
# minikube image build -f Dockerfile-env . -t recommendation-engine-env:python-3.12 -p cpu-cluster


# cd /mnt/data/ml-platform/containers/resume_salary_intelligence/recommendation_engine
# minikube image build -f Dockerfile-cli-input . -t recommendation-engine-cli-input:python-3.12 -p cpu-cluster

#=====================================================================================================================================================================================================================

# cd /mnt/data/ml-platform/containers/resume_salary_intelligence/salary_prediction
# minikube image build -f Dockerfile-env . -t salary-prediction-env:python-3.12 -p cpu-cluster


# cd /mnt/data/ml-platform/containers/resume_salary_intelligence/salary_prediction
# minikube image build -f Dockerfile-cli-input . -t salary-prediction-cli-input:python-3.12 -p cpu-cluster

##=====================================================================================================================================================================================================================

# cd /mnt/data/ml-platform/containers/Fastapi_inferencing
# minikube image build -f Dockerfile-env . -t inference-engine-fastapi:python-3.11.13-slim -p cpu-cluster

##=====================================================================================================================================================================================================================

# cd /mnt/data/ml-platform/containers/shopping_chatbot
# minikube image build -f Dockerfile-env . -t ollama-chatbot:python-3.12 -p cpu-cluster

##=====================================================================================================================================================================================================================

# #   Step 1 — Rebuild the Docker image (includes npm build inside Docker):                                                                  
  cd /mnt/data/ml-platform/containers/Angular                                                                                            
  minikube image build -f Dockerfile-env . -t angular-ml-platform:latest -p cpu-cluster                                                  
                                                                                                                                         
  kubectl rollout restart deployment/angular-app-deployment -n app
