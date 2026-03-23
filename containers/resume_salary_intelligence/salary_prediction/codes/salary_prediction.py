import os
import json
import argparse
from collections import OrderedDict

import joblib
import numpy as np
import pandas as pd

from database_entry import get_local_session, get_resume_user_field, update_market_ctc_by_resume, update_progress


MODEL_PATH = "/mnt/data/models/salary_prediction/salary_prediction_model.pkl"

RATING_MAP = {
    "Key_Performer": 5,
    "A": 4,
    "B": 3,
    "C": 2,
    "D": 1,
}

# Fixed stats from training-time preprocessing.
# These avoid any training-dataset reads during inference.
NUMERIC_STATS = {
    "Total_Experience": {"mean": 12.49308, "std": 7.471248363800807},
    "Total_Experience_in_field_applied": {"mean": 6.2582, "std": 5.819396253908358},
    "Current_CTC": {"mean": 1760945.38388, "std": 920194.1080452027},
    "Last_Appraisal_Rating": {"mean": 2.9338784658807935, "std": 1.3536568013518406},
    "No_Of_Companies_worked": {"mean": 3.48204, "std": 1.6903009904748545},
    "Number_of_Publications": {"mean": 4.08904, "std": 2.6065593947576744},
    "Certifications": {"mean": 0.77368, "std": 1.1994245526919045},
    "Expected_CTC": {"mean": 2250154.5104, "std": 1160456.9351034085},
}

RATING_FILL_VALUE = NUMERIC_STATS["Last_Appraisal_Rating"]["mean"]

DROP_COLUMNS = [
    "Applicant_ID",
    "Graduation_Specialization",
    "University_Grad",
    "Passing_Year_Of_Graduation",
    "PG_Specialization",
    "University_PG",
    "Passing_Year_Of_PG",
    "PHD_Specialization",
    "University_PHD",
    "Passing_Year_Of_PHD",
]

CATEGORICAL_BASE_COLUMNS = [
    "Department",
    "Role",
    "Industry",
    "Organization",
    "Designation",
    "Education",
    "Curent_Location",
    "Preferred_location",
    "Inhand_Offer",
    "International_degree_any",
]

# This was dropped in the final training matrix after VIF filtering.
VIF_DROPS = ["Total_Experience"]

# Field order must remain exactly in this shape.
PERSON_FIELD_ORDER = [
    "Applicant_ID",
    "Total_Experience",
    "Total_Experience_in_field_applied",
    "Department",
    "Role",
    "Industry",
    "Organization",
    "Designation",
    "Education",
    "Graduation_Specialization",
    "University_Grad",
    "Passing_Year_Of_Graduation",
    "PG_Specialization",
    "University_PG",
    "Passing_Year_Of_PG",
    "PHD_Specialization",
    "University_PHD",
    "Passing_Year_Of_PHD",
    "Curent_Location",
    "Preferred_location",
    "Current_CTC",
    "Inhand_Offer",
    "Last_Appraisal_Rating",
    "No_Of_Companies_worked",
    "Number_of_Publications",
    "Certifications",
    "International_degree_any",
]


def _zscore(value: float, mean: float, std: float) -> float:
    if std == 0:
        return value - mean
    return (value - mean) / std


def _clean_person(person: dict) -> dict:
    data = dict(person)

    for col in ["Department", "Role", "Industry", "Organization", "Designation"]:
        if pd.isna(data.get(col)):
            data[col] = "Others"

    rating = data.get("Last_Appraisal_Rating")
    rating = RATING_MAP.get(rating, rating)
    rating = pd.to_numeric(pd.Series([rating]), errors="coerce").iloc[0]
    if pd.isna(rating):
        rating = RATING_FILL_VALUE
    data["Last_Appraisal_Rating"] = float(rating)

    for col in DROP_COLUMNS:
        data.pop(col, None)

    return data


def preprocess_one_person(person: dict, model) -> pd.DataFrame:
    if not hasattr(model, "feature_names_in_"):
        raise ValueError("Loaded model does not expose feature_names_in_ needed for safe inference.")

    cleaned = _clean_person(person)
    model_features = list(model.feature_names_in_)
    row = {feature: 0.0 for feature in model_features}

    # Numeric features with z-score normalization to match training.
    for col, stats in NUMERIC_STATS.items():
        if col == "Expected_CTC" or col in VIF_DROPS:
            continue
        if col in row:
            raw_val = pd.to_numeric(pd.Series([cleaned.get(col)]), errors="coerce").iloc[0]
            if pd.isna(raw_val):
                raw_val = stats["mean"]
            row[col] = float(_zscore(float(raw_val), stats["mean"], stats["std"]))

    # Categorical one-hot reconstruction from model feature names.
    for cat_col in CATEGORICAL_BASE_COLUMNS:
        raw_value = cleaned.get(cat_col)
        raw_value = "Others" if pd.isna(raw_value) else str(raw_value)

        prefix = f"{cat_col}_"
        for feature in model_features:
            if feature.startswith(prefix):
                encoded_value = feature[len(prefix):]
                row[feature] = 1.0 if raw_value == encoded_value else 0.0

    return pd.DataFrame([row], columns=model_features)


