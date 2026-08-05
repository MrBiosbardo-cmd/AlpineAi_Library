"""
PDF Intake Script
-----------------
Stage 1 of the AlpineAi Library pipeline.

Scans a source directory for PDF files, validates them, and registers
each file in the intake queue for further processing.

Usage:
    python pipeline/01_intake.py --source /path/to/pdfs [--config config/pipeline.yaml]
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SUPPORTED_MIME = {"application/pdf"}


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_valid_pdf(path: Path) -> bool:
    """Return True if the file starts with the PDF magic bytes."""
    try:
        with open(path, "rb") as fh:
            return fh.read(4) == b"%PDF"
    except OSError:
        return False


def scan_source(source_dir: Path) -> list[dict]:
    """Walk source_dir and return intake records for every valid PDF."""
    records = []
    for pdf_path in sorted(source_dir.rglob("*.pdf")):
        if not is_valid_pdf(pdf_path):
            logger.warning("Skipping invalid PDF: %s", pdf_path)
            continue
        stat = pdf_path.stat()
        records.append(
            {
                "filename": pdf_path.name,
                "relative_path": str(pdf_path.relative_to(source_dir)),
                "size_bytes": stat.st_size,
                "sha256": sha256_of_file(pdf_path),
                "intake_timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "pending",
            }
        )
        logger.info("Queued: %s (%d bytes)", pdf_path.name, stat.st_size)
    return records


def write_queue(records: list[dict], queue_path: Path) -> None:
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with open(queue_path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2)
    logger.info("Wrote %d records to %s", len(records), queue_path)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="AlpineAi PDF Intake")
    parser.add_argument("--source", required=True, help="Directory containing source PDFs")
    parser.add_argument(
        "--queue",
        default="index/intake_queue.json",
        help="Path for the output queue file (default: index/intake_queue.json)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    source_dir = Path(args.source)
    if not source_dir.is_dir():
        logger.error("Source directory not found: %s", source_dir)
        sys.exit(1)

    records = scan_source(source_dir)
    if not records:
        logger.warning("No valid PDFs found in %s", source_dir)

    write_queue(records, Path(args.queue))
    return 0


if __name__ == "__main__":
    sys.exit(main())
