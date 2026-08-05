# AlpineAi Library

A **lean, pipeline-centred** repository for managing a PDF document library.

The repository stores the **processing pipeline** only.  
PDF files, raw archives, and large binary output are excluded from Git and treated as rebuildable inputs.

---

## Repository layout

```
AlpineAi_Library/
├── pipeline/               # Five-stage processing pipeline
│   ├── 01_intake.py            # Stage 1 – scan source dir, build intake queue
│   ├── 02_extract_metadata.py  # Stage 2 – extract PDF metadata
│   ├── 03_review_queue.py      # Stage 3 – flag records for manual review
│   ├── 04_generate_index.py    # Stage 4 – generate searchable index files
│   └── 05_quality_score.py     # Stage 5 – score records on metadata completeness
├── config/
│   └── pipeline.yaml       # Pipeline configuration
├── metadata/
│   └── document_schema.json  # JSON Schema for document records
├── index/                  # Generated index files (small ones are versioned)
│   ├── intake_queue.json        # (gitignored for large runs)
│   ├── library_index_slim.json  # Slim index – committed when small
│   └── quality_scores.csv       # Score summary
└── .gitignore              # Excludes *.pdf and large generated artefacts
```

---

## Pipeline stages

| # | Script | Input | Output |
|---|--------|-------|--------|
| 1 | `01_intake.py` | Source PDF directory | `index/intake_queue.json` |
| 2 | `02_extract_metadata.py` | `intake_queue.json` | `index/metadata_staging.json` |
| 3 | `03_review_queue.py` | `metadata_staging.json` | `index/review_queue.json`, `index/review_approved.json` |
| 4 | `04_generate_index.py` | `review_approved.json` | `index/library_index.json`, `index/library_index_slim.json` |
| 5 | `05_quality_score.py` | `library_index.json` | Updated `library_index.json`, `index/quality_scores.csv` |

---

## Quickstart

```bash
# 1. Point the pipeline at your PDF archive (outside this repo)
export ALPINEAI_SOURCE_DIR=/path/to/your/pdfs

# 2. Run each stage in order
python pipeline/01_intake.py --source "$ALPINEAI_SOURCE_DIR"
python pipeline/02_extract_metadata.py
python pipeline/03_review_queue.py
python pipeline/04_generate_index.py
python pipeline/05_quality_score.py
```

Optional dependencies (recommended):

```bash
pip install pdfminer.six pyyaml
```

---

## What stays in Git

| Included | Excluded |
|---|---|
| Pipeline scripts | *.pdf files |
| Config (`config/pipeline.yaml`) | Raw / processed PDF archives |
| Metadata schema | Large generated index files (`index/full_*.json`) |
| Slim index (when small) | `logs/` |
| `quality_scores.csv` | `.env` secrets |

PDFs are treated as **rebuildable inputs**.  
Re-run the pipeline against the external PDF archive at any time to regenerate the index.

---

## Design principles

1. **Store the process, not the dump** – only source code, config, and small derived artefacts live in Git.
2. **Reproducible** – given the same PDF archive, the pipeline produces the same index.
3. **Incremental** – each stage reads and writes well-defined JSON files, so individual stages can be re-run independently.
4. **Learn from errors** – quality scores and review flags surface metadata problems for correction before the next ingest cycle.