def build_person_payload(user_field: dict) -> dict:
    user_field = user_field or {}

    cert_value = user_field.get("certifications")
    cert_count = cert_value
    if isinstance(cert_value, list):
        cert_count = len(cert_value)

    ordered = OrderedDict()
    for key in PERSON_FIELD_ORDER:
        if key in user_field:
            ordered[key] = user_field.get(key)
        elif key == "Applicant_ID":
            ordered[key] = 99999
        elif key in ["PHD_Specialization", "University_PHD", "Passing_Year_Of_PHD"]:
            ordered[key] = np.nan
        elif key == "Certifications":
            ordered[key] = cert_count
        else:
            ordered[key] = np.nan

    return dict(ordered)


# def write_output(dest_dir: str, output: dict) -> None:
#     os.makedirs(dest_dir, exist_ok=True)
#     out_file = os.path.join(dest_dir, "salary_prediction_output.json")
#     with open(out_file, "w", encoding="utf-8") as f:
#         json.dump(output, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Salary Prediction")
    parser.add_argument("--src", help="Input path")
    parser.add_argument("--dest", help="Output path")
    parser.add_argument("--config", help="Optional config file", default=None)
    parser.add_argument("--workflow_name", default="workflow")
    parser.add_argument("--folder_name", default="folder")
    parser.add_argument("--data", default="data from the database")
    
    args = parser.parse_args()

    resume_id = args.folder_name
    data = json.loads(args.data)

    SessionLocal, engine = get_local_session()
    update_progress(SessionLocal=SessionLocal, status="RUNNING", progress=33, job_id=data["job_id"])

    user_field_raw = get_resume_user_field(SessionLocal, resume_id)

    unwanted_field = {
    "Applicant_ID": None,
    "PHD_Specialization": None,
    "University_PHD": None,
    "Passing_Year_Of_PHD": None
}
    user_field = user_field_raw | unwanted_field
    
    person_payload = build_person_payload(user_field)

    model = joblib.load(MODEL_PATH)
    features = preprocess_one_person(person_payload, model)

    pred_scaled = float(model.predict(features)[0])
    pred_expected_ctc = (
        pred_scaled * NUMERIC_STATS["Expected_CTC"]["std"]
        + NUMERIC_STATS["Expected_CTC"]["mean"]
    )
    pred_expected_ctc = round(pred_expected_ctc, 2)

    update_market_ctc_by_resume(SessionLocal, resume_id, pred_expected_ctc)
    update_progress(SessionLocal=SessionLocal, status="RUNNING", progress=75, job_id=data["job_id"])

    result = {
        "input": person_payload,
        "predicted_expected_ctc": pred_expected_ctc,
        "resume_id": str(resume_id),
    }

    print(json.dumps(result, indent=2))
    update_progress(SessionLocal=SessionLocal, status="COMPLETED", progress=100, job_id=data["job_id"])


if __name__ == "__main__":
    main()


# Extra_dummy_field = {
#     "Applicant_ID": None,
#     "PHD_Specialization": None,
#     "University_PHD": None,
#     "Passing_Year_Of_PHD": None
# }

# User_filed:
# PERSON_FIELD_ORDER = [
    # "Total_Experience",
    # "Total_Experience_in_field_applied",
    # "Department",
    # "Role",
    # "Industry",
    # "Organization",
    # "Designation",
    # "Education",
    # "Graduation_Specialization",
    # "University_Grad",
    # "Passing_Year_Of_Graduation",
    # "PG_Specialization",
    # "University_PG",
    # "Passing_Year_Of_PG",
    # "Curent_Location",
    # "Preferred_location",
    # "Current_CTC",
    # "Inhand_Offer",
    # "Last_Appraisal_Rating",
    # "No_Of_Companies_worked",
    # "Number_of_Publications",
    # "Certifications",
    # "International_degree_any",
# ]


# {
#   "user_field": {
#     "Role": "AI/ML Platform Engineer / MLOps Engineer",
#     "Industry": "Technology",
#     "Education": "PG",
#     "Department": "Engineering",
#     "Designation": "AI Platform Project Lead",
#     "Organization": "TCS",
#     "University_PG": "Great Lakes Executive Learning & The University of Texas at Austin",
#     "Curent_Location": "Ahmedabad",
#     "University_Grad": "Chennai",
#     "Total_Experience": "2",
#     "PG_Specialization": "Data Science & Business Analytics",
#     "Passing_Year_Of_PG": "2024",
#     "Graduation_Specialization": "Electrical and electronics",
#     "Passing_Year_Of_Graduation": "2023"
#     "Total_Experience_in_field_applied": "2",
#     "Preferred_location": ""Bengaluru,
#     "Current_CTC": "400000",
#     "Inhand_Offer": "N",
#     "Last_Appraisal_Rating": "A",
#     "No_Of_Companies_worked": "1",
#     "Number_of_Publications": "0",
#     "Certifications": "2",
#     "International_degree_any": "0",
# }