import json
from datetime import datetime

QUEUE_FILE = "review_queue.json"

def load_queue():
    with open(QUEUE_FILE, "r") as f:
        return json.load(f)

def save_queue(queue):
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)

def mark_complete(doc_id: str):
    queue = load_queue()
    if doc_id in queue["pending"]:
        queue["pending"].remove(doc_id)
    if doc_id not in queue["completed"]:
        queue["completed"].append(doc_id)
        queue["reviewed"] += 1
    save_queue(queue)
    print(f"{doc_id} marked as complete. Total reviewed: {queue['reviewed']}/49")

def mark_flagged(doc_id: str, reason: str):
    queue = load_queue()
    queue["flagged"].append({"id": doc_id, "reason": reason, "date": str(datetime.today().date())})
    save_queue(queue)
    print(f"{doc_id} flagged: {reason}")

def print_progress():
    queue = load_queue()
    print(f"\n--- Review Progress ---")
    print(f"Total Documents : {queue['total_documents']}")
    print(f"Reviewed        : {queue['reviewed']}")
    print(f"Pending         : {len(queue['pending'])}")
    print(f"Flagged         : {len(queue['flagged'])}")
    remaining = queue['total_documents'] - queue['reviewed']
    print(f"Remaining       : {remaining}")
    print("----------------------\n")

# Run a quick progress check
print_progress()
