import os
HF_BASE = "/mnt/disks/conda-envs/Dockerize-Platform/Volumes/Image-input/VLM_input/huggingface_cache"

os.environ["HF_HOME"] = HF_BASE
os.environ["HF_HUB_CACHE"] = f"{HF_BASE}/hub"
os.environ["TRANSFORMERS_CACHE"] = f"{HF_BASE}/transformers"
os.environ["HF_DATASETS_CACHE"] = f"{HF_BASE}/datasets"

os.environ["TMPDIR"] = f"{HF_BASE}/tmp"
os.environ["TEMP"] = f"{HF_BASE}/tmp"
os.environ["TMP"] = f"{HF_BASE}/tmp"

import torch
import json
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText
os.environ["HF_HOME"] = HF_BASE
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_TOKEN"] = "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"
 
# ----------------------------------------
# 1️⃣ Model Configuration
# ----------------------------------------
 
MODEL_ID = "Qwen/Qwen3-VL-4B-Instruct"
 
device = "cuda" if torch.cuda.is_available() else "cpu"
 
# Load processor (handles image + text)
processor = AutoProcessor.from_pretrained(MODEL_ID)
 
# Load model (use float16 for memory efficiency)
model = AutoModelForImageTextToText.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    device_map="auto"
)
 
model.eval()
 
 
# ----------------------------------------
# 2️⃣ System Prompt (Agent Behaviour)
# ----------------------------------------
 
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
 
 
# ----------------------------------------
# 3️⃣ Risk Extraction Function
# ----------------------------------------
 
def analyze_image_for_risk(image_path: str):
 
    image = Image.open(image_path).convert("RGB")
  
    # Build conversation format
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
 
 
 # Apply chat template properly
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
 
    # Try parsing JSON
    try:
        json_start = response.index("{")
        parsed = json.loads(response[json_start:])
    except:
        parsed = {
            "error": "Invalid JSON generated",
            "raw_output": response
        }
 
    return parsed
 
 
# ----------------------------------------
# 4️⃣ Run Worker (Standalone Test)
# ----------------------------------------
 
if __name__ == "__main__":
 
    image_path = "/home/debian/workspace/Bharath_Selvamani/Test/u-shaped-modular-kitchen-1000x1000.jpg"  # replace with your image
 
    result = analyze_image_for_risk(image_path)
 
    print("\nRisk Analysis Result:\n")
    print(json.dumps(result, indent=4))