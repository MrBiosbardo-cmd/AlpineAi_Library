# AlpineAi_Library

Pipeline-only rebuild of the Alpine AI research library.

## Goal
Drop PDFs into `data/raw/PDF_RAW/`, process them, and keep only the pipeline, indexes, and small metadata in Git.

## Folder contract
- `data/raw/PDF_RAW/` — input PDFs
- `data/processed/PDF_PROCESSED/` — processed outputs and regenerated artifacts
- `scripts/` — ingestion, review, and maintenance scripts
- `chat_interface/` — chat UI and server
- `README.md` — this guide

## Workflow
1. Put a PDF into `data/raw/PDF_RAW/`.
2. Run the import pipeline.
3. The pipeline generates processed outputs in `data/processed/PDF_PROCESSED/`.
4. Commit only code, config, indexes, and metadata.
5. Keep PDFs and large derived data out of Git.

## Why this structure
This repo is intentionally lean so the pipeline can improve over time without carrying archive baggage or Windows path-limit issues.
