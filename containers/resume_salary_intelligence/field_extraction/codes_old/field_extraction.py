import os
HF_BASE = "/mnt/disks/conda-envs/Dockerize-Platform/Volumes/Image-input/VLM_input/huggingface_cache"

os.environ["HF_HOME"] = HF_BASE
os.environ["HF_HUB_CACHE"] = f"{HF_BASE}/hub"
os.environ["TRANSFORMERS_CACHE"] = f"{HF_BASE}/transformers"
os.environ["HF_DATASETS_CACHE"] = f"{HF_BASE}/datasets"

os.environ["TMPDIR"] = f"{HF_BASE}/tmp"
os.environ["TEMP"] = f"{HF_BASE}/tmp"
os.environ["TMP"] = f"{HF_BASE}/tmp"

import json
import torch
import numpy as np
from transformers import AutoModelForCausalLM, AutoTokenizer

os.environ["HF_HOME"] = HF_BASE
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_TOKEN"] = "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"
 
# ---------------------------
# 1️⃣ Load LLM (LFM2.5 1.2B)
# ---------------------------
 
MODEL_ID = "LiquidAI/LFM2.5-1.2B-Instruct"
 
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
 
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    device_map="auto",
    torch_dtype=torch.bfloat16
)
 
 
SYSTEM_PROMPT = """
You are a resume information extraction agent.
 
Extract structured data from resumes.
Return ONLY valid JSON.
Do NOT include explanations.
If field is missing return null.
 
Schema:
{
  "name": "",
  "years_of_experience": "",
  "current_role": "",
  "primary_skills": [],
  "education_level": "",
  "location": "",
  "certifications": []
}
"""
 
def extract_features_with_llm(resume_text: str):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": resume_text}
    ]
 
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenizer=True,
        return_tensors="pt"
    ).to(model.device)

    inputs = {k: v.to(model.device) for k, v in inputs.items()}
 
    output = model.generate(
        **inputs,
        max_new_tokens=512,
        temperature=0.1
    )
 
    response = tokenizer.decode(
        output[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True
    )
 
    try:
        data = json.loads(response)
    except:
        data = {"error": "LLM failed to generate valid JSON", "raw_output": response}
 
    return data

if __name__=="__main__": 

     
    resume_text = """
Resume – MLOps Engineer
Name: Arjun Mehta
Phone: +91 98765 43210
Email: arjun.mehta.ml@samplemail.com
Location: Bengaluru, Karnataka
LinkedIn: linkedin.com/in/arjun-mehta-mlops
GitHub: github.com/arjun-mlops

Professional Summary
MLOps Engineer with 4+ years of experience in designing, deploying, and scaling machine learning pipelines in cloud environments. Skilled in CI/CD, model deployment, monitoring, and data pipeline automation. Currently working at Tata Consultancy Services (TCS) as part of the AI & Analytics practice, supporting production-grade ML systems for global enterprise clients.

Work Experience
MLOps Engineer – Tata Consultancy Services (TCS)
Jan 2022 – Present | Bengaluru, India

Designed and maintained automated ML pipelines using Kubeflow, Airflow, and MLflow, reducing model deployment time by 40%.
Built end‑to‑end CI/CD workflows using Azure DevOps and GitHub Actions for ML model packaging, testing, and deployment.
Containerized ML services using Docker and deployed scalable services on Kubernetes (AKS/EKS).
Implemented model monitoring dashboards using Prometheus, Grafana, and Azure Application Insights.
Set up feature stores using Feast, improving data consistency across training and inference.
Collaborated with data scientists to operationalize NLP and forecasting models for BFSI clients.


Technical Skills
Programming
Python, Bash, SQL, Go (basic)
MLOps / ML Platforms
MLflow, Kubeflow, Airflow, TFX, Feast, DVC
Cloud
Azure (primary), AWS (secondary), GCP (basic)
DevOps & CI/CD
Docker, Kubernetes, GitHub Actions, Azure DevOps, Terraform, Helm
Machine Learning
Scikit-learn, TensorFlow, PyTorch, XGBoost
Monitoring & Logging
Prometheus, Grafana, ELK Stack, Application Insights

Projects
1. Automated Model Deployment Platform

Created a reusable deployment framework for NLP-based classification systems.
Achieved fully automated data validation → training → evaluation → deployment using MLflow & Airflow.
Reduced manual intervention near-zero for production rollouts.

2. Real‑Time Fraud Detection Pipeline

Deployed streaming inference pipeline for financial transactions using AWS Lambda, SQS, and Docker.
Integrated model drift monitoring and auto‑retraining triggers.

3. Feature Store Integration for Enterprise Models

Implemented Feast with Azure Data Lake Storage.
Enabled consistent feature access across 8 ML teams.


Education
B.Tech – Computer Science Engineering
Visvesvaraya Technological University (VTU), Karnataka
2017 – 2021

Certifications

Microsoft Certified: Azure Data Scientist Associate
AWS Certified Machine Learning – Specialty
TensorFlow Developer Certificate


Tools & Technologies

Version Control: Git, GitLab
Databases: PostgreSQL, BigQuery, MongoDB
Message Queues: Kafka, SQS
IaC: Terraform, ARM


Personal Details

Languages: English, Hindi
Nationality: Indian
"""
    fields = extract_features_with_llm(resume_text)
    print(fields)

 