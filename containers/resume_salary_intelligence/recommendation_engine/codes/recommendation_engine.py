import os
import json
import argparse
import logging
from pathlib import Path

import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from database_entry import (
    get_local_session,
    get_job_descriptions,
    update_recommended_jobs,
)


logging.basicConfig(level=logging.INFO)

# Keep core model usage unchanged
model = SentenceTransformer(
    "perplexity-ai/pplx-embed-v1-0.6B",
    trust_remote_code=True,
)


def read_resume_text(src_dir: str) -> str:
    src_path = Path(src_dir)
    files = sorted([p for p in src_path.iterdir() if p.is_file()])

    if not files:
        raise FileNotFoundError(f"No input file found in {src_dir}")

    file_path = files[0]

    if file_path.suffix.lower() == ".pdf":
        reader = PdfReader(str(file_path))
        page_text = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(page_text).strip()
        if not text:
            raise ValueError(f"No extractable text found in PDF: {file_path}")
        return text

    for encoding in ("utf-8", "latin-1"):
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Unable to decode input file: {file_path}")


def rank_jobs(resume_text: str, jobs: list[tuple[str, str]], top_k: int = 6):
    if not jobs:
        return []

    job_ids = [str(job_id) for job_id, _ in jobs]
    job_descriptions = [description or "" for _, description in jobs]

    resume_embedding = model.encode(resume_text)
    job_embeddings = model.encode(job_descriptions)

    scores = cosine_similarity([resume_embedding], job_embeddings)[0]

    ranked_idx = np.argsort(scores)[::-1][:top_k]

    ranked = []
    for idx in ranked_idx:
        ranked.append(
            {
                "job_id": job_ids[idx],
                "description": job_descriptions[idx],
                "score": float(scores[idx]),
            }
        )

    return ranked


def build_recommended_jobs_payload(ranked_jobs: list[dict]) -> dict:
    # Keep rank-keyed output, but include both job_id and description for apply flow.
    return {
        str(i + 1): {
            "job_id": item["job_id"],
            "description": item["description"],
            "score": item["score"],
        }
        for i, item in enumerate(ranked_jobs)
    }


# def write_output(dest_dir: str, output: dict) -> None:
#     os.makedirs(dest_dir, exist_ok=True)
#     out_file = Path(dest_dir) / "recommendation_output.json"
#     out_file.write_text(json.dumps(output, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resume Job Recommendation")
    parser.add_argument("--src", help="Input resume directory")
    parser.add_argument("--dest", help="Output path")
    parser.add_argument("--config", help="Optional config file", default=None)
    parser.add_argument("--workflow_name", default="workflow")
    parser.add_argument("--folder_name", default="folder")

    args = parser.parse_args()

    resume_text = read_resume_text(args.src)

    SessionLocal, engine = get_local_session()
    jobs = get_job_descriptions(SessionLocal)

    ranked_jobs = rank_jobs(resume_text, jobs, top_k=6)
    recommended_jobs = build_recommended_jobs_payload(ranked_jobs)

    final_output = {
        "recommended_jobs": recommended_jobs,
        "ranked_jobs": ranked_jobs,
        "total_jobs": len(jobs),
    }

    # write_output(args.dest, final_output)
    update_recommended_jobs(SessionLocal, args.folder_name, recommended_jobs)

    logging.info("Final Structured Output:")
    logging.info(json.dumps(final_output, indent=2))
