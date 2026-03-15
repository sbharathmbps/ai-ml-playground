import os
import uuid
import time
import logging
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from run_workflow import run_argo_workflow 
from database_entry import get_local_session, insert_uploaded_image
logging.basicConfig(level=logging.INFO)


app = FastAPI()

BASE_IMAGE_PATH = "/mnt/data/inputs/"
ARGO_WORKFLOW_YAML_PATH = "/mnt/data/ml-platform/containers"
ARGO_WORKFLOW_API_URL = "http://argo-workflows-server.argo.svc.cluster.local:2746/api/v1/workflows/argo"
# ARGO_WORKFLOW_API_URL = "http://localhost:2746/api/v1/workflows/argo"

SessionLocal, engine = get_local_session()

class AuthTokenProvider:
    def get(self):
        token_path = os.getenv("TOKEN_PATH", "/var/run/secrets/tokens/token")
        with open(token_path, "r") as f:
            token = f.read().strip()
        if token.startswith("Bearer "):
            token = token[len("Bearer "):].strip()
        return token
token_provider = AuthTokenProvider()


@app.post("/upload_image/")
async def upload_image(file: UploadFile = File(...)):

    image_id = str(uuid.uuid4())

    os.makedirs(BASE_IMAGE_PATH, exist_ok=True)

    image_folder = os.path.join(BASE_IMAGE_PATH, image_id)
    os.makedirs(image_folder, exist_ok=True)

    image_path = os.path.join(image_folder, file.filename)

    with open(image_path, "wb") as buffer:
        buffer.write(await file.read())

    insert_uploaded_image(SessionLocal, image_id, image_path)

    return {
        "image_id": image_id,
        "image_path": image_path
    }


class RiskPipelineRequest(BaseModel):
    image_id: str

class inferenceApi_response(BaseModel):
    status: str
    Job_Name: str

@app.post("/risk_warning_system/")
async def risk_warning_system(data: RiskPipelineRequest):

    folder_name = data.image_id
    job_name = folder_name + str(int(time.time()))

    data_dict = data.model_dump()

    assets = ["all"]

    yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH,"risk_warning_system/risk_warning_system.yaml")
    dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH,"risk_warning_system/dependency_chart.json")

    status_code, status, job_name = run_argo_workflow(
        yaml_file_path=yaml_file_path,
        url=ARGO_WORKFLOW_API_URL,
        assets=assets,
        dependency_chart_path=dependency_chart_path,
        folder_name=folder_name,
        data=data_dict,
        namespace="argo",
        auth_token_provider=token_provider
    )

    return JSONResponse(content=inferenceApi_response(status=status,Job_Name=job_name).model_dump(),status_code=status_code)
