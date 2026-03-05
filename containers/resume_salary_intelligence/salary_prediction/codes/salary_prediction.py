import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


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

# Hardcoded input JSON for a single person.
HARDCODED_PERSON = {
    "Applicant_ID": 99999,
    "Total_Experience": 6,
    "Total_Experience_in_field_applied": 5,
    "Department": "Engineering",
    "Role": "Software Developer",
    "Industry": "IT Services",
    "Organization": "Private",
    "Designation": "Senior Software Engineer",
    "Education": "PG",
    "Graduation_Specialization": "Computer Science",
    "University_Grad": "Delhi",
    "Passing_Year_Of_Graduation": 2018,
    "PG_Specialization": "Data Science",
    "University_PG": "Delhi",
    "Passing_Year_Of_PG": 2020,
    "PHD_Specialization": np.nan,
    "University_PHD": np.nan,
    "Passing_Year_Of_PHD": np.nan,
    "Curent_Location": "Bangalore",
    "Preferred_location": "Bangalore",
    "Current_CTC": 1800000,
    "Inhand_Offer": "Y",
    "Last_Appraisal_Rating": "A",
    "No_Of_Companies_worked": 3,
    "Number_of_Publications": 1,
    "Certifications": 2,
    "International_degree_any": 0,
}


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


def main() -> None:
    model = joblib.load(MODEL_PATH)
    features = preprocess_one_person(HARDCODED_PERSON, model)

    pred_scaled = float(model.predict(features)[0])
    pred_expected_ctc = (
        pred_scaled * NUMERIC_STATS["Expected_CTC"]["std"]
        + NUMERIC_STATS["Expected_CTC"]["mean"]
    )

    result = {
        "input": HARDCODED_PERSON,
        "predicted_expected_ctc": round(pred_expected_ctc, 2)
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
