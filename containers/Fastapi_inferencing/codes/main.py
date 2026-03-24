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
    get_risk_warning_outcomes,
    get_resume_fields,
    update_user_fields,
    get_recommended_jobs,
    apply_for_job,
    get_hr_applications,
    update_application_status,
    find_existing_market_ctc,
    update_application_market_ctc,
    get_application_market_ctc,
    update_progress,
    get_job_status
)
logging.basicConfig(level=logging.INFO)


app = FastAPI()

BASE_IMAGE_PATH = os.getenv("BASE_IMAGE_PATH")
ARGO_WORKFLOW_YAML_PATH = os.getenv("ARGO_WORKFLOW_YAML_PATH")
ARGO_WORKFLOW_API_URL = os.getenv("ARGO_WORKFLOW_API_URL")

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

#================================ Module 1: Risk warning system ==========================================

"""
RISK WARNING SYSTEM: (end-to-end flow) 
- user uploads an image (/upload_image/)
- click on "check risks" should hit (/risk_warning_system/)
- inside there are 2 sequential pods.
- one is risk factor detection and second one is sentence based object detection
- risk factor detection on completion will store risk_detected, risk_level, risk_factors(single list of all risks), explanation field in risk_detection table
- sentence based object detection will loop using each risk_factors of the image and it will detect the objects mentioned in the sentence
- it will store the detections in detections field in respective to risk_factor field in sentenced_object_detection table
- In frontend, you need to show the image uploaded and each risk factors in side or below the image with a checkbox.
- On selection of checkbox, it should draw all bbox and its labels of the respective sentence(risk factor).
- Below I'm pasting output format of risk factor detection. Each parameters will be stored to its respective field in table.
{
  "risk_detected": true or false,
  "risk_level": "low" | "medium" | "high",
  "risk_factors": [],
  "explanation": ""
}
- you can add interactive screen of your choice using these parameters like risk_level, risk_detected, explanation etc
- Below I'm pasting the db inserting format for each sentence of an image(table: sentenced_object_detection).
            risk_factor = item.get("sentence")

            detections = {
                "bboxes": item.get("bboxes", []),
                "labels": item.get("labels", [])
            }
- progression of model should be periodically monitor through jobs_status table. 
- when /risk_warning_system/ started, job_id, status and progress will be updated. Progress will be updated periodically inside the code. You can use it to show the current progression % in frontend.
- Once status become COMPLETED and progress become 100% you can fetch the output through @app.get("/risk_warning_system/{image_id}")
- for output payload structure, you can refer get_risk_warning_outcomes from database_entry.py
- Use the related table fields to create interactive screen for it.
- need to check progress and status frequently (every second) to update in frontend
""" 

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
    job_id: str


@app.post("/risk_warning_system/")
async def risk_warning_system(data: RiskPipelineRequest):

    folder_name = data.image_id
    job_name = folder_name + str(int(time.time()))
    job_id = str(uuid.uuid4())

    data_dict = data.model_dump()
    data_dict["job_id"] = job_id
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

    if job_name == None:
        update_progress(SessionLocal=SessionLocal, status="FAILED", progress=0, job_id=job_id)
        return JSONResponse(content=inferenceApi_response(status=status,Job_Name=job_name,job_id=job_id).model_dump(),status_code=status_code)
    else:
        update_progress(SessionLocal=SessionLocal, status="RUNNING", progress=10, job_id=job_id)
        return JSONResponse(content=inferenceApi_response(status=status,Job_Name=job_name,job_id=job_id).model_dump(),status_code=status_code)


