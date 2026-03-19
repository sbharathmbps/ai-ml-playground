import os
import uuid
import time
import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from run_workflow import run_argo_workflow 
from database_entry import (
    get_local_session,
    insert_uploaded_image,
    insert_uploaded_resume,
    get_resume_fields,
    update_user_fields,
    get_recommended_jobs,
    apply_for_job,
    get_hr_applications,
    update_application_status,
    find_existing_market_ctc,
    update_application_market_ctc
)
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

#================================ Risk warning system ==========================================

@app.post("/upload_image/")
async def upload_image(file: UploadFile = File(...)):

    if not file.filename.lower().endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Only images are allowed")


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


#================================ Resume salary intelligence ==========================================

@app.post("/upload_resume/")
async def upload_resume(file: UploadFile = File(...)):

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    resume_id = str(uuid.uuid4())

    os.makedirs(BASE_IMAGE_PATH, exist_ok=True)

    resume_folder = os.path.join(BASE_IMAGE_PATH, resume_id)
    os.makedirs(resume_folder, exist_ok=True)

    resume_path = os.path.join(resume_folder, file.filename)

    with open(resume_path, "wb") as buffer:
        buffer.write(await file.read())

    insert_uploaded_resume(SessionLocal, resume_id, resume_path)

    return {
        "resume_id": resume_id,
        "resume_path": resume_path
    }


class ResumeIntelligenceRequest(BaseModel):
    resume_id: str

class inferenceApi_response(BaseModel):
    status: str
    Job_Name: str

@app.post("/automated_field_extraction/")
async def risk_warning_system(data: ResumeIntelligenceRequest):

    folder_name = data.resume_id
    job_name = folder_name + str(int(time.time()))

    data_dict = data.model_dump()

    assets = ["field_extraction"]

    yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH,"resume_salary_intelligence/resume_intelligence.yaml")
    dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH,"resume_salary_intelligence/dependency_chart.json")

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


class UserResumeFieldRequest(BaseModel):
    user_field: Dict[str, Any]

@app.get("/resume_fields/{resume_id}")
async def fetch_resume_fields(resume_id: str):

    try:
        result = get_resume_fields(SessionLocal, resume_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume_id")

    if result is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    return result


@app.put("/resume_fields/{resume_id}")
async def save_resume_fields(resume_id: str, data: UserResumeFieldRequest):

    try:
        updated = update_user_fields(SessionLocal, resume_id, data.user_field)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume_id")

    if not updated:
        raise HTTPException(status_code=404, detail="Resume not found")

    return {
        "resume_id": resume_id,
        "message": "User fields saved successfully"
    }


@app.post("/recommendation_engine/")
async def recommendation_engine(data: ResumeIntelligenceRequest):

    folder_name = data.resume_id
    job_name = folder_name + str(int(time.time()))

    data_dict = data.model_dump()

    assets = ["recommendation_engine"]

    yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH,"resume_salary_intelligence/resume_intelligence.yaml")
    dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH,"resume_salary_intelligence/dependency_chart.json")

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


@app.get("/recommended_jobs/{resume_id}")
async def fetch_recommended_jobs(resume_id: str):

    try:
        result = get_recommended_jobs(SessionLocal, resume_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume_id")

    if result is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    return result


class JobApplyRequest(BaseModel):
    resume_id: str
    job_id: str

@app.post("/apply_job/")
async def apply_job(data: JobApplyRequest):

    try:
        result = apply_for_job(SessionLocal, data.resume_id, data.job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume_id or job_id")

    if result["success"] is False and result["reason"] == "resume_not_found":
        raise HTTPException(status_code=404, detail="Resume not found")

    if result["success"] is False and result["reason"] == "job_not_found":
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "resume_id": data.resume_id,
        "job_id": data.job_id,
        "application_id": result["application_id"],
        "status": "applied",
        "message": "Job applied successfully"
    }


@app.get("/hr_applications/")
async def fetch_hr_applications(status: str = None):

    if status is not None and status not in ["applied", "selected", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    result = get_hr_applications(SessionLocal, status=status)

    return {
        "count": len(result),
        "applications": result
    }



class HRStatusUpdateRequest(BaseModel):
    application_id: str
    status: str

@app.put("/hr_application_status/")
async def update_hr_application_status(data: HRStatusUpdateRequest):

    if data.status not in ["selected", "rejected"]:
        raise HTTPException(status_code=400, detail="Status must be selected or rejected")

    try:
        updated = update_application_status(SessionLocal, data.application_id, data.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application_id")

    if not updated:
        raise HTTPException(status_code=404, detail="Application not found")

    return {
        "application_id": data.application_id,
        "status": data.status,
        "message": "Application status updated successfully"
    }


class SalaryPredictionRequest(BaseModel):
    resume_id: str
    application_id: Optional[str] = None

@app.post("/salary_prediction/")
async def salary_prediction(data: SalaryPredictionRequest):

    folder_name = data.resume_id
    application_id = data.application_id

    try:
        existing_market_ctc = find_existing_market_ctc(SessionLocal, folder_name)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume_id")

    if existing_market_ctc is not None:

        if application_id is not None:
            try:
                updated = update_application_market_ctc(SessionLocal, application_id, existing_market_ctc)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid application_id")
            if not updated:
                raise HTTPException(status_code=404, detail="Application not found")

        return {
            "status": "Market CTC already available",
            "resume_id": folder_name,
            "application_id": application_id,
            "market_ctc": float(existing_market_ctc)
        }

    job_name = folder_name + str(int(time.time()))

    data_dict = {"resume_id": folder_name}

    assets = ["salary_prediction"]

    yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH,"resume_salary_intelligence/resume_intelligence.yaml")
    dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH,"resume_salary_intelligence/dependency_chart.json")

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

    return JSONResponse(content=inferenceApi_response(status=status, Job_Name=job_name).model_dump(),status_code=status_code)
