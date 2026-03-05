import os
HF_BASE = os.getenv("HF_HOME", "/opt/hf-cache")

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# ================= IMPORTS =================

import json
import torch
import argparse
import logging
from PIL import Image, ImageDraw, ImageFont
from transformers import AutoProcessor, AutoModelForCausalLM
logging.basicConfig(level=logging.INFO)


# ================= MODEL CONFIG =================

FLORENCE_MODEL_ID = "microsoft/Florence-2-large"

device = "cuda" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if device == "cuda" else torch.float32

# ================= LOAD MODEL =================

logging.info("Loading Florence-2..")

processor = AutoProcessor.from_pretrained(
    FLORENCE_MODEL_ID,
    trust_remote_code=True,
    revision="21a599d414c4d928c9032694c424fb94458e3594"
)

model = AutoModelForCausalLM.from_pretrained(
    FLORENCE_MODEL_ID,
    torch_dtype=torch_dtype,
    trust_remote_code=True,
    revision="21a599d414c4d928c9032694c424fb94458e3594"
).to(device)

model.eval()

logging.info("Florence-2 loaded")

# ================= GROUND RISK SENTENCE =================

def ground_risk_sentence(image: Image.Image, risk_sentence: str):

    task = "<CAPTION_TO_PHRASE_GROUNDING>"
    prompt = task + risk_sentence

    inputs = processor(
        text=prompt,
        images=image,
        return_tensors="pt"
    ).to(device, torch_dtype)

    with torch.no_grad():
        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            num_beams=3,
            do_sample=False
        )

    generated_text = processor.batch_decode(
        generated_ids,
        skip_special_tokens=False
    )[0]

    parsed = processor.post_process_generation(
        generated_text,
        task=task,
        image_size=(image.width, image.height)
    )

    result = parsed.get(task, {"bboxes": [], "labels": []})

    return {
        "sentence": risk_sentence,
        "bboxes": result.get("bboxes", []),
        "labels": result.get("labels", [])
    }


# ================= DRAW BBOX =================

def draw_results(image: Image.Image, results: list):

    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except:
        font = ImageFont.load_default()

    colors = ["#FF0000", "#FFA500", "#00BFFF", "#00FF00", "#FF69B4", "#FFD700"]

    for idx, res in enumerate(results):

        color = colors[idx % len(colors)]
        bboxes = res["bboxes"]
        labels = res["labels"]

        for i, bbox in enumerate(bboxes):

            x1, y1, x2, y2 = bbox
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

            label = labels[i] if i < len(labels) else res["sentence"]

            text_bg_x2 = x1 + len(label) * 8

            draw.rectangle([x1, y1 - 20, text_bg_x2, y1], fill=color)
            draw.text((x1 + 2, y1 - 18), label, fill="black", font=font)

    return image


# ================= PIPELINE =================

def run_florence_risk_pipeline(image_path, risk_factors, output_image_path):

    image = Image.open(image_path).convert("RGB")

    all_results = []

    logging.info("\n Starting grounding...\n")

    for idx, sentence in enumerate(risk_factors):

        logging.info(f"{sentence}")

        result = ground_risk_sentence(image, sentence)

        if result["bboxes"]:
            logging.info(f"Found {len(result['bboxes'])} bbox(es)")
        else:
            logging.info("No bbox found")

        all_results.append(result)

    annotated = draw_results(image.copy(), all_results)
    annotated.save(output_image_path)

    logging.info(f"\n Saved annotated image to: {output_image_path}")

    return {
        "risk_factor_count": len(risk_factors),
        "grounded_results": all_results,
        "output_image": output_image_path
    }


# ================= CLI MAIN (ARGO COMPATIBLE) =================

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Florence Risk Grounding")

    parser.add_argument("--src", help="Input image path")
    parser.add_argument("--risk_json", help="JSON file containing risk factors")
    parser.add_argument("--output", help="Output annotated image path")
    parser.add_argument("--config", help="Optional config file", default=None)

    parser.add_argument("--workflow_name", default="workflow")
    parser.add_argument("--folder_name", default="folder")

    args = parser.parse_args()

    IMAGE_PATH = args.src
    RISK_JSON = args.risk_json
    OUTPUT_PATH = args.output

    workflow_name = args.workflow_name
    folder_name = args.folder_name

    # ================= LOAD RISK FACTORS =================

    if RISK_JSON:
        with open(RISK_JSON, "r") as f:
            risk_factors = json.load(f)
    else:
        raise ValueError("Risk JSON file required")

    # ================= RUN PIPELINE =================

    final_output = run_florence_risk_pipeline(IMAGE_PATH,risk_factors,OUTPUT_PATH)

    logging.info("\n Final Structured Output:")
    logging.info(json.dumps(final_output, indent=2))



# [
#     "Newspaper and other debris on stovetop and counter near heat source",
#     "Gas stove with visible gas hose exposed and not secured",
#     "Cabinet shelves holding metal containers and other items without proper spacing or securing",
#     "Kitchen counter cluttered with items that could be tripping hazards or interfere with safe operation"
# ]


# docker run --rm \
# -v /mnt/data/ml-platform/containers/risk_warning_system/sentenced_object_detection:/input \
# -v /mnt/data/ml-platform/containers/risk_warning_system/sentenced_object_detection/output:/output \
# sentenced-obj-det-cli-input:python-3.10-slim \
# --src /input/u-shaped-modular-kitchen-1000x1000.jpg \
# --risk_json /input/risk_factors.json \
# --output /output/florence_output.jpg \
# --workflow_name vlm_pipeline \
# --folder_name workorder_1234