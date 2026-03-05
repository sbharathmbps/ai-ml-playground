import os
import json
import argparse
import torch
from PIL import Image, ImageDraw, ImageFont
from transformers import AutoProcessor, AutoModelForCausalLM

# ============================================================
# 1) Environment Setup
# ============================================================

HF_BASE = os.getenv("HF_HOME", "/opt/hf-cache")
os.environ.setdefault("HF_HOME", HF_BASE)
os.environ.setdefault("HF_HUB_CACHE", f"{HF_BASE}/hub")
os.environ.setdefault("TRANSFORMERS_CACHE", f"{HF_BASE}/transformers")
os.environ.setdefault("HF_DATASETS_CACHE", f"{HF_BASE}/datasets")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

FLORENCE_MODEL_ID = "microsoft/Florence-2-large"
FLORENCE_REVISION = os.getenv("FLORENCE_REVISION")

device = "cuda" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if device == "cuda" else torch.float32

# ============================================================
# 2) Load Florence-2
# ============================================================

print("Loading Florence-2...")

from_pretrained_kwargs = {
    "trust_remote_code": True,
    "local_files_only": os.getenv("HF_HUB_OFFLINE", "1") == "1",
}
if FLORENCE_REVISION:
    from_pretrained_kwargs["revision"] = FLORENCE_REVISION

processor = AutoProcessor.from_pretrained(
    FLORENCE_MODEL_ID,
    **from_pretrained_kwargs,
)

model = AutoModelForCausalLM.from_pretrained(
    FLORENCE_MODEL_ID,
    torch_dtype=torch_dtype,
    **from_pretrained_kwargs,
).to(device)

model.eval()

print("Florence-2 loaded")

# ============================================================
# 3) Ground Single Risk Sentence
# ============================================================

def ground_risk_sentence(image: Image.Image, risk_sentence: str):
    task = "<CAPTION_TO_PHRASE_GROUNDING>"
    prompt = task + risk_sentence

    inputs = processor(
        text=prompt,
        images=image,
        return_tensors="pt"
    ).to(device)
    inputs["pixel_values"] = inputs["pixel_values"].to(torch_dtype)

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


# ============================================================
# 4) Draw Bounding Boxes
# ============================================================

def draw_results(image: Image.Image, results: list):
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16
        )
    except OSError:
        font = ImageFont.load_default()

    colors = [
        "#FF0000", "#FFA500", "#00BFFF",
        "#00FF00", "#FF69B4", "#FFD700"
    ]

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


# ============================================================
# 5) Main Risk Grounding Pipeline
# ============================================================

def run_florence_risk_pipeline(
        image_path: str,
        risk_factors: list,
        output_image_path: str
):
    image = Image.open(image_path).convert("RGB")

    all_results = []

    print("\nStarting grounding...\n")

    for idx, sentence in enumerate(risk_factors):
        print(f"[{idx+1}/{len(risk_factors)}] Grounding:")
        print(f"   -> {sentence}")

        result = ground_risk_sentence(image, sentence)

        if result["bboxes"]:
            print(f"   Found {len(result['bboxes'])} bbox(es)")
        else:
            print("   No bbox found")

        all_results.append(result)

    os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
    annotated = draw_results(image.copy(), all_results)
    annotated.save(output_image_path)

    print(f"\nSaved annotated image to: {output_image_path}")

    return {
        "risk_factor_count": len(risk_factors),
        "grounded_results": all_results,
        "output_image": output_image_path
    }


# ============================================================
# 6) Example / Docker Runtime Inputs
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-path", dest="image_path")
    parser.add_argument("--output-image", dest="output_image")
    parser.add_argument("--risk-factors-json", dest="risk_factors_json")
    parser.add_argument("--output-json", dest="output_json")
    args = parser.parse_args()

    IMAGE_PATH = (
        args.image_path
        or os.getenv("IMAGE_PATH")
        or "/data/input/u-shaped-modular-kitchen-1000x1000.jpg"
    )
    OUTPUT_PATH = (
        args.output_image
        or os.getenv("OUTPUT_PATH")
        or "/data/output/florence_output.jpg"
    )

    risk_factors_json = args.risk_factors_json or os.getenv("RISK_FACTORS_JSON")
    if risk_factors_json:
        RISK_FACTORS = json.loads(risk_factors_json)
    else:
        parser.error("Missing risk factors. Provide --risk-factors-json or RISK_FACTORS_JSON.")

    final_output = run_florence_risk_pipeline(
        IMAGE_PATH,
        RISK_FACTORS,
        OUTPUT_PATH
    )

    output_json_path = args.output_json or os.getenv("OUTPUT_JSON")
    if output_json_path:
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=2)

    print("\nFinal Structured Output:")
    print(json.dumps(final_output, indent=2))
