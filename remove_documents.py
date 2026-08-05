#!/usr/bin/env python3
"""
Remove specific documents from the Alpine AI Research Library.
Cleans up: Master_Index.csv, Manual_Review_Queue.csv, PDF files, and Markdown notes.
"""

import csv
import shutil
import sys
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Documents to remove
REMOVE_IDS = {
    "ALP-2026-0002",
    "ALP-2026-0005",
    "ALP-2026-0022",
    "ALP-2026-0023",
    "ALP-2026-0026",
    "ALP-2026-0027",
    "ALP-2026-0030",
    "ALP-2026-0032",
    "ALP-2026-0037",
    "ALP-2026-0039",
    "ALP-2026-0040",
    "ALP-2026-0042",
    "ALP-2026-0043",
    "ALP-2026-0047",
    "ALP-2026-0054",
    "ALP-2026-0060",
}

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "00_Library_Index" / "Master_Index.csv"
MANUAL_REVIEW_FILE = BASE_DIR / "00_Library_Index" / "Manual_Review_Queue.csv"
PDF_PROCESSED_ROOT = BASE_DIR / "PDF Processed"
PDF_RAW_ROOT = BASE_DIR / "PDF RAW"
NOTES_ROOT = BASE_DIR / "Notes"

def main():
    print(f"Removing {len(REMOVE_IDS)} documents from Alpine AI Research Library\n")
    
    # Read Master_Index to find PDFs and notes paths
    removed_data = {}
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Paper_ID") in REMOVE_IDS:
                    removed_data[row["Paper_ID"]] = {
                        "title": row.get("Title", ""),
                        "pdf": row.get("PDF_Filename", ""),
                        "notes": row.get("Obsidian_Path", ""),
                    }
    
    # 1. Remove PDFs from PDF Processed and PDF RAW
    pdf_removed = 0
    for paper_id, data in removed_data.items():
        pdf_rel = data.get("pdf", "")
        if pdf_rel:
            # Try PDF Processed
            pdf_path = PDF_PROCESSED_ROOT / pdf_rel
            if pdf_path.exists():
                pdf_path.unlink()
                print(f"[OK] Deleted PDF: {pdf_rel}")
                pdf_removed += 1
            
            # Try PDF RAW
            pdf_raw_path = PDF_RAW_ROOT / Path(pdf_rel).name
            if pdf_raw_path.exists():
                pdf_raw_path.unlink()
                print(f"[OK] Deleted PDF (RAW): {pdf_raw_path.name}")
                pdf_removed += 1
    
    # 2. Remove markdown notes
    notes_removed = 0
    for paper_id, data in removed_data.items():
        notes_rel = data.get("notes", "")
        if notes_rel:
            notes_path = NOTES_ROOT / notes_rel
            if notes_path.exists():
                notes_path.unlink()
                print(f"[OK] Deleted notes: {notes_rel}")
                notes_removed += 1
    
    # 3. Remove from Master_Index.csv
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            remaining_rows = [row for row in reader if row.get("Paper_ID") not in REMOVE_IDS]
        
        with open(INDEX_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(remaining_rows)
        
        print(f"\n[OK] Updated Master_Index.csv: removed {len(removed_data)} rows")
    
    # 4. Remove from Manual_Review_Queue.csv
    if MANUAL_REVIEW_FILE.exists():
        with open(MANUAL_REVIEW_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            remaining_review = [row for row in reader if row.get("Paper_ID") not in REMOVE_IDS]
        
        removed_from_queue = len(remaining_review)
        with open(MANUAL_REVIEW_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(remaining_review)
        
        print(f"[OK] Updated Manual_Review_Queue.csv")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Documents removed: {len(removed_data)}")
    print(f"  PDFs deleted: {pdf_removed}")
    print(f"  Markdown notes deleted: {notes_removed}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
