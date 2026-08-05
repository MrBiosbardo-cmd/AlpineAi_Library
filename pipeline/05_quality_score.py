"""
Quality Scoring Script
-----------------------
Stage 5 of the AlpineAi Library pipeline.

Reads the full library index and assigns a quality score (0–100) to each
record based on completeness of metadata and document characteristics.

Scoring rubric:
  +30  title present and non-trivial (>= 5 chars)
  +20  author present
  +15  subject or keywords present
  +20  page_count > 0
  +15  page_count >= 10 (substantive document)

Updated index is written back to index/library_index.json and a score
summary CSV is written to index/quality_scores.csv.

Usage:
    python pipeline/05_quality_score.py [--index index/library_index.json]
"""

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def compute_score(record: dict) -> int:
    score = 0
    title = str(record.get("title") or "")
    if len(title) >= 5:
        score += 30
    if record.get("author"):
        score += 20
    if record.get("subject") or record.get("keywords"):
        score += 15
    page_count = int(record.get("page_count") or 0)
    if page_count > 0:
        score += 20
    if page_count >= 10:
        score += 15
    return score


def score_records(records: list[dict]) -> list[dict]:
    return [{**r, "quality_score": compute_score(r)} for r in records]


def write_csv_summary(records: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["filename", "title", "author", "page_count", "quality_score"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    logger.info("Wrote quality summary to %s", path)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="AlpineAi Quality Scoring")
    parser.add_argument("--index", default="index/library_index.json")
    parser.add_argument("--csv-out", default="index/quality_scores.csv")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    index_path = Path(args.index)
    if not index_path.exists():
        logger.error("Index not found: %s", index_path)
        sys.exit(1)

    with open(index_path, encoding="utf-8") as fh:
        index = json.load(fh)

    scored = score_records(index.get("records", []))
    index["records"] = scored

    with open(index_path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2)
    logger.info("Updated index with quality scores: %s", index_path)

    write_csv_summary(scored, Path(args.csv_out))

    avg = sum(r["quality_score"] for r in scored) / len(scored) if scored else 0
    logger.info("Average quality score: %.1f / 100", avg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
