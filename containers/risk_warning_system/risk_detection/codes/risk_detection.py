import os
HF_BASE = os.getenv("HF_HOME", "/opt/hf-cache")

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# ================= IMPORTS =================

import json
import torch
import argparse
import logging
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText
from database_entry import get_local_session, update_risk_detection, update_progress


logging.basicConfig(level=logging.INFO)

# ================= MODEL CONFIG =================

MODEL_ID = "Qwen/Qwen3-VL-4B-Instruct"
MODEL_REVISION = os.getenv("QWEN_MODEL_REVISION")
MAX_IMAGE_SIDE = int(os.getenv("RISK_DETECTION_MAX_IMAGE_SIDE", "1280"))

device = "cuda" if torch.cuda.is_available() else "cpu"


def _preferred_cpu_dtype():
    # bfloat16 cuts CPU memory roughly in half compared to float32 on model load.
    # If the environment cannot support it cleanly, we fall back to float32.
    return torch.bfloat16


torch_dtype = torch.float16 if device == "cuda" else _preferred_cpu_dtype()

# ================= LOAD MODEL =================

logging.info("Loading Qwen VL model...")

from_pretrained_kwargs = {
    "trust_remote_code": True,
    "low_cpu_mem_usage": True,
    "local_files_only": os.getenv("HF_HUB_OFFLINE", "1") == "1",
}
if MODEL_REVISION:
    from_pretrained_kwargs["revision"] = MODEL_REVISION

processor = AutoProcessor.from_pretrained(
    MODEL_ID,
    **from_pretrained_kwargs
)

try:
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_ID,
        torch_dtype=torch_dtype,
        **from_pretrained_kwargs
    )
except Exception:
    if device == "cpu" and torch_dtype == torch.bfloat16:
        logging.warning("CPU bfloat16 load failed. Retrying with float32.")
        torch_dtype = torch.float32
        model = AutoModelForImageTextToText.from_pretrained(
            MODEL_ID,
            torch_dtype=torch_dtype,
            **from_pretrained_kwargs
        )
    else:
        raise

if device != "cpu":
    model.to(device)

logging.info("Qwen VL model loaded")

# ================= SYSTEM PROMPT =================

SYSTEM_PROMPT = """
You are an industrial and public safety risk inspection AI.

Analyze the provided image carefully.

Return ONLY valid JSON with this schema:

{
  "risk_detected": true or false,
  "risk_level": "low" | "medium" | "high",
  "risk_factors": [],
  "explanation": ""
}

Rules:
- If no safety issues, set risk_detected to false.
- Be concise.
- Do not add extra text.
"""

# ================= ANALYZE IMAGE =================

def analyze_image_for_risk(image_path):

    image = Image.open(image_path).convert("RGB")

    # Bound image size before VLM inference to reduce CPU latency and memory.
    if max(image.size) > MAX_IMAGE_SIDE:
        image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.Resampling.LANCZOS)

    messages = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": SYSTEM_PROMPT}
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": "Analyze this image for safety hazards."}
            ],
        }
    ]

    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt"
    ).to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=300,
            temperature=0.1
        )

    response = processor.decode(
        outputs[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True
    )

    try:
        json_start = response.index("{")
        parsed = json.loads(response[json_start:])
    except:
        parsed = {
            "error": "Invalid JSON generated",
            "raw_output": response
        }

    return parsed


# ================= CLI MAIN =================

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Qwen Risk Detection")

    parser.add_argument("--src", help="Input image path")
    parser.add_argument("--dest", help="Output path")
    parser.add_argument("--config", help="Optional config file", default=None)

    parser.add_argument("--workflow_name", default="workflow")
    parser.add_argument("--folder_name", default="folder")
    parser.add_argument("--data", default="data from the database")


    args = parser.parse_args()
    data = json.loads(args.data)

    src = args.src
    OUTPUT_PATH = args.dest

    workflow_name = args.workflow_name
    folder_name = args.folder_name

    IMAGE_PATH = os.path.join(src, os.listdir(src)[0])

    # ================= RUN PIPELINE =================
    SessionLocal, engine = get_local_session()
    update_progress(SessionLocal=SessionLocal, status="RUNNING", progress=16, job_id=data["job_id"])

    final_output = analyze_image_for_risk(IMAGE_PATH)
    update_progress(SessionLocal=SessionLocal, status="RUNNING", progress=57, job_id=data["job_id"])

    # if OUTPUT_JSON:
    #     os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    #     with open(OUTPUT_JSON, "w") as f:
    #         json.dump(final_output, f, indent=2)

    logging.info("\nFinal Structured Output:")
    logging.info(json.dumps(final_output, indent=2))
    update_risk_detection(SessionLocal, folder_name, final_output)
