"""
Index Generation Script
------------------------
Stage 4 of the AlpineAi Library pipeline.

Reads approved records and builds the searchable library index:

  - index/library_index.json : full index with all approved records
  - index/library_index_slim.json : lightweight index (title, author, sha256, page_count)

Usage:
    python pipeline/04_generate_index.py [--approved index/review_approved.json]
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SLIM_FIELDS = {"filename", "title", "author", "sha256", "page_count", "quality_score"}


def build_index(records: list[dict]) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_records": len(records),
        "records": records,
    }


def build_slim_index(records: list[dict]) -> dict:
    slim = [{k: r.get(k, "") for k in SLIM_FIELDS} for r in records]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_records": len(slim),
        "records": slim,
    }


def write_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    logger.info("Wrote %s (%d bytes)", path, path.stat().st_size)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="AlpineAi Index Generation")
    parser.add_argument("--approved", default="index/review_approved.json")
    parser.add_argument("--full-out", default="index/library_index.json")
    parser.add_argument("--slim-out", default="index/library_index_slim.json")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    approved_path = Path(args.approved)
    if not approved_path.exists():
        logger.error("Approved records file not found: %s", approved_path)
        sys.exit(1)

    with open(approved_path, encoding="utf-8") as fh:
        records = json.load(fh)

    write_json(build_index(records), Path(args.full_out))
    write_json(build_slim_index(records), Path(args.slim_out))
    logger.info("Index generation complete (%d records)", len(records))
    return 0


if __name__ == "__main__":
    sys.exit(main())