@app.get("/risk_warning_system/{image_id}")
async def fetch_risk_warning_outcomes(image_id: str):

    try:
        result = get_risk_warning_outcomes(SessionLocal, image_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid image_id")

    if result is None:
        raise HTTPException(status_code=404, detail="Image not found")

    return result

#================================ Module 2: Resume salary intelligence ==========================================

"""
RESUME SALARY INTELLIGENCE: (end-to-end flow) 
- this is big one compared to previous module.
- you might need two separate screen/sidebar option/module for employee tab and hr tab.
- lets start with employee tab.
- after resume uploded, user should supposed to fill the 22 field listed below with an example:
  "user_field": {
    "Role": "AI/ML Platform Engineer / MLOps Engineer",
    "Industry": "Technology",
    "Education": "PG",
    "Department": "Engineering",
    "Designation": "AI Platform Project Lead",
    "Organization": "TCS",
    "University_PG": "Great Lakes Executive Learning & The University of Texas at Austin",
    "Curent_Location": "Ahmedabad",
    "University_Grad": "Chennai",
    "Total_Experience": "2",
    "PG_Specialization": "Data Science & Business Analytics",
    "Passing_Year_Of_PG": "2024",
    "Graduation_Specialization": "Electrical and electronics",
    "Passing_Year_Of_Graduation": "2023"
    "Total_Experience_in_field_applied": "2",
    "Preferred_location": ""Bengaluru,
    "Current_CTC": "400000",
    "Inhand_Offer": "N",
    "Last_Appraisal_Rating": "A",
    "No_Of_Companies_worked": "1",
    "Number_of_Publications": "0",
    "Certifications": "2",
    "International_degree_any": "0",
}
- And there should be an option to fill fields using ai which will call automated_field_extraction.
- once the inferencing is done and status of the job become COMPLETED, trigger get("/resume_fields/{resume_id}") and fill the fields which we got from the db.
- user should fill the remaining field and user can edit the field filled using ai.
- once user filled all the fields and on submission trigger put("/resume_fields/{resume_id}") to get stored in db.
- after submitting all details, user will get an option to find matching jobs which should hit post("/recommendation_engine/")
- Once processing is done and updated in jobs_status table, get("/recommended_jobs/{resume_id}") will fetch outcomes from db.
- check get_recommended_jobs in database_entry.py to understand the output payload format which you will receive.
- list recommended jobs using the rank to user. On click, it should show the full details of job description and so on.
- click on apply should hit post("/apply_job/") and it will be moved to applied job.
- Now the hr side comes into picture. The applied job, user details, resume should be visible for hr now. @app.get("/hr_applications/")
- hr will get an option to calculate the market value of the employee by hitting post("/salary_prediction/")
- once it is completed show the market value stored in market_ctc field in application_status table. get("/salary_prediction/{application_id}")
- hr can either select or reject the application.
- for output payload structure, you can refer relative function from database_entry.py
- Use the related table fields to create interactive screen for it.
- need to check progress and status frequently (every second) to update in frontend

""" 

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
    job_id: str

@app.post("/automated_field_extraction/")
async def risk_warning_system(data: ResumeIntelligenceRequest):

    folder_name = data.resume_id
    job_name = folder_name + str(int(time.time()))

    job_id = str(uuid.uuid4())

    data_dict = data.model_dump()
    data_dict["job_id"] = job_id

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

    if job_name == None:
        update_progress(SessionLocal=SessionLocal, status="FAILED", progress=0, job_id=job_id)
        return JSONResponse(content=inferenceApi_response(status=status,Job_Name=job_name,job_id=job_id).model_dump(),status_code=status_code)
    else:
        update_progress(SessionLocal=SessionLocal, status="RUNNING", progress=10, job_id=job_id)
        return JSONResponse(content=inferenceApi_response(status=status,Job_Name=job_name,job_id=job_id).model_dump(),status_code=status_code)
    

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

    job_id = str(uuid.uuid4())

    data_dict = data.model_dump()
    data_dict["job_id"] = job_id

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

    if job_name == None:
        update_progress(SessionLocal=SessionLocal, status="FAILED", progress=0, job_id=job_id)
        return JSONResponse(content=inferenceApi_response(status=status,Job_Name=job_name,job_id=job_id).model_dump(),status_code=status_code)
    else:
        update_progress(SessionLocal=SessionLocal, status="RUNNING", progress=10, job_id=job_id)
        return JSONResponse(content=inferenceApi_response(status=status,Job_Name=job_name,job_id=job_id).model_dump(),status_code=status_code)
    

@app.get("/job_status/{job_id}")
async def fetch_job_status(job_id: str):
    result = get_job_status(SessionLocal, job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


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
    job_id = str(uuid.uuid4())

    try:
        existing_market_ctc = find_existing_market_ctc(SessionLocal, folder_name)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume_id")

    if existing_market_ctc is not None:

        if application_id is not None:
            try:
                updated = update_application_market_ctc(SessionLocal, application_id, existing_market_ctc)
                update_progress(SessionLocal=SessionLocal, status="COMPLETED", progress=100, job_id=job_id)
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
    data_dict = data.model_dump()
    data_dict["job_id"] = job_id
    data_dict["resume_id"] = folder_name

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

    if job_name == None:
        update_progress(SessionLocal=SessionLocal, status="FAILED", progress=0, job_id=job_id)
        return JSONResponse(content=inferenceApi_response(status=status,Job_Name=job_name,job_id=job_id).model_dump(),status_code=status_code)
    else:
        update_progress(SessionLocal=SessionLocal, status="RUNNING", progress=10, job_id=job_id)
        return JSONResponse(content=inferenceApi_response(status=status,Job_Name=job_name,job_id=job_id).model_dump(),status_code=status_code)


@app.get("/salary_prediction/{application_id}")
async def fetch_salary_prediction(application_id: str):

    try:
        result = get_application_market_ctc(SessionLocal, application_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application_id")

    if result is None:
        raise HTTPException(status_code=404, detail="Application not found")

    return result
