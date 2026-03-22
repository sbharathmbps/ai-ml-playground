import cv2
import numpy as np
from ultralytics import YOLO

# -----------------------------
# CONFIG
# -----------------------------
MODEL_PATH = "/mnt/data/models/model_yolo/yolov8n.pt"
VIDEO_PATH = "/mnt/data/inputs/traffic_video/280583726_main_xxl.mp4"
OUTPUT_PATH = "/mnt/data/inputs/traffic_video/output/280584058_main_xxl.mp4"

CONF_THRESHOLD = 0.1

# COCO class IDs
PERSON_ID = 0
BICYCLE_ID = 1
MOTORCYCLE_ID = 3

# -----------------------------
# LOAD MODEL
# -----------------------------
model = YOLO(MODEL_PATH)

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def center(box):
    return ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2)


def horizontal_overlap(p_box, b_box):
    px1, _, px2, _ = p_box
    bx1, _, bx2, _ = b_box

    overlap = max(0, min(px2, bx2) - max(px1, bx1))
    p_width = px2 - px1

    return overlap / (p_width + 1e-6)


def is_valid_pair(p_box, b_box):
    px1, py1, px2, py2 = p_box
    bx1, by1, bx2, by2 = b_box

    pcx, pcy = center(p_box)
    bcx, bcy = center(b_box)

    # -----------------------------
    # 1. Horizontal center alignment (PRIMARY SIGNAL)
    # -----------------------------
    x_diff = abs(pcx - bcx)
    max_width = max(px2 - px1, bx2 - bx1)

    x_aligned = x_diff < (0.6 * max_width)

    # -----------------------------
    # 2. Vertical relationship
    # -----------------------------
    # Person should be above or slightly inside bike region
    vertical_ok = (py2 < by2 + 80)

    # -----------------------------
    # 3. Adaptive distance threshold
    # -----------------------------
    dist = np.sqrt((pcx - bcx) ** 2 + (pcy - bcy) ** 2)

    # scale distance based on object size
    size_ref = max(px2 - px1, py2 - py1, bx2 - bx1, by2 - by1)
    adaptive_dist = 1.5 * size_ref

    dist_ok = dist < adaptive_dist

    # -----------------------------
    # 4. Soft horizontal overlap (NOT strict)
    # -----------------------------
    overlap_ratio = horizontal_overlap(p_box, b_box)
    overlap_ok = overlap_ratio > 0.1   # reduced from 0.3 → 0.1

    # -----------------------------
    # FINAL DECISION
    # -----------------------------
    return (
        x_aligned and
        vertical_ok and
        dist_ok and
        (overlap_ok or x_aligned)
    )


def merge_boxes(box1, box2):
    return [
        min(box1[0], box2[0]),
        min(box1[1], box2[1]),
        max(box1[2], box2[2]),
        max(box1[3], box2[3])
    ]


# -----------------------------
# VIDEO SETUP
# -----------------------------
cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    raise Exception("Error opening video file")

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
fps = int(cap.get(cv2.CAP_PROP_FPS))
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

out = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (w, h))

# -----------------------------
# PROCESS VIDEO
# -----------------------------
frame_count = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1

    # Resize for faster CPU inference
    frame_resized = cv2.resize(frame, (640, 384))

    # Run YOLO
    results = model(frame_resized, device="cpu", conf=CONF_THRESHOLD, verbose=False)[0]

    persons = []
    bikes = []

    # -----------------------------
    # COLLECT DETECTIONS
    # -----------------------------
    for box in results.boxes:
        cls = int(box.cls[0])
        xyxy = box.xyxy[0].cpu().numpy().astype(int)

        if cls == PERSON_ID:
            persons.append(xyxy)

        elif cls in [BICYCLE_ID, MOTORCYCLE_ID]:
            bikes.append(xyxy)

    # -----------------------------
    # MATCH PERSON + BIKE
    # -----------------------------
    merged_boxes = []
    used_bikes = set()

    for p_box in persons:
        best_match = None
        best_score = 0

        for i, b_box in enumerate(bikes):
            if i in used_bikes:
                continue

            if is_valid_pair(p_box, b_box):
                overlap = horizontal_overlap(p_box, b_box)

                if overlap > best_score:
                    best_score = overlap
                    best_match = i

        if best_match is not None:
            merged = merge_boxes(p_box, bikes[best_match])
            merged_boxes.append(merged)
            used_bikes.add(best_match)

    # -----------------------------
    # SCALE BACK TO ORIGINAL SIZE
    # -----------------------------
    scale_x = w / 640
    scale_y = h / 384

    # -----------------------------
    # DRAW OUTPUT
    # -----------------------------
    for m in merged_boxes:
        x1 = int(m[0] * scale_x)
        y1 = int(m[1] * scale_y)
        x2 = int(m[2] * scale_x)
        y2 = int(m[3] * scale_y)

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
        cv2.putText(frame, "Person+Bike",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 255, 0), 2)

    out.write(frame)

# -----------------------------
# CLEANUP
# -----------------------------
cap.release()
out.release()

print("✅ Processing complete. Saved to:", OUTPUT_PATH)

