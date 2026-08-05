from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / 'data' / 'raw' / 'PDF_RAW'
PROCESSED_DIR = ROOT / 'data' / 'processed' / 'PDF_PROCESSED'
INDEX_DIR = ROOT / 'data' / 'indexes'
METADATA_DIR = ROOT / 'data' / 'metadata'
REVIEW_QUEUE = ROOT / 'review_queue.json'


def ensure_dirs():
    for path in [RAW_DIR, PROCESSED_DIR, INDEX_DIR, METADATA_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def main():
    ensure_dirs()
    print(f'Input folder: {RAW_DIR}')
    print(f'Output folder: {PROCESSED_DIR}')
    print('Pipeline stub ready.')


if __name__ == '__main__':
    main()
