FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf-cache \
    HF_HUB_CACHE=/opt/hf-cache/hub \
    TRANSFORMERS_CACHE=/opt/hf-cache/transformers \
    HF_DATASETS_CACHE=/opt/hf-cache/datasets \
    FLORENCE_MODEL_ID=microsoft/Florence-2-large \
    FLORENCE_REVISION=21a599d414c4d928c9032694c424fb94458e3594

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && pip install -r /app/requirements.txt

COPY sentence_to_bbox.py /app/sentence_to_bbox.py

# Download and cache model artifacts inside the image at build time.
RUN python - <<'PY'
import os
from transformers import AutoProcessor, AutoModelForCausalLM

model_id = os.environ["FLORENCE_MODEL_ID"]
revision = os.environ.get("FLORENCE_REVISION")
kwargs = {"trust_remote_code": True}
if revision:
    kwargs["revision"] = revision

AutoProcessor.from_pretrained(model_id, **kwargs)
AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
print("Model cached in image.")
PY

# Runtime should use cached model and avoid network calls.
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

ENTRYPOINT ["python", "/app/sentence_to_bbox.py"]
