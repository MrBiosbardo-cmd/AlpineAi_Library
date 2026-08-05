"""
Manual Review Queue
--------------------
Stage 3 of the AlpineAi Library pipeline.

Reads the metadata staging file, flags records that require human review
(e.g. missing title, zero page count, duplicate SHA-256), and writes two
output files:

  - index/review_queue.json   : records needing manual attention
  - index/review_approved.json: records that passed automated checks

Usage:
    python pipeline/03_review_queue.py [--staging index/metadata_staging.json]
                                        [--approve-all]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def flag_reasons(record: dict, seen_hashes: set) -> list[str]:
    reasons = []
    if not record.get("title"):
        reasons.append("missing_title")
    if record.get("page_count", 0) == 0:
        reasons.append("zero_page_count")
    sha = record.get("sha256", "")
    if sha in seen_hashes:
        reasons.append("duplicate_sha256")
    return reasons


def run_review(records: list[dict], approve_all: bool = False):
    seen_hashes: set = set()
    needs_review = []
    approved = []

    for record in records:
        reasons = flag_reasons(record, seen_hashes)
        seen_hashes.add(record.get("sha256", ""))

        if reasons and not approve_all:
            record = {**record, "review_flags": reasons, "status": "needs_review"}
            needs_review.append(record)
        else:
            record = {**record, "review_flags": [], "status": "approved"}
            approved.append(record)

    return needs_review, approved


def write_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="AlpineAi Manual Review Queue")
    parser.add_argument("--staging", default="index/metadata_staging.json")
    parser.add_argument("--review-out", default="index/review_queue.json")
    parser.add_argument("--approved-out", default="index/review_approved.json")
    parser.add_argument(
        "--approve-all",
        action="store_true",
        help="Automatically approve all records (useful for initial bulk import)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    staging_path = Path(args.staging)
    if not staging_path.exists():
        logger.error("Staging file not found: %s", staging_path)
        sys.exit(1)

    with open(staging_path, encoding="utf-8") as fh:
        records = json.load(fh)

    needs_review, approved = run_review(records, approve_all=args.approve_all)

    write_json(needs_review, Path(args.review_out))
    write_json(approved, Path(args.approved_out))

    logger.info(
        "Review complete: %d approved, %d flagged for review",
        len(approved),
        len(needs_review),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
