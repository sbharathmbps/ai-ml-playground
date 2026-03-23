import os
import json
import argparse
import logging
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from database_entry import get_local_session, update_resume_extracted_field, update_progress


HF_BASE = os.getenv("HF_HOME", "/opt/hf-cache")
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

logging.basicConfig(level=logging.INFO)

MODEL_ID = "LiquidAI/LFM2.5-1.2B-Instruct"
MAX_INPUT_CHARS = 30000
 
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
 
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    device_map="auto",
    torch_dtype=torch.bfloat16
)

logging.info("LFM model loaded")

SYSTEM_PROMPT = """
You are a resume information extraction agent.

Extract structured data from resumes.
Return ONLY valid JSON.
Do NOT include explanations.
If field is missing return null.

Schema:
{
    "Total_Experience": "",
    "Department": "",
    "Role": "",
    "Industry": "",
    "Organization": "",
    "Designation": "",
    "Education": "",
    "Graduation_Specialization": "",
    "University_Grad": "",
    "Passing_Year_Of_Graduation": "",
    "PG_Specialization": "",
    "University_PG": "",
    "Passing_Year_Of_PG": "",
    "Curent_Location": ""
}
"""


def read_resume_text(src_dir: str) -> str:
    src_path = Path(src_dir)
    files = [p for p in src_path.iterdir() if p.is_file()]

    if not files:
        raise FileNotFoundError(f"No input file found in {src_dir}")

    file_path = files[0]

    if file_path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise ImportError(
                "PDF input detected but 'pypdf' is not installed. Install pypdf in the field_extraction image."
            ) from e

        reader = PdfReader(str(file_path))
        page_text = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(page_text).strip()
        if not text:
            raise ValueError(f"No extractable text found in PDF: {file_path}")
        if len(text) > MAX_INPUT_CHARS:
            logging.warning(
                "Input text too long (%s chars). Truncating to %s chars to avoid OOM.",
                len(text),
                MAX_INPUT_CHARS,
            )
            return text[:MAX_INPUT_CHARS]
        return text

    for encoding in ("utf-8", "latin-1"):
        try:
            text = file_path.read_text(encoding=encoding)
            if len(text) > MAX_INPUT_CHARS:
                logging.warning(
                    "Input text too long (%s chars). Truncating to %s chars to avoid OOM.",
                    len(text),
                    MAX_INPUT_CHARS,
                )
                return text[:MAX_INPUT_CHARS]
            return text
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Unable to decode input file: {file_path}")


def extract_features_with_llm(resume_text: str) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": resume_text},
    ]

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.1,
        )

    response = tokenizer.decode(
        output[0][inputs["input_ids"].shape[-1] :],
        skip_special_tokens=True,
    )

    try:
        json_start = response.index("{")
        return json.loads(response[json_start:])
    except Exception:
        return {
            "error": "LLM failed to generate valid JSON",
            "raw_output": response,
        }


# def write_output(dest_dir: str, output: dict) -> None:
#     os.makedirs(dest_dir, exist_ok=True)
#     out_file = Path(dest_dir) / "field_extraction_output.json"
#     out_file.write_text(json.dumps(output, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resume Field Extraction")
    parser.add_argument("--src", help="Input resume directory")
    parser.add_argument("--dest", help="Output path")
    parser.add_argument("--config", help="Optional config file", default=None)
    parser.add_argument("--workflow_name", default="workflow")
    parser.add_argument("--folder_name", default="folder")
    parser.add_argument("--data", default="data from the database")

    args = parser.parse_args()

    src = args.src
    folder_name = args.folder_name
    data = json.loads(args.data)   

    SessionLocal, engine = get_local_session()
    update_progress(SessionLocal=SessionLocal, status="RUNNING", progress=16, job_id=data["job_id"])

    resume_text = read_resume_text(src)
    update_progress(SessionLocal=SessionLocal, status="RUNNING", progress=25, job_id=data["job_id"])

    final_output = extract_features_with_llm(resume_text)
    update_progress(SessionLocal=SessionLocal, status="RUNNING", progress=88, job_id=data["job_id"])

    # write_output(args.dest, final_output)

    logging.info("Final Structured Output:")
    logging.info(json.dumps(final_output, indent=2))

    update_resume_extracted_field(SessionLocal, folder_name, final_output)
    update_progress(SessionLocal=SessionLocal, status="COMPLETED", progress=100, job_id=data["job_id"])

    