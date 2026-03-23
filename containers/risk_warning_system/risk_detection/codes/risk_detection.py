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

device = "cuda" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if device == "cuda" else torch.float32

# ================= LOAD MODEL =================

logging.info("Loading Qwen VL model...")

processor = AutoProcessor.from_pretrained(
    MODEL_ID,
    trust_remote_code=True
)

model = AutoModelForImageTextToText.from_pretrained(
    MODEL_ID,
    trust_remote_code=True,
    torch_dtype=torch_dtype,
    low_cpu_mem_usage=True
)

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
    update_progress(SessionLocal=SessionLocal, status="RUNNING", progress=88, job_id=data["job_id"])

    # if OUTPUT_JSON:
    #     os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    #     with open(OUTPUT_JSON, "w") as f:
    #         json.dump(final_output, f, indent=2)

    logging.info("\nFinal Structured Output:")
    logging.info(json.dumps(final_output, indent=2))
    update_risk_detection(SessionLocal, folder_name, final_output)
    update_progress(SessionLocal=SessionLocal, status="COMPLETED", progress=100, job_id=data["job_id"])
