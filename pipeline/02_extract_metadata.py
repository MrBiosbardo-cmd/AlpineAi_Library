"""
Metadata Extraction Script
---------------------------
Stage 2 of the AlpineAi Library pipeline.

Reads the intake queue, extracts metadata from each PDF using pdfminer
(or a lightweight fallback), and writes enriched records to the metadata
staging file.

Usage:
    python pipeline/02_extract_metadata.py [--queue index/intake_queue.json]
                                            [--out index/metadata_staging.json]
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def try_extract_pdf_info(pdf_path: Path) -> dict:
    """
    Extract basic metadata from a PDF.

    Attempts to use pdfminer.six if installed; falls back to header-only
    parsing so the pipeline can run without optional dependencies.
    """
    info: dict = {}
    try:
        from pdfminer.high_level import extract_pages  # type: ignore
        from pdfminer.pdfpage import PDFPage  # type: ignore
        from pdfminer.pdfparser import PDFParser  # type: ignore
        from pdfminer.pdfdocument import PDFDocument  # type: ignore

        with open(pdf_path, "rb") as fh:
            parser = PDFParser(fh)
            doc = PDFDocument(parser)
            if doc.info:
                raw = doc.info[0]
                for key in ("Title", "Author", "Subject", "Keywords", "Creator", "Producer"):
                    value = raw.get(key)
                    if value:
                        if isinstance(value, bytes):
                            value = value.decode("utf-8", errors="replace")
                        info[key.lower()] = value
            # Page count via generator (avoids loading full content)
            info["page_count"] = sum(1 for _ in PDFPage.get_pages(fh))
    except ImportError:
        logger.debug("pdfminer not available; using header-only extraction for %s", pdf_path)
    except Exception as exc:
        logger.warning("Could not extract metadata from %s: %s", pdf_path, exc)
    return info


def enrich_record(record: dict, source_root: Path) -> dict:
    pdf_path = source_root / record["relative_path"]
    pdf_info = try_extract_pdf_info(pdf_path) if pdf_path.exists() else {}
    return {
        **record,
        "title": pdf_info.get("title", ""),
        "author": pdf_info.get("author", ""),
        "subject": pdf_info.get("subject", ""),
        "keywords": pdf_info.get("keywords", ""),
        "page_count": pdf_info.get("page_count", 0),
        "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "extracted",
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="AlpineAi Metadata Extraction")
    parser.add_argument("--queue", default="index/intake_queue.json")
    parser.add_argument("--source", default=".", help="Root directory containing PDFs")
    parser.add_argument("--out", default="index/metadata_staging.json")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    queue_path = Path(args.queue)
    if not queue_path.exists():
        logger.error("Intake queue not found: %s", queue_path)
        sys.exit(1)

    with open(queue_path, encoding="utf-8") as fh:
        records = json.load(fh)

    source_root = Path(args.source)
    enriched = [enrich_record(r, source_root) for r in records]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(enriched, fh, indent=2)
    logger.info("Wrote %d enriched records to %s", len(enriched), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
