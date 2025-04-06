import json
from datetime import datetime
from pathlib import Path

FEEDBACK_LOG = Path("logs/feedback_log.jsonl")
FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)

def log_feedback(rfp_name, agent_name, output_text, rating, comment=""):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "rfp_file": rfp_name,
        "agent": agent_name,
        "output": output_text,
        "rating": rating,  # "👍" or "👎"
        "comment": comment
    }
    with open(FEEDBACK_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
