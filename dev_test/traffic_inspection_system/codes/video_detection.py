import os
HF_BASE = "/mnt/data/huggingface"

os.environ["HF_HOME"] = HF_BASE
os.environ["HF_HUB_CACHE"] = f"{HF_BASE}/hub"
os.environ["TRANSFORMERS_CACHE"] = f"{HF_BASE}/transformers"
os.environ["HF_DATASETS_CACHE"] = f"{HF_BASE}/datasets"

os.environ["TMPDIR"] = f"{HF_BASE}/tmp"
os.environ["TEMP"] = f"{HF_BASE}/tmp"
os.environ["TMP"] = f"{HF_BASE}/tmp"

import re
import gc
import cv2
import json
import torch
import argparse
import numpy as np
import pandas as pd
from PIL import Image
import logging
from database_entry import add_data, get_local_session, add_image_classification, add_image_quality, get_local_session_uvision, get_image_quality
from transformers import pipeline
logging.basicConfig(level=logging.INFO)

# ================= HF SETTINGS =================

os.environ["HF_HOME"] = HF_BASE
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_TOKEN"] = os.getenv('HF_TOKEN')

# ==================== CONFIG ====================

MODEL_ID = "google/siglip-so400m-patch14-384"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Reduce fragmentation
os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"

# ================== LOAD MODEL ==================

logging.info("Loading model...")

classifier = pipeline(task="zero-shot-image-classification", model=MODEL_ID, device=DEVICE)

logging.info("Model loaded successfully")

# ==================== PROMPT ====================

ASSET_LABELS = [
    "motorcycle rider wearing helmet",
    "motorcycle rider without helmet"
]

LABEL_TO_ASSET = {
    ASSET_LABELS[0]: "HELMET",
    ASSET_LABELS[1]: "NO_HELMET"
}
    
# ============== CLASSIFICATION FUNCTION ==============

def classify_image(image):

    outputs = classifier(image, candidate_labels=ASSET_LABELS)
    top = outputs[0]

    return {
        "helmet_status": LABEL_TO_ASSET[top["label"]],
        "confidence": round(top["score"] * 100, 2)
    }

# ===================== MAIN LOOP =====================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="My CLI script")
    parser.add_argument("--src", help="Path to the input file")
    parser.add_argument("--device",  help="device to run code ('cuda' for gpu, default is 'cpu')", default='cpu')
    parser.add_argument("--config",  help="Path to the config file")

    parser.add_argument("--workflow_name",  help="workflow name", default="workflow")
    parser.add_argument("--folder_name",  help="folder name", default="folder")
    parser.add_argument("--start_msg",   help="Array as a string containing names of asset to do Started entry in database jobstatus, e.g-> '[]', '[\"pole\"]'",default='[]')
    parser.add_argument("--end_msg",   help="Array as a string containing names of asset to do Completed entry in database jobstatus, e.g-> '[]', '[\"pole\"]'",default='[]')

    args = parser.parse_args()
    IMAGE_DIR = args.src 
    device = args.device
    config_path = args.config

    workflow_name = args.workflow_name 
    folder_name = args.folder_name
    start_msg = json.loads(args.start_msg) 
    end_msg = json.loads(args.end_msg) 

    with open(config_path, 'r') as file:
       conf_data = json.load(file)

    if  conf_data.get('DEVICE'):
        conf_data['DEVICE'] = device

    conf_data['project_name'] = folder_name

    if device != "cuda":
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

    workorder_id = int(folder_name[:4])
    detection_list = []
    
    SessionLocalUvision, engineUvision = get_local_session_uvision()
    image_id_list = get_image_quality(SessionLocalUvision, workorder_id)
    logging.info(f"image_id_list: {image_id_list}")

    SessionLocal, engine = get_local_session()

    if start_msg:
        for asset in start_msg:
            add_data(SessionLocal=SessionLocal, project=folder_name , job_name=workflow_name, status=f'{asset.replace("_"," ").title()} Started !')

    try:        
        for row in image_id_list:
            if row["image_quality"] in ["BLUR", "LOW_LIGHT/DARK"]:
                continue

            image_name = row["raw_image_name"]
            if not (image_name.split(".")[-1].lower() in ["jpg", "png", "jpeg"]):
                logging.info(f"Extension Not Allowed : Skipping {image_name}....")
                continue

            image_path = os.path.join(IMAGE_DIR, image_name)
            image = Image.open(image_path).convert("RGB")
            output = classify_image(image)

            detection_list.append({
                "unique_id": row["unique_id"],
                "helmet_status": str(output["helmet_status"]),                            
                "confidence": output["confidence"]                           
                }) 
            
        if detection_list:
            logging.info(f"detection_list: {detection_list}")    
            add_image_classification(SessionLocal=SessionLocalUvision, detection_list=detection_list)               


        if end_msg:
            for asset in end_msg:
                add_data(SessionLocal=SessionLocal, project=folder_name , job_name=workflow_name, status=f'{asset.replace("_"," ").title()} Completed !')

    except Exception as e: 
        logging.error(str(e))
        if end_msg:
            for asset in end_msg:
                add_data(SessionLocal=SessionLocal, project=folder_name , job_name=workflow_name, status=f'{asset.replace("_"," ").title()} Completed !')

