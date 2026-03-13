cd /mnt/data/ml-platform/containers/risk_warning_system/sentenced_object_detection
minikube image build -f Dockerfile-env . -t sentenced-obj-det-env:python-3.10-slim -p cpu-cluster
# # docker tag chatbot-env:python-3.12.11-slim-bookworm us-central1-docker.pkg.dev/utilities-vision/uvision-kubernetes-deployment/test/chatbot-env:python-3.12.11-slim-bookworm  
# # docker push us-central1-docker.pkg.dev/utilities-vision/uvision-kubernetes-deployment/test/chatbot-env:python-3.12.11-slim-bookworm                            


cd /mnt/data/ml-platform/containers/risk_warning_system/sentenced_object_detection
minikube image build -f Dockerfile-cli-input . -t sentenced-obj-det-cli-input:python-3.10-slim -p cpu-cluster
# # docker tag chatbot-cli-input:python-3.12.11-slim-bookworm us-central1-docker.pkg.dev/utilities-vision/uvision-kubernetes-deployment/test/chatbot-cli-input:python-3.12.11-slim-bookworm  
# # docker push us-central1-docker.pkg.dev/utilities-vision/uvision-kubernetes-deployment/test/chatbot-cli-input:python-3.12.11-slim-bookworm 


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


cd /mnt/data/ml-platform/containers/risk_warning_system/risk_detection
minikube image build -f Dockerfile-env . -t risk-detection-env:python-3.12 -p cpu-cluster
# # docker tag chatbot-env:python-3.12.11-slim-bookworm us-central1-docker.pkg.dev/utilities-vision/uvision-kubernetes-deployment/test/chatbot-env:python-3.12.11-slim-bookworm  
# # docker push us-central1-docker.pkg.dev/utilities-vision/uvision-kubernetes-deployment/test/chatbot-env:python-3.12.11-slim-bookworm                            


cd /mnt/data/ml-platform/containers/risk_warning_system/risk_detection
minikube image build -f Dockerfile-cli-input . -t risk-detection-cli-input:python-3.12 -p cpu-cluster
# # docker tag chatbot-cli-input:python-3.12.11-slim-bookworm us-central1-docker.pkg.dev/utilities-vision/uvision-kubernetes-deployment/test/chatbot-cli-input:python-3.12.11-slim-bookworm  
# # docker push us-central1-docker.pkg.dev/utilities-vision/uvision-kubernetes-deployment/test/chatbot-cli-input:python-3.12.11-slim-bookworm 


# docker run --rm \
# -v /mnt/data/ml-platform/containers/risk_warning_system/risk_detection:/input \
# -v /mnt/data/ml-platform/containers/risk_warning_system/risk_detection/output:/output \
# risk-detection-cli-input:python-3.12 \
# --src /input/u-shaped-modular-kitchen-1000x1000.jpg \
# --output_json /output/risk_factors.json \
# --workflow_name vlm_pipeline \
# --folder_name workorder_1234


#=====================================================================================================================================================================================================================


# cd /mnt/data/ml-platform/containers/Fastapi_inferencing
# minikube image build -f Dockerfile-env . -t inference-engine-fastapi:python-3.11.13-slim -p cpu-cluster
# docker tag chatbot-env:python-3.12.11-slim-bookworm us-central1-docker.pkg.dev/utilities-vision/uvision-kubernetes-deployment/test/chatbot-env:python-3.12.11-slim-bookworm  
# docker push us-central1-docker.pkg.dev/utilities-vision/uvision-kubernetes-deployment/test/chatbot-env:python-3.12.11-slim-bookworm                            
